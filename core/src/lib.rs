//! Canonical STRling compiler-kernel domain model.
//!
//! The certified contracts under `spec/contracts/1.0` are authoritative. This
//! crate is their reference implementation, not a source of specification
//! truth. Its current boundary contains strongly typed contract data,
//! structural validation, pure semantic normalization, target-neutral semantic
//! and safety analyses, structured diagnostic generation, pure factual target
//! capability evaluation, pure portability planning, independent pure PCRE2 and
//! ECMAScript and Python re structured target lowering, deterministic PCRE2 artifact
//! serialization, deterministic ECMAScript artifact serialization, and
//! bounded no-match evidence derived from exact canonical semantics, plus
//! crate-private stage orchestration. Runtime execution, bindings, editor
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
pub mod ecmascript_lowering;
pub mod ecmascript_serialization;
#[doc(hidden)]
pub mod editor_intelligence;
pub mod explanation;
pub mod no_match_explanation;
pub mod normalization;
pub mod portability_diagnostics;
pub mod portability_planning;
mod post_lowering_requirements;
pub mod protocol;
pub mod python_re_lowering;
pub mod python_re_serialization;
pub mod regex_frontend;
pub mod safety_analysis;
pub mod semantic;
pub mod semantic_analysis;
mod semantic_compatibility;
pub mod semantic_conversion;
pub mod semantic_frontend;
pub mod semantic_rewrite;
pub mod simply;
pub mod source;
pub mod stdlib;
pub mod structural_analysis;
pub mod target;
pub mod target_lowering;
pub mod target_serialization;
pub mod validation;

pub use kernel::{
    compile, compile_with_evidence, KernelCompileError, KernelCompileOutput, KernelStage,
};
pub use simply::{
    SimplyBuilder, SimplyCharacterSetMember, SimplyCompileProjection, SimplyError, SimplyErrorCode,
    SimplyErrors, SimplyOptions, SimplyValue, SIMPLY_LEGACY_PROTOCOL_VERSION,
    SIMPLY_PROTOCOL_VERSION,
};
