use std::collections::BTreeSet;

use serde_json::Value;
use strling_kernel::normalization::normalize;
use strling_kernel::protocol::CompileRequest;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::validation::{from_json, Validate};

const PROTOCOL_SCHEMA: &str = include_str!("../../spec/frontends/simply/1.0/protocol.schema.json");
const BUILDER_SCHEMA: &str =
    include_str!("../../spec/frontends/simply/1.0/builder-request.schema.json");
const CASE_SCHEMA: &str = include_str!("../../spec/frontends/simply/1.0/case.schema.json");
const PROTOCOL: &str = include_str!("../../spec/frontends/simply/1.0/protocol.json");
const POSITIVE: &str = include_str!("../../spec/frontends/simply/1.0/fixtures/positive.json");
const NEGATIVE: &str = include_str!("../../spec/frontends/simply/1.0/fixtures/negative.json");
const MANIFEST: &str = include_str!("../../spec/frontends/simply/1.0/fixtures/manifest.json");

#[test]
fn every_governed_builder_contract_file_is_bound_into_kernel_evidence() {
    for (name, document) in [
        ("protocol schema", PROTOCOL_SCHEMA),
        ("builder schema", BUILDER_SCHEMA),
        ("case schema", CASE_SCHEMA),
        ("protocol", PROTOCOL),
        ("positive cases", POSITIVE),
        ("negative cases", NEGATIVE),
        ("manifest", MANIFEST),
    ] {
        serde_json::from_str::<Value>(document)
            .unwrap_or_else(|error| panic!("{name} must be valid JSON: {error}"));
    }
}

#[test]
fn expected_builder_programs_are_canonical_and_requests_validate() {
    let suite: Value = serde_json::from_str(POSITIVE).expect("positive suite must decode");
    let cases = suite["cases"]
        .as_array()
        .expect("positive cases must be an array");
    assert_eq!(9, cases.len());

    for case in cases {
        let case_id = case["case_id"].as_str().expect("case identity");
        let expected_program = case["expected"]["semantic_program"].clone();
        let candidate: SemanticProgram = serde_json::from_value(expected_program.clone())
            .unwrap_or_else(|error| panic!("{case_id}: Semantic IR shape: {error}"));
        let normalized = normalize(&candidate)
            .unwrap_or_else(|errors| panic!("{case_id}: normalization failed: {errors}"));
        assert_eq!(
            candidate, normalized,
            "{case_id}: expected program is not canonical"
        );
        normalized
            .validate()
            .unwrap_or_else(|errors| panic!("{case_id}: semantic validation failed: {errors}"));

        let request_json = serde_json::to_string(&case["expected"]["compile_request"])
            .expect("request serialization");
        let request: CompileRequest = from_json(&request_json)
            .unwrap_or_else(|error| panic!("{case_id}: CompileRequest failed: {error}"));
        request
            .validate()
            .unwrap_or_else(|errors| panic!("{case_id}: request validation failed: {errors}"));
        let request_program = match request.input {
            strling_kernel::protocol::CompileInput::Semantic { program } => *program,
            strling_kernel::protocol::CompileInput::Source { .. } => {
                panic!("{case_id}: Simply must project semantic input")
            }
        };
        assert_eq!(
            candidate, request_program,
            "{case_id}: request input drifted"
        );
    }
}

#[test]
fn controlled_failures_cover_the_complete_stable_error_set() {
    let protocol: Value = serde_json::from_str(PROTOCOL).expect("protocol must decode");
    let expected: BTreeSet<_> = protocol["errors"]
        .as_array()
        .expect("protocol errors")
        .iter()
        .map(|entry| entry["code"].as_str().expect("error code"))
        .collect();
    let negative: Value = serde_json::from_str(NEGATIVE).expect("negative suite must decode");
    let actual: BTreeSet<_> = negative["cases"]
        .as_array()
        .expect("negative cases")
        .iter()
        .flat_map(|case| {
            case["expected"]["errors"]
                .as_array()
                .expect("expected errors")
                .iter()
        })
        .map(|entry| entry["code"].as_str().expect("error code"))
        .collect();
    assert_eq!(expected, actual);
    assert_eq!(12, expected.len());
}
