//! Closed proof construction for target-neutral semantic quality diagnostics.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::semantic::{
    AssertionPolarity, CharacterSetMember, LookaroundDirection, Node, PositionKind,
    RepetitionMaximum, RepetitionMode, UnicodeScalar,
};
use crate::semantic_analysis::{MaximumConsumption, SemanticFacts};
use crate::source::{CaptureId, NodeId};
use crate::structural_analysis::StructuralFacts;

/// Maximum proof-backed quality findings produced by one generation.
pub const MAX_QUALITY_FINDINGS: usize = 4_096;

/// Stable proof-backed quality conditions.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityFindingCode {
    ZeroMaximumRepetition,
    RedundantSingleRepetition,
    DuplicateAlternationBranch,
    ContradictoryBoundaryAssertions,
    ContradictoryLookaroundAssertions,
    OverlappingCharacterSetMembers,
    ZeroWidthBackreference,
}

/// Quality domain grouping independent of user-facing severity.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityFindingCategory {
    Unreachable,
    Degenerate,
    Contradiction,
    RedundantOverlap,
    CaptureReference,
}

/// Every quality finding is backed by a complete target-neutral proof.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityProofStatus {
    ProvenSemantic,
}

/// Repetition modes retained by quality evidence.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityRepetitionMode {
    Greedy,
    Lazy,
}

/// Boundary assertions covered by the exact contradiction proof.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityBoundaryKind {
    WordBoundary,
    NotWordBoundary,
}

/// Lookaround direction retained without depending on target syntax.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityLookaroundDirection {
    Ahead,
    Behind,
}

/// Lookaround polarity retained by contradiction evidence.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityAssertionPolarity {
    Positive,
    Negative,
}

/// Explicit character-set members for which intersection is decidable.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum QualityCharacterSetMember {
    Literal {
        value: UnicodeScalar,
    },
    Range {
        start: UnicodeScalar,
        end: UnicodeScalar,
    },
}

/// Typed evidence for one complete quality proof.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum QualityEvidence {
    ZeroMaximumRepetition {
        repetition_node_id: NodeId,
        operand_node_id: NodeId,
        minimum: u64,
        maximum: u64,
    },
    RedundantSingleRepetition {
        repetition_node_id: NodeId,
        operand_node_id: NodeId,
        minimum: u64,
        maximum: u64,
        mode: QualityRepetitionMode,
    },
    DuplicateAlternationBranch {
        alternation_node_id: NodeId,
        first_branch_index: usize,
        first_branch_node_id: NodeId,
        later_branch_index: usize,
        later_branch_node_id: NodeId,
    },
    ContradictoryBoundaryAssertions {
        sequence_node_id: NodeId,
        first_index: usize,
        first_node_id: NodeId,
        first_boundary: QualityBoundaryKind,
        later_index: usize,
        later_node_id: NodeId,
        later_boundary: QualityBoundaryKind,
    },
    ContradictoryLookaroundAssertions {
        sequence_node_id: NodeId,
        first_index: usize,
        first_node_id: NodeId,
        first_body_node_id: NodeId,
        first_polarity: QualityAssertionPolarity,
        later_index: usize,
        later_node_id: NodeId,
        later_body_node_id: NodeId,
        later_polarity: QualityAssertionPolarity,
        direction: QualityLookaroundDirection,
    },
    OverlappingCharacterSetMembers {
        character_set_node_id: NodeId,
        left_member_index: usize,
        left_member: QualityCharacterSetMember,
        right_member_index: usize,
        right_member: QualityCharacterSetMember,
        witness: UnicodeScalar,
    },
    ZeroWidthBackreference {
        backreference_node_id: NodeId,
        capture_id: CaptureId,
        capture_definition_node_id: NodeId,
        capture_body_node_id: NodeId,
        capture_body_maximum: u64,
    },
}

/// One positive quality condition with stable semantic evidence.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct QualityFinding {
    pub code: QualityFindingCode,
    pub category: QualityFindingCategory,
    pub primary_node_id: NodeId,
    pub evidence_node_ids: Vec<NodeId>,
    pub evidence: QualityEvidence,
    pub proof: QualityProofStatus,
}

/// Internal deterministic proof-construction failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum QualityDerivationErrorCode {
    FindingLimitExceeded,
    Invariant,
}

/// Internal deterministic proof-construction failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct QualityDerivationError {
    pub code: QualityDerivationErrorCode,
    pub path: String,
    pub message: String,
}

impl QualityDerivationError {
    fn invariant(path: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: QualityDerivationErrorCode::Invariant,
            path: path.into(),
            message: message.into(),
        }
    }
}

pub(crate) fn derive_quality_findings(
    input: &crate::semantic::SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) -> Result<Vec<QualityFinding>, QualityDerivationError> {
    let mut findings = Vec::new();
    visit_node(
        &input.root,
        "$.root",
        foundational,
        structural,
        &mut findings,
    )?;
    findings.sort();
    findings.dedup();
    Ok(findings)
}

fn visit_node(
    node: &Node,
    path: &str,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    findings: &mut Vec<QualityFinding>,
) -> Result<(), QualityDerivationError> {
    match node {
        Node::Repeat {
            node_id,
            body,
            min,
            max,
            mode,
            ..
        } => {
            if *max == RepetitionMaximum::Bounded(0) {
                push_finding(
                    findings,
                    QualityFinding {
                        code: QualityFindingCode::ZeroMaximumRepetition,
                        category: QualityFindingCategory::Unreachable,
                        primary_node_id: node_id.clone(),
                        evidence_node_ids: canonical_node_ids([
                            node_id.clone(),
                            body.node_id().clone(),
                        ]),
                        evidence: QualityEvidence::ZeroMaximumRepetition {
                            repetition_node_id: node_id.clone(),
                            operand_node_id: body.node_id().clone(),
                            minimum: *min,
                            maximum: 0,
                        },
                        proof: QualityProofStatus::ProvenSemantic,
                    },
                )?;
            } else if *min == 1 && *max == RepetitionMaximum::Bounded(1) {
                let mode = match mode {
                    RepetitionMode::Greedy => Some(QualityRepetitionMode::Greedy),
                    RepetitionMode::Lazy => Some(QualityRepetitionMode::Lazy),
                    RepetitionMode::Possessive => None,
                };
                if let Some(mode) = mode {
                    push_finding(
                        findings,
                        QualityFinding {
                            code: QualityFindingCode::RedundantSingleRepetition,
                            category: QualityFindingCategory::Degenerate,
                            primary_node_id: node_id.clone(),
                            evidence_node_ids: canonical_node_ids([
                                node_id.clone(),
                                body.node_id().clone(),
                            ]),
                            evidence: QualityEvidence::RedundantSingleRepetition {
                                repetition_node_id: node_id.clone(),
                                operand_node_id: body.node_id().clone(),
                                minimum: *min,
                                maximum: 1,
                                mode,
                            },
                            proof: QualityProofStatus::ProvenSemantic,
                        },
                    )?;
                }
            }
            visit_node(
                body,
                &format!("{path}.body"),
                foundational,
                structural,
                findings,
            )?;
        }
        Node::Alternation {
            node_id, branches, ..
        } => {
            let facts = structural.get(node_id).ok_or_else(|| {
                QualityDerivationError::invariant(path, "structural facts omitted an alternation")
            })?;
            for relation in &facts.alternation_branch_overlaps {
                let left = branches.get(relation.left_branch_index).ok_or_else(|| {
                    QualityDerivationError::invariant(
                        path,
                        "structural alternation relationship has an invalid left index",
                    )
                })?;
                let right = branches.get(relation.right_branch_index).ok_or_else(|| {
                    QualityDerivationError::invariant(
                        path,
                        "structural alternation relationship has an invalid right index",
                    )
                })?;
                if semantic_shape(left) == semantic_shape(right) {
                    push_finding(
                        findings,
                        QualityFinding {
                            code: QualityFindingCode::DuplicateAlternationBranch,
                            category: QualityFindingCategory::Unreachable,
                            primary_node_id: right.node_id().clone(),
                            evidence_node_ids: canonical_node_ids([
                                node_id.clone(),
                                left.node_id().clone(),
                                right.node_id().clone(),
                            ]),
                            evidence: QualityEvidence::DuplicateAlternationBranch {
                                alternation_node_id: node_id.clone(),
                                first_branch_index: relation.left_branch_index,
                                first_branch_node_id: left.node_id().clone(),
                                later_branch_index: relation.right_branch_index,
                                later_branch_node_id: right.node_id().clone(),
                            },
                            proof: QualityProofStatus::ProvenSemantic,
                        },
                    )?;
                }
            }
            for (index, branch) in branches.iter().enumerate() {
                visit_node(
                    branch,
                    &format!("{path}.branches[{index}]"),
                    foundational,
                    structural,
                    findings,
                )?;
            }
        }
        Node::Sequence { node_id, items, .. } => {
            find_assertion_contradictions(node_id, items, path, foundational, findings)?;
            for (index, item) in items.iter().enumerate() {
                visit_node(
                    item,
                    &format!("{path}.items[{index}]"),
                    foundational,
                    structural,
                    findings,
                )?;
            }
        }
        Node::CharacterSet {
            node_id, members, ..
        } => find_character_set_overlaps(node_id, members, findings)?,
        Node::Backreference {
            node_id,
            capture_id,
            ..
        } => {
            let resolution = foundational.backreference(node_id).ok_or_else(|| {
                QualityDerivationError::invariant(path, "backreference facts omitted a resolution")
            })?;
            let definition = foundational.capture_definition(capture_id).ok_or_else(|| {
                QualityDerivationError::invariant(
                    path,
                    "backreference capture definition is missing",
                )
            })?;
            let body_facts = foundational.get(&definition.body_node_id).ok_or_else(|| {
                QualityDerivationError::invariant(path, "capture body facts are missing")
            })?;
            if body_facts.maximum_consumption == MaximumConsumption::Finite(0) {
                push_finding(
                    findings,
                    QualityFinding {
                        code: QualityFindingCode::ZeroWidthBackreference,
                        category: QualityFindingCategory::CaptureReference,
                        primary_node_id: node_id.clone(),
                        evidence_node_ids: canonical_node_ids([
                            node_id.clone(),
                            resolution.definition_node_id.clone(),
                            definition.body_node_id.clone(),
                        ]),
                        evidence: QualityEvidence::ZeroWidthBackreference {
                            backreference_node_id: node_id.clone(),
                            capture_id: capture_id.clone(),
                            capture_definition_node_id: resolution.definition_node_id.clone(),
                            capture_body_node_id: definition.body_node_id.clone(),
                            capture_body_maximum: 0,
                        },
                        proof: QualityProofStatus::ProvenSemantic,
                    },
                )?;
            }
        }
        Node::Capture { body, .. } | Node::Lookaround { body, .. } | Node::Atomic { body, .. } => {
            visit_node(
                body,
                &format!("{path}.body"),
                foundational,
                structural,
                findings,
            )?
        }
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::Position { .. } => {}
    }
    Ok(())
}

fn find_assertion_contradictions(
    sequence_node_id: &NodeId,
    items: &[Node],
    path: &str,
    foundational: &SemanticFacts,
    findings: &mut Vec<QualityFinding>,
) -> Result<(), QualityDerivationError> {
    let mut word_boundary: Option<BoundaryCandidate> = None;
    let mut not_word_boundary: Option<BoundaryCandidate> = None;
    let mut lookarounds: BTreeMap<(u8, [u8; 32]), LookaroundGroup<'_>> = BTreeMap::new();

    for (index, item) in items.iter().enumerate() {
        let facts = foundational.get(item.node_id()).ok_or_else(|| {
            QualityDerivationError::invariant(
                format!("{path}.items[{index}]"),
                "foundational facts omitted a sequence item",
            )
        })?;
        if facts.maximum_consumption != MaximumConsumption::Finite(0) {
            word_boundary = None;
            not_word_boundary = None;
            lookarounds.clear();
            continue;
        }

        match item {
            Node::Position {
                node_id,
                position: PositionKind::WordBoundary,
                ..
            } => {
                let current = BoundaryCandidate {
                    index,
                    node_id: node_id.clone(),
                    boundary: QualityBoundaryKind::WordBoundary,
                };
                if let Some(first) = &not_word_boundary {
                    push_boundary_contradiction(findings, sequence_node_id, first, &current)?;
                }
                word_boundary.get_or_insert(current);
            }
            Node::Position {
                node_id,
                position: PositionKind::NotWordBoundary,
                ..
            } => {
                let current = BoundaryCandidate {
                    index,
                    node_id: node_id.clone(),
                    boundary: QualityBoundaryKind::NotWordBoundary,
                };
                if let Some(first) = &word_boundary {
                    push_boundary_contradiction(findings, sequence_node_id, first, &current)?;
                }
                not_word_boundary.get_or_insert(current);
            }
            Node::Lookaround {
                node_id,
                direction,
                polarity,
                body,
                ..
            } => {
                let key = (direction_key(*direction), shape_fingerprint(body)?);
                let group = lookarounds.entry(key).or_default();
                let opposite = match polarity {
                    AssertionPolarity::Positive => group.negative.as_ref(),
                    AssertionPolarity::Negative => group.positive.as_ref(),
                };
                if let Some(first) = opposite {
                    if semantic_shape(first.body) == semantic_shape(body) {
                        let direction = quality_direction(*direction);
                        let later_polarity = quality_polarity(*polarity);
                        push_finding(
                            findings,
                            QualityFinding {
                                code: QualityFindingCode::ContradictoryLookaroundAssertions,
                                category: QualityFindingCategory::Contradiction,
                                primary_node_id: node_id.clone(),
                                evidence_node_ids: canonical_node_ids([
                                    sequence_node_id.clone(),
                                    first.node_id.clone(),
                                    first.body.node_id().clone(),
                                    node_id.clone(),
                                    body.node_id().clone(),
                                ]),
                                evidence: QualityEvidence::ContradictoryLookaroundAssertions {
                                    sequence_node_id: sequence_node_id.clone(),
                                    first_index: first.index,
                                    first_node_id: first.node_id.clone(),
                                    first_body_node_id: first.body.node_id().clone(),
                                    first_polarity: first.polarity,
                                    later_index: index,
                                    later_node_id: node_id.clone(),
                                    later_body_node_id: body.node_id().clone(),
                                    later_polarity,
                                    direction,
                                },
                                proof: QualityProofStatus::ProvenSemantic,
                            },
                        )?;
                    }
                }
                let candidate = LookaroundCandidate {
                    index,
                    node_id: node_id.clone(),
                    body,
                    polarity: quality_polarity(*polarity),
                };
                match polarity {
                    AssertionPolarity::Positive => {
                        group.positive.get_or_insert(candidate);
                    }
                    AssertionPolarity::Negative => {
                        group.negative.get_or_insert(candidate);
                    }
                }
            }
            Node::Empty { .. }
            | Node::Sequence { .. }
            | Node::Alternation { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Repeat { .. }
            | Node::Position { .. }
            | Node::Capture { .. }
            | Node::Backreference { .. }
            | Node::Atomic { .. } => {}
        }
    }
    Ok(())
}

#[derive(Default)]
struct LookaroundGroup<'a> {
    positive: Option<LookaroundCandidate<'a>>,
    negative: Option<LookaroundCandidate<'a>>,
}

struct LookaroundCandidate<'a> {
    index: usize,
    node_id: NodeId,
    body: &'a Node,
    polarity: QualityAssertionPolarity,
}

struct BoundaryCandidate {
    index: usize,
    node_id: NodeId,
    boundary: QualityBoundaryKind,
}

fn push_boundary_contradiction(
    findings: &mut Vec<QualityFinding>,
    sequence_node_id: &NodeId,
    first: &BoundaryCandidate,
    later: &BoundaryCandidate,
) -> Result<(), QualityDerivationError> {
    push_finding(
        findings,
        QualityFinding {
            code: QualityFindingCode::ContradictoryBoundaryAssertions,
            category: QualityFindingCategory::Contradiction,
            primary_node_id: later.node_id.clone(),
            evidence_node_ids: canonical_node_ids([
                sequence_node_id.clone(),
                first.node_id.clone(),
                later.node_id.clone(),
            ]),
            evidence: QualityEvidence::ContradictoryBoundaryAssertions {
                sequence_node_id: sequence_node_id.clone(),
                first_index: first.index,
                first_node_id: first.node_id.clone(),
                first_boundary: first.boundary,
                later_index: later.index,
                later_node_id: later.node_id.clone(),
                later_boundary: later.boundary,
            },
            proof: QualityProofStatus::ProvenSemantic,
        },
    )
}

fn find_character_set_overlaps(
    node_id: &NodeId,
    members: &[CharacterSetMember],
    findings: &mut Vec<QualityFinding>,
) -> Result<(), QualityDerivationError> {
    let literals: Vec<_> = members
        .iter()
        .enumerate()
        .filter_map(|(index, member)| match member {
            CharacterSetMember::Literal { value } => Some((index, *value)),
            _ => None,
        })
        .collect();
    let ranges: Vec<_> = members
        .iter()
        .enumerate()
        .filter_map(|(index, member)| match member {
            CharacterSetMember::Range { start, end } => Some((index, *start, *end)),
            _ => None,
        })
        .collect();

    let mut widest_prior: Option<(usize, UnicodeScalar, UnicodeScalar)> = None;
    for &(index, start, end) in &ranges {
        if let Some((prior_index, prior_start, prior_end)) = widest_prior {
            if prior_end >= start {
                push_set_overlap(
                    findings,
                    node_id,
                    prior_index,
                    QualityCharacterSetMember::Range {
                        start: prior_start,
                        end: prior_end,
                    },
                    index,
                    QualityCharacterSetMember::Range { start, end },
                    start,
                )?;
            }
        }
        if widest_prior.map_or(true, |(_, _, prior_end)| end > prior_end) {
            widest_prior = Some((index, start, end));
        }
    }

    let mut range_cursor = 0_usize;
    let mut containing_range: Option<(usize, UnicodeScalar, UnicodeScalar)> = None;
    for &(literal_index, value) in &literals {
        while range_cursor < ranges.len() && ranges[range_cursor].1 <= value {
            let candidate = ranges[range_cursor];
            if containing_range.map_or(true, |(_, _, end)| candidate.2 > end) {
                containing_range = Some(candidate);
            }
            range_cursor += 1;
        }
        if let Some((range_index, start, end)) = containing_range {
            if end >= value {
                push_set_overlap(
                    findings,
                    node_id,
                    literal_index,
                    QualityCharacterSetMember::Literal { value },
                    range_index,
                    QualityCharacterSetMember::Range { start, end },
                    value,
                )?;
            }
        }
    }
    Ok(())
}

fn push_set_overlap(
    findings: &mut Vec<QualityFinding>,
    node_id: &NodeId,
    left_member_index: usize,
    left_member: QualityCharacterSetMember,
    right_member_index: usize,
    right_member: QualityCharacterSetMember,
    witness: UnicodeScalar,
) -> Result<(), QualityDerivationError> {
    push_finding(
        findings,
        QualityFinding {
            code: QualityFindingCode::OverlappingCharacterSetMembers,
            category: QualityFindingCategory::RedundantOverlap,
            primary_node_id: node_id.clone(),
            evidence_node_ids: vec![node_id.clone()],
            evidence: QualityEvidence::OverlappingCharacterSetMembers {
                character_set_node_id: node_id.clone(),
                left_member_index,
                left_member,
                right_member_index,
                right_member,
                witness,
            },
            proof: QualityProofStatus::ProvenSemantic,
        },
    )
}

fn push_finding(
    findings: &mut Vec<QualityFinding>,
    finding: QualityFinding,
) -> Result<(), QualityDerivationError> {
    if findings.len() >= MAX_QUALITY_FINDINGS {
        return Err(QualityDerivationError {
            code: QualityDerivationErrorCode::FindingLimitExceeded,
            path: "$.quality_findings".to_owned(),
            message: format!(
                "quality finding count exceeds deterministic limit of {MAX_QUALITY_FINDINGS}"
            ),
        });
    }
    findings.push(finding);
    Ok(())
}

fn canonical_node_ids<const N: usize>(node_ids: [NodeId; N]) -> Vec<NodeId> {
    let mut node_ids = node_ids.to_vec();
    node_ids.sort();
    node_ids.dedup();
    node_ids
}

fn direction_key(direction: LookaroundDirection) -> u8 {
    match direction {
        LookaroundDirection::Ahead => 0,
        LookaroundDirection::Behind => 1,
    }
}

fn quality_direction(direction: LookaroundDirection) -> QualityLookaroundDirection {
    match direction {
        LookaroundDirection::Ahead => QualityLookaroundDirection::Ahead,
        LookaroundDirection::Behind => QualityLookaroundDirection::Behind,
    }
}

fn quality_polarity(polarity: AssertionPolarity) -> QualityAssertionPolarity {
    match polarity {
        AssertionPolarity::Positive => QualityAssertionPolarity::Positive,
        AssertionPolarity::Negative => QualityAssertionPolarity::Negative,
    }
}

fn shape_fingerprint(node: &Node) -> Result<[u8; 32], QualityDerivationError> {
    let bytes = serde_json::to_vec(&semantic_shape(node)).map_err(|error| {
        QualityDerivationError::invariant(
            "$.quality_findings",
            format!("semantic shape could not be fingerprinted: {error}"),
        )
    })?;
    Ok(Sha256::digest(bytes).into())
}

fn semantic_shape(node: &Node) -> Value {
    match node {
        Node::Empty { .. } => json!(["empty"]),
        Node::Sequence { items, .. } => json!([
            "sequence",
            items.iter().map(semantic_shape).collect::<Vec<_>>()
        ]),
        Node::Alternation { branches, .. } => json!([
            "alternation",
            branches.iter().map(semantic_shape).collect::<Vec<_>>()
        ]),
        Node::Literal { text, .. } => json!(["literal", text]),
        Node::Wildcard {
            line_terminators, ..
        } => json!(["wildcard", line_terminators]),
        Node::CharacterSet {
            negated, members, ..
        } => json!(["character_set", negated, members]),
        Node::Repeat {
            body,
            min,
            max,
            mode,
            ..
        } => json!(["repeat", min, max, mode, semantic_shape(body)]),
        Node::Position { position, .. } => json!(["position", position]),
        Node::Capture {
            capture_id,
            name,
            body,
            ..
        } => json!(["capture", capture_id, name, semantic_shape(body)]),
        Node::Backreference { capture_id, .. } => json!(["backreference", capture_id]),
        Node::Lookaround {
            direction,
            polarity,
            body,
            ..
        } => json!(["lookaround", direction, polarity, semantic_shape(body)]),
        Node::Atomic { body, .. } => json!(["atomic", semantic_shape(body)]),
    }
}
