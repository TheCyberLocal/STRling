use std::collections::BTreeSet;

use serde_json::{json, Value};
use strling_kernel::normalization::normalize;
use strling_kernel::safety_analysis::{
    analyze_safety, SafetyAnalysis, SafetyEvidence, SafetyFindingCode, StructuralRelationshipKind,
    StructuralRelationshipRef,
};
use strling_kernel::semantic::{Node, RepetitionMaximum, SemanticProgram};
use strling_kernel::semantic_analysis::{analyze, SemanticFacts};
use strling_kernel::source::NodeId;
use strling_kernel::structural_analysis::{
    analyze_structure, OverlapRelation, ProgressClassification, RepetitionExtent, StructuralFacts,
};

const SEEDS: [u64; 4] = [
    0x5341_4645_5459_5f31,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const CASES_PER_SEED: usize = 96;

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
        let node_id = format!("node:safety.generated.{}", self.next_node);
        self.next_node += 1;
        node_id
    }

    fn capture_identity(&mut self) -> (String, String) {
        let capture = self.next_capture;
        self.next_capture += 1;
        (
            format!("capture:safety.generated.{capture}"),
            format!("safety_generated_{capture}"),
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
                    "capture_id": "capture:safety.stable",
                    "name": "safety_stable",
                    "body": capture_body
                },
                {
                    "node_id": reference,
                    "kind": "backreference",
                    "capture_id": "capture:safety.stable"
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
                "capture_id": "capture:safety.stable"
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
fn generated_programs_certify_safety_soundness_properties() {
    let mut covered_kinds = BTreeSet::new();
    let mut covered_findings = BTreeSet::new();
    let mut generated_cases = 0_usize;
    let mut uncertainty_records = 0_usize;

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
            let structural = analyze_structure(&semantic, &foundational).unwrap_or_else(|errors| {
                panic!("seed {seed:#x} case {case} failed structure: {errors:?}")
            });
            let semantic_before = semantic.clone();
            let foundational_before = foundational.clone();
            let structural_before = structural.clone();

            let first =
                analyze_safety(&semantic, &foundational, &structural).unwrap_or_else(|errors| {
                    panic!("seed {seed:#x} case {case} failed safety: {errors:?}")
                });
            let second = analyze_safety(&semantic, &foundational, &structural)
                .expect("repeat safety analysis must succeed");

            assert_eq!(
                first, second,
                "determinism failed for seed {seed:#x} case {case}"
            );
            assert_eq!(semantic, semantic_before, "Semantic IR was mutated");
            assert_eq!(
                foundational, foundational_before,
                "foundational facts were mutated"
            );
            assert_eq!(
                structural, structural_before,
                "structural facts were mutated"
            );
            assert_sound_evidence(&semantic, &foundational, &structural, &first);
            covered_findings.extend(first.findings().map(|finding| finding.code));
            uncertainty_records += first.uncertainties().count();
            generated_cases += 1;
        }
    }

    let mut witness_cases = 0_usize;
    for (candidate, expected_code) in property_witnesses() {
        let semantic = normalize(&candidate).expect("property witness must normalize");
        let foundational = analyze(&semantic).expect("property witness foundational facts");
        let structural =
            analyze_structure(&semantic, &foundational).expect("property witness structure");
        let safety = analyze_safety(&semantic, &foundational, &structural)
            .expect("property witness safety analysis");
        assert_sound_evidence(&semantic, &foundational, &structural, &safety);
        if let Some(expected_code) = expected_code {
            assert!(
                safety
                    .findings()
                    .any(|finding| finding.code == expected_code),
                "property witness did not produce {expected_code:?}"
            );
        }
        covered_findings.extend(safety.findings().map(|finding| finding.code));
        uncertainty_records += safety.uncertainties().count();
        witness_cases += 1;
    }

    assert_eq!(generated_cases, SEEDS.len() * CASES_PER_SEED);
    assert_eq!(witness_cases, 6);
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
    assert_eq!(
        covered_findings,
        BTreeSet::from([
            SafetyFindingCode::NestedRepetitionOverlap,
            SafetyFindingCode::RepeatedAlternationOverlap,
            SafetyFindingCode::RepetitionFollowerOverlap,
            SafetyFindingCode::UnboundedIndeterminateProgress,
            SafetyFindingCode::UnboundedNullableRepetition,
        ])
    );
    assert!(
        uncertainty_records > 0,
        "generated corpus must preserve unknowns"
    );
}

fn property_witnesses() -> Vec<(SemanticProgram, Option<SafetyFindingCode>)> {
    vec![
        (
            program(repeat(
                "node:nullable.outer",
                repeat(
                    "node:nullable.inner",
                    literal("node:nullable.atom", "a"),
                    0,
                    json!(1),
                    "greedy",
                ),
                0,
                Value::Null,
                "greedy",
            )),
            Some(SafetyFindingCode::UnboundedNullableRepetition),
        ),
        (
            program(json!({
                "node_id": "node:indeterminate.root",
                "kind": "sequence",
                "items": [
                    {
                        "node_id": "node:indeterminate.capture",
                        "kind": "capture",
                        "capture_id": "capture:indeterminate",
                        "body": repeat(
                            "node:indeterminate.optional",
                            literal("node:indeterminate.atom", "a"),
                            0,
                            json!(1),
                            "greedy"
                        )
                    },
                    repeat(
                        "node:indeterminate.repeat",
                        json!({
                            "node_id": "node:indeterminate.reference",
                            "kind": "backreference",
                            "capture_id": "capture:indeterminate"
                        }),
                        1,
                        Value::Null,
                        "greedy"
                    )
                ]
            })),
            Some(SafetyFindingCode::UnboundedIndeterminateProgress),
        ),
        (
            nested_repeat(Value::Null, "greedy", json!(2), "lazy"),
            Some(SafetyFindingCode::NestedRepetitionOverlap),
        ),
        (
            program(repeat(
                "node:alternation.repeat",
                json!({
                    "node_id": "node:alternation",
                    "kind": "alternation",
                    "branches": [
                        literal("node:alternation.left", "a"),
                        literal("node:alternation.right", "ab")
                    ]
                }),
                0,
                Value::Null,
                "greedy",
            )),
            Some(SafetyFindingCode::RepeatedAlternationOverlap),
        ),
        (
            program(json!({
                "node_id": "node:follower.sequence",
                "kind": "sequence",
                "items": [
                    repeat(
                        "node:follower.repeat",
                        literal("node:follower.operand", "a"),
                        0,
                        Value::Null,
                        "greedy"
                    ),
                    literal("node:follower.expression", "ab")
                ]
            })),
            Some(SafetyFindingCode::RepetitionFollowerOverlap),
        ),
        (
            program(repeat(
                "node:unknown.repeat",
                json!({
                    "node_id": "node:unknown.alternation",
                    "kind": "alternation",
                    "branches": [
                        property("node:unknown.left"),
                        property("node:unknown.right")
                    ]
                }),
                0,
                Value::Null,
                "greedy",
            )),
            None,
        ),
    ]
}

fn assert_sound_evidence(
    semantic: &SemanticProgram,
    foundational: &SemanticFacts,
    structural: &StructuralFacts,
    safety: &SafetyAnalysis,
) {
    let node_ids = semantic.node_ids();
    let mut positive_relationships = BTreeSet::new();
    for finding in safety.findings() {
        assert!(node_ids.contains(&finding.primary_node_id));
        assert!(finding
            .evidence_node_ids
            .iter()
            .all(|node_id| node_ids.contains(node_id)));
        assert!(finding
            .evidence_node_ids
            .windows(2)
            .all(|pair| pair[0] < pair[1]));
        assert!(finding
            .evidence_node_ids
            .binary_search(&finding.primary_node_id)
            .is_ok());
        match &finding.evidence {
            SafetyEvidence::RepetitionProgress {
                repetition_node_id,
                operand_node_id,
                extent,
                progress,
            } => {
                let repetition = structural
                    .get(repetition_node_id)
                    .and_then(|facts| facts.repetition.as_ref())
                    .expect("progress evidence needs repetition facts");
                assert_eq!(*extent, RepetitionExtent::Unbounded);
                assert_eq!(*extent, repetition.extent);
                assert_eq!(*operand_node_id, repetition.body_node_id);
                assert_eq!(*progress, repetition.operand_progress);
                match finding.code {
                    SafetyFindingCode::UnboundedNullableRepetition => {
                        assert_eq!(*progress, ProgressClassification::PotentiallyZeroConsuming)
                    }
                    SafetyFindingCode::UnboundedIndeterminateProgress => {
                        assert_eq!(*progress, ProgressClassification::Indeterminate)
                    }
                    _ => panic!("progress evidence has the wrong finding code"),
                }
            }
            SafetyEvidence::NestedRepetition {
                outer_repetition_node_id,
                inner_repetition_node_id,
                inner_operand_node_id,
                path,
                outer_extent,
                inner_length,
                inner_minimum,
                inner_maximum,
            } => {
                assert_eq!(finding.code, SafetyFindingCode::NestedRepetitionOverlap);
                assert_eq!(path.first(), Some(outer_repetition_node_id));
                assert_eq!(path.last(), Some(inner_repetition_node_id));
                assert_direct_path(&semantic.root, path);
                let outer = structural
                    .get(outer_repetition_node_id)
                    .and_then(|facts| facts.repetition.as_ref())
                    .expect("outer repetition facts");
                let inner = structural
                    .get(inner_repetition_node_id)
                    .expect("inner structural facts");
                let inner_repetition = inner.repetition.as_ref().expect("inner repetition facts");
                assert_eq!(*outer_extent, RepetitionExtent::Unbounded);
                assert_eq!(*outer_extent, outer.extent);
                assert_eq!(*inner_length, inner.length);
                assert_eq!(*inner_operand_node_id, inner_repetition.body_node_id);
                assert_eq!(
                    inner_repetition.operand_progress,
                    ProgressClassification::AlwaysConsuming
                );
                let Node::Repeat { min, max, .. } =
                    find_node(&semantic.root, inner_repetition_node_id)
                        .expect("inner repeat resolves")
                else {
                    panic!("nested evidence inner identity must be a repeat");
                };
                assert_eq!((*inner_minimum, *inner_maximum), (*min, *max));
            }
            SafetyEvidence::RepeatedAlternation {
                alternation_node_id,
                left_branch_index,
                right_branch_index,
                relationship,
                relation,
                ..
            } => {
                assert_eq!(finding.code, SafetyFindingCode::RepeatedAlternationOverlap);
                assert_eq!(*relation, OverlapRelation::Overlapping);
                assert_eq!(
                    relationship.kind,
                    StructuralRelationshipKind::AlternationBranchOverlap
                );
                assert_eq!(relationship.owner_node_id, *alternation_node_id);
                let stored = structural
                    .get(alternation_node_id)
                    .expect("alternation facts")
                    .alternation_branch_overlaps
                    .iter()
                    .find(|stored| {
                        stored.left_branch_index == *left_branch_index
                            && stored.right_branch_index == *right_branch_index
                            && stored.left_node_id == relationship.left_node_id
                            && stored.right_node_id == relationship.right_node_id
                    })
                    .expect("alternation relationship evidence resolves");
                assert_eq!(stored.relation, OverlapRelation::Overlapping);
                positive_relationships.insert(relationship.clone());
            }
            SafetyEvidence::RepetitionFollower {
                sequence_node_id,
                repetition_node_id,
                operand_node_id,
                follower_node_id,
                repetition_index,
                follower_index,
                relationship,
                relation,
                ..
            } => {
                assert_eq!(finding.code, SafetyFindingCode::RepetitionFollowerOverlap);
                assert_eq!(*relation, OverlapRelation::Overlapping);
                assert_eq!(
                    relationship.kind,
                    StructuralRelationshipKind::RepetitionFollowerOverlap
                );
                assert_eq!(relationship.owner_node_id, *sequence_node_id);
                assert_eq!(relationship.left_node_id, *operand_node_id);
                assert_eq!(relationship.right_node_id, *follower_node_id);
                let stored = structural
                    .get(sequence_node_id)
                    .expect("sequence facts")
                    .repetition_follow_overlaps
                    .iter()
                    .find(|stored| {
                        stored.repetition_node_id == *repetition_node_id
                            && stored.operand_node_id == *operand_node_id
                            && stored.following_node_id == *follower_node_id
                            && stored.repetition_index == *repetition_index
                            && stored.following_index == *follower_index
                    })
                    .expect("follower relationship evidence resolves");
                assert_eq!(stored.relation, OverlapRelation::Overlapping);
                let repetition = structural
                    .get(repetition_node_id)
                    .and_then(|facts| facts.repetition.as_ref())
                    .expect("follower repetition facts");
                assert_eq!(
                    repetition.operand_progress,
                    ProgressClassification::AlwaysConsuming
                );
                positive_relationships.insert(relationship.clone());
            }
        }
    }

    for (owner_node_id, facts) in structural.iter() {
        if let Some(repetition) = &facts.repetition {
            if repetition.extent == RepetitionExtent::Unbounded
                && repetition.operand_progress == ProgressClassification::AlwaysConsuming
            {
                assert!(!safety.findings().any(|finding| {
                    finding.primary_node_id == *owner_node_id
                        && matches!(
                            finding.code,
                            SafetyFindingCode::UnboundedNullableRepetition
                                | SafetyFindingCode::UnboundedIndeterminateProgress
                        )
                }));
            }
        }
        for relationship in &facts.alternation_branch_overlaps {
            if relationship.relation != OverlapRelation::Overlapping {
                let reference = StructuralRelationshipRef {
                    kind: StructuralRelationshipKind::AlternationBranchOverlap,
                    owner_node_id: owner_node_id.clone(),
                    left_node_id: relationship.left_node_id.clone(),
                    right_node_id: relationship.right_node_id.clone(),
                };
                assert!(!positive_relationships.contains(&reference));
            }
        }
        for relationship in &facts.repetition_follow_overlaps {
            if relationship.relation != OverlapRelation::Overlapping {
                let reference = StructuralRelationshipRef {
                    kind: StructuralRelationshipKind::RepetitionFollowerOverlap,
                    owner_node_id: owner_node_id.clone(),
                    left_node_id: relationship.operand_node_id.clone(),
                    right_node_id: relationship.following_node_id.clone(),
                };
                assert!(!positive_relationships.contains(&reference));
            }
        }
    }

    assert!(safety.uncertainties().all(|uncertainty| uncertainty
        .evidence_node_ids
        .iter()
        .all(|node_id| node_ids.contains(node_id))));
    assert_eq!(foundational.len(), structural.len());
}

fn assert_direct_path(root: &Node, path: &[NodeId]) {
    for pair in path.windows(2) {
        let parent = find_node(root, &pair[0]).expect("path parent resolves");
        assert!(direct_children(parent).any(|child| child.node_id() == &pair[1]));
    }
}

fn find_node<'a>(root: &'a Node, node_id: &NodeId) -> Option<&'a Node> {
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        if node.node_id() == node_id {
            return Some(node);
        }
        pending.extend(direct_children(node));
    }
    None
}

fn direct_children(node: &Node) -> Box<dyn Iterator<Item = &Node> + '_> {
    match node {
        Node::Sequence { items, .. } => Box::new(items.iter()),
        Node::Alternation { branches, .. } => Box::new(branches.iter()),
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => Box::new(std::iter::once(body.as_ref())),
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => Box::new(std::iter::empty()),
    }
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
    for child in direct_children(node) {
        collect_kinds(child, kinds);
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum LegacyDisposition {
    Agreement,
    CanonicalSemanticImprovement,
    LegacyFalsePositive,
    LegacyFalseNegativeCandidate,
    UnsupportedHistoricalHeuristic,
}

#[test]
fn representative_legacy_detector_differences_are_all_explained() {
    let cases = [
        (
            "nested_unbounded",
            nested_repeat(Value::Null, "greedy", Value::Null, "greedy"),
            true,
            Some(SafetyFindingCode::NestedRepetitionOverlap),
            LegacyDisposition::Agreement,
        ),
        (
            "bounded_inner_partition",
            nested_repeat(Value::Null, "greedy", json!(2), "greedy"),
            false,
            Some(SafetyFindingCode::NestedRepetitionOverlap),
            LegacyDisposition::CanonicalSemanticImprovement,
        ),
        (
            "possessive_inner",
            nested_repeat(Value::Null, "greedy", Value::Null, "possessive"),
            true,
            None,
            LegacyDisposition::LegacyFalsePositive,
        ),
        (
            "repeated_alternation",
            program(repeat(
                "node:repeat",
                json!({
                    "node_id": "node:alt",
                    "kind": "alternation",
                    "branches": [literal("node:left", "a"), literal("node:right", "a")]
                }),
                0,
                Value::Null,
                "greedy",
            )),
            false,
            Some(SafetyFindingCode::RepeatedAlternationOverlap),
            LegacyDisposition::LegacyFalseNegativeCandidate,
        ),
        (
            "follower_competition",
            program(json!({
                "node_id": "node:sequence",
                "kind": "sequence",
                "items": [
                    repeat(
                        "node:repeat",
                        literal("node:operand", "a"),
                        0,
                        Value::Null,
                        "greedy"
                    ),
                    literal("node:follower", "a")
                ]
            })),
            false,
            Some(SafetyFindingCode::RepetitionFollowerOverlap),
            LegacyDisposition::LegacyFalseNegativeCandidate,
        ),
        (
            "unknown_unicode_overlap",
            program(repeat(
                "node:repeat",
                json!({
                    "node_id": "node:alt",
                    "kind": "alternation",
                    "branches": [property("node:left"), property("node:right")]
                }),
                0,
                Value::Null,
                "greedy",
            )),
            false,
            None,
            LegacyDisposition::UnsupportedHistoricalHeuristic,
        ),
    ];

    let mut dispositions = BTreeSet::new();
    for (name, semantic, expected_legacy, expected_canonical, disposition) in cases {
        let normalized = normalize(&semantic).expect("legacy corpus must normalize");
        let foundational = analyze(&normalized).expect("legacy corpus foundational facts");
        let structural =
            analyze_structure(&normalized, &foundational).expect("legacy corpus structure");
        let safety = analyze_safety(&normalized, &foundational, &structural)
            .expect("legacy corpus safety analysis");
        assert_eq!(
            legacy_nested_unbounded(&normalized.root),
            expected_legacy,
            "{name}"
        );
        match expected_canonical {
            Some(code) => assert!(
                safety.findings().any(|finding| finding.code == code),
                "{name}: missing canonical finding {code:?}"
            ),
            None => assert!(
                !safety
                    .findings()
                    .any(|finding| finding.code == SafetyFindingCode::NestedRepetitionOverlap),
                "{name}: unexpected canonical nested finding"
            ),
        }
        dispositions.insert(disposition as u8);
    }

    assert_eq!(dispositions.len(), 5);
}

fn nested_repeat(
    outer_maximum: Value,
    outer_mode: &str,
    inner_maximum: Value,
    inner_mode: &str,
) -> SemanticProgram {
    program(repeat(
        "node:outer",
        repeat(
            "node:inner",
            literal("node:atom", "a"),
            1,
            inner_maximum,
            inner_mode,
        ),
        1,
        outer_maximum,
        outer_mode,
    ))
}

fn literal(id: &str, text: &str) -> Value {
    json!({"node_id": id, "kind": "literal", "text": text})
}

fn property(id: &str) -> Value {
    json!({
        "node_id": id,
        "kind": "character_set",
        "negated": false,
        "members": [{
            "kind": "unicode_property",
            "property": "General_Category",
            "negated": false
        }]
    })
}

fn repeat(id: &str, body: Value, minimum: u64, maximum: Value, mode: &str) -> Value {
    json!({
        "node_id": id,
        "kind": "repeat",
        "body": body,
        "min": minimum,
        "max": maximum,
        "mode": mode
    })
}

fn legacy_nested_unbounded(root: &Node) -> bool {
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        if let Node::Repeat {
            body,
            max: RepetitionMaximum::Unbounded,
            ..
        } = node
        {
            if legacy_has_nested_unbounded(body) {
                return true;
            }
        }
        pending.extend(direct_children(node));
    }
    false
}

fn legacy_has_nested_unbounded(node: &Node) -> bool {
    match node {
        Node::Repeat {
            max: RepetitionMaximum::Unbounded,
            ..
        } => true,
        Node::Capture { body, .. } | Node::Atomic { body, .. } => legacy_has_nested_unbounded(body),
        Node::Sequence { items, .. } if items.len() == 1 => legacy_has_nested_unbounded(&items[0]),
        Node::Alternation { branches, .. } => branches.iter().any(legacy_has_nested_unbounded),
        Node::Empty { .. }
        | Node::Sequence { .. }
        | Node::Repeat { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. }
        | Node::Lookaround { .. } => false,
    }
}
