use serde_json::{json, Value};
use strling_kernel::normalization::{normalize, NormalizationErrorCode};
use strling_kernel::semantic::{CharacterSetMember, Node, SemanticProgram};
use strling_kernel::validation::Validate;

const SEMANTIC_ALL: &str =
    include_str!("../../spec/contracts/1.0/examples/semantic-ir/semantic-all-nodes.json");
const SEMANTIC_CONSTRUCTED: &str =
    include_str!("../../spec/contracts/1.0/examples/semantic-ir/semantic-constructed.json");

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("test candidate must have a structurally valid shape")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

#[test]
fn already_normalized_contract_fixtures_are_unchanged() {
    for fixture in [SEMANTIC_ALL, SEMANTIC_CONSTRUCTED] {
        let candidate: SemanticProgram =
            serde_json::from_str(fixture).expect("fixture shape must deserialize");
        let normalized = normalize(&candidate).expect("canonical fixture must normalize");
        assert_eq!(normalized, candidate);
        normalized
            .validate()
            .expect("normalized result must validate");
    }
}

#[test]
fn sequences_flatten_unwrap_and_coalesce_without_crossing_boundaries() {
    let candidate = program(json!({
        "node_id": "node:sequence.outer",
        "kind": "sequence",
        "items": [
            literal("node:literal.a", "a"),
            {
                "node_id": "node:sequence.inner",
                "kind": "sequence",
                "items": [
                    literal("node:literal.b", "b"),
                    {
                        "node_id": "node:sequence.single",
                        "kind": "sequence",
                        "items": [literal("node:literal.c", "c")]
                    }
                ]
            },
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:kept",
                "body": literal("node:literal.d", "d")
            },
            literal("node:literal.e", "e")
        ]
    }));

    let normalized = normalize(&candidate).expect("sequence must normalize");
    let Node::Sequence { node_id, items, .. } = &normalized.root else {
        panic!("outer sequence should survive");
    };
    assert_eq!(node_id.as_str(), "node:sequence.outer");
    assert_eq!(items.len(), 3);
    assert!(matches!(
        &items[0],
        Node::Literal { node_id, text, .. }
            if node_id.as_str() == "node:literal.a" && text == "abc"
    ));
    assert!(matches!(&items[1], Node::Capture { .. }));
    assert!(matches!(
        &items[2],
        Node::Literal { node_id, text, .. }
            if node_id.as_str() == "node:literal.e" && text == "e"
    ));
    normalized.validate().expect("result must be canonical");
}

#[test]
fn alternations_flatten_and_preserve_branch_order_and_multiplicity() {
    let candidate = program(json!({
        "node_id": "node:alternation.outer",
        "kind": "alternation",
        "branches": [
            literal("node:literal.a", "a"),
            {
                "node_id": "node:alternation.inner",
                "kind": "alternation",
                "branches": [
                    literal("node:literal.b", "b"),
                    {
                        "node_id": "node:alternation.single",
                        "kind": "alternation",
                        "branches": [literal("node:literal.a2", "a")]
                    }
                ]
            }
        ]
    }));

    let normalized = normalize(&candidate).expect("alternation must normalize");
    let Node::Alternation { branches, .. } = &normalized.root else {
        panic!("outer alternation should survive");
    };
    let texts: Vec<_> = branches
        .iter()
        .map(|branch| match branch {
            Node::Literal { text, .. } => text.as_str(),
            _ => panic!("expected literal branch"),
        })
        .collect();
    assert_eq!(texts, ["a", "b", "a"]);
    normalized.validate().expect("result must be canonical");
}

#[test]
fn every_node_category_is_recursed_and_character_sets_are_canonicalized() {
    let candidate = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {"node_id": "node:empty", "kind": "empty"},
            {"node_id": "node:wildcard", "kind": "wildcard", "line_terminators": "include"},
            {
                "node_id": "node:set",
                "kind": "character_set",
                "negated": false,
                "members": [
                    {"kind": "unicode_property", "property": "General_Category", "value": "Letter", "negated": false},
                    {"kind": "literal", "value": "z"},
                    {"kind": "builtin", "name": "whitespace", "domain": "unicode", "negated": false},
                    {"kind": "literal", "value": "a"},
                    {"kind": "range", "start": "a", "end": "z"},
                    {"kind": "builtin", "name": "digit", "domain": "ascii", "negated": true},
                    {"kind": "literal", "value": "a"}
                ]
            },
            {
                "node_id": "node:repeat",
                "kind": "repeat",
                "body": {
                    "node_id": "node:repeat.wrapper",
                    "kind": "sequence",
                    "items": [literal("node:repeat.literal", "r")]
                },
                "min": 1,
                "max": null,
                "mode": "possessive"
            },
            {"node_id": "node:position", "kind": "position", "position": "word_boundary"},
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:logical",
                "name": "word",
                "body": {
                    "node_id": "node:capture.wrapper",
                    "kind": "alternation",
                    "branches": [literal("node:capture.literal", "c")]
                }
            },
            {"node_id": "node:backreference", "kind": "backreference", "capture_id": "capture:logical"},
            {
                "node_id": "node:lookaround",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "negative",
                "body": {
                    "node_id": "node:look.sequence",
                    "kind": "sequence",
                    "items": [
                        literal("node:look.literal", "l"),
                        {"node_id": "node:look.wildcard", "kind": "wildcard", "line_terminators": "exclude"}
                    ]
                }
            },
            {
                "node_id": "node:atomic",
                "kind": "atomic",
                "body": {
                    "node_id": "node:atomic.alternation",
                    "kind": "alternation",
                    "branches": [
                        literal("node:atomic.literal", "a"),
                        {"node_id": "node:atomic.empty", "kind": "empty"}
                    ]
                }
            }
        ]
    }));

    let normalized = normalize(&candidate).expect("all variants must normalize");
    normalized.validate().expect("result must be canonical");
    let Node::Sequence { items, .. } = &normalized.root else {
        panic!("root sequence must survive");
    };
    let Node::CharacterSet { members, .. } = &items[2] else {
        panic!("third item must remain a character set");
    };
    assert_eq!(members.len(), 6);
    assert!(matches!(members[0], CharacterSetMember::Literal { .. }));
    assert!(matches!(members[1], CharacterSetMember::Literal { .. }));
    assert!(matches!(members[2], CharacterSetMember::Range { .. }));
    assert!(matches!(members[3], CharacterSetMember::Builtin { .. }));
    assert!(matches!(members[4], CharacterSetMember::Builtin { .. }));
    assert!(matches!(
        members[5],
        CharacterSetMember::UnicodeProperty { .. }
    ));
    assert!(matches!(
        &items[3],
        Node::Repeat { body, .. }
            if matches!(body.as_ref(), Node::Literal { node_id, .. } if node_id.as_str() == "node:repeat.literal")
    ));
    assert!(matches!(
        &items[5],
        Node::Capture { body, .. }
            if matches!(body.as_ref(), Node::Literal { node_id, .. } if node_id.as_str() == "node:capture.literal")
    ));
}

#[test]
fn explicit_empty_operations_and_semantic_boundaries_are_preserved() {
    let candidate = program(json!({
        "node_id": "node:sequence",
        "kind": "sequence",
        "items": [
            {"node_id": "node:empty", "kind": "empty"},
            {
                "node_id": "node:repeat",
                "kind": "repeat",
                "body": literal("node:literal", "x"),
                "min": 0,
                "max": 1,
                "mode": "lazy"
            }
        ]
    }));
    let normalized = normalize(&candidate).expect("explicit empty is valid");
    assert_eq!(normalized, candidate);
}

#[test]
fn invalid_normalization_input_returns_stable_structured_categories() {
    let cases = [
        (
            program(json!({"node_id": "node:empty.sequence", "kind": "sequence", "items": []})),
            NormalizationErrorCode::InvalidSemanticStructure,
        ),
        (
            program(
                json!({"node_id": "node:empty.alternation", "kind": "alternation", "branches": []}),
            ),
            NormalizationErrorCode::InvalidSemanticStructure,
        ),
        (
            program(literal("node:empty.literal", "")),
            NormalizationErrorCode::InvalidSemanticStructure,
        ),
        (
            program(json!({
                "node_id": "node:repeat",
                "kind": "repeat",
                "body": {"node_id": "node:body", "kind": "empty"},
                "min": 3,
                "max": 2,
                "mode": "greedy"
            })),
            NormalizationErrorCode::InvalidRepetitionBounds,
        ),
        (
            program(json!({
                "node_id": "node:duplicate",
                "kind": "sequence",
                "items": [
                    {"node_id": "node:duplicate", "kind": "empty"},
                    {"node_id": "node:other", "kind": "empty"}
                ]
            })),
            NormalizationErrorCode::InvalidIdentity,
        ),
        (
            program(json!({
                "node_id": "node:backreference",
                "kind": "backreference",
                "capture_id": "capture:missing"
            })),
            NormalizationErrorCode::InvalidReference,
        ),
        (
            program(json!({
                "node_id": "node:set",
                "kind": "character_set",
                "negated": false,
                "members": []
            })),
            NormalizationErrorCode::InvalidCharacterSet,
        ),
    ];

    for (candidate, expected) in cases {
        let errors = normalize(&candidate).expect_err("candidate must fail safely");
        assert!(
            errors.errors.iter().any(|error| error.code == expected),
            "missing expected category {expected:?}: {errors:?}"
        );
    }
}
