use std::convert::TryFrom;

use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::explanation::explain_semantics;
use strling_kernel::normalization::normalize;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::simply::{SimplyBuilder, SimplyOptions};
use strling_kernel::source::SpecificationVersion;
use strling_kernel::structural_analysis::analyze_structure;

fn explain(input: &SemanticProgram) -> Value {
    let normalized = normalize(input).expect("normalize");
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
    serde_json::to_value(explanation).expect("serialize explanation")
}

fn semantic_projection(value: &mut Value) {
    match value {
        Value::Object(object) => {
            object.retain(|key, _| {
                key != "semantic_program"
                    && key != "node_id"
                    && key != "root_node_id"
                    && key != "source"
                    && key != "source_ids"
                    && !key.ends_with("_node_id")
                    && !key.ends_with("_node_ids")
            });
            for child in object.values_mut() {
                semantic_projection(child);
            }
        }
        Value::Array(items) => {
            for item in items {
                semantic_projection(item);
            }
        }
        _ => {}
    }
}

#[test]
fn simply_and_semantic_ir_explain_equivalent_structure() {
    let direct: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {"node_id": "node:direct", "kind": "literal", "text": "a"}
    }))
    .expect("direct Semantic IR");
    let mut builder = SimplyBuilder::new(
        "explanation-convergence",
        SpecificationVersion::try_from("1.0-draft.1").expect("specification version"),
        SimplyOptions::default(),
    )
    .expect("Simply builder");
    let root = builder.literal("root", "a").expect("Simply literal");
    let simply = builder.finish_program(&root).expect("Simply program");

    let mut direct_explanation = explain(&direct);
    let mut simply_explanation = explain(&simply);
    semantic_projection(&mut direct_explanation);
    semantic_projection(&mut simply_explanation);

    assert_eq!(direct_explanation, simply_explanation);
}
