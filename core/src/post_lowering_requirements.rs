//! Reconciliation of source requirements with capability-bearing target output.
//!
//! Target-specific extractors supply typed requirements from their structured
//! lowering trees. This module owns the target-independent union, exact-profile
//! evaluation, fail-closed disposition, and deterministic introduced identity.

use std::collections::BTreeMap;
use std::error::Error;
use std::fmt;

use crate::capability_evaluation::{
    evaluate_additional_requirements, CapabilityDisposition, SemanticRequirement,
    MAX_CAPABILITY_REQUIREMENTS,
};
use crate::portability_planning::RequirementIdentity;
use crate::source::{ContractVersion, NodeId, SpecificationVersion};
use crate::target::{CapabilityId, TargetProfile};

/// One capability occurrence found in structured target output.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct EmittedRequirement {
    pub requirement: SemanticRequirement,
    pub construct: &'static str,
}

/// One emitted-only requirement accepted by the exact target profile.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct IntroducedRequirement {
    pub identity: RequirementIdentity,
}

/// Stable fail-closed categories for post-lowering capability evaluation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PostLoweringRequirementFailureKind {
    InvalidProfile,
    Unsupported,
    ConstraintViolation,
    Unknown,
    RequirementLimitExceeded,
}

/// Structured evidence explaining why a lowered artifact cannot be emitted.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PostLoweringRequirementFailure {
    pub kind: PostLoweringRequirementFailureKind,
    pub node_id: Option<NodeId>,
    pub capability_id: Option<CapabilityId>,
    pub construct: Option<&'static str>,
    pub profile_id: String,
    pub profile_version: String,
    pub disposition: Option<CapabilityDisposition>,
    pub reason: String,
}

impl fmt::Display for PostLoweringRequirementFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        if let (Some(node_id), Some(capability_id), Some(construct), Some(disposition)) = (
            &self.node_id,
            &self.capability_id,
            self.construct,
            self.disposition,
        ) {
            return write!(
                formatter,
                "semantic node {} lowers through {construct}, which requires {}; exact target {} revision {} evaluates that capability as {disposition:?}, so the artifact cannot be emitted",
                node_id.as_str(),
                capability_id.as_str(),
                self.profile_id,
                self.profile_version,
            );
        }
        write!(
            formatter,
            "post-lowering requirements cannot be evaluated for exact target {} revision {}: {}",
            self.profile_id, self.profile_version, self.reason
        )
    }
}

impl Error for PostLoweringRequirementFailure {}

/// Evaluate and return only requirements introduced by lowering.
///
/// Source requirements remain authoritative semantic evidence. An emitted
/// requirement with the same node/capability pair is already represented by
/// that source occurrence. Every other emitted requirement is evaluated by the
/// common capability evaluator and receives a deterministic ordinal after the
/// complete source sequence.
pub(crate) fn reconcile_emitted_requirements(
    contract_version: ContractVersion,
    specification_version: &SpecificationVersion,
    target: &TargetProfile,
    source_requirement_count: usize,
    native_source_requirements: &[RequirementIdentity],
    emitted_requirements: Vec<EmittedRequirement>,
) -> Result<Vec<IntroducedRequirement>, Box<PostLoweringRequirementFailure>> {
    let emitted = classify_introduced_requirements(
        source_requirement_count,
        native_source_requirements,
        emitted_requirements,
    )
    .ok_or_else(|| Box::new(limit_failure(target)))?;

    let requirements: Vec<_> = emitted
        .iter()
        .map(|item| item.requirement.clone())
        .collect();
    let results = evaluate_additional_requirements(
        contract_version,
        specification_version,
        &requirements,
        target,
    )
    .map_err(|errors| {
        Box::new(PostLoweringRequirementFailure {
            kind: PostLoweringRequirementFailureKind::InvalidProfile,
            node_id: None,
            capability_id: None,
            construct: None,
            profile_id: target.profile_id.as_str().to_owned(),
            profile_version: target.profile_version.as_str().to_owned(),
            disposition: None,
            reason: errors.to_string(),
        })
    })?;

    let mut introduced = Vec::with_capacity(results.len());
    for (index, (emitted, result)) in emitted.into_iter().zip(results).enumerate() {
        if result.disposition != CapabilityDisposition::Supported {
            let kind = match result.disposition {
                CapabilityDisposition::Unsupported => {
                    PostLoweringRequirementFailureKind::Unsupported
                }
                CapabilityDisposition::ConstraintViolation => {
                    PostLoweringRequirementFailureKind::ConstraintViolation
                }
                CapabilityDisposition::Unknown => PostLoweringRequirementFailureKind::Unknown,
                CapabilityDisposition::Supported => unreachable!("guard rejects supported"),
            };
            return Err(Box::new(PostLoweringRequirementFailure {
                kind,
                node_id: Some(emitted.requirement.node_id),
                capability_id: Some(emitted.requirement.capability_id),
                construct: Some(emitted.construct),
                profile_id: target.profile_id.as_str().to_owned(),
                profile_version: target.profile_version.as_str().to_owned(),
                disposition: Some(result.disposition),
                reason:
                    "the exact target profile does not support this lowering-introduced capability"
                        .to_owned(),
            }));
        }
        let ordinal = source_requirement_count
            .checked_add(index)
            .and_then(|value| u32::try_from(value).ok())
            .ok_or_else(|| Box::new(limit_failure(target)))?;
        introduced.push(IntroducedRequirement {
            identity: RequirementIdentity {
                ordinal,
                node_id: emitted.requirement.node_id,
                capability_id: emitted.requirement.capability_id,
            },
        });
    }
    Ok(introduced)
}

/// Canonically classify the emitted requirements not already represented by a
/// natively implemented semantic requirement.
///
/// Target-plan validation reuses this classification so a capability-bearing
/// AST mutation cannot be serialized without an exactly matching requirement.
pub(crate) fn classify_introduced_requirements(
    source_requirement_count: usize,
    native_source_requirements: &[RequirementIdentity],
    mut emitted_requirements: Vec<EmittedRequirement>,
) -> Option<Vec<EmittedRequirement>> {
    emitted_requirements.sort();
    emitted_requirements.dedup();

    let mut introduced_by_key = BTreeMap::new();
    for emitted in emitted_requirements {
        let requirement = &emitted.requirement;
        if native_source_requirements.iter().any(|source| {
            source.node_id == requirement.node_id
                && source.capability_id == requirement.capability_id
        }) {
            continue;
        }
        introduced_by_key
            .entry((
                requirement.node_id.clone(),
                requirement.capability_id.clone(),
            ))
            .or_insert(emitted);
    }

    let total = source_requirement_count.checked_add(introduced_by_key.len())?;
    if total > MAX_CAPABILITY_REQUIREMENTS {
        return None;
    }
    Some(introduced_by_key.into_values().collect())
}

fn limit_failure(target: &TargetProfile) -> PostLoweringRequirementFailure {
    PostLoweringRequirementFailure {
        kind: PostLoweringRequirementFailureKind::RequirementLimitExceeded,
        node_id: None,
        capability_id: None,
        construct: None,
        profile_id: target.profile_id.as_str().to_owned(),
        profile_version: target.profile_version.as_str().to_owned(),
        disposition: None,
        reason: format!(
            "reconciled requirement count exceeds deterministic limit {MAX_CAPABILITY_REQUIREMENTS}"
        ),
    }
}
