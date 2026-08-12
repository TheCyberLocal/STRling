use std::collections::{BTreeMap, BTreeSet};

use super::*;

impl PortabilityPlan {
    /// Validate decision completeness, evidence soundness, aggregation, and
    /// rewrite dependency integrity without consulting any external state.
    pub fn validate(&self) -> Result<(), PortabilityPlanningErrors> {
        if self.decisions.windows(2).any(|pair| {
            pair[0].identity >= pair[1].identity || pair[0].requirement >= pair[1].requirement
        }) {
            return Err(error(
                PortabilityPlanningErrorCode::RequirementOrderMismatch,
                "$.decisions",
                "planned requirements must be unique and canonically ordered",
            ));
        }

        for (index, decision) in self.decisions.iter().enumerate() {
            if decision.identity.ordinal != index as u32
                || decision.identity.node_id != decision.requirement.node_id
                || decision.identity.capability_id != decision.requirement.capability_id
            {
                return Err(error(
                    PortabilityPlanningErrorCode::RequirementResultMismatch,
                    format!("$.decisions[{index}].identity"),
                    "planning identity does not match its semantic requirement",
                ));
            }
            validate_disposition(self, decision, index)?;
        }

        let expected_unresolved: Vec<_> = self
            .decisions
            .iter()
            .filter(|decision| {
                matches!(
                    decision.disposition,
                    RequirementPlanningDisposition::Unresolved(_)
                )
            })
            .map(|decision| decision.identity.clone())
            .collect();
        if self.unresolved_requirements != expected_unresolved {
            return Err(error(
                PortabilityPlanningErrorCode::AggregateStatusMismatch,
                "$.unresolved_requirements",
                "unresolved requirement index does not match per-requirement decisions",
            ));
        }

        let expected_dependencies = collect_rewrite_dependencies(&self.decisions);
        if self.rewrite_dependencies != expected_dependencies {
            return Err(error(
                PortabilityPlanningErrorCode::RewriteDependencyMissing,
                "$.rewrite_dependencies",
                "program rewrite dependencies do not match per-rewrite dependency evidence",
            ));
        }
        validate_dependency_graph(self)?;

        let expected_status = aggregate_status(&self.decisions);
        if self.status != expected_status {
            return Err(error(
                PortabilityPlanningErrorCode::AggregateStatusMismatch,
                "$.status",
                "overall portability status does not match complete per-requirement evidence",
            ));
        }
        Ok(())
    }
}

pub(super) fn aggregate_status(decisions: &[PlannedRequirement]) -> Option<PortabilityStatus> {
    if decisions.iter().any(|decision| {
        matches!(
            decision.disposition,
            RequirementPlanningDisposition::Unresolved(_)
        )
    }) {
        None
    } else if decisions.iter().any(|decision| {
        matches!(
            decision.disposition,
            RequirementPlanningDisposition::Unsupported(_)
        )
    }) {
        Some(PortabilityStatus::Unsupported)
    } else if decisions.iter().any(|decision| {
        matches!(
            decision.disposition,
            RequirementPlanningDisposition::EquivalentRewrite(_)
        )
    }) {
        Some(PortabilityStatus::EquivalentRewrite)
    } else {
        Some(PortabilityStatus::Native)
    }
}

pub(super) fn collect_rewrite_dependencies(
    decisions: &[PlannedRequirement],
) -> Vec<RewriteDependency> {
    let mut dependencies = Vec::new();
    for decision in decisions {
        if let RequirementPlanningDisposition::EquivalentRewrite(rewrite) = &decision.disposition {
            dependencies.extend(rewrite.rewrite_plan.dependencies.iter().cloned().map(
                |prerequisite| RewriteDependency {
                    prerequisite,
                    dependent: decision.identity.clone(),
                },
            ));
        }
    }
    dependencies.sort();
    dependencies.dedup();
    dependencies
}

fn validate_disposition(
    plan: &PortabilityPlan,
    decision: &PlannedRequirement,
    index: usize,
) -> Result<(), PortabilityPlanningErrors> {
    match &decision.disposition {
        RequirementPlanningDisposition::Native(native) => {
            validate_capability_result(plan, decision, &native.capability_result, index)?;
            if native.capability_result.disposition != CapabilityDisposition::Supported {
                return Err(evidence_error(
                    index,
                    "native decision requires Supported evidence",
                ));
            }
        }
        RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
            validate_capability_result(plan, decision, &rewrite.capability_result, index)?;
            if !matches!(
                rewrite.capability_result.disposition,
                CapabilityDisposition::Unsupported | CapabilityDisposition::ConstraintViolation
            ) {
                return Err(evidence_error(
                    index,
                    "equivalent rewrite requires explicit native insufficiency",
                ));
            }
            validate_rewrite_plan(plan, decision, &rewrite.rewrite_plan, index)?;
        }
        RequirementPlanningDisposition::Unsupported(unsupported) => {
            validate_capability_result(plan, decision, &unsupported.capability_result, index)?;
            if !matches!(
                unsupported.capability_result.disposition,
                CapabilityDisposition::Unsupported | CapabilityDisposition::ConstraintViolation
            ) {
                return Err(evidence_error(
                    index,
                    "unsupported decision requires explicit negative capability evidence",
                ));
            }
            validate_attempts(&unsupported.rewrite_attempts, index)?;
            if unsupported.rewrite_attempts.iter().any(|attempt| {
                matches!(
                    attempt.disposition,
                    RewriteAttemptDisposition::Applicable
                        | RewriteAttemptDisposition::ProofIndeterminate
                        | RewriteAttemptDisposition::ReplacementUnknown
                )
            }) {
                return Err(evidence_error(
                    index,
                    "unsupported decision cannot conceal an applicable or indeterminate rewrite",
                ));
            }
        }
        RequirementPlanningDisposition::Unresolved(unresolved) => {
            validate_capability_result(plan, decision, &unresolved.capability_result, index)?;
            match unresolved.reason {
                UnresolvedPlanningReason::CapabilityUnknown => {
                    if unresolved.capability_result.disposition != CapabilityDisposition::Unknown {
                        return Err(evidence_error(
                            index,
                            "capability-unknown evidence requires factual Unknown",
                        ));
                    }
                }
                UnresolvedPlanningReason::RewriteProofIndeterminate => {
                    if !unresolved.rewrite_attempts.iter().any(|attempt| {
                        attempt.disposition == RewriteAttemptDisposition::ProofIndeterminate
                    }) {
                        return Err(evidence_error(
                            index,
                            "indeterminate rewrite proof reason requires matching attempt evidence",
                        ));
                    }
                }
                UnresolvedPlanningReason::ReplacementCapabilityUnknown => {
                    if !unresolved.rewrite_attempts.iter().any(|attempt| {
                        attempt.disposition == RewriteAttemptDisposition::ReplacementUnknown
                    }) {
                        return Err(evidence_error(
                            index,
                            "unknown replacement support reason requires matching attempt evidence",
                        ));
                    }
                }
            }
            if unresolved.reason != UnresolvedPlanningReason::CapabilityUnknown {
                validate_attempts(&unresolved.rewrite_attempts, index)?;
            }
        }
    }
    Ok(())
}

fn validate_capability_result(
    plan: &PortabilityPlan,
    decision: &PlannedRequirement,
    result: &CapabilityResult,
    index: usize,
) -> Result<(), PortabilityPlanningErrors> {
    if result.requirement != decision.requirement
        || result.node_id != decision.requirement.node_id
        || result.evaluated_capability != decision.requirement.capability_id
        || result.target_profile != plan.target_profile
    {
        return Err(evidence_error(
            index,
            "decision capability evidence does not match requirement and target profile",
        ));
    }
    Ok(())
}

fn validate_rewrite_plan(
    plan: &PortabilityPlan,
    decision: &PlannedRequirement,
    rewrite: &SemanticRewritePlan,
    index: usize,
) -> Result<(), PortabilityPlanningErrors> {
    let expected_certification =
        equivalence::certification_for(rewrite.strategy_id).map_err(registry_error)?;
    if rewrite.certification != expected_certification
        || rewrite.original_requirement != decision.requirement
        || rewrite.target_profile != plan.target_profile
        || rewrite.affected_node_ids.is_empty()
        || !rewrite
            .affected_node_ids
            .contains(&decision.requirement.node_id)
        || rewrite
            .affected_node_ids
            .windows(2)
            .any(|pair| pair[0] >= pair[1])
    {
        return Err(rewrite_error(
            index,
            "rewrite identity or affected nodes are malformed",
        ));
    }
    if rewrite.proof.is_empty()
        || rewrite
            .proof
            .iter()
            .any(|proof| proof.disposition != RewriteProofDisposition::Satisfied)
        || rewrite
            .proof
            .windows(2)
            .any(|pair| pair[0].precondition >= pair[1].precondition)
    {
        return Err(rewrite_error(
            index,
            "equivalent rewrite requires unique ordered satisfied proof conditions",
        ));
    }
    if rewrite
        .replacement_requirements
        .windows(2)
        .any(|pair| pair[0] >= pair[1])
        || rewrite.replacement_requirements.len() != rewrite.replacement_support.len()
    {
        return Err(rewrite_error(
            index,
            "replacement requirements and support evidence are incomplete",
        ));
    }
    for (requirement, support) in rewrite
        .replacement_requirements
        .iter()
        .zip(&rewrite.replacement_support)
    {
        if support.requirement != *requirement
            || support.capability_result.requirement != *requirement
            || support.capability_result.target_profile != plan.target_profile
            || support.capability_result.disposition != CapabilityDisposition::Supported
        {
            return Err(rewrite_error(
                index,
                "replacement requirement lacks exact Supported capability evidence",
            ));
        }
    }
    if rewrite
        .dependencies
        .windows(2)
        .any(|pair| pair[0] >= pair[1])
        || rewrite.dependencies.contains(&decision.identity)
    {
        return Err(rewrite_error(
            index,
            "rewrite dependencies must be unique, sorted, and non-self-referential",
        ));
    }
    Ok(())
}

fn validate_attempts(
    attempts: &[RewriteAttempt],
    index: usize,
) -> Result<(), PortabilityPlanningErrors> {
    let expected = certified_rewrite_registry()
        .map_err(registry_error)?
        .strategy_ids();
    if attempts.len() != expected.len()
        || attempts
            .iter()
            .map(|attempt| attempt.strategy_id)
            .ne(expected)
    {
        return Err(rewrite_error(
            index,
            "rewrite attempts must cover the complete certified registry in stable order",
        ));
    }
    Ok(())
}

fn validate_dependency_graph(plan: &PortabilityPlan) -> Result<(), PortabilityPlanningErrors> {
    let rewrite_ids: BTreeSet<_> = plan
        .decisions
        .iter()
        .filter(|decision| {
            matches!(
                decision.disposition,
                RequirementPlanningDisposition::EquivalentRewrite(_)
            )
        })
        .map(|decision| decision.identity.clone())
        .collect();
    let mut indegree: BTreeMap<_, usize> = rewrite_ids
        .iter()
        .cloned()
        .map(|identity| (identity, 0))
        .collect();
    let mut outgoing: BTreeMap<RequirementIdentity, Vec<RequirementIdentity>> = BTreeMap::new();

    for dependency in &plan.rewrite_dependencies {
        if dependency.prerequisite == dependency.dependent
            || !rewrite_ids.contains(&dependency.prerequisite)
            || !rewrite_ids.contains(&dependency.dependent)
        {
            return Err(error(
                PortabilityPlanningErrorCode::RewriteDependencyMissing,
                "$.rewrite_dependencies",
                "rewrite dependency endpoints must identify distinct equivalent rewrites",
            ));
        }
        *indegree
            .get_mut(&dependency.dependent)
            .expect("validated dependent must exist") += 1;
        outgoing
            .entry(dependency.prerequisite.clone())
            .or_default()
            .push(dependency.dependent.clone());
    }

    let mut ready: BTreeSet<_> = indegree
        .iter()
        .filter(|(_, count)| **count == 0)
        .map(|(identity, _)| identity.clone())
        .collect();
    let mut visited = 0;
    while let Some(identity) = ready.pop_first() {
        visited += 1;
        if let Some(dependents) = outgoing.get(&identity) {
            for dependent in dependents {
                let count = indegree
                    .get_mut(dependent)
                    .expect("validated dependent must exist");
                *count -= 1;
                if *count == 0 {
                    ready.insert(dependent.clone());
                }
            }
        }
    }
    if visited != rewrite_ids.len() {
        return Err(error(
            PortabilityPlanningErrorCode::RewriteDependencyCycle,
            "$.rewrite_dependencies",
            "rewrite dependency graph contains a cycle",
        ));
    }
    Ok(())
}

fn evidence_error(index: usize, message: &str) -> PortabilityPlanningErrors {
    error(
        PortabilityPlanningErrorCode::CapabilityEvidenceMismatch,
        format!("$.decisions[{index}]"),
        message,
    )
}

fn rewrite_error(index: usize, message: &str) -> PortabilityPlanningErrors {
    error(
        PortabilityPlanningErrorCode::MalformedRewritePlan,
        format!("$.decisions[{index}].rewrite_plan"),
        message,
    )
}

fn error(
    code: PortabilityPlanningErrorCode,
    path: impl Into<String>,
    message: impl Into<String>,
) -> PortabilityPlanningErrors {
    PortabilityPlanningErrors::single(PortabilityPlanningError::new(code, path, message))
}
