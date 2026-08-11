//! Target-neutral compiler-stage orchestration through structured diagnostic
//! generation.

use std::error::Error;
use std::fmt;

use crate::diagnostic::Diagnostic;
use crate::diagnostic_generation::{
    generate_diagnostics, DiagnosticGenerationErrorCode, DiagnosticGenerationErrors,
    MAX_GENERATED_DIAGNOSTICS,
};
use crate::normalization::{normalize, NormalizationErrors};
use crate::protocol::{
    AnalysisResult, CompileOutcome, CompileResult, CompilerIdentity, LengthBounds, LengthMaximum,
    LengthUnit, NodeFacts as ProtocolNodeFacts, SemanticResult, SemanticResultStatus,
};
use crate::safety_analysis::{
    analyze_safety, SafetyAnalysisErrorCode, SafetyAnalysisErrors, MAX_SAFETY_NODES,
};
use crate::semantic::SemanticProgram;
use crate::semantic_analysis::{
    analyze, MaximumConsumption, Nullability, SemanticAnalysisErrorCode, SemanticAnalysisErrors,
    SemanticFacts, MAX_ANALYSIS_DEPTH,
};
use crate::structural_analysis::{
    analyze_structure, StructuralAnalysisErrorCode, StructuralAnalysisErrors, StructuralFacts,
};
use crate::validation::{Validate, ValidationErrors};

pub(crate) const MAX_PIPELINE_SEMANTIC_DEPTH: usize = MAX_ANALYSIS_DEPTH;
pub(crate) const MAX_PIPELINE_SEMANTIC_NODES: usize = MAX_SAFETY_NODES;
pub(crate) const MAX_PIPELINE_DIAGNOSTICS: usize = MAX_GENERATED_DIAGNOSTICS;

/// A whole-pipeline failure attributed to its owning target-neutral stage.
#[derive(Debug)]
pub enum CompilerPipelineErrors {
    Normalization(NormalizationErrors),
    FoundationalAnalysis(SemanticAnalysisErrors),
    StructuralAnalysis(StructuralAnalysisErrors),
    SafetyAnalysis(SafetyAnalysisErrors),
    DiagnosticGeneration(DiagnosticGenerationErrors),
    ResultValidation(ValidationErrors),
}

impl CompilerPipelineErrors {
    pub(crate) fn is_resource_exhaustion(&self) -> bool {
        match self {
            Self::FoundationalAnalysis(errors) => errors
                .errors
                .iter()
                .any(|error| error.code == SemanticAnalysisErrorCode::DepthLimitExceeded),
            Self::StructuralAnalysis(errors) => errors.errors.iter().any(|error| {
                matches!(
                    error.code,
                    StructuralAnalysisErrorCode::DepthLimitExceeded
                        | StructuralAnalysisErrorCode::RelationshipLimitExceeded
                )
            }),
            Self::SafetyAnalysis(errors) => errors.errors.iter().any(|error| {
                matches!(
                    error.code,
                    SafetyAnalysisErrorCode::DepthLimitExceeded
                        | SafetyAnalysisErrorCode::NodeLimitExceeded
                        | SafetyAnalysisErrorCode::FindingLimitExceeded
                        | SafetyAnalysisErrorCode::UncertaintyLimitExceeded
                )
            }),
            Self::DiagnosticGeneration(errors) => errors.errors.iter().any(|error| {
                matches!(
                    error.code,
                    DiagnosticGenerationErrorCode::DepthLimitExceeded
                        | DiagnosticGenerationErrorCode::NodeLimitExceeded
                        | DiagnosticGenerationErrorCode::DiagnosticLimitExceeded
                )
            }),
            Self::Normalization(_) | Self::ResultValidation(_) => false,
        }
    }
}
impl fmt::Display for CompilerPipelineErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Normalization(error) => error.fmt(formatter),
            Self::FoundationalAnalysis(error) => error.fmt(formatter),
            Self::StructuralAnalysis(error) => error.fmt(formatter),
            Self::SafetyAnalysis(error) => error.fmt(formatter),
            Self::DiagnosticGeneration(error) => error.fmt(formatter),
            Self::ResultValidation(error) => error.fmt(formatter),
        }
    }
}

impl Error for CompilerPipelineErrors {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Normalization(error) => Some(error),
            Self::FoundationalAnalysis(error) => Some(error),
            Self::StructuralAnalysis(error) => Some(error),
            Self::SafetyAnalysis(error) => Some(error),
            Self::DiagnosticGeneration(error) => Some(error),
            Self::ResultValidation(error) => Some(error),
        }
    }
}

/// Compile Semantic IR through target-neutral diagnostics without target
/// selection, lowering, or emission.
///
/// Safety diagnostics are advisory, so a valid semantic program returns a
/// successful `CompileResult` even when warnings or informational diagnostics
/// are present. The result deliberately has no portability plan or artifact.
pub fn compile_semantic_diagnostics(
    input: &SemanticProgram,
    compiler: &CompilerIdentity,
) -> Result<CompileResult, CompilerPipelineErrors> {
    let stages = run_target_neutral_stages(input)?;
    project_target_neutral_stages(stages, compiler)
}

/// Project one already-completed target-neutral stage bundle into the existing
/// compile-result contract without rerunning or reconstructing any stage.
pub(crate) fn project_target_neutral_stages(
    stages: TargetNeutralStages,
    compiler: &CompilerIdentity,
) -> Result<CompileResult, CompilerPipelineErrors> {
    let result = CompileResult {
        contract_version: stages.normalized.contract_version,
        compiler: compiler.clone(),
        specification_version: stages.normalized.specification_version.clone(),
        outcome: CompileOutcome::Succeeded,
        semantic_result: Some(SemanticResult {
            status: SemanticResultStatus::Complete,
            program: stages.normalized,
        }),
        analysis: Some(protocol_analysis(&stages.foundational)),
        portability: None,
        artifact: None,
        diagnostics: stages.diagnostics,
    };
    result
        .validate()
        .map_err(CompilerPipelineErrors::ResultValidation)?;
    Ok(result)
}

pub(crate) struct TargetNeutralStages {
    pub(crate) normalized: SemanticProgram,
    pub(crate) foundational: SemanticFacts,
    pub(crate) structural: StructuralFacts,
    pub(crate) diagnostics: Vec<Diagnostic>,
}

/// Execute every target-neutral stage exactly once in certified dependency
/// order. Target-aware consumers may borrow this completed bundle but
/// target-neutral stages never depend on those consumers.
pub(crate) fn run_target_neutral_stages(
    input: &SemanticProgram,
) -> Result<TargetNeutralStages, CompilerPipelineErrors> {
    let normalized = normalize(input).map_err(CompilerPipelineErrors::Normalization)?;
    let foundational =
        analyze(&normalized).map_err(CompilerPipelineErrors::FoundationalAnalysis)?;
    let structural = analyze_structure(&normalized, &foundational)
        .map_err(CompilerPipelineErrors::StructuralAnalysis)?;
    let safety = analyze_safety(&normalized, &foundational, &structural)
        .map_err(CompilerPipelineErrors::SafetyAnalysis)?;
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .map_err(CompilerPipelineErrors::DiagnosticGeneration)?
        .into_diagnostics();
    Ok(TargetNeutralStages {
        normalized,
        foundational,
        structural,
        diagnostics,
    })
}

fn protocol_analysis(foundational: &SemanticFacts) -> AnalysisResult {
    AnalysisResult {
        contract_version: foundational.contract_version,
        specification_version: foundational.specification_version.clone(),
        node_facts: foundational
            .iter()
            .map(|(node_id, facts)| ProtocolNodeFacts {
                node_id: node_id.clone(),
                nullable: match facts.nullability {
                    Nullability::Nullable => Some(true),
                    Nullability::NonNullable => Some(false),
                    Nullability::Unknown => None,
                },
                length_bounds: Some(LengthBounds {
                    min: facts.minimum_consumption,
                    max: match facts.maximum_consumption {
                        MaximumConsumption::Finite(maximum) => LengthMaximum::Bounded(maximum),
                        MaximumConsumption::Unbounded => LengthMaximum::Unbounded,
                    },
                    unit: LengthUnit::UnicodeScalarValues,
                }),
            })
            .collect(),
        feature_requirements: Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use serde_json::{json, Value};

    use super::*;
    use crate::diagnostic::Severity;
    use crate::diagnostic_generation::SAFETY_UNBOUNDED_NULLABLE_REPETITION;
    use crate::protocol::{CompileOutcome, SemanticResultStatus};
    use crate::semantic::Node;

    fn compiler() -> CompilerIdentity {
        serde_json::from_value(json!({
            "id": "strling-kernel",
            "version": "0.1.0"
        }))
        .expect("compiler identity must deserialize")
    }

    fn program(root: Value) -> SemanticProgram {
        serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": "sensitive",
            "root": root
        }))
        .expect("semantic program must deserialize")
    }

    #[test]
    fn safety_diagnostics_are_returned_without_target_artifacts() {
        let semantic = program(json!({
            "node_id": "node:nullable",
            "kind": "repeat",
            "body": {
                "node_id": "node:nullable.body",
                "kind": "empty"
            },
            "min": 0,
            "max": null,
            "mode": "greedy"
        }));

        let result = compile_semantic_diagnostics(&semantic, &compiler())
            .expect("target-neutral pipeline must succeed");

        assert_eq!(result.outcome, CompileOutcome::Succeeded);
        assert_eq!(result.diagnostics.len(), 1);
        assert_eq!(
            result.diagnostics[0].code.as_str(),
            SAFETY_UNBOUNDED_NULLABLE_REPETITION
        );
        assert_eq!(result.diagnostics[0].severity, Severity::Warning);
        assert!(result.diagnostics[0].primary_location.is_none());
        assert!(result.analysis.is_some());
        assert!(result.portability.is_none());
        assert!(result.artifact.is_none());
        let semantic_result = result
            .semantic_result
            .as_ref()
            .expect("pipeline must return normalized semantics");
        assert_eq!(semantic_result.status, SemanticResultStatus::Complete);
        result.validate().expect("pipeline result must validate");
    }

    #[test]
    fn finding_free_input_returns_an_empty_diagnostic_sequence() {
        let semantic = program(json!({
            "node_id": "node:literal",
            "kind": "literal",
            "text": "a"
        }));

        let result = compile_semantic_diagnostics(&semantic, &compiler())
            .expect("finding-free pipeline must succeed");

        assert!(result.diagnostics.is_empty());
        assert_eq!(result.outcome, CompileOutcome::Succeeded);
        assert!(result.analysis.is_some());
        assert!(result.portability.is_none());
        assert!(result.artifact.is_none());
    }

    #[test]
    fn pipeline_normalizes_before_analysis() {
        let semantic = program(json!({
            "node_id": "node:sequence",
            "kind": "sequence",
            "items": [
                {
                    "node_id": "node:left",
                    "kind": "literal",
                    "text": "a"
                },
                {
                    "node_id": "node:right",
                    "kind": "literal",
                    "text": "b"
                }
            ]
        }));

        let result = compile_semantic_diagnostics(&semantic, &compiler())
            .expect("normalizing pipeline must succeed");
        let normalized = &result
            .semantic_result
            .as_ref()
            .expect("pipeline must return normalized semantics")
            .program;

        assert!(matches!(
            &normalized.root,
            Node::Literal { node_id, text, .. }
                if node_id.as_str() == "node:left" && text == "ab"
        ));
        assert_eq!(
            result.analysis.as_ref().expect("analysis").node_facts.len(),
            1
        );
    }
}
