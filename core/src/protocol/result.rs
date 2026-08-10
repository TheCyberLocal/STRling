use serde::{Deserialize, Serialize};

use super::{AnalysisResult, CompilerIdentity};
use crate::diagnostic::{validate_diagnostic_order, Diagnostic};
use crate::semantic::SemanticProgram;
use crate::source::{ContractVersion, SpecificationVersion};
use crate::target::{PortabilityPlan, PortabilityStatus, TargetArtifact};
use crate::validation::{
    deserialize_optional_non_null, Validate, ValidationCode, ValidationError, ValidationErrors,
};

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CompileOutcome {
    Succeeded,
    Failed,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticResultStatus {
    Complete,
    Partial,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticResult {
    pub status: SemanticResultStatus,
    pub program: SemanticProgram,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CompileResult {
    pub contract_version: ContractVersion,
    pub compiler: CompilerIdentity,
    pub specification_version: SpecificationVersion,
    pub outcome: CompileOutcome,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub semantic_result: Option<SemanticResult>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub analysis: Option<AnalysisResult>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub portability: Option<PortabilityPlan>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub artifact: Option<TargetArtifact>,
    pub diagnostics: Vec<Diagnostic>,
}

impl Validate for CompileResult {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        for diagnostic in &self.diagnostics {
            if let Err(found) = diagnostic.validate() {
                errors.extend(found);
            }
        }
        if let Err(found) = validate_diagnostic_order(&self.diagnostics) {
            errors.extend(found);
        }
        let has_error = self.diagnostics.iter().any(Diagnostic::is_error);
        if self.outcome == CompileOutcome::Succeeded && has_error {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.outcome",
                "successful result cannot contain an error diagnostic",
            ));
        }
        if self.outcome == CompileOutcome::Failed && !has_error {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.outcome",
                "failed result must contain at least one error diagnostic",
            ));
        }

        if let Some(semantic) = &self.semantic_result {
            if let Err(found) = semantic.program.validate() {
                errors.extend(found);
            }
            if semantic.program.specification_version != self.specification_version {
                errors.push(ValidationError::new(
                    ValidationCode::SpecificationMismatch,
                    "$.semantic_result.program.specification_version",
                    "semantic result specification must match compile result",
                ));
            }
            if semantic.status == SemanticResultStatus::Partial {
                if self.outcome != CompileOutcome::Failed {
                    errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        "$.semantic_result.status",
                        "partial semantics occur only on failed results",
                    ));
                }
                if self.analysis.is_some() || self.portability.is_some() || self.artifact.is_some()
                {
                    errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        "$.semantic_result",
                        "partial semantics cannot feed analysis, planning, or emission",
                    ));
                }
            }
            if self.outcome == CompileOutcome::Succeeded
                && semantic.status != SemanticResultStatus::Complete
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    "$.semantic_result.status",
                    "successful semantic result must be complete",
                ));
            }
        }

        if let Some(analysis) = &self.analysis {
            if let Err(found) = analysis.validate() {
                errors.extend(found);
            }
            if analysis.specification_version != self.specification_version {
                errors.push(ValidationError::new(
                    ValidationCode::SpecificationMismatch,
                    "$.analysis.specification_version",
                    "analysis specification must match compile result",
                ));
            }
        }
        if let Some(portability) = &self.portability {
            if let Err(found) = portability.validate() {
                errors.extend(found);
            }
            if portability.specification_version != self.specification_version {
                errors.push(ValidationError::new(
                    ValidationCode::SpecificationMismatch,
                    "$.portability.specification_version",
                    "portability specification must match compile result",
                ));
            }
        }
        if let Some(artifact) = &self.artifact {
            if let Err(found) = artifact.validate() {
                errors.extend(found);
            }
            if has_error {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    "$.artifact",
                    "error diagnostics suppress emitted artifacts",
                ));
            }
            if artifact.specification_version != self.specification_version {
                errors.push(ValidationError::new(
                    ValidationCode::SpecificationMismatch,
                    "$.artifact.specification_version",
                    "artifact specification must match compile result",
                ));
            }
            if let Some(portability) = &self.portability {
                if portability.status == PortabilityStatus::Unsupported {
                    errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        "$.artifact",
                        "unsupported portability cannot produce an artifact",
                    ));
                }
                if artifact.target_profile != portability.target_profile {
                    errors.push(ValidationError::new(
                        ValidationCode::UnresolvedReference,
                        "$.artifact.target_profile",
                        "artifact and portability profiles must match",
                    ));
                }
                if PortabilityStatus::from(artifact.portability_status) != portability.status {
                    errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        "$.artifact.portability_status",
                        "artifact and portability statuses must match",
                    ));
                }
            }
            for diagnostic in &artifact.emission_diagnostics {
                if !self.diagnostics.contains(diagnostic) {
                    errors.push(ValidationError::new(
                        ValidationCode::UnresolvedReference,
                        "$.artifact.emission_diagnostics",
                        "artifact diagnostics must also occur in result diagnostics",
                    ));
                }
            }
        }
        errors.finish()
    }
}
