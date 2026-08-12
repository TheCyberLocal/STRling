use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;
use strling_kernel::target_lowering::{lower_pcre2, Pcre2LoweringErrorCode};
use strling_kernel::validation::Validate;

const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");

fn governed_pcre2_profile() -> TargetProfile {
    serde_json::from_str(PCRE2_1043).expect("governed PCRE2 10.43 profile must deserialize")
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
    let prefix = format!("node:property.{seed}");
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
                {
                    "kind": "builtin",
                    "name": "word",
                    "domain": "unicode",
                    "negated": false
                },
                {
                    "kind": "unicode_property",
                    "property": "Script",
                    "value": "Greek",
                    "negated": true
                }
            ]
        }),
        4..=6 => json!({
            "node_id": prefix,
            "kind": "repeat",
            "body": literal(format!("node:property.{seed}.body"), "r"),
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
                literal(format!("node:property.{seed}.left"), "a"),
                literal(format!("node:property.{seed}.right"), "bc")
            ]
        }),
        8 => json!({
            "node_id": prefix,
            "kind": "sequence",
            "items": [
                {
                    "node_id": format!("node:property.{seed}.capture"),
                    "kind": "capture",
                    "capture_id": format!("capture:property.{seed}"),
                    "name": format!("capture_{seed}"),
                    "body": literal(format!("node:property.{seed}.body"), "c")
                },
                {
                    "node_id": format!("node:property.{seed}.reference"),
                    "kind": "backreference",
                    "capture_id": format!("capture:property.{seed}")
                }
            ]
        }),
        9 | 10 => json!({
            "node_id": prefix,
            "kind": "lookaround",
            "direction": if seed % 2 == 0 { "ahead" } else { "behind" },
            "polarity": if seed % 3 == 0 { "negative" } else { "positive" },
            "body": literal(format!("node:property.{seed}.body"), "l")
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
            "body": literal(format!("node:property.{seed}.body"), "a")
        }),
        _ => json!({
            "node_id": prefix,
            "kind": "lookaround",
            "direction": "behind",
            "polarity": "positive",
            "body": {
                "node_id": format!("node:property.{seed}.body"),
                "kind": "alternation",
                "branches": [
                    literal(format!("node:property.{seed}.short"), "x"),
                    literal(format!("node:property.{seed}.long"), "yz")
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
fn generated_valid_programs_lower_deterministically_without_input_mutation() {
    let target = governed_pcre2_profile();
    for seed in 0..196 {
        let semantic = generated_program(seed);
        let portability = plan_for(&semantic, &target);
        let semantic_before = semantic.clone();
        let target_before = target.clone();
        let portability_before = portability.clone();

        let first = lower_pcre2(&semantic, &target, &portability).expect("first lowering");
        let second = lower_pcre2(&semantic, &target, &portability).expect("second lowering");

        assert_eq!(first, second, "seed {seed} must be deterministic");
        first
            .validate()
            .unwrap_or_else(|errors| panic!("seed {seed} must self-validate: {errors}"));
        assert_eq!(semantic, semantic_before, "seed {seed} mutated Semantic IR");
        assert_eq!(target, target_before, "seed {seed} mutated target profile");
        assert_eq!(
            portability, portability_before,
            "seed {seed} mutated portability plan"
        );
        assert_eq!(first.target_profile, target.reference().expect("reference"));
        assert_eq!(first.semantic_program, portability.semantic_program);
        assert_eq!(first.requirements.len(), portability.decisions.len());
    }
}

#[test]
fn generated_cross_program_evidence_is_always_rejected() {
    let target = governed_pcre2_profile();
    for seed in 0..64 {
        let planned = generated_program(seed);
        let supplied = program(
            literal(
                format!("node:cross-program.{seed}"),
                if seed % 2 == 0 { "left" } else { "right" },
            ),
            false,
        );
        let portability = plan_for(&planned, &target);

        let failure = lower_pcre2(&supplied, &target, &portability)
            .expect_err("foreign planner evidence must fail");
        assert_eq!(
            failure.code,
            Pcre2LoweringErrorCode::ProgramFingerprintMismatch,
            "seed {seed}"
        );
    }
}
