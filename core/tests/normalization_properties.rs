use std::collections::BTreeSet;

use serde_json::{json, Value};
use strling_kernel::normalization::{normalize, NormalizationErrorCode};
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::validation::{to_json, Validate};

const SEEDS: [u64; 4] = [
    0x5354_526c_696e_6701,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const CASES_PER_SEED: usize = 128;
const MALFORMED_CASES: usize = 256;

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("generated candidate must deserialize")
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
        let id = format!("node:generated.{}", self.next_node);
        self.next_node += 1;
        id
    }

    fn capture_id(&mut self) -> (String, String) {
        let number = self.next_capture;
        self.next_capture += 1;
        (
            format!("capture:generated.{number}"),
            format!("generated_{number}"),
        )
    }

    fn semantic_program(&mut self) -> SemanticProgram {
        let root_id = self.node_id();
        let capture_id = self.node_id();
        let reference_id = self.node_id();
        let capture_body = self.node(3);
        let generated = self.node(4);
        program(json!({
            "node_id": root_id,
            "kind": "sequence",
            "items": [
                {
                    "node_id": capture_id,
                    "kind": "capture",
                    "capture_id": "capture:stable",
                    "name": "stable",
                    "body": capture_body
                },
                {
                    "node_id": reference_id,
                    "kind": "backreference",
                    "capture_id": "capture:stable"
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
            1 => self.sequence(node_id, depth),
            2 => self.alternation(node_id, depth),
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
                let (capture_id, name) = self.capture_id();
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
                "capture_id": "capture:stable"
            }),
            10 => {
                let direction = if self.boolean() { "ahead" } else { "behind" };
                let polarity = if self.boolean() {
                    "positive"
                } else {
                    "negative"
                };
                let body = self.node(depth - 1);
                json!({
                    "node_id": node_id,
                    "kind": "lookaround",
                    "direction": direction,
                    "polarity": polarity,
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

    fn sequence(&mut self, node_id: String, depth: usize) -> Value {
        let child_depth = depth.saturating_sub(1);
        let count = 1 + self.pick(4);
        let items: Vec<_> = (0..count).map(|_| self.node(child_depth)).collect();
        json!({"node_id": node_id, "kind": "sequence", "items": items})
    }

    fn alternation(&mut self, node_id: String, depth: usize) -> Value {
        let child_depth = depth.saturating_sub(1);
        let count = 1 + self.pick(4);
        let branches: Vec<_> = (0..count).map(|_| self.node(child_depth)).collect();
        json!({"node_id": node_id, "kind": "alternation", "branches": branches})
    }

    fn character_set(&mut self, node_id: String) -> Value {
        let literal_value = ["a", "é", "中", "😀"][self.pick(4)];
        let literal = json!({"kind": "literal", "value": literal_value});
        let builtin_name = ["digit", "word", "whitespace"][self.pick(3)];
        let domain = if self.boolean() { "ascii" } else { "unicode" };
        let members = vec![
            json!({
                "kind": "unicode_property",
                "property": "General_Category",
                "value": "Letter",
                "negated": self.boolean()
            }),
            literal.clone(),
            json!({"kind": "range", "start": "a", "end": "z"}),
            json!({
                "kind": "builtin",
                "name": builtin_name,
                "domain": domain,
                "negated": self.boolean()
            }),
            literal,
        ];
        json!({
            "node_id": node_id,
            "kind": "character_set",
            "negated": self.boolean(),
            "members": members
        })
    }
}

fn collect_kinds(node: &Node, kinds: &mut BTreeSet<&'static str>) {
    let kind = match node {
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
    };
    kinds.insert(kind);
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

fn capture_links(node: &Node, captures: &mut BTreeSet<String>, references: &mut Vec<String>) {
    match node {
        Node::Capture {
            capture_id, body, ..
        } => {
            captures.insert(capture_id.as_str().to_owned());
            capture_links(body, captures, references);
        }
        Node::Backreference { capture_id, .. } => {
            references.push(capture_id.as_str().to_owned());
        }
        Node::Sequence { items, .. } => {
            for child in items {
                capture_links(child, captures, references);
            }
        }
        Node::Alternation { branches, .. } => {
            for child in branches {
                capture_links(child, captures, references);
            }
        }
        Node::Repeat { body, .. } | Node::Lookaround { body, .. } | Node::Atomic { body, .. } => {
            capture_links(body, captures, references)
        }
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. } => {}
    }
}

fn assert_target_neutral(value: &Value) {
    const FORBIDDEN_KEYS: [&str; 9] = [
        "target_profile",
        "engine_options",
        "emitted_pattern",
        "capture_number",
        "nullable",
        "length_bounds",
        "feature_requirements",
        "overlap",
        "safety_analysis",
    ];
    match value {
        Value::Array(values) => {
            for value in values {
                assert_target_neutral(value);
            }
        }
        Value::Object(object) => {
            for (key, value) in object {
                assert!(
                    !FORBIDDEN_KEYS.contains(&key.as_str()),
                    "forbidden key {key}"
                );
                assert_target_neutral(value);
            }
        }
        Value::Null | Value::Bool(_) | Value::Number(_) | Value::String(_) => {}
    }
}

#[test]
fn generated_valid_programs_certify_normalization_properties() {
    let mut seen_kinds = BTreeSet::new();
    for seed in SEEDS {
        let mut generator = Generator::new(seed);
        for case in 0..CASES_PER_SEED {
            let candidate = generator.semantic_program();
            collect_kinds(&candidate.root, &mut seen_kinds);
            let mut input_captures = BTreeSet::new();
            let mut input_references = Vec::new();
            capture_links(&candidate.root, &mut input_captures, &mut input_references);

            let first = normalize(&candidate)
                .unwrap_or_else(|errors| panic!("seed {seed:#x} case {case} failed: {errors:?}"));
            let repeated = normalize(&candidate).expect("identical input must normalize again");
            assert_eq!(first, repeated, "seed {seed:#x} case {case}");
            assert_eq!(
                to_json(&first).expect("first result serializes"),
                to_json(&repeated).expect("repeated result serializes"),
                "serialized determinism failed for seed {seed:#x} case {case}"
            );

            let twice = normalize(&first).expect("normalized output must normalize");
            assert_eq!(
                twice, first,
                "idempotence failed for seed {seed:#x} case {case}"
            );
            first
                .validate()
                .unwrap_or_else(|errors| panic!("invalid output: {errors:?}"));

            let mut output_captures = BTreeSet::new();
            let mut output_references = Vec::new();
            capture_links(&first.root, &mut output_captures, &mut output_references);
            assert_eq!(output_captures, input_captures);
            assert_eq!(output_references, input_references);
            assert_target_neutral(&serde_json::to_value(&first).expect("result to value"));
        }
    }

    let expected: BTreeSet<_> = [
        "empty",
        "sequence",
        "alternation",
        "literal",
        "wildcard",
        "character_set",
        "repeat",
        "position",
        "capture",
        "backreference",
        "lookaround",
        "atomic",
    ]
    .into_iter()
    .collect();
    assert_eq!(seen_kinds, expected);
}

fn malformed(case: usize) -> (SemanticProgram, NormalizationErrorCode) {
    let suffix = case.to_string();
    match case % 8 {
        0 => (
            program(json!({
                "node_id": format!("node:bad.sequence.{suffix}"),
                "kind": "sequence",
                "items": []
            })),
            NormalizationErrorCode::InvalidSemanticStructure,
        ),
        1 => (
            program(json!({
                "node_id": format!("node:bad.alternation.{suffix}"),
                "kind": "alternation",
                "branches": []
            })),
            NormalizationErrorCode::InvalidSemanticStructure,
        ),
        2 => (
            program(json!({
                "node_id": format!("node:bad.literal.{suffix}"),
                "kind": "literal",
                "text": ""
            })),
            NormalizationErrorCode::InvalidSemanticStructure,
        ),
        3 => (
            program(json!({
                "node_id": format!("node:bad.repeat.{suffix}"),
                "kind": "repeat",
                "body": {"node_id": format!("node:bad.body.{suffix}"), "kind": "empty"},
                "min": 4,
                "max": 3,
                "mode": "greedy"
            })),
            NormalizationErrorCode::InvalidRepetitionBounds,
        ),
        4 => (
            program(json!({
                "node_id": format!("node:bad.set.{suffix}"),
                "kind": "character_set",
                "negated": false,
                "members": [{"kind": "range", "start": "z", "end": "a"}]
            })),
            NormalizationErrorCode::InvalidCharacterSet,
        ),
        5 => (
            program(json!({
                "node_id": format!("node:bad.reference.{suffix}"),
                "kind": "backreference",
                "capture_id": format!("capture:missing.{suffix}")
            })),
            NormalizationErrorCode::InvalidReference,
        ),
        6 => {
            let duplicate = format!("node:bad.duplicate.{suffix}");
            (
                program(json!({
                    "node_id": duplicate,
                    "kind": "sequence",
                    "items": [
                        {"node_id": format!("node:bad.duplicate.{suffix}"), "kind": "empty"},
                        {"node_id": format!("node:bad.other.{suffix}"), "kind": "empty"}
                    ]
                })),
                NormalizationErrorCode::InvalidIdentity,
            )
        }
        7 => (
            program(json!({
                "node_id": format!("node:bad.captures.{suffix}"),
                "kind": "sequence",
                "items": [
                    {
                        "node_id": format!("node:bad.capture.a.{suffix}"),
                        "kind": "capture",
                        "capture_id": format!("capture:duplicate.{suffix}"),
                        "body": {"node_id": format!("node:bad.capture.body.a.{suffix}"), "kind": "empty"}
                    },
                    {
                        "node_id": format!("node:bad.capture.b.{suffix}"),
                        "kind": "capture",
                        "capture_id": format!("capture:duplicate.{suffix}"),
                        "body": {"node_id": format!("node:bad.capture.body.b.{suffix}"), "kind": "empty"}
                    }
                ]
            })),
            NormalizationErrorCode::InvalidIdentity,
        ),
        _ => unreachable!("malformed case class is bounded"),
    }
}

#[test]
fn generated_malformed_programs_fail_with_stable_categories() {
    for case in 0..MALFORMED_CASES {
        let (candidate, expected) = malformed(case);
        let errors = normalize(&candidate)
            .expect_err("generated malformed candidate must fail")
            .errors;
        assert!(
            errors.iter().any(|error| error.code == expected),
            "case {case} lacked {expected:?}: {errors:?}"
        );
    }
}
