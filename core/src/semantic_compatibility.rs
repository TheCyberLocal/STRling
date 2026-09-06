//! Canonical semantic predicates used by capability evaluation and target lowering.
//!
//! Target profiles describe native engine behavior. These helpers compare that
//! behavior with the current canonical semantic contract without inferring facts
//! from engine names or serialized regex text.

use crate::semantic::{
    AssertionPolarity, CharacterSetMember, Node, RepetitionMaximum, SemanticProgram,
};
use crate::source::CaptureId;
use crate::target::{
    BackreferenceUnsetBehavior, CaptureResetBehavior, CaseFoldingMode, CharacterSetUniverse,
    LineTerminator, LineTerminatorSequencePolicy, MatchingUnit, SemanticAlgorithmDefinition,
    SemanticSetDefinition, TargetLimitBound, TargetLimitPrediction, TargetLimitScope,
    TargetProfile,
};

/// Conservative compiler envelope for a bounded repetition when PCRE2's
/// compiled-pattern size is governed as unknown and artifact dependent.
///
/// This is deliberately below the observed one-literal failure boundary. It is
/// a refusal threshold, not a claim about a universal engine syntax limit.
pub(crate) const CONSERVATIVE_UNKNOWN_COMPILED_PATTERN_REPETITION_ENVELOPE: u64 = 4_096;

pub(crate) fn has_canonical_matching_unit(target: &TargetProfile) -> bool {
    algorithm(target, "matching_unit").is_some_and(|definition| {
        matches!(
            definition,
            SemanticAlgorithmDefinition::MatchingUnit {
                unit: MatchingUnit::UnicodeCodePoint
            }
        )
    })
}

pub(crate) fn native_wildcard_is_canonical(target: &TargetProfile) -> bool {
    set(target, "wildcard_exclusions").is_some_and(|definition| {
        let SemanticSetDefinition::CharacterSet {
            universe,
            scalars,
            ranges,
            unicode_general_categories,
        } = definition
        else {
            return false;
        };
        *universe == CharacterSetUniverse::UnicodeScalar
            && scalars.iter().map(String::as_str).eq([
                "U+000A", "U+000B", "U+000C", "U+000D", "U+0085", "U+2028", "U+2029",
            ])
            && ranges.is_empty()
            && unicode_general_categories.is_empty()
    })
}

pub(crate) fn native_line_anchors_are_canonical(target: &TargetProfile) -> bool {
    set(target, "line_terminators").is_some_and(|definition| {
        let SemanticSetDefinition::LineTerminatorSet {
            members,
            sequence_policy,
        } = definition
        else {
            return false;
        };
        members.as_slice()
            == [
                LineTerminator::Lf,
                LineTerminator::Vt,
                LineTerminator::Ff,
                LineTerminator::Cr,
                LineTerminator::Crlf,
                LineTerminator::Nel,
                LineTerminator::Ls,
                LineTerminator::Ps,
            ]
            && *sequence_policy == LineTerminatorSequencePolicy::AtomicLongest
    })
}

pub(crate) fn native_word_is_canonical(target: &TargetProfile) -> bool {
    set(target, "word_characters").is_some_and(|definition| {
        let SemanticSetDefinition::CharacterSet {
            universe,
            scalars,
            ranges,
            unicode_general_categories,
        } = definition
        else {
            return false;
        };
        *universe == CharacterSetUniverse::UnicodeScalar
            && scalars.is_empty()
            && ranges.is_empty()
            && unicode_general_categories
                .iter()
                .map(|category| category.as_str())
                .eq(["L", "Mn", "N", "Pc"])
    })
}

pub(crate) fn unset_backreference_is_canonical(target: &TargetProfile) -> bool {
    algorithm(target, "backreference_unset").is_some_and(|definition| {
        matches!(
            definition,
            SemanticAlgorithmDefinition::BackreferenceUnset {
                behavior: BackreferenceUnsetBehavior::Fail
            }
        )
    })
}

pub(crate) fn repeated_capture_is_canonical(target: &TargetProfile) -> bool {
    algorithm(target, "capture_reset_on_iteration").is_some_and(|definition| {
        matches!(
            definition,
            SemanticAlgorithmDefinition::CaptureResetOnIteration {
                behavior: CaptureResetBehavior::Retain
            }
        )
    })
}

pub(crate) fn has_unknown_compiled_pattern_limit(target: &TargetProfile) -> bool {
    target.target_limits.iter().any(|limit| {
        limit.scope == TargetLimitScope::CompiledPattern
            && limit.prediction == TargetLimitPrediction::ArtifactAndConfigurationDependent
            && matches!(limit.bound, TargetLimitBound::Unknown)
    })
}

/// True when this exact program can expose a target folding relation that is
/// not part of canonical simple Unicode folding.
pub(crate) fn case_folding_difference_is_reachable(
    input: &SemanticProgram,
    target: &TargetProfile,
) -> bool {
    let Some(definition) = algorithm(target, "case_folding") else {
        return true;
    };
    let SemanticAlgorithmDefinition::CaseFolding {
        mode,
        additional_equivalence_classes,
        ..
    } = definition
    else {
        return true;
    };

    match mode {
        CaseFoldingMode::SimpleUnicode => false,
        CaseFoldingMode::Ascii => [
            '\u{004B}', '\u{006B}', '\u{0053}', '\u{0073}', '\u{017F}', '\u{212A}',
        ]
        .into_iter()
        .any(|scalar| program_has_case_atom(&input.root, scalar)),
        CaseFoldingMode::EngineSpecific => additional_equivalence_classes.iter().any(|class| {
            let parsed: Vec<char> = class
                .iter()
                .filter_map(|value| parse_profile_scalar(value))
                .collect();
            let canonical = canonical_edge_class(&parsed);
            parsed != canonical
                && parsed
                    .iter()
                    .copied()
                    .any(|scalar| program_has_case_atom(&input.root, scalar))
        }),
        CaseFoldingMode::FullUnicode => program_contains_case_atom(&input.root),
    }
}

pub(crate) fn capture_may_be_unset(input: &SemanticProgram, capture_id: &CaptureId) -> bool {
    capture_path(&input.root, capture_id)
        .is_some_and(|path| path.iter().any(CaptureAncestor::may_skip_capture))
}

pub(crate) fn repeated_capture_reset_is_observable(
    input: &SemanticProgram,
    capture_id: &CaptureId,
) -> bool {
    let Some(path) = capture_path(&input.root, capture_id) else {
        return true;
    };
    path.iter().enumerate().any(|(index, ancestor)| {
        ancestor.repeats_more_than_once()
            && path[index + 1..]
                .iter()
                .any(CaptureAncestor::may_skip_capture)
    })
}

#[derive(Clone, Copy)]
enum CaptureAncestor {
    Alternation,
    Repeat {
        minimum: u64,
        maximum: RepetitionMaximum,
    },
    NegativeLookaround,
    Structural,
}

impl CaptureAncestor {
    fn may_skip_capture(&self) -> bool {
        matches!(
            self,
            Self::Alternation | Self::Repeat { minimum: 0, .. } | Self::NegativeLookaround
        )
    }

    fn repeats_more_than_once(&self) -> bool {
        matches!(
            self,
            Self::Repeat {
                maximum: RepetitionMaximum::Unbounded,
                ..
            } | Self::Repeat {
                maximum: RepetitionMaximum::Bounded(2..),
                ..
            }
        )
    }
}

fn capture_path<'a>(root: &'a Node, capture_id: &CaptureId) -> Option<Vec<CaptureAncestor>> {
    fn visit(node: &Node, capture_id: &CaptureId, path: &mut Vec<CaptureAncestor>) -> bool {
        match node {
            Node::Capture {
                capture_id: candidate,
                body,
                ..
            } => {
                if candidate == capture_id {
                    return true;
                }
                path.push(CaptureAncestor::Structural);
                if visit(body, capture_id, path) {
                    return true;
                }
                path.pop();
            }
            Node::Sequence { items, .. } => {
                path.push(CaptureAncestor::Structural);
                for item in items {
                    if visit(item, capture_id, path) {
                        return true;
                    }
                }
                path.pop();
            }
            Node::Alternation { branches, .. } => {
                path.push(CaptureAncestor::Alternation);
                for branch in branches {
                    if visit(branch, capture_id, path) {
                        return true;
                    }
                }
                path.pop();
            }
            Node::Repeat { body, min, max, .. } => {
                path.push(CaptureAncestor::Repeat {
                    minimum: *min,
                    maximum: *max,
                });
                if visit(body, capture_id, path) {
                    return true;
                }
                path.pop();
            }
            Node::Lookaround { body, polarity, .. } => {
                path.push(if *polarity == AssertionPolarity::Negative {
                    CaptureAncestor::NegativeLookaround
                } else {
                    CaptureAncestor::Structural
                });
                if visit(body, capture_id, path) {
                    return true;
                }
                path.pop();
            }
            Node::Atomic { body, .. } => {
                path.push(CaptureAncestor::Structural);
                if visit(body, capture_id, path) {
                    return true;
                }
                path.pop();
            }
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
        false
    }

    let mut path = Vec::new();
    visit(root, capture_id, &mut path).then_some(path)
}

fn program_contains_case_atom(node: &Node) -> bool {
    match node {
        Node::Literal { text, .. } => text.chars().any(char::is_alphabetic),
        Node::CharacterSet { members, .. } => !members.is_empty(),
        Node::Sequence { items, .. } => items.iter().any(program_contains_case_atom),
        Node::Alternation { branches, .. } => branches.iter().any(program_contains_case_atom),
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => program_contains_case_atom(body),
        Node::Empty { .. }
        | Node::Wildcard { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => false,
    }
}

fn program_has_case_atom(node: &Node, scalar: char) -> bool {
    match node {
        Node::Literal { text, .. } => text.chars().any(|value| value == scalar),
        Node::CharacterSet { members, .. } => members.iter().any(|member| match member {
            CharacterSetMember::Literal { value } => value.get() == scalar,
            CharacterSetMember::Range { start, end } => {
                start.get() <= scalar && scalar <= end.get()
            }
            CharacterSetMember::Builtin { .. } | CharacterSetMember::UnicodeProperty { .. } => {
                false
            }
        }),
        Node::Sequence { items, .. } => items
            .iter()
            .any(|child| program_has_case_atom(child, scalar)),
        Node::Alternation { branches, .. } => branches
            .iter()
            .any(|child| program_has_case_atom(child, scalar)),
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => program_has_case_atom(body, scalar),
        Node::Empty { .. }
        | Node::Wildcard { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => false,
    }
}

fn canonical_edge_class(values: &[char]) -> Vec<char> {
    let candidates: &[&[char]] = &[
        &['\u{0049}', '\u{0069}'],
        &['\u{004B}', '\u{006B}', '\u{212A}'],
        &['\u{0053}', '\u{0073}', '\u{017F}'],
        &['\u{03A3}', '\u{03C2}', '\u{03C3}'],
    ];
    candidates
        .iter()
        .find(|candidate| values.iter().any(|value| candidate.contains(value)))
        .map_or_else(Vec::new, |candidate| candidate.to_vec())
}

fn parse_profile_scalar(value: &str) -> Option<char> {
    let scalar = u32::from_str_radix(value.strip_prefix("U+")?, 16).ok()?;
    char::from_u32(scalar)
}

fn set<'a>(target: &'a TargetProfile, id: &str) -> Option<&'a SemanticSetDefinition> {
    target
        .semantic_sets
        .iter()
        .find(|set| set.set_id.as_str() == id)
        .map(|set| &set.definition)
}

fn algorithm<'a>(target: &'a TargetProfile, id: &str) -> Option<&'a SemanticAlgorithmDefinition> {
    target
        .semantic_algorithms
        .iter()
        .find(|algorithm| algorithm.algorithm_id.as_str() == id)
        .map(|algorithm| &algorithm.definition)
}
