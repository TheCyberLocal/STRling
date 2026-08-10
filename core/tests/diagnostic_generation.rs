use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::{
    generate_diagnostics, DiagnosticGenerationErrorCode, SAFETY_UNBOUNDED_NULLABLE_REPETITION,
};
use strling_kernel::safety_analysis::{analyze_safety, SafetyAnalysis};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::{analyze, SemanticFacts};
use strling_kernel::structural_analysis::{analyze_structure, StructuralFacts};

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

fn nullable_repeat(id: &str) -> Value {
    json!({
        "node_id": id,
        "kind": "repeat",
        "body": {"node_id": format!("{id}.body"), "kind": "empty"},
        "min": 0,
        "max": null,
        "mode": "greedy"
    })
}

fn prerequisites(semantic: &SemanticProgram) -> (SemanticFacts, StructuralFacts, SafetyAnalysis) {
    let foundational = analyze(semantic).expect("foundational analysis must succeed");
    let structural =
        analyze_structure(semantic, &foundational).expect("structural analysis must succeed");
    let safety =
        analyze_safety(semantic, &foundational, &structural).expect("safety analysis must succeed");
    (foundational, structural, safety)
}

#[test]
fn finding_free_input_produces_no_diagnostics() {
    let semantic = program(literal("node:literal", "a"));
    let (foundational, structural, safety) = prerequisites(&semantic);

    let generated = generate_diagnostics(&semantic, &foundational, &structural, &safety)
        .expect("generation must succeed");

    assert!(generated.is_empty());
    assert_eq!(generated.len(), 0);
    assert_eq!(generated.diagnostics().count(), 0);
}

#[test]
fn repeated_generation_is_identical_and_source_less_input_is_valid() {
    let semantic = program(nullable_repeat("node:repeat"));
    let (foundational, structural, safety) = prerequisites(&semantic);

    let first = generate_diagnostics(&semantic, &foundational, &structural, &safety)
        .expect("first generation must succeed");
    let second = generate_diagnostics(&semantic, &foundational, &structural, &safety)
        .expect("second generation must succeed");

    assert_eq!(first, second);
    let record = first.records().next().expect("one diagnostic");
    assert_eq!(
        record.diagnostic.code.as_str(),
        SAFETY_UNBOUNDED_NULLABLE_REPETITION
    );
    assert_eq!(record.diagnostic.occurrence.get(), 0);
    assert!(record.diagnostic.primary_location.is_none());
    assert_eq!(record.provenance.primary_node_id.as_str(), "node:repeat");
}

#[test]
fn occurrence_ordinals_are_stable_for_multiple_occurrences() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            nullable_repeat("node:z-repeat"),
            literal("node:separator", "x"),
            nullable_repeat("node:a-repeat")
        ]
    }));
    let (foundational, structural, safety) = prerequisites(&semantic);

    let first = generate_diagnostics(&semantic, &foundational, &structural, &safety)
        .expect("generation must succeed");
    let second = generate_diagnostics(&semantic, &foundational, &structural, &safety)
        .expect("repeated generation must succeed");
    let first_ids: Vec<_> = first
        .records()
        .map(|record| {
            (
                record.provenance.primary_node_id.as_str().to_owned(),
                record.diagnostic.occurrence.get(),
            )
        })
        .collect();
    let second_ids: Vec<_> = second
        .records()
        .map(|record| {
            (
                record.provenance.primary_node_id.as_str().to_owned(),
                record.diagnostic.occurrence.get(),
            )
        })
        .collect();

    assert_eq!(first_ids, second_ids);
    assert_eq!(
        first_ids,
        vec![
            ("node:a-repeat".to_owned(), 0),
            ("node:z-repeat".to_owned(), 1)
        ]
    );
}

#[test]
fn duplicate_finding_input_produces_one_diagnostic() {
    let semantic = program(nullable_repeat("node:repeat"));
    let (foundational, structural, safety) = prerequisites(&semantic);
    let mut value = serde_json::to_value(&safety).expect("safety must serialize");
    let duplicate = value["findings"][0].clone();
    value["findings"]
        .as_array_mut()
        .expect("findings array")
        .push(duplicate);
    let duplicated: SafetyAnalysis =
        serde_json::from_value(value).expect("duplicate evidence shape deserializes");

    let generated = generate_diagnostics(&semantic, &foundational, &structural, &duplicated)
        .expect("generation must deduplicate equivalent evidence");

    assert_eq!(generated.len(), 1);
}

#[test]
fn mismatched_prerequisite_stores_are_structured_errors() {
    let semantic = program(nullable_repeat("node:repeat"));
    let other = program(literal("node:other", "b"));
    let (foundational, structural, safety) = prerequisites(&semantic);
    let (other_foundational, other_structural, _) = prerequisites(&other);

    let foundational_errors =
        generate_diagnostics(&semantic, &other_foundational, &structural, &safety)
            .expect_err("mismatched foundational facts must fail");
    assert_eq!(
        foundational_errors.errors[0].code,
        DiagnosticGenerationErrorCode::MismatchedSemanticFacts
    );

    let structural_errors =
        generate_diagnostics(&semantic, &foundational, &other_structural, &safety)
            .expect_err("mismatched structural facts must fail");
    assert_eq!(
        structural_errors.errors[0].code,
        DiagnosticGenerationErrorCode::MismatchedStructuralFacts
    );
}

#[test]
fn malformed_safety_evidence_reference_is_a_structured_error() {
    let semantic = program(nullable_repeat("node:repeat"));
    let (foundational, structural, safety) = prerequisites(&semantic);
    let mut value = serde_json::to_value(&safety).expect("safety must serialize");
    value["findings"][0]["primary_node_id"] = json!("node:missing");
    let malformed: SafetyAnalysis =
        serde_json::from_value(value).expect("malformed reference shape deserializes");

    let errors = generate_diagnostics(&semantic, &foundational, &structural, &malformed)
        .expect_err("unknown evidence reference must fail");

    assert_eq!(
        errors.errors[0].code,
        DiagnosticGenerationErrorCode::MalformedEvidenceReference
    );
}
