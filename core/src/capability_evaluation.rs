//! Pure semantic-requirement extraction and target capability evaluation.
//!
//! Requirement extraction is target-neutral: it describes demanded semantics
//! using stable node identities and certified prerequisite facts. Target
//! profile comparison is added below this boundary by the evaluator.

use std::error::Error;
use std::fmt;

use crate::semantic::{
    AssertionPolarity, BuiltinClassName, CaseMatching, CharacterDomain, CharacterSetMember,
    LookaroundDirection, Node, PositionKind, RepetitionMode, SemanticProgram,
};
use crate::semantic_analysis::{
    semantic_program_identity, MaximumConsumption, SemanticFacts, SemanticNodeKind,
};
use crate::source::{CaptureId, ContractVersion, NodeId, SpecificationVersion};
use crate::structural_analysis::{LengthClassification, StructuralFacts};
use crate::target::CapabilityId;
use crate::validation::{Validate, ValidationCode};

const LOOKAHEAD: &str = "assertions.lookahead";
const FIXED_LOOKBEHIND: &str = "assertions.lookbehind.fixed_length";
const VARIABLE_LOOKBEHIND: &str = "assertions.lookbehind.variable_length";
const NAMED_CAPTURE: &str = "groups.named_capture";
const BACKREFERENCE: &str = "references.backreference";
const UNICODE_PROPERTY: &str = "character_properties.unicode";
const UNICODE_CHARACTER_CLASS: &str = "character_classes.unicode";
const ATOMIC_GROUP: &str = "groups.atomic";
const POSSESSIVE_REPETITION: &str = "repetition.possessive";
const LAZY_REPETITION: &str = "repetition.lazy";
const INPUT_START: &str = "anchors.input_start";
const INPUT_END: &str = "anchors.input_end";
const LINE_START: &str = "anchors.line_start";
const LINE_END: &str = "anchors.line_end";
const WORD_BOUNDARY: &str = "boundaries.word";
const END_BEFORE_FINAL_LINE_TERMINATOR: &str = "anchors.end_before_final_line_terminator";
const CASE_INSENSITIVE: &str = "matching.case_insensitive";

/// Stable error categories for requirement extraction and capability evaluation.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum CapabilityEvaluationErrorCode {
    InvalidSemanticProgram,
    FactVersionMismatch,
    FactProgramMismatch,
    MissingFoundationalFact,
    UnexpectedFoundationalFact,
    MissingStructuralFact,
    UnexpectedStructuralFact,
    FactInvariant,
}

/// One structured stage error.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CapabilityEvaluationError {
    pub code: CapabilityEvaluationErrorCode,
    pub path: String,
    pub message: String,
}

impl CapabilityEvaluationError {
    fn new(
        code: CapabilityEvaluationErrorCode,
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

/// Deterministically ordered failures from the pure capability stage.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CapabilityEvaluationErrors {
    pub errors: Vec<CapabilityEvaluationError>,
}

impl CapabilityEvaluationErrors {
    fn single(error: CapabilityEvaluationError) -> Self {
        Self {
            errors: vec![error],
        }
    }
}

impl fmt::Display for CapabilityEvaluationErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "capability evaluation failed with {} error(s)",
            self.errors.len()
        )
    }
}

impl Error for CapabilityEvaluationErrors {}

/// Target-neutral assertion polarity retained as typed requirement evidence.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RequirementPolarity {
    Positive,
    Negative,
}

impl From<AssertionPolarity> for RequirementPolarity {
    fn from(value: AssertionPolarity) -> Self {
        match value {
            AssertionPolarity::Positive => Self::Positive,
            AssertionPolarity::Negative => Self::Negative,
        }
    }
}

/// Certified semantic length evidence for a lookbehind body.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum LookbehindLength {
    Fixed { length: u64 },
    FiniteVariable { minimum: u64, maximum: u64 },
    Unbounded { minimum: u64 },
    Indeterminate { minimum: u64 },
}

/// Ratified position semantics without target spelling.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum PositionRequirement {
    InputStart,
    InputEnd,
    LineStart,
    LineEnd,
    WordBoundary,
    NotWordBoundary,
    EndBeforeFinalLineTerminator,
}

/// One typed semantic capability demand.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RequirementKind {
    Lookahead {
        polarity: RequirementPolarity,
    },
    Lookbehind {
        body_node_id: NodeId,
        polarity: RequirementPolarity,
        length: LookbehindLength,
    },
    NamedCapture {
        capture_id: CaptureId,
    },
    Backreference {
        capture_id: CaptureId,
        definition_node_id: NodeId,
    },
    UnicodeProperty {
        property: String,
        value: Option<String>,
        negated: bool,
    },
    UnicodeCharacterClass {
        name: BuiltinClassName,
        negated: bool,
    },
    Atomic,
    PossessiveRepetition,
    LazyRepetition,
    Position {
        position: PositionRequirement,
    },
    CaseInsensitive,
}

/// One target-neutral requirement occurrence keyed by stable semantic identity.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct SemanticRequirement {
    pub node_id: NodeId,
    pub capability_id: CapabilityId,
    pub kind: RequirementKind,
}

/// Complete, canonical requirement set for one semantic program.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SemanticRequirements {
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub requirements: Vec<SemanticRequirement>,
}

impl SemanticRequirements {
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.requirements.is_empty()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.requirements.len()
    }

    pub fn iter(&self) -> impl ExactSizeIterator<Item = &SemanticRequirement> {
        self.requirements.iter()
    }
}

/// Extract target-neutral semantic requirements from exact certified inputs.
///
/// The function requires canonical Semantic IR and the foundational and
/// structural fact stores produced for those exact immutable bytes. It never
/// reads source text and never invokes prerequisite analyses.
pub fn extract_requirements(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) -> Result<SemanticRequirements, CapabilityEvaluationErrors> {
    validate_prerequisites(input, foundational, structural)?;

    let mut requirements = Vec::new();
    if input.case_matching == CaseMatching::Insensitive {
        requirements.push(requirement(
            input.root.node_id().clone(),
            CASE_INSENSITIVE,
            RequirementKind::CaseInsensitive,
        ));
    }

    let mut pending = vec![&input.root];
    while let Some(node) = pending.pop() {
        extract_node_requirements(node, foundational, structural, &mut requirements)?;
        push_children(node, &mut pending);
    }

    requirements.sort();
    requirements.dedup();
    Ok(SemanticRequirements {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        requirements,
    })
}

fn extract_node_requirements(
    node: &Node,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    requirements: &mut Vec<SemanticRequirement>,
) -> Result<(), CapabilityEvaluationErrors> {
    match node {
        Node::CharacterSet {
            node_id, members, ..
        } => {
            for member in members {
                match member {
                    CharacterSetMember::Builtin {
                        name,
                        domain: CharacterDomain::Unicode,
                        negated,
                    } => requirements.push(requirement(
                        node_id.clone(),
                        UNICODE_CHARACTER_CLASS,
                        RequirementKind::UnicodeCharacterClass {
                            name: *name,
                            negated: *negated,
                        },
                    )),
                    CharacterSetMember::UnicodeProperty {
                        property,
                        value,
                        negated,
                    } => requirements.push(requirement(
                        node_id.clone(),
                        UNICODE_PROPERTY,
                        RequirementKind::UnicodeProperty {
                            property: property.clone(),
                            value: value.clone(),
                            negated: *negated,
                        },
                    )),
                    CharacterSetMember::Literal { .. }
                    | CharacterSetMember::Range { .. }
                    | CharacterSetMember::Builtin {
                        domain: CharacterDomain::Ascii,
                        ..
                    } => {}
                }
            }
        }
        Node::Repeat { node_id, mode, .. } => match mode {
            RepetitionMode::Greedy => {}
            RepetitionMode::Lazy => requirements.push(requirement(
                node_id.clone(),
                LAZY_REPETITION,
                RequirementKind::LazyRepetition,
            )),
            RepetitionMode::Possessive => requirements.push(requirement(
                node_id.clone(),
                POSSESSIVE_REPETITION,
                RequirementKind::PossessiveRepetition,
            )),
        },
        Node::Position {
            node_id, position, ..
        } => {
            let (capability, position) = position_requirement(*position);
            requirements.push(requirement(
                node_id.clone(),
                capability,
                RequirementKind::Position { position },
            ));
        }
        Node::Capture {
            node_id,
            capture_id,
            name,
            ..
        } if name.is_some() => {
            let definition = foundational
                .capture_definition(capture_id)
                .ok_or_else(|| missing_foundational(node_id, "named capture resolution"))?;
            if definition.definition_node_id != *node_id
                || definition.capture_id != *capture_id
                || definition.name != *name
            {
                return Err(fact_invariant(
                    node_id,
                    "certified capture definition does not match Semantic IR",
                ));
            }
            requirements.push(requirement(
                node_id.clone(),
                NAMED_CAPTURE,
                RequirementKind::NamedCapture {
                    capture_id: capture_id.clone(),
                },
            ));
        }
        Node::Backreference {
            node_id,
            capture_id,
            ..
        } => {
            let resolution = foundational
                .backreference(node_id)
                .ok_or_else(|| missing_foundational(node_id, "backreference resolution"))?;
            if resolution.backreference_node_id != *node_id || resolution.capture_id != *capture_id
            {
                return Err(fact_invariant(
                    node_id,
                    "certified backreference resolution does not match Semantic IR",
                ));
            }
            requirements.push(requirement(
                node_id.clone(),
                BACKREFERENCE,
                RequirementKind::Backreference {
                    capture_id: capture_id.clone(),
                    definition_node_id: resolution.definition_node_id.clone(),
                },
            ));
        }
        Node::Lookaround {
            node_id,
            direction,
            polarity,
            body,
            ..
        } => match direction {
            LookaroundDirection::Ahead => requirements.push(requirement(
                node_id.clone(),
                LOOKAHEAD,
                RequirementKind::Lookahead {
                    polarity: (*polarity).into(),
                },
            )),
            LookaroundDirection::Behind => {
                let length = lookbehind_length(body.node_id(), foundational, structural)?;
                let capability = match length {
                    LookbehindLength::Fixed { .. } => FIXED_LOOKBEHIND,
                    LookbehindLength::FiniteVariable { .. }
                    | LookbehindLength::Unbounded { .. }
                    | LookbehindLength::Indeterminate { .. } => VARIABLE_LOOKBEHIND,
                };
                requirements.push(requirement(
                    node_id.clone(),
                    capability,
                    RequirementKind::Lookbehind {
                        body_node_id: body.node_id().clone(),
                        polarity: (*polarity).into(),
                        length,
                    },
                ));
            }
        },
        Node::Atomic { node_id, .. } => requirements.push(requirement(
            node_id.clone(),
            ATOMIC_GROUP,
            RequirementKind::Atomic,
        )),
        Node::Empty { .. }
        | Node::Sequence { .. }
        | Node::Alternation { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::Capture { .. } => {}
    }
    Ok(())
}

fn lookbehind_length(
    body_node_id: &NodeId,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) -> Result<LookbehindLength, CapabilityEvaluationErrors> {
    let semantic = foundational
        .get(body_node_id)
        .ok_or_else(|| missing_foundational(body_node_id, "lookbehind length"))?;
    let structure = structural
        .get(body_node_id)
        .ok_or_else(|| missing_structural(body_node_id, "lookbehind length"))?;

    match structure.length {
        LengthClassification::Fixed(length) => {
            if semantic.minimum_consumption != length
                || semantic.maximum_consumption != MaximumConsumption::Finite(length)
            {
                return Err(fact_invariant(
                    body_node_id,
                    "fixed structural length contradicts foundational bounds",
                ));
            }
            Ok(LookbehindLength::Fixed { length })
        }
        LengthClassification::FiniteVariable => {
            let MaximumConsumption::Finite(maximum) = semantic.maximum_consumption else {
                return Err(fact_invariant(
                    body_node_id,
                    "finite-variable structural length lacks a finite foundational maximum",
                ));
            };
            if semantic.minimum_consumption >= maximum {
                return Err(fact_invariant(
                    body_node_id,
                    "finite-variable structural length requires distinct bounds",
                ));
            }
            Ok(LookbehindLength::FiniteVariable {
                minimum: semantic.minimum_consumption,
                maximum,
            })
        }
        LengthClassification::Unbounded => {
            if semantic.maximum_consumption != MaximumConsumption::Unbounded {
                return Err(fact_invariant(
                    body_node_id,
                    "unbounded structural length contradicts foundational bounds",
                ));
            }
            Ok(LookbehindLength::Unbounded {
                minimum: semantic.minimum_consumption,
            })
        }
        LengthClassification::Indeterminate => {
            if semantic.maximum_consumption != MaximumConsumption::Unbounded {
                return Err(fact_invariant(
                    body_node_id,
                    "indeterminate structural length contradicts foundational bounds",
                ));
            }
            Ok(LookbehindLength::Indeterminate {
                minimum: semantic.minimum_consumption,
            })
        }
    }
}

fn validate_prerequisites(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) -> Result<(), CapabilityEvaluationErrors> {
    if let Err(found) = input.validate() {
        let errors = found
            .errors
            .into_iter()
            .map(|error| {
                CapabilityEvaluationError::new(
                    CapabilityEvaluationErrorCode::InvalidSemanticProgram,
                    error.path,
                    match error.code {
                        ValidationCode::NonCanonicalOrder
                        | ValidationCode::NonCanonicalStructure => {
                            format!("normalized Semantic IR required: {}", error.message)
                        }
                        _ => error.message,
                    },
                )
            })
            .collect();
        return Err(CapabilityEvaluationErrors { errors });
    }

    if input.contract_version != foundational.contract_version
        || input.specification_version != foundational.specification_version
        || input.contract_version != structural.contract_version
        || input.specification_version != structural.specification_version
    {
        return Err(CapabilityEvaluationErrors::single(
            CapabilityEvaluationError::new(
                CapabilityEvaluationErrorCode::FactVersionMismatch,
                "$",
                "prerequisite fact versions do not match the semantic program",
            ),
        ));
    }

    let identity = semantic_program_identity(input).map_err(|error| {
        CapabilityEvaluationErrors::single(CapabilityEvaluationError::new(
            CapabilityEvaluationErrorCode::FactInvariant,
            "$",
            format!("semantic program identity could not be derived: {error}"),
        ))
    })?;
    if foundational.program_identity() != identity || structural.program_identity() != identity {
        return Err(CapabilityEvaluationErrors::single(
            CapabilityEvaluationError::new(
                CapabilityEvaluationErrorCode::FactProgramMismatch,
                "$",
                "prerequisite facts were not produced for this exact semantic program",
            ),
        ));
    }

    let node_ids = input.node_ids();
    for node_id in &node_ids {
        if foundational.get(node_id).is_none() {
            return Err(missing_foundational(node_id, "requirement extraction"));
        }
        if structural.get(node_id).is_none() {
            return Err(missing_structural(node_id, "requirement extraction"));
        }
    }
    for (node_id, _) in foundational.iter() {
        if !node_ids.contains(node_id) {
            return Err(CapabilityEvaluationErrors::single(
                CapabilityEvaluationError::new(
                    CapabilityEvaluationErrorCode::UnexpectedFoundationalFact,
                    "$.root",
                    format!("foundational facts contain unreachable node {node_id:?}"),
                ),
            ));
        }
    }
    for (node_id, _) in structural.iter() {
        if !node_ids.contains(node_id) {
            return Err(CapabilityEvaluationErrors::single(
                CapabilityEvaluationError::new(
                    CapabilityEvaluationErrorCode::UnexpectedStructuralFact,
                    "$.root",
                    format!("structural facts contain unreachable node {node_id:?}"),
                ),
            ));
        }
    }

    let mut pending = vec![&input.root];
    while let Some(node) = pending.pop() {
        let facts = foundational
            .get(node.node_id())
            .ok_or_else(|| missing_foundational(node.node_id(), "node kind validation"))?;
        if facts.kind != semantic_node_kind(node) {
            return Err(fact_invariant(
                node.node_id(),
                "foundational node kind does not match Semantic IR",
            ));
        }
        push_children(node, &mut pending);
    }
    Ok(())
}

fn semantic_node_kind(node: &Node) -> SemanticNodeKind {
    match node {
        Node::Empty { .. } => SemanticNodeKind::Empty,
        Node::Sequence { .. } => SemanticNodeKind::Sequence,
        Node::Alternation { .. } => SemanticNodeKind::Alternation,
        Node::Literal { .. } => SemanticNodeKind::Literal,
        Node::Wildcard { .. } => SemanticNodeKind::Wildcard,
        Node::CharacterSet { .. } => SemanticNodeKind::CharacterSet,
        Node::Repeat { .. } => SemanticNodeKind::Repeat,
        Node::Position { .. } => SemanticNodeKind::Position,
        Node::Capture { .. } => SemanticNodeKind::Capture,
        Node::Backreference { .. } => SemanticNodeKind::Backreference,
        Node::Lookaround { .. } => SemanticNodeKind::Lookaround,
        Node::Atomic { .. } => SemanticNodeKind::Atomic,
    }
}

fn position_requirement(position: PositionKind) -> (&'static str, PositionRequirement) {
    match position {
        PositionKind::InputStart => (INPUT_START, PositionRequirement::InputStart),
        PositionKind::InputEnd => (INPUT_END, PositionRequirement::InputEnd),
        PositionKind::LineStart => (LINE_START, PositionRequirement::LineStart),
        PositionKind::LineEnd => (LINE_END, PositionRequirement::LineEnd),
        PositionKind::WordBoundary => (WORD_BOUNDARY, PositionRequirement::WordBoundary),
        PositionKind::NotWordBoundary => (WORD_BOUNDARY, PositionRequirement::NotWordBoundary),
        PositionKind::EndBeforeFinalLineTerminator => (
            END_BEFORE_FINAL_LINE_TERMINATOR,
            PositionRequirement::EndBeforeFinalLineTerminator,
        ),
    }
}

fn requirement(
    node_id: NodeId,
    capability: &'static str,
    kind: RequirementKind,
) -> SemanticRequirement {
    SemanticRequirement {
        node_id,
        capability_id: CapabilityId::try_from(capability)
            .expect("canonical requirement capability identifier must be valid"),
        kind,
    }
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

fn missing_foundational(node_id: &NodeId, purpose: &str) -> CapabilityEvaluationErrors {
    CapabilityEvaluationErrors::single(CapabilityEvaluationError::new(
        CapabilityEvaluationErrorCode::MissingFoundationalFact,
        "$.root",
        format!("foundational facts omit {node_id:?} required for {purpose}"),
    ))
}

fn missing_structural(node_id: &NodeId, purpose: &str) -> CapabilityEvaluationErrors {
    CapabilityEvaluationErrors::single(CapabilityEvaluationError::new(
        CapabilityEvaluationErrorCode::MissingStructuralFact,
        "$.root",
        format!("structural facts omit {node_id:?} required for {purpose}"),
    ))
}

fn fact_invariant(node_id: &NodeId, message: &str) -> CapabilityEvaluationErrors {
    CapabilityEvaluationErrors::single(CapabilityEvaluationError::new(
        CapabilityEvaluationErrorCode::FactInvariant,
        "$.root",
        format!("{message}: {node_id:?}"),
    ))
}
