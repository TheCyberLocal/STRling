use std::ptr;

use serde_json::{json, Value};
use strling_interop::{
    strling_interop_abi_version_v1, strling_interop_execute_v1,
    strling_interop_owned_bytes_free_v1, StrlingInteropOwnedBytesV1,
    STRLING_INTEROP_STATUS_INVALID_ARGUMENT, STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY,
    STRLING_INTEROP_STATUS_RESPONSE_WRITTEN,
};

fn describe_request() -> Vec<u8> {
    serde_json::to_vec(&json!({
        "interop_protocol_version": "1.0.0",
        "operation": "describe",
        "payload": {},
    }))
    .expect("serialize describe request")
}

#[test]
fn native_abi_version_and_argument_statuses_are_stable() {
    assert_eq!(1, strling_interop_abi_version_v1());
    let request = describe_request();
    assert_eq!(STRLING_INTEROP_STATUS_INVALID_ARGUMENT, unsafe {
        strling_interop_execute_v1(request.as_ptr(), request.len(), ptr::null_mut())
    });
    let mut output = StrlingInteropOwnedBytesV1::default();
    assert_eq!(STRLING_INTEROP_STATUS_INVALID_ARGUMENT, unsafe {
        strling_interop_execute_v1(ptr::null(), 1, &mut output)
    });
    output.len = 1;
    assert_eq!(STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY, unsafe {
        strling_interop_execute_v1(request.as_ptr(), request.len(), &mut output)
    });
}

#[test]
fn native_response_is_owned_until_same_descriptor_is_freed() {
    let request = describe_request();
    let mut output = StrlingInteropOwnedBytesV1::default();
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_execute_v1(request.as_ptr(), request.len(), &mut output)
    });
    assert!(!output.data.is_null());
    assert!(output.len > 0);
    assert_ne!(request.as_ptr(), output.data.cast_const());
    let response = unsafe { std::slice::from_raw_parts(output.data, output.len) };
    let value: Value = serde_json::from_slice(response).expect("response remains readable");
    assert_eq!("completed", value["status"]);

    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_owned_bytes_free_v1(&mut output)
    });
    assert!(output.data.is_null());
    assert_eq!(0, output.len);
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_owned_bytes_free_v1(&mut output)
    });
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_owned_bytes_free_v1(ptr::null_mut())
    });
}

#[test]
fn native_empty_input_returns_a_structured_error_and_retains_nothing() {
    let mut output = StrlingInteropOwnedBytesV1::default();
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_execute_v1(ptr::null(), 0, &mut output)
    });
    let response = unsafe { std::slice::from_raw_parts(output.data, output.len) };
    let value: Value = serde_json::from_slice(response).expect("error response");
    assert_eq!("STRL-INTEROP-0002", value["error"]["code"]);
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_owned_bytes_free_v1(&mut output)
    });
}
