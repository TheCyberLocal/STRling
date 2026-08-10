use serde_json::{json, Value};
use strling_kernel::safety_analysis::{
    analyze_safety, SafetyEvidence, SafetyFindingCode, SafetyUncertaintyCode,
    SafetyUncertaintyReason,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::NodeId;
use strling_kernel::structural_analysis::analyze_structure;

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

fn literal(id: &str, text: &str) -> Value {
    json!({"node_id": id, "kind": "literal", "text": text})
}

fn repeat(id: &str, body: Value, minimum: u64, maximum: Value, mode: &str) -> Value {
    json!({
        "node_id": id,
        "kind": "repeat",
        "body": body,
        "min": minimum,
        "max": maximum,
        "mode": mode
    })
}

fn analyze_program(semantic: &SemanticProgram) -> strling_kernel::safety_analysis::SafetyAnalysis {
    let foundational = analyze(semantic).expect("test program needs foundational facts");
    let structural =
        analyze_structure(semantic, &foundational).expect("test program needs structural facts");
    analyze_safety(semantic, &foundational, &structural).expect("safety analysis must succeed")
}

fn finding_codes(semantic: &SemanticProgram) -> Vec<SafetyFindingCode> {
    analyze_program(semantic)
        .findings()
        .map(|finding| finding.code)
        .collect()
}

fn node_id(value: &str) -> NodeId {
    NodeId::try_from(value).expect("test node identity must be valid")
}

#[test]
fn unbounded_progress_findings_distinguish_proven_consumption_and_zero_progress() {
    let consuming = program(repeat(
        "node:consuming",
        literal("node:consuming.body", "a"),
        0,
        Value::Null,
        "greedy",
    ));
    assert!(finding_codes(&consuming).is_empty());

    let nullable = program(repeat(
        "node:nullable",
        json!({"node_id": "node:nullable.body", "kind": "empty"}),
        0,
        Value::Null,
        "greedy",
    ));
    let analysis = analyze_program(&nullable);
    let finding = analysis.findings().next().expect("nullable repeat finding");
    assert_eq!(finding.code, SafetyFindingCode::UnboundedNullableRepetition);
    assert_eq!(
        finding.evidence_node_ids,
        vec![node_id("node:nullable"), node_id("node:nullable.body")]
    );
    assert!(matches!(
        finding.evidence,
        SafetyEvidence::RepetitionProgress { .. }
    ));
}

#[test]
fn bounded_and_exact_nullable_repetitions_do_not_receive_unbounded_findings() {
    for (id, minimum, maximum) in [("node:bounded", 0, json!(5)), ("node:exact", 3, json!(3))] {
        let semantic = program(repeat(
            id,
            json!({"node_id": format!("{id}.body"), "kind": "empty"}),
            minimum,
            maximum,
            "greedy",
        ));
        assert!(
            finding_codes(&semantic).is_empty(),
            "unexpected finding for {id}"
        );
    }
}

#[test]
fn indeterminate_backreference_progress_has_its_own_stable_code() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:optional",
                "body": repeat(
                    "node:optional",
                    literal("node:optional.body", "a"),
                    0,
                    json!(1),
                    "greedy"
                )
            },
            repeat(
                "node:repeat",
                json!({
                    "node_id": "node:reference",
                    "kind": "backreference",
                    "capture_id": "capture:optional"
                }),
                1,
                Value::Null,
                "greedy"
            )
        ]
    }));

    assert!(finding_codes(&semantic).contains(&SafetyFindingCode::UnboundedIndeterminateProgress));
}

#[test]
fn direct_and_capture_wrapped_variable_nested_repetitions_are_proven() {
    let direct = program(repeat(
        "node:outer",
        repeat(
            "node:inner",
            literal("node:atom", "a"),
            1,
            Value::Null,
            "greedy",
        ),
        1,
        Value::Null,
        "greedy",
    ));
    assert!(finding_codes(&direct).contains(&SafetyFindingCode::NestedRepetitionOverlap));

    let wrapped = program(repeat(
        "node:outer",
        json!({
            "node_id": "node:capture",
            "kind": "capture",
            "capture_id": "capture:nested",
            "body": repeat(
                "node:inner",
                literal("node:atom", "a"),
                1,
                json!(2),
                "lazy"
            )
        }),
        0,
        Value::Null,
        "lazy",
    ));
    let analysis = analyze_program(&wrapped);
    let finding = analysis
        .findings()
        .find(|finding| finding.code == SafetyFindingCode::NestedRepetitionOverlap)
        .expect("capture-transparent nested finding");
    let SafetyEvidence::NestedRepetition { path, .. } = &finding.evidence else {
        panic!("nested finding needs nested evidence");
    };
    assert_eq!(
        path,
        &vec![
            node_id("node:outer"),
            node_id("node:capture"),
            node_id("node:inner")
        ]
    );
}

#[test]
fn fixed_inner_or_bounded_outer_repetition_is_not_nested_amplification() {
    let fixed_inner = program(repeat(
        "node:outer",
        repeat(
            "node:inner",
            literal("node:atom", "a"),
            1,
            json!(1),
            "greedy",
        ),
        0,
        Value::Null,
        "greedy",
    ));
    assert!(!finding_codes(&fixed_inner).contains(&SafetyFindingCode::NestedRepetitionOverlap));

    let bounded_outer = program(repeat(
        "node:outer",
        repeat(
            "node:inner",
            literal("node:atom", "a"),
            1,
            Value::Null,
            "greedy",
        ),
        0,
        json!(4),
        "greedy",
    ));
    assert!(!finding_codes(&bounded_outer).contains(&SafetyFindingCode::NestedRepetitionOverlap));
}

#[test]
fn possessive_and_atomic_boundaries_protect_nested_partition_proof() {
    for (outer_mode, inner_mode) in [("possessive", "greedy"), ("greedy", "possessive")] {
        let semantic = program(repeat(
            "node:outer",
            repeat(
                "node:inner",
                literal("node:atom", "a"),
                1,
                Value::Null,
                inner_mode,
            ),
            0,
            Value::Null,
            outer_mode,
        ));
        assert!(!finding_codes(&semantic).contains(&SafetyFindingCode::NestedRepetitionOverlap));
    }

    let atomic = program(repeat(
        "node:outer",
        json!({
            "node_id": "node:atomic",
            "kind": "atomic",
            "body": repeat(
                "node:inner",
                literal("node:atom", "a"),
                1,
                Value::Null,
                "greedy"
            )
        }),
        0,
        Value::Null,
        "greedy",
    ));
    assert!(!finding_codes(&atomic).contains(&SafetyFindingCode::NestedRepetitionOverlap));
}

#[test]
fn nested_analysis_enters_assertion_bodies_without_crossing_assertion_boundaries() {
    let semantic = program(json!({
        "node_id": "node:lookahead",
        "kind": "lookaround",
        "direction": "ahead",
        "polarity": "positive",
        "body": repeat(
            "node:outer",
            repeat(
                "node:inner",
                literal("node:atom", "a"),
                1,
                Value::Null,
                "greedy"
            ),
            1,
            Value::Null,
            "greedy"
        )
    }));
    assert!(finding_codes(&semantic).contains(&SafetyFindingCode::NestedRepetitionOverlap));
}

#[test]
fn indeterminate_nested_progress_is_preserved_as_uncertainty() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:optional",
                "body": repeat(
                    "node:optional",
                    literal("node:optional.body", "a"),
                    0,
                    json!(1),
                    "greedy"
                )
            },
            repeat(
                "node:outer",
                repeat(
                    "node:inner",
                    json!({
                        "node_id": "node:reference",
                        "kind": "backreference",
                        "capture_id": "capture:optional"
                    }),
                    1,
                    Value::Null,
                    "greedy"
                ),
                1,
                Value::Null,
                "greedy"
            )
        ]
    }));
    let analysis = analyze_program(&semantic);
    let uncertainty = analysis
        .uncertainties()
        .find(|uncertainty| uncertainty.code == SafetyUncertaintyCode::NestedRepetitionNotProven)
        .expect("indeterminate nested relationship must remain visible");
    assert_eq!(
        uncertainty.reason,
        SafetyUncertaintyReason::IndeterminateProgress
    );
    assert!(!analysis
        .findings()
        .any(|finding| finding.code == SafetyFindingCode::NestedRepetitionOverlap));
}
