//! Pure deterministic serialization of structured PCRE2 lowering plans.
//!
//! This module mechanically projects one validated [`Pcre2LoweringPlan`] into
//! PCRE2 regex text and a canonical [`TargetArtifact`]. It does not evaluate
//! capabilities, plan or apply rewrites, execute PCRE2, or consult ambient
//! state.

use std::collections::{BTreeMap, BTreeSet};
use std::convert::TryFrom;
use std::error::Error;
use std::fmt;
use std::fmt::Write;

use crate::diagnostic::{
    Advice, AdviceKind, CompilerPhase, Diagnostic, DiagnosticCategory, DiagnosticCode,
    DiagnosticOccurrence, Severity, SeverityBasis,
};
use crate::source::{CoordinateSystem, NodeId, SourceSpan, Utf8Encoding};
use crate::target::{
    EmittedPattern, EngineOption, GeneratedSpan, PatternSyntax, RequirementId, ResolutionCode,
    ResolvedRequirement, SourceMapEntry, TargetArtifact,
};
use crate::target_lowering::{
    Pcre2BuiltinClass, Pcre2CaseMatching, Pcre2CharacterDomain, Pcre2CharacterSetMember,
    Pcre2Lookaround, Pcre2LoweringPlan, Pcre2Node, Pcre2Operation, Pcre2Position, Pcre2Provenance,
    Pcre2RepetitionMaximum, Pcre2RepetitionMode, Pcre2Wildcard,
};
use crate::validation::Validate;

/// Maximum UTF-8 bytes emitted for one PCRE2 pattern.
pub const MAX_PCRE2_PATTERN_BYTES: usize = 16 * 1024 * 1024;

/// PCRE2's maximum ordinary capture slot and quantifier bound.
pub const MAX_PCRE2_PATTERN_COUNT: u64 = 65_535;

/// PCRE2's documented maximum named-capture length in code units.
pub const MAX_PCRE2_CAPTURE_NAME_CODE_UNITS: usize = 32;

/// Stable PCRE2 serialization failure categories.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum Pcre2SerializationErrorCode {
    InvalidLoweringPlan,
    InvalidCapture,
    InvalidUnicodeProperty,
    SyntaxLimitExceeded,
    ResourceLimitExceeded,
    InvalidArtifact,
}

impl Pcre2SerializationErrorCode {
    const fn diagnostic_code(self) -> &'static str {
        match self {
            Self::InvalidLoweringPlan => "STRL-PCRE2_EMIT-0001",
            Self::InvalidCapture => "STRL-PCRE2_EMIT-0002",
            Self::InvalidUnicodeProperty => "STRL-PCRE2_EMIT-0003",
            Self::SyntaxLimitExceeded => "STRL-PCRE2_EMIT-0004",
            Self::ResourceLimitExceeded => "STRL-PCRE2_EMIT-0005",
            Self::InvalidArtifact => "STRL-PCRE2_EMIT-0006",
        }
    }

    const fn category(self) -> DiagnosticCategory {
        match self {
            Self::InvalidLoweringPlan | Self::InvalidArtifact => DiagnosticCategory::Internal,
            Self::InvalidCapture | Self::InvalidUnicodeProperty | Self::SyntaxLimitExceeded => {
                DiagnosticCategory::TargetCapability
            }
            Self::ResourceLimitExceeded => DiagnosticCategory::ResourceLimit,
        }
    }
}

/// All-or-nothing failure from PCRE2 serialization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Pcre2SerializationFailure {
    pub code: Pcre2SerializationErrorCode,
    pub diagnostics: Vec<Diagnostic>,
}

impl fmt::Display for Pcre2SerializationFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "PCRE2 serialization failed with {} diagnostic(s)",
            self.diagnostics.len()
        )
    }
}

impl Error for Pcre2SerializationFailure {}

#[derive(Clone, Debug)]
struct EmitProblem {
    code: Pcre2SerializationErrorCode,
    provenance: Pcre2Provenance,
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
    fn push(&mut self, value: &str, provenance: &Pcre2Provenance) -> Result<(), Box<EmitProblem>> {
        if value.len() > MAX_PCRE2_PATTERN_BYTES.saturating_sub(self.text.len()) {
            return Err(problem(
                Pcre2SerializationErrorCode::ResourceLimitExceeded,
                provenance,
                format!("serialized PCRE2 pattern exceeds {MAX_PCRE2_PATTERN_BYTES} UTF-8 bytes"),
            ));
        }
        self.text.push_str(value);
        Ok(())
    }

    fn offset(&self) -> u64 {
        u64::try_from(self.text.len()).expect("pattern byte limit fits u64")
    }

    fn record(&mut self, start: u64, end: u64, provenance: &Pcre2Provenance) {
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

/// Serialize one exact structured PCRE2 plan into the canonical artifact.
pub fn serialize_pcre2(
    plan: &Pcre2LoweringPlan,
) -> Result<TargetArtifact, Pcre2SerializationFailure> {
    if let Err(errors) = plan.validate() {
        return Err(failure(
            plan,
            *problem(
                Pcre2SerializationErrorCode::InvalidLoweringPlan,
                &plan.root.provenance,
                format!("PCRE2 lowering plan is malformed: {errors}"),
            ),
        ));
    }
    validate_capture_plan(plan).map_err(|found| failure(plan, *found))?;

    let mut emitter = PatternEmitter::default();
    let full_start = emitter.offset();
    if plan.case_matching == Pcre2CaseMatching::Insensitive {
        emitter
            .push("(?i:", &plan.root.provenance)
            .map_err(|found| failure(plan, *found))?;
    }
    emit_node(&mut emitter, &plan.root).map_err(|found| failure(plan, *found))?;
    if plan.case_matching == Pcre2CaseMatching::Insensitive {
        emitter
            .push(")", &plan.root.provenance)
            .map_err(|found| failure(plan, *found))?;
    }
    emitter.record(full_start, emitter.offset(), &plan.root.provenance);
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
            flags: Vec::new(),
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
                Pcre2SerializationErrorCode::InvalidArtifact,
                &plan.root.provenance,
                format!("constructed PCRE2 TargetArtifact is invalid: {errors}"),
            ),
        )
    })?;
    Ok(artifact)
}

fn validate_capture_plan(plan: &Pcre2LoweringPlan) -> Result<(), Box<EmitProblem>> {
    let captures: BTreeMap<_, _> = plan
        .captures
        .iter()
        .map(|capture| (&capture.capture_id, capture))
        .collect();
    for capture in &plan.captures {
        if u64::from(capture.slot) > MAX_PCRE2_PATTERN_COUNT {
            return Err(problem(
                Pcre2SerializationErrorCode::SyntaxLimitExceeded,
                &plan.root.provenance,
                format!(
                    "PCRE2 capture slot {} exceeds the maximum {MAX_PCRE2_PATTERN_COUNT}",
                    capture.slot
                ),
            ));
        }
        if let Some(name) = &capture.name {
            validate_capture_name(name).map_err(|message| {
                problem(
                    Pcre2SerializationErrorCode::InvalidCapture,
                    &plan.root.provenance,
                    format!("PCRE2 capture name {name:?} is invalid: {message}"),
                )
            })?;
        }
    }

    let mut definitions = BTreeSet::new();
    let mut pending = vec![&plan.root];
    while let Some(node) = pending.pop() {
        match &node.operation {
            Pcre2Operation::Capture {
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
                        Pcre2SerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        "PCRE2 capture operation does not correspond exactly to one capture-table entry",
                    ));
                }
                pending.push(body);
            }
            Pcre2Operation::Backreference {
                slot,
                capture_id,
                name,
            } => {
                if captures.get(capture_id).map_or(true, |capture| {
                    capture.slot != *slot || capture.name.as_ref() != name.as_ref()
                }) {
                    return Err(problem(
                        Pcre2SerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        "PCRE2 backreference does not correspond exactly to the capture table",
                    ));
                }
            }
            Pcre2Operation::Sequence(children) | Pcre2Operation::Alternation(children) => {
                pending.extend(children.iter().rev());
            }
            Pcre2Operation::Repeat { body, .. }
            | Pcre2Operation::Lookaround { body, .. }
            | Pcre2Operation::Atomic(body) => pending.push(body),
            Pcre2Operation::Empty
            | Pcre2Operation::Literal(_)
            | Pcre2Operation::Wildcard(_)
            | Pcre2Operation::CharacterSet { .. }
            | Pcre2Operation::Position(_) => {}
        }
    }
    if definitions.len() != captures.len() {
        return Err(problem(
            Pcre2SerializationErrorCode::InvalidCapture,
            &plan.root.provenance,
            "PCRE2 capture table contains a definition absent from the target operation tree",
        ));
    }
    Ok(())
}

fn project_requirements(
    plan: &Pcre2LoweringPlan,
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
                        Pcre2SerializationErrorCode::InvalidLoweringPlan,
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
                    Pcre2SerializationErrorCode::InvalidLoweringPlan,
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

fn emit_node(emitter: &mut PatternEmitter, node: &Pcre2Node) -> Result<(), Box<EmitProblem>> {
    let start = emitter.offset();
    match &node.operation {
        Pcre2Operation::Empty => {}
        Pcre2Operation::Sequence(children) => {
            for child in children {
                emit_node(emitter, child)?;
            }
        }
        Pcre2Operation::Alternation(branches) => {
            emitter.push("(?:", &node.provenance)?;
            for (index, branch) in branches.iter().enumerate() {
                if index != 0 {
                    emitter.push("|", &node.provenance)?;
                }
                emit_node(emitter, branch)?;
            }
            emitter.push(")", &node.provenance)?;
        }
        Pcre2Operation::Literal(text) => {
            for character in text.chars() {
                emitter.push(&escape_pattern_character(character), &node.provenance)?;
            }
        }
        Pcre2Operation::Wildcard(Pcre2Wildcard::NativeExclude) => {
            emitter.push(".", &node.provenance)?;
        }
        Pcre2Operation::Wildcard(Pcre2Wildcard::CanonicalExclude) => {
            emitter.push(r"[^\n\x{b}\x{c}\r\x{85}\x{2028}\x{2029}]", &node.provenance)?;
        }
        Pcre2Operation::Wildcard(Pcre2Wildcard::Include) => {
            emitter.push("(?s:.)", &node.provenance)?;
        }
        Pcre2Operation::CharacterSet { negated, members } => {
            emit_character_set(emitter, node, *negated, members)?;
        }
        Pcre2Operation::Repeat {
            body,
            min,
            max,
            mode,
        } => {
            let maximum = match max {
                Pcre2RepetitionMaximum::Bounded(value) => Some(*value),
                Pcre2RepetitionMaximum::Unbounded => None,
            };
            if *min > MAX_PCRE2_PATTERN_COUNT
                || maximum.is_some_and(|value| value > MAX_PCRE2_PATTERN_COUNT)
            {
                return Err(problem(
                    Pcre2SerializationErrorCode::SyntaxLimitExceeded,
                    &node.provenance,
                    format!("PCRE2 repetition bounds exceed the maximum {MAX_PCRE2_PATTERN_COUNT}"),
                ));
            }
            emitter.push("(?:", &node.provenance)?;
            emit_node(emitter, body)?;
            emitter.push(")", &node.provenance)?;
            let quantifier = quantifier(*min, maximum);
            emitter.push(&quantifier, &node.provenance)?;
            match mode {
                Pcre2RepetitionMode::Greedy => {}
                Pcre2RepetitionMode::Lazy => emitter.push("?", &node.provenance)?,
                Pcre2RepetitionMode::Possessive => emitter.push("+", &node.provenance)?,
            }
        }
        Pcre2Operation::Position(position) => {
            let spelling = match position {
                Pcre2Position::InputStart => r"\A",
                Pcre2Position::InputEnd => r"\z",
                Pcre2Position::LineStart => "^",
                Pcre2Position::LineEnd => "$",
                Pcre2Position::WordBoundary => r"\b",
                Pcre2Position::NotWordBoundary => r"\B",
                Pcre2Position::EndBeforeFinalLineTerminator => r"\Z",
                Pcre2Position::CanonicalLineStart => {
                    r"(?:\A|(?<=\n)|(?<=[\x{b}\x{c}\x{85}\x{2028}\x{2029}])|(?<=\r)(?!\n))"
                }
                Pcre2Position::CanonicalLineEnd => {
                    r"(?:\z|(?=[\x{b}\x{c}\r\x{85}\x{2028}\x{2029}])|(?<!\r)(?=\n))"
                }
                Pcre2Position::CanonicalWordBoundary => {
                    r"(?:(?<=[\p{L}\p{Mn}\p{N}\p{Pc}])(?![\p{L}\p{Mn}\p{N}\p{Pc}])|(?<![\p{L}\p{Mn}\p{N}\p{Pc}])(?=[\p{L}\p{Mn}\p{N}\p{Pc}]))"
                }
                Pcre2Position::CanonicalNotWordBoundary => {
                    r"(?:(?<=[\p{L}\p{Mn}\p{N}\p{Pc}])(?=[\p{L}\p{Mn}\p{N}\p{Pc}])|(?<![\p{L}\p{Mn}\p{N}\p{Pc}])(?![\p{L}\p{Mn}\p{N}\p{Pc}]))"
                }
                Pcre2Position::CanonicalEndBeforeFinalLineTerminator => {
                    r"(?:\z|(?=(?:\r\n|[\x{b}\x{c}\r\x{85}\x{2028}\x{2029}])\z)|(?<!\r)(?=\n\z))"
                }
            };
            emitter.push(spelling, &node.provenance)?;
        }
        Pcre2Operation::Capture {
            name, body, slot, ..
        } => {
            if let Some(name) = name {
                validate_capture_name(name).map_err(|message| {
                    problem(
                        Pcre2SerializationErrorCode::InvalidCapture,
                        &node.provenance,
                        format!("PCRE2 capture name {name:?} is invalid: {message}"),
                    )
                })?;
                emitter.push("(?<", &node.provenance)?;
                emitter.push(name, &node.provenance)?;
                emitter.push(">", &node.provenance)?;
            } else {
                emitter.push("(", &node.provenance)?;
            }
            if u64::from(*slot) > MAX_PCRE2_PATTERN_COUNT {
                return Err(problem(
                    Pcre2SerializationErrorCode::SyntaxLimitExceeded,
                    &node.provenance,
                    "PCRE2 capture slot exceeds the target syntax limit",
                ));
            }
            emit_node(emitter, body)?;
            emitter.push(")", &node.provenance)?;
        }
        Pcre2Operation::Backreference { slot, .. } => {
            emitter.push(&format!(r"\g{{{slot}}}"), &node.provenance)?;
        }
        Pcre2Operation::Lookaround { assertion, body } => {
            let prefix = match assertion {
                Pcre2Lookaround::PositiveAhead => "(?=",
                Pcre2Lookaround::NegativeAhead => "(?!",
                Pcre2Lookaround::PositiveBehind => "(?<=",
                Pcre2Lookaround::NegativeBehind => "(?<!",
            };
            emitter.push(prefix, &node.provenance)?;
            if matches!(
                assertion,
                Pcre2Lookaround::PositiveBehind | Pcre2Lookaround::NegativeBehind
            ) {
                emit_lookbehind_body(emitter, body)?;
            } else {
                emit_node(emitter, body)?;
            }
            emitter.push(")", &node.provenance)?;
        }
        Pcre2Operation::Atomic(body) => {
            emitter.push("(?>", &node.provenance)?;
            emit_node(emitter, body)?;
            emitter.push(")", &node.provenance)?;
        }
    }
    let end = emitter.offset();
    emitter.record(start, end, &node.provenance);
    Ok(())
}

fn emit_lookbehind_body(
    emitter: &mut PatternEmitter,
    body: &Pcre2Node,
) -> Result<(), Box<EmitProblem>> {
    let Pcre2Operation::Alternation(branches) = &body.operation else {
        return emit_node(emitter, body);
    };
    let start = emitter.offset();
    for (index, branch) in branches.iter().enumerate() {
        if index != 0 {
            emitter.push("|", &body.provenance)?;
        }
        emit_node(emitter, branch)?;
    }
    emitter.record(start, emitter.offset(), &body.provenance);
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
    node: &Pcre2Node,
    negated: bool,
    members: &[Pcre2CharacterSetMember],
) -> Result<(), Box<EmitProblem>> {
    if members.iter().any(|member| {
        matches!(
            member,
            Pcre2CharacterSetMember::Builtin {
                domain: Pcre2CharacterDomain::Ascii | Pcre2CharacterDomain::CanonicalUnicodeWord,
                ..
            }
        )
    }) {
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
    node: &Pcre2Node,
    negated: bool,
    members: &[Pcre2CharacterSetMember],
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
        emitter.push("))(?s:.)", &node.provenance)?;
    } else if members.len() > 1 {
        emitter.push(")", &node.provenance)?;
    }
    Ok(())
}

fn emit_class_member(
    emitter: &mut PatternEmitter,
    node: &Pcre2Node,
    member: &Pcre2CharacterSetMember,
) -> Result<(), Box<EmitProblem>> {
    match member {
        Pcre2CharacterSetMember::Literal { value } => {
            emitter.push(&escape_class_character(*value), &node.provenance)
        }
        Pcre2CharacterSetMember::Range { start, end } => {
            emitter.push(&escape_class_character(*start), &node.provenance)?;
            emitter.push("-", &node.provenance)?;
            emitter.push(&escape_class_character(*end), &node.provenance)
        }
        Pcre2CharacterSetMember::Builtin {
            name,
            domain: Pcre2CharacterDomain::TargetNative | Pcre2CharacterDomain::Unicode,
            negated,
        } => emitter.push(builtin_escape(*name, *negated), &node.provenance),
        Pcre2CharacterSetMember::Builtin {
            domain: Pcre2CharacterDomain::Ascii,
            ..
        } => unreachable!("ASCII built-ins select atom-based set emission"),
        Pcre2CharacterSetMember::Builtin {
            domain: Pcre2CharacterDomain::CanonicalUnicodeWord,
            ..
        } => unreachable!("canonical Unicode word selects atom-based set emission"),
        Pcre2CharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => emit_unicode_property(emitter, node, property, value.as_deref(), *negated),
    }
}

fn emit_member_atom(
    emitter: &mut PatternEmitter,
    node: &Pcre2Node,
    member: &Pcre2CharacterSetMember,
) -> Result<(), Box<EmitProblem>> {
    match member {
        Pcre2CharacterSetMember::Literal { value } => {
            emitter.push("[", &node.provenance)?;
            emitter.push(&escape_class_character(*value), &node.provenance)?;
            emitter.push("]", &node.provenance)
        }
        Pcre2CharacterSetMember::Range { start, end } => {
            emitter.push("[", &node.provenance)?;
            emitter.push(&escape_class_character(*start), &node.provenance)?;
            emitter.push("-", &node.provenance)?;
            emitter.push(&escape_class_character(*end), &node.provenance)?;
            emitter.push("]", &node.provenance)
        }
        Pcre2CharacterSetMember::Builtin {
            name,
            domain: Pcre2CharacterDomain::TargetNative | Pcre2CharacterDomain::Unicode,
            negated,
        } => emitter.push(builtin_escape(*name, *negated), &node.provenance),
        Pcre2CharacterSetMember::Builtin {
            name,
            domain: Pcre2CharacterDomain::Ascii,
            negated,
        } => {
            emitter.push("(?-i:", &node.provenance)?;
            emitter.push(ascii_builtin_class(*name, *negated), &node.provenance)?;
            emitter.push(")", &node.provenance)
        }
        Pcre2CharacterSetMember::Builtin {
            name: Pcre2BuiltinClass::Word,
            domain: Pcre2CharacterDomain::CanonicalUnicodeWord,
            negated,
        } => emitter.push(
            if *negated {
                r"[^\p{L}\p{Mn}\p{N}\p{Pc}]"
            } else {
                r"[\p{L}\p{Mn}\p{N}\p{Pc}]"
            },
            &node.provenance,
        ),
        Pcre2CharacterSetMember::Builtin {
            domain: Pcre2CharacterDomain::CanonicalUnicodeWord,
            ..
        } => unreachable!("only Unicode word uses the canonical word domain"),
        Pcre2CharacterSetMember::UnicodeProperty {
            property,
            value,
            negated,
        } => emit_unicode_property(emitter, node, property, value.as_deref(), *negated),
    }
}

fn builtin_escape(name: Pcre2BuiltinClass, negated: bool) -> &'static str {
    match (name, negated) {
        (Pcre2BuiltinClass::Digit, false) => r"\d",
        (Pcre2BuiltinClass::Digit, true) => r"\D",
        (Pcre2BuiltinClass::Word, false) => r"\w",
        (Pcre2BuiltinClass::Word, true) => r"\W",
        (Pcre2BuiltinClass::Whitespace, false) => r"\s",
        (Pcre2BuiltinClass::Whitespace, true) => r"\S",
    }
}

fn ascii_builtin_class(name: Pcre2BuiltinClass, negated: bool) -> &'static str {
    match (name, negated) {
        (Pcre2BuiltinClass::Digit, false) => "[0-9]",
        (Pcre2BuiltinClass::Digit, true) => "[^0-9]",
        (Pcre2BuiltinClass::Word, false) => "[A-Za-z0-9_]",
        (Pcre2BuiltinClass::Word, true) => "[^A-Za-z0-9_]",
        (Pcre2BuiltinClass::Whitespace, false) => r"[\x{9}-\x{d}\x{20}]",
        (Pcre2BuiltinClass::Whitespace, true) => r"[^\x{9}-\x{d}\x{20}]",
    }
}

fn emit_unicode_property(
    emitter: &mut PatternEmitter,
    node: &Pcre2Node,
    property: &str,
    value: Option<&str>,
    negated: bool,
) -> Result<(), Box<EmitProblem>> {
    validate_unicode_identifier(property).map_err(|message| {
        problem(
            Pcre2SerializationErrorCode::InvalidUnicodeProperty,
            &node.provenance,
            format!("PCRE2 Unicode property {property:?} is invalid: {message}"),
        )
    })?;
    if let Some(value) = value {
        validate_unicode_identifier(value).map_err(|message| {
            problem(
                Pcre2SerializationErrorCode::InvalidUnicodeProperty,
                &node.provenance,
                format!("PCRE2 Unicode property value {value:?} is invalid: {message}"),
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

fn validate_capture_name(value: &str) -> Result<(), &'static str> {
    if value.len() > MAX_PCRE2_CAPTURE_NAME_CODE_UNITS {
        return Err("capture name exceeds 32 ASCII code units");
    }
    validate_ascii_identifier(value)
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
        '\\' | '^' | '$' | '.' | '|' | '?' | '*' | '+' | '(' | ')' | '[' | ']' | '{' | '}' => {
            format!(r"\{character}")
        }
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
        '\\' | '[' | ']' | '-' | '^' | ' ' | '#' => code_point_escape(character),
        value if value.is_control() || value.is_whitespace() => code_point_escape(value),
        value => value.to_string(),
    }
}

fn code_point_escape(character: char) -> String {
    let mut escaped = String::new();
    write!(&mut escaped, r"\x{{{:x}}}", u32::from(character))
        .expect("writing to String cannot fail");
    escaped
}

fn problem(
    code: Pcre2SerializationErrorCode,
    provenance: &Pcre2Provenance,
    message: impl Into<String>,
) -> Box<EmitProblem> {
    Box::new(EmitProblem {
        code,
        provenance: provenance.clone(),
        message: message.into(),
    })
}

fn failure(plan: &Pcre2LoweringPlan, problem: EmitProblem) -> Pcre2SerializationFailure {
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
            .expect("authored PCRE2 emission diagnostic code must be valid"),
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
    Pcre2SerializationFailure {
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
        assert_eq!(escape_pattern_character(' '), r"\x{20}");
        assert_eq!(escape_pattern_character('é'), "é");
        assert_eq!(escape_class_character('-'), r"\x{2d}");
        assert_eq!(escape_class_character('\n'), r"\n");
        assert_eq!(quantifier(0, None), "*");
        assert_eq!(quantifier(1, None), "+");
        assert_eq!(quantifier(0, Some(1)), "?");
        assert_eq!(quantifier(2, Some(2)), "{2}");
        assert_eq!(quantifier(2, None), "{2,}");
        assert_eq!(quantifier(2, Some(4)), "{2,4}");
    }
}
