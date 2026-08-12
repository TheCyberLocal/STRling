use std::collections::BTreeSet;

use serde_json::{json, Value};
use strling_kernel::capability_evaluation::{
    evaluate_capabilities, CapabilityDisposition, CapabilityEvaluation,
};
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::{
    certified_rewrite_registry, plan_portability, RequirementPlanningDisposition,
    RewriteAttemptDisposition, RewriteProofDisposition, RewriteStrategyId,
    UnresolvedPlanningReason,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::Sha256Digest;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;

const SEEDS: [u64; 4] = [
    0x504f_5254_4142_4c45,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const CASES_PER_SEED: usize = 64;
const GENERATED_PROGRAM_COUNT: usize = SEEDS.len() * CASES_PER_SEED;
const AUTHORED_PROFILE_COUNT: usize = 4;
const EXPECTED_PROFILE_EVALUATIONS: usize = GENERATED_PROGRAM_COUNT * AUTHORED_PROFILE_COUNT;
const EXPECTED_PLAN_INVOCATIONS: usize = EXPECTED_PROFILE_EVALUATIONS * 2;
const EXPECTED_MALFORMED_CASES: usize = AUTHORED_PROFILE_COUNT * 4;
const EXPECTED_REWRITE_PLANS: usize = 64;
const EXPECTED_UNRESOLVED_REQUIREMENTS: usize = 0;
const EXPECTED_DIFFERENTIAL_PROGRAMS: usize = 160;

const PROFILE_FIXTURES: [&str; AUTHORED_PROFILE_COUNT] = [
    include_str!("../../spec/targets/profiles/pcre2-10.42.json"),
    include_str!("../../spec/targets/profiles/pcre2-10.43.json"),
    include_str!("../../spec/targets/profiles/ecmascript-2024.json"),
    include_str!("../../spec/targets/profiles/python-re-3.11.json"),
];

struct Generator {
    state: u64,
    case_index: usize,
}

impl Generator {
    fn new(seed: u64) -> Self {
        Self {
            state: seed,
            case_index: 0,
        }
    }

    fn next(&mut self) -> u64 {
        self.state = self
            .state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        self.state
    }

    fn pick(&mut self, count: usize) -> usize {
        (self.next() % count as u64) as usize
    }

    fn boolean(&mut self) -> bool {
        self.pick(2) == 1
    }

    fn semantic_program(&mut self) -> SemanticProgram {
        let index = self.case_index;
        self.case_index += 1;
        let prefix = format!("node:portability.generated.{index}");
        let case_matching = if self.boolean() {
            "insensitive"
        } else {
            "sensitive"
        };
        let root = match index % 8 {
            0 => literal(&format!("{prefix}.literal"), "abc"),
            1 => atomic_literal(&prefix, self.boolean()),
            2 => atomic_alternation(&prefix),
            3 => possessive(&prefix),
            4 => lookahead(&prefix),
            5 => variable_lookbehind(&prefix, self.pick(300) + 2),
            6 => fixed_lookbehind(&prefix),
            _ => json!({
                "node_id": format!("{prefix}.sequence"),
                "kind": "sequence",
                "items": [
                    atomic_literal(&format!("{prefix}.mixed.atomic"), false),
                    possessive(&format!("{prefix}.mixed.possessive")),
                    if self.boolean() {
                        fixed_lookbehind(&format!("{prefix}.mixed.fixed"))
                    } else {
                        variable_lookbehind(
                            &format!("{prefix}.mixed.variable"),
                            self.pick(300) + 2,
                        )
                    }
                ]
            }),
        };
        let raw: SemanticProgram = serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": case_matching,
            "root": root
        }))
        .expect("generated program must deserialize");
        normalize(&raw).expect("generated program must normalize")
    }
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn atomic_literal(prefix: &str, unicode: bool) -> Value {
    json!({
        "node_id": format!("{prefix}.atomic"),
        "kind": "atomic",
        "body": literal(
            &format!("{prefix}.atomic.body"),
            if unicode { "λ" } else { "a" },
        )
    })
}

fn atomic_alternation(prefix: &str) -> Value {
    json!({
        "node_id": format!("{prefix}.atomic"),
        "kind": "atomic",
        "body": {
            "node_id": format!("{prefix}.atomic.body"),
            "kind": "alternation",
            "branches": [
                literal(&format!("{prefix}.atomic.left"), "a"),
                literal(&format!("{prefix}.atomic.right"), "b")
            ]
        }
    })
}

fn possessive(prefix: &str) -> Value {
    json!({
        "node_id": format!("{prefix}.possessive"),
        "kind": "repeat",
        "body": literal(&format!("{prefix}.possessive.body"), "p"),
        "min": 1,
        "max": null,
        "mode": "possessive"
    })
}

fn lookahead(prefix: &str) -> Value {
    json!({
        "node_id": format!("{prefix}.lookahead"),
        "kind": "lookaround",
        "direction": "ahead",
        "polarity": "positive",
        "body": literal(&format!("{prefix}.lookahead.body"), "l")
    })
}

fn fixed_lookbehind(prefix: &str) -> Value {
    json!({
        "node_id": format!("{prefix}.lookbehind"),
        "kind": "lookaround",
        "direction": "behind",
        "polarity": "positive",
        "body": literal(&format!("{prefix}.lookbehind.body"), "f")
    })
}

fn variable_lookbehind(prefix: &str, maximum: usize) -> Value {
    json!({
        "node_id": format!("{prefix}.lookbehind"),
        "kind": "lookaround",
        "direction": "behind",
        "polarity": "positive",
        "body": {
            "node_id": format!("{prefix}.lookbehind.body"),
            "kind": "alternation",
            "branches": [
                literal(&format!("{prefix}.lookbehind.short"), "v"),
                literal(
                    &format!("{prefix}.lookbehind.long"),
                    &"w".repeat(maximum),
                )
            ]
        }
    })
}

fn profiles() -> Vec<TargetProfile> {
    PROFILE_FIXTURES
        .iter()
        .map(|fixture| serde_json::from_str(fixture).expect("authored profile"))
        .collect()
}

fn evaluation_for(
    semantic: &SemanticProgram,
    target: &TargetProfile,
) -> (
    strling_kernel::semantic_analysis::SemanticFacts,
    strling_kernel::structural_analysis::StructuralFacts,
    CapabilityEvaluation,
) {
    let foundational = analyze(semantic).expect("foundational facts");
    let structural = analyze_structure(semantic, &foundational).expect("structural facts");
    let evaluation = evaluate_capabilities(semantic, &foundational, &structural, target)
        .expect("capability evaluation");
    (foundational, structural, evaluation)
}

fn disposition_signature(
    plan: &strling_kernel::portability_planning::PortabilityPlan,
) -> Vec<&'static str> {
    plan.decisions
        .iter()
        .map(|decision| match decision.disposition {
            RequirementPlanningDisposition::Native(_) => "native",
            RequirementPlanningDisposition::EquivalentRewrite(_) => "equivalent_rewrite",
            RequirementPlanningDisposition::Unsupported(_) => "unsupported",
            RequirementPlanningDisposition::Unresolved(_) => "unresolved",
        })
        .collect()
}

#[test]
fn generated_portability_plans_are_reproducible_complete_and_sound() {
    let profiles = profiles();
    let mut generated_programs = 0;
    let mut profile_evaluations = 0;
    let mut plan_invocations = 0;
    let mut rewrite_plan_count = 0;
    let mut unresolved_requirement_count = 0;
    let mut profile_differential_programs = 0;

    for seed in SEEDS {
        let mut generator = Generator::new(seed);
        for _ in 0..CASES_PER_SEED {
            let semantic = generator.semantic_program();
            generated_programs += 1;
            let mut signatures = BTreeSet::new();
            for target in &profiles {
                let (foundational, structural, evaluation) = evaluation_for(&semantic, target);
                profile_evaluations += 1;
                let semantic_before = semantic.clone();
                let foundational_before = foundational.clone();
                let structural_before = structural.clone();
                let target_before = target.clone();
                let evaluation_before = evaluation.clone();

                let first =
                    plan_portability(&semantic, &foundational, &structural, target, &evaluation)
                        .expect("first generated plan");
                let second =
                    plan_portability(&semantic, &foundational, &structural, target, &evaluation)
                        .expect("second generated plan");
                plan_invocations += 2;

                assert_eq!(first, second, "identical inputs require identical plans");
                assert_eq!(first.decisions.len(), evaluation.results.len());
                assert_eq!(
                    first
                        .decisions
                        .iter()
                        .map(|decision| &decision.requirement)
                        .collect::<Vec<_>>(),
                    evaluation.requirements.iter().collect::<Vec<_>>()
                );
                first.validate().expect("generated plan must self-validate");

                for (decision, result) in first.decisions.iter().zip(&evaluation.results) {
                    assert_eq!(decision.requirement, result.requirement);
                    match &decision.disposition {
                        RequirementPlanningDisposition::Native(native) => {
                            assert_eq!(
                                native.capability_result.disposition,
                                CapabilityDisposition::Supported
                            );
                        }
                        RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
                            rewrite_plan_count += 1;
                            let certification = certified_rewrite_registry()
                                .expect("authored registry")
                                .strategy(RewriteStrategyId::ElideAtomicLiteralV1)
                                .expect("atomic-literal strategy");
                            assert_eq!(
                                rewrite.rewrite_plan.strategy_id,
                                RewriteStrategyId::ElideAtomicLiteralV1
                            );
                            assert_eq!(
                                rewrite.rewrite_plan.certification.strategy_fingerprint,
                                certification.strategy_fingerprint
                            );
                            assert_eq!(
                                rewrite
                                    .rewrite_plan
                                    .certification
                                    .conformance_evidence_sha256,
                                certification.definition.conformance_evidence.sha256
                            );
                            assert!(rewrite.rewrite_plan.proof.iter().all(|proof| {
                                proof.disposition == RewriteProofDisposition::Satisfied
                            }));
                            assert!(rewrite.rewrite_plan.replacement_support.iter().all(
                                |support| {
                                    support.capability_result.disposition
                                        == CapabilityDisposition::Supported
                                }
                            ));
                        }
                        RequirementPlanningDisposition::Unsupported(unsupported) => {
                            assert_ne!(
                                unsupported.capability_result.disposition,
                                CapabilityDisposition::Unknown
                            );
                            assert!(unsupported.rewrite_attempts.iter().all(|attempt| {
                                !matches!(
                                    attempt.disposition,
                                    RewriteAttemptDisposition::Applicable
                                        | RewriteAttemptDisposition::ProofIndeterminate
                                        | RewriteAttemptDisposition::ReplacementUnknown
                                )
                            }));
                        }
                        RequirementPlanningDisposition::Unresolved(unresolved) => {
                            unresolved_requirement_count += 1;
                            if unresolved.reason == UnresolvedPlanningReason::CapabilityUnknown {
                                assert_eq!(
                                    unresolved.capability_result.disposition,
                                    CapabilityDisposition::Unknown
                                );
                            }
                        }
                    }
                    if result.disposition == CapabilityDisposition::Unknown {
                        assert!(matches!(
                            decision.disposition,
                            RequirementPlanningDisposition::Unresolved(_)
                        ));
                    }
                }

                signatures.insert(disposition_signature(&first));
                assert_eq!(semantic, semantic_before);
                assert_eq!(foundational, foundational_before);
                assert_eq!(structural, structural_before);
                assert_eq!(target, &target_before);
                assert_eq!(evaluation, evaluation_before);
            }
            if signatures.len() > 1 {
                profile_differential_programs += 1;
            }
        }
    }

    assert_eq!(generated_programs, GENERATED_PROGRAM_COUNT);
    assert_eq!(profile_evaluations, EXPECTED_PROFILE_EVALUATIONS);
    assert_eq!(plan_invocations, EXPECTED_PLAN_INVOCATIONS);
    assert_eq!(rewrite_plan_count, EXPECTED_REWRITE_PLANS);
    assert_eq!(
        unresolved_requirement_count,
        EXPECTED_UNRESOLVED_REQUIREMENTS
    );
    assert_eq!(
        profile_differential_programs,
        EXPECTED_DIFFERENTIAL_PROGRAMS
    );
    eprintln!(
        "PORTABILITY_PROPERTIES seeds={SEEDS:?} programs={generated_programs} profile_evaluations={profile_evaluations} plan_invocations={plan_invocations} rewrites={rewrite_plan_count} unresolved={unresolved_requirement_count} differential_programs={profile_differential_programs}"
    );
}

#[test]
fn malformed_planning_correspondence_is_rejected_reproducibly() {
    let semantic: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": atomic_literal("node:portability.malformed", false)
    }))
    .expect("malformed-case source program");
    let semantic = normalize(&semantic).expect("normalized malformed-case program");
    let profiles = profiles();
    let mut malformed_cases = 0;

    for (index, target) in profiles.iter().enumerate() {
        let (foundational, structural, evaluation) = evaluation_for(&semantic, target);

        let mut missing_result = evaluation.clone();
        missing_result.results.clear();
        assert!(plan_portability(
            &semantic,
            &foundational,
            &structural,
            target,
            &missing_result,
        )
        .is_err());
        malformed_cases += 1;

        let mut wrong_program = evaluation.clone();
        wrong_program.semantic_program = Sha256Digest::from_bytes([index as u8 + 1; 32]);
        assert!(plan_portability(
            &semantic,
            &foundational,
            &structural,
            target,
            &wrong_program,
        )
        .is_err());
        malformed_cases += 1;

        let mut missing_requirement = evaluation.clone();
        missing_requirement.requirements.requirements.clear();
        assert!(plan_portability(
            &semantic,
            &foundational,
            &structural,
            target,
            &missing_requirement,
        )
        .is_err());
        malformed_cases += 1;

        let mut wrong_profile_evidence = evaluation.clone();
        wrong_profile_evidence.results[0].profile_capability = None;
        assert!(plan_portability(
            &semantic,
            &foundational,
            &structural,
            target,
            &wrong_profile_evidence,
        )
        .is_err());
        malformed_cases += 1;
    }

    assert_eq!(malformed_cases, EXPECTED_MALFORMED_CASES);
}

#[test]
fn changing_only_the_profile_changes_atomic_literal_representation() {
    let semantic: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": atomic_literal("node:portability.profile", false)
    }))
    .expect("profile differential program");
    let semantic = normalize(&semantic).expect("normalized profile differential program");
    let profiles = profiles();
    let (foundational, structural, pcre_evaluation) = evaluation_for(&semantic, &profiles[0]);
    let ecma_evaluation =
        evaluate_capabilities(&semantic, &foundational, &structural, &profiles[2])
            .expect("ECMAScript evaluation");

    let pcre_plan = plan_portability(
        &semantic,
        &foundational,
        &structural,
        &profiles[0],
        &pcre_evaluation,
    )
    .expect("PCRE plan");
    let ecma_plan = plan_portability(
        &semantic,
        &foundational,
        &structural,
        &profiles[2],
        &ecma_evaluation,
    )
    .expect("ECMAScript plan");

    assert!(matches!(
        pcre_plan.decisions[0].disposition,
        RequirementPlanningDisposition::Native(_)
    ));
    assert!(matches!(
        ecma_plan.decisions[0].disposition,
        RequirementPlanningDisposition::EquivalentRewrite(_)
    ));
}
