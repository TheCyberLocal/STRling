//! Stable, deterministic facade over the canonical compiler stages.

use std::convert::TryFrom;
use std::error::Error;
use std::fmt;
use std::io::{self, Write};

use serde::Serialize;

use crate::capability_pipeline::compile_semantic_portability;
use crate::compiler_pipeline::{
    project_target_neutral_stages, run_target_neutral_stages, MAX_PIPELINE_DIAGNOSTICS,
    MAX_PIPELINE_SEMANTIC_DEPTH, MAX_PIPELINE_SEMANTIC_NODES,
};
use crate::diagnostic::{
    compare_diagnostics, CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode,
    DiagnosticOccurrence, Severity, SeverityBasis,
};
use crate::ecmascript_lowering::lower_ecmascript;
use crate::ecmascript_serialization::serialize_ecmascript;
use crate::explanation::ExplanationDocument;
use crate::portability_planning::{
    PortabilityPlan as PlannedPortability, RequirementPlanningDisposition,
};
use crate::protocol::{
    validate_exchange, CompileInput, CompileOutcome, CompileRequest, CompileResult, CompilerId,
    CompilerIdentity, CompilerVersion, RequestedOutput,
};
use crate::python_re_lowering::lower_python_re;
use crate::python_re_serialization::serialize_python_re;
use crate::regex_frontend::{self, RegexFrontendFailure};
use crate::semantic::{Node, SemanticProgram};
use crate::semantic_frontend::{self, SemanticFrontendFailure};
use crate::source::{ContractVersion, FrontendId, SourceDocument};
use crate::target::{
    PortabilityDecision, PortabilityPlan, PortabilityStatus, ReasonCode, RequirementId,
    TargetArtifact, TargetProfile, TargetProfileReference,
};
use crate::target_lowering::lower_pcre2;
use crate::target_serialization::serialize_pcre2;
use crate::validation::{Validate, ValidationErrors};

/// Stable compiler identity emitted by the canonical kernel facade.
pub const KERNEL_COMPILER_ID: &str = "strling_kernel";
/// Stable compiler version emitted by this non-published kernel crate.
pub const KERNEL_COMPILER_VERSION: &str = "0.1.0";
/// The exact semantic specification revision implemented by this kernel.
pub const SUPPORTED_SPECIFICATION_VERSION: &str = "1.0-draft.1";

/// Maximum canonical JSON bytes accepted for one request contract.
pub const MAX_REQUEST_CONTRACT_BYTES: usize = 8_388_608;
/// Maximum canonical JSON bytes accepted for supplied target-profile evidence.
pub const MAX_TARGET_PROFILE_BYTES: usize = 1_048_576;
/// Maximum semantic nesting accepted before recursive contract work.
pub const MAX_KERNEL_SEMANTIC_DEPTH: usize = MAX_PIPELINE_SEMANTIC_DEPTH;
/// Maximum semantic nodes accepted before canonical stage work.
pub const MAX_KERNEL_SEMANTIC_NODES: usize = MAX_PIPELINE_SEMANTIC_NODES;
/// Maximum diagnostics admitted to a completed result.
pub const MAX_KERNEL_DIAGNOSTICS: usize = MAX_PIPELINE_DIAGNOSTICS;

/// Stable diagnostic for deterministic kernel resource exhaustion.
pub const RESOURCE_EXHAUSTED_DIAGNOSTIC: &str = "STRL-PROTOCOL-0003";

/// Stable diagnostic for a valid request whose source frontend is unavailable.
pub const UNSUPPORTED_FRONTEND_DIAGNOSTIC: &str = "STRL-PROTOCOL-0002";
/// Stable diagnostic for source content that has not been resolved by the caller.
pub const SOURCE_CONTENT_UNAVAILABLE_DIAGNOSTIC: &str = "STRL-PROTOCOL-0006";
/// Stable diagnostic for a valid request using an unimplemented specification.
pub const UNSUPPORTED_SPECIFICATION_DIAGNOSTIC: &str = "STRL-PROTOCOL-0004";
/// Stable diagnostic for requested target output that has no certified projection.
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
    TargetAwarePipeline,
    TargetLowering,
    TargetSerialization,
    ResultProjection,
}

/// One canonical compilation result plus explanation evidence produced by the
/// same certified stage execution when semantic analysis completed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct KernelCompileOutput {
    pub result: CompileResult,
    pub explanation: Option<ExplanationDocument>,
}

impl KernelCompileOutput {
    fn without_explanation(result: CompileResult) -> Self {
        Self {
            result,
            explanation: None,
        }
    }
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
    compile_with_evidence(request, target_profile).map(|output| output.result)
}

/// Compile one canonical request and retain the explanation produced by that
/// exact stage execution when canonical semantic analysis completed.
///
/// The returned `CompileResult` is byte-for-byte the same value returned by
/// [`compile`]. Explanations remain independently versioned and are not added
/// to the compiler result contract.
pub fn compile_with_evidence(
    request: &CompileRequest,
    target_profile: Option<&TargetProfile>,
) -> Result<KernelCompileOutput, KernelCompileError> {
    let compiler = compiler_identity()?;
    if let Some(exhaustion) = preflight_request_resources(request)? {
        return preflight_resource_result(request, compiler, exhaustion)
            .map(KernelCompileOutput::without_explanation);
    }
    request
        .validate()
        .map_err(KernelCompileError::InvalidRequest)?;
    if request.contract_version != ContractVersion::V1_0_0 {
        return Err(KernelCompileError::UnsupportedContractVersion(
            request.contract_version,
        ));
    }
    if request.specification_version.as_str() != SUPPORTED_SPECIFICATION_VERSION {
        return failed_output(
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
        CompileInput::Source { document } => {
            compile_source_request(request, document, target_profile, &compiler)
        }
        CompileInput::Semantic { program } => {
            compile_semantic_request(request, program, target_profile, &compiler)
        }
    }
}

fn compile_source_request(
    request: &CompileRequest,
    document: &SourceDocument,
    target_profile: Option<&TargetProfile>,
    compiler: &CompilerIdentity,
) -> Result<KernelCompileOutput, KernelCompileError> {
    let program = match document.frontend.id.as_str() {
        regex_frontend::FRONTEND_ID => match regex_frontend::parse(document) {
            Ok(parsed) => parsed.program,
            Err(RegexFrontendFailure::Diagnostic(error)) => {
                return failed_output(request, compiler.clone(), error.diagnostic);
            }
            Err(RegexFrontendFailure::InvalidSource(errors)) => {
                return Err(KernelCompileError::InvalidRequest(errors));
            }
            Err(RegexFrontendFailure::ReferencedSourceUnavailable) => {
                return source_content_unavailable_output(request, compiler);
            }
            Err(RegexFrontendFailure::InvalidSemanticOutput(errors)) => {
                return Err(KernelCompileError::StageFailure {
                    stage: KernelStage::CanonicalSemanticPipeline,
                    message: format!("regex frontend produced invalid Semantic IR: {errors}"),
                });
            }
        },
        semantic_frontend::FRONTEND_ID => match semantic_frontend::parse(document) {
            Ok(parsed) => parsed.program,
            Err(SemanticFrontendFailure::Diagnostic(error)) => {
                return failed_output(request, compiler.clone(), error.diagnostic);
            }
            Err(SemanticFrontendFailure::InvalidSource(errors)) => {
                return Err(KernelCompileError::InvalidRequest(errors));
            }
            Err(SemanticFrontendFailure::ReferencedSourceUnavailable) => {
                return source_content_unavailable_output(request, compiler);
            }
            Err(SemanticFrontendFailure::InvalidSemanticOutput(errors)) => {
                return Err(KernelCompileError::StageFailure {
                    stage: KernelStage::CanonicalSemanticPipeline,
                    message: format!("semantic frontend produced invalid Semantic IR: {errors}"),
                });
            }
        },
        _ => {
            return failed_output(
                request,
                compiler.clone(),
                diagnostic(
                    request.contract_version,
                    UNSUPPORTED_FRONTEND_DIAGNOSTIC,
                    CompilerPhase::Protocol,
                    DiagnosticCategory::UnsupportedFrontend,
                    "The requested frontend is not supported by this compiler.",
                )?,
            );
        }
    };

    if let Some(exhaustion) = preflight_semantic_resources(request, &program) {
        return resource_failed_result(request, compiler.clone(), exhaustion)
            .map(KernelCompileOutput::without_explanation);
    }
    compile_semantic_request(request, &program, target_profile, compiler)
}

fn source_content_unavailable_output(
    request: &CompileRequest,
    compiler: &CompilerIdentity,
) -> Result<KernelCompileOutput, KernelCompileError> {
    failed_output(
        request,
        compiler.clone(),
        diagnostic(
            request.contract_version,
            SOURCE_CONTENT_UNAVAILABLE_DIAGNOSTIC,
            CompilerPhase::Protocol,
            DiagnosticCategory::MalformedRequest,
            "Referenced source content must be resolved and supplied inline before compilation.",
        )?,
    )
}

fn compile_semantic_request(
    request: &CompileRequest,
    program: &SemanticProgram,
    target_profile: Option<&TargetProfile>,
    compiler: &CompilerIdentity,
) -> Result<KernelCompileOutput, KernelCompileError> {
    if requests_target_work(request) {
        if let Some(profile) = target_profile {
            if !serialized_within_limit(profile, MAX_TARGET_PROFILE_BYTES)? {
                return resource_failed_result(
                    request,
                    compiler.clone(),
                    ResourceExhaustion::at_least("target profile bytes", MAX_TARGET_PROFILE_BYTES),
                )
                .map(KernelCompileOutput::without_explanation);
            }
        }
    }
    let target_profile = validate_target_profile_evidence(request, target_profile)?;
    let (mut result, portability, explanation) = match target_profile {
        Some(target) => {
            let output = match compile_semantic_portability(program, target) {
                Ok(output) => output,
                Err(error) if error.is_resource_exhaustion() => {
                    return resource_failed_result(
                        request,
                        compiler.clone(),
                        ResourceExhaustion::stage("target-aware pipeline"),
                    )
                    .map(KernelCompileOutput::without_explanation);
                }
                Err(error) => {
                    return Err(KernelCompileError::StageFailure {
                        stage: KernelStage::TargetAwarePipeline,
                        message: error.to_string(),
                    });
                }
            };
            let artifact = if requests_output(request, RequestedOutput::TargetArtifact) {
                project_target_artifact(&output.stages.normalized, target, &output.plan)?
            } else {
                ArtifactProjection::NotRequested
            };
            let explanation = output.explanation;
            let plan = output.plan;
            let mut result =
                project_target_neutral_stages(output.stages, compiler).map_err(|error| {
                    KernelCompileError::StageFailure {
                        stage: KernelStage::ResultProjection,
                        message: error.to_string(),
                    }
                })?;
            result.diagnostics.extend(output.portability_diagnostics);
            match artifact {
                ArtifactProjection::Produced(value) => result.artifact = Some(*value),
                ArtifactProjection::Failed(diagnostics) => {
                    result.diagnostics.extend(diagnostics);
                }
                ArtifactProjection::Unsupported => result.diagnostics.push(diagnostic(
                    request.contract_version,
                    TARGET_ARTIFACT_UNAVAILABLE_DIAGNOSTIC,
                    CompilerPhase::TargetLowering,
                    DiagnosticCategory::TargetCapability,
                    "The selected target profile cannot represent this program, so no artifact was produced.",
                )?),
                ArtifactProjection::BackendUnavailable => result.diagnostics.push(diagnostic(
                    request.contract_version,
                    TARGET_ARTIFACT_UNAVAILABLE_DIAGNOSTIC,
                    CompilerPhase::TargetLowering,
                    DiagnosticCategory::TargetCapability,
                    "No certified target backend is registered for the selected profile.",
                )?),
                ArtifactProjection::Incomplete | ArtifactProjection::NotRequested => {}
            }
            (result, Some(plan), explanation)
        }
        None => {
            let stages = match run_target_neutral_stages(program) {
                Ok(stages) => stages,
                Err(error) if error.is_resource_exhaustion() => {
                    return resource_failed_result(
                        request,
                        compiler.clone(),
                        ResourceExhaustion::stage("target-neutral pipeline"),
                    )
                    .map(KernelCompileOutput::without_explanation);
                }
                Err(error) => {
                    return Err(KernelCompileError::StageFailure {
                        stage: KernelStage::CanonicalSemanticPipeline,
                        message: error.to_string(),
                    });
                }
            };
            let explanation = stages.explanation.clone();
            let result = project_target_neutral_stages(stages, compiler).map_err(|error| {
                KernelCompileError::StageFailure {
                    stage: KernelStage::ResultProjection,
                    message: error.to_string(),
                }
            })?;
            (result, None, explanation)
        }
    };
    project_requested_target_neutral_outputs(request, &mut result);
    filter_advisory_diagnostics(request, &mut result.diagnostics);

    if let Some(plan) = portability {
        match project_portability(&plan)? {
            Some(portability) => {
                if requests_output(request, RequestedOutput::Portability) {
                    result.portability = Some(portability);
                }
            }
            None => result.diagnostics.push(diagnostic(
                request.contract_version,
                PORTABILITY_INCOMPLETE_DIAGNOSTIC,
                CompilerPhase::Portability,
                DiagnosticCategory::Portability,
                "The supplied target profile does not provide complete portability evidence.",
            )?),
        }
    }
    let retain_explanation = result.diagnostics.len() <= diagnostic_limit(request);
    let result = finish_result(request, result)?;
    Ok(KernelCompileOutput {
        result,
        explanation: retain_explanation.then_some(explanation),
    })
}

enum ArtifactProjection {
    NotRequested,
    Produced(Box<TargetArtifact>),
    Failed(Vec<Diagnostic>),
    Unsupported,
    Incomplete,
    BackendUnavailable,
}

fn project_target_artifact(
    program: &SemanticProgram,
    target: &TargetProfile,
    plan: &PlannedPortability,
) -> Result<ArtifactProjection, KernelCompileError> {
    match plan.status {
        None => return Ok(ArtifactProjection::Incomplete),
        Some(PortabilityStatus::Unsupported) => return Ok(ArtifactProjection::Unsupported),
        Some(PortabilityStatus::Native | PortabilityStatus::EquivalentRewrite) => {}
    }
    let mut artifact = match target.engine.id.as_str() {
        "pcre2" => {
            let lowered = match lower_pcre2(program, target, plan) {
                Ok(lowered) => lowered,
                Err(error) => {
                    return artifact_failure_projection(
                        KernelStage::TargetLowering,
                        error.to_string(),
                        error.diagnostics,
                    );
                }
            };
            match serialize_pcre2(&lowered) {
                Ok(artifact) => artifact,
                Err(error) => {
                    return artifact_failure_projection(
                        KernelStage::TargetSerialization,
                        error.to_string(),
                        error.diagnostics,
                    );
                }
            }
        }
        "ecmascript" => {
            let lowered = match lower_ecmascript(program, target, plan) {
                Ok(lowered) => lowered,
                Err(error) => {
                    return artifact_failure_projection(
                        KernelStage::TargetLowering,
                        error.to_string(),
                        error.diagnostics,
                    );
                }
            };
            match serialize_ecmascript(&lowered) {
                Ok(artifact) => artifact,
                Err(error) => {
                    return artifact_failure_projection(
                        KernelStage::TargetSerialization,
                        error.to_string(),
                        error.diagnostics,
                    );
                }
            }
        }
        "python_re" => {
            let lowered = match lower_python_re(program, target, plan) {
                Ok(lowered) => lowered,
                Err(error) => {
                    return artifact_failure_projection(
                        KernelStage::TargetLowering,
                        error.to_string(),
                        error.diagnostics,
                    );
                }
            };
            match serialize_python_re(&lowered) {
                Ok(artifact) => artifact,
                Err(error) => {
                    return artifact_failure_projection(
                        KernelStage::TargetSerialization,
                        error.to_string(),
                        error.diagnostics,
                    );
                }
            }
        }
        _ => return Ok(ArtifactProjection::BackendUnavailable),
    };
    let semantic_node_ids = program.node_ids();
    for entry in &mut artifact.source_map {
        entry
            .node_ids
            .retain(|node_id| semantic_node_ids.contains(node_id));
    }
    Ok(ArtifactProjection::Produced(Box::new(artifact)))
}

fn artifact_failure_projection(
    stage: KernelStage,
    message: String,
    diagnostics: Vec<Diagnostic>,
) -> Result<ArtifactProjection, KernelCompileError> {
    if diagnostics.is_empty() {
        Err(KernelCompileError::StageFailure { stage, message })
    } else {
        Ok(ArtifactProjection::Failed(diagnostics))
    }
}

#[derive(Debug)]
struct ResourceExhaustion {
    message: String,
}

impl ResourceExhaustion {
    fn observed(resource: &str, limit: usize, actual: usize) -> Self {
        Self {
            message: format!(
                "Kernel resource limit exceeded: {resource} limit {limit}, observed {actual}."
            ),
        }
    }

    fn at_least(resource: &str, limit: usize) -> Self {
        Self {
            message: format!(
                "Kernel resource limit exceeded: {resource} limit {limit}, observed at least {}.",
                limit.saturating_add(1)
            ),
        }
    }

    fn stage(stage: &str) -> Self {
        Self {
            message: format!("Kernel resource limit exceeded during the certified {stage}."),
        }
    }
}

fn preflight_request_resources(
    request: &CompileRequest,
) -> Result<Option<ResourceExhaustion>, KernelCompileError> {
    if let CompileInput::Semantic { program } = &request.input {
        if let Some(exhaustion) = preflight_semantic_resources(request, program) {
            return Ok(Some(exhaustion));
        }
    }
    if !serialized_within_limit(request, MAX_REQUEST_CONTRACT_BYTES)? {
        return Ok(Some(ResourceExhaustion::at_least(
            "request contract bytes",
            MAX_REQUEST_CONTRACT_BYTES,
        )));
    }
    Ok(None)
}

fn preflight_semantic_resources(
    request: &CompileRequest,
    program: &SemanticProgram,
) -> Option<ResourceExhaustion> {
    let caller_limit = request
        .compiler_options
        .resource_limits
        .as_ref()
        .and_then(|limits| limits.max_semantic_nodes)
        .filter(|limit| *limit > 0)
        .map(|limit| usize::try_from(limit).unwrap_or(usize::MAX));
    let node_limit = caller_limit
        .unwrap_or(MAX_KERNEL_SEMANTIC_NODES)
        .min(MAX_KERNEL_SEMANTIC_NODES);
    let mut pending = vec![(&program.root, 1_usize)];
    let mut nodes = 0_usize;
    while let Some((node, depth)) = pending.pop() {
        if depth > MAX_KERNEL_SEMANTIC_DEPTH {
            return Some(ResourceExhaustion::observed(
                "semantic nesting depth",
                MAX_KERNEL_SEMANTIC_DEPTH,
                depth,
            ));
        }
        nodes = nodes.saturating_add(1);
        if nodes > node_limit {
            return Some(ResourceExhaustion::observed(
                "semantic nodes",
                node_limit,
                nodes,
            ));
        }
        let child_depth = depth.saturating_add(1);
        match node {
            Node::Sequence { items, .. } => {
                pending.extend(items.iter().rev().map(|child| (child, child_depth)));
            }
            Node::Alternation { branches, .. } => {
                pending.extend(branches.iter().rev().map(|child| (child, child_depth)));
            }
            Node::Repeat { body, .. }
            | Node::Capture { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => pending.push((body, child_depth)),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
    }
    None
}

fn serialized_within_limit<T: Serialize + ?Sized>(
    value: &T,
    limit: usize,
) -> Result<bool, KernelCompileError> {
    let mut writer = BoundedWriter {
        bytes: 0,
        limit,
        exceeded: false,
    };
    match serde_json::to_writer(&mut writer, value) {
        Ok(()) => Ok(true),
        Err(_) if writer.exceeded => Ok(false),
        Err(error) => Err(KernelCompileError::StageFailure {
            stage: KernelStage::ContractValidation,
            message: format!("contract size accounting failed: {error}"),
        }),
    }
}

struct BoundedWriter {
    bytes: usize,
    limit: usize,
    exceeded: bool,
}

impl Write for BoundedWriter {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        if buffer.len() > self.limit.saturating_sub(self.bytes) {
            self.exceeded = true;
            return Err(io::Error::new(
                io::ErrorKind::Other,
                "contract byte limit exceeded",
            ));
        }
        self.bytes += buffer.len();
        Ok(buffer.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}
fn validate_target_profile_evidence<'a>(
    request: &CompileRequest,
    supplied: Option<&'a TargetProfile>,
) -> Result<Option<&'a TargetProfile>, KernelCompileError> {
    if !requests_target_work(request) {
        if supplied.is_some() {
            return Err(KernelCompileError::UnexpectedTargetProfile);
        }
        return Ok(None);
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
    Ok(Some(supplied))
}

fn project_portability(
    planned: &PlannedPortability,
) -> Result<Option<PortabilityPlan>, KernelCompileError> {
    let Some(status) = planned.status else {
        return Ok(None);
    };
    let mut decisions = Vec::with_capacity(planned.decisions.len());
    for planned_decision in &planned.decisions {
        let requirement_id_value = format!(
            "requirement:semantic.{:010}",
            planned_decision.identity.ordinal
        );
        let requirement_id =
            RequirementId::try_from(requirement_id_value.as_str()).map_err(|message| {
                KernelCompileError::StageFailure {
                    stage: KernelStage::ResultProjection,
                    message,
                }
            })?;
        let (decision_status, reason) = match &planned_decision.disposition {
            RequirementPlanningDisposition::Native(native) => {
                let reason = if native.capability_result.constraint_evaluations.is_empty() {
                    "profile_capability_available"
                } else {
                    "within_profile_limit"
                };
                (PortabilityStatus::Native, reason)
            }
            RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
                let reason = match rewrite.rewrite_plan.strategy_id.as_str() {
                    "rewrite.atomic_literal.elide.v1" => "literal_atomicity_redundant",
                    strategy => {
                        return Err(KernelCompileError::StageFailure {
                            stage: KernelStage::ResultProjection,
                            message: format!(
                                "no contract reason code is defined for rewrite strategy {strategy}"
                            ),
                        });
                    }
                };
                (PortabilityStatus::EquivalentRewrite, reason)
            }
            RequirementPlanningDisposition::Unsupported(_) => (
                PortabilityStatus::Unsupported,
                "profile_capability_unavailable",
            ),
            RequirementPlanningDisposition::Unresolved(_) => {
                return Err(KernelCompileError::StageFailure {
                    stage: KernelStage::ResultProjection,
                    message: "final portability plan contains unresolved evidence".to_owned(),
                });
            }
        };
        let reason_code =
            ReasonCode::try_from(reason).map_err(|message| KernelCompileError::StageFailure {
                stage: KernelStage::ResultProjection,
                message,
            })?;
        let node_ids = match &planned_decision.disposition {
            RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
                rewrite.rewrite_plan.affected_node_ids.clone()
            }
            _ => vec![planned_decision.requirement.node_id.clone()],
        };
        decisions.push(PortabilityDecision {
            requirement_id,
            capability_id: planned_decision.requirement.capability_id.clone(),
            node_ids,
            status: decision_status,
            reason_code,
        });
    }
    let portability = PortabilityPlan {
        contract_version: planned.contract_version,
        specification_version: planned.specification_version.clone(),
        target_profile: planned.target_profile.clone(),
        status,
        decisions,
    };
    portability
        .validate()
        .map_err(KernelCompileError::InvalidResult)?;
    Ok(Some(portability))
}

fn project_requested_target_neutral_outputs(request: &CompileRequest, result: &mut CompileResult) {
    if !requests_output(request, RequestedOutput::Semantic) {
        result.semantic_result = None;
    }
    if !requests_output(request, RequestedOutput::Analysis) {
        result.analysis = None;
    }
    result.portability = None;
    if !requests_output(request, RequestedOutput::TargetArtifact) {
        result.artifact = None;
    }
}

fn filter_advisory_diagnostics(request: &CompileRequest, diagnostics: &mut Vec<Diagnostic>) {
    let minimum = request.compiler_options.diagnostic_policy.minimum_severity;
    diagnostics.retain(|item| item.is_error() || item.severity <= minimum);
}

fn resource_failed_result(
    request: &CompileRequest,
    compiler: CompilerIdentity,
    exhaustion: ResourceExhaustion,
) -> Result<CompileResult, KernelCompileError> {
    failed_result(
        request,
        compiler,
        resource_diagnostic(request.contract_version, &exhaustion.message)?,
    )
}

fn preflight_resource_result(
    request: &CompileRequest,
    compiler: CompilerIdentity,
    exhaustion: ResourceExhaustion,
) -> Result<CompileResult, KernelCompileError> {
    let mut result = CompileResult {
        contract_version: request.contract_version,
        compiler,
        specification_version: request.specification_version.clone(),
        outcome: CompileOutcome::Failed,
        semantic_result: None,
        analysis: None,
        portability: None,
        artifact: None,
        diagnostics: vec![resource_diagnostic(
            request.contract_version,
            &exhaustion.message,
        )?],
    };
    canonicalize_diagnostics(&mut result.diagnostics)?;
    result
        .validate()
        .map_err(KernelCompileError::InvalidResult)?;
    Ok(result)
}

fn resource_diagnostic(
    contract_version: ContractVersion,
    message: &str,
) -> Result<Diagnostic, KernelCompileError> {
    diagnostic(
        contract_version,
        RESOURCE_EXHAUSTED_DIAGNOSTIC,
        CompilerPhase::Protocol,
        DiagnosticCategory::ResourceLimit,
        message,
    )
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

fn failed_output(
    request: &CompileRequest,
    compiler: CompilerIdentity,
    diagnostic: Diagnostic,
) -> Result<KernelCompileOutput, KernelCompileError> {
    failed_result(request, compiler, diagnostic).map(KernelCompileOutput::without_explanation)
}

fn diagnostic_limit(request: &CompileRequest) -> usize {
    request
        .compiler_options
        .resource_limits
        .as_ref()
        .and_then(|limits| limits.max_diagnostics)
        .map(|limit| usize::try_from(limit).unwrap_or(usize::MAX))
        .unwrap_or(MAX_KERNEL_DIAGNOSTICS)
        .min(MAX_KERNEL_DIAGNOSTICS)
}

fn finish_result(
    request: &CompileRequest,
    mut result: CompileResult,
) -> Result<CompileResult, KernelCompileError> {
    let diagnostic_limit = diagnostic_limit(request);
    if result.diagnostics.len() > diagnostic_limit {
        return resource_failed_result(
            request,
            result.compiler,
            ResourceExhaustion::observed("diagnostics", diagnostic_limit, result.diagnostics.len()),
        );
    }
    canonicalize_diagnostics(&mut result.diagnostics)?;
    result.outcome = if result.diagnostics.iter().any(Diagnostic::is_error) {
        CompileOutcome::Failed
    } else {
        CompileOutcome::Succeeded
    };
    result
        .validate()
        .map_err(KernelCompileError::InvalidResult)?;
    let supported_frontends = [
        FrontendId::try_from(regex_frontend::FRONTEND_ID).map_err(|message| {
            KernelCompileError::StageFailure {
                stage: KernelStage::ResultProjection,
                message: message.to_string(),
            }
        })?,
        FrontendId::try_from(semantic_frontend::FRONTEND_ID).map_err(|message| {
            KernelCompileError::StageFailure {
                stage: KernelStage::ResultProjection,
                message: message.to_string(),
            }
        })?,
    ];
    validate_exchange(request, &result, &supported_frontends)
        .map_err(KernelCompileError::InvalidResult)?;
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

#[cfg(test)]
mod tests {
    use super::*;

    fn target_diagnostic(code: &str) -> Diagnostic {
        diagnostic(
            ContractVersion::V1_0_0,
            code,
            CompilerPhase::Emission,
            DiagnosticCategory::TargetCapability,
            "governed target emission failure",
        )
        .expect("test diagnostic")
    }

    #[test]
    fn artifact_failure_projection_preserves_every_structured_diagnostic() {
        let diagnostics = vec![
            target_diagnostic("STRL-TEST-0002"),
            target_diagnostic("STRL-TEST-0001"),
        ];
        let projection = artifact_failure_projection(
            KernelStage::TargetSerialization,
            "serializer reported diagnostics".to_owned(),
            diagnostics.clone(),
        )
        .expect("structured failure projection");

        let ArtifactProjection::Failed(actual) = projection else {
            panic!("structured diagnostics must produce a failed artifact projection");
        };
        assert_eq!(actual, diagnostics);
    }

    #[test]
    fn artifact_failure_without_diagnostics_remains_an_internal_stage_failure() {
        let error = match artifact_failure_projection(
            KernelStage::TargetSerialization,
            "serializer failed without diagnostic evidence".to_owned(),
            Vec::new(),
        ) {
            Err(error) => error,
            Ok(_) => panic!("missing diagnostic payload must not become a compile result"),
        };

        let KernelCompileError::StageFailure { stage, message } = error else {
            panic!("missing diagnostic payload must remain an internal stage failure");
        };
        assert_eq!(stage, KernelStage::TargetSerialization);
        assert_eq!(message, "serializer failed without diagnostic evidence");
    }
}
