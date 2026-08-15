use serde_json::{json, Value};
use strling_interop::{execute_bytes, MAX_INTEROP_RESPONSE_BYTES};

const ERROR_CODES: [&str; 10] = [
    "STRL-INTEROP-0001",
    "STRL-INTEROP-0002",
    "STRL-INTEROP-0003",
    "STRL-INTEROP-0004",
    "STRL-INTEROP-0005",
    "STRL-INTEROP-0006",
    "STRL-INTEROP-0007",
    "STRL-INTEROP-0008",
    "STRL-INTEROP-0009",
    "STRL-INTEROP-0010",
];

pub fn assert_closed_response(request: &[u8]) -> Value {
    let first = execute_bytes(request);
    let second = execute_bytes(request);
    assert_eq!(
        first, second,
        "identical requests must be byte deterministic"
    );
    assert!(!first.is_empty(), "the boundary must emit one response");
    assert!(
        first.len() <= MAX_INTEROP_RESPONSE_BYTES,
        "the response must remain within the contract ceiling"
    );
    let response: Value = serde_json::from_slice(&first).expect("response must be valid JSON");
    assert_eq!(Some("1.0.0"), response["interop_protocol_version"].as_str());
    match response["status"].as_str() {
        Some("completed") => {
            assert!(response["operation"].as_str().is_some());
            assert!(!response["result"].is_null());
        }
        Some("error") => {
            let code = response["error"]["code"]
                .as_str()
                .expect("interop error code");
            assert!(ERROR_CODES.contains(&code));
            assert!(response["error"]["path"].as_str().is_some());
        }
        status => panic!("unexpected interop response status: {status:?}"),
    }
    response
}

pub fn request(operation: &str, payload: Value) -> Vec<u8> {
    serde_json::to_vec(&json!({
        "interop_protocol_version": "1.0.0",
        "operation": operation,
        "payload": payload,
    }))
    .expect("serialize fuzz request")
}

pub fn arbitrary_value(data: &[u8]) -> Value {
    serde_json::from_slice(data)
        .unwrap_or_else(|_| Value::String(String::from_utf8_lossy(data).into_owned()))
}

pub fn assert_error_code(response: &Value, expected: &str) {
    assert_eq!(Some("error"), response["status"].as_str());
    assert_eq!(Some(expected), response["error"]["code"].as_str());
}
