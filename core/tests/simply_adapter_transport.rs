use std::io::Write;
use std::process::{Command, Stdio};

use serde_json::Value;
use strling_kernel::compile;
use strling_kernel::protocol::CompileRequest;
use strling_kernel::simply::{
    decode_simply_builder_request, replay_simply_builder_request, SimplyBuilderRequestDecodeError,
};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::from_json;

const POSITIVE: &str = include_str!("../../spec/frontends/simply/1.0/fixtures/positive.json");
const NEGATIVE: &str = include_str!("../../spec/frontends/simply/1.0/fixtures/negative.json");
const POSITIVE_1_1: &str = include_str!("../../spec/frontends/simply/1.1/fixtures/positive.json");
const NEGATIVE_1_1: &str = include_str!("../../spec/frontends/simply/1.1/fixtures/negative.json");
const RESPONSE_SCHEMA: &str =
    include_str!("../../spec/frontends/simply/1.0/adapter-response.schema.json");
const RESPONSE_SCHEMA_1_1: &str =
    include_str!("../../spec/frontends/simply/1.1/adapter-response.schema.json");
const BUILDER_SCHEMA_1_1: &str =
    include_str!("../../spec/frontends/simply/1.1/builder-request.schema.json");
const CASE_SCHEMA_1_1: &str = include_str!("../../spec/frontends/simply/1.1/case.schema.json");
const MANIFEST_1_1: &str = include_str!("../../spec/frontends/simply/1.1/fixtures/manifest.json");
const PROTOCOL_1_1: &str = include_str!("../../spec/frontends/simply/1.1/protocol.json");
const PROTOCOL_SCHEMA_1_1: &str =
    include_str!("../../spec/frontends/simply/1.1/protocol.schema.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");

fn cases(document: &str) -> Vec<Value> {
    serde_json::from_str::<Value>(document).expect("suite JSON")["cases"]
        .as_array()
        .expect("cases")
        .clone()
}

#[test]
fn adapter_response_schema_is_bound_into_kernel_transport_evidence() {
    let schema: Value =
        serde_json::from_str(RESPONSE_SCHEMA).expect("adapter response schema must decode");
    assert_eq!(
        "https://strling.dev/frontends/simply/1.0/adapter-response.schema.json",
        schema["$id"]
    );
    let schema: Value =
        serde_json::from_str(RESPONSE_SCHEMA_1_1).expect("1.1 adapter response schema must decode");
    assert_eq!(
        "https://strling.dev/frontends/simply/1.1/adapter-response.schema.json",
        schema["$id"]
    );
    for (name, document) in [
        ("builder schema", BUILDER_SCHEMA_1_1),
        ("case schema", CASE_SCHEMA_1_1),
        ("manifest", MANIFEST_1_1),
        ("protocol", PROTOCOL_1_1),
        ("protocol schema", PROTOCOL_SCHEMA_1_1),
    ] {
        serde_json::from_str::<Value>(document)
            .unwrap_or_else(|error| panic!("Simply 1.1 {name} must decode: {error}"));
    }
}

#[test]
fn every_positive_builder_request_replays_to_the_exact_canonical_request() {
    for case in cases(POSITIVE) {
        let case_id = case["case_id"].as_str().expect("case id");
        let request_json = serde_json::to_string(&case["request"]).expect("request serialization");
        let decoded = decode_simply_builder_request(&request_json)
            .unwrap_or_else(|error| panic!("{case_id}: decode failed: {error}"));
        assert_eq!(
            case["request"],
            serde_json::to_value(&decoded).expect("decoded serialization"),
            "{case_id}: stable BuilderRequest serialization drifted"
        );
        let projected = replay_simply_builder_request(decoded)
            .unwrap_or_else(|errors| panic!("{case_id}: replay failed: {errors}"));
        assert_eq!(
            case["expected"]["compile_request"],
            serde_json::to_value(projected).expect("CompileRequest serialization"),
            "{case_id}: canonical request drifted"
        );
    }
}

#[test]
fn every_supported_case_matches_direct_compile_results() {
    let profile: TargetProfile = serde_json::from_str(PCRE2_1043).expect("PCRE2 10.43 profile");
    for case in cases(POSITIVE) {
        let case_id = case["case_id"].as_str().expect("case id");
        let request_json = serde_json::to_string(&case["request"]).expect("request serialization");
        let adapter_request = replay_simply_builder_request(
            decode_simply_builder_request(&request_json).expect("adapter decode"),
        )
        .unwrap_or_else(|errors| panic!("{case_id}: adapter replay: {errors}"));
        let direct_json = serde_json::to_string(&case["expected"]["compile_request"])
            .expect("direct serialization");
        let direct_request: CompileRequest = from_json(&direct_json)
            .unwrap_or_else(|error| panic!("{case_id}: direct request: {error}"));
        assert_eq!(direct_request, adapter_request, "{case_id}: request");
        let target = if direct_request.target_profile.is_some() {
            Some(&profile)
        } else {
            None
        };
        let direct_result = compile(&direct_request, target)
            .unwrap_or_else(|error| panic!("{case_id}: direct compile: {error}"));
        let adapter_result = compile(&adapter_request, target)
            .unwrap_or_else(|error| panic!("{case_id}: adapter compile: {error}"));
        assert_eq!(
            serde_json::to_value(direct_result).expect("direct result"),
            serde_json::to_value(adapter_result).expect("adapter result"),
            "{case_id}: CompileResult"
        );
    }
}

#[test]
fn every_negative_request_preserves_its_stable_error_identity_and_path() {
    for case in cases(NEGATIVE) {
        let case_id = case["case_id"].as_str().expect("case id");
        let request_json = serde_json::to_string(&case["request"]).expect("request serialization");
        let errors = match decode_simply_builder_request(&request_json) {
            Ok(decoded) => replay_simply_builder_request(decoded)
                .expect_err("negative request must fail during replay"),
            Err(SimplyBuilderRequestDecodeError::Construction(errors)) => errors,
            Err(SimplyBuilderRequestDecodeError::Malformed(message)) => {
                panic!("{case_id}: governed JSON must not be malformed: {message}")
            }
        };
        assert_eq!(
            case["expected"]["errors"],
            serde_json::to_value(errors.errors).expect("error serialization"),
            "{case_id}: stable error drifted"
        );
    }
}

#[test]
fn cli_emits_success_and_failure_adapter_envelopes() {
    let positive = &cases(POSITIVE)[0];
    let (positive_status, positive_stdout, positive_stderr) =
        run_cli(&serde_json::to_string(&positive["request"]).unwrap());
    assert_eq!(Some(0), positive_status, "{positive_stderr}");
    let response: Value = serde_json::from_slice(&positive_stdout).expect("success response");
    assert_eq!("success", response["status"]);
    assert_eq!("1.0.0", response["protocol_version"]);
    assert_eq!(
        positive["expected"]["compile_request"],
        response["compile_request"]
    );
    assert_eq!("succeeded", response["compile_result"]["outcome"]);

    let negative = cases(NEGATIVE)
        .into_iter()
        .find(|case| case["case_id"] == "finite-maximum-below-minimum")
        .expect("bounds case");
    let (negative_status, negative_stdout, negative_stderr) =
        run_cli(&serde_json::to_string(&negative["request"]).unwrap());
    assert_eq!(Some(2), negative_status, "{negative_stderr}");
    let response: Value = serde_json::from_slice(&negative_stdout).expect("failure response");
    assert_eq!("failure", response["status"]);
    assert_eq!(negative["expected"]["errors"], response["errors"]);

    let positive = &cases(POSITIVE_1_1)[0];
    let (positive_status, positive_stdout, positive_stderr) =
        run_cli(&serde_json::to_string(&positive["request"]).unwrap());
    assert_eq!(Some(0), positive_status, "{positive_stderr}");
    let response: Value = serde_json::from_slice(&positive_stdout).expect("1.1 success response");
    assert_eq!("success", response["status"]);
    assert_eq!("1.1.0", response["protocol_version"]);

    let negative = &cases(NEGATIVE_1_1)[0];
    let (negative_status, negative_stdout, negative_stderr) =
        run_cli(&serde_json::to_string(&negative["request"]).unwrap());
    assert_eq!(Some(2), negative_status, "{negative_stderr}");
    let response: Value = serde_json::from_slice(&negative_stdout).expect("1.1 failure response");
    assert_eq!("failure", response["status"]);
    assert_eq!("1.1.0", response["protocol_version"]);
    assert_eq!(negative["expected"]["errors"], response["errors"]);
}

#[test]
fn malformed_json_stays_a_transport_error() {
    let (status, stdout, stderr) = run_cli("{");
    assert_eq!(Some(64), status);
    assert!(stdout.is_empty());
    assert!(stderr.contains("invalid Simply builder request"));
}

fn run_cli(input: &str) -> (Option<i32>, Vec<u8>, String) {
    let mut child = Command::new(env!("CARGO_BIN_EXE_strling-kernel"))
        .arg("--simply")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn strling-kernel");
    child
        .stdin
        .as_mut()
        .expect("stdin")
        .write_all(input.as_bytes())
        .expect("write request");
    let output = child.wait_with_output().expect("wait for strling-kernel");
    (
        output.status.code(),
        output.stdout,
        String::from_utf8(output.stderr).expect("UTF-8 stderr"),
    )
}
