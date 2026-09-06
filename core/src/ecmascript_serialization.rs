//! Pure deterministic serialization of structured ECMAScript lowering plans.
//!
//! This module mechanically projects one validated [`EcmascriptLoweringPlan`]
//! into ECMAScript RegExp source, canonical flags, and a [`TargetArtifact`]. It
//! does not evaluate capabilities, plan or apply rewrites, execute JavaScript,
//! or consult ambient state.

use std::collections::{BTreeMap, BTreeSet};
use std::convert::TryFrom;
use std::error::Error;
use std::fmt;
use std::fmt::Write;

use crate::diagnostic::{
    Advice, AdviceKind, CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode,
    DiagnosticOccurrence, Severity, SeverityBasis,
};
use crate::ecmascript_lowering::{
    EcmascriptBuiltinClass, EcmascriptCaseMatching, EcmascriptCharacterDomain,
    EcmascriptCharacterSetMember, EcmascriptLookaround, EcmascriptLoweringPlan, EcmascriptNode,
    EcmascriptOperation, EcmascriptPosition, EcmascriptProvenance, EcmascriptRepetitionMaximum,
    EcmascriptRepetitionMode, EcmascriptWildcard,
};
use crate::source::{CoordinateSystem, NodeId, SourceSpan, Utf8Encoding};
use crate::target::{
    EmittedPattern, EngineOption, EngineOptionValue, GeneratedSpan, OptionStage, PatternSyntax,
    RequirementId, ResolutionCode, ResolvedRequirement, SourceMapEntry, TargetArtifact,
};
use crate::validation::Validate;

/// Maximum UTF-8 bytes emitted for one ECMAScript pattern source.
pub const MAX_ECMASCRIPT_PATTERN_BYTES: usize = 16 * 1024 * 1024;

const ECMASCRIPT_PROFILE_ID: &str = "profile:ecmascript/2024";
const ECMASCRIPT_PROFILE_VERSION: &str = "1.2.0";
const ECMASCRIPT_PROFILE_SHA256: &str =
    "5b012d7b0536610d4496718e6954c8f9ec80c16dde26a18f70663d0275ec333e";
const UNICODE_MODE_OPTION: &str = "ecmascript.unicode_mode";

/// Stable ECMAScript serialization failure categories.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum EcmascriptSerializationErrorCode {
    InvalidLoweringPlan,
    InvalidCapture,
    InvalidUnicodeProperty,
    SyntaxLimitExceeded,
    ResourceLimitExceeded,
    InvalidFlags,
    InvalidArtifact,
}

impl EcmascriptSerializationErrorCode {
    const fn diagnostic_code(self) -> &'static str {
        match self {
            Self::InvalidLoweringPlan => "STRL-ECMASCRIPT_EMIT-0001",
            Self::InvalidCapture => "STRL-ECMASCRIPT_EMIT-0002",
            Self::InvalidUnicodeProperty => "STRL-ECMASCRIPT_EMIT-0003",
            Self::SyntaxLimitExceeded => "STRL-ECMASCRIPT_EMIT-0004",
            Self::ResourceLimitExceeded => "STRL-ECMASCRIPT_EMIT-0005",
            Self::InvalidFlags => "STRL-ECMASCRIPT_EMIT-0006",
            Self::InvalidArtifact => "STRL-ECMASCRIPT_EMIT-0007",
        }
    }

    const fn category(self) -> DiagnosticCategory {
        match self {
            Self::InvalidLoweringPlan | Self::InvalidArtifact => DiagnosticCategory::Internal,
            Self::InvalidCapture
            | Self::InvalidUnicodeProperty
            | Self::SyntaxLimitExceeded
            | Self::InvalidFlags => DiagnosticCategory::TargetCapability,
            Self::ResourceLimitExceeded => DiagnosticCategory::ResourceLimit,
        }
    }
}

/// All-or-nothing failure from ECMAScript serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EcmascriptSerializationFailure {
    pub code: EcmascriptSerializationErrorCode,
    pub diagnostics: Vec<Diagnostic>,
}

impl fmt::Display for EcmascriptSerializationFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "ECMAScript serialization failed with {} diagnostic(s)",
            self.diagnostics.len()
        )
    }
}

impl Error for EcmascriptSerializationFailure {}

#[derive(Clone, Debug)]
struct EmitProblem {
    code: EcmascriptSerializationErrorCode,
    provenance: EcmascriptProvenance,
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
        provenance: &EcmascriptProvenance,
    ) -> Result<(), Box<EmitProblem>> {
        if value
            .len()
            .checked_add(self.text.len())
            .map_or(true, |length| length > MAX_ECMASCRIPT_PATTERN_BYTES)
        {
            return Err(problem(
                EcmascriptSerializationErrorCode::ResourceLimitExceeded,
                provenance,
                format!(
                    "serialized ECMAScript pattern exceeds {MAX_ECMASCRIPT_PATTERN_BYTES} UTF-8 bytes"
                ),
            ));
        }
        self.text.push_str(value);
        Ok(())
    }

    fn offset(&self) -> u64 {
        u64::try_from(self.text.len()).expect("pattern byte limit fits u64")
    }

    fn record(&mut self, start: u64, end: u64, provenance: &EcmascriptProvenance) {
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

/// Serialize one exact structured ECMAScript plan into the canonical artifact.
pub fn serialize_ecmascript(
    plan: &EcmascriptLoweringPlan,
) -> Result<TargetArtifact, EcmascriptSerializationFailure> {
    if let Err(errors) = plan.validate() {
        return Err(failure(
            plan,
            *problem(
                EcmascriptSerializationErrorCode::InvalidLoweringPlan,
                &plan.root.provenance,
                format!("ECMAScript lowering plan is malformed: {errors}"),
            ),
        ));
    }
    validate_profile_reference(plan).map_err(|found| failure(plan, *found))?;
    validate_capture_plan(plan).map_err(|found| failure(plan, *found))?;
    validate_flag_interactions(plan).map_err(|found| failure(plan, *found))?;
    let flags = materialize_flags(plan).map_err(|found| failure(plan, *found))?;

    let mut emitter = PatternEmitter::default();
    emit_node(&mut emitter, &plan.root).map_err(|found| failure(plan, *found))?;
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
                EcmascriptSerializationErrorCode::InvalidArtifact,
                &plan.root.provenance,
                format!("constructed ECMAScript TargetArtifact is invalid: {errors}"),
            ),
        )
    })?;
    Ok(artifact)
}

fn validate_profile_reference(plan: &EcmascriptLoweringPlan) -> Result<(), Box<EmitProblem>> {
    if plan.target_profile.profile_id.as_str() != ECMASCRIPT_PROFILE_ID
        || plan.target_profile.profile_version.as_str() != ECMASCRIPT_PROFILE_VERSION
        || plan.target_profile.sha256.as_str() != ECMASCRIPT_PROFILE_SHA256
    {
        return Err(problem(
            EcmascriptSerializationErrorCode::InvalidFlags,
            &plan.root.provenance,
            "ECMAScript serialization requires the exact governed 2024 profile revision 1.2.0",
        ));
    }
    Ok(())
}

fn materialize_flags(plan: &EcmascriptLoweringPlan) -> Result<Vec<String>, Box<EmitProblem>> {
    let unicode = plan
        .options
        .iter()
        .find(|option| option.option_id.as_str() == UNICODE_MODE_OPTION)
        .ok_or_else(|| {
            problem(
                EcmascriptSerializationErrorCode::InvalidFlags,
                &plan.root.provenance,
                "ECMAScript artifact requires the profile-owned Unicode mode option",
            )
        })?;
    if unicode.stage != OptionStage::Compile
        || !matches!(&unicode.value, EngineOptionValue::String(value) if value == "u")
    {
        return Err(problem(
            EcmascriptSerializationErrorCode::InvalidFlags,
            &plan.root.provenance,
            "ECMAScript Unicode mode must materialize as the compile-stage u flag",
        ));
    }

    let mut flags = Vec::with_capacity(2);
    if plan.case_matching == EcmascriptCaseMatching::Insensitive {
        flags.push("i".to_owned());
    }
    flags.push("u".to_owned());
    Ok(flags)
}

fn validate_flag_interactions(plan: &EcmascriptLoweringPlan) -> Result<(), Box<EmitProblem>> {
    if plan.case_matching != EcmascriptCaseMatching::Insensitive {
        return Ok(());
    }
    let mut pending = vec![&plan.root];
    while let Some(node) = pending.pop() {
        match &node.operation {
            EcmascriptOperation::CharacterSet { members, .. } => {
                if members.iter().any(|member| {
                    matches!(
                        member,
                        EcmascriptCharacterSetMember::Builtin {
                            name: EcmascriptBuiltinClass::Word,
                            domain: EcmascriptCharacterDomain::Ascii,
                            ..
                        }
                    )
                }) {
                    return Err(problem(
                        EcmascriptSerializationErrorCode::InvalidFlags,
                        &node.provenance,
                        "ES2024 global i cannot preserve exact ASCII word membership without scoped flag removal",
                    ));
                }
            }
            EcmascriptOperation::Sequence(children)
            | EcmascriptOperation::Alternation(children) => {
                pending.extend(children.iter().rev());
            }
            EcmascriptOperation::Repeat { body, .. }
            | EcmascriptOperation::Capture { body, .. }
            | EcmascriptOperation::Lookaround { body, .. } => pending.push(body),
            EcmascriptOperation::Empty
            | EcmascriptOperation::Literal(_)
            | EcmascriptOperation::Wildcard(_)
            | EcmascriptOperation::Position(_)
            | EcmascriptOperation::Backreference { .. } => {}
        }
    }
    Ok(())
}

fn validate_capture_plan(plan: &EcmascriptLoweringPlan) -> Result<(), Box<EmitProblem>> {
    let captures: BTreeMap<_, _> = plan
        .captures
        .iter()
        .map(|capture| (&capture.capture_id, capture))
        .collect();
    let mut names = BTreeSet::new();
    for capture in &plan.captures {
        if capture.slot == 0 {
            return Err(problem(
                EcmascriptSerializationErrorCode::SyntaxLimitExceeded,
                &plan.root.provenance,
                "ECMAScript capture slots start at one",
            ));
        }
        if let Some(name) = &capture.name {
            validate_ascii_identifier(name).map_err(|message| {
                problem(
                    EcmascriptSerializationErrorCode::InvalidCapture,
                    &plan.root.provenance,
                    format!("ECMAScript capture name {name:?} is invalid: {message}"),
                )
            })?;
            if !names.insert(name) {
                return Err(problem(
                    EcmascriptSerializationErrorCode::InvalidCapture,
                    &plan.root.provenance,
                    format!("duplicate ECMAScript capture name {name:?} is not ES2024 syntax"),
                ));
            }
        }
    }

    let mut definitions = BTreeSet::new();
    let mut pending = vec![&plan.root];
    while let Some(node) = pending.pop() {
        match &node.operation {
            EcmascriptOperation::Capture {
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
                        EcmascriptSerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        "ECMAScript capture operation does not correspond exactly to one capture-table entry",
                    ));
                }
                pending.push(body);
            }
            EcmascriptOperation::Backreference {
                slot,
                capture_id,
                name,
            } => {
                if captures.get(capture_id).map_or(true, |capture| {
                    capture.slot != *slot || capture.name.as_ref() != name.as_ref()
                }) {
                    return Err(problem(
                        EcmascriptSerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        "ECMAScript backreference does not correspond exactly to the capture table",
                    ));
                }
            }
            EcmascriptOperation::Sequence(children)
            | EcmascriptOperation::Alternation(children) => {
                pending.extend(children.iter().rev());
            }
            EcmascriptOperation::Repeat { body, .. }
            | EcmascriptOperation::Lookaround { body, .. } => pending.push(body),
            EcmascriptOperation::Empty
            | EcmascriptOperation::Literal(_)
            | EcmascriptOperation::Wildcard(_)
            | EcmascriptOperation::CharacterSet { .. }
            | EcmascriptOperation::Position(_) => {}
        }
    }
    if definitions.len() != captures.len() {
        return Err(problem(
            EcmascriptSerializationErrorCode::InvalidCapture,
            &plan.root.provenance,
            "ECMAScript capture table contains a definition absent from the target operation tree",
        ));
    }
    Ok(())
}

fn project_requirements(
    plan: &EcmascriptLoweringPlan,
) -> Result<Vec<ResolvedRequirement>, Box<EmitProblem>> {
    plan.requirements
        .iter()
        .map(|requirement| {
            let requirement_id_value =
                format!("requirement:semantic.{:010}", requirement.identity.ordinal);
            let requirement_id =
                RequirementId::try_from(requirement_id_value.as_str()).map_err(|message| {
                    problem(
                        EcmascriptSerializationErrorCode::InvalidLoweringPlan,
                        &plan.root.provenance,
                        message,
                    )
                })?;
            let resolution = requirement
                .rewrite_strategy
                .map_or("profile_capability_resolved", |strategy| strategy.as_str());
            let resolution_code = ResolutionCode::try_from(resolution).map_err(|message| {
                problem(
                    EcmascriptSerializationErrorCode::InvalidLoweringPlan,
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
        .collect()
}

fn emit_node(emitter: &mut PatternEmitter, node: &EcmascriptNode) -> Result<(), Box<EmitProblem>> {
    let start = emitter.offset();
    match &node.operation {
        EcmascriptOperation::Empty => {}
        EcmascriptOperation::Sequence(children) => {
            for child in children {
                emit_node(emitter, child)?;
            }
        }
        EcmascriptOperation::Alternation(branches) => {
            emitter.push("(?:", &node.provenance)?;
            for (index, branch) in branches.iter().enumerate() {
                if index != 0 {
                    emitter.push("|", &node.provenance)?;
                }
                emit_node(emitter, branch)?;
            }
            emitter.push(")", &node.provenance)?;
        }
        EcmascriptOperation::Literal(text) => {
            for character in text.chars() {
                emitter.push(&escape_pattern_character(character), &node.provenance)?;
            }
        }
        EcmascriptOperation::Wildcard(EcmascriptWildcard::ExcludeLineTerminators) => {
            emitter.push(".", &node.provenance)?;
        }
        EcmascriptOperation::Wildcard(EcmascriptWildcard::IncludeLineTerminators) => {
            emitter.push(r"[\s\S]", &node.provenance)?;
        }
        EcmascriptOperation::CharacterSet { negated, members } => {
            emit_character_set(emitter, node, *negated, members)?;
        }
        EcmascriptOperation::Repeat {
            body,
            min,
            max,
            mode,
        } => {
            let maximum = match max {
                EcmascriptRepetitionMaximum::Bounded(value) => Some(*value),
                EcmascriptRepetitionMaximum::Unbounded => None,
            };
            if maximum.is_some_and(|value| value < *min) {
                return Err(problem(
                    EcmascriptSerializationErrorCode::SyntaxLimitExceeded,
                    &node.provenance,
                    "ECMAScript repetition maximum is smaller than its minimum",
                ));
            }
            emitter.push("(?:", &node.provenance)?;
            emit_node(emitter, body)?;
            emitter.push(")", &node.provenance)?;
            emitter.push(&quantifier(*min, maximum), &node.provenance)?;
            if *mode == EcmascriptRepetitionMode::Lazy {
                emitter.push("?", &node.provenance)?;
            }
        }
        EcmascriptOperation::Position(position) => {
            let spelling = match position {
                EcmascriptPosition::InputStart => "^",
                EcmascriptPosition::InputEnd => r"(?![\s\S])",
                EcmascriptPosition::LineStart => r"(?:^|(?<=[\n\r\u2028\u2029]))",
                EcmascriptPosition::LineEnd => r"(?=$|[\n\r\u2028\u2029])",
                EcmascriptPosition::WordBoundary => r"\b",
                EcmascriptPosition::NotWordBoundary => r"\B",
                EcmascriptPosition::EndBeforeFinalLineTerminator => {
                    r"(?=$|(?:\r\n|[\r\u2028\u2029]|(?<!\r)\n)(?![\s\S]))"
                }
            };
            emitter.push(spelling, &node.provenance)?;
        }
        EcmascriptOperation::Capture {
            name, body, slot, ..
        } => {
            if *slot == 0 {
                return Err(problem(
                    EcmascriptSerializationErrorCode::SyntaxLimitExceeded,
                    &node.provenance,
                    "ECMAScript capture slots start at one",
                ));
            }
            if let Some(name) = name {
                validate_ascii_identifier(name).map_err(|message| {
                    problem(
                        EcmascriptSerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        format!("ECMAScript capture name {name:?} is invalid: {message}"),
                    )
                })?;
                emitter.push("(?<", &node.provenance)?;
                emitter.push(name, &node.provenance)?;
                emitter.push(">", &node.provenance)?;
            } else {
                emitter.push("(", &node.provenance)?;
            }
            emit_node(emitter, body)?;
            emitter.push(")", &node.provenance)?;
        }
        EcmascriptOperation::Backreference { slot, name, .. } => {
            emitter.push("(?:", &node.provenance)?;
            if let Some(name) = name {
                validate_ascii_identifier(name).map_err(|message| {
                    problem(
                        EcmascriptSerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        format!("ECMAScript backreference name {name:?} is invalid: {message}"),
                    )
                })?;
                emitter.push(r"\k<", &node.provenance)?;
                emitter.push(name, &node.provenance)?;
                emitter.push(">", &node.provenance)?;
            } else {
                emitter.push(&format!(r"\{slot}"), &node.provenance)?;
            }
            emitter.push(")", &node.provenance)?;
        }
        EcmascriptOperation::Lookaround { assertion, body } => {
            let prefix = match assertion {
                EcmascriptLookaround::PositiveAhead => "(?=",
                EcmascriptLookaround::NegativeAhead => "(?!",
                EcmascriptLookaround::PositiveBehind => "(?<=",
                EcmascriptLookaround::NegativeBehind => "(?<!",
            };
            emitter.push(prefix, &node.provenance)?;
            emit_node(emitter, body)?;
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
    node: &EcmascriptNode,
    negated: bool,
    members: &[EcmascriptCharacterSetMember],
) -> Result<(), Box<EmitProblem>> {
    if members
        .iter()
        .any(|member| matches!(member, EcmascriptCharacterSetMember::Builtin { .. }))
    {
        return emit_set_as_atoms(emitter, node, negated, members);
    }

    emitter.push(if negated { "[^" } else { "[" }, &node.provenance)?;
    for member in members {
        emit_class_member(emitter, node, member)?;
    }
    emitter.push("]", &node.provenance)
}

fn emit_set_as_atoms(
    emitter: &mut PatternEmitter,
    node: &EcmascriptNode,
    negated: bool,
    members: &[EcmascriptCharacterSetMember],
) -> Result<(), Box<EmitProblem>> {
    if negated {
        emitter.push("(?!(?:", &node.provenance)?;
    } else if members.len() > 1 {
        emitter.push("(?:", &node.provenance)?;
    }
    for (index, member) in members.iter().enumerate() {
        if index != 0 {
            emitter.push("|", &node.provenance)?;
        }
        emit_member_atom(emitter, node, member)?;
    }
    if negated {
        emitter.push(r"))[\s\S]", &node.provenance)?;
    } else if members.len() > 1 {
        emitter.push(")", &node.provenance)?;
    }
    Ok(())
}

fn emit_class_member(
    emitter: &mut PatternEmitter,
    node: &EcmascriptNode,
    member: &EcmascriptCharacterSetMember,
) -> Result<(), Box<EmitProblem>> {
    match member {
        EcmascriptCharacterSetMember::Literal { value } => {
            emitter.push(&escape_class_character(*value), &node.provenance)
        }
        EcmascriptCharacterSetMember::Range { start, end } => {
            emitter.push(&escape_class_character(*start), &node.provenance)?;
            emitter.push("-", &node.provenance)?;
            emitter.push(&escape_class_character(*end), &node.provenance)
        }
        EcmascriptCharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => emit_unicode_property(emitter, node, property, value.as_deref(), *negated),
        EcmascriptCharacterSetMember::Builtin { .. } => {
            unreachable!("built-ins select atom-based set emission")
        }
    }
}

fn emit_member_atom(
    emitter: &mut PatternEmitter,
    node: &EcmascriptNode,
    member: &EcmascriptCharacterSetMember,
) -> Result<(), Box<EmitProblem>> {
    match member {
        EcmascriptCharacterSetMember::Literal { value } => {
            emitter.push("[", &node.provenance)?;
            emitter.push(&escape_class_character(*value), &node.provenance)?;
            emitter.push("]", &node.provenance)
        }
        EcmascriptCharacterSetMember::Range { start, end } => {
            emitter.push("[", &node.provenance)?;
            emitter.push(&escape_class_character(*start), &node.provenance)?;
            emitter.push("-", &node.provenance)?;
            emitter.push(&escape_class_character(*end), &node.provenance)?;
            emitter.push("]", &node.provenance)
        }
        EcmascriptCharacterSetMember::Builtin {
            name,
            domain,
            negated,
        } => emitter.push(builtin_atom(*name, *domain, *negated), &node.provenance),
        EcmascriptCharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => emit_unicode_property(emitter, node, property, value.as_deref(), *negated),
    }
}

fn builtin_atom(
    name: EcmascriptBuiltinClass,
    domain: EcmascriptCharacterDomain,
    negated: bool,
) -> &'static str {
    match (domain, name, negated) {
        (EcmascriptCharacterDomain::Ascii, EcmascriptBuiltinClass::Digit, false) => "[0-9]",
        (EcmascriptCharacterDomain::Ascii, EcmascriptBuiltinClass::Digit, true) => "[^0-9]",
        (EcmascriptCharacterDomain::Ascii, EcmascriptBuiltinClass::Word, false) => "[A-Za-z0-9_]",
        (EcmascriptCharacterDomain::Ascii, EcmascriptBuiltinClass::Word, true) => "[^A-Za-z0-9_]",
        (EcmascriptCharacterDomain::Ascii, EcmascriptBuiltinClass::Whitespace, false) => {
            r"[\x09-\x0d\x20]"
        }
        (EcmascriptCharacterDomain::Ascii, EcmascriptBuiltinClass::Whitespace, true) => {
            r"[^\x09-\x0d\x20]"
        }
        (EcmascriptCharacterDomain::TargetNative, EcmascriptBuiltinClass::Digit, false) => r"\d",
        (EcmascriptCharacterDomain::TargetNative, EcmascriptBuiltinClass::Digit, true) => r"\D",
        (EcmascriptCharacterDomain::TargetNative, EcmascriptBuiltinClass::Word, false) => r"\w",
        (EcmascriptCharacterDomain::TargetNative, EcmascriptBuiltinClass::Word, true) => r"\W",
        (EcmascriptCharacterDomain::TargetNative, EcmascriptBuiltinClass::Whitespace, false) => {
            r"\s"
        }
        (EcmascriptCharacterDomain::TargetNative, EcmascriptBuiltinClass::Whitespace, true) => {
            r"\S"
        }
        (EcmascriptCharacterDomain::Unicode, EcmascriptBuiltinClass::Digit, false) => {
            r"\p{Decimal_Number}"
        }
        (EcmascriptCharacterDomain::Unicode, EcmascriptBuiltinClass::Digit, true) => {
            r"\P{Decimal_Number}"
        }
        (EcmascriptCharacterDomain::Unicode, EcmascriptBuiltinClass::Whitespace, false) => {
            r"\p{White_Space}"
        }
        (EcmascriptCharacterDomain::Unicode, EcmascriptBuiltinClass::Whitespace, true) => {
            r"\P{White_Space}"
        }
        (EcmascriptCharacterDomain::Unicode, EcmascriptBuiltinClass::Word, false) => {
            r"[\p{Letter}\p{Number}\p{Nonspacing_Mark}\p{Connector_Punctuation}]"
        }
        (EcmascriptCharacterDomain::Unicode, EcmascriptBuiltinClass::Word, true) => {
            r"[^\p{Letter}\p{Number}\p{Nonspacing_Mark}\p{Connector_Punctuation}]"
        }
    }
}

fn emit_unicode_property(
    emitter: &mut PatternEmitter,
    node: &EcmascriptNode,
    property: &str,
    value: Option<&str>,
    negated: bool,
) -> Result<(), Box<EmitProblem>> {
    validate_unicode_identifier(property).map_err(|message| {
        problem(
            EcmascriptSerializationErrorCode::InvalidUnicodeProperty,
            &node.provenance,
            format!("ECMAScript Unicode property {property:?} is invalid: {message}"),
        )
    })?;
    if let Some(value) = value {
        validate_unicode_identifier(value).map_err(|message| {
            problem(
                EcmascriptSerializationErrorCode::InvalidUnicodeProperty,
                &node.provenance,
                format!("ECMAScript Unicode property value {value:?} is invalid: {message}"),
            )
        })?;
    }
    emitter.push(if negated { r"\P{" } else { r"\p{" }, &node.provenance)?;
    emitter.push(property, &node.provenance)?;
    if let Some(value) = value {
        emitter.push("=", &node.provenance)?;
        emitter.push(value, &node.provenance)?;
    }
    emitter.push("}", &node.provenance)
}

fn validate_unicode_identifier(value: &str) -> Result<(), &'static str> {
    if value.len() > 128 {
        return Err("Unicode property identifier exceeds 128 ASCII code units");
    }
    validate_ascii_identifier(value)
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

fn escape_pattern_character(character: char) -> String {
    match character {
        '\\' | '^' | '$' | '.' | '|' | '?' | '*' | '+' | '(' | ')' | '[' | ']' | '{' | '}'
        | '/' => format!(r"\{character}"),
        '\t' => r"\t".to_owned(),
        '\n' => r"\n".to_owned(),
        '\r' => r"\r".to_owned(),
        '\u{000c}' => r"\f".to_owned(),
        '\u{000b}' => r"\v".to_owned(),
        ' ' | '#' => code_point_escape(character),
        value if value.is_control() || value.is_whitespace() => code_point_escape(value),
        value => value.to_string(),
    }
}

fn escape_class_character(character: char) -> String {
    match character {
        '\t' => r"\t".to_owned(),
        '\n' => r"\n".to_owned(),
        '\r' => r"\r".to_owned(),
        '\u{000c}' => r"\f".to_owned(),
        '\u{000b}' => r"\v".to_owned(),
        '\\' | '[' | ']' | '-' | '^' | '/' | ' ' | '#' => code_point_escape(character),
        value if value.is_control() || value.is_whitespace() => code_point_escape(value),
        value => value.to_string(),
    }
}

fn code_point_escape(character: char) -> String {
    let value = u32::from(character);
    let mut escaped = String::new();
    match value {
        0..=0xff => write!(&mut escaped, r"\x{value:02x}"),
        0x100..=0xffff => write!(&mut escaped, r"\u{value:04x}"),
        _ => write!(&mut escaped, r"\u{{{value:x}}}"),
    }
    .expect("writing to String cannot fail");
    escaped
}

fn problem(
    code: EcmascriptSerializationErrorCode,
    provenance: &EcmascriptProvenance,
    message: impl Into<String>,
) -> Box<EmitProblem> {
    Box::new(EmitProblem {
        code,
        provenance: provenance.clone(),
        message: message.into(),
    })
}

fn failure(plan: &EcmascriptLoweringPlan, problem: EmitProblem) -> EcmascriptSerializationFailure {
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
            .expect("authored ECMAScript emission diagnostic code must be valid"),
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
    EcmascriptSerializationFailure {
        code: problem.code,
        diagnostics: vec![diagnostic],
    }
}

#[cfg(test)]
mod tests {
    use super::{escape_class_character, escape_pattern_character, quantifier};

    #[test]
    fn primitive_spellings_are_canonical() {
        assert_eq!(escape_pattern_character('.'), r"\.");
        assert_eq!(escape_pattern_character(' '), r"\x20");
        assert_eq!(escape_pattern_character('é'), "é");
        assert_eq!(escape_pattern_character('😀'), "😀");
        assert_eq!(escape_class_character('-'), r"\x2d");
        assert_eq!(escape_class_character('\u{2028}'), r"\u2028");
        assert_eq!(quantifier(0, None), "*");
        assert_eq!(quantifier(1, None), "+");
        assert_eq!(quantifier(0, Some(1)), "?");
        assert_eq!(quantifier(2, Some(2)), "{2}");
        assert_eq!(quantifier(2, None), "{2,}");
        assert_eq!(quantifier(2, Some(4)), "{2,4}");
    }
}
