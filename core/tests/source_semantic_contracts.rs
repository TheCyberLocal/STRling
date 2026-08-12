use std::convert::TryFrom;

use serde_json::Value;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::source::{SourceDocument, SourceId, SourceOrigin, SourceSpan};
use strling_kernel::validation::{from_json, to_json, ContractError, Validate, ValidationCode};

const SOURCE_INLINE: &str =
    include_str!("../../spec/contracts/1.0/examples/source/source-inline-unicode.json");
const SOURCE_REFERENCE: &str =
    include_str!("../../spec/contracts/1.0/examples/source/source-reference.json");
const SEMANTIC_ALL: &str =
    include_str!("../../spec/contracts/1.0/examples/semantic-ir/semantic-all-nodes.json");
const SEMANTIC_CONSTRUCTED: &str =
    include_str!("../../spec/contracts/1.0/examples/semantic-ir/semantic-constructed.json");

const INVALID_SEMANTIC: &[(&str, &str)] = &[
    (
        "nested sequence",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/nested-sequence.json"),
    ),
    (
        "duplicate node",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/duplicate-node-id.json"),
    ),
    (
        "target syntax",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/target-syntax-leak.json"),
    ),
    (
        "adjacent literals",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/uncoalesced-literals.json"),
    ),
    (
        "repeat bounds",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/reversed-repeat.json"),
    ),
    (
        "missing capture",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/missing-capture.json"),
    ),
    (
        "undeclared source",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/undeclared-source.json"),
    ),
    (
        "duplicate capture",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/duplicate-capture-id.json"),
    ),
    (
        "UTF-8 span",
        include_str!("../../spec/contracts/1.0/invalid/semantic-ir/invalid-utf8-span.json"),
    ),
];

#[test]
fn canonical_source_fixtures_deserialize_and_validate() {
    let inline: SourceDocument = from_json(SOURCE_INLINE).expect("inline source must validate");
    let reference: SourceDocument =
        from_json(SOURCE_REFERENCE).expect("referenced source must validate");
    assert_eq!(inline.source_id.as_str(), "src:example.unicode");
    assert_eq!(reference.source_id.as_str(), "src:example.referenced");
}

#[test]
fn every_ratified_semantic_variant_fixture_validates() {
    let program: SemanticProgram =
        from_json(SEMANTIC_ALL).expect("all-node Semantic IR must validate");
    assert_eq!(program.root.node_id().as_str(), "node:all.root");
    assert!(program.sources.is_some());
}

#[test]
fn source_less_constructed_semantics_validate() {
    let program: SemanticProgram =
        from_json(SEMANTIC_CONSTRUCTED).expect("constructed semantics must validate");
    assert!(program.sources.is_none());
}

#[test]
fn all_controlled_invalid_semantics_are_rejected() {
    for (description, fixture) in INVALID_SEMANTIC {
        assert!(
            from_json::<SemanticProgram>(fixture).is_err(),
            "invalid fixture unexpectedly accepted: {description}"
        );
    }
}

#[test]
fn mixed_source_content_is_rejected_as_unknown_data() {
    let fixture = include_str!("../../spec/contracts/1.0/invalid/source/source-mixed-content.json");
    assert!(matches!(
        from_json::<SourceDocument>(fixture),
        Err(ContractError::Deserialization(_))
    ));
}

#[test]
fn optional_fields_reject_explicit_null() {
    let invalid = SOURCE_INLINE.replace(
        "\"display_name\": \"Unicode coordinate example\"",
        "\"display_name\": null",
    );
    assert!(matches!(
        from_json::<SourceDocument>(&invalid),
        Err(ContractError::Deserialization(_))
    ));
}

#[test]
fn required_nullable_repetition_maximum_cannot_be_omitted() {
    let invalid = r#"{
        "contract_version":"1.0.0",
        "specification_version":"1.0-draft.1",
        "normalization":"canonical-v1",
        "case_matching":"sensitive",
        "root":{
            "node_id":"node:repeat",
            "kind":"repeat",
            "body":{"node_id":"node:body","kind":"empty"},
            "min":0,
            "mode":"greedy"
        }
    }"#;
    assert!(matches!(
        from_json::<SemanticProgram>(invalid),
        Err(ContractError::Deserialization(_))
    ));
}

#[test]
fn utf8_spans_use_half_open_byte_boundaries() {
    let source_id = SourceId::try_from("src:utf8").expect("valid source identity");
    let text = "\u{03b1}\u{1f600}beta";
    let alpha = SourceSpan::new(source_id.clone(), 0, 2).expect("valid alpha span");
    alpha
        .validate_against_text(text)
        .expect("alpha ends on UTF-8 boundary");
    let emoji = SourceSpan::new(source_id.clone(), 2, 6).expect("valid emoji span");
    emoji
        .validate_against_text(text)
        .expect("emoji uses four UTF-8 bytes");
    let invalid = SourceSpan::new(source_id, 3, 5).expect("ordered span");
    let errors = invalid
        .validate_against_text(text)
        .expect_err("interior emoji bytes must fail");
    assert_eq!(errors.errors[0].code, ValidationCode::Utf8Boundary);
}

#[test]
fn reversed_span_returns_structured_validation_error() {
    let span: SourceSpan = serde_json::from_str(
        r#"{"source_id":"src:bad","coordinate_system":"utf8-bytes","start":3,"end":2}"#,
    )
    .expect("shape deserializes before relational validation");
    let errors = span.validate().expect_err("reversed span must fail");
    assert_eq!(errors.errors[0].code, ValidationCode::InvalidSpan);
}

#[test]
fn overlapping_and_out_of_range_spans_are_rejected() {
    let source_id = SourceId::try_from("src:span-validation").expect("source identity");
    let overlapping = SourceOrigin {
        source_spans: Some(vec![
            SourceSpan::new(source_id.clone(), 0, 4).expect("first span"),
            SourceSpan::new(source_id.clone(), 2, 6).expect("second span"),
        ]),
        derived_from_node_ids: None,
    };
    let errors = overlapping.validate().expect_err("overlap must fail");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::InvalidSpan));

    let out_of_range = SourceSpan::new(source_id, 0, 7).expect("ordered span");
    let errors = out_of_range
        .validate_against_text("six")
        .expect_err("out-of-range span must fail");
    assert_eq!(errors.errors[0].code, ValidationCode::Utf8Boundary);
}

#[test]
fn source_and_semantic_round_trips_preserve_structure() {
    for source in [SOURCE_INLINE, SOURCE_REFERENCE] {
        let model: SourceDocument = from_json(source).expect("source validates");
        let encoded = to_json(&model).expect("source serializes");
        assert_eq!(
            serde_json::from_str::<Value>(source).expect("fixture JSON"),
            serde_json::from_str::<Value>(&encoded).expect("encoded JSON")
        );
        assert_eq!(encoded, to_json(&model).expect("stable serialization"));
    }
    for source in [SEMANTIC_ALL, SEMANTIC_CONSTRUCTED] {
        let model: SemanticProgram = from_json(source).expect("semantic IR validates");
        let encoded = to_json(&model).expect("semantic IR serializes");
        assert_eq!(
            serde_json::from_str::<Value>(source).expect("fixture JSON"),
            serde_json::from_str::<Value>(&encoded).expect("encoded JSON")
        );
        assert_eq!(encoded, to_json(&model).expect("stable serialization"));
    }
}
