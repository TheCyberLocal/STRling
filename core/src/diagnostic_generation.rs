//! Canonical projection of certified semantic safety evidence plus closed,
//! proof-backed semantic quality conditions into structured diagnostics.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::diagnostic::{
    compare_diagnostics, validate_diagnostic_order, Advice, AdviceKind, CompilerPhase, Diagnostic,
    DiagnosticCategory, DiagnosticCode, DiagnosticOccurrence, RelatedLocation, RelatedLocationRole,
    Severity, SeverityBasis,
};
use crate::safety_analysis::{
    enforce_resource_limits, validate_analysis, validate_foundational_correspondence,
    validate_structural_correspondence, SafetyAnalysis, SafetyAnalysisErrorCode,
    SafetyAnalysisErrors, SafetyEvidence, SafetyFinding, SafetyFindingCode,
    StructuralRelationshipKind, StructuralRelationshipRef, MAX_SAFETY_FINDINGS,
};
use crate::semantic::{Node, SemanticProgram};
use crate::semantic_analysis::{SemanticFacts, SemanticProgramIdentity};
use crate::source::{NodeId, SourceOrigin, SourceSpan};
use crate::structural_analysis::StructuralFacts;
use crate::validation::{Validate, ValidationCode, ValidationErrors};

mod quality;

use quality::{derive_quality_findings, QualityDerivationErrorCode};
pub use quality::{
    QualityAssertionPolarity, QualityBoundaryKind, QualityCharacterSetMember, QualityEvidence,
    QualityFinding, QualityFindingCategory, QualityFindingCode, QualityLookaroundDirection,
    QualityProofStatus, QualityRepetitionMode, MAX_QUALITY_FINDINGS,
};

/// Canonical source provenance retained for one semantic evidence node.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiagnosticNodeOrigin {
    pub node_id: NodeId,
    pub origin: SourceOrigin,
}

/// Stable external code for an unbounded nullable repetition.
pub const SAFETY_UNBOUNDED_NULLABLE_REPETITION: &str = "STRL-SAFETY-0001";
/// Stable external code for an unbounded repetition with indeterminate progress.
pub const SAFETY_UNBOUNDED_INDETERMINATE_PROGRESS: &str = "STRL-SAFETY-0002";
/// Stable external code for proved nested repetition overlap.
pub const SAFETY_NESTED_REPETITION_OVERLAP: &str = "STRL-SAFETY-0003";
/// Stable external code for proved overlap between repeated alternatives.
pub const SAFETY_REPEATED_ALTERNATION_OVERLAP: &str = "STRL-SAFETY-0004";
/// Stable external code for proved repetition/follower overlap.
pub const SAFETY_REPETITION_FOLLOWER_OVERLAP: &str = "STRL-SAFETY-0005";
/// Stable external code for a repetition whose operand is unreachable.
pub const QUALITY_ZERO_MAXIMUM_REPETITION: &str = "STRL-QUALITY-0001";
/// Stable external code for a non-possessive repetition that executes exactly once.
pub const QUALITY_REDUNDANT_SINGLE_REPETITION: &str = "STRL-QUALITY-0002";
/// Stable external code for an exact duplicate later alternation branch.
pub const QUALITY_DUPLICATE_ALTERNATION_BRANCH: &str = "STRL-QUALITY-0003";
/// Stable external code for same-position complementary boundary assertions.
pub const QUALITY_CONTRADICTORY_BOUNDARY_ASSERTIONS: &str = "STRL-QUALITY-0004";
/// Stable external code for equivalent opposite-polarity lookarounds.
pub const QUALITY_CONTRADICTORY_LOOKAROUND_ASSERTIONS: &str = "STRL-QUALITY-0005";
/// Stable external code for explicit character-set members with proved overlap.
pub const QUALITY_OVERLAPPING_CHARACTER_SET_MEMBERS: &str = "STRL-QUALITY-0006";
/// Stable external code for a backreference to a proven zero-width capture body.
pub const QUALITY_ZERO_WIDTH_BACKREFERENCE: &str = "STRL-QUALITY-0007";

/// Maximum diagnostics produced by one generation invocation.
pub const MAX_GENERATED_DIAGNOSTICS: usize = MAX_SAFETY_FINDINGS + MAX_QUALITY_FINDINGS;

/// Typed provenance for one canonical generated diagnostic.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum DiagnosticEvidence {
    Safety(SafetyEvidence),
    Quality(QualityEvidence),
}

/// Stable semantic evidence retained beside one contract diagnostic.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiagnosticProvenance {
    pub primary_node_id: NodeId,
    pub contributing_node_ids: Vec<NodeId>,
    pub relationship: Option<StructuralRelationshipRef>,
    pub evidence: DiagnosticEvidence,
    pub source_origins: Vec<DiagnosticNodeOrigin>,
}

/// One structured contract diagnostic and its generation-only provenance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GeneratedDiagnostic {
    pub diagnostic: Diagnostic,
    pub provenance: DiagnosticProvenance,
}

/// Canonically ordered diagnostics produced for one exact semantic program.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct DiagnosticGeneration {
    records: Vec<GeneratedDiagnostic>,
    program_identity: Option<SemanticProgramIdentity>,
}

impl DiagnosticGeneration {
    /// Iterate evidence-bearing generation records in contract diagnostic order.
    pub fn records(&self) -> impl ExactSizeIterator<Item = &GeneratedDiagnostic> {
        self.records.iter()
    }

    #[must_use]
    pub(crate) fn program_identity(&self) -> Option<SemanticProgramIdentity> {
        self.program_identity
    }

    /// Iterate certified contract diagnostics in canonical result order.
    pub fn diagnostics(&self) -> impl ExactSizeIterator<Item = &Diagnostic> {
        self.records.iter().map(|record| &record.diagnostic)
    }

    /// Consume generation provenance and return the `CompileResult` projection.
    #[must_use]
    pub fn into_diagnostics(self) -> Vec<Diagnostic> {
        self.records
            .into_iter()
            .map(|record| record.diagnostic)
            .collect()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.records.len()
    }
}

/// Stable categories for diagnostic-generation failure.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum DiagnosticGenerationErrorCode {
    InvalidSemanticStructure,
    InvalidIdentity,
    NonCanonicalInput,
    DepthLimitExceeded,
    NodeLimitExceeded,
    DiagnosticLimitExceeded,
    MismatchedSemanticFacts,
    MismatchedStructuralFacts,
    MissingSemanticFact,
    UnexpectedSemanticFact,
    MissingStructuralFact,
    UnexpectedStructuralFact,
    MalformedStructuralFact,
    MalformedEvidenceReference,
    OccurrenceOverflow,
    GenerationInvariant,
}

/// One machine-classifiable generation failure with a stable input path.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DiagnosticGenerationError {
    pub code: DiagnosticGenerationErrorCode,
    pub path: String,
    pub message: String,
}

impl DiagnosticGenerationError {
    fn new(
        code: DiagnosticGenerationErrorCode,
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

/// Ordered failures returned for invalid prerequisite or safety evidence.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DiagnosticGenerationErrors {
    pub errors: Vec<DiagnosticGenerationError>,
}

impl DiagnosticGenerationErrors {
    fn single(error: DiagnosticGenerationError) -> Self {
        Self {
            errors: vec![error],
        }
    }

    fn from_safety(errors: SafetyAnalysisErrors) -> Self {
        Self {
            errors: errors
                .errors
                .into_iter()
                .map(|error| DiagnosticGenerationError {
                    code: generation_code(error.code),
                    path: error.path,
                    message: error.message,
                })
                .collect(),
        }
    }

    fn from_validation(errors: ValidationErrors) -> Self {
        Self {
            errors: errors
                .errors
                .into_iter()
                .map(|error| DiagnosticGenerationError {
                    code: validation_code(error.code),
                    path: error.path,
                    message: error.message,
                })
                .collect(),
        }
    }
}

impl fmt::Display for DiagnosticGenerationErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} diagnostic generation error(s)",
            self.errors.len()
        )
    }
}

impl Error for DiagnosticGenerationErrors {}

/// Generate canonical diagnostics from certified facts and safety evidence.
///
/// The stage validates correspondence and safety evidence shape, never derives
/// a safety condition, and independently constructs only its closed set of
/// semantic quality proofs. Current typed uncertainty is intentionally not
/// promoted into a diagnostic.
pub fn generate_diagnostics(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    safety: &SafetyAnalysis,
) -> Result<DiagnosticGeneration, DiagnosticGenerationErrors> {
    enforce_resource_limits(&input.root).map_err(DiagnosticGenerationErrors::from_safety)?;
    input
        .validate()
        .map_err(DiagnosticGenerationErrors::from_validation)?;
    validate_foundational_correspondence(input, foundational)
        .map_err(DiagnosticGenerationErrors::from_safety)?;
    validate_structural_correspondence(input, structural)
        .map_err(DiagnosticGenerationErrors::from_safety)?;

    let canonical_safety = SafetyAnalysis::from_parts(
        safety.findings().cloned().collect(),
        safety.uncertainties().cloned().collect(),
    )
    .map_err(DiagnosticGenerationErrors::from_safety)?;
    validate_analysis(input, structural, &canonical_safety)
        .map_err(DiagnosticGenerationErrors::from_safety)?;

    let node_index = index_nodes(&input.root);
    validate_projection_evidence(&node_index, structural, &canonical_safety)?;
    let mut records: Vec<_> = canonical_safety
        .findings()
        .map(|finding| build_safety_record(input, &node_index, finding))
        .collect::<Result<_, _>>()?;
    let quality_findings =
        derive_quality_findings(input, foundational, structural).map_err(|error| {
            DiagnosticGenerationErrors::single(DiagnosticGenerationError::new(
                match error.code {
                    QualityDerivationErrorCode::FindingLimitExceeded => {
                        DiagnosticGenerationErrorCode::DiagnosticLimitExceeded
                    }
                    QualityDerivationErrorCode::Invariant => {
                        DiagnosticGenerationErrorCode::GenerationInvariant
                    }
                },
                error.path,
                error.message,
            ))
        })?;
    records.extend(
        quality_findings
            .iter()
            .map(|finding| build_quality_record(input, &node_index, finding))
            .collect::<Result<Vec<_>, _>>()?,
    );
    if records.len() > MAX_GENERATED_DIAGNOSTICS {
        return Err(DiagnosticGenerationErrors::single(
            DiagnosticGenerationError::new(
                DiagnosticGenerationErrorCode::DiagnosticLimitExceeded,
                "$.diagnostics",
                format!(
                    "diagnostic count exceeds the deterministic limit of {MAX_GENERATED_DIAGNOSTICS}"
                ),
            ),
        ));
    }

    records.sort_by(compare_occurrence_keys);
    for (index, record) in records.iter_mut().enumerate() {
        let occurrence = u64::try_from(index).map_err(|_| {
            DiagnosticGenerationErrors::single(DiagnosticGenerationError::new(
                DiagnosticGenerationErrorCode::OccurrenceOverflow,
                "$.diagnostics",
                "diagnostic occurrence ordinal exceeds u64",
            ))
        })?;
        record.diagnostic.occurrence = DiagnosticOccurrence::new(occurrence);
    }
    records.sort_by(|left, right| compare_diagnostics(&left.diagnostic, &right.diagnostic));

    for record in &records {
        record
            .diagnostic
            .validate()
            .map_err(DiagnosticGenerationErrors::from_validation)?;
    }
    let diagnostics: Vec<_> = records
        .iter()
        .map(|record| record.diagnostic.clone())
        .collect();
    validate_diagnostic_order(&diagnostics).map_err(DiagnosticGenerationErrors::from_validation)?;

    Ok(DiagnosticGeneration {
        records,
        program_identity: Some(foundational.program_identity()),
    })
}

fn build_safety_record(
    input: &SemanticProgram,
    nodes: &BTreeMap<NodeId, &Node>,
    finding: &SafetyFinding,
) -> Result<GeneratedDiagnostic, DiagnosticGenerationErrors> {
    let (code, severity, message) = diagnostic_policy(finding.code);
    let primary_node_id = diagnostic_primary_node_id(finding);
    let primary_location = primary_span(nodes, primary_node_id).cloned();
    let related_locations =
        related_locations(nodes, finding, primary_node_id, primary_location.as_ref());
    let advice = advice(finding.code);
    let code = DiagnosticCode::try_from(code).map_err(|message| {
        DiagnosticGenerationErrors::single(DiagnosticGenerationError::new(
            DiagnosticGenerationErrorCode::GenerationInvariant,
            "$.diagnostics.code",
            message,
        ))
    })?;

    Ok(GeneratedDiagnostic {
        diagnostic: Diagnostic {
            contract_version: input.contract_version,
            occurrence: DiagnosticOccurrence::new(0),
            code,
            severity,
            severity_basis: SeverityBasis::CompilerPolicy,
            phase: CompilerPhase::SemanticAnalysis,
            category: DiagnosticCategory::Safety,
            message: message.to_owned(),
            primary_location,
            related_locations: (!related_locations.is_empty()).then_some(related_locations),
            advice: Some(advice),
            fixes: None,
        },
        provenance: DiagnosticProvenance {
            primary_node_id: primary_node_id.clone(),
            contributing_node_ids: finding.evidence_node_ids.clone(),
            relationship: relationship(&finding.evidence).cloned(),
            evidence: DiagnosticEvidence::Safety(finding.evidence.clone()),
            source_origins: source_origins(nodes, primary_node_id, &finding.evidence_node_ids),
        },
    })
}

fn build_quality_record(
    input: &SemanticProgram,
    nodes: &BTreeMap<NodeId, &Node>,
    finding: &QualityFinding,
) -> Result<GeneratedDiagnostic, DiagnosticGenerationErrors> {
    let (code, severity, message) = quality_diagnostic_policy(finding.code);
    let primary_node_id = &finding.primary_node_id;
    let primary_location = primary_span(nodes, primary_node_id).cloned();
    let related_locations =
        quality_related_locations(nodes, finding, primary_node_id, primary_location.as_ref());
    let code = DiagnosticCode::try_from(code).map_err(|message| {
        DiagnosticGenerationErrors::single(DiagnosticGenerationError::new(
            DiagnosticGenerationErrorCode::GenerationInvariant,
            "$.diagnostics.code",
            message,
        ))
    })?;

    Ok(GeneratedDiagnostic {
        diagnostic: Diagnostic {
            contract_version: input.contract_version,
            occurrence: DiagnosticOccurrence::new(0),
            code,
            severity,
            severity_basis: SeverityBasis::CompilerPolicy,
            phase: CompilerPhase::SemanticAnalysis,
            category: DiagnosticCategory::SemanticValidity,
            message: message.to_owned(),
            primary_location,
            related_locations: (!related_locations.is_empty()).then_some(related_locations),
            advice: Some(quality_advice(finding.code)),
            fixes: None,
        },
        provenance: DiagnosticProvenance {
            primary_node_id: primary_node_id.clone(),
            contributing_node_ids: finding.evidence_node_ids.clone(),
            relationship: None,
            evidence: DiagnosticEvidence::Quality(finding.evidence.clone()),
            source_origins: source_origins(nodes, primary_node_id, &finding.evidence_node_ids),
        },
    })
}

fn diagnostic_policy(code: SafetyFindingCode) -> (&'static str, Severity, &'static str) {
    match code {
        SafetyFindingCode::UnboundedNullableRepetition => (
            SAFETY_UNBOUNDED_NULLABLE_REPETITION,
            Severity::Warning,
            "Unbounded repetition has an operand that can match without consuming input.",
        ),
        SafetyFindingCode::UnboundedIndeterminateProgress => (
            SAFETY_UNBOUNDED_INDETERMINATE_PROGRESS,
            Severity::Info,
            "Unbounded repetition has an operand whose progress could not be determined.",
        ),
        SafetyFindingCode::NestedRepetitionOverlap => (
            SAFETY_NESTED_REPETITION_OVERLAP,
            Severity::Warning,
            "An outer repetition can repartition input with an overlapping inner repetition.",
        ),
        SafetyFindingCode::RepeatedAlternationOverlap => (
            SAFETY_REPEATED_ALTERNATION_OVERLAP,
            Severity::Warning,
            "A repeated alternation has branches with overlapping leading consumption.",
        ),
        SafetyFindingCode::RepetitionFollowerOverlap => (
            SAFETY_REPETITION_FOLLOWER_OVERLAP,
            Severity::Warning,
            "A repetition and its immediate follower can consume overlapping leading input.",
        ),
    }
}

fn quality_diagnostic_policy(code: QualityFindingCode) -> (&'static str, Severity, &'static str) {
    match code {
        QualityFindingCode::ZeroMaximumRepetition => (
            QUALITY_ZERO_MAXIMUM_REPETITION,
            Severity::Warning,
            "A repetition with maximum zero has an unreachable operand.",
        ),
        QualityFindingCode::RedundantSingleRepetition => (
            QUALITY_REDUNDANT_SINGLE_REPETITION,
            Severity::Info,
            "A non-possessive repetition that executes exactly once is semantically redundant.",
        ),
        QualityFindingCode::DuplicateAlternationBranch => (
            QUALITY_DUPLICATE_ALTERNATION_BRANCH,
            Severity::Warning,
            "A later alternation branch duplicates an earlier canonical semantic branch.",
        ),
        QualityFindingCode::ContradictoryBoundaryAssertions => (
            QUALITY_CONTRADICTORY_BOUNDARY_ASSERTIONS,
            Severity::Warning,
            "The same input position requires both word-boundary and not-word-boundary.",
        ),
        QualityFindingCode::ContradictoryLookaroundAssertions => (
            QUALITY_CONTRADICTORY_LOOKAROUND_ASSERTIONS,
            Severity::Warning,
            "Equivalent lookarounds at the same input position require opposite outcomes.",
        ),
        QualityFindingCode::OverlappingCharacterSetMembers => (
            QUALITY_OVERLAPPING_CHARACTER_SET_MEMBERS,
            Severity::Info,
            "Explicit character-set members overlap on a proven Unicode scalar.",
        ),
        QualityFindingCode::ZeroWidthBackreference => (
            QUALITY_ZERO_WIDTH_BACKREFERENCE,
            Severity::Info,
            "A backreference targets a capture body proven to consume no input.",
        ),
    }
}

fn advice(code: SafetyFindingCode) -> Vec<Advice> {
    let (note, help) = match code {
        SafetyFindingCode::UnboundedNullableRepetition => (
            "This proves a target-neutral non-progress structure, not universal runtime vulnerability.",
            "Require the repeated operand to consume input before another unbounded iteration.",
        ),
        SafetyFindingCode::UnboundedIndeterminateProgress => (
            "The repetition is unbounded, but available semantic facts do not prove whether its operand always consumes input.",
            "Make operand progress explicit or bound the repetition when unbounded progress cannot be established.",
        ),
        SafetyFindingCode::NestedRepetitionOverlap => (
            "The structural proof identifies competing repeated partitions; runtime impact remains target-dependent.",
            "Remove the ambiguous nested repeated partition or make each repetition consume a distinct region.",
        ),
        SafetyFindingCode::RepeatedAlternationOverlap => (
            "The overlap is structurally proven; its runtime impact remains target-dependent.",
            "Narrow the overlapping branches so repeated input selects a distinct alternative.",
        ),
        SafetyFindingCode::RepetitionFollowerOverlap => (
            "The repeated operand and follower share proved leading consumption; runtime impact remains target-dependent.",
            "Separate repeated content from follower input that competes for the same leading characters.",
        ),
    };
    vec![
        Advice {
            kind: AdviceKind::Note,
            message: note.to_owned(),
        },
        Advice {
            kind: AdviceKind::Help,
            message: help.to_owned(),
        },
    ]
}

fn quality_advice(code: QualityFindingCode) -> Vec<Advice> {
    let (note, help) = match code {
        QualityFindingCode::ZeroMaximumRepetition => (
            "The certified repetition bound prevents the operand from executing.",
            "Remove the unreachable operand or express the intended repetition bound.",
        ),
        QualityFindingCode::RedundantSingleRepetition => (
            "The exact count is one and no possessive commitment is present.",
            "Use the operand directly when the exact-once wrapper is not needed for provenance.",
        ),
        QualityFindingCode::DuplicateAlternationBranch => (
            "Every semantic field and capture/reference identity agrees; only node identity or source provenance differs.",
            "Remove the later duplicate branch or make its semantic intent distinct.",
        ),
        QualityFindingCode::ContradictoryBoundaryAssertions => (
            "No consuming expression separates the complementary boundary requirements.",
            "Remove one boundary assertion or separate them with the intended consuming expression.",
        ),
        QualityFindingCode::ContradictoryLookaroundAssertions => (
            "The assertions have the same direction and canonical-equivalent bodies but opposite polarity.",
            "Keep the assertion outcome that represents the intended condition.",
        ),
        QualityFindingCode::OverlappingCharacterSetMembers => (
            "The evidence records an explicit scalar contained by both members; symbolic class and case-fold guesses are not used.",
            "Merge or narrow the explicit members when the overlap is unintended.",
        ),
        QualityFindingCode::ZeroWidthBackreference => (
            "When the capture participates, its certified body cannot contribute consuming progress.",
            "Use a consuming capture body or remove the reference if zero-width behavior is not intentional.",
        ),
    };
    vec![
        Advice {
            kind: AdviceKind::Note,
            message: note.to_owned(),
        },
        Advice {
            kind: AdviceKind::Help,
            message: help.to_owned(),
        },
    ]
}

fn index_nodes(root: &Node) -> BTreeMap<NodeId, &Node> {
    let mut nodes = BTreeMap::new();
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        nodes.insert(node.node_id().clone(), node);
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
    nodes
}

fn source_origins(
    nodes: &BTreeMap<NodeId, &Node>,
    primary_node_id: &NodeId,
    contributing_node_ids: &[NodeId],
) -> Vec<DiagnosticNodeOrigin> {
    let mut node_ids: BTreeSet<_> = contributing_node_ids.iter().cloned().collect();
    node_ids.insert(primary_node_id.clone());
    node_ids
        .into_iter()
        .filter_map(|node_id| {
            nodes
                .get(&node_id)
                .and_then(|node| node.origin())
                .cloned()
                .map(|origin| DiagnosticNodeOrigin { node_id, origin })
        })
        .collect()
}

fn validate_projection_evidence(
    nodes: &BTreeMap<NodeId, &Node>,
    structural: &StructuralFacts,
    safety: &SafetyAnalysis,
) -> Result<(), DiagnosticGenerationErrors> {
    for finding in safety.findings() {
        match &finding.evidence {
            SafetyEvidence::RepetitionProgress { .. } => {}
            SafetyEvidence::NestedRepetition {
                outer_repetition_node_id,
                inner_repetition_node_id,
                inner_operand_node_id,
                path,
                outer_extent,
                inner_length,
                inner_minimum,
                inner_maximum,
            } => {
                let Some(Node::Repeat { .. }) = nodes.get(outer_repetition_node_id).copied() else {
                    return Err(projection_error("nested outer repetition does not resolve"));
                };
                let Some(Node::Repeat { body, min, max, .. }) =
                    nodes.get(inner_repetition_node_id).copied()
                else {
                    return Err(projection_error("nested inner repetition does not resolve"));
                };
                if body.node_id() != inner_operand_node_id
                    || min != inner_minimum
                    || max != inner_maximum
                    || path.first() != Some(outer_repetition_node_id)
                    || path.last() != Some(inner_repetition_node_id)
                    || path.windows(2).any(|pair| {
                        nodes
                            .get(&pair[0])
                            .map_or(true, |parent| !is_direct_child(parent, &pair[1]))
                    })
                {
                    return Err(projection_error(
                        "nested repetition evidence path is malformed",
                    ));
                }
                let outer_facts = structural
                    .get(outer_repetition_node_id)
                    .and_then(|facts| facts.repetition.as_ref());
                let inner_facts = structural.get(inner_repetition_node_id);
                if outer_facts.map_or(true, |facts| facts.extent != *outer_extent)
                    || inner_facts.map_or(true, |facts| facts.length != *inner_length)
                {
                    return Err(projection_error(
                        "nested repetition evidence contradicts structural facts",
                    ));
                }
            }
            SafetyEvidence::RepeatedAlternation {
                repetition_node_id,
                alternation_node_id,
                left_branch_index,
                right_branch_index,
                relationship,
                relation,
                ..
            } => {
                if !matches!(nodes.get(repetition_node_id), Some(Node::Repeat { .. }))
                    || !matches!(
                        nodes.get(alternation_node_id),
                        Some(Node::Alternation { .. })
                    )
                    || relationship.kind != StructuralRelationshipKind::AlternationBranchOverlap
                    || relationship.owner_node_id != *alternation_node_id
                {
                    return Err(projection_error(
                        "repeated alternation relationship owner is malformed",
                    ));
                }
                let structural_relationship =
                    structural.get(alternation_node_id).and_then(|facts| {
                        facts.alternation_branch_overlaps.iter().find(|candidate| {
                            candidate.left_branch_index == *left_branch_index
                                && candidate.right_branch_index == *right_branch_index
                        })
                    });
                if structural_relationship.map_or(true, |candidate| {
                    candidate.left_node_id != relationship.left_node_id
                        || candidate.right_node_id != relationship.right_node_id
                        || candidate.relation != *relation
                }) {
                    return Err(projection_error(
                        "repeated alternation relationship does not match structural facts",
                    ));
                }
            }
            SafetyEvidence::RepetitionFollower {
                sequence_node_id,
                repetition_node_id,
                operand_node_id,
                follower_node_id,
                repetition_index,
                follower_index,
                relationship,
                relation,
                ..
            } => {
                if !matches!(nodes.get(sequence_node_id), Some(Node::Sequence { .. }))
                    || !matches!(nodes.get(repetition_node_id), Some(Node::Repeat { .. }))
                    || relationship.kind != StructuralRelationshipKind::RepetitionFollowerOverlap
                    || relationship.owner_node_id != *sequence_node_id
                    || relationship.left_node_id != *operand_node_id
                    || relationship.right_node_id != *follower_node_id
                {
                    return Err(projection_error(
                        "repetition/follower relationship owner is malformed",
                    ));
                }
                let structural_relationship = structural.get(sequence_node_id).and_then(|facts| {
                    facts.repetition_follow_overlaps.iter().find(|candidate| {
                        candidate.repetition_index == *repetition_index
                            && candidate.following_index == *follower_index
                    })
                });
                if structural_relationship.map_or(true, |candidate| {
                    candidate.repetition_node_id != *repetition_node_id
                        || candidate.operand_node_id != *operand_node_id
                        || candidate.following_node_id != *follower_node_id
                        || candidate.relation != *relation
                }) {
                    return Err(projection_error(
                        "repetition/follower relationship does not match structural facts",
                    ));
                }
            }
        }
    }
    Ok(())
}

fn is_direct_child(parent: &Node, child_node_id: &NodeId) -> bool {
    match parent {
        Node::Sequence { items, .. } => items.iter().any(|child| child.node_id() == child_node_id),
        Node::Alternation { branches, .. } => branches
            .iter()
            .any(|child| child.node_id() == child_node_id),
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => body.node_id() == child_node_id,
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => false,
    }
}

fn projection_error(message: &str) -> DiagnosticGenerationErrors {
    DiagnosticGenerationErrors::single(DiagnosticGenerationError::new(
        DiagnosticGenerationErrorCode::MalformedEvidenceReference,
        "$.safety.findings",
        message,
    ))
}

fn node_spans<'a>(nodes: &'a BTreeMap<NodeId, &Node>, node_id: &NodeId) -> &'a [SourceSpan] {
    nodes
        .get(node_id)
        .and_then(|node| node.origin())
        .and_then(|origin| origin.source_spans.as_deref())
        .unwrap_or_default()
}

fn primary_span<'a>(
    nodes: &'a BTreeMap<NodeId, &Node>,
    node_id: &NodeId,
) -> Option<&'a SourceSpan> {
    node_spans(nodes, node_id).iter().min_by(|left, right| {
        (left.end - left.start)
            .cmp(&(right.end - right.start))
            .then_with(|| left.cmp(right))
    })
}

fn diagnostic_primary_node_id(finding: &SafetyFinding) -> &NodeId {
    match &finding.evidence {
        SafetyEvidence::RepeatedAlternation {
            repetition_node_id, ..
        } => repetition_node_id,
        SafetyEvidence::RepetitionProgress {
            repetition_node_id, ..
        }
        | SafetyEvidence::NestedRepetition {
            outer_repetition_node_id: repetition_node_id,
            ..
        }
        | SafetyEvidence::RepetitionFollower {
            repetition_node_id, ..
        } => repetition_node_id,
    }
}

fn related_locations(
    nodes: &BTreeMap<NodeId, &Node>,
    finding: &SafetyFinding,
    primary_node_id: &NodeId,
    primary: Option<&SourceSpan>,
) -> Vec<RelatedLocation> {
    let mut related = Vec::new();
    for span in node_spans(nodes, primary_node_id) {
        if Some(span) != primary {
            push_related(
                &mut related,
                RelatedLocationRole::Context,
                "Additional source region for the primary safety finding.",
                span,
            );
        }
    }

    match &finding.evidence {
        SafetyEvidence::RepetitionProgress {
            operand_node_id, ..
        } => push_node_locations(
            &mut related,
            nodes,
            operand_node_id,
            RelatedLocationRole::Cause,
            "This operand does not have guaranteed consuming progress.",
        ),
        SafetyEvidence::NestedRepetition {
            inner_repetition_node_id,
            inner_operand_node_id,
            ..
        } => {
            push_node_locations(
                &mut related,
                nodes,
                inner_repetition_node_id,
                RelatedLocationRole::Cause,
                "This inner repetition creates the competing repeated partition.",
            );
            push_node_locations(
                &mut related,
                nodes,
                inner_operand_node_id,
                RelatedLocationRole::Context,
                "This inner operand supplies the overlapping consumed region.",
            );
        }
        SafetyEvidence::RepeatedAlternation { relationship, .. } => {
            push_node_locations(
                &mut related,
                nodes,
                &relationship.left_node_id,
                RelatedLocationRole::Cause,
                "This repeated branch overlaps the other related branch.",
            );
            push_node_locations(
                &mut related,
                nodes,
                &relationship.right_node_id,
                RelatedLocationRole::Cause,
                "This repeated branch overlaps the other related branch.",
            );
        }
        SafetyEvidence::RepetitionFollower {
            operand_node_id,
            follower_node_id,
            ..
        } => {
            push_node_locations(
                &mut related,
                nodes,
                follower_node_id,
                RelatedLocationRole::Cause,
                "This immediate follower competes with the repetition for leading input.",
            );
            push_node_locations(
                &mut related,
                nodes,
                operand_node_id,
                RelatedLocationRole::Context,
                "This repeated operand supplies the overlapping leading consumption.",
            );
        }
    }
    related
}

fn quality_related_locations(
    nodes: &BTreeMap<NodeId, &Node>,
    finding: &QualityFinding,
    primary_node_id: &NodeId,
    primary: Option<&SourceSpan>,
) -> Vec<RelatedLocation> {
    let mut related = Vec::new();
    for span in node_spans(nodes, primary_node_id) {
        if Some(span) != primary {
            push_related(
                &mut related,
                RelatedLocationRole::Context,
                "Additional source region for the primary quality finding.",
                span,
            );
        }
    }

    match &finding.evidence {
        QualityEvidence::ZeroMaximumRepetition {
            operand_node_id, ..
        } => push_node_locations(
            &mut related,
            nodes,
            operand_node_id,
            RelatedLocationRole::Cause,
            "This operand is unreachable because the repetition maximum is zero.",
        ),
        QualityEvidence::RedundantSingleRepetition {
            operand_node_id, ..
        } => push_node_locations(
            &mut related,
            nodes,
            operand_node_id,
            RelatedLocationRole::Context,
            "This operand already represents the exact-once semantic behavior.",
        ),
        QualityEvidence::DuplicateAlternationBranch {
            first_branch_node_id,
            ..
        } => push_node_locations(
            &mut related,
            nodes,
            first_branch_node_id,
            RelatedLocationRole::Definition,
            "This earlier branch has the same canonical semantic shape.",
        ),
        QualityEvidence::ContradictoryBoundaryAssertions { first_node_id, .. } => {
            push_node_locations(
                &mut related,
                nodes,
                first_node_id,
                RelatedLocationRole::Cause,
                "This earlier assertion requires the complementary boundary state.",
            )
        }
        QualityEvidence::ContradictoryLookaroundAssertions {
            first_node_id,
            first_body_node_id,
            later_body_node_id,
            ..
        } => {
            push_node_locations(
                &mut related,
                nodes,
                first_node_id,
                RelatedLocationRole::Cause,
                "This earlier equivalent lookaround has the opposite polarity.",
            );
            push_node_locations(
                &mut related,
                nodes,
                first_body_node_id,
                RelatedLocationRole::Context,
                "This body is canonically equivalent to the later lookaround body.",
            );
            push_node_locations(
                &mut related,
                nodes,
                later_body_node_id,
                RelatedLocationRole::Context,
                "This body is canonically equivalent to the earlier lookaround body.",
            );
        }
        QualityEvidence::OverlappingCharacterSetMembers { .. } => {}
        QualityEvidence::ZeroWidthBackreference {
            capture_definition_node_id,
            capture_body_node_id,
            ..
        } => {
            push_node_locations(
                &mut related,
                nodes,
                capture_definition_node_id,
                RelatedLocationRole::Definition,
                "This capture defines the referenced logical identity.",
            );
            push_node_locations(
                &mut related,
                nodes,
                capture_body_node_id,
                RelatedLocationRole::Cause,
                "This capture body is proven to have maximum consumption zero.",
            );
        }
    }
    related
}

fn push_node_locations(
    related: &mut Vec<RelatedLocation>,
    nodes: &BTreeMap<NodeId, &Node>,
    node_id: &NodeId,
    role: RelatedLocationRole,
    message: &str,
) {
    for span in node_spans(nodes, node_id) {
        push_related(related, role, message, span);
    }
}

fn push_related(
    related: &mut Vec<RelatedLocation>,
    role: RelatedLocationRole,
    message: &str,
    span: &SourceSpan,
) {
    if related.iter().any(|existing| {
        existing.role == role && existing.message == message && existing.location == *span
    }) {
        return;
    }
    related.push(RelatedLocation {
        role,
        message: message.to_owned(),
        location: span.clone(),
    });
}

fn relationship(evidence: &SafetyEvidence) -> Option<&StructuralRelationshipRef> {
    match evidence {
        SafetyEvidence::RepeatedAlternation { relationship, .. }
        | SafetyEvidence::RepetitionFollower { relationship, .. } => Some(relationship),
        SafetyEvidence::RepetitionProgress { .. } | SafetyEvidence::NestedRepetition { .. } => None,
    }
}

fn compare_occurrence_keys(
    left: &GeneratedDiagnostic,
    right: &GeneratedDiagnostic,
) -> std::cmp::Ordering {
    left.diagnostic
        .code
        .cmp(&right.diagnostic.code)
        .then_with(|| {
            left.provenance
                .primary_node_id
                .cmp(&right.provenance.primary_node_id)
        })
        .then_with(|| {
            left.provenance
                .contributing_node_ids
                .cmp(&right.provenance.contributing_node_ids)
        })
        .then_with(|| left.provenance.evidence.cmp(&right.provenance.evidence))
}

fn generation_code(code: SafetyAnalysisErrorCode) -> DiagnosticGenerationErrorCode {
    match code {
        SafetyAnalysisErrorCode::InvalidSemanticStructure => {
            DiagnosticGenerationErrorCode::InvalidSemanticStructure
        }
        SafetyAnalysisErrorCode::InvalidIdentity => DiagnosticGenerationErrorCode::InvalidIdentity,
        SafetyAnalysisErrorCode::NonCanonicalInput => {
            DiagnosticGenerationErrorCode::NonCanonicalInput
        }
        SafetyAnalysisErrorCode::DepthLimitExceeded => {
            DiagnosticGenerationErrorCode::DepthLimitExceeded
        }
        SafetyAnalysisErrorCode::NodeLimitExceeded => {
            DiagnosticGenerationErrorCode::NodeLimitExceeded
        }
        SafetyAnalysisErrorCode::FindingLimitExceeded
        | SafetyAnalysisErrorCode::UncertaintyLimitExceeded => {
            DiagnosticGenerationErrorCode::DiagnosticLimitExceeded
        }
        SafetyAnalysisErrorCode::MismatchedSemanticFacts => {
            DiagnosticGenerationErrorCode::MismatchedSemanticFacts
        }
        SafetyAnalysisErrorCode::MismatchedStructuralFacts => {
            DiagnosticGenerationErrorCode::MismatchedStructuralFacts
        }
        SafetyAnalysisErrorCode::MissingSemanticFact => {
            DiagnosticGenerationErrorCode::MissingSemanticFact
        }
        SafetyAnalysisErrorCode::UnexpectedSemanticFact => {
            DiagnosticGenerationErrorCode::UnexpectedSemanticFact
        }
        SafetyAnalysisErrorCode::MissingStructuralFact => {
            DiagnosticGenerationErrorCode::MissingStructuralFact
        }
        SafetyAnalysisErrorCode::UnexpectedStructuralFact => {
            DiagnosticGenerationErrorCode::UnexpectedStructuralFact
        }
        SafetyAnalysisErrorCode::MalformedStructuralFact => {
            DiagnosticGenerationErrorCode::MalformedStructuralFact
        }
        SafetyAnalysisErrorCode::MalformedEvidenceReference => {
            DiagnosticGenerationErrorCode::MalformedEvidenceReference
        }
        SafetyAnalysisErrorCode::AnalysisInvariant => {
            DiagnosticGenerationErrorCode::GenerationInvariant
        }
    }
}

fn validation_code(code: ValidationCode) -> DiagnosticGenerationErrorCode {
    match code {
        ValidationCode::InvalidIdentity | ValidationCode::DuplicateIdentity => {
            DiagnosticGenerationErrorCode::InvalidIdentity
        }
        ValidationCode::NonCanonicalOrder | ValidationCode::NonCanonicalStructure => {
            DiagnosticGenerationErrorCode::NonCanonicalInput
        }
        _ => DiagnosticGenerationErrorCode::InvalidSemanticStructure,
    }
}
