//! Target-neutral structural facts derived from canonical Semantic IR and
//! certified foundational semantic facts.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::semantic::{
    CharacterSetMember, LineTerminators, Node, RepetitionMaximum, SemanticProgram, UnicodeScalar,
};
use crate::semantic_analysis::{
    semantic_program_identity, MaximumConsumption, Nullability, SemanticFacts, SemanticNodeKind,
    MAX_ANALYSIS_DEPTH,
};
use crate::source::{ContractVersion, NodeId, SpecificationVersion};
use crate::validation::{Validate, ValidationCode, ValidationErrors};

/// Maximum accepted semantic nesting for structural analysis.
pub const MAX_STRUCTURE_DEPTH: usize = MAX_ANALYSIS_DEPTH;

/// Maximum exact terms retained in one leading-consumption set.
///
/// One slot is reserved for a typed complexity-limit unknown when a union
/// crosses this deterministic bound.
pub const MAX_LEADING_TERMS: usize = 256;

/// Stable categories for structural-analysis failures.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum StructuralAnalysisErrorCode {
    InvalidSemanticStructure,
    InvalidIdentity,
    NonCanonicalInput,
    DepthLimitExceeded,
    MismatchedFoundationalFacts,
    MissingFoundationalFact,
    UnexpectedFoundationalFact,
    FoundationalKindMismatch,
    AnalysisInvariant,
}

/// One machine-classifiable structural-analysis failure with a stable path.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StructuralAnalysisError {
    pub code: StructuralAnalysisErrorCode,
    pub path: String,
    pub message: String,
}

impl StructuralAnalysisError {
    fn new(
        code: StructuralAnalysisErrorCode,
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

/// Ordered failures returned for invalid programs or mismatched fact stores.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StructuralAnalysisErrors {
    pub errors: Vec<StructuralAnalysisError>,
}

impl StructuralAnalysisErrors {
    fn single(error: StructuralAnalysisError) -> Self {
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
                    StructuralAnalysisError::new(
                        structural_code(error.code),
                        error.path,
                        error.message,
                    )
                })
                .collect(),
        }
    }
}

impl fmt::Display for StructuralAnalysisErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} structural analysis error(s)",
            self.errors.len()
        )
    }
}

impl Error for StructuralAnalysisErrors {}

/// Why a first consumed scalar cannot be represented exactly.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum LeadingUnknownReason {
    Backreference { node_id: NodeId },
    NullablePrefix { node_id: NodeId },
    Nullability { node_id: NodeId },
    TermLimitExceeded,
}

/// One target-neutral possibility for the first semantic consumption.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum LeadingTerm {
    Empty,
    Scalar(UnicodeScalar),
    CharacterSet {
        negated: bool,
        members: Vec<CharacterSetMember>,
    },
    Wildcard {
        line_terminators: LineTerminators,
    },
    Unknown(LeadingUnknownReason),
}

/// Deterministic symbolic union of leading-consumption possibilities.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct LeadingConsumption {
    terms: BTreeSet<LeadingTerm>,
}

impl LeadingConsumption {
    /// Iterate possibilities in canonical value order.
    pub fn iter(&self) -> impl ExactSizeIterator<Item = &LeadingTerm> {
        self.terms.iter()
    }

    #[must_use]
    pub fn contains(&self, term: &LeadingTerm) -> bool {
        self.terms.contains(term)
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.terms.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.terms.is_empty()
    }

    fn singleton(term: LeadingTerm) -> Self {
        let mut leading = Self::default();
        leading.insert(term);
        leading
    }

    fn insert(&mut self, term: LeadingTerm) {
        let limit = LeadingTerm::Unknown(LeadingUnknownReason::TermLimitExceeded);
        if self.terms.contains(&term) || self.terms.contains(&limit) {
            return;
        }
        if self.terms.len() < MAX_LEADING_TERMS.saturating_sub(1) {
            self.terms.insert(term);
        } else {
            self.terms.insert(limit);
        }
    }

    fn extend(&mut self, other: &Self) {
        for term in &other.terms {
            self.insert(term.clone());
        }
    }

    fn extend_consuming(&mut self, other: &Self) {
        for term in &other.terms {
            if *term != LeadingTerm::Empty {
                self.insert(term.clone());
            }
        }
    }
}

/// Structural facts associated with one reachable semantic node.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NodeStructuralFacts {
    pub leading_consumption: LeadingConsumption,
}

/// Complete deterministic structural fact store for one canonical program.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StructuralFacts {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    node_facts: BTreeMap<NodeId, NodeStructuralFacts>,
}

impl StructuralFacts {
    #[must_use]
    pub fn get(&self, node_id: &NodeId) -> Option<&NodeStructuralFacts> {
        self.node_facts.get(node_id)
    }

    /// Iterate in canonical stable-node-identity order.
    pub fn iter(&self) -> impl ExactSizeIterator<Item = (&NodeId, &NodeStructuralFacts)> {
        self.node_facts.iter()
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

/// Analyze structural facts for one already-normalized semantic program.
///
/// This pure stage requires certified foundational facts for the exact program.
/// It never invokes normalization or foundational analysis implicitly.
pub fn analyze_structure(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
) -> Result<StructuralFacts, StructuralAnalysisErrors> {
    enforce_depth_limit(&input.root)?;
    input
        .validate()
        .map_err(StructuralAnalysisErrors::from_validation)?;
    validate_foundational_correspondence(input, foundational)?;

    let node_facts = StructureAnalyzer {
        foundational,
        node_facts: BTreeMap::new(),
    }
    .analyze(&input.root)?;

    if node_facts.len() != foundational.len() {
        return Err(StructuralAnalysisErrors::single(
            StructuralAnalysisError::new(
                StructuralAnalysisErrorCode::AnalysisInvariant,
                "$.root",
                "structural analysis did not produce exactly one record per foundational node",
            ),
        ));
    }

    Ok(StructuralFacts {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        node_facts,
    })
}

struct StructureAnalyzer<'a> {
    foundational: &'a SemanticFacts,
    node_facts: BTreeMap<NodeId, NodeStructuralFacts>,
}

impl StructureAnalyzer<'_> {
    fn analyze(
        mut self,
        root: &Node,
    ) -> Result<BTreeMap<NodeId, NodeStructuralFacts>, StructuralAnalysisErrors> {
        self.node(root, "$.root")?;
        Ok(self.node_facts)
    }

    fn node(
        &mut self,
        node: &Node,
        path: &str,
    ) -> Result<LeadingConsumption, StructuralAnalysisErrors> {
        if let Some(facts) = self.node_facts.get(node.node_id()) {
            return Ok(facts.leading_consumption.clone());
        }

        let leading = match node {
            Node::Empty { .. } | Node::Position { .. } => {
                LeadingConsumption::singleton(LeadingTerm::Empty)
            }
            Node::Literal { text, .. } => {
                let Some(first) = text.chars().next() else {
                    return Err(invariant(
                        path,
                        "canonical literal unexpectedly has no scalar",
                    ));
                };
                LeadingConsumption::singleton(LeadingTerm::Scalar(UnicodeScalar::from_char(first)))
            }
            Node::Wildcard {
                line_terminators, ..
            } => LeadingConsumption::singleton(LeadingTerm::Wildcard {
                line_terminators: *line_terminators,
            }),
            Node::CharacterSet {
                negated, members, ..
            } => LeadingConsumption::singleton(LeadingTerm::CharacterSet {
                negated: *negated,
                members: members.clone(),
            }),
            Node::Sequence { items, .. } => {
                let mut children = Vec::with_capacity(items.len());
                for (index, child) in items.iter().enumerate() {
                    children.push((child, self.node(child, &format!("{path}.items[{index}]"))?));
                }
                let mut leading = self.sequence(&children, path)?;
                self.include_empty_or_unknown(node, &mut leading, path)?;
                leading
            }
            Node::Alternation { branches, .. } => {
                let mut leading = LeadingConsumption::default();
                for (index, branch) in branches.iter().enumerate() {
                    let branch_leading = self.node(branch, &format!("{path}.branches[{index}]"))?;
                    leading.extend(&branch_leading);
                }
                leading
            }
            Node::Repeat { body, max, .. } => {
                let body_leading = self.node(body, &format!("{path}.body"))?;
                let mut leading = LeadingConsumption::default();
                if *max != RepetitionMaximum::Bounded(0) {
                    leading.extend(&body_leading);
                }
                self.include_empty_or_unknown(node, &mut leading, path)?;
                leading
            }
            Node::Capture { body, .. } | Node::Atomic { body, .. } => {
                self.node(body, &format!("{path}.body"))?
            }
            Node::Backreference { node_id, .. } => {
                let facts = self
                    .foundational
                    .get(node_id)
                    .ok_or_else(|| missing_fact(path, node_id, "backreference leading analysis"))?;
                if facts.maximum_consumption == MaximumConsumption::Finite(0) {
                    LeadingConsumption::singleton(LeadingTerm::Empty)
                } else {
                    LeadingConsumption::singleton(LeadingTerm::Unknown(
                        LeadingUnknownReason::Backreference {
                            node_id: node_id.clone(),
                        },
                    ))
                }
            }
            Node::Lookaround { body, .. } => {
                self.node(body, &format!("{path}.body"))?;
                LeadingConsumption::singleton(LeadingTerm::Empty)
            }
        };

        if leading.is_empty() {
            return Err(invariant(
                path,
                "structural analysis produced an empty leading-consumption union",
            ));
        }
        if self
            .node_facts
            .insert(
                node.node_id().clone(),
                NodeStructuralFacts {
                    leading_consumption: leading.clone(),
                },
            )
            .is_some()
        {
            return Err(StructuralAnalysisErrors::single(
                StructuralAnalysisError::new(
                    StructuralAnalysisErrorCode::InvalidIdentity,
                    format!("{path}.node_id"),
                    "node identity must be unique during structural analysis",
                ),
            ));
        }
        Ok(leading)
    }

    fn sequence(
        &self,
        children: &[(&Node, LeadingConsumption)],
        path: &str,
    ) -> Result<LeadingConsumption, StructuralAnalysisErrors> {
        let mut leading = LeadingConsumption::default();
        for (child, child_leading) in children {
            leading.extend_consuming(child_leading);
            let facts = self.foundational.get(child.node_id()).ok_or_else(|| {
                missing_fact(path, child.node_id(), "nullable-prefix composition")
            })?;
            match facts.nullability {
                Nullability::Nullable => {}
                Nullability::NonNullable => break,
                Nullability::Unknown => {
                    leading.insert(LeadingTerm::Unknown(LeadingUnknownReason::NullablePrefix {
                        node_id: child.node_id().clone(),
                    }));
                }
            }
        }

        Ok(leading)
    }

    fn include_empty_or_unknown(
        &self,
        node: &Node,
        leading: &mut LeadingConsumption,
        path: &str,
    ) -> Result<(), StructuralAnalysisErrors> {
        let facts = self
            .foundational
            .get(node.node_id())
            .ok_or_else(|| missing_fact(path, node.node_id(), "node nullability"))?;
        match facts.nullability {
            Nullability::Nullable => leading.insert(LeadingTerm::Empty),
            Nullability::NonNullable => {}
            Nullability::Unknown => {
                leading.insert(LeadingTerm::Unknown(LeadingUnknownReason::Nullability {
                    node_id: node.node_id().clone(),
                }))
            }
        }
        Ok(())
    }
}

fn validate_foundational_correspondence(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
) -> Result<(), StructuralAnalysisErrors> {
    if input.contract_version != foundational.contract_version
        || input.specification_version != foundational.specification_version
    {
        return Err(mismatch(
            "$",
            "foundational fact versions do not match the semantic program",
        ));
    }

    let identity = semantic_program_identity(input).map_err(|error| {
        invariant(
            "$",
            format!("semantic program identity could not be derived: {error}"),
        )
    })?;
    if identity != foundational.program_identity() {
        return Err(mismatch(
            "$",
            "foundational facts were not produced for this exact semantic program",
        ));
    }

    let node_ids = input.node_ids();
    for node_id in &node_ids {
        if foundational.get(node_id).is_none() {
            return Err(StructuralAnalysisErrors::single(
                StructuralAnalysisError::new(
                    StructuralAnalysisErrorCode::MissingFoundationalFact,
                    "$.root",
                    format!("foundational fact store omits reachable node {node_id:?}"),
                ),
            ));
        }
    }
    for (node_id, _) in foundational.iter() {
        if !node_ids.contains(node_id) {
            return Err(StructuralAnalysisErrors::single(
                StructuralAnalysisError::new(
                    StructuralAnalysisErrorCode::UnexpectedFoundationalFact,
                    "$.root",
                    format!("foundational fact store contains unreachable node {node_id:?}"),
                ),
            ));
        }
    }

    let mut pending = vec![(&input.root, "$.root".to_owned())];
    while let Some((node, path)) = pending.pop() {
        let facts = foundational
            .get(node.node_id())
            .ok_or_else(|| missing_fact(&path, node.node_id(), "node kind validation"))?;
        if facts.kind != node_kind(node) {
            return Err(StructuralAnalysisErrors::single(
                StructuralAnalysisError::new(
                    StructuralAnalysisErrorCode::FoundationalKindMismatch,
                    format!("{path}.node_id"),
                    "foundational node kind does not match Semantic IR",
                ),
            ));
        }
        push_children_with_paths(node, &path, &mut pending);
    }
    Ok(())
}

fn enforce_depth_limit(root: &Node) -> Result<(), StructuralAnalysisErrors> {
    let mut pending = vec![(root, 1_usize)];
    while let Some((node, depth)) = pending.pop() {
        if depth > MAX_STRUCTURE_DEPTH {
            return Err(StructuralAnalysisErrors::single(
                StructuralAnalysisError::new(
                    StructuralAnalysisErrorCode::DepthLimitExceeded,
                    "$.root",
                    format!(
                        "semantic nesting depth exceeds structural analysis limit of {MAX_STRUCTURE_DEPTH}"
                    ),
                ),
            ));
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

fn push_children_with_paths<'a>(node: &'a Node, path: &str, pending: &mut Vec<(&'a Node, String)>) {
    match node {
        Node::Sequence { items, .. } => pending.extend(
            items
                .iter()
                .enumerate()
                .rev()
                .map(|(index, child)| (child, format!("{path}.items[{index}]"))),
        ),
        Node::Alternation { branches, .. } => pending.extend(
            branches
                .iter()
                .enumerate()
                .rev()
                .map(|(index, child)| (child, format!("{path}.branches[{index}]"))),
        ),
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => pending.push((body, format!("{path}.body"))),
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

fn missing_fact(path: &str, node_id: &NodeId, purpose: &str) -> StructuralAnalysisErrors {
    StructuralAnalysisErrors::single(StructuralAnalysisError::new(
        StructuralAnalysisErrorCode::MissingFoundationalFact,
        format!("{path}.node_id"),
        format!("foundational fact missing for {purpose}: {node_id:?}"),
    ))
}

fn mismatch(path: &str, message: &str) -> StructuralAnalysisErrors {
    StructuralAnalysisErrors::single(StructuralAnalysisError::new(
        StructuralAnalysisErrorCode::MismatchedFoundationalFacts,
        path,
        message,
    ))
}

fn invariant(path: &str, message: impl Into<String>) -> StructuralAnalysisErrors {
    StructuralAnalysisErrors::single(StructuralAnalysisError::new(
        StructuralAnalysisErrorCode::AnalysisInvariant,
        path,
        message,
    ))
}

fn structural_code(code: ValidationCode) -> StructuralAnalysisErrorCode {
    match code {
        ValidationCode::DuplicateIdentity | ValidationCode::InvalidIdentity => {
            StructuralAnalysisErrorCode::InvalidIdentity
        }
        ValidationCode::NonCanonicalOrder | ValidationCode::NonCanonicalStructure => {
            StructuralAnalysisErrorCode::NonCanonicalInput
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
        | ValidationCode::UnresolvedReference
        | ValidationCode::Utf8Boundary => StructuralAnalysisErrorCode::InvalidSemanticStructure,
    }
}
