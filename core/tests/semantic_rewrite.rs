use serde_json::json;
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::RewriteStrategyId;
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::semantic_rewrite::{
    request_semantic_rewrite, SemanticRewriteErrorCode, SemanticRewriteRequest,
};
use strling_kernel::source::{ContractVersion, NodeId};
use strling_kernel::structural_analysis::analyze_structure;

fn program(
    minimum: u64,
    maximum: Option<u64>,
    mode: &str,
    body: serde_json::Value,
) -> SemanticProgram {
    let maximum = maximum.map_or(serde_json::Value::Null, |value| json!(value));
    let raw: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {
            "node_id": "node:rewrite.repeat",
            "kind": "repeat",
            "body": body,
            "min": minimum,
            "max": maximum,
            "mode": mode
        }
    }))
    .expect("semantic input");
    normalize(&raw).expect("normalized input")
}

fn request(strategy_id: RewriteStrategyId, node: &str) -> SemanticRewriteRequest {
    SemanticRewriteRequest {
        contract_version: ContractVersion::V1_0_0,
        strategy_id,
        node_id: NodeId::try_from(node).expect("node identity"),
    }
}

#[test]
fn greedy_and_lazy_exact_once_requests_return_certified_unapplied_actions() {
    for mode in ["greedy", "lazy"] {
        let semantic = program(
            1,
            Some(1),
            mode,
            json!({
                "node_id": "node:rewrite.capture",
                "kind": "capture",
                "capture_id": "capture:rewrite.value",
                "name": "value",
                "body": {
                    "node_id": "node:rewrite.literal",
                    "kind": "literal",
                    "text": "λ"
                }
            }),
        );
        let original = semantic.clone();
        let foundational = analyze(&semantic).expect("foundational facts");
        let structural = analyze_structure(&semantic, &foundational).expect("structural facts");
        let rewrite_request = request(
            RewriteStrategyId::ElideExactOnceRepetitionV1,
            "node:rewrite.repeat",
        );

        let first =
            request_semantic_rewrite(&semantic, &foundational, &structural, &rewrite_request)
                .expect("request succeeds")
                .expect("exact-once action");
        let second =
            request_semantic_rewrite(&semantic, &foundational, &structural, &rewrite_request)
                .expect("repeated request succeeds")
                .expect("repeated exact-once action");

        assert_eq!(first, second);
        assert_eq!(semantic, original, "request must not mutate input");
        assert_eq!(
            first.removed_wrapper_node_id.as_str(),
            "node:rewrite.repeat"
        );
        assert_eq!(first.replacement_node_id.as_str(), "node:rewrite.capture");
        assert!(matches!(first.replacement_subtree, Node::Capture { .. }));
        assert_eq!(first.proof.len(), 4);
        assert_eq!(
            first.certification.strategy_fingerprint.as_str(),
            "6aca0899f54a7d2154bff4dd96fa14bf8147d250ffe1d63cef0a572dced0b71e"
        );
        assert!(first.explanation.contains("explicit consumer"));
    }
}

#[test]
fn possessive_nonexact_absent_and_wrong_kind_requests_produce_no_action() {
    for (minimum, maximum, mode) in [
        (1, Some(1), "possessive"),
        (0, Some(1), "greedy"),
        (1, Some(2), "lazy"),
        (1, None, "greedy"),
    ] {
        let semantic = program(
            minimum,
            maximum,
            mode,
            json!({
                "node_id": "node:rewrite.literal",
                "kind": "literal",
                "text": "a"
            }),
        );
        let foundational = analyze(&semantic).expect("foundational facts");
        let structural = analyze_structure(&semantic, &foundational).expect("structural facts");
        let rewrite_request = request(
            RewriteStrategyId::ElideExactOnceRepetitionV1,
            "node:rewrite.repeat",
        );
        assert_eq!(
            request_semantic_rewrite(&semantic, &foundational, &structural, &rewrite_request,)
                .expect("non-applicable request is not malformed"),
            None
        );
    }

    let semantic = program(
        1,
        Some(1),
        "greedy",
        json!({
            "node_id": "node:rewrite.literal",
            "kind": "literal",
            "text": "a"
        }),
    );
    let foundational = analyze(&semantic).expect("foundational facts");
    let structural = analyze_structure(&semantic, &foundational).expect("structural facts");
    let absent = request(
        RewriteStrategyId::ElideExactOnceRepetitionV1,
        "node:rewrite.absent",
    );
    assert_eq!(
        request_semantic_rewrite(&semantic, &foundational, &structural, &absent)
            .expect("absent node is non-applicable"),
        None
    );
    let body = request(
        RewriteStrategyId::ElideExactOnceRepetitionV1,
        "node:rewrite.literal",
    );
    assert_eq!(
        request_semantic_rewrite(&semantic, &foundational, &structural, &body)
            .expect("wrong node kind is non-applicable"),
        None
    );
}

#[test]
fn mandatory_portability_strategy_cannot_cross_the_optional_action_boundary() {
    let semantic = program(
        1,
        Some(1),
        "greedy",
        json!({
            "node_id": "node:rewrite.literal",
            "kind": "literal",
            "text": "a"
        }),
    );
    let foundational = analyze(&semantic).expect("foundational facts");
    let structural = analyze_structure(&semantic, &foundational).expect("structural facts");
    let atomic = request(
        RewriteStrategyId::ElideAtomicLiteralV1,
        "node:rewrite.repeat",
    );
    let error = request_semantic_rewrite(&semantic, &foundational, &structural, &atomic)
        .expect_err("mandatory strategy is not an optional action");
    assert_eq!(
        error.errors[0].code,
        SemanticRewriteErrorCode::StrategyNotOptional
    );
}

#[test]
fn mismatched_certified_facts_fail_without_partial_action() {
    let semantic = program(
        1,
        Some(1),
        "greedy",
        json!({
            "node_id": "node:rewrite.literal",
            "kind": "literal",
            "text": "a"
        }),
    );
    let other = program(
        1,
        Some(1),
        "lazy",
        json!({
            "node_id": "node:rewrite.other",
            "kind": "literal",
            "text": "b"
        }),
    );
    let foundational = analyze(&other).expect("other foundational facts");
    let structural = analyze_structure(&other, &foundational).expect("other structural facts");
    let rewrite_request = request(
        RewriteStrategyId::ElideExactOnceRepetitionV1,
        "node:rewrite.repeat",
    );
    let error = request_semantic_rewrite(&semantic, &foundational, &structural, &rewrite_request)
        .expect_err("cross-program facts fail");
    assert!(error
        .errors
        .iter()
        .all(|item| item.code == SemanticRewriteErrorCode::InvalidPrerequisites));
}
