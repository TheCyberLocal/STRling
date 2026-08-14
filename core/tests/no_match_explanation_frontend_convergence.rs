use std::convert::TryFrom;

use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::explanation::{explain_semantics, ExplanationDocument};
use strling_kernel::no_match_explanation::{explain_no_match, NoMatchExecutionMode, NoMatchLimits};
use strling_kernel::normalization::normalize;
use strling_kernel::regex_frontend;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::semantic_frontend;
use strling_kernel::simply::{SimplyBuilder, SimplyOptions};
use strling_kernel::source::{SourceDocument, SpecificationVersion};
use strling_kernel::structural_analysis::analyze_structure;

fn source_document(
    frontend_id: &str,
    dialect_version: &str,
    media_type: &str,
    source_id: &str,
    text: &str,
) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": source_id,
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": frontend_id,
            "dialect_version": dialect_version
        },
        "display_name": "no-match-convergence.fixture",
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": media_type,
            "text": text
        },
        "provenance": {
            "kind": "authored",
            "description": "P15-T03 frontend convergence fixture"
        }
    }))
    .expect("source document")
}

fn explain(input: &SemanticProgram) -> (SemanticProgram, ExplanationDocument) {
    let normalized = normalize(input).expect("normalize");
    let foundational = analyze(&normalized).expect("foundational analysis");
    let structural = analyze_structure(&normalized, &foundational).expect("structural analysis");
    let safety = analyze_safety(&normalized, &foundational, &structural).expect("safety analysis");
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .expect("diagnostic generation");
    let semantic = explain_semantics(
        &normalized,
        &foundational,
        &structural,
        &safety,
        &diagnostics,
    )
    .expect("semantic explanation");
    (normalized, semantic)
}

fn explanation_projection(program: &SemanticProgram) -> Value {
    let (normalized, semantic) = explain(program);
    let explanation = explain_no_match(
        &normalized,
        &semantic,
        "dog",
        NoMatchExecutionMode::Search,
        NoMatchLimits::default(),
    )
    .expect("no-match explanation");
    let mut value = serde_json::to_value(explanation).expect("serialize explanation");
    erase_alpha_identity(&mut value);
    value
}

fn erase_alpha_identity(value: &mut Value) {
    match value {
        Value::Object(object) => {
            object.retain(|key, _| {
                key != "semantic_program"
                    && key != "node_id"
                    && key != "capture_id"
                    && key != "source"
            });
            for child in object.values_mut() {
                erase_alpha_identity(child);
            }
        }
        Value::Array(items) => {
            for item in items {
                erase_alpha_identity(item);
            }
        }
        _ => {}
    }
}

#[test]
fn direct_simply_semantic_dsl_and_regex_import_converge_after_alpha_projection() {
    let direct: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {"node_id": "node:direct", "kind": "literal", "text": "cat"}
    }))
    .expect("direct Semantic IR");

    let mut builder = SimplyBuilder::new(
        "no-match-convergence",
        SpecificationVersion::try_from("1.0-draft.1").expect("specification version"),
        SimplyOptions::default(),
    )
    .expect("Simply builder");
    let simply_root = builder.literal("root", "cat").expect("Simply literal");
    let simply = builder
        .finish_program(&simply_root)
        .expect("Simply program");

    let semantic_dsl = semantic_frontend::parse(&source_document(
        semantic_frontend::FRONTEND_ID,
        semantic_frontend::DIALECT_VERSION,
        semantic_frontend::MEDIA_TYPE,
        "src:no-match.semantic",
        "semantic strling 1.0;\ncase sensitive;\npattern text \"cat\";\n",
    ))
    .expect("Semantic STRling frontend")
    .program;

    let imported = regex_frontend::parse(&source_document(
        regex_frontend::FRONTEND_ID,
        regex_frontend::DIALECT_VERSION,
        "text/strling-regex",
        "src:no-match.regex",
        "cat",
    ))
    .expect("regex compatibility frontend")
    .program;

    let expected = explanation_projection(&direct);
    for (surface, program) in [
        ("Simply", simply),
        ("Semantic STRling", semantic_dsl),
        ("regex import", imported),
    ] {
        assert_eq!(
            explanation_projection(&program),
            expected,
            "{surface} explanation must alpha-converge"
        );
    }
}
