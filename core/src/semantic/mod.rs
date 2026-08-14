//! Target-neutral canonical Semantic IR contracts.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

use crate::source::{
    CaptureId, ContractVersion, NodeId, SourceDocument, SourceId, SourceOrigin,
    SpecificationVersion,
};
use crate::validation::{
    deserialize_optional_non_null, nonempty, Validate, ValidationCode, ValidationError,
    ValidationErrors,
};

/// The normalization contract certified by a Semantic IR program.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum Normalization {
    #[serde(rename = "canonical-v1")]
    CanonicalV1,
}

/// Target-neutral global case-matching intent.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CaseMatching {
    Sensitive,
    Insensitive,
}

/// One Unicode scalar, never a UTF-16 surrogate or multi-scalar string.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct UnicodeScalar(char);

impl UnicodeScalar {
    pub(crate) const fn from_char(value: char) -> Self {
        Self(value)
    }

    #[must_use]
    pub fn get(self) -> char {
        self.0
    }
}

impl fmt::Display for UnicodeScalar {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(formatter)
    }
}

impl Serialize for UnicodeScalar {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.collect_str(self)
    }
}

impl<'de> Deserialize<'de> for UnicodeScalar {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        let mut characters = value.chars();
        match (characters.next(), characters.next()) {
            (Some(character), None) => Ok(Self(character)),
            _ => Err(serde::de::Error::custom(
                "Unicode scalar must contain exactly one scalar value",
            )),
        }
    }
}

/// Wildcard treatment of line terminators.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LineTerminators {
    Exclude,
    Include,
}

/// Built-in character class semantics.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum BuiltinClassName {
    Digit,
    Word,
    Whitespace,
}

impl BuiltinClassName {
    fn as_str(self) -> &'static str {
        match self {
            Self::Digit => "digit",
            Self::Word => "word",
            Self::Whitespace => "whitespace",
        }
    }
}

/// Interpretation policy for a built-in class.
///
/// `TargetNative` preserves the selected engine's shorthand-class meaning.
/// It exists for governed compatibility semantics whose accepted character
/// set is intentionally profile-dependent.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CharacterDomain {
    Ascii,
    TargetNative,
    Unicode,
}

impl CharacterDomain {
    fn as_str(self) -> &'static str {
        match self {
            Self::Ascii => "ascii",
            Self::TargetNative => "target_native",
            Self::Unicode => "unicode",
        }
    }
}

/// Canonically ordered semantic members of a character set.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum CharacterSetMember {
    Literal {
        value: UnicodeScalar,
    },
    Range {
        start: UnicodeScalar,
        end: UnicodeScalar,
    },
    Builtin {
        name: BuiltinClassName,
        domain: CharacterDomain,
        negated: bool,
    },
    UnicodeProperty {
        property: String,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        value: Option<String>,
        negated: bool,
    },
}

impl CharacterSetMember {
    fn canonical_key(&self) -> (u8, String, String, bool) {
        match self {
            Self::Literal { value } => (0, value.to_string(), String::new(), false),
            Self::Range { start, end } => (1, start.to_string(), end.to_string(), false),
            Self::Builtin {
                name,
                domain,
                negated,
            } => (
                2,
                name.as_str().to_owned(),
                domain.as_str().to_owned(),
                *negated,
            ),
            Self::UnicodeProperty {
                property,
                value,
                negated,
            } => (
                3,
                property.clone(),
                value.clone().unwrap_or_default(),
                *negated,
            ),
        }
    }

    fn validate_at(&self, path: &str, errors: &mut ValidationErrors) {
        match self {
            Self::Range { start, end } if start > end => {
                errors.push(ValidationError::new(
                    ValidationCode::InvalidBounds,
                    path,
                    "character-set range start must not exceed end",
                ));
            }
            Self::UnicodeProperty {
                property, value, ..
            } => {
                nonempty(property, format!("{path}.property"), errors);
                if let Some(value) = value {
                    nonempty(value, format!("{path}.value"), errors);
                }
            }
            _ => {}
        }
    }
}

/// Finite or unbounded repetition maximum. JSON null alone means unbounded.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RepetitionMaximum {
    Bounded(u64),
    Unbounded,
}

impl Serialize for RepetitionMaximum {
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

struct RepetitionMaximumVisitor;

impl<'de> serde::de::Visitor<'de> for RepetitionMaximumVisitor {
    type Value = RepetitionMaximum;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a nonnegative integer or null")
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(RepetitionMaximum::Bounded(value))
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(RepetitionMaximum::Unbounded)
    }

    fn visit_none<E>(self) -> Result<Self::Value, E>
    where
        E: serde::de::Error,
    {
        Ok(RepetitionMaximum::Unbounded)
    }
}

impl<'de> Deserialize<'de> for RepetitionMaximum {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(RepetitionMaximumVisitor)
    }
}

/// Backtracking behavior for repetition.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RepetitionMode {
    Greedy,
    Lazy,
    Possessive,
}

/// Canonical semantic positions and boundaries.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum PositionKind {
    InputStart,
    InputEnd,
    LineStart,
    LineEnd,
    WordBoundary,
    NotWordBoundary,
    EndBeforeFinalLineTerminator,
}

/// Direction of a semantic lookaround assertion.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LookaroundDirection {
    Ahead,
    Behind,
}

/// Polarity of a semantic lookaround assertion.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AssertionPolarity {
    Positive,
    Negative,
}

/// Every currently ratified, target-neutral Semantic IR node.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Node {
    Empty {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
    },
    Sequence {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        items: Vec<Node>,
    },
    Alternation {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        branches: Vec<Node>,
    },
    Literal {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        text: String,
    },
    Wildcard {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        line_terminators: LineTerminators,
    },
    CharacterSet {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        negated: bool,
        members: Vec<CharacterSetMember>,
    },
    Repeat {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        body: Box<Node>,
        min: u64,
        max: RepetitionMaximum,
        mode: RepetitionMode,
    },
    Position {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        position: PositionKind,
    },
    Capture {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        capture_id: CaptureId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        name: Option<String>,
        body: Box<Node>,
    },
    Backreference {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        capture_id: CaptureId,
    },
    Lookaround {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        direction: LookaroundDirection,
        polarity: AssertionPolarity,
        body: Box<Node>,
    },
    Atomic {
        node_id: NodeId,
        #[serde(
            default,
            deserialize_with = "deserialize_optional_non_null",
            skip_serializing_if = "Option::is_none"
        )]
        origin: Option<SourceOrigin>,
        body: Box<Node>,
    },
}

impl Node {
    #[must_use]
    pub fn node_id(&self) -> &NodeId {
        match self {
            Self::Empty { node_id, .. }
            | Self::Sequence { node_id, .. }
            | Self::Alternation { node_id, .. }
            | Self::Literal { node_id, .. }
            | Self::Wildcard { node_id, .. }
            | Self::CharacterSet { node_id, .. }
            | Self::Repeat { node_id, .. }
            | Self::Position { node_id, .. }
            | Self::Capture { node_id, .. }
            | Self::Backreference { node_id, .. }
            | Self::Lookaround { node_id, .. }
            | Self::Atomic { node_id, .. } => node_id,
        }
    }

    #[must_use]
    pub fn origin(&self) -> Option<&SourceOrigin> {
        match self {
            Self::Empty { origin, .. }
            | Self::Sequence { origin, .. }
            | Self::Alternation { origin, .. }
            | Self::Literal { origin, .. }
            | Self::Wildcard { origin, .. }
            | Self::CharacterSet { origin, .. }
            | Self::Repeat { origin, .. }
            | Self::Position { origin, .. }
            | Self::Capture { origin, .. }
            | Self::Backreference { origin, .. }
            | Self::Lookaround { origin, .. }
            | Self::Atomic { origin, .. } => origin.as_ref(),
        }
    }

    fn validate_at(&self, path: &str, context: &mut SemanticContext<'_>) {
        if !context.node_ids.insert(self.node_id().clone()) {
            context.errors.push(ValidationError::new(
                ValidationCode::DuplicateIdentity,
                format!("{path}.node_id"),
                "node identity must be unique in one Semantic IR program",
            ));
        }
        if let Some(origin) = self.origin() {
            if let Err(errors) = origin.validate() {
                context.errors.extend(errors);
            }
            if let Some(spans) = &origin.source_spans {
                for (index, span) in spans.iter().enumerate() {
                    match context.sources.get(&span.source_id) {
                        Some(source) => {
                            if let Some(text) = source.content.inline_text() {
                                if let Err(errors) = span.validate_against_text(text) {
                                    context.errors.extend(errors);
                                }
                            }
                        }
                        None => context.errors.push(ValidationError::new(
                            ValidationCode::UnresolvedReference,
                            format!("{path}.origin.source_spans[{index}].source_id"),
                            "origin span must reference an embedded source",
                        )),
                    }
                }
            }
        }

        match self {
            Self::Empty { .. } | Self::Wildcard { .. } | Self::Position { .. } => {}
            Self::Sequence { items, .. } => {
                if items.len() < 2 {
                    context.errors.push(ValidationError::new(
                        ValidationCode::EmptyCollection,
                        format!("{path}.items"),
                        "canonical sequence requires at least two children",
                    ));
                }
                if items
                    .iter()
                    .any(|item| matches!(item, Self::Sequence { .. }))
                {
                    context.errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        format!("{path}.items"),
                        "canonical sequence cannot contain a sequence",
                    ));
                }
                if items.windows(2).any(|pair| {
                    matches!(
                        (&pair[0], &pair[1]),
                        (Self::Literal { .. }, Self::Literal { .. })
                    )
                }) {
                    context.errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        format!("{path}.items"),
                        "adjacent canonical literals must be coalesced",
                    ));
                }
                for (index, child) in items.iter().enumerate() {
                    child.validate_at(&format!("{path}.items[{index}]"), context);
                }
            }
            Self::Alternation { branches, .. } => {
                if branches.len() < 2 {
                    context.errors.push(ValidationError::new(
                        ValidationCode::EmptyCollection,
                        format!("{path}.branches"),
                        "canonical alternation requires at least two branches",
                    ));
                }
                if branches
                    .iter()
                    .any(|branch| matches!(branch, Self::Alternation { .. }))
                {
                    context.errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        format!("{path}.branches"),
                        "canonical alternation cannot contain an alternation",
                    ));
                }
                for (index, child) in branches.iter().enumerate() {
                    child.validate_at(&format!("{path}.branches[{index}]"), context);
                }
            }
            Self::Literal { text, .. } => {
                nonempty(text, format!("{path}.text"), &mut context.errors);
            }
            Self::CharacterSet { members, .. } => {
                if members.is_empty() {
                    context.errors.push(ValidationError::new(
                        ValidationCode::EmptyCollection,
                        format!("{path}.members"),
                        "character set requires at least one member",
                    ));
                }
                if members
                    .windows(2)
                    .any(|pair| pair[0].canonical_key() >= pair[1].canonical_key())
                {
                    context.errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalOrder,
                        format!("{path}.members"),
                        "character-set members must be unique and canonically sorted",
                    ));
                }
                for (index, member) in members.iter().enumerate() {
                    member.validate_at(&format!("{path}.members[{index}]"), &mut context.errors);
                }
            }
            Self::Repeat { body, min, max, .. } => {
                if matches!(max, RepetitionMaximum::Bounded(maximum) if maximum < min) {
                    context.errors.push(ValidationError::new(
                        ValidationCode::InvalidBounds,
                        format!("{path}.max"),
                        "finite repetition maximum must not be less than minimum",
                    ));
                }
                body.validate_at(&format!("{path}.body"), context);
            }
            Self::Capture {
                capture_id,
                name,
                body,
                ..
            } => {
                if !context.capture_ids.insert(capture_id.clone()) {
                    context.errors.push(ValidationError::new(
                        ValidationCode::DuplicateIdentity,
                        format!("{path}.capture_id"),
                        "logical capture identity must be unique",
                    ));
                }
                if let Some(name) = name {
                    nonempty(name, format!("{path}.name"), &mut context.errors);
                    if !context.capture_names.insert(name.clone()) {
                        context.errors.push(ValidationError::new(
                            ValidationCode::DuplicateIdentity,
                            format!("{path}.name"),
                            "capture name must be unique",
                        ));
                    }
                }
                body.validate_at(&format!("{path}.body"), context);
            }
            Self::Backreference { capture_id, .. } => {
                context
                    .references
                    .push((path.to_owned(), capture_id.clone()));
            }
            Self::Lookaround { body, .. } | Self::Atomic { body, .. } => {
                body.validate_at(&format!("{path}.body"), context);
            }
        }
    }
}

struct SemanticContext<'a> {
    sources: BTreeMap<&'a SourceId, &'a SourceDocument>,
    node_ids: BTreeSet<NodeId>,
    capture_ids: BTreeSet<CaptureId>,
    capture_names: BTreeSet<String>,
    references: Vec<(String, CaptureId)>,
    errors: ValidationErrors,
}

impl<'a> SemanticContext<'a> {
    fn new(sources: BTreeMap<&'a SourceId, &'a SourceDocument>) -> Self {
        Self {
            sources,
            node_ids: BTreeSet::new(),
            capture_ids: BTreeSet::new(),
            capture_names: BTreeSet::new(),
            references: Vec::new(),
            errors: ValidationErrors::default(),
        }
    }
}

/// The sole canonical, normalized, target-neutral representation of regex intent.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticProgram {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub normalization: Normalization,
    pub case_matching: CaseMatching,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub sources: Option<Vec<SourceDocument>>,
    pub root: Node,
}

impl SemanticProgram {
    /// Stable semantic identities available for keyed cross-phase results.
    #[must_use]
    pub fn node_ids(&self) -> BTreeSet<NodeId> {
        fn visit(node: &Node, ids: &mut BTreeSet<NodeId>) {
            ids.insert(node.node_id().clone());
            match node {
                Node::Sequence { items, .. } => {
                    for child in items {
                        visit(child, ids);
                    }
                }
                Node::Alternation { branches, .. } => {
                    for child in branches {
                        visit(child, ids);
                    }
                }
                Node::Repeat { body, .. }
                | Node::Capture { body, .. }
                | Node::Lookaround { body, .. }
                | Node::Atomic { body, .. } => visit(body, ids),
                Node::Empty { .. }
                | Node::Literal { .. }
                | Node::Wildcard { .. }
                | Node::CharacterSet { .. }
                | Node::Position { .. }
                | Node::Backreference { .. } => {}
            }
        }
        let mut ids = BTreeSet::new();
        visit(&self.root, &mut ids);
        ids
    }
}

impl Validate for SemanticProgram {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut source_map = BTreeMap::new();
        let mut preflight = ValidationErrors::default();
        if let Some(sources) = &self.sources {
            if sources.is_empty() {
                preflight.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    "$.sources",
                    "embedded sources must not be empty",
                ));
            }
            for (index, source) in sources.iter().enumerate() {
                if let Err(errors) = source.validate() {
                    preflight.extend(errors);
                }
                if source.specification_version != self.specification_version {
                    preflight.push(ValidationError::new(
                        ValidationCode::SpecificationMismatch,
                        format!("$.sources[{index}].specification_version"),
                        "embedded source must use the program specification version",
                    ));
                }
                if source_map.insert(&source.source_id, source).is_some() {
                    preflight.push(ValidationError::new(
                        ValidationCode::DuplicateIdentity,
                        format!("$.sources[{index}].source_id"),
                        "embedded source identity must be unique",
                    ));
                }
            }
        }

        let mut context = SemanticContext::new(source_map);
        context.errors.extend(preflight);
        self.root.validate_at("$.root", &mut context);
        for (path, capture_id) in &context.references {
            if !context.capture_ids.contains(capture_id) {
                context.errors.push(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    format!("{path}.capture_id"),
                    "backreference must resolve to a logical capture identity",
                ));
            }
        }
        context.errors.finish()
    }
}
