use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::explanation::explain_semantics;
use strling_kernel::normalization::normalize;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;

fn explain(root: Value) -> strling_kernel::explanation::ExplanationDocument {
    let input: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("semantic fixture");
    let normalized = normalize(&input).expect("normalize");
    let foundational = analyze(&normalized).expect("foundational analysis");
    let structural = analyze_structure(&normalized, &foundational).expect("structural analysis");
    let safety = analyze_safety(&normalized, &foundational, &structural).expect("safety analysis");
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .expect("diagnostic generation");
    explain_semantics(
        &normalized,
        &foundational,
        &structural,
        &safety,
        &diagnostics,
    )
    .expect("semantic explanation")
}

#[test]
fn serialization_is_byte_deterministic() {
    let explanation = explain(json!({
        "node_id": "node:choice",
        "kind": "alternation",
        "branches": [
            {"node_id": "node:a", "kind": "literal", "text": "a"},
            {"node_id": "node:b", "kind": "literal", "text": "b"}
        ]
    }));

    let first = serde_json::to_vec(&explanation).expect("serialize once");
    let second = serde_json::to_vec(&explanation).expect("serialize twice");
    assert_eq!(first, second);
}

#[test]
fn source_less_explanations_do_not_invent_spans() {
    let explanation = explain(json!({
        "node_id": "node:root",
        "kind": "literal",
        "text": "value"
    }));

    assert!(explanation.program.source_ids.is_empty());
    assert!(explanation.nodes[0].source.source_spans.is_empty());
    assert!(explanation.nodes[0].source.derived_from_node_ids.is_empty());
}

#[test]
fn canonical_provenance_is_preserved_without_source_text_inference() {
    let input: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "sources": [{
            "contract_version": "1.0.0",
            "source_id": "src:explanation",
            "specification_version": "1.0-draft.1",
            "frontend": {"id": "semantic", "dialect_version": "1.0"},
            "content": {"kind": "inline", "encoding": "utf-8", "text": "a"},
            "provenance": {"kind": "authored"}
        }],
        "root": {
            "node_id": "node:root",
            "kind": "literal",
            "origin": {"source_spans": [{
                "source_id": "src:explanation",
                "coordinate_system": "utf8-bytes",
                "start": 0,
                "end": 1
            }]},
            "text": "a"
        }
    }))
    .expect("source-backed semantic fixture");
    let normalized = normalize(&input).expect("normalize");
    let foundational = analyze(&normalized).expect("foundational analysis");
    let structural = analyze_structure(&normalized, &foundational).expect("structural analysis");
    let safety = analyze_safety(&normalized, &foundational, &structural).expect("safety analysis");
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .expect("diagnostic generation");
    let explanation = explain_semantics(
        &normalized,
        &foundational,
        &structural,
        &safety,
        &diagnostics,
    )
    .expect("semantic explanation");

    assert_eq!(explanation.program.source_ids.len(), 1);
    assert_eq!(explanation.nodes[0].source.source_spans.len(), 1);
    assert_eq!(explanation.nodes[0].source.source_spans[0].start, 0);
    assert_eq!(explanation.nodes[0].source.source_spans[0].end, 1);
}

#[test]
fn leading_consumption_unknowns_remain_explicit() {
    let explanation = explain(json!({
        "node_id": "node:sequence", "kind": "sequence", "items": [
            {
                "node_id": "node:capture", "kind": "capture", "capture_id": "capture:value",
                "body": {"node_id": "node:body", "kind": "literal", "text": "a"}
            },
            {"node_id": "node:reference", "kind": "backreference", "capture_id": "capture:value"}
        ]
    }));
    let reference = explanation
        .nodes
        .iter()
        .find(|node| node.node_id.as_str() == "node:reference")
        .expect("backreference explanation");
    let leading = serde_json::to_value(&reference.structural.leading_consumption)
        .expect("serialize leading terms");

    assert!(leading
        .as_array()
        .expect("leading array")
        .iter()
        .any(|term| { term["kind"] == "unknown" && term["reason"] == "backreference" }));
}

#[test]
fn same_node_ids_cannot_reuse_diagnostics_across_programs() {
    let unsafe_input: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {
            "node_id": "node:repeat", "kind": "repeat",
            "body": {"node_id": "node:body", "kind": "empty"},
            "min": 0, "max": null, "mode": "greedy"
        }
    }))
    .expect("unsafe semantic fixture");
    let safe_input: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {
            "node_id": "node:repeat", "kind": "repeat",
            "body": {"node_id": "node:body", "kind": "literal", "text": "a"},
            "min": 0, "max": null, "mode": "greedy"
        }
    }))
    .expect("safe semantic fixture");
    let unsafe_foundational = analyze(&unsafe_input).expect("unsafe foundational");
    let unsafe_structural =
        analyze_structure(&unsafe_input, &unsafe_foundational).expect("unsafe structural");
    let unsafe_safety = analyze_safety(&unsafe_input, &unsafe_foundational, &unsafe_structural)
        .expect("unsafe safety");
    let stale_generation = generate_diagnostics(
        &unsafe_input,
        &unsafe_foundational,
        &unsafe_structural,
        &unsafe_safety,
    )
    .expect("unsafe diagnostics");
    let safe_foundational = analyze(&safe_input).expect("safe foundational");
    let safe_structural =
        analyze_structure(&safe_input, &safe_foundational).expect("safe structural");
    let safe_safety =
        analyze_safety(&safe_input, &safe_foundational, &safe_structural).expect("safe safety");

    let errors = explain_semantics(
        &safe_input,
        &safe_foundational,
        &safe_structural,
        &safe_safety,
        &stale_generation,
    )
    .expect_err("cross-program diagnostic evidence must fail");

    assert_eq!(
        errors.errors[0].code,
        strling_kernel::explanation::ExplanationErrorCode::MismatchedDiagnosticEvidence
    );
}
