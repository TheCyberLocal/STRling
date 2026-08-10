use serde_json::{json, Value};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::{analyze, SemanticAnalysisErrorCode};
use strling_kernel::source::NodeId;
use strling_kernel::structural_analysis::{
    analyze_structure, LengthClassification, ProgressClassification, RepetitionExtent,
};

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

fn node_id(value: &str) -> NodeId {
    NodeId::try_from(value).expect("test node identity must be valid")
}

#[test]
fn literals_assertions_and_lookarounds_classify_fixed_semantic_length() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {"node_id": "node:position", "kind": "position", "position": "input_start"},
            {
                "node_id": "node:lookaround",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "negative",
                "body": literal("node:lookaround.body", "xy")
            },
            literal("node:literal", "😀x")
        ]
    }));
    let foundational = analyze(&semantic).expect("fixed program must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("structure must analyze");

    assert_eq!(
        facts.get(&node_id("node:position")).expect("facts").length,
        LengthClassification::Fixed(0)
    );
    assert_eq!(
        facts
            .get(&node_id("node:lookaround"))
            .expect("facts")
            .length,
        LengthClassification::Fixed(0)
    );
    assert_eq!(
        facts
            .get(&node_id("node:lookaround.body"))
            .expect("facts")
            .length,
        LengthClassification::Fixed(2)
    );
    assert_eq!(
        facts.get(&node_id("node:literal")).expect("facts").length,
        LengthClassification::Fixed(2)
    );
    assert_eq!(
        facts.get(&node_id("node:root")).expect("facts").length,
        LengthClassification::Fixed(2)
    );
}

#[test]
fn alternation_distinguishes_equal_and_unequal_finite_lengths() {
    let equal = program(json!({
        "node_id": "node:equal",
        "kind": "alternation",
        "branches": [literal("node:equal.a", "a"), literal("node:equal.e", "é")]
    }));
    let foundational = analyze(&equal).expect("equal alternation must analyze");
    let facts = analyze_structure(&equal, &foundational).expect("structure must analyze");
    assert_eq!(
        facts.get(&node_id("node:equal")).expect("facts").length,
        LengthClassification::Fixed(1)
    );

    let unequal = program(json!({
        "node_id": "node:unequal",
        "kind": "alternation",
        "branches": [literal("node:unequal.a", "a"), literal("node:unequal.bc", "bc")]
    }));
    let foundational = analyze(&unequal).expect("unequal alternation must analyze");
    let facts = analyze_structure(&unequal, &foundational).expect("structure must analyze");
    assert_eq!(
        facts.get(&node_id("node:unequal")).expect("facts").length,
        LengthClassification::FiniteVariable
    );
}

#[test]
fn exact_bounded_and_unbounded_repetitions_keep_extent_separate_from_length() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            {
                "node_id": "node:exact",
                "kind": "repeat",
                "body": literal("node:exact.body", "xy"),
                "min": 3,
                "max": 3,
                "mode": "greedy"
            },
            {
                "node_id": "node:bounded",
                "kind": "repeat",
                "body": literal("node:bounded.body", "a"),
                "min": 1,
                "max": 3,
                "mode": "lazy"
            },
            {
                "node_id": "node:unbounded",
                "kind": "repeat",
                "body": literal("node:unbounded.body", "z"),
                "min": 1,
                "max": null,
                "mode": "possessive"
            }
        ]
    }));
    let foundational = analyze(&semantic).expect("repetitions must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("structure must analyze");

    let exact = facts.get(&node_id("node:exact")).expect("facts");
    assert_eq!(exact.length, LengthClassification::Fixed(6));
    let exact_repeat = exact.repetition.as_ref().expect("repeat facts");
    assert_eq!(exact_repeat.extent, RepetitionExtent::Finite);
    assert_eq!(
        exact_repeat.operand_progress,
        ProgressClassification::AlwaysConsuming
    );

    let bounded = facts.get(&node_id("node:bounded")).expect("facts");
    assert_eq!(bounded.length, LengthClassification::FiniteVariable);
    assert_eq!(
        bounded.repetition.as_ref().expect("repeat facts").extent,
        RepetitionExtent::Finite
    );

    let unbounded = facts.get(&node_id("node:unbounded")).expect("facts");
    assert_eq!(unbounded.length, LengthClassification::Unbounded);
    assert_eq!(
        unbounded.repetition.as_ref().expect("repeat facts").extent,
        RepetitionExtent::Unbounded
    );
    assert!(facts
        .get(&node_id("node:unbounded.body"))
        .expect("facts")
        .repetition
        .is_none());
}

#[test]
fn unbounded_repetition_over_zero_width_operand_is_a_fact_not_a_verdict() {
    let semantic = program(json!({
        "node_id": "node:repeat",
        "kind": "repeat",
        "body": {"node_id": "node:empty", "kind": "empty"},
        "min": 0,
        "max": null,
        "mode": "greedy"
    }));
    let foundational = analyze(&semantic).expect("zero-width repetition must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("structure must analyze");
    let repeat = facts.get(&node_id("node:repeat")).expect("facts");

    assert_eq!(repeat.length, LengthClassification::Fixed(0));
    let repetition = repeat.repetition.as_ref().expect("repeat facts");
    assert_eq!(repetition.extent, RepetitionExtent::Unbounded);
    assert_eq!(
        repetition.operand_progress,
        ProgressClassification::PotentiallyZeroConsuming
    );
}

#[test]
fn unknown_and_cyclic_backreference_bounds_remain_indeterminate() {
    let cyclic = program(json!({
        "node_id": "node:capture",
        "kind": "capture",
        "capture_id": "capture:cycle",
        "name": "cycle",
        "body": {
            "node_id": "node:reference",
            "kind": "backreference",
            "capture_id": "capture:cycle"
        }
    }));
    let foundational = analyze(&cyclic).expect("cyclic reference must be conservatively analyzed");
    let facts = analyze_structure(&cyclic, &foundational).expect("structure must analyze");
    assert_eq!(
        facts.get(&node_id("node:capture")).expect("facts").length,
        LengthClassification::Indeterminate
    );
    assert_eq!(
        facts.get(&node_id("node:reference")).expect("facts").length,
        LengthClassification::Indeterminate
    );

    let empty_reference = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:empty.capture",
                "kind": "capture",
                "capture_id": "capture:empty",
                "body": {"node_id": "node:empty.body", "kind": "empty"}
            },
            {
                "node_id": "node:empty.reference",
                "kind": "backreference",
                "capture_id": "capture:empty"
            }
        ]
    }));
    let foundational = analyze(&empty_reference).expect("empty reference must analyze");
    let facts = analyze_structure(&empty_reference, &foundational).expect("structure must analyze");
    assert_eq!(
        facts
            .get(&node_id("node:empty.reference"))
            .expect("facts")
            .length,
        LengthClassification::Fixed(0)
    );
}

#[test]
fn repetition_over_unknown_backreference_has_indeterminate_progress() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:optional",
                "body": {
                    "node_id": "node:optional",
                    "kind": "repeat",
                    "body": literal("node:optional.body", "a"),
                    "min": 0,
                    "max": 1,
                    "mode": "greedy"
                }
            },
            {
                "node_id": "node:repeat",
                "kind": "repeat",
                "body": {
                    "node_id": "node:reference",
                    "kind": "backreference",
                    "capture_id": "capture:optional"
                },
                "min": 1,
                "max": null,
                "mode": "greedy"
            }
        ]
    }));
    let foundational = analyze(&semantic).expect("unknown reference repetition must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("structure must analyze");
    let repeat = facts.get(&node_id("node:repeat")).expect("facts");

    assert_eq!(repeat.length, LengthClassification::Indeterminate);
    assert_eq!(
        repeat
            .repetition
            .as_ref()
            .expect("repeat facts")
            .operand_progress,
        ProgressClassification::Indeterminate
    );
}

#[test]
fn checked_arithmetic_overflow_remains_owned_by_foundational_analysis() {
    let semantic = program(json!({
        "node_id": "node:overflow",
        "kind": "repeat",
        "body": literal("node:overflow.body", "ab"),
        "min": 18446744073709551615_u64,
        "max": 18446744073709551615_u64,
        "mode": "greedy"
    }));
    let errors = analyze(&semantic).expect_err("foundational arithmetic must reject overflow");
    assert_eq!(
        errors.errors[0].code,
        SemanticAnalysisErrorCode::ArithmeticOverflow
    );
}
