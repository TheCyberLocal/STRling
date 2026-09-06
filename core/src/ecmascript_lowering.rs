//! Pure lowering from normalized Semantic IR and a certified portability plan.
//!
//! This module produces target-specific structure only. It does not serialize
//! regex syntax, construct a `TargetArtifact` or `RegExp`, execute JavaScript,
//! import PCRE2 target code, or consult any ambient state.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use crate::capability_evaluation::{
    emitted_requirement, emitted_wildcard_requirement, LookbehindLength, PositionRequirement,
    RequirementKind, RequirementPolarity,
};
use crate::diagnostic::{
    Advice, AdviceKind, CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode,
    DiagnosticOccurrence, Severity, SeverityBasis,
};
use crate::portability_planning::{
    PortabilityPlan, RequirementIdentity, RequirementPlanningDisposition,
    RewriteCertificationEvidence, RewriteProofEvaluation, RewriteStrategyId, SemanticRewritePlan,
};
use crate::post_lowering_requirements::{
    classify_introduced_requirements, reconcile_emitted_requirements, EmittedRequirement,
    PostLoweringRequirementFailureKind,
};
use crate::semantic::{
    AssertionPolarity, BuiltinClassName, CaseMatching, CharacterDomain, CharacterSetMember,
    LineTerminators, LookaroundDirection, Node, Normalization, PositionKind, RepetitionMaximum,
    RepetitionMode, SemanticProgram,
};
use crate::semantic_compatibility::{
    native_line_anchors_are_canonical, native_wildcard_is_canonical, native_word_is_canonical,
};
use crate::source::{
    CaptureId, ContractVersion, NodeId, Sha256Digest, SourceSpan, SpecificationVersion,
};
use crate::target::{
    ArtifactPortabilityStatus, EngineOptionValue, OptionId, OptionSelection, OptionStage,
    PortabilityStatus, TargetProfile, TargetProfileReference,
};
use crate::validation::{
    canonical_sha256, Validate, ValidationCode, ValidationError, ValidationErrors,
};

/// Maximum Semantic IR nodes admitted by one lowering invocation.
pub const MAX_ECMASCRIPT_LOWERING_NODES: usize = 65_536;

/// Maximum Semantic IR nesting admitted by one lowering invocation.
pub const MAX_ECMASCRIPT_LOWERING_DEPTH: usize = 128;

/// Stable target-lowering failure categories.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum EcmascriptLoweringErrorCode {
    InvalidSemanticProgram,
    ResourceLimitExceeded,
    InvalidTargetProfile,
    NonEcmascriptTarget,
    IncompatibleTargetProfile,
    InvalidPortabilityPlan,
    ProgramFingerprintMismatch,
    TargetProfileMismatch,
    VersionMismatch,
    UnresolvedRequirement,
    UnsupportedRequirement,
    MalformedRewritePlan,
    CaptureResolution,
    IntroducedRequirement,
    InvalidLoweringPlan,
}

impl EcmascriptLoweringErrorCode {
    const fn diagnostic_code(self) -> &'static str {
        match self {
            Self::InvalidSemanticProgram => "STRL-ECMASCRIPT_LOWERING-0001",
            Self::ResourceLimitExceeded => "STRL-ECMASCRIPT_LOWERING-0002",
            Self::InvalidTargetProfile => "STRL-ECMASCRIPT_LOWERING-0003",
            Self::NonEcmascriptTarget => "STRL-ECMASCRIPT_LOWERING-0004",
            Self::IncompatibleTargetProfile => "STRL-ECMASCRIPT_LOWERING-0005",
            Self::InvalidPortabilityPlan => "STRL-ECMASCRIPT_LOWERING-0006",
            Self::ProgramFingerprintMismatch => "STRL-ECMASCRIPT_LOWERING-0007",
            Self::TargetProfileMismatch => "STRL-ECMASCRIPT_LOWERING-0008",
            Self::VersionMismatch => "STRL-ECMASCRIPT_LOWERING-0009",
            Self::UnresolvedRequirement => "STRL-ECMASCRIPT_LOWERING-0010",
            Self::UnsupportedRequirement => "STRL-ECMASCRIPT_LOWERING-0011",
            Self::MalformedRewritePlan => "STRL-ECMASCRIPT_LOWERING-0012",
            Self::CaptureResolution => "STRL-ECMASCRIPT_LOWERING-0013",
            Self::IntroducedRequirement => "STRL-ECMASCRIPT_LOWERING-0014",
            Self::InvalidLoweringPlan => "STRL-ECMASCRIPT_LOWERING-0015",
        }
    }

    const fn category(self) -> DiagnosticCategory {
        match self {
            Self::InvalidSemanticProgram | Self::CaptureResolution => {
                DiagnosticCategory::SemanticValidity
            }
            Self::ResourceLimitExceeded => DiagnosticCategory::ResourceLimit,
            Self::NonEcmascriptTarget
            | Self::IncompatibleTargetProfile
            | Self::UnresolvedRequirement
            | Self::UnsupportedRequirement
            | Self::IntroducedRequirement => DiagnosticCategory::TargetCapability,
            Self::InvalidTargetProfile
            | Self::InvalidPortabilityPlan
            | Self::ProgramFingerprintMismatch
            | Self::TargetProfileMismatch
            | Self::VersionMismatch
            | Self::MalformedRewritePlan
            | Self::InvalidLoweringPlan => DiagnosticCategory::Internal,
        }
    }
}

/// All-or-nothing failure from ECMAScript target lowering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptLoweringFailure {
    pub code: EcmascriptLoweringErrorCode,
    pub diagnostics: Vec<Diagnostic>,
}

impl fmt::Display for EcmascriptLoweringFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "ECMAScript target lowering failed with {} diagnostic(s)",
            self.diagnostics.len()
        )
    }
}

impl Error for EcmascriptLoweringFailure {}

/// ECMAScript interpretation of global case intent, retained outside pattern text.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EcmascriptCaseMatching {
    Sensitive,
    Insensitive,
}

/// One exact profile option selected before serialization or execution.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptOptionPlan {
    pub option_id: OptionId,
    pub stage: OptionStage,
    pub value: EngineOptionValue,
    pub selection: OptionSelection,
}

/// Provenance carried by every target operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptProvenance {
    pub semantic_node_ids: Vec<NodeId>,
    pub source_spans: Vec<SourceSpan>,
    pub applied_rewrite: Option<RequirementIdentity>,
}

/// ECMAScript wildcard behavior without syntax spelling.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EcmascriptWildcard {
    ExcludeLineTerminators,
    CanonicalExcludeLineTerminators,
    IncludeLineTerminators,
}

/// ECMAScript built-in character-class identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EcmascriptBuiltinClass {
    Digit,
    Word,
    Whitespace,
}

/// ECMAScript built-in class interpretation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EcmascriptCharacterDomain {
    Ascii,
    TargetNative,
    Unicode,
    CanonicalUnicodeWord,
}

/// Structured character-set member awaiting serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum EcmascriptCharacterSetMember {
    Literal {
        value: char,
    },
    Range {
        start: char,
        end: char,
    },
    Builtin {
        name: EcmascriptBuiltinClass,
        domain: EcmascriptCharacterDomain,
        negated: bool,
    },
    UnicodeProperty {
        property: String,
        value: Option<String>,
        negated: bool,
    },
}

/// ECMAScript repetition maximum without quantifier punctuation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EcmascriptRepetitionMaximum {
    Bounded(u64),
    Unbounded,
}

/// ECMAScript repetition backtracking behavior.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EcmascriptRepetitionMode {
    Greedy,
    Lazy,
}

/// ECMAScript position identity without anchor spelling.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EcmascriptPosition {
    InputStart,
    InputEnd,
    LineStart,
    LineEnd,
    WordBoundary,
    NotWordBoundary,
    EndBeforeFinalLineTerminator,
    CanonicalLineStart,
    CanonicalLineEnd,
    CanonicalWordBoundary,
    CanonicalNotWordBoundary,
    CanonicalEndBeforeFinalLineTerminator,
}

/// ECMAScript assertion identity without grouping punctuation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EcmascriptLookaround {
    PositiveAhead,
    NegativeAhead,
    PositiveBehind,
    NegativeBehind,
}

/// Closed ECMAScript operation vocabulary before regex serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum EcmascriptOperation {
    Empty,
    Sequence(Vec<EcmascriptNode>),
    Alternation(Vec<EcmascriptNode>),
    Literal(String),
    Wildcard(EcmascriptWildcard),
    CharacterSet {
        negated: bool,
        members: Vec<EcmascriptCharacterSetMember>,
    },
    Repeat {
        body: Box<EcmascriptNode>,
        min: u64,
        max: EcmascriptRepetitionMaximum,
        mode: EcmascriptRepetitionMode,
    },
    Position(EcmascriptPosition),
    Capture {
        slot: u32,
        capture_id: CaptureId,
        name: Option<String>,
        body: Box<EcmascriptNode>,
    },
    Backreference {
        slot: u32,
        capture_id: CaptureId,
        name: Option<String>,
    },
    Lookaround {
        assertion: EcmascriptLookaround,
        body: Box<EcmascriptNode>,
    },
}

/// One ECMAScript target node with exact semantic provenance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptNode {
    pub provenance: EcmascriptProvenance,
    pub operation: EcmascriptOperation,
}

/// Deterministic logical-capture to ECMAScript slot assignment.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptCapture {
    pub slot: u32,
    pub capture_id: CaptureId,
    pub name: Option<String>,
    pub definition_node_id: NodeId,
    pub source_spans: Vec<SourceSpan>,
}

/// Exact completed planner decision retained by the target plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptRequirementResolution {
    pub identity: RequirementIdentity,
    pub status: ArtifactPortabilityStatus,
    pub rewrite_strategy: Option<RewriteStrategyId>,
}

/// Certified semantic rewrite actually applied by ECMAScript lowering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptAppliedRewrite {
    pub identity: RequirementIdentity,
    pub strategy_id: RewriteStrategyId,
    pub certification: RewriteCertificationEvidence,
    pub affected_node_ids: Vec<NodeId>,
    pub proof: Vec<RewriteProofEvaluation>,
    pub target_profile: TargetProfileReference,
}

/// Complete, deterministic, pre-serialization ECMAScript target representation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptLoweringPlan {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub semantic_program: Sha256Digest,
    pub target_profile: TargetProfileReference,
    pub portability_status: ArtifactPortabilityStatus,
    pub case_matching: EcmascriptCaseMatching,
    pub options: Vec<EcmascriptOptionPlan>,
    pub captures: Vec<EcmascriptCapture>,
    /// Requirements inherent in Semantic IR and planned before lowering.
    pub semantic_requirements: Vec<EcmascriptRequirementResolution>,
    /// Authoritative union of semantic and lowering-introduced requirements.
    pub requirements: Vec<EcmascriptRequirementResolution>,
    pub applied_rewrites: Vec<EcmascriptAppliedRewrite>,
    pub root: EcmascriptNode,
}

struct CaptureTable {
    ordered: Vec<EcmascriptCapture>,
    by_id: BTreeMap<CaptureId, EcmascriptCapture>,
}

struct RewriteTable<'a> {
    by_node: BTreeMap<NodeId, (&'a RequirementIdentity, &'a SemanticRewritePlan)>,
}

/// Lower one exact semantic program and certified plan into structured ECMAScript data.
pub fn lower_ecmascript(
    input: &SemanticProgram,
    target: &TargetProfile,
    portability: &PortabilityPlan,
) -> Result<EcmascriptLoweringPlan, EcmascriptLoweringFailure> {
    enforce_resource_limits(input)?;
    if let Err(errors) = input.validate() {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::InvalidSemanticProgram,
            Some(input.root.node_id()),
            format!("normalized Semantic IR is invalid: {errors}"),
        ));
    }
    if input.normalization != Normalization::CanonicalV1 {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::InvalidSemanticProgram,
            Some(input.root.node_id()),
            "ECMAScript lowering requires canonical-v1 Semantic IR",
        ));
    }
    if let Err(errors) = target.validate() {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::InvalidTargetProfile,
            Some(input.root.node_id()),
            format!("ECMAScript target profile is invalid: {errors}"),
        ));
    }
    if target.engine.id.as_str() != "ecmascript" {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::NonEcmascriptTarget,
            Some(input.root.node_id()),
            format!(
                "ECMAScript lowering cannot consume engine {}",
                target.engine.id.as_str()
            ),
        ));
    }
    if target.contract_version != input.contract_version
        || target
            .compatible_specification_versions
            .binary_search(&input.specification_version)
            .is_err()
    {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::IncompatibleTargetProfile,
            Some(input.root.node_id()),
            "ECMAScript target profile does not certify the semantic contract/specification versions",
        ));
    }
    if let Err(errors) = portability.validate() {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::InvalidPortabilityPlan,
            Some(input.root.node_id()),
            format!("portability plan is malformed: {errors}"),
        ));
    }

    let semantic_program = canonical_sha256(input)
        .map(Sha256Digest::from_bytes)
        .map_err(|error| {
            failure(
                input,
                EcmascriptLoweringErrorCode::ProgramFingerprintMismatch,
                Some(input.root.node_id()),
                format!("semantic program fingerprint could not be derived: {error}"),
            )
        })?;
    if portability.semantic_program != semantic_program {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::ProgramFingerprintMismatch,
            Some(input.root.node_id()),
            "portability plan was not produced for the supplied Semantic IR bytes",
        ));
    }
    let target_profile = target.reference().map_err(|errors| {
        failure(
            input,
            EcmascriptLoweringErrorCode::InvalidTargetProfile,
            Some(input.root.node_id()),
            format!("ECMAScript target profile reference could not be derived: {errors}"),
        )
    })?;
    if portability.target_profile != target_profile {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::TargetProfileMismatch,
            Some(input.root.node_id()),
            "portability plan does not name the exact supplied ECMAScript profile revision and fingerprint",
        ));
    }
    if portability.contract_version != input.contract_version
        || portability.specification_version != input.specification_version
    {
        return Err(failure(
            input,
            EcmascriptLoweringErrorCode::VersionMismatch,
            Some(input.root.node_id()),
            "portability plan versions do not match the supplied Semantic IR",
        ));
    }

    let portability_status = completed_status(input, portability)?;
    let captures = collect_captures(input)?;
    let rewrites = validate_rewrites(input, portability)?;
    let semantic_requirements: Vec<_> = portability
        .decisions
        .iter()
        .map(|decision| match &decision.disposition {
            RequirementPlanningDisposition::Native(_) => EcmascriptRequirementResolution {
                identity: decision.identity.clone(),
                status: ArtifactPortabilityStatus::Native,
                rewrite_strategy: None,
            },
            RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
                EcmascriptRequirementResolution {
                    identity: decision.identity.clone(),
                    status: ArtifactPortabilityStatus::EquivalentRewrite,
                    rewrite_strategy: Some(rewrite.rewrite_plan.strategy_id),
                }
            }
            RequirementPlanningDisposition::Unsupported(_)
            | RequirementPlanningDisposition::Unresolved(_) => {
                unreachable!("completed status rejects incomplete dispositions")
            }
        })
        .collect();
    let applied_rewrites = portability
        .decisions
        .iter()
        .filter_map(|decision| match &decision.disposition {
            RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
                Some(EcmascriptAppliedRewrite {
                    identity: decision.identity.clone(),
                    strategy_id: rewrite.rewrite_plan.strategy_id,
                    certification: rewrite.rewrite_plan.certification.clone(),
                    affected_node_ids: rewrite.rewrite_plan.affected_node_ids.clone(),
                    proof: rewrite.rewrite_plan.proof.clone(),
                    target_profile: rewrite.rewrite_plan.target_profile.clone(),
                })
            }
            RequirementPlanningDisposition::Native(_)
            | RequirementPlanningDisposition::Unsupported(_)
            | RequirementPlanningDisposition::Unresolved(_) => None,
        })
        .collect();
    let options = target
        .options
        .iter()
        .map(|option| EcmascriptOptionPlan {
            option_id: option.option_id.clone(),
            stage: option.stage,
            value: option.value.clone(),
            selection: option.selection,
        })
        .collect();

    let case_matching = match input.case_matching {
        CaseMatching::Sensitive => EcmascriptCaseMatching::Sensitive,
        CaseMatching::Insensitive => EcmascriptCaseMatching::Insensitive,
    };
    let root = lower_node(input, target, &input.root, &captures, &rewrites)?;
    let emitted =
        extract_ecmascript_emitted_requirements(&root, case_matching, &semantic_requirements);
    let native_source_identities: Vec<_> = semantic_requirements
        .iter()
        .filter(|requirement| requirement.status == ArtifactPortabilityStatus::Native)
        .map(|requirement| requirement.identity.clone())
        .collect();
    let introduced = reconcile_emitted_requirements(
        input.contract_version,
        &input.specification_version,
        target,
        semantic_requirements.len(),
        &native_source_identities,
        emitted,
    )
    .map_err(|error| {
        let code = match error.kind {
            PostLoweringRequirementFailureKind::RequirementLimitExceeded => {
                EcmascriptLoweringErrorCode::ResourceLimitExceeded
            }
            PostLoweringRequirementFailureKind::InvalidProfile
            | PostLoweringRequirementFailureKind::Unsupported
            | PostLoweringRequirementFailureKind::ConstraintViolation
            | PostLoweringRequirementFailureKind::Unknown => {
                EcmascriptLoweringErrorCode::IntroducedRequirement
            }
        };
        failure(input, code, error.node_id.as_ref(), error.to_string())
    })?;
    let mut requirements = semantic_requirements.clone();
    requirements.extend(introduced.into_iter().map(|requirement| {
        EcmascriptRequirementResolution {
            identity: requirement.identity,
            status: ArtifactPortabilityStatus::Native,
            rewrite_strategy: None,
        }
    }));
    let plan = EcmascriptLoweringPlan {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        semantic_program,
        target_profile,
        portability_status,
        case_matching,
        options,
        captures: captures.ordered.clone(),
        semantic_requirements,
        requirements,
        applied_rewrites,
        root,
    };
    plan.validate().map_err(|errors| {
        failure(
            input,
            EcmascriptLoweringErrorCode::InvalidLoweringPlan,
            Some(input.root.node_id()),
            format!("constructed ECMAScript lowering plan is invalid: {errors}"),
        )
    })?;
    Ok(plan)
}

fn completed_status(
    input: &SemanticProgram,
    portability: &PortabilityPlan,
) -> Result<ArtifactPortabilityStatus, EcmascriptLoweringFailure> {
    match portability.status {
        Some(PortabilityStatus::Native) => Ok(ArtifactPortabilityStatus::Native),
        Some(PortabilityStatus::EquivalentRewrite) => {
            Ok(ArtifactPortabilityStatus::EquivalentRewrite)
        }
        Some(PortabilityStatus::Unsupported) => {
            let node_id = portability.decisions.iter().find_map(|decision| {
                matches!(
                    decision.disposition,
                    RequirementPlanningDisposition::Unsupported(_)
                )
                .then_some(&decision.requirement.node_id)
            });
            Err(failure(
                input,
                EcmascriptLoweringErrorCode::UnsupportedRequirement,
                node_id,
                "ECMAScript lowering requires every semantic requirement to have a native or certified equivalent representation",
            ))
        }
        None => {
            let node_id = portability.decisions.iter().find_map(|decision| {
                matches!(
                    decision.disposition,
                    RequirementPlanningDisposition::Unresolved(_)
                )
                .then_some(&decision.requirement.node_id)
            });
            Err(failure(
                input,
                EcmascriptLoweringErrorCode::UnresolvedRequirement,
                node_id,
                "ECMAScript lowering rejects unresolved capability or rewrite evidence",
            ))
        }
    }
}

fn enforce_resource_limits(input: &SemanticProgram) -> Result<(), EcmascriptLoweringFailure> {
    let mut pending = vec![(&input.root, 1_usize)];
    let mut nodes = 0_usize;
    while let Some((node, depth)) = pending.pop() {
        nodes += 1;
        if nodes > MAX_ECMASCRIPT_LOWERING_NODES || depth > MAX_ECMASCRIPT_LOWERING_DEPTH {
            return Err(failure(
                input,
                EcmascriptLoweringErrorCode::ResourceLimitExceeded,
                Some(node.node_id()),
                format!(
                    "ECMAScript lowering limit exceeded (maximum {MAX_ECMASCRIPT_LOWERING_NODES} nodes and depth {MAX_ECMASCRIPT_LOWERING_DEPTH})"
                ),
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

fn collect_captures(input: &SemanticProgram) -> Result<CaptureTable, EcmascriptLoweringFailure> {
    let mut ordered = Vec::new();
    let mut pending = vec![&input.root];
    while let Some(node) = pending.pop() {
        if let Node::Capture {
            node_id,
            capture_id,
            name,
            ..
        } = node
        {
            let slot = u32::try_from(ordered.len() + 1).map_err(|_| {
                failure(
                    input,
                    EcmascriptLoweringErrorCode::CaptureResolution,
                    Some(node_id),
                    "ECMAScript capture slot capacity exceeded",
                )
            })?;
            ordered.push(EcmascriptCapture {
                slot,
                capture_id: capture_id.clone(),
                name: name.clone(),
                definition_node_id: node_id.clone(),
                source_spans: source_spans(node),
            });
        }
        push_children(node, &mut pending);
    }
    let by_id = ordered
        .iter()
        .cloned()
        .map(|capture| (capture.capture_id.clone(), capture))
        .collect();
    Ok(CaptureTable { ordered, by_id })
}

fn validate_rewrites<'a>(
    input: &SemanticProgram,
    portability: &'a PortabilityPlan,
) -> Result<RewriteTable<'a>, EcmascriptLoweringFailure> {
    let nodes = node_index(&input.root);
    let mut by_node = BTreeMap::new();
    for decision in &portability.decisions {
        let RequirementPlanningDisposition::EquivalentRewrite(rewrite) = &decision.disposition
        else {
            continue;
        };
        let plan = &rewrite.rewrite_plan;
        match plan.strategy_id {
            RewriteStrategyId::ElideAtomicLiteralV1 => {
                let Some(Node::Atomic { body, .. }) =
                    nodes.get(&decision.requirement.node_id).copied()
                else {
                    return Err(malformed_rewrite(
                        input,
                        &decision.requirement.node_id,
                        "atomic-literal elision does not identify an atomic Semantic IR node",
                    ));
                };
                if !matches!(body.as_ref(), Node::Literal { .. }) {
                    return Err(malformed_rewrite(
                        input,
                        &decision.requirement.node_id,
                        "atomic-literal elision requires a direct literal body",
                    ));
                }
                let mut expected =
                    vec![decision.requirement.node_id.clone(), body.node_id().clone()];
                expected.sort();
                if plan.affected_node_ids != expected {
                    return Err(malformed_rewrite(
                        input,
                        &decision.requirement.node_id,
                        "atomic-literal elision affected-node evidence does not match the supplied program",
                    ));
                }
            }
            RewriteStrategyId::ElideExactOnceRepetitionV1 => {
                return Err(malformed_rewrite(
                    input,
                    &decision.requirement.node_id,
                    "request-only exact-once rewrite cannot enter a portability lowering plan",
                ));
            }
        }
        if by_node
            .insert(
                decision.requirement.node_id.clone(),
                (&decision.identity, plan),
            )
            .is_some()
        {
            return Err(malformed_rewrite(
                input,
                &decision.requirement.node_id,
                "multiple rewrites target one Semantic IR node",
            ));
        }
    }
    Ok(RewriteTable { by_node })
}

fn malformed_rewrite(
    input: &SemanticProgram,
    node_id: &NodeId,
    message: impl Into<String>,
) -> EcmascriptLoweringFailure {
    failure(
        input,
        EcmascriptLoweringErrorCode::MalformedRewritePlan,
        Some(node_id),
        message,
    )
}

fn lower_node(
    input: &SemanticProgram,
    target: &TargetProfile,
    node: &Node,
    captures: &CaptureTable,
    rewrites: &RewriteTable<'_>,
) -> Result<EcmascriptNode, EcmascriptLoweringFailure> {
    if let Some((identity, rewrite)) = rewrites.by_node.get(node.node_id()) {
        match (rewrite.strategy_id, node) {
            (RewriteStrategyId::ElideAtomicLiteralV1, Node::Atomic { body, .. }) => {
                let mut lowered = lower_node(input, target, body, captures, rewrites)?;
                lowered.provenance =
                    merge_provenance(provenance(node), lowered.provenance, (*identity).clone());
                return Ok(lowered);
            }
            (RewriteStrategyId::ElideAtomicLiteralV1, _) => {
                return Err(malformed_rewrite(
                    input,
                    node.node_id(),
                    "atomic-literal rewrite reached a non-atomic lowering branch",
                ));
            }
            (RewriteStrategyId::ElideExactOnceRepetitionV1, _) => {
                return Err(malformed_rewrite(
                    input,
                    node.node_id(),
                    "request-only exact-once rewrite reached ECMAScript lowering",
                ));
            }
        }
    }

    let operation = match node {
        Node::Empty { .. } => EcmascriptOperation::Empty,
        Node::Sequence { items, .. } => EcmascriptOperation::Sequence(
            items
                .iter()
                .map(|item| lower_node(input, target, item, captures, rewrites))
                .collect::<Result<_, _>>()?,
        ),
        Node::Alternation { branches, .. } => EcmascriptOperation::Alternation(
            branches
                .iter()
                .map(|branch| lower_node(input, target, branch, captures, rewrites))
                .collect::<Result<_, _>>()?,
        ),
        Node::Literal { text, .. } => EcmascriptOperation::Literal(text.clone()),
        Node::Wildcard {
            line_terminators, ..
        } => EcmascriptOperation::Wildcard(match line_terminators {
            LineTerminators::Exclude if native_wildcard_is_canonical(target) => {
                EcmascriptWildcard::ExcludeLineTerminators
            }
            LineTerminators::Exclude => EcmascriptWildcard::CanonicalExcludeLineTerminators,
            LineTerminators::Include => EcmascriptWildcard::IncludeLineTerminators,
        }),
        Node::CharacterSet {
            negated, members, ..
        } => EcmascriptOperation::CharacterSet {
            negated: *negated,
            members: members
                .iter()
                .map(|member| lower_set_member(member, target))
                .collect(),
        },
        Node::Repeat {
            body,
            min,
            max,
            mode,
            ..
        } => {
            let mode = match mode {
                RepetitionMode::Greedy => EcmascriptRepetitionMode::Greedy,
                RepetitionMode::Lazy => EcmascriptRepetitionMode::Lazy,
                RepetitionMode::Possessive => {
                    return Err(failure(
                        input,
                        EcmascriptLoweringErrorCode::UnsupportedRequirement,
                        Some(node.node_id()),
                        "ECMAScript lowering cannot retain an unrewritten possessive repetition",
                    ));
                }
            };
            EcmascriptOperation::Repeat {
                body: Box::new(lower_node(input, target, body, captures, rewrites)?),
                min: *min,
                max: match max {
                    RepetitionMaximum::Bounded(maximum) => {
                        EcmascriptRepetitionMaximum::Bounded(*maximum)
                    }
                    RepetitionMaximum::Unbounded => EcmascriptRepetitionMaximum::Unbounded,
                },
                mode,
            }
        }
        Node::Position { position, .. } => EcmascriptOperation::Position(match position {
            PositionKind::InputStart => EcmascriptPosition::InputStart,
            PositionKind::InputEnd => EcmascriptPosition::InputEnd,
            PositionKind::LineStart if native_line_anchors_are_canonical(target) => {
                EcmascriptPosition::LineStart
            }
            PositionKind::LineStart => EcmascriptPosition::CanonicalLineStart,
            PositionKind::LineEnd if native_line_anchors_are_canonical(target) => {
                EcmascriptPosition::LineEnd
            }
            PositionKind::LineEnd => EcmascriptPosition::CanonicalLineEnd,
            PositionKind::WordBoundary if native_word_is_canonical(target) => {
                EcmascriptPosition::WordBoundary
            }
            PositionKind::WordBoundary => EcmascriptPosition::CanonicalWordBoundary,
            PositionKind::NotWordBoundary if native_word_is_canonical(target) => {
                EcmascriptPosition::NotWordBoundary
            }
            PositionKind::NotWordBoundary => EcmascriptPosition::CanonicalNotWordBoundary,
            PositionKind::EndBeforeFinalLineTerminator => {
                EcmascriptPosition::CanonicalEndBeforeFinalLineTerminator
            }
        }),
        Node::Capture {
            capture_id,
            name,
            body,
            ..
        } => {
            let capture = captures.by_id.get(capture_id).ok_or_else(|| {
                failure(
                    input,
                    EcmascriptLoweringErrorCode::CaptureResolution,
                    Some(node.node_id()),
                    format!(
                        "capture {} has no deterministic ECMAScript slot",
                        capture_id.as_str()
                    ),
                )
            })?;
            EcmascriptOperation::Capture {
                slot: capture.slot,
                capture_id: capture_id.clone(),
                name: name.clone(),
                body: Box::new(lower_node(input, target, body, captures, rewrites)?),
            }
        }
        Node::Backreference { capture_id, .. } => {
            let capture = captures.by_id.get(capture_id).ok_or_else(|| {
                failure(
                    input,
                    EcmascriptLoweringErrorCode::CaptureResolution,
                    Some(node.node_id()),
                    format!(
                        "backreference {} has no deterministic ECMAScript capture slot",
                        capture_id.as_str()
                    ),
                )
            })?;
            EcmascriptOperation::Backreference {
                slot: capture.slot,
                capture_id: capture_id.clone(),
                name: capture.name.clone(),
            }
        }
        Node::Lookaround {
            direction,
            polarity,
            body,
            ..
        } => EcmascriptOperation::Lookaround {
            assertion: match (direction, polarity) {
                (LookaroundDirection::Ahead, AssertionPolarity::Positive) => {
                    EcmascriptLookaround::PositiveAhead
                }
                (LookaroundDirection::Ahead, AssertionPolarity::Negative) => {
                    EcmascriptLookaround::NegativeAhead
                }
                (LookaroundDirection::Behind, AssertionPolarity::Positive) => {
                    EcmascriptLookaround::PositiveBehind
                }
                (LookaroundDirection::Behind, AssertionPolarity::Negative) => {
                    EcmascriptLookaround::NegativeBehind
                }
            },
            body: Box::new(lower_node(input, target, body, captures, rewrites)?),
        },
        Node::Atomic { .. } => {
            return Err(failure(
                input,
                EcmascriptLoweringErrorCode::UnsupportedRequirement,
                Some(node.node_id()),
                "ECMAScript lowering cannot retain an unrewritten atomic group",
            ));
        }
    };
    Ok(EcmascriptNode {
        provenance: provenance(node),
        operation,
    })
}

fn lower_set_member(
    member: &CharacterSetMember,
    target: &TargetProfile,
) -> EcmascriptCharacterSetMember {
    match member {
        CharacterSetMember::Literal { value } => {
            EcmascriptCharacterSetMember::Literal { value: value.get() }
        }
        CharacterSetMember::Range { start, end } => EcmascriptCharacterSetMember::Range {
            start: start.get(),
            end: end.get(),
        },
        CharacterSetMember::Builtin {
            name,
            domain,
            negated,
        } => EcmascriptCharacterSetMember::Builtin {
            name: match name {
                BuiltinClassName::Digit => EcmascriptBuiltinClass::Digit,
                BuiltinClassName::Word => EcmascriptBuiltinClass::Word,
                BuiltinClassName::Whitespace => EcmascriptBuiltinClass::Whitespace,
            },
            domain: match (*domain, *name) {
                (CharacterDomain::Ascii, _) => EcmascriptCharacterDomain::Ascii,
                (CharacterDomain::TargetNative, _) => EcmascriptCharacterDomain::TargetNative,
                (CharacterDomain::Unicode, BuiltinClassName::Word)
                    if !native_word_is_canonical(target) =>
                {
                    EcmascriptCharacterDomain::CanonicalUnicodeWord
                }
                (CharacterDomain::Unicode, _) => EcmascriptCharacterDomain::Unicode,
            },
            negated: *negated,
        },
        CharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => EcmascriptCharacterSetMember::UnicodeProperty {
            property: property.clone(),
            value: value.clone(),
            negated: *negated,
        },
    }
}

fn extract_ecmascript_emitted_requirements(
    root: &EcmascriptNode,
    case_matching: EcmascriptCaseMatching,
    semantic_requirements: &[EcmascriptRequirementResolution],
) -> Vec<EmittedRequirement> {
    let mut requirements = Vec::new();
    if case_matching == EcmascriptCaseMatching::Insensitive {
        push_emitted(
            &mut requirements,
            &root.provenance,
            "matching.case_insensitive",
            RequirementKind::CaseInsensitive,
            "ECMAScript case-insensitive flag",
        );
    }
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        match &node.operation {
            EcmascriptOperation::Empty => {}
            EcmascriptOperation::Sequence(children)
            | EcmascriptOperation::Alternation(children) => {
                pending.extend(children.iter().rev());
            }
            EcmascriptOperation::Literal(text) => {
                let scalars: Vec<_> = text.chars().filter(|scalar| !scalar.is_ascii()).collect();
                if !scalars.is_empty() {
                    push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "character_semantics.unicode_scalar",
                        RequirementKind::UnicodeScalarLiteral { scalars },
                        "ECMAScript Unicode literal",
                    );
                }
            }
            EcmascriptOperation::Wildcard(wildcard) => push_emitted_wildcard(
                &mut requirements,
                &node.provenance,
                *wildcard == EcmascriptWildcard::IncludeLineTerminators,
                "ECMAScript wildcard",
            ),
            EcmascriptOperation::CharacterSet { negated, members } => {
                for member in members {
                    extract_ecmascript_member_requirement(
                        &mut requirements,
                        &node.provenance,
                        member,
                    );
                }
                if *negated
                    && members.iter().any(|member| {
                        matches!(member, EcmascriptCharacterSetMember::Builtin { .. })
                    })
                {
                    push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "assertions.lookahead",
                        RequirementKind::Lookahead {
                            polarity: RequirementPolarity::Negative,
                        },
                        "ECMAScript negated atom-set guard",
                    );
                    push_emitted_wildcard(
                        &mut requirements,
                        &node.provenance,
                        true,
                        "ECMAScript negated atom-set consumer",
                    );
                }
            }
            EcmascriptOperation::Repeat { body, mode, .. } => {
                pending.push(body);
                match mode {
                    EcmascriptRepetitionMode::Greedy => {}
                    EcmascriptRepetitionMode::Lazy => push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "repetition.lazy",
                        RequirementKind::LazyRepetition,
                        "ECMAScript lazy quantifier",
                    ),
                }
            }
            EcmascriptOperation::Position(position) => {
                let (capability, position_kind) = ecmascript_position_requirement(*position);
                push_emitted(
                    &mut requirements,
                    &node.provenance,
                    capability,
                    RequirementKind::Position {
                        position: position_kind,
                    },
                    "ECMAScript anchor or boundary",
                );
                match position {
                    EcmascriptPosition::InputStart
                    | EcmascriptPosition::WordBoundary
                    | EcmascriptPosition::NotWordBoundary => {}
                    EcmascriptPosition::InputEnd => push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "assertions.lookahead",
                        RequirementKind::Lookahead {
                            polarity: RequirementPolarity::Negative,
                        },
                        "ECMAScript input-end guard",
                    ),
                    EcmascriptPosition::LineStart => push_fixed_lookbehind(
                        &mut requirements,
                        &node.provenance,
                        RequirementPolarity::Positive,
                        "ECMAScript line-start predecessor test",
                    ),
                    EcmascriptPosition::LineEnd => push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "assertions.lookahead",
                        RequirementKind::Lookahead {
                            polarity: RequirementPolarity::Positive,
                        },
                        "ECMAScript line-end successor test",
                    ),
                    EcmascriptPosition::EndBeforeFinalLineTerminator => {
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Positive,
                            },
                            "ECMAScript final-line successor test",
                        );
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Negative,
                            },
                            "ECMAScript final-input guard",
                        );
                        push_fixed_lookbehind(
                            &mut requirements,
                            &node.provenance,
                            RequirementPolarity::Negative,
                            "ECMAScript final-LF predecessor test",
                        );
                    }
                    EcmascriptPosition::CanonicalLineStart => {
                        push_fixed_lookbehind(
                            &mut requirements,
                            &node.provenance,
                            RequirementPolarity::Positive,
                            "ECMAScript canonical line-start predecessor test",
                        );
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Negative,
                            },
                            "ECMAScript canonical line-start CRLF guard",
                        );
                    }
                    EcmascriptPosition::CanonicalLineEnd => {
                        push_fixed_lookbehind(
                            &mut requirements,
                            &node.provenance,
                            RequirementPolarity::Negative,
                            "ECMAScript canonical line-end CRLF guard",
                        );
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Positive,
                            },
                            "ECMAScript canonical line-end successor test",
                        );
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Negative,
                            },
                            "ECMAScript canonical input-end guard",
                        );
                    }
                    EcmascriptPosition::CanonicalWordBoundary
                    | EcmascriptPosition::CanonicalNotWordBoundary => {
                        push_fixed_lookbehind(
                            &mut requirements,
                            &node.provenance,
                            RequirementPolarity::Positive,
                            "ECMAScript canonical word transition",
                        );
                        push_fixed_lookbehind(
                            &mut requirements,
                            &node.provenance,
                            RequirementPolarity::Negative,
                            "ECMAScript canonical word transition",
                        );
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Positive,
                            },
                            "ECMAScript canonical word transition",
                        );
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Negative,
                            },
                            "ECMAScript canonical word transition",
                        );
                        push_canonical_word_property_requirements(
                            &mut requirements,
                            &node.provenance,
                        );
                    }
                    EcmascriptPosition::CanonicalEndBeforeFinalLineTerminator => {
                        push_fixed_lookbehind(
                            &mut requirements,
                            &node.provenance,
                            RequirementPolarity::Negative,
                            "ECMAScript canonical final-LF predecessor test",
                        );
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Positive,
                            },
                            "ECMAScript canonical final-line successor test",
                        );
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead {
                                polarity: RequirementPolarity::Negative,
                            },
                            "ECMAScript canonical final-input guard",
                        );
                    }
                }
            }
            EcmascriptOperation::Capture {
                capture_id,
                name,
                body,
                ..
            } => {
                pending.push(body);
                push_emitted(
                    &mut requirements,
                    &node.provenance,
                    "groups.capture_iteration_state",
                    RequirementKind::CaptureIterationState {
                        capture_id: capture_id.clone(),
                    },
                    "ECMAScript capture iteration state",
                );
                if let Some(name) = name {
                    push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "groups.named_capture",
                        RequirementKind::NamedCapture {
                            capture_id: capture_id.clone(),
                            name: name.clone(),
                        },
                        "ECMAScript named capture",
                    );
                }
            }
            EcmascriptOperation::Backreference { capture_id, .. } => push_emitted(
                &mut requirements,
                &node.provenance,
                "references.backreference",
                RequirementKind::Backreference {
                    capture_id: capture_id.clone(),
                    definition_node_id: node.provenance.semantic_node_ids[0].clone(),
                },
                "ECMAScript backreference",
            ),
            EcmascriptOperation::Lookaround { assertion, body } => {
                pending.push(body);
                let polarity =
                    match assertion {
                        EcmascriptLookaround::PositiveAhead
                        | EcmascriptLookaround::PositiveBehind => RequirementPolarity::Positive,
                        EcmascriptLookaround::NegativeAhead
                        | EcmascriptLookaround::NegativeBehind => RequirementPolarity::Negative,
                    };
                match assertion {
                    EcmascriptLookaround::PositiveAhead | EcmascriptLookaround::NegativeAhead => {
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead { polarity },
                            "ECMAScript lookahead",
                        )
                    }
                    EcmascriptLookaround::PositiveBehind | EcmascriptLookaround::NegativeBehind => {
                        let capability =
                            lookbehind_capability(&node.provenance, semantic_requirements);
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            capability,
                            RequirementKind::Lookbehind {
                                body_node_id: body.provenance.semantic_node_ids[0].clone(),
                                polarity,
                                length: LookbehindLength::Fixed { length: 1 },
                            },
                            "ECMAScript lookbehind",
                        );
                    }
                }
            }
        }
    }
    requirements
}

fn extract_ecmascript_member_requirement(
    requirements: &mut Vec<EmittedRequirement>,
    provenance: &EcmascriptProvenance,
    member: &EcmascriptCharacterSetMember,
) {
    match member {
        EcmascriptCharacterSetMember::Literal { value } if !value.is_ascii() => push_emitted(
            requirements,
            provenance,
            "character_semantics.unicode_scalar",
            RequirementKind::UnicodeScalarSetMember {
                start: *value,
                end: *value,
            },
            "ECMAScript Unicode set scalar",
        ),
        EcmascriptCharacterSetMember::Range { start, end }
            if !start.is_ascii() || !end.is_ascii() =>
        {
            push_emitted(
                requirements,
                provenance,
                "character_semantics.unicode_scalar",
                RequirementKind::UnicodeScalarSetMember {
                    start: *start,
                    end: *end,
                },
                "ECMAScript Unicode set range",
            );
        }
        EcmascriptCharacterSetMember::Builtin {
            name,
            domain: EcmascriptCharacterDomain::Unicode,
            negated,
        } => push_emitted(
            requirements,
            provenance,
            "character_classes.unicode",
            RequirementKind::UnicodeCharacterClass {
                name: ecmascript_builtin_name(*name),
                negated: *negated,
            },
            "ECMAScript Unicode built-in class",
        ),
        EcmascriptCharacterSetMember::Builtin {
            name,
            domain: EcmascriptCharacterDomain::CanonicalUnicodeWord,
            negated,
        } => {
            push_emitted(
                requirements,
                provenance,
                "character_classes.unicode",
                RequirementKind::UnicodeCharacterClass {
                    name: ecmascript_builtin_name(*name),
                    negated: *negated,
                },
                "ECMAScript canonical Unicode word class",
            );
            push_canonical_word_property_requirements(requirements, provenance);
        }
        EcmascriptCharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => push_emitted(
            requirements,
            provenance,
            "character_properties.unicode",
            RequirementKind::UnicodeProperty {
                property: property.clone(),
                value: value.clone(),
                negated: *negated,
            },
            "ECMAScript Unicode property",
        ),
        EcmascriptCharacterSetMember::Literal { .. }
        | EcmascriptCharacterSetMember::Range { .. }
        | EcmascriptCharacterSetMember::Builtin {
            domain: EcmascriptCharacterDomain::Ascii | EcmascriptCharacterDomain::TargetNative,
            ..
        } => {}
    }
}

fn push_canonical_word_property_requirements(
    requirements: &mut Vec<EmittedRequirement>,
    provenance: &EcmascriptProvenance,
) {
    for property in ["L", "Mn", "N", "Pc"] {
        push_emitted(
            requirements,
            provenance,
            "character_properties.unicode",
            RequirementKind::UnicodeProperty {
                property: property.to_owned(),
                value: None,
                negated: false,
            },
            "ECMAScript canonical Unicode word property",
        );
    }
}

fn push_emitted(
    requirements: &mut Vec<EmittedRequirement>,
    provenance: &EcmascriptProvenance,
    capability: &'static str,
    kind: RequirementKind,
    construct: &'static str,
) {
    for node_id in &provenance.semantic_node_ids {
        requirements.push(EmittedRequirement {
            requirement: emitted_requirement(node_id.clone(), capability, kind.clone()),
            construct,
        });
    }
}

fn push_emitted_wildcard(
    requirements: &mut Vec<EmittedRequirement>,
    provenance: &EcmascriptProvenance,
    includes_line_terminators: bool,
    construct: &'static str,
) {
    for node_id in &provenance.semantic_node_ids {
        requirements.push(EmittedRequirement {
            requirement: emitted_wildcard_requirement(node_id.clone(), includes_line_terminators),
            construct,
        });
    }
}

fn push_fixed_lookbehind(
    requirements: &mut Vec<EmittedRequirement>,
    provenance: &EcmascriptProvenance,
    polarity: RequirementPolarity,
    construct: &'static str,
) {
    push_emitted(
        requirements,
        provenance,
        "assertions.lookbehind.fixed_length",
        RequirementKind::Lookbehind {
            body_node_id: provenance.semantic_node_ids[0].clone(),
            polarity,
            length: LookbehindLength::Fixed { length: 1 },
        },
        construct,
    );
}

fn ecmascript_builtin_name(name: EcmascriptBuiltinClass) -> BuiltinClassName {
    match name {
        EcmascriptBuiltinClass::Digit => BuiltinClassName::Digit,
        EcmascriptBuiltinClass::Word => BuiltinClassName::Word,
        EcmascriptBuiltinClass::Whitespace => BuiltinClassName::Whitespace,
    }
}

fn ecmascript_position_requirement(
    position: EcmascriptPosition,
) -> (&'static str, PositionRequirement) {
    match position {
        EcmascriptPosition::InputStart => ("anchors.input_start", PositionRequirement::InputStart),
        EcmascriptPosition::InputEnd => ("anchors.input_end", PositionRequirement::InputEnd),
        EcmascriptPosition::LineStart | EcmascriptPosition::CanonicalLineStart => {
            ("anchors.line_start", PositionRequirement::LineStart)
        }
        EcmascriptPosition::LineEnd | EcmascriptPosition::CanonicalLineEnd => {
            ("anchors.line_end", PositionRequirement::LineEnd)
        }
        EcmascriptPosition::WordBoundary | EcmascriptPosition::CanonicalWordBoundary => {
            ("boundaries.word", PositionRequirement::WordBoundary)
        }
        EcmascriptPosition::NotWordBoundary | EcmascriptPosition::CanonicalNotWordBoundary => {
            ("boundaries.word", PositionRequirement::NotWordBoundary)
        }
        EcmascriptPosition::EndBeforeFinalLineTerminator
        | EcmascriptPosition::CanonicalEndBeforeFinalLineTerminator => (
            "anchors.end_before_final_line_terminator",
            PositionRequirement::EndBeforeFinalLineTerminator,
        ),
    }
}

fn lookbehind_capability(
    provenance: &EcmascriptProvenance,
    semantic_requirements: &[EcmascriptRequirementResolution],
) -> &'static str {
    if semantic_requirements.iter().any(|requirement| {
        requirement.identity.capability_id.as_str() == "assertions.lookbehind.variable_length"
            && provenance
                .semantic_node_ids
                .contains(&requirement.identity.node_id)
    }) {
        "assertions.lookbehind.variable_length"
    } else {
        "assertions.lookbehind.fixed_length"
    }
}

fn provenance(node: &Node) -> EcmascriptProvenance {
    let mut semantic_node_ids = vec![node.node_id().clone()];
    if let Some(derived) = node
        .origin()
        .and_then(|origin| origin.derived_from_node_ids.as_ref())
    {
        semantic_node_ids.extend(derived.iter().cloned());
    }
    semantic_node_ids.sort();
    semantic_node_ids.dedup();
    EcmascriptProvenance {
        semantic_node_ids,
        source_spans: source_spans(node),
        applied_rewrite: None,
    }
}

fn merge_provenance(
    mut wrapper: EcmascriptProvenance,
    body: EcmascriptProvenance,
    rewrite: RequirementIdentity,
) -> EcmascriptProvenance {
    wrapper.semantic_node_ids.extend(body.semantic_node_ids);
    wrapper.semantic_node_ids.sort();
    wrapper.semantic_node_ids.dedup();
    wrapper.source_spans.extend(body.source_spans);
    wrapper.source_spans.sort();
    wrapper.source_spans.dedup();
    wrapper.applied_rewrite = Some(rewrite);
    wrapper
}

fn source_spans(node: &Node) -> Vec<SourceSpan> {
    node.origin()
        .and_then(|origin| origin.source_spans.clone())
        .unwrap_or_default()
}

fn node_index(root: &Node) -> BTreeMap<NodeId, &Node> {
    let mut index = BTreeMap::new();
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        index.insert(node.node_id().clone(), node);
        push_children(node, &mut pending);
    }
    index
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

fn failure(
    input: &SemanticProgram,
    code: EcmascriptLoweringErrorCode,
    node_id: Option<&NodeId>,
    message: impl Into<String>,
) -> EcmascriptLoweringFailure {
    let primary_location = node_id.and_then(|id| {
        find_node(&input.root, id)
            .and_then(Node::origin)
            .and_then(|origin| origin.source_spans.as_ref())
            .and_then(|spans| {
                spans.iter().min_by(|left, right| {
                    (left.end - left.start)
                        .cmp(&(right.end - right.start))
                        .then_with(|| left.cmp(right))
                })
            })
            .cloned()
    });
    let node_advice = node_id.map(|id| Advice {
        kind: AdviceKind::Note,
        message: format!("Affected Semantic IR node: {}.", id.as_str()),
    });
    let diagnostic = Diagnostic {
        contract_version: input.contract_version,
        occurrence: DiagnosticOccurrence::new(0),
        code: DiagnosticCode::try_from(code.diagnostic_code())
            .expect("authored ECMAScript lowering diagnostic code must be valid"),
        severity: Severity::Error,
        severity_basis: SeverityBasis::TargetProfile,
        phase: CompilerPhase::TargetLowering,
        category: code.category(),
        message: message.into(),
        primary_location,
        related_locations: None,
        advice: node_advice.map(|advice| vec![advice]),
        fixes: None,
    };
    EcmascriptLoweringFailure {
        code,
        diagnostics: vec![diagnostic],
    }
}

fn find_node<'a>(root: &'a Node, sought: &NodeId) -> Option<&'a Node> {
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        if node.node_id() == sought {
            return Some(node);
        }
        push_children(node, &mut pending);
    }
    None
}

impl Validate for EcmascriptLoweringPlan {
    fn validate(&self) -> Result<(), ValidationErrors> {
        let mut errors = ValidationErrors::default();
        if self
            .options
            .windows(2)
            .any(|pair| pair[0].option_id >= pair[1].option_id)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.options",
                "ECMAScript options must have unique sorted identities",
            ));
        }
        for (index, capture) in self.captures.iter().enumerate() {
            if capture.slot != u32::try_from(index + 1).unwrap_or(u32::MAX) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.captures[{index}].slot"),
                    "ECMAScript capture slots must be consecutive and one-based",
                ));
            }
            if capture
                .source_spans
                .windows(2)
                .any(|pair| pair[0] >= pair[1])
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.captures[{index}].source_spans"),
                    "capture source spans must be unique and sorted",
                ));
            }
        }
        let unique_capture_ids: BTreeSet<_> = self
            .captures
            .iter()
            .map(|capture| &capture.capture_id)
            .collect();
        let unique_capture_nodes: BTreeSet<_> = self
            .captures
            .iter()
            .map(|capture| &capture.definition_node_id)
            .collect();
        if unique_capture_ids.len() != self.captures.len()
            || unique_capture_nodes.len() != self.captures.len()
        {
            errors.push(ValidationError::new(
                ValidationCode::DuplicateIdentity,
                "$.captures",
                "ECMAScript capture identities and definitions must be unique",
            ));
        }
        if self
            .semantic_requirements
            .iter()
            .enumerate()
            .any(|(index, requirement)| requirement.identity.ordinal != index as u32)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.semantic_requirements",
                "semantic requirement resolutions must retain canonical planner order",
            ));
        }
        if self
            .requirements
            .iter()
            .enumerate()
            .any(|(index, requirement)| requirement.identity.ordinal != index as u32)
            || self.requirements.len() < self.semantic_requirements.len()
            || self.requirements[..self.semantic_requirements.len()] != self.semantic_requirements
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.requirements",
                "artifact requirements must preserve the semantic prefix and append canonical lowering requirements",
            ));
        }
        let semantic_keys: BTreeSet<_> = self
            .semantic_requirements
            .iter()
            .filter(|requirement| requirement.status == ArtifactPortabilityStatus::Native)
            .map(|requirement| {
                (
                    &requirement.identity.node_id,
                    &requirement.identity.capability_id,
                )
            })
            .collect();
        if self
            .requirements
            .get(self.semantic_requirements.len()..)
            .unwrap_or_default()
            .iter()
            .any(|requirement| {
                requirement.status != ArtifactPortabilityStatus::Native
                    || requirement.rewrite_strategy.is_some()
                    || semantic_keys.contains(&(
                        &requirement.identity.node_id,
                        &requirement.identity.capability_id,
                    ))
            })
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.requirements",
                "lowering-introduced requirements must be native, unrevised, and absent from the semantic requirement set",
            ));
        }
        let native_source_requirements: Vec<_> = self
            .semantic_requirements
            .iter()
            .filter(|requirement| requirement.status == ArtifactPortabilityStatus::Native)
            .map(|requirement| requirement.identity.clone())
            .collect();
        let emitted = extract_ecmascript_emitted_requirements(
            &self.root,
            self.case_matching,
            &self.semantic_requirements,
        );
        let exact_introduced = classify_introduced_requirements(
            self.semantic_requirements.len(),
            &native_source_requirements,
            emitted,
        )
        .map(|requirements| {
            requirements
                .into_iter()
                .enumerate()
                .map(|(index, requirement)| RequirementIdentity {
                    ordinal: u32::try_from(self.semantic_requirements.len() + index)
                        .unwrap_or(u32::MAX),
                    node_id: requirement.requirement.node_id,
                    capability_id: requirement.requirement.capability_id,
                })
                .collect::<Vec<_>>()
        });
        let actual_introduced: Vec<_> = self
            .requirements
            .get(self.semantic_requirements.len()..)
            .unwrap_or_default()
            .iter()
            .map(|requirement| requirement.identity.clone())
            .collect();
        if exact_introduced.as_deref() != Some(actual_introduced.as_slice()) {
            errors.push(ValidationError::new(
                ValidationCode::UnresolvedReference,
                "$.requirements",
                "lowering-introduced requirements must exactly classify the capability-bearing ECMAScript target tree",
            ));
        }
        let expected_status =
            if self.requirements.iter().any(|requirement| {
                requirement.status == ArtifactPortabilityStatus::EquivalentRewrite
            }) {
                ArtifactPortabilityStatus::EquivalentRewrite
            } else {
                ArtifactPortabilityStatus::Native
            };
        if self.portability_status != expected_status {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.portability_status",
                "lowering portability status must aggregate requirement resolutions",
            ));
        }
        let rewrite_identities: Vec<_> = self
            .semantic_requirements
            .iter()
            .filter(|requirement| requirement.rewrite_strategy.is_some())
            .map(|requirement| &requirement.identity)
            .collect();
        if self.applied_rewrites.len() != rewrite_identities.len()
            || self
                .applied_rewrites
                .iter()
                .zip(rewrite_identities)
                .any(|(rewrite, identity)| &rewrite.identity != identity)
        {
            errors.push(ValidationError::new(
                ValidationCode::UnresolvedReference,
                "$.applied_rewrites",
                "applied rewrites must correspond one-for-one with rewritten requirements",
            ));
        }
        for (index, rewrite) in self.applied_rewrites.iter().enumerate() {
            if rewrite.target_profile != self.target_profile
                || rewrite.affected_node_ids.is_empty()
                || rewrite
                    .affected_node_ids
                    .windows(2)
                    .any(|pair| pair[0] >= pair[1])
            {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalStructure,
                    format!("$.applied_rewrites[{index}]"),
                    "applied rewrite evidence must be canonical and target-exact",
                ));
            }
        }
        validate_target_tree(&self.root, &self.captures, &mut errors);
        errors.finish()
    }
}

fn validate_target_tree(
    root: &EcmascriptNode,
    captures: &[EcmascriptCapture],
    errors: &mut ValidationErrors,
) {
    let capture_slots: BTreeMap<_, _> = captures
        .iter()
        .map(|capture| (capture.capture_id.clone(), capture.slot))
        .collect();
    let mut pending = vec![(root, "$.root".to_owned(), 1_usize)];
    let mut nodes = 0_usize;
    while let Some((node, path, depth)) = pending.pop() {
        nodes += 1;
        if nodes > MAX_ECMASCRIPT_LOWERING_NODES || depth > MAX_ECMASCRIPT_LOWERING_DEPTH {
            errors.push(ValidationError::new(
                ValidationCode::InvalidBounds,
                path,
                "ECMAScript target tree exceeds lowering resource limits",
            ));
            return;
        }
        if node.provenance.semantic_node_ids.is_empty()
            || node
                .provenance
                .semantic_node_ids
                .windows(2)
                .any(|pair| pair[0] >= pair[1])
            || node
                .provenance
                .source_spans
                .windows(2)
                .any(|pair| pair[0] >= pair[1])
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                format!("{path}.provenance"),
                "target node provenance must be nonempty, unique, and sorted",
            ));
        }
        match &node.operation {
            EcmascriptOperation::Capture {
                slot,
                capture_id,
                body,
                ..
            } => {
                if capture_slots.get(capture_id) != Some(slot) {
                    errors.push(ValidationError::new(
                        ValidationCode::UnresolvedReference,
                        format!("{path}.capture_id"),
                        "target capture does not match the canonical slot table",
                    ));
                }
                pending.push((body, format!("{path}.body"), depth + 1));
            }
            EcmascriptOperation::Backreference {
                slot, capture_id, ..
            } => {
                if capture_slots.get(capture_id) != Some(slot) {
                    errors.push(ValidationError::new(
                        ValidationCode::UnresolvedReference,
                        format!("{path}.capture_id"),
                        "target backreference does not match the canonical slot table",
                    ));
                }
            }
            EcmascriptOperation::Sequence(children) => {
                for (index, child) in children.iter().enumerate().rev() {
                    pending.push((child, format!("{path}.items[{index}]"), depth + 1));
                }
            }
            EcmascriptOperation::Alternation(children) => {
                for (index, child) in children.iter().enumerate().rev() {
                    pending.push((child, format!("{path}.branches[{index}]"), depth + 1));
                }
            }
            EcmascriptOperation::Repeat { body, .. }
            | EcmascriptOperation::Lookaround { body, .. } => {
                pending.push((body, format!("{path}.body"), depth + 1));
            }
            EcmascriptOperation::Empty
            | EcmascriptOperation::Literal(_)
            | EcmascriptOperation::Wildcard(_)
            | EcmascriptOperation::CharacterSet { .. }
            | EcmascriptOperation::Position(_) => {}
        }
    }
}
