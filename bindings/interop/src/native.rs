#[cfg(not(target_arch = "wasm32"))]
use std::panic::{catch_unwind, AssertUnwindSafe};
#[cfg(not(target_arch = "wasm32"))]
use std::ptr;
#[cfg(not(target_arch = "wasm32"))]
use std::slice;

#[cfg(not(target_arch = "wasm32"))]
use crate::protocol::execute_bytes;

pub const STRLING_INTEROP_STATUS_RESPONSE_WRITTEN: u32 = 0;
pub const STRLING_INTEROP_STATUS_INVALID_ARGUMENT: u32 = 1;
pub const STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY: u32 = 2;
#[cfg(not(target_arch = "wasm32"))]
pub const STRLING_INTEROP_STATUS_PANIC: u32 = 3;
pub const STRLING_INTEROP_STATUS_INTERNAL_FAILURE: u32 = 4;

#[repr(C)]
#[derive(Debug)]
#[cfg(not(target_arch = "wasm32"))]
pub struct StrlingInteropOwnedBytesV1 {
    pub data: *mut u8,
    pub len: usize,
}

#[cfg(not(target_arch = "wasm32"))]
impl Default for StrlingInteropOwnedBytesV1 {
    fn default() -> Self {
        Self {
            data: ptr::null_mut(),
            len: 0,
        }
    }
}

#[no_mangle]
#[cfg(not(target_arch = "wasm32"))]
pub extern "C" fn strling_interop_abi_version_v1() -> u32 {
    1
}

#[no_mangle]
#[cfg(not(target_arch = "wasm32"))]
/// Execute one request through the canonical interop dispatcher.
///
/// # Safety
///
/// A non-null `request_data` must identify `request_len` readable bytes for
/// the duration of this call. `output` must identify one exclusive, writable
/// descriptor whose fields are both zero. The descriptor must later be freed
/// exactly once with `strling_interop_owned_bytes_free_v1` and must not be
/// copied while it owns a response.
pub unsafe extern "C" fn strling_interop_execute_v1(
    request_data: *const u8,
    request_len: usize,
    output: *mut StrlingInteropOwnedBytesV1,
) -> u32 {
    catch_boundary(|| {
        // SAFETY: This helper validates null and descriptor state before every
        // dereference. Non-null pointer validity remains the caller's C ABI
        // contract and cannot be proven from an address alone.
        unsafe { execute_native(request_data, request_len, output) }
    })
}

#[no_mangle]
#[cfg(not(target_arch = "wasm32"))]
/// Release a response produced by `strling_interop_execute_v1`.
///
/// # Safety
///
/// A non-null `output` must identify an exclusive, writable descriptor. Its
/// fields must either both be zero or be the exact, not-yet-freed pair written
/// by `strling_interop_execute_v1`; stale descriptor copies are invalid.
pub unsafe extern "C" fn strling_interop_owned_bytes_free_v1(
    output: *mut StrlingInteropOwnedBytesV1,
) -> u32 {
    catch_boundary(|| {
        // SAFETY: The helper accepts null, validates the descriptor pair, zeros
        // it before release, and reconstructs only allocations created here.
        unsafe { free_native(output) }
    })
}

#[cfg(not(target_arch = "wasm32"))]
fn catch_boundary(call: impl FnOnce() -> u32) -> u32 {
    catch_unwind(AssertUnwindSafe(call)).unwrap_or(STRLING_INTEROP_STATUS_PANIC)
}

#[cfg(not(target_arch = "wasm32"))]
unsafe fn execute_native(
    request_data: *const u8,
    request_len: usize,
    output: *mut StrlingInteropOwnedBytesV1,
) -> u32 {
    if output.is_null() {
        return STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
    }
    // SAFETY: `output` is non-null; validity and exclusivity are caller ABI
    // obligations documented by the generated header.
    let output = unsafe { &mut *output };
    if !output.data.is_null() || output.len != 0 {
        return STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY;
    }
    let request = if request_data.is_null() {
        if request_len != 0 {
            return STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
        }
        &[]
    } else {
        // SAFETY: Non-null input must identify `request_len` immutable bytes for
        // this call; that lifetime is the caller's ABI obligation.
        unsafe { slice::from_raw_parts(request_data, request_len) }
    };
    let response = execute_bytes(request).into_boxed_slice();
    if response.is_empty() {
        return STRLING_INTEROP_STATUS_INTERNAL_FAILURE;
    }
    output.len = response.len();
    output.data = Box::into_raw(response).cast::<u8>();
    STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
}

#[cfg(not(target_arch = "wasm32"))]
unsafe fn free_native(output: *mut StrlingInteropOwnedBytesV1) -> u32 {
    if output.is_null() {
        return STRLING_INTEROP_STATUS_RESPONSE_WRITTEN;
    }
    // SAFETY: Non-null descriptor validity and exclusivity are caller ABI
    // obligations. The function zeros it before releasing its allocation.
    let output = unsafe { &mut *output };
    let data = output.data;
    let len = output.len;
    output.data = ptr::null_mut();
    output.len = 0;
    if data.is_null() {
        return if len == 0 {
            STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
        } else {
            STRLING_INTEROP_STATUS_INVALID_ARGUMENT
        };
    }
    if len == 0 {
        return STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
    }
    // SAFETY: A valid owning descriptor contains the pointer and exact length
    // produced by `Box<[u8]>` in `execute_native` and has not been copied/freed.
    let slice = ptr::slice_from_raw_parts_mut(data, len);
    drop(unsafe { Box::from_raw(slice) });
    STRLING_INTEROP_STATUS_RESPONSE_WRITTEN
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn native_boundary_contains_unwind() {
        assert_eq!(
            STRLING_INTEROP_STATUS_PANIC,
            catch_boundary(|| panic!("controlled boundary panic"))
        );
    }
}
