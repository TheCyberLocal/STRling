use serde_json::{json, Value};
use strling_kernel::normalization::{normalize, NormalizationErrorCode};
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::validation::Validate;

#[derive(Clone, Debug, Eq, PartialEq)]
enum LegacyShape {
    Empty,
    Sequence(Vec<Self>),
    Alternation(Vec<Self>),
    Literal(String),
    Wildcard,
    CharacterSet(Vec<String>),
    Repeat(Box<Self>),
    Position,
    Capture(Box<Self>),
    Backreference,
    Lookaround(Box<Self>),
    Atomic(Box<Self>),
}

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("compatibility candidate must deserialize")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn empty(node_id: &str) -> Value {
    json!({"node_id": node_id, "kind": "empty"})
}

fn legacy_shape(node: &Node) -> LegacyShape {
    match node {
        Node::Empty { .. } => LegacyShape::Empty,
        Node::Sequence { items, .. } => {
            LegacyShape::Sequence(items.iter().map(legacy_shape).collect())
        }
        Node::Alternation { branches, .. } => {
            LegacyShape::Alternation(branches.iter().map(legacy_shape).collect())
        }
        Node::Literal { text, .. } => LegacyShape::Literal(text.clone()),
        Node::Wildcard { .. } => LegacyShape::Wildcard,
        Node::CharacterSet { members, .. } => LegacyShape::CharacterSet(
            members
                .iter()
                .map(|member| serde_json::to_string(member).expect("member serializes"))
                .collect(),
        ),
        Node::Repeat { body, .. } => LegacyShape::Repeat(Box::new(legacy_shape(body))),
        Node::Position { .. } => LegacyShape::Position,
        Node::Capture { body, .. } => LegacyShape::Capture(Box::new(legacy_shape(body))),
        Node::Backreference { .. } => LegacyShape::Backreference,
        Node::Lookaround { body, .. } => LegacyShape::Lookaround(Box::new(legacy_shape(body))),
        Node::Atomic { body, .. } => LegacyShape::Atomic(Box::new(legacy_shape(body))),
    }
}

fn legacy_normalize(node: LegacyShape) -> LegacyShape {
    match node {
        LegacyShape::Sequence(items) => {
            let mut flattened = Vec::new();
            for item in items {
                match legacy_normalize(item) {
                    LegacyShape::Sequence(items) => flattened.extend(items),
                    item => flattened.push(item),
                }
            }
            let mut coalesced = Vec::new();
            let mut buffer = String::new();
            for item in flattened {
                match item {
                    LegacyShape::Literal(text) => buffer.push_str(&text),
                    item => {
                        if !buffer.is_empty() {
                            coalesced.push(LegacyShape::Literal(std::mem::take(&mut buffer)));
                        }
                        coalesced.push(item);
                    }
                }
            }
            if !buffer.is_empty() {
                coalesced.push(LegacyShape::Literal(buffer));
            }
            if coalesced.len() == 1 {
                coalesced.remove(0)
            } else {
                LegacyShape::Sequence(coalesced)
            }
        }
        LegacyShape::Alternation(branches) => {
            let mut flattened = Vec::new();
            for branch in branches {
                match legacy_normalize(branch) {
                    LegacyShape::Alternation(branches) => flattened.extend(branches),
                    branch => flattened.push(branch),
                }
            }
            if flattened.len() == 1 {
                flattened.remove(0)
            } else {
                LegacyShape::Alternation(flattened)
            }
        }
        LegacyShape::Repeat(body) => LegacyShape::Repeat(Box::new(legacy_normalize(*body))),
        LegacyShape::Capture(body) => LegacyShape::Capture(Box::new(legacy_normalize(*body))),
        LegacyShape::Lookaround(body) => LegacyShape::Lookaround(Box::new(legacy_normalize(*body))),
        LegacyShape::Atomic(body) => LegacyShape::Atomic(Box::new(legacy_normalize(*body))),
        leaf => leaf,
    }
}

#[test]
fn selected_legacy_structural_corpus_has_zero_unexplained_differences() {
    let cases = [
        program(json!({
            "node_id": "node:case1.outer",
            "kind": "sequence",
            "items": [{
                "node_id": "node:case1.inner",
                "kind": "sequence",
                "items": [literal("node:case1.a", "a"), literal("node:case1.b", "b")]
            }]
        })),
        program(json!({
            "node_id": "node:case2.sequence",
            "kind": "sequence",
            "items": [
                literal("node:case2.a", "a"),
                literal("node:case2.b", "b"),
                {"node_id": "node:case2.wildcard", "kind": "wildcard", "line_terminators": "exclude"},
                literal("node:case2.c", "c")
            ]
        })),
        program(json!({
            "node_id": "node:case3.outer",
            "kind": "alternation",
            "branches": [
                literal("node:case3.a", "a"),
                {
                    "node_id": "node:case3.inner",
                    "kind": "alternation",
                    "branches": [literal("node:case3.b", "b"), literal("node:case3.c", "c")]
                }
            ]
        })),
        program(json!({
            "node_id": "node:case4.repeat",
            "kind": "repeat",
            "body": {
                "node_id": "node:case4.wrapper",
                "kind": "sequence",
                "items": [literal("node:case4.literal", "r")]
            },
            "min": 1,
            "max": 3,
            "mode": "lazy"
        })),
        program(json!({
            "node_id": "node:case5.capture",
            "kind": "capture",
            "capture_id": "capture:case5",
            "body": {
                "node_id": "node:case5.wrapper",
                "kind": "alternation",
                "branches": [literal("node:case5.literal", "c")]
            }
        })),
        program(json!({
            "node_id": "node:case6.look",
            "kind": "lookaround",
            "direction": "ahead",
            "polarity": "positive",
            "body": {
                "node_id": "node:case6.sequence",
                "kind": "sequence",
                "items": [literal("node:case6.a", "a"), literal("node:case6.b", "b")]
            }
        })),
        program(json!({
            "node_id": "node:case7.atomic",
            "kind": "atomic",
            "body": {
                "node_id": "node:case7.outer",
                "kind": "alternation",
                "branches": [
                    literal("node:case7.a", "a"),
                    {
                        "node_id": "node:case7.inner",
                        "kind": "alternation",
                        "branches": [literal("node:case7.b", "b")]
                    }
                ]
            }
        })),
        program(json!({
            "node_id": "node:case8.sequence",
            "kind": "sequence",
            "items": [empty("node:case8.empty"), literal("node:case8.literal", "x")]
        })),
        program(json!({
            "node_id": "node:case9.sequence",
            "kind": "sequence",
            "items": [
                {
                    "node_id": "node:case9.capture",
                    "kind": "capture",
                    "capture_id": "capture:case9",
                    "body": literal("node:case9.literal", "x")
                },
                {
                    "node_id": "node:case9.reference",
                    "kind": "backreference",
                    "capture_id": "capture:case9"
                }
            ]
        })),
    ];

    for (index, candidate) in cases.into_iter().enumerate() {
        let legacy = legacy_normalize(legacy_shape(&candidate.root));
        let canonical = normalize(&candidate)
            .unwrap_or_else(|errors| panic!("case {index} failed: {errors:?}"));
        assert_eq!(legacy_shape(&canonical.root), legacy, "case {index}");
        canonical
            .validate()
            .expect("canonical result must validate");
    }
}

#[test]
fn canonical_contract_corrections_are_explicit_and_bounded() {
    let empty_sequence = program(json!({
        "node_id": "node:empty.sequence",
        "kind": "sequence",
        "items": []
    }));
    let empty_alternation = program(json!({
        "node_id": "node:empty.alternation",
        "kind": "alternation",
        "branches": []
    }));
    let empty_literal = program(literal("node:empty.literal", ""));
    for candidate in [&empty_sequence, &empty_alternation, &empty_literal] {
        let legacy = legacy_normalize(legacy_shape(&candidate.root));
        assert!(matches!(
            legacy,
            LegacyShape::Sequence(_) | LegacyShape::Alternation(_) | LegacyShape::Literal(_)
        ));
        let errors = normalize(candidate).expect_err("canonical malformed input must fail");
        assert!(errors
            .errors
            .iter()
            .any(|error| error.code == NormalizationErrorCode::InvalidSemanticStructure));
    }

    let unordered_set = program(json!({
        "node_id": "node:set",
        "kind": "character_set",
        "negated": false,
        "members": [
            {"kind": "range", "start": "a", "end": "z"},
            {"kind": "literal", "value": "z"},
            {"kind": "literal", "value": "a"},
            {"kind": "literal", "value": "a"}
        ]
    }));
    let legacy = legacy_normalize(legacy_shape(&unordered_set.root));
    let canonical = normalize(&unordered_set).expect("set must canonicalize");
    assert_ne!(legacy_shape(&canonical.root), legacy);
    let Node::CharacterSet { members, .. } = &canonical.root else {
        panic!("set node must survive");
    };
    assert_eq!(members.len(), 3);
    canonical.validate().expect("canonical set must validate");
}
