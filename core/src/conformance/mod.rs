//! Specification-authored conformance case and authority-manifest contracts.

use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};
use std::convert::TryFrom;

use serde::{Deserialize, Deserializer, Serialize};

use crate::diagnostic::{CompilerPhase, DiagnosticCategory, DiagnosticCode, Severity};
use crate::protocol::CompileInput;
use crate::semantic::{Node, SemanticProgram};
use crate::source::{
    CaptureId, ContractVersion, CoordinateSystem, Sha256Digest, SourceDocument, SourceId,
    SourceSpan, SpecificationVersion,
};
use crate::target::{PortabilityStatus, ReasonCode, TargetProfileReference, TargetProfileSet};
use crate::validation::{
    canonical_sha256, deserialize_optional_non_null, nonempty, Validate, ValidationCode,
    ValidationError, ValidationErrors,
};

fn scoped_identifier(value: &str) -> bool {
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

fn path_identifier(value: &str, prefix: &str) -> bool {
    let Some(value) = value.strip_prefix(prefix) else {
        return false;
    };
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
        } else if matches!(character, '.' | '_' | '/' | '-') && !separator {
            separator = true;
        } else {
            return false;
        }
    }
    !separator
}

fn spec_path(value: &str) -> bool {
    value.strip_prefix("spec/").is_some_and(|remainder| {
        !remainder.is_empty()
            && remainder.chars().all(|character| {
                character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '/' | '-')
            })
    })
}

fn case_path(value: &str) -> bool {
    value
        .strip_prefix("spec/conformance/cases/")
        .is_some_and(|remainder| {
            remainder.ends_with(".json")
                && remainder.chars().all(|character| {
                    character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '/' | '-')
                })
        })
}

macro_rules! string_type {
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

string_type!(
    CaseId,
    |value: &str| path_identifier(value, "case:"),
    "conformance case identity"
);
string_type!(
    ManifestId,
    |value: &str| path_identifier(value, "manifest:"),
    "conformance manifest identity"
);
string_type!(
    ConformanceIdentifier,
    scoped_identifier,
    "conformance identity"
);
string_type!(IntentSource, spec_path, "specification intent path");
string_type!(CasePath, case_path, "conformance case path");
string_type!(
    NormativeSource,
    |value: &str| value.starts_with("spec/versions/") && spec_path(value),
    "ratified specification path"
);

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum AuthorshipKind {
    #[serde(rename = "specification_authored")]
    SpecificationAuthored,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Authorship {
    pub kind: AuthorshipKind,
    pub intent_source: IntentSource,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticNodeKind {
    Empty,
    Sequence,
    Alternation,
    Literal,
    Wildcard,
    CharacterSet,
    Repeat,
    Position,
    Capture,
    Backreference,
    Lookaround,
    Atomic,
}

impl SemanticNodeKind {
    fn of(node: &Node) -> Self {
        match node {
            Node::Empty { .. } => Self::Empty,
            Node::Sequence { .. } => Self::Sequence,
            Node::Alternation { .. } => Self::Alternation,
            Node::Literal { .. } => Self::Literal,
            Node::Wildcard { .. } => Self::Wildcard,
            Node::CharacterSet { .. } => Self::CharacterSet,
            Node::Repeat { .. } => Self::Repeat,
            Node::Position { .. } => Self::Position,
            Node::Capture { .. } => Self::Capture,
            Node::Backreference { .. } => Self::Backreference,
            Node::Lookaround { .. } => Self::Lookaround,
            Node::Atomic { .. } => Self::Atomic,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticFacts {
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub root_kind: Option<SemanticNodeKind>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub node_count: Option<u64>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub capture_ids: Option<Vec<CaptureId>>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticExpectation {
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub exact_program: Option<SemanticProgram>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub facts: Option<SemanticFacts>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DiagnosticExpectation {
    pub code: DiagnosticCode,
    pub phase: CompilerPhase,
    pub category: DiagnosticCategory,
    pub severity: Severity,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub primary_location: Option<SourceSpan>,
    pub count: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DiagnosticExpectations {
    pub items: Vec<DiagnosticExpectation>,
    pub allow_additional: bool,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum MatchOperation {
    FullMatch,
    Search,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SubjectSpan {
    pub coordinate_system: CoordinateSystem,
    pub start: u64,
    pub end: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CaptureExpectation {
    pub capture_id: CaptureId,
    pub matched: bool,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub text: Option<String>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub subject_span: Option<SubjectSpan>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct PositiveMatch {
    pub match_id: ConformanceIdentifier,
    pub subject: String,
    pub captures: Vec<CaptureExpectation>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NegativeMatch {
    pub match_id: ConformanceIdentifier,
    pub subject: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct MatchExpectations {
    pub operation: MatchOperation,
    pub positive: Vec<PositiveMatch>,
    pub negative: Vec<NegativeMatch>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct TargetExpectation {
    pub target_profile: TargetProfileReference,
    pub status: PortabilityStatus,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub reason_codes: Option<Vec<ReasonCode>>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum CompatibilityEvidenceKind {
    LegacyFixture,
    ImplementationTest,
    HistoricalOutput,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CompatibilityEvidence {
    pub kind: CompatibilityEvidenceKind,
    pub reference: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Expectations {
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub semantic: Option<SemanticExpectation>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub diagnostics: Option<DiagnosticExpectations>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub matches: Option<MatchExpectations>,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub targets: Option<Vec<TargetExpectation>>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConformanceCase {
    pub contract_version: ContractVersion,
    pub case_id: CaseId,
    pub specification_version: SpecificationVersion,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub title: Option<String>,
    pub authorship: Authorship,
    pub input: CompileInput,
    pub expectations: Expectations,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub compatibility_evidence: Vec<CompatibilityEvidence>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<ConformanceIdentifier>,
}

impl Validate for ConformanceCase {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if let Err(found) = self.input.validate() {
            errors.extend(found);
        }
        if self.input.specification_version() != &self.specification_version {
            errors.push(ValidationError::new(
                ValidationCode::SpecificationMismatch,
                "$.input",
                "conformance input and case specification versions must match",
            ));
        }
        if let Some(title) = &self.title {
            nonempty(title, "$.title", &mut errors);
        }
        let program = match &self.input {
            CompileInput::Semantic { program } => Some(program.as_ref()),
            CompileInput::Source { .. } => None,
        };
        let sources = input_sources(&self.input);
        self.expectations
            .validate_at(program, &sources, &self.specification_version, &mut errors);

        if self.compatibility_evidence.windows(2).any(|pair| {
            (pair[0].kind, pair[0].reference.as_str()) >= (pair[1].kind, pair[1].reference.as_str())
        }) {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.compatibility_evidence",
                "compatibility evidence must have unique sorted kind/reference keys",
            ));
        }
        for (index, evidence) in self.compatibility_evidence.iter().enumerate() {
            nonempty(
                &evidence.reference,
                format!("$.compatibility_evidence[{index}].reference"),
                &mut errors,
            );
        }
        if self.tags.windows(2).any(|pair| pair[0] >= pair[1]) {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.tags",
                "conformance tags must be unique and sorted",
            ));
        }
        errors.finish()
    }
}

impl ConformanceCase {
    /// Resolve every target expectation against an explicitly supplied profile set.
    pub fn validate_against_profiles(
        &self,
        profiles: &TargetProfileSet,
    ) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if let Err(found) = self.validate() {
            errors.extend(found);
        }
        if let Some(targets) = &self.expectations.targets {
            for (index, target) in targets.iter().enumerate() {
                match profiles.resolve(&target.target_profile) {
                    Ok(profile)
                        if !profile
                            .compatible_specification_versions
                            .contains(&self.specification_version) =>
                    {
                        errors.push(ValidationError::new(
                            ValidationCode::SpecificationMismatch,
                            format!("$.expectations.targets[{index}].target_profile"),
                            "target profile is not compatible with the case specification",
                        ));
                    }
                    Err(found) => errors.extend(found),
                    Ok(_) => {}
                }
            }
        }
        errors.finish()
    }

    pub fn fingerprint(&self) -> Result<Sha256Digest, ValidationErrors> {
        canonical_sha256(self)
            .map(Sha256Digest::from_bytes)
            .map_err(|error| {
                ValidationErrors::single(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    "$",
                    format!("conformance case canonical JSON failed: {error}"),
                ))
            })
    }
}

impl Expectations {
    fn validate_at(
        &self,
        input_program: Option<&SemanticProgram>,
        sources: &BTreeMap<&SourceId, &SourceDocument>,
        specification_version: &SpecificationVersion,
        errors: &mut ValidationErrors,
    ) {
        if self.semantic.is_none()
            && self.diagnostics.is_none()
            && self.matches.is_none()
            && self.targets.is_none()
        {
            errors.push(ValidationError::new(
                ValidationCode::EmptyValue,
                "$.expectations",
                "a conformance case must declare at least one expectation layer",
            ));
        }

        let mut expectation_program = input_program;
        if let Some(semantic) = &self.semantic {
            if semantic.exact_program.is_none() && semantic.facts.is_none() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyValue,
                    "$.expectations.semantic",
                    "semantic expectations require exact_program or facts",
                ));
            }
            if let Some(exact) = &semantic.exact_program {
                if let Err(found) = exact.validate() {
                    errors.extend(found);
                }
                if &exact.specification_version != specification_version {
                    errors.push(ValidationError::new(
                        ValidationCode::SpecificationMismatch,
                        "$.expectations.semantic.exact_program.specification_version",
                        "exact semantic expectation must use the case specification",
                    ));
                }
                if input_program.is_some_and(|input| input != exact) {
                    errors.push(ValidationError::new(
                        ValidationCode::NonCanonicalStructure,
                        "$.expectations.semantic.exact_program",
                        "canonical semantic input must equal its exact expectation",
                    ));
                }
                expectation_program = Some(exact);
            }
            if let Some(facts) = &semantic.facts {
                facts.validate_at(expectation_program, errors);
            }
        }

        let mut expected_error = false;
        if let Some(diagnostics) = &self.diagnostics {
            if diagnostics.items.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    "$.expectations.diagnostics.items",
                    "diagnostic expectations require at least one item",
                ));
            }
            if diagnostics
                .items
                .windows(2)
                .any(|pair| diagnostic_expectation_cmp(&pair[0], &pair[1]) != Ordering::Less)
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    "$.expectations.diagnostics.items",
                    "diagnostic expectations must have unique canonical keys",
                ));
            }
            for (index, diagnostic) in diagnostics.items.iter().enumerate() {
                if diagnostic.count == 0 {
                    errors.push(ValidationError::new(
                        ValidationCode::InvalidBounds,
                        format!("$.expectations.diagnostics.items[{index}].count"),
                        "diagnostic expectation count must be at least one",
                    ));
                }
                expected_error |= diagnostic.severity == Severity::Error;
                if let Some(location) = &diagnostic.primary_location {
                    match sources.get(&location.source_id) {
                        Some(source) => {
                            if let Some(text) = source.content.inline_text() {
                                if let Err(found) = location.validate_against_text(text) {
                                    errors.extend(found);
                                }
                            } else if let Err(found) = location.validate() {
                                errors.extend(found);
                            }
                        }
                        None => errors.push(ValidationError::new(
                            ValidationCode::UnresolvedReference,
                            format!(
                                "$.expectations.diagnostics.items[{index}].primary_location.source_id"
                            ),
                            "diagnostic expectation refers to an undeclared source",
                        )),
                    }
                }
            }
        }

        if expected_error && (self.matches.is_some() || self.targets.is_some()) {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.expectations",
                "expected errors cannot coexist with match or target expectations",
            ));
        }
        if let Some(matches) = &self.matches {
            matches.validate_at(expectation_program, errors);
        }
        if let Some(targets) = &self.targets {
            if targets.is_empty() {
                errors.push(ValidationError::new(
                    ValidationCode::EmptyCollection,
                    "$.expectations.targets",
                    "target expectations require at least one profile",
                ));
            }
            if targets
                .windows(2)
                .any(|pair| pair[0].target_profile >= pair[1].target_profile)
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    "$.expectations.targets",
                    "target expectations require unique sorted profile references",
                ));
            }
            for (index, target) in targets.iter().enumerate() {
                if let Some(reason_codes) = &target.reason_codes {
                    if reason_codes.windows(2).any(|pair| pair[0] >= pair[1]) {
                        errors.push(ValidationError::new(
                            ValidationCode::NonCanonicalOrder,
                            format!("$.expectations.targets[{index}].reason_codes"),
                            "target reason codes must be unique and sorted",
                        ));
                    }
                }
            }
        }
    }
}

impl SemanticFacts {
    fn validate_at(&self, program: Option<&SemanticProgram>, errors: &mut ValidationErrors) {
        if self.root_kind.is_none() && self.node_count.is_none() && self.capture_ids.is_none() {
            errors.push(ValidationError::new(
                ValidationCode::EmptyValue,
                "$.expectations.semantic.facts",
                "semantic facts require at least one asserted fact",
            ));
        }
        if self.node_count == Some(0) {
            errors.push(ValidationError::new(
                ValidationCode::InvalidBounds,
                "$.expectations.semantic.facts.node_count",
                "semantic node count must be at least one",
            ));
        }
        if let Some(captures) = &self.capture_ids {
            if captures.windows(2).any(|pair| pair[0] >= pair[1]) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    "$.expectations.semantic.facts.capture_ids",
                    "semantic fact capture identities must be unique and sorted",
                ));
            }
        }
        let Some(program) = program else {
            return;
        };
        let nodes = collect_nodes(&program.root);
        if self
            .root_kind
            .is_some_and(|kind| kind != SemanticNodeKind::of(&program.root))
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.expectations.semantic.facts.root_kind",
                "semantic root-kind fact contradicts the expected program",
            ));
        }
        if self
            .node_count
            .is_some_and(|count| usize::try_from(count).ok() != Some(nodes.len()))
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.expectations.semantic.facts.node_count",
                "semantic node-count fact contradicts the expected program",
            ));
        }
        let mut actual_captures: Vec<_> = nodes
            .iter()
            .filter_map(|node| match node {
                Node::Capture { capture_id, .. } => Some(capture_id.clone()),
                _ => None,
            })
            .collect();
        actual_captures.sort();
        if self
            .capture_ids
            .as_ref()
            .is_some_and(|expected| expected != &actual_captures)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.expectations.semantic.facts.capture_ids",
                "semantic capture facts contradict the expected program",
            ));
        }
    }
}

impl MatchExpectations {
    fn validate_at(&self, program: Option<&SemanticProgram>, errors: &mut ValidationErrors) {
        if self.positive.is_empty() && self.negative.is_empty() {
            errors.push(ValidationError::new(
                ValidationCode::EmptyCollection,
                "$.expectations.matches",
                "match expectations require a positive or negative subject",
            ));
        }
        if self
            .positive
            .windows(2)
            .any(|pair| pair[0].match_id >= pair[1].match_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.expectations.matches.positive",
                "positive match identities must be unique and sorted",
            ));
        }
        if self
            .negative
            .windows(2)
            .any(|pair| pair[0].match_id >= pair[1].match_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.expectations.matches.negative",
                "negative match identities must be unique and sorted",
            ));
        }
        let negative_ids: BTreeSet<_> = self.negative.iter().map(|item| &item.match_id).collect();
        if self
            .positive
            .iter()
            .any(|item| negative_ids.contains(&item.match_id))
        {
            errors.push(ValidationError::new(
                ValidationCode::DuplicateIdentity,
                "$.expectations.matches",
                "match identities must be unique across positive and negative subjects",
            ));
        }
        let declared_captures: BTreeSet<_> = program
            .map(|program| {
                collect_nodes(&program.root)
                    .into_iter()
                    .filter_map(|node| match node {
                        Node::Capture { capture_id, .. } => Some(capture_id),
                        _ => None,
                    })
                    .collect()
            })
            .unwrap_or_default();
        for (match_index, item) in self.positive.iter().enumerate() {
            if item
                .captures
                .windows(2)
                .any(|pair| pair[0].capture_id >= pair[1].capture_id)
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.expectations.matches.positive[{match_index}].captures"),
                    "capture expectations require unique sorted logical identities",
                ));
            }
            for (capture_index, capture) in item.captures.iter().enumerate() {
                let path = format!(
                    "$.expectations.matches.positive[{match_index}].captures[{capture_index}]"
                );
                if !declared_captures.contains(&capture.capture_id) {
                    errors.push(ValidationError::new(
                        ValidationCode::UnresolvedReference,
                        format!("{path}.capture_id"),
                        "capture expectation refers to an undeclared logical identity",
                    ));
                }
                capture.validate_at(&item.subject, &path, errors);
            }
        }
    }
}

impl CaptureExpectation {
    fn validate_at(&self, subject: &str, path: &str, errors: &mut ValidationErrors) {
        if self.matched != (self.text.is_some() && self.subject_span.is_some()) {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                path,
                "matched captures require text and span; unmatched captures forbid both",
            ));
            return;
        }
        let (Some(text), Some(span)) = (&self.text, &self.subject_span) else {
            return;
        };
        let start = usize::try_from(span.start).ok();
        let end = usize::try_from(span.end).ok();
        if span.start > span.end
            || start.map_or(true, |offset| !subject.is_char_boundary(offset))
            || end.map_or(true, |offset| !subject.is_char_boundary(offset))
        {
            errors.push(ValidationError::new(
                ValidationCode::Utf8Boundary,
                format!("{path}.subject_span"),
                "capture span must use valid half-open UTF-8 subject boundaries",
            ));
            return;
        }
        if &subject[start.unwrap_or(0)..end.unwrap_or(0)] != text {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                format!("{path}.text"),
                "capture text must equal its UTF-8 subject span",
            ));
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum ManifestOwnership {
    #[serde(rename = "specification")]
    Specification,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AuthorityStatus {
    Draft,
    DelegatedNormative,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Delegation {
    pub ratified_specification: SpecificationVersion,
    pub normative_source: NormativeSource,
    pub section: String,
    pub approval_record: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CaseEntry {
    pub case_id: CaseId,
    pub path: CasePath,
    pub sha256: Sha256Digest,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConformanceManifest {
    pub contract_version: ContractVersion,
    pub manifest_id: ManifestId,
    pub specification_version: SpecificationVersion,
    pub ownership: ManifestOwnership,
    pub authority_status: AuthorityStatus,
    #[serde(
        default,
        deserialize_with = "deserialize_optional_non_null",
        skip_serializing_if = "Option::is_none"
    )]
    pub delegation: Option<Delegation>,
    pub cases: Vec<CaseEntry>,
}

impl Validate for ConformanceManifest {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        match (self.authority_status, &self.delegation) {
            (AuthorityStatus::Draft, Some(_)) => errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.delegation",
                "draft conformance manifests cannot claim normative delegation",
            )),
            (AuthorityStatus::DelegatedNormative, None) => {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    "$.delegation",
                    "delegated normative manifests require an explicit delegation",
                ));
            }
            (AuthorityStatus::DelegatedNormative, Some(delegation)) => {
                if delegation.ratified_specification != self.specification_version {
                    errors.push(ValidationError::new(
                        ValidationCode::SpecificationMismatch,
                        "$.delegation.ratified_specification",
                        "delegation must name the manifest specification",
                    ));
                }
                nonempty(&delegation.section, "$.delegation.section", &mut errors);
                nonempty(
                    &delegation.approval_record,
                    "$.delegation.approval_record",
                    &mut errors,
                );
            }
            (AuthorityStatus::Draft, None) => {}
        }
        if self.cases.is_empty() {
            errors.push(ValidationError::new(
                ValidationCode::EmptyCollection,
                "$.cases",
                "conformance manifest requires at least one case",
            ));
        }
        if self
            .cases
            .windows(2)
            .any(|pair| pair[0].case_id >= pair[1].case_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.cases",
                "manifest case entries require unique sorted case identities",
            ));
        }
        let mut paths = BTreeSet::new();
        for (index, entry) in self.cases.iter().enumerate() {
            if !paths.insert(&entry.path) {
                errors.push(ValidationError::new(
                    ValidationCode::DuplicateIdentity,
                    format!("$.cases[{index}].path"),
                    "manifest case paths must be unique",
                ));
            }
        }
        errors.finish()
    }
}

impl ConformanceManifest {
    /// Certify an explicitly provided, in-memory case corpus against this manifest.
    pub fn certify_cases(
        &self,
        cases: &[(CasePath, ConformanceCase)],
        profiles: &TargetProfileSet,
    ) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if let Err(found) = self.validate() {
            errors.extend(found);
        }
        if cases.len() != self.cases.len() {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.cases",
                "manifest must list every and only supplied specification-owned case",
            ));
        }
        for (index, entry) in self.cases.iter().enumerate() {
            let Some((_, case)) = cases.iter().find(|(path, _)| path == &entry.path) else {
                errors.push(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    format!("$.cases[{index}].path"),
                    "manifest case path does not resolve in the supplied corpus",
                ));
                continue;
            };
            if case.case_id != entry.case_id {
                errors.push(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    format!("$.cases[{index}].case_id"),
                    "manifest case identity does not match its case document",
                ));
            }
            if case.specification_version != self.specification_version {
                errors.push(ValidationError::new(
                    ValidationCode::SpecificationMismatch,
                    format!("$.cases[{index}]"),
                    "manifest and case specification versions must match",
                ));
            }
            match case.fingerprint() {
                Ok(fingerprint) if fingerprint != entry.sha256 => {
                    errors.push(ValidationError::new(
                        ValidationCode::InvalidDigest,
                        format!("$.cases[{index}].sha256"),
                        "manifest fingerprint does not match canonical case JSON",
                    ));
                }
                Err(found) => errors.extend(found),
                Ok(_) => {}
            }
            if let Err(found) = case.validate_against_profiles(profiles) {
                errors.extend(found);
            }
        }
        let declared_paths: BTreeSet<_> = self.cases.iter().map(|entry| &entry.path).collect();
        for (index, (path, _)) in cases.iter().enumerate() {
            if !declared_paths.contains(path) {
                errors.push(ValidationError::new(
                    ValidationCode::UnresolvedReference,
                    format!("$.supplied_cases[{index}]"),
                    "supplied case is not owned by the manifest",
                ));
            }
        }
        errors.finish()
    }
}

fn input_sources(input: &CompileInput) -> BTreeMap<&SourceId, &SourceDocument> {
    match input {
        CompileInput::Source { document } => {
            BTreeMap::from([(&document.source_id, document.as_ref())])
        }
        CompileInput::Semantic { program } => program
            .sources
            .as_ref()
            .map(|sources| {
                sources
                    .iter()
                    .map(|source| (&source.source_id, source))
                    .collect()
            })
            .unwrap_or_default(),
    }
}

fn collect_nodes(root: &Node) -> Vec<&Node> {
    fn visit<'a>(node: &'a Node, nodes: &mut Vec<&'a Node>) {
        nodes.push(node);
        match node {
            Node::Sequence { items, .. } => {
                for child in items {
                    visit(child, nodes);
                }
            }
            Node::Alternation { branches, .. } => {
                for child in branches {
                    visit(child, nodes);
                }
            }
            Node::Repeat { body, .. }
            | Node::Capture { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => visit(body, nodes),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
    }
    let mut nodes = Vec::new();
    visit(root, &mut nodes);
    nodes
}

fn diagnostic_expectation_cmp(
    left: &DiagnosticExpectation,
    right: &DiagnosticExpectation,
) -> Ordering {
    location_cmp(
        left.primary_location.as_ref(),
        right.primary_location.as_ref(),
    )
    .then_with(|| left.phase.cmp(&right.phase))
    .then_with(|| left.severity.cmp(&right.severity))
    .then_with(|| left.category.cmp(&right.category))
    .then_with(|| left.code.cmp(&right.code))
}

fn location_cmp(left: Option<&SourceSpan>, right: Option<&SourceSpan>) -> Ordering {
    match (left, right) {
        (Some(left), Some(right)) => left.cmp(right),
        (Some(_), None) => Ordering::Less,
        (None, Some(_)) => Ordering::Greater,
        (None, None) => Ordering::Equal,
    }
}
