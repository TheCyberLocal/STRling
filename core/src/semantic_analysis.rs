//! Foundational target-neutral facts derived from canonical Semantic IR.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::semantic::{Node, SemanticProgram};
use crate::source::{CaptureId, ContractVersion, NodeId, SpecificationVersion};
use crate::validation::{Validate, ValidationCode, ValidationErrors};

mod capture;
mod consumption;

pub use capture::{BackreferenceResolution, CaptureDefinition};
pub use consumption::{Consumption, MaximumConsumption, Nullability};

/// Maximum accepted semantic nesting before recursive contract validation.
///
/// The preflight walk itself is iterative, so externally supplied pathological
/// structures fail predictably rather than exhausting the process stack.
pub const MAX_ANALYSIS_DEPTH: usize = 128;

/// Stable categories for semantic-analysis failures.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticAnalysisErrorCode {
    InvalidSemanticStructure,
    InvalidIdentity,
    InvalidReference,
    NonCanonicalInput,
    DepthLimitExceeded,
    ArithmeticOverflow,
    AnalysisInvariant,
}

/// One machine-classifiable semantic-analysis failure with a stable data path.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticAnalysisError {
    pub code: SemanticAnalysisErrorCode,
    pub path: String,
    pub message: String,
}

impl SemanticAnalysisError {
    fn new(
        code: SemanticAnalysisErrorCode,
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

/// Ordered failures returned for invalid or noncanonical semantic input.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticAnalysisErrors {
    pub errors: Vec<SemanticAnalysisError>,
}

impl SemanticAnalysisErrors {
    fn single(error: SemanticAnalysisError) -> Self {
        Self {
            errors: vec![error],
        }
    }

    fn from_validation(errors: ValidationErrors) -> Self {
        Self {
            errors: errors
                .errors
                .into_iter()
                .map(|error| {
                    SemanticAnalysisError::new(analysis_code(error.code), error.path, error.message)
                })
                .collect(),
        }
    }
}

impl fmt::Display for SemanticAnalysisErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} semantic analysis error(s)",
            self.errors.len()
        )
    }
}

impl Error for SemanticAnalysisErrors {}

/// The ratified Semantic IR category represented by a fact record.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
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

/// Facts associated with one reachable stable semantic node identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NodeFacts {
    pub kind: SemanticNodeKind,
    pub nullability: Nullability,
    pub minimum_consumption: u64,
    pub maximum_consumption: MaximumConsumption,
    pub consumption: Consumption,
    pub captures_defined: BTreeSet<CaptureId>,
    pub captures_referenced: BTreeSet<CaptureId>,
    pub backreferences_used: BTreeSet<NodeId>,
    pub capture: Option<CaptureDefinition>,
    pub backreference: Option<BackreferenceResolution>,
}

/// Complete deterministic fact store for one canonical semantic program.
///
/// The internal `BTreeMap` makes identity order stable without treating
/// traversal order or allocation addresses as externally observable facts.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticFacts {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    node_facts: BTreeMap<NodeId, NodeFacts>,
    capture_definitions: BTreeMap<CaptureId, CaptureDefinition>,
    backreferences: BTreeMap<NodeId, BackreferenceResolution>,
}

impl SemanticFacts {
    /// Look up facts by the stable identity carried by Semantic IR.
    #[must_use]
    pub fn get(&self, node_id: &NodeId) -> Option<&NodeFacts> {
        self.node_facts.get(node_id)
    }

    /// Iterate in canonical node-identity order.
    pub fn iter(&self) -> impl ExactSizeIterator<Item = (&NodeId, &NodeFacts)> {
        self.node_facts.iter()
    }

    #[must_use]
    pub fn capture_definition(&self, capture_id: &CaptureId) -> Option<&CaptureDefinition> {
        self.capture_definitions.get(capture_id)
    }

    /// Iterate logical capture declarations in canonical identity order.
    pub fn capture_definitions(
        &self,
    ) -> impl ExactSizeIterator<Item = (&CaptureId, &CaptureDefinition)> {
        self.capture_definitions.iter()
    }

    #[must_use]
    pub fn backreference(&self, node_id: &NodeId) -> Option<&BackreferenceResolution> {
        self.backreferences.get(node_id)
    }

    /// Iterate resolved backreferences in canonical node-identity order.
    pub fn backreferences(
        &self,
    ) -> impl ExactSizeIterator<Item = (&NodeId, &BackreferenceResolution)> {
        self.backreferences.iter()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.node_facts.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.node_facts.is_empty()
    }
}

/// Analyze one already-normalized target-neutral semantic program.
///
/// This pure stage never invokes normalization. Invalid and noncanonical
/// candidates are rejected with stable structured errors.
pub fn analyze(input: &SemanticProgram) -> Result<SemanticFacts, SemanticAnalysisErrors> {
    enforce_depth_limit(&input.root)?;
    input
        .validate()
        .map_err(SemanticAnalysisErrors::from_validation)?;

    let consumption_facts = consumption::analyze_consumption(input)?;
    let capture_analysis = capture::analyze_captures(input)?;
    let mut node_facts = BTreeMap::new();
    let mut pending = vec![&input.root];
    while let Some(node) = pending.pop() {
        let node_id = node.node_id().clone();
        let capture = capture_analysis.node_facts.get(&node_id).ok_or_else(|| {
            SemanticAnalysisErrors::single(SemanticAnalysisError::new(
                SemanticAnalysisErrorCode::AnalysisInvariant,
                "$.root",
                format!("capture analysis omitted reachable node: {node_id:?}"),
            ))
        })?;
        if node_facts
            .insert(
                node_id.clone(),
                match consumption_facts.get(&node_id) {
                    Some(consumption) => NodeFacts {
                        kind: node_kind(node),
                        nullability: consumption.nullability,
                        minimum_consumption: consumption.minimum,
                        maximum_consumption: consumption.maximum,
                        consumption: consumption.consumption,
                        captures_defined: capture.captures_defined.clone(),
                        captures_referenced: capture.captures_referenced.clone(),
                        backreferences_used: capture.backreferences_used.clone(),
                        capture: capture.capture.clone(),
                        backreference: capture.backreference.clone(),
                    },
                    None => {
                        return Err(SemanticAnalysisErrors::single(SemanticAnalysisError::new(
                            SemanticAnalysisErrorCode::AnalysisInvariant,
                            "$.root",
                            format!("consumption analysis omitted reachable node: {node_id:?}"),
                        )));
                    }
                },
            )
            .is_some()
        {
            return Err(SemanticAnalysisErrors::single(SemanticAnalysisError::new(
                SemanticAnalysisErrorCode::InvalidIdentity,
                "$.root",
                format!("duplicate node identity reached during analysis: {node_id:?}"),
            )));
        }
        push_children(node, &mut pending);
    }

    if node_facts.is_empty() {
        return Err(SemanticAnalysisErrors::single(SemanticAnalysisError::new(
            SemanticAnalysisErrorCode::AnalysisInvariant,
            "$.root",
            "analysis produced no fact record for the semantic root",
        )));
    }

    Ok(SemanticFacts {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        node_facts,
        capture_definitions: capture_analysis.definitions,
        backreferences: capture_analysis.backreferences,
    })
}

fn enforce_depth_limit(root: &Node) -> Result<(), SemanticAnalysisErrors> {
    let mut pending = vec![(root, 1_usize)];
    while let Some((node, depth)) = pending.pop() {
        if depth > MAX_ANALYSIS_DEPTH {
            return Err(SemanticAnalysisErrors::single(SemanticAnalysisError::new(
                SemanticAnalysisErrorCode::DepthLimitExceeded,
                "$.root",
                format!("semantic nesting depth exceeds analysis limit of {MAX_ANALYSIS_DEPTH}"),
            )));
        }
        let child_depth = depth + 1;
        match node {
            Node::Sequence { items, .. } => {
                pending.extend(items.iter().rev().map(|child| (child, child_depth)));
            }
            Node::Alternation { branches, .. } => {
                pending.extend(branches.iter().rev().map(|child| (child, child_depth)));
            }
            Node::Repeat { body, .. }
            | Node::Capture { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => pending.push((body, child_depth)),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
    }
    Ok(())
}

fn push_children<'a>(node: &'a Node, pending: &mut Vec<&'a Node>) {
    match node {
        Node::Sequence { items, .. } => pending.extend(items.iter().rev()),
        Node::Alternation { branches, .. } => pending.extend(branches.iter().rev()),
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => pending.push(body),
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => {}
    }
}

fn node_kind(node: &Node) -> SemanticNodeKind {
    match node {
        Node::Empty { .. } => SemanticNodeKind::Empty,
        Node::Sequence { .. } => SemanticNodeKind::Sequence,
        Node::Alternation { .. } => SemanticNodeKind::Alternation,
        Node::Literal { .. } => SemanticNodeKind::Literal,
        Node::Wildcard { .. } => SemanticNodeKind::Wildcard,
        Node::CharacterSet { .. } => SemanticNodeKind::CharacterSet,
        Node::Repeat { .. } => SemanticNodeKind::Repeat,
        Node::Position { .. } => SemanticNodeKind::Position,
        Node::Capture { .. } => SemanticNodeKind::Capture,
        Node::Backreference { .. } => SemanticNodeKind::Backreference,
        Node::Lookaround { .. } => SemanticNodeKind::Lookaround,
        Node::Atomic { .. } => SemanticNodeKind::Atomic,
    }
}

fn analysis_code(code: ValidationCode) -> SemanticAnalysisErrorCode {
    match code {
        ValidationCode::DuplicateIdentity | ValidationCode::InvalidIdentity => {
            SemanticAnalysisErrorCode::InvalidIdentity
        }
        ValidationCode::UnresolvedReference => SemanticAnalysisErrorCode::InvalidReference,
        ValidationCode::NonCanonicalOrder | ValidationCode::NonCanonicalStructure => {
            SemanticAnalysisErrorCode::NonCanonicalInput
        }
        ValidationCode::EmptyCollection
        | ValidationCode::EmptyValue
        | ValidationCode::InvalidBounds
        | ValidationCode::InvalidDigest
        | ValidationCode::InvalidProvenance
        | ValidationCode::InvalidSpan
        | ValidationCode::InvalidUri
        | ValidationCode::InvalidVersion
        | ValidationCode::SpecificationMismatch
        | ValidationCode::Utf8Boundary => SemanticAnalysisErrorCode::InvalidSemanticStructure,
    }
}
