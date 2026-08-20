//! Curated Rust facade over the canonical STRling compiler kernel.
//!
//! Language semantics, validation, target planning, and emission are owned by
//! `strling-kernel` and the versioned contracts under `spec/`. This crate adds
//! only Rust package ergonomics; it does not contain a parser, compiler, IR, or
//! target emitter of its own.
#![forbid(unsafe_code)]

/// Canonical compile request, result, analysis, and compiler-option contracts.
pub mod contract {
    pub use strling_kernel::protocol::*;
}

/// Canonical structured diagnostic contracts.
pub mod diagnostics {
    pub use strling_kernel::diagnostic::*;
}

/// Canonical Semantic IR values accepted by [`crate::compile`].
pub mod semantic {
    pub use strling_kernel::semantic::*;
}

/// Canonical Simply 1.0/1.1 builder and replay contracts.
pub mod simply {
    pub use strling_kernel::simply::*;
}

/// Canonical source identity, provenance, and UTF-8 byte-coordinate contracts.
pub mod source {
    pub use strling_kernel::source::*;
}

/// Canonical registered standard-library builders.
/// Canonical lexical-shape builders. These helpers do not claim semantic
/// validation.
pub mod stdlib {
    pub use strling_kernel::stdlib::*;
}

/// Canonical target profile, portability, and artifact contracts.
pub mod target {
    pub use strling_kernel::target::*;
}

pub use contract::{CompileRequest, CompileResult};
pub use diagnostics::Diagnostic;
pub use simply::{
    SimplyBuilder, SimplyCharacterSetMember, SimplyCompileProjection, SimplyError, SimplyErrorCode,
    SimplyErrors, SimplyOptions, SimplyValue,
};
pub use strling_kernel::{
    compile, compile_with_evidence, KernelCompileError, KernelCompileOutput, KernelStage,
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
