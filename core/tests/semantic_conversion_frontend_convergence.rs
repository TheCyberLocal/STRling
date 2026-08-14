use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::ecmascript_lowering::lower_ecmascript;
use strling_kernel::ecmascript_serialization::serialize_ecmascript;
use strling_kernel::explanation::explain_semantics;
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::protocol::CompileInput;
use strling_kernel::regex_frontend;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::semantic_conversion::{
    convert_semantic_program, SemanticConversionDestination, SemanticConversionErrorCode,
    SemanticConversionOutput, SemanticConversionStatus,
};
use strling_kernel::semantic_frontend;
use strling_kernel::simply::{decode_simply_builder_request, replay_simply_builder_request};
use strling_kernel::source::SourceDocument;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{ArtifactPortabilityStatus, TargetArtifact, TargetProfile};

const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

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

fn source_document(
    frontend: &str,
    media_type: &str,
    source_id: &str,
    text: &str,
) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": source_id,
        "specification_version": "1.0-draft.1",
        "frontend": {"id": frontend, "dialect_version": "1.0.0"},
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": media_type,
            "text": text
        },
        "provenance": {"kind": "imported"}
    }))
    .expect("source document")
}

fn ecmascript_artifact(input: &SemanticProgram) -> TargetArtifact {
    let target: TargetProfile = serde_json::from_str(ECMASCRIPT).expect("ECMAScript profile");
    let foundational = analyze(input).expect("foundational analysis");
    let structural = analyze_structure(input, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(input, &foundational, &structural, &target)
        .expect("capability evaluation");
    let portability = plan_portability(input, &foundational, &structural, &target, &evaluation)
        .expect("portability planning");
    let lowering = lower_ecmascript(input, &target, &portability).expect("ECMAScript lowering");
    serialize_ecmascript(&lowering).expect("ECMAScript serialization")
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

#[test]
fn imported_regex_converges_through_both_generated_surfaces_and_target_artifacts() {
    let imported = regex_frontend::parse(&source_document(
        "strling.regex-compat",
        "text/strling-regex",
        "src:conversion.imported-regex",
        r"(?<word>a)\k<word>",
    ))
    .expect("regex frontend")
    .program;

    let semantic_result = convert_semantic_program(
        &imported,
        SemanticConversionDestination::SemanticStrling,
        None,
    )
    .expect("Semantic STRling conversion");
    assert_eq!(semantic_result.status, SemanticConversionStatus::Exact);
    let Some(SemanticConversionOutput::SemanticStrling { text, .. }) = semantic_result.output
    else {
        panic!("Semantic STRling output");
    };
    let semantic_reconstructed = semantic_frontend::parse(&source_document(
        "strling.semantic",
        "text/x-strling-semantic",
        "src:conversion.generated-semantic",
        &text,
    ))
    .expect("generated Semantic STRling frontend")
    .program;

    let simply_result = convert_semantic_program(
        &imported,
        SemanticConversionDestination::SimplyBuilder,
        None,
    )
    .expect("Simply conversion");
    assert_eq!(simply_result.status, SemanticConversionStatus::Exact);
    let Some(SemanticConversionOutput::SimplyBuilder { request, .. }) = simply_result.output else {
        panic!("Simply output");
    };
    let decoded = decode_simply_builder_request(
        &serde_json::to_string(&request).expect("generated Simply JSON"),
    )
    .expect("generated Simply decode");
    let CompileInput::Semantic { program } = replay_simply_builder_request(decoded)
        .expect("generated Simply replay")
        .input
    else {
        panic!("generated Simply semantic projection");
    };
    let simply_reconstructed = *program;

    let original_artifact = ecmascript_artifact(&imported);
    for reconstructed in [&semantic_reconstructed, &simply_reconstructed] {
        let artifact = ecmascript_artifact(reconstructed);
        assert_eq!(artifact.pattern, original_artifact.pattern);
        assert_eq!(artifact.engine_options, original_artifact.engine_options);
        assert_eq!(
            artifact.portability_status,
            ArtifactPortabilityStatus::Native
        );
        assert_eq!(
            artifact.portability_status,
            original_artifact.portability_status
        );
    }
    assert_eq!(original_artifact.pattern.text, r"(?<word>a)(?:\k<word>)");
    assert_eq!(original_artifact.pattern.flags, ["u"]);
}
