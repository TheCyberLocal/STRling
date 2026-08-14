use serde_json::{json, Value};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_conversion::{
    convert_semantic_program, SemanticConversionDestination, SemanticConversionErrorCode,
    SemanticConversionIssueCode, SemanticConversionOutput, SemanticConversionStatus,
    SemanticEquivalenceStatus,
};
use strling_kernel::semantic_frontend;
use strling_kernel::simply::{decode_simply_builder_request, replay_simply_builder_request};

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "insensitive",
        "root": root
    }))
    .expect("semantic fixture")
}

fn comprehensive_program() -> SemanticProgram {
    program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {"node_id": "node:empty", "kind": "empty"},
            {"node_id": "node:literal", "kind": "literal", "text": "a\n\"\\"},
            {"node_id": "node:wildcard", "kind": "wildcard", "line_terminators": "include"},
            {
                "node_id": "node:set",
                "kind": "character_set",
                "negated": false,
                "members": [
                    {"kind": "literal", "value": "a"},
                    {"kind": "range", "start": "b", "end": "z"},
                    {"kind": "builtin", "name": "digit", "domain": "target_native", "negated": true},
                    {"kind": "unicode_property", "property": "General_Category", "value": "Letter", "negated": false}
                ]
            },
            {
                "node_id": "node:choice",
                "kind": "alternation",
                "branches": [
                    {"node_id": "node:choice.a", "kind": "literal", "text": "x"},
                    {"node_id": "node:choice.empty", "kind": "empty"}
                ]
            },
            {
                "node_id": "node:repeat",
                "kind": "repeat",
                "body": {"node_id": "node:repeat.body", "kind": "literal", "text": "r"},
                "min": 1,
                "max": null,
                "mode": "possessive"
            },
            {"node_id": "node:position", "kind": "position", "position": "word_boundary"},
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:word",
                "name": "word_capture",
                "body": {"node_id": "node:capture.body", "kind": "literal", "text": "c"}
            },
            {"node_id": "node:reference", "kind": "backreference", "capture_id": "capture:word"},
            {
                "node_id": "node:lookaround",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "negative",
                "body": {"node_id": "node:lookaround.body", "kind": "literal", "text": "l"}
            },
            {
                "node_id": "node:atomic",
                "kind": "atomic",
                "body": {"node_id": "node:atomic.body", "kind": "literal", "text": "q"}
            }
        ]
    }))
}

#[test]
fn every_node_and_set_member_kind_reconstructs_exactly_in_both_destinations() {
    let input = comprehensive_program();
    for destination in [
        SemanticConversionDestination::SemanticStrling,
        SemanticConversionDestination::SimplyBuilder,
    ] {
        let result = convert_semantic_program(&input, destination, None).expect("conversion");
        assert_eq!(result.status, SemanticConversionStatus::Exact);
        assert_eq!(result.equivalence.status, SemanticEquivalenceStatus::Proven);
        assert_eq!(
            result.equivalence.source_fingerprint,
            result
                .equivalence
                .reconstructed_fingerprint
                .expect("exact proof fingerprint")
        );
        assert_eq!(result.source_summary.node_count, result.node_mappings.len());
        assert_eq!(
            result.source_summary.capture_count,
            result.capture_mappings.len()
        );
        assert!(result.issues.is_empty());

        match result.output.expect("exact output") {
            SemanticConversionOutput::SemanticStrling { text, .. } => {
                assert!(text.starts_with("semantic strling 1.0;\ncase insensitive;"));
                assert!(text.contains("target digit"));
                assert!(result
                    .node_mappings
                    .iter()
                    .all(|mapping| mapping.byte_span.is_some()));
            }
            SemanticConversionOutput::SimplyBuilder { request, .. } => {
                let request_json = serde_json::to_string(&request).expect("request JSON");
                let decoded =
                    decode_simply_builder_request(&request_json).expect("decode generated Simply");
                replay_simply_builder_request(decoded).expect("replay generated Simply");
                let operations = request["steps"]
                    .as_array()
                    .expect("steps")
                    .iter()
                    .map(|step| step["operation"].as_str().expect("operation"))
                    .collect::<Vec<_>>();
                assert!(!operations.iter().any(|operation| matches!(
                    *operation,
                    "import_node" | "import_program" | "stdlib_helper"
                )));
                assert!(result
                    .node_mappings
                    .iter()
                    .all(|mapping| mapping.byte_span.is_none()));
            }
        }
    }
}

#[test]
fn unnamed_capture_is_partial_without_a_false_equivalence_claim() {
    let input = program(json!({
        "node_id": "node:capture",
        "kind": "capture",
        "capture_id": "capture:unnamed",
        "body": {"node_id": "node:body", "kind": "literal", "text": "a"}
    }));
    let result =
        convert_semantic_program(&input, SemanticConversionDestination::SemanticStrling, None)
            .expect("partial conversion");

    assert_eq!(result.status, SemanticConversionStatus::Partial);
    assert_eq!(
        result.equivalence.status,
        SemanticEquivalenceStatus::NotProven
    );
    assert!(result.equivalence.reconstructed_fingerprint.is_none());
    assert_eq!(result.issues.len(), 2);
    assert_eq!(
        result.issues[0].code,
        SemanticConversionIssueCode::CaptureNameSubstituted
    );
    assert_eq!(
        result.issues[1].code,
        SemanticConversionIssueCode::ManualCaptureNameRequired
    );
    let SemanticConversionOutput::SemanticStrling { text, .. } =
        result.output.expect("partial text")
    else {
        panic!("expected Semantic STRling output");
    };
    assert!(text.contains("capture capture_1"));
}

#[test]
fn every_unrepresentable_reference_topology_is_explicitly_unsupported() {
    let cases = [
        (
            program(json!({
                "node_id": "node:forward.root",
                "kind": "sequence",
                "items": [
                    {"node_id": "node:forward.ref", "kind": "backreference", "capture_id": "capture:later"},
                    {
                        "node_id": "node:forward.capture",
                        "kind": "capture",
                        "capture_id": "capture:later",
                        "name": "later",
                        "body": {"node_id": "node:forward.body", "kind": "literal", "text": "a"}
                    }
                ]
            })),
            SemanticConversionIssueCode::ForwardBackreferenceUnsupported,
        ),
        (
            program(json!({
                "node_id": "node:self.capture",
                "kind": "capture",
                "capture_id": "capture:self",
                "name": "self_capture",
                "body": {"node_id": "node:self.ref", "kind": "backreference", "capture_id": "capture:self"}
            })),
            SemanticConversionIssueCode::SelfBackreferenceUnsupported,
        ),
        (
            program(json!({
                "node_id": "node:outer.capture",
                "kind": "capture",
                "capture_id": "capture:outer",
                "name": "outer_capture",
                "body": {
                    "node_id": "node:inner.capture",
                    "kind": "capture",
                    "capture_id": "capture:inner",
                    "name": "inner_capture",
                    "body": {"node_id": "node:recursive.ref", "kind": "backreference", "capture_id": "capture:outer"}
                }
            })),
            SemanticConversionIssueCode::RecursiveBackreferenceUnsupported,
        ),
    ];

    for (input, code) in cases {
        let result =
            convert_semantic_program(&input, SemanticConversionDestination::SemanticStrling, None)
                .expect("unsupported result");
        assert_eq!(result.status, SemanticConversionStatus::Unsupported);
        assert!(result.output.is_none());
        assert!(result.node_mappings.is_empty());
        assert_eq!(result.issues[0].code, code);
        assert_eq!(
            result.equivalence.status,
            SemanticEquivalenceStatus::NotApplicable
        );
    }
}

#[test]
fn malformed_semantic_input_fails_before_rendering() {
    let input = program(json!({
        "node_id": "node:duplicate",
        "kind": "sequence",
        "items": [
            {"node_id": "node:duplicate", "kind": "empty"},
            {"node_id": "node:other", "kind": "empty"}
        ]
    }));
    let errors =
        convert_semantic_program(&input, SemanticConversionDestination::SemanticStrling, None)
            .expect_err("invalid input must fail");
    assert!(errors
        .errors
        .iter()
        .all(|error| error.code == SemanticConversionErrorCode::InvalidSemanticProgram));
}

#[test]
fn semantic_output_bytes_are_accepted_by_the_existing_frontend() {
    let input = program(json!({
        "node_id": "node:literal",
        "kind": "literal",
        "text": "a"
    }));
    let result =
        convert_semantic_program(&input, SemanticConversionDestination::SemanticStrling, None)
            .expect("conversion");
    let SemanticConversionOutput::SemanticStrling { text, .. } =
        result.output.expect("text output")
    else {
        panic!("expected text output");
    };
    assert_eq!(
        text,
        "semantic strling 1.0;\ncase insensitive;\n\npattern text \"a\";\n"
    );
    assert_eq!(semantic_frontend::DIALECT_VERSION, "1.0.0");
}
