use serde_json::{json, Value};
use strling_kernel::normalization::normalize;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::{analyze, SemanticAnalysisErrorCode};
use strling_kernel::source::{CaptureId, NodeId};

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

fn capture_id(value: &str) -> CaptureId {
    CaptureId::try_from(value).expect("test capture identity must be valid")
}

#[test]
fn nested_capture_and_reference_subtrees_are_complete_and_ordered() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:outer",
                "kind": "capture",
                "capture_id": "capture:z-outer",
                "name": "outer",
                "body": {
                    "node_id": "node:inner",
                    "kind": "capture",
                    "capture_id": "capture:a-inner",
                    "name": "inner",
                    "body": {"node_id": "node:literal", "kind": "literal", "text": "x"}
                }
            },
            {
                "node_id": "node:wrapper",
                "kind": "atomic",
                "body": {
                    "node_id": "node:lookaround",
                    "kind": "lookaround",
                    "direction": "ahead",
                    "polarity": "positive",
                    "body": {"node_id": "node:z-reference", "kind": "backreference", "capture_id": "capture:z-outer"}
                }
            },
            {"node_id": "node:a-reference", "kind": "backreference", "capture_id": "capture:a-inner"}
        ]
    }));
    let analysis = analyze(&semantic).expect("capture relationship corpus must analyze");

    let root = analysis.get(&node_id("node:root")).expect("root facts");
    let captures: Vec<_> = root
        .captures_defined
        .iter()
        .map(CaptureId::as_str)
        .collect();
    assert_eq!(captures, ["capture:a-inner", "capture:z-outer"]);
    let references: Vec<_> = root
        .backreferences_used
        .iter()
        .map(NodeId::as_str)
        .collect();
    assert_eq!(references, ["node:a-reference", "node:z-reference"]);
    let referenced: Vec<_> = root
        .captures_referenced
        .iter()
        .map(CaptureId::as_str)
        .collect();
    assert_eq!(referenced, ["capture:a-inner", "capture:z-outer"]);

    let outer = analysis.get(&node_id("node:outer")).expect("outer facts");
    assert_eq!(outer.captures_defined.len(), 2);
    let inner = analysis.get(&node_id("node:inner")).expect("inner facts");
    assert_eq!(
        inner.captures_defined,
        [capture_id("capture:a-inner")].into()
    );

    let definitions: Vec<_> = analysis
        .capture_definitions()
        .map(|(id, definition)| (id.as_str(), definition.definition_node_id.as_str()))
        .collect();
    assert_eq!(
        definitions,
        [
            ("capture:a-inner", "node:inner"),
            ("capture:z-outer", "node:outer")
        ]
    );
}

#[test]
fn every_backreference_resolves_to_the_exact_logical_capture() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {"node_id": "node:reference.before", "kind": "backreference", "capture_id": "capture:logical"},
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:logical",
                "name": "logical_name",
                "body": {"node_id": "node:body", "kind": "literal", "text": "abc"}
            },
            {"node_id": "node:reference.after", "kind": "backreference", "capture_id": "capture:logical"}
        ]
    }));
    let analysis = analyze(&semantic).expect("forward and later references must resolve");

    let definition = analysis
        .capture_definition(&capture_id("capture:logical"))
        .expect("logical capture must be indexed");
    assert_eq!(definition.definition_node_id.as_str(), "node:capture");
    assert_eq!(definition.body_node_id.as_str(), "node:body");
    assert_eq!(definition.name.as_deref(), Some("logical_name"));

    for reference in ["node:reference.before", "node:reference.after"] {
        let resolution = analysis
            .backreference(&node_id(reference))
            .expect("backreference must resolve");
        assert_eq!(resolution.capture_id.as_str(), "capture:logical");
        assert_eq!(resolution.definition_node_id.as_str(), "node:capture");
        assert_eq!(
            analysis
                .get(&node_id(reference))
                .and_then(|facts| facts.backreference.as_ref()),
            Some(resolution)
        );
    }
}

#[test]
fn normalization_of_unrelated_wrappers_preserves_reference_identity() {
    let candidate = program(json!({
        "node_id": "node:wrapper",
        "kind": "sequence",
        "items": [{
            "node_id": "node:root",
            "kind": "sequence",
            "items": [
                {
                    "node_id": "node:capture",
                    "kind": "capture",
                    "capture_id": "capture:stable",
                    "body": {"node_id": "node:body", "kind": "literal", "text": "x"}
                },
                {"node_id": "node:reference", "kind": "backreference", "capture_id": "capture:stable"}
            ]
        }]
    }));
    let normalized = normalize(&candidate).expect("unrelated wrapper must normalize");
    let analysis = analyze(&normalized).expect("normalized relationship must analyze");
    let resolution = analysis
        .backreference(&node_id("node:reference"))
        .expect("reference identity must survive");
    assert_eq!(resolution.capture_id.as_str(), "capture:stable");
    assert_eq!(resolution.definition_node_id.as_str(), "node:capture");
}

#[test]
fn malformed_capture_relationships_fail_with_stable_categories() {
    let unresolved = program(json!({
        "node_id": "node:reference",
        "kind": "backreference",
        "capture_id": "capture:missing"
    }));
    let errors = analyze(&unresolved).expect_err("unresolved reference must fail");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == SemanticAnalysisErrorCode::InvalidReference));

    let duplicate = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:first",
                "kind": "capture",
                "capture_id": "capture:duplicate",
                "body": {"node_id": "node:first.body", "kind": "empty"}
            },
            {
                "node_id": "node:second",
                "kind": "capture",
                "capture_id": "capture:duplicate",
                "body": {"node_id": "node:second.body", "kind": "empty"}
            }
        ]
    }));
    let errors = analyze(&duplicate).expect_err("duplicate capture identity must fail");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == SemanticAnalysisErrorCode::InvalidIdentity));
}
