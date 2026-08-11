use serde_json::{json, Value};
use strling_kernel::capability_evaluation::{
    evaluate_capabilities, CapabilityDisposition, CapabilityEvaluation,
};
use strling_kernel::portability_planning::{
    plan_portability, PortabilityPlanningErrorCode, RequirementPlanningDisposition,
    UnresolvedPlanningReason,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::{analyze, SemanticFacts};
use strling_kernel::structural_analysis::{analyze_structure, StructuralFacts};
use strling_kernel::target::{PortabilityStatus, TargetProfile};

const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("test program must deserialize")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn profile(fixture: &str) -> TargetProfile {
    serde_json::from_str(fixture).expect("authored profile must deserialize")
}

fn prerequisites(semantic: &SemanticProgram) -> (SemanticFacts, StructuralFacts) {
    let foundational = analyze(semantic).expect("foundational analysis must succeed");
    let structural =
        analyze_structure(semantic, &foundational).expect("structural analysis must succeed");
    (foundational, structural)
}

fn evaluate(
    semantic: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    target: &TargetProfile,
) -> CapabilityEvaluation {
    evaluate_capabilities(semantic, foundational, structural, target)
        .expect("capability evaluation must succeed")
}

fn atomic(node_id: &str, body_id: &str, text: &str) -> Value {
    json!({
        "node_id": node_id,
        "kind": "atomic",
        "body": literal(body_id, text)
    })
}

fn lookahead(node_id: &str, body_id: &str) -> Value {
    json!({
        "node_id": node_id,
        "kind": "lookaround",
        "direction": "ahead",
        "polarity": "positive",
        "body": literal(body_id, "x")
    })
}

#[test]
fn program_without_special_requirements_is_natively_portable() {
    let semantic = program(literal("node:literal", "abc"));
    let target = profile(PCRE2_1042);
    let (foundational, structural) = prerequisites(&semantic);
    let evaluation = evaluate(&semantic, &foundational, &structural, &target);

    let plan = plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
        .expect("empty requirement plan must succeed");

    assert!(plan.decisions.is_empty());
    assert!(plan.unresolved_requirements.is_empty());
    assert_eq!(plan.status, Some(PortabilityStatus::Native));
    assert_eq!(plan.target_profile, target.reference().expect("reference"));
}

#[test]
fn supported_results_become_native_with_exact_evidence() {
    let semantic = program(atomic("node:atomic", "node:atomic.body", "a"));
    let target = profile(PCRE2_1042);
    let (foundational, structural) = prerequisites(&semantic);
    let evaluation = evaluate(&semantic, &foundational, &structural, &target);

    let plan = plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
        .expect("native planning must succeed");

    assert_eq!(plan.status, Some(PortabilityStatus::Native));
    assert_eq!(plan.decisions.len(), 1);
    assert_eq!(plan.decisions[0].identity.ordinal, 0);
    match &plan.decisions[0].disposition {
        RequirementPlanningDisposition::Native(decision) => {
            assert_eq!(
                decision.capability_result.disposition,
                CapabilityDisposition::Supported
            );
            assert_eq!(decision.capability_result, evaluation.results[0]);
        }
        disposition => panic!("expected native decision, got {disposition:?}"),
    }
}

#[test]
fn multiple_supported_requirements_remain_independent_and_ordered() {
    let semantic = program(json!({
        "node_id": "node:sequence",
        "kind": "sequence",
        "items": [
            atomic("node:atomic", "node:atomic.body", "a"),
            {
                "node_id": "node:possessive",
                "kind": "repeat",
                "body": literal("node:possessive.body", "b"),
                "min": 1,
                "max": null,
                "mode": "possessive"
            }
        ]
    }));
    let target = profile(PCRE2_1042);
    let (foundational, structural) = prerequisites(&semantic);
    let evaluation = evaluate(&semantic, &foundational, &structural, &target);

    let plan = plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
        .expect("multiple native requirements must plan");

    assert_eq!(plan.decisions.len(), 2);
    assert_eq!(plan.status, Some(PortabilityStatus::Native));
    assert!(plan.decisions.iter().all(|decision| matches!(
        decision.disposition,
        RequirementPlanningDisposition::Native(_)
    )));
    assert_eq!(plan.decisions[0].identity.ordinal, 0);
    assert_eq!(plan.decisions[1].identity.ordinal, 1);
    assert_ne!(plan.decisions[0].identity, plan.decisions[1].identity);
}

#[test]
fn unknown_capability_remains_unresolved_outside_final_status() {
    let semantic = program(lookahead("node:lookahead", "node:lookahead.body"));
    let target = profile(PCRE2_1042);
    let (foundational, structural) = prerequisites(&semantic);
    let evaluation = evaluate(&semantic, &foundational, &structural, &target);
    assert_eq!(
        evaluation.results[0].disposition,
        CapabilityDisposition::Unknown
    );

    let plan = plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
        .expect("unknown evidence must be preserved");

    assert_eq!(plan.status, None);
    assert_eq!(plan.unresolved_requirements.len(), 1);
    match &plan.decisions[0].disposition {
        RequirementPlanningDisposition::Unresolved(decision) => {
            assert_eq!(decision.reason, UnresolvedPlanningReason::CapabilityUnknown);
            assert_eq!(
                decision.capability_result.disposition,
                CapabilityDisposition::Unknown
            );
        }
        disposition => panic!("expected unresolved evidence, got {disposition:?}"),
    }
}

#[test]
fn mixed_native_and_unknown_requirements_do_not_claim_final_status() {
    let semantic = program(json!({
        "node_id": "node:sequence",
        "kind": "sequence",
        "items": [
            atomic("node:atomic", "node:atomic.body", "a"),
            lookahead("node:lookahead", "node:lookahead.body")
        ]
    }));
    let target = profile(PCRE2_1042);
    let (foundational, structural) = prerequisites(&semantic);
    let evaluation = evaluate(&semantic, &foundational, &structural, &target);

    let plan = plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
        .expect("mixed evidence must plan");

    assert_eq!(plan.decisions.len(), 2);
    assert_eq!(plan.status, None);
    assert_eq!(plan.unresolved_requirements.len(), 1);
    assert!(plan.decisions.iter().any(|decision| matches!(
        decision.disposition,
        RequirementPlanningDisposition::Native(_)
    )));
    assert!(plan.decisions.iter().any(|decision| matches!(
        decision.disposition,
        RequirementPlanningDisposition::Unresolved(_)
    )));
}

#[test]
fn mismatched_capability_result_is_rejected() {
    let semantic = program(atomic("node:atomic", "node:atomic.body", "a"));
    let target = profile(PCRE2_1042);
    let (foundational, structural) = prerequisites(&semantic);
    let mut evaluation = evaluate(&semantic, &foundational, &structural, &target);
    evaluation.results.clear();

    let errors = plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
        .expect_err("missing result must fail correspondence");

    assert_eq!(
        errors.errors[0].code,
        PortabilityPlanningErrorCode::RequirementResultMismatch
    );
}

#[test]
fn exact_program_fingerprint_prevents_cross_program_evidence_reuse() {
    let evaluated_program = program(atomic("node:atomic", "node:atomic.body", "a"));
    let supplied_program = program(atomic("node:atomic", "node:atomic.body", "b"));
    let target = profile(PCRE2_1042);
    let (evaluated_foundational, evaluated_structural) = prerequisites(&evaluated_program);
    let evaluation = evaluate(
        &evaluated_program,
        &evaluated_foundational,
        &evaluated_structural,
        &target,
    );
    let (supplied_foundational, supplied_structural) = prerequisites(&supplied_program);

    let errors = plan_portability(
        &supplied_program,
        &supplied_foundational,
        &supplied_structural,
        &target,
        &evaluation,
    )
    .expect_err("cross-program evaluation must fail");

    assert_eq!(
        errors.errors[0].code,
        PortabilityPlanningErrorCode::EvaluationProgramMismatch
    );
}

#[test]
fn mismatched_profile_is_rejected_without_engine_assumptions() {
    let semantic = program(atomic("node:atomic", "node:atomic.body", "a"));
    let evaluated_target = profile(PCRE2_1042);
    let supplied_target = profile(ECMASCRIPT);
    let (foundational, structural) = prerequisites(&semantic);
    let evaluation = evaluate(&semantic, &foundational, &structural, &evaluated_target);

    let errors = plan_portability(
        &semantic,
        &foundational,
        &structural,
        &supplied_target,
        &evaluation,
    )
    .expect_err("mismatched exact profile must fail");

    assert_eq!(
        errors.errors[0].code,
        PortabilityPlanningErrorCode::TargetProfileMismatch
    );
}

#[test]
fn repeated_planning_is_deterministic_and_inputs_are_immutable() {
    let semantic = program(json!({
        "node_id": "node:sequence",
        "kind": "sequence",
        "items": [
            atomic("node:atomic", "node:atomic.body", "a"),
            lookahead("node:lookahead", "node:lookahead.body")
        ]
    }));
    let target = profile(PCRE2_1042);
    let (foundational, structural) = prerequisites(&semantic);
    let evaluation = evaluate(&semantic, &foundational, &structural, &target);
    let semantic_before = semantic.clone();
    let foundational_before = foundational.clone();
    let structural_before = structural.clone();
    let target_before = target.clone();
    let evaluation_before = evaluation.clone();

    let first = plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
        .expect("first plan");
    let second = plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
        .expect("second plan");

    assert_eq!(first, second);
    assert_eq!(semantic, semantic_before);
    assert_eq!(foundational, foundational_before);
    assert_eq!(structural, structural_before);
    assert_eq!(target, target_before);
    assert_eq!(evaluation, evaluation_before);
}
