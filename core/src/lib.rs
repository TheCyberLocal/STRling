//! Canonical STRling compiler-kernel domain model.
//!
//! The certified contracts under `spec/contracts/1.0` are authoritative. This
//! crate is their reference implementation, not a source of specification
//! truth. Its current boundary contains strongly typed contract data,
//! structural validation, and pure semantic normalization. Later executable
//! compiler phases are intentionally absent.
#![forbid(unsafe_code)]

pub mod conformance;
pub mod diagnostic;
pub mod normalization;
pub mod protocol;
pub mod semantic;
pub mod source;
pub mod target;
pub mod validation;
