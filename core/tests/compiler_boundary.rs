use serde_json::{json, Value};
use strling_kernel::diagnostic::Severity;
use strling_kernel::protocol::{
    CompileOutcome, CompileRequest, RequestedOutput, SemanticResultStatus,
};
use strling_kernel::source::SpecificationVersion;
use strling_kernel::target::{TargetProfile, TargetProfileReference};
use strling_kernel::validation::{from_json, ContractError, Validate};
use strling_kernel::{compile, KernelCompileError};

const SOURCE_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/source-success.json");
const TARGET_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/target-artifact.json");
const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");

fn semantic_request(root: Value, outputs: Vec<&str>) -> CompileRequest {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": {
            "kind": "semantic",
            "program": {
                "contract_version": "1.0.0",
                "specification_version": "1.0-draft.1",
                "normalization": "canonical-v1",
                "case_matching": "sensitive",
                "root": root
            }
        },
        "requested_outputs": outputs,
        "compiler_options": {
            "partial_semantics": "forbid",
            "diagnostic_policy": { "minimum_severity": "hint" }
        }
    }))
    .expect("semantic request shape")
}

fn minimal_request() -> CompileRequest {
    semantic_request(
        json!({
            "node_id": "node:boundary.minimal",
            "kind": "literal",
            "text": "x"
        }),
        vec!["semantic"],
    )
}

#[test]
fn minimal_valid_request_uses_the_public_facade() {
    let result = compile(&minimal_request(), None).expect("minimal request compiles");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert_eq!(result.compiler.id.as_str(), "strling_kernel");
    assert_eq!(result.compiler.version.as_str(), "0.1.0");
    assert_eq!(
        result.semantic_result.expect("requested semantics").status,
        SemanticResultStatus::Complete
    );
    assert!(result.analysis.is_none());
    assert!(result.portability.is_none());
    assert!(result.artifact.is_none());
    assert!(result.diagnostics.is_empty());
}

#[test]
fn representative_semantic_request_returns_analysis_and_safety_diagnostics() {
    let request = semantic_request(
        json!({
            "node_id": "node:boundary.repeat",
            "kind": "repeat",
            "body": {
                "node_id": "node:boundary.empty",
                "kind": "empty"
            },
            "min": 0,
            "max": null,
            "mode": "greedy"
        }),
        vec!["semantic", "analysis"],
    );

    let result = compile(&request, None).expect("representative request compiles");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert!(result.semantic_result.is_some());
    assert_eq!(
        result
            .analysis
            .as_ref()
            .expect("requested analysis")
            .node_facts
            .len(),
        2
    );
    assert_eq!(result.diagnostics.len(), 1);
    assert_eq!(result.diagnostics[0].severity, Severity::Warning);
    result.validate().expect("facade result validates");
}

#[test]
fn source_less_analysis_request_remains_valid() {
    let request = semantic_request(
        json!({
            "node_id": "node:boundary.source-less",
            "kind": "empty"
        }),
        vec!["analysis"],
    );

    let result = compile(&request, None).expect("source-less request compiles");

    assert!(result.semantic_result.is_none());
    assert!(result.analysis.is_some());
    assert_eq!(result.outcome, CompileOutcome::Succeeded);
}

#[test]
fn malformed_typed_request_is_a_boundary_error() {
    let mut request = minimal_request();
    request.requested_outputs.clear();

    assert!(matches!(
        compile(&request, None),
        Err(KernelCompileError::InvalidRequest(_))
    ));
}

#[test]
fn unsupported_contract_version_is_rejected_before_the_facade() {
    let serialized = serde_json::to_string(&minimal_request()).expect("serialize request");
    let future = serialized.replace("1.0.0", "2.0.0");

    assert!(matches!(
        from_json::<CompileRequest>(&future),
        Err(ContractError::Deserialization(_))
    ));
}

#[test]
fn mismatched_target_profile_evidence_is_typed() {
    let request: CompileRequest = from_json(TARGET_REQUEST).expect("target request");
    let profile: TargetProfile = from_json(PCRE2_1042).expect("profile");

    let error = compile(&request, Some(&profile)).expect_err("profile must mismatch");
    let KernelCompileError::TargetProfileMismatch { expected, actual } = error else {
        panic!("unexpected error: {error}");
    };
    assert_ne!(expected, actual);
}

#[test]
fn missing_target_profile_evidence_is_typed() {
    let request: CompileRequest = from_json(TARGET_REQUEST).expect("target request");

    let error = compile(&request, None).expect_err("profile must be required");
    assert!(matches!(
        error,
        KernelCompileError::TargetProfileRequired { .. }
    ));
}

#[test]
fn unsupported_future_output_mode_is_malformed_contract_data() {
    let mut value = serde_json::to_value(minimal_request()).expect("request value");
    value["requested_outputs"] = json!(["future_output"]);
    let serialized = serde_json::to_string(&value).expect("serialize mutation");

    assert!(matches!(
        from_json::<CompileRequest>(&serialized),
        Err(ContractError::Deserialization(_))
    ));
}

#[test]
fn unsupported_specification_returns_a_structured_failed_result() {
    let mut request = minimal_request();
    let future = SpecificationVersion::try_from("1.1").expect("specification version");
    request.specification_version = future.clone();
    let strling_kernel::protocol::CompileInput::Semantic { program } = &mut request.input else {
        panic!("semantic input expected");
    };
    program.specification_version = future;

    let result = compile(&request, None).expect("unsupported spec is a compile result");

    assert_eq!(result.outcome, CompileOutcome::Failed);
    assert_eq!(result.diagnostics.len(), 1);
    assert_eq!(result.diagnostics[0].code.as_str(), "STRL-PROTOCOL-0004");
    assert!(result.semantic_result.is_none());
}

#[test]
fn source_frontend_is_explicitly_unsupported() {
    let request: CompileRequest = from_json(SOURCE_REQUEST).expect("source request");

    let result = compile(&request, None).expect("unsupported frontend is a result");

    assert_eq!(result.outcome, CompileOutcome::Failed);
    assert_eq!(result.diagnostics[0].code.as_str(), "STRL-PROTOCOL-0002");
    assert!(result.semantic_result.is_none());
}

#[test]
fn artifact_mode_projects_the_certified_target_output() {
    let request: CompileRequest = from_json(TARGET_REQUEST).expect("target request");
    let profile: TargetProfile = from_json(PCRE2_1043).expect("profile");
    assert_eq!(
        request.target_profile,
        Some(profile.reference().expect("profile reference"))
    );

    let result = compile(&request, Some(&profile)).expect("target artifact compiles");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert!(result.semantic_result.is_some());
    assert!(result.portability.is_some());
    assert!(result.artifact.is_some());
    assert!(!result
        .diagnostics
        .iter()
        .any(|item| item.code.as_str() == "STRL-PROTOCOL-0005"));
}

#[test]
fn repeated_invocation_is_equal_and_does_not_mutate_the_request() {
    let request = minimal_request();
    let original = request.clone();

    let first = compile(&request, None).expect("first compile");
    let second = compile(&request, None).expect("second compile");

    assert_eq!(first, second);
    assert_eq!(request, original);
}

#[test]
fn target_profile_reference_type_remains_the_request_authority() {
    let request: CompileRequest = from_json(TARGET_REQUEST).expect("target request");
    let reference: TargetProfileReference = request.target_profile.expect("reference");

    assert_eq!(reference.profile_id.as_str(), "profile:pcre2/10.43");
    assert!(request
        .requested_outputs
        .contains(&RequestedOutput::TargetArtifact));
}
