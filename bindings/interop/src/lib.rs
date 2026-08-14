//! Stable native and WebAssembly adapter boundary for the canonical compiler.
//!
//! The versioned contracts under `spec/interop/1.0` are authoritative. This
//! crate owns transport and raw-memory mechanics only; all STRling semantics
//! remain in `strling-kernel` and its controlling specifications.
#![deny(unsafe_op_in_unsafe_fn)]

mod native;
mod protocol;
#[cfg(target_arch = "wasm32")]
mod wasm;

#[cfg(not(target_arch = "wasm32"))]
pub use native::{
    strling_interop_abi_version_v1, strling_interop_execute_v1,
    strling_interop_owned_bytes_free_v1, StrlingInteropOwnedBytesV1, STRLING_INTEROP_STATUS_PANIC,
};
pub use native::{
    STRLING_INTEROP_STATUS_INTERNAL_FAILURE, STRLING_INTEROP_STATUS_INVALID_ARGUMENT,
    STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY, STRLING_INTEROP_STATUS_RESPONSE_WRITTEN,
};
pub use protocol::{execute_bytes, MAX_INTEROP_REQUEST_BYTES, MAX_INTEROP_RESPONSE_BYTES};
