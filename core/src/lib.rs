//! Canonical STRling compiler-kernel domain model.
//!
//! The certified contracts under `spec/contracts/1.0` are authoritative. This
//! crate is their reference implementation, not a source of specification
//! truth. Its current boundary contains strongly typed contract data,
//! structural validation, pure semantic normalization, and target-neutral
//! foundational and structural semantic analysis, and structured semantic
//! safety evidence. Portability, lowering, emission, and product integration
//! remain intentionally absent.
#![forbid(unsafe_code)]

pub mod conformance;
pub mod diagnostic;
pub mod diagnostic_generation;
pub mod normalization;
pub mod protocol;
pub mod safety_analysis;
pub mod semantic;
pub mod semantic_analysis;
pub mod source;
pub mod structural_analysis;
pub mod target;
pub mod validation;
