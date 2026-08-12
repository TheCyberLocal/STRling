use serde_json::json;
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::normalization::normalize;
use strling_kernel::portability_diagnostics::{
    explain_portability, PortabilityDiagnosticErrorCode, PORTABILITY_NATIVE_DIAGNOSTIC,
    PORTABILITY_REWRITE_DIAGNOSTIC, PORTABILITY_UNRESOLVED_DIAGNOSTIC,
    PORTABILITY_UNSUPPORTED_DIAGNOSTIC,
};
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::regex_frontend::parse;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::SourceDocument;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;

const PCRE2: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

#[test]
fn native_rewrite_unsupported_and_unresolved_decisions_are_explained() {
    let cases = [
        ("(?>a)", PCRE2, PORTABILITY_NATIVE_DIAGNOSTIC),
        ("(?>a)", ECMASCRIPT, PORTABILITY_REWRITE_DIAGNOSTIC),
        ("(?>a|b)", ECMASCRIPT, PORTABILITY_UNSUPPORTED_DIAGNOSTIC),
        ("(?>λ)", ECMASCRIPT, PORTABILITY_UNRESOLVED_DIAGNOSTIC),
    ];

    for (source, profile, expected_code) in cases {
        let semantic = parsed_program(source);
        let target: TargetProfile = serde_json::from_str(profile).expect("target profile");
        let (plan, first) = plan_and_explain(&semantic, &target);
        let second = explain_portability(&semantic, &plan).expect("second explanation pass");

        assert_eq!(first, second, "explanations must be deterministic");
        assert!(first
            .iter()
            .any(|diagnostic| diagnostic.code.as_str() == expected_code));
        for diagnostic in &first {
            assert_eq!(
                diagnostic.phase,
                strling_kernel::diagnostic::CompilerPhase::Portability
            );
            assert_eq!(
                diagnostic.category,
                strling_kernel::diagnostic::DiagnosticCategory::Portability
            );
            assert_eq!(
                diagnostic.severity_basis,
                strling_kernel::diagnostic::SeverityBasis::TargetProfile
            );
            assert!(diagnostic.primary_location.is_some());
            assert!(diagnostic
                .advice
                .as_ref()
                .is_some_and(|advice| !advice.is_empty()));
        }
    }
}

#[test]
fn equivalent_rewrite_explanation_carries_source_and_certification_evidence() {
    let semantic = parsed_program("(?>a)");
    let target: TargetProfile = serde_json::from_str(ECMASCRIPT).expect("target profile");
    let (plan, diagnostics) = plan_and_explain(&semantic, &target);
    let rewrite = diagnostics
        .iter()
        .find(|diagnostic| diagnostic.code.as_str() == PORTABILITY_REWRITE_DIAGNOSTIC)
        .expect("rewrite explanation");

    assert!(rewrite.message.contains("redundant atomic wrapper"));
    let primary = rewrite
        .primary_location
        .as_ref()
        .expect("primary source span");
    assert_eq!(primary.start, 0);
    assert_eq!(primary.end, 5);
    assert!(rewrite
        .related_locations
        .as_ref()
        .is_some_and(|related| !related.is_empty()));
    let advice = rewrite
        .advice
        .as_ref()
        .expect("structured explanation advice")
        .iter()
        .map(|item| item.message.as_str())
        .collect::<Vec<_>>()
        .join("\n");
    assert!(advice.contains("rewrite.atomic_literal.elide.v1"));
    assert!(
        advice.contains("sha256:52d1a15ffb3becdde9e33f708539395e395eff752741283d90ff8bb1ccb64cc5")
    );
    assert!(
        advice.contains("sha256:5fe61a36f43a50b7ce5f6e2b13f0ac36ded8bda0e6255a66027bcf669a1d3532")
    );
    assert!(advice.contains("precondition.original_node_atomic"));
    assert_eq!(plan.decisions.len(), 1);
}

#[test]
fn explanation_rejects_cross_program_plan_reuse() {
    let semantic = parsed_program("(?>a)");
    let other = parsed_program("(?>b)");
    let target: TargetProfile = serde_json::from_str(ECMASCRIPT).expect("target profile");
    let (plan, _) = plan_and_explain(&semantic, &target);

    let error = explain_portability(&other, &plan).expect_err("cross-program reuse must fail");
    assert_eq!(
        error.code,
        PortabilityDiagnosticErrorCode::ProgramFingerprintMismatch
    );
}

#[test]
fn identical_requirement_evidence_is_coalesced_without_losing_its_count() {
    let semantic: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {
            "node_id": "node:portability-diagnostics.unicode-set",
            "kind": "character_set",
            "negated": false,
            "members": [
                { "kind": "literal", "value": "λ" },
                { "kind": "literal", "value": "Ж" }
            ]
        }
    }))
    .expect("semantic program");
    let target: TargetProfile = serde_json::from_str(ECMASCRIPT).expect("target profile");
    let (plan, diagnostics) = plan_and_explain(&semantic, &target);

    assert_eq!(plan.decisions.len(), 2);
    assert_eq!(diagnostics.len(), 1);
    assert!(diagnostics[0]
        .advice
        .as_ref()
        .expect("coalesced evidence advice")
        .iter()
        .any(|item| item.message.contains("2 canonical requirement occurrences")));
}

fn parsed_program(source: &str) -> SemanticProgram {
    let document: SourceDocument = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": "src:portability-diagnostics",
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": "strling.regex-compat",
            "dialect_version": "1.0.0"
        },
        "content": { "kind": "inline", "encoding": "utf-8", "text": source },
        "provenance": { "kind": "imported" }
    }))
    .expect("source document");
    parse(&document).expect("regex source must parse").program
}

fn plan_and_explain(
    input: &SemanticProgram,
    target: &TargetProfile,
) -> (
    strling_kernel::portability_planning::PortabilityPlan,
    Vec<strling_kernel::diagnostic::Diagnostic>,
) {
    let normalized = normalize(input).expect("canonical normalization");
    let foundational = analyze(&normalized).expect("foundational facts");
    let structural = analyze_structure(&normalized, &foundational).expect("structural facts");
    let evaluation = evaluate_capabilities(&normalized, &foundational, &structural, target)
        .expect("capability evaluation");
    let plan = plan_portability(&normalized, &foundational, &structural, target, &evaluation)
        .expect("portability plan");
    let diagnostics = explain_portability(&normalized, &plan).expect("portability explanations");
    (plan, diagnostics)
}
