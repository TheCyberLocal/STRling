//! Pure lowering from normalized Semantic IR and a certified portability plan.
//!
//! This module produces target-specific structure only. It does not serialize
//! regex syntax, construct a `TargetArtifact` or compiled pattern, execute
//! Python, import peer-target or historical binding code, or consult ambient
//! state.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;

use crate::diagnostic::{
    Advice, AdviceKind, CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode,
    DiagnosticOccurrence, Severity, SeverityBasis,
};
use crate::portability_planning::{
    PortabilityPlan, RequirementIdentity, RequirementPlanningDisposition,
    RewriteCertificationEvidence, RewriteProofEvaluation, RewriteStrategyId, SemanticRewritePlan,
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
pub const MAX_PYTHON_RE_LOWERING_NODES: usize = 65_536;

/// Maximum Semantic IR nesting admitted by one lowering invocation.
pub const MAX_PYTHON_RE_LOWERING_DEPTH: usize = 128;

/// Stable target-lowering failure categories.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum PythonReLoweringErrorCode {
    InvalidSemanticProgram,
    ResourceLimitExceeded,
    InvalidTargetProfile,
    NonPythonReTarget,
    IncompatibleTargetProfile,
    InvalidPortabilityPlan,
    ProgramFingerprintMismatch,
    TargetProfileMismatch,
    VersionMismatch,
    UnresolvedRequirement,
    UnsupportedRequirement,
    MalformedRewritePlan,
    CaptureResolution,
    PatternKindMismatch,
    InvalidLoweringPlan,
}

impl PythonReLoweringErrorCode {
    const fn diagnostic_code(self) -> &'static str {
        match self {
            Self::InvalidSemanticProgram => "STRL-PYTHON_RE_LOWERING-0001",
            Self::ResourceLimitExceeded => "STRL-PYTHON_RE_LOWERING-0002",
            Self::InvalidTargetProfile => "STRL-PYTHON_RE_LOWERING-0003",
            Self::NonPythonReTarget => "STRL-PYTHON_RE_LOWERING-0004",
            Self::IncompatibleTargetProfile => "STRL-PYTHON_RE_LOWERING-0005",
            Self::InvalidPortabilityPlan => "STRL-PYTHON_RE_LOWERING-0006",
            Self::ProgramFingerprintMismatch => "STRL-PYTHON_RE_LOWERING-0007",
            Self::TargetProfileMismatch => "STRL-PYTHON_RE_LOWERING-0008",
            Self::VersionMismatch => "STRL-PYTHON_RE_LOWERING-0009",
            Self::UnresolvedRequirement => "STRL-PYTHON_RE_LOWERING-0010",
            Self::UnsupportedRequirement => "STRL-PYTHON_RE_LOWERING-0011",
            Self::MalformedRewritePlan => "STRL-PYTHON_RE_LOWERING-0012",
            Self::CaptureResolution => "STRL-PYTHON_RE_LOWERING-0013",
            Self::PatternKindMismatch => "STRL-PYTHON_RE_LOWERING-0014",
            Self::InvalidLoweringPlan => "STRL-PYTHON_RE_LOWERING-0015",
        }
    }

    const fn category(self) -> DiagnosticCategory {
        match self {
            Self::InvalidSemanticProgram | Self::CaptureResolution => {
                DiagnosticCategory::SemanticValidity
            }
            Self::ResourceLimitExceeded => DiagnosticCategory::ResourceLimit,
            Self::NonPythonReTarget
            | Self::IncompatibleTargetProfile
            | Self::PatternKindMismatch
            | Self::UnresolvedRequirement
            | Self::UnsupportedRequirement => DiagnosticCategory::TargetCapability,
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

/// All-or-nothing failure from Python re target lowering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReLoweringFailure {
    pub code: PythonReLoweringErrorCode,
    pub diagnostics: Vec<Diagnostic>,
}

impl fmt::Display for PythonReLoweringFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "Python re target lowering failed with {} diagnostic(s)",
            self.diagnostics.len()
        )
    }
}

impl Error for PythonReLoweringFailure {}

/// Python re interpretation of global case intent, retained outside pattern text.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonReCaseMatching {
    Sensitive,
    Insensitive,
}

/// Python pattern/subject representation selected by the target profile.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonRePatternKind {
    Str,
    Bytes,
}

/// One exact profile option selected before serialization or execution.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReOptionPlan {
    pub option_id: OptionId,
    pub stage: OptionStage,
    pub value: EngineOptionValue,
    pub selection: OptionSelection,
}

/// Provenance carried by every target operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReProvenance {
    pub semantic_node_ids: Vec<NodeId>,
    pub source_spans: Vec<SourceSpan>,
    pub applied_rewrite: Option<RequirementIdentity>,
}

/// Python re wildcard behavior without syntax spelling.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonReWildcard {
    ExcludeLineTerminators,
    IncludeLineTerminators,
}

/// Python re built-in character-class identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonReBuiltinClass {
    Digit,
    Word,
    Whitespace,
}

/// Python re built-in class interpretation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonReCharacterDomain {
    Ascii,
    Unicode,
}

/// Structured character-set member awaiting serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PythonReCharacterSetMember {
    Literal {
        value: char,
    },
    Range {
        start: char,
        end: char,
    },
    Builtin {
        name: PythonReBuiltinClass,
        domain: PythonReCharacterDomain,
        negated: bool,
    },
    UnicodeProperty {
        property: String,
        value: Option<String>,
        negated: bool,
    },
}

/// Python re repetition maximum without quantifier punctuation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonReRepetitionMaximum {
    Bounded(u64),
    Unbounded,
}

/// Python re repetition backtracking behavior.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonReRepetitionMode {
    Greedy,
    Lazy,
    Possessive,
}

/// Python re position identity without anchor spelling.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonRePosition {
    InputStart,
    InputEnd,
    LineStart,
    LineEnd,
    WordBoundary,
    NotWordBoundary,
    EndBeforeFinalLineTerminator,
}

/// Python re assertion identity without grouping punctuation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PythonReLookaround {
    PositiveAhead,
    NegativeAhead,
    PositiveBehind,
    NegativeBehind,
}

/// Closed Python re operation vocabulary before regex serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PythonReOperation {
    Empty,
    Sequence(Vec<PythonReNode>),
    Alternation(Vec<PythonReNode>),
    Literal(String),
    Wildcard(PythonReWildcard),
    CharacterSet {
        negated: bool,
        members: Vec<PythonReCharacterSetMember>,
    },
    Repeat {
        body: Box<PythonReNode>,
        min: u64,
        max: PythonReRepetitionMaximum,
        mode: PythonReRepetitionMode,
    },
    Position(PythonRePosition),
    Capture {
        slot: u32,
        capture_id: CaptureId,
        name: Option<String>,
        body: Box<PythonReNode>,
    },
    Backreference {
        slot: u32,
        capture_id: CaptureId,
        name: Option<String>,
    },
    Lookaround {
        assertion: PythonReLookaround,
        body: Box<PythonReNode>,
    },
    Atomic {
        body: Box<PythonReNode>,
    },
}

/// One Python re target node with exact semantic provenance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReNode {
    pub provenance: PythonReProvenance,
    pub operation: PythonReOperation,
}

/// Deterministic logical-capture to Python re slot assignment.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReCapture {
    pub slot: u32,
    pub capture_id: CaptureId,
    pub name: Option<String>,
    pub definition_node_id: NodeId,
    pub source_spans: Vec<SourceSpan>,
}

/// Exact completed planner decision retained by the target plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReRequirementResolution {
    pub identity: RequirementIdentity,
    pub status: ArtifactPortabilityStatus,
    pub rewrite_strategy: Option<RewriteStrategyId>,
}

/// Certified semantic rewrite actually applied by Python re lowering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReAppliedRewrite {
    pub identity: RequirementIdentity,
    pub strategy_id: RewriteStrategyId,
    pub certification: RewriteCertificationEvidence,
    pub affected_node_ids: Vec<NodeId>,
    pub proof: Vec<RewriteProofEvaluation>,
    pub target_profile: TargetProfileReference,
}

/// Complete, deterministic, pre-serialization Python re target representation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReLoweringPlan {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub semantic_program: Sha256Digest,
    pub target_profile: TargetProfileReference,
    pub portability_status: ArtifactPortabilityStatus,
    pub pattern_kind: PythonRePatternKind,
    pub case_matching: PythonReCaseMatching,
    pub options: Vec<PythonReOptionPlan>,
    pub captures: Vec<PythonReCapture>,
    pub requirements: Vec<PythonReRequirementResolution>,
    pub applied_rewrites: Vec<PythonReAppliedRewrite>,
    pub root: PythonReNode,
}

struct CaptureTable {
    ordered: Vec<PythonReCapture>,
    by_id: BTreeMap<CaptureId, PythonReCapture>,
}

struct RewriteTable<'a> {
    by_node: BTreeMap<NodeId, (&'a RequirementIdentity, &'a SemanticRewritePlan)>,
}

/// Lower one exact semantic program and certified plan into structured Python re data.
pub fn lower_python_re(
    input: &SemanticProgram,
    target: &TargetProfile,
    portability: &PortabilityPlan,
) -> Result<PythonReLoweringPlan, PythonReLoweringFailure> {
    enforce_resource_limits(input)?;
    if let Err(errors) = input.validate() {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::InvalidSemanticProgram,
            Some(input.root.node_id()),
            format!("normalized Semantic IR is invalid: {errors}"),
        ));
    }
    if input.normalization != Normalization::CanonicalV1 {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::InvalidSemanticProgram,
            Some(input.root.node_id()),
            "Python re lowering requires canonical-v1 Semantic IR",
        ));
    }
    if let Err(errors) = target.validate() {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::InvalidTargetProfile,
            Some(input.root.node_id()),
            format!("Python re target profile is invalid: {errors}"),
        ));
    }
    if target.engine.id.as_str() != "python_re" {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::NonPythonReTarget,
            Some(input.root.node_id()),
            format!(
                "Python re lowering cannot consume engine {}",
                target.engine.id.as_str()
            ),
        ));
    }
    let Some(runtime) = target.runtime.as_ref() else {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::InvalidTargetProfile,
            Some(input.root.node_id()),
            "Python re lowering requires an explicit CPython runtime identity",
        ));
    };
    if runtime.id.as_str() != "cpython" {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::NonPythonReTarget,
            Some(input.root.node_id()),
            format!(
                "Python re lowering cannot consume runtime {}",
                runtime.id.as_str()
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
            PythonReLoweringErrorCode::IncompatibleTargetProfile,
            Some(input.root.node_id()),
            "Python re target profile does not certify the semantic contract/specification versions",
        ));
    }
    if let Err(errors) = portability.validate() {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::InvalidPortabilityPlan,
            Some(input.root.node_id()),
            format!("portability plan is malformed: {errors}"),
        ));
    }

    let semantic_program = canonical_sha256(input)
        .map(Sha256Digest::from_bytes)
        .map_err(|error| {
            failure(
                input,
                PythonReLoweringErrorCode::ProgramFingerprintMismatch,
                Some(input.root.node_id()),
                format!("semantic program fingerprint could not be derived: {error}"),
            )
        })?;
    if portability.semantic_program != semantic_program {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::ProgramFingerprintMismatch,
            Some(input.root.node_id()),
            "portability plan was not produced for the supplied Semantic IR bytes",
        ));
    }
    let target_profile = target.reference().map_err(|errors| {
        failure(
            input,
            PythonReLoweringErrorCode::InvalidTargetProfile,
            Some(input.root.node_id()),
            format!("Python re target profile reference could not be derived: {errors}"),
        )
    })?;
    if portability.target_profile != target_profile {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::TargetProfileMismatch,
            Some(input.root.node_id()),
            "portability plan does not name the exact supplied Python re profile revision and fingerprint",
        ));
    }
    if portability.contract_version != input.contract_version
        || portability.specification_version != input.specification_version
    {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::VersionMismatch,
            Some(input.root.node_id()),
            "portability plan versions do not match the supplied Semantic IR",
        ));
    }

    let portability_status = completed_status(input, portability)?;
    let captures = collect_captures(input)?;
    let rewrites = validate_rewrites(input, portability)?;
    let requirements = portability
        .decisions
        .iter()
        .map(|decision| match &decision.disposition {
            RequirementPlanningDisposition::Native(_) => PythonReRequirementResolution {
                identity: decision.identity.clone(),
                status: ArtifactPortabilityStatus::Native,
                rewrite_strategy: None,
            },
            RequirementPlanningDisposition::EquivalentRewrite(rewrite) => {
                PythonReRequirementResolution {
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
                Some(PythonReAppliedRewrite {
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
    let options: Vec<_> = target
        .options
        .iter()
        .map(|option| PythonReOptionPlan {
            option_id: option.option_id.clone(),
            stage: option.stage,
            value: option.value.clone(),
            selection: option.selection,
        })
        .collect();
    let pattern_kind = pattern_kind(input, &options)?;

    let plan = PythonReLoweringPlan {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        semantic_program,
        target_profile,
        portability_status,
        pattern_kind,
        case_matching: match input.case_matching {
            CaseMatching::Sensitive => PythonReCaseMatching::Sensitive,
            CaseMatching::Insensitive => PythonReCaseMatching::Insensitive,
        },
        options,
        captures: captures.ordered.clone(),
        requirements,
        applied_rewrites,
        root: lower_node(input, &input.root, &captures, &rewrites)?,
    };
    plan.validate().map_err(|errors| {
        failure(
            input,
            PythonReLoweringErrorCode::InvalidLoweringPlan,
            Some(input.root.node_id()),
            format!("constructed Python re lowering plan is invalid: {errors}"),
        )
    })?;
    Ok(plan)
}

fn pattern_kind(
    input: &SemanticProgram,
    options: &[PythonReOptionPlan],
) -> Result<PythonRePatternKind, PythonReLoweringFailure> {
    let matching: Vec<_> = options
        .iter()
        .filter(|option| option.option_id.as_str() == "python.pattern_kind")
        .collect();
    let [option] = matching.as_slice() else {
        return Err(failure(
            input,
            PythonReLoweringErrorCode::PatternKindMismatch,
            Some(input.root.node_id()),
            "Python re lowering requires exactly one python.pattern_kind option",
        ));
    };
    match &option.value {
        EngineOptionValue::String(value) if value == "str" => Ok(PythonRePatternKind::Str),
        EngineOptionValue::String(value) if value == "bytes" => {
            if semantic_requires_unicode(&input.root) {
                Err(failure(
                    input,
                    PythonReLoweringErrorCode::PatternKindMismatch,
                    Some(input.root.node_id()),
                    "Python bytes patterns cannot preserve Unicode scalar, class, or property semantics",
                ))
            } else {
                Ok(PythonRePatternKind::Bytes)
            }
        }
        EngineOptionValue::String(value) => Err(failure(
            input,
            PythonReLoweringErrorCode::PatternKindMismatch,
            Some(input.root.node_id()),
            format!("unsupported Python pattern kind: {value}"),
        )),
        EngineOptionValue::Number(_) | EngineOptionValue::Boolean(_) => Err(failure(
            input,
            PythonReLoweringErrorCode::PatternKindMismatch,
            Some(input.root.node_id()),
            "python.pattern_kind must be the string 'str' or 'bytes'",
        )),
    }
}

fn semantic_requires_unicode(root: &Node) -> bool {
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        match node {
            Node::Literal { text, .. } if !text.is_ascii() => return true,
            Node::CharacterSet { members, .. }
                if members.iter().any(|member| match member {
                    CharacterSetMember::Literal { value } => !value.get().is_ascii(),
                    CharacterSetMember::Range { start, end } => {
                        !start.get().is_ascii() || !end.get().is_ascii()
                    }
                    CharacterSetMember::Builtin { domain, .. } => {
                        *domain == CharacterDomain::Unicode
                    }
                    CharacterSetMember::UnicodeProperty { .. } => true,
                }) =>
            {
                return true;
            }
            _ => push_children(node, &mut pending),
        }
    }
    false
}

fn completed_status(
    input: &SemanticProgram,
    portability: &PortabilityPlan,
) -> Result<ArtifactPortabilityStatus, PythonReLoweringFailure> {
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
                PythonReLoweringErrorCode::UnsupportedRequirement,
                node_id,
                "Python re lowering requires every semantic requirement to have a native or certified equivalent representation",
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
                PythonReLoweringErrorCode::UnresolvedRequirement,
                node_id,
                "Python re lowering rejects unresolved capability or rewrite evidence",
            ))
        }
    }
}

fn enforce_resource_limits(input: &SemanticProgram) -> Result<(), PythonReLoweringFailure> {
    let mut pending = vec![(&input.root, 1_usize)];
    let mut nodes = 0_usize;
    while let Some((node, depth)) = pending.pop() {
        nodes += 1;
        if nodes > MAX_PYTHON_RE_LOWERING_NODES || depth > MAX_PYTHON_RE_LOWERING_DEPTH {
            return Err(failure(
                input,
                PythonReLoweringErrorCode::ResourceLimitExceeded,
                Some(node.node_id()),
                format!(
                    "Python re lowering limit exceeded (maximum {MAX_PYTHON_RE_LOWERING_NODES} nodes and depth {MAX_PYTHON_RE_LOWERING_DEPTH})"
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

fn collect_captures(input: &SemanticProgram) -> Result<CaptureTable, PythonReLoweringFailure> {
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
                    PythonReLoweringErrorCode::CaptureResolution,
                    Some(node_id),
                    "Python re capture slot capacity exceeded",
                )
            })?;
            ordered.push(PythonReCapture {
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
) -> Result<RewriteTable<'a>, PythonReLoweringFailure> {
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
) -> PythonReLoweringFailure {
    failure(
        input,
        PythonReLoweringErrorCode::MalformedRewritePlan,
        Some(node_id),
        message,
    )
}

fn lower_node(
    input: &SemanticProgram,
    node: &Node,
    captures: &CaptureTable,
    rewrites: &RewriteTable<'_>,
) -> Result<PythonReNode, PythonReLoweringFailure> {
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
                    "request-only exact-once rewrite reached Python re lowering",
                ));
            }
        }
    }

    let operation = match node {
        Node::Empty { .. } => PythonReOperation::Empty,
        Node::Sequence { items, .. } => PythonReOperation::Sequence(
            items
                .iter()
                .map(|item| lower_node(input, item, captures, rewrites))
                .collect::<Result<_, _>>()?,
        ),
        Node::Alternation { branches, .. } => PythonReOperation::Alternation(
            branches
                .iter()
                .map(|branch| lower_node(input, branch, captures, rewrites))
                .collect::<Result<_, _>>()?,
        ),
        Node::Literal { text, .. } => PythonReOperation::Literal(text.clone()),
        Node::Wildcard {
            line_terminators, ..
        } => PythonReOperation::Wildcard(match line_terminators {
            LineTerminators::Exclude => PythonReWildcard::ExcludeLineTerminators,
            LineTerminators::Include => PythonReWildcard::IncludeLineTerminators,
        }),
        Node::CharacterSet {
            negated, members, ..
        } => PythonReOperation::CharacterSet {
            negated: *negated,
            members: members.iter().map(lower_set_member).collect(),
        },
        Node::Repeat {
            body,
            min,
            max,
            mode,
            ..
        } => {
            let mode = match mode {
                RepetitionMode::Greedy => PythonReRepetitionMode::Greedy,
                RepetitionMode::Lazy => PythonReRepetitionMode::Lazy,
                RepetitionMode::Possessive => PythonReRepetitionMode::Possessive,
            };
            PythonReOperation::Repeat {
                body: Box::new(lower_node(input, body, captures, rewrites)?),
                min: *min,
                max: match max {
                    RepetitionMaximum::Bounded(maximum) => {
                        PythonReRepetitionMaximum::Bounded(*maximum)
                    }
                    RepetitionMaximum::Unbounded => PythonReRepetitionMaximum::Unbounded,
                },
                mode,
            }
        }
        Node::Position { position, .. } => PythonReOperation::Position(match position {
            PositionKind::InputStart => PythonRePosition::InputStart,
            PositionKind::InputEnd => PythonRePosition::InputEnd,
            PositionKind::LineStart => PythonRePosition::LineStart,
            PositionKind::LineEnd => PythonRePosition::LineEnd,
            PositionKind::WordBoundary => PythonRePosition::WordBoundary,
            PositionKind::NotWordBoundary => PythonRePosition::NotWordBoundary,
            PositionKind::EndBeforeFinalLineTerminator => {
                PythonRePosition::EndBeforeFinalLineTerminator
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
                    PythonReLoweringErrorCode::CaptureResolution,
                    Some(node.node_id()),
                    format!(
                        "capture {} has no deterministic Python re slot",
                        capture_id.as_str()
                    ),
                )
            })?;
            PythonReOperation::Capture {
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
                    PythonReLoweringErrorCode::CaptureResolution,
                    Some(node.node_id()),
                    format!(
                        "backreference {} has no deterministic Python re capture slot",
                        capture_id.as_str()
                    ),
                )
            })?;
            PythonReOperation::Backreference {
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
        } => PythonReOperation::Lookaround {
            assertion: match (direction, polarity) {
                (LookaroundDirection::Ahead, AssertionPolarity::Positive) => {
                    PythonReLookaround::PositiveAhead
                }
                (LookaroundDirection::Ahead, AssertionPolarity::Negative) => {
                    PythonReLookaround::NegativeAhead
                }
                (LookaroundDirection::Behind, AssertionPolarity::Positive) => {
                    PythonReLookaround::PositiveBehind
                }
                (LookaroundDirection::Behind, AssertionPolarity::Negative) => {
                    PythonReLookaround::NegativeBehind
                }
            },
            body: Box::new(lower_node(input, body, captures, rewrites)?),
        },
        Node::Atomic { body, .. } => PythonReOperation::Atomic {
            body: Box::new(lower_node(input, body, captures, rewrites)?),
        },
    };
    Ok(PythonReNode {
        provenance: provenance(node),
        operation,
    })
}

fn lower_set_member(member: &CharacterSetMember) -> PythonReCharacterSetMember {
    match member {
        CharacterSetMember::Literal { value } => {
            PythonReCharacterSetMember::Literal { value: value.get() }
        }
        CharacterSetMember::Range { start, end } => PythonReCharacterSetMember::Range {
            start: start.get(),
            end: end.get(),
        },
        CharacterSetMember::Builtin {
            name,
            domain,
            negated,
        } => PythonReCharacterSetMember::Builtin {
            name: match name {
                BuiltinClassName::Digit => PythonReBuiltinClass::Digit,
                BuiltinClassName::Word => PythonReBuiltinClass::Word,
                BuiltinClassName::Whitespace => PythonReBuiltinClass::Whitespace,
            },
            domain: match domain {
                CharacterDomain::Ascii => PythonReCharacterDomain::Ascii,
                CharacterDomain::Unicode => PythonReCharacterDomain::Unicode,
            },
            negated: *negated,
        },
        CharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => PythonReCharacterSetMember::UnicodeProperty {
            property: property.clone(),
            value: value.clone(),
            negated: *negated,
        },
    }
}

fn provenance(node: &Node) -> PythonReProvenance {
    let mut semantic_node_ids = vec![node.node_id().clone()];
    if let Some(derived) = node
        .origin()
        .and_then(|origin| origin.derived_from_node_ids.as_ref())
    {
        semantic_node_ids.extend(derived.iter().cloned());
    }
    semantic_node_ids.sort();
    semantic_node_ids.dedup();
    PythonReProvenance {
        semantic_node_ids,
        source_spans: source_spans(node),
        applied_rewrite: None,
    }
}

fn merge_provenance(
    mut wrapper: PythonReProvenance,
    body: PythonReProvenance,
    rewrite: RequirementIdentity,
) -> PythonReProvenance {
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
    code: PythonReLoweringErrorCode,
    node_id: Option<&NodeId>,
    message: impl Into<String>,
) -> PythonReLoweringFailure {
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
            .expect("authored Python re lowering diagnostic code must be valid"),
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
    PythonReLoweringFailure {
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

impl Validate for PythonReLoweringPlan {
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
                "Python re options must have unique sorted identities",
            ));
        }
        let pattern_options: Vec<_> = self
            .options
            .iter()
            .filter(|option| option.option_id.as_str() == "python.pattern_kind")
            .collect();
        let expected_pattern = match self.pattern_kind {
            PythonRePatternKind::Str => "str",
            PythonRePatternKind::Bytes => "bytes",
        };
        if pattern_options.len() != 1
            || !matches!(
                &pattern_options[0].value,
                EngineOptionValue::String(value) if value == expected_pattern
            )
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalStructure,
                "$.pattern_kind",
                "Python pattern kind must correspond to the exact profile option",
            ));
        }
        for (index, capture) in self.captures.iter().enumerate() {
            if capture.slot != u32::try_from(index + 1).unwrap_or(u32::MAX) {
                errors.push(ValidationError::new(
                    ValidationCode::NonCanonicalOrder,
                    format!("$.captures[{index}].slot"),
                    "Python re capture slots must be consecutive and one-based",
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
                "Python re capture identities and definitions must be unique",
            ));
        }
        if self
            .requirements
            .iter()
            .enumerate()
            .any(|(index, requirement)| requirement.identity.ordinal != index as u32)
        {
            errors.push(ValidationError::new(
                ValidationCode::NonCanonicalOrder,
                "$.requirements",
                "requirement resolutions must retain canonical planner order",
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
            .requirements
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
    root: &PythonReNode,
    captures: &[PythonReCapture],
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
        if nodes > MAX_PYTHON_RE_LOWERING_NODES || depth > MAX_PYTHON_RE_LOWERING_DEPTH {
            errors.push(ValidationError::new(
                ValidationCode::InvalidBounds,
                path,
                "Python re target tree exceeds lowering resource limits",
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
            PythonReOperation::Capture {
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
            PythonReOperation::Backreference {
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
            PythonReOperation::Sequence(children) => {
                for (index, child) in children.iter().enumerate().rev() {
                    pending.push((child, format!("{path}.items[{index}]"), depth + 1));
                }
            }
            PythonReOperation::Alternation(children) => {
                for (index, child) in children.iter().enumerate().rev() {
                    pending.push((child, format!("{path}.branches[{index}]"), depth + 1));
                }
            }
            PythonReOperation::Repeat { body, .. }
            | PythonReOperation::Lookaround { body, .. }
            | PythonReOperation::Atomic { body } => {
                pending.push((body, format!("{path}.body"), depth + 1));
            }
            PythonReOperation::Empty
            | PythonReOperation::Literal(_)
            | PythonReOperation::Wildcard(_)
            | PythonReOperation::CharacterSet { .. }
            | PythonReOperation::Position(_) => {}
        }
    }
}
