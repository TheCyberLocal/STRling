use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::ecmascript_lowering::lower_ecmascript;
use strling_kernel::ecmascript_serialization::{
    serialize_ecmascript, EcmascriptSerializationErrorCode,
};
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::{canonical_sha256, to_json, Validate};

const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

fn profile() -> TargetProfile {
    serde_json::from_str(ECMASCRIPT).expect("governed ECMAScript profile")
}

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("generated Semantic IR")
}

fn literal(node_id: impl Into<String>, text: impl Into<String>) -> Value {
    json!({"node_id": node_id.into(), "kind": "literal", "text": text.into()})
}

fn generated_program(seed: u32) -> SemanticProgram {
    let prefix = format!("node:generated.{seed}");
    let root = match seed % 7 {
        0 => literal(
            format!("{prefix}.literal"),
            format!("value-{seed}.[]{{}}/é😀\n"),
        ),
        1 => json!({
            "node_id": format!("{prefix}.alternation"),
            "kind": "alternation",
            "branches": [
                literal(format!("{prefix}.left"), format!("a{seed}")),
                {
                    "node_id": format!("{prefix}.sequence"),
                    "kind": "sequence",
                    "items": [
                        literal(format!("{prefix}.middle"), "bc"),
                        {"node_id": format!("{prefix}.empty"), "kind": "empty"}
                    ]
                }
            ]
        }),
        2 => json!({
            "node_id": format!("{prefix}.repeat"),
            "kind": "repeat",
            "body": {
                "node_id": format!("{prefix}.repeat.alternation"),
                "kind": "alternation",
                "branches": [
                    literal(format!("{prefix}.repeat.left"), "x"),
                    literal(format!("{prefix}.repeat.right"), "yz")
                ]
            },
            "min": seed % 3,
            "max": seed % 3 + 3,
            "mode": if seed % 2 == 0 { "greedy" } else { "lazy" }
        }),
        3 => json!({
            "node_id": format!("{prefix}.set"),
            "kind": "character_set",
            "negated": seed % 2 == 0,
            "members": [
                {"kind": "literal", "value": "]"},
                {"kind": "range", "start": "a", "end": "f"},
                {"kind": "builtin", "name": "digit", "domain": "unicode", "negated": false},
                {"kind": "unicode_property", "property": "Script", "value": "Greek", "negated": seed % 3 == 0}
            ]
        }),
        4 => json!({
            "node_id": format!("{prefix}.captures"),
            "kind": "sequence",
            "items": [
                {
                    "node_id": format!("{prefix}.capture"),
                    "kind": "capture",
                    "capture_id": format!("capture:generated.{seed}"),
                    "name": format!("capture_{seed}"),
                    "body": literal(format!("{prefix}.capture.body"), "word")
                },
                {
                    "node_id": format!("{prefix}.reference"),
                    "kind": "backreference",
                    "capture_id": format!("capture:generated.{seed}")
                }
            ]
        }),
        5 => json!({
            "node_id": format!("{prefix}.lookaround"),
            "kind": "sequence",
            "items": [
                {
                    "node_id": format!("{prefix}.behind"),
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": if seed % 2 == 0 { "positive" } else { "negative" },
                    "body": literal(format!("{prefix}.behind.body"), "pre")
                },
                literal(format!("{prefix}.subject"), "value"),
                {
                    "node_id": format!("{prefix}.ahead"),
                    "kind": "lookaround",
                    "direction": "ahead",
                    "polarity": "positive",
                    "body": literal(format!("{prefix}.ahead.body"), "post")
                }
            ]
        }),
        _ => json!({
            "node_id": format!("{prefix}.positions"),
            "kind": "sequence",
            "items": [
                {"node_id": format!("{prefix}.start"), "kind": "position", "position": "input_start"},
                {"node_id": format!("{prefix}.wildcard.exclude"), "kind": "wildcard", "line_terminators": "exclude"},
                {"node_id": format!("{prefix}.wildcard.include"), "kind": "wildcard", "line_terminators": "include"},
                {"node_id": format!("{prefix}.end"), "kind": "position", "position": "input_end"}
            ]
        }),
    };
    program(root)
}

fn lower(
    semantic: &SemanticProgram,
    target: &TargetProfile,
) -> strling_kernel::ecmascript_lowering::EcmascriptLoweringPlan {
    let foundational = analyze(semantic).expect("foundational analysis");
    let structural = analyze_structure(semantic, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(semantic, &foundational, &structural, target)
        .expect("capability evaluation");
    let portability = plan_portability(semantic, &foundational, &structural, target, &evaluation)
        .expect("portability planning");
    lower_ecmascript(semantic, target, &portability).expect("ECMAScript lowering")
}

#[test]
fn generated_programs_serialize_deterministically_without_input_mutation() {
    let target = profile();
    for seed in 0..196_u32 {
        let semantic = generated_program(seed);
        let lowered = lower(&semantic, &target);
        let before = lowered.clone();
        let first = serialize_ecmascript(&lowered)
            .unwrap_or_else(|error| panic!("seed {seed} first artifact: {error}"));
        let second = serialize_ecmascript(&lowered)
            .unwrap_or_else(|error| panic!("seed {seed} second artifact: {error}"));

        assert_eq!(lowered, before, "seed {seed} mutated lowering plan");
        assert_eq!(first, second, "seed {seed} typed artifact drift");
        assert_eq!(
            to_json(&first).expect("first JSON"),
            to_json(&second).expect("second JSON"),
            "seed {seed} JSON drift"
        );
        assert_eq!(
            canonical_sha256(&first).expect("first digest"),
            canonical_sha256(&second).expect("second digest"),
            "seed {seed} fingerprint drift"
        );
        first
            .validate()
            .unwrap_or_else(|errors| panic!("seed {seed} invalid artifact: {errors}"));
        first
            .validate_against_profile(&target)
            .unwrap_or_else(|errors| panic!("seed {seed} profile mismatch: {errors}"));
    }
}

#[test]
fn escape_palette_mutations_are_deterministic_and_valid_utf8() {
    let target = profile();
    let palette = [
        '.', '^', '$', '|', '?', '*', '+', '(', ')', '[', ']', '{', '}', '\\', '/', '-', '#', ' ',
        '\t', '\n', '\r', '\u{000b}', '\u{000c}', '\0', '\u{007f}', '\u{0085}', '\u{2028}',
        '\u{2029}', 'é', 'λ', '界', '😀', '𐐷', '_', '9', 'A', 'z', '&', '!', ':',
    ];
    for seed in 0..128_usize {
        let text = (0..48)
            .map(|offset| palette[(seed * 17 + offset * 11) % palette.len()])
            .collect::<String>();
        let semantic = program(literal(format!("node:escape.{seed}"), text));
        let lowered = lower(&semantic, &target);
        let first = serialize_ecmascript(&lowered).expect("first escaped artifact");
        let second = serialize_ecmascript(&lowered).expect("second escaped artifact");
        assert_eq!(first.pattern.text, second.pattern.text, "seed {seed}");
        assert!(first.source_map.iter().all(|entry| first
            .pattern
            .text
            .is_char_boundary(entry.generated_span.start as usize)
            && first
                .pattern
                .text
                .is_char_boundary(entry.generated_span.end as usize)));
    }
}

#[test]
fn missing_profile_flag_intent_is_rejected_for_generated_plans() {
    let target = profile();
    for seed in 0..64_u32 {
        let semantic = generated_program(seed);
        let mut lowered = lower(&semantic, &target);
        lowered.options.clear();
        let failure = serialize_ecmascript(&lowered).expect_err("missing Unicode option");
        assert_eq!(
            failure.code,
            EcmascriptSerializationErrorCode::InvalidFlags,
            "seed {seed}"
        );
    }
}
