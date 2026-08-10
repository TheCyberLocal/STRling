use std::collections::{BTreeMap, BTreeSet};

use serde_json::{json, Value};
use strling_kernel::normalization::normalize;
use strling_kernel::semantic::{Node, RepetitionMaximum, SemanticProgram};
use strling_kernel::semantic_analysis::{analyze, Consumption, MaximumConsumption, Nullability};
use strling_kernel::source::{CaptureId, NodeId};

const SEEDS: [u64; 4] = [
    0x5345_4d41_4e54_4943,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const CASES_PER_SEED: usize = 128;
const MALFORMED_CASES: usize = 256;
const DIFFERENTIAL_CASES: usize = 128;

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
        let value = format!("node:analysis.generated.{}", self.next_node);
        self.next_node += 1;
        value
    }

    fn capture_identity(&mut self) -> (String, String) {
        let value = self.next_capture;
        self.next_capture += 1;
        (
            format!("capture:analysis.generated.{value}"),
            format!("analysis_generated_{value}"),
        )
    }

    fn semantic_program(&mut self) -> SemanticProgram {
        let root = self.node_id();
        let capture = self.node_id();
        let reference = self.node_id();
        let body = self.node(3);
        let generated = self.node(4);
        program(json!({
            "node_id": root,
            "kind": "sequence",
            "items": [
                {
                    "node_id": capture,
                    "kind": "capture",
                    "capture_id": "capture:analysis.stable",
                    "name": "analysis_stable",
                    "body": body
                },
                {
                    "node_id": reference,
                    "kind": "backreference",
                    "capture_id": "capture:analysis.stable"
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
                let child_depth = depth.saturating_sub(1);
                let count = 1 + self.pick(4);
                let items: Vec<_> = (0..count).map(|_| self.node(child_depth)).collect();
                json!({"node_id": node_id, "kind": "sequence", "items": items})
            }
            2 => {
                let child_depth = depth.saturating_sub(1);
                let count = 1 + self.pick(4);
                let branches: Vec<_> = (0..count).map(|_| self.node(child_depth)).collect();
                json!({"node_id": node_id, "kind": "alternation", "branches": branches})
            }
            3 => {
                const VALUES: [&str; 6] = ["a", "ß", "é", "e\u{301}", "😀", "中"];
                let unit = VALUES[self.pick(VALUES.len())];
                let text = unit.repeat(1 + self.pick(3));
                json!({"node_id": node_id, "kind": "literal", "text": text})
            }
            4 => json!({
                "node_id": node_id,
                "kind": "wildcard",
                "line_terminators": if self.boolean() { "include" } else { "exclude" }
            }),
            5 => self.character_set(node_id),
            6 => {
                let min = self.pick(4) as u64;
                let max = if self.boolean() {
                    Value::Null
                } else {
                    json!(min + self.pick(4) as u64)
                };
                let mode = ["greedy", "lazy", "possessive"][self.pick(3)];
                let body = self.node(depth - 1);
                json!({
                    "node_id": node_id,
                    "kind": "repeat",
                    "body": body,
                    "min": min,
                    "max": max,
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
                "capture_id": "capture:analysis.stable"
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
        let value = ["a", "é", "中", "😀"][self.pick(4)];
        let members = vec![
            json!({
                "kind": "unicode_property",
                "property": "General_Category",
                "value": "Letter",
                "negated": self.boolean()
            }),
            json!({"kind": "literal", "value": value}),
            json!({"kind": "range", "start": "a", "end": "z"}),
            json!({
                "kind": "builtin",
                "name": (["digit", "word", "whitespace"][self.pick(3)]),
                "domain": if self.boolean() { "ascii" } else { "unicode" },
                "negated": self.boolean()
            }),
        ];
        json!({
            "node_id": node_id,
            "kind": "character_set",
            "negated": self.boolean(),
            "members": members
        })
    }
}

#[test]
fn generated_normalized_programs_certify_foundational_analysis_properties() {
    let mut covered_kinds = BTreeSet::new();
    let mut cases = 0;

    for seed in SEEDS {
        let mut generator = Generator::new(seed);
        for _ in 0..CASES_PER_SEED {
            let candidate = generator.semantic_program();
            let normalized = normalize(&candidate).expect("generated program must normalize");
            collect_kinds(&normalized.root, &mut covered_kinds);
            let unchanged = normalized.clone();

            let first = analyze(&normalized).expect("normalized program must analyze");
            let second = analyze(&normalized).expect("repeated analysis must succeed");
            assert_eq!(first, second, "analysis must be deterministic");
            assert_eq!(normalized, unchanged, "analysis must not mutate input");
            assert_eq!(first.len(), normalized.node_ids().len());

            for node_id in normalized.node_ids() {
                let facts = first.get(&node_id).expect("every node needs facts");
                if let MaximumConsumption::Finite(maximum) = facts.maximum_consumption {
                    assert!(facts.minimum_consumption <= maximum);
                }
                if facts.nullability == Nullability::Nullable {
                    assert_eq!(facts.minimum_consumption, 0);
                }
                if facts.consumption == Consumption::AlwaysZeroWidth {
                    assert_eq!(facts.minimum_consumption, 0);
                    assert_eq!(facts.maximum_consumption, MaximumConsumption::Finite(0));
                }
            }

            let mut references = BTreeMap::new();
            collect_references(&normalized.root, &mut references);
            for (node_id, capture_id) in references {
                let resolution = first
                    .backreference(&node_id)
                    .expect("every certified reference must resolve");
                assert_eq!(resolution.capture_id, capture_id);
                let definition = first
                    .capture_definition(&capture_id)
                    .expect("resolved capture must have a definition");
                assert_eq!(resolution.definition_node_id, definition.definition_node_id);
            }
            cases += 1;
        }
    }

    assert_eq!(cases, SEEDS.len() * CASES_PER_SEED);
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

#[test]
fn generated_malformed_programs_fail_deterministically_without_panics() {
    for case in 0..MALFORMED_CASES {
        let semantic = malformed_program(case % 4);
        let first = analyze(&semantic).expect_err("malformed program must fail analysis");
        let second = analyze(&semantic).expect_err("repeated malformed input must fail");
        assert_eq!(first, second, "failure categories and paths must be stable");
        assert!(!first.errors.is_empty());
    }
}

#[test]
fn bounded_semantic_evidence_has_zero_unexplained_length_differences() {
    let mut generator = Generator::new(0x4556_4944_454e_4345);
    for _ in 0..DIFFERENTIAL_CASES {
        let candidate = program(generator.bounded_node(4));
        let normalized = normalize(&candidate).expect("bounded evidence must normalize");
        let analysis = analyze(&normalized).expect("bounded evidence must analyze");
        let mut evidence = BTreeMap::new();
        evidence_lengths(&normalized.root, &mut evidence);

        for (node_id, lengths) in evidence {
            let facts = analysis.get(&node_id).expect("evidence node needs facts");
            let minimum = *lengths
                .iter()
                .next()
                .expect("evidence language is nonempty");
            let maximum = *lengths
                .iter()
                .next_back()
                .expect("evidence language is nonempty");
            assert_eq!(facts.minimum_consumption, minimum);
            assert_eq!(
                facts.maximum_consumption,
                MaximumConsumption::Finite(maximum)
            );
            assert_eq!(
                facts.nullability,
                if lengths.contains(&0) {
                    Nullability::Nullable
                } else {
                    Nullability::NonNullable
                }
            );
            let expected_consumption = if lengths == BTreeSet::from([0]) {
                Consumption::AlwaysZeroWidth
            } else if lengths.contains(&0) {
                Consumption::Variable
            } else {
                Consumption::AlwaysConsuming
            };
            assert_eq!(facts.consumption, expected_consumption);
        }
    }
}

impl Generator {
    fn bounded_node(&mut self, depth: usize) -> Value {
        let choice = if depth == 0 {
            self.pick(5)
        } else {
            self.pick(10)
        };
        let node_id = self.node_id();
        match choice {
            0 => json!({"node_id": node_id, "kind": "empty"}),
            1 => {
                json!({"node_id": node_id, "kind": "literal", "text": (["a", "é", "😀x"][self.pick(3)])})
            }
            2 => json!({"node_id": node_id, "kind": "wildcard", "line_terminators": "include"}),
            3 => json!({
                "node_id": node_id,
                "kind": "character_set",
                "negated": false,
                "members": [{"kind": "range", "start": "a", "end": "z"}]
            }),
            4 => json!({"node_id": node_id, "kind": "position", "position": "input_start"}),
            5 => {
                let child_depth = depth - 1;
                let items = vec![
                    self.bounded_node(child_depth),
                    self.bounded_node(child_depth),
                ];
                json!({"node_id": node_id, "kind": "sequence", "items": items})
            }
            6 => {
                let child_depth = depth - 1;
                let branches = vec![
                    self.bounded_node(child_depth),
                    self.bounded_node(child_depth),
                ];
                json!({"node_id": node_id, "kind": "alternation", "branches": branches})
            }
            7 => {
                let min = self.pick(3) as u64;
                let max = min + self.pick(3) as u64;
                let body = self.bounded_node(depth - 1);
                json!({"node_id": node_id, "kind": "repeat", "body": body, "min": min, "max": max, "mode": "greedy"})
            }
            8 => {
                let (capture_id, name) = self.capture_identity();
                let body = self.bounded_node(depth - 1);
                json!({"node_id": node_id, "kind": "capture", "capture_id": capture_id, "name": name, "body": body})
            }
            9 => {
                let body = self.bounded_node(depth - 1);
                if self.boolean() {
                    json!({"node_id": node_id, "kind": "atomic", "body": body})
                } else {
                    json!({"node_id": node_id, "kind": "lookaround", "direction": "behind", "polarity": "positive", "body": body})
                }
            }
            _ => unreachable!("bounded generator choice is bounded"),
        }
    }
}

fn malformed_program(choice: usize) -> SemanticProgram {
    match choice {
        0 => program(json!({
            "node_id": "node:malformed.sequence",
            "kind": "sequence",
            "items": [{"node_id": "node:malformed.only", "kind": "empty"}]
        })),
        1 => program(json!({
            "node_id": "node:malformed.root",
            "kind": "alternation",
            "branches": [
                {"node_id": "node:malformed.duplicate", "kind": "empty"},
                {"node_id": "node:malformed.duplicate", "kind": "empty"}
            ]
        })),
        2 => program(json!({
            "node_id": "node:malformed.reference",
            "kind": "backreference",
            "capture_id": "capture:malformed.missing"
        })),
        3 => program(json!({
            "node_id": "node:overflow.outer",
            "kind": "repeat",
            "body": {
                "node_id": "node:overflow.inner",
                "kind": "repeat",
                "body": {"node_id": "node:overflow.literal", "kind": "literal", "text": "x"},
                "min": 18446744073709551615u64,
                "max": 18446744073709551615u64,
                "mode": "greedy"
            },
            "min": 2,
            "max": 2,
            "mode": "greedy"
        })),
        _ => unreachable!("malformed choice is bounded"),
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
    visit_children(node, |child| collect_kinds(child, kinds));
}

fn collect_references(node: &Node, references: &mut BTreeMap<NodeId, CaptureId>) {
    if let Node::Backreference {
        node_id,
        capture_id,
        ..
    } = node
    {
        references.insert(node_id.clone(), capture_id.clone());
    }
    visit_children(node, |child| collect_references(child, references));
}

fn visit_children<'a>(node: &'a Node, mut visit: impl FnMut(&'a Node)) {
    match node {
        Node::Sequence { items, .. } => {
            for child in items {
                visit(child);
            }
        }
        Node::Alternation { branches, .. } => {
            for child in branches {
                visit(child);
            }
        }
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => visit(body),
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => {}
    }
}

fn evidence_lengths(node: &Node, evidence: &mut BTreeMap<NodeId, BTreeSet<u64>>) -> BTreeSet<u64> {
    let lengths = match node {
        Node::Empty { .. } | Node::Position { .. } => BTreeSet::from([0]),
        Node::Literal { text, .. } => BTreeSet::from([text.chars().count() as u64]),
        Node::Wildcard { .. } | Node::CharacterSet { .. } => BTreeSet::from([1]),
        Node::Sequence { items, .. } => items.iter().fold(BTreeSet::from([0]), |left, child| {
            let right = evidence_lengths(child, evidence);
            left.iter()
                .flat_map(|left| right.iter().map(move |right| left + right))
                .collect()
        }),
        Node::Alternation { branches, .. } => {
            let mut lengths = BTreeSet::new();
            for branch in branches {
                lengths.extend(evidence_lengths(branch, evidence));
            }
            lengths
        }
        Node::Repeat { body, min, max, .. } => {
            let body = evidence_lengths(body, evidence);
            let RepetitionMaximum::Bounded(maximum) = max else {
                panic!("bounded evidence generator never creates unbounded repetition");
            };
            let mut accepted = BTreeSet::new();
            let mut current = BTreeSet::from([0]);
            for count in 0..=*maximum {
                if count >= *min {
                    accepted.extend(current.iter().copied());
                }
                current = current
                    .iter()
                    .flat_map(|left| body.iter().map(move |right| left + right))
                    .collect();
            }
            accepted
        }
        Node::Capture { body, .. } | Node::Atomic { body, .. } => evidence_lengths(body, evidence),
        Node::Lookaround { body, .. } => {
            evidence_lengths(body, evidence);
            BTreeSet::from([0])
        }
        Node::Backreference { .. } => {
            panic!("bounded evidence generator never creates backreferences")
        }
    };
    evidence.insert(node.node_id().clone(), lengths.clone());
    lengths
}
