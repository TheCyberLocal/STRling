use std::collections::BTreeSet;
use std::error::Error;
use std::fmt;
use std::sync::OnceLock;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

use super::RewriteStrategyId;
use crate::source::{ContractVersion, Sha256Digest};
use crate::validation::canonical_sha256;

const REGISTRY_JSON: &str = include_str!("../../../spec/portability/equivalence/1.0/registry.json");
const ATOMIC_LITERAL_EVIDENCE_JSON: &str =
    include_str!("../../../spec/portability/equivalence/1.0/atomic-literal-elision.cases.json");
const EXACT_ONCE_EVIDENCE_JSON: &str = include_str!(
    "../../../spec/portability/equivalence/1.0/exact-once-repetition-elision.cases.json"
);
const ECMASCRIPT_EXECUTION_JSON: &str =
    include_str!("../../../tests/conformance/ecmascript-runtime-certification.json");
const PCRE2_EXECUTION_JSON: &str =
    include_str!("../../../tests/conformance/pcre2-runtime-certification.json");
const PYTHON_RE_EXECUTION_JSON: &str =
    include_str!("../../../tests/conformance/python-re-runtime-certification.json");

const ATOMIC_LITERAL_EVIDENCE_PATH: &str =
    "spec/portability/equivalence/1.0/atomic-literal-elision.cases.json";
const EXACT_ONCE_EVIDENCE_PATH: &str =
    "spec/portability/equivalence/1.0/exact-once-repetition-elision.cases.json";
const ECMASCRIPT_EXECUTION_PATH: &str = "tests/conformance/ecmascript-runtime-certification.json";
const PCRE2_EXECUTION_PATH: &str = "tests/conformance/pcre2-runtime-certification.json";
const PYTHON_RE_EXECUTION_PATH: &str = "tests/conformance/python-re-runtime-certification.json";

const ALL_INITIAL_PROFILES: [&str; 5] = [
    "profile:ecmascript/2024",
    "profile:pcre2/10.42",
    "profile:pcre2/10.43",
    "profile:python-re/3.11",
    "profile:python-re/3.11-bytes",
];

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

/// Whether a strategy is selected by portability planning or only by request.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RewriteApplicationKind {
    MandatoryPortability,
    OptionalOptimization,
}

/// The registry-owned selection boundary for a certified strategy.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RewriteSelection {
    UnsupportedOriginalCapability,
    ExplicitRequestOnly,
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
    pub direct_body_node_kind: Option<String>,
}

/// The only transformation currently admitted by the closed library.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteTransformation {
    pub operation: String,
    pub replacement: String,
}

/// Capability requirements removed and introduced by the transformation.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteCapabilityEffects {
    pub original_requirement_kind: Option<String>,
    pub replacement_requirement_kinds: Vec<String>,
}

/// Exact initial profiles and selection policy certified for one strategy.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteTargetApplicability {
    pub profiles: Vec<String>,
    pub selection: RewriteSelection,
}

/// Authored conformance evidence bound to one strategy.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteConformanceEvidence {
    pub evidence_id: String,
    pub path: String,
    pub sha256: Sha256Digest,
}

/// Exact runtime corpus evidence bound to one or more initial profiles.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteExecutionEvidence {
    pub evidence_id: String,
    pub path: String,
    pub sha256: Sha256Digest,
    pub profiles: Vec<String>,
}

/// One fully authored semantics-preserving rewrite definition.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RewriteStrategyDefinition {
    pub strategy_id: String,
    pub application_kind: RewriteApplicationKind,
    pub applicable_semantic_shape: RewriteSemanticShape,
    pub transformation: RewriteTransformation,
    pub capability_effects: RewriteCapabilityEffects,
    pub target_applicability: RewriteTargetApplicability,
    pub preconditions: Vec<RewriteObligation>,
    pub semantic_invariants: Vec<RewriteObligation>,
    pub unsupported_conditions: Vec<RewriteObligation>,
    pub provenance_behavior: String,
    pub explanation: String,
    pub proof_method: RewriteProofMethod,
    pub target_scope: RewriteTargetScope,
    pub required_tests: Vec<String>,
    pub conformance_evidence: RewriteConformanceEvidence,
    pub execution_evidence: Vec<RewriteExecutionEvidence>,
}

/// A registry entry plus the canonical fingerprint of its authored definition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CertifiedRewriteStrategy {
    pub strategy_id: RewriteStrategyId,
    pub definition: RewriteStrategyDefinition,
    pub strategy_fingerprint: Sha256Digest,
}

/// The validated, versioned equivalence registry consumed by certified stages.
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
    pub fn portability_strategy_ids(&self) -> Vec<RewriteStrategyId> {
        self.strategies
            .iter()
            .filter(|strategy| {
                strategy.definition.application_kind == RewriteApplicationKind::MandatoryPortability
            })
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

/// Immutable certification evidence copied into each selected rewrite action.
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

struct EvidenceInputs<'a> {
    atomic_literal: &'a [u8],
    exact_once: &'a [u8],
    ecmascript: &'a [u8],
    pcre2: &'a [u8],
    python_re: &'a [u8],
}

static CERTIFIED_REGISTRY: OnceLock<Result<CertifiedRewriteRegistry, RewriteRegistryError>> =
    OnceLock::new();

/// Load the repository-authored registry and certify all embedded evidence.
pub fn certified_rewrite_registry(
) -> Result<&'static CertifiedRewriteRegistry, RewriteRegistryError> {
    match CERTIFIED_REGISTRY.get_or_init(|| {
        certify_rewrite_registry_with_evidence(
            REGISTRY_JSON.as_bytes(),
            ATOMIC_LITERAL_EVIDENCE_JSON.as_bytes(),
            EXACT_ONCE_EVIDENCE_JSON.as_bytes(),
            ECMASCRIPT_EXECUTION_JSON.as_bytes(),
            PCRE2_EXECUTION_JSON.as_bytes(),
            PYTHON_RE_EXECUTION_JSON.as_bytes(),
        )
    }) {
        Ok(registry) => Ok(registry),
        Err(error) => Err(error.clone()),
    }
}

/// Preserve the original atomic-evidence mutation hook for contract tests.
pub fn certify_rewrite_registry(
    registry_json: &[u8],
    atomic_literal_evidence_json: &[u8],
) -> Result<CertifiedRewriteRegistry, RewriteRegistryError> {
    certify_rewrite_registry_with_evidence(
        registry_json,
        atomic_literal_evidence_json,
        EXACT_ONCE_EVIDENCE_JSON.as_bytes(),
        ECMASCRIPT_EXECUTION_JSON.as_bytes(),
        PCRE2_EXECUTION_JSON.as_bytes(),
        PYTHON_RE_EXECUTION_JSON.as_bytes(),
    )
}

/// Certify caller-supplied registry, conformance, and exact-runtime bytes.
#[allow(clippy::too_many_arguments)]
pub fn certify_rewrite_registry_with_evidence(
    registry_json: &[u8],
    atomic_literal_evidence_json: &[u8],
    exact_once_evidence_json: &[u8],
    ecmascript_execution_json: &[u8],
    pcre2_execution_json: &[u8],
    python_re_execution_json: &[u8],
) -> Result<CertifiedRewriteRegistry, RewriteRegistryError> {
    let authored: AuthoredRegistry = serde_json::from_slice(registry_json)
        .map_err(|error| RewriteRegistryError::new(format!("invalid rewrite registry: {error}")))?;
    if authored.registry_version != ContractVersion::V1_0_0 {
        return Err(RewriteRegistryError::new(
            "unsupported rewrite registry version",
        ));
    }
    if authored.strategies.len() != 2 {
        return Err(RewriteRegistryError::new(
            "the certified registry must contain exactly the reviewed strategy set",
        ));
    }

    let inputs = EvidenceInputs {
        atomic_literal: atomic_literal_evidence_json,
        exact_once: exact_once_evidence_json,
        ecmascript: ecmascript_execution_json,
        pcre2: pcre2_execution_json,
        python_re: python_re_execution_json,
    };
    let mut strategies = Vec::with_capacity(authored.strategies.len());
    for definition in authored.strategies {
        let strategy_id = parse_strategy_id(&definition.strategy_id)?;
        validate_definition(&definition, strategy_id, &inputs)?;
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

pub(crate) fn certification_for(
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
        "rewrite.repeat_exactly_once.elide.v1" => Ok(RewriteStrategyId::ElideExactOnceRepetitionV1),
        _ => Err(RewriteRegistryError::new(format!(
            "unimplemented rewrite strategy in authored registry: {value}"
        ))),
    }
}

fn validate_definition(
    definition: &RewriteStrategyDefinition,
    strategy_id: RewriteStrategyId,
    inputs: &EvidenceInputs<'_>,
) -> Result<(), RewriteRegistryError> {
    validate_common_definition(definition)?;
    match strategy_id {
        RewriteStrategyId::ElideAtomicLiteralV1 => validate_atomic_literal(definition)?,
        RewriteStrategyId::ElideExactOnceRepetitionV1 => validate_exact_once(definition)?,
    }

    let (conformance_path, conformance_bytes) = match strategy_id {
        RewriteStrategyId::ElideAtomicLiteralV1 => {
            (ATOMIC_LITERAL_EVIDENCE_PATH, inputs.atomic_literal)
        }
        RewriteStrategyId::ElideExactOnceRepetitionV1 => {
            (EXACT_ONCE_EVIDENCE_PATH, inputs.exact_once)
        }
    };
    validate_conformance(definition, conformance_path, conformance_bytes)?;
    validate_execution(definition, inputs)?;
    Ok(())
}

fn validate_common_definition(
    definition: &RewriteStrategyDefinition,
) -> Result<(), RewriteRegistryError> {
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
    if definition.proof_method != RewriteProofMethod::Structural
        || definition.target_scope != RewriteTargetScope::TargetNeutral
        || definition.transformation.operation != "elide_wrapper"
        || definition.transformation.replacement != "direct_body"
        || !definition
            .capability_effects
            .replacement_requirement_kinds
            .is_empty()
        || definition.provenance_behavior.trim().is_empty()
        || definition.explanation.trim().is_empty()
        || definition.required_tests.len() < 2
        || has_duplicate_ids(definition.required_tests.iter().map(String::as_str))
        || definition
            .target_applicability
            .profiles
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>()
            != ALL_INITIAL_PROFILES
    {
        return Err(RewriteRegistryError::new(
            "rewrite shape, transformation, target coverage, tests, or explanation is incomplete",
        ));
    }
    Ok(())
}

fn validate_atomic_literal(
    definition: &RewriteStrategyDefinition,
) -> Result<(), RewriteRegistryError> {
    if definition.strategy_id != "rewrite.atomic_literal.elide.v1"
        || definition.application_kind != RewriteApplicationKind::MandatoryPortability
        || definition.applicable_semantic_shape.original_node_kind != "atomic"
        || definition
            .applicable_semantic_shape
            .direct_body_node_kind
            .as_deref()
            != Some("literal")
        || definition
            .capability_effects
            .original_requirement_kind
            .as_deref()
            != Some("atomic")
        || definition.target_applicability.selection
            != RewriteSelection::UnsupportedOriginalCapability
        || obligation_ids(&definition.preconditions)
            != [
                "precondition.original_node_atomic",
                "precondition.direct_body_relationship",
                "precondition.body_node_literal",
            ]
    {
        return Err(RewriteRegistryError::new(
            "atomic-literal strategy identity or proof boundary is malformed",
        ));
    }
    Ok(())
}

fn validate_exact_once(definition: &RewriteStrategyDefinition) -> Result<(), RewriteRegistryError> {
    if definition.strategy_id != "rewrite.repeat_exactly_once.elide.v1"
        || definition.application_kind != RewriteApplicationKind::OptionalOptimization
        || definition.applicable_semantic_shape.original_node_kind != "repeat"
        || definition
            .applicable_semantic_shape
            .direct_body_node_kind
            .is_some()
        || definition
            .capability_effects
            .original_requirement_kind
            .is_some()
        || definition.target_applicability.selection != RewriteSelection::ExplicitRequestOnly
        || obligation_ids(&definition.preconditions)
            != [
                "precondition.original_node_repeat",
                "precondition.direct_body_relationship",
                "precondition.minimum_exactly_one",
                "precondition.maximum_exactly_one",
                "precondition.mode_nonpossessive",
            ]
    {
        return Err(RewriteRegistryError::new(
            "exact-once strategy identity or proof boundary is malformed",
        ));
    }
    Ok(())
}

fn validate_conformance(
    definition: &RewriteStrategyDefinition,
    expected_path: &str,
    evidence_bytes: &[u8],
) -> Result<(), RewriteRegistryError> {
    let actual_sha256 = Sha256Digest::from_bytes(Sha256::digest(evidence_bytes).into());
    if definition.conformance_evidence.path != expected_path
        || definition.conformance_evidence.sha256 != actual_sha256
        || !definition
            .required_tests
            .contains(&definition.conformance_evidence.evidence_id)
    {
        return Err(RewriteRegistryError::new(
            "rewrite conformance evidence is missing or stale",
        ));
    }
    let evidence: Value = serde_json::from_slice(evidence_bytes)
        .map_err(|error| RewriteRegistryError::new(format!("invalid rewrite evidence: {error}")))?;
    if evidence.get("suite_version").and_then(Value::as_str) != Some("1.0.0")
        || evidence.get("strategy_id").and_then(Value::as_str)
            != Some(definition.strategy_id.as_str())
        || evidence
            .get("cases")
            .and_then(Value::as_array)
            .map_or(true, Vec::is_empty)
        || evidence
            .get("preserved_invariants")
            .and_then(Value::as_array)
            .map_or(true, Vec::is_empty)
    {
        return Err(RewriteRegistryError::new(
            "rewrite conformance suite does not satisfy the strategy obligations",
        ));
    }
    Ok(())
}

fn validate_execution(
    definition: &RewriteStrategyDefinition,
    inputs: &EvidenceInputs<'_>,
) -> Result<(), RewriteRegistryError> {
    let expected = [
        (
            ECMASCRIPT_EXECUTION_PATH,
            inputs.ecmascript,
            &["profile:ecmascript/2024"][..],
        ),
        (
            PCRE2_EXECUTION_PATH,
            inputs.pcre2,
            &["profile:pcre2/10.42", "profile:pcre2/10.43"][..],
        ),
        (
            PYTHON_RE_EXECUTION_PATH,
            inputs.python_re,
            &["profile:python-re/3.11", "profile:python-re/3.11-bytes"][..],
        ),
    ];
    if definition.execution_evidence.len() != expected.len() {
        return Err(RewriteRegistryError::new(
            "rewrite execution evidence is profile-incomplete",
        ));
    }
    let mut covered_profiles = BTreeSet::new();
    for (evidence, (expected_path, bytes, expected_profiles)) in
        definition.execution_evidence.iter().zip(expected)
    {
        let actual_sha256 = Sha256Digest::from_bytes(Sha256::digest(bytes).into());
        if evidence.path != expected_path
            || evidence.sha256 != actual_sha256
            || evidence
                .profiles
                .iter()
                .map(String::as_str)
                .collect::<Vec<_>>()
                != expected_profiles
        {
            return Err(RewriteRegistryError::new(
                "rewrite execution evidence is missing, stale, or profile-incomplete",
            ));
        }
        covered_profiles.extend(evidence.profiles.iter().cloned());
        let corpus: Value = serde_json::from_slice(bytes).map_err(|error| {
            RewriteRegistryError::new(format!("invalid rewrite execution evidence: {error}"))
        })?;
        let has_strategy = corpus
            .get("rewrite_cases")
            .and_then(Value::as_array)
            .is_some_and(|cases| {
                cases.iter().any(|case| {
                    case.get("strategy_id").and_then(Value::as_str)
                        == Some(definition.strategy_id.as_str())
                })
            });
        if !has_strategy {
            return Err(RewriteRegistryError::new(
                "rewrite execution corpus omits the registered strategy",
            ));
        }
    }
    if covered_profiles
        != definition
            .target_applicability
            .profiles
            .iter()
            .cloned()
            .collect()
    {
        return Err(RewriteRegistryError::new(
            "rewrite execution evidence does not cover every applicable profile",
        ));
    }
    Ok(())
}

fn obligation_ids(obligations: &[RewriteObligation]) -> Vec<&str> {
    obligations.iter().map(|item| item.id.as_str()).collect()
}

fn has_duplicate_ids<'a>(mut values: impl Iterator<Item = &'a str>) -> bool {
    let mut seen = BTreeSet::new();
    values.any(|value| !seen.insert(value))
}
