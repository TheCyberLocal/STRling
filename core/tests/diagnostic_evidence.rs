use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::{
    generate_diagnostics, DiagnosticEvidence, DiagnosticGeneration, DiagnosticGenerationErrorCode,
};
use strling_kernel::safety_analysis::{analyze_safety, SafetyAnalysis, SafetyEvidence};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
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

fn source_program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "sources": [{
            "contract_version": "1.0.0",
            "source_id": "src:evidence",
            "specification_version": "1.0-draft.1",
            "frontend": {
                "id": "semantic_strling",
                "dialect_version": "1.0-draft.1"
            },
            "content": {
                "kind": "inline",
                "encoding": "utf-8",
                "text": "abc"
            },
            "provenance": {"kind": "authored"}
        }],
        "root": root
    }))
    .expect("source-backed test program must deserialize")
}

fn origin(start: u64, end: u64) -> Value {
    json!({
        "source_spans": [{
            "source_id": "src:evidence",
            "coordinate_system": "utf8-bytes",
            "start": start,
            "end": end
        }]
    })
}

fn generate(semantic: &SemanticProgram) -> DiagnosticGeneration {
    let foundational = analyze(semantic).expect("foundational analysis must succeed");
    let structural =
        analyze_structure(semantic, &foundational).expect("structural analysis must succeed");
    let safety =
        analyze_safety(semantic, &foundational, &structural).expect("safety analysis must succeed");
    generate_diagnostics(semantic, &foundational, &structural, &safety)
        .expect("diagnostic generation must succeed")
}

fn nested(with_source: bool) -> SemanticProgram {
    let root = json!({
        "node_id": "node:nested.outer",
        "kind": "repeat",
        "origin": with_source.then(|| origin(0, 3)),
        "body": {
            "node_id": "node:nested.inner",
            "kind": "repeat",
            "origin": with_source.then(|| origin(0, 2)),
            "body": {
                "node_id": "node:nested.atom",
                "kind": "literal",
                "origin": with_source.then(|| origin(0, 1)),
                "text": "a"
            },
            "min": 1,
            "max": null,
            "mode": "greedy"
        },
        "min": 0,
        "max": null,
        "mode": "greedy"
    });
    if with_source {
        source_program(root)
    } else {
        let mut root = root;
        remove_null_origins(&mut root);
        program(root)
    }
}

fn remove_null_origins(value: &mut Value) {
    match value {
        Value::Object(object) => {
            if object.get("origin") == Some(&Value::Null) {
                object.remove("origin");
            }
            for child in object.values_mut() {
                remove_null_origins(child);
            }
        }
        Value::Array(items) => {
            for item in items {
                remove_null_origins(item);
            }
        }
        _ => {}
    }
}

fn repeated_alternation() -> SemanticProgram {
    program(json!({
        "node_id": "node:alternation.repeat",
        "kind": "repeat",
        "body": {
            "node_id": "node:alternation",
            "kind": "alternation",
            "branches": [
                {"node_id": "node:alternation.left", "kind": "literal", "text": "a"},
                {"node_id": "node:alternation.right", "kind": "literal", "text": "ab"}
            ]
        },
        "min": 0,
        "max": null,
        "mode": "greedy"
    }))
}

#[test]
fn generation_records_retain_complete_stable_source_and_path_evidence() {
    let generated = generate(&nested(true));
    let record = generated
        .records()
        .next()
        .expect("nested diagnostic record");

    let node_ids: Vec<_> = record
        .provenance
        .source_origins
        .iter()
        .map(|source| source.node_id.as_str())
        .collect();
    assert_eq!(
        node_ids,
        vec!["node:nested.atom", "node:nested.inner", "node:nested.outer"]
    );
    let DiagnosticEvidence::Safety(SafetyEvidence::NestedRepetition { path, .. }) =
        &record.provenance.evidence
    else {
        panic!("nested diagnostic must retain nested evidence");
    };
    assert_eq!(
        path.iter().map(|node| node.as_str()).collect::<Vec<_>>(),
        vec!["node:nested.outer", "node:nested.inner"]
    );
    assert_eq!(
        record.provenance.primary_node_id.as_str(),
        "node:nested.outer"
    );
}

#[test]
fn absent_source_keeps_semantic_evidence_without_fabricating_locations() {
    let generated = generate(&nested(false));
    let record = generated
        .records()
        .next()
        .expect("nested diagnostic record");

    assert!(record.provenance.source_origins.is_empty());
    assert!(record.diagnostic.primary_location.is_none());
    assert!(record.diagnostic.related_locations.is_none());
    assert!(record.provenance.contributing_node_ids.len() >= 3);
}

#[test]
fn malformed_relationship_identity_cannot_drive_source_projection() {
    let semantic = repeated_alternation();
    let foundational = analyze(&semantic).expect("foundational analysis");
    let structural = analyze_structure(&semantic, &foundational).expect("structural analysis");
    let safety = analyze_safety(&semantic, &foundational, &structural).expect("safety analysis");
    let mut value = serde_json::to_value(safety).expect("safety must serialize");
    value["findings"][0]["evidence"]["relationship"]["right_node_id"] =
        json!("node:alternation.left");
    let malformed: SafetyAnalysis =
        serde_json::from_value(value).expect("malformed relationship shape deserializes");

    let errors = generate_diagnostics(&semantic, &foundational, &structural, &malformed)
        .expect_err("malformed relationship identity must fail");

    assert_eq!(
        errors.errors[0].code,
        DiagnosticGenerationErrorCode::MalformedEvidenceReference
    );
}

#[test]
fn remediation_is_descriptive_advice_without_target_syntax_or_edits() {
    for semantic in [nested(false), repeated_alternation()] {
        let generated = generate(&semantic);
        for diagnostic in generated.diagnostics() {
            let advice = diagnostic.advice.as_ref().expect("safety advice");
            let combined = advice
                .iter()
                .map(|item| item.message.as_str())
                .collect::<Vec<_>>()
                .join(" ")
                .to_ascii_lowercase();
            assert!(!combined.contains("possessive"));
            assert!(!combined.contains("atomic"));
            assert!(!combined.contains("(?"));
            assert!(diagnostic.fixes.is_none());
        }
    }
}
