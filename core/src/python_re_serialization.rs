//! Pure deterministic serialization of structured Python `re` lowering plans.
//!
//! This module mechanically projects one validated [`PythonReLoweringPlan`]
//! into Python regular-expression source, canonical flags, and a
//! [`TargetArtifact`]. It does not evaluate capabilities, plan or apply
//! rewrites, execute Python, or consult ambient state.

use std::collections::{BTreeMap, BTreeSet};
use std::convert::TryFrom;
use std::error::Error;
use std::fmt;
use std::fmt::Write;

use crate::diagnostic::{
    Advice, AdviceKind, CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode,
    DiagnosticOccurrence, Severity, SeverityBasis,
};
use crate::python_re_lowering::{
    PythonReBuiltinClass, PythonReCaseMatching, PythonReCharacterDomain,
    PythonReCharacterSetMember, PythonReLookaround, PythonReLoweringPlan, PythonReNode,
    PythonReOperation, PythonRePatternKind, PythonRePosition, PythonReProvenance,
    PythonReRepetitionMaximum, PythonReRepetitionMode, PythonReWildcard,
};
use crate::source::{CoordinateSystem, NodeId, SourceSpan, Utf8Encoding};
use crate::target::{
    EmittedPattern, EngineOption, EngineOptionValue, GeneratedSpan, OptionStage, PatternSyntax,
    RequirementId, ResolutionCode, ResolvedRequirement, SourceMapEntry, TargetArtifact,
};
use crate::validation::Validate;

/// Maximum UTF-8 bytes emitted for one Python `re` pattern source.
pub const MAX_PYTHON_RE_PATTERN_BYTES: usize = 16 * 1024 * 1024;

/// Largest repetition count admitted by CPython 3.11's `_sre` parser.
pub const MAX_PYTHON_RE_REPETITION: u64 = 4_294_967_294;

const PYTHON_RE_STR_PROFILE_ID: &str = "profile:python-re/3.11";
const PYTHON_RE_STR_PROFILE_VERSION: &str = "1.4.0";
const PYTHON_RE_STR_PROFILE_SHA256: &str =
    "b3d5e5cbce0a2cd1f0f236914b7d35abc6e7c7614ff9d80d4ee2b7c546d5f3cf";
const PYTHON_RE_BYTES_PROFILE_ID: &str = "profile:python-re/3.11-bytes";
const PYTHON_RE_BYTES_PROFILE_VERSION: &str = "1.2.0";
const PYTHON_RE_BYTES_PROFILE_SHA256: &str =
    "385ed4271e999db85dd0d4c1fd2894c50b2eb16e0d40a3c83b0306fb7fa1805c";
const PATTERN_KIND_OPTION: &str = "python.pattern_kind";

/// Stable Python `re` serialization failure categories.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum PythonReSerializationErrorCode {
    InvalidLoweringPlan,
    InvalidCapture,
    UnsupportedUnicodeProperty,
    PatternKindMismatch,
    SyntaxLimitExceeded,
    ResourceLimitExceeded,
    InvalidFlags,
    InvalidArtifact,
}

impl PythonReSerializationErrorCode {
    const fn diagnostic_code(self) -> &'static str {
        match self {
            Self::InvalidLoweringPlan => "STRL-PYTHON_RE_EMIT-0001",
            Self::InvalidCapture => "STRL-PYTHON_RE_EMIT-0002",
            Self::UnsupportedUnicodeProperty => "STRL-PYTHON_RE_EMIT-0003",
            Self::PatternKindMismatch => "STRL-PYTHON_RE_EMIT-0004",
            Self::SyntaxLimitExceeded => "STRL-PYTHON_RE_EMIT-0005",
            Self::ResourceLimitExceeded => "STRL-PYTHON_RE_EMIT-0006",
            Self::InvalidFlags => "STRL-PYTHON_RE_EMIT-0007",
            Self::InvalidArtifact => "STRL-PYTHON_RE_EMIT-0008",
        }
    }

    const fn category(self) -> DiagnosticCategory {
        match self {
            Self::InvalidLoweringPlan | Self::InvalidArtifact => DiagnosticCategory::Internal,
            Self::ResourceLimitExceeded => DiagnosticCategory::ResourceLimit,
            Self::InvalidCapture
            | Self::UnsupportedUnicodeProperty
            | Self::PatternKindMismatch
            | Self::SyntaxLimitExceeded
            | Self::InvalidFlags => DiagnosticCategory::TargetCapability,
        }
    }
}

/// All-or-nothing failure from Python `re` serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PythonReSerializationFailure {
    pub code: PythonReSerializationErrorCode,
    pub diagnostics: Vec<Diagnostic>,
}

impl fmt::Display for PythonReSerializationFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "Python re serialization failed with {} diagnostic(s)",
            self.diagnostics.len()
        )
    }
}

impl Error for PythonReSerializationFailure {}

#[derive(Clone, Debug)]
struct EmitProblem {
    code: PythonReSerializationErrorCode,
    provenance: PythonReProvenance,
    message: String,
}

#[derive(Default)]
struct MappedProvenance {
    node_ids: BTreeSet<NodeId>,
    source_spans: BTreeSet<SourceSpan>,
}

#[derive(Default)]
struct PatternEmitter {
    text: String,
    source_map: BTreeMap<(u64, u64), MappedProvenance>,
}

impl PatternEmitter {
    fn push(
        &mut self,
        value: &str,
        provenance: &PythonReProvenance,
    ) -> Result<(), Box<EmitProblem>> {
        if value
            .len()
            .checked_add(self.text.len())
            .map_or(true, |length| length > MAX_PYTHON_RE_PATTERN_BYTES)
        {
            return Err(problem(
                PythonReSerializationErrorCode::ResourceLimitExceeded,
                provenance,
                format!(
                    "serialized Python re pattern exceeds {MAX_PYTHON_RE_PATTERN_BYTES} UTF-8 bytes"
                ),
            ));
        }
        self.text.push_str(value);
        Ok(())
    }

    fn offset(&self) -> u64 {
        u64::try_from(self.text.len()).expect("pattern byte limit fits u64")
    }

    fn record(&mut self, start: u64, end: u64, provenance: &PythonReProvenance) {
        let mapped = self.source_map.entry((start, end)).or_default();
        mapped
            .node_ids
            .extend(provenance.semantic_node_ids.iter().cloned());
        mapped
            .source_spans
            .extend(provenance.source_spans.iter().cloned());
    }

    fn finish_source_map(self) -> (String, Vec<SourceMapEntry>) {
        let source_map = self
            .source_map
            .into_iter()
            .map(|((start, end), provenance)| SourceMapEntry {
                generated_span: GeneratedSpan {
                    coordinate_system: CoordinateSystem::Utf8Bytes,
                    start,
                    end,
                },
                node_ids: provenance.node_ids.into_iter().collect(),
                source_spans: provenance.source_spans.into_iter().collect(),
            })
            .collect();
        (self.text, source_map)
    }
}

/// Serialize one exact structured Python `re` plan into the canonical artifact.
pub fn serialize_python_re(
    plan: &PythonReLoweringPlan,
) -> Result<TargetArtifact, PythonReSerializationFailure> {
    if let Err(errors) = plan.validate() {
        return Err(failure(
            plan,
            *problem(
                PythonReSerializationErrorCode::InvalidLoweringPlan,
                &plan.root.provenance,
                format!("Python re lowering plan is malformed: {errors}"),
            ),
        ));
    }
    validate_profile_reference(plan).map_err(|found| failure(plan, *found))?;
    validate_pattern_kind(plan).map_err(|found| failure(plan, *found))?;
    validate_capture_plan(plan).map_err(|found| failure(plan, *found))?;
    let flags = materialize_flags(plan).map_err(|found| failure(plan, *found))?;

    let mut emitter = PatternEmitter::default();
    emit_node(&mut emitter, &plan.root, plan.pattern_kind)
        .map_err(|found| failure(plan, *found))?;
    let full_end = emitter.offset();
    emitter.record(0, full_end, &plan.root.provenance);
    let (text, source_map) = emitter.finish_source_map();

    let engine_options = plan
        .options
        .iter()
        .map(|option| EngineOption {
            option_id: option.option_id.clone(),
            stage: option.stage,
            value: option.value.clone(),
        })
        .collect();
    let requirements = project_requirements(plan).map_err(|found| failure(plan, *found))?;
    let artifact = TargetArtifact {
        contract_version: plan.contract_version,
        specification_version: plan.specification_version.clone(),
        target_profile: plan.target_profile.clone(),
        portability_status: plan.portability_status,
        pattern: EmittedPattern {
            syntax: PatternSyntax::Regex,
            encoding: Utf8Encoding::Utf8,
            text,
            flags,
        },
        engine_options,
        requirements,
        source_map,
        emission_diagnostics: Vec::new(),
    };
    artifact.validate().map_err(|errors| {
        failure(
            plan,
            *problem(
                PythonReSerializationErrorCode::InvalidArtifact,
                &plan.root.provenance,
                format!("constructed Python re TargetArtifact is invalid: {errors}"),
            ),
        )
    })?;
    Ok(artifact)
}

fn validate_profile_reference(plan: &PythonReLoweringPlan) -> Result<(), Box<EmitProblem>> {
    let expected = match plan.pattern_kind {
        PythonRePatternKind::Str => (
            PYTHON_RE_STR_PROFILE_ID,
            PYTHON_RE_STR_PROFILE_VERSION,
            PYTHON_RE_STR_PROFILE_SHA256,
        ),
        PythonRePatternKind::Bytes => (
            PYTHON_RE_BYTES_PROFILE_ID,
            PYTHON_RE_BYTES_PROFILE_VERSION,
            PYTHON_RE_BYTES_PROFILE_SHA256,
        ),
    };
    if plan.target_profile.profile_id.as_str() != expected.0
        || plan.target_profile.profile_version.as_str() != expected.1
        || plan.target_profile.sha256.as_str() != expected.2
    {
        return Err(problem(
            PythonReSerializationErrorCode::InvalidFlags,
            &plan.root.provenance,
            "Python re serialization requires the exact governed str or bytes 3.11 profile",
        ));
    }
    Ok(())
}

fn validate_pattern_kind(plan: &PythonReLoweringPlan) -> Result<(), Box<EmitProblem>> {
    let matching = plan
        .options
        .iter()
        .filter(|option| option.option_id.as_str() == PATTERN_KIND_OPTION)
        .collect::<Vec<_>>();
    let [option] = matching.as_slice() else {
        return Err(problem(
            PythonReSerializationErrorCode::PatternKindMismatch,
            &plan.root.provenance,
            "Python re serialization requires exactly one python.pattern_kind option",
        ));
    };
    let expected = match plan.pattern_kind {
        PythonRePatternKind::Str => "str",
        PythonRePatternKind::Bytes => "bytes",
    };
    if option.stage != OptionStage::Runtime
        || !matches!(&option.value, EngineOptionValue::String(value) if value == expected)
    {
        return Err(problem(
            PythonReSerializationErrorCode::PatternKindMismatch,
            &plan.root.provenance,
            "python.pattern_kind must be the runtime-stage value matching the lowering plan",
        ));
    }
    Ok(())
}

fn materialize_flags(plan: &PythonReLoweringPlan) -> Result<Vec<String>, Box<EmitProblem>> {
    match plan.case_matching {
        PythonReCaseMatching::Sensitive => Ok(Vec::new()),
        PythonReCaseMatching::Insensitive => Ok(vec!["i".to_owned()]),
    }
}

fn validate_capture_plan(plan: &PythonReLoweringPlan) -> Result<(), Box<EmitProblem>> {
    let captures: BTreeMap<_, _> = plan
        .captures
        .iter()
        .map(|capture| (&capture.capture_id, capture))
        .collect();
    let mut names = BTreeSet::new();
    for capture in &plan.captures {
        if capture.slot == 0 {
            return Err(problem(
                PythonReSerializationErrorCode::SyntaxLimitExceeded,
                &plan.root.provenance,
                "Python re capture slots start at one",
            ));
        }
        if let Some(name) = &capture.name {
            validate_ascii_identifier(name).map_err(|message| {
                problem(
                    PythonReSerializationErrorCode::InvalidCapture,
                    &plan.root.provenance,
                    format!("Python re capture name {name:?} is invalid: {message}"),
                )
            })?;
            if !names.insert(name) {
                return Err(problem(
                    PythonReSerializationErrorCode::InvalidCapture,
                    &plan.root.provenance,
                    format!("duplicate Python re capture name {name:?}"),
                ));
            }
        }
    }

    let mut definitions = BTreeSet::new();
    let mut pending = vec![&plan.root];
    while let Some(node) = pending.pop() {
        match &node.operation {
            PythonReOperation::Capture {
                slot,
                capture_id,
                name,
                body,
            } => {
                let declared = captures.get(capture_id);
                if declared.map_or(true, |capture| {
                    capture.slot != *slot || capture.name.as_ref() != name.as_ref()
                }) || !definitions.insert(capture_id)
                {
                    return Err(problem(
                        PythonReSerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        "Python re capture operation does not correspond exactly to one capture-table entry",
                    ));
                }
                pending.push(body);
            }
            PythonReOperation::Backreference {
                slot,
                capture_id,
                name,
            } => {
                if captures.get(capture_id).map_or(true, |capture| {
                    capture.slot != *slot || capture.name.as_ref() != name.as_ref()
                }) {
                    return Err(problem(
                        PythonReSerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        "Python re backreference does not correspond exactly to the capture table",
                    ));
                }
                if name.is_none() && *slot > 99 {
                    return Err(problem(
                        PythonReSerializationErrorCode::SyntaxLimitExceeded,
                        &node.provenance,
                        "Python re decimal pattern backreferences are limited to capture slots 1 through 99",
                    ));
                }
            }
            PythonReOperation::Sequence(children) | PythonReOperation::Alternation(children) => {
                pending.extend(children.iter().rev())
            }
            PythonReOperation::Repeat { body, .. }
            | PythonReOperation::Lookaround { body, .. }
            | PythonReOperation::Atomic { body } => pending.push(body),
            PythonReOperation::Empty
            | PythonReOperation::Literal(_)
            | PythonReOperation::Wildcard(_)
            | PythonReOperation::CharacterSet { .. }
            | PythonReOperation::Position(_) => {}
        }
    }
    if definitions.len() != captures.len() {
        return Err(problem(
            PythonReSerializationErrorCode::InvalidCapture,
            &plan.root.provenance,
            "Python re capture table contains a definition absent from the target operation tree",
        ));
    }
    Ok(())
}

fn project_requirements(
    plan: &PythonReLoweringPlan,
) -> Result<Vec<ResolvedRequirement>, Box<EmitProblem>> {
    let mut projected: Vec<_> = plan
        .requirements
        .iter()
        .enumerate()
        .map(|(index, requirement)| {
            let semantic = index < plan.semantic_requirements.len();
            let namespace = if semantic { "semantic" } else { "lowering" };
            let ordinal = if semantic {
                index
            } else {
                index - plan.semantic_requirements.len()
            };
            let requirement_id_value = format!("requirement:{namespace}.{ordinal:010}");
            let requirement_id =
                RequirementId::try_from(requirement_id_value.as_str()).map_err(|message| {
                    problem(
                        PythonReSerializationErrorCode::InvalidLoweringPlan,
                        &plan.root.provenance,
                        message,
                    )
                })?;
            let resolution = if semantic {
                requirement
                    .rewrite_strategy
                    .map_or("profile_capability_resolved", |strategy| strategy.as_str())
            } else {
                "lowering_introduced_profile_capability_resolved"
            };
            let resolution_code = ResolutionCode::try_from(resolution).map_err(|message| {
                problem(
                    PythonReSerializationErrorCode::InvalidLoweringPlan,
                    &plan.root.provenance,
                    message,
                )
            })?;
            Ok(ResolvedRequirement {
                requirement_id,
                capability_id: requirement.identity.capability_id.clone(),
                status: requirement.status,
                resolution_code,
            })
        })
        .collect::<Result<Vec<ResolvedRequirement>, Box<EmitProblem>>>()?;
    projected.sort_by(|left, right| left.requirement_id.cmp(&right.requirement_id));
    Ok(projected)
}

fn emit_node(
    emitter: &mut PatternEmitter,
    node: &PythonReNode,
    pattern_kind: PythonRePatternKind,
) -> Result<(), Box<EmitProblem>> {
    let start = emitter.offset();
    match &node.operation {
        PythonReOperation::Empty => {}
        PythonReOperation::Sequence(children) => {
            for child in children {
                emit_node(emitter, child, pattern_kind)?;
            }
        }
        PythonReOperation::Alternation(branches) => {
            emitter.push("(?:", &node.provenance)?;
            for (index, branch) in branches.iter().enumerate() {
                if index != 0 {
                    emitter.push("|", &node.provenance)?;
                }
                emit_node(emitter, branch, pattern_kind)?;
            }
            emitter.push(")", &node.provenance)?;
        }
        PythonReOperation::Literal(text) => {
            for character in text.chars() {
                validate_scalar_for_kind(character, pattern_kind, node)?;
                emitter.push(
                    &escape_pattern_character(character, pattern_kind),
                    &node.provenance,
                )?;
            }
        }
        PythonReOperation::Wildcard(PythonReWildcard::NativeExclude) => {
            emitter.push(".", &node.provenance)?;
        }
        PythonReOperation::Wildcard(PythonReWildcard::CanonicalExclude) => {
            emitter.push(r"[^\n\v\f\r\x85\u2028\u2029]", &node.provenance)?;
        }
        PythonReOperation::Wildcard(PythonReWildcard::Include) => {
            emitter.push("(?s:.)", &node.provenance)?;
        }
        PythonReOperation::CharacterSet { negated, members } => {
            emit_character_set(emitter, node, pattern_kind, *negated, members)?;
        }
        PythonReOperation::Repeat {
            body,
            min,
            max,
            mode,
        } => {
            let maximum = match max {
                PythonReRepetitionMaximum::Bounded(value) => Some(*value),
                PythonReRepetitionMaximum::Unbounded => None,
            };
            if *min > MAX_PYTHON_RE_REPETITION
                || maximum.is_some_and(|value| value > MAX_PYTHON_RE_REPETITION)
                || maximum.is_some_and(|value| value < *min)
            {
                return Err(problem(
                    PythonReSerializationErrorCode::SyntaxLimitExceeded,
                    &node.provenance,
                    "Python re repetition bounds exceed CPython 3.11 syntax limits",
                ));
            }
            emitter.push("(?:", &node.provenance)?;
            emit_node(emitter, body, pattern_kind)?;
            emitter.push(")", &node.provenance)?;
            emitter.push(&quantifier(*min, maximum), &node.provenance)?;
            match mode {
                PythonReRepetitionMode::Greedy => {}
                PythonReRepetitionMode::Lazy => emitter.push("?", &node.provenance)?,
                PythonReRepetitionMode::Possessive => emitter.push("+", &node.provenance)?,
            }
        }
        PythonReOperation::Position(position) => {
            let spelling = match position {
                PythonRePosition::InputStart => r"\A",
                PythonRePosition::InputEnd => r"\Z",
                PythonRePosition::LineStart => "(?m:^)",
                PythonRePosition::LineEnd => "(?m:$)",
                PythonRePosition::CanonicalLineStart => {
                    r"(?:\A|(?<=\n)|(?<=[\v\f\x85\u2028\u2029])|(?<=\r)(?!\n))"
                }
                PythonRePosition::CanonicalLineEnd => {
                    r"(?:\Z|(?=[\v\f\r\x85\u2028\u2029])|(?<!\r)(?=\n))"
                }
                PythonRePosition::WordBoundary => r"\b",
                PythonRePosition::NotWordBoundary => r"\B",
                PythonRePosition::EndBeforeFinalLineTerminator => "$",
                PythonRePosition::CanonicalEndBeforeFinalLineTerminator => {
                    r"(?:\Z|(?=(?:\r\n|[\v\f\r\x85\u2028\u2029])\Z)|(?<!\r)(?=\n\Z))"
                }
            };
            emitter.push(spelling, &node.provenance)?;
        }
        PythonReOperation::Capture {
            name, body, slot, ..
        } => {
            if *slot == 0 {
                return Err(problem(
                    PythonReSerializationErrorCode::SyntaxLimitExceeded,
                    &node.provenance,
                    "Python re capture slots start at one",
                ));
            }
            if let Some(name) = name {
                validate_ascii_identifier(name).map_err(|message| {
                    problem(
                        PythonReSerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        format!("Python re capture name {name:?} is invalid: {message}"),
                    )
                })?;
                emitter.push("(?P<", &node.provenance)?;
                emitter.push(name, &node.provenance)?;
                emitter.push(">", &node.provenance)?;
            } else {
                emitter.push("(", &node.provenance)?;
            }
            emit_node(emitter, body, pattern_kind)?;
            emitter.push(")", &node.provenance)?;
        }
        PythonReOperation::Backreference { slot, name, .. } => {
            emitter.push("(?:", &node.provenance)?;
            if let Some(name) = name {
                validate_ascii_identifier(name).map_err(|message| {
                    problem(
                        PythonReSerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        format!("Python re backreference name {name:?} is invalid: {message}"),
                    )
                })?;
                emitter.push("(?P=", &node.provenance)?;
                emitter.push(name, &node.provenance)?;
                emitter.push(")", &node.provenance)?;
            } else {
                emitter.push(&format!(r"\{slot}"), &node.provenance)?;
            }
            emitter.push(")", &node.provenance)?;
        }
        PythonReOperation::Lookaround { assertion, body } => {
            let prefix = match assertion {
                PythonReLookaround::PositiveAhead => "(?=",
                PythonReLookaround::NegativeAhead => "(?!",
                PythonReLookaround::PositiveBehind => "(?<=",
                PythonReLookaround::NegativeBehind => "(?<!",
            };
            emitter.push(prefix, &node.provenance)?;
            emit_node(emitter, body, pattern_kind)?;
            emitter.push(")", &node.provenance)?;
        }
        PythonReOperation::Atomic { body } => {
            emitter.push("(?>", &node.provenance)?;
            emit_node(emitter, body, pattern_kind)?;
            emitter.push(")", &node.provenance)?;
        }
    }
    let end = emitter.offset();
    emitter.record(start, end, &node.provenance);
    Ok(())
}

fn quantifier(minimum: u64, maximum: Option<u64>) -> String {
    match (minimum, maximum) {
        (0, None) => "*".to_owned(),
        (1, None) => "+".to_owned(),
        (0, Some(1)) => "?".to_owned(),
        (minimum, Some(maximum)) if minimum == maximum => format!("{{{minimum}}}"),
        (minimum, None) => format!("{{{minimum},}}"),
        (minimum, Some(maximum)) => format!("{{{minimum},{maximum}}}"),
    }
}

fn emit_character_set(
    emitter: &mut PatternEmitter,
    node: &PythonReNode,
    pattern_kind: PythonRePatternKind,
    negated: bool,
    members: &[PythonReCharacterSetMember],
) -> Result<(), Box<EmitProblem>> {
    if members.is_empty() {
        return emitter.push(if negated { "(?s:.)" } else { "(?!)" }, &node.provenance);
    }
    if negated {
        emitter.push("(?!(?:", &node.provenance)?;
    } else if members.len() > 1 {
        emitter.push("(?:", &node.provenance)?;
    }
    for (index, member) in members.iter().enumerate() {
        if index != 0 {
            emitter.push("|", &node.provenance)?;
        }
        emit_member_atom(emitter, node, pattern_kind, member)?;
    }
    if negated {
        emitter.push("))(?s:.)", &node.provenance)?;
    } else if members.len() > 1 {
        emitter.push(")", &node.provenance)?;
    }
    Ok(())
}

fn emit_member_atom(
    emitter: &mut PatternEmitter,
    node: &PythonReNode,
    pattern_kind: PythonRePatternKind,
    member: &PythonReCharacterSetMember,
) -> Result<(), Box<EmitProblem>> {
    match member {
        PythonReCharacterSetMember::Literal { value } => {
            validate_scalar_for_kind(*value, pattern_kind, node)?;
            emitter.push("[", &node.provenance)?;
            emitter.push(
                &escape_class_character(*value, pattern_kind),
                &node.provenance,
            )?;
            emitter.push("]", &node.provenance)
        }
        PythonReCharacterSetMember::Range { start, end } => {
            validate_scalar_for_kind(*start, pattern_kind, node)?;
            validate_scalar_for_kind(*end, pattern_kind, node)?;
            if start > end {
                return Err(problem(
                    PythonReSerializationErrorCode::InvalidLoweringPlan,
                    &node.provenance,
                    "Python re character range start exceeds its end",
                ));
            }
            emitter.push("[", &node.provenance)?;
            emitter.push(
                &escape_class_character(*start, pattern_kind),
                &node.provenance,
            )?;
            emitter.push("-", &node.provenance)?;
            emitter.push(
                &escape_class_character(*end, pattern_kind),
                &node.provenance,
            )?;
            emitter.push("]", &node.provenance)
        }
        PythonReCharacterSetMember::Builtin {
            name,
            domain,
            negated,
        } => emitter.push(
            builtin_atom(*name, *domain, *negated, pattern_kind).ok_or_else(|| {
                problem(
                    PythonReSerializationErrorCode::PatternKindMismatch,
                    &node.provenance,
                    "Python bytes patterns cannot serialize Unicode-domain built-in classes",
                )
            })?,
            &node.provenance,
        ),
        PythonReCharacterSetMember::UnicodeProperty { .. } => Err(problem(
            PythonReSerializationErrorCode::UnsupportedUnicodeProperty,
            &node.provenance,
            "Python re does not support Unicode property escape syntax",
        )),
    }
}

fn builtin_atom(
    name: PythonReBuiltinClass,
    domain: PythonReCharacterDomain,
    negated: bool,
    pattern_kind: PythonRePatternKind,
) -> Option<&'static str> {
    match (pattern_kind, domain, name, negated) {
        (_, PythonReCharacterDomain::TargetNative, PythonReBuiltinClass::Digit, false) => {
            Some(r"\d")
        }
        (_, PythonReCharacterDomain::TargetNative, PythonReBuiltinClass::Digit, true) => {
            Some(r"\D")
        }
        (_, PythonReCharacterDomain::TargetNative, PythonReBuiltinClass::Word, false) => {
            Some(r"\w")
        }
        (_, PythonReCharacterDomain::TargetNative, PythonReBuiltinClass::Word, true) => Some(r"\W"),
        (_, PythonReCharacterDomain::TargetNative, PythonReBuiltinClass::Whitespace, false) => {
            Some(r"\s")
        }
        (_, PythonReCharacterDomain::TargetNative, PythonReBuiltinClass::Whitespace, true) => {
            Some(r"\S")
        }
        (PythonRePatternKind::Bytes, PythonReCharacterDomain::Unicode, _, _) => None,
        (_, PythonReCharacterDomain::Ascii, PythonReBuiltinClass::Digit, false) => Some(r"(?a:\d)"),
        (_, PythonReCharacterDomain::Ascii, PythonReBuiltinClass::Digit, true) => Some(r"(?a:\D)"),
        (_, PythonReCharacterDomain::Ascii, PythonReBuiltinClass::Word, false) => Some(r"(?a:\w)"),
        (_, PythonReCharacterDomain::Ascii, PythonReBuiltinClass::Word, true) => Some(r"(?a:\W)"),
        (_, PythonReCharacterDomain::Ascii, PythonReBuiltinClass::Whitespace, false) => {
            Some(r"(?a:\s)")
        }
        (_, PythonReCharacterDomain::Ascii, PythonReBuiltinClass::Whitespace, true) => {
            Some(r"(?a:\S)")
        }
        (
            PythonRePatternKind::Str,
            PythonReCharacterDomain::Unicode,
            PythonReBuiltinClass::Digit,
            false,
        ) => Some(r"(?u:\d)"),
        (
            PythonRePatternKind::Str,
            PythonReCharacterDomain::Unicode,
            PythonReBuiltinClass::Digit,
            true,
        ) => Some(r"(?u:\D)"),
        (
            PythonRePatternKind::Str,
            PythonReCharacterDomain::Unicode,
            PythonReBuiltinClass::Word,
            false,
        ) => Some(r"(?u:\w)"),
        (
            PythonRePatternKind::Str,
            PythonReCharacterDomain::Unicode,
            PythonReBuiltinClass::Word,
            true,
        ) => Some(r"(?u:\W)"),
        (
            PythonRePatternKind::Str,
            PythonReCharacterDomain::Unicode,
            PythonReBuiltinClass::Whitespace,
            false,
        ) => Some(r"(?u:\s)"),
        (
            PythonRePatternKind::Str,
            PythonReCharacterDomain::Unicode,
            PythonReBuiltinClass::Whitespace,
            true,
        ) => Some(r"(?u:\S)"),
    }
}

fn validate_scalar_for_kind(
    character: char,
    pattern_kind: PythonRePatternKind,
    node: &PythonReNode,
) -> Result<(), Box<EmitProblem>> {
    if pattern_kind == PythonRePatternKind::Bytes && !character.is_ascii() {
        return Err(problem(
            PythonReSerializationErrorCode::PatternKindMismatch,
            &node.provenance,
            "Python bytes pattern source may contain only ASCII scalars",
        ));
    }
    Ok(())
}

fn validate_ascii_identifier(value: &str) -> Result<(), &'static str> {
    let mut characters = value.chars();
    let Some(first) = characters.next() else {
        return Err("identifier is empty");
    };
    if !(first.is_ascii_alphabetic() || first == '_') {
        return Err("identifier must start with an ASCII letter or underscore");
    }
    if !characters.all(|character| character.is_ascii_alphanumeric() || character == '_') {
        return Err("identifier may contain only ASCII letters, digits, and underscores");
    }
    Ok(())
}

fn escape_pattern_character(character: char, pattern_kind: PythonRePatternKind) -> String {
    match character {
        '\\' | '^' | '$' | '.' | '|' | '?' | '*' | '+' | '(' | ')' | '[' | ']' | '{' | '}' => {
            format!(r"\{character}")
        }
        ' ' | '#' => code_point_escape(character, pattern_kind),
        value if value.is_control() || value.is_whitespace() => {
            code_point_escape(value, pattern_kind)
        }
        value => value.to_string(),
    }
}

fn escape_class_character(character: char, pattern_kind: PythonRePatternKind) -> String {
    match character {
        '\\' | '[' | ']' | '-' | '^' | ' ' | '#' => code_point_escape(character, pattern_kind),
        value if value.is_control() || value.is_whitespace() => {
            code_point_escape(value, pattern_kind)
        }
        value => value.to_string(),
    }
}

fn code_point_escape(character: char, pattern_kind: PythonRePatternKind) -> String {
    let value = u32::from(character);
    let mut escaped = String::new();
    match (pattern_kind, value) {
        (_, 0..=0xff) => write!(&mut escaped, r"\x{value:02x}"),
        (PythonRePatternKind::Str, 0x100..=0xffff) => {
            write!(&mut escaped, r"\u{value:04x}")
        }
        (PythonRePatternKind::Str, _) => write!(&mut escaped, r"\U{value:08x}"),
        (PythonRePatternKind::Bytes, _) => {
            unreachable!("bytes scalar validation precedes escaping")
        }
    }
    .expect("writing to String cannot fail");
    escaped
}

fn problem(
    code: PythonReSerializationErrorCode,
    provenance: &PythonReProvenance,
    message: impl Into<String>,
) -> Box<EmitProblem> {
    Box::new(EmitProblem {
        code,
        provenance: provenance.clone(),
        message: message.into(),
    })
}

fn failure(plan: &PythonReLoweringPlan, problem: EmitProblem) -> PythonReSerializationFailure {
    let primary_location = problem
        .provenance
        .source_spans
        .iter()
        .min_by(|left, right| {
            (left.end - left.start)
                .cmp(&(right.end - right.start))
                .then_with(|| left.cmp(right))
        })
        .cloned();
    let node_advice = problem
        .provenance
        .semantic_node_ids
        .first()
        .map(|node_id| Advice {
            kind: AdviceKind::Note,
            message: format!("Affected Semantic IR node: {}.", node_id.as_str()),
        });
    let diagnostic = Diagnostic {
        contract_version: plan.contract_version,
        occurrence: DiagnosticOccurrence::new(0),
        code: DiagnosticCode::try_from(problem.code.diagnostic_code())
            .expect("authored Python re emission diagnostic code must be valid"),
        severity: Severity::Error,
        severity_basis: SeverityBasis::TargetProfile,
        phase: CompilerPhase::Emission,
        category: problem.code.category(),
        message: problem.message,
        primary_location,
        related_locations: None,
        advice: node_advice.map(|advice| vec![advice]),
        fixes: None,
    };
    PythonReSerializationFailure {
        code: problem.code,
        diagnostics: vec![diagnostic],
    }
}

#[cfg(test)]
mod tests {
    use super::{
        escape_class_character, escape_pattern_character, quantifier, PythonRePatternKind,
    };

    #[test]
    fn primitive_spellings_are_canonical() {
        assert_eq!(
            escape_pattern_character('.', PythonRePatternKind::Str),
            r"\."
        );
        assert_eq!(
            escape_pattern_character(' ', PythonRePatternKind::Str),
            r"\x20"
        );
        assert_eq!(
            escape_pattern_character('\u{2028}', PythonRePatternKind::Str),
            r"\u2028"
        );
        assert_eq!(
            escape_pattern_character('😀', PythonRePatternKind::Str),
            "😀"
        );
        assert_eq!(
            escape_class_character('-', PythonRePatternKind::Bytes),
            r"\x2d"
        );
        assert_eq!(quantifier(0, None), "*");
        assert_eq!(quantifier(1, None), "+");
        assert_eq!(quantifier(0, Some(1)), "?");
        assert_eq!(quantifier(2, Some(2)), "{2}");
        assert_eq!(quantifier(2, None), "{2,}");
        assert_eq!(quantifier(2, Some(4)), "{2,4}");
    }
}
