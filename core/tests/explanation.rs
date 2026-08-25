use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;

use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::explanation::{explain_semantics, explain_target, EvidenceClass};
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::{plan_portability, RequirementPlanningDisposition};
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{PortabilityStatus, TargetProfile};
use strling_kernel::{
    capability_evaluation::evaluate_capabilities, explanation::ExplanationDocument,
};

const ECMASCRIPT_2024: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");

fn repository_file(path: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join(path)
}

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

fn explain(input: &SemanticProgram) -> ExplanationDocument {
    let normalized = normalize(input).expect("normalize");
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
fn source_less_literal_matches_the_normative_structured_example() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "literal",
        "text": "a"
    }));
    let actual = serde_json::to_value(explain(&semantic)).expect("serialize explanation");
    let expected: Value = serde_json::from_str(
        &fs::read_to_string(repository_file(
            "spec/explanations/semantic/1.0/examples/source-less-literal.json",
        ))
        .expect("read explanation contract example"),
    )
    .expect("contract example");

    assert_eq!(actual, expected);
}

#[test]
fn safety_and_diagnostics_remain_distinct_evidence_classes() {
    let semantic = program(json!({
        "node_id": "node:repeat",
        "kind": "repeat",
        "body": {"node_id": "node:empty", "kind": "empty"},
        "min": 0,
        "max": null,
        "mode": "greedy"
    }));
    let explanation = explain(&semantic);

    assert_eq!(explanation.safety_findings.len(), 1);
    assert_eq!(
        explanation.safety_findings[0].evidence_class,
        EvidenceClass::SemanticFact
    );
    assert_eq!(explanation.diagnostics.len(), 1);
    assert_eq!(
        explanation.diagnostics[0].evidence_class,
        EvidenceClass::DiagnosticAdvice
    );
    assert_eq!(explanation.concise.safety_finding_count, 1);
    assert_eq!(explanation.concise.diagnostic_count, 1);
}

#[test]
fn target_projection_uses_completed_plan_evidence_without_mutating_semantics() {
    let semantic = program(json!({
        "node_id": "node:atomic",
        "kind": "atomic",
        "body": {"node_id": "node:literal", "kind": "literal", "text": "x"}
    }));
    let normalized = normalize(&semantic).expect("normalize");
    let foundational = analyze(&normalized).expect("foundational analysis");
    let structural = analyze_structure(&normalized, &foundational).expect("structural analysis");
    let safety = analyze_safety(&normalized, &foundational, &structural).expect("safety analysis");
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .expect("diagnostic generation");
    let neutral = explain_semantics(
        &normalized,
        &foundational,
        &structural,
        &safety,
        &diagnostics,
    )
    .expect("semantic explanation");
    let target: TargetProfile = serde_json::from_str(ECMASCRIPT_2024).expect("target profile");
    let evaluation = evaluate_capabilities(&normalized, &foundational, &structural, &target)
        .expect("capability evaluation");
    let plan = plan_portability(
        &normalized,
        &foundational,
        &structural,
        &target,
        &evaluation,
    )
    .expect("portability plan");

    let projected = explain_target(&neutral, &evaluation, &plan).expect("target explanation");
    let native_target: TargetProfile = serde_json::from_str(PCRE2_1042).expect("native target");
    let native_evaluation =
        evaluate_capabilities(&normalized, &foundational, &structural, &native_target)
            .expect("native capability evaluation");
    let native_plan = plan_portability(
        &normalized,
        &foundational,
        &structural,
        &native_target,
        &native_evaluation,
    )
    .expect("native portability plan");
    let native_projected =
        explain_target(&neutral, &native_evaluation, &native_plan).expect("native explanation");

    assert!(neutral.target.is_none());
    assert!(neutral.concise.target.is_none());
    assert_eq!(plan.status, Some(PortabilityStatus::EquivalentRewrite));
    assert!(matches!(
        plan.decisions[0].disposition,
        RequirementPlanningDisposition::EquivalentRewrite(_)
    ));
    let detailed = projected.target.as_ref().expect("target details");
    assert_eq!(detailed.decisions.len(), 1);
    assert_eq!(
        detailed.decisions[0].evidence_class,
        EvidenceClass::TargetPlan
    );
    assert!(detailed.diagnostics.is_empty());
    assert_eq!(projected.nodes, neutral.nodes);
    assert_eq!(projected.safety_findings, neutral.safety_findings);
    assert_eq!(projected.diagnostics, neutral.diagnostics);
    assert_eq!(native_plan.status, Some(PortabilityStatus::Native));
    assert_eq!(native_projected.nodes, projected.nodes);
    assert_eq!(native_projected.safety_findings, projected.safety_findings);
    assert_ne!(native_projected.target, projected.target);
}

#[test]
fn every_semantic_node_kind_has_a_typed_projection() {
    let roots = [
        json!({"node_id": "node:empty", "kind": "empty"}),
        json!({
            "node_id": "node:sequence", "kind": "sequence", "items": [
                {"node_id": "node:sequence.literal", "kind": "literal", "text": "a"},
                {"node_id": "node:sequence.wildcard", "kind": "wildcard", "line_terminators": "exclude"}
            ]
        }),
        json!({
            "node_id": "node:alternation", "kind": "alternation", "branches": [
                {"node_id": "node:alternation.a", "kind": "literal", "text": "a"},
                {"node_id": "node:alternation.b", "kind": "literal", "text": "b"}
            ]
        }),
        json!({"node_id": "node:literal", "kind": "literal", "text": "a"}),
        json!({"node_id": "node:wildcard", "kind": "wildcard", "line_terminators": "include"}),
        json!({
            "node_id": "node:set", "kind": "character_set", "negated": false,
            "members": [{"kind": "literal", "value": "a"}]
        }),
        json!({
            "node_id": "node:repeat", "kind": "repeat",
            "body": {"node_id": "node:repeat.body", "kind": "literal", "text": "a"},
            "min": 1, "max": 2, "mode": "lazy"
        }),
        json!({"node_id": "node:position", "kind": "position", "position": "input_start"}),
        json!({
            "node_id": "node:capture", "kind": "capture", "capture_id": "capture:value", "name": "value",
            "body": {"node_id": "node:capture.body", "kind": "literal", "text": "a"}
        }),
        json!({
            "node_id": "node:reference.sequence", "kind": "sequence", "items": [
                {
                    "node_id": "node:reference.capture", "kind": "capture", "capture_id": "capture:ref",
                    "body": {"node_id": "node:reference.body", "kind": "literal", "text": "a"}
                },
                {"node_id": "node:reference", "kind": "backreference", "capture_id": "capture:ref"}
            ]
        }),
        json!({
            "node_id": "node:lookaround", "kind": "lookaround", "direction": "ahead", "polarity": "positive",
            "body": {"node_id": "node:lookaround.body", "kind": "literal", "text": "a"}
        }),
        json!({
            "node_id": "node:atomic", "kind": "atomic",
            "body": {"node_id": "node:atomic.body", "kind": "literal", "text": "a"}
        }),
    ];
    let mut kinds = BTreeSet::new();
    for root in roots {
        for node in explain(&program(root)).nodes {
            let value = serde_json::to_value(node.semantic).expect("serialize node semantics");
            kinds.insert(value["kind"].as_str().expect("semantic kind").to_owned());
        }
    }

    assert_eq!(
        kinds,
        BTreeSet::from([
            "alternation".to_owned(),
            "atomic".to_owned(),
            "backreference".to_owned(),
            "capture".to_owned(),
            "character_set".to_owned(),
            "empty".to_owned(),
            "literal".to_owned(),
            "lookaround".to_owned(),
            "position".to_owned(),
            "repeat".to_owned(),
            "sequence".to_owned(),
            "wildcard".to_owned(),
        ])
    );
}
