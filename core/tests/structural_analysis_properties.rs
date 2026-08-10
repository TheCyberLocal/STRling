use std::collections::BTreeSet;

use serde_json::{json, Value};
use strling_kernel::normalization::normalize;
use strling_kernel::semantic::{
    CaseMatching, CharacterSetMember, Node, SemanticProgram, UnicodeScalar,
};
use strling_kernel::semantic_analysis::{analyze, MaximumConsumption, SemanticFacts};
use strling_kernel::source::{NodeId, SpecificationVersion};
use strling_kernel::structural_analysis::{
    analyze_structure, LeadingConsumption, LeadingTerm, LengthClassification, OverlapRelation,
    ProgressClassification, StructuralAnalysisErrorCode, StructuralFacts,
};

const SEEDS: [u64; 4] = [
    0x5354_5255_4354_5552,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const CASES_PER_SEED: usize = 96;
const MALFORMED_CASES: usize = 64;

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("generated program must deserialize")
}

struct Generator {
    state: u64,
    next_node: u64,
    next_capture: u64,
}

impl Generator {
    fn new(seed: u64) -> Self {
        Self {
            state: seed,
            next_node: 0,
            next_capture: 0,
        }
    }

    fn next(&mut self) -> u64 {
        self.state = self
            .state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        self.state
    }

    fn pick(&mut self, count: usize) -> usize {
        (self.next() % count as u64) as usize
    }

    fn boolean(&mut self) -> bool {
        self.pick(2) == 1
    }

    fn node_id(&mut self) -> String {
        let node_id = format!("node:structure.generated.{}", self.next_node);
        self.next_node += 1;
        node_id
    }

    fn capture_identity(&mut self) -> (String, String) {
        let capture = self.next_capture;
        self.next_capture += 1;
        (
            format!("capture:structure.generated.{capture}"),
            format!("structure_generated_{capture}"),
        )
    }

    fn semantic_program(&mut self) -> SemanticProgram {
        let root = self.node_id();
        let capture = self.node_id();
        let reference = self.node_id();
        let capture_body = self.node(3);
        let generated = self.node(4);
        program(json!({
            "node_id": root,
            "kind": "sequence",
            "items": [
                {
                    "node_id": capture,
                    "kind": "capture",
                    "capture_id": "capture:structure.stable",
                    "name": "structure_stable",
                    "body": capture_body
                },
                {
                    "node_id": reference,
                    "kind": "backreference",
                    "capture_id": "capture:structure.stable"
                },
                generated
            ]
        }))
    }

    fn node(&mut self, depth: usize) -> Value {
        let choice = if depth == 0 {
            self.pick(6)
        } else {
            self.pick(12)
        };
        let node_id = self.node_id();
        match choice {
            0 => json!({"node_id": node_id, "kind": "empty"}),
            1 => {
                let children = 1 + self.pick(4);
                let items: Vec<_> = (0..children)
                    .map(|_| self.node(depth.saturating_sub(1)))
                    .collect();
                json!({"node_id": node_id, "kind": "sequence", "items": items})
            }
            2 => {
                let children = 1 + self.pick(4);
                let branches: Vec<_> = (0..children)
                    .map(|_| self.node(depth.saturating_sub(1)))
                    .collect();
                json!({"node_id": node_id, "kind": "alternation", "branches": branches})
            }
            3 => {
                let unit = ["a", "A", "é", "中", "😀"][self.pick(5)];
                json!({
                    "node_id": node_id,
                    "kind": "literal",
                    "text": unit.repeat(1 + self.pick(3))
                })
            }
            4 => json!({
                "node_id": node_id,
                "kind": "wildcard",
                "line_terminators": if self.boolean() { "include" } else { "exclude" }
            }),
            5 => self.character_set(node_id),
            6 => {
                let minimum = self.pick(4) as u64;
                let maximum = if self.boolean() {
                    Value::Null
                } else {
                    json!(minimum + self.pick(4) as u64)
                };
                let mode = ["greedy", "lazy", "possessive"][self.pick(3)];
                let body = self.node(depth - 1);
                json!({
                    "node_id": node_id,
                    "kind": "repeat",
                    "body": body,
                    "min": minimum,
                    "max": maximum,
                    "mode": mode
                })
            }
            7 => {
                let positions = [
                    "input_start",
                    "input_end",
                    "line_start",
                    "line_end",
                    "word_boundary",
                    "not_word_boundary",
                    "end_before_final_line_terminator",
                ];
                json!({
                    "node_id": node_id,
                    "kind": "position",
                    "position": positions[self.pick(positions.len())]
                })
            }
            8 => {
                let (capture_id, name) = self.capture_identity();
                let body = self.node(depth - 1);
                json!({
                    "node_id": node_id,
                    "kind": "capture",
                    "capture_id": capture_id,
                    "name": name,
                    "body": body
                })
            }
            9 => json!({
                "node_id": node_id,
                "kind": "backreference",
                "capture_id": "capture:structure.stable"
            }),
            10 => {
                let body = self.node(depth - 1);
                json!({
                    "node_id": node_id,
                    "kind": "lookaround",
                    "direction": if self.boolean() { "ahead" } else { "behind" },
                    "polarity": if self.boolean() { "positive" } else { "negative" },
                    "body": body
                })
            }
            11 => {
                let body = self.node(depth - 1);
                json!({"node_id": node_id, "kind": "atomic", "body": body})
            }
            _ => unreachable!("generator choice is bounded"),
        }
    }

    fn character_set(&mut self, node_id: String) -> Value {
        let negated = self.boolean();
        if self.boolean() {
            let start = ["a", "m", "é"][self.pick(3)];
            let end = match start {
                "a" => "f",
                "m" => "z",
                "é" => "ê",
                _ => unreachable!("start choice is bounded"),
            };
            json!({
                "node_id": node_id,
                "kind": "character_set",
                "negated": negated,
                "members": [
                    {"kind": "literal", "value": (["a", "z", "中"][self.pick(3)])},
                    {"kind": "range", "start": start, "end": end}
                ]
            })
        } else {
            json!({
                "node_id": node_id,
                "kind": "character_set",
                "negated": negated,
                "members": [{
                    "kind": "builtin",
                    "name": (["digit", "word", "whitespace"][self.pick(3)]),
                    "domain": if self.boolean() { "ascii" } else { "unicode" },
                    "negated": self.boolean()
                }]
            })
        }
    }
}
#[test]
fn generated_normalized_programs_certify_structural_properties() {
    let mut covered_kinds = BTreeSet::new();
    let mut generated_cases = 0;

    for seed in SEEDS {
        let mut generator = Generator::new(seed);
        for case in 0..CASES_PER_SEED {
            let candidate = generator.semantic_program();
            let semantic = normalize(&candidate).unwrap_or_else(|errors| {
                panic!("seed {seed:#x} case {case} failed normalization: {errors:?}")
            });
            collect_kinds(&semantic.root, &mut covered_kinds);
            let foundational = analyze(&semantic).unwrap_or_else(|errors| {
                panic!("seed {seed:#x} case {case} failed analysis: {errors:?}")
            });
            let semantic_before = semantic.clone();
            let foundational_before = foundational.clone();

            let first = analyze_structure(&semantic, &foundational).unwrap_or_else(|errors| {
                panic!("seed {seed:#x} case {case} failed structure: {errors:?}")
            });
            let second =
                analyze_structure(&semantic, &foundational).expect("repeat analysis must succeed");

            assert_eq!(
                first, second,
                "determinism failed for seed {seed:#x} case {case}"
            );
            assert_eq!(semantic, semantic_before, "Semantic IR was mutated");
            assert_eq!(
                foundational, foundational_before,
                "foundational facts were mutated"
            );
            assert_complete_and_consistent(&semantic, &foundational, &first);
            generated_cases += 1;
        }
    }

    assert_eq!(generated_cases, SEEDS.len() * CASES_PER_SEED);
    assert_eq!(
        covered_kinds,
        BTreeSet::from([
            "alternation",
            "atomic",
            "backreference",
            "capture",
            "character_set",
            "empty",
            "literal",
            "lookaround",
            "position",
            "repeat",
            "sequence",
            "wildcard",
        ])
    );
}

fn assert_complete_and_consistent(
    semantic: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
) {
    assert_eq!(structural.len(), semantic.node_ids().len());
    for node_id in semantic.node_ids() {
        let structural_node = structural
            .get(&node_id)
            .expect("every node needs structural facts");
        let foundational_node = foundational
            .get(&node_id)
            .expect("every node needs foundational facts");
        assert!(!structural_node.leading_consumption.is_empty());

        match structural_node.length {
            LengthClassification::Fixed(length) => {
                assert_eq!(foundational_node.minimum_consumption, length);
                assert_eq!(
                    foundational_node.maximum_consumption,
                    MaximumConsumption::Finite(length)
                );
            }
            LengthClassification::FiniteVariable => {
                let MaximumConsumption::Finite(maximum) = foundational_node.maximum_consumption
                else {
                    panic!("finite-variable length needs a finite maximum");
                };
                assert!(foundational_node.minimum_consumption < maximum);
            }
            LengthClassification::Unbounded | LengthClassification::Indeterminate => {
                assert_eq!(
                    foundational_node.maximum_consumption,
                    MaximumConsumption::Unbounded
                );
            }
        }

        if let Some(repetition) = &structural_node.repetition {
            let body = foundational
                .get(&repetition.body_node_id)
                .expect("repetition body needs foundational facts");
            if repetition.operand_progress == ProgressClassification::AlwaysConsuming {
                assert!(body.minimum_consumption > 0);
            }
        }

        for relationship in &structural_node.alternation_branch_overlaps {
            if relationship.relation == OverlapRelation::Disjoint {
                assert_independently_disjoint(
                    structural,
                    &relationship.left_node_id,
                    &relationship.right_node_id,
                    semantic.case_matching,
                );
            }
        }
        for relationship in &structural_node.repetition_follow_overlaps {
            if relationship.relation == OverlapRelation::Disjoint {
                assert_independently_disjoint(
                    structural,
                    &relationship.operand_node_id,
                    &relationship.following_node_id,
                    semantic.case_matching,
                );
            }
        }
    }
}

fn assert_independently_disjoint(
    structural: &StructuralFacts,
    left: &NodeId,
    right: &NodeId,
    case_matching: CaseMatching,
) {
    let left = &structural
        .get(left)
        .expect("left relationship node needs facts")
        .leading_consumption;
    let right = &structural
        .get(right)
        .expect("right relationship node needs facts")
        .leading_consumption;
    assert_eq!(
        independent_disjoint(left, right, case_matching),
        Some(true),
        "every Disjoint result needs an independent exact proof"
    );
}

fn independent_disjoint(
    left: &LeadingConsumption,
    right: &LeadingConsumption,
    case_matching: CaseMatching,
) -> Option<bool> {
    let mut all_disjoint = true;
    for left_term in left.iter() {
        for right_term in right.iter() {
            match independent_term_disjoint(left_term, right_term, case_matching) {
                Some(true) => {}
                Some(false) => all_disjoint = false,
                None => return None,
            }
        }
    }
    Some(all_disjoint)
}
fn independent_term_disjoint(
    left: &LeadingTerm,
    right: &LeadingTerm,
    case_matching: CaseMatching,
) -> Option<bool> {
    match (left, right) {
        (LeadingTerm::Empty, LeadingTerm::Empty) => Some(false),
        (LeadingTerm::Unknown(_), _) | (_, LeadingTerm::Unknown(_)) => None,
        (LeadingTerm::Empty, _) | (_, LeadingTerm::Empty) => Some(true),
        (LeadingTerm::Scalar(left), LeadingTerm::Scalar(right)) => {
            if left == right {
                Some(false)
            } else if case_matching == CaseMatching::Sensitive {
                Some(true)
            } else {
                None
            }
        }
        (LeadingTerm::Scalar(value), LeadingTerm::CharacterSet { negated, members })
        | (LeadingTerm::CharacterSet { negated, members }, LeadingTerm::Scalar(value)) => {
            independent_scalar_set(*value, *negated, members, case_matching)
        }
        (
            LeadingTerm::CharacterSet {
                negated: left_negated,
                members: left_members,
            },
            LeadingTerm::CharacterSet {
                negated: right_negated,
                members: right_members,
            },
        ) => independent_set_set(
            *left_negated,
            left_members,
            *right_negated,
            right_members,
            case_matching,
        ),
        (LeadingTerm::Wildcard { .. }, LeadingTerm::Wildcard { .. }) => Some(false),
        (LeadingTerm::Wildcard { line_terminators }, LeadingTerm::Scalar(_))
        | (LeadingTerm::Scalar(_), LeadingTerm::Wildcard { line_terminators })
            if *line_terminators == strling_kernel::semantic::LineTerminators::Include =>
        {
            Some(false)
        }
        (
            LeadingTerm::Wildcard {
                line_terminators: strling_kernel::semantic::LineTerminators::Include,
            },
            LeadingTerm::CharacterSet {
                negated: false,
                members,
            },
        )
        | (
            LeadingTerm::CharacterSet {
                negated: false,
                members,
            },
            LeadingTerm::Wildcard {
                line_terminators: strling_kernel::semantic::LineTerminators::Include,
            },
        ) if exact_intervals(members).is_some() => Some(false),
        (LeadingTerm::Wildcard { .. }, _) | (_, LeadingTerm::Wildcard { .. }) => None,
    }
}

fn independent_scalar_set(
    value: UnicodeScalar,
    negated: bool,
    members: &[CharacterSetMember],
    case_matching: CaseMatching,
) -> Option<bool> {
    let (intervals, symbolic) = intervals_and_symbolic(members);
    let contained = contains(&intervals, u32::from(value.get()));
    if !negated && contained {
        return Some(false);
    }
    if negated && contained {
        return Some(true);
    }
    if symbolic || case_matching == CaseMatching::Insensitive {
        None
    } else {
        Some(!negated)
    }
}

fn independent_set_set(
    left_negated: bool,
    left_members: &[CharacterSetMember],
    right_negated: bool,
    right_members: &[CharacterSetMember],
    case_matching: CaseMatching,
) -> Option<bool> {
    let (left, left_symbolic) = intervals_and_symbolic(left_members);
    let (right, right_symbolic) = intervals_and_symbolic(right_members);
    match (left_negated, right_negated) {
        (false, false) => {
            if intersects(&left, &right) {
                Some(false)
            } else if left_symbolic || right_symbolic || case_matching == CaseMatching::Insensitive
            {
                None
            } else {
                Some(true)
            }
        }
        (false, true) => independent_positive_negative(
            &left,
            left_symbolic,
            &right,
            right_symbolic,
            case_matching,
        ),
        (true, false) => independent_positive_negative(
            &right,
            right_symbolic,
            &left,
            left_symbolic,
            case_matching,
        ),
        (true, true) => None,
    }
}

fn independent_positive_negative(
    positive: &[(u32, u32)],
    positive_symbolic: bool,
    excluded: &[(u32, u32)],
    excluded_symbolic: bool,
    case_matching: CaseMatching,
) -> Option<bool> {
    if !positive_symbolic && subset(positive, excluded) {
        return Some(true);
    }
    if !excluded_symbolic && !subset(positive, excluded) && case_matching == CaseMatching::Sensitive
    {
        return Some(false);
    }
    None
}
fn exact_intervals(members: &[CharacterSetMember]) -> Option<Vec<(u32, u32)>> {
    let (intervals, symbolic) = intervals_and_symbolic(members);
    (!symbolic).then_some(intervals)
}

fn intervals_and_symbolic(members: &[CharacterSetMember]) -> (Vec<(u32, u32)>, bool) {
    let mut intervals = Vec::new();
    let mut symbolic = false;
    for member in members {
        match member {
            CharacterSetMember::Literal { value } => {
                let value = u32::from(value.get());
                intervals.push((value, value));
            }
            CharacterSetMember::Range { start, end } => {
                intervals.push((u32::from(start.get()), u32::from(end.get())));
            }
            CharacterSetMember::Builtin { .. } | CharacterSetMember::UnicodeProperty { .. } => {
                symbolic = true
            }
        }
    }
    intervals.sort_unstable();
    let mut merged: Vec<(u32, u32)> = Vec::new();
    for (start, end) in intervals {
        match merged.last_mut() {
            Some((_, previous_end)) if start <= previous_end.saturating_add(1) => {
                *previous_end = (*previous_end).max(end);
            }
            _ => merged.push((start, end)),
        }
    }
    (merged, symbolic)
}

fn contains(intervals: &[(u32, u32)], value: u32) -> bool {
    intervals
        .iter()
        .any(|(start, end)| *start <= value && value <= *end)
}

fn intersects(left: &[(u32, u32)], right: &[(u32, u32)]) -> bool {
    left.iter().any(|(left_start, left_end)| {
        right
            .iter()
            .any(|(right_start, right_end)| *left_start <= *right_end && *right_start <= *left_end)
    })
}

fn subset(left: &[(u32, u32)], right: &[(u32, u32)]) -> bool {
    left.iter().all(|(left_start, left_end)| {
        right
            .iter()
            .any(|(right_start, right_end)| right_start <= left_start && left_end <= right_end)
    })
}

fn collect_kinds(node: &Node, kinds: &mut BTreeSet<&'static str>) {
    kinds.insert(match node {
        Node::Empty { .. } => "empty",
        Node::Sequence { .. } => "sequence",
        Node::Alternation { .. } => "alternation",
        Node::Literal { .. } => "literal",
        Node::Wildcard { .. } => "wildcard",
        Node::CharacterSet { .. } => "character_set",
        Node::Repeat { .. } => "repeat",
        Node::Position { .. } => "position",
        Node::Capture { .. } => "capture",
        Node::Backreference { .. } => "backreference",
        Node::Lookaround { .. } => "lookaround",
        Node::Atomic { .. } => "atomic",
    });
    match node {
        Node::Sequence { items, .. } => {
            for child in items {
                collect_kinds(child, kinds);
            }
        }
        Node::Alternation { branches, .. } => {
            for child in branches {
                collect_kinds(child, kinds);
            }
        }
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => collect_kinds(body, kinds),
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => {}
    }
}
#[test]
fn malformed_and_mismatched_inputs_fail_deterministically() {
    let valid = program(json!({
        "node_id": "node:valid",
        "kind": "literal",
        "text": "x"
    }));
    let valid_facts = analyze(&valid).expect("valid foundational facts");

    for case in 0..MALFORMED_CASES {
        let malformed = malformed(case);
        let first = analyze_structure(&malformed, &valid_facts)
            .expect_err("malformed Semantic IR must fail");
        let second =
            analyze_structure(&malformed, &valid_facts).expect_err("malformed failure must repeat");
        assert_eq!(first, second);
        assert!(!first.errors.is_empty());
    }

    let other = program(json!({
        "node_id": "node:other",
        "kind": "literal",
        "text": "y"
    }));
    let first = analyze_structure(&other, &valid_facts)
        .expect_err("mismatched foundational store must fail");
    let second = analyze_structure(&other, &valid_facts)
        .expect_err("mismatched foundational failure must repeat");
    assert_eq!(first, second);
    assert_eq!(
        first.errors[0].code,
        StructuralAnalysisErrorCode::MismatchedFoundationalFacts
    );

    let mut wrong_version = valid.clone();
    wrong_version.specification_version =
        SpecificationVersion::try_from("1.0-draft.2").expect("test version is valid");
    let version_error =
        analyze_structure(&wrong_version, &valid_facts).expect_err("version mismatch must fail");
    assert_eq!(
        version_error.errors[0].code,
        StructuralAnalysisErrorCode::MismatchedFoundationalFacts
    );
}

fn malformed(case: usize) -> SemanticProgram {
    match case % 4 {
        0 => program(json!({
            "node_id": format!("node:malformed.sequence.{case}"),
            "kind": "sequence",
            "items": [{"node_id": format!("node:malformed.only.{case}"), "kind": "empty"}]
        })),
        1 => program(json!({
            "node_id": format!("node:malformed.alternation.{case}"),
            "kind": "alternation",
            "branches": [{"node_id": format!("node:malformed.only.{case}"), "kind": "empty"}]
        })),
        2 => program(json!({
            "node_id": format!("node:malformed.root.{case}"),
            "kind": "alternation",
            "branches": [
                {"node_id": format!("node:malformed.duplicate.{case}"), "kind": "empty"},
                {"node_id": format!("node:malformed.duplicate.{case}"), "kind": "empty"}
            ]
        })),
        3 => program(json!({
            "node_id": format!("node:malformed.reference.{case}"),
            "kind": "backreference",
            "capture_id": format!("capture:malformed.missing.{case}")
        })),
        _ => unreachable!("malformed choice is bounded"),
    }
}
