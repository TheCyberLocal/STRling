//! Deterministic canonicalization of target-neutral Semantic IR.

use std::collections::{HashMap, HashSet};
use std::error::Error;
use std::fmt::{self, Write as _};

use serde::{Deserialize, Serialize};

use crate::semantic::{
    BuiltinClassName, CharacterDomain, CharacterSetMember, Node, RepetitionMaximum, SemanticProgram,
};
use crate::source::{CaptureId, NodeId, SourceDocument, SourceId, SourceOrigin, SourceSpan};
use crate::validation::{Validate, ValidationCode, ValidationErrors};

/// Stable categories for failures encountered before or during normalization.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NormalizationErrorCode {
    InvalidSemanticStructure,
    InvalidIdentity,
    InvalidReference,
    InvalidRepetitionBounds,
    InvalidCharacterSet,
    InvalidProvenance,
    CanonicalizationInvariant,
    UnsupportedContractState,
}

/// One machine-classifiable normalization failure with a stable data path.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NormalizationError {
    pub code: NormalizationErrorCode,
    pub path: String,
    pub message: String,
}

impl NormalizationError {
    fn new(
        code: NormalizationErrorCode,
        path: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            code,
            path: path.into(),
            message: message.into(),
        }
    }
}

/// Ordered failures returned for malformed Semantic IR candidates.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NormalizationErrors {
    pub errors: Vec<NormalizationError>,
}

impl NormalizationErrors {
    fn push(&mut self, error: NormalizationError) {
        self.errors.push(error);
    }

    fn finish(self) -> Result<(), Self> {
        if self.errors.is_empty() {
            Ok(())
        } else {
            Err(self)
        }
    }

    fn canonicalization(errors: ValidationErrors) -> Self {
        Self {
            errors: errors
                .errors
                .into_iter()
                .map(|error| {
                    NormalizationError::new(
                        NormalizationErrorCode::CanonicalizationInvariant,
                        error.path,
                        error.message,
                    )
                })
                .collect(),
        }
    }
}

impl fmt::Display for NormalizationErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} semantic normalization error(s)",
            self.errors.len()
        )
    }
}

impl Error for NormalizationErrors {}

/// Normalize a structurally decoded Semantic IR candidate into `canonical-v1`.
///
/// The operation is pure and target-neutral. It preserves every retained node
/// and logical capture identity, and returns structured failures for malformed
/// semantic state instead of panicking.
pub fn normalize(input: &SemanticProgram) -> Result<SemanticProgram, NormalizationErrors> {
    normalize_owned(input.clone())
}

/// Normalize an already-owned candidate without cloning its complete tree.
///
/// Canonical frontends use this internal path immediately after lowering. The
/// public borrowed API remains unchanged for callers that retain their input.
pub(crate) fn normalize_owned(
    input: SemanticProgram,
) -> Result<SemanticProgram, NormalizationErrors> {
    Preflight::validate(&input)?;

    let SemanticProgram {
        contract_version,
        specification_version,
        normalization,
        case_matching,
        sources,
        root,
    } = input;
    let output = SemanticProgram {
        contract_version,
        specification_version,
        normalization,
        case_matching,
        sources,
        root: normalize_node(root),
    };
    output
        .validate()
        .map_err(NormalizationErrors::canonicalization)?;
    Ok(output)
}

struct Preflight<'a> {
    sources: HashMap<&'a SourceId, &'a SourceDocument>,
    node_ids: HashSet<&'a NodeId>,
    capture_ids: HashSet<&'a CaptureId>,
    capture_names: HashSet<&'a str>,
    references: Vec<(String, &'a CaptureId)>,
    errors: NormalizationErrors,
}

impl<'a> Preflight<'a> {
    fn validate(program: &'a SemanticProgram) -> Result<(), NormalizationErrors> {
        let mut preflight = Self {
            sources: HashMap::new(),
            node_ids: HashSet::new(),
            capture_ids: HashSet::new(),
            capture_names: HashSet::new(),
            references: Vec::new(),
            errors: NormalizationErrors::default(),
        };

        if let Some(sources) = &program.sources {
            if sources.is_empty() {
                preflight.error(
                    NormalizationErrorCode::InvalidSemanticStructure,
                    "$.sources",
                    "embedded sources must not be empty",
                );
            }
            for (index, source) in sources.iter().enumerate() {
                let path = format!("$.sources[{index}]");
                if let Err(errors) = source.validate() {
                    preflight.extend_validation(&path, errors);
                }
                if source.specification_version != program.specification_version {
                    preflight.error(
                        NormalizationErrorCode::InvalidSemanticStructure,
                        format!("{path}.specification_version"),
                        "embedded source must use the program specification version",
                    );
                }
                if preflight
                    .sources
                    .insert(&source.source_id, source)
                    .is_some()
                {
                    preflight.error(
                        NormalizationErrorCode::InvalidIdentity,
                        format!("{path}.source_id"),
                        "embedded source identity must be unique",
                    );
                }
            }
        }

        let mut path = String::with_capacity(128);
        path.push_str("$.root");
        preflight.visit_node(&program.root, &mut path);
        for (path, capture_id) in &preflight.references {
            if !preflight.capture_ids.contains(*capture_id) {
                preflight.errors.push(NormalizationError::new(
                    NormalizationErrorCode::InvalidReference,
                    format!("{path}.capture_id"),
                    "backreference must resolve to a logical capture identity",
                ));
            }
        }
        preflight.errors.finish()
    }

    fn visit_node(&mut self, node: &'a Node, path: &mut String) {
        if !self.node_ids.insert(node.node_id()) {
            self.error(
                NormalizationErrorCode::InvalidIdentity,
                format!("{path}.node_id"),
                "node identity must be unique before normalization",
            );
        }
        if let Some(origin) = node.origin() {
            let parent_length = path.len();
            path.push_str(".origin");
            self.validate_origin(origin, path);
            path.truncate(parent_length);
        }

        match node {
            Node::Empty { .. } | Node::Wildcard { .. } | Node::Position { .. } => {}
            Node::Sequence { items, .. } => {
                if items.is_empty() {
                    self.error(
                        NormalizationErrorCode::InvalidSemanticStructure,
                        format!("{path}.items"),
                        "sequence input must contain at least one child",
                    );
                }
                let parent_length = path.len();
                for (index, child) in items.iter().enumerate() {
                    path.truncate(parent_length);
                    let _ = write!(path, ".items[{index}]");
                    self.visit_node(child, path);
                }
                path.truncate(parent_length);
            }
            Node::Alternation { branches, .. } => {
                if branches.is_empty() {
                    self.error(
                        NormalizationErrorCode::InvalidSemanticStructure,
                        format!("{path}.branches"),
                        "alternation input must contain at least one branch",
                    );
                }
                let parent_length = path.len();
                for (index, child) in branches.iter().enumerate() {
                    path.truncate(parent_length);
                    let _ = write!(path, ".branches[{index}]");
                    self.visit_node(child, path);
                }
                path.truncate(parent_length);
            }
            Node::Literal { text, .. } => {
                if text.is_empty() {
                    self.error(
                        NormalizationErrorCode::InvalidSemanticStructure,
                        format!("{path}.text"),
                        "literal input text must not be empty",
                    );
                }
            }
            Node::CharacterSet { members, .. } => {
                if members.is_empty() {
                    self.error(
                        NormalizationErrorCode::InvalidCharacterSet,
                        format!("{path}.members"),
                        "character set must contain at least one member",
                    );
                }
                let parent_length = path.len();
                for (index, member) in members.iter().enumerate() {
                    path.truncate(parent_length);
                    let _ = write!(path, ".members[{index}]");
                    self.validate_set_member(member, path);
                }
                path.truncate(parent_length);
            }
            Node::Repeat { body, min, max, .. } => {
                if matches!(max, RepetitionMaximum::Bounded(maximum) if maximum < min) {
                    self.error(
                        NormalizationErrorCode::InvalidRepetitionBounds,
                        format!("{path}.max"),
                        "finite repetition maximum must not be less than minimum",
                    );
                }
                let parent_length = path.len();
                path.push_str(".body");
                self.visit_node(body, path);
                path.truncate(parent_length);
            }
            Node::Capture {
                capture_id,
                name,
                body,
                ..
            } => {
                if !self.capture_ids.insert(capture_id) {
                    self.error(
                        NormalizationErrorCode::InvalidIdentity,
                        format!("{path}.capture_id"),
                        "logical capture identity must be unique",
                    );
                }
                if let Some(name) = name {
                    if name.is_empty() {
                        self.error(
                            NormalizationErrorCode::InvalidSemanticStructure,
                            format!("{path}.name"),
                            "capture name must not be empty",
                        );
                    } else if !self.capture_names.insert(name.as_str()) {
                        self.error(
                            NormalizationErrorCode::InvalidIdentity,
                            format!("{path}.name"),
                            "capture name must be unique",
                        );
                    }
                }
                let parent_length = path.len();
                path.push_str(".body");
                self.visit_node(body, path);
                path.truncate(parent_length);
            }
            Node::Backreference { capture_id, .. } => {
                self.references.push((path.clone(), capture_id));
            }
            Node::Lookaround { body, .. } | Node::Atomic { body, .. } => {
                let parent_length = path.len();
                path.push_str(".body");
                self.visit_node(body, path);
                path.truncate(parent_length);
            }
        }
    }

    fn validate_origin(&mut self, origin: &SourceOrigin, path: &mut String) {
        if origin.source_spans.is_none() && origin.derived_from_node_ids.is_none() {
            self.error(
                NormalizationErrorCode::InvalidProvenance,
                path.as_str(),
                "origin requires source spans, derived node identities, or both",
            );
        }
        if let Some(spans) = &origin.source_spans {
            if spans.is_empty() {
                self.error(
                    NormalizationErrorCode::InvalidProvenance,
                    format!("{path}.source_spans"),
                    "source spans must not be empty",
                );
            }
            let origin_length = path.len();
            for (index, span) in spans.iter().enumerate() {
                path.truncate(origin_length);
                let _ = write!(path, ".source_spans[{index}]");
                match self.sources.get(&span.source_id) {
                    Some(source) => {
                        if let Some(text) = source.content.inline_text() {
                            if let Err(errors) = span.validate_against_text(text) {
                                self.extend_validation(path, errors);
                            }
                        } else if let Err(errors) = span.validate() {
                            self.extend_validation(path, errors);
                        }
                    }
                    None => self.error(
                        NormalizationErrorCode::InvalidProvenance,
                        format!("{path}.source_id"),
                        "origin span must reference an embedded source",
                    ),
                }
            }
            path.truncate(origin_length);
        }
        if origin
            .derived_from_node_ids
            .as_ref()
            .is_some_and(Vec::is_empty)
        {
            self.error(
                NormalizationErrorCode::InvalidProvenance,
                format!("{path}.derived_from_node_ids"),
                "derived node identities must not be empty",
            );
        }
    }

    fn validate_set_member(&mut self, member: &CharacterSetMember, path: &str) {
        match member {
            CharacterSetMember::Range { start, end } if start > end => self.error(
                NormalizationErrorCode::InvalidCharacterSet,
                path,
                "character-set range start must not exceed end",
            ),
            CharacterSetMember::UnicodeProperty {
                property, value, ..
            } => {
                if property.is_empty() {
                    self.error(
                        NormalizationErrorCode::InvalidCharacterSet,
                        format!("{path}.property"),
                        "Unicode property must not be empty",
                    );
                }
                if value.as_ref().is_some_and(String::is_empty) {
                    self.error(
                        NormalizationErrorCode::InvalidCharacterSet,
                        format!("{path}.value"),
                        "Unicode property value must not be empty",
                    );
                }
            }
            _ => {}
        }
    }

    fn extend_validation(&mut self, prefix: &str, errors: ValidationErrors) {
        for error in errors.errors {
            let suffix = error.path.strip_prefix('$').unwrap_or(&error.path);
            self.error(
                normalization_code(error.code),
                format!("{prefix}{suffix}"),
                error.message,
            );
        }
    }

    fn error(
        &mut self,
        code: NormalizationErrorCode,
        path: impl Into<String>,
        message: impl Into<String>,
    ) {
        self.errors
            .push(NormalizationError::new(code, path, message));
    }
}

fn normalization_code(code: ValidationCode) -> NormalizationErrorCode {
    match code {
        ValidationCode::DuplicateIdentity | ValidationCode::InvalidIdentity => {
            NormalizationErrorCode::InvalidIdentity
        }
        ValidationCode::UnresolvedReference => NormalizationErrorCode::InvalidReference,
        ValidationCode::InvalidBounds => NormalizationErrorCode::InvalidSemanticStructure,
        ValidationCode::InvalidProvenance
        | ValidationCode::InvalidSpan
        | ValidationCode::Utf8Boundary => NormalizationErrorCode::InvalidProvenance,
        ValidationCode::EmptyCollection
        | ValidationCode::EmptyValue
        | ValidationCode::InvalidDigest
        | ValidationCode::InvalidUri
        | ValidationCode::InvalidVersion
        | ValidationCode::NonCanonicalOrder
        | ValidationCode::NonCanonicalStructure
        | ValidationCode::SpecificationMismatch => NormalizationErrorCode::InvalidSemanticStructure,
    }
}

fn normalize_node(node: Node) -> Node {
    match node {
        Node::Empty { node_id, origin } => Node::Empty {
            node_id,
            origin: normalize_origin(origin),
        },
        Node::Sequence {
            node_id,
            origin,
            items,
        } => normalize_sequence(node_id, origin, items),
        Node::Alternation {
            node_id,
            origin,
            branches,
        } => normalize_alternation(node_id, origin, branches),
        Node::Literal {
            node_id,
            origin,
            text,
        } => Node::Literal {
            node_id,
            origin: normalize_origin(origin),
            text,
        },
        Node::Wildcard {
            node_id,
            origin,
            line_terminators,
        } => Node::Wildcard {
            node_id,
            origin: normalize_origin(origin),
            line_terminators,
        },
        Node::CharacterSet {
            node_id,
            origin,
            negated,
            members,
        } => {
            let mut members = members;
            members.sort_by_key(character_set_key);
            members.dedup();
            Node::CharacterSet {
                node_id,
                origin: normalize_origin(origin),
                negated,
                members,
            }
        }
        Node::Repeat {
            node_id,
            origin,
            body,
            min,
            max,
            mode,
        } => Node::Repeat {
            node_id,
            origin: normalize_origin(origin),
            body: Box::new(normalize_node(*body)),
            min,
            max,
            mode,
        },
        Node::Position {
            node_id,
            origin,
            position,
        } => Node::Position {
            node_id,
            origin: normalize_origin(origin),
            position,
        },
        Node::Capture {
            node_id,
            origin,
            capture_id,
            name,
            body,
        } => Node::Capture {
            node_id,
            origin: normalize_origin(origin),
            capture_id,
            name,
            body: Box::new(normalize_node(*body)),
        },
        Node::Backreference {
            node_id,
            origin,
            capture_id,
        } => Node::Backreference {
            node_id,
            origin: normalize_origin(origin),
            capture_id,
        },
        Node::Lookaround {
            node_id,
            origin,
            direction,
            polarity,
            body,
        } => Node::Lookaround {
            node_id,
            origin: normalize_origin(origin),
            direction,
            polarity,
            body: Box::new(normalize_node(*body)),
        },
        Node::Atomic {
            node_id,
            origin,
            body,
        } => Node::Atomic {
            node_id,
            origin: normalize_origin(origin),
            body: Box::new(normalize_node(*body)),
        },
    }
}

fn normalize_sequence(node_id: NodeId, origin: Option<SourceOrigin>, items: Vec<Node>) -> Node {
    let mut container_origin = normalize_origin(origin);
    let mut flattened = Vec::new();
    for child in items {
        match normalize_node(child) {
            Node::Sequence {
                node_id,
                origin,
                items,
            } => {
                accumulate_removed(&mut container_origin, origin, node_id);
                flattened.extend(items);
            }
            child => flattened.push(child),
        }
    }

    let mut coalesced: Vec<Node> = Vec::new();
    for child in flattened {
        match child {
            Node::Literal {
                node_id,
                origin,
                text,
            } => {
                if let Some(Node::Literal {
                    origin: previous_origin,
                    text: previous_text,
                    ..
                }) = coalesced.last_mut()
                {
                    previous_text.push_str(&text);
                    accumulate_removed(previous_origin, origin, node_id);
                } else {
                    coalesced.push(Node::Literal {
                        node_id,
                        origin,
                        text,
                    });
                }
            }
            child => coalesced.push(child),
        }
    }

    if coalesced.len() == 1 {
        let mut child = coalesced.remove(0);
        accumulate_removed(node_origin_mut(&mut child), container_origin, node_id);
        child
    } else {
        Node::Sequence {
            node_id,
            origin: container_origin,
            items: coalesced,
        }
    }
}

fn normalize_alternation(
    node_id: NodeId,
    origin: Option<SourceOrigin>,
    branches: Vec<Node>,
) -> Node {
    let mut container_origin = normalize_origin(origin);
    let mut flattened = Vec::new();
    for branch in branches {
        match normalize_node(branch) {
            Node::Alternation {
                node_id,
                origin,
                branches,
            } => {
                accumulate_removed(&mut container_origin, origin, node_id);
                flattened.extend(branches);
            }
            branch => flattened.push(branch),
        }
    }

    if flattened.len() == 1 {
        let mut branch = flattened.remove(0);
        accumulate_removed(node_origin_mut(&mut branch), container_origin, node_id);
        branch
    } else {
        Node::Alternation {
            node_id,
            origin: container_origin,
            branches: flattened,
        }
    }
}

fn normalize_origin(origin: Option<SourceOrigin>) -> Option<SourceOrigin> {
    origin.map(|mut origin| {
        canonicalize_origin(&mut origin);
        origin
    })
}

fn accumulate_removed(
    target: &mut Option<SourceOrigin>,
    removed_origin: Option<SourceOrigin>,
    removed_node_id: NodeId,
) {
    let target = target.get_or_insert(SourceOrigin {
        source_spans: None,
        derived_from_node_ids: None,
    });
    if let Some(removed_origin) = removed_origin {
        if let Some(spans) = removed_origin.source_spans {
            target
                .source_spans
                .get_or_insert_with(Vec::new)
                .extend(spans);
        }
        if let Some(node_ids) = removed_origin.derived_from_node_ids {
            target
                .derived_from_node_ids
                .get_or_insert_with(Vec::new)
                .extend(node_ids);
        }
    }
    target
        .derived_from_node_ids
        .get_or_insert_with(Vec::new)
        .push(removed_node_id);
    canonicalize_origin(target);
}

fn canonicalize_origin(origin: &mut SourceOrigin) {
    if let Some(spans) = &mut origin.source_spans {
        spans.sort();
        spans.dedup();
        let mut disjoint: Vec<SourceSpan> = Vec::with_capacity(spans.len());
        for span in spans.drain(..) {
            if let Some(previous) = disjoint.last_mut() {
                if previous.source_id == span.source_id && previous.end > span.start {
                    previous.end = previous.end.max(span.end);
                    continue;
                }
            }
            disjoint.push(span);
        }
        *spans = disjoint;
    }
    if let Some(node_ids) = &mut origin.derived_from_node_ids {
        node_ids.sort();
        node_ids.dedup();
    }
}

fn node_origin_mut(node: &mut Node) -> &mut Option<SourceOrigin> {
    match node {
        Node::Empty { origin, .. }
        | Node::Sequence { origin, .. }
        | Node::Alternation { origin, .. }
        | Node::Literal { origin, .. }
        | Node::Wildcard { origin, .. }
        | Node::CharacterSet { origin, .. }
        | Node::Repeat { origin, .. }
        | Node::Position { origin, .. }
        | Node::Capture { origin, .. }
        | Node::Backreference { origin, .. }
        | Node::Lookaround { origin, .. }
        | Node::Atomic { origin, .. } => origin,
    }
}

fn character_set_key(member: &CharacterSetMember) -> (u8, String, String, bool) {
    match member {
        CharacterSetMember::Literal { value } => (0, value.to_string(), String::new(), false),
        CharacterSetMember::Range { start, end } => (1, start.to_string(), end.to_string(), false),
        CharacterSetMember::Builtin {
            name,
            domain,
            negated,
        } => (
            2,
            match name {
                BuiltinClassName::Digit => "digit",
                BuiltinClassName::Word => "word",
                BuiltinClassName::Whitespace => "whitespace",
            }
            .to_owned(),
            match domain {
                CharacterDomain::Ascii => "ascii",
                CharacterDomain::TargetNative => "target_native",
                CharacterDomain::Unicode => "unicode",
            }
            .to_owned(),
            *negated,
        ),
        CharacterSetMember::UnicodeProperty {
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
