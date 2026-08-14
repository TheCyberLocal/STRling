use std::panic::{catch_unwind, AssertUnwindSafe};

use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::explanation::{explain_semantics, ExplanationDocument};
use strling_kernel::no_match_explanation::{explain_no_match, NoMatchExecutionMode, NoMatchLimits};
use strling_kernel::normalization::normalize;
use strling_kernel::safety_analysis::analyze_safety;
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
    .expect("semantic fixture")
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

#[test]
fn bounded_pathological_inputs_never_panic_or_exceed_reported_limits() {
    let roots = [
        json!({
            "node_id": "node:alternation",
            "kind": "alternation",
            "branches": [
                {"node_id": "node:a", "kind": "literal", "text": "aaaa"},
                {"node_id": "node:b", "kind": "literal", "text": "bbbb"}
            ]
        }),
        json!({
            "node_id": "node:repeat",
            "kind": "repeat",
            "body": {"node_id": "node:empty", "kind": "empty"},
            "min": 0,
            "max": null,
            "mode": "greedy"
        }),
        json!({
            "node_id": "node:nested",
            "kind": "capture",
            "capture_id": "capture:outer",
            "body": {
                "node_id": "node:nested.inner",
                "kind": "capture",
                "capture_id": "capture:inner",
                "body": {"node_id": "node:nested.literal", "kind": "literal", "text": "z"}
            }
        }),
    ];
    let subjects = ["", "a", "aaaaaaaa", "éééé", "🙂🙂🙂🙂", "a\nb\r\nc"];

    for root in roots {
        let (input, semantic) = explain(&program(root));
        for subject in subjects {
            let actual = catch_unwind(AssertUnwindSafe(|| {
                explain_no_match(
                    &input,
                    &semantic,
                    subject,
                    NoMatchExecutionMode::Search,
                    NoMatchLimits {
                        max_steps: 256,
                        max_depth: 16,
                        max_branch_expansions: 64,
                        max_findings: 8,
                        ..NoMatchLimits::default()
                    },
                )
            }))
            .expect("bounded evaluator must not panic")
            .expect("valid bounded input");

            assert!(actual.work.steps <= actual.limits.max_steps);
            assert!(actual.work.maximum_depth <= actual.limits.max_depth);
            assert!(actual.work.branch_expansions <= actual.limits.max_branch_expansions);
            assert!(actual.findings.len() <= actual.limits.max_findings);
        }
    }
}

#[test]
fn serialized_results_are_byte_identical_for_repeated_supported_evaluation() {
    let (input, semantic) = explain(&program(json!({
        "node_id": "node:literal",
        "kind": "literal",
        "text": "cat"
    })));
    let mut previous = None;

    for _ in 0..32 {
        let actual = explain_no_match(
            &input,
            &semantic,
            "dog",
            NoMatchExecutionMode::Search,
            NoMatchLimits::default(),
        )
        .expect("supported evaluation");
        let bytes = serde_json::to_vec(&actual).expect("serialize result");
        if let Some(expected) = &previous {
            assert_eq!(&bytes, expected);
        }
        previous = Some(bytes);
    }
}
