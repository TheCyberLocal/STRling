//! Versioned, deterministic explanations projected from completed canonical stages.
//!
//! This module is deliberately a projection boundary. It consumes Semantic IR,
//! certified analysis stores, evidence-bearing diagnostics, and completed target
//! plans. It never parses source syntax, reruns analysis, or infers semantics from
//! emitted target patterns.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::capability_evaluation::{
    CapabilityDisposition, CapabilityEvaluation, CapabilityResult, ConstraintDisposition,
    ConstraintEvidence,
};
use crate::diagnostic::{validate_diagnostic_order, Diagnostic};
use crate::diagnostic_generation::DiagnosticGeneration;
use crate::portability_planning::{
    PlannedRequirement, PortabilityPlan, RequirementPlanningDisposition, RewriteAttempt,
    RewriteAttemptDisposition, RewriteProofDisposition, UnresolvedPlanningReason,
};
use crate::safety_analysis::{
    validate_analysis, validate_foundational_correspondence, validate_structural_correspondence,
    SafetyAnalysis, SafetyAnalysisErrors, SafetyFindingCategory, SafetyFindingCode,
    SafetyProofStatus, SafetyUncertaintyCode, SafetyUncertaintyReason,
};
use crate::semantic::{
    AssertionPolarity, CaseMatching, CharacterSetMember, LineTerminators, LookaroundDirection,
    Node, PositionKind, RepetitionMaximum, RepetitionMode, SemanticProgram,
};
use crate::semantic_analysis::{
    Consumption, MaximumConsumption, NodeFacts, Nullability, SemanticFacts,
};
use crate::source::{
    CaptureId, ContractVersion, NodeId, Sha256Digest, SourceId, SourceOrigin, SourceSpan,
    SpecificationVersion,
};
use crate::structural_analysis::{
    AlternationBranchOverlap, LeadingTerm, LeadingUnknownReason, LengthClassification,
    NodeStructuralFacts, OverlapRelation, OverlapUnknownReason, ProgressClassification,
    RepetitionExtent, RepetitionFollowOverlap, StructuralFacts,
};
use crate::target::{
    CapabilityAvailability, CapabilityConstraint, CapabilityId, EngineIdentity, PortabilityStatus,
    RuntimeIdentity, TargetProfileReference,
};
use crate::validation::{canonical_sha256, Validate};

/// Current independent semantic-explanation model version.
pub const SEMANTIC_EXPLANATION_MODEL_VERSION: &str = "1.0.0";

/// The closed model-version vocabulary implemented by this kernel.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum ExplanationModelVersion {
    #[serde(rename = "1.0.0")]
    V1_0_0,
}

/// Whether an entity is fact, a completed target decision, advice, or uncertainty.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceClass {
    SemanticFact,
    TargetPlan,
    DiagnosticAdvice,
    Uncertainty,
}

/// Whether the semantic program carries source documents.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SourceMode {
    SourceLess,
    ProvenanceAvailable,
}

/// Stable source and derivation evidence for one explanation entity.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SourceLink {
    pub source_spans: Vec<SourceSpan>,
    pub derived_from_node_ids: Vec<NodeId>,
}

/// Finite or unbounded successful-consumption maximum.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum LengthMaximumExplanation {
    Bounded { value: u64 },
    Unbounded,
}

/// Target-neutral foundational facts for one semantic node.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NodeFactExplanation {
    pub nullability: NullabilityExplanation,
    pub minimum_consumption: u64,
    pub maximum_consumption: LengthMaximumExplanation,
    pub consumption: ConsumptionExplanation,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NullabilityExplanation {
    Nullable,
    NonNullable,
    Unknown,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ConsumptionExplanation {
    AlwaysZeroWidth,
    AlwaysConsuming,
    Variable,
    Indeterminate,
}

/// Concise target projection, derived from the detailed target entities.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConciseTargetExplanation {
    pub target_profile: TargetProfileReference,
    pub status: TargetExplanationStatus,
    pub decision_count: usize,
    pub unresolved_count: usize,
    pub diagnostic_count: usize,
}

/// Bounded program summary suitable for concise rendering.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConciseExplanation {
    pub evidence_class: EvidenceClass,
    pub root_node_id: NodeId,
    pub source_mode: SourceMode,
    pub node_count: usize,
    pub capture_count: usize,
    pub backreference_count: usize,
    pub safety_finding_count: usize,
    pub uncertainty_count: usize,
    pub diagnostic_count: usize,
    pub root_facts: NodeFactExplanation,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub target: Option<ConciseTargetExplanation>,
}

/// Program-wide target-neutral context.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProgramExplanation {
    pub evidence_class: EvidenceClass,
    pub root_node_id: NodeId,
    pub case_matching: CaseMatching,
    pub source_mode: SourceMode,
    pub source_ids: Vec<SourceId>,
}

/// Semantic shape with child objects replaced by stable node identities.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum NodeSemanticExplanation {
    Empty,
    Sequence {
        items: Vec<NodeId>,
    },
    Alternation {
        branches: Vec<NodeId>,
    },
    Literal {
        text: String,
    },
    Wildcard {
        line_terminators: LineTerminators,
    },
    CharacterSet {
        negated: bool,
        members: Vec<CharacterSetMember>,
    },
    Repeat {
        body_node_id: NodeId,
        minimum: u64,
        maximum: LengthMaximumExplanation,
        mode: RepetitionMode,
    },
    Position {
        position: PositionKind,
    },
    Capture {
        capture_id: CaptureId,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        body_node_id: NodeId,
    },
    Backreference {
        capture_id: CaptureId,
        definition_node_id: NodeId,
    },
    Lookaround {
        direction: LookaroundDirection,
        polarity: AssertionPolarity,
        body_node_id: NodeId,
    },
    Atomic {
        body_node_id: NodeId,
    },
}

/// Leading-consumption possibilities, retaining explicit unknowns.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum LeadingTermExplanation {
    Empty,
    Scalar {
        value: String,
    },
    CharacterSet {
        negated: bool,
        members: Vec<CharacterSetMember>,
    },
    Wildcard {
        line_terminators: LineTerminators,
    },
    Unknown {
        reason: LeadingUnknownReasonExplanation,
        #[serde(skip_serializing_if = "Option::is_none")]
        node_id: Option<NodeId>,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LeadingUnknownReasonExplanation {
    Backreference,
    NullablePrefix,
    Nullability,
    TermLimitExceeded,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum LengthClassificationExplanation {
    Fixed { value: u64 },
    FiniteVariable,
    Unbounded,
    Indeterminate,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum OverlapExplanation {
    Disjoint,
    Overlapping,
    Unknown {
        reason: OverlapUnknownReasonExplanation,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum OverlapUnknownReasonExplanation {
    LeadingUnknown,
    CaseFolding,
    CharacterCategory,
    LineTerminatorExclusion,
    ComparisonLimitExceeded,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RepetitionStructuralExplanation {
    pub body_node_id: NodeId,
    pub extent: RepetitionExtent,
    pub operand_progress: ProgressClassification,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct AlternationOverlapExplanation {
    pub left_branch_index: usize,
    pub left_node_id: NodeId,
    pub right_branch_index: usize,
    pub right_node_id: NodeId,
    pub relation: OverlapExplanation,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RepetitionFollowerOverlapExplanation {
    pub repetition_index: usize,
    pub repetition_node_id: NodeId,
    pub operand_node_id: NodeId,
    pub following_index: usize,
    pub following_node_id: NodeId,
    pub relation: OverlapExplanation,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StructuralExplanation {
    pub leading_consumption: Vec<LeadingTermExplanation>,
    pub length: LengthClassificationExplanation,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub repetition: Option<RepetitionStructuralExplanation>,
    pub alternation_branch_overlaps: Vec<AlternationOverlapExplanation>,
    pub repetition_follower_overlaps: Vec<RepetitionFollowerOverlapExplanation>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NodeExplanation {
    pub evidence_class: EvidenceClass,
    pub node_id: NodeId,
    pub source: SourceLink,
    pub semantic: NodeSemanticExplanation,
    pub facts: NodeFactExplanation,
    pub structural: StructuralExplanation,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CaptureExplanation {
    pub evidence_class: EvidenceClass,
    pub capture_id: CaptureId,
    pub definition_node_id: NodeId,
    pub body_node_id: NodeId,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    pub reference_node_ids: Vec<NodeId>,
    pub source: SourceLink,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SafetyExplanation {
    pub evidence_class: EvidenceClass,
    pub code: SafetyFindingCode,
    pub category: SafetyFindingCategory,
    pub primary_node_id: NodeId,
    pub contributing_node_ids: Vec<NodeId>,
    pub proof: SafetyProofStatus,
    pub source: SourceLink,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum UncertaintyReasonExplanation {
    IndeterminateProgress,
    UnknownLeadingConsumption,
    NullableOnlyOverlap,
    StructuralOverlapLeadingUnknown,
    StructuralOverlapCaseFolding,
    StructuralOverlapCharacterCategory,
    StructuralOverlapLineTerminatorExclusion,
    StructuralOverlapComparisonLimitExceeded,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct UncertaintyExplanation {
    pub evidence_class: EvidenceClass,
    pub code: SafetyUncertaintyCode,
    pub reason: UncertaintyReasonExplanation,
    pub primary_node_id: NodeId,
    pub contributing_node_ids: Vec<NodeId>,
    pub source: SourceLink,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DiagnosticExplanation {
    pub evidence_class: EvidenceClass,
    pub diagnostic: Diagnostic,
    pub primary_node_id: NodeId,
    pub contributing_node_ids: Vec<NodeId>,
    pub source: SourceLink,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ConstraintDispositionExplanation {
    Satisfied,
    Violated,
    Unknown,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ConstraintEvidenceExplanation {
    RequirementFact,
    ProfileOption,
    MissingRequirementFact,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConstraintExplanation {
    pub constraint: CapabilityConstraint,
    pub disposition: ConstraintDispositionExplanation,
    pub evidence: ConstraintEvidenceExplanation,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RewriteAttemptDispositionExplanation {
    NotApplicable,
    ProofFailed,
    ProofIndeterminate,
    ReplacementUnsupported,
    ReplacementUnknown,
    Applicable,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteAttemptExplanation {
    pub strategy_id: String,
    pub disposition: RewriteAttemptDispositionExplanation,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ProofDispositionExplanation {
    Satisfied,
    Failed,
    Indeterminate,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum TargetOutcomeExplanation {
    Native,
    EquivalentRewrite {
        strategy_id: String,
        affected_node_ids: Vec<NodeId>,
        dependency_ordinals: Vec<u32>,
        proof_dispositions: Vec<ProofDispositionExplanation>,
    },
    Unsupported {
        rewrite_attempts: Vec<RewriteAttemptExplanation>,
    },
    Unresolved {
        reason: UnresolvedReasonExplanation,
        rewrite_attempts: Vec<RewriteAttemptExplanation>,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum UnresolvedReasonExplanation {
    CapabilityUnknown,
    RewriteProofIndeterminate,
    ReplacementCapabilityUnknown,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CapabilityAvailabilityExplanation {
    Available,
    Constrained,
    Unavailable,
    Unknown,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CapabilityDispositionExplanation {
    Supported,
    Unsupported,
    ConstraintViolation,
    Unknown,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TargetDecisionExplanation {
    pub ordinal: u32,
    pub evidence_class: EvidenceClass,
    pub node_id: NodeId,
    pub capability_id: CapabilityId,
    pub capability_availability: CapabilityAvailabilityExplanation,
    pub capability_disposition: CapabilityDispositionExplanation,
    pub constraints: Vec<ConstraintExplanation>,
    pub outcome: TargetOutcomeExplanation,
    pub source: SourceLink,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TargetExplanationStatus {
    Native,
    EquivalentRewrite,
    Unsupported,
    Unresolved,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TargetExplanation {
    pub evidence_class: EvidenceClass,
    pub target_profile: TargetProfileReference,
    pub engine: EngineIdentity,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime: Option<RuntimeIdentity>,
    pub status: TargetExplanationStatus,
    pub decisions: Vec<TargetDecisionExplanation>,
    pub diagnostics: Vec<DiagnosticExplanation>,
}

/// Complete structured explanation object. Generated text views are not stored here.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExplanationDocument {
    pub model_version: ExplanationModelVersion,
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub semantic_program: Sha256Digest,
    pub concise: ConciseExplanation,
    pub program: ProgramExplanation,
    pub nodes: Vec<NodeExplanation>,
    pub captures: Vec<CaptureExplanation>,
    pub safety_findings: Vec<SafetyExplanation>,
    pub uncertainties: Vec<UncertaintyExplanation>,
    pub diagnostics: Vec<DiagnosticExplanation>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub target: Option<TargetExplanation>,
}

/// Stable categories for explanation projection failures.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ExplanationErrorCode {
    InvalidPrerequisite,
    MissingNode,
    MismatchedDiagnosticEvidence,
    MismatchedCapabilityEvaluation,
    MismatchedPortabilityPlan,
    SerializationInvariant,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExplanationError {
    pub code: ExplanationErrorCode,
    pub path: String,
    pub message: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExplanationErrors {
    pub errors: Vec<ExplanationError>,
}

impl ExplanationErrors {
    fn single(
        code: ExplanationErrorCode,
        path: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            errors: vec![ExplanationError {
                code,
                path: path.into(),
                message: message.into(),
            }],
        }
    }

    fn from_safety(errors: SafetyAnalysisErrors) -> Self {
        Self {
            errors: errors
                .errors
                .into_iter()
                .map(|error| ExplanationError {
                    code: ExplanationErrorCode::InvalidPrerequisite,
                    path: error.path,
                    message: error.message,
                })
                .collect(),
        }
    }
}

impl fmt::Display for ExplanationErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} explanation projection error(s)",
            self.errors.len()
        )
    }
}

impl Error for ExplanationErrors {}

/// Project one exact completed target-neutral pipeline into the semantic model.
pub fn explain_semantics(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    safety: &SafetyAnalysis,
    generation: &DiagnosticGeneration,
) -> Result<ExplanationDocument, ExplanationErrors> {
    input.validate().map_err(|errors| ExplanationErrors {
        errors: errors
            .errors
            .into_iter()
            .map(|error| ExplanationError {
                code: ExplanationErrorCode::InvalidPrerequisite,
                path: error.path,
                message: error.message,
            })
            .collect(),
    })?;
    validate_foundational_correspondence(input, foundational)
        .map_err(ExplanationErrors::from_safety)?;
    validate_structural_correspondence(input, structural)
        .map_err(ExplanationErrors::from_safety)?;
    validate_analysis(input, structural, safety).map_err(ExplanationErrors::from_safety)?;
    if generation.program_identity() != Some(foundational.program_identity()) {
        return Err(ExplanationErrors::single(
            ExplanationErrorCode::MismatchedDiagnosticEvidence,
            "$.diagnostics",
            "diagnostic generation was not produced for this exact semantic program",
        ));
    }

    let node_index = index_nodes(&input.root);
    validate_generation(&node_index, generation)?;
    let semantic_program = Sha256Digest::from_bytes(canonical_sha256(input).map_err(|error| {
        ExplanationErrors::single(
            ExplanationErrorCode::SerializationInvariant,
            "$",
            format!("semantic program fingerprint could not be derived: {error}"),
        )
    })?);

    let nodes = foundational
        .iter()
        .map(|(node_id, facts)| {
            let node = node_index.get(node_id).ok_or_else(|| {
                ExplanationErrors::single(
                    ExplanationErrorCode::MissingNode,
                    "$.nodes",
                    format!("foundational facts reference missing node {node_id:?}"),
                )
            })?;
            let structural_facts = structural.get(node_id).ok_or_else(|| {
                ExplanationErrors::single(
                    ExplanationErrorCode::MissingNode,
                    "$.nodes",
                    format!("structural facts omit node {node_id:?}"),
                )
            })?;
            Ok(NodeExplanation {
                evidence_class: EvidenceClass::SemanticFact,
                node_id: node_id.clone(),
                source: source_link(node.origin()),
                semantic: semantic_explanation(node, foundational)?,
                facts: fact_explanation(facts),
                structural: structural_explanation(structural_facts),
            })
        })
        .collect::<Result<Vec<_>, ExplanationErrors>>()?;

    let captures = foundational
        .capture_definitions()
        .map(|(capture_id, definition)| {
            let definition_node =
                node_index
                    .get(&definition.definition_node_id)
                    .ok_or_else(|| {
                        ExplanationErrors::single(
                            ExplanationErrorCode::MissingNode,
                            "$.captures",
                            "capture definition node is missing",
                        )
                    })?;
            let reference_node_ids = foundational
                .backreferences()
                .filter(|(_, resolution)| &resolution.capture_id == capture_id)
                .map(|(node_id, _)| node_id.clone())
                .collect();
            Ok(CaptureExplanation {
                evidence_class: EvidenceClass::SemanticFact,
                capture_id: capture_id.clone(),
                definition_node_id: definition.definition_node_id.clone(),
                body_node_id: definition.body_node_id.clone(),
                name: definition.name.clone(),
                reference_node_ids,
                source: source_link(definition_node.origin()),
            })
        })
        .collect::<Result<Vec<_>, ExplanationErrors>>()?;

    let safety_findings = safety
        .findings()
        .map(|finding| {
            let contributing_node_ids = evidence_nodes(
                &finding.primary_node_id,
                finding.evidence_node_ids.iter().cloned(),
            );
            SafetyExplanation {
                evidence_class: EvidenceClass::SemanticFact,
                code: finding.code,
                category: finding.category,
                primary_node_id: finding.primary_node_id.clone(),
                source: aggregate_source_link(&node_index, &contributing_node_ids),
                contributing_node_ids,
                proof: finding.proof,
            }
        })
        .collect::<Vec<_>>();
    let uncertainties = safety
        .uncertainties()
        .map(|uncertainty| {
            let contributing_node_ids = evidence_nodes(
                &uncertainty.primary_node_id,
                uncertainty.evidence_node_ids.iter().cloned(),
            );
            UncertaintyExplanation {
                evidence_class: EvidenceClass::Uncertainty,
                code: uncertainty.code,
                reason: uncertainty_reason(uncertainty.reason),
                primary_node_id: uncertainty.primary_node_id.clone(),
                source: aggregate_source_link(&node_index, &contributing_node_ids),
                contributing_node_ids,
            }
        })
        .collect::<Vec<_>>();
    let diagnostics = generation
        .records()
        .map(|record| {
            let contributing_node_ids = evidence_nodes(
                &record.provenance.primary_node_id,
                record.provenance.contributing_node_ids.iter().cloned(),
            );
            DiagnosticExplanation {
                evidence_class: EvidenceClass::DiagnosticAdvice,
                diagnostic: record.diagnostic.clone(),
                primary_node_id: record.provenance.primary_node_id.clone(),
                source: aggregate_source_link(&node_index, &contributing_node_ids),
                contributing_node_ids,
            }
        })
        .collect::<Vec<_>>();

    let root_facts = foundational.get(input.root.node_id()).ok_or_else(|| {
        ExplanationErrors::single(
            ExplanationErrorCode::MissingNode,
            "$.concise.root_facts",
            "root foundational facts are missing",
        )
    })?;
    let source_mode = source_mode(input);
    let source_ids = input
        .sources
        .as_ref()
        .map(|sources| {
            sources
                .iter()
                .map(|source| source.source_id.clone())
                .collect()
        })
        .unwrap_or_default();
    let backreference_count = foundational.backreferences().len();

    Ok(ExplanationDocument {
        model_version: ExplanationModelVersion::V1_0_0,
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        semantic_program,
        concise: ConciseExplanation {
            evidence_class: EvidenceClass::SemanticFact,
            root_node_id: input.root.node_id().clone(),
            source_mode,
            node_count: nodes.len(),
            capture_count: captures.len(),
            backreference_count,
            safety_finding_count: safety_findings.len(),
            uncertainty_count: uncertainties.len(),
            diagnostic_count: diagnostics.len(),
            root_facts: fact_explanation(root_facts),
            target: None,
        },
        program: ProgramExplanation {
            evidence_class: EvidenceClass::SemanticFact,
            root_node_id: input.root.node_id().clone(),
            case_matching: input.case_matching,
            source_mode,
            source_ids,
        },
        nodes,
        captures,
        safety_findings,
        uncertainties,
        diagnostics,
        target: None,
    })
}

/// Add a target section from an already-completed evaluation and plan.
pub fn explain_target(
    semantic: &ExplanationDocument,
    evaluation: &CapabilityEvaluation,
    plan: &PortabilityPlan,
) -> Result<ExplanationDocument, ExplanationErrors> {
    validate_target_correspondence(semantic, evaluation, plan)?;
    let node_sources: BTreeMap<_, _> = semantic
        .nodes
        .iter()
        .map(|node| (node.node_id.clone(), node.source.clone()))
        .collect();
    let decisions = plan
        .decisions
        .iter()
        .enumerate()
        .map(|(index, decision)| target_decision(index, decision, plan, &node_sources))
        .collect::<Result<Vec<_>, ExplanationErrors>>()?;
    let unresolved_count = decisions
        .iter()
        .filter(|decision| {
            matches!(
                decision.outcome,
                TargetOutcomeExplanation::Unresolved { .. }
            )
        })
        .count();
    let status = if unresolved_count > 0 {
        TargetExplanationStatus::Unresolved
    } else {
        target_status(plan.status)
    };
    let target = TargetExplanation {
        evidence_class: EvidenceClass::TargetPlan,
        target_profile: plan.target_profile.clone(),
        engine: evaluation.target_engine.clone(),
        runtime: evaluation.target_runtime.clone(),
        status,
        decisions,
        // Current portability diagnostics do not retain stable node provenance.
        // The evidence-bearing plan is complete; do not attach diagnostics by
        // guessing from prose or source spans.
        diagnostics: Vec::new(),
    };
    let concise_target = ConciseTargetExplanation {
        target_profile: target.target_profile.clone(),
        status: target.status,
        decision_count: target.decisions.len(),
        unresolved_count,
        diagnostic_count: target.diagnostics.len(),
    };
    let mut document = semantic.clone();
    document.concise.target = Some(concise_target);
    document.target = Some(target);
    Ok(document)
}

fn index_nodes(root: &Node) -> BTreeMap<NodeId, &Node> {
    let mut index = BTreeMap::new();
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        index.insert(node.node_id().clone(), node);
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
    index
}

fn validate_generation(
    nodes: &BTreeMap<NodeId, &Node>,
    generation: &DiagnosticGeneration,
) -> Result<(), ExplanationErrors> {
    let diagnostics = generation.diagnostics().cloned().collect::<Vec<_>>();
    validate_diagnostic_order(&diagnostics).map_err(|errors| ExplanationErrors {
        errors: errors
            .errors
            .into_iter()
            .map(|error| ExplanationError {
                code: ExplanationErrorCode::MismatchedDiagnosticEvidence,
                path: error.path,
                message: error.message,
            })
            .collect(),
    })?;
    for (index, record) in generation.records().enumerate() {
        let mut referenced = record.provenance.contributing_node_ids.clone();
        referenced.push(record.provenance.primary_node_id.clone());
        for node_id in referenced {
            if !nodes.contains_key(&node_id) {
                return Err(ExplanationErrors::single(
                    ExplanationErrorCode::MismatchedDiagnosticEvidence,
                    format!("$.diagnostics[{index}]"),
                    format!("diagnostic provenance references missing node {node_id:?}"),
                ));
            }
        }
        for origin in &record.provenance.source_origins {
            let expected = nodes.get(&origin.node_id).and_then(|node| node.origin());
            if expected != Some(&origin.origin) {
                return Err(ExplanationErrors::single(
                    ExplanationErrorCode::MismatchedDiagnosticEvidence,
                    format!("$.diagnostics[{index}].source"),
                    "diagnostic source provenance does not match Semantic IR",
                ));
            }
        }
    }
    Ok(())
}

fn semantic_explanation(
    node: &Node,
    foundational: &SemanticFacts,
) -> Result<NodeSemanticExplanation, ExplanationErrors> {
    Ok(match node {
        Node::Empty { .. } => NodeSemanticExplanation::Empty,
        Node::Sequence { items, .. } => NodeSemanticExplanation::Sequence {
            items: items.iter().map(|item| item.node_id().clone()).collect(),
        },
        Node::Alternation { branches, .. } => NodeSemanticExplanation::Alternation {
            branches: branches
                .iter()
                .map(|branch| branch.node_id().clone())
                .collect(),
        },
        Node::Literal { text, .. } => NodeSemanticExplanation::Literal { text: text.clone() },
        Node::Wildcard {
            line_terminators, ..
        } => NodeSemanticExplanation::Wildcard {
            line_terminators: *line_terminators,
        },
        Node::CharacterSet {
            negated, members, ..
        } => NodeSemanticExplanation::CharacterSet {
            negated: *negated,
            members: members.clone(),
        },
        Node::Repeat {
            body,
            min,
            max,
            mode,
            ..
        } => NodeSemanticExplanation::Repeat {
            body_node_id: body.node_id().clone(),
            minimum: *min,
            maximum: repetition_maximum(*max),
            mode: *mode,
        },
        Node::Position { position, .. } => NodeSemanticExplanation::Position {
            position: *position,
        },
        Node::Capture {
            capture_id,
            name,
            body,
            ..
        } => NodeSemanticExplanation::Capture {
            capture_id: capture_id.clone(),
            name: name.clone(),
            body_node_id: body.node_id().clone(),
        },
        Node::Backreference {
            node_id,
            capture_id,
            ..
        } => {
            let resolution = foundational.backreference(node_id).ok_or_else(|| {
                ExplanationErrors::single(
                    ExplanationErrorCode::InvalidPrerequisite,
                    "$.nodes",
                    "backreference resolution is missing",
                )
            })?;
            NodeSemanticExplanation::Backreference {
                capture_id: capture_id.clone(),
                definition_node_id: resolution.definition_node_id.clone(),
            }
        }
        Node::Lookaround {
            direction,
            polarity,
            body,
            ..
        } => NodeSemanticExplanation::Lookaround {
            direction: *direction,
            polarity: *polarity,
            body_node_id: body.node_id().clone(),
        },
        Node::Atomic { body, .. } => NodeSemanticExplanation::Atomic {
            body_node_id: body.node_id().clone(),
        },
    })
}

fn fact_explanation(facts: &NodeFacts) -> NodeFactExplanation {
    NodeFactExplanation {
        nullability: match facts.nullability {
            Nullability::Nullable => NullabilityExplanation::Nullable,
            Nullability::NonNullable => NullabilityExplanation::NonNullable,
            Nullability::Unknown => NullabilityExplanation::Unknown,
        },
        minimum_consumption: facts.minimum_consumption,
        maximum_consumption: match facts.maximum_consumption {
            MaximumConsumption::Finite(value) => LengthMaximumExplanation::Bounded { value },
            MaximumConsumption::Unbounded => LengthMaximumExplanation::Unbounded,
        },
        consumption: match facts.consumption {
            Consumption::AlwaysZeroWidth => ConsumptionExplanation::AlwaysZeroWidth,
            Consumption::AlwaysConsuming => ConsumptionExplanation::AlwaysConsuming,
            Consumption::Variable => ConsumptionExplanation::Variable,
            Consumption::Indeterminate => ConsumptionExplanation::Indeterminate,
        },
    }
}

fn structural_explanation(facts: &NodeStructuralFacts) -> StructuralExplanation {
    StructuralExplanation {
        leading_consumption: facts
            .leading_consumption
            .iter()
            .map(leading_explanation)
            .collect(),
        length: length_explanation(facts.length),
        repetition: facts
            .repetition
            .as_ref()
            .map(|repetition| RepetitionStructuralExplanation {
                body_node_id: repetition.body_node_id.clone(),
                extent: repetition.extent,
                operand_progress: repetition.operand_progress,
            }),
        alternation_branch_overlaps: facts
            .alternation_branch_overlaps
            .iter()
            .map(alternation_overlap)
            .collect(),
        repetition_follower_overlaps: facts
            .repetition_follow_overlaps
            .iter()
            .map(repetition_follower_overlap)
            .collect(),
    }
}

fn leading_explanation(term: &LeadingTerm) -> LeadingTermExplanation {
    match term {
        LeadingTerm::Empty => LeadingTermExplanation::Empty,
        LeadingTerm::Scalar(value) => LeadingTermExplanation::Scalar {
            value: value.to_string(),
        },
        LeadingTerm::CharacterSet { negated, members } => LeadingTermExplanation::CharacterSet {
            negated: *negated,
            members: members.clone(),
        },
        LeadingTerm::Wildcard { line_terminators } => LeadingTermExplanation::Wildcard {
            line_terminators: *line_terminators,
        },
        LeadingTerm::Unknown(reason) => {
            let (reason, node_id) = match reason {
                LeadingUnknownReason::Backreference { node_id } => (
                    LeadingUnknownReasonExplanation::Backreference,
                    Some(node_id.clone()),
                ),
                LeadingUnknownReason::NullablePrefix { node_id } => (
                    LeadingUnknownReasonExplanation::NullablePrefix,
                    Some(node_id.clone()),
                ),
                LeadingUnknownReason::Nullability { node_id } => (
                    LeadingUnknownReasonExplanation::Nullability,
                    Some(node_id.clone()),
                ),
                LeadingUnknownReason::TermLimitExceeded => {
                    (LeadingUnknownReasonExplanation::TermLimitExceeded, None)
                }
            };
            LeadingTermExplanation::Unknown { reason, node_id }
        }
    }
}

fn length_explanation(length: LengthClassification) -> LengthClassificationExplanation {
    match length {
        LengthClassification::Fixed(value) => LengthClassificationExplanation::Fixed { value },
        LengthClassification::FiniteVariable => LengthClassificationExplanation::FiniteVariable,
        LengthClassification::Unbounded => LengthClassificationExplanation::Unbounded,
        LengthClassification::Indeterminate => LengthClassificationExplanation::Indeterminate,
    }
}

fn overlap_explanation(relation: OverlapRelation) -> OverlapExplanation {
    match relation {
        OverlapRelation::Disjoint => OverlapExplanation::Disjoint,
        OverlapRelation::Overlapping => OverlapExplanation::Overlapping,
        OverlapRelation::Unknown(reason) => OverlapExplanation::Unknown {
            reason: match reason {
                OverlapUnknownReason::LeadingUnknown => {
                    OverlapUnknownReasonExplanation::LeadingUnknown
                }
                OverlapUnknownReason::CaseFolding => OverlapUnknownReasonExplanation::CaseFolding,
                OverlapUnknownReason::CharacterCategory => {
                    OverlapUnknownReasonExplanation::CharacterCategory
                }
                OverlapUnknownReason::LineTerminatorExclusion => {
                    OverlapUnknownReasonExplanation::LineTerminatorExclusion
                }
                OverlapUnknownReason::ComparisonLimitExceeded => {
                    OverlapUnknownReasonExplanation::ComparisonLimitExceeded
                }
            },
        },
    }
}

fn alternation_overlap(value: &AlternationBranchOverlap) -> AlternationOverlapExplanation {
    AlternationOverlapExplanation {
        left_branch_index: value.left_branch_index,
        left_node_id: value.left_node_id.clone(),
        right_branch_index: value.right_branch_index,
        right_node_id: value.right_node_id.clone(),
        relation: overlap_explanation(value.relation),
    }
}

fn repetition_follower_overlap(
    value: &RepetitionFollowOverlap,
) -> RepetitionFollowerOverlapExplanation {
    RepetitionFollowerOverlapExplanation {
        repetition_index: value.repetition_index,
        repetition_node_id: value.repetition_node_id.clone(),
        operand_node_id: value.operand_node_id.clone(),
        following_index: value.following_index,
        following_node_id: value.following_node_id.clone(),
        relation: overlap_explanation(value.relation),
    }
}

fn repetition_maximum(maximum: RepetitionMaximum) -> LengthMaximumExplanation {
    match maximum {
        RepetitionMaximum::Bounded(value) => LengthMaximumExplanation::Bounded { value },
        RepetitionMaximum::Unbounded => LengthMaximumExplanation::Unbounded,
    }
}

fn uncertainty_reason(reason: SafetyUncertaintyReason) -> UncertaintyReasonExplanation {
    match reason {
        SafetyUncertaintyReason::IndeterminateProgress => {
            UncertaintyReasonExplanation::IndeterminateProgress
        }
        SafetyUncertaintyReason::UnknownLeadingConsumption => {
            UncertaintyReasonExplanation::UnknownLeadingConsumption
        }
        SafetyUncertaintyReason::NullableOnlyOverlap => {
            UncertaintyReasonExplanation::NullableOnlyOverlap
        }
        SafetyUncertaintyReason::StructuralOverlap(reason) => match reason {
            OverlapUnknownReason::LeadingUnknown => {
                UncertaintyReasonExplanation::StructuralOverlapLeadingUnknown
            }
            OverlapUnknownReason::CaseFolding => {
                UncertaintyReasonExplanation::StructuralOverlapCaseFolding
            }
            OverlapUnknownReason::CharacterCategory => {
                UncertaintyReasonExplanation::StructuralOverlapCharacterCategory
            }
            OverlapUnknownReason::LineTerminatorExclusion => {
                UncertaintyReasonExplanation::StructuralOverlapLineTerminatorExclusion
            }
            OverlapUnknownReason::ComparisonLimitExceeded => {
                UncertaintyReasonExplanation::StructuralOverlapComparisonLimitExceeded
            }
        },
    }
}

fn source_mode(input: &SemanticProgram) -> SourceMode {
    if input.sources.as_ref().map_or(true, Vec::is_empty) {
        SourceMode::SourceLess
    } else {
        SourceMode::ProvenanceAvailable
    }
}

fn source_link(origin: Option<&SourceOrigin>) -> SourceLink {
    SourceLink {
        source_spans: origin
            .and_then(|origin| origin.source_spans.clone())
            .unwrap_or_default(),
        derived_from_node_ids: origin
            .and_then(|origin| origin.derived_from_node_ids.clone())
            .unwrap_or_default(),
    }
}

fn aggregate_source_link(nodes: &BTreeMap<NodeId, &Node>, node_ids: &[NodeId]) -> SourceLink {
    let mut source_spans = BTreeSet::new();
    let mut derived_from_node_ids = BTreeSet::new();
    for node_id in node_ids {
        if let Some(origin) = nodes.get(node_id).and_then(|node| node.origin()) {
            if let Some(spans) = &origin.source_spans {
                source_spans.extend(spans.iter().cloned());
            }
            if let Some(derived) = &origin.derived_from_node_ids {
                derived_from_node_ids.extend(derived.iter().cloned());
            }
        }
    }
    SourceLink {
        source_spans: source_spans.into_iter().collect(),
        derived_from_node_ids: derived_from_node_ids.into_iter().collect(),
    }
}

fn evidence_nodes(primary: &NodeId, contributing: impl Iterator<Item = NodeId>) -> Vec<NodeId> {
    let mut nodes = BTreeSet::new();
    nodes.insert(primary.clone());
    nodes.extend(contributing);
    nodes.into_iter().collect()
}

fn validate_target_correspondence(
    semantic: &ExplanationDocument,
    evaluation: &CapabilityEvaluation,
    plan: &PortabilityPlan,
) -> Result<(), ExplanationErrors> {
    if semantic.target.is_some() || semantic.concise.target.is_some() {
        return Err(ExplanationErrors::single(
            ExplanationErrorCode::MismatchedPortabilityPlan,
            "$.target",
            "target projection requires the target-neutral explanation",
        ));
    }
    if semantic.contract_version != evaluation.contract_version
        || semantic.specification_version != evaluation.specification_version
        || semantic.semantic_program != evaluation.semantic_program
    {
        return Err(ExplanationErrors::single(
            ExplanationErrorCode::MismatchedCapabilityEvaluation,
            "$",
            "capability evaluation does not describe this semantic explanation",
        ));
    }
    if semantic.contract_version != plan.contract_version
        || semantic.specification_version != plan.specification_version
        || semantic.semantic_program != plan.semantic_program
        || evaluation.target_profile != plan.target_profile
    {
        return Err(ExplanationErrors::single(
            ExplanationErrorCode::MismatchedPortabilityPlan,
            "$",
            "portability plan does not describe this explanation and target",
        ));
    }
    if evaluation.results.len() != plan.decisions.len() {
        return Err(ExplanationErrors::single(
            ExplanationErrorCode::MismatchedPortabilityPlan,
            "$.decisions",
            "evaluation and plan decision counts differ",
        ));
    }
    for (index, (result, decision)) in evaluation.results.iter().zip(&plan.decisions).enumerate() {
        let planned_result = capability_result(decision);
        if planned_result != result
            || decision.identity.ordinal as usize != index
            || decision.identity.node_id != result.node_id
            || decision.identity.capability_id != result.evaluated_capability
        {
            return Err(ExplanationErrors::single(
                ExplanationErrorCode::MismatchedPortabilityPlan,
                format!("$.decisions[{index}]"),
                "portability decision does not preserve capability evidence and order",
            ));
        }
    }
    Ok(())
}

fn capability_result(decision: &PlannedRequirement) -> &CapabilityResult {
    match &decision.disposition {
        RequirementPlanningDisposition::Native(value) => &value.capability_result,
        RequirementPlanningDisposition::EquivalentRewrite(value) => &value.capability_result,
        RequirementPlanningDisposition::Unsupported(value) => &value.capability_result,
        RequirementPlanningDisposition::Unresolved(value) => &value.capability_result,
    }
}

fn target_decision(
    index: usize,
    decision: &PlannedRequirement,
    plan: &PortabilityPlan,
    node_sources: &BTreeMap<NodeId, SourceLink>,
) -> Result<TargetDecisionExplanation, ExplanationErrors> {
    let result = capability_result(decision);
    let outcome = match &decision.disposition {
        RequirementPlanningDisposition::Native(_) => TargetOutcomeExplanation::Native,
        RequirementPlanningDisposition::EquivalentRewrite(value) => {
            let dependency_ordinals = plan
                .rewrite_dependencies
                .iter()
                .filter(|edge| edge.dependent == decision.identity)
                .map(|edge| edge.prerequisite.ordinal)
                .collect();
            TargetOutcomeExplanation::EquivalentRewrite {
                strategy_id: value.rewrite_plan.strategy_id.as_str().to_owned(),
                affected_node_ids: value.rewrite_plan.affected_node_ids.clone(),
                dependency_ordinals,
                proof_dispositions: value
                    .rewrite_plan
                    .proof
                    .iter()
                    .map(|proof| proof_disposition(proof.disposition))
                    .collect(),
            }
        }
        RequirementPlanningDisposition::Unsupported(value) => {
            TargetOutcomeExplanation::Unsupported {
                rewrite_attempts: value.rewrite_attempts.iter().map(rewrite_attempt).collect(),
            }
        }
        RequirementPlanningDisposition::Unresolved(value) => TargetOutcomeExplanation::Unresolved {
            reason: unresolved_reason(value.reason),
            rewrite_attempts: value.rewrite_attempts.iter().map(rewrite_attempt).collect(),
        },
    };
    let source = node_sources
        .get(&decision.identity.node_id)
        .cloned()
        .ok_or_else(|| {
            ExplanationErrors::single(
                ExplanationErrorCode::MissingNode,
                format!("$.target.decisions[{index}].node_id"),
                "target decision references a node absent from the semantic explanation",
            )
        })?;
    Ok(TargetDecisionExplanation {
        ordinal: decision.identity.ordinal,
        evidence_class: if matches!(outcome, TargetOutcomeExplanation::Unresolved { .. }) {
            EvidenceClass::Uncertainty
        } else {
            EvidenceClass::TargetPlan
        },
        node_id: decision.identity.node_id.clone(),
        capability_id: decision.identity.capability_id.clone(),
        capability_availability: availability_explanation(result),
        capability_disposition: disposition_explanation(result.disposition),
        constraints: result
            .constraint_evaluations
            .iter()
            .map(|evaluation| ConstraintExplanation {
                constraint: evaluation.constraint.clone(),
                disposition: match evaluation.disposition {
                    ConstraintDisposition::Satisfied => ConstraintDispositionExplanation::Satisfied,
                    ConstraintDisposition::Violated => ConstraintDispositionExplanation::Violated,
                    ConstraintDisposition::Unknown => ConstraintDispositionExplanation::Unknown,
                },
                evidence: match evaluation.evidence {
                    ConstraintEvidence::RequirementFact(_) => {
                        ConstraintEvidenceExplanation::RequirementFact
                    }
                    ConstraintEvidence::ProfileOption(_) => {
                        ConstraintEvidenceExplanation::ProfileOption
                    }
                    ConstraintEvidence::MissingRequirementFact { .. } => {
                        ConstraintEvidenceExplanation::MissingRequirementFact
                    }
                },
            })
            .collect(),
        outcome,
        source,
    })
}

fn availability_explanation(result: &CapabilityResult) -> CapabilityAvailabilityExplanation {
    match result
        .profile_capability
        .as_ref()
        .map(|capability| capability.availability)
    {
        Some(CapabilityAvailability::Available) => CapabilityAvailabilityExplanation::Available,
        Some(CapabilityAvailability::Constrained) => CapabilityAvailabilityExplanation::Constrained,
        Some(CapabilityAvailability::Unavailable) => CapabilityAvailabilityExplanation::Unavailable,
        None => CapabilityAvailabilityExplanation::Unknown,
    }
}

fn disposition_explanation(value: CapabilityDisposition) -> CapabilityDispositionExplanation {
    match value {
        CapabilityDisposition::Supported => CapabilityDispositionExplanation::Supported,
        CapabilityDisposition::Unsupported => CapabilityDispositionExplanation::Unsupported,
        CapabilityDisposition::ConstraintViolation => {
            CapabilityDispositionExplanation::ConstraintViolation
        }
        CapabilityDisposition::Unknown => CapabilityDispositionExplanation::Unknown,
    }
}

fn proof_disposition(value: RewriteProofDisposition) -> ProofDispositionExplanation {
    match value {
        RewriteProofDisposition::Satisfied => ProofDispositionExplanation::Satisfied,
        RewriteProofDisposition::Failed => ProofDispositionExplanation::Failed,
        RewriteProofDisposition::Indeterminate => ProofDispositionExplanation::Indeterminate,
    }
}

fn rewrite_attempt(value: &RewriteAttempt) -> RewriteAttemptExplanation {
    RewriteAttemptExplanation {
        strategy_id: value.strategy_id.as_str().to_owned(),
        disposition: match value.disposition {
            RewriteAttemptDisposition::NotApplicable => {
                RewriteAttemptDispositionExplanation::NotApplicable
            }
            RewriteAttemptDisposition::ProofFailed => {
                RewriteAttemptDispositionExplanation::ProofFailed
            }
            RewriteAttemptDisposition::ProofIndeterminate => {
                RewriteAttemptDispositionExplanation::ProofIndeterminate
            }
            RewriteAttemptDisposition::ReplacementUnsupported => {
                RewriteAttemptDispositionExplanation::ReplacementUnsupported
            }
            RewriteAttemptDisposition::ReplacementUnknown => {
                RewriteAttemptDispositionExplanation::ReplacementUnknown
            }
            RewriteAttemptDisposition::Applicable => {
                RewriteAttemptDispositionExplanation::Applicable
            }
        },
    }
}

fn unresolved_reason(value: UnresolvedPlanningReason) -> UnresolvedReasonExplanation {
    match value {
        UnresolvedPlanningReason::CapabilityUnknown => {
            UnresolvedReasonExplanation::CapabilityUnknown
        }
        UnresolvedPlanningReason::RewriteProofIndeterminate => {
            UnresolvedReasonExplanation::RewriteProofIndeterminate
        }
        UnresolvedPlanningReason::ReplacementCapabilityUnknown => {
            UnresolvedReasonExplanation::ReplacementCapabilityUnknown
        }
    }
}

fn target_status(status: Option<PortabilityStatus>) -> TargetExplanationStatus {
    match status {
        Some(PortabilityStatus::Native) => TargetExplanationStatus::Native,
        Some(PortabilityStatus::EquivalentRewrite) => TargetExplanationStatus::EquivalentRewrite,
        Some(PortabilityStatus::Unsupported) => TargetExplanationStatus::Unsupported,
        None => TargetExplanationStatus::Unresolved,
    }
}
