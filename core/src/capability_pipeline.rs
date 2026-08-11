//! Crate-private orchestration for the first target-aware compiler stage.

use std::error::Error;
use std::fmt;

use crate::capability_evaluation::{
    evaluate_capabilities, CapabilityEvaluation, CapabilityEvaluationErrors,
};
use crate::compiler_pipeline::{run_target_neutral_stages, CompilerPipelineErrors};
use crate::diagnostic::Diagnostic;
use crate::semantic::SemanticProgram;
use crate::target::TargetProfile;

#[derive(Debug)]
pub enum CapabilityPipelineErrors {
    TargetNeutral(CompilerPipelineErrors),
    CapabilityEvaluation(CapabilityEvaluationErrors),
}

impl fmt::Display for CapabilityPipelineErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::TargetNeutral(error) => error.fmt(formatter),
            Self::CapabilityEvaluation(error) => error.fmt(formatter),
        }
    }
}

impl Error for CapabilityPipelineErrors {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::TargetNeutral(error) => Some(error),
            Self::CapabilityEvaluation(error) => Some(error),
        }
    }
}

/// Target-neutral diagnostics and factual target support produced without a
/// portability plan, target lowering, or artifact.
pub struct CapabilityPipelineOutput {
    pub diagnostics: Vec<Diagnostic>,
    pub evaluation: CapabilityEvaluation,
}

/// Normalize and run every target-neutral analysis before factual capability
/// evaluation against the supplied immutable profile.
pub fn compile_semantic_capabilities(
    input: &SemanticProgram,
    target: &TargetProfile,
) -> Result<CapabilityPipelineOutput, CapabilityPipelineErrors> {
    let stages =
        run_target_neutral_stages(input).map_err(CapabilityPipelineErrors::TargetNeutral)?;
    let evaluation = evaluate_capabilities(
        &stages.normalized,
        &stages.foundational,
        &stages.structural,
        target,
    )
    .map_err(CapabilityPipelineErrors::CapabilityEvaluation)?;
    Ok(CapabilityPipelineOutput {
        diagnostics: stages.diagnostics,
        evaluation,
    })
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::*;
    use crate::capability_evaluation::CapabilityDisposition;
    use crate::diagnostic_generation::SAFETY_UNBOUNDED_NULLABLE_REPETITION;

    const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");

    #[test]
    fn capability_stage_follows_target_neutral_diagnostics() {
        let semantic: SemanticProgram = serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": "sensitive",
            "root": {
                "node_id": "node:pipeline.atomic",
                "kind": "atomic",
                "body": {
                    "node_id": "node:pipeline.repeat",
                    "kind": "repeat",
                    "body": {
                        "node_id": "node:pipeline.empty",
                        "kind": "empty"
                    },
                    "min": 0,
                    "max": null,
                    "mode": "greedy"
                }
            }
        }))
        .expect("semantic fixture");
        let target: TargetProfile = serde_json::from_str(PCRE2_1042).expect("profile fixture");

        let output =
            compile_semantic_capabilities(&semantic, &target).expect("pipeline must complete");

        assert!(output.diagnostics.iter().any(|diagnostic| {
            diagnostic.code.as_str() == SAFETY_UNBOUNDED_NULLABLE_REPETITION
        }));
        assert_eq!(output.evaluation.results.len(), 1);
        assert_eq!(
            output.evaluation.results[0].disposition,
            CapabilityDisposition::Supported
        );
    }
}
