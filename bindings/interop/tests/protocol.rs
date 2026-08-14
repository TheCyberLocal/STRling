use std::sync::Arc;
use std::thread;

use serde_json::{json, Value};
use strling_interop::execute_bytes;

fn request(operation: &str, payload: Value) -> Vec<u8> {
    serde_json::to_vec(&json!({
        "interop_protocol_version": "1.0.0",
        "operation": operation,
        "payload": payload,
    }))
    .expect("serialize request")
}

fn execute(request: &[u8]) -> Value {
    serde_json::from_slice(&execute_bytes(request)).expect("valid response")
}

fn target_profile(version: &str) -> Value {
    let text = match version {
        "10.42" => include_str!("../../../spec/targets/profiles/pcre2-10.42.json"),
        "10.43" => include_str!("../../../spec/targets/profiles/pcre2-10.43.json"),
        _ => panic!("unknown profile"),
    };
    serde_json::from_str(text).expect("target profile fixture")
}

fn source_request(name: &str) -> Value {
    let text = match name {
        "success" => include_str!(
            "../../../spec/contracts/1.0/examples/compile-request/regex-compat-success.json"
        ),
        "failed" => include_str!(
            "../../../spec/contracts/1.0/examples/compile-request/regex-compat-malformed.json"
        ),
        _ => panic!("unknown fixture"),
    };
    serde_json::from_str(text).expect("compile request fixture")
}

#[test]
fn describe_returns_exact_governed_identity_deterministically() {
    let input = request("describe", json!({}));
    let first = execute_bytes(&input);
    let second = execute_bytes(&input);
    assert_eq!(first, second);
    let response: Value = serde_json::from_slice(&first).expect("describe response");
    assert_eq!("completed", response["status"]);
    assert_eq!("strling.interop", response["result"]["contract_id"]);
    assert_eq!("1.0.0", response["result"]["protocol_version"]);
}

#[test]
fn compile_preserves_success_and_failed_result_outcomes() {
    for (fixture, expected) in [("success", "succeeded"), ("failed", "failed")] {
        let input = request(
            "compile",
            json!({"compile_request": source_request(fixture)}),
        );
        let response = execute(&input);
        assert_eq!("completed", response["status"]);
        assert_eq!(expected, response["result"]["outcome"]);
    }
}

#[test]
fn profile_inspection_computes_the_exact_reference() {
    let profile = target_profile("10.42");
    let input = request("target_profile.inspect", json!({"target_profile": profile}));
    let first = execute_bytes(&input);
    assert_eq!(first, execute_bytes(&input));
    let response: Value = serde_json::from_slice(&first).expect("inspection response");
    assert_eq!("completed", response["status"]);
    assert_eq!(
        response["result"]["target_profile"]["profile_id"],
        response["result"]["profile_reference"]["profile_id"]
    );
    assert!(response["result"]["profile_reference"]["sha256"]
        .as_str()
        .is_some_and(|digest| digest.len() == 64
            && digest
                .chars()
                .all(|character| character.is_ascii_hexdigit())));
}

#[test]
fn target_aware_compile_requires_the_exact_supplied_profile() {
    let compile_request: Value = serde_json::from_str(include_str!(
        "../../../spec/contracts/1.0/examples/compile-request/target-artifact.json"
    ))
    .expect("target-aware request");
    let succeeded = execute(&request(
        "compile",
        json!({
            "compile_request": compile_request,
            "target_profile": target_profile("10.43"),
        }),
    ));
    assert_eq!("completed", succeeded["status"]);
    assert_eq!("succeeded", succeeded["result"]["outcome"]);

    let missing = execute(&request(
        "compile",
        json!({"compile_request": compile_request}),
    ));
    assert_eq!("STRL-INTEROP-0008", missing["error"]["code"]);

    let mismatched = execute(&request(
        "compile",
        json!({
            "compile_request": compile_request,
            "target_profile": target_profile("10.42"),
        }),
    ));
    assert_eq!("STRL-INTEROP-0008", mismatched["error"]["code"]);
}

#[test]
fn target_neutral_compile_rejects_an_unexpected_profile() {
    let response = execute(&request(
        "compile",
        json!({
            "compile_request": source_request("success"),
            "target_profile": target_profile("10.43"),
        }),
    ));
    assert_eq!("STRL-INTEROP-0008", response["error"]["code"]);
}

#[test]
fn simply_10_and_11_replay_through_the_canonical_builder() {
    let fixtures: Value = serde_json::from_str(include_str!(
        "../../../spec/frontends/simply/1.0/fixtures/positive.json"
    ))
    .expect("Simply 1.0 fixtures");
    let request_10 = fixtures["cases"][0]["request"].clone();
    let fixtures: Value = serde_json::from_str(include_str!(
        "../../../spec/frontends/simply/1.1/fixtures/positive.json"
    ))
    .expect("Simply 1.1 fixtures");
    let request_11 = fixtures["cases"][0]["request"].clone();

    for (builder_request, version) in [(request_10, "1.0.0"), (request_11, "1.1.0")] {
        let response = execute(&request(
            "simply.compile",
            json!({"builder_request": builder_request}),
        ));
        assert_eq!("completed", response["status"]);
        assert_eq!("success", response["result"]["status"]);
        assert_eq!(version, response["result"]["protocol_version"]);
    }
}

#[test]
fn simply_construction_failure_remains_a_completed_adapter_response() {
    let fixtures: Value = serde_json::from_str(include_str!(
        "../../../spec/frontends/simply/1.1/fixtures/negative.json"
    ))
    .expect("Simply negative fixtures");
    let response = execute(&request(
        "simply.compile",
        json!({"builder_request": fixtures["cases"][0]["request"]}),
    ));
    assert_eq!("completed", response["status"]);
    assert_eq!("failure", response["result"]["status"]);
    assert_eq!("STRL-SIMPLY-0010", response["result"]["errors"][0]["code"]);
}

#[test]
fn malformed_boundaries_have_closed_error_identities() {
    let cases: Vec<(Vec<u8>, &str)> = vec![
        (vec![0xff], "STRL-INTEROP-0001"),
        (b"{".to_vec(), "STRL-INTEROP-0002"),
        (b"[]".to_vec(), "STRL-INTEROP-0003"),
        (
            br#"{"interop_protocol_version":"9.0.0","operation":"describe","payload":{}}"#
                .to_vec(),
            "STRL-INTEROP-0004",
        ),
        (
            br#"{"interop_protocol_version":"1.0.0","operation":"unknown","payload":{}}"#
                .to_vec(),
            "STRL-INTEROP-0005",
        ),
        (
            br#"{"interop_protocol_version":"1.0.0","operation":"describe","payload":{"extra":true}}"#
                .to_vec(),
            "STRL-INTEROP-0007",
        ),
    ];
    for (input, code) in cases {
        assert_eq!(code, execute(&input)["error"]["code"]);
    }
}

#[test]
fn request_limit_is_checked_before_json_parsing() {
    let oversized = vec![b' '; strling_interop::MAX_INTEROP_REQUEST_BYTES + 1];
    assert_eq!("STRL-INTEROP-0006", execute(&oversized)["error"]["code"]);
}

#[test]
fn concurrent_valid_and_invalid_calls_are_isolated_and_deterministic() {
    let valid = Arc::new(request("describe", json!({})));
    let expected = execute_bytes(&valid);
    let handles: Vec<_> = (0..32)
        .map(|index| {
            let valid = Arc::clone(&valid);
            thread::spawn(move || {
                if index % 5 == 0 {
                    let invalid = execute_bytes(b"{");
                    let value: Value = serde_json::from_slice(&invalid).expect("error response");
                    assert_eq!("STRL-INTEROP-0002", value["error"]["code"]);
                }
                execute_bytes(&valid)
            })
        })
        .collect();
    for handle in handles {
        assert_eq!(expected, handle.join().expect("thread completes"));
    }
}
