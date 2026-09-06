//! Versioned engine/runtime capability declarations.

use std::convert::TryFrom;

use serde::{Deserialize, Deserializer, Serialize};

use super::{
    scoped_lower_identifier, EngineOptionValue, OptionId, OptionStage, ProfileId, ProfileVersion,
    TargetProfileReference,
};
use crate::source::{ContractVersion, Sha256Digest, SpecificationVersion};
use crate::validation::{
    canonical_sha256, deserialize_optional_non_null, nonempty, Validate, ValidationCode,
    ValidationError, ValidationErrors,
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
profile_identifier!(SemanticSetId, "semantic set identity");
profile_identifier!(SemanticAlgorithmId, "semantic algorithm identity");
profile_identifier!(TargetLimitId, "target limit identity");
profile_identifier!(SemanticFactRole, "semantic fact role");
profile_identifier!(AlgorithmVariantId, "semantic algorithm variant identity");

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

fn unicode_version(value: &str) -> bool {
    let parts: Vec<_> = value.split('.').collect();
    parts.len() == 3 && parts.iter().all(|part| canonical_numeric_part(part))
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
version_value!(
    FixedUnicodeVersion,
    unicode_version,
    "fixed Unicode version"
);

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum UnicodeVersion {
    Fixed { value: FixedUnicodeVersion },
    LatestUnicodeAtEdition { edition: EditionVersion },
}

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

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CharacterSetUniverse {
    Byte,
    UnicodeScalar,
}

#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ScalarRange {
    pub start: String,
    pub end: String,
}

#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(transparent)]
pub struct UnicodeGeneralCategory(String);

impl UnicodeGeneralCategory {
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl TryFrom<&str> for UnicodeGeneralCategory {
    type Error = String;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        const CATEGORIES: &[&str] = &[
            "C", "Cc", "Cf", "Cn", "Co", "Cs", "L", "Ll", "Lm", "Lo", "Lt", "Lu", "M", "Mc", "Me",
            "Mn", "N", "Nd", "Nl", "No", "P", "Pc", "Pd", "Pe", "Pf", "Pi", "Po", "Ps", "S", "Sc",
            "Sk", "Sm", "So", "Z", "Zl", "Zp", "Zs",
        ];
        if CATEGORIES.binary_search(&value).is_ok() {
            Ok(Self(value.to_owned()))
        } else {
            Err(format!("invalid Unicode general category: {value}"))
        }
    }
}

impl<'de> Deserialize<'de> for UnicodeGeneralCategory {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Self::try_from(value.as_str()).map_err(serde::de::Error::custom)
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub enum LineTerminator {
    #[serde(rename = "LF")]
    Lf,
    #[serde(rename = "VT")]
    Vt,
    #[serde(rename = "FF")]
    Ff,
    #[serde(rename = "CR")]
    Cr,
    #[serde(rename = "CRLF")]
    Crlf,
    #[serde(rename = "NEL")]
    Nel,
    #[serde(rename = "LS")]
    Ls,
    #[serde(rename = "PS")]
    Ps,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LineTerminatorSequencePolicy {
    IndependentCodePoints,
    AtomicLongest,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum SemanticSetDefinition {
    CharacterSet {
        universe: CharacterSetUniverse,
        scalars: Vec<String>,
        ranges: Vec<ScalarRange>,
        unicode_general_categories: Vec<UnicodeGeneralCategory>,
    },
    LineTerminatorSet {
        members: Vec<LineTerminator>,
        sequence_policy: LineTerminatorSequencePolicy,
    },
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticSet {
    pub set_id: SemanticSetId,
    pub definition: SemanticSetDefinition,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub unicode_version: Option<UnicodeVersion>,
    pub evidence: Vec<EvidenceId>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum BackreferenceUnsetBehavior {
    Empty,
    Fail,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CaptureResetBehavior {
    Reset,
    Retain,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CaseFoldingMode {
    Ascii,
    SimpleUnicode,
    FullUnicode,
    EngineSpecific,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum MatchingUnit {
    Byte,
    UnicodeCodePoint,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum SemanticAlgorithmDefinition {
    BackreferenceUnset {
        behavior: BackreferenceUnsetBehavior,
    },
    CaptureResetOnIteration {
        behavior: CaptureResetBehavior,
    },
    CaseFolding {
        mode: CaseFoldingMode,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        variant: Option<AlgorithmVariantId>,
        additional_equivalence_classes: Vec<Vec<String>>,
    },
    MatchingUnit {
        unit: MatchingUnit,
    },
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticAlgorithm {
    pub algorithm_id: SemanticAlgorithmId,
    pub definition: SemanticAlgorithmDefinition,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub unicode_version: Option<UnicodeVersion>,
    pub evidence: Vec<EvidenceId>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TargetLimitScope {
    SyntacticQuantifier,
    CompiledPattern,
    ResourceDependent,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TargetLimitOperator {
    Equals,
    AtMost,
    AtLeast,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum TargetLimitBound {
    Numeric {
        operator: TargetLimitOperator,
        value: u64,
        unit: ConstraintUnit,
    },
    Unknown,
    ResourceDependent,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TargetLimitPrediction {
    Exact,
    ArtifactAndConfigurationDependent,
    ResourceDependent,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TargetLimit {
    pub limit_id: TargetLimitId,
    pub scope: TargetLimitScope,
    pub bound: TargetLimitBound,
    pub prediction: TargetLimitPrediction,
    pub evidence: Vec<EvidenceId>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum SemanticFactReference {
    SemanticSet {
        role: SemanticFactRole,
        fact_id: SemanticSetId,
    },
    SemanticAlgorithm {
        role: SemanticFactRole,
        fact_id: SemanticAlgorithmId,
    },
    TargetLimit {
        role: SemanticFactRole,
        fact_id: TargetLimitId,
    },
}

impl SemanticFactReference {
    fn kind_name(&self) -> &'static str {
        match self {
            Self::SemanticAlgorithm { .. } => "semantic_algorithm",
            Self::SemanticSet { .. } => "semantic_set",
            Self::TargetLimit { .. } => "target_limit",
        }
    }

    fn role(&self) -> &SemanticFactRole {
        match self {
            Self::SemanticSet { role, .. }
            | Self::SemanticAlgorithm { role, .. }
            | Self::TargetLimit { role, .. } => role,
        }
    }

    fn fact_id(&self) -> &str {
        match self {
            Self::SemanticSet { fact_id, .. } => fact_id.as_str(),
            Self::SemanticAlgorithm { fact_id, .. } => fact_id.as_str(),
            Self::TargetLimit { fact_id, .. } => fact_id.as_str(),
        }
    }

    fn canonical_key(&self) -> (&'static str, &str, &str) {
        (self.kind_name(), self.role().as_str(), self.fact_id())
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Capability {
    pub capability_id: super::CapabilityId,
    pub availability: CapabilityAvailability,
    pub constraints: Vec<CapabilityConstraint>,
    pub semantic_fact_refs: Vec<SemanticFactReference>,
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
    pub semantic_sets: Vec<SemanticSet>,
    pub semantic_algorithms: Vec<SemanticAlgorithm>,
    pub target_limits: Vec<TargetLimit>,
    pub options: Vec<ProfileOption>,
    pub evidence: Vec<TargetEvidence>,
}

fn parse_unicode_scalar(value: &str) -> Option<u32> {
    let digits = value.strip_prefix("U+")?;
    if !(4..=6).contains(&digits.len())
        || !digits
            .bytes()
            .all(|byte| byte.is_ascii_digit() || matches!(byte, b'A'..=b'F'))
    {
        return None;
    }
    let scalar = u32::from_str_radix(digits, 16).ok()?;
    if scalar > 0x10_FFFF || (0xD800..=0xDFFF).contains(&scalar) {
        return None;
    }
    (format!("U+{scalar:04X}") == value).then_some(scalar)
}

fn validate_evidence_references(
    evidence: &[EvidenceId],
    path: &str,
    profile_evidence: &[TargetEvidence],
    errors: &mut ValidationErrors,
) {
    if evidence.is_empty() {
        errors.push(ValidationError::new(
            ValidationCode::EmptyCollection,
            path,
            "semantic facts require at least one evidence reference",
        ));
    }
    if evidence.windows(2).any(|pair| pair[0] >= pair[1]) {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalOrder,
            path,
            "semantic fact evidence references must be unique and sorted",
        ));
    }
    for (index, reference) in evidence.iter().enumerate() {
        if !profile_evidence
            .iter()
            .any(|candidate| candidate.evidence_id == *reference)
        {
            errors.push(ValidationError::new(
                ValidationCode::UnresolvedReference,
                format!("{path}[{index}]"),
                "semantic fact evidence reference is not declared by the profile",
            ));
        }
    }
}

fn validate_character_set(
    universe: CharacterSetUniverse,
    scalars: &[String],
    ranges: &[ScalarRange],
    categories: &[UnicodeGeneralCategory],
    unicode_version: Option<&UnicodeVersion>,
    definition_path: &str,
    unicode_version_path: &str,
    errors: &mut ValidationErrors,
) {
    if scalars.is_empty() && ranges.is_empty() && categories.is_empty() {
        errors.push(ValidationError::new(
            ValidationCode::EmptyCollection,
            definition_path,
            "character-set definitions require at least one member",
        ));
    }

    let parsed_scalars: Vec<_> = scalars
        .iter()
        .enumerate()
        .map(|(index, scalar)| {
            let parsed = parse_unicode_scalar(scalar);
            if parsed.is_none() {
                errors.push(ValidationError::new(
                    ValidationCode::InvalidIdentity,
                    format!("{definition_path}.scalars[{index}]"),
                    "character-set scalars require canonical U+XXXX Unicode scalar notation",
                ));
            }
            parsed
        })
        .collect();
    if parsed_scalars.windows(2).any(|pair| match pair {
        [Some(left), Some(right)] => left >= right,
        _ => false,
    }) {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalOrder,
            format!("{definition_path}.scalars"),
            "character-set scalars must be unique and sorted by scalar value",
        ));
    }

    let mut parsed_ranges = Vec::with_capacity(ranges.len());
    for (index, range) in ranges.iter().enumerate() {
        let start = parse_unicode_scalar(&range.start);
        let end = parse_unicode_scalar(&range.end);
        if start.is_none() {
            errors.push(ValidationError::new(
                ValidationCode::InvalidIdentity,
                format!("{definition_path}.ranges[{index}].start"),
                "character-set range starts require canonical U+XXXX Unicode scalar notation",
            ));
        }
        if end.is_none() {
            errors.push(ValidationError::new(
                ValidationCode::InvalidIdentity,
                format!("{definition_path}.ranges[{index}].end"),
                "character-set range ends require canonical U+XXXX Unicode scalar notation",
            ));
        }
        if matches!((start, end), (Some(start), Some(end)) if start >= end) {
            errors.push(ValidationError::new(
                ValidationCode::InvalidBounds,
                format!("{definition_path}.ranges[{index}]"),
                "character-set ranges must contain at least two increasing scalars",
            ));
        }
        parsed_ranges.push((start, end));
    }
    if parsed_ranges.windows(2).any(|pair| match pair {
        [(Some(_), Some(left_end)), (Some(right_start), Some(_))] => {
            left_end.saturating_add(1) >= *right_start
        }
        _ => false,
    }) {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalOrder,
            format!("{definition_path}.ranges"),
            "character-set ranges must be sorted, disjoint, and non-adjacent",
        ));
    }
    for (scalar_index, scalar) in parsed_scalars.iter().enumerate() {
        if scalar.is_some_and(|scalar| {
            parsed_ranges.iter().any(
                |(start, end)| matches!((start, end), (Some(start), Some(end)) if (*start..=*end).contains(&scalar)),
            )
        }) {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                format!("{definition_path}.scalars[{scalar_index}]"),
                "character-set scalars must not duplicate a declared range member",
            ));
        }
    }

    if categories.windows(2).any(|pair| pair[0] >= pair[1]) {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalOrder,
            format!("{definition_path}.unicode_general_categories"),
            "Unicode general categories must be unique and sorted",
        ));
    }
    for aggregate in ["C", "L", "M", "N", "P", "S", "Z"] {
        if categories
            .iter()
            .any(|category| category.as_str() == aggregate)
            && categories.iter().any(|category| {
                category.as_str().len() == 2 && category.as_str().starts_with(aggregate)
            })
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                format!("{definition_path}.unicode_general_categories"),
                "aggregate Unicode categories must not be combined with their subcategories",
            ));
        }
    }

    match universe {
        CharacterSetUniverse::Byte => {
            if parsed_scalars.iter().flatten().any(|scalar| *scalar > 0xFF)
                || parsed_ranges
                    .iter()
                    .any(|(_, end)| end.is_some_and(|end| end > 0xFF))
            {
                errors.push(ValidationError::new(
                    ValidationCode::InvalidBounds,
                    definition_path,
                    "byte character sets cannot contain values above U+00FF",
                ));
            }
            if !categories.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("{definition_path}.unicode_general_categories"),
                    "byte character sets cannot depend on Unicode general categories",
                ));
            }
            if unicode_version.is_some() {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    unicode_version_path,
                    "byte character sets cannot declare a Unicode version",
                ));
            }
        }
        CharacterSetUniverse::UnicodeScalar
            if !categories.is_empty() && unicode_version.is_none() =>
        {
            errors.push(ValidationError::new(
                ValidationCode::InvalidVersion,
                unicode_version_path,
                "category-derived character sets require an explicit Unicode version",
            ));
        }
        CharacterSetUniverse::UnicodeScalar => {}
    }
}

fn validate_equivalence_classes(
    classes: &[Vec<String>],
    path: &str,
    errors: &mut ValidationErrors,
) {
    let mut previous: Option<Vec<u32>> = None;
    let mut seen = Vec::new();
    for (class_index, class) in classes.iter().enumerate() {
        if class.len() < 2 {
            errors.push(ValidationError::new(
                ValidationCode::EmptyCollection,
                format!("{path}[{class_index}]"),
                "case-folding equivalence classes require at least two scalars",
            ));
        }
        let mut parsed = Vec::with_capacity(class.len());
        for (scalar_index, scalar) in class.iter().enumerate() {
            match parse_unicode_scalar(scalar) {
                Some(value) => parsed.push(value),
                None => errors.push(ValidationError::new(
                    ValidationCode::InvalidIdentity,
                    format!("{path}[{class_index}][{scalar_index}]"),
                    "case-folding equivalence classes require canonical Unicode scalars",
                )),
            }
        }
        if parsed.windows(2).any(|pair| pair[0] >= pair[1]) {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                format!("{path}[{class_index}]"),
                "case-folding equivalence-class scalars must be unique and sorted",
            ));
        }
        if previous
            .as_ref()
            .is_some_and(|previous| previous >= &parsed)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                path,
                "case-folding equivalence classes must be unique and sorted",
            ));
        }
        for scalar in &parsed {
            if seen.contains(scalar) {
                errors.push(ValidationError::new(
                    ValidationCode::DuplicateIdentity,
                    format!("{path}[{class_index}]"),
                    "a scalar may occur in only one additional equivalence class",
                ));
            }
            seen.push(*scalar);
        }
        previous = Some(parsed);
    }
}

fn definition_algorithm_id(definition: &SemanticAlgorithmDefinition) -> &'static str {
    match definition {
        SemanticAlgorithmDefinition::BackreferenceUnset { .. } => "backreference_unset",
        SemanticAlgorithmDefinition::CaptureResetOnIteration { .. } => "capture_reset_on_iteration",
        SemanticAlgorithmDefinition::CaseFolding { .. } => "case_folding",
        SemanticAlgorithmDefinition::MatchingUnit { .. } => "matching_unit",
    }
}

fn validate_algorithm(
    algorithm: &SemanticAlgorithm,
    index: usize,
    profile_evidence: &[TargetEvidence],
    errors: &mut ValidationErrors,
) {
    let path = format!("$.semantic_algorithms[{index}]");
    if algorithm.algorithm_id.as_str() != definition_algorithm_id(&algorithm.definition) {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalStructure,
            format!("{path}.algorithm_id"),
            "semantic algorithm identity must match its closed definition kind",
        ));
    }
    match &algorithm.definition {
        SemanticAlgorithmDefinition::CaseFolding {
            mode,
            variant,
            additional_equivalence_classes,
        } => {
            let unicode_sensitive = *mode != CaseFoldingMode::Ascii;
            if unicode_sensitive != algorithm.unicode_version.is_some() {
                errors.push(ValidationError::new(
                    ValidationCode::InvalidVersion,
                    format!("{path}.unicode_version"),
                    "Unicode-sensitive case folding requires exactly one Unicode version",
                ));
            }
            if (*mode == CaseFoldingMode::EngineSpecific) != variant.is_some() {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("{path}.definition.variant"),
                    "only engine-specific case folding requires a variant identity",
                ));
            }
            if *mode == CaseFoldingMode::Ascii && !additional_equivalence_classes.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("{path}.definition.additional_equivalence_classes"),
                    "ASCII case folding cannot declare Unicode equivalence classes",
                ));
            }
            validate_equivalence_classes(
                additional_equivalence_classes,
                &format!("{path}.definition.additional_equivalence_classes"),
                errors,
            );
        }
        SemanticAlgorithmDefinition::BackreferenceUnset { .. }
        | SemanticAlgorithmDefinition::CaptureResetOnIteration { .. }
        | SemanticAlgorithmDefinition::MatchingUnit { .. } => {
            if algorithm.unicode_version.is_some() {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("{path}.unicode_version"),
                    "this semantic algorithm is independent of Unicode data",
                ));
            }
        }
    }
    validate_evidence_references(
        &algorithm.evidence,
        &format!("{path}.evidence"),
        profile_evidence,
        errors,
    );
}

fn validate_limit(limit: &TargetLimit, index: usize, errors: &mut ValidationErrors) {
    let path = format!("$.target_limits[{index}]");
    let valid = match limit.scope {
        TargetLimitScope::SyntacticQuantifier => {
            matches!(limit.bound, TargetLimitBound::Numeric { .. })
                && limit.prediction == TargetLimitPrediction::Exact
        }
        TargetLimitScope::CompiledPattern => {
            !matches!(limit.bound, TargetLimitBound::ResourceDependent)
                && limit.prediction == TargetLimitPrediction::ArtifactAndConfigurationDependent
        }
        TargetLimitScope::ResourceDependent => {
            matches!(limit.bound, TargetLimitBound::ResourceDependent)
                && limit.prediction == TargetLimitPrediction::ResourceDependent
        }
    };
    if !valid {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalStructure,
            path,
            "target limit scope, bound, and prediction must preserve syntactic, compiled-pattern, and resource-dependent distinctions",
        ));
    }
    if limit.limit_id.as_str() == "compiled_pattern_size"
        && limit.scope != TargetLimitScope::CompiledPattern
    {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalStructure,
            format!("$.target_limits[{index}].limit_id"),
            "compiled_pattern_size must describe a compiled-pattern limit",
        ));
    }
    if limit.limit_id.as_str() == "syntactic_quantifier_bound"
        && limit.scope != TargetLimitScope::SyntacticQuantifier
    {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalStructure,
            format!("$.target_limits[{index}].limit_id"),
            "syntactic_quantifier_bound must describe a syntactic quantifier limit",
        ));
    }
}

fn capability_supports_word(capability: &Capability) -> bool {
    let Some(constraint) = capability
        .constraints
        .iter()
        .find(|constraint| constraint.constraint_id.as_str() == "class")
    else {
        return true;
    };
    match &constraint.value {
        ConstraintValue::Scalar(ConstraintScalar::String(value)) => value == "word",
        ConstraintValue::OneOf(values) => values
            .iter()
            .any(|value| matches!(value, ConstraintScalar::String(value) if value == "word")),
        ConstraintValue::Scalar(ConstraintScalar::Number(_) | ConstraintScalar::Boolean(_)) => {
            false
        }
    }
}

fn has_semantic_fact(capability: &Capability, kind: &str, role: &str, fact_id: &str) -> bool {
    capability.semantic_fact_refs.iter().any(|reference| {
        reference.kind_name() == kind
            && reference.role().as_str() == role
            && reference.fact_id() == fact_id
    })
}

fn require_semantic_fact(
    capability: &Capability,
    capability_index: usize,
    kind: &str,
    role: &str,
    fact_id: &str,
    errors: &mut ValidationErrors,
) {
    if !has_semantic_fact(capability, kind, role, fact_id) {
        errors.push(ValidationError::new(
            ValidationCode::UnresolvedReference,
            format!("$.capabilities[{capability_index}].semantic_fact_refs"),
            format!(
                "usable capability {} requires {kind} role {role} referencing {fact_id}",
                capability.capability_id.as_str()
            ),
        ));
    }
}

impl TargetProfile {
    /// Compute the canonical JSON fingerprint used by immutable references.
    pub fn reference(&self) -> Result<TargetProfileReference, ValidationErrors> {
        let digest = canonical_sha256(self).map_err(|error| {
            ValidationErrors::single(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$",
                format!("target profile canonical JSON failed: {error}"),
            ))
        })?;
        Ok(TargetProfileReference {
            profile_id: self.profile_id.clone(),
            profile_version: self.profile_version.clone(),
            sha256: Sha256Digest::from_bytes(digest),
        })
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
            .semantic_sets
            .windows(2)
            .any(|pair| pair[0].set_id >= pair[1].set_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.semantic_sets",
                "semantic sets must have unique sorted identities",
            ));
        }
        if self
            .semantic_algorithms
            .windows(2)
            .any(|pair| pair[0].algorithm_id >= pair[1].algorithm_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.semantic_algorithms",
                "semantic algorithms must have unique sorted identities",
            ));
        }
        if self
            .target_limits
            .windows(2)
            .any(|pair| pair[0].limit_id >= pair[1].limit_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.target_limits",
                "target limits must have unique sorted identities",
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

        for (index, set) in self.semantic_sets.iter().enumerate() {
            let path = format!("$.semantic_sets[{index}]");
            match &set.definition {
                SemanticSetDefinition::CharacterSet {
                    universe,
                    scalars,
                    ranges,
                    unicode_general_categories,
                } => validate_character_set(
                    *universe,
                    scalars,
                    ranges,
                    unicode_general_categories,
                    set.unicode_version.as_ref(),
                    &format!("{path}.definition"),
                    &format!("{path}.unicode_version"),
                    &mut errors,
                ),
                SemanticSetDefinition::LineTerminatorSet {
                    members,
                    sequence_policy,
                } => {
                    if members.is_empty() {
                        errors.push(ValidationError::new(
                            ValidationCode::EmptyCollection,
                            format!("{path}.definition.members"),
                            "line-terminator sets require at least one member",
                        ));
                    }
                    if members.windows(2).any(|pair| pair[0] >= pair[1]) {
                        errors.push(ValidationError::new(
                            ValidationCode::NonCanonicalOrder,
                            format!("{path}.definition.members"),
                            "line terminators must be unique and follow canonical semantic order",
                        ));
                    }
                    let has_crlf = members.contains(&LineTerminator::Crlf);
                    if has_crlf
                        && (!members.contains(&LineTerminator::Cr)
                            || !members.contains(&LineTerminator::Lf))
                    {
                        errors.push(ValidationError::new(
                            ValidationCode::NonCanonicalStructure,
                            format!("{path}.definition.members"),
                            "CRLF sequence semantics require both CR and LF members",
                        ));
                    }
                    if *sequence_policy == LineTerminatorSequencePolicy::AtomicLongest && !has_crlf
                    {
                        errors.push(ValidationError::new(
                            ValidationCode::NonCanonicalStructure,
                            format!("{path}.definition.sequence_policy"),
                            "atomic-longest line semantics require an explicit CRLF member",
                        ));
                    }
                    if set.unicode_version.is_some() {
                        errors.push(ValidationError::new(
                            ValidationCode::NonCanonicalStructure,
                            format!("{path}.unicode_version"),
                            "line-terminator sets are independent of Unicode data versions",
                        ));
                    }
                }
            }
            if set.set_id.as_str() == "line_terminators"
                && !matches!(
                    set.definition,
                    SemanticSetDefinition::LineTerminatorSet { .. }
                )
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("{path}.set_id"),
                    "line_terminators must use the line_terminator_set definition",
                ));
            }
            if set.set_id.as_str() == "wildcard_exclusions"
                && !matches!(set.definition, SemanticSetDefinition::CharacterSet { .. })
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("{path}.set_id"),
                    "wildcard_exclusions must use the character_set definition",
                ));
            }
            if set.set_id.as_str() == "word_characters"
                && !matches!(set.definition, SemanticSetDefinition::CharacterSet { .. })
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("{path}.set_id"),
                    "word_characters must use the character_set definition",
                ));
            }
            validate_evidence_references(
                &set.evidence,
                &format!("{path}.evidence"),
                &self.evidence,
                &mut errors,
            );
        }
        for (index, algorithm) in self.semantic_algorithms.iter().enumerate() {
            validate_algorithm(algorithm, index, &self.evidence, &mut errors);
        }
        for (index, limit) in self.target_limits.iter().enumerate() {
            validate_limit(limit, index, &mut errors);
            validate_evidence_references(
                &limit.evidence,
                &format!("$.target_limits[{index}].evidence"),
                &self.evidence,
                &mut errors,
            );
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
            if capability
                .semantic_fact_refs
                .windows(2)
                .any(|pair| pair[0].canonical_key() >= pair[1].canonical_key())
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.capabilities[{index}].semantic_fact_refs"),
                    "capability semantic fact references must have unique sorted kind, role, and fact identities",
                ));
            }
            if capability.semantic_fact_refs.windows(2).any(|pair| {
                pair[0].kind_name() == pair[1].kind_name() && pair[0].role() == pair[1].role()
            }) {
                errors.push(ValidationError::new(
                    ValidationCode::DuplicateIdentity,
                    format!("$.capabilities[{index}].semantic_fact_refs"),
                    "a capability may bind each semantic fact kind and role only once",
                ));
            }
            for (reference_index, reference) in capability.semantic_fact_refs.iter().enumerate() {
                let resolved = match reference {
                    SemanticFactReference::SemanticSet { fact_id, .. } => self
                        .semantic_sets
                        .iter()
                        .any(|candidate| candidate.set_id == *fact_id),
                    SemanticFactReference::SemanticAlgorithm { fact_id, .. } => self
                        .semantic_algorithms
                        .iter()
                        .any(|candidate| candidate.algorithm_id == *fact_id),
                    SemanticFactReference::TargetLimit { fact_id, .. } => self
                        .target_limits
                        .iter()
                        .any(|candidate| candidate.limit_id == *fact_id),
                };
                if !resolved {
                    errors.push(ValidationError::new(
                        ValidationCode::UnresolvedReference,
                        format!(
                            "$.capabilities[{index}].semantic_fact_refs[{reference_index}].fact_id"
                        ),
                        "capability semantic fact reference is not declared by the profile",
                    ));
                }
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

            if capability.availability != CapabilityAvailability::Unavailable {
                match capability.capability_id.as_str() {
                    "anchors.end_before_final_line_terminator"
                    | "anchors.line_end"
                    | "anchors.line_start" => require_semantic_fact(
                        capability,
                        index,
                        "semantic_set",
                        "line_terminators",
                        "line_terminators",
                        &mut errors,
                    ),
                    "boundaries.word" => require_semantic_fact(
                        capability,
                        index,
                        "semantic_set",
                        "word_characters",
                        "word_characters",
                        &mut errors,
                    ),
                    "character_classes.unicode" if capability_supports_word(capability) => {
                        require_semantic_fact(
                            capability,
                            index,
                            "semantic_set",
                            "word_characters",
                            "word_characters",
                            &mut errors,
                        );
                    }
                    "matching.case_insensitive" => require_semantic_fact(
                        capability,
                        index,
                        "semantic_algorithm",
                        "case_folding",
                        "case_folding",
                        &mut errors,
                    ),
                    "references.backreference" => {
                        require_semantic_fact(
                            capability,
                            index,
                            "semantic_algorithm",
                            "backreference_unset",
                            "backreference_unset",
                            &mut errors,
                        );
                        require_semantic_fact(
                            capability,
                            index,
                            "semantic_algorithm",
                            "capture_reset_on_iteration",
                            "capture_reset_on_iteration",
                            &mut errors,
                        );
                    }
                    "character_semantics.unicode_scalar" => require_semantic_fact(
                        capability,
                        index,
                        "semantic_algorithm",
                        "matching_unit",
                        "matching_unit",
                        &mut errors,
                    ),
                    "character_classes.wildcard" => {
                        require_semantic_fact(
                            capability,
                            index,
                            "semantic_algorithm",
                            "matching_unit",
                            "matching_unit",
                            &mut errors,
                        );
                        require_semantic_fact(
                            capability,
                            index,
                            "semantic_set",
                            "wildcard_exclusions",
                            "wildcard_exclusions",
                            &mut errors,
                        );
                    }
                    "repetition.bounded"
                        if !capability.semantic_fact_refs.iter().any(|reference| {
                            let SemanticFactReference::TargetLimit { fact_id, .. } = reference
                            else {
                                return false;
                            };
                            self.target_limits.iter().any(|limit| {
                                limit.limit_id == *fact_id
                                    && matches!(
                                        limit.scope,
                                        TargetLimitScope::SyntacticQuantifier
                                            | TargetLimitScope::CompiledPattern
                                    )
                            })
                        }) =>
                    {
                        errors.push(ValidationError::new(
                            ValidationCode::UnresolvedReference,
                            format!("$.capabilities[{index}].semantic_fact_refs"),
                            "usable repetition.bounded requires a syntactic-quantifier or compiled-pattern target-limit fact",
                        ));
                    }
                    _ => {}
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
