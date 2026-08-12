use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::python_re_lowering::{
    lower_python_re, PythonReCharacterSetMember, PythonReOperation, PythonReRepetitionMaximum,
};
use strling_kernel::python_re_serialization::{
    serialize_python_re, PythonReSerializationErrorCode, MAX_PYTHON_RE_PATTERN_BYTES,
    MAX_PYTHON_RE_REPETITION,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{ArtifactPortabilityStatus, TargetProfile};
use strling_kernel::validation::{canonical_sha256, to_json, Validate};

const PYTHON_STR: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");
const PYTHON_BYTES: &str = include_str!("../../spec/targets/profiles/python-re-3.11-bytes.json");

fn str_profile() -> TargetProfile {
    serde_json::from_str(PYTHON_STR).expect("governed Python str profile")
}

fn bytes_profile() -> TargetProfile {
    serde_json::from_str(PYTHON_BYTES).expect("governed Python bytes profile")
}

fn program_with_case(root: Value, case_matching: &str) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": case_matching,
        "root": root
    }))
    .expect("test Semantic IR")
}

fn program(root: Value) -> SemanticProgram {
    program_with_case(root, "sensitive")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn plan_for(semantic: &SemanticProgram, target: &TargetProfile) -> PortabilityPlan {
    let foundational = analyze(semantic).expect("foundational analysis");
    let structural = analyze_structure(semantic, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(semantic, &foundational, &structural, target)
        .expect("capability evaluation");
    plan_portability(semantic, &foundational, &structural, target, &evaluation)
        .expect("portability planning")
}

fn lower(
    semantic: &SemanticProgram,
    target: &TargetProfile,
) -> strling_kernel::python_re_lowering::PythonReLoweringPlan {
    let portability = plan_for(semantic, target);
    lower_python_re(semantic, target, &portability).expect("Python re lowering")
}

#[test]
fn str_artifact_projects_exact_flags_options_requirements_and_utf8_provenance() {
    let semantic = program_with_case(
        json!({
            "node_id": "node:artifact.root",
            "kind": "sequence",
            "items": [
                literal("node:artifact.literal", ". #\n\0é😀"),
                {
                    "node_id": "node:artifact.wildcard",
                    "kind": "wildcard",
                    "line_terminators": "include"
                },
                {
                    "node_id": "node:artifact.repeat",
                    "kind": "repeat",
                    "body": literal("node:artifact.repeat.body", "q"),
                    "min": 1,
                    "max": 3,
                    "mode": "lazy"
                }
            ]
        }),
        "insensitive",
    );
    let target = str_profile();
    let lowered = lower(&semantic, &target);
    let before = lowered.clone();
    let artifact = serialize_python_re(&lowered).expect("Python str artifact");

    assert_eq!(lowered, before, "serialization must not mutate its input");
    assert_eq!(artifact.pattern.flags, vec!["i".to_owned()]);
    assert_eq!(
        artifact.pattern.text,
        r"\.\x20\x23\x0a\x00é😀(?s:.)(?:q){1,3}?"
    );
    assert_eq!(artifact.engine_options.len(), 1);
    assert_eq!(
        artifact.engine_options[0].option_id.as_str(),
        "python.pattern_kind"
    );
    assert!(matches!(
        &artifact.engine_options[0].value,
        strling_kernel::target::EngineOptionValue::String(value) if value == "str"
    ));
    assert_eq!(
        artifact.portability_status,
        ArtifactPortabilityStatus::Native
    );
    assert!(artifact.emission_diagnostics.is_empty());
    assert!(artifact
        .source_map
        .windows(2)
        .all(|pair| pair[0].generated_span < pair[1].generated_span));
    assert!(artifact.source_map.iter().all(|entry| {
        artifact
            .pattern
            .text
            .is_char_boundary(entry.generated_span.start as usize)
            && artifact
                .pattern
                .text
                .is_char_boundary(entry.generated_span.end as usize)
    }));
    artifact.validate().expect("artifact self-validation");
    artifact
        .validate_against_profile(&target)
        .expect("artifact resolves against exact str profile");

    let first_json = to_json(&artifact).expect("artifact JSON");
    let second = serialize_python_re(&lowered).expect("repeated artifact");
    assert_eq!(artifact, second);
    assert_eq!(first_json, to_json(&second).expect("repeated JSON"));
    assert_eq!(
        canonical_sha256(&artifact).expect("artifact digest"),
        canonical_sha256(&second).expect("repeated artifact digest")
    );
}

#[test]
fn operation_spellings_preserve_precedence_positions_captures_and_assertions() {
    let semantic = program(json!({
        "node_id": "node:syntax.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:syntax.alternation",
                "kind": "alternation",
                "branches": [
                    literal("node:syntax.alternation.left", "a"),
                    literal("node:syntax.alternation.right", "bc")
                ]
            },
            {"node_id": "node:syntax.input-start", "kind": "position", "position": "input_start"},
            {"node_id": "node:syntax.input-end", "kind": "position", "position": "input_end"},
            {"node_id": "node:syntax.line-start", "kind": "position", "position": "line_start"},
            {"node_id": "node:syntax.line-end", "kind": "position", "position": "line_end"},
            {"node_id": "node:syntax.final", "kind": "position", "position": "end_before_final_line_terminator"},
            {"node_id": "node:syntax.word", "kind": "position", "position": "word_boundary"},
            {"node_id": "node:syntax.not-word", "kind": "position", "position": "not_word_boundary"},
            {
                "node_id": "node:syntax.capture.named",
                "kind": "capture",
                "capture_id": "capture:syntax.named",
                "name": "word",
                "body": literal("node:syntax.capture.named.body", "n")
            },
            {
                "node_id": "node:syntax.reference.named",
                "kind": "backreference",
                "capture_id": "capture:syntax.named"
            },
            {
                "node_id": "node:syntax.capture.numbered",
                "kind": "capture",
                "capture_id": "capture:syntax.numbered",
                "body": literal("node:syntax.capture.numbered.body", "x")
            },
            {
                "node_id": "node:syntax.reference.numbered",
                "kind": "backreference",
                "capture_id": "capture:syntax.numbered"
            },
            {
                "node_id": "node:syntax.ahead",
                "kind": "lookaround",
                "direction": "ahead",
                "polarity": "negative",
                "body": literal("node:syntax.ahead.body", "z")
            },
            {
                "node_id": "node:syntax.behind",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "positive",
                "body": literal("node:syntax.behind.body", "y")
            },
            {
                "node_id": "node:syntax.atomic",
                "kind": "atomic",
                "body": literal("node:syntax.atomic.body", "q")
            },
            {
                "node_id": "node:syntax.possessive",
                "kind": "repeat",
                "body": literal("node:syntax.possessive.body", "p"),
                "min": 1,
                "max": null,
                "mode": "possessive"
            }
        ]
    }));
    let artifact = serialize_python_re(&lower(&semantic, &str_profile())).expect("artifact");
    assert!(artifact.pattern.flags.is_empty());
    assert_eq!(
        artifact.pattern.text,
        r"(?:a|bc)\A\Z(?m:^)(?m:$)$\b\B(?P<word>n)(?:(?P=word))(x)(?:\2)(?!z)(?<=y)(?>q)(?:p)++"
    );
}

#[test]
fn character_sets_keep_ascii_unicode_and_outer_negation_scoped() {
    let semantic = program(json!({
        "node_id": "node:sets.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:sets.mixed",
                "kind": "character_set",
                "negated": false,
                "members": [
                    {"kind": "builtin", "name": "digit", "domain": "ascii", "negated": false},
                    {"kind": "builtin", "name": "word", "domain": "unicode", "negated": false}
                ]
            },
            {
                "node_id": "node:sets.outer-negative",
                "kind": "character_set",
                "negated": true,
                "members": [
                    {"kind": "literal", "value": "-"},
                    {"kind": "builtin", "name": "word", "domain": "ascii", "negated": false}
                ]
            }
        ]
    }));
    let artifact = serialize_python_re(&lower(&semantic, &str_profile())).expect("artifact");
    assert_eq!(
        artifact.pattern.text,
        r"(?:(?a:\d)|(?u:\w))(?!(?:[\x2d]|(?a:\w)))(?s:.)"
    );
}

#[test]
fn bytes_artifact_uses_its_exact_profile_and_ascii_pattern_source() {
    let semantic = program_with_case(
        json!({
            "node_id": "node:bytes.root",
            "kind": "sequence",
            "items": [
                {
                    "node_id": "node:bytes.capture",
                    "kind": "capture",
                    "capture_id": "capture:bytes.word",
                    "name": "word",
                    "body": literal("node:bytes.capture.body", "A#")
                },
                {
                    "node_id": "node:bytes.reference",
                    "kind": "backreference",
                    "capture_id": "capture:bytes.word"
                },
                {
                    "node_id": "node:bytes.word",
                    "kind": "character_set",
                    "negated": false,
                    "members": [
                        {"kind": "builtin", "name": "word", "domain": "ascii", "negated": false}
                    ]
                }
            ]
        }),
        "insensitive",
    );
    let target = bytes_profile();
    let artifact = serialize_python_re(&lower(&semantic, &target)).expect("bytes artifact");
    assert_eq!(artifact.pattern.flags, vec!["i".to_owned()]);
    assert!(artifact.pattern.text.is_ascii());
    assert_eq!(
        artifact.pattern.text,
        r"(?P<word>A\x23)(?:(?P=word))(?a:\w)"
    );
    assert!(matches!(
        &artifact.engine_options[0].value,
        strling_kernel::target::EngineOptionValue::String(value) if value == "bytes"
    ));
    artifact
        .validate_against_profile(&target)
        .expect("artifact resolves against exact bytes profile");
}

#[test]
fn malformed_plans_and_python_syntax_limits_fail_closed_with_stable_codes() {
    let target = str_profile();
    let simple = program(literal("node:fail.simple", "a"));

    let mut wrong_profile = lower(&simple, &target);
    wrong_profile.target_profile.sha256 = strling_kernel::source::Sha256Digest::try_from(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    .expect("digest shape");
    assert_eq!(
        serialize_python_re(&wrong_profile)
            .expect_err("stale profile")
            .code,
        PythonReSerializationErrorCode::InvalidFlags
    );

    let capture_program = program(json!({
        "node_id": "node:fail.capture",
        "kind": "capture",
        "capture_id": "capture:fail.capture",
        "name": "valid",
        "body": literal("node:fail.capture.body", "a")
    }));
    let mut capture_plan = lower(&capture_program, &target);
    let PythonReOperation::Capture { name, .. } = &mut capture_plan.root.operation else {
        panic!("capture root")
    };
    *name = Some("bad-name".to_owned());
    assert_eq!(
        serialize_python_re(&capture_plan)
            .expect_err("invalid capture name")
            .code,
        PythonReSerializationErrorCode::InvalidCapture
    );

    let set_program = program(json!({
        "node_id": "node:fail.set",
        "kind": "character_set",
        "negated": false,
        "members": [{"kind": "literal", "value": "a"}]
    }));
    let mut property_plan = lower(&set_program, &target);
    let PythonReOperation::CharacterSet { members, .. } = &mut property_plan.root.operation else {
        panic!("character-set root")
    };
    members[0] = PythonReCharacterSetMember::UnicodeProperty {
        property: "Script".to_owned(),
        value: Some("Latin".to_owned()),
        negated: false,
    };
    assert_eq!(
        serialize_python_re(&property_plan)
            .expect_err("unsupported property")
            .code,
        PythonReSerializationErrorCode::UnsupportedUnicodeProperty
    );

    let bytes_target = bytes_profile();
    let mut non_ascii_bytes = lower(&simple, &bytes_target);
    non_ascii_bytes.root.operation = PythonReOperation::Literal("é".to_owned());
    assert_eq!(
        serialize_python_re(&non_ascii_bytes)
            .expect_err("non-ASCII bytes source")
            .code,
        PythonReSerializationErrorCode::PatternKindMismatch
    );

    let mut excessive_repeat = lower(&simple, &target);
    excessive_repeat.root.operation = PythonReOperation::Repeat {
        body: Box::new(excessive_repeat.root.clone()),
        min: MAX_PYTHON_RE_REPETITION + 1,
        max: PythonReRepetitionMaximum::Unbounded,
        mode: strling_kernel::python_re_lowering::PythonReRepetitionMode::Greedy,
    };
    assert_eq!(
        serialize_python_re(&excessive_repeat)
            .expect_err("repetition syntax bound")
            .code,
        PythonReSerializationErrorCode::SyntaxLimitExceeded
    );

    let mut huge = lower(&simple, &target);
    huge.root.operation = PythonReOperation::Literal("a".repeat(MAX_PYTHON_RE_PATTERN_BYTES + 1));
    assert_eq!(
        serialize_python_re(&huge)
            .expect_err("pattern size bound")
            .code,
        PythonReSerializationErrorCode::ResourceLimitExceeded
    );
}
