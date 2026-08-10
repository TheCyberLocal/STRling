//! Structured diagnostic contracts.

use std::cmp::Ordering;
use std::collections::BTreeSet;
use std::convert::TryFrom;

use serde::{Deserialize, Deserializer, Serialize};

use crate::source::{ContractVersion, SourceSpan};
use crate::validation::{
    deserialize_optional_non_null, nonempty, Validate, ValidationCode, ValidationError,
    ValidationErrors,
};

fn diagnostic_code(value: &str) -> bool {
    let Some(remainder) = value.strip_prefix("STRL-") else {
        return false;
    };
    let Some((scope, number)) = remainder.rsplit_once('-') else {
        return false;
    };
    let mut scope_characters = scope.chars();
    matches!(scope_characters.next(), Some(first) if first.is_ascii_uppercase())
        && scope_characters.all(|character| {
            character.is_ascii_uppercase() || character.is_ascii_digit() || character == '_'
        })
        && number.len() == 4
        && number.chars().all(|character| character.is_ascii_digit())
}

fn fix_id(value: &str) -> bool {
    let Some(remainder) = value.strip_prefix("fix:") else {
        return false;
    };
    scoped_lower_identifier(remainder)
}

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

validated_string!(DiagnosticCode, diagnostic_code, "diagnostic code");
validated_string!(FixId, fix_id, "fix identity");

/// Unique ordinal for one diagnostic occurrence in a deterministic result.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(transparent)]
pub struct DiagnosticOccurrence(u64);

impl DiagnosticOccurrence {
    #[must_use]
    pub fn new(value: u64) -> Self {
        Self(value)
    }

    #[must_use]
    pub fn get(self) -> u64 {
        self.0
    }
}

/// Diagnostic severity in normative ordering.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    Error,
    Warning,
    Info,
    Hint,
}

impl Severity {
    fn rank(self) -> u8 {
        match self {
            Self::Error => 0,
            Self::Warning => 1,
            Self::Info => 2,
            Self::Hint => 3,
        }
    }
}

/// Authority that owns a diagnostic's severity.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SeverityBasis {
    Normative,
    TargetProfile,
    CompilerPolicy,
}

/// Compiler phase in deterministic diagnostic order.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CompilerPhase {
    Protocol,
    FrontendParse,
    SemanticLowering,
    Normalization,
    SemanticAnalysis,
    Portability,
    TargetLowering,
    Emission,
}

impl CompilerPhase {
    fn rank(self) -> u8 {
        match self {
            Self::Protocol => 0,
            Self::FrontendParse => 1,
            Self::SemanticLowering => 2,
            Self::Normalization => 3,
            Self::SemanticAnalysis => 4,
            Self::Portability => 5,
            Self::TargetLowering => 6,
            Self::Emission => 7,
        }
    }
}

/// Stable diagnostic category independent of presentation text.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum DiagnosticCategory {
    MalformedRequest,
    UnsupportedFrontend,
    Syntax,
    SemanticValidity,
    Normalization,
    ResourceLimit,
    Portability,
    TargetCapability,
    Safety,
    Internal,
}

/// Explanatory relationship to the primary diagnostic location.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RelatedLocationRole {
    Cause,
    Definition,
    Reference,
    Context,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RelatedLocation {
    pub role: RelatedLocationRole,
    pub message: String,
    pub location: SourceSpan,
}

/// Non-identity diagnostic advice.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AdviceKind {
    Note,
    Help,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Advice {
    pub kind: AdviceKind,
    pub message: String,
}

/// Confidence that an edit can be applied automatically.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum FixApplicability {
    MachineApplicable,
    Suggested,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TextEdit {
    pub span: SourceSpan,
    pub replacement: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Fix {
    pub fix_id: FixId,
    pub title: String,
    pub applicability: FixApplicability,
    pub edits: Vec<TextEdit>,
}

/// The one structured diagnostic shape for all compiler surfaces.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Diagnostic {
    pub contract_version: ContractVersion,
    pub occurrence: DiagnosticOccurrence,
    pub code: DiagnosticCode,
    pub severity: Severity,
    pub severity_basis: SeverityBasis,
    pub phase: CompilerPhase,
    pub category: DiagnosticCategory,
    pub message: String,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub primary_location: Option<SourceSpan>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub related_locations: Option<Vec<RelatedLocation>>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub advice: Option<Vec<Advice>>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub fixes: Option<Vec<Fix>>,
}

impl Diagnostic {
    #[must_use]
    pub fn is_error(&self) -> bool {
        self.severity == Severity::Error
    }
}

impl Validate for Diagnostic {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        nonempty(&self.message, "$.message", &mut errors);
        if let Some(location) = &self.primary_location {
            if let Err(found) = location.validate() {
                errors.extend(found);
            }
        }
        if let Some(related) = &self.related_locations {
            for (index, item) in related.iter().enumerate() {
                nonempty(
                    &item.message,
                    format!("$.related_locations[{index}].message"),
                    &mut errors,
                );
                if let Err(found) = item.location.validate() {
                    errors.extend(found);
                }
            }
        }
        if let Some(advice) = &self.advice {
            for (index, item) in advice.iter().enumerate() {
                nonempty(
                    &item.message,
                    format!("$.advice[{index}].message"),
                    &mut errors,
                );
            }
        }
        if let Some(fixes) = &self.fixes {
            for (fix_index, fix) in fixes.iter().enumerate() {
                nonempty(
                    &fix.title,
                    format!("$.fixes[{fix_index}].title"),
                    &mut errors,
                );
                if fix.edits.is_empty() {
                    errors.push(ValidationError::new(
                        ValidationCode::EmptyCollection,
                        format!("$.fixes[{fix_index}].edits"),
                        "fix must contain at least one edit",
                    ));
                }
                if fix.edits.windows(2).any(|pair| {
                    let left = &pair[0].span;
                    let right = &pair[1].span;
                    (left.source_id.clone(), left.start, left.end)
                        > (right.source_id.clone(), right.start, right.end)
                }) {
                    errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalOrder,
                        format!("$.fixes[{fix_index}].edits"),
                        "fix edits must be sorted by source/start/end",
                    ));
                }
                for (edit_index, edit) in fix.edits.iter().enumerate() {
                    if let Err(found) = edit.span.validate() {
                        errors.extend(found);
                    }
                    if edit_index > 0 {
                        let previous = &fix.edits[edit_index - 1].span;
                        if previous.source_id == edit.span.source_id
                            && edit.span.start < previous.end
                        {
                            errors.push(ValidationError::new(
                                ValidationCode::InvalidSpan,
                                format!("$.fixes[{fix_index}].edits[{edit_index}].span"),
                                "fix edits must not overlap",
                            ));
                        }
                    }
                }
            }
        }
        errors.finish()
    }
}

/// Compare diagnostics using only the canonical identity/order key, never prose.
#[must_use]
pub fn compare_diagnostics(left: &Diagnostic, right: &Diagnostic) -> Ordering {
    compare_locations(
        left.primary_location.as_ref(),
        right.primary_location.as_ref(),
    )
    .then_with(|| left.phase.rank().cmp(&right.phase.rank()))
    .then_with(|| left.severity.rank().cmp(&right.severity.rank()))
    .then_with(|| left.code.cmp(&right.code))
    .then_with(|| left.occurrence.cmp(&right.occurrence))
}

fn compare_locations(left: Option<&SourceSpan>, right: Option<&SourceSpan>) -> Ordering {
    match (left, right) {
        (Some(left), Some(right)) => {
            (&left.source_id, left.start, left.end).cmp(&(&right.source_id, right.start, right.end))
        }
        (Some(_), None) => Ordering::Less,
        (None, Some(_)) => Ordering::Greater,
        (None, None) => Ordering::Equal,
    }
}

/// Validate result-level occurrence uniqueness and deterministic ordering.
pub fn validate_diagnostic_order(diagnostics: &[Diagnostic]) -> Result<(), ValidationErrors> {
    let mut errors = ValidationErrors::default();
    let mut occurrences = BTreeSet::new();
    for (index, diagnostic) in diagnostics.iter().enumerate() {
        if !occurrences.insert(diagnostic.occurrence) {
            errors.push(ValidationError::new(
                ValidationCode::DuplicateIdentity,
                format!("$.diagnostics[{index}].occurrence"),
                "diagnostic occurrence must be unique within a result",
            ));
        }
    }
    if diagnostics
        .windows(2)
        .any(|pair| compare_diagnostics(&pair[0], &pair[1]) == Ordering::Greater)
    {
        errors.push(ValidationError::new(
            ValidationCode::NonCanonicalOrder,
            "$.diagnostics",
            "diagnostics must use canonical result order",
        ));
    }
    errors.finish()
}
