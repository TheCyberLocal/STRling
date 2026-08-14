//! Bounded no-match evidence derived from canonical semantics.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;
use std::time::Instant;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::explanation::{
    ExplanationDocument, ExplanationModelVersion, SourceLink, TargetExplanationStatus,
};
use crate::semantic::{
    AssertionPolarity, BuiltinClassName, CaseMatching, CharacterDomain, CharacterSetMember,
    LineTerminators, LookaroundDirection, Node, PositionKind, RepetitionMaximum, RepetitionMode,
    SemanticProgram,
};
use crate::source::{CaptureId, ContractVersion, NodeId, Sha256Digest, SpecificationVersion};
use crate::target::{EngineIdentity, RuntimeIdentity, TargetProfileReference};
use crate::validation::{canonical_sha256, Validate};

/// Current independent bounded no-match model version.
pub const NO_MATCH_EXPLANATION_MODEL_VERSION: &str = "1.0.0";

/// Absolute UTF-8 input ceiling for one evaluation.
pub const MAX_NO_MATCH_SUBJECT_UTF8_BYTES: usize = 16 * 1024;
/// Absolute Unicode-scalar input ceiling for one evaluation.
pub const MAX_NO_MATCH_SUBJECT_UNICODE_SCALARS: usize = 4_096;
/// Absolute logical work-step ceiling.
pub const MAX_NO_MATCH_STEPS: u64 = 100_000;
/// Absolute semantic and evaluation nesting ceiling.
pub const MAX_NO_MATCH_DEPTH: usize = 128;
/// Absolute branch and state-expansion ceiling.
pub const MAX_NO_MATCH_BRANCH_EXPANSIONS: u64 = 4_096;
/// Absolute retained-finding ceiling.
pub const MAX_NO_MATCH_FINDINGS: usize = 32;
/// Absolute elapsed-work fail-safe in milliseconds.
pub const MAX_NO_MATCH_ELAPSED_MILLISECONDS: u64 = 250;

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum NoMatchExplanationModelVersion {
    #[serde(rename = "1.0.0")]
    V1_0_0,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchExecutionMode {
    Search,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchOutcome {
    Matched,
    NoMatch,
    Unknown,
    Unavailable,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchExplanationDisposition {
    NotApplicable,
    Proven,
    Likely,
    Unknown,
    Unavailable,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchConfidence {
    Proven,
    Likely,
    Unknown,
    Unavailable,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchEvidenceClass {
    CanonicalEvaluation,
    TargetPlan,
    Uncertainty,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchReasonCode {
    LiteralMismatch,
    WildcardLineTerminator,
    CharacterSetMismatch,
    InputStartAssertionFailed,
    InputEndAssertionFailed,
    LineStartAssertionFailed,
    LineEndAssertionFailed,
    WordBoundaryAssertionFailed,
    NotWordBoundaryAssertionFailed,
    FinalLineTerminatorAssertionFailed,
    AlternationExhausted,
    RepetitionMinimumUnmet,
    PositiveLookaroundFailed,
    NegativeLookaroundMatched,
    CaptureUnavailable,
    BackreferenceMismatch,
    TargetUnsupported,
    TargetUnresolved,
    TargetSemanticsUnknown,
    SubjectUtf8LimitReached,
    SubjectScalarLimitReached,
    StepLimitReached,
    DepthLimitReached,
    BranchLimitReached,
    FindingLimitReached,
    ElapsedLimitReached,
    SemanticEvaluationUnavailable,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchLimitKind {
    SubjectUtf8Bytes,
    SubjectUnicodeScalars,
    Steps,
    Depth,
    Branches,
    Findings,
    Elapsed,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchTargetStatus {
    Native,
    EquivalentRewrite,
    Unsupported,
    Unresolved,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchSemanticExplanationLink {
    pub model_version: ExplanationModelVersion,
    pub semantic_program: Sha256Digest,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchSubjectIdentity {
    pub sha256: Sha256Digest,
    pub utf8_bytes: usize,
    pub unicode_scalars: usize,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchTargetContext {
    pub target_profile: TargetProfileReference,
    pub engine: EngineIdentity,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime: Option<RuntimeIdentity>,
    pub status: NoMatchTargetStatus,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum NoMatchSubjectLocation {
    Position { byte_offset: usize },
    Span { start: usize, end: usize },
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchBranchContext {
    pub node_id: NodeId,
    pub branch_index: usize,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchRepetitionContext {
    pub node_id: NodeId,
    pub iteration: u64,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchAssertionKind {
    Position,
    Lookahead,
    Lookbehind,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchAssertionContext {
    pub node_id: NodeId,
    pub kind: NoMatchAssertionKind,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub polarity: Option<AssertionPolarity>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchFindingContext {
    pub candidate_start: usize,
    pub branches: Vec<NoMatchBranchContext>,
    pub repetitions: Vec<NoMatchRepetitionContext>,
    pub assertions: Vec<NoMatchAssertionContext>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capture_id: Option<CaptureId>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchFinding {
    pub ordinal: usize,
    pub reason_code: NoMatchReasonCode,
    pub confidence: NoMatchConfidence,
    pub evidence_class: NoMatchEvidenceClass,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub node_id: Option<NodeId>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source: Option<SourceLink>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub subject_location: Option<NoMatchSubjectLocation>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub context: Option<NoMatchFindingContext>,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchLimits {
    pub max_subject_utf8_bytes: usize,
    pub max_subject_unicode_scalars: usize,
    pub max_steps: u64,
    pub max_depth: usize,
    pub max_branch_expansions: u64,
    pub max_findings: usize,
    pub max_elapsed_milliseconds: u64,
}

impl Default for NoMatchLimits {
    fn default() -> Self {
        Self {
            max_subject_utf8_bytes: MAX_NO_MATCH_SUBJECT_UTF8_BYTES,
            max_subject_unicode_scalars: MAX_NO_MATCH_SUBJECT_UNICODE_SCALARS,
            max_steps: MAX_NO_MATCH_STEPS,
            max_depth: MAX_NO_MATCH_DEPTH,
            max_branch_expansions: MAX_NO_MATCH_BRANCH_EXPANSIONS,
            max_findings: MAX_NO_MATCH_FINDINGS,
            max_elapsed_milliseconds: MAX_NO_MATCH_ELAPSED_MILLISECONDS,
        }
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchWorkReport {
    pub candidate_starts: usize,
    pub steps: u64,
    pub maximum_depth: usize,
    pub branch_expansions: u64,
    pub findings_considered: usize,
    pub reached_limits: Vec<NoMatchLimitKind>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchExplanationDocument {
    pub model_version: NoMatchExplanationModelVersion,
    pub contract_version: ContractVersion,
    pub specification_version: SpecificationVersion,
    pub semantic_program: Sha256Digest,
    pub semantic_explanation: NoMatchSemanticExplanationLink,
    pub execution_mode: NoMatchExecutionMode,
    pub subject: NoMatchSubjectIdentity,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub target: Option<NoMatchTargetContext>,
    pub outcome: NoMatchOutcome,
    pub explanation_disposition: NoMatchExplanationDisposition,
    pub findings: Vec<NoMatchFinding>,
    pub limits: NoMatchLimits,
    pub work: NoMatchWorkReport,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NoMatchExplanationErrorCode {
    InvalidProgram,
    MismatchedExplanation,
    InvalidLimits,
    SubjectExceedsHardLimit,
    SerializationInvariant,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchExplanationError {
    pub code: NoMatchExplanationErrorCode,
    pub path: String,
    pub message: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct NoMatchExplanationErrors {
    pub errors: Vec<NoMatchExplanationError>,
}

impl NoMatchExplanationErrors {
    fn single(
        code: NoMatchExplanationErrorCode,
        path: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            errors: vec![NoMatchExplanationError {
                code,
                path: path.into(),
                message: message.into(),
            }],
        }
    }
}

impl fmt::Display for NoMatchExplanationErrors {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "bounded no-match explanation failed with {} error(s)",
            self.errors.len()
        )
    }
}

impl Error for NoMatchExplanationErrors {}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct EvalState {
    position: usize,
    captures: BTreeMap<CaptureId, (usize, usize)>,
}

#[derive(Clone, Debug)]
struct EvalContext {
    candidate_start: usize,
    branches: Vec<NoMatchBranchContext>,
    repetitions: Vec<NoMatchRepetitionContext>,
    assertions: Vec<NoMatchAssertionContext>,
    capture_id: Option<CaptureId>,
}

impl EvalContext {
    fn new(candidate_start: usize) -> Self {
        Self {
            candidate_start,
            branches: Vec::new(),
            repetitions: Vec::new(),
            assertions: Vec::new(),
            capture_id: None,
        }
    }

    fn public(&self) -> NoMatchFindingContext {
        NoMatchFindingContext {
            candidate_start: self.candidate_start,
            branches: self.branches.clone(),
            repetitions: self.repetitions.clone(),
            assertions: self.assertions.clone(),
            capture_id: self.capture_id.clone(),
        }
    }
}

#[derive(Clone, Debug)]
struct Failure {
    reason_code: NoMatchReasonCode,
    node_id: Option<NodeId>,
    subject_location: Option<NoMatchSubjectLocation>,
    context: Option<EvalContext>,
    ambiguous: bool,
}

#[derive(Clone, Debug, Default)]
struct EvalBatch {
    states: Vec<EvalState>,
    failures: Vec<Failure>,
    uncertainties: Vec<Failure>,
}

impl EvalBatch {
    fn matched(state: EvalState) -> Self {
        Self {
            states: vec![state],
            ..Self::default()
        }
    }

    fn known_failure(failure: Failure) -> Self {
        Self {
            failures: vec![failure],
            ..Self::default()
        }
    }

    fn uncertain(failure: Failure) -> Self {
        Self {
            uncertainties: vec![failure],
            ..Self::default()
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct SubjectScalar {
    start: usize,
    end: usize,
    value: char,
}

struct Budget {
    limits: NoMatchLimits,
    started: Instant,
    candidate_starts: usize,
    steps: u64,
    maximum_depth: usize,
    branch_expansions: u64,
    findings_considered: usize,
    retained_finding_keys: BTreeSet<(NoMatchReasonCode, Option<NodeId>)>,
    reached_limits: BTreeSet<NoMatchLimitKind>,
}

impl Budget {
    fn new(limits: NoMatchLimits) -> Self {
        Self {
            limits,
            started: Instant::now(),
            candidate_starts: 0,
            steps: 0,
            maximum_depth: 0,
            branch_expansions: 0,
            findings_considered: 0,
            retained_finding_keys: BTreeSet::new(),
            reached_limits: BTreeSet::new(),
        }
    }

    fn check_elapsed(&mut self) -> Result<(), NoMatchLimitKind> {
        if self.limits.max_elapsed_milliseconds == 0
            || self.started.elapsed().as_millis()
                >= u128::from(self.limits.max_elapsed_milliseconds)
        {
            self.reached_limits.insert(NoMatchLimitKind::Elapsed);
            return Err(NoMatchLimitKind::Elapsed);
        }
        Ok(())
    }

    fn candidate(&mut self) -> Result<(), NoMatchLimitKind> {
        self.check_elapsed()?;
        self.candidate_starts += 1;
        self.step(0)
    }

    fn step(&mut self, depth: usize) -> Result<(), NoMatchLimitKind> {
        self.check_elapsed()?;
        if depth > self.limits.max_depth {
            self.reached_limits.insert(NoMatchLimitKind::Depth);
            return Err(NoMatchLimitKind::Depth);
        }
        self.maximum_depth = self.maximum_depth.max(depth);
        if self.steps >= self.limits.max_steps {
            self.reached_limits.insert(NoMatchLimitKind::Steps);
            return Err(NoMatchLimitKind::Steps);
        }
        self.steps += 1;
        Ok(())
    }

    fn branch(&mut self) -> Result<(), NoMatchLimitKind> {
        self.check_elapsed()?;
        if self.branch_expansions >= self.limits.max_branch_expansions {
            self.reached_limits.insert(NoMatchLimitKind::Branches);
            return Err(NoMatchLimitKind::Branches);
        }
        self.branch_expansions += 1;
        Ok(())
    }

    fn finding(
        &mut self,
        reason: NoMatchReasonCode,
        node_id: Option<&NodeId>,
    ) -> Result<(), NoMatchLimitKind> {
        self.findings_considered += 1;
        let key = (reason, node_id.cloned());
        if self.retained_finding_keys.contains(&key) {
            return Ok(());
        }
        if self.retained_finding_keys.len() >= self.limits.max_findings {
            self.reached_limits.insert(NoMatchLimitKind::Findings);
            return Err(NoMatchLimitKind::Findings);
        }
        self.retained_finding_keys.insert(key);
        Ok(())
    }

    fn report(&self) -> NoMatchWorkReport {
        NoMatchWorkReport {
            candidate_starts: self.candidate_starts,
            steps: self.steps,
            maximum_depth: self.maximum_depth,
            branch_expansions: self.branch_expansions,
            findings_considered: self.findings_considered,
            reached_limits: self.reached_limits.iter().copied().collect(),
        }
    }
}

struct Evaluator<'a> {
    input: &'a SemanticProgram,
    subject: &'a str,
    scalars: Vec<SubjectScalar>,
    boundaries: Vec<usize>,
    boundary_indexes: BTreeMap<usize, usize>,
    budget: Budget,
}

impl<'a> Evaluator<'a> {
    fn new(input: &'a SemanticProgram, subject: &'a str, limits: NoMatchLimits) -> Self {
        let mut scalars = Vec::new();
        let mut boundaries = vec![0];
        for (start, value) in subject.char_indices() {
            let end = start + value.len_utf8();
            scalars.push(SubjectScalar { start, end, value });
            boundaries.push(end);
        }
        let boundary_indexes = boundaries
            .iter()
            .copied()
            .enumerate()
            .map(|(index, offset)| (offset, index))
            .collect();
        Self {
            input,
            subject,
            scalars,
            boundaries,
            boundary_indexes,
            budget: Budget::new(limits),
        }
    }

    fn run(&mut self) -> Result<Evaluation, NoMatchLimitKind> {
        let mut failures = Vec::new();
        let mut uncertainties = Vec::new();
        for candidate_start in self.boundaries.clone() {
            self.budget.candidate()?;
            let state = EvalState {
                position: candidate_start,
                captures: BTreeMap::new(),
            };
            let batch = self.evaluate_node(
                &self.input.root,
                state,
                &EvalContext::new(candidate_start),
                1,
            )?;
            if !batch.states.is_empty() {
                return Ok(Evaluation::Matched);
            }
            failures.extend(batch.failures);
            uncertainties.extend(batch.uncertainties);
        }
        if let Some(uncertainty) = canonical_failures(uncertainties).into_iter().next() {
            Ok(Evaluation::Unknown(uncertainty))
        } else {
            Ok(Evaluation::NoMatch(canonical_failures(failures)))
        }
    }

    fn evaluate_node(
        &mut self,
        node: &Node,
        state: EvalState,
        context: &EvalContext,
        depth: usize,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        self.budget.step(depth)?;
        match node {
            Node::Empty { .. } => Ok(EvalBatch::matched(state)),
            Node::Sequence { items, .. } => self.evaluate_sequence(items, state, context, depth),
            Node::Alternation {
                node_id, branches, ..
            } => self.evaluate_alternation(node_id, branches, state, context, depth),
            Node::Literal { node_id, text, .. } => {
                self.evaluate_literal(node_id, text, state, context, depth)
            }
            Node::Wildcard {
                node_id,
                line_terminators,
                ..
            } => self.evaluate_wildcard(node_id, *line_terminators, state, context),
            Node::CharacterSet {
                node_id,
                negated,
                members,
                ..
            } => self.evaluate_character_set(node_id, *negated, members, state, context),
            Node::Repeat {
                node_id,
                body,
                min,
                max,
                mode,
                ..
            } => self.evaluate_repeat(node_id, body, *min, *max, *mode, state, context, depth),
            Node::Position {
                node_id, position, ..
            } => self.evaluate_position(node_id, *position, state, context),
            Node::Capture {
                capture_id, body, ..
            } => self.evaluate_capture(capture_id, body, state, context, depth),
            Node::Backreference {
                node_id,
                capture_id,
                ..
            } => self.evaluate_backreference(node_id, capture_id, state, context, depth),
            Node::Lookaround {
                node_id,
                direction,
                polarity,
                body,
                ..
            } => self
                .evaluate_lookaround(node_id, *direction, *polarity, body, state, context, depth),
            Node::Atomic { node_id, .. } => {
                self.uncertain_node(NoMatchReasonCode::SemanticEvaluationUnavailable, node_id)
            }
        }
    }

    fn evaluate_sequence(
        &mut self,
        items: &[Node],
        state: EvalState,
        context: &EvalContext,
        depth: usize,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        let mut current = vec![state];
        let mut failures = Vec::new();
        let mut uncertainties = Vec::new();
        for item in items {
            let mut next = Vec::new();
            for candidate in current {
                let batch = self.evaluate_node(item, candidate, context, depth + 1)?;
                next.extend(batch.states);
                failures.extend(batch.failures);
                uncertainties.extend(batch.uncertainties);
            }
            current = deduplicate_states(next);
            if current.is_empty() {
                return Ok(EvalBatch {
                    states: Vec::new(),
                    failures,
                    uncertainties,
                });
            }
        }
        Ok(EvalBatch {
            states: current,
            failures,
            uncertainties,
        })
    }

    fn evaluate_alternation(
        &mut self,
        node_id: &NodeId,
        branches: &[Node],
        state: EvalState,
        context: &EvalContext,
        depth: usize,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        let mut states = Vec::new();
        let mut uncertainties = Vec::new();
        for (branch_index, branch) in branches.iter().enumerate() {
            self.budget.branch()?;
            let mut branch_context = context.clone();
            branch_context.branches.push(NoMatchBranchContext {
                node_id: node_id.clone(),
                branch_index,
            });
            let batch = self.evaluate_node(branch, state.clone(), &branch_context, depth + 1)?;
            states.extend(batch.states);
            uncertainties.extend(batch.uncertainties);
        }
        let states = deduplicate_states(states);
        if !states.is_empty() {
            return Ok(EvalBatch {
                states,
                failures: Vec::new(),
                uncertainties,
            });
        }
        if !uncertainties.is_empty() {
            return Ok(EvalBatch {
                states: Vec::new(),
                failures: Vec::new(),
                uncertainties,
            });
        }
        let failure = self.failure(
            NoMatchReasonCode::AlternationExhausted,
            Some(node_id),
            Some(NoMatchSubjectLocation::Position {
                byte_offset: state.position,
            }),
            Some(context.clone()),
            true,
        )?;
        Ok(EvalBatch::known_failure(failure))
    }

    fn evaluate_literal(
        &mut self,
        node_id: &NodeId,
        text: &str,
        mut state: EvalState,
        context: &EvalContext,
        depth: usize,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        if self.input.case_matching == CaseMatching::Insensitive && !text.is_ascii() {
            return self.uncertain_node(NoMatchReasonCode::TargetSemanticsUnknown, node_id);
        }
        let mut position = state.position;
        for expected in text.chars() {
            self.budget.step(depth)?;
            let Some(actual) = self.scalar_at(position) else {
                let failure = self.failure(
                    NoMatchReasonCode::LiteralMismatch,
                    Some(node_id),
                    Some(NoMatchSubjectLocation::Position {
                        byte_offset: position,
                    }),
                    Some(context.clone()),
                    false,
                )?;
                return Ok(EvalBatch::known_failure(failure));
            };
            let equal = match self.input.case_matching {
                CaseMatching::Sensitive => expected == actual.value,
                CaseMatching::Insensitive if expected.is_ascii() && actual.value.is_ascii() => {
                    expected.eq_ignore_ascii_case(&actual.value)
                }
                CaseMatching::Insensitive => {
                    return self.uncertain_node(NoMatchReasonCode::TargetSemanticsUnknown, node_id);
                }
            };
            if !equal {
                let failure = self.failure(
                    NoMatchReasonCode::LiteralMismatch,
                    Some(node_id),
                    Some(NoMatchSubjectLocation::Span {
                        start: actual.start,
                        end: actual.end,
                    }),
                    Some(context.clone()),
                    false,
                )?;
                return Ok(EvalBatch::known_failure(failure));
            }
            position = actual.end;
        }
        state.position = position;
        Ok(EvalBatch::matched(state))
    }

    fn evaluate_wildcard(
        &mut self,
        node_id: &NodeId,
        line_terminators: LineTerminators,
        mut state: EvalState,
        context: &EvalContext,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        let Some(actual) = self.scalar_at(state.position) else {
            let failure = self.failure(
                NoMatchReasonCode::WildcardLineTerminator,
                Some(node_id),
                Some(NoMatchSubjectLocation::Position {
                    byte_offset: state.position,
                }),
                Some(context.clone()),
                false,
            )?;
            return Ok(EvalBatch::known_failure(failure));
        };
        if line_terminators == LineTerminators::Exclude
            && matches!(actual.value, '\n' | '\r' | '\u{2028}' | '\u{2029}')
        {
            let failure = self.failure(
                NoMatchReasonCode::WildcardLineTerminator,
                Some(node_id),
                Some(NoMatchSubjectLocation::Span {
                    start: actual.start,
                    end: actual.end,
                }),
                Some(context.clone()),
                false,
            )?;
            return Ok(EvalBatch::known_failure(failure));
        }
        state.position = actual.end;
        Ok(EvalBatch::matched(state))
    }

    fn evaluate_character_set(
        &mut self,
        node_id: &NodeId,
        negated: bool,
        members: &[CharacterSetMember],
        mut state: EvalState,
        context: &EvalContext,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        let Some(actual) = self.scalar_at(state.position) else {
            let failure = self.failure(
                NoMatchReasonCode::CharacterSetMismatch,
                Some(node_id),
                Some(NoMatchSubjectLocation::Position {
                    byte_offset: state.position,
                }),
                Some(context.clone()),
                false,
            )?;
            return Ok(EvalBatch::known_failure(failure));
        };
        let mut matched = false;
        for member in members {
            match self.member_matches(member, actual.value) {
                Some(value) => matched |= value,
                None => {
                    let reason = if matches!(
                        member,
                        CharacterSetMember::Builtin {
                            domain: CharacterDomain::TargetNative,
                            ..
                        }
                    ) {
                        NoMatchReasonCode::TargetSemanticsUnknown
                    } else {
                        NoMatchReasonCode::SemanticEvaluationUnavailable
                    };
                    return self.uncertain_node(reason, node_id);
                }
            }
        }
        if negated {
            matched = !matched;
        }
        if matched {
            state.position = actual.end;
            Ok(EvalBatch::matched(state))
        } else {
            let failure = self.failure(
                NoMatchReasonCode::CharacterSetMismatch,
                Some(node_id),
                Some(NoMatchSubjectLocation::Span {
                    start: actual.start,
                    end: actual.end,
                }),
                Some(context.clone()),
                false,
            )?;
            Ok(EvalBatch::known_failure(failure))
        }
    }

    fn member_matches(&self, member: &CharacterSetMember, actual: char) -> Option<bool> {
        let value = match member {
            CharacterSetMember::Literal { value } => match self.input.case_matching {
                CaseMatching::Sensitive => value.get() == actual,
                CaseMatching::Insensitive if value.get().is_ascii() && actual.is_ascii() => {
                    value.get().eq_ignore_ascii_case(&actual)
                }
                CaseMatching::Insensitive => return None,
            },
            CharacterSetMember::Range { start, end } => match self.input.case_matching {
                CaseMatching::Sensitive => start.get() <= actual && actual <= end.get(),
                CaseMatching::Insensitive
                    if start.get().is_ascii() && end.get().is_ascii() && actual.is_ascii() =>
                {
                    let folded = actual.to_ascii_lowercase();
                    start.get().to_ascii_lowercase() <= folded
                        && folded <= end.get().to_ascii_lowercase()
                }
                CaseMatching::Insensitive => return None,
            },
            CharacterSetMember::Builtin {
                name,
                domain: CharacterDomain::Ascii,
                negated,
            } => {
                let matched = match name {
                    BuiltinClassName::Digit => actual.is_ascii_digit(),
                    BuiltinClassName::Word => actual.is_ascii_alphanumeric() || actual == '_',
                    BuiltinClassName::Whitespace => {
                        matches!(actual, '\t' | '\n' | '\u{000b}' | '\u{000c}' | '\r' | ' ')
                    }
                };
                return Some(if *negated { !matched } else { matched });
            }
            CharacterSetMember::Builtin {
                domain: CharacterDomain::Unicode | CharacterDomain::TargetNative,
                ..
            }
            | CharacterSetMember::UnicodeProperty { .. } => return None,
        };
        Some(value)
    }

    #[allow(clippy::too_many_arguments)]
    fn evaluate_repeat(
        &mut self,
        node_id: &NodeId,
        body: &Node,
        minimum: u64,
        maximum: RepetitionMaximum,
        mode: RepetitionMode,
        state: EvalState,
        context: &EvalContext,
        depth: usize,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        if mode == RepetitionMode::Possessive {
            return self.uncertain_node(NoMatchReasonCode::SemanticEvaluationUnavailable, node_id);
        }
        let maximum = match maximum {
            RepetitionMaximum::Bounded(value) => Some(value),
            RepetitionMaximum::Unbounded => None,
        };
        let mut count = 0_u64;
        let mut frontier = vec![state.clone()];
        let mut eligible = if minimum == 0 {
            vec![state]
        } else {
            Vec::new()
        };
        let mut uncertainties = Vec::new();
        while maximum.map_or(true, |value| count < value) && !frontier.is_empty() {
            let mut next = Vec::new();
            let mut progressed = false;
            for candidate in frontier {
                self.budget.branch()?;
                let mut repetition_context = context.clone();
                repetition_context
                    .repetitions
                    .push(NoMatchRepetitionContext {
                        node_id: node_id.clone(),
                        iteration: count,
                    });
                let before = candidate.clone();
                let batch = self.evaluate_node(body, candidate, &repetition_context, depth + 1)?;
                progressed |= batch
                    .states
                    .iter()
                    .any(|value| value.position != before.position);
                next.extend(batch.states);
                uncertainties.extend(batch.uncertainties);
            }
            next = deduplicate_states(next);
            if next.is_empty() {
                break;
            }
            count += 1;
            if count >= minimum {
                eligible.extend(next.clone());
            }
            frontier = next;
            if !progressed {
                break;
            }
        }
        eligible = deduplicate_states(eligible);
        if !eligible.is_empty() {
            if mode == RepetitionMode::Greedy {
                eligible.reverse();
            }
            return Ok(EvalBatch {
                states: eligible,
                failures: Vec::new(),
                uncertainties,
            });
        }
        if !uncertainties.is_empty() {
            return Ok(EvalBatch {
                states: Vec::new(),
                failures: Vec::new(),
                uncertainties,
            });
        }
        let failure = self.failure(
            NoMatchReasonCode::RepetitionMinimumUnmet,
            Some(node_id),
            Some(NoMatchSubjectLocation::Position {
                byte_offset: context.candidate_start,
            }),
            Some(context.clone()),
            false,
        )?;
        Ok(EvalBatch::known_failure(failure))
    }

    fn evaluate_position(
        &mut self,
        node_id: &NodeId,
        position: PositionKind,
        state: EvalState,
        context: &EvalContext,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        let result = self.position_matches(position, state.position);
        let (matched, reason) = match result {
            PositionResult::Known(value) => (value, position_reason(position)),
            PositionResult::TargetUnknown => {
                return self.uncertain_node(NoMatchReasonCode::TargetSemanticsUnknown, node_id);
            }
        };
        if matched {
            return Ok(EvalBatch::matched(state));
        }
        let mut failure_context = context.clone();
        failure_context.assertions.push(NoMatchAssertionContext {
            node_id: node_id.clone(),
            kind: NoMatchAssertionKind::Position,
            polarity: None,
        });
        let failure = self.failure(
            reason,
            Some(node_id),
            Some(NoMatchSubjectLocation::Position {
                byte_offset: state.position,
            }),
            Some(failure_context),
            false,
        )?;
        Ok(EvalBatch::known_failure(failure))
    }

    fn position_matches(&self, position: PositionKind, offset: usize) -> PositionResult {
        match position {
            PositionKind::InputStart => PositionResult::Known(offset == 0),
            PositionKind::InputEnd => PositionResult::Known(offset == self.subject.len()),
            PositionKind::LineStart => {
                if offset == 0 {
                    PositionResult::Known(true)
                } else {
                    match self.scalar_before(offset).map(|value| value.value) {
                        Some('\n') => PositionResult::Known(true),
                        Some('\r' | '\u{2028}' | '\u{2029}') => PositionResult::TargetUnknown,
                        Some(_) => PositionResult::Known(false),
                        None => PositionResult::Known(false),
                    }
                }
            }
            PositionKind::LineEnd => {
                if offset == self.subject.len() {
                    PositionResult::Known(true)
                } else {
                    match self.scalar_at(offset).map(|value| value.value) {
                        Some('\n') => PositionResult::Known(true),
                        Some('\r' | '\u{2028}' | '\u{2029}') => PositionResult::TargetUnknown,
                        Some(_) => PositionResult::Known(false),
                        None => PositionResult::Known(false),
                    }
                }
            }
            PositionKind::WordBoundary | PositionKind::NotWordBoundary => {
                let left = self.scalar_before(offset).map(|value| value.value);
                let right = self.scalar_at(offset).map(|value| value.value);
                if left.is_some_and(|value| !value.is_ascii())
                    || right.is_some_and(|value| !value.is_ascii())
                {
                    return PositionResult::TargetUnknown;
                }
                let left_word = left.is_some_and(ascii_word);
                let right_word = right.is_some_and(ascii_word);
                let boundary = left_word != right_word;
                PositionResult::Known(if position == PositionKind::WordBoundary {
                    boundary
                } else {
                    !boundary
                })
            }
            PositionKind::EndBeforeFinalLineTerminator => {
                let scalar = self.scalar_at(offset);
                if offset == self.subject.len()
                    || scalar
                        .is_some_and(|value| value.value == '\n' && value.end == self.subject.len())
                {
                    PositionResult::Known(true)
                } else if scalar
                    .is_some_and(|value| matches!(value.value, '\r' | '\u{2028}' | '\u{2029}'))
                {
                    PositionResult::TargetUnknown
                } else {
                    PositionResult::Known(false)
                }
            }
        }
    }

    fn evaluate_capture(
        &mut self,
        capture_id: &CaptureId,
        body: &Node,
        state: EvalState,
        context: &EvalContext,
        depth: usize,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        let start = state.position;
        let mut capture_context = context.clone();
        capture_context.capture_id = Some(capture_id.clone());
        let mut batch = self.evaluate_node(body, state, &capture_context, depth + 1)?;
        for matched in &mut batch.states {
            matched
                .captures
                .insert(capture_id.clone(), (start, matched.position));
        }
        Ok(batch)
    }

    fn evaluate_backreference(
        &mut self,
        node_id: &NodeId,
        capture_id: &CaptureId,
        mut state: EvalState,
        context: &EvalContext,
        depth: usize,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        let mut reference_context = context.clone();
        reference_context.capture_id = Some(capture_id.clone());
        let Some((start, end)) = state.captures.get(capture_id).copied() else {
            let failure = self.failure(
                NoMatchReasonCode::CaptureUnavailable,
                Some(node_id),
                Some(NoMatchSubjectLocation::Position {
                    byte_offset: state.position,
                }),
                Some(reference_context),
                false,
            )?;
            return Ok(EvalBatch::known_failure(failure));
        };
        let captured = &self.subject[start..end];
        if self.input.case_matching == CaseMatching::Insensitive && !captured.is_ascii() {
            return self.uncertain_node(NoMatchReasonCode::TargetSemanticsUnknown, node_id);
        }
        let target_end = state.position.saturating_add(captured.len());
        self.budget.step(depth)?;
        let matched = self
            .subject
            .get(state.position..target_end)
            .is_some_and(|value| {
                if self.input.case_matching == CaseMatching::Sensitive {
                    value == captured
                } else {
                    value.eq_ignore_ascii_case(captured)
                }
            });
        if matched {
            state.position = target_end;
            Ok(EvalBatch::matched(state))
        } else {
            let location = self.scalar_at(state.position).map_or(
                NoMatchSubjectLocation::Position {
                    byte_offset: state.position,
                },
                |value| NoMatchSubjectLocation::Span {
                    start: value.start,
                    end: value.end,
                },
            );
            let failure = self.failure(
                NoMatchReasonCode::BackreferenceMismatch,
                Some(node_id),
                Some(location),
                Some(reference_context),
                false,
            )?;
            Ok(EvalBatch::known_failure(failure))
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn evaluate_lookaround(
        &mut self,
        node_id: &NodeId,
        direction: LookaroundDirection,
        polarity: AssertionPolarity,
        body: &Node,
        state: EvalState,
        context: &EvalContext,
        depth: usize,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        if contains_capture_state(body) {
            return self.uncertain_node(NoMatchReasonCode::SemanticEvaluationUnavailable, node_id);
        }
        let kind = match direction {
            LookaroundDirection::Ahead => NoMatchAssertionKind::Lookahead,
            LookaroundDirection::Behind => NoMatchAssertionKind::Lookbehind,
        };
        let mut assertion_context = context.clone();
        assertion_context.assertions.push(NoMatchAssertionContext {
            node_id: node_id.clone(),
            kind,
            polarity: Some(polarity),
        });

        let (matched, uncertain) = match direction {
            LookaroundDirection::Ahead => {
                let batch =
                    self.evaluate_node(body, state.clone(), &assertion_context, depth + 1)?;
                (!batch.states.is_empty(), !batch.uncertainties.is_empty())
            }
            LookaroundDirection::Behind => {
                let mut matched = false;
                let mut uncertain = false;
                for start in self
                    .boundaries
                    .iter()
                    .copied()
                    .take_while(|offset| *offset <= state.position)
                    .collect::<Vec<_>>()
                {
                    self.budget.branch()?;
                    let batch = self.evaluate_node(
                        body,
                        EvalState {
                            position: start,
                            captures: state.captures.clone(),
                        },
                        &assertion_context,
                        depth + 1,
                    )?;
                    matched |= batch
                        .states
                        .iter()
                        .any(|candidate| candidate.position == state.position);
                    uncertain |= !batch.uncertainties.is_empty();
                }
                (matched, uncertain)
            }
        };
        if uncertain && !matched {
            return self.uncertain_node(NoMatchReasonCode::SemanticEvaluationUnavailable, node_id);
        }
        let assertion_satisfied = match polarity {
            AssertionPolarity::Positive => matched,
            AssertionPolarity::Negative => !matched,
        };
        if assertion_satisfied {
            return Ok(EvalBatch::matched(state));
        }
        let reason = match polarity {
            AssertionPolarity::Positive => NoMatchReasonCode::PositiveLookaroundFailed,
            AssertionPolarity::Negative => NoMatchReasonCode::NegativeLookaroundMatched,
        };
        let failure = self.failure(
            reason,
            Some(node_id),
            Some(NoMatchSubjectLocation::Position {
                byte_offset: state.position,
            }),
            Some(assertion_context),
            false,
        )?;
        Ok(EvalBatch::known_failure(failure))
    }

    fn uncertain_node(
        &mut self,
        reason_code: NoMatchReasonCode,
        node_id: &NodeId,
    ) -> Result<EvalBatch, NoMatchLimitKind> {
        let failure = self.failure(reason_code, Some(node_id), None, None, false)?;
        Ok(EvalBatch::uncertain(failure))
    }

    fn failure(
        &mut self,
        reason_code: NoMatchReasonCode,
        node_id: Option<&NodeId>,
        subject_location: Option<NoMatchSubjectLocation>,
        context: Option<EvalContext>,
        ambiguous: bool,
    ) -> Result<Failure, NoMatchLimitKind> {
        self.budget.finding(reason_code, node_id)?;
        Ok(Failure {
            reason_code,
            node_id: node_id.cloned(),
            subject_location,
            context,
            ambiguous,
        })
    }

    fn scalar_at(&self, offset: usize) -> Option<SubjectScalar> {
        let index = *self.boundary_indexes.get(&offset)?;
        self.scalars.get(index).copied()
    }

    fn scalar_before(&self, offset: usize) -> Option<SubjectScalar> {
        let index = *self.boundary_indexes.get(&offset)?;
        index
            .checked_sub(1)
            .and_then(|value| self.scalars.get(value).copied())
    }
}

enum Evaluation {
    Matched,
    NoMatch(Vec<Failure>),
    Unknown(Failure),
}

enum PositionResult {
    Known(bool),
    TargetUnknown,
}

/// Produce bounded structured evidence for one explicit search operation.
pub fn explain_no_match(
    input: &SemanticProgram,
    semantic: &ExplanationDocument,
    subject: &str,
    execution_mode: NoMatchExecutionMode,
    limits: NoMatchLimits,
) -> Result<NoMatchExplanationDocument, NoMatchExplanationErrors> {
    validate_inputs(input, semantic, subject, limits)?;
    let semantic_program = Sha256Digest::from_bytes(canonical_sha256(input).map_err(|error| {
        NoMatchExplanationErrors::single(
            NoMatchExplanationErrorCode::SerializationInvariant,
            "$.semantic_program",
            format!("semantic program fingerprint could not be derived: {error}"),
        )
    })?);
    let scalar_count = subject.chars().count();
    let subject_identity = NoMatchSubjectIdentity {
        sha256: Sha256Digest::from_bytes(Sha256::digest(subject.as_bytes()).into()),
        utf8_bytes: subject.len(),
        unicode_scalars: scalar_count,
    };
    let target = semantic.target.as_ref().map(|value| NoMatchTargetContext {
        target_profile: value.target_profile.clone(),
        engine: value.engine.clone(),
        runtime: value.runtime.clone(),
        status: match value.status {
            TargetExplanationStatus::Native => NoMatchTargetStatus::Native,
            TargetExplanationStatus::EquivalentRewrite => NoMatchTargetStatus::EquivalentRewrite,
            TargetExplanationStatus::Unsupported => NoMatchTargetStatus::Unsupported,
            TargetExplanationStatus::Unresolved => NoMatchTargetStatus::Unresolved,
        },
    });
    let base = DocumentBase {
        input,
        semantic,
        semantic_program,
        subject: subject_identity,
        execution_mode,
        target,
        limits,
    };

    if let Some(target) = &base.target {
        let unavailable = match target.status {
            NoMatchTargetStatus::Unsupported => Some(NoMatchReasonCode::TargetUnsupported),
            NoMatchTargetStatus::Unresolved => Some(NoMatchReasonCode::TargetUnresolved),
            NoMatchTargetStatus::Native | NoMatchTargetStatus::EquivalentRewrite => None,
        };
        if let Some(reason) = unavailable {
            return Ok(base.document(
                NoMatchOutcome::Unavailable,
                NoMatchExplanationDisposition::Unavailable,
                vec![base.public_finding(
                    Failure {
                        reason_code: reason,
                        node_id: None,
                        subject_location: None,
                        context: None,
                        ambiguous: false,
                    },
                    0,
                    NoMatchConfidence::Unavailable,
                    NoMatchEvidenceClass::TargetPlan,
                )?],
                empty_work(),
            ));
        }
    }

    let mut preflight = Budget::new(limits);
    let subject_limit = if subject.len() > limits.max_subject_utf8_bytes {
        preflight
            .reached_limits
            .insert(NoMatchLimitKind::SubjectUtf8Bytes);
        Some((
            NoMatchReasonCode::SubjectUtf8LimitReached,
            NoMatchLimitKind::SubjectUtf8Bytes,
        ))
    } else if scalar_count > limits.max_subject_unicode_scalars {
        preflight
            .reached_limits
            .insert(NoMatchLimitKind::SubjectUnicodeScalars);
        Some((
            NoMatchReasonCode::SubjectScalarLimitReached,
            NoMatchLimitKind::SubjectUnicodeScalars,
        ))
    } else if limits.max_elapsed_milliseconds == 0 {
        preflight.reached_limits.insert(NoMatchLimitKind::Elapsed);
        Some((
            NoMatchReasonCode::ElapsedLimitReached,
            NoMatchLimitKind::Elapsed,
        ))
    } else {
        None
    };
    if let Some((reason, _)) = subject_limit {
        return Ok(base.unknown_limit(reason, preflight.report()));
    }

    let mut evaluator = Evaluator::new(input, subject, limits);
    let evaluation = match evaluator.run() {
        Ok(value) => value,
        Err(limit) => {
            let reason = limit_reason(limit);
            return Ok(base.unknown_limit(reason, evaluator.budget.report()));
        }
    };
    let work = evaluator.budget.report();
    match evaluation {
        Evaluation::Matched => Ok(base.document(
            NoMatchOutcome::Matched,
            NoMatchExplanationDisposition::NotApplicable,
            Vec::new(),
            work,
        )),
        Evaluation::Unknown(failure) => Ok(base.document(
            NoMatchOutcome::Unknown,
            NoMatchExplanationDisposition::Unknown,
            vec![base.public_finding(
                failure,
                0,
                NoMatchConfidence::Unknown,
                NoMatchEvidenceClass::Uncertainty,
            )?],
            work,
        )),
        Evaluation::NoMatch(failures) => {
            if failures.is_empty() {
                let failure = Failure {
                    reason_code: NoMatchReasonCode::SemanticEvaluationUnavailable,
                    node_id: Some(input.root.node_id().clone()),
                    subject_location: None,
                    context: None,
                    ambiguous: false,
                };
                return Ok(base.document(
                    NoMatchOutcome::Unknown,
                    NoMatchExplanationDisposition::Unknown,
                    vec![base.public_finding(
                        failure,
                        0,
                        NoMatchConfidence::Unknown,
                        NoMatchEvidenceClass::Uncertainty,
                    )?],
                    work,
                ));
            }
            let likely = failures.len() > 1 || failures.iter().any(|failure| failure.ambiguous);
            let (disposition, confidence) = if likely {
                (
                    NoMatchExplanationDisposition::Likely,
                    NoMatchConfidence::Likely,
                )
            } else {
                (
                    NoMatchExplanationDisposition::Proven,
                    NoMatchConfidence::Proven,
                )
            };
            let findings = failures
                .into_iter()
                .enumerate()
                .map(|(ordinal, failure)| {
                    base.public_finding(
                        failure,
                        ordinal,
                        confidence,
                        NoMatchEvidenceClass::CanonicalEvaluation,
                    )
                })
                .collect::<Result<Vec<_>, _>>()?;
            Ok(base.document(NoMatchOutcome::NoMatch, disposition, findings, work))
        }
    }
}

struct DocumentBase<'a> {
    input: &'a SemanticProgram,
    semantic: &'a ExplanationDocument,
    semantic_program: Sha256Digest,
    subject: NoMatchSubjectIdentity,
    execution_mode: NoMatchExecutionMode,
    target: Option<NoMatchTargetContext>,
    limits: NoMatchLimits,
}

impl DocumentBase<'_> {
    fn document(
        &self,
        outcome: NoMatchOutcome,
        disposition: NoMatchExplanationDisposition,
        findings: Vec<NoMatchFinding>,
        work: NoMatchWorkReport,
    ) -> NoMatchExplanationDocument {
        NoMatchExplanationDocument {
            model_version: NoMatchExplanationModelVersion::V1_0_0,
            contract_version: self.input.contract_version,
            specification_version: self.input.specification_version.clone(),
            semantic_program: self.semantic_program.clone(),
            semantic_explanation: NoMatchSemanticExplanationLink {
                model_version: self.semantic.model_version,
                semantic_program: self.semantic_program.clone(),
            },
            execution_mode: self.execution_mode,
            subject: self.subject.clone(),
            target: self.target.clone(),
            outcome,
            explanation_disposition: disposition,
            findings,
            limits: self.limits,
            work,
        }
    }

    fn unknown_limit(
        &self,
        reason: NoMatchReasonCode,
        work: NoMatchWorkReport,
    ) -> NoMatchExplanationDocument {
        self.document(
            NoMatchOutcome::Unknown,
            NoMatchExplanationDisposition::Unknown,
            vec![NoMatchFinding {
                ordinal: 0,
                reason_code: reason,
                confidence: NoMatchConfidence::Unknown,
                evidence_class: NoMatchEvidenceClass::Uncertainty,
                node_id: None,
                source: None,
                subject_location: None,
                context: None,
            }],
            work,
        )
    }

    fn public_finding(
        &self,
        failure: Failure,
        ordinal: usize,
        confidence: NoMatchConfidence,
        evidence_class: NoMatchEvidenceClass,
    ) -> Result<NoMatchFinding, NoMatchExplanationErrors> {
        let source = failure
            .node_id
            .as_ref()
            .map(|node_id| {
                self.semantic
                    .nodes
                    .iter()
                    .find(|node| &node.node_id == node_id)
                    .map(|node| node.source.clone())
                    .ok_or_else(|| {
                        NoMatchExplanationErrors::single(
                            NoMatchExplanationErrorCode::MismatchedExplanation,
                            "$.semantic_explanation.nodes",
                            "finding node is absent from the semantic explanation",
                        )
                    })
            })
            .transpose()?;
        Ok(NoMatchFinding {
            ordinal,
            reason_code: failure.reason_code,
            confidence,
            evidence_class,
            node_id: failure.node_id,
            source,
            subject_location: failure.subject_location,
            context: failure.context.map(|value| value.public()),
        })
    }
}

fn validate_inputs(
    input: &SemanticProgram,
    semantic: &ExplanationDocument,
    subject: &str,
    limits: NoMatchLimits,
) -> Result<(), NoMatchExplanationErrors> {
    input
        .validate()
        .map_err(|errors| NoMatchExplanationErrors {
            errors: errors
                .errors
                .into_iter()
                .map(|error| NoMatchExplanationError {
                    code: NoMatchExplanationErrorCode::InvalidProgram,
                    path: error.path,
                    message: error.message,
                })
                .collect(),
        })?;
    validate_limits(limits)?;
    if subject.len() > MAX_NO_MATCH_SUBJECT_UTF8_BYTES {
        return Err(NoMatchExplanationErrors::single(
            NoMatchExplanationErrorCode::SubjectExceedsHardLimit,
            "$.subject",
            format!(
                "subject exceeds absolute UTF-8 ceiling of {MAX_NO_MATCH_SUBJECT_UTF8_BYTES} bytes"
            ),
        ));
    }
    if subject
        .chars()
        .take(MAX_NO_MATCH_SUBJECT_UNICODE_SCALARS + 1)
        .count()
        > MAX_NO_MATCH_SUBJECT_UNICODE_SCALARS
    {
        return Err(NoMatchExplanationErrors::single(
            NoMatchExplanationErrorCode::SubjectExceedsHardLimit,
            "$.subject",
            format!(
                "subject exceeds absolute Unicode-scalar ceiling of {MAX_NO_MATCH_SUBJECT_UNICODE_SCALARS} scalars"
            ),
        ));
    }
    let digest = Sha256Digest::from_bytes(canonical_sha256(input).map_err(|error| {
        NoMatchExplanationErrors::single(
            NoMatchExplanationErrorCode::SerializationInvariant,
            "$.semantic_program",
            format!("semantic program fingerprint could not be derived: {error}"),
        )
    })?);
    if semantic.contract_version != input.contract_version
        || semantic.specification_version != input.specification_version
        || semantic.semantic_program != digest
        || semantic.program.root_node_id != *input.root.node_id()
    {
        return Err(NoMatchExplanationErrors::single(
            NoMatchExplanationErrorCode::MismatchedExplanation,
            "$.semantic_explanation",
            "semantic explanation identity does not correspond to the evaluated program",
        ));
    }
    let explained_nodes = semantic
        .nodes
        .iter()
        .map(|node| node.node_id.clone())
        .collect::<BTreeSet<_>>();
    if explained_nodes != input.node_ids() {
        return Err(NoMatchExplanationErrors::single(
            NoMatchExplanationErrorCode::MismatchedExplanation,
            "$.semantic_explanation.nodes",
            "semantic explanation node coverage does not equal the evaluated program",
        ));
    }
    Ok(())
}

fn validate_limits(limits: NoMatchLimits) -> Result<(), NoMatchExplanationErrors> {
    let invalid = limits.max_subject_utf8_bytes == 0
        || limits.max_subject_utf8_bytes > MAX_NO_MATCH_SUBJECT_UTF8_BYTES
        || limits.max_subject_unicode_scalars == 0
        || limits.max_subject_unicode_scalars > MAX_NO_MATCH_SUBJECT_UNICODE_SCALARS
        || limits.max_steps == 0
        || limits.max_steps > MAX_NO_MATCH_STEPS
        || limits.max_depth == 0
        || limits.max_depth > MAX_NO_MATCH_DEPTH
        || limits.max_branch_expansions == 0
        || limits.max_branch_expansions > MAX_NO_MATCH_BRANCH_EXPANSIONS
        || limits.max_findings == 0
        || limits.max_findings > MAX_NO_MATCH_FINDINGS
        || limits.max_elapsed_milliseconds > MAX_NO_MATCH_ELAPSED_MILLISECONDS;
    if invalid {
        return Err(NoMatchExplanationErrors::single(
            NoMatchExplanationErrorCode::InvalidLimits,
            "$.limits",
            "no-match limits must be nonzero except elapsed and no greater than contract ceilings",
        ));
    }
    Ok(())
}

fn canonical_failures(failures: Vec<Failure>) -> Vec<Failure> {
    let mut seen = BTreeSet::new();
    let mut canonical = Vec::new();
    for failure in failures {
        let key = (failure.reason_code, failure.node_id.clone());
        if seen.insert(key) {
            canonical.push(failure);
        }
    }
    canonical
}

fn deduplicate_states(states: Vec<EvalState>) -> Vec<EvalState> {
    states
        .into_iter()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

fn empty_work() -> NoMatchWorkReport {
    NoMatchWorkReport {
        candidate_starts: 0,
        steps: 0,
        maximum_depth: 0,
        branch_expansions: 0,
        findings_considered: 0,
        reached_limits: Vec::new(),
    }
}

fn limit_reason(limit: NoMatchLimitKind) -> NoMatchReasonCode {
    match limit {
        NoMatchLimitKind::SubjectUtf8Bytes => NoMatchReasonCode::SubjectUtf8LimitReached,
        NoMatchLimitKind::SubjectUnicodeScalars => NoMatchReasonCode::SubjectScalarLimitReached,
        NoMatchLimitKind::Steps => NoMatchReasonCode::StepLimitReached,
        NoMatchLimitKind::Depth => NoMatchReasonCode::DepthLimitReached,
        NoMatchLimitKind::Branches => NoMatchReasonCode::BranchLimitReached,
        NoMatchLimitKind::Findings => NoMatchReasonCode::FindingLimitReached,
        NoMatchLimitKind::Elapsed => NoMatchReasonCode::ElapsedLimitReached,
    }
}

fn position_reason(position: PositionKind) -> NoMatchReasonCode {
    match position {
        PositionKind::InputStart => NoMatchReasonCode::InputStartAssertionFailed,
        PositionKind::InputEnd => NoMatchReasonCode::InputEndAssertionFailed,
        PositionKind::LineStart => NoMatchReasonCode::LineStartAssertionFailed,
        PositionKind::LineEnd => NoMatchReasonCode::LineEndAssertionFailed,
        PositionKind::WordBoundary => NoMatchReasonCode::WordBoundaryAssertionFailed,
        PositionKind::NotWordBoundary => NoMatchReasonCode::NotWordBoundaryAssertionFailed,
        PositionKind::EndBeforeFinalLineTerminator => {
            NoMatchReasonCode::FinalLineTerminatorAssertionFailed
        }
    }
}

fn ascii_word(value: char) -> bool {
    value.is_ascii_alphanumeric() || value == '_'
}

fn contains_capture_state(node: &Node) -> bool {
    match node {
        Node::Capture { .. } | Node::Backreference { .. } => true,
        Node::Sequence { items, .. } => items.iter().any(contains_capture_state),
        Node::Alternation { branches, .. } => branches.iter().any(contains_capture_state),
        Node::Repeat { body, .. } | Node::Lookaround { body, .. } | Node::Atomic { body, .. } => {
            contains_capture_state(body)
        }
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. } => false,
    }
}
