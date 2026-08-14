use serde_json::json;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_conversion::{
    convert_semantic_program, SemanticConversionDestination, SemanticConversionStatus,
};

fn generated_program(seed: u32) -> SemanticProgram {
    let root = match seed % 6 {
        0 => json!({"node_id": "node:root", "kind": "empty"}),
        1 => json!({"node_id": "node:root", "kind": "literal", "text": format!("value-{seed}")}),
        2 => json!({"node_id": "node:root", "kind": "wildcard", "line_terminators": "exclude"}),
        3 => json!({
            "node_id": "node:root",
            "kind": "alternation",
            "branches": [
                {"node_id": "node:left", "kind": "literal", "text": "a"},
                {"node_id": "node:right", "kind": "empty"}
            ]
        }),
        4 => json!({
            "node_id": "node:root",
            "kind": "repeat",
            "body": {"node_id": "node:body", "kind": "literal", "text": "a"},
            "min": seed as u64 % 3,
            "max": seed as u64 % 3 + 2,
            "mode": "lazy"
        }),
        _ => json!({
            "node_id": "node:root",
            "kind": "character_set",
            "negated": seed % 2 == 0,
            "members": [
                {"kind": "literal", "value": "a"},
                {"kind": "builtin", "name": "word", "domain": "unicode", "negated": false}
            ]
        }),
    };
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": if seed % 2 == 0 { "sensitive" } else { "insensitive" },
        "root": root
    }))
    .expect("generated semantic program")
}

#[test]
fn repeated_conversion_bytes_are_deterministic_for_a_bounded_corpus() {
    for seed in 0..96 {
        let input = generated_program(seed);
        for destination in [
            SemanticConversionDestination::SemanticStrling,
            SemanticConversionDestination::SimplyBuilder,
        ] {
            let first = convert_semantic_program(&input, destination, None).expect("first");
            let second = convert_semantic_program(&input, destination, None).expect("second");
            assert_eq!(first.status, SemanticConversionStatus::Exact);
            assert_eq!(
                serde_json::to_vec(&first).expect("serialize first"),
                serde_json::to_vec(&second).expect("serialize second"),
                "seed {seed} destination {destination:?}"
            );
        }
    }
}

#[test]
fn bounded_nested_inputs_convert_without_panicking() {
    for depth in 1..=64 {
        let mut root =
            json!({"node_id": format!("node:leaf.{depth}"), "kind": "literal", "text": "a"});
        for level in (0..depth).rev() {
            root = json!({
                "node_id": format!("node:atomic.{depth}.{level}"),
                "kind": "atomic",
                "body": root
            });
        }
        let input: SemanticProgram = serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": "sensitive",
            "root": root
        }))
        .expect("nested semantic program");
        for destination in [
            SemanticConversionDestination::SemanticStrling,
            SemanticConversionDestination::SimplyBuilder,
        ] {
            let result =
                convert_semantic_program(&input, destination, None).expect("bounded conversion");
            assert_eq!(result.status, SemanticConversionStatus::Exact);
        }
    }
}
