#![no_main]

mod common;

use libfuzzer_sys::fuzz_target;
use serde_json::json;

fuzz_target!(|data: &[u8]| {
    let (selector, rest) = data.split_first().unwrap_or((&0, &[]));
    let noise = String::from_utf8_lossy(rest);
    let (request, expected) = match selector % 5 {
        0 => (
            serde_json::to_vec(&json!({
                "interop_protocol_version": format!("unsupported-{noise}"),
                "operation": "describe",
                "payload": {},
            }))
            .expect("serialize unsupported version"),
            "STRL-INTEROP-0004",
        ),
        1 => (
            common::request(&format!("unsupported-{noise}"), json!({})),
            "STRL-INTEROP-0005",
        ),
        2 => (
            serde_json::to_vec(&json!({
                "interop_protocol_version": "1.0.0",
                "operation": "describe",
                "payload": {},
                "unknown": common::arbitrary_value(rest),
            }))
            .expect("serialize unknown envelope field"),
            "STRL-INTEROP-0003",
        ),
        3 => (
            common::request(
                "describe",
                json!({"unknown": common::arbitrary_value(rest)}),
            ),
            "STRL-INTEROP-0007",
        ),
        _ => (
            serde_json::to_vec(&json!({
                "interop_protocol_version": "1.0.0",
                "operation": "describe",
            }))
            .expect("serialize missing payload"),
            "STRL-INTEROP-0003",
        ),
    };
    let response = common::assert_closed_response(&request);
    common::assert_error_code(&response, expected);
});
