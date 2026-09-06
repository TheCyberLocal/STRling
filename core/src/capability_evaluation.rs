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
use crate::source::{CaptureId, ContractVersion, NodeId, Sha256Digest, SpecificationVersion};
use crate::structural_analysis::{LengthClassification, StructuralFacts};
use crate::target::{
    Capability, CapabilityAvailability, CapabilityConstraint, CapabilityId, ConstraintId,
    ConstraintOperator, ConstraintScalar, ConstraintUnit, ConstraintValue, EngineIdentity,
    ProfileOption, RuntimeIdentity, SemanticAlgorithm, SemanticFactReference, SemanticSet,
    TargetLimit, TargetProfile, TargetProfileReference, TargetProfileSet,
};
use crate::validation::{canonical_sha256, Validate, ValidationCode};

const LOOKAHEAD: &str = "assertions.lookahead";
const FIXED_LOOKBEHIND: &str = "assertions.lookbehind.fixed_length";
const VARIABLE_LOOKBEHIND: &str = "assertions.lookbehind.variable_length";
const NAMED_CAPTURE: &str = "groups.named_capture";
const BACKREFERENCE: &str = "references.backreference";
const UNICODE_PROPERTY: &str = "character_properties.unicode";
const UNICODE_CHARACTER_CLASS: &str = "character_classes.unicode";
const UNICODE_SCALAR_SEMANTICS: &str = "character_semantics.unicode_scalar";
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

/// Maximum target requirements extracted for one canonical request.
pub const MAX_CAPABILITY_REQUIREMENTS: usize = 4_096;

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
    InvalidTargetProfile,
    IncompatibleTargetProfile,
    TargetProfileResolution,
    RequirementLimitExceeded,
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
    FixedAlternatives { minimum: u64, maximum: u64 },
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
        name: String,
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
    UnicodeScalarLiteral {
        scalars: Vec<char>,
    },
    UnicodeScalarSetMember {
        start: char,
        end: char,
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

/// A scalar or conservative non-finite fact available to typed constraints.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ConstraintFactValue {
    Scalar(ConstraintScalar),
    Unbounded,
    Indeterminate,
}

/// Provenance for a fact without source text or target syntax.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ConstraintFactSource {
    SemanticRequirement { node_id: NodeId },
    StructuralLength { body_node_id: NodeId },
}

/// One typed fact offered to a profile constraint with exact units.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RequirementConstraintFact {
    pub constraint_id: ConstraintId,
    pub value: ConstraintFactValue,
    pub unit: Option<ConstraintUnit>,
    pub source: ConstraintFactSource,
}

/// Factual support result, deliberately distinct from portability status.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum CapabilityDisposition {
    Supported,
    Unsupported,
    ConstraintViolation,
    Unknown,
}

/// Result of evaluating one certified profile constraint.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum ConstraintDisposition {
    Satisfied,
    Violated,
    Unknown,
}

/// Exact evidence used for a constraint result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ConstraintEvidence {
    RequirementFact(RequirementConstraintFact),
    ProfileOption(ProfileOption),
    MissingRequirementFact { constraint_id: ConstraintId },
}

/// One typed constraint comparison.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ConstraintEvaluation {
    pub constraint: CapabilityConstraint,
    pub evidence: ConstraintEvidence,
    pub disposition: ConstraintDisposition,
}

/// One governed semantic fact resolved from a capability reference.
///
/// Keeping the resolved value in the evaluation result makes semantic support
/// auditable without inferring behavior from a target or engine name.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ResolvedSemanticFact {
    SemanticSet(SemanticSet),
    SemanticAlgorithm(SemanticAlgorithm),
    TargetLimit(TargetLimit),
}

/// One requirement-to-profile factual result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CapabilityResult {
    pub node_id: NodeId,
    pub requirement: SemanticRequirement,
    pub target_profile: TargetProfileReference,
    pub target_engine: EngineIdentity,
    pub target_runtime: Option<RuntimeIdentity>,
    pub evaluated_capability: CapabilityId,
    pub profile_capability: Option<Capability>,
    pub semantic_facts: Vec<ResolvedSemanticFact>,
    pub constraint_facts: Vec<RequirementConstraintFact>,
    pub constraint_evaluations: Vec<ConstraintEvaluation>,
    pub disposition: CapabilityDisposition,
}

/// Complete deterministic comparison for one program and exact target profile.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CapabilityEvaluation {
    pub contract_version: ContractVersion,
    pub semantic_program: Sha256Digest,
    pub specification_version: SpecificationVersion,
    pub target_profile: TargetProfileReference,
    pub target_engine: EngineIdentity,
    pub target_runtime: Option<RuntimeIdentity>,
    pub requirements: SemanticRequirements,
    pub results: Vec<CapabilityResult>,
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
        enforce_requirement_limit(requirements.len())?;
    }

    let mut pending = vec![&input.root];
    while let Some(node) = pending.pop() {
        extract_node_requirements(node, foundational, structural, &mut requirements)?;
        push_children(node, &mut pending);
        enforce_requirement_limit(requirements.len())?;
    }

    requirements.sort();
    requirements.dedup();
    Ok(SemanticRequirements {
        contract_version: input.contract_version,
        specification_version: input.specification_version.clone(),
        requirements,
    })
}

fn enforce_requirement_limit(count: usize) -> Result<(), CapabilityEvaluationErrors> {
    if count > MAX_CAPABILITY_REQUIREMENTS {
        return Err(CapabilityEvaluationErrors::single(
            CapabilityEvaluationError::new(
                CapabilityEvaluationErrorCode::RequirementLimitExceeded,
                "$.requirements",
                format!(
                    "capability requirement count exceeds deterministic limit {MAX_CAPABILITY_REQUIREMENTS}"
                ),
            ),
        ));
    }
    Ok(())
}
/// Evaluate extracted semantic requirements against one supplied immutable
/// target profile.
pub fn evaluate_capabilities(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    target: &TargetProfile,
) -> Result<CapabilityEvaluation, CapabilityEvaluationErrors> {
    let semantic_program = semantic_program_fingerprint(input)?;
    let requirements = extract_requirements(input, foundational, structural)?;
    validate_target_profile(input, target)?;
    let target_reference = target.reference().map_err(|errors| {
        map_profile_errors(CapabilityEvaluationErrorCode::InvalidTargetProfile, errors)
    })?;

    let results = requirements
        .iter()
        .map(|requirement| evaluate_requirement(requirement, target, &target_reference))
        .collect();

    Ok(CapabilityEvaluation {
        contract_version: input.contract_version,
        semantic_program,
        specification_version: input.specification_version.clone(),
        target_profile: target_reference,
        target_engine: target.engine.clone(),
        target_runtime: target.runtime.clone(),
        requirements,
        results,
    })
}

/// Resolve an immutable target reference from a caller-supplied profile set,
/// including exact revision and canonical fingerprint verification.
pub fn evaluate_capabilities_for_reference(
    input: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    reference: &TargetProfileReference,
    profiles: &TargetProfileSet,
) -> Result<CapabilityEvaluation, CapabilityEvaluationErrors> {
    let target = profiles.resolve(reference).map_err(|errors| {
        map_profile_errors(
            CapabilityEvaluationErrorCode::TargetProfileResolution,
            errors,
        )
    })?;
    evaluate_capabilities(input, foundational, structural, target)
}

/// Resolve the governed semantic facts attached to one capability.
///
/// The profile is validated first, so a missing required fact, dangling
/// reference, or malformed definition fails closed instead of returning a
/// partial description. An unlisted capability remains an explicit unknown.
pub fn resolve_capability_semantic_facts(
    target: &TargetProfile,
    capability_id: &CapabilityId,
) -> Result<Option<Vec<ResolvedSemanticFact>>, CapabilityEvaluationErrors> {
    target.validate().map_err(|errors| {
        map_profile_errors(CapabilityEvaluationErrorCode::InvalidTargetProfile, errors)
    })?;
    Ok(lookup_capability(target, capability_id)
        .map(|capability| resolve_semantic_facts(capability, target)))
}

fn evaluate_requirement(
    requirement: &SemanticRequirement,
    target: &TargetProfile,
    target_reference: &TargetProfileReference,
) -> CapabilityResult {
    let constraint_facts = requirement_constraint_facts(requirement);
    let profile_capability = lookup_capability(target, &requirement.capability_id).cloned();
    let semantic_facts = profile_capability
        .as_ref()
        .map(|capability| resolve_semantic_facts(capability, target))
        .unwrap_or_default();
    let (constraint_evaluations, disposition) = match &profile_capability {
        None => (Vec::new(), CapabilityDisposition::Unknown),
        Some(capability) => match capability.availability {
            CapabilityAvailability::Available => (Vec::new(), CapabilityDisposition::Supported),
            CapabilityAvailability::Unavailable => (Vec::new(), CapabilityDisposition::Unsupported),
            CapabilityAvailability::Constrained => {
                let evaluations: Vec<_> = capability
                    .constraints
                    .iter()
                    .map(|constraint| evaluate_constraint(constraint, &constraint_facts, target))
                    .collect();
                let disposition = if evaluations
                    .iter()
                    .any(|result| result.disposition == ConstraintDisposition::Violated)
                {
                    CapabilityDisposition::ConstraintViolation
                } else if evaluations
                    .iter()
                    .any(|result| result.disposition == ConstraintDisposition::Unknown)
                {
                    CapabilityDisposition::Unknown
                } else {
                    CapabilityDisposition::Supported
                };
                (evaluations, disposition)
            }
        },
    };

    CapabilityResult {
        node_id: requirement.node_id.clone(),
        requirement: requirement.clone(),
        target_profile: target_reference.clone(),
        target_engine: target.engine.clone(),
        target_runtime: target.runtime.clone(),
        evaluated_capability: requirement.capability_id.clone(),
        profile_capability,
        semantic_facts,
        constraint_facts,
        constraint_evaluations,
        disposition,
    }
}

fn resolve_semantic_facts(
    capability: &Capability,
    target: &TargetProfile,
) -> Vec<ResolvedSemanticFact> {
    capability
        .semantic_fact_refs
        .iter()
        .filter_map(|reference| match reference {
            SemanticFactReference::SemanticSet { fact_id, .. } => target
                .semantic_sets
                .binary_search_by(|fact| fact.set_id.cmp(fact_id))
                .ok()
                .map(|index| {
                    ResolvedSemanticFact::SemanticSet(target.semantic_sets[index].clone())
                }),
            SemanticFactReference::SemanticAlgorithm { fact_id, .. } => target
                .semantic_algorithms
                .binary_search_by(|fact| fact.algorithm_id.cmp(fact_id))
                .ok()
                .map(|index| {
                    ResolvedSemanticFact::SemanticAlgorithm(
                        target.semantic_algorithms[index].clone(),
                    )
                }),
            SemanticFactReference::TargetLimit { fact_id, .. } => target
                .target_limits
                .binary_search_by(|fact| fact.limit_id.cmp(fact_id))
                .ok()
                .map(|index| {
                    ResolvedSemanticFact::TargetLimit(target.target_limits[index].clone())
                }),
        })
        .collect()
}

fn lookup_capability<'a>(
    target: &'a TargetProfile,
    capability_id: &CapabilityId,
) -> Option<&'a Capability> {
    target
        .capabilities
        .binary_search_by(|candidate| candidate.capability_id.cmp(capability_id))
        .ok()
        .map(|index| &target.capabilities[index])
}

fn evaluate_constraint(
    constraint: &CapabilityConstraint,
    facts: &[RequirementConstraintFact],
    target: &TargetProfile,
) -> ConstraintEvaluation {
    if constraint.operator == ConstraintOperator::RequiresOption {
        return evaluate_required_option(constraint, target);
    }

    let Some(fact) = facts
        .iter()
        .find(|fact| fact.constraint_id == constraint.constraint_id)
        .cloned()
    else {
        return ConstraintEvaluation {
            constraint: constraint.clone(),
            evidence: ConstraintEvidence::MissingRequirementFact {
                constraint_id: constraint.constraint_id.clone(),
            },
            disposition: ConstraintDisposition::Unknown,
        };
    };

    let disposition = if units_are_equal(constraint.unit.as_ref(), fact.unit.as_ref()) {
        compare_constraint(constraint.operator, &constraint.value, &fact.value)
    } else if constraint.unit.is_some() && fact.unit.is_some() {
        ConstraintDisposition::Violated
    } else {
        ConstraintDisposition::Unknown
    };
    ConstraintEvaluation {
        constraint: constraint.clone(),
        evidence: ConstraintEvidence::RequirementFact(fact),
        disposition,
    }
}

fn evaluate_required_option(
    constraint: &CapabilityConstraint,
    target: &TargetProfile,
) -> ConstraintEvaluation {
    let option = match &constraint.value {
        ConstraintValue::Scalar(ConstraintScalar::String(option_id)) => target
            .options
            .binary_search_by(|candidate| candidate.option_id.as_str().cmp(option_id))
            .ok()
            .map(|index| target.options[index].clone()),
        ConstraintValue::Scalar(ConstraintScalar::Number(_))
        | ConstraintValue::Scalar(ConstraintScalar::Boolean(_))
        | ConstraintValue::OneOf(_) => None,
    };

    match option {
        Some(option) => ConstraintEvaluation {
            constraint: constraint.clone(),
            evidence: ConstraintEvidence::ProfileOption(option),
            disposition: ConstraintDisposition::Satisfied,
        },
        None => ConstraintEvaluation {
            constraint: constraint.clone(),
            evidence: ConstraintEvidence::MissingRequirementFact {
                constraint_id: constraint.constraint_id.clone(),
            },
            disposition: ConstraintDisposition::Unknown,
        },
    }
}

fn compare_constraint(
    operator: ConstraintOperator,
    expected: &ConstraintValue,
    actual: &ConstraintFactValue,
) -> ConstraintDisposition {
    match (operator, expected, actual) {
        (
            ConstraintOperator::Equals,
            ConstraintValue::Scalar(expected),
            ConstraintFactValue::Scalar(actual),
        ) => compare_equal_scalars(actual, expected),
        (
            ConstraintOperator::OneOf,
            ConstraintValue::OneOf(expected),
            ConstraintFactValue::Scalar(actual),
        ) => compare_one_of(actual, expected),
        (
            ConstraintOperator::AtMost,
            ConstraintValue::Scalar(ConstraintScalar::Number(expected)),
            ConstraintFactValue::Scalar(ConstraintScalar::Number(actual)),
        ) => compare_integer_numbers(actual, expected).map_or(
            ConstraintDisposition::Unknown,
            |ordering| {
                if ordering.is_le() {
                    ConstraintDisposition::Satisfied
                } else {
                    ConstraintDisposition::Violated
                }
            },
        ),
        (
            ConstraintOperator::AtLeast,
            ConstraintValue::Scalar(ConstraintScalar::Number(expected)),
            ConstraintFactValue::Scalar(ConstraintScalar::Number(actual)),
        ) => compare_integer_numbers(actual, expected).map_or(
            ConstraintDisposition::Unknown,
            |ordering| {
                if ordering.is_ge() {
                    ConstraintDisposition::Satisfied
                } else {
                    ConstraintDisposition::Violated
                }
            },
        ),
        (
            ConstraintOperator::AtMost,
            ConstraintValue::Scalar(ConstraintScalar::Number(_)),
            ConstraintFactValue::Unbounded,
        ) => ConstraintDisposition::Violated,
        (
            ConstraintOperator::AtLeast,
            ConstraintValue::Scalar(ConstraintScalar::Number(_)),
            ConstraintFactValue::Unbounded,
        ) => ConstraintDisposition::Satisfied,
        (_, _, ConstraintFactValue::Indeterminate)
        | (_, _, ConstraintFactValue::Unbounded)
        | (ConstraintOperator::RequiresOption, _, _)
        | (_, ConstraintValue::OneOf(_), _)
        | (_, ConstraintValue::Scalar(_), _) => ConstraintDisposition::Unknown,
    }
}

fn compare_equal_scalars(
    actual: &ConstraintScalar,
    expected: &ConstraintScalar,
) -> ConstraintDisposition {
    match (actual, expected) {
        (ConstraintScalar::String(actual), ConstraintScalar::String(expected)) => {
            bool_disposition(actual == expected)
        }
        (ConstraintScalar::Number(actual), ConstraintScalar::Number(expected)) => {
            compare_integer_numbers(actual, expected)
                .map_or(ConstraintDisposition::Unknown, |ordering| {
                    bool_disposition(ordering.is_eq())
                })
        }
        (ConstraintScalar::Boolean(actual), ConstraintScalar::Boolean(expected)) => {
            bool_disposition(actual == expected)
        }
        (ConstraintScalar::String(_), _)
        | (ConstraintScalar::Number(_), _)
        | (ConstraintScalar::Boolean(_), _) => ConstraintDisposition::Unknown,
    }
}

fn compare_one_of(
    actual: &ConstraintScalar,
    expected: &[ConstraintScalar],
) -> ConstraintDisposition {
    let comparable: Vec<_> = expected
        .iter()
        .filter(|candidate| same_scalar_type(actual, candidate))
        .collect();
    if comparable.is_empty() {
        ConstraintDisposition::Unknown
    } else {
        bool_disposition(comparable.into_iter().any(|candidate| {
            compare_equal_scalars(actual, candidate) == ConstraintDisposition::Satisfied
        }))
    }
}

fn same_scalar_type(left: &ConstraintScalar, right: &ConstraintScalar) -> bool {
    matches!(
        (left, right),
        (ConstraintScalar::String(_), ConstraintScalar::String(_))
            | (ConstraintScalar::Number(_), ConstraintScalar::Number(_))
            | (ConstraintScalar::Boolean(_), ConstraintScalar::Boolean(_))
    )
}

fn compare_integer_numbers(
    left: &serde_json::Number,
    right: &serde_json::Number,
) -> Option<std::cmp::Ordering> {
    match (left.as_i64(), right.as_i64()) {
        (Some(left), Some(right)) => Some(left.cmp(&right)),
        _ => match (left.as_u64(), right.as_u64()) {
            (Some(left), Some(right)) => Some(left.cmp(&right)),
            _ => None,
        },
    }
}

fn bool_disposition(value: bool) -> ConstraintDisposition {
    if value {
        ConstraintDisposition::Satisfied
    } else {
        ConstraintDisposition::Violated
    }
}

fn units_are_equal(left: Option<&ConstraintUnit>, right: Option<&ConstraintUnit>) -> bool {
    match (left, right) {
        (None, None) => true,
        (Some(left), Some(right)) => left == right,
        (None, Some(_)) | (Some(_), None) => false,
    }
}

fn requirement_constraint_facts(
    requirement: &SemanticRequirement,
) -> Vec<RequirementConstraintFact> {
    let mut facts = Vec::new();
    let semantic_source = ConstraintFactSource::SemanticRequirement {
        node_id: requirement.node_id.clone(),
    };
    match &requirement.kind {
        RequirementKind::Lookahead { polarity } => facts.push(scalar_fact(
            "polarity",
            ConstraintScalar::String(polarity_name(*polarity).to_owned()),
            None,
            semantic_source,
        )),
        RequirementKind::Lookbehind {
            body_node_id,
            polarity,
            length,
        } => {
            facts.push(scalar_fact(
                "polarity",
                ConstraintScalar::String(polarity_name(*polarity).to_owned()),
                None,
                semantic_source,
            ));
            let source = ConstraintFactSource::StructuralLength {
                body_node_id: body_node_id.clone(),
            };
            match length {
                LookbehindLength::Fixed { length } => {
                    facts.push(scalar_fact(
                        "common_fixed_width",
                        ConstraintScalar::Boolean(true),
                        None,
                        source.clone(),
                    ));
                    facts.push(numeric_fact("fixed_length", *length, source.clone()));
                    facts.push(numeric_fact("bounded_minimum", *length, source.clone()));
                    facts.push(numeric_fact("bounded_maximum", *length, source));
                }
                LookbehindLength::FixedAlternatives { minimum, maximum } => {
                    facts.push(scalar_fact(
                        "common_fixed_width",
                        ConstraintScalar::Boolean(false),
                        None,
                        source.clone(),
                    ));
                    facts.push(numeric_fact("bounded_minimum", *minimum, source.clone()));
                    facts.push(numeric_fact("bounded_maximum", *maximum, source));
                }
                LookbehindLength::FiniteVariable { minimum, maximum } => {
                    facts.push(numeric_fact("bounded_minimum", *minimum, source.clone()));
                    facts.push(numeric_fact("bounded_maximum", *maximum, source));
                }
                LookbehindLength::Unbounded { minimum } => {
                    facts.push(numeric_fact("bounded_minimum", *minimum, source.clone()));
                    facts.push(nonfinite_fact(
                        "bounded_maximum",
                        ConstraintFactValue::Unbounded,
                        source,
                    ));
                }
                LookbehindLength::Indeterminate { minimum } => {
                    facts.push(numeric_fact("bounded_minimum", *minimum, source.clone()));
                    facts.push(nonfinite_fact(
                        "bounded_maximum",
                        ConstraintFactValue::Indeterminate,
                        source,
                    ));
                }
            }
        }
        RequirementKind::UnicodeProperty {
            property,
            value,
            negated,
        } => {
            facts.push(scalar_fact(
                "property",
                ConstraintScalar::String(property.clone()),
                None,
                semantic_source.clone(),
            ));
            if let Some(value) = value {
                facts.push(scalar_fact(
                    "property_value",
                    ConstraintScalar::String(value.clone()),
                    None,
                    semantic_source.clone(),
                ));
            }
            facts.push(scalar_fact(
                "negated",
                ConstraintScalar::Boolean(*negated),
                None,
                semantic_source,
            ));
        }
        RequirementKind::UnicodeCharacterClass { name, negated } => {
            facts.push(scalar_fact(
                "class",
                ConstraintScalar::String(builtin_class_name(*name).to_owned()),
                None,
                semantic_source.clone(),
            ));
            facts.push(scalar_fact(
                "negated",
                ConstraintScalar::Boolean(*negated),
                None,
                semantic_source,
            ));
        }
        RequirementKind::UnicodeScalarLiteral { .. }
        | RequirementKind::UnicodeScalarSetMember { .. } => {}
        RequirementKind::Position { position } => facts.push(scalar_fact(
            "position",
            ConstraintScalar::String(position_name(*position).to_owned()),
            None,
            semantic_source,
        )),
        RequirementKind::NamedCapture { name, .. } => {
            facts.push(numeric_fact_with_unit(
                "name_code_units",
                u64::try_from(name.len()).expect("capture name length must fit in u64"),
                "code_units",
                semantic_source.clone(),
            ));
            facts.push(scalar_fact(
                "name_syntax",
                ConstraintScalar::String(capture_name_syntax(name).to_owned()),
                None,
                semantic_source,
            ));
        }
        RequirementKind::Backreference { .. }
        | RequirementKind::Atomic
        | RequirementKind::PossessiveRepetition
        | RequirementKind::LazyRepetition
        | RequirementKind::CaseInsensitive => {}
    }
    facts.sort_by(|left, right| left.constraint_id.cmp(&right.constraint_id));
    facts
}

fn scalar_fact(
    constraint_id: &'static str,
    value: ConstraintScalar,
    unit: Option<ConstraintUnit>,
    source: ConstraintFactSource,
) -> RequirementConstraintFact {
    RequirementConstraintFact {
        constraint_id: ConstraintId::try_from(constraint_id)
            .expect("canonical requirement constraint identifier must be valid"),
        value: ConstraintFactValue::Scalar(value),
        unit,
        source,
    }
}

fn numeric_fact(
    constraint_id: &'static str,
    value: u64,
    source: ConstraintFactSource,
) -> RequirementConstraintFact {
    scalar_fact(
        constraint_id,
        ConstraintScalar::Number(serde_json::Number::from(value)),
        Some(
            ConstraintUnit::try_from("characters")
                .expect("canonical requirement constraint unit must be valid"),
        ),
        source,
    )
}

fn numeric_fact_with_unit(
    constraint_id: &'static str,
    value: u64,
    unit: &'static str,
    source: ConstraintFactSource,
) -> RequirementConstraintFact {
    scalar_fact(
        constraint_id,
        ConstraintScalar::Number(serde_json::Number::from(value)),
        Some(
            ConstraintUnit::try_from(unit)
                .expect("canonical requirement constraint unit must be valid"),
        ),
        source,
    )
}

fn nonfinite_fact(
    constraint_id: &'static str,
    value: ConstraintFactValue,
    source: ConstraintFactSource,
) -> RequirementConstraintFact {
    RequirementConstraintFact {
        constraint_id: ConstraintId::try_from(constraint_id)
            .expect("canonical requirement constraint identifier must be valid"),
        value,
        unit: Some(
            ConstraintUnit::try_from("characters")
                .expect("canonical requirement constraint unit must be valid"),
        ),
        source,
    }
}

fn polarity_name(polarity: RequirementPolarity) -> &'static str {
    match polarity {
        RequirementPolarity::Positive => "positive",
        RequirementPolarity::Negative => "negative",
    }
}

fn builtin_class_name(name: BuiltinClassName) -> &'static str {
    match name {
        BuiltinClassName::Digit => "digit",
        BuiltinClassName::Word => "word",
        BuiltinClassName::Whitespace => "whitespace",
    }
}

fn capture_name_syntax(name: &str) -> &'static str {
    let mut characters = name.chars();
    match characters.next() {
        Some(first)
            if (first.is_ascii_alphabetic() || first == '_')
                && characters
                    .all(|character| character.is_ascii_alphanumeric() || character == '_') =>
        {
            "ascii_identifier"
        }
        _ => "other",
    }
}

fn position_name(position: PositionRequirement) -> &'static str {
    match position {
        PositionRequirement::InputStart => "input_start",
        PositionRequirement::InputEnd => "input_end",
        PositionRequirement::LineStart => "line_start",
        PositionRequirement::LineEnd => "line_end",
        PositionRequirement::WordBoundary => "word_boundary",
        PositionRequirement::NotWordBoundary => "not_word_boundary",
        PositionRequirement::EndBeforeFinalLineTerminator => "end_before_final_line_terminator",
    }
}

fn validate_target_profile(
    input: &SemanticProgram,
    target: &TargetProfile,
) -> Result<(), CapabilityEvaluationErrors> {
    target.validate().map_err(|errors| {
        map_profile_errors(CapabilityEvaluationErrorCode::InvalidTargetProfile, errors)
    })?;
    if target.contract_version != input.contract_version {
        return Err(CapabilityEvaluationErrors::single(
            CapabilityEvaluationError::new(
                CapabilityEvaluationErrorCode::IncompatibleTargetProfile,
                "$.target_profile.contract_version",
                "target profile contract version does not match the semantic program",
            ),
        ));
    }
    if target
        .compatible_specification_versions
        .binary_search(&input.specification_version)
        .is_err()
    {
        return Err(CapabilityEvaluationErrors::single(
            CapabilityEvaluationError::new(
                CapabilityEvaluationErrorCode::IncompatibleTargetProfile,
                "$.target_profile.compatible_specification_versions",
                "target profile does not certify the semantic program specification version",
            ),
        ));
    }
    Ok(())
}

fn map_profile_errors(
    code: CapabilityEvaluationErrorCode,
    errors: crate::validation::ValidationErrors,
) -> CapabilityEvaluationErrors {
    CapabilityEvaluationErrors {
        errors: errors
            .errors
            .into_iter()
            .map(|error| {
                CapabilityEvaluationError::new(
                    code,
                    format!("$.target_profile{}", error.path.trim_start_matches('$')),
                    error.message,
                )
            })
            .collect(),
    }
}

fn extract_node_requirements(
    node: &Node,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    requirements: &mut Vec<SemanticRequirement>,
) -> Result<(), CapabilityEvaluationErrors> {
    match node {
        Node::Literal { node_id, text, .. } => {
            let scalars: Vec<_> = text.chars().filter(|scalar| !scalar.is_ascii()).collect();
            if !scalars.is_empty() {
                requirements.push(requirement(
                    node_id.clone(),
                    UNICODE_SCALAR_SEMANTICS,
                    RequirementKind::UnicodeScalarLiteral { scalars },
                ));
            }
        }
        Node::CharacterSet {
            node_id, members, ..
        } => {
            for member in members {
                match member {
                    CharacterSetMember::Literal { value } if !value.get().is_ascii() => {
                        requirements.push(requirement(
                            node_id.clone(),
                            UNICODE_SCALAR_SEMANTICS,
                            RequirementKind::UnicodeScalarSetMember {
                                start: value.get(),
                                end: value.get(),
                            },
                        ));
                    }
                    CharacterSetMember::Range { start, end }
                        if !start.get().is_ascii() || !end.get().is_ascii() =>
                    {
                        requirements.push(requirement(
                            node_id.clone(),
                            UNICODE_SCALAR_SEMANTICS,
                            RequirementKind::UnicodeScalarSetMember {
                                start: start.get(),
                                end: end.get(),
                            },
                        ));
                    }
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
                        domain: CharacterDomain::Ascii | CharacterDomain::TargetNative,
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
                    name: name.clone().expect("guard requires a capture name"),
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
                let length = lookbehind_length(body, foundational, structural)?;
                let capability = match length {
                    LookbehindLength::Fixed { .. } | LookbehindLength::FixedAlternatives { .. } => {
                        FIXED_LOOKBEHIND
                    }
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
        | Node::Wildcard { .. }
        | Node::Capture { .. } => {}
    }
    Ok(())
}

fn lookbehind_length(
    body: &Node,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) -> Result<LookbehindLength, CapabilityEvaluationErrors> {
    let body_node_id = body.node_id();
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
            if let Node::Alternation { branches, .. } = body {
                let mut lengths = Vec::with_capacity(branches.len());
                for branch in branches {
                    let Some(length) =
                        certified_fixed_length(branch.node_id(), foundational, structural)?
                    else {
                        lengths.clear();
                        break;
                    };
                    lengths.push(length);
                }
                if let (Some(minimum), Some(maximum)) = (lengths.iter().min(), lengths.iter().max())
                {
                    return Ok(LookbehindLength::FixedAlternatives {
                        minimum: *minimum,
                        maximum: *maximum,
                    });
                }
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

fn certified_fixed_length(
    node_id: &NodeId,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) -> Result<Option<u64>, CapabilityEvaluationErrors> {
    let semantic = foundational
        .get(node_id)
        .ok_or_else(|| missing_foundational(node_id, "fixed-alternative lookbehind length"))?;
    let structure = structural
        .get(node_id)
        .ok_or_else(|| missing_structural(node_id, "fixed-alternative lookbehind length"))?;
    let LengthClassification::Fixed(length) = structure.length else {
        return Ok(None);
    };
    if semantic.minimum_consumption != length
        || semantic.maximum_consumption != MaximumConsumption::Finite(length)
    {
        return Err(fact_invariant(
            node_id,
            "fixed structural length contradicts foundational bounds",
        ));
    }
    Ok(Some(length))
}

fn semantic_program_fingerprint(
    input: &SemanticProgram,
) -> Result<Sha256Digest, CapabilityEvaluationErrors> {
    canonical_sha256(input)
        .map(Sha256Digest::from_bytes)
        .map_err(|error| {
            CapabilityEvaluationErrors::single(CapabilityEvaluationError::new(
                CapabilityEvaluationErrorCode::FactInvariant,
                "$",
                format!("semantic program fingerprint could not be derived: {error}"),
            ))
        })
}

pub(crate) fn validate_prerequisites(
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
