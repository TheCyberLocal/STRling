use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::ecmascript_lowering::{
    lower_ecmascript, EcmascriptCharacterSetMember, EcmascriptOperation,
};
use strling_kernel::ecmascript_serialization::{
    serialize_ecmascript, EcmascriptSerializationErrorCode, MAX_ECMASCRIPT_PATTERN_BYTES,
};
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{ArtifactPortabilityStatus, TargetProfile};
use strling_kernel::validation::{canonical_sha256, to_json, Validate};

const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

fn profile() -> TargetProfile {
    serde_json::from_str(ECMASCRIPT).expect("governed ECMAScript profile")
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
) -> strling_kernel::ecmascript_lowering::EcmascriptLoweringPlan {
    let portability = plan_for(semantic, target);
    lower_ecmascript(semantic, target, &portability).expect("ECMAScript lowering")
}

#[test]
fn artifact_projects_exact_flags_options_requirements_and_utf8_provenance() {
    let semantic = program_with_case(
        json!({
            "node_id": "node:artifact.root",
            "kind": "sequence",
            "items": [
                literal("node:artifact.literal", ". /\n\0é😀"),
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
    let target = profile();
    let lowered = lower(&semantic, &target);
    let before = lowered.clone();
    let artifact = serialize_ecmascript(&lowered).expect("ECMAScript artifact");

    assert_eq!(
        lowered, before,
        "serialization must borrow without mutation"
    );
    assert_eq!(artifact.pattern.flags, vec!["i".to_owned(), "u".to_owned()]);
    assert_eq!(artifact.pattern.text, r"\.\x20\/\n\x00é😀[\s\S](?:q){1,3}?");
    assert_eq!(artifact.engine_options.len(), 1);
    assert_eq!(
        artifact.engine_options[0].option_id.as_str(),
        "ecmascript.unicode_mode"
    );
    assert_eq!(
        artifact.portability_status,
        ArtifactPortabilityStatus::Native
    );
    assert!(artifact.emission_diagnostics.is_empty());
    assert!(artifact
        .source_map
        .windows(2)
        .all(|pair| pair[0].generated_span < pair[1].generated_span));
    assert!(artifact
        .source_map
        .iter()
        .all(|entry| entry.generated_span.end as usize <= artifact.pattern.text.len()));
    artifact.validate().expect("artifact self-validation");
    artifact
        .validate_against_profile(&target)
        .expect("artifact resolves against exact profile");

    let first_json = to_json(&artifact).expect("artifact JSON");
    let second = serialize_ecmascript(&lowered).expect("repeated artifact");
    assert_eq!(artifact, second);
    assert_eq!(first_json, to_json(&second).expect("repeated JSON"));
    assert_eq!(
        canonical_sha256(&artifact).expect("artifact digest"),
        canonical_sha256(&second).expect("repeated artifact digest")
    );
}

#[test]
fn operation_spellings_preserve_precedence_positions_captures_and_lookarounds() {
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
            }
        ]
    }));
    let artifact = serialize_ecmascript(&lower(&semantic, &profile())).expect("artifact");
    assert_eq!(artifact.pattern.flags, vec!["u".to_owned()]);
    assert_eq!(
        artifact.pattern.text,
        r"(?:a|bc)^(?![\s\S])(?:^|(?<=[\n\r\u2028\u2029]))(?=$|[\n\r\u2028\u2029])(?=$|(?:\r\n|[\r\u2028\u2029]|(?<!\r)\n)(?![\s\S]))\b\B(?<word>n)(?:\k<word>)(x)(?:\2)(?!z)(?<=y)"
    );
}

#[test]
fn character_sets_use_independent_ascii_unicode_and_mixed_set_spellings() {
    let semantic = program(json!({
        "node_id": "node:sets.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:sets.ascii",
                "kind": "character_set",
                "negated": false,
                "members": [
                    {"kind": "builtin", "name": "digit", "domain": "ascii", "negated": false},
                    {"kind": "builtin", "name": "whitespace", "domain": "ascii", "negated": true}
                ]
            },
            {
                "node_id": "node:sets.unicode",
                "kind": "character_set",
                "negated": false,
                "members": [
                    {"kind": "builtin", "name": "digit", "domain": "unicode", "negated": false},
                    {"kind": "builtin", "name": "word", "domain": "unicode", "negated": false},
                    {"kind": "unicode_property", "property": "Script", "value": "Greek", "negated": false}
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
    let artifact = serialize_ecmascript(&lower(&semantic, &profile())).expect("artifact");
    assert_eq!(
        artifact.pattern.text,
        r"(?:[0-9]|[^\x09-\x0d\x20])(?:\p{Decimal_Number}|[\p{Letter}\p{Number}\p{Nonspacing_Mark}\p{Connector_Punctuation}]|\p{Script=Greek})(?!(?:[\x2d]|[A-Za-z0-9_]))[\s\S]"
    );
}

#[test]
fn certified_atomic_literal_rewrite_projects_without_atomic_syntax() {
    let semantic = program(json!({
        "node_id": "node:rewrite.atomic",
        "kind": "atomic",
        "body": literal("node:rewrite.literal", "a.b")
    }));
    let artifact = serialize_ecmascript(&lower(&semantic, &profile())).expect("rewrite artifact");
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
    assert!(!artifact.pattern.text.contains("?>"));
}

#[test]
fn malformed_plans_and_syntax_data_fail_closed_with_stable_codes() {
    let target = profile();
    let simple = program(literal("node:fail.simple", "a"));

    let mut wrong_profile = lower(&simple, &target);
    wrong_profile.target_profile.sha256 = strling_kernel::source::Sha256Digest::try_from(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    .expect("digest shape");
    assert_eq!(
        serialize_ecmascript(&wrong_profile)
            .expect_err("stale profile")
            .code,
        EcmascriptSerializationErrorCode::InvalidFlags
    );

    let capture_program = program(json!({
        "node_id": "node:fail.capture",
        "kind": "capture",
        "capture_id": "capture:fail.capture",
        "name": "valid",
        "body": literal("node:fail.capture.body", "a")
    }));
    let mut capture_plan = lower(&capture_program, &target);
    let EcmascriptOperation::Capture { name, .. } = &mut capture_plan.root.operation else {
        panic!("capture root")
    };
    *name = Some("bad-name".to_owned());
    assert_eq!(
        serialize_ecmascript(&capture_plan)
            .expect_err("invalid capture name")
            .code,
        EcmascriptSerializationErrorCode::InvalidCapture
    );

    let property_program = program(json!({
        "node_id": "node:fail.property",
        "kind": "character_set",
        "negated": false,
        "members": [{
            "kind": "unicode_property",
            "property": "Script",
            "value": "Latin",
            "negated": false
        }]
    }));
    let mut property_plan = lower(&property_program, &target);
    let EcmascriptOperation::CharacterSet { members, .. } = &mut property_plan.root.operation
    else {
        panic!("character-set root")
    };
    let EcmascriptCharacterSetMember::UnicodeProperty { property, .. } = &mut members[0] else {
        panic!("Unicode property member")
    };
    *property = "bad-property".to_owned();
    assert_eq!(
        serialize_ecmascript(&property_plan)
            .expect_err("invalid property")
            .code,
        EcmascriptSerializationErrorCode::InvalidUnicodeProperty
    );

    let mut huge = lower(&simple, &target);
    huge.root.operation =
        EcmascriptOperation::Literal("a".repeat(MAX_ECMASCRIPT_PATTERN_BYTES + 1));
    assert_eq!(
        serialize_ecmascript(&huge)
            .expect_err("pattern size bound")
            .code,
        EcmascriptSerializationErrorCode::ResourceLimitExceeded
    );
}

#[test]
fn insensitive_ascii_word_class_fails_instead_of_widening_membership() {
    let semantic = program_with_case(
        json!({
            "node_id": "node:flags.ascii-word",
            "kind": "character_set",
            "negated": false,
            "members": [{
                "kind": "builtin",
                "name": "word",
                "domain": "ascii",
                "negated": false
            }]
        }),
        "insensitive",
    );
    let failure = serialize_ecmascript(&lower(&semantic, &profile()))
        .expect_err("ES2024 has no scoped -i for exact ASCII word membership");
    assert_eq!(failure.code, EcmascriptSerializationErrorCode::InvalidFlags);
    assert!(failure.diagnostics[0].message.contains("ASCII word"));
}
