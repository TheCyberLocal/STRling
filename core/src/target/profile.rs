//! Versioned engine/runtime capability declarations.

use std::convert::TryFrom;

use serde::{Deserialize, Deserializer, Serialize};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use super::{
    scoped_lower_identifier, EngineOptionValue, OptionId, OptionStage, ProfileId, ProfileVersion,
    TargetProfileReference,
};
use crate::source::{ContractVersion, Sha256Digest, SpecificationVersion};
use crate::validation::{
    deserialize_optional_non_null, nonempty, Validate, ValidationCode, ValidationError,
    ValidationErrors,
};

macro_rules! profile_identifier {
    ($name:ident, $description:literal) => {
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
                if scoped_lower_identifier(value) {
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

profile_identifier!(EngineId, "engine identity");
profile_identifier!(RuntimeId, "runtime identity");
profile_identifier!(ConstraintId, "capability constraint identity");
profile_identifier!(ConstraintUnit, "capability constraint unit");
profile_identifier!(EvidenceId, "profile evidence identity");

fn canonical_numeric_part(value: &str) -> bool {
    value == "0"
        || (!value.starts_with('0')
            && !value.is_empty()
            && value.chars().all(|character| character.is_ascii_digit()))
}

fn semantic_version(value: &str) -> bool {
    let core_end = value.find(['-', '+']).unwrap_or(value.len());
    let core = &value[..core_end];
    let mut parts = core.split('.');
    if !matches!(
        (parts.next(), parts.next(), parts.next(), parts.next()),
        (Some(major), Some(minor), Some(patch), None)
            if canonical_numeric_part(major)
                && canonical_numeric_part(minor)
                && canonical_numeric_part(patch)
    ) {
        return false;
    }
    let suffix = &value[core_end..];
    if suffix.is_empty() {
        return true;
    }
    if let Some(prerelease) = suffix.strip_prefix('-') {
        let build_at = prerelease.find('+');
        let (prerelease, build) = build_at.map_or((prerelease, None), |index| {
            (&prerelease[..index], Some(&prerelease[index + 1..]))
        });
        return version_suffix(prerelease) && build.map_or(true, version_suffix);
    }
    suffix.strip_prefix('+').is_some_and(version_suffix)
}

fn version_suffix(value: &str) -> bool {
    !value.is_empty()
        && value
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || matches!(character, '.' | '-'))
}

fn dotted_numeric_version(value: &str) -> bool {
    let parts: Vec<_> = value.split('.').collect();
    (2..=4).contains(&parts.len()) && parts.iter().all(|part| canonical_numeric_part(part))
}

fn edition_version(value: &str) -> bool {
    value.len() == 4
        && !value.starts_with('0')
        && value.chars().all(|character| character.is_ascii_digit())
}

macro_rules! version_value {
    ($name:ident, $validator:ident, $description:literal) => {
        #[derive(Clone, Debug, Eq, Hash, PartialEq, Serialize)]
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

version_value!(SemanticVersion, semantic_version, "semantic version");
version_value!(
    DottedNumericVersion,
    dotted_numeric_version,
    "dotted numeric version"
);
version_value!(EditionVersion, edition_version, "edition version");

#[derive(Clone, Debug, Eq, Hash, PartialEq, Serialize)]
#[serde(transparent)]
pub struct OpaqueVersion(String);

impl OpaqueVersion {
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl TryFrom<&str> for OpaqueVersion {
    type Error = String;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        if !value.is_empty() && value.chars().count() <= 128 {
            Ok(Self(value.to_owned()))
        } else {
            Err(format!("invalid opaque version: {value}"))
        }
    }
}

impl<'de> Deserialize<'de> for OpaqueVersion {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Self::try_from(value.as_str()).map_err(serde::de::Error::custom)
    }
}

/// Explicitly tagged target version; callers never compare schemes by guessing.
#[derive(Clone, Debug, Deserialize, Eq, Hash, PartialEq, Serialize)]
#[serde(tag = "scheme", content = "value", rename_all = "snake_case")]
pub enum TargetVersion {
    Semver(SemanticVersion),
    DottedNumeric(DottedNumericVersion),
    Edition(EditionVersion),
    Opaque(OpaqueVersion),
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EngineIdentity {
    pub id: EngineId,
    pub version: TargetVersion,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeIdentity {
    pub id: RuntimeId,
    pub version: TargetVersion,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum CapabilityScopeKind {
    #[serde(rename = "enumerated")]
    Enumerated,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum UnlistedCapabilities {
    #[serde(rename = "unknown")]
    Unknown,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CapabilityScope {
    pub kind: CapabilityScopeKind,
    pub unlisted_capabilities: UnlistedCapabilities,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CapabilityAvailability {
    Available,
    Constrained,
    Unavailable,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ConstraintOperator {
    Equals,
    AtMost,
    AtLeast,
    OneOf,
    RequiresOption,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(untagged)]
pub enum ConstraintScalar {
    String(String),
    Number(serde_json::Number),
    Boolean(bool),
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(untagged)]
pub enum ConstraintValue {
    Scalar(ConstraintScalar),
    OneOf(Vec<ConstraintScalar>),
}

impl ConstraintValue {
    fn validate_at(&self, path: &str, errors: &mut ValidationErrors) {
        if let Self::OneOf(values) = self {
            if values.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    path,
                    "constraint value arrays require at least one scalar",
                ));
            }
            if values
                .iter()
                .enumerate()
                .any(|(index, value)| values[..index].contains(value))
            {
                errors.push(ValidationError::new(
                    ValidationCode::DuplicateIdentity,
                    path,
                    "constraint value arrays require unique JSON scalars",
                ));
            }
        }
    }

    fn required_option(&self) -> Option<&str> {
        match self {
            Self::Scalar(ConstraintScalar::String(value)) => Some(value),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CapabilityConstraint {
    pub constraint_id: ConstraintId,
    pub operator: ConstraintOperator,
    pub value: ConstraintValue,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub unit: Option<ConstraintUnit>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Capability {
    pub capability_id: super::CapabilityId,
    pub availability: CapabilityAvailability,
    pub constraints: Vec<CapabilityConstraint>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum OptionSelection {
    Required,
    ProfileDefault,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ProfileOption {
    pub option_id: OptionId,
    pub stage: OptionStage,
    pub value: EngineOptionValue,
    pub selection: OptionSelection,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceAuthority {
    NormativeStandard,
    EngineDocumentation,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TargetEvidence {
    pub evidence_id: EvidenceId,
    pub authority: EvidenceAuthority,
    pub url: String,
    pub locator: String,
}

/// One immutable, enumerated-scope target capability declaration.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TargetProfile {
    pub contract_version: ContractVersion,
    pub profile_id: ProfileId,
    pub profile_version: ProfileVersion,
    pub engine: EngineIdentity,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub runtime: Option<RuntimeIdentity>,
    pub compatible_specification_versions: Vec<SpecificationVersion>,
    pub capability_scope: CapabilityScope,
    pub capabilities: Vec<Capability>,
    pub options: Vec<ProfileOption>,
    pub evidence: Vec<TargetEvidence>,
}

impl TargetProfile {
    /// Compute the canonical JSON fingerprint used by immutable references.
    pub fn reference(&self) -> Result<TargetProfileReference, ValidationErrors> {
        let mut value = serde_json::to_value(self).map_err(|error| {
            ValidationErrors::single(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$",
                format!("target profile could not be serialized: {error}"),
            ))
        })?;
        canonicalize(&mut value);
        let bytes = serde_json::to_vec(&value).map_err(|error| {
            ValidationErrors::single(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$",
                format!("target profile canonical JSON failed: {error}"),
            ))
        })?;
        let digest: [u8; 32] = Sha256::digest(bytes).into();
        Ok(TargetProfileReference {
            profile_id: self.profile_id.clone(),
            profile_version: self.profile_version.clone(),
            sha256: Sha256Digest::from_bytes(digest),
        })
    }
}

fn canonicalize(value: &mut Value) {
    match value {
        Value::Array(items) => {
            for item in items {
                canonicalize(item);
            }
        }
        Value::Object(object) => {
            let mut entries: Vec<_> = std::mem::take(object).into_iter().collect();
            entries.sort_by(|left, right| left.0.cmp(&right.0));
            let mut sorted = Map::new();
            for (key, mut child) in entries {
                canonicalize(&mut child);
                sorted.insert(key, child);
            }
            *object = sorted;
        }
        _ => {}
    }
}

impl Validate for TargetProfile {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if self.compatible_specification_versions.is_empty() {
            errors.push(ValidationError::new(
                ValidationCode::EmptyCollection,
                "$.compatible_specification_versions",
                "target profile requires at least one compatible specification",
            ));
        }
        if self
            .compatible_specification_versions
            .windows(2)
            .any(|pair| pair[0] >= pair[1])
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.compatible_specification_versions",
                "compatible specification versions must be unique and sorted",
            ));
        }
        if self
            .capabilities
            .windows(2)
            .any(|pair| pair[0].capability_id >= pair[1].capability_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.capabilities",
                "capabilities must have unique sorted identities",
            ));
        }
        if self
            .options
            .windows(2)
            .any(|pair| pair[0].option_id >= pair[1].option_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.options",
                "profile options must have unique sorted identities",
            ));
        }
        if self.evidence.is_empty() {
            errors.push(ValidationError::new(
                ValidationCode::EmptyCollection,
                "$.evidence",
                "target profile requires authored evidence",
            ));
        }
        if self
            .evidence
            .windows(2)
            .any(|pair| pair[0].evidence_id >= pair[1].evidence_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.evidence",
                "profile evidence must have unique sorted identities",
            ));
        }

        for (index, capability) in self.capabilities.iter().enumerate() {
            let constrained = capability.availability == CapabilityAvailability::Constrained;
            if constrained != !capability.constraints.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("$.capabilities[{index}].constraints"),
                    "only constrained capabilities carry one or more constraints",
                ));
            }
            if capability
                .constraints
                .windows(2)
                .any(|pair| pair[0].constraint_id >= pair[1].constraint_id)
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.capabilities[{index}].constraints"),
                    "capability constraints must have unique sorted identities",
                ));
            }
            for (constraint_index, constraint) in capability.constraints.iter().enumerate() {
                let path = format!("$.capabilities[{index}].constraints[{constraint_index}].value");
                constraint.value.validate_at(&path, &mut errors);
                if constraint.operator == ConstraintOperator::RequiresOption {
                    let option_id = constraint.value.required_option();
                    if option_id.is_none()
                        || !self
                            .options
                            .iter()
                            .any(|option| Some(option.option_id.as_str()) == option_id)
                    {
                        errors.push(ValidationError::new(
                            ValidationCode::UnresolvedReference,
                            path,
                            "requires_option must name an option declared by the profile",
                        ));
                    }
                }
            }
        }
        for (index, evidence) in self.evidence.iter().enumerate() {
            if !evidence.url.starts_with("https://")
                || !evidence.url["https://".len()..].contains('.')
            {
                errors.push(ValidationError::new(
                    ValidationCode::InvalidUri,
                    format!("$.evidence[{index}].url"),
                    "target evidence requires an absolute HTTPS URI",
                ));
            }
            nonempty(
                &evidence.locator,
                format!("$.evidence[{index}].locator"),
                &mut errors,
            );
        }
        errors.finish()
    }
}

/// In-memory profile set used to resolve immutable references explicitly.
#[derive(Clone, Debug, Default)]
pub struct TargetProfileSet {
    profiles: Vec<TargetProfile>,
}

impl TargetProfileSet {
    pub fn new(profiles: Vec<TargetProfile>) -> Result<Self, ValidationErrors> {
        let set = Self { profiles };
        set.validate()?;
        Ok(set)
    }

    pub fn resolve(
        &self,
        reference: &TargetProfileReference,
    ) -> Result<&TargetProfile, ValidationErrors> {
        let profile = self
            .profiles
            .iter()
            .find(|profile| {
                profile.profile_id == reference.profile_id
                    && profile.profile_version == reference.profile_version
            })
            .ok_or_else(|| {
                ValidationErrors::single(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    "$.target_profile",
                    "target profile identity and revision are not present",
                ))
            })?;
        if profile.reference()? != *reference {
            return Err(ValidationErrors::single(ValidationError::new(
                ValidationCode::InvalidDigest,
                "$.target_profile.sha256",
                "target profile fingerprint does not match canonical JSON",
            )));
        }
        Ok(profile)
    }
}

impl Validate for TargetProfileSet {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        for (index, profile) in self.profiles.iter().enumerate() {
            if let Err(found) = profile.validate() {
                errors.extend(found);
            }
            if self.profiles[..index].iter().any(|existing| {
                existing.profile_id == profile.profile_id
                    && existing.profile_version == profile.profile_version
            }) {
                errors.push(ValidationError::new(
                    ValidationCode::DuplicateIdentity,
                    format!("$.profiles[{index}]"),
                    "target profile identity and revision must be unique",
                ));
            }
        }
        errors.finish()
    }
}
