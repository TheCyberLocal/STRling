use serde_json::{json, Value};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::{
    analyze, Consumption, MaximumConsumption, Nullability, SemanticAnalysisErrorCode,
};
use strling_kernel::source::NodeId;

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

fn facts<'a>(
    analysis: &'a strling_kernel::semantic_analysis::SemanticFacts,
    node_id: &str,
) -> &'a strling_kernel::semantic_analysis::NodeFacts {
    analysis
        .get(&NodeId::try_from(node_id).expect("test node identity must be valid"))
        .expect("test node must have facts")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

#[test]
fn leaf_lengths_count_unicode_scalars_not_utf8_bytes() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            literal("node:literal", "éλ😀e\u{301}"),
            {"node_id": "node:wildcard", "kind": "wildcard", "line_terminators": "include"},
            {
                "node_id": "node:set",
                "kind": "character_set",
                "negated": false,
                "members": [{"kind": "literal", "value": "😀"}]
            }
        ]
    }));
    let analysis = analyze(&semantic).expect("canonical Unicode program must analyze");

    let literal = facts(&analysis, "node:literal");
    assert_eq!(literal.minimum_consumption, 5);
    assert_eq!(literal.maximum_consumption, MaximumConsumption::Finite(5));
    assert_eq!(literal.nullability, Nullability::NonNullable);
    assert_eq!(literal.consumption, Consumption::AlwaysConsuming);
    for node_id in ["node:wildcard", "node:set"] {
        let leaf = facts(&analysis, node_id);
        assert_eq!(leaf.minimum_consumption, 1);
        assert_eq!(leaf.maximum_consumption, MaximumConsumption::Finite(1));
    }
}

#[test]
fn sequence_and_alternation_compose_exact_bounds() {
    let semantic = program(json!({
        "node_id": "node:sequence",
        "kind": "sequence",
        "items": [
            literal("node:first", "ab"),
            {
                "node_id": "node:choice",
                "kind": "alternation",
                "branches": [
                    {"node_id": "node:empty", "kind": "empty"},
                    literal("node:long", "λ😀x")
                ]
            }
        ]
    }));
    let analysis = analyze(&semantic).expect("nested program must analyze");

    let choice = facts(&analysis, "node:choice");
    assert_eq!(choice.nullability, Nullability::Nullable);
    assert_eq!(choice.minimum_consumption, 0);
    assert_eq!(choice.maximum_consumption, MaximumConsumption::Finite(3));
    assert_eq!(choice.consumption, Consumption::Variable);

    let sequence = facts(&analysis, "node:sequence");
    assert_eq!(sequence.nullability, Nullability::NonNullable);
    assert_eq!(sequence.minimum_consumption, 2);
    assert_eq!(sequence.maximum_consumption, MaximumConsumption::Finite(5));
    assert_eq!(sequence.consumption, Consumption::AlwaysConsuming);
}

#[test]
fn repetition_covers_zero_exact_bounded_unbounded_and_nullable_operands() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:zero",
                "kind": "repeat",
                "body": literal("node:zero.body", "x"),
                "min": 0,
                "max": 0,
                "mode": "greedy"
            },
            {
                "node_id": "node:exact",
                "kind": "repeat",
                "body": literal("node:exact.body", "ab"),
                "min": 3,
                "max": 3,
                "mode": "lazy"
            },
            {
                "node_id": "node:bounded",
                "kind": "repeat",
                "body": literal("node:bounded.body", "😀"),
                "min": 2,
                "max": 5,
                "mode": "possessive"
            },
            {
                "node_id": "node:unbounded",
                "kind": "repeat",
                "body": {
                    "node_id": "node:nullable.body",
                    "kind": "alternation",
                    "branches": [
                        {"node_id": "node:nullable.empty", "kind": "empty"},
                        literal("node:nullable.literal", "z")
                    ]
                },
                "min": 0,
                "max": null,
                "mode": "greedy"
            },
            {
                "node_id": "node:empty-unbounded",
                "kind": "repeat",
                "body": {"node_id": "node:empty.body", "kind": "empty"},
                "min": 7,
                "max": null,
                "mode": "greedy"
            }
        ]
    }));
    let analysis = analyze(&semantic).expect("repetition corpus must analyze");

    assert_eq!(
        facts(&analysis, "node:zero").maximum_consumption,
        MaximumConsumption::Finite(0)
    );
    let exact = facts(&analysis, "node:exact");
    assert_eq!(
        (exact.minimum_consumption, exact.maximum_consumption),
        (6, MaximumConsumption::Finite(6))
    );
    let bounded = facts(&analysis, "node:bounded");
    assert_eq!(
        (bounded.minimum_consumption, bounded.maximum_consumption),
        (2, MaximumConsumption::Finite(5))
    );
    let unbounded = facts(&analysis, "node:unbounded");
    assert_eq!(unbounded.nullability, Nullability::Nullable);
    assert_eq!(unbounded.maximum_consumption, MaximumConsumption::Unbounded);
    assert_eq!(unbounded.consumption, Consumption::Variable);
    let empty_unbounded = facts(&analysis, "node:empty-unbounded");
    assert_eq!(
        empty_unbounded.maximum_consumption,
        MaximumConsumption::Finite(0)
    );
    assert_eq!(empty_unbounded.consumption, Consumption::AlwaysZeroWidth);
}

#[test]
fn assertions_are_outer_zero_width_while_children_keep_independent_facts() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {"node_id": "node:position", "kind": "position", "position": "word_boundary"},
            {
                "node_id": "node:lookahead",
                "kind": "lookaround",
                "direction": "ahead",
                "polarity": "positive",
                "body": literal("node:ahead.body", "😀x")
            },
            {
                "node_id": "node:lookbehind",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "negative",
                "body": literal("node:behind.body", "abc")
            }
        ]
    }));
    let analysis = analyze(&semantic).expect("assertion corpus must analyze");

    for node_id in [
        "node:position",
        "node:lookahead",
        "node:lookbehind",
        "node:root",
    ] {
        let assertion = facts(&analysis, node_id);
        assert_eq!(assertion.minimum_consumption, 0);
        assert_eq!(assertion.maximum_consumption, MaximumConsumption::Finite(0));
        assert_eq!(assertion.consumption, Consumption::AlwaysZeroWidth);
    }
    assert_eq!(facts(&analysis, "node:ahead.body").minimum_consumption, 2);
    assert_eq!(facts(&analysis, "node:behind.body").minimum_consumption, 3);
}

#[test]
fn captures_atomic_nodes_and_backreferences_use_target_neutral_body_bounds() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:capture.fixed",
                "kind": "capture",
                "capture_id": "capture:fixed",
                "body": {
                    "node_id": "node:atomic",
                    "kind": "atomic",
                    "body": literal("node:fixed.body", "é😀")
                }
            },
            {"node_id": "node:reference.fixed", "kind": "backreference", "capture_id": "capture:fixed"},
            {
                "node_id": "node:capture.optional",
                "kind": "capture",
                "capture_id": "capture:optional",
                "body": {
                    "node_id": "node:optional",
                    "kind": "repeat",
                    "body": literal("node:optional.body", "q"),
                    "min": 0,
                    "max": 1,
                    "mode": "greedy"
                }
            },
            {"node_id": "node:reference.optional", "kind": "backreference", "capture_id": "capture:optional"}
        ]
    }));
    let analysis = analyze(&semantic).expect("capture corpus must analyze");

    for node_id in ["node:capture.fixed", "node:atomic", "node:reference.fixed"] {
        let node = facts(&analysis, node_id);
        assert_eq!(node.minimum_consumption, 2);
        assert_eq!(node.maximum_consumption, MaximumConsumption::Finite(2));
        assert_eq!(node.nullability, Nullability::NonNullable);
    }
    let optional_reference = facts(&analysis, "node:reference.optional");
    assert_eq!(optional_reference.nullability, Nullability::Unknown);
    assert_eq!(optional_reference.minimum_consumption, 0);
    assert_eq!(
        optional_reference.maximum_consumption,
        MaximumConsumption::Finite(1)
    );
    assert_eq!(optional_reference.consumption, Consumption::Indeterminate);
}

#[test]
fn cyclic_capture_reference_bounds_are_explicitly_conservative() {
    let semantic = program(json!({
        "node_id": "node:capture",
        "kind": "capture",
        "capture_id": "capture:self",
        "body": {"node_id": "node:reference", "kind": "backreference", "capture_id": "capture:self"}
    }));
    let analysis =
        analyze(&semantic).expect("structurally valid cycle must analyze conservatively");
    for node_id in ["node:capture", "node:reference"] {
        let node = facts(&analysis, node_id);
        assert_eq!(node.nullability, Nullability::Unknown);
        assert_eq!(node.minimum_consumption, 0);
        assert_eq!(node.maximum_consumption, MaximumConsumption::Unbounded);
        assert_eq!(node.consumption, Consumption::Indeterminate);
    }
}

#[test]
fn arithmetic_overflow_is_a_structured_failure() {
    let semantic = program(json!({
        "node_id": "node:outer",
        "kind": "repeat",
        "body": {
            "node_id": "node:inner",
            "kind": "repeat",
            "body": literal("node:literal", "x"),
            "min": 18446744073709551615u64,
            "max": 18446744073709551615u64,
            "mode": "greedy"
        },
        "min": 2,
        "max": 2,
        "mode": "greedy"
    }));
    let errors = analyze(&semantic).expect_err("overflow must fail without wrapping");
    assert_eq!(
        errors.errors[0].code,
        SemanticAnalysisErrorCode::ArithmeticOverflow
    );
}
