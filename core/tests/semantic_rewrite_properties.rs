use serde_json::json;
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::RewriteStrategyId;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::semantic_rewrite::{request_semantic_rewrite, SemanticRewriteRequest};
use strling_kernel::source::{ContractVersion, NodeId};
use strling_kernel::structural_analysis::analyze_structure;

#[test]
fn fixed_seed_candidates_are_deterministic_immutable_and_exactly_guarded() {
    let mut applicable = 0;
    for index in 0_u64..256 {
        let value = 0x9E37_79B9_7F4A_7C15_u64.wrapping_mul(index + 1);
        let minimum = value % 3;
        let maximum = match (value >> 8) % 4 {
            0 => serde_json::Value::Null,
            other => json!(other - 1),
        };
        if maximum.as_u64().is_some_and(|maximum| maximum < minimum) {
            continue;
        }
        let mode = ["greedy", "lazy", "possessive"][((value >> 16) % 3) as usize];
        let raw: SemanticProgram = serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": "sensitive",
            "root": {
                "node_id": format!("node:rewrite.generated.{index}.repeat"),
                "kind": "repeat",
                "body": {
                    "node_id": format!("node:rewrite.generated.{index}.body"),
                    "kind": "literal",
                    "text": if value & 1 == 0 { "a" } else { "λ" }
                },
                "min": minimum,
                "max": maximum,
                "mode": mode
            }
        }))
        .expect("generated semantic program");
        let semantic = normalize(&raw).expect("generated normalization");
        let original = semantic.clone();
        let foundational = analyze(&semantic).expect("generated foundational facts");
        let structural =
            analyze_structure(&semantic, &foundational).expect("generated structural facts");
        let request = SemanticRewriteRequest {
            contract_version: ContractVersion::V1_0_0,
            strategy_id: RewriteStrategyId::ElideExactOnceRepetitionV1,
            node_id: NodeId::try_from(format!("node:rewrite.generated.{index}.repeat"))
                .expect("generated node identity"),
        };
        let first = request_semantic_rewrite(&semantic, &foundational, &structural, &request)
            .expect("generated rewrite request");
        let second = request_semantic_rewrite(&semantic, &foundational, &structural, &request)
            .expect("repeated generated rewrite request");
        assert_eq!(first, second);
        assert_eq!(semantic, original);

        let expected =
            minimum == 1 && maximum.as_u64() == Some(1) && matches!(mode, "greedy" | "lazy");
        assert_eq!(first.is_some(), expected, "candidate {index}");
        applicable += usize::from(expected);
    }
    assert!(
        applicable > 0,
        "fixed seed must exercise applicable actions"
    );
}
