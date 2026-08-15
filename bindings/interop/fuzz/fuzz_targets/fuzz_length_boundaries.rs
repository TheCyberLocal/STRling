#![no_main]

mod common;

use std::mem;
use std::ptr::{self, NonNull};

use libfuzzer_sys::fuzz_target;
use strling_interop::{
    strling_interop_execute_v1, strling_interop_owned_bytes_free_v1, StrlingInteropOwnedBytesV1,
    MAX_INTEROP_REQUEST_BYTES, STRLING_INTEROP_STATUS_INVALID_ARGUMENT,
    STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY, STRLING_INTEROP_STATUS_RESPONSE_WRITTEN,
};

fuzz_target!(|data: &[u8]| {
    for length in [
        1,
        mem::size_of::<StrlingInteropOwnedBytesV1>(),
        MAX_INTEROP_REQUEST_BYTES,
        MAX_INTEROP_REQUEST_BYTES + 1,
        usize::MAX,
    ] {
        let mut output = StrlingInteropOwnedBytesV1::default();
        assert_eq!(STRLING_INTEROP_STATUS_INVALID_ARGUMENT, unsafe {
            strling_interop_execute_v1(ptr::null(), length, &mut output)
        });
        assert!(output.data.is_null());
        assert_eq!(0, output.len);
    }

    let mut occupied_pointer = StrlingInteropOwnedBytesV1 {
        data: NonNull::<u8>::dangling().as_ptr(),
        len: 0,
    };
    assert_eq!(STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY, unsafe {
        strling_interop_execute_v1(data.as_ptr(), data.len(), &mut occupied_pointer)
    });
    let mut occupied_length = StrlingInteropOwnedBytesV1 {
        data: ptr::null_mut(),
        len: mem::size_of::<StrlingInteropOwnedBytesV1>(),
    };
    assert_eq!(STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY, unsafe {
        strling_interop_execute_v1(data.as_ptr(), data.len(), &mut occupied_length)
    });

    let mut output = StrlingInteropOwnedBytesV1::default();
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_execute_v1(data.as_ptr(), data.len(), &mut output)
    });
    assert!(!output.data.is_null());
    assert!(output.len > 0);
    assert_eq!(STRLING_INTEROP_STATUS_RESPONSE_WRITTEN, unsafe {
        strling_interop_owned_bytes_free_v1(&mut output)
    });
    assert!(output.data.is_null());
    assert_eq!(0, output.len);

    common::assert_closed_response(data);
});
