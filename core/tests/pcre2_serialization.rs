use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{ArtifactPortabilityStatus, TargetProfile};
use strling_kernel::target_lowering::{lower_pcre2, Pcre2Operation};
use strling_kernel::target_serialization::{
    serialize_pcre2, Pcre2SerializationErrorCode, MAX_PCRE2_PATTERN_BYTES, MAX_PCRE2_PATTERN_COUNT,
};
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

fn pcre2_without_atomic_groups() -> TargetProfile {
    let mut value = serde_json::to_value(full_pcre2_profile()).expect("profile JSON");
    for capability in value["capabilities"]
        .as_array_mut()
        .expect("capability array")
    {
        if capability["capability_id"] == "groups.atomic" {
            capability["availability"] = json!("unavailable");
        }
    }
    serde_json::from_value(value).expect("atomic-free PCRE2 profile must deserialize")
}

fn program_with_case(root: Value, case_matching: &str) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": case_matching,
        "root": root
    }))
    .expect("test Semantic IR must deserialize")
}

fn program(root: Value) -> SemanticProgram {
    program_with_case(root, "sensitive")
}

fn source_program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "sources": [{
            "contract_version": "1.0.0",
            "source_id": "src:pcre2-serialization",
            "specification_version": "1.0-draft.1",
            "frontend": {
                "id": "semantic_strling",
                "dialect_version": "1.0-draft.1"
            },
            "content": {
                "kind": "inline",
                "encoding": "utf-8",
                "text": "ab"
            },
            "provenance": {"kind": "authored"}
        }],
        "root": root
    }))
    .expect("source-backed Semantic IR must deserialize")
}

fn origin(start: u64, end: u64) -> Value {
    json!({
        "source_spans": [{
            "source_id": "src:pcre2-serialization",
            "coordinate_system": "utf8-bytes",
            "start": start,
            "end": end
        }]
    })
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
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

fn lower(
    semantic: &SemanticProgram,
    target: &TargetProfile,
) -> strling_kernel::target_lowering::Pcre2LoweringPlan {
    let portability = plan_for(semantic, target);
    lower_pcre2(semantic, target, &portability).expect("lowering must succeed")
}

fn all_features_program() -> SemanticProgram {
    program_with_case(
        json!({
            "node_id": "node:emit.root",
            "kind": "sequence",
            "items": [
                {"node_id": "node:emit.empty", "kind": "empty"},
                {
                    "node_id": "node:emit.alternation",
                    "kind": "alternation",
                    "branches": [
                        literal("node:emit.alternation.left", "a"),
                        literal("node:emit.alternation.right", "bc")
                    ]
                },
                {"node_id": "node:emit.wildcard.exclude", "kind": "wildcard", "line_terminators": "exclude"},
                {"node_id": "node:emit.wildcard.include", "kind": "wildcard", "line_terminators": "include"},
                {
                    "node_id": "node:emit.set",
                    "kind": "character_set",
                    "negated": false,
                    "members": [
                        {"kind": "literal", "value": "é"},
                        {"kind": "range", "start": "a", "end": "z"},
                        {"kind": "builtin", "name": "digit", "domain": "ascii", "negated": false},
                        {"kind": "builtin", "name": "word", "domain": "unicode", "negated": true},
                        {"kind": "unicode_property", "property": "Script", "value": "Latin", "negated": false}
                    ]
                },
                {
                    "node_id": "node:emit.repeat.greedy",
                    "kind": "repeat",
                    "body": literal("node:emit.repeat.greedy.body", "g"),
                    "min": 0,
                    "max": null,
                    "mode": "greedy"
                },
                {
                    "node_id": "node:emit.repeat.lazy",
                    "kind": "repeat",
                    "body": literal("node:emit.repeat.lazy.body", "l"),
                    "min": 1,
                    "max": 3,
                    "mode": "lazy"
                },
                {
                    "node_id": "node:emit.repeat.possessive",
                    "kind": "repeat",
                    "body": literal("node:emit.repeat.possessive.body", "p"),
                    "min": 2,
                    "max": 4,
                    "mode": "possessive"
                },
                {"node_id": "node:emit.input-start", "kind": "position", "position": "input_start"},
                {"node_id": "node:emit.input-end", "kind": "position", "position": "input_end"},
                {"node_id": "node:emit.line-start", "kind": "position", "position": "line_start"},
                {"node_id": "node:emit.line-end", "kind": "position", "position": "line_end"},
                {"node_id": "node:emit.word", "kind": "position", "position": "word_boundary"},
                {"node_id": "node:emit.not-word", "kind": "position", "position": "not_word_boundary"},
                {"node_id": "node:emit.final", "kind": "position", "position": "end_before_final_line_terminator"},
                {
                    "node_id": "node:emit.capture.named",
                    "kind": "capture",
                    "capture_id": "capture:emit.named",
                    "name": "word",
                    "body": literal("node:emit.capture.named.body", "n")
                },
                {
                    "node_id": "node:emit.capture.unnamed",
                    "kind": "capture",
                    "capture_id": "capture:emit.unnamed",
                    "body": literal("node:emit.capture.unnamed.body", "u")
                },
                {"node_id": "node:emit.reference.named", "kind": "backreference", "capture_id": "capture:emit.named"},
                {"node_id": "node:emit.reference.unnamed", "kind": "backreference", "capture_id": "capture:emit.unnamed"},
                {
                    "node_id": "node:emit.ahead.positive",
                    "kind": "lookaround",
                    "direction": "ahead",
                    "polarity": "positive",
                    "body": literal("node:emit.ahead.positive.body", "a")
                },
                {
                    "node_id": "node:emit.ahead.negative",
                    "kind": "lookaround",
                    "direction": "ahead",
                    "polarity": "negative",
                    "body": literal("node:emit.ahead.negative.body", "b")
                },
                {
                    "node_id": "node:emit.behind.positive",
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": "positive",
                    "body": literal("node:emit.behind.positive.body", "c")
                },
                {
                    "node_id": "node:emit.behind.negative",
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": "negative",
                    "body": literal("node:emit.behind.negative.body", "d")
                },
                {
                    "node_id": "node:emit.atomic",
                    "kind": "atomic",
                    "body": literal("node:emit.atomic.body", "t")
                }
            ]
        }),
        "insensitive",
    )
}

#[test]
fn every_target_operation_serializes_to_one_valid_deterministic_artifact() {
    let semantic = all_features_program();
    let target = full_pcre2_profile();
    let lowered = lower(&semantic, &target);
    let lowered_before = lowered.clone();

    let artifact = serialize_pcre2(&lowered).expect("serialization must succeed");

    assert_eq!(
        lowered, lowered_before,
        "serialization must not mutate its input"
    );
    artifact.validate().expect("artifact must self-validate");
    artifact
        .validate_against_profile(&target)
        .expect("artifact must resolve against the exact profile");
    assert_eq!(artifact.engine_options.len(), 2);
    assert!(artifact.pattern.text.starts_with("(?i:"));
    assert!(artifact.pattern.text.ends_with(')'));
    assert!(artifact.pattern.text.contains("(?:a|bc)"));
    assert!(artifact.pattern.text.contains(".(?s:.)"));
    assert!(artifact
        .pattern
        .text
        .contains(r"(?:[é]|[a-z]|(?-i:[0-9])|\W|\p{Script=Latin})"));
    assert!(artifact
        .pattern
        .text
        .contains("(?:g)*(?:l){1,3}?(?:p){2,4}+"));
    assert!(artifact.pattern.text.contains(r"\A\z^$\b\B\Z"));
    assert!(artifact.pattern.text.contains(r"(?<word>n)(u)\g{1}\g{2}"));
    assert!(artifact
        .pattern
        .text
        .contains("(?=a)(?!b)(?<=c)(?<!d)(?>t)"));
    assert!(!artifact.pattern.text.contains("(*UTF)"));
    assert!(!artifact.pattern.text.contains("(*UCP)"));
    assert_eq!(artifact.requirements.len(), lowered.requirements.len());
    assert_eq!(
        artifact
            .requirements
            .first()
            .map(|item| item.requirement_id.as_str()),
        Some("requirement:semantic.0000000000")
    );
    assert!(artifact
        .source_map
        .windows(2)
        .all(|pair| { pair[0].generated_span < pair[1].generated_span }));

    let first_json = to_json(&artifact).expect("artifact JSON");
    let second = serialize_pcre2(&lowered).expect("repeated serialization");
    assert_eq!(artifact, second);
    assert_eq!(
        first_json,
        to_json(&second).expect("repeated artifact JSON")
    );
    assert_eq!(
        canonical_sha256(&artifact).expect("artifact fingerprint"),
        canonical_sha256(&second).expect("repeated artifact fingerprint")
    );
}

#[test]
fn literals_classes_options_and_utf8_spans_are_unambiguous() {
    let semantic = program_with_case(literal("node:escaping", ". []{}\\ #\n\0é"), "insensitive");
    let target = full_pcre2_profile();
    let artifact = serialize_pcre2(&lower(&semantic, &target)).expect("artifact");

    assert_eq!(
        artifact.pattern.text,
        r"(?i:\.\x{20}\[\]\{\}\\\x{20}\x{23}\n\x{0}é)"
    );
    assert_eq!(artifact.engine_options[0].option_id.as_str(), "pcre2.ucp");
    assert_eq!(artifact.engine_options[1].option_id.as_str(), "pcre2.utf");
    let pattern_length = u64::try_from(artifact.pattern.text.len()).expect("pattern length");
    let full = artifact
        .source_map
        .iter()
        .find(|entry| entry.generated_span.start == 0 && entry.generated_span.end == pattern_length)
        .expect("full generated mapping");
    assert_eq!(full.generated_span.start, 0);
    assert_eq!(full.generated_span.end, pattern_length);
    assert!(artifact
        .pattern
        .text
        .is_char_boundary(usize::try_from(full.generated_span.end).expect("end offset")));
}

#[test]
fn identical_empty_spans_coalesce_sorted_provenance() {
    let semantic = source_program(json!({
        "node_id": "node:empty.root",
        "kind": "sequence",
        "origin": origin(0, 2),
        "items": [
            {"node_id": "node:empty.left", "kind": "empty", "origin": origin(0, 0)},
            {"node_id": "node:empty.right", "kind": "empty", "origin": origin(1, 1)}
        ]
    }));
    let target = full_pcre2_profile();
    let artifact = serialize_pcre2(&lower(&semantic, &target)).expect("empty artifact");

    assert!(artifact.pattern.text.is_empty());
    assert_eq!(artifact.source_map.len(), 1);
    assert_eq!(artifact.source_map[0].generated_span.start, 0);
    assert_eq!(artifact.source_map[0].generated_span.end, 0);
    assert_eq!(artifact.source_map[0].node_ids.len(), 3);
    assert_eq!(artifact.source_map[0].source_spans.len(), 3);
    artifact.validate().expect("coalesced artifact validates");
}

#[test]
fn certified_rewrite_projects_exact_resolution_without_reapplying_policy() {
    let semantic = program(json!({
        "node_id": "node:rewrite.atomic",
        "kind": "atomic",
        "body": literal("node:rewrite.literal", "a.b")
    }));
    let target = pcre2_without_atomic_groups();
    let lowered = lower(&semantic, &target);
    let artifact = serialize_pcre2(&lowered).expect("rewritten artifact");

    assert_eq!(artifact.pattern.text, r"a\.b");
    assert_eq!(
        artifact.portability_status,
        ArtifactPortabilityStatus::EquivalentRewrite
    );
    assert_eq!(artifact.requirements.len(), 1);
    assert_eq!(
        artifact.requirements[0].resolution_code.as_str(),
        "rewrite.atomic_literal.elide.v1"
    );
    assert_eq!(
        artifact.requirements[0].status,
        ArtifactPortabilityStatus::EquivalentRewrite
    );
}

#[test]
fn malformed_capture_property_bounds_and_plan_fail_closed() {
    let target = full_pcre2_profile();

    let capture_program = program(json!({
        "node_id": "node:bad-capture",
        "kind": "capture",
        "capture_id": "capture:bad-capture",
        "name": "valid_name",
        "body": literal("node:bad-capture.body", "a")
    }));
    let mut capture_plan = lower(&capture_program, &target);
    capture_plan.captures[0].name = Some("bad-name".to_owned());
    let Pcre2Operation::Capture { name, .. } = &mut capture_plan.root.operation else {
        panic!("capture root")
    };
    *name = Some("bad-name".to_owned());
    let failure = serialize_pcre2(&capture_plan).expect_err("invalid capture name");
    assert_eq!(failure.code, Pcre2SerializationErrorCode::InvalidCapture);
    assert_eq!(
        failure.diagnostics[0].phase,
        strling_kernel::diagnostic::CompilerPhase::Emission
    );

    let property_program = program(json!({
        "node_id": "node:bad-property",
        "kind": "character_set",
        "negated": false,
        "members": [{
            "kind": "unicode_property",
            "property": "Script}",
            "value": "Latin",
            "negated": false
        }]
    }));
    let failure =
        serialize_pcre2(&lower(&property_program, &target)).expect_err("invalid property syntax");
    assert_eq!(
        failure.code,
        Pcre2SerializationErrorCode::InvalidUnicodeProperty
    );

    let repetition_program = program(json!({
        "node_id": "node:large-repeat",
        "kind": "repeat",
        "body": literal("node:large-repeat.body", "a"),
        "min": MAX_PCRE2_PATTERN_COUNT + 1,
        "max": MAX_PCRE2_PATTERN_COUNT + 1,
        "mode": "greedy"
    }));
    let failure =
        serialize_pcre2(&lower(&repetition_program, &target)).expect_err("PCRE2 count limit");
    assert_eq!(
        failure.code,
        Pcre2SerializationErrorCode::SyntaxLimitExceeded
    );

    let simple = program(literal("node:bad-plan", "a"));
    let mut bad_plan = lower(&simple, &target);
    bad_plan.options.swap(0, 1);
    let failure = serialize_pcre2(&bad_plan).expect_err("noncanonical option order");
    assert_eq!(
        failure.code,
        Pcre2SerializationErrorCode::InvalidLoweringPlan
    );
}

#[test]
fn pattern_growth_is_resource_bounded() {
    let target = full_pcre2_profile();
    let semantic = program(literal("node:large-pattern", "a"));
    let mut plan = lower(&semantic, &target);
    plan.root.operation = Pcre2Operation::Literal("a".repeat(MAX_PCRE2_PATTERN_BYTES + 1));

    let failure = serialize_pcre2(&plan).expect_err("pattern byte bound");
    assert_eq!(
        failure.code,
        Pcre2SerializationErrorCode::ResourceLimitExceeded
    );
}
