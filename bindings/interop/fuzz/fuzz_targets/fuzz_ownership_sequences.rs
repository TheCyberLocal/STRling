#![no_main]

mod common;

use std::ptr;

use libfuzzer_sys::fuzz_target;
use strling_interop::{
    strling_interop_execute_v1, strling_interop_owned_bytes_free_v1, StrlingInteropOwnedBytesV1,
    STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY, STRLING_INTEROP_STATUS_RESPONSE_WRITTEN,
};

fuzz_target!(|data: &[u8]| {
    let request = data.get(64..).unwrap_or(data);
    let mut output = StrlingInteropOwnedBytesV1::default();
    for action in data.iter().take(64).map(|byte| byte % 4) {
        match action {
            0 | 1 => {
                let was_empty = output.data.is_null() && output.len == 0;
                let input = if action == 0 { request } else { b"{" };
                let status =
                    unsafe { strling_interop_execute_v1(input.as_ptr(), input.len(), &mut output) };
                assert_eq!(
                    if was_empty {
                        STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
                    } else {
                        STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY
                    },
                    status
                );
                assert!(!output.data.is_null());
                assert!(output.len > 0);
            }
            2 => {
                assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
                    strling_interop_owned_bytes_free_v1(&mut output)
                });
                assert!(output.data.is_null());
                assert_eq!(0, output.len);
            }
            _ => {
                assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
                    strling_interop_owned_bytes_free_v1(ptr::null_mut())
                });
            }
        }
    }
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_owned_bytes_free_v1(&mut output)
    });
    assert!(output.data.is_null());
    assert_eq!(0, output.len);

    common::assert_closed_response(request);
});
