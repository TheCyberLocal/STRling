//! Pure request boundary for optional certified Semantic IR rewrite actions.
//!
//! This stage never mutates a program, scans raw source, consults diagnostics,
//! selects target policy, lowers, serializes, or executes a runtime.

use std::error::Error;
use std::fmt;

use crate::capability_evaluation::validate_prerequisites;
use crate::portability_planning::{
    certified_rewrite_registry, RewriteApplicationKind, RewriteCertificationEvidence,
    RewriteStrategyId,
};
use crate::semantic::{Node, RepetitionMaximum, RepetitionMode, SemanticProgram};
use crate::semantic_analysis::{SemanticFacts, SemanticNodeKind};
use crate::source::{ContractVersion, NodeId, Sha256Digest, SourceOrigin, SpecificationVersion};
use crate::structural_analysis::StructuralFacts;
use crate::validation::canonical_sha256;

/// Stable failures at the explicit optional-rewrite boundary.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum SemanticRewriteErrorCode {
    UnsupportedContract,
    InvalidPrerequisites,
    InvalidRewriteRegistry,
    StrategyNotOptional,
    ProgramFingerprintFailure,
}

/// One deterministic request failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticRewriteError {
    pub code: SemanticRewriteErrorCode,
    pub path: String,
    pub message: String,
}

impl SemanticRewriteError {
    fn new(
        code: SemanticRewriteErrorCode,
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

/// Ordered failures returned without a partial action.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticRewriteErrors {
    pub errors: Vec<SemanticRewriteError>,
}

impl SemanticRewriteErrors {
    fn single(error: SemanticRewriteError) -> Self {
        Self {
            errors: vec![error],
        }
    }
}

impl fmt::Display for SemanticRewriteErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "semantic rewrite request failed with {} error(s)",
            self.errors.len()
        )
    }
}

impl Error for SemanticRewriteErrors {}

/// One caller-owned request for one certified optional strategy and node.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticRewriteRequest {
    pub contract_version: ContractVersion,
    pub strategy_id: RewriteStrategyId,
    pub node_id: NodeId,
}

/// Closed proof conditions for exact-once wrapper elision.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum SemanticRewriteProofCondition {
    OriginalNodeIsRepeat {
        node_id: NodeId,
    },
    DirectBodyRelationship {
        repeat_node_id: NodeId,
        body_node_id: NodeId,
    },
    BoundsExactlyOne {
        node_id: NodeId,
    },
    ModeNonPossessive {
        node_id: NodeId,
    },
}

/// Exact fact or authored Semantic IR field used by one condition.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum SemanticRewriteProofEvidence {
    FoundationalNodeKind {
        node_id: NodeId,
        actual: SemanticNodeKind,
    },
    SemanticChildRelationship {
        parent_node_id: NodeId,
        child_node_id: NodeId,
    },
    AuthoredRepetitionBounds {
        node_id: NodeId,
        minimum: u64,
        maximum: RepetitionMaximum,
    },
    AuthoredRepetitionMode {
        node_id: NodeId,
        mode: RepetitionMode,
    },
}

/// One satisfied condition and the evidence used to satisfy it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticRewriteProofEvaluation {
    pub condition: SemanticRewriteProofCondition,
    pub evidence: SemanticRewriteProofEvidence,
}

/// A certified request-only replacement description.
///
/// `replacement_subtree` is a clone of the existing direct body, including its
/// original identity and provenance. The input program is never mutated.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CertifiedSemanticRewriteAction {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub semantic_program: Sha256Digest,
    pub strategy_id: RewriteStrategyId,
    pub certification: RewriteCertificationEvidence,
    pub removed_wrapper_node_id: NodeId,
    pub removed_wrapper_origin: Option<SourceOrigin>,
    pub replacement_node_id: NodeId,
    pub replacement_subtree: Node,
    pub proof: Vec<SemanticRewriteProofEvaluation>,
    pub explanation: String,
}

/// Construct one certified optional action when every proof condition holds.
///
/// `Ok(None)` is the stable non-applicable result for an absent node or failed
/// exact-shape precondition. Registry or prerequisite corruption is an error.
pub fn request_semantic_rewrite(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    request: &SemanticRewriteRequest,
) -> Result<Option<CertifiedSemanticRewriteAction>, SemanticRewriteErrors> {
    if request.contract_version != ContractVersion::V1_0_0
        || request.contract_version != input.contract_version
    {
        return Err(SemanticRewriteErrors::single(SemanticRewriteError::new(
            SemanticRewriteErrorCode::UnsupportedContract,
            "$.contract_version",
            "rewrite request and Semantic IR must use contract version 1.0.0",
        )));
    }
    validate_prerequisites(input, foundational, structural).map_err(|errors| {
        SemanticRewriteErrors {
            errors: errors
                .errors
                .into_iter()
                .map(|error| {
                    SemanticRewriteError::new(
                        SemanticRewriteErrorCode::InvalidPrerequisites,
                        error.path,
                        error.message,
                    )
                })
                .collect(),
        }
    })?;

    let registry = certified_rewrite_registry().map_err(|error| {
        SemanticRewriteErrors::single(SemanticRewriteError::new(
            SemanticRewriteErrorCode::InvalidRewriteRegistry,
            "$.rewrite_registry",
            error.message,
        ))
    })?;
    let strategy = registry.strategy(request.strategy_id).ok_or_else(|| {
        SemanticRewriteErrors::single(SemanticRewriteError::new(
            SemanticRewriteErrorCode::InvalidRewriteRegistry,
            "$.strategy_id",
            "requested rewrite strategy is not registered",
        ))
    })?;
    if strategy.definition.application_kind != RewriteApplicationKind::OptionalOptimization {
        return Err(SemanticRewriteErrors::single(SemanticRewriteError::new(
            SemanticRewriteErrorCode::StrategyNotOptional,
            "$.strategy_id",
            "mandatory portability strategies cannot be requested as optional actions",
        )));
    }
    if request.strategy_id != RewriteStrategyId::ElideExactOnceRepetitionV1 {
        return Err(SemanticRewriteErrors::single(SemanticRewriteError::new(
            SemanticRewriteErrorCode::StrategyNotOptional,
            "$.strategy_id",
            "the optional strategy has no request implementation",
        )));
    }

    let Some(node) = find_node(&input.root, &request.node_id) else {
        return Ok(None);
    };
    let Some(facts) = foundational.get(&request.node_id) else {
        return Ok(None);
    };
    let Node::Repeat {
        node_id,
        origin,
        body,
        min,
        max,
        mode,
    } = node
    else {
        return Ok(None);
    };
    if facts.kind != SemanticNodeKind::Repeat
        || *min != 1
        || *max != RepetitionMaximum::Bounded(1)
        || *mode == RepetitionMode::Possessive
    {
        return Ok(None);
    }

    let body_node_id = body.node_id().clone();
    let proof = vec![
        SemanticRewriteProofEvaluation {
            condition: SemanticRewriteProofCondition::OriginalNodeIsRepeat {
                node_id: node_id.clone(),
            },
            evidence: SemanticRewriteProofEvidence::FoundationalNodeKind {
                node_id: node_id.clone(),
                actual: facts.kind,
            },
        },
        SemanticRewriteProofEvaluation {
            condition: SemanticRewriteProofCondition::DirectBodyRelationship {
                repeat_node_id: node_id.clone(),
                body_node_id: body_node_id.clone(),
            },
            evidence: SemanticRewriteProofEvidence::SemanticChildRelationship {
                parent_node_id: node_id.clone(),
                child_node_id: body_node_id.clone(),
            },
        },
        SemanticRewriteProofEvaluation {
            condition: SemanticRewriteProofCondition::BoundsExactlyOne {
                node_id: node_id.clone(),
            },
            evidence: SemanticRewriteProofEvidence::AuthoredRepetitionBounds {
                node_id: node_id.clone(),
                minimum: *min,
                maximum: *max,
            },
        },
        SemanticRewriteProofEvaluation {
            condition: SemanticRewriteProofCondition::ModeNonPossessive {
                node_id: node_id.clone(),
            },
            evidence: SemanticRewriteProofEvidence::AuthoredRepetitionMode {
                node_id: node_id.clone(),
                mode: *mode,
            },
        },
    ];
    let semantic_program = canonical_sha256(input)
        .map(Sha256Digest::from_bytes)
        .map_err(|error| {
            SemanticRewriteErrors::single(SemanticRewriteError::new(
                SemanticRewriteErrorCode::ProgramFingerprintFailure,
                "$",
                format!("semantic program fingerprint could not be derived: {error}"),
            ))
        })?;
    let certification = crate::portability_planning::certification_for(request.strategy_id)
        .map_err(|error| {
            SemanticRewriteErrors::single(SemanticRewriteError::new(
                SemanticRewriteErrorCode::InvalidRewriteRegistry,
                "$.rewrite_registry",
                error.message,
            ))
        })?;

    Ok(Some(CertifiedSemanticRewriteAction {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        semantic_program,
        strategy_id: request.strategy_id,
        certification,
        removed_wrapper_node_id: node_id.clone(),
        removed_wrapper_origin: origin.clone(),
        replacement_node_id: body_node_id,
        replacement_subtree: body.as_ref().clone(),
        proof,
        explanation: strategy.definition.explanation.clone(),
    }))
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
