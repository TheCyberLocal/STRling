//! Stable, deterministic facade over the canonical compiler stages.

use std::convert::TryFrom;
use std::error::Error;
use std::fmt;

use crate::compiler_pipeline::compile_semantic_diagnostics;
use crate::diagnostic::{
    compare_diagnostics, CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode,
    DiagnosticOccurrence, Severity, SeverityBasis,
};
use crate::protocol::{
    validate_exchange, CompileInput, CompileOutcome, CompileRequest, CompileResult, CompilerId,
    CompilerIdentity, CompilerVersion, RequestedOutput,
};
use crate::source::ContractVersion;
use crate::target::{TargetProfile, TargetProfileReference};
use crate::validation::{Validate, ValidationErrors};

/// Stable compiler identity emitted by the canonical kernel facade.
pub const KERNEL_COMPILER_ID: &str = "strling_kernel";
/// Stable compiler version emitted by this non-published kernel crate.
pub const KERNEL_COMPILER_VERSION: &str = "0.1.0";
/// The exact semantic specification revision implemented by this kernel.
pub const SUPPORTED_SPECIFICATION_VERSION: &str = "1.0-draft.1";

/// Stable diagnostic for a valid request whose source frontend is unavailable.
pub const UNSUPPORTED_FRONTEND_DIAGNOSTIC: &str = "STRL-PROTOCOL-0002";
/// Stable diagnostic for a valid request using an unimplemented specification.
pub const UNSUPPORTED_SPECIFICATION_DIAGNOSTIC: &str = "STRL-PROTOCOL-0004";
/// Stable diagnostic for requested target lowering or emission that is absent.
pub const TARGET_ARTIFACT_UNAVAILABLE_DIAGNOSTIC: &str = "STRL-PROTOCOL-0005";
/// Stable diagnostic for target-aware evidence without a final contract state.
pub const PORTABILITY_INCOMPLETE_DIAGNOSTIC: &str = "STRL-PORTABILITY-0001";

/// Canonical stage owning a typed boundary failure.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum KernelStage {
    ContractValidation,
    TargetProfileEvidence,
    CompilerIdentity,
    CanonicalSemanticPipeline,
    ResultProjection,
}

/// Typed failures at the in-process facade boundary.
#[derive(Debug)]
pub enum KernelCompileError {
    InvalidRequest(ValidationErrors),
    UnsupportedContractVersion(ContractVersion),
    TargetProfileRequired {
        expected: Box<TargetProfileReference>,
    },
    UnexpectedTargetProfile,
    InvalidTargetProfile(ValidationErrors),
    TargetProfileMismatch {
        expected: Box<TargetProfileReference>,
        actual: Box<TargetProfileReference>,
    },
    StageFailure {
        stage: KernelStage,
        message: String,
    },
    InvalidResult(ValidationErrors),
}

impl fmt::Display for KernelCompileError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidRequest(errors) => {
                write!(formatter, "kernel request validation failed: {errors}")
            }
            Self::UnsupportedContractVersion(version) => {
                write!(
                    formatter,
                    "kernel does not support contract version {version:?}"
                )
            }
            Self::TargetProfileRequired { .. } => {
                formatter.write_str("target-aware compilation requires the exact target profile")
            }
            Self::UnexpectedTargetProfile => formatter
                .write_str("a target profile was supplied for a target-neutral compile request"),
            Self::InvalidTargetProfile(errors) => {
                write!(formatter, "target profile validation failed: {errors}")
            }
            Self::TargetProfileMismatch { .. } => formatter.write_str(
                "supplied target profile identity, version, or fingerprint does not match request",
            ),
            Self::StageFailure { stage, message } => {
                write!(
                    formatter,
                    "canonical kernel stage {stage:?} failed: {message}"
                )
            }
            Self::InvalidResult(errors) => {
                write!(
                    formatter,
                    "kernel result projection failed validation: {errors}"
                )
            }
        }
    }
}

impl Error for KernelCompileError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::InvalidRequest(errors)
            | Self::InvalidTargetProfile(errors)
            | Self::InvalidResult(errors) => Some(errors),
            Self::UnsupportedContractVersion(_)
            | Self::TargetProfileRequired { .. }
            | Self::UnexpectedTargetProfile
            | Self::TargetProfileMismatch { .. }
            | Self::StageFailure { .. } => None,
        }
    }
}

/// Compile one canonical request using only borrowed in-memory contract data.
///
/// `target_profile` is required exactly when the semantic request asks for
/// portability or an artifact. The facade never resolves profile references
/// through host state and never mutates either input.
pub fn compile(
    request: &CompileRequest,
    target_profile: Option<&TargetProfile>,
) -> Result<CompileResult, KernelCompileError> {
    request
        .validate()
        .map_err(KernelCompileError::InvalidRequest)?;
    if request.contract_version != ContractVersion::V1_0_0 {
        return Err(KernelCompileError::UnsupportedContractVersion(
            request.contract_version,
        ));
    }

    let compiler = compiler_identity()?;
    if request.specification_version.as_str() != SUPPORTED_SPECIFICATION_VERSION {
        return failed_result(
            request,
            compiler,
            diagnostic(
                request.contract_version,
                UNSUPPORTED_SPECIFICATION_DIAGNOSTIC,
                CompilerPhase::Protocol,
                DiagnosticCategory::MalformedRequest,
                "The requested semantic specification is not implemented by this compiler.",
            )?,
        );
    }

    match &request.input {
        CompileInput::Source { .. } => failed_result(
            request,
            compiler,
            diagnostic(
                request.contract_version,
                UNSUPPORTED_FRONTEND_DIAGNOSTIC,
                CompilerPhase::Protocol,
                DiagnosticCategory::UnsupportedFrontend,
                "The requested frontend is not supported by this compiler.",
            )?,
        ),
        CompileInput::Semantic { program } => {
            compile_semantic_request(request, program, target_profile, &compiler)
        }
    }
}

fn compile_semantic_request(
    request: &CompileRequest,
    program: &crate::semantic::SemanticProgram,
    target_profile: Option<&TargetProfile>,
    compiler: &CompilerIdentity,
) -> Result<CompileResult, KernelCompileError> {
    validate_target_profile_evidence(request, target_profile)?;

    let mut result = compile_semantic_diagnostics(program, compiler).map_err(|error| {
        KernelCompileError::StageFailure {
            stage: KernelStage::CanonicalSemanticPipeline,
            message: error.to_string(),
        }
    })?;
    project_requested_target_neutral_outputs(request, &mut result);
    filter_advisory_diagnostics(request, &mut result.diagnostics);

    if requests_output(request, RequestedOutput::Portability) {
        result.diagnostics.push(diagnostic(
            request.contract_version,
            PORTABILITY_INCOMPLETE_DIAGNOSTIC,
            CompilerPhase::Portability,
            DiagnosticCategory::Portability,
            "Canonical portability result projection is not yet configured.",
        )?);
    }
    if requests_output(request, RequestedOutput::TargetArtifact) {
        result.diagnostics.push(diagnostic(
            request.contract_version,
            TARGET_ARTIFACT_UNAVAILABLE_DIAGNOSTIC,
            CompilerPhase::TargetLowering,
            DiagnosticCategory::TargetCapability,
            "Target lowering and emission are not implemented by this compiler.",
        )?);
    }

    finish_result(request, result)
}

fn validate_target_profile_evidence(
    request: &CompileRequest,
    supplied: Option<&TargetProfile>,
) -> Result<(), KernelCompileError> {
    if !requests_target_work(request) {
        if supplied.is_some() {
            return Err(KernelCompileError::UnexpectedTargetProfile);
        }
        return Ok(());
    }

    let expected =
        request
            .target_profile
            .as_ref()
            .ok_or_else(|| KernelCompileError::StageFailure {
                stage: KernelStage::ContractValidation,
                message: "validated target-aware request omitted its profile reference".to_owned(),
            })?;
    let supplied = supplied.ok_or_else(|| KernelCompileError::TargetProfileRequired {
        expected: Box::new(expected.clone()),
    })?;
    supplied
        .validate()
        .map_err(KernelCompileError::InvalidTargetProfile)?;
    let actual = supplied
        .reference()
        .map_err(KernelCompileError::InvalidTargetProfile)?;
    if &actual != expected {
        return Err(KernelCompileError::TargetProfileMismatch {
            expected: Box::new(expected.clone()),
            actual: Box::new(actual),
        });
    }
    Ok(())
}

fn project_requested_target_neutral_outputs(request: &CompileRequest, result: &mut CompileResult) {
    if !requests_output(request, RequestedOutput::Semantic) {
        result.semantic_result = None;
    }
    if !requests_output(request, RequestedOutput::Analysis) {
        result.analysis = None;
    }
    result.portability = None;
    result.artifact = None;
}

fn filter_advisory_diagnostics(request: &CompileRequest, diagnostics: &mut Vec<Diagnostic>) {
    let minimum = request.compiler_options.diagnostic_policy.minimum_severity;
    diagnostics.retain(|item| item.is_error() || item.severity <= minimum);
}

fn failed_result(
    request: &CompileRequest,
    compiler: CompilerIdentity,
    diagnostic: Diagnostic,
) -> Result<CompileResult, KernelCompileError> {
    finish_result(
        request,
        CompileResult {
            contract_version: request.contract_version,
            compiler,
            specification_version: request.specification_version.clone(),
            outcome: CompileOutcome::Failed,
            semantic_result: None,
            analysis: None,
            portability: None,
            artifact: None,
            diagnostics: vec![diagnostic],
        },
    )
}

fn finish_result(
    request: &CompileRequest,
    mut result: CompileResult,
) -> Result<CompileResult, KernelCompileError> {
    canonicalize_diagnostics(&mut result.diagnostics)?;
    result.outcome = if result.diagnostics.iter().any(Diagnostic::is_error) {
        CompileOutcome::Failed
    } else {
        CompileOutcome::Succeeded
    };
    result
        .validate()
        .map_err(KernelCompileError::InvalidResult)?;
    validate_exchange(request, &result, &[]).map_err(KernelCompileError::InvalidResult)?;
    Ok(result)
}

fn canonicalize_diagnostics(diagnostics: &mut [Diagnostic]) -> Result<(), KernelCompileError> {
    diagnostics.sort_by(compare_diagnostics);
    for (index, diagnostic) in diagnostics.iter_mut().enumerate() {
        let occurrence = u64::try_from(index).map_err(|_| KernelCompileError::StageFailure {
            stage: KernelStage::ResultProjection,
            message: "diagnostic occurrence exceeds the contract integer range".to_owned(),
        })?;
        diagnostic.occurrence = DiagnosticOccurrence::new(occurrence);
    }
    Ok(())
}

fn diagnostic(
    contract_version: ContractVersion,
    code: &str,
    phase: CompilerPhase,
    category: DiagnosticCategory,
    message: &str,
) -> Result<Diagnostic, KernelCompileError> {
    let code =
        DiagnosticCode::try_from(code).map_err(|message| KernelCompileError::StageFailure {
            stage: KernelStage::ResultProjection,
            message,
        })?;
    Ok(Diagnostic {
        contract_version,
        occurrence: DiagnosticOccurrence::new(0),
        code,
        severity: Severity::Error,
        severity_basis: SeverityBasis::Normative,
        phase,
        category,
        message: message.to_owned(),
        primary_location: None,
        related_locations: None,
        advice: None,
        fixes: None,
    })
}

fn compiler_identity() -> Result<CompilerIdentity, KernelCompileError> {
    let id = CompilerId::try_from(KERNEL_COMPILER_ID).map_err(|message| {
        KernelCompileError::StageFailure {
            stage: KernelStage::CompilerIdentity,
            message,
        }
    })?;
    let version = CompilerVersion::try_from(KERNEL_COMPILER_VERSION).map_err(|message| {
        KernelCompileError::StageFailure {
            stage: KernelStage::CompilerIdentity,
            message,
        }
    })?;
    Ok(CompilerIdentity { id, version })
}

fn requests_target_work(request: &CompileRequest) -> bool {
    requests_output(request, RequestedOutput::Portability)
        || requests_output(request, RequestedOutput::TargetArtifact)
}

fn requests_output(request: &CompileRequest, output: RequestedOutput) -> bool {
    request.requested_outputs.contains(&output)
}
