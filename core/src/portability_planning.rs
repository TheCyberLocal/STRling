//! Pure, target-neutral planning over certified capability evaluation.
//!
//! This stage chooses a representation strategy. It never mutates Semantic IR,
//! applies a rewrite, lowers captures, emits target syntax, or probes a runtime.

mod equivalence;
mod validation;

pub(crate) use equivalence::certification_for;

pub use equivalence::{
    certified_rewrite_registry, certify_rewrite_registry, certify_rewrite_registry_with_evidence,
    CertifiedRewriteRegistry, CertifiedRewriteStrategy, RewriteApplicationKind,
    RewriteCapabilityEffects, RewriteCertificationEvidence, RewriteConformanceEvidence,
    RewriteExecutionEvidence, RewriteObligation, RewriteProofMethod, RewriteRegistryError,
    RewriteSelection, RewriteSemanticShape, RewriteStrategyDefinition, RewriteTargetApplicability,
    RewriteTargetScope, RewriteTransformation,
};

use std::error::Error;
use std::fmt;

use validation::{aggregate_status, collect_rewrite_dependencies};

use crate::capability_evaluation::{
    validate_prerequisites, CapabilityDisposition, CapabilityEvaluation,
    CapabilityEvaluationErrors, CapabilityResult, RequirementKind, SemanticRequirement,
    MAX_CAPABILITY_REQUIREMENTS,
};
use crate::semantic::{Node, SemanticProgram};
use crate::semantic_analysis::{SemanticFacts, SemanticNodeKind};
use crate::source::{ContractVersion, NodeId, Sha256Digest, SpecificationVersion};
use crate::structural_analysis::StructuralFacts;
use crate::target::{
    CapabilityAvailability, CapabilityId, PortabilityStatus, TargetProfile, TargetProfileReference,
};
use crate::validation::{canonical_sha256, Validate};

/// Maximum final or unresolved requirement decisions in one plan.
pub const MAX_PORTABILITY_DECISIONS: usize = MAX_CAPABILITY_REQUIREMENTS;

/// Maximum canonical dependencies among rewrite decisions in one plan.
pub const MAX_REWRITE_DEPENDENCIES: usize = 4_096;

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
    InvalidRewriteRegistry,
    RequirementIdentityOverflow,
    MalformedRewritePlan,
    RewriteDependencyMissing,
    RewriteDependencyCycle,
    ResourceLimitExceeded,
    AggregateStatusMismatch,
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
    ElideExactOnceRepetitionV1,
}

impl RewriteStrategyId {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ElideAtomicLiteralV1 => "rewrite.atomic_literal.elide.v1",
            Self::ElideExactOnceRepetitionV1 => "rewrite.repeat_exactly_once.elide.v1",
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
    pub certification: RewriteCertificationEvidence,
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

/// Plan representation decisions from one exact certified evaluation.
pub fn plan_portability(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    target: &TargetProfile,
    evaluation: &CapabilityEvaluation,
) -> Result<PortabilityPlan, PortabilityPlanningErrors> {
    let semantic_program =
        validate_correspondence(input, foundational, structural, target, evaluation)?;

    enforce_planning_limit(
        evaluation.results.len(),
        MAX_PORTABILITY_DECISIONS,
        "portability decision",
    )?;
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
                match evaluate_rewrite_registry(input, foundational, evaluation, result)? {
                    RewriteRegistryResolution::Equivalent(rewrite_plan) => {
                        RequirementPlanningDisposition::EquivalentRewrite(Box::new(
                            EquivalentRewriteDecision {
                                capability_result: result.clone(),
                                rewrite_plan: *rewrite_plan,
                            },
                        ))
                    }
                    RewriteRegistryResolution::Incomplete { reason, attempts } => {
                        unresolved_requirements.push(identity.clone());
                        RequirementPlanningDisposition::Unresolved(Box::new(UnresolvedDecision {
                            capability_result: result.clone(),
                            reason,
                            rewrite_attempts: attempts,
                        }))
                    }
                    RewriteRegistryResolution::NoEquivalent(attempts) => {
                        RequirementPlanningDisposition::Unsupported(Box::new(UnsupportedDecision {
                            capability_result: result.clone(),
                            rewrite_attempts: attempts,
                        }))
                    }
                }
            }
        };
        decisions.push(PlannedRequirement {
            identity,
            requirement: result.requirement.clone(),
            disposition,
        });
    }

    let rewrite_dependencies = collect_rewrite_dependencies(&decisions);
    enforce_planning_limit(
        rewrite_dependencies.len(),
        MAX_REWRITE_DEPENDENCIES,
        "rewrite dependency",
    )?;
    let status = aggregate_status(&decisions);
    let plan = PortabilityPlan {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        semantic_program,
        target_profile: evaluation.target_profile.clone(),
        decisions,
        rewrite_dependencies,
        unresolved_requirements,
        status,
    };
    plan.validate()?;
    Ok(plan)
}

fn enforce_planning_limit(
    count: usize,
    limit: usize,
    resource: &str,
) -> Result<(), PortabilityPlanningErrors> {
    if count > limit {
        return Err(PortabilityPlanningErrors::single(
            PortabilityPlanningError::new(
                PortabilityPlanningErrorCode::ResourceLimitExceeded,
                "$.decisions",
                format!("{resource} count exceeds deterministic limit {limit}"),
            ),
        ));
    }
    Ok(())
}
enum RewriteRegistryResolution {
    Equivalent(Box<SemanticRewritePlan>),
    Incomplete {
        reason: UnresolvedPlanningReason,
        attempts: Vec<RewriteAttempt>,
    },
    NoEquivalent(Vec<RewriteAttempt>),
}

struct StrategyEvaluation {
    attempt: RewriteAttempt,
    plan: Option<SemanticRewritePlan>,
}

enum ReplacementSupportOutcome {
    Supported(Vec<ReplacementCapabilityEvidence>),
    Unsupported(Vec<ReplacementCapabilityEvidence>),
    Unknown(Vec<ReplacementCapabilityEvidence>),
}

fn evaluate_rewrite_registry(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    evaluation: &CapabilityEvaluation,
    capability_result: &CapabilityResult,
) -> Result<RewriteRegistryResolution, PortabilityPlanningErrors> {
    let registry = certified_rewrite_registry().map_err(registry_error)?;
    let strategy_ids = registry.portability_strategy_ids();
    let mut attempts = Vec::with_capacity(strategy_ids.len());
    let mut selected = None;
    for strategy_id in strategy_ids {
        let certification = equivalence::certification_for(strategy_id).map_err(registry_error)?;
        let evaluated = match strategy_id {
            RewriteStrategyId::ElideAtomicLiteralV1 => evaluate_atomic_literal_elision(
                input,
                foundational,
                evaluation,
                capability_result,
                certification,
            ),
            RewriteStrategyId::ElideExactOnceRepetitionV1 => StrategyEvaluation {
                attempt: RewriteAttempt {
                    strategy_id,
                    disposition: RewriteAttemptDisposition::NotApplicable,
                    proof: Vec::new(),
                    replacement_requirements: Vec::new(),
                    replacement_support: Vec::new(),
                },
                plan: None,
            },
        };
        if selected.is_none() {
            selected = evaluated.plan;
        }
        attempts.push(evaluated.attempt);
    }

    if let Some(plan) = selected {
        return Ok(RewriteRegistryResolution::Equivalent(Box::new(plan)));
    }
    if attempts
        .iter()
        .any(|attempt| attempt.disposition == RewriteAttemptDisposition::ProofIndeterminate)
    {
        return Ok(RewriteRegistryResolution::Incomplete {
            reason: UnresolvedPlanningReason::RewriteProofIndeterminate,
            attempts,
        });
    }
    if attempts
        .iter()
        .any(|attempt| attempt.disposition == RewriteAttemptDisposition::ReplacementUnknown)
    {
        return Ok(RewriteRegistryResolution::Incomplete {
            reason: UnresolvedPlanningReason::ReplacementCapabilityUnknown,
            attempts,
        });
    }
    Ok(RewriteRegistryResolution::NoEquivalent(attempts))
}

fn evaluate_atomic_literal_elision(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    evaluation: &CapabilityEvaluation,
    capability_result: &CapabilityResult,
    certification: RewriteCertificationEvidence,
) -> StrategyEvaluation {
    if !matches!(capability_result.requirement.kind, RequirementKind::Atomic) {
        return StrategyEvaluation {
            attempt: RewriteAttempt {
                strategy_id: RewriteStrategyId::ElideAtomicLiteralV1,
                disposition: RewriteAttemptDisposition::NotApplicable,
                proof: Vec::new(),
                replacement_requirements: Vec::new(),
                replacement_support: Vec::new(),
            },
            plan: None,
        };
    }

    let original_node_id = capability_result.requirement.node_id.clone();
    let original_kind = foundational.get(&original_node_id).map(|facts| facts.kind);
    let mut proof = vec![node_kind_proof(
        original_node_id.clone(),
        SemanticNodeKind::Atomic,
        original_kind,
    )];

    let Some(Node::Atomic { body, .. }) = find_node(&input.root, &original_node_id) else {
        let disposition = proof_attempt_disposition(&proof);
        return StrategyEvaluation {
            attempt: RewriteAttempt {
                strategy_id: RewriteStrategyId::ElideAtomicLiteralV1,
                disposition,
                proof,
                replacement_requirements: Vec::new(),
                replacement_support: Vec::new(),
            },
            plan: None,
        };
    };

    let body_node_id = body.node_id().clone();
    proof.push(RewriteProofEvaluation {
        precondition: RewriteProofPrecondition::AtomicBodyNode {
            atomic_node_id: original_node_id.clone(),
            body_node_id: body_node_id.clone(),
        },
        evidence: RewriteProofEvidence::SemanticChildRelationship {
            parent_node_id: original_node_id.clone(),
            child_node_id: body_node_id.clone(),
        },
        disposition: RewriteProofDisposition::Satisfied,
    });
    proof.push(node_kind_proof(
        body_node_id.clone(),
        SemanticNodeKind::Literal,
        foundational.get(&body_node_id).map(|facts| facts.kind),
    ));

    let replacement_requirements = Vec::new();
    let replacement_support =
        match resolve_replacement_support(&replacement_requirements, evaluation) {
            ReplacementSupportOutcome::Supported(evidence) => evidence,
            ReplacementSupportOutcome::Unsupported(evidence) => {
                return StrategyEvaluation {
                    attempt: RewriteAttempt {
                        strategy_id: RewriteStrategyId::ElideAtomicLiteralV1,
                        disposition: RewriteAttemptDisposition::ReplacementUnsupported,
                        proof,
                        replacement_requirements,
                        replacement_support: evidence,
                    },
                    plan: None,
                };
            }
            ReplacementSupportOutcome::Unknown(evidence) => {
                return StrategyEvaluation {
                    attempt: RewriteAttempt {
                        strategy_id: RewriteStrategyId::ElideAtomicLiteralV1,
                        disposition: RewriteAttemptDisposition::ReplacementUnknown,
                        proof,
                        replacement_requirements,
                        replacement_support: evidence,
                    },
                    plan: None,
                };
            }
        };

    let disposition = proof_attempt_disposition(&proof);
    if disposition != RewriteAttemptDisposition::Applicable {
        return StrategyEvaluation {
            attempt: RewriteAttempt {
                strategy_id: RewriteStrategyId::ElideAtomicLiteralV1,
                disposition,
                proof,
                replacement_requirements,
                replacement_support,
            },
            plan: None,
        };
    }

    let mut affected_node_ids = vec![original_node_id, body_node_id];
    affected_node_ids.sort();
    affected_node_ids.dedup();
    let plan = SemanticRewritePlan {
        strategy_id: RewriteStrategyId::ElideAtomicLiteralV1,
        certification,
        affected_node_ids,
        original_requirement: capability_result.requirement.clone(),
        replacement_requirements: replacement_requirements.clone(),
        proof: proof.clone(),
        replacement_support: replacement_support.clone(),
        target_profile: evaluation.target_profile.clone(),
        dependencies: Vec::new(),
    };
    StrategyEvaluation {
        attempt: RewriteAttempt {
            strategy_id: RewriteStrategyId::ElideAtomicLiteralV1,
            disposition: RewriteAttemptDisposition::Applicable,
            proof,
            replacement_requirements,
            replacement_support,
        },
        plan: Some(plan),
    }
}

fn node_kind_proof(
    node_id: NodeId,
    expected: SemanticNodeKind,
    actual: Option<SemanticNodeKind>,
) -> RewriteProofEvaluation {
    match actual {
        Some(actual) => RewriteProofEvaluation {
            precondition: if expected == SemanticNodeKind::Atomic {
                RewriteProofPrecondition::OriginalNodeKind {
                    node_id: node_id.clone(),
                    expected,
                }
            } else {
                RewriteProofPrecondition::BodyNodeKind {
                    node_id: node_id.clone(),
                    expected,
                }
            },
            evidence: RewriteProofEvidence::FoundationalNodeKind { node_id, actual },
            disposition: if actual == expected {
                RewriteProofDisposition::Satisfied
            } else {
                RewriteProofDisposition::Failed
            },
        },
        None => RewriteProofEvaluation {
            precondition: if expected == SemanticNodeKind::Atomic {
                RewriteProofPrecondition::OriginalNodeKind {
                    node_id: node_id.clone(),
                    expected,
                }
            } else {
                RewriteProofPrecondition::BodyNodeKind {
                    node_id: node_id.clone(),
                    expected,
                }
            },
            evidence: RewriteProofEvidence::MissingCertifiedFact { node_id },
            disposition: RewriteProofDisposition::Indeterminate,
        },
    }
}

fn proof_attempt_disposition(proof: &[RewriteProofEvaluation]) -> RewriteAttemptDisposition {
    if proof
        .iter()
        .any(|evaluation| evaluation.disposition == RewriteProofDisposition::Indeterminate)
    {
        RewriteAttemptDisposition::ProofIndeterminate
    } else if proof
        .iter()
        .any(|evaluation| evaluation.disposition == RewriteProofDisposition::Failed)
    {
        RewriteAttemptDisposition::ProofFailed
    } else {
        RewriteAttemptDisposition::Applicable
    }
}

fn resolve_replacement_support(
    requirements: &[SemanticRequirement],
    evaluation: &CapabilityEvaluation,
) -> ReplacementSupportOutcome {
    let mut evidence = Vec::with_capacity(requirements.len());
    for requirement in requirements {
        let Some(result) = evaluation
            .results
            .iter()
            .find(|result| result.requirement == *requirement)
            .cloned()
        else {
            return ReplacementSupportOutcome::Unknown(evidence);
        };
        let disposition = result.disposition;
        evidence.push(ReplacementCapabilityEvidence {
            requirement: requirement.clone(),
            capability_result: result,
        });
        match replacement_failure(disposition) {
            Some(RewriteAttemptDisposition::ReplacementUnsupported) => {
                return ReplacementSupportOutcome::Unsupported(evidence);
            }
            Some(RewriteAttemptDisposition::ReplacementUnknown) => {
                return ReplacementSupportOutcome::Unknown(evidence);
            }
            Some(_) | None => {}
        }
    }
    ReplacementSupportOutcome::Supported(evidence)
}

fn replacement_failure(disposition: CapabilityDisposition) -> Option<RewriteAttemptDisposition> {
    match disposition {
        CapabilityDisposition::Supported => None,
        CapabilityDisposition::Unsupported | CapabilityDisposition::ConstraintViolation => {
            Some(RewriteAttemptDisposition::ReplacementUnsupported)
        }
        CapabilityDisposition::Unknown => Some(RewriteAttemptDisposition::ReplacementUnknown),
    }
}

fn registry_error(error: RewriteRegistryError) -> PortabilityPlanningErrors {
    PortabilityPlanningErrors::single(PortabilityPlanningError::new(
        PortabilityPlanningErrorCode::InvalidRewriteRegistry,
        "$.rewrite_registry",
        error.message,
    ))
}

fn find_node<'a>(root: &'a Node, node_id: &NodeId) -> Option<&'a Node> {
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        if node.node_id() == node_id {
            return Some(node);
        }
        match node {
            Node::Sequence { items, .. } => pending.extend(items.iter().rev()),
            Node::Alternation { branches, .. } => pending.extend(branches.iter().rev()),
            Node::Repeat { body, .. }
            | Node::Capture { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => pending.push(body),
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

#[cfg(test)]
mod rewrite_proof_tests {
    use super::*;

    fn node_id(value: &str) -> NodeId {
        NodeId::try_from(value).expect("test node identity")
    }

    #[test]
    fn missing_certified_node_kind_is_indeterminate_proof() {
        let evaluation = node_kind_proof(
            node_id("node:proof.missing"),
            SemanticNodeKind::Literal,
            None,
        );

        assert_eq!(
            evaluation.disposition,
            RewriteProofDisposition::Indeterminate
        );
        assert!(matches!(
            evaluation.evidence,
            RewriteProofEvidence::MissingCertifiedFact { .. }
        ));
        assert_eq!(
            proof_attempt_disposition(&[evaluation]),
            RewriteAttemptDisposition::ProofIndeterminate
        );
    }

    #[test]
    fn replacement_support_classifier_rejects_negative_and_unknown_results() {
        assert_eq!(
            replacement_failure(CapabilityDisposition::Unsupported),
            Some(RewriteAttemptDisposition::ReplacementUnsupported)
        );
        assert_eq!(
            replacement_failure(CapabilityDisposition::ConstraintViolation),
            Some(RewriteAttemptDisposition::ReplacementUnsupported)
        );
        assert_eq!(
            replacement_failure(CapabilityDisposition::Unknown),
            Some(RewriteAttemptDisposition::ReplacementUnknown)
        );
        assert_eq!(replacement_failure(CapabilityDisposition::Supported), None);
    }
}
