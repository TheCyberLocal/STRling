use std::ptr;
use std::slice;

use crate::native::{
    STRLING_INTEROP_STATUS_INTERNAL_FAILURE, STRLING_INTEROP_STATUS_INVALID_ARGUMENT,
    STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY, STRLING_INTEROP_STATUS_RESPONSE_WRITTEN,
};
use crate::protocol::{execute_bytes, MAX_INTEROP_REQUEST_BYTES};

const DESCRIPTOR_SIZE: u32 = 8;
const DESCRIPTOR_ALIGNMENT: u32 = 4;

#[no_mangle]
pub extern "C" fn strling_wasm_abi_version_v1() -> u32 {
    1
}

#[no_mangle]
pub extern "C" fn strling_wasm_alloc_v1(len: u32) -> u32 {
    if len == 0 || usize::try_from(len).map_or(true, |len| len > MAX_INTEROP_REQUEST_BYTES) {
        return 0;
    }
    let Ok(len) = usize::try_from(len) else {
        return 0;
    };
    let mut bytes = Vec::new();
    if bytes.try_reserve_exact(len).is_err() {
        return 0;
    }
    bytes.resize(len, 0);
    Box::into_raw(bytes.into_boxed_slice()).cast::<u8>() as u32
}

#[no_mangle]
/// Release one allocation previously returned by `strling_wasm_alloc_v1`.
///
/// # Safety
///
/// Nonzero `ptr` and `len` must be the exact owning pair returned by
/// `strling_wasm_alloc_v1`, still live in this module instance and freed once.
pub unsafe extern "C" fn strling_wasm_dealloc_v1(ptr: u32, len: u32) -> u32 {
    if ptr == 0 {
        return if len == 0 {
            STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
        } else {
            STRLING_INTEROP_STATUS_INVALID_ARGUMENT
        };
    }
    if len == 0 || !memory_range_valid(ptr, len) {
        return STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
    }
    let slice = ptr::slice_from_raw_parts_mut(ptr as *mut u8, len as usize);
    // SAFETY: The host contract requires the exact pointer/length returned by
    // `strling_wasm_alloc_v1`, released exactly once.
    drop(unsafe { Box::from_raw(slice) });
    STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
}

#[no_mangle]
/// Execute one request from this module instance's linear memory.
///
/// # Safety
///
/// The request range must be readable for this call. `descriptor_ptr` must be
/// four-byte aligned and identify eight writable zero bytes in this instance.
/// The host must not retain stale descriptor copies or concurrently mutate
/// these ranges while the call is active.
pub unsafe extern "C" fn strling_wasm_execute_v1(
    request_ptr: u32,
    request_len: u32,
    descriptor_ptr: u32,
) -> u32 {
    if descriptor_ptr == 0
        || descriptor_ptr % DESCRIPTOR_ALIGNMENT != 0
        || !memory_range_valid(descriptor_ptr, DESCRIPTOR_SIZE)
    {
        return STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
    }
    // SAFETY: The eight-byte descriptor range was validated against current
    // linear memory and the contract fixes little-endian u32 fields.
    let descriptor = unsafe { slice::from_raw_parts_mut(descriptor_ptr as *mut u8, 8) };
    if read_u32(descriptor, 0) != 0 || read_u32(descriptor, 4) != 0 {
        return STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY;
    }
    if (request_ptr == 0 && request_len != 0)
        || (request_len != 0 && !memory_range_valid(request_ptr, request_len))
    {
        return STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
    }
    let request = if request_len == 0 {
        Vec::new()
    } else {
        // SAFETY: The request range was validated against current linear
        // memory. Copying now prevents later response allocation/growth from
        // affecting the borrowed input view.
        unsafe { slice::from_raw_parts(request_ptr as *const u8, request_len as usize) }.to_vec()
    };
    let response = execute_bytes(&request).into_boxed_slice();
    if response.is_empty() || response.len() > u32::MAX as usize {
        return STRLING_INTEROP_STATUS_INTERNAL_FAILURE;
    }
    let response_len = response.len() as u32;
    let response_ptr = Box::into_raw(response).cast::<u8>() as u32;
    write_u32(descriptor, 0, response_ptr);
    write_u32(descriptor, 4, response_len);
    STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
}

#[no_mangle]
/// Release a response through its in-memory owning descriptor.
///
/// # Safety
///
/// A nonzero `descriptor_ptr` must be four-byte aligned and identify the same
/// exclusive eight-byte descriptor written by `strling_wasm_execute_v1` in
/// this module instance. The owning pair must not already have been freed.
pub unsafe extern "C" fn strling_wasm_owned_bytes_free_v1(descriptor_ptr: u32) -> u32 {
    if descriptor_ptr == 0 {
        return STRLING_INTEROP_STATUS_RESPONSE_WRITTEN;
    }
    if descriptor_ptr % DESCRIPTOR_ALIGNMENT != 0
        || !memory_range_valid(descriptor_ptr, DESCRIPTOR_SIZE)
    {
        return STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
    }
    // SAFETY: The descriptor range was validated against current linear
    // memory. It is zeroed before any owned response is released.
    let descriptor = unsafe { slice::from_raw_parts_mut(descriptor_ptr as *mut u8, 8) };
    let data = read_u32(descriptor, 0);
    let len = read_u32(descriptor, 4);
    write_u32(descriptor, 0, 0);
    write_u32(descriptor, 4, 0);
    if data == 0 {
        return if len == 0 {
            STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
        } else {
            STRLING_INTEROP_STATUS_INVALID_ARGUMENT
        };
    }
    if len == 0 || !memory_range_valid(data, len) {
        return STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
    }
    let slice = ptr::slice_from_raw_parts_mut(data as *mut u8, len as usize);
    // SAFETY: A valid owning descriptor contains the exact pointer/length
    // produced by `strling_wasm_execute_v1` and has not been copied/freed.
    drop(unsafe { Box::from_raw(slice) });
    STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
}

fn memory_range_valid(ptr: u32, len: u32) -> bool {
    let Some(end) = ptr.checked_add(len) else {
        return false;
    };
    let memory_bytes = core::arch::wasm32::memory_size(0).saturating_mul(65_536);
    usize::try_from(end).is_ok_and(|end| end <= memory_bytes)
}

fn read_u32(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(
        bytes[offset..offset + 4]
            .try_into()
            .expect("validated descriptor field"),
    )
}

fn write_u32(bytes: &mut [u8], offset: usize, value: u32) {
    bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}
