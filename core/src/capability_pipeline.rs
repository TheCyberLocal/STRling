//! Crate-private orchestration through canonical portability planning.

use std::error::Error;
use std::fmt;

use crate::capability_evaluation::{
    evaluate_capabilities, CapabilityEvaluation, CapabilityEvaluationErrorCode,
    CapabilityEvaluationErrors,
};
use crate::compiler_pipeline::{
    run_target_neutral_stages, CompilerPipelineErrors, TargetNeutralStages,
};
use crate::portability_planning::{
    plan_portability, PortabilityPlan, PortabilityPlanningErrorCode, PortabilityPlanningErrors,
};
use crate::semantic::SemanticProgram;
use crate::target::TargetProfile;

#[derive(Debug)]
pub enum PortabilityPipelineErrors {
    TargetNeutral(CompilerPipelineErrors),
    CapabilityEvaluation(CapabilityEvaluationErrors),
    PortabilityPlanning(PortabilityPlanningErrors),
}

impl PortabilityPipelineErrors {
    pub(crate) fn is_resource_exhaustion(&self) -> bool {
        match self {
            Self::TargetNeutral(error) => error.is_resource_exhaustion(),
            Self::CapabilityEvaluation(errors) => errors
                .errors
                .iter()
                .any(|error| error.code == CapabilityEvaluationErrorCode::RequirementLimitExceeded),
            Self::PortabilityPlanning(errors) => errors
                .errors
                .iter()
                .any(|error| error.code == PortabilityPlanningErrorCode::ResourceLimitExceeded),
        }
    }
}
impl fmt::Display for PortabilityPipelineErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::TargetNeutral(error) => error.fmt(formatter),
            Self::CapabilityEvaluation(error) => error.fmt(formatter),
            Self::PortabilityPlanning(error) => error.fmt(formatter),
        }
    }
}

impl Error for PortabilityPipelineErrors {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::TargetNeutral(error) => Some(error),
            Self::CapabilityEvaluation(error) => Some(error),
            Self::PortabilityPlanning(error) => Some(error),
        }
    }
}

/// Target-neutral diagnostics, factual support, and representation decisions
/// produced without applying rewrites, lowering, emission, or an artifact.
pub struct PortabilityPipelineOutput {
    pub stages: TargetNeutralStages,
    pub evaluation: CapabilityEvaluation,
    pub plan: PortabilityPlan,
}

/// Normalize and run every target-neutral analysis before factual capability
/// evaluation and pure portability planning against one immutable profile.
pub fn compile_semantic_portability(
    input: &SemanticProgram,
    target: &TargetProfile,
) -> Result<PortabilityPipelineOutput, PortabilityPipelineErrors> {
    let stages =
        run_target_neutral_stages(input).map_err(PortabilityPipelineErrors::TargetNeutral)?;
    let evaluation = evaluate_capabilities(
        &stages.normalized,
        &stages.foundational,
        &stages.structural,
        target,
    )
    .map_err(PortabilityPipelineErrors::CapabilityEvaluation)?;
    let plan = plan_portability(
        &stages.normalized,
        &stages.foundational,
        &stages.structural,
        target,
        &evaluation,
    )
    .map_err(PortabilityPipelineErrors::PortabilityPlanning)?;
    Ok(PortabilityPipelineOutput {
        stages,
        evaluation,
        plan,
    })
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::*;
    use crate::capability_evaluation::CapabilityDisposition;
    use crate::diagnostic_generation::SAFETY_UNBOUNDED_NULLABLE_REPETITION;
    use crate::portability_planning::RequirementPlanningDisposition;
    use crate::target::PortabilityStatus;

    const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
    const ECMASCRIPT_2024: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

    #[test]
    fn planning_follows_capabilities_without_changing_safety_diagnostics() {
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
            compile_semantic_portability(&semantic, &target).expect("pipeline must complete");

        assert!(output.stages.diagnostics.iter().any(|diagnostic| {
            diagnostic.code.as_str() == SAFETY_UNBOUNDED_NULLABLE_REPETITION
        }));
        assert_eq!(output.evaluation.results.len(), 1);
        assert_eq!(
            output.evaluation.results[0].disposition,
            CapabilityDisposition::Supported
        );
        assert_eq!(output.plan.status, Some(PortabilityStatus::Native));
    }

    #[test]
    fn pipeline_can_plan_a_rewrite_without_applying_it() {
        let semantic: SemanticProgram = serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": "sensitive",
            "root": {
                "node_id": "node:pipeline.atomic-literal",
                "kind": "atomic",
                "body": {
                    "node_id": "node:pipeline.literal",
                    "kind": "literal",
                    "text": "x"
                }
            }
        }))
        .expect("semantic fixture");
        let original = semantic.clone();
        let target: TargetProfile = serde_json::from_str(ECMASCRIPT_2024).expect("profile fixture");

        let output =
            compile_semantic_portability(&semantic, &target).expect("pipeline must complete");

        assert_eq!(
            output.evaluation.results[0].disposition,
            CapabilityDisposition::Unsupported
        );
        assert!(matches!(
            output.plan.decisions[0].disposition,
            RequirementPlanningDisposition::EquivalentRewrite(_)
        ));
        assert_eq!(
            output.plan.status,
            Some(PortabilityStatus::EquivalentRewrite)
        );
        assert_eq!(semantic, original);
    }
}
