use std::convert::TryFrom;

use serde_json::{json, Value};
use strling_kernel::diagnostic::{Diagnostic, Severity};
use strling_kernel::protocol::{
    validate_exchange, validate_exchange_with_profiles, AnalysisResult, CompileOutcome,
    CompileRequest, CompileResult, SemanticResultStatus,
};
use strling_kernel::source::{FrontendId, NodeId};
use strling_kernel::target::{PortabilityPlan, TargetArtifact, TargetProfile, TargetProfileSet};
use strling_kernel::validation::{from_json, to_json, ContractError, ValidationCode};

const DIAGNOSTIC: &str =
    include_str!("../../spec/contracts/1.0/examples/diagnostic/parser-error.json");
const ANALYSIS: &str = include_str!("../../spec/contracts/1.0/examples/analysis/basic-facts.json");

const REQUESTS: &[(&str, &str)] = &[
    (
        "source success",
        include_str!("../../spec/contracts/1.0/examples/compile-request/source-success.json"),
    ),
    (
        "semantic input",
        include_str!("../../spec/contracts/1.0/examples/compile-request/semantic-input.json"),
    ),
    (
        "partial failure",
        include_str!("../../spec/contracts/1.0/examples/compile-request/partial-failure.json"),
    ),
    (
        "unsupported frontend",
        include_str!("../../spec/contracts/1.0/examples/compile-request/unsupported-frontend.json"),
    ),
    (
        "target artifact",
        include_str!("../../spec/contracts/1.0/examples/compile-request/target-artifact.json"),
    ),
];

const RESULTS: &[(&str, &str)] = &[
    (
        "success",
        include_str!("../../spec/contracts/1.0/examples/compile-result/success.json"),
    ),
    (
        "multiple diagnostics",
        include_str!("../../spec/contracts/1.0/examples/compile-result/multiple-diagnostics.json"),
    ),
    (
        "partial failure",
        include_str!("../../spec/contracts/1.0/examples/compile-result/partial-failure.json"),
    ),
    (
        "unsupported frontend",
        include_str!("../../spec/contracts/1.0/examples/compile-result/unsupported-frontend.json"),
    ),
    (
        "target artifact",
        include_str!("../../spec/contracts/1.0/examples/compile-result/target-artifact.json"),
    ),
];

fn profiles() -> TargetProfileSet {
    let profiles: Vec<TargetProfile> = [
        include_str!("../../spec/targets/profiles/pcre2-10.42.json"),
        include_str!("../../spec/targets/profiles/pcre2-10.43.json"),
        include_str!("../../spec/targets/profiles/ecmascript-2024.json"),
        include_str!("../../spec/targets/profiles/python-re-3.11.json"),
    ]
    .iter()
    .map(|fixture| from_json(fixture).expect("authored profile"))
    .collect();
    TargetProfileSet::new(profiles).expect("profile set")
}

#[test]
fn canonical_diagnostic_and_analysis_fixtures_validate() {
    let diagnostic: Diagnostic = from_json(DIAGNOSTIC).expect("diagnostic validates");
    assert_eq!(diagnostic.code.as_str(), "STRL-PARSE-0001");
    assert_eq!(diagnostic.severity, Severity::Error);
    let analysis: AnalysisResult = from_json(ANALYSIS).expect("analysis validates");
    assert_eq!(analysis.node_facts.len(), 1);
}

#[test]
fn every_compile_request_fixture_validates() {
    for (description, fixture) in REQUESTS {
        from_json::<CompileRequest>(fixture)
            .unwrap_or_else(|error| panic!("{description} request failed: {error}"));
    }
}

#[test]
fn every_compile_result_fixture_validates() {
    for (description, fixture) in RESULTS {
        from_json::<CompileResult>(fixture)
            .unwrap_or_else(|error| panic!("{description} result failed: {error}"));
    }
}

#[test]
fn result_states_are_structured_without_prose_identity() {
    let success: CompileResult = from_json(RESULTS[0].1).expect("success validates");
    assert_eq!(success.outcome, CompileOutcome::Succeeded);
    assert_eq!(
        success.semantic_result.expect("semantic result").status,
        SemanticResultStatus::Complete
    );
    let failure: CompileResult = from_json(RESULTS[3].1).expect("failure validates");
    assert_eq!(failure.outcome, CompileOutcome::Failed);
    assert!(failure.diagnostics.iter().any(Diagnostic::is_error));
}

#[test]
fn canonical_request_result_exchanges_validate() {
    let supported = [
        FrontendId::try_from("semantic_strling").expect("frontend"),
        FrontendId::try_from("regex_frontend").expect("frontend"),
    ];
    for (request_index, result_index) in [(0, 0), (2, 2), (3, 3), (4, 4)] {
        let request: CompileRequest = from_json(REQUESTS[request_index].1).expect("request");
        let result: CompileResult = from_json(RESULTS[result_index].1).expect("result");
        validate_exchange(&request, &result, &supported).unwrap_or_else(|errors| {
            panic!(
                "exchange {} failed with {:?}",
                REQUESTS[request_index].0, errors.errors
            )
        });
    }
}

#[test]
fn target_exchange_resolves_immutable_profile_and_artifact_options() {
    let request: CompileRequest = from_json(REQUESTS[4].1).expect("request");
    let result: CompileResult = from_json(RESULTS[4].1).expect("result");
    let supported = [
        FrontendId::try_from("semantic_strling").expect("frontend"),
        FrontendId::try_from("regex_frontend").expect("frontend"),
    ];
    validate_exchange_with_profiles(&request, &result, &supported, &profiles())
        .expect("profile-aware exchange");
}

#[test]
fn cross_phase_node_references_must_resolve_to_semantic_ir() {
    let request: CompileRequest = from_json(REQUESTS[4].1).expect("request");
    let mut result: CompileResult = from_json(RESULTS[4].1).expect("result");
    result.artifact.as_mut().expect("artifact").source_map[0].node_ids[0] =
        NodeId::try_from("node:not.declared").expect("node identity");
    let supported = [
        FrontendId::try_from("semantic_strling").expect("frontend"),
        FrontendId::try_from("regex_frontend").expect("frontend"),
    ];
    let errors = validate_exchange(&request, &result, &supported)
        .expect_err("undeclared artifact node must fail");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::UnresolvedReference));

    let request: CompileRequest = from_json(REQUESTS[0].1).expect("request");
    let mut result: CompileResult = from_json(RESULTS[0].1).expect("result");
    result.analysis.as_mut().expect("analysis").node_facts[0].node_id =
        NodeId::try_from("node:not.declared").expect("node identity");
    assert!(validate_exchange(&request, &result, &supported).is_err());
}

#[test]
fn controlled_invalid_protocol_objects_are_rejected() {
    let invalid_requests = [
        include_str!("../../spec/contracts/1.0/invalid/compile-request/mixed-input.json"),
        include_str!(
            "../../spec/contracts/1.0/invalid/compile-request/artifact-without-profile.json"
        ),
    ];
    for fixture in invalid_requests {
        assert!(from_json::<CompileRequest>(fixture).is_err());
    }

    let invalid_results = [
        include_str!("../../spec/contracts/1.0/invalid/compile-result/success-with-error.json"),
        include_str!("../../spec/contracts/1.0/invalid/compile-result/failed-without-error.json"),
        include_str!("../../spec/contracts/1.0/invalid/compile-result/partial-with-analysis.json"),
        include_str!(
            "../../spec/contracts/1.0/invalid/compile-result/diagnostics-out-of-order.json"
        ),
    ];
    for fixture in invalid_results {
        assert!(from_json::<CompileResult>(fixture).is_err());
    }
}

#[test]
fn failed_result_integrity_mutations_fail_closed() {
    let mut missing_payload: Value = serde_json::from_str(RESULTS[3].1).expect("failed result");
    missing_payload
        .as_object_mut()
        .expect("result object")
        .remove("diagnostics");
    assert!(from_json::<CompileResult>(
        &serde_json::to_string(&missing_payload).expect("mutation JSON")
    )
    .is_err());

    let mut malformed: Value = serde_json::from_str(RESULTS[3].1).expect("failed result");
    malformed["diagnostics"][0]["message"] = Value::String(String::new());
    assert!(
        from_json::<CompileResult>(&serde_json::to_string(&malformed).expect("mutation JSON"))
            .is_err()
    );

    let mut contradictory: Value = serde_json::from_str(RESULTS[4].1).expect("artifact result");
    contradictory["outcome"] = json!("failed");
    contradictory["diagnostics"] =
        json!([serde_json::from_str::<Value>(DIAGNOSTIC).expect("canonical error diagnostic")]);
    assert!(from_json::<CompileResult>(
        &serde_json::to_string(&contradictory).expect("mutation JSON")
    )
    .is_err());
}

#[test]
fn diagnostic_location_and_artifact_envelope_negatives_are_rejected() {
    let diagnostic =
        include_str!("../../spec/contracts/1.0/invalid/diagnostic/reversed-location.json");
    let error = from_json::<Diagnostic>(diagnostic).expect_err("reversed span must fail");
    assert!(matches!(error, ContractError::Validation(_)));

    let invalid_artifacts = [
        include_str!("../../spec/contracts/1.0/invalid/target-artifact/options-out-of-order.json"),
        include_str!(
            "../../spec/contracts/1.0/invalid/target-artifact/reversed-generated-span.json"
        ),
        include_str!("../../spec/contracts/1.0/invalid/target-artifact/unsupported-status.json"),
    ];
    for fixture in invalid_artifacts {
        assert!(from_json::<TargetArtifact>(fixture).is_err());
    }
}

#[test]
fn portability_examples_use_only_the_certified_vocabulary() {
    for fixture in [
        include_str!("../../spec/contracts/1.0/examples/portability/pcre2-native.json"),
        include_str!("../../spec/contracts/1.0/examples/portability/ecmascript-rewrite.json"),
        include_str!("../../spec/contracts/1.0/examples/portability/python-unsupported.json"),
    ] {
        from_json::<PortabilityPlan>(fixture).expect("portability fixture validates");
    }
}

#[test]
fn undeclared_diagnostic_source_fails_exchange_validation() {
    let request: CompileRequest = from_json(REQUESTS[3].1).expect("request");
    let mut result: CompileResult = from_json(RESULTS[3].1).expect("result");
    let location: strling_kernel::source::SourceSpan = serde_json::from_str(
        r#"{"source_id":"src:not-declared","coordinate_system":"utf8-bytes","start":0,"end":1}"#,
    )
    .expect("span shape");
    result.diagnostics[0].primary_location = Some(location);
    let supported = [
        FrontendId::try_from("semantic_strling").expect("frontend"),
        FrontendId::try_from("regex_frontend").expect("frontend"),
    ];
    let errors =
        validate_exchange(&request, &result, &supported).expect_err("source is undeclared");
    assert!(errors
        .errors
        .iter()
        .any(|error| error.code == ValidationCode::UnresolvedReference));
}

#[test]
fn protocol_round_trips_are_structurally_stable() {
    for (_, fixture) in REQUESTS {
        let model: CompileRequest = from_json(fixture).expect("request validates");
        let first = to_json(&model).expect("request serializes");
        let second = to_json(&model).expect("request serializes deterministically");
        assert_eq!(first, second);
        assert_eq!(
            serde_json::from_str::<Value>(fixture).expect("fixture JSON"),
            serde_json::from_str::<Value>(&first).expect("serialized JSON")
        );
    }
    for (_, fixture) in RESULTS {
        let model: CompileResult = from_json(fixture).expect("result validates");
        let first = to_json(&model).expect("result serializes");
        assert_eq!(first, to_json(&model).expect("stable result serialization"));
        assert_eq!(
            serde_json::from_str::<Value>(fixture).expect("fixture JSON"),
            serde_json::from_str::<Value>(&first).expect("serialized JSON")
        );
    }
}

#[test]
fn optional_protocol_sections_reject_explicit_null() {
    let invalid = REQUESTS[0].1.replace(
        "\"requested_outputs\":",
        "\"target_profile\": null, \"requested_outputs\":",
    );
    assert!(matches!(
        from_json::<CompileRequest>(&invalid),
        Err(ContractError::Deserialization(_))
    ));
}
