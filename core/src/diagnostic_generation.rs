//! Pure projection of certified semantic safety evidence into structured
//! diagnostics.

use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::diagnostic::{
    compare_diagnostics, validate_diagnostic_order, CompilerPhase, Diagnostic, DiagnosticCategory,
    DiagnosticCode, DiagnosticOccurrence, Severity, SeverityBasis,
};
use crate::safety_analysis::{
    enforce_resource_limits, validate_analysis, validate_foundational_correspondence,
    validate_structural_correspondence, SafetyAnalysis, SafetyAnalysisErrorCode,
    SafetyAnalysisErrors, SafetyEvidence, SafetyFinding, SafetyFindingCode,
    StructuralRelationshipRef, MAX_SAFETY_FINDINGS,
};
use crate::semantic::SemanticProgram;
use crate::semantic_analysis::SemanticFacts;
use crate::source::NodeId;
use crate::structural_analysis::StructuralFacts;
use crate::validation::{Validate, ValidationCode, ValidationErrors};

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

/// Maximum diagnostics produced by one generation invocation.
pub const MAX_GENERATED_DIAGNOSTICS: usize = MAX_SAFETY_FINDINGS;

/// Stable semantic evidence retained beside one contract diagnostic.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiagnosticProvenance {
    pub primary_node_id: NodeId,
    pub contributing_node_ids: Vec<NodeId>,
    pub relationship: Option<StructuralRelationshipRef>,
    pub safety_evidence: SafetyEvidence,
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
}

impl DiagnosticGeneration {
    /// Iterate evidence-bearing generation records in contract diagnostic order.
    pub fn records(&self) -> impl ExactSizeIterator<Item = &GeneratedDiagnostic> {
        self.records.iter()
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
/// The stage validates correspondence and evidence shape but never derives a
/// safety condition. Current typed uncertainty is intentionally not promoted
/// into a diagnostic.
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

    let mut records: Vec<_> = canonical_safety
        .findings()
        .map(|finding| build_record(input, finding))
        .collect::<Result<_, _>>()?;
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

    Ok(DiagnosticGeneration { records })
}

fn build_record(
    input: &SemanticProgram,
    finding: &SafetyFinding,
) -> Result<GeneratedDiagnostic, DiagnosticGenerationErrors> {
    let (code, severity, message) = diagnostic_policy(finding.code);
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
            primary_location: None,
            related_locations: None,
            advice: None,
            fixes: None,
        },
        provenance: DiagnosticProvenance {
            primary_node_id: finding.primary_node_id.clone(),
            contributing_node_ids: finding.evidence_node_ids.clone(),
            relationship: relationship(&finding.evidence).cloned(),
            safety_evidence: finding.evidence.clone(),
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
            "Nested repetitions have a proved overlapping consumption structure.",
        ),
        SafetyFindingCode::RepeatedAlternationOverlap => (
            SAFETY_REPEATED_ALTERNATION_OVERLAP,
            Severity::Warning,
            "Repeated alternatives have proved overlapping leading consumption.",
        ),
        SafetyFindingCode::RepetitionFollowerOverlap => (
            SAFETY_REPETITION_FOLLOWER_OVERLAP,
            Severity::Warning,
            "A repetition and its follower have proved overlapping leading consumption.",
        ),
    }
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
        .then_with(|| {
            left.provenance
                .safety_evidence
                .cmp(&right.provenance.safety_evidence)
        })
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
