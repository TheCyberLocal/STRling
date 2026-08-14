use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::explanation::explain_semantics;
use strling_kernel::normalization::normalize;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::semantic_conversion::{
    convert_semantic_program, SemanticConversionDestination, SemanticConversionErrorCode,
    SemanticConversionOutput, SemanticConversionStatus,
};
use strling_kernel::structural_analysis::analyze_structure;

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("semantic fixture")
}

fn explanation(input: &SemanticProgram) -> strling_kernel::explanation::ExplanationDocument {
    let normalized = normalize(input).expect("normalize");
    let foundational = analyze(&normalized).expect("foundational analysis");
    let structural = analyze_structure(&normalized, &foundational).expect("structural analysis");
    let safety = analyze_safety(&normalized, &foundational, &structural).expect("safety analysis");
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .expect("diagnostics");
    explain_semantics(
        &normalized,
        &foundational,
        &structural,
        &safety,
        &diagnostics,
    )
    .expect("explanation")
}

#[test]
fn equivalent_source_less_inputs_converge_on_destination_semantics() {
    let direct = program(json!({
        "node_id": "node:direct",
        "kind": "literal",
        "text": "value"
    }));
    let renamed = program(json!({
        "node_id": "node:renamed",
        "kind": "literal",
        "text": "value"
    }));

    let first = convert_semantic_program(
        &direct,
        SemanticConversionDestination::SemanticStrling,
        None,
    )
    .expect("direct conversion");
    let second = convert_semantic_program(
        &renamed,
        SemanticConversionDestination::SemanticStrling,
        None,
    )
    .expect("renamed conversion");
    let (
        Some(SemanticConversionOutput::SemanticStrling { text: first, .. }),
        Some(SemanticConversionOutput::SemanticStrling { text: second, .. }),
    ) = (first.output, second.output)
    else {
        panic!("expected Semantic STRling outputs");
    };
    assert_eq!(first, second);
}

#[test]
fn exact_explanation_links_unsupported_nodes_without_influencing_output() {
    let input = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {"node_id": "node:reference", "kind": "backreference", "capture_id": "capture:later"},
            {
                "node_id": "node:capture",
                "kind": "capture",
                "capture_id": "capture:later",
                "name": "later",
                "body": {"node_id": "node:body", "kind": "literal", "text": "a"}
            }
        ]
    }));
    let explanation = explanation(&input);
    let without =
        convert_semantic_program(&input, SemanticConversionDestination::SemanticStrling, None)
            .expect("unsupported without explanation");
    let with = convert_semantic_program(
        &input,
        SemanticConversionDestination::SemanticStrling,
        Some(&explanation),
    )
    .expect("unsupported with explanation");

    assert_eq!(with.status, SemanticConversionStatus::Unsupported);
    assert_eq!(with.output, without.output);
    assert_eq!(with.issues, without.issues);
    assert_eq!(with.explanation_links.len(), 1);
    assert_eq!(with.explanation_links[0].node_id.as_str(), "node:reference");
    assert_eq!(
        with.explanation_links[0].semantic_program,
        with.source_program
    );
}

#[test]
fn mismatched_explanation_is_rejected_instead_of_silently_dropped() {
    let input = program(json!({
        "node_id": "node:input",
        "kind": "literal",
        "text": "a"
    }));
    let other = program(json!({
        "node_id": "node:other",
        "kind": "literal",
        "text": "b"
    }));
    let explanation = explanation(&other);

    let errors = convert_semantic_program(
        &input,
        SemanticConversionDestination::SimplyBuilder,
        Some(&explanation),
    )
    .expect_err("mismatched explanation");
    assert_eq!(
        errors.errors[0].code,
        SemanticConversionErrorCode::MismatchedExplanation
    );
}

#[test]
fn result_serialization_uses_the_versioned_contract_vocabulary() {
    let input = program(json!({
        "node_id": "node:literal",
        "kind": "literal",
        "text": "a"
    }));
    let result =
        convert_semantic_program(&input, SemanticConversionDestination::SimplyBuilder, None)
            .expect("Simply conversion");
    let value = serde_json::to_value(result).expect("serialize conversion result");

    assert_eq!(value["conversion_version"], "1.0.0");
    assert_eq!(value["destination"], "simply_builder");
    assert_eq!(
        value["destination_contract"]["id"],
        "strling.simply-builder"
    );
    assert_eq!(value["status"], "exact");
    assert_eq!(value["comment_policy"], "semantic_ir_only");
    assert_eq!(
        value["equivalence"]["method"],
        "normalized_semantic_alpha_equivalence@1.0.0"
    );
    assert_eq!(
        value["equivalence"]["excluded_evidence"],
        json!(["node_ids", "capture_ids", "origins", "sources"])
    );
}
