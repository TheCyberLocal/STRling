use std::convert::TryFrom;
use std::fmt;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::source::{ContractVersion, NodeId, SpecificationVersion};
use crate::target::RequirementId;
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

/// Stable target-neutral feature identity.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(transparent)]
pub struct FeatureId(String);

impl FeatureId {
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl TryFrom<&str> for FeatureId {
    type Error = String;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        if scoped_lower_identifier(value) {
            Ok(Self(value.to_owned()))
        } else {
            Err(format!("invalid feature identity: {value}"))
        }
    }
}

impl<'de> Deserialize<'de> for FeatureId {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Self::try_from(value.as_str()).map_err(serde::de::Error::custom)
    }
}

/// Required finite or unbounded derived length maximum.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LengthMaximum {
    Bounded(u64),
    Unbounded,
}

impl Serialize for LengthMaximum {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        match self {
            Self::Bounded(maximum) => serializer.serialize_u64(*maximum),
            Self::Unbounded => serializer.serialize_none(),
        }
    }
}

struct LengthMaximumVisitor;

impl<'de> serde::de::Visitor<'de> for LengthMaximumVisitor {
    type Value = LengthMaximum;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a nonnegative integer or null")
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(LengthMaximum::Bounded(value))
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(LengthMaximum::Unbounded)
    }
}

impl<'de> Deserialize<'de> for LengthMaximum {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(LengthMaximumVisitor)
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum LengthUnit {
    #[serde(rename = "unicode-scalar-values")]
    UnicodeScalarValues,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct LengthBounds {
    pub min: u64,
    pub max: LengthMaximum,
    pub unit: LengthUnit,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NodeFacts {
    pub node_id: NodeId,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub nullable: Option<bool>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub length_bounds: Option<LengthBounds>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct FeatureRequirement {
    pub requirement_id: RequirementId,
    pub feature_id: FeatureId,
    pub node_ids: Vec<NodeId>,
}

/// Derived facts remain keyed by node identity, outside Semantic IR.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct AnalysisResult {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub node_facts: Vec<NodeFacts>,
    pub feature_requirements: Vec<FeatureRequirement>,
}

impl Validate for AnalysisResult {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if self
            .node_facts
            .windows(2)
            .any(|pair| pair[0].node_id >= pair[1].node_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.node_facts",
                "node facts require unique sorted node identities",
            ));
        }
        for (index, facts) in self.node_facts.iter().enumerate() {
            if facts.nullable.is_none() && facts.length_bounds.is_none() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyValue,
                    format!("$.node_facts[{index}]"),
                    "node facts require nullability, length bounds, or both",
                ));
            }
            if let Some(bounds) = &facts.length_bounds {
                if matches!(bounds.max, LengthMaximum::Bounded(maximum) if maximum < bounds.min) {
                    errors.push(ValidationError::new(
                        ValidationCode::InvalidBounds,
                        format!("$.node_facts[{index}].length_bounds.max"),
                        "finite length maximum must not be less than minimum",
                    ));
                }
            }
        }
        if self
            .feature_requirements
            .windows(2)
            .any(|pair| pair[0].requirement_id >= pair[1].requirement_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.feature_requirements",
                "feature requirements require unique sorted identities",
            ));
        }
        for (index, requirement) in self.feature_requirements.iter().enumerate() {
            if requirement.node_ids.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    format!("$.feature_requirements[{index}].node_ids"),
                    "feature requirement needs at least one node identity",
                ));
            }
            if requirement
                .node_ids
                .windows(2)
                .any(|pair| pair[0] >= pair[1])
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.feature_requirements[{index}].node_ids"),
                    "feature requirement node identities must be unique and sorted",
                ));
            }
        }
        errors.finish()
    }
}
