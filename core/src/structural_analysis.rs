//! Target-neutral structural facts derived from canonical Semantic IR and
//! certified foundational semantic facts.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::semantic::{
    CaseMatching, CharacterSetMember, LineTerminators, Node, RepetitionMaximum, SemanticProgram,
    UnicodeScalar,
};
use crate::semantic_analysis::{
    semantic_program_identity, Consumption, MaximumConsumption, NodeFacts, Nullability,
    SemanticFacts, SemanticNodeKind, MAX_ANALYSIS_DEPTH,
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

/// Maximum pair relationships materialized for one structural node.
pub const MAX_RELATIONSHIP_PAIRS: usize = 4_096;

/// Maximum symbolic term comparisons used for one overlap decision.
pub const MAX_OVERLAP_COMPARISONS: usize = 4_096;

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
    RelationshipLimitExceeded,
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

/// Semantic successful-consumption length derived from certified bounds.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum LengthClassification {
    Fixed(u64),
    FiniteVariable,
    Unbounded,
    Indeterminate,
}

/// Whether a repetition has a finite structural maximum.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RepetitionExtent {
    Finite,
    Unbounded,
}

/// Whether a repetition operand proves progress on every successful match.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum ProgressClassification {
    AlwaysConsuming,
    PotentiallyZeroConsuming,
    Indeterminate,
}

/// Repetition-only structural facts without a safety interpretation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepetitionStructuralFacts {
    pub body_node_id: NodeId,
    pub extent: RepetitionExtent,
    pub operand_progress: ProgressClassification,
}

/// Why exact leading-consumption overlap could not be decided.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum OverlapUnknownReason {
    LeadingUnknown,
    CaseFolding,
    CharacterCategory,
    LineTerminatorExclusion,
    ComparisonLimitExceeded,
}

/// Conservative relation between two symbolic leading-consumption sets.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum OverlapRelation {
    Disjoint,
    Overlapping,
    Unknown(OverlapUnknownReason),
}

/// One canonical pair of alternatives and their leading-consumption relation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AlternationBranchOverlap {
    pub left_branch_index: usize,
    pub left_node_id: NodeId,
    pub right_branch_index: usize,
    pub right_node_id: NodeId,
    pub relation: OverlapRelation,
}

/// One repeated operand and its immediately following sequence expression.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RepetitionFollowOverlap {
    pub repetition_index: usize,
    pub repetition_node_id: NodeId,
    pub operand_node_id: NodeId,
    pub following_index: usize,
    pub following_node_id: NodeId,
    pub relation: OverlapRelation,
}

/// Structural facts associated with one reachable semantic node.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NodeStructuralFacts {
    pub leading_consumption: LeadingConsumption,
    pub length: LengthClassification,
    pub repetition: Option<RepetitionStructuralFacts>,
    pub alternation_branch_overlaps: Vec<AlternationBranchOverlap>,
    pub repetition_follow_overlaps: Vec<RepetitionFollowOverlap>,
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
        case_matching: input.case_matching,
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
    case_matching: CaseMatching,
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
        let foundational_facts = self
            .foundational
            .get(node.node_id())
            .ok_or_else(|| missing_fact(path, node.node_id(), "length classification"))?;
        let length = classify_length(foundational_facts, path)?;
        let repetition = match node {
            Node::Repeat { body, max, .. } => {
                let body_facts = self.foundational.get(body.node_id()).ok_or_else(|| {
                    missing_fact(path, body.node_id(), "repetition operand progress")
                })?;
                Some(RepetitionStructuralFacts {
                    body_node_id: body.node_id().clone(),
                    extent: match max {
                        RepetitionMaximum::Bounded(_) => RepetitionExtent::Finite,
                        RepetitionMaximum::Unbounded => RepetitionExtent::Unbounded,
                    },
                    operand_progress: classify_progress(body_facts),
                })
            }
            _ => None,
        };
        let alternation_branch_overlaps = match node {
            Node::Alternation { branches, .. } => self.alternation_relationships(branches, path)?,
            _ => Vec::new(),
        };
        let repetition_follow_overlaps = match node {
            Node::Sequence { items, .. } => self.repetition_follow_relationships(items, path)?,
            _ => Vec::new(),
        };
        if self
            .node_facts
            .insert(
                node.node_id().clone(),
                NodeStructuralFacts {
                    leading_consumption: leading.clone(),
                    length,
                    repetition,
                    alternation_branch_overlaps,
                    repetition_follow_overlaps,
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

    fn alternation_relationships(
        &self,
        branches: &[Node],
        path: &str,
    ) -> Result<Vec<AlternationBranchOverlap>, StructuralAnalysisErrors> {
        ensure_pair_limit(branches.len(), path, "alternation branch")?;
        let mut relationships = Vec::new();
        for left_index in 0..branches.len() {
            for right_index in (left_index + 1)..branches.len() {
                let left = &branches[left_index];
                let right = &branches[right_index];
                let left_facts = self
                    .node_facts
                    .get(left.node_id())
                    .ok_or_else(|| invariant(path, "alternation child lacks structural facts"))?;
                let right_facts = self
                    .node_facts
                    .get(right.node_id())
                    .ok_or_else(|| invariant(path, "alternation child lacks structural facts"))?;
                relationships.push(AlternationBranchOverlap {
                    left_branch_index: left_index,
                    left_node_id: left.node_id().clone(),
                    right_branch_index: right_index,
                    right_node_id: right.node_id().clone(),
                    relation: leading_overlap(
                        &left_facts.leading_consumption,
                        &right_facts.leading_consumption,
                        self.case_matching,
                    ),
                });
            }
        }
        Ok(relationships)
    }

    fn repetition_follow_relationships(
        &self,
        items: &[Node],
        path: &str,
    ) -> Result<Vec<RepetitionFollowOverlap>, StructuralAnalysisErrors> {
        let relationship_count = items
            .windows(2)
            .filter(|pair| {
                matches!(
                    &pair[0],
                    Node::Repeat {
                        max,
                        ..
                    } if *max != RepetitionMaximum::Bounded(0)
                )
            })
            .count();
        if relationship_count > MAX_RELATIONSHIP_PAIRS {
            return Err(relationship_limit(path, "repetition/follow"));
        }

        let mut relationships = Vec::with_capacity(relationship_count);
        for (repetition_index, pair) in items.windows(2).enumerate() {
            let Node::Repeat {
                node_id, body, max, ..
            } = &pair[0]
            else {
                continue;
            };
            if *max == RepetitionMaximum::Bounded(0) {
                continue;
            }
            let following = &pair[1];
            let operand_facts = self
                .node_facts
                .get(body.node_id())
                .ok_or_else(|| invariant(path, "repetition operand lacks structural facts"))?;
            let following_facts = self
                .node_facts
                .get(following.node_id())
                .ok_or_else(|| invariant(path, "following expression lacks structural facts"))?;
            relationships.push(RepetitionFollowOverlap {
                repetition_index,
                repetition_node_id: node_id.clone(),
                operand_node_id: body.node_id().clone(),
                following_index: repetition_index + 1,
                following_node_id: following.node_id().clone(),
                relation: leading_overlap(
                    &operand_facts.leading_consumption,
                    &following_facts.leading_consumption,
                    self.case_matching,
                ),
            });
        }
        Ok(relationships)
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

/// Compare two symbolic leading-consumption unions conservatively.
///
/// `Disjoint` is returned only when every represented pair is provably
/// disjoint under the canonical program's case-matching semantics.
#[must_use]
pub fn leading_overlap(
    left: &LeadingConsumption,
    right: &LeadingConsumption,
    case_matching: CaseMatching,
) -> OverlapRelation {
    let mut comparisons = 0_usize;
    let mut unknown: Option<OverlapUnknownReason> = None;
    for left_term in left.iter() {
        for right_term in right.iter() {
            comparisons = comparisons.saturating_add(1);
            if comparisons > MAX_OVERLAP_COMPARISONS {
                return OverlapRelation::Unknown(OverlapUnknownReason::ComparisonLimitExceeded);
            }
            match term_overlap(left_term, right_term, case_matching) {
                OverlapRelation::Overlapping => return OverlapRelation::Overlapping,
                OverlapRelation::Unknown(reason) => {
                    unknown = Some(unknown.map_or(reason, |current| current.min(reason)));
                }
                OverlapRelation::Disjoint => {}
            }
        }
    }
    unknown.map_or(OverlapRelation::Disjoint, OverlapRelation::Unknown)
}

fn term_overlap(
    left: &LeadingTerm,
    right: &LeadingTerm,
    case_matching: CaseMatching,
) -> OverlapRelation {
    match (left, right) {
        (LeadingTerm::Empty, LeadingTerm::Empty) => OverlapRelation::Overlapping,
        (LeadingTerm::Unknown(_), _) | (_, LeadingTerm::Unknown(_)) => {
            OverlapRelation::Unknown(OverlapUnknownReason::LeadingUnknown)
        }
        (LeadingTerm::Empty, _) | (_, LeadingTerm::Empty) => OverlapRelation::Disjoint,
        (LeadingTerm::Scalar(left), LeadingTerm::Scalar(right)) => {
            if left == right {
                OverlapRelation::Overlapping
            } else if case_matching == CaseMatching::Sensitive {
                OverlapRelation::Disjoint
            } else {
                OverlapRelation::Unknown(OverlapUnknownReason::CaseFolding)
            }
        }
        (LeadingTerm::Scalar(value), LeadingTerm::CharacterSet { negated, members })
        | (LeadingTerm::CharacterSet { negated, members }, LeadingTerm::Scalar(value)) => {
            scalar_set_overlap(*value, *negated, members, case_matching)
        }
        (
            LeadingTerm::CharacterSet {
                negated: left_negated,
                members: left_members,
            },
            LeadingTerm::CharacterSet {
                negated: right_negated,
                members: right_members,
            },
        ) => set_overlap(
            *left_negated,
            left_members,
            *right_negated,
            right_members,
            case_matching,
        ),
        (LeadingTerm::Wildcard { .. }, LeadingTerm::Wildcard { .. }) => {
            OverlapRelation::Overlapping
        }
        (LeadingTerm::Wildcard { line_terminators }, LeadingTerm::Scalar(_))
        | (LeadingTerm::Scalar(_), LeadingTerm::Wildcard { line_terminators }) => {
            if *line_terminators == LineTerminators::Include {
                OverlapRelation::Overlapping
            } else {
                OverlapRelation::Unknown(OverlapUnknownReason::LineTerminatorExclusion)
            }
        }
        (
            LeadingTerm::Wildcard { line_terminators },
            LeadingTerm::CharacterSet { negated, members },
        )
        | (
            LeadingTerm::CharacterSet { negated, members },
            LeadingTerm::Wildcard { line_terminators },
        ) => wildcard_set_overlap(*line_terminators, *negated, members),
    }
}

#[derive(Debug)]
struct CharacterSetModel {
    intervals: Vec<(u32, u32)>,
    has_symbolic_members: bool,
}

fn scalar_set_overlap(
    value: UnicodeScalar,
    negated: bool,
    members: &[CharacterSetMember],
    case_matching: CaseMatching,
) -> OverlapRelation {
    let model = character_set_model(members);
    let contained = interval_contains(&model.intervals, u32::from(value.get()));
    if !negated && contained || negated && !contained && !model.has_symbolic_members {
        if contained || case_matching == CaseMatching::Sensitive {
            OverlapRelation::Overlapping
        } else {
            OverlapRelation::Unknown(OverlapUnknownReason::CaseFolding)
        }
    } else if negated && contained {
        OverlapRelation::Disjoint
    } else if model.has_symbolic_members {
        OverlapRelation::Unknown(OverlapUnknownReason::CharacterCategory)
    } else if case_matching == CaseMatching::Sensitive {
        OverlapRelation::Disjoint
    } else {
        OverlapRelation::Unknown(OverlapUnknownReason::CaseFolding)
    }
}

fn wildcard_set_overlap(
    line_terminators: LineTerminators,
    negated: bool,
    members: &[CharacterSetMember],
) -> OverlapRelation {
    if line_terminators == LineTerminators::Exclude {
        return OverlapRelation::Unknown(OverlapUnknownReason::LineTerminatorExclusion);
    }
    let model = character_set_model(members);
    if !negated && !model.intervals.is_empty() {
        OverlapRelation::Overlapping
    } else {
        OverlapRelation::Unknown(OverlapUnknownReason::CharacterCategory)
    }
}

fn set_overlap(
    left_negated: bool,
    left_members: &[CharacterSetMember],
    right_negated: bool,
    right_members: &[CharacterSetMember],
    case_matching: CaseMatching,
) -> OverlapRelation {
    let left = character_set_model(left_members);
    let right = character_set_model(right_members);
    match (left_negated, right_negated) {
        (false, false) => {
            if intervals_intersect(&left.intervals, &right.intervals) {
                OverlapRelation::Overlapping
            } else if left.has_symbolic_members || right.has_symbolic_members {
                OverlapRelation::Unknown(OverlapUnknownReason::CharacterCategory)
            } else if case_matching == CaseMatching::Sensitive {
                OverlapRelation::Disjoint
            } else {
                OverlapRelation::Unknown(OverlapUnknownReason::CaseFolding)
            }
        }
        (false, true) => positive_negative_overlap(&left, &right, case_matching),
        (true, false) => positive_negative_overlap(&right, &left, case_matching),
        (true, true) => OverlapRelation::Unknown(OverlapUnknownReason::CharacterCategory),
    }
}

fn positive_negative_overlap(
    positive: &CharacterSetModel,
    excluded: &CharacterSetModel,
    case_matching: CaseMatching,
) -> OverlapRelation {
    if !excluded.has_symbolic_members && !intervals_subset(&positive.intervals, &excluded.intervals)
    {
        if case_matching == CaseMatching::Sensitive {
            return OverlapRelation::Overlapping;
        }
        return OverlapRelation::Unknown(OverlapUnknownReason::CaseFolding);
    }
    if !positive.has_symbolic_members && intervals_subset(&positive.intervals, &excluded.intervals)
    {
        return OverlapRelation::Disjoint;
    }
    OverlapRelation::Unknown(OverlapUnknownReason::CharacterCategory)
}

fn character_set_model(members: &[CharacterSetMember]) -> CharacterSetModel {
    let mut intervals = Vec::new();
    let mut has_symbolic_members = false;
    for member in members {
        match member {
            CharacterSetMember::Literal { value } => {
                let value = u32::from(value.get());
                intervals.push((value, value));
            }
            CharacterSetMember::Range { start, end } => {
                intervals.push((u32::from(start.get()), u32::from(end.get())));
            }
            CharacterSetMember::Builtin { .. } | CharacterSetMember::UnicodeProperty { .. } => {
                has_symbolic_members = true;
            }
        }
    }
    intervals.sort_unstable();
    let mut merged: Vec<(u32, u32)> = Vec::with_capacity(intervals.len());
    for (start, end) in intervals {
        match merged.last_mut() {
            Some((_, previous_end)) if start <= previous_end.saturating_add(1) => {
                *previous_end = (*previous_end).max(end);
            }
            _ => merged.push((start, end)),
        }
    }
    CharacterSetModel {
        intervals: merged,
        has_symbolic_members,
    }
}

fn interval_contains(intervals: &[(u32, u32)], value: u32) -> bool {
    intervals
        .iter()
        .any(|(start, end)| *start <= value && value <= *end)
}

fn intervals_intersect(left: &[(u32, u32)], right: &[(u32, u32)]) -> bool {
    let mut left_index = 0;
    let mut right_index = 0;
    while left_index < left.len() && right_index < right.len() {
        let left_interval = left[left_index];
        let right_interval = right[right_index];
        if left_interval.0 <= right_interval.1 && right_interval.0 <= left_interval.1 {
            return true;
        }
        if left_interval.1 < right_interval.1 {
            left_index += 1;
        } else {
            right_index += 1;
        }
    }
    false
}

fn intervals_subset(subset: &[(u32, u32)], superset: &[(u32, u32)]) -> bool {
    let mut superset_index = 0;
    for (subset_start, subset_end) in subset {
        while superset_index < superset.len() && superset[superset_index].1 < *subset_start {
            superset_index += 1;
        }
        if superset_index == superset.len()
            || superset[superset_index].0 > *subset_start
            || superset[superset_index].1 < *subset_end
        {
            return false;
        }
    }
    true
}

fn ensure_pair_limit(
    item_count: usize,
    path: &str,
    relationship: &str,
) -> Result<(), StructuralAnalysisErrors> {
    let pair_count = item_count
        .checked_mul(item_count.saturating_sub(1))
        .map(|value| value / 2)
        .ok_or_else(|| relationship_limit(path, relationship))?;
    if pair_count > MAX_RELATIONSHIP_PAIRS {
        Err(relationship_limit(path, relationship))
    } else {
        Ok(())
    }
}

fn relationship_limit(path: &str, relationship: &str) -> StructuralAnalysisErrors {
    StructuralAnalysisErrors::single(StructuralAnalysisError::new(
        StructuralAnalysisErrorCode::RelationshipLimitExceeded,
        path,
        format!(
            "{relationship} relationship count exceeds deterministic limit {MAX_RELATIONSHIP_PAIRS}"
        ),
    ))
}

fn classify_length(
    facts: &NodeFacts,
    path: &str,
) -> Result<LengthClassification, StructuralAnalysisErrors> {
    match facts.maximum_consumption {
        MaximumConsumption::Finite(maximum) => match facts.minimum_consumption.cmp(&maximum) {
            std::cmp::Ordering::Equal => Ok(LengthClassification::Fixed(maximum)),
            std::cmp::Ordering::Less => Ok(LengthClassification::FiniteVariable),
            std::cmp::Ordering::Greater => Err(invariant(
                path,
                "foundational minimum consumption exceeds finite maximum",
            )),
        },
        MaximumConsumption::Unbounded => {
            if facts.consumption == Consumption::Indeterminate {
                Ok(LengthClassification::Indeterminate)
            } else {
                Ok(LengthClassification::Unbounded)
            }
        }
    }
}

fn classify_progress(facts: &NodeFacts) -> ProgressClassification {
    if facts.minimum_consumption > 0 {
        ProgressClassification::AlwaysConsuming
    } else if facts.nullability == Nullability::Nullable
        || matches!(
            facts.consumption,
            Consumption::AlwaysZeroWidth | Consumption::Variable
        )
    {
        ProgressClassification::PotentiallyZeroConsuming
    } else {
        ProgressClassification::Indeterminate
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
