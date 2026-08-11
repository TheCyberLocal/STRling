//! Pure, target-neutral planning over certified capability evaluation.
//!
//! This stage chooses a representation strategy. It never mutates Semantic IR,
//! applies a rewrite, lowers captures, emits target syntax, or probes a runtime.

use std::error::Error;
use std::fmt;

use crate::capability_evaluation::{
    validate_prerequisites, CapabilityDisposition, CapabilityEvaluation,
    CapabilityEvaluationErrors, CapabilityResult, SemanticRequirement,
};
use crate::semantic::SemanticProgram;
use crate::semantic_analysis::{SemanticFacts, SemanticNodeKind};
use crate::source::{ContractVersion, NodeId, Sha256Digest, SpecificationVersion};
use crate::structural_analysis::StructuralFacts;
use crate::target::{
    CapabilityAvailability, CapabilityId, PortabilityStatus, TargetProfile, TargetProfileReference,
};
use crate::validation::{canonical_sha256, Validate};

/// Stable error categories for portability-planning correspondence failures.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum PortabilityPlanningErrorCode {
    InvalidPrerequisites,
    ProgramFingerprintMismatch,
    EvaluationVersionMismatch,
    EvaluationProgramMismatch,
    InvalidTargetProfile,
    TargetProfileMismatch,
    RequirementOrderMismatch,
    RequirementResultMismatch,
    CapabilityEvidenceMismatch,
    RequirementIdentityOverflow,
}

/// One deterministic portability-planning failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PortabilityPlanningError {
    pub code: PortabilityPlanningErrorCode,
    pub path: String,
    pub message: String,
}

impl PortabilityPlanningError {
    fn new(
        code: PortabilityPlanningErrorCode,
        path: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            code,
            path: path.into(),
            message: message.into(),
        }
    }
}

/// Deterministically ordered failures from the pure planning stage.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PortabilityPlanningErrors {
    pub errors: Vec<PortabilityPlanningError>,
}

impl PortabilityPlanningErrors {
    fn single(error: PortabilityPlanningError) -> Self {
        Self {
            errors: vec![error],
        }
    }
}

impl fmt::Display for PortabilityPlanningErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "portability planning failed with {} error(s)",
            self.errors.len()
        )
    }
}

impl Error for PortabilityPlanningErrors {}

/// Stable identity for one occurrence in canonical requirement order.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct RequirementIdentity {
    pub ordinal: u32,
    pub node_id: NodeId,
    pub capability_id: CapabilityId,
}

/// The closed, target-neutral rewrite-strategy vocabulary.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RewriteStrategyId {
    ElideAtomicLiteralV1,
}

impl RewriteStrategyId {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ElideAtomicLiteralV1 => "rewrite.atomic_literal.elide.v1",
        }
    }
}

/// Structural proof conditions understood by the certified registry.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RewriteProofPrecondition {
    OriginalNodeKind {
        node_id: NodeId,
        expected: SemanticNodeKind,
    },
    AtomicBodyNode {
        atomic_node_id: NodeId,
        body_node_id: NodeId,
    },
    BodyNodeKind {
        node_id: NodeId,
        expected: SemanticNodeKind,
    },
}

/// Certified evidence offered to one rewrite proof condition.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RewriteProofEvidence {
    FoundationalNodeKind {
        node_id: NodeId,
        actual: SemanticNodeKind,
    },
    SemanticChildRelationship {
        parent_node_id: NodeId,
        child_node_id: NodeId,
    },
    MissingCertifiedFact {
        node_id: NodeId,
    },
}

/// Result of evaluating one explicit proof condition.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RewriteProofDisposition {
    Satisfied,
    Failed,
    Indeterminate,
}

/// One proof condition and the exact evidence used to evaluate it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RewriteProofEvaluation {
    pub precondition: RewriteProofPrecondition,
    pub evidence: RewriteProofEvidence,
    pub disposition: RewriteProofDisposition,
}

/// Certified support for a replacement semantic requirement.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReplacementCapabilityEvidence {
    pub requirement: SemanticRequirement,
    pub capability_result: CapabilityResult,
}

/// A target-neutral rewrite instruction for a later transformation stage.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticRewritePlan {
    pub strategy_id: RewriteStrategyId,
    pub affected_node_ids: Vec<NodeId>,
    pub original_requirement: SemanticRequirement,
    pub replacement_requirements: Vec<SemanticRequirement>,
    pub proof: Vec<RewriteProofEvaluation>,
    pub replacement_support: Vec<ReplacementCapabilityEvidence>,
    pub target_profile: TargetProfileReference,
    pub dependencies: Vec<RequirementIdentity>,
}

/// Why one registered strategy did not produce an equivalent rewrite.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RewriteAttemptDisposition {
    NotApplicable,
    ProofFailed,
    ProofIndeterminate,
    ReplacementUnsupported,
    ReplacementUnknown,
    Applicable,
}

/// Stable evidence for one deterministic registry attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RewriteAttempt {
    pub strategy_id: RewriteStrategyId,
    pub disposition: RewriteAttemptDisposition,
    pub proof: Vec<RewriteProofEvaluation>,
    pub replacement_requirements: Vec<SemanticRequirement>,
    pub replacement_support: Vec<ReplacementCapabilityEvidence>,
}

/// Exact supported capability evidence for a native decision.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeDecision {
    pub capability_result: CapabilityResult,
}

/// Exact negative capability and rewrite evidence for an unsupported decision.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UnsupportedDecision {
    pub capability_result: CapabilityResult,
    pub rewrite_attempts: Vec<RewriteAttempt>,
}

/// An equivalent semantic rewrite selected without applying it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EquivalentRewriteDecision {
    pub capability_result: CapabilityResult,
    pub rewrite_plan: SemanticRewritePlan,
}

/// Typed reasons that prevent a final requirement-level portability decision.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum UnresolvedPlanningReason {
    CapabilityUnknown,
    RewriteProofIndeterminate,
    ReplacementCapabilityUnknown,
    RewriteStrategyEvaluationPending,
}

/// Incomplete evidence retained outside the final portability vocabulary.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UnresolvedDecision {
    pub capability_result: CapabilityResult,
    pub reason: UnresolvedPlanningReason,
    pub rewrite_attempts: Vec<RewriteAttempt>,
}

/// Exactly one planning disposition for one semantic requirement.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RequirementPlanningDisposition {
    Native(Box<NativeDecision>),
    EquivalentRewrite(Box<EquivalentRewriteDecision>),
    Unsupported(Box<UnsupportedDecision>),
    Unresolved(Box<UnresolvedDecision>),
}

/// One canonically ordered per-requirement plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlannedRequirement {
    pub identity: RequirementIdentity,
    pub requirement: SemanticRequirement,
    pub disposition: RequirementPlanningDisposition,
}

/// Ordering edge between interacting rewrite plans.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct RewriteDependency {
    pub prerequisite: RequirementIdentity,
    pub dependent: RequirementIdentity,
}

/// Complete deterministic representation plan for one program and profile.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PortabilityPlan {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub semantic_program: Sha256Digest,
    pub target_profile: TargetProfileReference,
    pub decisions: Vec<PlannedRequirement>,
    pub rewrite_dependencies: Vec<RewriteDependency>,
    pub unresolved_requirements: Vec<RequirementIdentity>,
    pub status: Option<PortabilityStatus>,
}

/// Plan native and unresolved requirements from one exact certified evaluation.
///
/// Non-native strategy selection is completed by the certified registry in the
/// next planning layer; until then explicit negative native results are retained
/// as incomplete planning evidence rather than overclaimed as unsupported.
pub fn plan_portability(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    target: &TargetProfile,
    evaluation: &CapabilityEvaluation,
) -> Result<PortabilityPlan, PortabilityPlanningErrors> {
    let semantic_program =
        validate_correspondence(input, foundational, structural, target, evaluation)?;

    let mut decisions = Vec::with_capacity(evaluation.results.len());
    let mut unresolved_requirements = Vec::new();
    for (index, result) in evaluation.results.iter().enumerate() {
        let ordinal = u32::try_from(index).map_err(|_| {
            PortabilityPlanningErrors::single(PortabilityPlanningError::new(
                PortabilityPlanningErrorCode::RequirementIdentityOverflow,
                "$.results",
                "requirement count exceeds stable planning identity capacity",
            ))
        })?;
        let identity = RequirementIdentity {
            ordinal,
            node_id: result.requirement.node_id.clone(),
            capability_id: result.requirement.capability_id.clone(),
        };
        let disposition = match result.disposition {
            CapabilityDisposition::Supported => {
                RequirementPlanningDisposition::Native(Box::new(NativeDecision {
                    capability_result: result.clone(),
                }))
            }
            CapabilityDisposition::Unknown => {
                unresolved_requirements.push(identity.clone());
                RequirementPlanningDisposition::Unresolved(Box::new(UnresolvedDecision {
                    capability_result: result.clone(),
                    reason: UnresolvedPlanningReason::CapabilityUnknown,
                    rewrite_attempts: Vec::new(),
                }))
            }
            CapabilityDisposition::Unsupported | CapabilityDisposition::ConstraintViolation => {
                unresolved_requirements.push(identity.clone());
                RequirementPlanningDisposition::Unresolved(Box::new(UnresolvedDecision {
                    capability_result: result.clone(),
                    reason: UnresolvedPlanningReason::RewriteStrategyEvaluationPending,
                    rewrite_attempts: Vec::new(),
                }))
            }
        };
        decisions.push(PlannedRequirement {
            identity,
            requirement: result.requirement.clone(),
            disposition,
        });
    }

    let status = if unresolved_requirements.is_empty() {
        Some(PortabilityStatus::Native)
    } else {
        None
    };
    Ok(PortabilityPlan {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        semantic_program,
        target_profile: evaluation.target_profile.clone(),
        decisions,
        rewrite_dependencies: Vec::new(),
        unresolved_requirements,
        status,
    })
}

fn validate_correspondence(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    target: &TargetProfile,
    evaluation: &CapabilityEvaluation,
) -> Result<Sha256Digest, PortabilityPlanningErrors> {
    validate_prerequisites(input, foundational, structural).map_err(map_prerequisite_errors)?;
    target
        .validate()
        .map_err(|errors| PortabilityPlanningErrors {
            errors: errors
                .errors
                .into_iter()
                .map(|error| {
                    PortabilityPlanningError::new(
                        PortabilityPlanningErrorCode::InvalidTargetProfile,
                        error.path,
                        error.message,
                    )
                })
                .collect(),
        })?;

    let semantic_program = canonical_sha256(input)
        .map(Sha256Digest::from_bytes)
        .map_err(|error| {
            PortabilityPlanningErrors::single(PortabilityPlanningError::new(
                PortabilityPlanningErrorCode::ProgramFingerprintMismatch,
                "$",
                format!("semantic program fingerprint could not be derived: {error}"),
            ))
        })?;
    if evaluation.semantic_program != semantic_program {
        return Err(PortabilityPlanningErrors::single(
            PortabilityPlanningError::new(
                PortabilityPlanningErrorCode::EvaluationProgramMismatch,
                "$.evaluation.semantic_program",
                "capability evaluation was not produced for this exact semantic program",
            ),
        ));
    }
    if evaluation.contract_version != input.contract_version
        || evaluation.specification_version != input.specification_version
        || evaluation.requirements.contract_version != input.contract_version
        || evaluation.requirements.specification_version != input.specification_version
    {
        return Err(PortabilityPlanningErrors::single(
            PortabilityPlanningError::new(
                PortabilityPlanningErrorCode::EvaluationVersionMismatch,
                "$.evaluation",
                "capability evaluation versions do not match the semantic program",
            ),
        ));
    }

    let target_reference = target
        .reference()
        .map_err(|errors| PortabilityPlanningErrors {
            errors: errors
                .errors
                .into_iter()
                .map(|error| {
                    PortabilityPlanningError::new(
                        PortabilityPlanningErrorCode::InvalidTargetProfile,
                        error.path,
                        error.message,
                    )
                })
                .collect(),
        })?;
    if evaluation.target_profile != target_reference
        || evaluation.target_engine != target.engine
        || evaluation.target_runtime != target.runtime
    {
        return Err(PortabilityPlanningErrors::single(
            PortabilityPlanningError::new(
                PortabilityPlanningErrorCode::TargetProfileMismatch,
                "$.evaluation.target_profile",
                "capability evaluation does not match the supplied exact target profile",
            ),
        ));
    }

    if evaluation
        .requirements
        .requirements
        .windows(2)
        .any(|pair| pair[0] >= pair[1])
    {
        return Err(PortabilityPlanningErrors::single(
            PortabilityPlanningError::new(
                PortabilityPlanningErrorCode::RequirementOrderMismatch,
                "$.evaluation.requirements",
                "semantic requirements must be unique and canonically ordered",
            ),
        ));
    }
    if evaluation.requirements.len() != evaluation.results.len() {
        return Err(PortabilityPlanningErrors::single(
            PortabilityPlanningError::new(
                PortabilityPlanningErrorCode::RequirementResultMismatch,
                "$.evaluation.results",
                "every semantic requirement requires exactly one capability result",
            ),
        ));
    }

    for (index, (requirement, result)) in evaluation
        .requirements
        .iter()
        .zip(&evaluation.results)
        .enumerate()
    {
        if &result.requirement != requirement
            || result.node_id != requirement.node_id
            || result.evaluated_capability != requirement.capability_id
        {
            return Err(PortabilityPlanningErrors::single(
                PortabilityPlanningError::new(
                    PortabilityPlanningErrorCode::RequirementResultMismatch,
                    format!("$.evaluation.results[{index}]"),
                    "capability result does not correspond to its canonical requirement",
                ),
            ));
        }
        if result.target_profile != target_reference
            || result.target_engine != target.engine
            || result.target_runtime != target.runtime
        {
            return Err(PortabilityPlanningErrors::single(
                PortabilityPlanningError::new(
                    PortabilityPlanningErrorCode::TargetProfileMismatch,
                    format!("$.evaluation.results[{index}].target_profile"),
                    "capability result does not match the supplied exact target profile",
                ),
            ));
        }
        let profile_capability = target
            .capabilities
            .binary_search_by(|candidate| candidate.capability_id.cmp(&requirement.capability_id))
            .ok()
            .map(|capability_index| &target.capabilities[capability_index]);
        if result.profile_capability.as_ref() != profile_capability {
            return Err(PortabilityPlanningErrors::single(
                PortabilityPlanningError::new(
                    PortabilityPlanningErrorCode::CapabilityEvidenceMismatch,
                    format!("$.evaluation.results[{index}].profile_capability"),
                    "capability evidence does not match the supplied profile record",
                ),
            ));
        }
        if result.disposition == CapabilityDisposition::Supported
            && !matches!(
                result
                    .profile_capability
                    .as_ref()
                    .map(|capability| capability.availability),
                Some(CapabilityAvailability::Available | CapabilityAvailability::Constrained)
            )
        {
            return Err(PortabilityPlanningErrors::single(
                PortabilityPlanningError::new(
                    PortabilityPlanningErrorCode::CapabilityEvidenceMismatch,
                    format!("$.evaluation.results[{index}].disposition"),
                    "supported disposition lacks affirmative profile capability evidence",
                ),
            ));
        }
    }
    Ok(semantic_program)
}

fn map_prerequisite_errors(errors: CapabilityEvaluationErrors) -> PortabilityPlanningErrors {
    PortabilityPlanningErrors {
        errors: errors
            .errors
            .into_iter()
            .map(|error| {
                PortabilityPlanningError::new(
                    PortabilityPlanningErrorCode::InvalidPrerequisites,
                    error.path,
                    error.message,
                )
            })
            .collect(),
    }
}
