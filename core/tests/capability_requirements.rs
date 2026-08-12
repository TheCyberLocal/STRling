use serde_json::{json, Value};
use strling_kernel::capability_evaluation::{
    extract_requirements, LookbehindLength, PositionRequirement, RequirementKind,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;

fn program_with_case(root: Value, case_matching: &str) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": case_matching,
        "root": root
    }))
    .expect("test program must deserialize")
}

fn program(root: Value) -> SemanticProgram {
    program_with_case(root, "sensitive")
}

fn extract(
    semantic: &SemanticProgram,
) -> strling_kernel::capability_evaluation::SemanticRequirements {
    let foundational = analyze(semantic).expect("program must have foundational facts");
    let structural =
        analyze_structure(semantic, &foundational).expect("program must have structural facts");
    extract_requirements(semantic, &foundational, &structural).expect("requirements must extract")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

#[test]
fn ordinary_source_less_programs_can_require_nothing() {
    let semantic = program(json!({
        "node_id": "node:plain.root",
        "kind": "sequence",
        "items": [
            {"node_id": "node:plain.empty", "kind": "empty"},
            literal("node:plain.literal", "plain")
        ]
    }));
    assert!(semantic.sources.is_none());
    assert!(extract(&semantic).is_empty());
}

#[test]
fn captures_references_assertions_and_backtracking_modes_are_typed() {
    let semantic = program(json!({
        "node_id": "node:mixed.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:mixed.capture",
                "kind": "capture",
                "capture_id": "capture:mixed.word",
                "name": "word",
                "body": literal("node:mixed.capture.body", "a")
            },
            {
                "node_id": "node:mixed.reference",
                "kind": "backreference",
                "capture_id": "capture:mixed.word"
            },
            {
                "node_id": "node:mixed.lookahead",
                "kind": "lookaround",
                "direction": "ahead",
                "polarity": "negative",
                "body": literal("node:mixed.lookahead.body", "b")
            },
            {
                "node_id": "node:mixed.lookbehind.fixed",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "positive",
                "body": literal("node:mixed.lookbehind.fixed.body", "xy")
            },
            {
                "node_id": "node:mixed.lookbehind.fixed_alternatives",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "negative",
                "body": {
                    "node_id": "node:mixed.lookbehind.fixed_alternatives.body",
                    "kind": "alternation",
                    "branches": [
                        literal("node:mixed.lookbehind.fixed_alternatives.short", "q"),
                        literal("node:mixed.lookbehind.fixed_alternatives.long", "rst")
                    ]
                }
            },
            {
                "node_id": "node:mixed.lookbehind.variable",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "negative",
                "body": {
                    "node_id": "node:mixed.lookbehind.variable.body",
                    "kind": "repeat",
                    "body": literal("node:mixed.lookbehind.variable.repeated", "q"),
                    "min": 1,
                    "max": 3,
                    "mode": "greedy"
                }
            },
            {
                "node_id": "node:mixed.atomic",
                "kind": "atomic",
                "body": literal("node:mixed.atomic.body", "c")
            },
            {
                "node_id": "node:mixed.possessive",
                "kind": "repeat",
                "body": literal("node:mixed.possessive.body", "d"),
                "min": 1,
                "max": null,
                "mode": "possessive"
            },
            {
                "node_id": "node:mixed.lazy",
                "kind": "repeat",
                "body": literal("node:mixed.lazy.body", "e"),
                "min": 0,
                "max": 3,
                "mode": "lazy"
            }
        ]
    }));

    let found = extract(&semantic);
    let capabilities: Vec<_> = found
        .iter()
        .map(|requirement| requirement.capability_id.as_str())
        .collect();
    assert_eq!(
        capabilities,
        [
            "groups.atomic",
            "groups.named_capture",
            "repetition.lazy",
            "assertions.lookahead",
            "assertions.lookbehind.fixed_length",
            "assertions.lookbehind.fixed_length",
            "assertions.lookbehind.variable_length",
            "repetition.possessive",
            "references.backreference",
        ]
    );
    assert!(found.iter().any(|requirement| {
        matches!(
            requirement.kind,
            RequirementKind::Lookbehind {
                length: LookbehindLength::Fixed { length: 2 },
                ..
            }
        )
    }));
    assert!(found.iter().any(|requirement| {
        matches!(
            requirement.kind,
            RequirementKind::Lookbehind {
                length: LookbehindLength::FixedAlternatives {
                    minimum: 1,
                    maximum: 3
                },
                ..
            }
        )
    }));
    assert!(found.iter().any(|requirement| {
        matches!(
            requirement.kind,
            RequirementKind::Lookbehind {
                length: LookbehindLength::FiniteVariable {
                    minimum: 1,
                    maximum: 3
                },
                ..
            }
        )
    }));
    assert!(found.iter().any(|requirement| {
        matches!(
            &requirement.kind,
            RequirementKind::NamedCapture { name, .. } if name == "word"
        )
    }));
}

#[test]
fn unicode_members_and_every_position_preserve_node_evidence() {
    let semantic = program_with_case(
        json!({
            "node_id": "node:semantics.root",
            "kind": "sequence",
            "items": [
                {
                    "node_id": "node:semantics.characters",
                    "kind": "character_set",
                    "negated": false,
                    "members": [
                        {
                            "kind": "builtin",
                            "name": "word",
                            "domain": "unicode",
                            "negated": false
                        },
                        {
                            "kind": "unicode_property",
                            "property": "General_Category",
                            "value": "Letter",
                            "negated": true
                        }
                    ]
                },
                {"node_id": "node:position.input_start", "kind": "position", "position": "input_start"},
                {"node_id": "node:position.input_end", "kind": "position", "position": "input_end"},
                {"node_id": "node:position.line_start", "kind": "position", "position": "line_start"},
                {"node_id": "node:position.line_end", "kind": "position", "position": "line_end"},
                {"node_id": "node:position.word", "kind": "position", "position": "word_boundary"},
                {"node_id": "node:position.not_word", "kind": "position", "position": "not_word_boundary"},
                {
                    "node_id": "node:position.final",
                    "kind": "position",
                    "position": "end_before_final_line_terminator"
                }
            ]
        }),
        "insensitive",
    );

    let found = extract(&semantic);
    assert_eq!(found.len(), 10);
    assert!(found.iter().any(|requirement| {
        requirement.node_id.as_str() == "node:semantics.root"
            && matches!(requirement.kind, RequirementKind::CaseInsensitive)
    }));
    let positions: Vec<_> = found
        .iter()
        .filter_map(|requirement| match requirement.kind {
            RequirementKind::Position { position } => Some(position),
            _ => None,
        })
        .collect();
    assert_eq!(
        positions,
        [
            PositionRequirement::EndBeforeFinalLineTerminator,
            PositionRequirement::InputEnd,
            PositionRequirement::InputStart,
            PositionRequirement::LineEnd,
            PositionRequirement::LineStart,
            PositionRequirement::NotWordBoundary,
            PositionRequirement::WordBoundary,
        ]
    );
}

#[test]
fn nested_extraction_is_stably_ordered_and_repeatable() {
    let semantic = program(json!({
        "node_id": "node:z.root",
        "kind": "atomic",
        "body": {
            "node_id": "node:a.lookahead",
            "kind": "lookaround",
            "direction": "ahead",
            "polarity": "positive",
            "body": {
                "node_id": "node:m.repeat",
                "kind": "repeat",
                "body": literal("node:m.repeat.body", "x"),
                "min": 0,
                "max": null,
                "mode": "possessive"
            }
        }
    }));

    let first = extract(&semantic);
    let second = extract(&semantic);
    assert_eq!(first, second);
    let ids: Vec<_> = first
        .iter()
        .map(|requirement| requirement.node_id.as_str())
        .collect();
    assert_eq!(ids, ["node:a.lookahead", "node:m.repeat", "node:z.root"]);
}
