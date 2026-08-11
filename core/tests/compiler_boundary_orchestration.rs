use serde_json::{json, Value};
use strling_kernel::compile;
use strling_kernel::protocol::{CompileOutcome, CompileRequest};
use strling_kernel::target::{PortabilityStatus, TargetProfile};
use strling_kernel::validation::{from_json, Validate};

const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const ECMASCRIPT_2024: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PYTHON_RE_311: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");

fn targeted_request(root: Value, outputs: Vec<&str>, profile: &TargetProfile) -> CompileRequest {
    let mut request: CompileRequest = serde_json::from_value(json!({
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
    .expect("semantic request shape");
    request.target_profile = Some(profile.reference().expect("profile reference"));
    request
}

#[test]
fn portability_request_traverses_the_canonical_target_aware_pipeline() {
    let profile: TargetProfile = from_json(PCRE2_1042).expect("profile");
    let request = targeted_request(
        json!({
            "node_id": "node:boundary.portable",
            "kind": "literal",
            "text": "portable"
        }),
        vec!["portability"],
        &profile,
    );

    let result = compile(&request, Some(&profile)).expect("portability compiles");
    let portability = result.portability.as_ref().expect("requested portability");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert_eq!(portability.status, PortabilityStatus::Native);
    assert!(portability.decisions.is_empty());
    assert!(result.semantic_result.is_none());
    assert!(result.analysis.is_none());
    assert!(result.artifact.is_none());
    result.validate().expect("result validates");
}

#[test]
fn certified_rewrite_is_projected_without_applying_or_emitting_it() {
    let profile: TargetProfile = from_json(ECMASCRIPT_2024).expect("profile");
    let request = targeted_request(
        json!({
            "node_id": "node:boundary.atomic",
            "kind": "atomic",
            "body": {
                "node_id": "node:boundary.atomic.body",
                "kind": "literal",
                "text": "x"
            }
        }),
        vec!["semantic", "portability"],
        &profile,
    );

    let result = compile(&request, Some(&profile)).expect("rewrite plans");
    let portability = result.portability.as_ref().expect("portability");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert_eq!(portability.status, PortabilityStatus::EquivalentRewrite);
    assert_eq!(portability.decisions.len(), 1);
    assert_eq!(
        portability.decisions[0].requirement_id.as_str(),
        "requirement:semantic.0000000000"
    );
    assert_eq!(
        portability.decisions[0].reason_code.as_str(),
        "literal_atomicity_redundant"
    );
    assert!(result.semantic_result.is_some());
    assert!(result.artifact.is_none());
    result.validate().expect("projected result validates");
}

#[test]
fn unsupported_target_capability_is_a_final_portability_result() {
    let profile: TargetProfile = from_json(PYTHON_RE_311).expect("profile");
    let request = targeted_request(
        json!({
            "node_id": "node:boundary.lookbehind",
            "kind": "lookaround",
            "direction": "behind",
            "polarity": "positive",
            "body": {
                "node_id": "node:boundary.lookbehind.body",
                "kind": "alternation",
                "branches": [
                    {
                        "node_id": "node:boundary.lookbehind.short",
                        "kind": "literal",
                        "text": "x"
                    },
                    {
                        "node_id": "node:boundary.lookbehind.long",
                        "kind": "literal",
                        "text": "yyy"
                    }
                ]
            }
        }),
        vec!["portability"],
        &profile,
    );

    let result = compile(&request, Some(&profile)).expect("unsupported is evidence");
    let portability = result.portability.as_ref().expect("portability");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert_eq!(portability.status, PortabilityStatus::Unsupported);
    assert_eq!(portability.decisions.len(), 1);
    assert_eq!(
        portability.decisions[0].reason_code.as_str(),
        "profile_capability_unavailable"
    );
    assert!(result.artifact.is_none());
    result.validate().expect("result validates");
}

#[test]
fn incomplete_profile_evidence_fails_without_partial_portability() {
    let mut profile: TargetProfile = from_json(ECMASCRIPT_2024).expect("profile");
    profile
        .capabilities
        .retain(|capability| capability.capability_id.as_str() != "groups.atomic");
    let request = targeted_request(
        json!({
            "node_id": "node:boundary.incomplete",
            "kind": "atomic",
            "body": {
                "node_id": "node:boundary.incomplete.body",
                "kind": "literal",
                "text": "x"
            }
        }),
        vec!["portability"],
        &profile,
    );

    let result = compile(&request, Some(&profile)).expect("incomplete is a result");

    assert_eq!(result.outcome, CompileOutcome::Failed);
    assert!(result.portability.is_none());
    assert!(result
        .diagnostics
        .iter()
        .any(|item| item.code.as_str() == "STRL-PORTABILITY-0001"));
    result.validate().expect("failed result validates");
}

#[test]
fn target_neutral_outputs_do_not_require_or_run_target_evidence() {
    let profile: TargetProfile = from_json(PCRE2_1042).expect("profile");
    let request = targeted_request(
        json!({
            "node_id": "node:boundary.neutral",
            "kind": "literal",
            "text": "x"
        }),
        vec!["semantic"],
        &profile,
    );

    let result = compile(&request, None).expect("target-neutral compile");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert!(result.semantic_result.is_some());
    assert!(result.portability.is_none());
}
