use serde_json::{json, Value};
use strling_kernel::capability_evaluation::{
    evaluate_capabilities, CapabilityDisposition, CapabilityEvaluationErrorCode,
    ConstraintDisposition, ConstraintEvidence,
};
use strling_kernel::normalization::normalize;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;

const SEEDS: [u64; 4] = [
    0x4341_5041_4249_4c49,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const CASES_PER_SEED: usize = 64;
const GENERATED_PROGRAM_COUNT: usize = SEEDS.len() * CASES_PER_SEED;
const AUTHORED_PROFILE_COUNT: usize = 4;
const EXPECTED_PROFILE_EVALUATIONS: usize = GENERATED_PROGRAM_COUNT * AUTHORED_PROFILE_COUNT * 2;
const EXPECTED_MALFORMED_PROFILES: usize = AUTHORED_PROFILE_COUNT * 4;

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
        let case_index = self.case_index;
        self.case_index += 1;
        let prefix = format!("node:capability.generated.{case_index}");
        let capture_id = format!("capture:capability.generated.{case_index}");
        let capture_name = format!("capability_generated_{case_index}");
        let lookbehind_kind = self.pick(3);
        let repetition_mode = ["greedy", "lazy", "possessive"][self.pick(3)];
        let position = [
            "input_start",
            "input_end",
            "line_start",
            "line_end",
            "word_boundary",
            "not_word_boundary",
            "end_before_final_line_terminator",
        ][self.pick(7)];
        let unicode_literal = self.boolean();
        let unicode_set = self.boolean();
        let unicode_property = self.boolean();
        let unicode_class = self.boolean();
        let case_matching = if self.boolean() {
            "insensitive"
        } else {
            "sensitive"
        };

        let lookbehind_body = match lookbehind_kind {
            0 => literal(
                &format!("{prefix}.lookbehind.body"),
                &"f".repeat(self.pick(4) + 1),
            ),
            1 => {
                let maximum = self.pick(300) + 2;
                json!({
                    "node_id": format!("{prefix}.lookbehind.body"),
                    "kind": "alternation",
                    "branches": [
                        literal(&format!("{prefix}.lookbehind.short"), "g"),
                        literal(
                            &format!("{prefix}.lookbehind.long"),
                            &"h".repeat(maximum)
                        )
                    ]
                })
            }
            _ => json!({
                "node_id": format!("{prefix}.lookbehind.body"),
                "kind": "repeat",
                "body": literal(&format!("{prefix}.lookbehind.operand"), "i"),
                "min": self.pick(3),
                "max": null,
                "mode": "greedy"
            }),
        };

        let mut members = vec![if unicode_set {
            json!({"kind": "literal", "value": "é"})
        } else {
            json!({"kind": "literal", "value": "k"})
        }];
        if self.boolean() {
            members.push(json!({"kind": "range", "start": "m", "end": "p"}));
        }
        if unicode_class {
            members.push(json!({
                "kind": "builtin",
                "name": (["digit", "word", "whitespace"][self.pick(3)]),
                "domain": "unicode",
                "negated": self.boolean()
            }));
        }
        if unicode_property {
            members.push(json!({
                "kind": "unicode_property",
                "property": "General_Category",
                "value": (["Letter", "Number"][self.pick(2)]),
                "negated": self.boolean()
            }));
        }

        let candidate: SemanticProgram = serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": case_matching,
            "root": {
                "node_id": format!("{prefix}.root"),
                "kind": "sequence",
                "items": [
                    {
                        "node_id": format!("{prefix}.capture"),
                        "kind": "capture",
                        "capture_id": capture_id,
                        "name": capture_name,
                        "body": literal(&format!("{prefix}.capture.body"), "a")
                    },
                    {
                        "node_id": format!("{prefix}.reference"),
                        "kind": "backreference",
                        "capture_id": format!("capture:capability.generated.{case_index}")
                    },
                    {
                        "node_id": format!("{prefix}.lookahead"),
                        "kind": "lookaround",
                        "direction": "ahead",
                        "polarity": if self.boolean() { "positive" } else { "negative" },
                        "body": literal(&format!("{prefix}.lookahead.body"), "b")
                    },
                    {
                        "node_id": format!("{prefix}.lookbehind"),
                        "kind": "lookaround",
                        "direction": "behind",
                        "polarity": if self.boolean() { "positive" } else { "negative" },
                        "body": lookbehind_body
                    },
                    {
                        "node_id": format!("{prefix}.atomic"),
                        "kind": "atomic",
                        "body": literal(&format!("{prefix}.atomic.body"), "c")
                    },
                    {
                        "node_id": format!("{prefix}.repeat"),
                        "kind": "repeat",
                        "body": literal(&format!("{prefix}.repeat.body"), "d"),
                        "min": self.pick(3),
                        "max": self.pick(5) + 3,
                        "mode": repetition_mode
                    },
                    {
                        "node_id": format!("{prefix}.characters"),
                        "kind": "character_set",
                        "negated": self.boolean(),
                        "members": members
                    },
                    {
                        "node_id": format!("{prefix}.position"),
                        "kind": "position",
                        "position": position
                    },
                    literal(
                        &format!("{prefix}.literal"),
                        if unicode_literal { "λ" } else { "z" }
                    )
                ]
            }
        }))
        .expect("generated candidate must deserialize");
        let normalized = normalize(&candidate).expect("generated candidate must normalize");
        assert_eq!(
            normalized, candidate,
            "generator must produce canonical Semantic IR"
        );
        normalized
    }
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn profiles() -> Vec<TargetProfile> {
    PROFILE_FIXTURES
        .iter()
        .map(|fixture| {
            serde_json::from_str(fixture).expect("authored target profile must deserialize")
        })
        .collect()
}

#[test]
fn generated_capability_properties_are_reproducible_and_sound() {
    let profiles = profiles();
    let mut generated_programs = 0;
    let mut profile_evaluations = 0;
    let mut profile_differentials = 0;
    let mut unknown_results = 0;
    let mut constraint_violations = 0;

    for seed in SEEDS {
        let mut generator = Generator::new(seed);
        for _ in 0..CASES_PER_SEED {
            let semantic = generator.semantic_program();
            let foundational = analyze(&semantic).expect("generated foundational facts");
            let structural =
                analyze_structure(&semantic, &foundational).expect("generated structural facts");
            let semantic_before = semantic.clone();
            let foundational_before = foundational.clone();
            let structural_before = structural.clone();
            let mut profile_results = Vec::new();

            for target in &profiles {
                let target_before = target.clone();
                let first = evaluate_capabilities(&semantic, &foundational, &structural, target)
                    .expect("first generated evaluation");
                let second = evaluate_capabilities(&semantic, &foundational, &structural, target)
                    .expect("second generated evaluation");
                profile_evaluations += 2;

                assert_eq!(first, second, "identical inputs must be deterministic");
                assert_eq!(first.results.len(), first.requirements.len());
                assert!(first
                    .results
                    .iter()
                    .zip(first.requirements.iter())
                    .all(|(result, requirement)| result.requirement == *requirement));

                for result in &first.results {
                    if result.profile_capability.is_none() {
                        assert_eq!(
                            result.disposition,
                            CapabilityDisposition::Unknown,
                            "absent capability data must stay unknown"
                        );
                    }
                    if result.disposition == CapabilityDisposition::Unknown {
                        unknown_results += 1;
                    }
                    if result.disposition == CapabilityDisposition::ConstraintViolation {
                        constraint_violations += 1;
                        let violated: Vec<_> = result
                            .constraint_evaluations
                            .iter()
                            .filter(|evaluation| {
                                evaluation.disposition == ConstraintDisposition::Violated
                            })
                            .collect();
                        assert!(!violated.is_empty());
                        for evaluation in violated {
                            let ConstraintEvidence::RequirementFact(fact) = &evaluation.evidence
                            else {
                                panic!("constraint violation requires typed requirement evidence");
                            };
                            assert!(result.constraint_facts.contains(fact));
                        }
                    }
                }

                assert_eq!(*target, target_before, "target profile must be immutable");
                profile_results.push(first);
            }

            let requirements = &profile_results[0].requirements;
            assert!(profile_results
                .iter()
                .all(|evaluation| evaluation.requirements == *requirements));
            let baseline: Vec<_> = profile_results[0]
                .results
                .iter()
                .map(|result| result.disposition)
                .collect();
            if profile_results.iter().skip(1).any(|evaluation| {
                evaluation
                    .results
                    .iter()
                    .map(|result| result.disposition)
                    .collect::<Vec<_>>()
                    != baseline
            }) {
                profile_differentials += 1;
            }

            assert_eq!(semantic, semantic_before);
            assert_eq!(foundational, foundational_before);
            assert_eq!(structural, structural_before);
            generated_programs += 1;
        }
    }

    assert_eq!(generated_programs, GENERATED_PROGRAM_COUNT);
    assert_eq!(profile_evaluations, EXPECTED_PROFILE_EVALUATIONS);
    assert!(profile_differentials > 0);
    assert!(unknown_results > 0);
    assert!(constraint_violations > 0);
}

#[test]
fn controlled_malformed_profiles_never_enter_evaluation() {
    let semantic: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {
            "node_id": "node:malformed.atomic",
            "kind": "atomic",
            "body": literal("node:malformed.atomic.body", "a")
        }
    }))
    .expect("controlled semantic program");
    let foundational = analyze(&semantic).expect("foundational facts");
    let structural = analyze_structure(&semantic, &foundational).expect("structural facts");
    let mut malformed_profiles = Vec::new();

    for target in profiles() {
        let mut reversed = target.clone();
        reversed.capabilities.reverse();
        malformed_profiles.push(reversed);

        let mut duplicate_capability = target.clone();
        duplicate_capability
            .capabilities
            .push(duplicate_capability.capabilities[0].clone());
        duplicate_capability
            .capabilities
            .sort_by(|left, right| left.capability_id.cmp(&right.capability_id));
        malformed_profiles.push(duplicate_capability);

        let mut empty_evidence = target.clone();
        empty_evidence.evidence.clear();
        malformed_profiles.push(empty_evidence);

        let mut duplicate_evidence = target;
        duplicate_evidence
            .evidence
            .push(duplicate_evidence.evidence[0].clone());
        duplicate_evidence
            .evidence
            .sort_by(|left, right| left.evidence_id.cmp(&right.evidence_id));
        malformed_profiles.push(duplicate_evidence);
    }

    assert_eq!(malformed_profiles.len(), EXPECTED_MALFORMED_PROFILES);
    for target in malformed_profiles {
        let errors = evaluate_capabilities(&semantic, &foundational, &structural, &target)
            .expect_err("malformed profile must fail validation");
        assert!(errors
            .errors
            .iter()
            .all(|error| error.code == CapabilityEvaluationErrorCode::InvalidTargetProfile));
    }
}
