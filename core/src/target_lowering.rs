//! Pure lowering from normalized Semantic IR and a certified portability plan.
//!
//! This module produces target-specific structure only. It does not serialize
//! regex syntax, construct a `TargetArtifact`, execute PCRE2, or consult any
//! ambient state.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use crate::capability_evaluation::{
    emitted_bounded_repetition_requirement, emitted_requirement, emitted_wildcard_requirement,
    LookbehindLength, PositionRequirement, RequirementKind, RequirementPolarity,
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
pub const MAX_PCRE2_LOWERING_NODES: usize = 65_536;

/// Maximum Semantic IR nesting admitted by one lowering invocation.
pub const MAX_PCRE2_LOWERING_DEPTH: usize = 128;

/// Stable target-lowering failure categories.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum Pcre2LoweringErrorCode {
    InvalidSemanticProgram,
    ResourceLimitExceeded,
    InvalidTargetProfile,
    NonPcre2Target,
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

impl Pcre2LoweringErrorCode {
    const fn diagnostic_code(self) -> &'static str {
        match self {
            Self::InvalidSemanticProgram => "STRL-PCRE2_LOWERING-0001",
            Self::ResourceLimitExceeded => "STRL-PCRE2_LOWERING-0002",
            Self::InvalidTargetProfile => "STRL-PCRE2_LOWERING-0003",
            Self::NonPcre2Target => "STRL-PCRE2_LOWERING-0004",
            Self::IncompatibleTargetProfile => "STRL-PCRE2_LOWERING-0005",
            Self::InvalidPortabilityPlan => "STRL-PCRE2_LOWERING-0006",
            Self::ProgramFingerprintMismatch => "STRL-PCRE2_LOWERING-0007",
            Self::TargetProfileMismatch => "STRL-PCRE2_LOWERING-0008",
            Self::VersionMismatch => "STRL-PCRE2_LOWERING-0009",
            Self::UnresolvedRequirement => "STRL-PCRE2_LOWERING-0010",
            Self::UnsupportedRequirement => "STRL-PCRE2_LOWERING-0011",
            Self::MalformedRewritePlan => "STRL-PCRE2_LOWERING-0012",
            Self::CaptureResolution => "STRL-PCRE2_LOWERING-0013",
            Self::IntroducedRequirement => "STRL-PCRE2_LOWERING-0014",
            Self::InvalidLoweringPlan => "STRL-PCRE2_LOWERING-0015",
        }
    }

    const fn category(self) -> DiagnosticCategory {
        match self {
            Self::InvalidSemanticProgram | Self::CaptureResolution => {
                DiagnosticCategory::SemanticValidity
            }
            Self::ResourceLimitExceeded => DiagnosticCategory::ResourceLimit,
            Self::NonPcre2Target
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

/// All-or-nothing failure from PCRE2 target lowering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2LoweringFailure {
    pub code: Pcre2LoweringErrorCode,
    pub diagnostics: Vec<Diagnostic>,
}

impl fmt::Display for Pcre2LoweringFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "PCRE2 target lowering failed with {} diagnostic(s)",
            self.diagnostics.len()
        )
    }
}

impl Error for Pcre2LoweringFailure {}

/// PCRE2 interpretation of global case intent, retained outside pattern text.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Pcre2CaseMatching {
    Sensitive,
    Insensitive,
}

/// One exact profile option selected before serialization or execution.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2OptionPlan {
    pub option_id: OptionId,
    pub stage: OptionStage,
    pub value: EngineOptionValue,
    pub selection: OptionSelection,
}

/// Provenance carried by every target operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2Provenance {
    pub semantic_node_ids: Vec<NodeId>,
    pub source_spans: Vec<SourceSpan>,
    pub applied_rewrite: Option<RequirementIdentity>,
}

/// PCRE2 wildcard behavior without syntax spelling.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Pcre2Wildcard {
    ExcludeLineTerminators,
    IncludeLineTerminators,
}

/// PCRE2 built-in character-class identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Pcre2BuiltinClass {
    Digit,
    Word,
    Whitespace,
}

/// PCRE2 built-in class interpretation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Pcre2CharacterDomain {
    Ascii,
    TargetNative,
    Unicode,
}

/// Structured character-set member awaiting serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Pcre2CharacterSetMember {
    Literal {
        value: char,
    },
    Range {
        start: char,
        end: char,
    },
    Builtin {
        name: Pcre2BuiltinClass,
        domain: Pcre2CharacterDomain,
        negated: bool,
    },
    UnicodeProperty {
        property: String,
        value: Option<String>,
        negated: bool,
    },
}

/// PCRE2 repetition maximum without quantifier punctuation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Pcre2RepetitionMaximum {
    Bounded(u64),
    Unbounded,
}

/// PCRE2 repetition backtracking behavior.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Pcre2RepetitionMode {
    Greedy,
    Lazy,
    Possessive,
}

/// PCRE2 position identity without anchor spelling.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Pcre2Position {
    InputStart,
    InputEnd,
    LineStart,
    LineEnd,
    WordBoundary,
    NotWordBoundary,
    EndBeforeFinalLineTerminator,
}

/// PCRE2 assertion identity without grouping punctuation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Pcre2Lookaround {
    PositiveAhead,
    NegativeAhead,
    PositiveBehind,
    NegativeBehind,
}

/// Closed PCRE2 operation vocabulary before regex serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Pcre2Operation {
    Empty,
    Sequence(Vec<Pcre2Node>),
    Alternation(Vec<Pcre2Node>),
    Literal(String),
    Wildcard(Pcre2Wildcard),
    CharacterSet {
        negated: bool,
        members: Vec<Pcre2CharacterSetMember>,
    },
    Repeat {
        body: Box<Pcre2Node>,
        min: u64,
        max: Pcre2RepetitionMaximum,
        mode: Pcre2RepetitionMode,
    },
    Position(Pcre2Position),
    Capture {
        slot: u32,
        capture_id: CaptureId,
        name: Option<String>,
        body: Box<Pcre2Node>,
    },
    Backreference {
        slot: u32,
        capture_id: CaptureId,
        name: Option<String>,
    },
    Lookaround {
        assertion: Pcre2Lookaround,
        body: Box<Pcre2Node>,
    },
    Atomic(Box<Pcre2Node>),
}

/// One PCRE2 target node with exact semantic provenance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2Node {
    pub provenance: Pcre2Provenance,
    pub operation: Pcre2Operation,
}

/// Deterministic logical-capture to PCRE2 slot assignment.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2Capture {
    pub slot: u32,
    pub capture_id: CaptureId,
    pub name: Option<String>,
    pub definition_node_id: NodeId,
    pub source_spans: Vec<SourceSpan>,
}

/// Exact completed planner decision retained by the target plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2RequirementResolution {
    pub identity: RequirementIdentity,
    pub status: ArtifactPortabilityStatus,
    pub rewrite_strategy: Option<RewriteStrategyId>,
}

/// Certified semantic rewrite actually applied by PCRE2 lowering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2AppliedRewrite {
    pub identity: RequirementIdentity,
    pub strategy_id: RewriteStrategyId,
    pub certification: RewriteCertificationEvidence,
    pub affected_node_ids: Vec<NodeId>,
    pub proof: Vec<RewriteProofEvaluation>,
    pub target_profile: TargetProfileReference,
}

/// Complete, deterministic, pre-serialization PCRE2 target representation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2LoweringPlan {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub semantic_program: Sha256Digest,
    pub target_profile: TargetProfileReference,
    pub portability_status: ArtifactPortabilityStatus,
    pub case_matching: Pcre2CaseMatching,
    pub options: Vec<Pcre2OptionPlan>,
    pub captures: Vec<Pcre2Capture>,
    /// Requirements inherent in Semantic IR and planned before lowering.
    pub semantic_requirements: Vec<Pcre2RequirementResolution>,
    /// Authoritative union of semantic and lowering-introduced requirements.
    pub requirements: Vec<Pcre2RequirementResolution>,
    pub applied_rewrites: Vec<Pcre2AppliedRewrite>,
    pub root: Pcre2Node,
}

struct CaptureTable {
    ordered: Vec<Pcre2Capture>,
    by_id: BTreeMap<CaptureId, Pcre2Capture>,
}

struct RewriteTable<'a> {
    by_node: BTreeMap<NodeId, (&'a RequirementIdentity, &'a SemanticRewritePlan)>,
}

/// Lower one exact semantic program and certified plan into structured PCRE2 data.
pub fn lower_pcre2(
    input: &SemanticProgram,
    target: &TargetProfile,
    portability: &PortabilityPlan,
) -> Result<Pcre2LoweringPlan, Pcre2LoweringFailure> {
    enforce_resource_limits(input)?;
    if let Err(errors) = input.validate() {
        return Err(failure(
            input,
            Pcre2LoweringErrorCode::InvalidSemanticProgram,
            Some(input.root.node_id()),
            format!("normalized Semantic IR is invalid: {errors}"),
        ));
    }
    if input.normalization != Normalization::CanonicalV1 {
        return Err(failure(
            input,
            Pcre2LoweringErrorCode::InvalidSemanticProgram,
            Some(input.root.node_id()),
            "PCRE2 lowering requires canonical-v1 Semantic IR",
        ));
    }
    if let Err(errors) = target.validate() {
        return Err(failure(
            input,
            Pcre2LoweringErrorCode::InvalidTargetProfile,
            Some(input.root.node_id()),
            format!("PCRE2 target profile is invalid: {errors}"),
        ));
    }
    if target.engine.id.as_str() != "pcre2" {
        return Err(failure(
            input,
            Pcre2LoweringErrorCode::NonPcre2Target,
            Some(input.root.node_id()),
            format!(
                "PCRE2 lowering cannot consume engine {}",
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
            Pcre2LoweringErrorCode::IncompatibleTargetProfile,
            Some(input.root.node_id()),
            "PCRE2 target profile does not certify the semantic contract/specification versions",
        ));
    }
    if let Err(errors) = portability.validate() {
        return Err(failure(
            input,
            Pcre2LoweringErrorCode::InvalidPortabilityPlan,
            Some(input.root.node_id()),
            format!("portability plan is malformed: {errors}"),
        ));
    }

    let semantic_program = canonical_sha256(input)
        .map(Sha256Digest::from_bytes)
        .map_err(|error| {
            failure(
                input,
                Pcre2LoweringErrorCode::ProgramFingerprintMismatch,
                Some(input.root.node_id()),
                format!("semantic program fingerprint could not be derived: {error}"),
            )
        })?;
    if portability.semantic_program != semantic_program {
        return Err(failure(
            input,
            Pcre2LoweringErrorCode::ProgramFingerprintMismatch,
            Some(input.root.node_id()),
            "portability plan was not produced for the supplied Semantic IR bytes",
        ));
    }
    let target_profile = target.reference().map_err(|errors| {
        failure(
            input,
            Pcre2LoweringErrorCode::InvalidTargetProfile,
            Some(input.root.node_id()),
            format!("PCRE2 target profile reference could not be derived: {errors}"),
        )
    })?;
    if portability.target_profile != target_profile {
        return Err(failure(
            input,
            Pcre2LoweringErrorCode::TargetProfileMismatch,
            Some(input.root.node_id()),
            "portability plan does not name the exact supplied PCRE2 profile revision and fingerprint",
        ));
    }
    if portability.contract_version != input.contract_version
        || portability.specification_version != input.specification_version
    {
        return Err(failure(
            input,
            Pcre2LoweringErrorCode::VersionMismatch,
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
            RequirementPlanningDisposition::Native(_) => Pcre2RequirementResolution {
                identity: decision.identity.clone(),
                status: ArtifactPortabilityStatus::Native,
                rewrite_strategy: None,
            },
            RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
                Pcre2RequirementResolution {
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
                Some(Pcre2AppliedRewrite {
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
        .map(|option| Pcre2OptionPlan {
            option_id: option.option_id.clone(),
            stage: option.stage,
            value: option.value.clone(),
            selection: option.selection,
        })
        .collect();

    let root = lower_node(input, &input.root, &captures, &rewrites)?;
    let emitted = extract_pcre2_emitted_requirements(
        &root,
        match input.case_matching {
            CaseMatching::Sensitive => Pcre2CaseMatching::Sensitive,
            CaseMatching::Insensitive => Pcre2CaseMatching::Insensitive,
        },
        &semantic_requirements,
    );
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
                Pcre2LoweringErrorCode::ResourceLimitExceeded
            }
            PostLoweringRequirementFailureKind::InvalidProfile
            | PostLoweringRequirementFailureKind::Unsupported
            | PostLoweringRequirementFailureKind::ConstraintViolation
            | PostLoweringRequirementFailureKind::Unknown => {
                Pcre2LoweringErrorCode::IntroducedRequirement
            }
        };
        failure(input, code, error.node_id.as_ref(), error.to_string())
    })?;
    let mut requirements = semantic_requirements.clone();
    requirements.extend(
        introduced
            .into_iter()
            .map(|requirement| Pcre2RequirementResolution {
                identity: requirement.identity,
                status: ArtifactPortabilityStatus::Native,
                rewrite_strategy: None,
            }),
    );
    let plan = Pcre2LoweringPlan {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        semantic_program,
        target_profile,
        portability_status,
        case_matching: match input.case_matching {
            CaseMatching::Sensitive => Pcre2CaseMatching::Sensitive,
            CaseMatching::Insensitive => Pcre2CaseMatching::Insensitive,
        },
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
            Pcre2LoweringErrorCode::InvalidLoweringPlan,
            Some(input.root.node_id()),
            format!("constructed PCRE2 lowering plan is invalid: {errors}"),
        )
    })?;
    Ok(plan)
}

fn completed_status(
    input: &SemanticProgram,
    portability: &PortabilityPlan,
) -> Result<ArtifactPortabilityStatus, Pcre2LoweringFailure> {
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
                Pcre2LoweringErrorCode::UnsupportedRequirement,
                node_id,
                "PCRE2 lowering requires every semantic requirement to have a native or certified equivalent representation",
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
                Pcre2LoweringErrorCode::UnresolvedRequirement,
                node_id,
                "PCRE2 lowering rejects unresolved capability or rewrite evidence",
            ))
        }
    }
}

fn enforce_resource_limits(input: &SemanticProgram) -> Result<(), Pcre2LoweringFailure> {
    let mut pending = vec![(&input.root, 1_usize)];
    let mut nodes = 0_usize;
    while let Some((node, depth)) = pending.pop() {
        nodes += 1;
        if nodes > MAX_PCRE2_LOWERING_NODES || depth > MAX_PCRE2_LOWERING_DEPTH {
            return Err(failure(
                input,
                Pcre2LoweringErrorCode::ResourceLimitExceeded,
                Some(node.node_id()),
                format!(
                    "PCRE2 lowering limit exceeded (maximum {MAX_PCRE2_LOWERING_NODES} nodes and depth {MAX_PCRE2_LOWERING_DEPTH})"
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

fn collect_captures(input: &SemanticProgram) -> Result<CaptureTable, Pcre2LoweringFailure> {
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
                    Pcre2LoweringErrorCode::CaptureResolution,
                    Some(node_id),
                    "PCRE2 capture slot capacity exceeded",
                )
            })?;
            ordered.push(Pcre2Capture {
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
) -> Result<RewriteTable<'a>, Pcre2LoweringFailure> {
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
) -> Pcre2LoweringFailure {
    failure(
        input,
        Pcre2LoweringErrorCode::MalformedRewritePlan,
        Some(node_id),
        message,
    )
}

fn lower_node(
    input: &SemanticProgram,
    node: &Node,
    captures: &CaptureTable,
    rewrites: &RewriteTable<'_>,
) -> Result<Pcre2Node, Pcre2LoweringFailure> {
    if let Some((identity, rewrite)) = rewrites.by_node.get(node.node_id()) {
        match (rewrite.strategy_id, node) {
            (RewriteStrategyId::ElideAtomicLiteralV1, Node::Atomic { body, .. }) => {
                let mut lowered = lower_node(input, body, captures, rewrites)?;
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
                    "request-only exact-once rewrite reached PCRE2 lowering",
                ));
            }
        }
    }

    let operation = match node {
        Node::Empty { .. } => Pcre2Operation::Empty,
        Node::Sequence { items, .. } => Pcre2Operation::Sequence(
            items
                .iter()
                .map(|item| lower_node(input, item, captures, rewrites))
                .collect::<Result<_, _>>()?,
        ),
        Node::Alternation { branches, .. } => Pcre2Operation::Alternation(
            branches
                .iter()
                .map(|branch| lower_node(input, branch, captures, rewrites))
                .collect::<Result<_, _>>()?,
        ),
        Node::Literal { text, .. } => Pcre2Operation::Literal(text.clone()),
        Node::Wildcard {
            line_terminators, ..
        } => Pcre2Operation::Wildcard(match line_terminators {
            LineTerminators::Exclude => Pcre2Wildcard::ExcludeLineTerminators,
            LineTerminators::Include => Pcre2Wildcard::IncludeLineTerminators,
        }),
        Node::CharacterSet {
            negated, members, ..
        } => Pcre2Operation::CharacterSet {
            negated: *negated,
            members: members.iter().map(lower_set_member).collect(),
        },
        Node::Repeat {
            body,
            min,
            max,
            mode,
            ..
        } => Pcre2Operation::Repeat {
            body: Box::new(lower_node(input, body, captures, rewrites)?),
            min: *min,
            max: match max {
                RepetitionMaximum::Bounded(maximum) => Pcre2RepetitionMaximum::Bounded(*maximum),
                RepetitionMaximum::Unbounded => Pcre2RepetitionMaximum::Unbounded,
            },
            mode: match mode {
                RepetitionMode::Greedy => Pcre2RepetitionMode::Greedy,
                RepetitionMode::Lazy => Pcre2RepetitionMode::Lazy,
                RepetitionMode::Possessive => Pcre2RepetitionMode::Possessive,
            },
        },
        Node::Position { position, .. } => Pcre2Operation::Position(match position {
            PositionKind::InputStart => Pcre2Position::InputStart,
            PositionKind::InputEnd => Pcre2Position::InputEnd,
            PositionKind::LineStart => Pcre2Position::LineStart,
            PositionKind::LineEnd => Pcre2Position::LineEnd,
            PositionKind::WordBoundary => Pcre2Position::WordBoundary,
            PositionKind::NotWordBoundary => Pcre2Position::NotWordBoundary,
            PositionKind::EndBeforeFinalLineTerminator => {
                Pcre2Position::EndBeforeFinalLineTerminator
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
                    Pcre2LoweringErrorCode::CaptureResolution,
                    Some(node.node_id()),
                    format!(
                        "capture {} has no deterministic PCRE2 slot",
                        capture_id.as_str()
                    ),
                )
            })?;
            Pcre2Operation::Capture {
                slot: capture.slot,
                capture_id: capture_id.clone(),
                name: name.clone(),
                body: Box::new(lower_node(input, body, captures, rewrites)?),
            }
        }
        Node::Backreference { capture_id, .. } => {
            let capture = captures.by_id.get(capture_id).ok_or_else(|| {
                failure(
                    input,
                    Pcre2LoweringErrorCode::CaptureResolution,
                    Some(node.node_id()),
                    format!(
                        "backreference {} has no deterministic PCRE2 capture slot",
                        capture_id.as_str()
                    ),
                )
            })?;
            Pcre2Operation::Backreference {
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
        } => Pcre2Operation::Lookaround {
            assertion: match (direction, polarity) {
                (LookaroundDirection::Ahead, AssertionPolarity::Positive) => {
                    Pcre2Lookaround::PositiveAhead
                }
                (LookaroundDirection::Ahead, AssertionPolarity::Negative) => {
                    Pcre2Lookaround::NegativeAhead
                }
                (LookaroundDirection::Behind, AssertionPolarity::Positive) => {
                    Pcre2Lookaround::PositiveBehind
                }
                (LookaroundDirection::Behind, AssertionPolarity::Negative) => {
                    Pcre2Lookaround::NegativeBehind
                }
            },
            body: Box::new(lower_node(input, body, captures, rewrites)?),
        },
        Node::Atomic { body, .. } => {
            Pcre2Operation::Atomic(Box::new(lower_node(input, body, captures, rewrites)?))
        }
    };
    Ok(Pcre2Node {
        provenance: provenance(node),
        operation,
    })
}

fn lower_set_member(member: &CharacterSetMember) -> Pcre2CharacterSetMember {
    match member {
        CharacterSetMember::Literal { value } => {
            Pcre2CharacterSetMember::Literal { value: value.get() }
        }
        CharacterSetMember::Range { start, end } => Pcre2CharacterSetMember::Range {
            start: start.get(),
            end: end.get(),
        },
        CharacterSetMember::Builtin {
            name,
            domain,
            negated,
        } => Pcre2CharacterSetMember::Builtin {
            name: match name {
                BuiltinClassName::Digit => Pcre2BuiltinClass::Digit,
                BuiltinClassName::Word => Pcre2BuiltinClass::Word,
                BuiltinClassName::Whitespace => Pcre2BuiltinClass::Whitespace,
            },
            domain: match domain {
                CharacterDomain::Ascii => Pcre2CharacterDomain::Ascii,
                CharacterDomain::TargetNative => Pcre2CharacterDomain::TargetNative,
                CharacterDomain::Unicode => Pcre2CharacterDomain::Unicode,
            },
            negated: *negated,
        },
        CharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => Pcre2CharacterSetMember::UnicodeProperty {
            property: property.clone(),
            value: value.clone(),
            negated: *negated,
        },
    }
}

fn extract_pcre2_emitted_requirements(
    root: &Pcre2Node,
    case_matching: Pcre2CaseMatching,
    semantic_requirements: &[Pcre2RequirementResolution],
) -> Vec<EmittedRequirement> {
    let mut requirements = Vec::new();
    if case_matching == Pcre2CaseMatching::Insensitive {
        push_emitted(
            &mut requirements,
            &root.provenance,
            "matching.case_insensitive",
            RequirementKind::CaseInsensitive,
            "PCRE2 case-insensitive scope",
        );
    }
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        match &node.operation {
            Pcre2Operation::Empty => {}
            Pcre2Operation::Sequence(children) | Pcre2Operation::Alternation(children) => {
                pending.extend(children.iter().rev());
            }
            Pcre2Operation::Literal(text) => {
                let scalars: Vec<_> = text.chars().filter(|scalar| !scalar.is_ascii()).collect();
                if !scalars.is_empty() {
                    push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "character_semantics.unicode_scalar",
                        RequirementKind::UnicodeScalarLiteral { scalars },
                        "PCRE2 Unicode literal",
                    );
                }
            }
            Pcre2Operation::Wildcard(wildcard) => push_emitted_wildcard(
                &mut requirements,
                &node.provenance,
                *wildcard == Pcre2Wildcard::IncludeLineTerminators,
                "PCRE2 wildcard",
            ),
            Pcre2Operation::CharacterSet { negated, members } => {
                for member in members {
                    extract_pcre2_member_requirement(&mut requirements, &node.provenance, member);
                }
                if *negated
                    && members.iter().any(|member| {
                        matches!(
                            member,
                            Pcre2CharacterSetMember::Builtin {
                                domain: Pcre2CharacterDomain::Ascii,
                                ..
                            }
                        )
                    })
                {
                    push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "assertions.lookahead",
                        RequirementKind::Lookahead {
                            polarity: RequirementPolarity::Negative,
                        },
                        "PCRE2 negated atom-set guard",
                    );
                    push_emitted_wildcard(
                        &mut requirements,
                        &node.provenance,
                        true,
                        "PCRE2 negated atom-set consumer",
                    );
                }
            }
            Pcre2Operation::Repeat {
                body,
                min,
                max,
                mode,
            } => {
                pending.push(body);
                if let Pcre2RepetitionMaximum::Bounded(maximum) = max {
                    for node_id in &node.provenance.semantic_node_ids {
                        requirements.push(EmittedRequirement {
                            requirement: emitted_bounded_repetition_requirement(
                                node_id.clone(),
                                *min,
                                *maximum,
                            ),
                            construct: "PCRE2 bounded quantifier",
                        });
                    }
                }
                match mode {
                    Pcre2RepetitionMode::Greedy => {}
                    Pcre2RepetitionMode::Lazy => push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "repetition.lazy",
                        RequirementKind::LazyRepetition,
                        "PCRE2 lazy quantifier",
                    ),
                    Pcre2RepetitionMode::Possessive => push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "repetition.possessive",
                        RequirementKind::PossessiveRepetition,
                        "PCRE2 possessive quantifier",
                    ),
                }
            }
            Pcre2Operation::Position(position) => {
                let (capability, position) = pcre2_position_requirement(*position);
                push_emitted(
                    &mut requirements,
                    &node.provenance,
                    capability,
                    RequirementKind::Position { position },
                    "PCRE2 anchor or boundary",
                );
            }
            Pcre2Operation::Capture {
                capture_id,
                name,
                body,
                ..
            } => {
                pending.push(body);
                if let Some(name) = name {
                    push_emitted(
                        &mut requirements,
                        &node.provenance,
                        "groups.named_capture",
                        RequirementKind::NamedCapture {
                            capture_id: capture_id.clone(),
                            name: name.clone(),
                        },
                        "PCRE2 named capture",
                    );
                }
            }
            Pcre2Operation::Backreference { capture_id, .. } => push_emitted(
                &mut requirements,
                &node.provenance,
                "references.backreference",
                RequirementKind::Backreference {
                    capture_id: capture_id.clone(),
                    definition_node_id: node.provenance.semantic_node_ids[0].clone(),
                },
                "PCRE2 backreference",
            ),
            Pcre2Operation::Lookaround { assertion, body } => {
                pending.push(body);
                let polarity = match assertion {
                    Pcre2Lookaround::PositiveAhead | Pcre2Lookaround::PositiveBehind => {
                        RequirementPolarity::Positive
                    }
                    Pcre2Lookaround::NegativeAhead | Pcre2Lookaround::NegativeBehind => {
                        RequirementPolarity::Negative
                    }
                };
                match assertion {
                    Pcre2Lookaround::PositiveAhead | Pcre2Lookaround::NegativeAhead => {
                        push_emitted(
                            &mut requirements,
                            &node.provenance,
                            "assertions.lookahead",
                            RequirementKind::Lookahead { polarity },
                            "PCRE2 lookahead",
                        );
                    }
                    Pcre2Lookaround::PositiveBehind | Pcre2Lookaround::NegativeBehind => {
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
                            "PCRE2 lookbehind",
                        );
                    }
                }
            }
            Pcre2Operation::Atomic(body) => {
                pending.push(body);
                push_emitted(
                    &mut requirements,
                    &node.provenance,
                    "groups.atomic",
                    RequirementKind::Atomic,
                    "PCRE2 atomic group",
                );
            }
        }
    }
    requirements
}

fn extract_pcre2_member_requirement(
    requirements: &mut Vec<EmittedRequirement>,
    provenance: &Pcre2Provenance,
    member: &Pcre2CharacterSetMember,
) {
    match member {
        Pcre2CharacterSetMember::Literal { value } if !value.is_ascii() => push_emitted(
            requirements,
            provenance,
            "character_semantics.unicode_scalar",
            RequirementKind::UnicodeScalarSetMember {
                start: *value,
                end: *value,
            },
            "PCRE2 Unicode set scalar",
        ),
        Pcre2CharacterSetMember::Range { start, end } if !start.is_ascii() || !end.is_ascii() => {
            push_emitted(
                requirements,
                provenance,
                "character_semantics.unicode_scalar",
                RequirementKind::UnicodeScalarSetMember {
                    start: *start,
                    end: *end,
                },
                "PCRE2 Unicode set range",
            );
        }
        Pcre2CharacterSetMember::Builtin {
            name,
            domain: Pcre2CharacterDomain::Unicode,
            negated,
        } => push_emitted(
            requirements,
            provenance,
            "character_classes.unicode",
            RequirementKind::UnicodeCharacterClass {
                name: pcre2_builtin_name(*name),
                negated: *negated,
            },
            "PCRE2 Unicode built-in class",
        ),
        Pcre2CharacterSetMember::UnicodeProperty {
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
            "PCRE2 Unicode property",
        ),
        Pcre2CharacterSetMember::Literal { .. }
        | Pcre2CharacterSetMember::Range { .. }
        | Pcre2CharacterSetMember::Builtin {
            domain: Pcre2CharacterDomain::Ascii | Pcre2CharacterDomain::TargetNative,
            ..
        } => {}
    }
}

fn push_emitted(
    requirements: &mut Vec<EmittedRequirement>,
    provenance: &Pcre2Provenance,
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
    provenance: &Pcre2Provenance,
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

fn pcre2_builtin_name(name: Pcre2BuiltinClass) -> BuiltinClassName {
    match name {
        Pcre2BuiltinClass::Digit => BuiltinClassName::Digit,
        Pcre2BuiltinClass::Word => BuiltinClassName::Word,
        Pcre2BuiltinClass::Whitespace => BuiltinClassName::Whitespace,
    }
}

fn pcre2_position_requirement(position: Pcre2Position) -> (&'static str, PositionRequirement) {
    match position {
        Pcre2Position::InputStart => ("anchors.input_start", PositionRequirement::InputStart),
        Pcre2Position::InputEnd => ("anchors.input_end", PositionRequirement::InputEnd),
        Pcre2Position::LineStart => ("anchors.line_start", PositionRequirement::LineStart),
        Pcre2Position::LineEnd => ("anchors.line_end", PositionRequirement::LineEnd),
        Pcre2Position::WordBoundary => ("boundaries.word", PositionRequirement::WordBoundary),
        Pcre2Position::NotWordBoundary => ("boundaries.word", PositionRequirement::NotWordBoundary),
        Pcre2Position::EndBeforeFinalLineTerminator => (
            "anchors.end_before_final_line_terminator",
            PositionRequirement::EndBeforeFinalLineTerminator,
        ),
    }
}

fn lookbehind_capability(
    provenance: &Pcre2Provenance,
    semantic_requirements: &[Pcre2RequirementResolution],
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

fn provenance(node: &Node) -> Pcre2Provenance {
    let mut semantic_node_ids = vec![node.node_id().clone()];
    if let Some(derived) = node
        .origin()
        .and_then(|origin| origin.derived_from_node_ids.as_ref())
    {
        semantic_node_ids.extend(derived.iter().cloned());
    }
    semantic_node_ids.sort();
    semantic_node_ids.dedup();
    Pcre2Provenance {
        semantic_node_ids,
        source_spans: source_spans(node),
        applied_rewrite: None,
    }
}

fn merge_provenance(
    mut wrapper: Pcre2Provenance,
    body: Pcre2Provenance,
    rewrite: RequirementIdentity,
) -> Pcre2Provenance {
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
    code: Pcre2LoweringErrorCode,
    node_id: Option<&NodeId>,
    message: impl Into<String>,
) -> Pcre2LoweringFailure {
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
            .expect("authored PCRE2 lowering diagnostic code must be valid"),
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
    Pcre2LoweringFailure {
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

impl Validate for Pcre2LoweringPlan {
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
                "PCRE2 options must have unique sorted identities",
            ));
        }
        for (index, capture) in self.captures.iter().enumerate() {
            if capture.slot != u32::try_from(index + 1).unwrap_or(u32::MAX) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.captures[{index}].slot"),
                    "PCRE2 capture slots must be consecutive and one-based",
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
                "PCRE2 capture identities and definitions must be unique",
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
        let emitted = extract_pcre2_emitted_requirements(
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
                "lowering-introduced requirements must exactly classify the capability-bearing PCRE2 target tree",
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
    root: &Pcre2Node,
    captures: &[Pcre2Capture],
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
        if nodes > MAX_PCRE2_LOWERING_NODES || depth > MAX_PCRE2_LOWERING_DEPTH {
            errors.push(ValidationError::new(
                ValidationCode::InvalidBounds,
                path,
                "PCRE2 target tree exceeds lowering resource limits",
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
            Pcre2Operation::Capture {
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
            Pcre2Operation::Backreference {
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
            Pcre2Operation::Sequence(children) => {
                for (index, child) in children.iter().enumerate().rev() {
                    pending.push((child, format!("{path}.items[{index}]"), depth + 1));
                }
            }
            Pcre2Operation::Alternation(children) => {
                for (index, child) in children.iter().enumerate().rev() {
                    pending.push((child, format!("{path}.branches[{index}]"), depth + 1));
                }
            }
            Pcre2Operation::Repeat { body, .. }
            | Pcre2Operation::Lookaround { body, .. }
            | Pcre2Operation::Atomic(body) => {
                pending.push((body, format!("{path}.body"), depth + 1));
            }
            Pcre2Operation::Empty
            | Pcre2Operation::Literal(_)
            | Pcre2Operation::Wildcard(_)
            | Pcre2Operation::CharacterSet { .. }
            | Pcre2Operation::Position(_) => {}
        }
    }
}
