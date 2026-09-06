//! Curated Rust facade over the canonical STRling compiler implementation.
//!
//! This crate root compiles the same governed source files as the unpublished
//! internal `strling-kernel` package. Language semantics, validation, target
//! planning, and emission remain owned by those canonical sources and the
//! versioned contracts under `spec/`; this facade adds no second implementation.
#![forbid(unsafe_code)]
// The same canonical modules also serve the broader unpublished internal
// package. Items used only by that package remain intentionally private and
// unreachable here, so their imports and declarations are expected to be
// unused when compiled through this curated crate root.
#![allow(dead_code, unused_imports)]

mod capability_evaluation;
#[allow(dead_code)]
mod capability_pipeline;
#[allow(dead_code)]
mod compiler_pipeline;
mod conformance;
mod diagnostic;
mod diagnostic_generation;
mod ecmascript_lowering;
mod ecmascript_serialization;
#[allow(dead_code)]
mod editor_intelligence;
mod explanation;
mod kernel;
mod no_match_explanation;
mod normalization;
mod portability_diagnostics;
mod portability_planning;
mod post_lowering_requirements;
mod protocol;
mod python_re_lowering;
mod python_re_serialization;
mod regex_frontend;
mod safety_analysis;
mod semantic_analysis;
mod semantic_conversion;
mod semantic_frontend;
mod semantic_rewrite;
mod structural_analysis;
mod target_lowering;
mod target_serialization;
mod validation;

/// Canonical compile request, result, analysis, and compiler-option contracts.
pub mod contract {
    pub use crate::protocol::*;
}

/// Canonical structured diagnostic contracts.
pub mod diagnostics {
    pub use crate::diagnostic::*;
}

/// Canonical Semantic IR values accepted by [`crate::compile`].
pub mod semantic;

/// Canonical Simply 1.0/1.1 builder and replay contracts.
pub mod simply;

/// Canonical source identity, provenance, and UTF-8 byte-coordinate contracts.
pub mod source;

/// Canonical registered standard-library builders.
///
/// Current helpers are lexical-shape builders; they do not claim semantic
/// validation.
pub mod stdlib;

/// Canonical target profile, portability, and artifact contracts.
pub mod target;

pub use contract::{CompileRequest, CompileResult};
pub use diagnostics::Diagnostic;
pub use kernel::{
    compile, compile_with_evidence, KernelCompileError, KernelCompileOutput, KernelStage,
};
pub use simply::{
    SimplyBuilder, SimplyCharacterSetMember, SimplyCompileProjection, SimplyError, SimplyErrorCode,
    SimplyErrors, SimplyOptions, SimplyValue,
};
pub use target::{TargetArtifact, TargetProfile, TargetProfileReference};

/// The host-package version. Compiler and contract versions remain independent.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Return the host-package version without selecting compiler or target behavior.
#[must_use]
pub const fn version() -> &'static str {
    VERSION
}

/// Execute the exact supplied canonical request as a check convenience.
///
/// The request's `requested_outputs` remain authoritative; this function does
/// not add or remove outputs and requires the same exact target profile as
/// [`compile`].
pub fn check(
    request: &CompileRequest,
    target_profile: Option<&TargetProfile>,
) -> Result<CompileResult, KernelCompileError> {
    compile(request, target_profile)
}
