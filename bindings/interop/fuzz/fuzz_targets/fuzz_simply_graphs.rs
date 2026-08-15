#![no_main]

mod common;

use libfuzzer_sys::fuzz_target;
use serde_json::{json, Value};

fuzz_target!(|data: &[u8]| {
    let (selector, rest) = data.split_first().unwrap_or((&0, &[]));
    let fixtures: Value = serde_json::from_str(include_str!(
        "../../../../spec/frontends/simply/1.1/fixtures/positive.json"
    ))
    .expect("canonical Simply fuzz seed");
    let cases = fixtures["cases"]
        .as_array()
        .expect("canonical Simply cases");
    let mut builder_request = cases[usize::from(*selector) % cases.len()]["request"].clone();
    match selector % 6 {
        0 => {}
        1 => {
            builder_request["identity_namespace"] =
                Value::String(String::from_utf8_lossy(rest).into_owned());
        }
        2 => {
            builder_request["root_step_id"] =
                Value::String(String::from_utf8_lossy(rest).into_owned());
        }
        3 => {
            builder_request["steps"][0]["operation"] =
                Value::String(format!("fuzz-{}", String::from_utf8_lossy(rest)));
        }
        4 => {
            builder_request["steps"][0]["arguments"] = common::arbitrary_value(rest);
        }
        _ => builder_request = common::arbitrary_value(rest),
    }
    let request = common::request(
        "simply.compile",
        json!({"builder_request": builder_request}),
    );
    let response = common::assert_closed_response(&request);
    match response["status"].as_str() {
        Some("error") => {
            assert!(matches!(
                response["error"]["code"].as_str(),
                Some("STRL-INTEROP-0007" | "STRL-INTEROP-0008")
            ));
        }
        Some("completed") => {
            assert_eq!(Some("simply.compile"), response["operation"].as_str());
            assert!(matches!(
                response["result"]["status"].as_str(),
                Some("success" | "failure")
            ));
            assert!(matches!(
                response["result"]["protocol_version"].as_str(),
                Some("1.0.0" | "1.1.0")
            ));
        }
        _ => unreachable!("closed response helper validates status"),
    }
});
