use std::convert::TryFrom;

use serde::{Deserialize, Deserializer, Serialize};

use crate::diagnostic::Severity;
use crate::semantic::SemanticProgram;
use crate::source::{ContractVersion, SourceDocument, SpecificationVersion};
use crate::target::TargetProfileReference;
use crate::validation::{
    deserialize_optional_non_null, Validate, ValidationCode, ValidationError, ValidationErrors,
};

fn scoped_lower_identifier(value: &str) -> bool {
    let mut characters = value.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    if !first.is_ascii_lowercase() {
        return false;
    }
    let mut separator = false;
    for character in characters {
        if character.is_ascii_lowercase() || character.is_ascii_digit() {
            separator = false;
        } else if matches!(character, '.' | '_' | '-') && !separator {
            separator = true;
        } else {
            return false;
        }
    }
    !separator
}

fn canonical_number(value: &str) -> bool {
    value == "0"
        || (value.starts_with(|character: char| matches!(character, '1'..='9'))
            && value.chars().all(|character| character.is_ascii_digit()))
}

fn compiler_version(value: &str) -> bool {
    let suffix_index = value.find(['-', '+']);
    let (core, suffix) = suffix_index.map_or((value, None), |index| {
        (&value[..index], Some(&value[index + 1..]))
    });
    let mut parts = core.split('.');
    let valid_core = matches!(
        (parts.next(), parts.next(), parts.next(), parts.next()),
        (Some(major), Some(minor), Some(patch), None)
            if canonical_number(major)
                && canonical_number(minor)
                && canonical_number(patch)
    );
    valid_core
        && suffix.map_or(true, |suffix| {
            !suffix.is_empty()
                && suffix.chars().all(|character| {
                    character.is_ascii_alphanumeric() || matches!(character, '.' | '-')
                })
        })
}

macro_rules! validated_string {
    ($name:ident, $validator:ident, $description:literal) => {
        #[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize)]
        #[serde(transparent)]
        pub struct $name(String);

        impl $name {
            #[must_use]
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }

        impl TryFrom<&str> for $name {
            type Error = String;

            fn try_from(value: &str) -> Result<Self, Self::Error> {
                if $validator(value) {
                    Ok(Self(value.to_owned()))
                } else {
                    Err(format!("invalid {}: {value}", $description))
                }
            }
        }

        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
            where
                D: Deserializer<'de>,
            {
                let value = String::deserialize(deserializer)?;
                Self::try_from(value.as_str()).map_err(serde::de::Error::custom)
            }
        }
    };
}

validated_string!(CompilerId, scoped_lower_identifier, "compiler identity");
validated_string!(CompilerVersion, compiler_version, "compiler version");

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CompilerIdentity {
    pub id: CompilerId,
    pub version: CompilerVersion,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum CompileInput {
    Source { document: Box<SourceDocument> },
    Semantic { program: Box<SemanticProgram> },
}

impl CompileInput {
    pub fn specification_version(&self) -> &SpecificationVersion {
        match self {
            Self::Source { document } => &document.specification_version,
            Self::Semantic { program } => &program.specification_version,
        }
    }

    pub(crate) fn validate_input(&self) -> Result<(), ValidationErrors> {
        match self {
            Self::Source { document } => document.validate(),
            Self::Semantic { program } => program.validate(),
        }
    }
}

impl Validate for CompileInput {
    fn validate(&self) -> Result<(), ValidationErrors> {
        self.validate_input()
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RequestedOutput {
    Semantic,
    Analysis,
    Portability,
    TargetArtifact,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PartialSemantics {
    Forbid,
    AllowForDiagnostics,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DiagnosticPolicy {
    pub minimum_severity: Severity,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ResourceLimits {
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub max_semantic_nodes: Option<u64>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub max_diagnostics: Option<u64>,
}

impl ResourceLimits {
    fn validate_at(&self, path: &str, errors: &mut ValidationErrors) {
        if self.max_semantic_nodes.is_none() && self.max_diagnostics.is_none() {
            errors.push(ValidationError::new(
                ValidationCode::EmptyValue,
                path,
                "resource limits require at least one bound",
            ));
        }
        if self.max_semantic_nodes == Some(0) {
            errors.push(ValidationError::new(
                ValidationCode::InvalidBounds,
                format!("{path}.max_semantic_nodes"),
                "semantic node limit must be at least one",
            ));
        }
        if self.max_diagnostics == Some(0) {
            errors.push(ValidationError::new(
                ValidationCode::InvalidBounds,
                format!("{path}.max_diagnostics"),
                "diagnostic limit must be at least one",
            ));
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CompilerOptions {
    pub partial_semantics: PartialSemantics,
    pub diagnostic_policy: DiagnosticPolicy,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub resource_limits: Option<ResourceLimits>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CompileRequest {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub input: CompileInput,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub target_profile: Option<TargetProfileReference>,
    pub requested_outputs: Vec<RequestedOutput>,
    pub compiler_options: CompilerOptions,
}

impl Validate for CompileRequest {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if let Err(found) = self.input.validate_input() {
            errors.extend(found);
        }
        if self.input.specification_version() != &self.specification_version {
            errors.push(ValidationError::new(
                ValidationCode::SpecificationMismatch,
                "$.input",
                "compile input and request specification versions must match",
            ));
        }
        if self.requested_outputs.is_empty() {
            errors.push(ValidationError::new(
                ValidationCode::EmptyCollection,
                "$.requested_outputs",
                "at least one output must be requested",
            ));
        }
        if self
            .requested_outputs
            .windows(2)
            .any(|pair| pair[0] >= pair[1])
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.requested_outputs",
                "requested outputs must be unique and canonically ordered",
            ));
        }
        let needs_profile = self.requested_outputs.iter().any(|output| {
            matches!(
                output,
                RequestedOutput::Portability | RequestedOutput::TargetArtifact
            )
        });
        if needs_profile && self.target_profile.is_none() {
            errors.push(ValidationError::new(
                ValidationCode::UnresolvedReference,
                "$.target_profile",
                "portability and artifact outputs require a target profile",
            ));
        }
        if let Some(profile) = &self.target_profile {
            if let Err(found) = profile.validate() {
                errors.extend(found);
            }
        }
        if let Some(limits) = &self.compiler_options.resource_limits {
            limits.validate_at("$.compiler_options.resource_limits", &mut errors);
        }
        errors.finish()
    }
}
