//! Version-aware target profile, portability, and artifact contracts.

mod profile;
pub use profile::*;

use std::convert::TryFrom;

use serde::{Deserialize, Deserializer, Serialize};

use crate::diagnostic::{validate_diagnostic_order, CompilerPhase, Diagnostic, Severity};
use crate::source::{
    ContractVersion, CoordinateSystem, NodeId, Sha256Digest, SourceSpan, SpecificationVersion,
    Utf8Encoding,
};
use crate::validation::{Validate, ValidationCode, ValidationError, ValidationErrors};

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

fn prefixed_scoped_identifier(value: &str, prefix: &str) -> bool {
    value
        .strip_prefix(prefix)
        .is_some_and(scoped_lower_identifier)
}

fn profile_id(value: &str) -> bool {
    let Some(remainder) = value.strip_prefix("profile:") else {
        return false;
    };
    let mut characters = remainder.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    remainder.len() <= 128
        && (first.is_ascii_lowercase() || first.is_ascii_digit())
        && characters.all(|character| {
            character.is_ascii_lowercase()
                || character.is_ascii_digit()
                || matches!(character, '.' | '_' | '/' | '-')
        })
}

fn canonical_number(value: &str) -> bool {
    value == "0"
        || (value.starts_with(|character: char| matches!(character, '1'..='9'))
            && value.chars().all(|character| character.is_ascii_digit()))
}

fn semantic_version(value: &str) -> bool {
    let mut parts = value.split('.');
    matches!(
        (parts.next(), parts.next(), parts.next(), parts.next()),
        (Some(major), Some(minor), Some(patch), None)
            if canonical_number(major)
                && canonical_number(minor)
                && canonical_number(patch)
    )
}

macro_rules! validated_string {
    ($name:ident, $validator:expr, $description:literal) => {
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
                let validator: fn(&str) -> bool = $validator;
                if validator(value) {
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

validated_string!(ProfileId, profile_id, "target profile identity");
validated_string!(ProfileVersion, semantic_version, "target profile version");
validated_string!(
    RequirementId,
    |value: &str| prefixed_scoped_identifier(value, "requirement:"),
    "requirement identity"
);
validated_string!(CapabilityId, scoped_lower_identifier, "capability identity");
validated_string!(OptionId, scoped_lower_identifier, "engine option identity");
validated_string!(
    ResolutionCode,
    scoped_lower_identifier,
    "target resolution code"
);
validated_string!(
    ReasonCode,
    scoped_lower_identifier,
    "portability reason code"
);

/// Immutable target profile identity, schema revision, and canonical fingerprint.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TargetProfileReference {
    pub profile_id: ProfileId,
    pub profile_version: ProfileVersion,
    pub sha256: Sha256Digest,
}

impl Validate for TargetProfileReference {
    fn validate(&self) -> Result<(), ValidationErrors> {
        Ok(())
    }
}

/// The complete and only portability vocabulary.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PortabilityStatus {
    Native,
    EquivalentRewrite,
    Unsupported,
}

/// One requirement-to-capability decision.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PortabilityDecision {
    pub requirement_id: RequirementId,
    pub capability_id: CapabilityId,
    pub node_ids: Vec<NodeId>,
    pub status: PortabilityStatus,
    pub reason_code: ReasonCode,
}

/// Target-profile comparison result. No planning algorithm is implemented here.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PortabilityPlan {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub target_profile: TargetProfileReference,
    pub status: PortabilityStatus,
    pub decisions: Vec<PortabilityDecision>,
}

impl Validate for PortabilityPlan {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if self
            .decisions
            .windows(2)
            .any(|pair| pair[0].requirement_id >= pair[1].requirement_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.decisions",
                "portability decisions require unique sorted requirement identities",
            ));
        }
        for (index, decision) in self.decisions.iter().enumerate() {
            if decision.node_ids.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    format!("$.decisions[{index}].node_ids"),
                    "portability decision requires at least one node identity",
                ));
            }
            if decision.node_ids.windows(2).any(|pair| pair[0] >= pair[1]) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.decisions[{index}].node_ids"),
                    "decision node identities must be unique and sorted",
                ));
            }
        }
        let expected = self
            .decisions
            .iter()
            .map(|decision| decision.status)
            .max()
            .unwrap_or(PortabilityStatus::Native);
        if self.status != expected {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.status",
                "overall portability must equal the least-supported decision",
            ));
        }
        errors.finish()
    }
}

/// Artifact statuses exclude unsupported because unsupported plans cannot emit.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ArtifactPortabilityStatus {
    Native,
    EquivalentRewrite,
}

impl From<ArtifactPortabilityStatus> for PortabilityStatus {
    fn from(value: ArtifactPortabilityStatus) -> Self {
        match value {
            ArtifactPortabilityStatus::Native => Self::Native,
            ArtifactPortabilityStatus::EquivalentRewrite => Self::EquivalentRewrite,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum PatternSyntax {
    #[serde(rename = "regex")]
    Regex,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EmittedPattern {
    pub syntax: PatternSyntax,
    pub encoding: Utf8Encoding,
    pub text: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub flags: Vec<String>,
}

/// JSON scalar selected for an engine option.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(untagged)]
pub enum EngineOptionValue {
    String(String),
    Number(serde_json::Number),
    Boolean(bool),
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum OptionStage {
    Compile,
    Runtime,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EngineOption {
    pub option_id: OptionId,
    pub stage: OptionStage,
    pub value: EngineOptionValue,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ResolvedRequirement {
    pub requirement_id: RequirementId,
    pub capability_id: CapabilityId,
    pub status: ArtifactPortabilityStatus,
    pub resolution_code: ResolutionCode,
}

/// Half-open UTF-8 byte span in emitted pattern text.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct GeneratedSpan {
    pub coordinate_system: CoordinateSystem,
    pub start: u64,
    pub end: u64,
}

impl GeneratedSpan {
    fn validate_against(&self, text: &str) -> Result<(), ValidationErrors> {
        let start = usize::try_from(self.start).ok();
        let end = usize::try_from(self.end).ok();
        if self.start > self.end {
            return Err(ValidationErrors::single(ValidationError::new(
                ValidationCode::InvalidSpan,
                "$.generated_span",
                "generated span start must not exceed end",
            )));
        }
        if start.map_or(true, |offset| !text.is_char_boundary(offset))
            || end.map_or(true, |offset| !text.is_char_boundary(offset))
        {
            return Err(ValidationErrors::single(ValidationError::new(
                ValidationCode::Utf8Boundary,
                "$.generated_span",
                "generated span endpoints must be UTF-8 pattern boundaries",
            )));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SourceMapEntry {
    pub generated_span: GeneratedSpan,
    pub node_ids: Vec<NodeId>,
    pub source_spans: Vec<SourceSpan>,
}

/// Deterministic target-specific material, kept separate from Semantic IR.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TargetArtifact {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub target_profile: TargetProfileReference,
    pub portability_status: ArtifactPortabilityStatus,
    pub pattern: EmittedPattern,
    pub engine_options: Vec<EngineOption>,
    pub requirements: Vec<ResolvedRequirement>,
    pub source_map: Vec<SourceMapEntry>,
    pub emission_diagnostics: Vec<Diagnostic>,
}

impl Validate for TargetArtifact {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if self.pattern.flags.windows(2).any(|pair| pair[0] >= pair[1]) {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.pattern.flags",
                "pattern flags must be unique and sorted",
            ));
        }
        for (index, flag) in self.pattern.flags.iter().enumerate() {
            if flag.len() != 1 || !flag.bytes().all(|byte| byte.is_ascii_lowercase()) {
                errors.push(ValidationError::new(
                    ValidationCode::InvalidIdentity,
                    format!("$.pattern.flags[{index}]"),
                    "pattern flag must be one lowercase ASCII letter",
                ));
            }
        }
        if self
            .engine_options
            .windows(2)
            .any(|pair| (&pair[0].option_id, pair[0].stage) >= (&pair[1].option_id, pair[1].stage))
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.engine_options",
                "engine options must have unique sorted option/stage keys",
            ));
        }
        if self
            .requirements
            .windows(2)
            .any(|pair| pair[0].requirement_id >= pair[1].requirement_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.requirements",
                "resolved requirements require unique sorted identities",
            ));
        }
        let expected = self
            .requirements
            .iter()
            .map(|requirement| requirement.status)
            .max()
            .unwrap_or(ArtifactPortabilityStatus::Native);
        if self.portability_status != expected {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.portability_status",
                "artifact status must equal its least-supported requirement",
            ));
        }
        if self
            .source_map
            .windows(2)
            .any(|pair| pair[0].generated_span >= pair[1].generated_span)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.source_map",
                "source map requires unique sorted generated spans",
            ));
        }
        for (index, entry) in self.source_map.iter().enumerate() {
            if let Err(found) = entry.generated_span.validate_against(&self.pattern.text) {
                errors.extend(found);
            }
            if entry.node_ids.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    format!("$.source_map[{index}].node_ids"),
                    "source-map entry requires at least one node identity",
                ));
            }
            if entry.node_ids.windows(2).any(|pair| pair[0] >= pair[1]) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.source_map[{index}].node_ids"),
                    "source-map node identities must be unique and sorted",
                ));
            }
            if entry.source_spans.windows(2).any(|pair| pair[0] >= pair[1]) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.source_map[{index}].source_spans"),
                    "source-map source spans must be unique and sorted",
                ));
            }
            for span in &entry.source_spans {
                if let Err(found) = span.validate() {
                    errors.extend(found);
                }
            }
        }
        for (index, diagnostic) in self.emission_diagnostics.iter().enumerate() {
            if let Err(found) = diagnostic.validate() {
                errors.extend(found);
            }
            if diagnostic.severity == Severity::Error {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("$.emission_diagnostics[{index}].severity"),
                    "emitted artifact cannot contain an error diagnostic",
                ));
            }
            if !matches!(
                diagnostic.phase,
                CompilerPhase::TargetLowering | CompilerPhase::Emission
            ) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("$.emission_diagnostics[{index}].phase"),
                    "artifact diagnostics must belong to target lowering or emission",
                ));
            }
        }
        if let Err(found) = validate_diagnostic_order(&self.emission_diagnostics) {
            errors.extend(found);
        }
        errors.finish()
    }
}

impl TargetArtifact {
    /// Validate profile-dependent artifact invariants without resolving files or networks.
    pub fn validate_against_profile(
        &self,
        profile: &TargetProfile,
    ) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if let Err(found) = self.validate() {
            errors.extend(found);
        }
        if let Err(found) = profile.validate() {
            errors.extend(found);
        }
        match profile.reference() {
            Ok(reference) if reference != self.target_profile => {
                errors.push(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    "$.target_profile",
                    "artifact target profile identity, revision, or fingerprint does not match",
                ));
            }
            Err(found) => errors.extend(found),
            Ok(_) => {}
        }
        if !profile
            .compatible_specification_versions
            .contains(&self.specification_version)
        {
            errors.push(ValidationError::new(
                ValidationCode::SpecificationMismatch,
                "$.specification_version",
                "artifact specification is not compatible with its target profile",
            ));
        }

        for (index, option) in self.engine_options.iter().enumerate() {
            let declared = profile
                .options
                .iter()
                .find(|candidate| candidate.option_id == option.option_id);
            match declared {
                None => errors.push(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    format!("$.engine_options[{index}].option_id"),
                    "artifact option is not declared by the target profile",
                )),
                Some(declared)
                    if declared.stage != option.stage || declared.value != option.value =>
                {
                    errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        format!("$.engine_options[{index}]"),
                        "artifact option stage and value must equal the profile declaration",
                    ));
                }
                Some(_) => {}
            }
        }
        for required in profile
            .options
            .iter()
            .filter(|option| option.selection == OptionSelection::Required)
        {
            if !self
                .engine_options
                .iter()
                .any(|option| option.option_id == required.option_id)
            {
                errors.push(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    "$.engine_options",
                    format!(
                        "artifact omits required target option {}",
                        required.option_id.as_str()
                    ),
                ));
            }
        }
        errors.finish()
    }
}
