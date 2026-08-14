//! Deterministic projections from canonical Semantic IR into semantic authoring surfaces.
//!
//! `strling.semantic-conversion@1.0.0` under `spec/conversions/semantic/1.0`
//! is authoritative. This module renders from validated canonical semantics,
//! reconstructs through the existing destination frontend, and claims exactness
//! only after normalized semantic alpha-equivalence succeeds.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::explanation::{
    EvidenceClass, ExplanationDocument, ExplanationModelVersion, TargetExplanationStatus,
    TargetOutcomeExplanation,
};
use crate::protocol::CompileInput;
use crate::semantic::{
    AssertionPolarity, BuiltinClassName, CaseMatching, CharacterDomain, CharacterSetMember,
    LineTerminators, LookaroundDirection, Node, PositionKind, RepetitionMaximum, RepetitionMode,
    SemanticProgram,
};
use crate::semantic_frontend;
use crate::simply::{decode_simply_builder_request, replay_simply_builder_request};
use crate::source::{
    CaptureId, ContractVersion, DialectVersion, FrontendId, FrontendIdentity, NodeId, Producer,
    ProducerId, Provenance, ProvenanceKind, Sha256Digest, SourceContent, SourceDocument, SourceId,
    SpecificationVersion, Utf8Encoding,
};
use crate::target::{CapabilityId, ProfileId};
use crate::validation::{canonical_sha256, Validate, ValidationErrors};

pub const SEMANTIC_CONVERSION_VERSION: &str = "1.0.0";
pub const SEMANTIC_ALPHA_EQUIVALENCE_METHOD: &str = "normalized_semantic_alpha_equivalence@1.0.0";

const SEMANTIC_DSL_MEDIA_TYPE: &str = "text/x-strling-semantic; charset=utf-8";
const SEMANTIC_DSL_IDENTIFIER_LIMIT: usize = 64;
const SEMANTIC_DSL_RESERVED: &[&str] = &[
    "any",
    "at",
    "before",
    "capture",
    "case",
    "character",
    "choice",
    "empty",
    "if",
    "not",
    "pattern",
    "repeat",
    "same",
    "semantic",
    "sequence",
    "text",
    "unless",
    "without",
];

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum SemanticConversionVersion {
    #[serde(rename = "1.0.0")]
    V1_0_0,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticConversionDestination {
    SemanticStrling,
    SimplyBuilder,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum DestinationContractVersion {
    #[serde(rename = "1.0.0")]
    V1_0_0,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum DestinationContractId {
    #[serde(rename = "strling.semantic")]
    SemanticStrling,
    #[serde(rename = "strling.simply-builder")]
    SimplyBuilder,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DestinationContract {
    pub id: DestinationContractId,
    pub version: DestinationContractVersion,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticConversionStatus {
    Exact,
    Partial,
    Unsupported,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum CommentMigrationPolicy {
    #[serde(rename = "semantic_ir_only")]
    SemanticIrOnly,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionSourceSummary {
    pub node_count: usize,
    pub capture_count: usize,
    pub backreference_count: usize,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum SemanticConversionOutput {
    SemanticStrling {
        source_id: SourceId,
        media_type: String,
        text: String,
        sha256: Sha256Digest,
    },
    SimplyBuilder {
        protocol_version: String,
        request: Value,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ConversionByteSpan {
    pub start: u64,
    pub end: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionNodeMapping {
    pub source_node_id: NodeId,
    pub destination_key: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub byte_span: Option<ConversionByteSpan>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionCaptureMapping {
    pub source_capture_id: CaptureId,
    pub destination_key: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub identifier_span: Option<ConversionByteSpan>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum SemanticEquivalenceMethod {
    #[serde(rename = "normalized_semantic_alpha_equivalence@1.0.0")]
    NormalizedSemanticAlphaV1,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticEquivalenceStatus {
    Proven,
    NotProven,
    NotApplicable,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ExcludedEquivalenceEvidence {
    NodeIds,
    CaptureIds,
    Origins,
    Sources,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticEquivalenceEvidence {
    pub method: SemanticEquivalenceMethod,
    pub status: SemanticEquivalenceStatus,
    pub source_fingerprint: Sha256Digest,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reconstructed_fingerprint: Option<Sha256Digest>,
    pub excluded_evidence: Vec<ExcludedEquivalenceEvidence>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticConversionIssueCode {
    CommentsNotAvailable,
    CaptureNameSubstituted,
    ManualCaptureNameRequired,
    ForwardBackreferenceUnsupported,
    SelfBackreferenceUnsupported,
    RecursiveBackreferenceUnsupported,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticConversionIssueCategory {
    NonsemanticLoss,
    Loss,
    Approximation,
    ManualDecision,
    Unsupported,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionIssue {
    pub issue_id: String,
    pub code: SemanticConversionIssueCode,
    pub category: SemanticConversionIssueCategory,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source_node_id: Option<NodeId>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source_capture_id: Option<CaptureId>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub replacement: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionExplanationLink {
    pub model_version: ExplanationModelVersion,
    pub semantic_program: Sha256Digest,
    pub node_id: NodeId,
    pub evidence_class: EvidenceClass,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticConversionTargetStatus {
    Portable,
    PortableWithRewrite,
    NotPortable,
    Unknown,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionTargetAnnotation {
    pub profile_id: ProfileId,
    pub status: SemanticConversionTargetStatus,
    pub decision_ordinal: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capability: Option<CapabilityId>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub constraint: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rewrite: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionResult {
    pub conversion_version: SemanticConversionVersion,
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub source_program: Sha256Digest,
    pub destination: SemanticConversionDestination,
    pub destination_contract: DestinationContract,
    pub status: SemanticConversionStatus,
    pub comment_policy: CommentMigrationPolicy,
    pub source_summary: SemanticConversionSourceSummary,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub output: Option<SemanticConversionOutput>,
    pub node_mappings: Vec<SemanticConversionNodeMapping>,
    pub capture_mappings: Vec<SemanticConversionCaptureMapping>,
    pub equivalence: SemanticEquivalenceEvidence,
    pub issues: Vec<SemanticConversionIssue>,
    pub explanation_links: Vec<SemanticConversionExplanationLink>,
    pub target_annotations: Vec<SemanticConversionTargetAnnotation>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticConversionErrorCode {
    InvalidSemanticProgram,
    MismatchedExplanation,
    SerializationInvariant,
    DestinationReconstruction,
    EquivalenceProofFailed,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionError {
    pub code: SemanticConversionErrorCode,
    pub path: String,
    pub message: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticConversionErrors {
    pub errors: Vec<SemanticConversionError>,
}

impl SemanticConversionErrors {
    fn single(
        code: SemanticConversionErrorCode,
        path: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            errors: vec![SemanticConversionError {
                code,
                path: path.into(),
                message: message.into(),
            }],
        }
    }

    fn invalid_program(errors: ValidationErrors) -> Self {
        Self {
            errors: errors
                .errors
                .into_iter()
                .map(|error| SemanticConversionError {
                    code: SemanticConversionErrorCode::InvalidSemanticProgram,
                    path: error.path,
                    message: error.message,
                })
                .collect(),
        }
    }
}

impl fmt::Display for SemanticConversionErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} semantic conversion error(s)",
            self.errors.len()
        )
    }
}

impl Error for SemanticConversionErrors {}

/// Convert one validated canonical Semantic IR program into a semantic authoring surface.
///
/// Optional explanation evidence must identify the exact input program. It is
/// copied only as structured links and target annotations; it never influences
/// representability, rendering, or equivalence.
pub fn convert_semantic_program(
    input: &SemanticProgram,
    destination: SemanticConversionDestination,
    explanation: Option<&ExplanationDocument>,
) -> Result<SemanticConversionResult, SemanticConversionErrors> {
    input
        .validate()
        .map_err(SemanticConversionErrors::invalid_program)?;
    let source_program = digest(input)?;
    validate_explanation(input, &source_program, explanation)?;
    let source_fingerprint = alpha_fingerprint(input)?;
    let source_summary = summarize(input);
    let target_annotations = target_annotations(explanation);

    match destination {
        SemanticConversionDestination::SemanticStrling => convert_to_semantic_strling(
            input,
            source_program,
            source_fingerprint,
            source_summary,
            explanation,
            target_annotations,
        ),
        SemanticConversionDestination::SimplyBuilder => convert_to_simply(
            input,
            source_program,
            source_fingerprint,
            source_summary,
            explanation,
            target_annotations,
        ),
    }
}

fn convert_to_semantic_strling(
    input: &SemanticProgram,
    source_program: Sha256Digest,
    source_fingerprint: Sha256Digest,
    source_summary: SemanticConversionSourceSummary,
    explanation: Option<&ExplanationDocument>,
    target_annotations: Vec<SemanticConversionTargetAnnotation>,
) -> Result<SemanticConversionResult, SemanticConversionErrors> {
    let captures = capture_definitions(&input.root);
    let topology = unsupported_backreferences(&input.root);
    if !topology.is_empty() {
        let issues = topology
            .into_iter()
            .enumerate()
            .map(|(index, issue)| topology_issue(index, issue))
            .collect::<Vec<_>>();
        let explanation_links = explanation_links(&source_program, &issues, explanation);
        return Ok(SemanticConversionResult {
            conversion_version: SemanticConversionVersion::V1_0_0,
            contract_version: input.contract_version,
            specification_version: input.specification_version.clone(),
            source_program,
            destination: SemanticConversionDestination::SemanticStrling,
            destination_contract: semantic_destination_contract(),
            status: SemanticConversionStatus::Unsupported,
            comment_policy: CommentMigrationPolicy::SemanticIrOnly,
            source_summary,
            output: None,
            node_mappings: Vec::new(),
            capture_mappings: Vec::new(),
            equivalence: equivalence(
                SemanticEquivalenceStatus::NotApplicable,
                source_fingerprint,
                None,
            ),
            issues,
            explanation_links,
            target_annotations,
        });
    }

    let (names, issues) = capture_names(&captures);
    let rendered = DslRenderer::new(names).render(input);
    let source_id = SourceId::try_from(format!(
        "src:semantic-conversion.{}",
        &source_program.as_str()[..12]
    ))
    .map_err(|error| {
        SemanticConversionErrors::single(
            SemanticConversionErrorCode::SerializationInvariant,
            "$.output.source_id",
            error.to_string(),
        )
    })?;
    let document = generated_semantic_document(input, source_id.clone(), &rendered.text)?;
    let reconstructed = semantic_frontend::parse(&document).map_err(|error| {
        SemanticConversionErrors::single(
            SemanticConversionErrorCode::DestinationReconstruction,
            "$.output.text",
            error.to_string(),
        )
    })?;
    let reconstructed_fingerprint = alpha_fingerprint(&reconstructed.program)?;
    let exact = issues.is_empty();
    if exact && reconstructed_fingerprint != source_fingerprint {
        return Err(SemanticConversionErrors::single(
            SemanticConversionErrorCode::EquivalenceProofFailed,
            "$.equivalence",
            "Semantic STRling reconstruction changed normalized canonical semantics",
        ));
    }
    let text_digest = Sha256Digest::from_bytes(Sha256::digest(rendered.text.as_bytes()).into());
    let explanation_links = explanation_links(&source_program, &issues, explanation);

    Ok(SemanticConversionResult {
        conversion_version: SemanticConversionVersion::V1_0_0,
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        source_program,
        destination: SemanticConversionDestination::SemanticStrling,
        destination_contract: semantic_destination_contract(),
        status: if exact {
            SemanticConversionStatus::Exact
        } else {
            SemanticConversionStatus::Partial
        },
        comment_policy: CommentMigrationPolicy::SemanticIrOnly,
        source_summary,
        output: Some(SemanticConversionOutput::SemanticStrling {
            source_id,
            media_type: SEMANTIC_DSL_MEDIA_TYPE.to_owned(),
            text: rendered.text,
            sha256: text_digest,
        }),
        node_mappings: rendered.node_mappings,
        capture_mappings: rendered.capture_mappings,
        equivalence: if exact {
            equivalence(
                SemanticEquivalenceStatus::Proven,
                source_fingerprint,
                Some(reconstructed_fingerprint),
            )
        } else {
            equivalence(
                SemanticEquivalenceStatus::NotProven,
                source_fingerprint,
                None,
            )
        },
        issues,
        explanation_links,
        target_annotations,
    })
}

fn convert_to_simply(
    input: &SemanticProgram,
    source_program: Sha256Digest,
    source_fingerprint: Sha256Digest,
    source_summary: SemanticConversionSourceSummary,
    explanation: Option<&ExplanationDocument>,
    target_annotations: Vec<SemanticConversionTargetAnnotation>,
) -> Result<SemanticConversionResult, SemanticConversionErrors> {
    let rendered = render_simply(input, &source_program);
    let request_json = serde_json::to_string(&rendered.request).map_err(|error| {
        SemanticConversionErrors::single(
            SemanticConversionErrorCode::SerializationInvariant,
            "$.output.request",
            error.to_string(),
        )
    })?;
    let decoded = decode_simply_builder_request(&request_json).map_err(|error| {
        SemanticConversionErrors::single(
            SemanticConversionErrorCode::DestinationReconstruction,
            "$.output.request",
            error.to_string(),
        )
    })?;
    let request = replay_simply_builder_request(decoded).map_err(|error| {
        SemanticConversionErrors::single(
            SemanticConversionErrorCode::DestinationReconstruction,
            "$.output.request",
            error.to_string(),
        )
    })?;
    let CompileInput::Semantic { program } = request.input else {
        return Err(SemanticConversionErrors::single(
            SemanticConversionErrorCode::DestinationReconstruction,
            "$.output.request",
            "Simply reconstruction did not produce canonical semantic input",
        ));
    };
    let reconstructed_fingerprint = alpha_fingerprint(&program)?;
    if reconstructed_fingerprint != source_fingerprint {
        return Err(SemanticConversionErrors::single(
            SemanticConversionErrorCode::EquivalenceProofFailed,
            "$.equivalence",
            "Simply reconstruction changed normalized canonical semantics",
        ));
    }
    let explanation_links = explanation_links(&source_program, &[], explanation);

    Ok(SemanticConversionResult {
        conversion_version: SemanticConversionVersion::V1_0_0,
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        source_program,
        destination: SemanticConversionDestination::SimplyBuilder,
        destination_contract: simply_destination_contract(),
        status: SemanticConversionStatus::Exact,
        comment_policy: CommentMigrationPolicy::SemanticIrOnly,
        source_summary,
        output: Some(SemanticConversionOutput::SimplyBuilder {
            protocol_version: "1.0.0".to_owned(),
            request: rendered.request,
        }),
        node_mappings: rendered.node_mappings,
        capture_mappings: rendered.capture_mappings,
        equivalence: equivalence(
            SemanticEquivalenceStatus::Proven,
            source_fingerprint,
            Some(reconstructed_fingerprint),
        ),
        issues: Vec::new(),
        explanation_links,
        target_annotations,
    })
}

fn semantic_destination_contract() -> DestinationContract {
    DestinationContract {
        id: DestinationContractId::SemanticStrling,
        version: DestinationContractVersion::V1_0_0,
    }
}

fn simply_destination_contract() -> DestinationContract {
    DestinationContract {
        id: DestinationContractId::SimplyBuilder,
        version: DestinationContractVersion::V1_0_0,
    }
}

fn equivalence(
    status: SemanticEquivalenceStatus,
    source_fingerprint: Sha256Digest,
    reconstructed_fingerprint: Option<Sha256Digest>,
) -> SemanticEquivalenceEvidence {
    SemanticEquivalenceEvidence {
        method: SemanticEquivalenceMethod::NormalizedSemanticAlphaV1,
        status,
        source_fingerprint,
        reconstructed_fingerprint,
        excluded_evidence: vec![
            ExcludedEquivalenceEvidence::NodeIds,
            ExcludedEquivalenceEvidence::CaptureIds,
            ExcludedEquivalenceEvidence::Origins,
            ExcludedEquivalenceEvidence::Sources,
        ],
    }
}

fn digest<T: Serialize>(value: &T) -> Result<Sha256Digest, SemanticConversionErrors> {
    canonical_sha256(value)
        .map(Sha256Digest::from_bytes)
        .map_err(|error| {
            SemanticConversionErrors::single(
                SemanticConversionErrorCode::SerializationInvariant,
                "$",
                error.to_string(),
            )
        })
}

fn alpha_fingerprint(program: &SemanticProgram) -> Result<Sha256Digest, SemanticConversionErrors> {
    let captures = capture_definitions(&program.root);
    let capture_ids = captures
        .iter()
        .enumerate()
        .map(|(index, capture)| {
            (
                capture.capture_id.as_str().to_owned(),
                format!("capture:alpha/c{:06}", index + 1),
            )
        })
        .collect::<BTreeMap<_, _>>();
    let mut value = serde_json::to_value(program).map_err(|error| {
        SemanticConversionErrors::single(
            SemanticConversionErrorCode::SerializationInvariant,
            "$",
            error.to_string(),
        )
    })?;
    if let Value::Object(object) = &mut value {
        object.remove("sources");
    }
    strip_nonsemantic_evidence(&mut value, &capture_ids);
    digest(&value)
}

fn strip_nonsemantic_evidence(value: &mut Value, capture_ids: &BTreeMap<String, String>) {
    match value {
        Value::Array(items) => {
            for item in items {
                strip_nonsemantic_evidence(item, capture_ids);
            }
        }
        Value::Object(object) => {
            object.remove("node_id");
            object.remove("origin");
            if let Some(Value::String(capture_id)) = object.get_mut("capture_id") {
                if let Some(replacement) = capture_ids.get(capture_id) {
                    *capture_id = replacement.clone();
                }
            }
            for child in object.values_mut() {
                strip_nonsemantic_evidence(child, capture_ids);
            }
        }
        Value::Null | Value::Bool(_) | Value::Number(_) | Value::String(_) => {}
    }
}

fn validate_explanation(
    input: &SemanticProgram,
    source_program: &Sha256Digest,
    explanation: Option<&ExplanationDocument>,
) -> Result<(), SemanticConversionErrors> {
    let Some(explanation) = explanation else {
        return Ok(());
    };
    if &explanation.semantic_program != source_program
        || explanation.contract_version != input.contract_version
        || explanation.specification_version != input.specification_version
    {
        return Err(SemanticConversionErrors::single(
            SemanticConversionErrorCode::MismatchedExplanation,
            "$.explanation",
            "explanation identity does not correspond to the conversion input",
        ));
    }
    let explanation_nodes = explanation
        .nodes
        .iter()
        .map(|node| node.node_id.clone())
        .collect::<BTreeSet<_>>();
    if explanation_nodes != input.node_ids() {
        return Err(SemanticConversionErrors::single(
            SemanticConversionErrorCode::MismatchedExplanation,
            "$.explanation.nodes",
            "explanation node coverage does not equal the conversion input",
        ));
    }
    Ok(())
}

fn explanation_links(
    source_program: &Sha256Digest,
    issues: &[SemanticConversionIssue],
    explanation: Option<&ExplanationDocument>,
) -> Vec<SemanticConversionExplanationLink> {
    if explanation.is_none() {
        return Vec::new();
    }
    issues
        .iter()
        .filter_map(|issue| issue.source_node_id.clone())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .map(|node_id| SemanticConversionExplanationLink {
            model_version: ExplanationModelVersion::V1_0_0,
            semantic_program: source_program.clone(),
            node_id,
            evidence_class: EvidenceClass::SemanticFact,
        })
        .collect()
}

fn target_annotations(
    explanation: Option<&ExplanationDocument>,
) -> Vec<SemanticConversionTargetAnnotation> {
    let Some(target) = explanation.and_then(|value| value.target.as_ref()) else {
        return Vec::new();
    };
    let status = match target.status {
        TargetExplanationStatus::Native => SemanticConversionTargetStatus::Portable,
        TargetExplanationStatus::EquivalentRewrite => {
            SemanticConversionTargetStatus::PortableWithRewrite
        }
        TargetExplanationStatus::Unsupported => SemanticConversionTargetStatus::NotPortable,
        TargetExplanationStatus::Unresolved => SemanticConversionTargetStatus::Unknown,
    };
    let mut annotations = target
        .decisions
        .iter()
        .map(|decision| SemanticConversionTargetAnnotation {
            profile_id: target.target_profile.profile_id.clone(),
            status,
            decision_ordinal: decision.ordinal,
            capability: Some(decision.capability_id.clone()),
            constraint: None,
            rewrite: match &decision.outcome {
                TargetOutcomeExplanation::EquivalentRewrite { strategy_id, .. } => {
                    Some(strategy_id.clone())
                }
                TargetOutcomeExplanation::Native
                | TargetOutcomeExplanation::Unsupported { .. }
                | TargetOutcomeExplanation::Unresolved { .. } => None,
            },
        })
        .collect::<Vec<_>>();
    annotations.sort_by(|left, right| {
        left.capability
            .as_ref()
            .map(CapabilityId::as_str)
            .cmp(&right.capability.as_ref().map(CapabilityId::as_str))
            .then(left.decision_ordinal.cmp(&right.decision_ordinal))
    });
    annotations
}

fn generated_semantic_document(
    input: &SemanticProgram,
    source_id: SourceId,
    text: &str,
) -> Result<SourceDocument, SemanticConversionErrors> {
    let frontend_id = FrontendId::try_from("strling.semantic").map_err(identity_error)?;
    let dialect_version = DialectVersion::try_from("1.0.0").map_err(identity_error)?;
    let producer_id =
        ProducerId::try_from("strling.semantic-conversion").map_err(identity_error)?;
    Ok(SourceDocument {
        contract_version: input.contract_version,
        source_id,
        specification_version: input.specification_version.clone(),
        frontend: FrontendIdentity {
            id: frontend_id,
            dialect_version,
        },
        display_name: Some("Generated Semantic STRling conversion".to_owned()),
        content: SourceContent::Inline {
            encoding: Utf8Encoding::Utf8,
            media_type: Some(semantic_frontend::MEDIA_TYPE.to_owned()),
            text: text.to_owned(),
        },
        provenance: Provenance {
            kind: ProvenanceKind::Projected,
            producer: Some(Producer {
                id: producer_id,
                version: SEMANTIC_CONVERSION_VERSION.to_owned(),
            }),
            parent_sources: None,
            description: Some("Projected from canonical Semantic IR".to_owned()),
        },
    })
}

fn identity_error(error: impl fmt::Display) -> SemanticConversionErrors {
    SemanticConversionErrors::single(
        SemanticConversionErrorCode::SerializationInvariant,
        "$.output",
        error.to_string(),
    )
}

fn summarize(input: &SemanticProgram) -> SemanticConversionSourceSummary {
    fn visit(node: &Node, counts: &mut (usize, usize, usize)) {
        counts.0 += 1;
        match node {
            Node::Sequence { items, .. } => {
                for child in items {
                    visit(child, counts);
                }
            }
            Node::Alternation { branches, .. } => {
                for child in branches {
                    visit(child, counts);
                }
            }
            Node::Repeat { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => visit(body, counts),
            Node::Capture { body, .. } => {
                counts.1 += 1;
                visit(body, counts);
            }
            Node::Backreference { .. } => counts.2 += 1,
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. } => {}
        }
    }
    let mut counts = (0, 0, 0);
    visit(&input.root, &mut counts);
    SemanticConversionSourceSummary {
        node_count: counts.0,
        capture_count: counts.1,
        backreference_count: counts.2,
    }
}

#[derive(Clone)]
struct CaptureDefinition {
    node_id: NodeId,
    capture_id: CaptureId,
    name: Option<String>,
}

fn capture_definitions(root: &Node) -> Vec<CaptureDefinition> {
    fn visit(node: &Node, captures: &mut Vec<CaptureDefinition>) {
        match node {
            Node::Sequence { items, .. } => {
                for child in items {
                    visit(child, captures);
                }
            }
            Node::Alternation { branches, .. } => {
                for child in branches {
                    visit(child, captures);
                }
            }
            Node::Capture {
                node_id,
                capture_id,
                name,
                body,
                ..
            } => {
                captures.push(CaptureDefinition {
                    node_id: node_id.clone(),
                    capture_id: capture_id.clone(),
                    name: name.clone(),
                });
                visit(body, captures);
            }
            Node::Repeat { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => visit(body, captures),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
    }
    let mut captures = Vec::new();
    visit(root, &mut captures);
    captures
}

fn valid_semantic_identifier(value: &str) -> bool {
    value.len() <= SEMANTIC_DSL_IDENTIFIER_LIMIT
        && matches!(value.as_bytes().first(), Some(b'a'..=b'z'))
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
        && SEMANTIC_DSL_RESERVED.binary_search(&value).is_err()
}

fn capture_names(
    captures: &[CaptureDefinition],
) -> (BTreeMap<CaptureId, String>, Vec<SemanticConversionIssue>) {
    let mut used = captures
        .iter()
        .filter_map(|capture| capture.name.as_ref())
        .filter(|name| valid_semantic_identifier(name))
        .cloned()
        .collect::<BTreeSet<_>>();
    let mut names = BTreeMap::new();
    let mut issues = Vec::new();
    let mut placeholder = 1_usize;
    for capture in captures {
        let name = capture
            .name
            .as_ref()
            .filter(|name| valid_semantic_identifier(name))
            .cloned()
            .unwrap_or_else(|| loop {
                let candidate = format!("capture_{placeholder}");
                placeholder += 1;
                if used.insert(candidate.clone()) {
                    break candidate;
                }
            });
        if capture.name.as_deref() != Some(name.as_str()) {
            let first = issues.len() + 1;
            issues.push(SemanticConversionIssue {
                issue_id: format!("issue/{first:06}"),
                code: SemanticConversionIssueCode::CaptureNameSubstituted,
                category: SemanticConversionIssueCategory::Approximation,
                message: "The missing or invalid capture name was assigned a deterministic textual placeholder."
                    .to_owned(),
                source_node_id: Some(capture.node_id.clone()),
                source_capture_id: Some(capture.capture_id.clone()),
                replacement: Some(name.clone()),
            });
            issues.push(SemanticConversionIssue {
                issue_id: format!("issue/{:06}", first + 1),
                code: SemanticConversionIssueCode::ManualCaptureNameRequired,
                category: SemanticConversionIssueCategory::ManualDecision,
                message: "Review and replace the generated capture name before treating the text as authoritative."
                    .to_owned(),
                source_node_id: Some(capture.node_id.clone()),
                source_capture_id: Some(capture.capture_id.clone()),
                replacement: Some(name.clone()),
            });
        }
        names.insert(capture.capture_id.clone(), name);
    }
    (names, issues)
}

#[derive(Clone)]
struct UnsupportedBackreference {
    code: SemanticConversionIssueCode,
    node_id: NodeId,
    capture_id: CaptureId,
}

fn unsupported_backreferences(root: &Node) -> Vec<UnsupportedBackreference> {
    fn visit(
        node: &Node,
        active: &mut Vec<CaptureId>,
        completed: &mut BTreeSet<CaptureId>,
        issues: &mut Vec<UnsupportedBackreference>,
    ) {
        match node {
            Node::Sequence { items, .. } => {
                for child in items {
                    visit(child, active, completed, issues);
                }
            }
            Node::Alternation { branches, .. } => {
                for child in branches {
                    visit(child, active, completed, issues);
                }
            }
            Node::Capture {
                capture_id, body, ..
            } => {
                active.push(capture_id.clone());
                visit(body, active, completed, issues);
                active.pop();
                completed.insert(capture_id.clone());
            }
            Node::Backreference {
                node_id,
                capture_id,
                ..
            } if !completed.contains(capture_id) => {
                let code = if active.last() == Some(capture_id) {
                    SemanticConversionIssueCode::SelfBackreferenceUnsupported
                } else if active.contains(capture_id) {
                    SemanticConversionIssueCode::RecursiveBackreferenceUnsupported
                } else {
                    SemanticConversionIssueCode::ForwardBackreferenceUnsupported
                };
                issues.push(UnsupportedBackreference {
                    code,
                    node_id: node_id.clone(),
                    capture_id: capture_id.clone(),
                });
            }
            Node::Repeat { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => visit(body, active, completed, issues),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
    }
    let mut issues = Vec::new();
    visit(root, &mut Vec::new(), &mut BTreeSet::new(), &mut issues);
    issues
}

fn topology_issue(index: usize, issue: UnsupportedBackreference) -> SemanticConversionIssue {
    let message = match issue.code {
        SemanticConversionIssueCode::ForwardBackreferenceUnsupported => {
            "Semantic STRling requires the referenced capture to be completed before this backreference."
        }
        SemanticConversionIssueCode::SelfBackreferenceUnsupported => {
            "Semantic STRling cannot represent a backreference within its own active capture."
        }
        SemanticConversionIssueCode::RecursiveBackreferenceUnsupported => {
            "Semantic STRling cannot represent a backreference to an active enclosing capture."
        }
        SemanticConversionIssueCode::CommentsNotAvailable
        | SemanticConversionIssueCode::CaptureNameSubstituted
        | SemanticConversionIssueCode::ManualCaptureNameRequired => {
            "Semantic STRling backreference topology is unsupported."
        }
    };
    SemanticConversionIssue {
        issue_id: format!("issue/{:06}", index + 1),
        code: issue.code,
        category: SemanticConversionIssueCategory::Unsupported,
        message: message.to_owned(),
        source_node_id: Some(issue.node_id),
        source_capture_id: Some(issue.capture_id),
        replacement: None,
    }
}

struct RenderedDsl {
    text: String,
    node_mappings: Vec<SemanticConversionNodeMapping>,
    capture_mappings: Vec<SemanticConversionCaptureMapping>,
}

struct DslRenderer {
    text: String,
    capture_names: BTreeMap<CaptureId, String>,
    node_mappings: Vec<SemanticConversionNodeMapping>,
    capture_mappings: Vec<SemanticConversionCaptureMapping>,
    node_ordinals: BTreeMap<NodeId, usize>,
}

impl DslRenderer {
    fn new(capture_names: BTreeMap<CaptureId, String>) -> Self {
        Self {
            text: String::new(),
            capture_names,
            node_mappings: Vec::new(),
            capture_mappings: Vec::new(),
            node_ordinals: BTreeMap::new(),
        }
    }

    fn render(mut self, input: &SemanticProgram) -> RenderedDsl {
        assign_node_ordinals(&input.root, &mut self.node_ordinals);
        self.text.push_str("semantic strling 1.0;\n");
        self.text.push_str(match input.case_matching {
            CaseMatching::Sensitive => "case sensitive;\n\n",
            CaseMatching::Insensitive => "case insensitive;\n\n",
        });
        self.text.push_str("pattern ");
        self.render_node(&input.root, 0);
        self.text.push('\n');
        self.node_mappings
            .sort_by(|left, right| left.source_node_id.cmp(&right.source_node_id));
        self.capture_mappings
            .sort_by(|left, right| left.source_capture_id.cmp(&right.source_capture_id));
        RenderedDsl {
            text: self.text,
            node_mappings: self.node_mappings,
            capture_mappings: self.capture_mappings,
        }
    }

    fn render_node(&mut self, node: &Node, indentation: usize) {
        let start = self.text.len();
        match node {
            Node::Empty { .. } => self.text.push_str("empty;"),
            Node::Sequence { items, .. } => self.render_children("sequence", items, indentation),
            Node::Alternation { branches, .. } => {
                self.render_children("choice", branches, indentation);
            }
            Node::Literal { text, .. } => {
                self.text.push_str("text ");
                render_string(text, &mut self.text);
                self.text.push(';');
            }
            Node::Wildcard {
                line_terminators, ..
            } => self.text.push_str(match line_terminators {
                LineTerminators::Include => "any character including line terminators;",
                LineTerminators::Exclude => "any character excluding line terminators;",
            }),
            Node::CharacterSet {
                negated, members, ..
            } => {
                self.text.push_str(if *negated {
                    "character except {\n"
                } else {
                    "character from {\n"
                });
                for member in members {
                    indent(indentation + 1, &mut self.text);
                    render_set_member(member, &mut self.text);
                    self.text.push('\n');
                }
                indent(indentation, &mut self.text);
                self.text.push('}');
            }
            Node::Repeat {
                body,
                min,
                max,
                mode,
                ..
            } => {
                self.text.push_str("repeat from ");
                self.text.push_str(&min.to_string());
                self.text.push_str(" to ");
                match max {
                    RepetitionMaximum::Bounded(maximum) => {
                        self.text.push_str(&maximum.to_string());
                    }
                    RepetitionMaximum::Unbounded => self.text.push_str("unbounded"),
                }
                self.text.push_str(" using ");
                self.text.push_str(repetition_mode(*mode));
                self.text.push_str(" {\n");
                indent(indentation + 1, &mut self.text);
                self.render_node(body, indentation + 1);
                self.text.push('\n');
                indent(indentation, &mut self.text);
                self.text.push('}');
            }
            Node::Position { position, .. } => self.text.push_str(position_source(*position)),
            Node::Capture {
                capture_id, body, ..
            } => {
                self.text.push_str("capture ");
                let identifier_start = self.text.len();
                let name = self
                    .capture_names
                    .get(capture_id)
                    .expect("validated capture has a conversion name")
                    .clone();
                self.text.push_str(&name);
                let identifier_end = self.text.len();
                self.capture_mappings
                    .push(SemanticConversionCaptureMapping {
                        source_capture_id: capture_id.clone(),
                        destination_key: name,
                        identifier_span: Some(ConversionByteSpan {
                            start: identifier_start as u64,
                            end: identifier_end as u64,
                        }),
                    });
                self.text.push_str(" {\n");
                indent(indentation + 1, &mut self.text);
                self.render_node(body, indentation + 1);
                self.text.push('\n');
                indent(indentation, &mut self.text);
                self.text.push('}');
            }
            Node::Backreference { capture_id, .. } => {
                self.text.push_str("same text as ");
                self.text.push_str(
                    self.capture_names
                        .get(capture_id)
                        .expect("validated backreference resolves to a conversion name"),
                );
                self.text.push(';');
            }
            Node::Lookaround {
                direction,
                polarity,
                body,
                ..
            } => {
                self.text.push_str(match polarity {
                    AssertionPolarity::Positive => "if ",
                    AssertionPolarity::Negative => "unless ",
                });
                self.text.push_str(match direction {
                    LookaroundDirection::Ahead => "followed by {\n",
                    LookaroundDirection::Behind => "preceded by {\n",
                });
                indent(indentation + 1, &mut self.text);
                self.render_node(body, indentation + 1);
                self.text.push('\n');
                indent(indentation, &mut self.text);
                self.text.push('}');
            }
            Node::Atomic { body, .. } => {
                self.text.push_str("without backtracking {\n");
                indent(indentation + 1, &mut self.text);
                self.render_node(body, indentation + 1);
                self.text.push('\n');
                indent(indentation, &mut self.text);
                self.text.push('}');
            }
        }
        let ordinal = self
            .node_ordinals
            .get(node.node_id())
            .expect("node ordinal was preassigned");
        self.node_mappings.push(SemanticConversionNodeMapping {
            source_node_id: node.node_id().clone(),
            destination_key: format!("semantic-output/node/{ordinal:06}"),
            byte_span: Some(ConversionByteSpan {
                start: start as u64,
                end: self.text.len() as u64,
            }),
        });
    }

    fn render_children(&mut self, keyword: &str, children: &[Node], indentation: usize) {
        self.text.push_str(keyword);
        self.text.push_str(" {\n");
        for child in children {
            indent(indentation + 1, &mut self.text);
            self.render_node(child, indentation + 1);
            self.text.push('\n');
        }
        indent(indentation, &mut self.text);
        self.text.push('}');
    }
}

fn assign_node_ordinals(node: &Node, ordinals: &mut BTreeMap<NodeId, usize>) {
    let next = ordinals.len() + 1;
    ordinals.insert(node.node_id().clone(), next);
    match node {
        Node::Sequence { items, .. } => {
            for child in items {
                assign_node_ordinals(child, ordinals);
            }
        }
        Node::Alternation { branches, .. } => {
            for child in branches {
                assign_node_ordinals(child, ordinals);
            }
        }
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => assign_node_ordinals(body, ordinals),
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => {}
    }
}

fn render_set_member(member: &CharacterSetMember, output: &mut String) {
    match member {
        CharacterSetMember::Literal { value } => {
            output.push_str("scalar ");
            render_string(&value.to_string(), output);
        }
        CharacterSetMember::Range { start, end } => {
            output.push_str("range ");
            render_string(&start.to_string(), output);
            output.push_str(" through ");
            render_string(&end.to_string(), output);
        }
        CharacterSetMember::Builtin {
            name,
            domain,
            negated,
        } => {
            if *negated {
                output.push_str("not ");
            }
            output.push_str(match domain {
                CharacterDomain::Ascii => "ascii ",
                CharacterDomain::TargetNative => "target ",
                CharacterDomain::Unicode => "unicode ",
            });
            output.push_str(builtin_name(*name));
        }
        CharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => {
            if *negated {
                output.push_str("not ");
            }
            output.push_str("property ");
            render_string(property, output);
            if let Some(value) = value {
                output.push_str(" value ");
                render_string(value, output);
            }
        }
    }
    output.push(';');
}

fn render_string(value: &str, output: &mut String) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{0008}' => output.push_str("\\b"),
            '\u{000c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            '\0' => output.push_str("\\0"),
            value if value <= '\u{001f}' || value == '\u{007f}' => {
                use std::fmt::Write;
                let _ = write!(output, "\\u{{{:X}}}", value as u32);
            }
            value => output.push(value),
        }
    }
    output.push('"');
}

fn indent(level: usize, output: &mut String) {
    for _ in 0..level {
        output.push_str("    ");
    }
}

fn builtin_name(name: BuiltinClassName) -> &'static str {
    match name {
        BuiltinClassName::Digit => "digit",
        BuiltinClassName::Word => "word",
        BuiltinClassName::Whitespace => "whitespace",
    }
}

fn repetition_mode(mode: RepetitionMode) -> &'static str {
    match mode {
        RepetitionMode::Greedy => "greedy",
        RepetitionMode::Lazy => "lazy",
        RepetitionMode::Possessive => "possessive",
    }
}

fn position_source(position: PositionKind) -> &'static str {
    match position {
        PositionKind::InputStart => "at input start;",
        PositionKind::InputEnd => "at input end;",
        PositionKind::LineStart => "at line start;",
        PositionKind::LineEnd => "at line end;",
        PositionKind::WordBoundary => "at word boundary;",
        PositionKind::NotWordBoundary => "not at word boundary;",
        PositionKind::EndBeforeFinalLineTerminator => "before final line terminator;",
    }
}

struct RenderedSimply {
    request: Value,
    node_mappings: Vec<SemanticConversionNodeMapping>,
    capture_mappings: Vec<SemanticConversionCaptureMapping>,
}

fn render_simply(input: &SemanticProgram, source_program: &Sha256Digest) -> RenderedSimply {
    let mut node_ordinals = BTreeMap::new();
    assign_node_ordinals(&input.root, &mut node_ordinals);
    let capture_ids = capture_definitions(&input.root)
        .into_iter()
        .enumerate()
        .map(|(index, capture)| (capture.capture_id, format!("c{:06}", index + 1)))
        .collect::<BTreeMap<_, _>>();
    let mut steps = Vec::new();
    render_simply_node(&input.root, &node_ordinals, &capture_ids, &mut steps);
    let mut node_mappings = node_ordinals
        .iter()
        .map(|(node_id, ordinal)| SemanticConversionNodeMapping {
            source_node_id: node_id.clone(),
            destination_key: format!("n{ordinal:06}"),
            byte_span: None,
        })
        .collect::<Vec<_>>();
    node_mappings.sort_by(|left, right| left.source_node_id.cmp(&right.source_node_id));
    let mut capture_mappings = capture_ids
        .iter()
        .map(|(capture_id, key)| SemanticConversionCaptureMapping {
            source_capture_id: capture_id.clone(),
            destination_key: key.clone(),
            identifier_span: None,
        })
        .collect::<Vec<_>>();
    capture_mappings.sort_by(|left, right| left.source_capture_id.cmp(&right.source_capture_id));
    let root_ordinal = node_ordinals
        .get(input.root.node_id())
        .expect("root node ordinal exists");
    RenderedSimply {
        request: json!({
            "protocol_version": "1.0.0",
            "contract_version": input.contract_version,
            "specification_version": input.specification_version,
            "identity_namespace": format!("migration.{}", &source_program.as_str()[..12]),
            "semantic_options": {
                "case_matching": input.case_matching,
                "text_model": "unicode_scalar_values",
                "builtin_character_domain": "unicode",
                "wildcard_line_terminators": "exclude"
            },
            "steps": steps,
            "root_step_id": format!("n{root_ordinal:06}"),
            "compile": {
                "requested_outputs": ["semantic"],
                "compiler_options": {
                    "partial_semantics": "forbid",
                    "diagnostic_policy": { "minimum_severity": "info" }
                }
            }
        }),
        node_mappings,
        capture_mappings,
    }
}

fn render_simply_node(
    node: &Node,
    node_ordinals: &BTreeMap<NodeId, usize>,
    capture_ids: &BTreeMap<CaptureId, String>,
    steps: &mut Vec<Value>,
) {
    match node {
        Node::Sequence { items, .. } => {
            for child in items {
                render_simply_node(child, node_ordinals, capture_ids, steps);
            }
        }
        Node::Alternation { branches, .. } => {
            for child in branches {
                render_simply_node(child, node_ordinals, capture_ids, steps);
            }
        }
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => {
            render_simply_node(body, node_ordinals, capture_ids, steps);
        }
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => {}
    }
    let ordinal = node_ordinals
        .get(node.node_id())
        .expect("node ordinal was preassigned");
    let step_id = format!("n{ordinal:06}");
    let step = match node {
        Node::Empty { .. } => json!({
            "step_id": step_id,
            "operation": "empty",
            "arguments": {}
        }),
        Node::Literal { text, .. } => json!({
            "step_id": step_id,
            "operation": "literal",
            "arguments": { "text": text }
        }),
        Node::Wildcard {
            line_terminators, ..
        } => json!({
            "step_id": step_id,
            "operation": "wildcard",
            "arguments": { "line_terminators": line_terminators }
        }),
        Node::CharacterSet {
            negated, members, ..
        } => json!({
            "step_id": step_id,
            "operation": "character_set",
            "arguments": {
                "negated": negated,
                "members": members
            }
        }),
        Node::Sequence { items, .. } => json!({
            "step_id": step_id,
            "operation": "sequence",
            "arguments": {
                "values": child_step_ids(items, node_ordinals)
            }
        }),
        Node::Alternation { branches, .. } => json!({
            "step_id": step_id,
            "operation": "alternation",
            "arguments": {
                "values": child_step_ids(branches, node_ordinals)
            }
        }),
        Node::Repeat {
            body,
            min,
            max,
            mode,
            ..
        } => json!({
            "step_id": step_id,
            "operation": "repeat",
            "arguments": {
                "value": node_step_id(body, node_ordinals),
                "min": min,
                "max": max,
                "mode": mode
            }
        }),
        Node::Position { position, .. } => json!({
            "step_id": step_id,
            "operation": "position",
            "arguments": { "position": position }
        }),
        Node::Capture {
            capture_id,
            name,
            body,
            ..
        } => {
            let mut arguments = serde_json::Map::new();
            arguments.insert("value".to_owned(), json!(node_step_id(body, node_ordinals)));
            arguments.insert(
                "capture_key".to_owned(),
                json!(capture_ids
                    .get(capture_id)
                    .expect("capture key was preassigned")),
            );
            if let Some(name) = name {
                arguments.insert("name".to_owned(), json!(name));
            }
            json!({
                "step_id": step_id,
                "operation": "capture",
                "arguments": arguments
            })
        }
        Node::Backreference { capture_id, .. } => json!({
            "step_id": step_id,
            "operation": "backreference",
            "arguments": {
                "capture_key": capture_ids
                    .get(capture_id)
                    .expect("validated backreference resolves to a capture key")
            }
        }),
        Node::Lookaround {
            direction,
            polarity,
            body,
            ..
        } => json!({
            "step_id": step_id,
            "operation": "lookaround",
            "arguments": {
                "value": node_step_id(body, node_ordinals),
                "direction": direction,
                "polarity": polarity
            }
        }),
        Node::Atomic { body, .. } => json!({
            "step_id": step_id,
            "operation": "atomic",
            "arguments": { "value": node_step_id(body, node_ordinals) }
        }),
    };
    steps.push(step);
}

fn child_step_ids(children: &[Node], ordinals: &BTreeMap<NodeId, usize>) -> Vec<String> {
    children
        .iter()
        .map(|child| node_step_id(child, ordinals))
        .collect()
}

fn node_step_id(node: &Node, ordinals: &BTreeMap<NodeId, usize>) -> String {
    format!(
        "n{:06}",
        ordinals
            .get(node.node_id())
            .expect("node ordinal was preassigned")
    )
}
