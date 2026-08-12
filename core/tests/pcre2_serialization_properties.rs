use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;
use strling_kernel::target_lowering::lower_pcre2;
use strling_kernel::target_serialization::{serialize_pcre2, Pcre2SerializationErrorCode};
use strling_kernel::validation::{canonical_sha256, to_json, Validate};

const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");

const ALL_REQUIREMENT_CAPABILITIES: &[&str] = &[
    "anchors.end_before_final_line_terminator",
    "anchors.input_end",
    "anchors.input_start",
    "anchors.line_end",
    "anchors.line_start",
    "assertions.lookahead",
    "assertions.lookbehind.fixed_length",
    "assertions.lookbehind.variable_length",
    "boundaries.word",
    "character_classes.unicode",
    "character_properties.unicode",
    "character_semantics.unicode_scalar",
    "groups.atomic",
    "groups.named_capture",
    "matching.case_insensitive",
    "references.backreference",
    "repetition.lazy",
    "repetition.possessive",
];

fn full_pcre2_profile() -> TargetProfile {
    let mut value: Value = serde_json::from_str(PCRE2_1042).expect("PCRE2 fixture JSON");
    value["capabilities"] = Value::Array(
        ALL_REQUIREMENT_CAPABILITIES
            .iter()
            .map(|capability| {
                json!({
                    "capability_id": capability,
                    "availability": "available",
                    "constraints": []
                })
            })
            .collect(),
    );
    serde_json::from_value(value).expect("complete PCRE2 profile must deserialize")
}

fn program(root: Value, insensitive: bool) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": if insensitive { "insensitive" } else { "sensitive" },
        "root": root
    }))
    .expect("generated Semantic IR must deserialize")
}

fn literal(node_id: String, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn generated_program(seed: u64) -> SemanticProgram {
    let prefix = format!("node:serialization.{seed}");
    let root = match seed % 14 {
        0 => json!({"node_id": prefix, "kind": "empty"}),
        1 => literal(prefix, if seed % 2 == 0 { "ascii" } else { "λ" }),
        2 => json!({
            "node_id": prefix,
            "kind": "wildcard",
            "line_terminators": if seed % 2 == 0 { "include" } else { "exclude" }
        }),
        3 => json!({
            "node_id": prefix,
            "kind": "character_set",
            "negated": seed % 2 == 0,
            "members": [
                {"kind": "literal", "value": "é"},
                {"kind": "range", "start": "a", "end": "z"},
                {"kind": "builtin", "name": "word", "domain": "unicode", "negated": false},
                {"kind": "unicode_property", "property": "Script", "value": "Greek", "negated": true}
            ]
        }),
        4..=6 => json!({
            "node_id": prefix,
            "kind": "repeat",
            "body": literal(format!("node:serialization.{seed}.body"), "r"),
            "min": seed % 3,
            "max": (seed % 3) + 4,
            "mode": match seed % 3 {
                0 => "greedy",
                1 => "lazy",
                _ => "possessive"
            }
        }),
        7 => json!({
            "node_id": prefix,
            "kind": "alternation",
            "branches": [
                literal(format!("node:serialization.{seed}.left"), "a"),
                literal(format!("node:serialization.{seed}.right"), "bc")
            ]
        }),
        8 => json!({
            "node_id": prefix,
            "kind": "sequence",
            "items": [
                {
                    "node_id": format!("node:serialization.{seed}.capture"),
                    "kind": "capture",
                    "capture_id": format!("capture:serialization.{seed}"),
                    "name": format!("capture_{seed}"),
                    "body": literal(format!("node:serialization.{seed}.body"), "c")
                },
                {
                    "node_id": format!("node:serialization.{seed}.reference"),
                    "kind": "backreference",
                    "capture_id": format!("capture:serialization.{seed}")
                }
            ]
        }),
        9 | 10 => json!({
            "node_id": prefix,
            "kind": "lookaround",
            "direction": if seed % 2 == 0 { "ahead" } else { "behind" },
            "polarity": if seed % 3 == 0 { "negative" } else { "positive" },
            "body": literal(format!("node:serialization.{seed}.body"), "l")
        }),
        11 => json!({
            "node_id": prefix,
            "kind": "position",
            "position": match seed % 7 {
                0 => "input_start",
                1 => "input_end",
                2 => "line_start",
                3 => "line_end",
                4 => "word_boundary",
                5 => "not_word_boundary",
                _ => "end_before_final_line_terminator"
            }
        }),
        12 => json!({
            "node_id": prefix,
            "kind": "atomic",
            "body": literal(format!("node:serialization.{seed}.body"), "a")
        }),
        _ => json!({
            "node_id": prefix,
            "kind": "lookaround",
            "direction": "behind",
            "polarity": "positive",
            "body": {
                "node_id": format!("node:serialization.{seed}.body"),
                "kind": "alternation",
                "branches": [
                    literal(format!("node:serialization.{seed}.short"), "x"),
                    literal(format!("node:serialization.{seed}.long"), "yz")
                ]
            }
        }),
    };
    program(root, seed % 5 == 0)
}

fn plan_for(semantic: &SemanticProgram, target: &TargetProfile) -> PortabilityPlan {
    let foundational = analyze(semantic).expect("foundational analysis must succeed");
    let structural =
        analyze_structure(semantic, &foundational).expect("structural analysis must succeed");
    let evaluation = evaluate_capabilities(semantic, &foundational, &structural, target)
        .expect("capability evaluation must succeed");
    plan_portability(semantic, &foundational, &structural, target, &evaluation)
        .expect("portability planning must succeed")
}

#[test]
fn generated_programs_serialize_byte_identically_without_input_mutation() {
    let target = full_pcre2_profile();
    for seed in 0..196 {
        let semantic = generated_program(seed);
        let portability = plan_for(&semantic, &target);
        let lowered = lower_pcre2(&semantic, &target, &portability).expect("lowering");
        let lowered_before = lowered.clone();

        let first = serialize_pcre2(&lowered).expect("first artifact");
        let second = serialize_pcre2(&lowered).expect("second artifact");

        assert_eq!(first, second, "seed {seed}");
        assert_eq!(
            to_json(&first).expect("first JSON"),
            to_json(&second).expect("second JSON"),
            "seed {seed}"
        );
        assert_eq!(
            canonical_sha256(&first).expect("first fingerprint"),
            canonical_sha256(&second).expect("second fingerprint"),
            "seed {seed}"
        );
        assert_eq!(lowered, lowered_before, "seed {seed} mutated lowering plan");
        first
            .validate()
            .unwrap_or_else(|errors| panic!("seed {seed} artifact invalid: {errors}"));
        first
            .validate_against_profile(&target)
            .unwrap_or_else(|errors| panic!("seed {seed} profile mismatch: {errors}"));
        assert!(!first.pattern.text.contains("(*UTF)"), "seed {seed}");
        assert!(!first.pattern.text.contains("(*UCP)"), "seed {seed}");
    }
}

#[test]
fn generated_literal_escape_mutations_are_deterministic_and_utf8_bounded() {
    const PALETTE: &[char] = &[
        '.', '^', '$', '|', '?', '*', '+', '(', ')', '[', ']', '{', '}', '\\', ' ', '#', '\t',
        '\n', '\r', '\u{000b}', '\u{000c}', '\0', 'a', '9', '-', '_', 'é', 'λ', '界',
    ];
    let target = full_pcre2_profile();
    for seed in 0..128_u64 {
        let mut text = String::new();
        for offset in 0..48_u64 {
            let index = usize::try_from((seed * 17 + offset * 11) % PALETTE.len() as u64)
                .expect("palette index");
            text.push(PALETTE[index]);
        }
        let semantic = program(
            literal(format!("node:escape-mutation.{seed}"), &text),
            seed % 2 == 0,
        );
        let portability = plan_for(&semantic, &target);
        let lowered = lower_pcre2(&semantic, &target, &portability).expect("lowering");
        let first = serialize_pcre2(&lowered).expect("first artifact");
        let second = serialize_pcre2(&lowered).expect("second artifact");

        assert_eq!(first.pattern.text, second.pattern.text, "seed {seed}");
        assert!(first
            .pattern
            .text
            .is_char_boundary(first.pattern.text.len()));
        assert!(first.source_map.iter().all(|entry| {
            usize::try_from(entry.generated_span.end)
                .ok()
                .is_some_and(|end| first.pattern.text.is_char_boundary(end))
        }));
    }
}

#[test]
fn generated_noncanonical_option_orders_fail_before_emission() {
    let target = full_pcre2_profile();
    for seed in 0..64_u64 {
        let semantic = generated_program(seed);
        let portability = plan_for(&semantic, &target);
        let mut lowered = lower_pcre2(&semantic, &target, &portability).expect("lowering");
        lowered.options.swap(0, 1);

        let failure = serialize_pcre2(&lowered).expect_err("shuffled options must fail");
        assert_eq!(
            failure.code,
            Pcre2SerializationErrorCode::InvalidLoweringPlan,
            "seed {seed}"
        );
    }
}
