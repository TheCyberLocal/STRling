use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::python_re_lowering::{lower_python_re, PythonReOperation};
use strling_kernel::python_re_serialization::{
    serialize_python_re, PythonReSerializationErrorCode,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::{canonical_sha256, to_json, Validate};

const PYTHON_STR: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");
const PYTHON_BYTES: &str = include_str!("../../spec/targets/profiles/python-re-3.11-bytes.json");

fn str_profile() -> TargetProfile {
    serde_json::from_str(PYTHON_STR).expect("governed Python str profile")
}

fn bytes_profile() -> TargetProfile {
    serde_json::from_str(PYTHON_BYTES).expect("governed Python bytes profile")
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

fn generated_program(seed: u32, bytes: bool) -> SemanticProgram {
    let prefix = format!("node:generated.{seed}");
    let root = match seed % 8 {
        0 => literal(
            format!("{prefix}.literal"),
            if bytes {
                format!("value-{seed}.[]{{}}#\n")
            } else {
                format!("value-{seed}.[]{{}}#é😀\n")
            },
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
                {
                    "kind": "builtin",
                    "name": "digit",
                    "domain": if bytes { "ascii" } else { "unicode" },
                    "negated": false
                }
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
        6 if bytes => json!({
            "node_id": format!("{prefix}.positions"),
            "kind": "sequence",
            "items": [
                {"node_id": format!("{prefix}.start"), "kind": "position", "position": "input_start"},
                literal(format!("{prefix}.literal"), "x"),
                {"node_id": format!("{prefix}.end"), "kind": "position", "position": "input_end"}
            ]
        }),
        6 => json!({
            "node_id": format!("{prefix}.positions"),
            "kind": "sequence",
            "items": [
                {"node_id": format!("{prefix}.start"), "kind": "position", "position": "input_start"},
                {"node_id": format!("{prefix}.wildcard.exclude"), "kind": "wildcard", "line_terminators": "exclude"},
                {"node_id": format!("{prefix}.wildcard.include"), "kind": "wildcard", "line_terminators": "include"},
                {"node_id": format!("{prefix}.end"), "kind": "position", "position": "input_end"}
            ]
        }),
        _ => json!({
            "node_id": format!("{prefix}.atomic-sequence"),
            "kind": "sequence",
            "items": [
                {
                    "node_id": format!("{prefix}.atomic"),
                    "kind": "atomic",
                    "body": {
                        "node_id": format!("{prefix}.atomic.choice"),
                        "kind": "alternation",
                        "branches": [
                            literal(format!("{prefix}.atomic.left"), "ab"),
                            literal(format!("{prefix}.atomic.right"), "a")
                        ]
                    }
                },
                {
                    "node_id": format!("{prefix}.possessive"),
                    "kind": "repeat",
                    "body": literal(format!("{prefix}.possessive.body"), "z"),
                    "min": 1,
                    "max": null,
                    "mode": "possessive"
                }
            ]
        }),
    };
    program(root)
}

fn lower(
    semantic: &SemanticProgram,
    target: &TargetProfile,
) -> strling_kernel::python_re_lowering::PythonReLoweringPlan {
    let foundational = analyze(semantic).expect("foundational analysis");
    let structural = analyze_structure(semantic, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(semantic, &foundational, &structural, target)
        .expect("capability evaluation");
    let portability = plan_portability(semantic, &foundational, &structural, target, &evaluation)
        .expect("portability planning");
    lower_python_re(semantic, target, &portability).expect("Python re lowering")
}

#[test]
fn generated_str_and_bytes_programs_are_deterministic_and_immutable() {
    for (target, bytes) in [(str_profile(), false), (bytes_profile(), true)] {
        for seed in 0..196_u32 {
            let semantic = generated_program(seed, bytes);
            let lowered = lower(&semantic, &target);
            let before = lowered.clone();
            let first = serialize_python_re(&lowered)
                .unwrap_or_else(|error| panic!("bytes={bytes} seed={seed}: {error}"));
            let second = serialize_python_re(&lowered).expect("repeated artifact");

            assert_eq!(lowered, before, "bytes={bytes} seed={seed} mutated input");
            assert_eq!(first, second, "bytes={bytes} seed={seed} typed drift");
            assert_eq!(
                to_json(&first).expect("first JSON"),
                to_json(&second).expect("second JSON"),
                "bytes={bytes} seed={seed} JSON drift"
            );
            assert_eq!(
                canonical_sha256(&first).expect("first digest"),
                canonical_sha256(&second).expect("second digest"),
                "bytes={bytes} seed={seed} fingerprint drift"
            );
            first.validate().unwrap_or_else(|errors| {
                panic!("bytes={bytes} seed={seed} invalid artifact: {errors}")
            });
            first
                .validate_against_profile(&target)
                .unwrap_or_else(|errors| {
                    panic!("bytes={bytes} seed={seed} profile mismatch: {errors}")
                });
            if bytes {
                assert!(first.pattern.text.is_ascii(), "seed={seed}");
            }
        }
    }
}

#[test]
fn escape_palette_mutations_preserve_utf8_boundaries() {
    let target = str_profile();
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
        let first = serialize_python_re(&lowered).expect("first escaped artifact");
        let second = serialize_python_re(&lowered).expect("second escaped artifact");
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
fn profile_and_pattern_kind_mutations_fail_closed() {
    for (target, bytes) in [(str_profile(), false), (bytes_profile(), true)] {
        for seed in 0..64_u32 {
            let semantic = generated_program(seed, bytes);
            let mut lowered = lower(&semantic, &target);
            lowered.options.clear();
            let failure = serialize_python_re(&lowered).expect_err("missing pattern kind");
            assert_eq!(
                failure.code,
                PythonReSerializationErrorCode::InvalidLoweringPlan,
                "bytes={bytes} seed={seed}"
            );
        }
    }

    let semantic = generated_program(0, false);
    let mut wrong_kind = lower(&semantic, &str_profile());
    wrong_kind.pattern_kind = strling_kernel::python_re_lowering::PythonRePatternKind::Bytes;
    let failure = serialize_python_re(&wrong_kind).expect_err("cross-kind mutation");
    assert!(matches!(
        failure.code,
        PythonReSerializationErrorCode::InvalidLoweringPlan
            | PythonReSerializationErrorCode::InvalidFlags
    ));
}

#[test]
fn malformed_range_mutations_are_rejected_without_panicking() {
    let semantic = program(json!({
        "node_id": "node:range",
        "kind": "character_set",
        "negated": false,
        "members": [{"kind": "range", "start": "a", "end": "z"}]
    }));
    let mut lowered = lower(&semantic, &str_profile());
    let PythonReOperation::CharacterSet { members, .. } = &mut lowered.root.operation else {
        panic!("set root")
    };
    members[0] = strling_kernel::python_re_lowering::PythonReCharacterSetMember::Range {
        start: 'z',
        end: 'a',
    };
    let failure = serialize_python_re(&lowered).expect_err("reversed range");
    assert_eq!(
        failure.code,
        PythonReSerializationErrorCode::InvalidLoweringPlan
    );
}
