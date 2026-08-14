use std::ptr;

use serde_json::{json, Value};
use strling_interop::{
    execute_bytes, strling_interop_execute_v1, strling_interop_owned_bytes_free_v1,
    StrlingInteropOwnedBytesV1, MAX_INTEROP_RESPONSE_BYTES,
    STRLING_INTEROP_STATUS_RESPONSE_WRITTEN,
};

fn next(state: &mut u64) -> u8 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    (*state >> 24) as u8
}

#[test]
fn bounded_arbitrary_bytes_never_panic_and_are_byte_deterministic() {
    let mut state = 0x9e37_79b9_7f4a_7c15;
    for length in (0..=512).chain([1023, 1024, 4095, 4096]) {
        let input: Vec<_> = (0..length).map(|_| next(&mut state)).collect();
        let first = execute_bytes(&input);
        let second = execute_bytes(&input);
        assert_eq!(first, second);
        assert!(!first.is_empty());
        assert!(first.len() <= MAX_INTEROP_RESPONSE_BYTES);
        let response: Value = serde_json::from_slice(&first).expect("one JSON response");
        assert!(matches!(
            response["status"].as_str(),
            Some("completed" | "error")
        ));
    }
}

#[test]
fn structured_envelope_mutations_keep_closed_dispositions() {
    let mutations = [
        json!({}),
        json!({"interop_protocol_version":"9.0.0","operation":"describe","payload":{}}),
        json!({"interop_protocol_version":"1.0.0","operation":"unknown","payload":{}}),
        json!({"interop_protocol_version":"1.0.0","operation":"describe","payload":{},"extra":true}),
        json!({"interop_protocol_version":"1.0.0","operation":"describe","payload":{"extra":true}}),
    ];
    let expected = [
        "STRL-INTEROP-0003",
        "STRL-INTEROP-0004",
        "STRL-INTEROP-0005",
        "STRL-INTEROP-0003",
        "STRL-INTEROP-0007",
    ];
    for (mutation, expected) in mutations.into_iter().zip(expected) {
        let response: Value = serde_json::from_slice(&execute_bytes(
            &serde_json::to_vec(&mutation).expect("serialize mutation"),
        ))
        .expect("error response");
        assert_eq!(expected, response["error"]["code"]);
    }
}

#[test]
fn repeated_native_execute_free_sequences_preserve_zeroed_ownership() {
    let request = serde_json::to_vec(&json!({
        "interop_protocol_version": "1.0.0",
        "operation": "describe",
        "payload": {},
    }))
    .expect("serialize request");
    for _ in 0..256 {
        let mut output = StrlingInteropOwnedBytesV1::default();
        assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
            strling_interop_execute_v1(request.as_ptr(), request.len(), &mut output)
        });
        assert!(!output.data.is_null());
        assert!(output.len > 0);
        assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
            strling_interop_owned_bytes_free_v1(&mut output)
        });
        assert!(output.data.is_null());
        assert_eq!(0, output.len);
        assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
            strling_interop_owned_bytes_free_v1(&mut output)
        });
    }
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_owned_bytes_free_v1(ptr::null_mut())
    });
}
