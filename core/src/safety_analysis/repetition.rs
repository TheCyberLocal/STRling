//! Repetition progress and transparent nested-repetition proofs.

use crate::semantic::{CharacterSetMember, RepetitionMode};
use crate::structural_analysis::LeadingTerm;

use super::*;

pub(super) fn analyze(
    root: &Node,
    structural: &StructuralFacts,
) -> Result<(SafetyAnalysis, usize), SafetyAnalysisErrors> {
    Analyzer {
        structural,
        findings: Vec::new(),
        uncertainties: Vec::new(),
    }
    .analyze(root)
}

struct Analyzer<'a> {
    structural: &'a StructuralFacts,
    findings: Vec<SafetyFinding>,
    uncertainties: Vec<SafetyUncertainty>,
}

impl Analyzer<'_> {
    fn analyze(mut self, root: &Node) -> Result<(SafetyAnalysis, usize), SafetyAnalysisErrors> {
        let mut pending = vec![root];
        let mut visited = 0_usize;
        while let Some(node) = pending.pop() {
            visited += 1;
            if matches!(node, Node::Repeat { .. }) {
                self.repetition_progress(node)?;
                self.nested_repetitions(node)?;
            }
            push_children(node, &mut pending);
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
