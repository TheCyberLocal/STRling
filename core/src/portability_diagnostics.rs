//! Structured, target-aware explanations derived from a certified portability plan.
//!
//! This stage explains factual and planning evidence. It does not recompute
//! capabilities, select or apply rewrites, lower Semantic IR, or emit syntax.

use std::error::Error;
use std::fmt;

use crate::capability_evaluation::{
    CapabilityDisposition, CapabilityResult, ConstraintDisposition,
};
use crate::diagnostic::{
    compare_diagnostics, Advice, AdviceKind, CompilerPhase, Diagnostic, DiagnosticCategory,
    DiagnosticCode, DiagnosticOccurrence, RelatedLocation, RelatedLocationRole, Severity,
    SeverityBasis,
};
use crate::portability_planning::{
    certified_rewrite_registry, PortabilityPlan, RequirementPlanningDisposition,
    RewriteAttemptDisposition, UnresolvedPlanningReason,
};
use crate::semantic::{Node, SemanticProgram};
use crate::source::{NodeId, Sha256Digest, SourceSpan};
use crate::target::CapabilityAvailability;
use crate::validation::{canonical_sha256, Validate};

/// Stable explanation for native target support.
pub const PORTABILITY_NATIVE_DIAGNOSTIC: &str = "STRL-PORTABILITY-0101";
/// Stable explanation for a certified semantics-preserving rewrite.
pub const PORTABILITY_REWRITE_DIAGNOSTIC: &str = "STRL-PORTABILITY-0102";
/// Stable explanation for explicit unsupported target evidence.
pub const PORTABILITY_UNSUPPORTED_DIAGNOSTIC: &str = "STRL-PORTABILITY-0103";
/// Stable explanation for incomplete target or proof evidence.
pub const PORTABILITY_UNRESOLVED_DIAGNOSTIC: &str = "STRL-PORTABILITY-0104";

/// Stable error categories for explanation correspondence failures.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PortabilityDiagnosticErrorCode {
    ProgramFingerprintMismatch,
    InvalidPlan,
    InvalidRegistry,
    InvalidDiagnostic,
}

/// One deterministic failure in target-aware explanation generation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PortabilityDiagnosticError {
    pub code: PortabilityDiagnosticErrorCode,
    pub message: String,
}

impl PortabilityDiagnosticError {
    fn new(code: PortabilityDiagnosticErrorCode, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }
}

impl fmt::Display for PortabilityDiagnosticError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl Error for PortabilityDiagnosticError {}

/// Explain every factual/planning decision using only certified in-memory evidence.
pub fn explain_portability(
    input: &SemanticProgram,
    plan: &PortabilityPlan,
) -> Result<Vec<Diagnostic>, PortabilityDiagnosticError> {
    plan.validate().map_err(|errors| {
        PortabilityDiagnosticError::new(
            PortabilityDiagnosticErrorCode::InvalidPlan,
            errors.to_string(),
        )
    })?;
    let actual = canonical_sha256(input)
        .map(Sha256Digest::from_bytes)
        .map_err(|error| {
            PortabilityDiagnosticError::new(
                PortabilityDiagnosticErrorCode::ProgramFingerprintMismatch,
                format!("semantic program cannot be fingerprinted: {error}"),
            )
        })?;
    if plan.semantic_program != actual {
        return Err(PortabilityDiagnosticError::new(
            PortabilityDiagnosticErrorCode::ProgramFingerprintMismatch,
            "portability plan does not correspond to the supplied semantic program",
        ));
    }

    let mut diagnostics = Vec::with_capacity(plan.decisions.len());
    for decision in &plan.decisions {
        let capability = decision.requirement.capability_id.as_str();
        let profile = format!(
            "{}@{}",
            plan.target_profile.profile_id.as_str(),
            plan.target_profile.profile_version.as_str()
        );
        let (code, severity, message, affected_node_ids, mut advice) =
            match &decision.disposition {
                RequirementPlanningDisposition::Native(native) => (
                    PORTABILITY_NATIVE_DIAGNOSTIC,
                    Severity::Info,
                    format!(
                        "Capability {capability} is native for target profile {profile}."
                    ),
                    vec![decision.requirement.node_id.clone()],
                    vec![Advice {
                        kind: AdviceKind::Note,
                        message: capability_summary(&native.capability_result),
                    }],
                ),
                RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
                    let registry = certified_rewrite_registry().map_err(|error| {
                        PortabilityDiagnosticError::new(
                            PortabilityDiagnosticErrorCode::InvalidRegistry,
                            error.message,
                        )
                    })?;
                    let strategy = registry
                        .strategy(rewrite.rewrite_plan.strategy_id)
                        .ok_or_else(|| {
                            PortabilityDiagnosticError::new(
                                PortabilityDiagnosticErrorCode::InvalidRegistry,
                                "selected rewrite strategy is absent from the certified registry",
                            )
                        })?;
                    let certification = &rewrite.rewrite_plan.certification;
                    (
                        PORTABILITY_REWRITE_DIAGNOSTIC,
                        Severity::Info,
                        strategy.definition.explanation.clone(),
                        rewrite.rewrite_plan.affected_node_ids.clone(),
                        vec![
                            Advice {
                                kind: AdviceKind::Note,
                                message: capability_summary(&rewrite.capability_result),
                            },
                            Advice {
                                kind: AdviceKind::Note,
                                message: format!(
                                    "Certification: registry 1.0.0; strategy {} sha256:{}; conformance {} sha256:{}.",
                                    rewrite.rewrite_plan.strategy_id.as_str(),
                                    certification.strategy_fingerprint.as_str(),
                                    certification.conformance_evidence_id,
                                    certification.conformance_evidence_sha256.as_str()
                                ),
                            },
                            Advice {
                                kind: AdviceKind::Note,
                                message: format!(
                                    "Satisfied proof obligations: {}.",
                                    strategy
                                        .definition
                                        .preconditions
                                        .iter()
                                        .map(|item| item.id.as_str())
                                        .collect::<Vec<_>>()
                                        .join(", ")
                                ),
                            },
                        ],
                    )
                }
                RequirementPlanningDisposition::Unsupported(unsupported) => (
                    PORTABILITY_UNSUPPORTED_DIAGNOSTIC,
                    Severity::Warning,
                    format!(
                        "Target profile {profile} cannot satisfy capability {capability}, and no certified equivalent rewrite applies."
                    ),
                    vec![decision.requirement.node_id.clone()],
                    vec![
                        Advice {
                            kind: AdviceKind::Note,
                            message: capability_summary(&unsupported.capability_result),
                        },
                        Advice {
                            kind: AdviceKind::Note,
                            message: attempt_summary(&unsupported.rewrite_attempts),
                        },
                    ],
                ),
                RequirementPlanningDisposition::Unresolved(unresolved) => (
                    PORTABILITY_UNRESOLVED_DIAGNOSTIC,
                    Severity::Warning,
                    format!(
                        "Portability for capability {capability} is unresolved for target profile {profile}."
                    ),
                    vec![decision.requirement.node_id.clone()],
                    vec![
                        Advice {
                            kind: AdviceKind::Note,
                            message: capability_summary(&unresolved.capability_result),
                        },
                        Advice {
                            kind: AdviceKind::Note,
                            message: format!(
                                "Unresolved reason: {}.",
                                unresolved_reason(unresolved.reason)
                            ),
                        },
                    ],
                ),
            };
        advice.push(Advice {
            kind: AdviceKind::Note,
            message: format!(
                "Affected Semantic IR nodes: {}.",
                affected_node_ids
                    .iter()
                    .map(NodeId::as_str)
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
        });
        let (primary_location, related_locations) =
            source_locations(&input.root, &affected_node_ids);
        let code = DiagnosticCode::try_from(code).map_err(|message| {
            PortabilityDiagnosticError::new(
                PortabilityDiagnosticErrorCode::InvalidDiagnostic,
                message,
            )
        })?;
        let diagnostic = Diagnostic {
            contract_version: plan.contract_version,
            occurrence: DiagnosticOccurrence::new(0),
            code,
            severity,
            severity_basis: SeverityBasis::TargetProfile,
            phase: CompilerPhase::Portability,
            category: DiagnosticCategory::Portability,
            message,
            primary_location,
            related_locations,
            advice: Some(advice),
            fixes: None,
        };
        diagnostic.validate().map_err(|errors| {
            PortabilityDiagnosticError::new(
                PortabilityDiagnosticErrorCode::InvalidDiagnostic,
                errors.to_string(),
            )
        })?;
        diagnostics.push(diagnostic);
    }
    diagnostics.sort_by(compare_diagnostics);

    let mut coalesced = Vec::<(Diagnostic, usize)>::new();
    for diagnostic in diagnostics {
        if let Some((previous, count)) = coalesced.last_mut() {
            if *previous == diagnostic {
                *count += 1;
                continue;
            }
        }
        coalesced.push((diagnostic, 1));
    }

    let mut diagnostics = Vec::with_capacity(coalesced.len());
    for (index, (mut diagnostic, count)) in coalesced.into_iter().enumerate() {
        if count > 1 {
            diagnostic
                .advice
                .get_or_insert_with(Vec::new)
                .push(Advice {
                    kind: AdviceKind::Note,
                    message: format!(
                        "This identical evidence applies to {count} canonical requirement occurrences on the affected Semantic IR nodes."
                    ),
                });
        }
        diagnostic.occurrence = DiagnosticOccurrence::new(index as u64);
        diagnostic.validate().map_err(|errors| {
            PortabilityDiagnosticError::new(
                PortabilityDiagnosticErrorCode::InvalidDiagnostic,
                errors.to_string(),
            )
        })?;
        diagnostics.push(diagnostic);
    }
    Ok(diagnostics)
}

fn capability_summary(result: &CapabilityResult) -> String {
    let disposition = match result.disposition {
        CapabilityDisposition::Supported => "supported",
        CapabilityDisposition::Unsupported => "unsupported",
        CapabilityDisposition::ConstraintViolation => "constraint_violation",
        CapabilityDisposition::Unknown => "unknown",
    };
    let availability = match result
        .profile_capability
        .as_ref()
        .map(|capability| capability.availability)
    {
        Some(CapabilityAvailability::Available) => "available",
        Some(CapabilityAvailability::Constrained) => "constrained",
        Some(CapabilityAvailability::Unavailable) => "unavailable",
        None => "unlisted",
    };
    let constraints = result
        .constraint_evaluations
        .iter()
        .map(|evaluation| {
            let disposition = match evaluation.disposition {
                ConstraintDisposition::Satisfied => "satisfied",
                ConstraintDisposition::Violated => "violated",
                ConstraintDisposition::Unknown => "unknown",
            };
            format!(
                "{}={disposition}",
                evaluation.constraint.constraint_id.as_str()
            )
        })
        .collect::<Vec<_>>();
    if constraints.is_empty() {
        format!(
            "Capability evidence: disposition {disposition}; profile availability {availability}."
        )
    } else {
        format!(
            "Capability evidence: disposition {disposition}; profile availability {availability}; constraints {}.",
            constraints.join(", ")
        )
    }
}

fn attempt_summary(attempts: &[crate::portability_planning::RewriteAttempt]) -> String {
    let entries = attempts
        .iter()
        .map(|attempt| {
            format!(
                "{}={}",
                attempt.strategy_id.as_str(),
                attempt_disposition(attempt.disposition)
            )
        })
        .collect::<Vec<_>>();
    format!("Certified rewrite attempts: {}.", entries.join(", "))
}

fn attempt_disposition(disposition: RewriteAttemptDisposition) -> &'static str {
    match disposition {
        RewriteAttemptDisposition::NotApplicable => "not_applicable",
        RewriteAttemptDisposition::ProofFailed => "proof_failed",
        RewriteAttemptDisposition::ProofIndeterminate => "proof_indeterminate",
        RewriteAttemptDisposition::ReplacementUnsupported => "replacement_unsupported",
        RewriteAttemptDisposition::ReplacementUnknown => "replacement_unknown",
        RewriteAttemptDisposition::Applicable => "applicable",
    }
}

fn unresolved_reason(reason: UnresolvedPlanningReason) -> &'static str {
    match reason {
        UnresolvedPlanningReason::CapabilityUnknown => "capability_unknown",
        UnresolvedPlanningReason::RewriteProofIndeterminate => "rewrite_proof_indeterminate",
        UnresolvedPlanningReason::ReplacementCapabilityUnknown => "replacement_capability_unknown",
    }
}

fn source_locations(
    root: &Node,
    affected_node_ids: &[NodeId],
) -> (Option<SourceSpan>, Option<Vec<RelatedLocation>>) {
    let mut evidence = Vec::new();
    for node_id in affected_node_ids {
        if let Some(node) = find_node(root, node_id) {
            if let Some(spans) = node
                .origin()
                .and_then(|origin| origin.source_spans.as_ref())
            {
                evidence.extend(spans.iter().cloned().map(|span| (node_id.clone(), span)));
            }
        }
    }
    evidence.sort_by(|left, right| {
        (&left.1.source_id, left.1.start, left.1.end, &left.0).cmp(&(
            &right.1.source_id,
            right.1.start,
            right.1.end,
            &right.0,
        ))
    });
    evidence.dedup();
    let Some((_, primary)) = evidence.first().cloned() else {
        return (None, None);
    };
    let related = evidence
        .into_iter()
        .skip(1)
        .map(|(node_id, location)| RelatedLocation {
            role: RelatedLocationRole::Context,
            message: format!("Related rewrite evidence for {}.", node_id.as_str()),
            location,
        })
        .collect::<Vec<_>>();
    (
        Some(primary),
        if related.is_empty() {
            None
        } else {
            Some(related)
        },
    )
}

fn find_node<'a>(root: &'a Node, node_id: &NodeId) -> Option<&'a Node> {
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        if node.node_id() == node_id {
            return Some(node);
        }
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
    None
}
