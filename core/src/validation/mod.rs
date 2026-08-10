//! Structured cross-contract validation support.

use std::error::Error;
use std::fmt;

use serde::de::DeserializeOwned;
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

/// Stable categories for structural contract validation failures.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ValidationCode {
    DuplicateIdentity,
    EmptyCollection,
    EmptyValue,
    InvalidBounds,
    InvalidDigest,
    InvalidIdentity,
    InvalidProvenance,
    InvalidSpan,
    InvalidUri,
    InvalidVersion,
    NonCanonicalOrder,
    NonCanonicalStructure,
    SpecificationMismatch,
    UnresolvedReference,
    Utf8Boundary,
}

/// One machine-classifiable validation failure with a stable data path.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ValidationError {
    pub code: ValidationCode,
    pub path: String,
    pub message: String,
}

impl ValidationError {
    #[must_use]
    pub fn new(code: ValidationCode, path: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code,
            path: path.into(),
            message: message.into(),
        }
    }
}

/// Ordered validation failures returned for externally supplied contract data.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ValidationErrors {
    pub errors: Vec<ValidationError>,
}

impl ValidationErrors {
    #[must_use]
    pub fn single(error: ValidationError) -> Self {
        Self {
            errors: vec![error],
        }
    }

    pub(crate) fn push(&mut self, error: ValidationError) {
        self.errors.push(error);
    }

    pub(crate) fn extend(&mut self, other: Self) {
        self.errors.extend(other.errors);
    }

    pub(crate) fn finish(self) -> Result<(), Self> {
        if self.errors.is_empty() {
            Ok(())
        } else {
            Err(self)
        }
    }
}

impl fmt::Display for ValidationErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} contract validation error(s)",
            self.errors.len()
        )
    }
}

impl Error for ValidationErrors {}

/// Structural validation implemented by every externally supplied contract root.
pub trait Validate {
    /// Validate invariants that Rust and Serde cannot express by construction.
    fn validate(&self) -> Result<(), ValidationErrors>;
}

/// Deserialization and validation failures remain distinguishable without prose parsing.
#[derive(Debug)]
pub enum ContractError {
    Deserialization(serde_json::Error),
    Validation(ValidationErrors),
}

impl fmt::Display for ContractError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Deserialization(error) => {
                write!(formatter, "contract deserialization failed: {error}")
            }
            Self::Validation(errors) => errors.fmt(formatter),
        }
    }
}

impl Error for ContractError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Deserialization(error) => Some(error),
            Self::Validation(errors) => Some(errors),
        }
    }
}

/// Deserialize closed JSON data and apply its domain invariants.
pub fn from_json<T>(input: &str) -> Result<T, ContractError>
where
    T: DeserializeOwned + Validate,
{
    let value: T = serde_json::from_str(input).map_err(ContractError::Deserialization)?;
    value.validate().map_err(ContractError::Validation)?;
    Ok(value)
}

/// Serialize a contract value using deterministic struct and ordered-map traversal.
pub fn to_json<T>(value: &T) -> Result<String, serde_json::Error>
where
    T: Serialize,
{
    serde_json::to_string(value)
}

/// SHA-256 of compact JSON with recursively sorted object keys and UTF-8 text.
pub fn canonical_sha256<T>(value: &T) -> Result<[u8; 32], serde_json::Error>
where
    T: Serialize,
{
    let mut value = serde_json::to_value(value)?;
    canonicalize(&mut value);
    Ok(Sha256::digest(serde_json::to_vec(&value)?).into())
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

/// Optional schema fields reject explicit JSON null while accepting omission.
pub(crate) fn deserialize_optional_non_null<'de, D, T>(
    deserializer: D,
) -> Result<Option<T>, D::Error>
where
    D: Deserializer<'de>,
    T: Deserialize<'de>,
{
    T::deserialize(deserializer).map(Some)
}

pub(crate) fn nonempty(value: &str, path: impl Into<String>, errors: &mut ValidationErrors) {
    if value.is_empty() {
        errors.push(ValidationError::new(
            ValidationCode::EmptyValue,
            path,
            "value must not be empty",
        ));
    }
}
