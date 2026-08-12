use std::error::Error;
use std::fmt;
use std::sync::OnceLock;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::RewriteStrategyId;
use crate::source::{ContractVersion, Sha256Digest};
use crate::validation::canonical_sha256;

const REGISTRY_JSON: &str = include_str!("../../../spec/portability/equivalence/1.0/registry.json");
const ATOMIC_LITERAL_EVIDENCE_JSON: &str =
    include_str!("../../../spec/portability/equivalence/1.0/atomic-literal-elision.cases.json");
const ATOMIC_LITERAL_EVIDENCE_PATH: &str =
    "spec/portability/equivalence/1.0/atomic-literal-elision.cases.json";

/// Proof method admitted by the authored equivalence registry.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RewriteProofMethod {
    Structural,
}

/// Whether equivalence depends on target-neutral or target-specific semantics.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RewriteTargetScope {
    TargetNeutral,
}

/// One stable proof, invariant, or unsupported-condition obligation.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteObligation {
    pub id: String,
    pub text: String,
}

/// The exact Semantic IR shape admitted by a rewrite strategy.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteSemanticShape {
    pub original_node_kind: String,
    pub direct_body_node_kind: String,
}

/// Authored conformance evidence bound to one strategy.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteConformanceEvidence {
    pub evidence_id: String,
    pub path: String,
    pub sha256: Sha256Digest,
}

/// A future runtime obligation retained before a target emitter exists.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteExecutionHook {
    pub hook_id: String,
    pub status: String,
    pub obligation: String,
}

/// One fully authored semantics-preserving rewrite definition.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteStrategyDefinition {
    pub strategy_id: String,
    pub applicable_semantic_shape: RewriteSemanticShape,
    pub original_requirement_kind: String,
    pub preconditions: Vec<RewriteObligation>,
    pub semantic_invariants: Vec<RewriteObligation>,
    pub unsupported_conditions: Vec<RewriteObligation>,
    pub explanation: String,
    pub proof_method: RewriteProofMethod,
    pub target_scope: RewriteTargetScope,
    pub required_tests: Vec<String>,
    pub conformance_evidence: RewriteConformanceEvidence,
    pub execution_hooks: Vec<RewriteExecutionHook>,
}

/// A registry entry plus the canonical fingerprint of its authored definition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CertifiedRewriteStrategy {
    pub strategy_id: RewriteStrategyId,
    pub definition: RewriteStrategyDefinition,
    pub strategy_fingerprint: Sha256Digest,
}

/// The validated, versioned equivalence registry consumed by the planner.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CertifiedRewriteRegistry {
    pub registry_version: ContractVersion,
    pub strategies: Vec<CertifiedRewriteStrategy>,
}

impl CertifiedRewriteRegistry {
    #[must_use]
    pub fn strategy_ids(&self) -> Vec<RewriteStrategyId> {
        self.strategies
            .iter()
            .map(|strategy| strategy.strategy_id)
            .collect()
    }

    #[must_use]
    pub fn strategy(&self, strategy_id: RewriteStrategyId) -> Option<&CertifiedRewriteStrategy> {
        self.strategies
            .iter()
            .find(|strategy| strategy.strategy_id == strategy_id)
    }
}

/// Immutable certification evidence copied into each selected rewrite plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RewriteCertificationEvidence {
    pub registry_version: ContractVersion,
    pub strategy_fingerprint: Sha256Digest,
    pub conformance_evidence_id: String,
    pub conformance_evidence_sha256: Sha256Digest,
}

/// A deterministic authored-registry or evidence-integrity failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RewriteRegistryError {
    pub message: String,
}

impl RewriteRegistryError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl fmt::Display for RewriteRegistryError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl Error for RewriteRegistryError {}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct AuthoredRegistry {
    registry_version: ContractVersion,
    strategies: Vec<RewriteStrategyDefinition>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct EvidenceSuite {
    suite_version: ContractVersion,
    strategy_id: String,
    cases: Vec<serde_json::Value>,
    preserved_invariants: Vec<String>,
    execution_hooks: Vec<RewriteExecutionHook>,
}

static CERTIFIED_REGISTRY: OnceLock<Result<CertifiedRewriteRegistry, RewriteRegistryError>> =
    OnceLock::new();

/// Load the repository-authored registry and certify its embedded evidence.
pub fn certified_rewrite_registry(
) -> Result<&'static CertifiedRewriteRegistry, RewriteRegistryError> {
    match CERTIFIED_REGISTRY.get_or_init(|| {
        certify_rewrite_registry(
            REGISTRY_JSON.as_bytes(),
            ATOMIC_LITERAL_EVIDENCE_JSON.as_bytes(),
        )
    }) {
        Ok(registry) => Ok(registry),
        Err(error) => Err(error.clone()),
    }
}

/// Validate caller-supplied registry/evidence bytes using the production rules.
///
/// This hook lets contract tests prove that missing or stale authored evidence
/// fails before a strategy can be selected or reported as equivalent.
pub fn certify_rewrite_registry(
    registry_json: &[u8],
    atomic_literal_evidence_json: &[u8],
) -> Result<CertifiedRewriteRegistry, RewriteRegistryError> {
    let authored: AuthoredRegistry = serde_json::from_slice(registry_json)
        .map_err(|error| RewriteRegistryError::new(format!("invalid rewrite registry: {error}")))?;
    if authored.registry_version != ContractVersion::V1_0_0 {
        return Err(RewriteRegistryError::new(
            "unsupported rewrite registry version",
        ));
    }
    if authored.strategies.len() != 1 {
        return Err(RewriteRegistryError::new(
            "the certified registry must contain exactly the reviewed strategy set",
        ));
    }

    let evidence: EvidenceSuite = serde_json::from_slice(atomic_literal_evidence_json)
        .map_err(|error| RewriteRegistryError::new(format!("invalid rewrite evidence: {error}")))?;
    let evidence_sha256 =
        Sha256Digest::from_bytes(Sha256::digest(atomic_literal_evidence_json).into());
    let mut strategies = Vec::with_capacity(authored.strategies.len());
    for definition in authored.strategies {
        let strategy_id = parse_strategy_id(&definition.strategy_id)?;
        validate_definition(&definition, &evidence, &evidence_sha256)?;
        let fingerprint = canonical_sha256(&definition).map_err(|error| {
            RewriteRegistryError::new(format!("rewrite strategy cannot be fingerprinted: {error}"))
        })?;
        strategies.push(CertifiedRewriteStrategy {
            strategy_id,
            definition,
            strategy_fingerprint: Sha256Digest::from_bytes(fingerprint),
        });
    }
    if strategies
        .windows(2)
        .any(|pair| pair[0].strategy_id >= pair[1].strategy_id)
    {
        return Err(RewriteRegistryError::new(
            "rewrite strategies must be unique and canonically ordered",
        ));
    }
    Ok(CertifiedRewriteRegistry {
        registry_version: authored.registry_version,
        strategies,
    })
}

pub(super) fn certification_for(
    strategy_id: RewriteStrategyId,
) -> Result<RewriteCertificationEvidence, RewriteRegistryError> {
    let registry = certified_rewrite_registry()?;
    let strategy = registry
        .strategy(strategy_id)
        .ok_or_else(|| RewriteRegistryError::new("rewrite strategy is not certified"))?;
    Ok(RewriteCertificationEvidence {
        registry_version: registry.registry_version,
        strategy_fingerprint: strategy.strategy_fingerprint.clone(),
        conformance_evidence_id: strategy.definition.conformance_evidence.evidence_id.clone(),
        conformance_evidence_sha256: strategy.definition.conformance_evidence.sha256.clone(),
    })
}

fn parse_strategy_id(value: &str) -> Result<RewriteStrategyId, RewriteRegistryError> {
    match value {
        "rewrite.atomic_literal.elide.v1" => Ok(RewriteStrategyId::ElideAtomicLiteralV1),
        _ => Err(RewriteRegistryError::new(format!(
            "unimplemented rewrite strategy in authored registry: {value}"
        ))),
    }
}

fn validate_definition(
    definition: &RewriteStrategyDefinition,
    evidence: &EvidenceSuite,
    actual_evidence_sha256: &Sha256Digest,
) -> Result<(), RewriteRegistryError> {
    if definition.strategy_id != "rewrite.atomic_literal.elide.v1"
        || definition.applicable_semantic_shape.original_node_kind != "atomic"
        || definition.applicable_semantic_shape.direct_body_node_kind != "literal"
        || definition.original_requirement_kind != "atomic"
        || definition.proof_method != RewriteProofMethod::Structural
        || definition.target_scope != RewriteTargetScope::TargetNeutral
    {
        return Err(RewriteRegistryError::new(
            "atomic-literal strategy identity or semantic shape is malformed",
        ));
    }
    for (label, obligations) in [
        ("preconditions", &definition.preconditions),
        ("semantic invariants", &definition.semantic_invariants),
        ("unsupported conditions", &definition.unsupported_conditions),
    ] {
        if obligations.is_empty()
            || obligations
                .iter()
                .any(|item| item.id.trim().is_empty() || item.text.trim().is_empty())
            || has_duplicate_ids(obligations.iter().map(|item| item.id.as_str()))
        {
            return Err(RewriteRegistryError::new(format!(
                "rewrite strategy {label} are missing or duplicated"
            )));
        }
    }
    if definition.explanation.trim().is_empty()
        || definition.required_tests
            != [
                "property.normalized_programs.v1".to_owned(),
                "conformance.atomic_literal_elision.v1".to_owned(),
            ]
        || definition.execution_hooks.is_empty()
        || definition.execution_hooks.iter().any(|hook| {
            hook.hook_id.trim().is_empty()
                || hook.status != "deferred_until_target_emitter"
                || hook.obligation.trim().is_empty()
        })
    {
        return Err(RewriteRegistryError::new(
            "rewrite explanation, test obligations, or execution hooks are incomplete",
        ));
    }
    if definition.conformance_evidence.path != ATOMIC_LITERAL_EVIDENCE_PATH
        || definition.conformance_evidence.evidence_id != "conformance.atomic_literal_elision.v1"
        || definition.conformance_evidence.sha256 != *actual_evidence_sha256
    {
        return Err(RewriteRegistryError::new(
            "rewrite conformance evidence is missing or stale",
        ));
    }
    if evidence.suite_version != ContractVersion::V1_0_0
        || evidence.strategy_id != definition.strategy_id
        || evidence.cases.is_empty()
        || evidence.preserved_invariants.is_empty()
        || evidence.execution_hooks != definition.execution_hooks
    {
        return Err(RewriteRegistryError::new(
            "rewrite conformance suite does not satisfy the strategy obligations",
        ));
    }
    Ok(())
}

fn has_duplicate_ids<'a>(mut values: impl Iterator<Item = &'a str>) -> bool {
    let mut seen = std::collections::BTreeSet::new();
    values.any(|value| !seen.insert(value))
}
