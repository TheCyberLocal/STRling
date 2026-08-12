//! Canonical STRling compiler-kernel domain model.
//!
//! The certified contracts under `spec/contracts/1.0` are authoritative. This
//! crate is their reference implementation, not a source of specification
//! truth. Its current boundary contains strongly typed contract data,
//! structural validation, pure semantic normalization, target-neutral semantic
//! and safety analyses, structured diagnostic generation, pure factual target
//! capability evaluation, pure portability planning, and crate-private stage
//! orchestration. Rewrite application, lowering, emission, bindings, editor
//! presentation, and product integration remain intentionally absent.
#![forbid(unsafe_code)]

pub mod capability_evaluation;
pub mod kernel;
// Certified stage orchestration stays crate-private; external embedders enter
// through `kernel::compile`.
#[allow(dead_code)]
mod capability_pipeline;
#[allow(dead_code)]
mod compiler_pipeline;
pub mod conformance;
pub mod diagnostic;
pub mod diagnostic_generation;
pub mod normalization;
pub mod portability_planning;
pub mod protocol;
pub mod regex_frontend;
pub mod safety_analysis;
pub mod semantic;
pub mod semantic_analysis;
pub mod source;
pub mod structural_analysis;
pub mod target;
pub mod validation;

pub use kernel::{compile, KernelCompileError, KernelStage};
