//! Structured target-neutral safety evidence derived from certified semantic
//! and structural facts.

use std::collections::BTreeSet;
use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::semantic::{Node, RepetitionMaximum, SemanticProgram};
use crate::semantic_analysis::{
    semantic_program_identity, SemanticFacts, SemanticNodeKind, MAX_ANALYSIS_DEPTH,
};
use crate::source::NodeId;
use crate::structural_analysis::{
    LengthClassification, OverlapRelation, OverlapUnknownReason, ProgressClassification,
    RepetitionExtent, StructuralFacts,
};
use crate::validation::{Validate, ValidationCode, ValidationErrors};

mod repetition;

/// Maximum semantic nodes accepted by one safety-analysis invocation.
pub const MAX_SAFETY_NODES: usize = 65_536;

/// Maximum positive findings returned by one safety-analysis invocation.
pub const MAX_SAFETY_FINDINGS: usize = 4_096;

/// Maximum uncertainty records returned by one safety-analysis invocation.
pub const MAX_SAFETY_UNCERTAINTIES: usize = 4_096;

/// Stable positive semantic-safety conditions.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SafetyFindingCode {
    UnboundedNullableRepetition,
    UnboundedIndeterminateProgress,
    NestedRepetitionOverlap,
    RepeatedAlternationOverlap,
    RepetitionFollowerOverlap,
}

/// Domain grouping independent of user-facing diagnostic severity.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SafetyFindingCategory {
    RepetitionProgress,
    NestedRepetition,
    RepeatedAlternation,
    RepetitionFollowerCompetition,
}

/// Positive findings are emitted only for a complete structural proof.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SafetyProofStatus {
    ProvenStructural,
}

/// Stable structural relationship kinds referenced by safety evidence.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum StructuralRelationshipKind {
    AlternationBranchOverlap,
    RepetitionFollowerOverlap,
}

/// Stable identity for one already-certified structural relationship.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StructuralRelationshipRef {
    pub kind: StructuralRelationshipKind,
    pub owner_node_id: NodeId,
    pub left_node_id: NodeId,
    pub right_node_id: NodeId,
}

/// Typed proof data for a positive finding.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum SafetyEvidence {
    RepetitionProgress {
        repetition_node_id: NodeId,
        operand_node_id: NodeId,
        extent: RepetitionExtent,
        progress: ProgressClassification,
    },
    NestedRepetition {
        outer_repetition_node_id: NodeId,
        inner_repetition_node_id: NodeId,
        inner_operand_node_id: NodeId,
        path: Vec<NodeId>,
        outer_extent: RepetitionExtent,
        inner_length: LengthClassification,
        inner_minimum: u64,
        inner_maximum: RepetitionMaximum,
    },
    RepeatedAlternation {
        repetition_node_id: NodeId,
        alternation_node_id: NodeId,
        left_branch_index: usize,
        right_branch_index: usize,
        repetition_minimum: u64,
        repetition_maximum: RepetitionMaximum,
        relationship: StructuralRelationshipRef,
        relation: OverlapRelation,
    },
    RepetitionFollower {
        sequence_node_id: NodeId,
        repetition_node_id: NodeId,
        operand_node_id: NodeId,
        follower_node_id: NodeId,
        repetition_index: usize,
        follower_index: usize,
        repetition_minimum: u64,
        repetition_maximum: RepetitionMaximum,
        extent: RepetitionExtent,
        relationship: StructuralRelationshipRef,
        relation: OverlapRelation,
    },
}

/// One positive structural condition with stable semantic evidence.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SafetyFinding {
    pub code: SafetyFindingCode,
    pub category: SafetyFindingCategory,
    pub primary_node_id: NodeId,
    pub evidence_node_ids: Vec<NodeId>,
    pub evidence: SafetyEvidence,
    pub proof: SafetyProofStatus,
}

/// Stable classes of safety questions left unresolved.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SafetyUncertaintyCode {
    NestedRepetitionNotProven,
    RepeatedAlternationNotProven,
    RepetitionFollowerNotProven,
}

/// Certified reason a positive structural proof could not be completed.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(tag = "kind", content = "detail", rename_all = "snake_case")]
pub enum SafetyUncertaintyReason {
    IndeterminateProgress,
    UnknownLeadingConsumption,
    NullableOnlyOverlap,
    StructuralOverlap(OverlapUnknownReason),
}

/// Typed context for one unresolved safety question.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum SafetyUncertaintyEvidence {
    NestedRepetition {
        outer_repetition_node_id: NodeId,
        inner_repetition_node_id: NodeId,
        path: Vec<NodeId>,
    },
    RepeatedAlternation {
        repetition_node_id: NodeId,
        alternation_node_id: NodeId,
        relationship: StructuralRelationshipRef,
    },
    RepetitionFollower {
        sequence_node_id: NodeId,
        repetition_node_id: NodeId,
        relationship: StructuralRelationshipRef,
    },
}

/// One applicable but unproved target-neutral safety conclusion.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SafetyUncertainty {
    pub code: SafetyUncertaintyCode,
    pub primary_node_id: NodeId,
    pub evidence_node_ids: Vec<NodeId>,
    pub reason: SafetyUncertaintyReason,
    pub evidence: SafetyUncertaintyEvidence,
}

/// Deterministic semantic-safety output for one canonical program.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SafetyAnalysis {
    findings: Vec<SafetyFinding>,
    uncertainties: Vec<SafetyUncertainty>,
}

impl SafetyAnalysis {
    /// Iterate positive findings in canonical value order.
    pub fn findings(&self) -> impl ExactSizeIterator<Item = &SafetyFinding> {
        self.findings.iter()
    }

    /// Iterate unresolved conclusions in canonical value order.
    pub fn uncertainties(&self) -> impl ExactSizeIterator<Item = &SafetyUncertainty> {
        self.uncertainties.iter()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.findings.is_empty() && self.uncertainties.is_empty()
    }

    fn from_parts(
        mut findings: Vec<SafetyFinding>,
        mut uncertainties: Vec<SafetyUncertainty>,
    ) -> Result<Self, SafetyAnalysisErrors> {
        if findings.len() > MAX_SAFETY_FINDINGS {
            return Err(limit_error(
                SafetyAnalysisErrorCode::FindingLimitExceeded,
                MAX_SAFETY_FINDINGS,
                "positive finding",
            ));
        }
        if uncertainties.len() > MAX_SAFETY_UNCERTAINTIES {
            return Err(limit_error(
                SafetyAnalysisErrorCode::UncertaintyLimitExceeded,
                MAX_SAFETY_UNCERTAINTIES,
                "uncertainty",
            ));
        }
        findings.sort_unstable();
        findings.dedup();
        uncertainties.sort_unstable();
        uncertainties.dedup();
        Ok(Self {
            findings,
            uncertainties,
        })
    }
}

/// Stable categories for safety-analysis failure.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SafetyAnalysisErrorCode {
    InvalidSemanticStructure,
    InvalidIdentity,
    NonCanonicalInput,
    DepthLimitExceeded,
    NodeLimitExceeded,
    FindingLimitExceeded,
    UncertaintyLimitExceeded,
    MismatchedSemanticFacts,
    MismatchedStructuralFacts,
    MissingSemanticFact,
    UnexpectedSemanticFact,
    MissingStructuralFact,
    UnexpectedStructuralFact,
    MalformedStructuralFact,
    MalformedEvidenceReference,
    AnalysisInvariant,
}

/// One machine-classifiable safety-analysis failure with a stable data path.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SafetyAnalysisError {
    pub code: SafetyAnalysisErrorCode,
    pub path: String,
    pub message: String,
}

impl SafetyAnalysisError {
    fn new(
        code: SafetyAnalysisErrorCode,
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

/// Ordered failures returned for invalid programs, facts, or evidence.
#[derive(Clone, Debug, Default, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SafetyAnalysisErrors {
    pub errors: Vec<SafetyAnalysisError>,
}

impl SafetyAnalysisErrors {
    fn single(error: SafetyAnalysisError) -> Self {
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
                    SafetyAnalysisError::new(safety_code(error.code), error.path, error.message)
                })
                .collect(),
        }
    }
}

impl fmt::Display for SafetyAnalysisErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} semantic safety analysis error(s)",
            self.errors.len()
        )
    }
}

impl Error for SafetyAnalysisErrors {}

/// Analyze structured safety evidence for one normalized semantic program.
///
/// This stage consumes only the exact certified foundational and structural
/// stores supplied by the caller. It never reconstructs either prerequisite.
pub fn analyze_safety(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) -> Result<SafetyAnalysis, SafetyAnalysisErrors> {
    enforce_resource_limits(&input.root)?;
    input
        .validate()
        .map_err(SafetyAnalysisErrors::from_validation)?;
    validate_foundational_correspondence(input, foundational)?;
    validate_structural_correspondence(input, structural)?;

    let (analysis, visited) = repetition::analyze(&input.root, foundational, structural)?;
    if visited != structural.len() || visited != foundational.len() {
        return Err(invariant(
            "$.root",
            "bounded traversal did not visit exactly one record per certified node",
        ));
    }

    validate_analysis(input, structural, &analysis)?;
    Ok(analysis)
}

fn validate_foundational_correspondence(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
) -> Result<(), SafetyAnalysisErrors> {
    if input.contract_version != foundational.contract_version
        || input.specification_version != foundational.specification_version
    {
        return Err(stage_error(
            SafetyAnalysisErrorCode::MismatchedSemanticFacts,
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
        return Err(stage_error(
            SafetyAnalysisErrorCode::MismatchedSemanticFacts,
            "foundational facts were not produced for this exact semantic program",
        ));
    }

    let node_ids = input.node_ids();
    for node_id in &node_ids {
        if foundational.get(node_id).is_none() {
            return Err(stage_error(
                SafetyAnalysisErrorCode::MissingSemanticFact,
                format!("foundational fact store omits reachable node {node_id:?}"),
            ));
        }
    }
    for (node_id, _) in foundational.iter() {
        if !node_ids.contains(node_id) {
            return Err(stage_error(
                SafetyAnalysisErrorCode::UnexpectedSemanticFact,
                format!("foundational fact store contains unreachable node {node_id:?}"),
            ));
        }
    }

    let mut pending = vec![&input.root];
    while let Some(node) = pending.pop() {
        let facts = foundational.get(node.node_id()).ok_or_else(|| {
            stage_error(
                SafetyAnalysisErrorCode::MissingSemanticFact,
                "reachable node lacks foundational facts",
            )
        })?;
        if facts.kind != node_kind(node) {
            return Err(stage_error(
                SafetyAnalysisErrorCode::MismatchedSemanticFacts,
                "foundational node kind does not match Semantic IR",
            ));
        }
        push_children(node, &mut pending);
    }
    Ok(())
}

fn validate_structural_correspondence(
    input: &SemanticProgram,
    structural: &StructuralFacts,
) -> Result<(), SafetyAnalysisErrors> {
    if input.contract_version != structural.contract_version
        || input.specification_version != structural.specification_version
    {
        return Err(stage_error(
            SafetyAnalysisErrorCode::MismatchedStructuralFacts,
            "structural fact versions do not match the semantic program",
        ));
    }
    let identity = semantic_program_identity(input).map_err(|error| {
        invariant(
            "$",
            format!("semantic program identity could not be derived: {error}"),
        )
    })?;
    if identity != structural.program_identity() {
        return Err(stage_error(
            SafetyAnalysisErrorCode::MismatchedStructuralFacts,
            "structural facts were not produced for this exact semantic program",
        ));
    }

    let node_ids = input.node_ids();
    for node_id in &node_ids {
        if structural.get(node_id).is_none() {
            return Err(stage_error(
                SafetyAnalysisErrorCode::MissingStructuralFact,
                format!("structural fact store omits reachable node {node_id:?}"),
            ));
        }
    }
    for (node_id, _) in structural.iter() {
        if !node_ids.contains(node_id) {
            return Err(stage_error(
                SafetyAnalysisErrorCode::UnexpectedStructuralFact,
                format!("structural fact store contains unreachable node {node_id:?}"),
            ));
        }
    }

    let mut pending = vec![&input.root];
    while let Some(node) = pending.pop() {
        validate_structural_node(node, structural, &node_ids)?;
        push_children(node, &mut pending);
    }
    Ok(())
}

fn validate_structural_node(
    node: &Node,
    structural: &StructuralFacts,
    node_ids: &BTreeSet<NodeId>,
) -> Result<(), SafetyAnalysisErrors> {
    let facts = structural.get(node.node_id()).ok_or_else(|| {
        stage_error(
            SafetyAnalysisErrorCode::MissingStructuralFact,
            "reachable node lacks structural facts",
        )
    })?;

    match node {
        Node::Repeat { body, .. } => match &facts.repetition {
            Some(repetition) if repetition.body_node_id == *body.node_id() => {}
            _ => {
                return Err(malformed(
                    "repeat structural record has an invalid operand reference",
                ))
            }
        },
        _ if facts.repetition.is_some() => {
            return Err(malformed(
                "non-repeat structural record contains repetition facts",
            ));
        }
        _ => {}
    }

    match node {
        Node::Alternation { branches, .. } => {
            let mut relationship_index = 0_usize;
            for left_index in 0..branches.len() {
                for right_index in (left_index + 1)..branches.len() {
                    let relationship = facts
                        .alternation_branch_overlaps
                        .get(relationship_index)
                        .ok_or_else(|| malformed("alternation relationships are incomplete"))?;
                    if relationship.left_branch_index != left_index
                        || relationship.right_branch_index != right_index
                        || relationship.left_node_id != *branches[left_index].node_id()
                        || relationship.right_node_id != *branches[right_index].node_id()
                    {
                        return Err(malformed(
                            "alternation relationship identity or order is malformed",
                        ));
                    }
                    relationship_index += 1;
                }
            }
            if relationship_index != facts.alternation_branch_overlaps.len() {
                return Err(malformed("alternation relationships contain extras"));
            }
        }
        _ if !facts.alternation_branch_overlaps.is_empty() => {
            return Err(malformed(
                "non-alternation structural record contains branch relationships",
            ));
        }
        _ => {}
    }

    match node {
        Node::Sequence { items, .. } => {
            let mut relationship_index = 0_usize;
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
                let relationship = facts
                    .repetition_follow_overlaps
                    .get(relationship_index)
                    .ok_or_else(|| malformed("repetition/follower relationships are incomplete"))?;
                if relationship.repetition_index != repetition_index
                    || relationship.following_index != repetition_index + 1
                    || relationship.repetition_node_id != *node_id
                    || relationship.operand_node_id != *body.node_id()
                    || relationship.following_node_id != *pair[1].node_id()
                {
                    return Err(malformed(
                        "repetition/follower relationship identity or order is malformed",
                    ));
                }
                relationship_index += 1;
            }
            if relationship_index != facts.repetition_follow_overlaps.len() {
                return Err(malformed(
                    "repetition/follower relationships contain extras",
                ));
            }
        }
        _ if !facts.repetition_follow_overlaps.is_empty() => {
            return Err(malformed(
                "non-sequence structural record contains follower relationships",
            ));
        }
        _ => {}
    }

    for relationship in &facts.alternation_branch_overlaps {
        if !node_ids.contains(&relationship.left_node_id)
            || !node_ids.contains(&relationship.right_node_id)
        {
            return Err(malformed(
                "alternation relationship references an unknown node",
            ));
        }
    }
    for relationship in &facts.repetition_follow_overlaps {
        if !node_ids.contains(&relationship.repetition_node_id)
            || !node_ids.contains(&relationship.operand_node_id)
            || !node_ids.contains(&relationship.following_node_id)
        {
            return Err(malformed(
                "follower relationship references an unknown node",
            ));
        }
    }
    Ok(())
}

fn validate_analysis(
    input: &SemanticProgram,
    structural: &StructuralFacts,
    analysis: &SafetyAnalysis,
) -> Result<(), SafetyAnalysisErrors> {
    if analysis.findings.len() > MAX_SAFETY_FINDINGS {
        return Err(limit_error(
            SafetyAnalysisErrorCode::FindingLimitExceeded,
            MAX_SAFETY_FINDINGS,
            "positive finding",
        ));
    }
    if analysis.uncertainties.len() > MAX_SAFETY_UNCERTAINTIES {
        return Err(limit_error(
            SafetyAnalysisErrorCode::UncertaintyLimitExceeded,
            MAX_SAFETY_UNCERTAINTIES,
            "uncertainty",
        ));
    }
    if !analysis.findings.windows(2).all(|pair| pair[0] < pair[1]) {
        return Err(evidence_error(
            "positive findings are not unique canonical order",
        ));
    }
    if !analysis
        .uncertainties
        .windows(2)
        .all(|pair| pair[0] < pair[1])
    {
        return Err(evidence_error(
            "uncertainty records are not unique canonical order",
        ));
    }

    let node_ids = input.node_ids();
    for finding in &analysis.findings {
        validate_evidence_ids(
            &node_ids,
            &finding.primary_node_id,
            &finding.evidence_node_ids,
        )?;
        if finding.category != finding_category(finding.code)
            || finding.proof != SafetyProofStatus::ProvenStructural
        {
            return Err(evidence_error(
                "finding code, category, or proof status is malformed",
            ));
        }
        validate_finding_evidence(input, structural, finding)?;
    }
    for uncertainty in &analysis.uncertainties {
        validate_evidence_ids(
            &node_ids,
            &uncertainty.primary_node_id,
            &uncertainty.evidence_node_ids,
        )?;
    }
    Ok(())
}

fn validate_finding_evidence(
    input: &SemanticProgram,
    structural: &StructuralFacts,
    finding: &SafetyFinding,
) -> Result<(), SafetyAnalysisErrors> {
    match (&finding.code, &finding.evidence) {
        (
            SafetyFindingCode::UnboundedNullableRepetition
            | SafetyFindingCode::UnboundedIndeterminateProgress,
            SafetyEvidence::RepetitionProgress {
                repetition_node_id,
                operand_node_id,
                extent,
                progress,
            },
        ) => {
            if finding.primary_node_id != *repetition_node_id {
                return Err(evidence_error(
                    "progress finding primary identity is malformed",
                ));
            }
            let repetition = find_node(&input.root, repetition_node_id)
                .ok_or_else(|| evidence_error("progress finding repetition does not resolve"))?;
            let Node::Repeat { body, .. } = repetition else {
                return Err(evidence_error(
                    "progress finding primary is not a repetition",
                ));
            };
            let facts = structural
                .get(repetition_node_id)
                .and_then(|facts| facts.repetition.as_ref())
                .ok_or_else(|| evidence_error("progress finding lacks repetition facts"))?;
            if *operand_node_id != *body.node_id()
                || *operand_node_id != facts.body_node_id
                || *extent != facts.extent
                || *progress != facts.operand_progress
            {
                return Err(evidence_error(
                    "progress finding contradicts structural facts",
                ));
            }
        }
        (SafetyFindingCode::NestedRepetitionOverlap, SafetyEvidence::NestedRepetition { .. })
        | (
            SafetyFindingCode::RepeatedAlternationOverlap,
            SafetyEvidence::RepeatedAlternation { .. },
        )
        | (
            SafetyFindingCode::RepetitionFollowerOverlap,
            SafetyEvidence::RepetitionFollower { .. },
        ) => {}
        _ => {
            return Err(evidence_error(
                "finding code does not match its typed evidence",
            ))
        }
    }
    Ok(())
}

fn validate_evidence_ids(
    node_ids: &BTreeSet<NodeId>,
    primary: &NodeId,
    evidence: &[NodeId],
) -> Result<(), SafetyAnalysisErrors> {
    if !node_ids.contains(primary) || evidence.iter().any(|node_id| !node_ids.contains(node_id)) {
        return Err(evidence_error(
            "safety evidence references an unknown semantic node",
        ));
    }
    if evidence.is_empty()
        || !evidence.windows(2).all(|pair| pair[0] < pair[1])
        || evidence.binary_search(primary).is_err()
    {
        return Err(evidence_error(
            "evidence node identities must be unique canonical order and include the primary",
        ));
    }
    Ok(())
}

fn enforce_resource_limits(root: &Node) -> Result<(), SafetyAnalysisErrors> {
    let mut pending = vec![(root, 1_usize)];
    let mut nodes = 0_usize;
    while let Some((node, depth)) = pending.pop() {
        if depth > MAX_ANALYSIS_DEPTH {
            return Err(stage_error(
                SafetyAnalysisErrorCode::DepthLimitExceeded,
                format!(
                    "semantic nesting depth exceeds safety analysis limit of {MAX_ANALYSIS_DEPTH}"
                ),
            ));
        }
        nodes = nodes.saturating_add(1);
        if nodes > MAX_SAFETY_NODES {
            return Err(limit_error(
                SafetyAnalysisErrorCode::NodeLimitExceeded,
                MAX_SAFETY_NODES,
                "semantic node",
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

fn find_node<'a>(root: &'a Node, node_id: &NodeId) -> Option<&'a Node> {
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        if node.node_id() == node_id {
            return Some(node);
        }
        push_children(node, &mut pending);
    }
    None
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

fn finding_category(code: SafetyFindingCode) -> SafetyFindingCategory {
    match code {
        SafetyFindingCode::UnboundedNullableRepetition
        | SafetyFindingCode::UnboundedIndeterminateProgress => {
            SafetyFindingCategory::RepetitionProgress
        }
        SafetyFindingCode::NestedRepetitionOverlap => SafetyFindingCategory::NestedRepetition,
        SafetyFindingCode::RepeatedAlternationOverlap => SafetyFindingCategory::RepeatedAlternation,
        SafetyFindingCode::RepetitionFollowerOverlap => {
            SafetyFindingCategory::RepetitionFollowerCompetition
        }
    }
}

fn stage_error(code: SafetyAnalysisErrorCode, message: impl Into<String>) -> SafetyAnalysisErrors {
    SafetyAnalysisErrors::single(SafetyAnalysisError::new(code, "$.root", message))
}

fn malformed(message: &str) -> SafetyAnalysisErrors {
    stage_error(SafetyAnalysisErrorCode::MalformedStructuralFact, message)
}

fn evidence_error(message: &str) -> SafetyAnalysisErrors {
    stage_error(SafetyAnalysisErrorCode::MalformedEvidenceReference, message)
}

fn limit_error(
    code: SafetyAnalysisErrorCode,
    limit: usize,
    resource: &str,
) -> SafetyAnalysisErrors {
    stage_error(
        code,
        format!("{resource} count exceeds deterministic limit {limit}"),
    )
}

fn invariant(path: &str, message: impl Into<String>) -> SafetyAnalysisErrors {
    SafetyAnalysisErrors::single(SafetyAnalysisError::new(
        SafetyAnalysisErrorCode::AnalysisInvariant,
        path,
        message,
    ))
}

fn safety_code(code: ValidationCode) -> SafetyAnalysisErrorCode {
    match code {
        ValidationCode::DuplicateIdentity | ValidationCode::InvalidIdentity => {
            SafetyAnalysisErrorCode::InvalidIdentity
        }
        ValidationCode::NonCanonicalOrder | ValidationCode::NonCanonicalStructure => {
            SafetyAnalysisErrorCode::NonCanonicalInput
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
        | ValidationCode::Utf8Boundary => SafetyAnalysisErrorCode::InvalidSemanticStructure,
    }
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use super::*;
    use crate::semantic_analysis::analyze;
    use crate::structural_analysis::analyze_structure;

    fn literal_program() -> SemanticProgram {
        serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": "sensitive",
            "root": {"node_id": "node:safety.literal", "kind": "literal", "text": "a"}
        }))
        .expect("test program must deserialize")
    }

    #[test]
    fn incomplete_structural_coverage_is_rejected() {
        let semantic = literal_program();
        let foundational = analyze(&semantic).expect("foundational facts");
        let mut structural = analyze_structure(&semantic, &foundational).expect("structural facts");
        structural.remove_node_for_test(semantic.root.node_id());

        let errors = analyze_safety(&semantic, &foundational, &structural)
            .expect_err("incomplete structural facts must fail");
        assert_eq!(
            errors.errors[0].code,
            SafetyAnalysisErrorCode::MissingStructuralFact
        );
    }

    #[test]
    fn result_parts_are_sorted_and_deduplicated() {
        let semantic = literal_program();
        let make = |code| SafetyFinding {
            code,
            category: finding_category(code),
            primary_node_id: semantic.root.node_id().clone(),
            evidence_node_ids: vec![semantic.root.node_id().clone()],
            evidence: SafetyEvidence::RepetitionProgress {
                repetition_node_id: semantic.root.node_id().clone(),
                operand_node_id: semantic.root.node_id().clone(),
                extent: RepetitionExtent::Unbounded,
                progress: ProgressClassification::Indeterminate,
            },
            proof: SafetyProofStatus::ProvenStructural,
        };
        let lower = make(SafetyFindingCode::UnboundedNullableRepetition);
        let higher = make(SafetyFindingCode::UnboundedIndeterminateProgress);

        let analysis =
            SafetyAnalysis::from_parts(vec![higher.clone(), lower.clone(), higher], Vec::new())
                .expect("bounded parts must assemble");
        assert_eq!(
            analysis.findings,
            vec![
                lower,
                make(SafetyFindingCode::UnboundedIndeterminateProgress)
            ]
        );
    }

    #[test]
    fn malformed_evidence_reference_is_rejected() {
        let semantic = literal_program();
        let foundational = analyze(&semantic).expect("foundational facts");
        let structural = analyze_structure(&semantic, &foundational).expect("structural facts");
        let analysis = SafetyAnalysis {
            findings: vec![SafetyFinding {
                code: SafetyFindingCode::UnboundedNullableRepetition,
                category: SafetyFindingCategory::RepetitionProgress,
                primary_node_id: semantic.root.node_id().clone(),
                evidence_node_ids: vec![semantic.root.node_id().clone()],
                evidence: SafetyEvidence::RepetitionProgress {
                    repetition_node_id: semantic.root.node_id().clone(),
                    operand_node_id: semantic.root.node_id().clone(),
                    extent: RepetitionExtent::Unbounded,
                    progress: ProgressClassification::PotentiallyZeroConsuming,
                },
                proof: SafetyProofStatus::ProvenStructural,
            }],
            uncertainties: Vec::new(),
        };

        let errors = validate_analysis(&semantic, &structural, &analysis)
            .expect_err("literal cannot support repetition evidence");
        assert_eq!(
            errors.errors[0].code,
            SafetyAnalysisErrorCode::MalformedEvidenceReference
        );
    }

    #[test]
    fn result_limit_is_a_structured_error() {
        let semantic = literal_program();
        let foundational = analyze(&semantic).expect("foundational facts");
        let structural = analyze_structure(&semantic, &foundational).expect("structural facts");
        let invalid = SafetyAnalysis {
            findings: Vec::new(),
            uncertainties: vec![
                SafetyUncertainty {
                    code: SafetyUncertaintyCode::NestedRepetitionNotProven,
                    primary_node_id: semantic.root.node_id().clone(),
                    evidence_node_ids: vec![semantic.root.node_id().clone()],
                    reason: SafetyUncertaintyReason::UnknownLeadingConsumption,
                    evidence: SafetyUncertaintyEvidence::NestedRepetition {
                        outer_repetition_node_id: semantic.root.node_id().clone(),
                        inner_repetition_node_id: semantic.root.node_id().clone(),
                        path: vec![semantic.root.node_id().clone()],
                    },
                };
                MAX_SAFETY_UNCERTAINTIES + 1
            ],
        };

        let errors = validate_analysis(&semantic, &structural, &invalid)
            .expect_err("oversized uncertainty output must fail");
        assert_eq!(
            errors.errors[0].code,
            SafetyAnalysisErrorCode::UncertaintyLimitExceeded
        );
    }
}
