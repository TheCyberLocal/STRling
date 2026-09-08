//! Source identity, provenance, and UTF-8 byte-coordinate contracts.

use std::convert::TryFrom;
use std::error::Error;
use std::fmt;

use serde::{Deserialize, Deserializer, Serialize};

use crate::validation::{
    deserialize_optional_non_null, nonempty, Validate, ValidationCode, ValidationError,
    ValidationErrors,
};

/// The independently versioned canonical contract suite.
#[derive(Clone, Copy, Debug, Default, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub enum ContractVersion {
    #[serde(rename = "1.0.0")]
    #[default]
    V1_0_0,
}

/// A failed attempt to construct an opaque serialized identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IdentityError {
    kind: &'static str,
    value: String,
}

impl IdentityError {
    fn new(kind: &'static str, value: impl Into<String>) -> Self {
        Self {
            kind,
            value: value.into(),
        }
    }
}

impl fmt::Display for IdentityError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "invalid {}: {}", self.kind, self.value)
    }
}

impl Error for IdentityError {}

fn opaque_id(value: &str, prefix: &str) -> bool {
    let Some(suffix) = value.strip_prefix(prefix) else {
        return false;
    };
    let mut characters = suffix.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    suffix.len() <= 128
        && first.is_ascii_alphanumeric()
        && characters.all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '/' | '-')
        })
}

fn frontend_style_id(value: &str) -> bool {
    let mut characters = value.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    if !first.is_ascii_lowercase() {
        return false;
    }
    let mut previous_was_separator = false;
    for character in characters {
        if character.is_ascii_lowercase() || character.is_ascii_digit() {
            previous_was_separator = false;
        } else if matches!(character, '.' | '_' | '-') && !previous_was_separator {
            previous_was_separator = true;
        } else {
            return false;
        }
    }
    !previous_was_separator
}

fn dialect_version(value: &str) -> bool {
    let mut characters = value.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    value.len() <= 64
        && first.is_ascii_alphanumeric()
        && characters.all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-')
        })
}

fn canonical_number(value: &str, zero_allowed: bool) -> bool {
    if value == "0" {
        return zero_allowed;
    }
    value
        .strip_prefix(|character: char| matches!(character, '1'..='9'))
        .is_some_and(|remainder| {
            remainder
                .chars()
                .all(|character| character.is_ascii_digit())
        })
}

fn specification_version(value: &str) -> bool {
    let (main, draft) = match value.split_once("-draft.") {
        Some((main, draft)) => (main, Some(draft)),
        None => (value, None),
    };
    let mut parts = main.split('.');
    let valid_main = matches!(
        (parts.next(), parts.next(), parts.next()),
        (Some(major), Some(minor), None)
            if canonical_number(major, true) && canonical_number(minor, true)
    );
    valid_main
        && draft.map_or(true, |number| {
            canonical_number(number, false) && number != "0"
        })
}

macro_rules! opaque_string {
    ($name:ident, $kind:literal, $validator:expr) => {
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
            type Error = IdentityError;

            fn try_from(value: &str) -> Result<Self, Self::Error> {
                let validator: fn(&str) -> bool = $validator;
                if validator(value) {
                    Ok(Self(value.to_owned()))
                } else {
                    Err(IdentityError::new($kind, value))
                }
            }
        }

        impl TryFrom<String> for $name {
            type Error = IdentityError;

            fn try_from(value: String) -> Result<Self, Self::Error> {
                let validator: fn(&str) -> bool = $validator;
                if validator(&value) {
                    Ok(Self(value))
                } else {
                    Err(IdentityError::new($kind, value))
                }
            }
        }

        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
            where
                D: Deserializer<'de>,
            {
                let value = String::deserialize(deserializer)?;
                Self::try_from(value).map_err(serde::de::Error::custom)
            }
        }
    };
}

opaque_string!(SourceId, "source_id", |value: &str| opaque_id(
    value, "src:"
));
opaque_string!(NodeId, "node_id", |value: &str| opaque_id(value, "node:"));
opaque_string!(CaptureId, "capture_id", |value: &str| opaque_id(
    value, "capture:"
));
opaque_string!(FrontendId, "frontend id", frontend_style_id);
opaque_string!(ProducerId, "producer id", frontend_style_id);
opaque_string!(DialectVersion, "dialect version", dialect_version);
opaque_string!(
    SpecificationVersion,
    "specification version",
    specification_version
);
opaque_string!(Sha256Digest, "SHA-256 digest", |value: &str| {
    value.len() == 64
        && value
            .chars()
            .all(|character| character.is_ascii_digit() || matches!(character, 'a'..='f'))
});

impl Sha256Digest {
    /// Construct a lowercase contract digest from an already-computed SHA-256 value.
    #[must_use]
    pub fn from_bytes(bytes: [u8; 32]) -> Self {
        let mut value = String::with_capacity(64);
        for byte in bytes {
            use std::fmt::Write;
            let _ = write!(value, "{byte:02x}");
        }
        Self(value)
    }
}

/// Frontend identity does not expose the frontend's private syntax representation.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FrontendIdentity {
    pub id: FrontendId,
    pub dialect_version: DialectVersion,
}

/// UTF-8 is the only canonical serialized source encoding.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum Utf8Encoding {
    #[serde(rename = "utf-8")]
    Utf8,
}

/// Exact inline text or a digest-pinned external source reference.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum SourceContent {
    Inline {
        encoding: Utf8Encoding,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        media_type: Option<String>,
        text: String,
    },
    Reference {
        encoding: Utf8Encoding,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        media_type: Option<String>,
        uri: String,
        sha256: Sha256Digest,
    },
}

impl SourceContent {
    #[must_use]
    pub fn inline_text(&self) -> Option<&str> {
        match self {
            Self::Inline { text, .. } => Some(text),
            Self::Reference { .. } => None,
        }
    }

    fn validate_at(&self, path: &str, errors: &mut ValidationErrors) {
        match self {
            Self::Inline {
                media_type, text, ..
            } => {
                if let Some(media_type) = media_type {
                    nonempty(media_type, format!("{path}.media_type"), errors);
                }
                // Rust strings are valid Unicode and therefore encode deterministically as UTF-8.
                let _ = text;
            }
            Self::Reference {
                media_type, uri, ..
            } => {
                if let Some(media_type) = media_type {
                    nonempty(media_type, format!("{path}.media_type"), errors);
                }
                if !absolute_uri(uri) {
                    errors.push(ValidationError::new(
                        ValidationCode::InvalidUri,
                        format!("{path}.uri"),
                        "source reference must be an absolute URI",
                    ));
                }
            }
        }
    }
}

fn absolute_uri(value: &str) -> bool {
    let Some((scheme, remainder)) = value.split_once(':') else {
        return false;
    };
    let mut characters = scheme.chars();
    matches!(characters.next(), Some(first) if first.is_ascii_alphabetic())
        && characters.all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '+' | '-' | '.')
        })
        && !remainder.is_empty()
}

/// Compiler or tool that produced generated/projected source.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Producer {
    pub id: ProducerId,
    pub version: String,
}

/// A source relationship in provenance.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ParentSource {
    pub source_id: SourceId,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub span: Option<SourceSpan>,
}

/// Authorship class for a source document.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ProvenanceKind {
    Authored,
    Imported,
    Generated,
    Projected,
}

/// Authorship and derivation evidence independent of filesystem location.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Provenance {
    pub kind: ProvenanceKind,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub producer: Option<Producer>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub parent_sources: Option<Vec<ParentSource>>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub description: Option<String>,
}

impl Provenance {
    fn validate_at(&self, path: &str, errors: &mut ValidationErrors) {
        if self.kind == ProvenanceKind::Authored && self.parent_sources.is_some() {
            errors.push(ValidationError::new(
                ValidationCode::InvalidProvenance,
                format!("{path}.parent_sources"),
                "authored provenance must not declare parent sources",
            ));
        }
        if matches!(
            self.kind,
            ProvenanceKind::Generated | ProvenanceKind::Projected
        ) && self.producer.is_none()
        {
            errors.push(ValidationError::new(
                ValidationCode::InvalidProvenance,
                format!("{path}.producer"),
                "generated and projected provenance require a producer",
            ));
        }
        if let Some(producer) = &self.producer {
            nonempty(
                &producer.version,
                format!("{path}.producer.version"),
                errors,
            );
        }
        if let Some(parents) = &self.parent_sources {
            if parents.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    format!("{path}.parent_sources"),
                    "parent_sources must contain at least one entry",
                ));
            }
            for (index, parent) in parents.iter().enumerate() {
                if let Some(span) = &parent.span {
                    if span.source_id != parent.source_id {
                        errors.push(ValidationError::new(
                            ValidationCode::InvalidProvenance,
                            format!("{path}.parent_sources[{index}].span.source_id"),
                            "parent span must identify its parent source",
                        ));
                    }
                    if let Err(found) = span.validate() {
                        errors.extend(found);
                    }
                }
            }
        }
        if let Some(description) = &self.description {
            nonempty(description, format!("{path}.description"), errors);
        }
    }
}

/// Canonical source coordinates are zero-based, half-open UTF-8 byte offsets.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
pub enum CoordinateSystem {
    #[serde(rename = "utf8-bytes")]
    Utf8Bytes,
}

/// A source range tied to one opaque source identity.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SourceSpan {
    pub source_id: SourceId,
    pub coordinate_system: CoordinateSystem,
    pub start: u64,
    pub end: u64,
}

impl SourceSpan {
    pub fn new(source_id: SourceId, start: u64, end: u64) -> Result<Self, ValidationErrors> {
        let span = Self {
            source_id,
            coordinate_system: CoordinateSystem::Utf8Bytes,
            start,
            end,
        };
        span.validate()?;
        Ok(span)
    }

    pub fn validate_against_text(&self, text: &str) -> Result<(), ValidationErrors> {
        self.validate()?;
        let start = usize::try_from(self.start).ok();
        let end = usize::try_from(self.end).ok();
        if start.map_or(true, |offset| !text.is_char_boundary(offset))
            || end.map_or(true, |offset| !text.is_char_boundary(offset))
        {
            return Err(ValidationErrors::single(ValidationError::new(
                ValidationCode::Utf8Boundary,
                "$.span",
                "source span endpoints must be UTF-8 scalar boundaries within the source",
            )));
        }
        Ok(())
    }
}

impl Validate for SourceSpan {
    fn validate(&self) -> Result<(), ValidationErrors> {
        if self.start > self.end {
            Err(ValidationErrors::single(ValidationError::new(
                ValidationCode::InvalidSpan,
                "$.span",
                "source span start must not exceed end",
            )))
        } else {
            Ok(())
        }
    }
}

/// Optional attribution for a semantic node.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SourceOrigin {
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub source_spans: Option<Vec<SourceSpan>>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub derived_from_node_ids: Option<Vec<NodeId>>,
}

impl Validate for SourceOrigin {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if self.source_spans.is_none() && self.derived_from_node_ids.is_none() {
            errors.push(ValidationError::new(
                ValidationCode::EmptyCollection,
                "$.origin",
                "origin requires source_spans, derived_from_node_ids, or both",
            ));
        }
        if let Some(spans) = &self.source_spans {
            if spans.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    "$.origin.source_spans",
                    "source_spans must not be empty",
                ));
            }
            if !strictly_sorted(spans) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    "$.origin.source_spans",
                    "source spans must be unique and sorted by source/start/end",
                ));
            }
            for (index, pair) in spans.windows(2).enumerate() {
                if pair[0].source_id == pair[1].source_id && pair[0].end > pair[1].start {
                    errors.push(ValidationError::new(
                        ValidationCode::InvalidSpan,
                        format!("$.origin.source_spans[{}]", index + 1),
                        "source spans for one origin must not overlap",
                    ));
                }
            }
            for span in spans {
                if let Err(found) = span.validate() {
                    errors.extend(found);
                }
            }
        }
        if let Some(node_ids) = &self.derived_from_node_ids {
            if node_ids.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    "$.origin.derived_from_node_ids",
                    "derived_from_node_ids must not be empty",
                ));
            }
            if !strictly_sorted(node_ids) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    "$.origin.derived_from_node_ids",
                    "derived node identities must be unique and sorted",
                ));
            }
        }
        errors.finish()
    }
}

fn strictly_sorted<T: Ord>(items: &[T]) -> bool {
    items.windows(2).all(|window| window[0] < window[1])
}

/// Source identity, frontend dialect, exact content, and provenance.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SourceDocument {
    pub contract_version: ContractVersion,
    pub source_id: SourceId,
    pub specification_version: SpecificationVersion,
    pub frontend: FrontendIdentity,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub display_name: Option<String>,
    pub content: SourceContent,
    pub provenance: Provenance,
}

impl Validate for SourceDocument {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if let Some(display_name) = &self.display_name {
            nonempty(display_name, "$.display_name", &mut errors);
        }
        self.content.validate_at("$.content", &mut errors);
        self.provenance.validate_at("$.provenance", &mut errors);
        errors.finish()
    }
}
