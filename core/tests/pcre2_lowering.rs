use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::{NodeId, SpecificationVersion};
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{
    ArtifactPortabilityStatus, EngineOptionValue, OptionSelection, OptionStage, TargetProfile,
};
use strling_kernel::target_lowering::{
    lower_pcre2, Pcre2CaseMatching, Pcre2CharacterDomain, Pcre2CharacterSetMember, Pcre2Lookaround,
    Pcre2LoweringErrorCode, Pcre2Operation, Pcre2Position, Pcre2RepetitionMaximum,
    Pcre2RepetitionMode, Pcre2Wildcard, MAX_PCRE2_LOWERING_DEPTH,
};
use strling_kernel::validation::Validate;

const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");
const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

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
            "source_id": "src:pcre2-lowering",
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
            "source_id": "src:pcre2-lowering",
            "coordinate_system": "utf8-bytes",
            "start": start,
            "end": end
        }]
    })
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

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
                        },
                        {
                            "kind": "unicode_property",
                            "property": "Script",
                            "value": "Latin",
                            "negated": false
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
                },
                {
                    "node_id": "node:all.behind.variable-positive",
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": "positive",
                    "body": {
                        "node_id": "node:all.behind.variable-positive.body",
                        "kind": "alternation",
                        "branches": [
                            literal("node:all.behind.variable-positive.short", "x"),
                            literal("node:all.behind.variable-positive.long", "yz")
                        ]
                    }
                },
                {
                    "node_id": "node:all.behind.variable-negative",
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": "negative",
                    "body": {
                        "node_id": "node:all.behind.variable-negative.body",
                        "kind": "alternation",
                        "branches": [
                            literal("node:all.behind.variable-negative.short", "q"),
                            literal("node:all.behind.variable-negative.long", "rs")
                        ]
                    }
                },
                {
                    "node_id": "node:all.atomic",
                    "kind": "atomic",
                    "body": literal("node:all.atomic.body", "t")
                }
            ]
        }),
        "insensitive",
    )
}

#[test]
fn every_semantic_variant_lowers_to_explicit_pcre2_structure() {
    let semantic = comprehensive_program();
    let target = full_pcre2_profile();
    let portability = plan_for(&semantic, &target);
    let semantic_before = semantic.clone();
    let target_before = target.clone();
    let portability_before = portability.clone();

    let lowered = lower_pcre2(&semantic, &target, &portability).expect("lowering must succeed");

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
    assert_eq!(lowered.case_matching, Pcre2CaseMatching::Insensitive);
    assert_eq!(
        lowered.portability_status,
        ArtifactPortabilityStatus::Native
    );
    assert_eq!(lowered.options.len(), 2);
    assert!(lowered
        .options
        .iter()
        .all(|option| option.option_id.as_str().starts_with("pcre2.")));
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

    let Pcre2Operation::Sequence(items) = &lowered.root.operation else {
        panic!("root must remain an ordered sequence");
    };
    assert_eq!(items.len(), 27);
    assert!(matches!(items[0].operation, Pcre2Operation::Empty));
    assert!(matches!(items[1].operation, Pcre2Operation::Alternation(_)));
    assert_eq!(
        items[2].provenance.semantic_node_ids,
        [
            NodeId::try_from("node:all.empty").expect("node ID"),
            NodeId::try_from("node:all.literal").expect("node ID")
        ]
    );
    assert!(matches!(
        items[2].operation,
        Pcre2Operation::Literal(ref value) if value == "é"
    ));
    assert!(matches!(
        items[3].operation,
        Pcre2Operation::Wildcard(Pcre2Wildcard::ExcludeLineTerminators)
    ));
    assert!(matches!(
        items[4].operation,
        Pcre2Operation::Wildcard(Pcre2Wildcard::IncludeLineTerminators)
    ));
    let Pcre2Operation::CharacterSet { negated, members } = &items[5].operation else {
        panic!("character set must remain structured");
    };
    assert!(*negated);
    assert_eq!(members.len(), 5);
    assert!(matches!(
        members[0],
        Pcre2CharacterSetMember::Literal { value: 'é' }
    ));
    assert!(matches!(
        members[3],
        Pcre2CharacterSetMember::Builtin {
            domain: Pcre2CharacterDomain::Unicode,
            negated: true,
            ..
        }
    ));
    assert!(matches!(
        items[6].operation,
        Pcre2Operation::Repeat {
            min: 0,
            max: Pcre2RepetitionMaximum::Unbounded,
            mode: Pcre2RepetitionMode::Greedy,
            ..
        }
    ));
    assert!(matches!(
        items[7].operation,
        Pcre2Operation::Repeat {
            min: 1,
            max: Pcre2RepetitionMaximum::Bounded(3),
            mode: Pcre2RepetitionMode::Lazy,
            ..
        }
    ));
    assert!(matches!(
        items[8].operation,
        Pcre2Operation::Repeat {
            min: 2,
            max: Pcre2RepetitionMaximum::Bounded(4),
            mode: Pcre2RepetitionMode::Possessive,
            ..
        }
    ));
    let positions = [
        Pcre2Position::InputStart,
        Pcre2Position::InputEnd,
        Pcre2Position::LineStart,
        Pcre2Position::LineEnd,
        Pcre2Position::WordBoundary,
        Pcre2Position::NotWordBoundary,
        Pcre2Position::EndBeforeFinalLineTerminator,
    ];
    for (item, expected) in items[9..16].iter().zip(positions) {
        assert!(matches!(item.operation, Pcre2Operation::Position(found) if found == expected));
    }
    assert!(matches!(
        items[16].operation,
        Pcre2Operation::Capture {
            slot: 1,
            ref name,
            ..
        } if name.as_deref() == Some("word")
    ));
    assert!(matches!(
        items[17].operation,
        Pcre2Operation::Capture {
            slot: 2,
            name: None,
            ..
        }
    ));
    assert!(matches!(
        items[18].operation,
        Pcre2Operation::Backreference { slot: 1, .. }
    ));
    assert!(matches!(
        items[19].operation,
        Pcre2Operation::Backreference { slot: 2, .. }
    ));
    let assertions = [
        Pcre2Lookaround::PositiveAhead,
        Pcre2Lookaround::NegativeAhead,
        Pcre2Lookaround::PositiveBehind,
        Pcre2Lookaround::NegativeBehind,
        Pcre2Lookaround::PositiveBehind,
        Pcre2Lookaround::NegativeBehind,
    ];
    for (item, expected) in items[20..26].iter().zip(assertions) {
        assert!(matches!(
            item.operation,
            Pcre2Operation::Lookaround {
                assertion,
                ..
            } if assertion == expected
        ));
    }
    assert!(matches!(items[26].operation, Pcre2Operation::Atomic(_)));

    let repeated = lower_pcre2(&semantic, &target, &portability).expect("repeat lowering");
    assert_eq!(lowered, repeated, "lowering must be deterministic");
}

#[test]
fn certified_atomic_literal_rewrite_is_applied_and_retained() {
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
    let target = pcre2_without_atomic_groups();
    let portability = plan_for(&semantic, &target);

    let lowered = lower_pcre2(&semantic, &target, &portability).expect("rewrite lowering");

    assert_eq!(
        lowered.portability_status,
        ArtifactPortabilityStatus::EquivalentRewrite
    );
    assert!(matches!(
        lowered.root.operation,
        Pcre2Operation::Literal(ref value) if value == "a"
    ));
    assert_eq!(lowered.applied_rewrites.len(), 1);
    assert_eq!(
        lowered.applied_rewrites[0].strategy_id.as_str(),
        "rewrite.atomic_literal.elide.v1"
    );
    assert_eq!(
        lowered.applied_rewrites[0].target_profile,
        lowered.target_profile
    );
    assert_eq!(lowered.root.provenance.source_spans.len(), 2);
    assert_eq!(
        lowered.root.provenance.applied_rewrite.as_ref(),
        Some(&lowered.applied_rewrites[0].identity)
    );
    assert_eq!(
        lowered.root.provenance.semantic_node_ids,
        [
            NodeId::try_from("node:rewrite.atomic").expect("node ID"),
            NodeId::try_from("node:rewrite.body").expect("node ID")
        ]
    );
    assert_eq!(
        lowered.requirements[0].rewrite_strategy,
        Some(lowered.applied_rewrites[0].strategy_id)
    );
}

#[test]
fn profile_default_and_runtime_options_remain_typed_data() {
    let mut profile_value: Value = serde_json::from_str(PCRE2_1043).expect("10.43 JSON");
    profile_value["options"]
        .as_array_mut()
        .expect("profile options")
        .push(json!({
            "option_id": "pcre2.jit",
            "stage": "runtime",
            "value": false,
            "selection": "profile_default"
        }));
    profile_value["options"]
        .as_array_mut()
        .expect("profile options")
        .sort_by(|left, right| left["option_id"].as_str().cmp(&right["option_id"].as_str()));
    let target: TargetProfile =
        serde_json::from_value(profile_value).expect("extended PCRE2 profile");
    let semantic = program(literal("node:options.literal", "plain"));
    let portability = plan_for(&semantic, &target);

    let lowered = lower_pcre2(&semantic, &target, &portability).expect("option lowering");

    assert_eq!(lowered.options.len(), 4);
    let jit = lowered
        .options
        .iter()
        .find(|option| option.option_id.as_str() == "pcre2.jit")
        .expect("JIT option");
    assert_eq!(jit.stage, OptionStage::Runtime);
    assert_eq!(jit.selection, OptionSelection::ProfileDefault);
    assert_eq!(jit.value, EngineOptionValue::Boolean(false));
    let lookbehind = lowered
        .options
        .iter()
        .find(|option| option.option_id.as_str() == "pcre2.max_variable_lookbehind")
        .expect("lookbehind option");
    assert_eq!(lookbehind.stage, OptionStage::Compile);
    assert_eq!(lookbehind.selection, OptionSelection::ProfileDefault);
    assert!(matches!(
        &lookbehind.value,
        EngineOptionValue::Number(value) if value.as_u64() == Some(255)
    ));
    assert!(lowered
        .options
        .iter()
        .filter(|option| option.option_id.as_str().ends_with("ucp")
            || option.option_id.as_str().ends_with("utf"))
        .all(|option| option.selection == OptionSelection::Required));
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
    let stock_target: TargetProfile = serde_json::from_str(PCRE2_1042).expect("profile");
    let unresolved_plan = plan_for(&unresolved_semantic, &stock_target);
    let unresolved = lower_pcre2(&unresolved_semantic, &stock_target, &unresolved_plan)
        .expect_err("unknown lookahead support must not lower");
    assert_eq!(
        unresolved.code,
        Pcre2LoweringErrorCode::UnresolvedRequirement
    );
    assert_eq!(
        unresolved.diagnostics[0].code.as_str(),
        "STRL-PCRE2_LOWERING-0010"
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
        "node_id": "node:unsupported.atomic",
        "kind": "atomic",
        "body": {
            "node_id": "node:unsupported.repeat",
            "kind": "repeat",
            "body": literal("node:unsupported.literal", "a"),
            "min": 1,
            "max": 2,
            "mode": "greedy"
        }
    }));
    let target = pcre2_without_atomic_groups();
    let unsupported_plan = plan_for(&unsupported_semantic, &target);
    let unsupported = lower_pcre2(&unsupported_semantic, &target, &unsupported_plan)
        .expect_err("uncertified atomic rewrite must not lower");
    assert_eq!(
        unsupported.code,
        Pcre2LoweringErrorCode::UnsupportedRequirement
    );
    assert_eq!(
        unsupported.diagnostics[0].code.as_str(),
        "STRL-PCRE2_LOWERING-0011"
    );
}

#[test]
fn stale_mismatched_and_non_pcre2_inputs_are_rejected_before_lowering() {
    let first = program(literal("node:stale.literal", "a"));
    let second = program(literal("node:stale.literal", "b"));
    let target = full_pcre2_profile();
    let plan = plan_for(&first, &target);
    assert_eq!(
        lower_pcre2(&second, &target, &plan)
            .expect_err("cross-program evidence must fail")
            .code,
        Pcre2LoweringErrorCode::ProgramFingerprintMismatch
    );

    let stock_1042: TargetProfile = serde_json::from_str(PCRE2_1042).expect("10.42");
    let stock_1043: TargetProfile = serde_json::from_str(PCRE2_1043).expect("10.43");
    let plain = program(literal("node:profile.literal", "plain"));
    let profile_plan = plan_for(&plain, &stock_1042);
    assert_eq!(
        lower_pcre2(&plain, &stock_1043, &profile_plan)
            .expect_err("profile revision mismatch must fail")
            .code,
        Pcre2LoweringErrorCode::TargetProfileMismatch
    );

    let ecmascript: TargetProfile = serde_json::from_str(ECMASCRIPT).expect("ECMAScript");
    assert_eq!(
        lower_pcre2(&plain, &ecmascript, &profile_plan)
            .expect_err("non-PCRE2 target must fail")
            .code,
        Pcre2LoweringErrorCode::NonPcre2Target
    );

    let mut wrong_version = plan_for(&plain, &stock_1042);
    wrong_version.specification_version =
        SpecificationVersion::try_from("1.0-draft.2").expect("test specification version");
    assert_eq!(
        lower_pcre2(&plain, &stock_1042, &wrong_version)
            .expect_err("plan version mismatch must fail")
            .code,
        Pcre2LoweringErrorCode::VersionMismatch
    );
}

#[test]
fn malformed_planner_and_rewrite_evidence_are_rejected() {
    let semantic = program(json!({
        "node_id": "node:malformed.atomic",
        "kind": "atomic",
        "body": literal("node:malformed.body", "a")
    }));
    let target = pcre2_without_atomic_groups();
    let plan = plan_for(&semantic, &target);

    let mut malformed_identity = plan.clone();
    malformed_identity.decisions[0].identity.ordinal = 9;
    assert_eq!(
        lower_pcre2(&semantic, &target, &malformed_identity)
            .expect_err("malformed plan must fail")
            .code,
        Pcre2LoweringErrorCode::InvalidPortabilityPlan
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
        lower_pcre2(&semantic, &target, &malformed_rewrite)
            .expect_err("rewrite/program shape mismatch must fail")
            .code,
        Pcre2LoweringErrorCode::MalformedRewritePlan
    );
}

#[test]
fn invalid_semantic_and_excessive_depth_fail_without_partial_output() {
    let target = full_pcre2_profile();
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
        lower_pcre2(&invalid, &target, &plan)
            .expect_err("invalid canonical structure must fail")
            .code,
        Pcre2LoweringErrorCode::InvalidSemanticProgram
    );

    let mut deep = shallow.clone();
    let mut root = deep.root;
    for depth in 0..MAX_PCRE2_LOWERING_DEPTH {
        root = Node::Atomic {
            node_id: NodeId::try_from(format!("node:depth.wrapper-{depth}")).expect("node ID"),
            origin: None,
            body: Box::new(root),
        };
    }
    deep.root = root;
    assert_eq!(
        lower_pcre2(&deep, &target, &plan)
            .expect_err("depth above the target limit must fail")
            .code,
        Pcre2LoweringErrorCode::ResourceLimitExceeded
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
    let target = full_pcre2_profile();
    let portability = plan_for(&semantic, &target);
    let mut lowered = lower_pcre2(&semantic, &target, &portability).expect("lowering");
    lowered.captures[0].slot = 2;
    assert!(lowered.validate().is_err());
}
