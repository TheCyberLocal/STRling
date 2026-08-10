use serde_json::{json, Value};
use strling_kernel::semantic::{CharacterSetMember, SemanticProgram};
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::NodeId;
use strling_kernel::structural_analysis::{
    analyze_structure, LeadingTerm, LeadingUnknownReason, StructuralAnalysisErrorCode,
};

const SEMANTIC_ALL: &str =
    include_str!("../../spec/contracts/1.0/examples/semantic-ir/semantic-all-nodes.json");

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

fn node_id(value: &str) -> NodeId {
    NodeId::try_from(value).expect("test node identity must be valid")
}

fn literal(id: &str, text: &str) -> Value {
    json!({"node_id": id, "kind": "literal", "text": text})
}

fn scalar_terms(
    facts: &strling_kernel::structural_analysis::StructuralFacts,
    id: &str,
) -> Vec<char> {
    facts
        .get(&node_id(id))
        .expect("node needs structural facts")
        .leading_consumption
        .iter()
        .filter_map(|term| match term {
            LeadingTerm::Scalar(value) => Some(value.get()),
            _ => None,
        })
        .collect()
}

#[test]
fn every_reachable_variant_has_deterministic_leading_facts() {
    let semantic: SemanticProgram =
        serde_json::from_str(SEMANTIC_ALL).expect("canonical fixture must deserialize");
    let foundational = analyze(&semantic).expect("canonical fixture must have foundational facts");

    let first = analyze_structure(&semantic, &foundational).expect("fixture must analyze");
    let second = analyze_structure(&semantic, &foundational).expect("repeat must analyze");

    assert_eq!(first, second);
    assert_eq!(first.len(), semantic.node_ids().len());
    assert!(first
        .iter()
        .all(|(_, facts)| !facts.leading_consumption.is_empty()));
    let ids: Vec<_> = first.iter().map(|(id, _)| id.as_str()).collect();
    let mut sorted = ids.clone();
    sorted.sort_unstable();
    assert_eq!(ids, sorted);
}

#[test]
fn equal_and_distinct_literals_form_canonical_scalar_unions() {
    let equal = program(json!({
        "node_id": "node:equal",
        "kind": "alternation",
        "branches": [literal("node:equal.left", "a"), literal("node:equal.right", "a")]
    }));
    let foundational = analyze(&equal).expect("equal literals must analyze");
    let facts = analyze_structure(&equal, &foundational).expect("leading facts must derive");
    assert_eq!(scalar_terms(&facts, "node:equal"), ['a']);

    let distinct = program(json!({
        "node_id": "node:distinct",
        "kind": "alternation",
        "branches": [literal("node:distinct.z", "z"), literal("node:distinct.a", "a")]
    }));
    let foundational = analyze(&distinct).expect("distinct literals must analyze");
    let facts = analyze_structure(&distinct, &foundational).expect("leading facts must derive");
    assert_eq!(scalar_terms(&facts, "node:distinct"), ['a', 'z']);
}

#[test]
fn leading_literals_use_unicode_scalars_not_encoded_bytes() {
    let semantic = program(json!({
        "node_id": "node:unicode",
        "kind": "alternation",
        "branches": [
            literal("node:unicode.emoji", "😀tail"),
            literal("node:unicode.cjk", "中tail"),
            literal("node:unicode.accent", "é")
        ]
    }));
    let foundational = analyze(&semantic).expect("Unicode literals must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("leading facts must derive");
    assert_eq!(scalar_terms(&facts, "node:unicode"), ['é', '中', '😀']);
}

#[test]
fn nullable_prefixes_and_assertions_expose_only_outer_consumers() {
    let semantic = program(json!({
        "node_id": "node:sequence",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:optional",
                "kind": "repeat",
                "body": literal("node:optional.body", "x"),
                "min": 0,
                "max": 1,
                "mode": "greedy"
            },
            {
                "node_id": "node:lookahead",
                "kind": "lookaround",
                "direction": "ahead",
                "polarity": "positive",
                "body": literal("node:lookahead.body", "y")
            },
            literal("node:following", "z")
        ]
    }));
    let foundational = analyze(&semantic).expect("nullable sequence must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("leading facts must derive");

    assert_eq!(scalar_terms(&facts, "node:sequence"), ['x', 'z']);
    assert_eq!(scalar_terms(&facts, "node:lookahead.body"), ['y']);
    assert!(facts
        .get(&node_id("node:lookahead"))
        .expect("lookahead needs facts")
        .leading_consumption
        .contains(&LeadingTerm::Empty));
    let optional = &facts
        .get(&node_id("node:optional"))
        .expect("repeat needs facts")
        .leading_consumption;
    assert!(optional.contains(&LeadingTerm::Empty));
    assert_eq!(scalar_terms(&facts, "node:optional"), ['x']);
}

#[test]
fn nested_alternation_unions_are_flattened_only_in_fact_space() {
    let semantic = program(json!({
        "node_id": "node:outer",
        "kind": "alternation",
        "branches": [
            literal("node:a", "a"),
            {
                "node_id": "node:atomic",
                "kind": "atomic",
                "body": {
                    "node_id": "node:inner",
                    "kind": "alternation",
                    "branches": [literal("node:c", "c"), literal("node:b", "b")]
                }
            }
        ]
    }));
    let unchanged = semantic.clone();
    let foundational = analyze(&semantic).expect("nested alternation must analyze");
    let foundational_unchanged = foundational.clone();
    let facts = analyze_structure(&semantic, &foundational).expect("leading facts must derive");

    assert_eq!(scalar_terms(&facts, "node:outer"), ['a', 'b', 'c']);
    assert_eq!(semantic, unchanged);
    assert_eq!(foundational, foundational_unchanged);
}

#[test]
fn wildcard_and_character_predicates_remain_symbolic() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            {
                "node_id": "node:wildcard",
                "kind": "wildcard",
                "line_terminators": "exclude"
            },
            {
                "node_id": "node:set",
                "kind": "character_set",
                "negated": false,
                "members": [
                    {"kind": "literal", "value": "a"},
                    {"kind": "range", "start": "m", "end": "z"}
                ]
            }
        ]
    }));
    let foundational = analyze(&semantic).expect("symbolic consumers must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("leading facts must derive");
    let root: Vec<_> = facts
        .get(&node_id("node:root"))
        .expect("root needs facts")
        .leading_consumption
        .iter()
        .collect();

    assert!(root.iter().any(|term| matches!(
        term,
        LeadingTerm::Wildcard { line_terminators }
            if *line_terminators == strling_kernel::semantic::LineTerminators::Exclude
    )));
    assert!(root.iter().any(|term| matches!(
        term,
        LeadingTerm::CharacterSet { negated: false, members }
            if matches!(members.as_slice(), [CharacterSetMember::Literal { .. }, CharacterSetMember::Range { .. }])
    )));
}

#[test]
fn zero_maximum_repeat_has_no_body_consumption_in_its_outer_leading_set() {
    let semantic = program(json!({
        "node_id": "node:never",
        "kind": "repeat",
        "body": literal("node:never.body", "q"),
        "min": 0,
        "max": 0,
        "mode": "possessive"
    }));
    let foundational = analyze(&semantic).expect("zero repeat must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("leading facts must derive");
    let repeat = &facts
        .get(&node_id("node:never"))
        .expect("repeat needs facts")
        .leading_consumption;

    assert_eq!(repeat.len(), 1);
    assert!(repeat.contains(&LeadingTerm::Empty));
    assert_eq!(scalar_terms(&facts, "node:never.body"), ['q']);
}

#[test]
fn backreferences_remain_conservative_and_unknown_prefixes_continue() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:reference",
                "kind": "backreference",
                "capture_id": "capture:stable"
            },
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:stable",
                "name": "stable",
                "body": {
                    "node_id": "node:capture.body",
                    "kind": "repeat",
                    "body": literal("node:capture.literal", "x"),
                    "min": 0,
                    "max": 1,
                    "mode": "greedy"
                }
            },
            literal("node:following", "a")
        ]
    }));
    let foundational = analyze(&semantic).expect("backreference program must analyze");
    let facts = analyze_structure(&semantic, &foundational).expect("leading facts must derive");
    let reference_unknown = LeadingTerm::Unknown(LeadingUnknownReason::Backreference {
        node_id: node_id("node:reference"),
    });
    let prefix_unknown = LeadingTerm::Unknown(LeadingUnknownReason::NullablePrefix {
        node_id: node_id("node:reference"),
    });

    let reference = &facts
        .get(&node_id("node:reference"))
        .expect("reference needs facts")
        .leading_consumption;
    assert!(reference.contains(&reference_unknown));
    let root = &facts
        .get(&node_id("node:root"))
        .expect("root needs facts")
        .leading_consumption;
    assert!(root.contains(&reference_unknown));
    assert!(root.contains(&prefix_unknown));
    assert_eq!(scalar_terms(&facts, "node:root"), ['a', 'x']);
}

#[test]
fn mismatched_foundational_state_is_a_structured_error() {
    let semantic = program(literal("node:root", "a"));
    let other = program(literal("node:root", "b"));
    let foundational = analyze(&other).expect("other program must analyze");

    let errors = analyze_structure(&semantic, &foundational)
        .expect_err("facts for a different exact program must be rejected");
    assert_eq!(
        errors.errors[0].code,
        StructuralAnalysisErrorCode::MismatchedFoundationalFacts
    );
}
