use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::python_re_lowering::{
    lower_python_re, PythonReCaseMatching, PythonReCharacterDomain, PythonReCharacterSetMember,
    PythonReLookaround, PythonReLoweringErrorCode, PythonReOperation, PythonRePatternKind,
    PythonRePosition, PythonReRepetitionMaximum, PythonReRepetitionMode, PythonReWildcard,
    MAX_PYTHON_RE_LOWERING_DEPTH,
};
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::{NodeId, SpecificationVersion};
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{
    ArtifactPortabilityStatus, EngineOptionValue, OptionSelection, OptionStage, TargetProfile,
};
use strling_kernel::validation::Validate;

const PYTHON_RE: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");
const PCRE2: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");

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
            "source_id": "src:python-re-lowering",
            "specification_version": "1.0-draft.1",
            "frontend": {
                "id": "semantic_strling",
                "dialect_version": "1.0-draft.1"
            },
            "content": {
                "kind": "inline",
                "encoding": "utf-8",
                "text": "abcdefghijklmnopqrstuvwxyz"
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
            "source_id": "src:python-re-lowering",
            "coordinate_system": "utf8-bytes",
            "start": start,
            "end": end
        }]
    })
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn governed_python_re_profile() -> TargetProfile {
    serde_json::from_str(PYTHON_RE).expect("governed Python re 3.11 profile must deserialize")
}

fn python_re_profile_with_canonical_native_word() -> TargetProfile {
    let mut value = serde_json::to_value(governed_python_re_profile()).expect("profile JSON");
    let word = value["semantic_sets"]
        .as_array_mut()
        .expect("semantic set array")
        .iter_mut()
        .find(|fact| fact["set_id"] == "word_characters")
        .expect("word set");
    word["definition"] = json!({
        "kind": "character_set",
        "universe": "unicode_scalar",
        "scalars": [],
        "ranges": [],
        "unicode_general_categories": ["L", "Mn", "N", "Pc"]
    });
    let folding = value["semantic_algorithms"]
        .as_array_mut()
        .expect("semantic algorithm array")
        .iter_mut()
        .find(|fact| fact["algorithm_id"] == "case_folding")
        .expect("case-folding algorithm");
    folding["definition"] = json!({
        "kind": "case_folding",
        "mode": "simple_unicode",
        "additional_equivalence_classes": []
    });
    serde_json::from_value(value).expect("canonical-word test profile must deserialize")
}

fn python_re_profile_with_pattern_kind(pattern_kind: &str) -> TargetProfile {
    let mut value = serde_json::to_value(governed_python_re_profile()).expect("profile JSON");
    value["options"][0]["value"] = json!(pattern_kind);
    serde_json::from_value(value).expect("pattern-kind profile must deserialize")
}

fn python_re_without_lookahead_evidence() -> TargetProfile {
    let mut value = serde_json::to_value(governed_python_re_profile()).expect("profile JSON");
    value["capabilities"]
        .as_array_mut()
        .expect("capability array")
        .retain(|capability| capability["capability_id"] != "assertions.lookahead");
    serde_json::from_value(value).expect("incomplete Python re profile must deserialize")
}

fn python_re_with_atomic_rewrite() -> TargetProfile {
    let mut value = serde_json::to_value(governed_python_re_profile()).expect("profile JSON");
    let atomic = value["capabilities"]
        .as_array_mut()
        .expect("capability array")
        .iter_mut()
        .find(|capability| capability["capability_id"] == "groups.atomic")
        .expect("atomic capability");
    atomic["availability"] = json!("unavailable");
    serde_json::from_value(value).expect("rewrite-selecting Python re profile must deserialize")
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

fn comprehensive_program() -> SemanticProgram {
    program_with_case(
        json!({
            "node_id": "node:all.root",
            "kind": "sequence",
            "items": [
                {"node_id": "node:all.empty", "kind": "empty"},
                {
                    "node_id": "node:all.alternation",
                    "kind": "alternation",
                    "branches": [
                        literal("node:all.alternation.literal", "a"),
                        {"node_id": "node:all.alternation.empty", "kind": "empty"}
                    ]
                },
                {
                    "node_id": "node:all.literal",
                    "kind": "literal",
                    "text": "é",
                    "origin": {
                        "derived_from_node_ids": ["node:all.empty"]
                    }
                },
                {
                    "node_id": "node:all.wildcard.exclude",
                    "kind": "wildcard",
                    "line_terminators": "exclude"
                },
                {
                    "node_id": "node:all.wildcard.include",
                    "kind": "wildcard",
                    "line_terminators": "include"
                },
                {
                    "node_id": "node:all.set",
                    "kind": "character_set",
                    "negated": true,
                    "members": [
                        {"kind": "literal", "value": "é"},
                        {"kind": "range", "start": "a", "end": "z"},
                        {
                            "kind": "builtin",
                            "name": "digit",
                            "domain": "ascii",
                            "negated": false
                        },
                        {
                            "kind": "builtin",
                            "name": "word",
                            "domain": "unicode",
                            "negated": true
                        }
                    ]
                },
                {
                    "node_id": "node:all.repeat.greedy",
                    "kind": "repeat",
                    "body": literal("node:all.repeat.greedy.body", "g"),
                    "min": 0,
                    "max": null,
                    "mode": "greedy"
                },
                {
                    "node_id": "node:all.repeat.lazy",
                    "kind": "repeat",
                    "body": literal("node:all.repeat.lazy.body", "l"),
                    "min": 1,
                    "max": 3,
                    "mode": "lazy"
                },
                {
                    "node_id": "node:all.repeat.possessive",
                    "kind": "repeat",
                    "body": literal("node:all.repeat.possessive.body", "p"),
                    "min": 2,
                    "max": 4,
                    "mode": "possessive"
                },
                {
                    "node_id": "node:all.atomic",
                    "kind": "atomic",
                    "body": literal("node:all.atomic.body", "t")
                },
                {"node_id": "node:all.position.input-start", "kind": "position", "position": "input_start"},
                {"node_id": "node:all.position.input-end", "kind": "position", "position": "input_end"},
                {"node_id": "node:all.position.line-start", "kind": "position", "position": "line_start"},
                {"node_id": "node:all.position.line-end", "kind": "position", "position": "line_end"},
                {"node_id": "node:all.position.word", "kind": "position", "position": "word_boundary"},
                {"node_id": "node:all.position.not-word", "kind": "position", "position": "not_word_boundary"},
                {"node_id": "node:all.position.final", "kind": "position", "position": "end_before_final_line_terminator"},
                {
                    "node_id": "node:all.capture.named",
                    "kind": "capture",
                    "capture_id": "capture:all.named",
                    "name": "word",
                    "body": literal("node:all.capture.named.body", "n")
                },
                {
                    "node_id": "node:all.capture.unnamed",
                    "kind": "capture",
                    "capture_id": "capture:all.unnamed",
                    "body": {
                        "node_id": "node:all.capture.unnamed.body",
                        "kind": "wildcard",
                        "line_terminators": "exclude"
                    }
                },
                {
                    "node_id": "node:all.reference.named",
                    "kind": "backreference",
                    "capture_id": "capture:all.named"
                },
                {
                    "node_id": "node:all.reference.unnamed",
                    "kind": "backreference",
                    "capture_id": "capture:all.unnamed"
                },
                {
                    "node_id": "node:all.ahead.positive",
                    "kind": "lookaround",
                    "direction": "ahead",
                    "polarity": "positive",
                    "body": literal("node:all.ahead.positive.body", "a")
                },
                {
                    "node_id": "node:all.ahead.negative",
                    "kind": "lookaround",
                    "direction": "ahead",
                    "polarity": "negative",
                    "body": literal("node:all.ahead.negative.body", "b")
                },
                {
                    "node_id": "node:all.behind.positive",
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": "positive",
                    "body": literal("node:all.behind.positive.body", "c")
                },
                {
                    "node_id": "node:all.behind.negative",
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": "negative",
                    "body": literal("node:all.behind.negative.body", "d")
                }
            ]
        }),
        "insensitive",
    )
}

#[test]
fn every_semantic_variant_lowers_to_explicit_python_re_structure() {
    let semantic = comprehensive_program();
    let target = python_re_profile_with_canonical_native_word();
    let portability = plan_for(&semantic, &target);
    let semantic_before = semantic.clone();
    let target_before = target.clone();
    let portability_before = portability.clone();

    let lowered = lower_python_re(&semantic, &target, &portability).expect("lowering must succeed");

    assert_eq!(
        semantic, semantic_before,
        "Semantic IR must remain immutable"
    );
    assert_eq!(
        target, target_before,
        "target profile must remain immutable"
    );
    assert_eq!(
        portability, portability_before,
        "portability plan must remain immutable"
    );
    assert_eq!(lowered.case_matching, PythonReCaseMatching::Insensitive);
    assert_eq!(lowered.pattern_kind, PythonRePatternKind::Str);
    assert_eq!(
        lowered.portability_status,
        ArtifactPortabilityStatus::Native
    );
    assert_eq!(lowered.options.len(), 1);
    assert!(lowered
        .options
        .iter()
        .all(|option| option.option_id.as_str().starts_with("python.")));
    assert_eq!(lowered.captures.len(), 2);
    assert_eq!(lowered.captures[0].slot, 1);
    assert_eq!(lowered.captures[0].capture_id.as_str(), "capture:all.named");
    assert_eq!(lowered.captures[0].name.as_deref(), Some("word"));
    assert_eq!(lowered.captures[1].slot, 2);
    assert_eq!(
        lowered.captures[1].capture_id.as_str(),
        "capture:all.unnamed"
    );
    assert!(lowered
        .requirements
        .iter()
        .all(
            |resolution| resolution.status == ArtifactPortabilityStatus::Native
                && resolution.rewrite_strategy.is_none()
        ));
    assert!(lowered.applied_rewrites.is_empty());
    lowered.validate().expect("target plan must self-validate");

    let PythonReOperation::Sequence(items) = &lowered.root.operation else {
        panic!("root must remain an ordered sequence");
    };
    assert_eq!(items.len(), 25);
    assert!(matches!(items[0].operation, PythonReOperation::Empty));
    assert!(matches!(
        items[1].operation,
        PythonReOperation::Alternation(_)
    ));
    assert_eq!(
        items[2].provenance.semantic_node_ids,
        [
            NodeId::try_from("node:all.empty").expect("node ID"),
            NodeId::try_from("node:all.literal").expect("node ID")
        ]
    );
    assert!(matches!(
        items[2].operation,
        PythonReOperation::Literal(ref value) if value == "é"
    ));
    assert!(matches!(
        items[3].operation,
        PythonReOperation::Wildcard(PythonReWildcard::CanonicalExcludeLineTerminators)
    ));
    assert!(matches!(
        items[4].operation,
        PythonReOperation::Wildcard(PythonReWildcard::IncludeLineTerminators)
    ));
    let PythonReOperation::CharacterSet { negated, members } = &items[5].operation else {
        panic!("character set must remain structured");
    };
    assert!(*negated);
    assert_eq!(members.len(), 4);
    assert!(matches!(
        members[0],
        PythonReCharacterSetMember::Literal { value: 'é' }
    ));
    assert!(matches!(
        members[3],
        PythonReCharacterSetMember::Builtin {
            domain: PythonReCharacterDomain::Unicode,
            negated: true,
            ..
        }
    ));
    assert!(matches!(
        items[6].operation,
        PythonReOperation::Repeat {
            min: 0,
            max: PythonReRepetitionMaximum::Unbounded,
            mode: PythonReRepetitionMode::Greedy,
            ..
        }
    ));
    assert!(matches!(
        items[7].operation,
        PythonReOperation::Repeat {
            min: 1,
            max: PythonReRepetitionMaximum::Bounded(3),
            mode: PythonReRepetitionMode::Lazy,
            ..
        }
    ));
    assert!(matches!(
        items[8].operation,
        PythonReOperation::Repeat {
            min: 2,
            max: PythonReRepetitionMaximum::Bounded(4),
            mode: PythonReRepetitionMode::Possessive,
            ..
        }
    ));
    assert!(matches!(
        items[9].operation,
        PythonReOperation::Atomic { .. }
    ));
    let positions = [
        PythonRePosition::InputStart,
        PythonRePosition::InputEnd,
        PythonRePosition::CanonicalLineStart,
        PythonRePosition::CanonicalLineEnd,
        PythonRePosition::WordBoundary,
        PythonRePosition::NotWordBoundary,
        PythonRePosition::CanonicalEndBeforeFinalLineTerminator,
    ];
    for (item, expected) in items[10..17].iter().zip(positions) {
        assert!(matches!(item.operation, PythonReOperation::Position(found) if found == expected));
    }
    assert!(matches!(
        items[17].operation,
        PythonReOperation::Capture {
            slot: 1,
            ref name,
            ..
        } if name.as_deref() == Some("word")
    ));
    assert!(matches!(
        items[18].operation,
        PythonReOperation::Capture {
            slot: 2,
            name: None,
            ..
        }
    ));
    assert!(matches!(
        items[19].operation,
        PythonReOperation::Backreference { slot: 1, .. }
    ));
    assert!(matches!(
        items[20].operation,
        PythonReOperation::Backreference { slot: 2, .. }
    ));
    let assertions = [
        PythonReLookaround::PositiveAhead,
        PythonReLookaround::NegativeAhead,
        PythonReLookaround::PositiveBehind,
        PythonReLookaround::NegativeBehind,
    ];
    for (item, expected) in items[21..25].iter().zip(assertions) {
        assert!(matches!(
            item.operation,
            PythonReOperation::Lookaround {
                assertion,
                ..
            } if assertion == expected
        ));
    }
    let repeated = lower_python_re(&semantic, &target, &portability).expect("repeat lowering");
    assert_eq!(lowered, repeated, "lowering must be deterministic");
}

#[test]
fn atomic_groups_are_native_and_retain_exact_provenance() {
    let semantic = source_program(json!({
        "node_id": "node:rewrite.atomic",
        "kind": "atomic",
        "origin": origin(0, 3),
        "body": {
            "node_id": "node:rewrite.body",
            "kind": "literal",
            "origin": origin(1, 2),
            "text": "a"
        }
    }));
    let target = governed_python_re_profile();
    let portability = plan_for(&semantic, &target);

    let lowered = lower_python_re(&semantic, &target, &portability).expect("atomic lowering");

    assert_eq!(
        lowered.portability_status,
        ArtifactPortabilityStatus::Native
    );
    assert!(matches!(
        lowered.root.operation,
        PythonReOperation::Atomic { .. }
    ));
    assert!(lowered.applied_rewrites.is_empty());
    assert_eq!(lowered.root.provenance.source_spans.len(), 1);
    assert!(lowered.root.provenance.applied_rewrite.is_none());
    assert_eq!(
        lowered.root.provenance.semantic_node_ids,
        [NodeId::try_from("node:rewrite.atomic").expect("node ID")]
    );
    assert!(lowered.requirements[0].rewrite_strategy.is_none());
}

#[test]
fn planner_certified_rewrites_are_applied_and_retained() {
    let semantic = source_program(json!({
        "node_id": "node:rewrite.certified",
        "kind": "atomic",
        "origin": origin(0, 3),
        "body": {
            "node_id": "node:rewrite.certified.body",
            "kind": "literal",
            "origin": origin(1, 2),
            "text": "a"
        }
    }));
    let target = python_re_with_atomic_rewrite();
    let portability = plan_for(&semantic, &target);
    let lowered = lower_python_re(&semantic, &target, &portability).expect("rewrite lowering");

    assert_eq!(
        lowered.portability_status,
        ArtifactPortabilityStatus::EquivalentRewrite
    );
    assert!(matches!(
        lowered.root.operation,
        PythonReOperation::Literal(ref value) if value == "a"
    ));
    assert_eq!(lowered.applied_rewrites.len(), 1);
    assert_eq!(
        lowered.applied_rewrites[0].strategy_id.as_str(),
        "rewrite.atomic_literal.elide.v1"
    );
    assert_eq!(
        lowered.root.provenance.applied_rewrite.as_ref(),
        Some(&lowered.applied_rewrites[0].identity)
    );
    assert_eq!(
        lowered.requirements[0].rewrite_strategy,
        Some(lowered.applied_rewrites[0].strategy_id)
    );
}

#[test]
fn required_pattern_kind_remains_typed_runtime_data() {
    let target = governed_python_re_profile();
    let semantic = program(literal("node:options.literal", "plain"));
    let portability = plan_for(&semantic, &target);

    let lowered = lower_python_re(&semantic, &target, &portability).expect("option lowering");

    assert_eq!(lowered.options.len(), 1);
    let pattern_kind = lowered
        .options
        .iter()
        .find(|option| option.option_id.as_str() == "python.pattern_kind")
        .expect("pattern kind option");
    assert_eq!(pattern_kind.stage, OptionStage::Runtime);
    assert_eq!(pattern_kind.selection, OptionSelection::Required);
    assert_eq!(
        pattern_kind.value,
        EngineOptionValue::String("str".to_owned())
    );
    assert_eq!(lowered.pattern_kind, PythonRePatternKind::Str);
}

#[test]
fn unresolved_and_unsupported_plans_fail_closed_with_stable_diagnostics() {
    let unresolved_semantic = source_program(json!({
        "node_id": "node:unresolved.lookahead",
        "kind": "lookaround",
        "origin": origin(2, 6),
        "direction": "ahead",
        "polarity": "positive",
        "body": literal("node:unresolved.body", "a")
    }));
    let incomplete_target = python_re_without_lookahead_evidence();
    let unresolved_plan = plan_for(&unresolved_semantic, &incomplete_target);
    let unresolved = lower_python_re(&unresolved_semantic, &incomplete_target, &unresolved_plan)
        .expect_err("unknown lookahead support must not lower");
    assert_eq!(
        unresolved.code,
        PythonReLoweringErrorCode::UnresolvedRequirement
    );
    assert_eq!(
        unresolved.diagnostics[0].code.as_str(),
        "STRL-PYTHON_RE_LOWERING-0010"
    );
    assert_eq!(
        unresolved.diagnostics[0]
            .primary_location
            .as_ref()
            .expect("source location")
            .start,
        2
    );

    let unsupported_semantic = program(json!({
        "node_id": "node:unsupported.variable-lookbehind",
        "kind": "lookaround",
        "direction": "behind",
        "polarity": "positive",
        "body": {
            "node_id": "node:unsupported.variable-body",
            "kind": "alternation",
            "branches": [
                literal("node:unsupported.short", "a"),
                literal("node:unsupported.long", "bc")
            ]
        }
    }));
    let target = governed_python_re_profile();
    let unsupported_plan = plan_for(&unsupported_semantic, &target);
    let unsupported = lower_python_re(&unsupported_semantic, &target, &unsupported_plan)
        .expect_err("variable-length lookbehind must not lower");
    assert_eq!(
        unsupported.code,
        PythonReLoweringErrorCode::UnsupportedRequirement
    );
    assert_eq!(
        unsupported.diagnostics[0].code.as_str(),
        "STRL-PYTHON_RE_LOWERING-0011"
    );

    let property_semantic = program(json!({
        "node_id": "node:unsupported.property",
        "kind": "character_set",
        "negated": false,
        "members": [{
            "kind": "unicode_property",
            "property": "General_Category",
            "value": "Letter",
            "negated": false
        }]
    }));
    let property_plan = plan_for(&property_semantic, &target);
    let property = lower_python_re(&property_semantic, &target, &property_plan)
        .expect_err("Unicode property escapes must not lower");
    assert_eq!(
        property.code,
        PythonReLoweringErrorCode::UnsupportedRequirement
    );
    assert_eq!(
        property.diagnostics[0].code.as_str(),
        "STRL-PYTHON_RE_LOWERING-0011"
    );
}

#[test]
fn bytes_patterns_accept_ascii_and_reject_unicode_semantics() {
    let bytes_target = python_re_profile_with_pattern_kind("bytes");
    let ascii = program(literal("node:bytes.ascii", "plain"));
    let ascii_plan = plan_for(&ascii, &bytes_target);
    let lowered = lower_python_re(&ascii, &bytes_target, &ascii_plan).expect("ASCII bytes plan");
    assert_eq!(lowered.pattern_kind, PythonRePatternKind::Bytes);
    assert_eq!(
        lowered.options[0].value,
        EngineOptionValue::String("bytes".to_owned())
    );

    let unicode = program(literal("node:bytes.unicode", "λ"));
    let unicode_plan = plan_for(&unicode, &bytes_target);
    let failure = lower_python_re(&unicode, &bytes_target, &unicode_plan)
        .expect_err("bytes patterns cannot carry Unicode scalar semantics");
    assert_eq!(failure.code, PythonReLoweringErrorCode::PatternKindMismatch);
    assert_eq!(
        failure.diagnostics[0].code.as_str(),
        "STRL-PYTHON_RE_LOWERING-0014"
    );
}

#[test]
fn stale_mismatched_and_non_python_re_inputs_are_rejected_before_lowering() {
    let first = program(literal("node:stale.literal", "a"));
    let second = program(literal("node:stale.literal", "b"));
    let target = governed_python_re_profile();
    let plan = plan_for(&first, &target);
    assert_eq!(
        lower_python_re(&second, &target, &plan)
            .expect_err("cross-program evidence must fail")
            .code,
        PythonReLoweringErrorCode::ProgramFingerprintMismatch
    );

    let mut changed_profile = target.clone();
    changed_profile.evidence[0].locator.push_str("#changed");
    let plain = program(literal("node:profile.literal", "plain"));
    let profile_plan = plan_for(&plain, &target);
    assert_eq!(
        lower_python_re(&plain, &changed_profile, &profile_plan)
            .expect_err("profile revision mismatch must fail")
            .code,
        PythonReLoweringErrorCode::TargetProfileMismatch
    );

    let pcre2: TargetProfile = serde_json::from_str(PCRE2).expect("PCRE2 profile");
    let pcre2_plan = plan_for(&plain, &pcre2);
    assert_eq!(
        lower_python_re(&plain, &pcre2, &pcre2_plan)
            .expect_err("non-Python re target must fail")
            .code,
        PythonReLoweringErrorCode::NonPythonReTarget
    );

    let mut wrong_version = plan_for(&plain, &target);
    wrong_version.specification_version =
        SpecificationVersion::try_from("1.0-draft.2").expect("test specification version");
    assert_eq!(
        lower_python_re(&plain, &target, &wrong_version)
            .expect_err("plan version mismatch must fail")
            .code,
        PythonReLoweringErrorCode::VersionMismatch
    );
}

#[test]
fn malformed_planner_and_rewrite_evidence_are_rejected() {
    let semantic = program(json!({
        "node_id": "node:malformed.atomic",
        "kind": "atomic",
        "body": literal("node:malformed.body", "a")
    }));
    let target = python_re_with_atomic_rewrite();
    let plan = plan_for(&semantic, &target);

    let mut malformed_identity = plan.clone();
    malformed_identity.decisions[0].identity.ordinal = 9;
    assert_eq!(
        lower_python_re(&semantic, &target, &malformed_identity)
            .expect_err("malformed plan must fail")
            .code,
        PythonReLoweringErrorCode::InvalidPortabilityPlan
    );

    let mut malformed_rewrite = plan;
    let strling_kernel::portability_planning::RequirementPlanningDisposition::EquivalentRewrite(
        rewrite,
    ) = &mut malformed_rewrite.decisions[0].disposition
    else {
        panic!("fixture must select a rewrite");
    };
    rewrite
        .rewrite_plan
        .affected_node_ids
        .push(NodeId::try_from("node:malformed.extra").expect("node ID"));
    rewrite.rewrite_plan.affected_node_ids.sort();
    malformed_rewrite
        .validate()
        .expect("planner validation intentionally permits additional affected provenance");
    assert_eq!(
        lower_python_re(&semantic, &target, &malformed_rewrite)
            .expect_err("rewrite/program shape mismatch must fail")
            .code,
        PythonReLoweringErrorCode::MalformedRewritePlan
    );
}

#[test]
fn invalid_semantic_and_excessive_depth_fail_without_partial_output() {
    let target = governed_python_re_profile();
    let shallow = program(literal("node:depth.base", "a"));
    let plan = plan_for(&shallow, &target);

    let mut invalid = shallow.clone();
    invalid.root = Node::Sequence {
        node_id: NodeId::try_from("node:invalid.sequence").expect("node ID"),
        origin: None,
        items: vec![Node::Empty {
            node_id: NodeId::try_from("node:invalid.only-child").expect("node ID"),
            origin: None,
        }],
    };
    assert_eq!(
        lower_python_re(&invalid, &target, &plan)
            .expect_err("invalid canonical structure must fail")
            .code,
        PythonReLoweringErrorCode::InvalidSemanticProgram
    );

    let mut deep = shallow.clone();
    let mut root = deep.root;
    for depth in 0..MAX_PYTHON_RE_LOWERING_DEPTH {
        root = Node::Atomic {
            node_id: NodeId::try_from(format!("node:depth.wrapper-{depth}")).expect("node ID"),
            origin: None,
            body: Box::new(root),
        };
    }
    deep.root = root;
    assert_eq!(
        lower_python_re(&deep, &target, &plan)
            .expect_err("depth above the target limit must fail")
            .code,
        PythonReLoweringErrorCode::ResourceLimitExceeded
    );
}

#[test]
fn constructed_plan_validation_detects_capture_slot_corruption() {
    let semantic = program(json!({
        "node_id": "node:capture.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:capture.definition",
                "kind": "capture",
                "capture_id": "capture:validation",
                "body": literal("node:capture.body", "a")
            },
            {
                "node_id": "node:capture.reference",
                "kind": "backreference",
                "capture_id": "capture:validation"
            }
        ]
    }));
    let target = governed_python_re_profile();
    let portability = plan_for(&semantic, &target);
    let mut lowered = lower_python_re(&semantic, &target, &portability).expect("lowering");
    lowered.captures[0].slot = 2;
    assert!(lowered.validate().is_err());
}
