use serde_json::{json, Value};
use strling_kernel::capability_evaluation::{
    evaluate_capabilities, CapabilityDisposition, CapabilityEvaluation,
};
use strling_kernel::ecmascript_lowering::lower_ecmascript;
use strling_kernel::ecmascript_serialization::serialize_ecmascript;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;
use strling_kernel::target_lowering::{lower_pcre2, Pcre2LoweringErrorCode};
use strling_kernel::target_serialization::serialize_pcre2;

const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");
const PYTHON_STR: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");
const PYTHON_BYTES: &str = include_str!("../../spec/targets/profiles/python-re-3.11-bytes.json");

fn profile(source: &str) -> TargetProfile {
    serde_json::from_str(source).expect("governed target profile")
}

fn program(root: Value) -> SemanticProgram {
    program_with_case(root, "sensitive")
}

fn program_with_case(root: Value, case_matching: &str) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": case_matching,
        "root": root
    }))
    .expect("semantic program")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn evaluate(input: &SemanticProgram, target: &TargetProfile) -> CapabilityEvaluation {
    let foundational = analyze(input).expect("foundational analysis");
    let structural = analyze_structure(input, &foundational).expect("structural analysis");
    evaluate_capabilities(input, &foundational, &structural, target).expect("capability evaluation")
}

fn plan(input: &SemanticProgram, target: &TargetProfile) -> PortabilityPlan {
    let foundational = analyze(input).expect("foundational analysis");
    let structural = analyze_structure(input, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(input, &foundational, &structural, target)
        .expect("capability evaluation");
    plan_portability(input, &foundational, &structural, target, &evaluation)
        .expect("portability plan")
}

fn disposition(
    evaluation: &CapabilityEvaluation,
    capability: &str,
) -> Option<CapabilityDisposition> {
    evaluation
        .results
        .iter()
        .find(|result| result.requirement.capability_id.as_str() == capability)
        .map(|result| result.disposition)
}

#[test]
fn explicit_wildcard_and_line_lowerings_cannot_regress_to_native_shortcuts() {
    let ecmascript = profile(ECMASCRIPT);
    let wildcard = program(json!({
        "node_id": "node:wildcard",
        "kind": "wildcard",
        "line_terminators": "exclude"
    }));
    let lowered = lower_ecmascript(&wildcard, &ecmascript, &plan(&wildcard, &ecmascript))
        .expect("ECMAScript wildcard lowering");
    let artifact = serialize_ecmascript(&lowered).expect("ECMAScript wildcard artifact");
    assert_eq!(artifact.pattern.text, r"[^\n\v\f\r\u0085\u2028\u2029]");
    assert_ne!(artifact.pattern.text, ".");

    let line_start = program(json!({
        "node_id": "node:line-start",
        "kind": "position",
        "position": "line_start"
    }));
    let lowered = lower_ecmascript(&line_start, &ecmascript, &plan(&line_start, &ecmascript))
        .expect("ECMAScript line-start lowering");
    let artifact = serialize_ecmascript(&lowered).expect("ECMAScript line-start artifact");
    assert!(artifact.pattern.text.contains(r"(?<=\r)(?!\n)"));
    assert!(artifact.requirements.iter().any(|requirement| {
        requirement.capability_id.as_str() == "assertions.lookbehind.fixed_length"
    }));
    assert!(artifact
        .requirements
        .iter()
        .any(|requirement| { requirement.capability_id.as_str() == "assertions.lookahead" }));
}

#[test]
fn unicode_word_semantics_are_native_explicit_or_refused_by_profile_fact() {
    let word = program(json!({
        "node_id": "node:word",
        "kind": "character_set",
        "negated": false,
        "members": [{
            "kind": "builtin",
            "name": "word",
            "domain": "unicode",
            "negated": false
        }]
    }));

    let pcre_1042 = profile(PCRE2_1042);
    let lowered = lower_pcre2(&word, &pcre_1042, &plan(&word, &pcre_1042))
        .expect("PCRE2 10.42 explicit word lowering");
    let artifact = serialize_pcre2(&lowered).expect("PCRE2 10.42 word artifact");
    assert_eq!(artifact.pattern.text, r"[\p{L}\p{Mn}\p{N}\p{Pc}]");
    assert_ne!(artifact.pattern.text, r"\w");

    let pcre_1043 = profile(PCRE2_1043);
    let lowered = lower_pcre2(&word, &pcre_1043, &plan(&word, &pcre_1043))
        .expect("PCRE2 10.43 native word lowering");
    assert_eq!(
        serialize_pcre2(&lowered)
            .expect("PCRE2 10.43 word artifact")
            .pattern
            .text,
        r"[\w]"
    );

    assert_eq!(
        disposition(
            &evaluate(&word, &profile(PYTHON_STR)),
            "character_classes.unicode"
        ),
        Some(CapabilityDisposition::Unsupported)
    );
}

#[test]
fn case_folding_refusal_is_reachable_and_not_engine_wide() {
    let python = profile(PYTHON_STR);
    let affected = program_with_case(literal("node:i", "I"), "insensitive");
    assert_eq!(
        disposition(&evaluate(&affected, &python), "matching.case_insensitive"),
        Some(CapabilityDisposition::Unsupported)
    );

    let unaffected = program_with_case(literal("node:k", "K"), "insensitive");
    assert_eq!(
        disposition(&evaluate(&unaffected, &python), "matching.case_insensitive"),
        Some(CapabilityDisposition::Supported)
    );
}

#[test]
fn backreference_algorithm_differences_are_rejected_only_when_observable() {
    let ecmascript = profile(ECMASCRIPT);
    let safe = program(json!({
        "node_id": "node:safe.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:safe.capture",
                "kind": "capture",
                "capture_id": "capture:safe",
                "body": literal("node:safe.body", "a")
            },
            {
                "node_id": "node:safe.reference",
                "kind": "backreference",
                "capture_id": "capture:safe"
            }
        ]
    }));
    assert_eq!(
        disposition(&evaluate(&safe, &ecmascript), "references.backreference"),
        Some(CapabilityDisposition::Supported)
    );

    let may_be_unset = program(json!({
        "node_id": "node:unset.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:unset.choice",
                "kind": "alternation",
                "branches": [
                    {
                        "node_id": "node:unset.capture",
                        "kind": "capture",
                        "capture_id": "capture:unset",
                        "body": literal("node:unset.body", "a")
                    },
                    literal("node:unset.other", "b")
                ]
            },
            {
                "node_id": "node:unset.reference",
                "kind": "backreference",
                "capture_id": "capture:unset"
            }
        ]
    }));
    assert_eq!(
        disposition(
            &evaluate(&may_be_unset, &ecmascript),
            "references.backreference"
        ),
        Some(CapabilityDisposition::Unsupported)
    );
}

#[test]
fn repeated_capture_reset_is_rejected_only_when_a_later_iteration_can_skip() {
    let ecmascript = profile(ECMASCRIPT);
    let observable = program(json!({
        "node_id": "node:repeat",
        "kind": "repeat",
        "min": 1,
        "max": 2,
        "mode": "greedy",
        "body": {
            "node_id": "node:choice",
            "kind": "alternation",
            "branches": [
                {
                    "node_id": "node:capture",
                    "kind": "capture",
                    "capture_id": "capture:iteration",
                    "body": literal("node:capture.body", "a")
                },
                literal("node:other", "b")
            ]
        }
    }));
    assert_eq!(
        disposition(
            &evaluate(&observable, &ecmascript),
            "groups.capture_iteration_state"
        ),
        Some(CapabilityDisposition::Unsupported)
    );

    let safe = program(json!({
        "node_id": "node:safe.repeat",
        "kind": "repeat",
        "min": 1,
        "max": 2,
        "mode": "greedy",
        "body": {
            "node_id": "node:safe.capture",
            "kind": "capture",
            "capture_id": "capture:safe.iteration",
            "body": literal("node:safe.capture.body", "a")
        }
    }));
    assert_eq!(
        disposition(
            &evaluate(&safe, &ecmascript),
            "groups.capture_iteration_state"
        ),
        None
    );
}

#[test]
fn pcre_compiled_size_uncertainty_and_python_bytes_fail_closed() {
    let pcre = profile(PCRE2_1043);
    let accepted = program(json!({
        "node_id": "node:repeat-4096",
        "kind": "repeat",
        "min": 1,
        "max": 4096,
        "mode": "greedy",
        "body": literal("node:repeat-4096.body", "a")
    }));
    assert_eq!(
        disposition(&evaluate(&accepted, &pcre), "repetition.bounded"),
        None
    );
    lower_pcre2(&accepted, &pcre, &plan(&accepted, &pcre))
        .expect("bounded repetition inside the conservative envelope");

    let refused = program(json!({
        "node_id": "node:repeat-4097",
        "kind": "repeat",
        "min": 1,
        "max": 4097,
        "mode": "greedy",
        "body": literal("node:repeat-4097.body", "a")
    }));
    assert_eq!(
        disposition(&evaluate(&refused, &pcre), "repetition.bounded"),
        None
    );
    assert_eq!(
        lower_pcre2(&refused, &pcre, &plan(&refused, &pcre))
            .expect_err("unknown compiled-size region must fail after structured lowering")
            .code,
        Pcre2LoweringErrorCode::IntroducedRequirement
    );

    let bytes = profile(PYTHON_BYTES);
    let wildcard = program(json!({
        "node_id": "node:bytes.wildcard",
        "kind": "wildcard",
        "line_terminators": "include"
    }));
    assert_eq!(
        disposition(&evaluate(&wildcard, &bytes), "character_classes.wildcard"),
        Some(CapabilityDisposition::Unsupported)
    );

    let negated = program(json!({
        "node_id": "node:bytes.negated",
        "kind": "character_set",
        "negated": true,
        "members": [{"kind": "literal", "value": "a"}]
    }));
    assert_eq!(
        disposition(
            &evaluate(&negated, &bytes),
            "character_semantics.unicode_scalar"
        ),
        Some(CapabilityDisposition::Unsupported)
    );
}
