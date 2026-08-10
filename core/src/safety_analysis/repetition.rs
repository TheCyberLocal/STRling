//! Repetition progress, nested partition, and certified competition proofs.

use crate::semantic::{CharacterSetMember, RepetitionMode};
use crate::structural_analysis::LeadingTerm;

use super::*;

pub(super) fn analyze(
    root: &Node,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) -> Result<(SafetyAnalysis, usize), SafetyAnalysisErrors> {
    Analyzer {
        foundational,
        structural,
        findings: Vec::new(),
        uncertainties: Vec::new(),
    }
    .analyze(root)
}

#[derive(Clone)]
struct RepeatedRegion {
    repetition_node_id: NodeId,
    minimum: u64,
    maximum: RepetitionMaximum,
}

struct Analyzer<'a> {
    foundational: &'a SemanticFacts,
    structural: &'a StructuralFacts,
    findings: Vec<SafetyFinding>,
    uncertainties: Vec<SafetyUncertainty>,
}

impl Analyzer<'_> {
    fn analyze(mut self, root: &Node) -> Result<(SafetyAnalysis, usize), SafetyAnalysisErrors> {
        let mut pending = vec![(root, Vec::new())];
        let mut visited = 0_usize;
        while let Some((node, repeated_regions)) = pending.pop() {
            visited += 1;
            match node {
                Node::Repeat { .. } => {
                    self.repetition_progress(node)?;
                    self.nested_repetitions(node)?;
                }
                Node::Alternation { .. } => {
                    self.repeated_alternation(node, &repeated_regions)?;
                }
                Node::Sequence { .. } => self.repetition_followers(node)?,
                Node::Empty { .. }
                | Node::Literal { .. }
                | Node::Wildcard { .. }
                | Node::CharacterSet { .. }
                | Node::Position { .. }
                | Node::Capture { .. }
                | Node::Backreference { .. }
                | Node::Lookaround { .. }
                | Node::Atomic { .. } => {}
            }
            push_children_with_regions(node, &repeated_regions, &mut pending);
        }
        Ok((
            SafetyAnalysis::from_parts(self.findings, self.uncertainties)?,
            visited,
        ))
    }

    fn repetition_progress(&mut self, node: &Node) -> Result<(), SafetyAnalysisErrors> {
        let Node::Repeat { node_id, body, .. } = node else {
            return Ok(());
        };
        let repetition = self
            .structural
            .get(node_id)
            .and_then(|facts| facts.repetition.as_ref())
            .ok_or_else(|| malformed("repeat lacks certified repetition facts"))?;
        if repetition.extent != RepetitionExtent::Unbounded {
            return Ok(());
        }
        let code = match repetition.operand_progress {
            ProgressClassification::AlwaysConsuming => return Ok(()),
            ProgressClassification::PotentiallyZeroConsuming => {
                SafetyFindingCode::UnboundedNullableRepetition
            }
            ProgressClassification::Indeterminate => {
                SafetyFindingCode::UnboundedIndeterminateProgress
            }
        };
        self.push_finding(SafetyFinding {
            code,
            category: finding_category(code),
            primary_node_id: node_id.clone(),
            evidence_node_ids: canonical_node_ids([node_id, body.node_id()]),
            evidence: SafetyEvidence::RepetitionProgress {
                repetition_node_id: node_id.clone(),
                operand_node_id: body.node_id().clone(),
                extent: repetition.extent,
                progress: repetition.operand_progress,
            },
            proof: SafetyProofStatus::ProvenStructural,
        })
    }

    fn nested_repetitions(&mut self, outer: &Node) -> Result<(), SafetyAnalysisErrors> {
        let Node::Repeat {
            node_id: outer_id,
            body: outer_body,
            mode: outer_mode,
            ..
        } = outer
        else {
            return Ok(());
        };
        let outer_facts = self
            .structural
            .get(outer_id)
            .and_then(|facts| facts.repetition.as_ref())
            .ok_or_else(|| malformed("outer repeat lacks certified repetition facts"))?;
        if outer_facts.extent != RepetitionExtent::Unbounded
            || *outer_mode == RepetitionMode::Possessive
        {
            return Ok(());
        }

        let mut pending = vec![(
            outer_body.as_ref(),
            vec![outer_id.clone(), outer_body.node_id().clone()],
        )];
        while let Some((candidate, path)) = pending.pop() {
            match candidate {
                Node::Repeat {
                    node_id: inner_id,
                    body: inner_body,
                    min: inner_minimum,
                    max: inner_maximum,
                    mode: inner_mode,
                    ..
                } => {
                    if *inner_mode == RepetitionMode::Possessive
                        || !repetition_count_varies(*inner_minimum, *inner_maximum)
                    {
                        continue;
                    }
                    let inner_facts = self
                        .structural
                        .get(inner_id)
                        .ok_or_else(|| malformed("inner repeat lacks structural facts"))?;
                    let repetition = inner_facts
                        .repetition
                        .as_ref()
                        .ok_or_else(|| malformed("inner repeat lacks repetition facts"))?;
                    match repetition.operand_progress {
                        ProgressClassification::AlwaysConsuming => {
                            let operand_facts = self
                                .structural
                                .get(inner_body.node_id())
                                .ok_or_else(|| malformed("inner operand lacks structural facts"))?;
                            if has_concrete_consuming_lead(operand_facts) {
                                self.push_finding(SafetyFinding {
                                    code: SafetyFindingCode::NestedRepetitionOverlap,
                                    category: SafetyFindingCategory::NestedRepetition,
                                    primary_node_id: outer_id.clone(),
                                    evidence_node_ids: canonical_node_ids(
                                        path.iter().chain([inner_body.node_id()]),
                                    ),
                                    evidence: SafetyEvidence::NestedRepetition {
                                        outer_repetition_node_id: outer_id.clone(),
                                        inner_repetition_node_id: inner_id.clone(),
                                        inner_operand_node_id: inner_body.node_id().clone(),
                                        path,
                                        outer_extent: outer_facts.extent,
                                        inner_length: inner_facts.length,
                                        inner_minimum: *inner_minimum,
                                        inner_maximum: *inner_maximum,
                                    },
                                    proof: SafetyProofStatus::ProvenStructural,
                                })?;
                            } else {
                                self.push_nested_uncertainty(
                                    outer_id,
                                    inner_id,
                                    path,
                                    SafetyUncertaintyReason::UnknownLeadingConsumption,
                                )?;
                            }
                        }
                        ProgressClassification::Indeterminate => {
                            self.push_nested_uncertainty(
                                outer_id,
                                inner_id,
                                path,
                                SafetyUncertaintyReason::IndeterminateProgress,
                            )?;
                        }
                        ProgressClassification::PotentiallyZeroConsuming => {}
                    }
                }
                Node::Capture { body, .. } => {
                    let mut child_path = path;
                    child_path.push(body.node_id().clone());
                    pending.push((body, child_path));
                }
                Node::Alternation { branches, .. } => {
                    for branch in branches.iter().rev() {
                        let mut branch_path = path.clone();
                        branch_path.push(branch.node_id().clone());
                        pending.push((branch, branch_path));
                    }
                }
                Node::Empty { .. }
                | Node::Sequence { .. }
                | Node::Literal { .. }
                | Node::Wildcard { .. }
                | Node::CharacterSet { .. }
                | Node::Position { .. }
                | Node::Backreference { .. }
                | Node::Lookaround { .. }
                | Node::Atomic { .. } => {}
            }
        }
        Ok(())
    }

    fn repeated_alternation(
        &mut self,
        node: &Node,
        repeated_regions: &[RepeatedRegion],
    ) -> Result<(), SafetyAnalysisErrors> {
        let Node::Alternation { node_id, .. } = node else {
            return Ok(());
        };
        let relationships = &self
            .structural
            .get(node_id)
            .ok_or_else(|| malformed("alternation lacks structural facts"))?
            .alternation_branch_overlaps;
        for region in repeated_regions {
            for relationship in relationships {
                let relationship_ref = StructuralRelationshipRef {
                    kind: StructuralRelationshipKind::AlternationBranchOverlap,
                    owner_node_id: node_id.clone(),
                    left_node_id: relationship.left_node_id.clone(),
                    right_node_id: relationship.right_node_id.clone(),
                };
                let evidence_node_ids = canonical_node_ids([
                    &region.repetition_node_id,
                    node_id,
                    &relationship.left_node_id,
                    &relationship.right_node_id,
                ]);
                match relationship.relation {
                    OverlapRelation::Disjoint => {}
                    OverlapRelation::Unknown(reason) => {
                        self.push_uncertainty(SafetyUncertainty {
                            code: SafetyUncertaintyCode::RepeatedAlternationNotProven,
                            primary_node_id: node_id.clone(),
                            evidence_node_ids,
                            reason: SafetyUncertaintyReason::StructuralOverlap(reason),
                            evidence: SafetyUncertaintyEvidence::RepeatedAlternation {
                                repetition_node_id: region.repetition_node_id.clone(),
                                alternation_node_id: node_id.clone(),
                                relationship: relationship_ref,
                            },
                        })?;
                    }
                    OverlapRelation::Overlapping => {
                        let left = self
                            .foundational
                            .get(&relationship.left_node_id)
                            .ok_or_else(|| malformed("left branch lacks foundational facts"))?;
                        let right = self
                            .foundational
                            .get(&relationship.right_node_id)
                            .ok_or_else(|| malformed("right branch lacks foundational facts"))?;
                        if left.minimum_consumption == 0 && right.minimum_consumption == 0 {
                            self.push_uncertainty(SafetyUncertainty {
                                code: SafetyUncertaintyCode::RepeatedAlternationNotProven,
                                primary_node_id: node_id.clone(),
                                evidence_node_ids,
                                reason: SafetyUncertaintyReason::NullableOnlyOverlap,
                                evidence: SafetyUncertaintyEvidence::RepeatedAlternation {
                                    repetition_node_id: region.repetition_node_id.clone(),
                                    alternation_node_id: node_id.clone(),
                                    relationship: relationship_ref,
                                },
                            })?;
                        } else {
                            self.push_finding(SafetyFinding {
                                code: SafetyFindingCode::RepeatedAlternationOverlap,
                                category: SafetyFindingCategory::RepeatedAlternation,
                                primary_node_id: node_id.clone(),
                                evidence_node_ids,
                                evidence: SafetyEvidence::RepeatedAlternation {
                                    repetition_node_id: region.repetition_node_id.clone(),
                                    alternation_node_id: node_id.clone(),
                                    left_branch_index: relationship.left_branch_index,
                                    right_branch_index: relationship.right_branch_index,
                                    repetition_minimum: region.minimum,
                                    repetition_maximum: region.maximum,
                                    relationship: relationship_ref,
                                    relation: relationship.relation,
                                },
                                proof: SafetyProofStatus::ProvenStructural,
                            })?;
                        }
                    }
                }
            }
        }
        Ok(())
    }

    fn repetition_followers(&mut self, node: &Node) -> Result<(), SafetyAnalysisErrors> {
        let Node::Sequence { node_id, items, .. } = node else {
            return Ok(());
        };
        let relationships = &self
            .structural
            .get(node_id)
            .ok_or_else(|| malformed("sequence lacks structural facts"))?
            .repetition_follow_overlaps;
        for relationship in relationships {
            let repetition_node = items
                .get(relationship.repetition_index)
                .ok_or_else(|| malformed("follower relationship repetition index is invalid"))?;
            let Node::Repeat { min, max, mode, .. } = repetition_node else {
                return Err(malformed(
                    "follower relationship does not identify a repetition",
                ));
            };
            if *mode == RepetitionMode::Possessive || !repetition_count_varies(*min, *max) {
                continue;
            }
            let repetition = self
                .structural
                .get(&relationship.repetition_node_id)
                .and_then(|facts| facts.repetition.as_ref())
                .ok_or_else(|| malformed("follower repetition lacks structural facts"))?;
            let relationship_ref = StructuralRelationshipRef {
                kind: StructuralRelationshipKind::RepetitionFollowerOverlap,
                owner_node_id: node_id.clone(),
                left_node_id: relationship.operand_node_id.clone(),
                right_node_id: relationship.following_node_id.clone(),
            };
            let evidence_node_ids = canonical_node_ids([
                node_id,
                &relationship.repetition_node_id,
                &relationship.operand_node_id,
                &relationship.following_node_id,
            ]);
            match relationship.relation {
                OverlapRelation::Disjoint => {}
                OverlapRelation::Unknown(reason) => {
                    self.push_follower_uncertainty(
                        node_id,
                        &relationship.repetition_node_id,
                        evidence_node_ids,
                        relationship_ref,
                        SafetyUncertaintyReason::StructuralOverlap(reason),
                    )?;
                }
                OverlapRelation::Overlapping => match repetition.operand_progress {
                    ProgressClassification::AlwaysConsuming => {
                        self.push_finding(SafetyFinding {
                            code: SafetyFindingCode::RepetitionFollowerOverlap,
                            category: SafetyFindingCategory::RepetitionFollowerCompetition,
                            primary_node_id: relationship.repetition_node_id.clone(),
                            evidence_node_ids,
                            evidence: SafetyEvidence::RepetitionFollower {
                                sequence_node_id: node_id.clone(),
                                repetition_node_id: relationship.repetition_node_id.clone(),
                                operand_node_id: relationship.operand_node_id.clone(),
                                follower_node_id: relationship.following_node_id.clone(),
                                repetition_index: relationship.repetition_index,
                                follower_index: relationship.following_index,
                                repetition_minimum: *min,
                                repetition_maximum: *max,
                                extent: repetition.extent,
                                relationship: relationship_ref,
                                relation: relationship.relation,
                            },
                            proof: SafetyProofStatus::ProvenStructural,
                        })?;
                    }
                    ProgressClassification::Indeterminate => {
                        self.push_follower_uncertainty(
                            node_id,
                            &relationship.repetition_node_id,
                            evidence_node_ids,
                            relationship_ref,
                            SafetyUncertaintyReason::IndeterminateProgress,
                        )?;
                    }
                    ProgressClassification::PotentiallyZeroConsuming => {
                        self.push_follower_uncertainty(
                            node_id,
                            &relationship.repetition_node_id,
                            evidence_node_ids,
                            relationship_ref,
                            SafetyUncertaintyReason::NullableOnlyOverlap,
                        )?;
                    }
                },
            }
        }
        Ok(())
    }

    fn push_nested_uncertainty(
        &mut self,
        outer_id: &NodeId,
        inner_id: &NodeId,
        path: Vec<NodeId>,
        reason: SafetyUncertaintyReason,
    ) -> Result<(), SafetyAnalysisErrors> {
        self.push_uncertainty(SafetyUncertainty {
            code: SafetyUncertaintyCode::NestedRepetitionNotProven,
            primary_node_id: outer_id.clone(),
            evidence_node_ids: canonical_node_ids(path.iter()),
            reason,
            evidence: SafetyUncertaintyEvidence::NestedRepetition {
                outer_repetition_node_id: outer_id.clone(),
                inner_repetition_node_id: inner_id.clone(),
                path,
            },
        })
    }

    fn push_follower_uncertainty(
        &mut self,
        sequence_id: &NodeId,
        repetition_id: &NodeId,
        evidence_node_ids: Vec<NodeId>,
        relationship: StructuralRelationshipRef,
        reason: SafetyUncertaintyReason,
    ) -> Result<(), SafetyAnalysisErrors> {
        self.push_uncertainty(SafetyUncertainty {
            code: SafetyUncertaintyCode::RepetitionFollowerNotProven,
            primary_node_id: repetition_id.clone(),
            evidence_node_ids,
            reason,
            evidence: SafetyUncertaintyEvidence::RepetitionFollower {
                sequence_node_id: sequence_id.clone(),
                repetition_node_id: repetition_id.clone(),
                relationship,
            },
        })
    }

    fn push_finding(&mut self, finding: SafetyFinding) -> Result<(), SafetyAnalysisErrors> {
        if self.findings.len() >= MAX_SAFETY_FINDINGS {
            return Err(limit_error(
                SafetyAnalysisErrorCode::FindingLimitExceeded,
                MAX_SAFETY_FINDINGS,
                "positive finding",
            ));
        }
        self.findings.push(finding);
        Ok(())
    }

    fn push_uncertainty(
        &mut self,
        uncertainty: SafetyUncertainty,
    ) -> Result<(), SafetyAnalysisErrors> {
        if self.uncertainties.len() >= MAX_SAFETY_UNCERTAINTIES {
            return Err(limit_error(
                SafetyAnalysisErrorCode::UncertaintyLimitExceeded,
                MAX_SAFETY_UNCERTAINTIES,
                "uncertainty",
            ));
        }
        self.uncertainties.push(uncertainty);
        Ok(())
    }
}

fn push_children_with_regions<'a>(
    node: &'a Node,
    repeated_regions: &[RepeatedRegion],
    pending: &mut Vec<(&'a Node, Vec<RepeatedRegion>)>,
) {
    match node {
        Node::Sequence { items, .. } => {
            for child in items.iter().rev() {
                pending.push((child, repeated_regions.to_vec()));
            }
        }
        Node::Alternation { branches, .. } => {
            for branch in branches.iter().rev() {
                pending.push((branch, repeated_regions.to_vec()));
            }
        }
        Node::Repeat {
            node_id,
            body,
            min,
            max,
            mode,
            ..
        } => {
            let mut body_regions = repeated_regions.to_vec();
            if *mode != RepetitionMode::Possessive && repetition_executes_twice(*max) {
                body_regions.push(RepeatedRegion {
                    repetition_node_id: node_id.clone(),
                    minimum: *min,
                    maximum: *max,
                });
            }
            pending.push((body, body_regions));
        }
        Node::Capture { body, .. } => pending.push((body, repeated_regions.to_vec())),
        Node::Lookaround { body, .. } | Node::Atomic { body, .. } => {
            pending.push((body, Vec::new()));
        }
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => {}
    }
}

fn repetition_executes_twice(maximum: RepetitionMaximum) -> bool {
    match maximum {
        RepetitionMaximum::Bounded(maximum) => maximum >= 2,
        RepetitionMaximum::Unbounded => true,
    }
}

fn repetition_count_varies(minimum: u64, maximum: RepetitionMaximum) -> bool {
    match maximum {
        RepetitionMaximum::Bounded(maximum) => minimum < maximum,
        RepetitionMaximum::Unbounded => true,
    }
}

fn has_concrete_consuming_lead(facts: &crate::structural_analysis::NodeStructuralFacts) -> bool {
    facts.leading_consumption.iter().any(|term| match term {
        LeadingTerm::Scalar(_) | LeadingTerm::Wildcard { .. } => true,
        LeadingTerm::CharacterSet {
            negated: false,
            members,
        } => members.iter().any(|member| {
            matches!(
                member,
                CharacterSetMember::Literal { .. } | CharacterSetMember::Range { .. }
            )
        }),
        LeadingTerm::Empty
        | LeadingTerm::CharacterSet { negated: true, .. }
        | LeadingTerm::Unknown(_) => false,
    })
}

fn canonical_node_ids<'a>(node_ids: impl IntoIterator<Item = &'a NodeId>) -> Vec<NodeId> {
    node_ids
        .into_iter()
        .cloned()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}
