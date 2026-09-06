use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::ecmascript_lowering::{
    lower_ecmascript, EcmascriptLoweringErrorCode, EcmascriptOperation, EcmascriptPosition,
};
use strling_kernel::ecmascript_serialization::serialize_ecmascript;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::python_re_lowering::{lower_python_re, PythonReLoweringErrorCode};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{CapabilityId, TargetArtifact, TargetProfile};
use strling_kernel::target_lowering::lower_pcre2;
use strling_kernel::validation::Validate;

const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PCRE2: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");
const PYTHON_RE: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("test Semantic IR")
}

fn profile(source: &str) -> TargetProfile {
    serde_json::from_str(source).expect("governed target profile")
}

fn plan_for(semantic: &SemanticProgram, target: &TargetProfile) -> PortabilityPlan {
    let foundational = analyze(semantic).expect("foundational analysis");
    let structural = analyze_structure(semantic, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(semantic, &foundational, &structural, target)
        .expect("source capability evaluation");
    plan_portability(semantic, &foundational, &structural, target, &evaluation)
        .expect("source portability plan")
}

fn remove_capability(target: &TargetProfile, capability_id: &str) -> TargetProfile {
    let mut value = serde_json::to_value(target).expect("profile JSON");
    value["capabilities"]
        .as_array_mut()
        .expect("capabilities")
        .retain(|capability| capability["capability_id"] != capability_id);
    serde_json::from_value(value).expect("synthetic restrictive profile")
}

fn constrain_lookahead_to_unicode_option(target: &TargetProfile) -> TargetProfile {
    let mut value = serde_json::to_value(target).expect("profile JSON");
    let lookahead = value["capabilities"]
        .as_array_mut()
        .expect("capabilities")
        .iter_mut()
        .find(|capability| capability["capability_id"] == "assertions.lookahead")
        .expect("lookahead capability");
    lookahead["availability"] = json!("constrained");
    lookahead["constraints"] = json!([{
        "constraint_id": "unicode_mode",
        "operator": "requires_option",
        "value": "ecmascript.unicode_mode"
    }]);
    serde_json::from_value(value).expect("constrained synthetic profile")
}

fn position(node_id: &str, value: &str) -> SemanticProgram {
    program(json!({"node_id": node_id, "kind": "position", "position": value}))
}

fn lookahead_program() -> SemanticProgram {
    program(json!({
        "node_id": "node:lookahead",
        "kind": "lookaround",
        "direction": "ahead",
        "polarity": "positive",
        "body": {"node_id": "node:lookahead.body", "kind": "literal", "text": "a"}
    }))
}

fn negated_set(node_id: &str, members: Value) -> SemanticProgram {
    program(json!({
        "node_id": node_id,
        "kind": "character_set",
        "negated": true,
        "members": members
    }))
}

fn capability_ids<'a>(requirements: impl IntoIterator<Item = &'a CapabilityId>) -> Vec<&'a str> {
    requirements.into_iter().map(CapabilityId::as_str).collect()
}

fn artifact_digest(artifact: &TargetArtifact) -> Vec<u8> {
    Sha256::digest(serde_json::to_vec(artifact).expect("canonical artifact JSON")).to_vec()
}

#[test]
fn source_emitted_and_shared_requirements_reconcile_canonically() {
    let target = profile(ECMASCRIPT);

    let source_only = program(json!({
        "node_id": "node:capture",
        "kind": "capture",
        "capture_id": "capture:one",
        "name": "one",
        "body": {"node_id": "node:capture.body", "kind": "literal", "text": "a"}
    }));
    let source_plan = plan_for(&source_only, &target);
    let source_lowered = lower_ecmascript(&source_only, &target, &source_plan).expect("lower");
    assert_eq!(source_lowered.semantic_requirements.len(), 1);
    assert_eq!(source_lowered.requirements.len(), 2);
    assert_eq!(
        capability_ids(
            source_lowered
                .requirements
                .iter()
                .map(|requirement| &requirement.identity.capability_id)
        ),
        ["groups.named_capture", "groups.capture_iteration_state"]
    );

    let emitted_only = program(json!({
        "node_id": "node:wildcard",
        "kind": "wildcard",
        "line_terminators": "include"
    }));
    let emitted_plan = plan_for(&emitted_only, &target);
    assert_eq!(emitted_plan.decisions.len(), 1);
    let emitted_lowered = lower_ecmascript(&emitted_only, &target, &emitted_plan).expect("lower");
    assert_eq!(emitted_lowered.semantic_requirements.len(), 1);
    assert_eq!(
        capability_ids(
            emitted_lowered
                .requirements
                .iter()
                .map(|requirement| &requirement.identity.capability_id)
        ),
        ["character_classes.wildcard"]
    );

    let shared = lookahead_program();
    let shared_plan = plan_for(&shared, &target);
    let shared_lowered = lower_ecmascript(&shared, &target, &shared_plan).expect("lower");
    assert_eq!(shared_lowered.semantic_requirements.len(), 1);
    assert_eq!(shared_lowered.requirements.len(), 1);
    assert_eq!(
        shared_lowered.requirements[0]
            .identity
            .capability_id
            .as_str(),
        "assertions.lookahead"
    );
}

#[test]
fn ecmascript_positions_declare_every_lowering_assertion() {
    let target = profile(ECMASCRIPT);
    let cases = [
        (
            "input_end",
            vec!["anchors.input_end", "assertions.lookahead"],
        ),
        (
            "line_start",
            vec![
                "anchors.line_start",
                "assertions.lookahead",
                "assertions.lookbehind.fixed_length",
            ],
        ),
        (
            "line_end",
            vec![
                "anchors.line_end",
                "assertions.lookahead",
                "assertions.lookbehind.fixed_length",
            ],
        ),
        (
            "end_before_final_line_terminator",
            vec![
                "anchors.end_before_final_line_terminator",
                "assertions.lookahead",
                "assertions.lookbehind.fixed_length",
            ],
        ),
    ];
    for (value, expected) in cases {
        let semantic = position(&format!("node:{value}"), value);
        let plan = plan_for(&semantic, &target);
        let lowered = lower_ecmascript(&semantic, &target, &plan).expect("position lowers");
        assert_eq!(
            capability_ids(
                lowered
                    .requirements
                    .iter()
                    .map(|requirement| &requirement.identity.capability_id)
            ),
            expected,
            "{value}"
        );
    }
}

#[test]
fn restrictive_profiles_reject_lowering_introduced_assertions_after_precheck() {
    let ecmascript = profile(ECMASCRIPT);
    let no_lookbehind = remove_capability(&ecmascript, "assertions.lookbehind.fixed_length");
    let line_start = position("node:line-start", "line_start");
    let early = plan_for(&line_start, &no_lookbehind);
    assert!(early.unresolved_requirements.is_empty());
    assert_eq!(early.decisions.len(), 1);
    let failure = lower_ecmascript(&line_start, &no_lookbehind, &early)
        .expect_err("introduced lookbehind must fail closed");
    assert_eq!(
        failure.code,
        EcmascriptLoweringErrorCode::IntroducedRequirement
    );
    assert!(failure.diagnostics[0]
        .message
        .contains("assertions.lookbehind.fixed_length"));
    assert!(failure.diagnostics[0].message.contains("node:line-start"));
    assert!(failure.diagnostics[0]
        .message
        .contains(no_lookbehind.profile_id.as_str()));

    let python = profile(PYTHON_RE);
    let no_lookahead = remove_capability(&python, "assertions.lookahead");
    let negated = negated_set("node:negated", json!([{"kind": "literal", "value": "a"}]));
    let early = plan_for(&negated, &no_lookahead);
    assert!(early.unresolved_requirements.is_empty());
    let failure = lower_python_re(&negated, &no_lookahead, &early)
        .expect_err("introduced lookahead must fail closed");
    assert_eq!(
        failure.code,
        PythonReLoweringErrorCode::IntroducedRequirement
    );
    assert!(failure.diagnostics[0]
        .message
        .contains("assertions.lookahead"));
}

#[test]
fn constrained_introduced_capability_is_evaluated_with_exact_profile_options() {
    let target = constrain_lookahead_to_unicode_option(&profile(ECMASCRIPT));
    target.validate().expect("constrained profile validates");
    let semantic = position("node:input-end", "input_end");
    let early = plan_for(&semantic, &target);
    assert!(early
        .decisions
        .iter()
        .all(|decision| decision.identity.capability_id.as_str() != "assertions.lookahead"));
    let lowered = lower_ecmascript(&semantic, &target, &early)
        .expect("selected Unicode option satisfies introduced lookahead");
    assert!(lowered.requirements.iter().any(|requirement| {
        requirement.identity.capability_id.as_str() == "assertions.lookahead"
    }));
}

#[test]
fn negated_set_requirement_inventory_matches_each_target_lowering() {
    let scalar = json!([{"kind": "literal", "value": "a"}]);
    let range = json!([{"kind": "range", "start": "a", "end": "z"}]);
    let builtin_scalar = json!([
        {"kind": "literal", "value": "a"},
        {"kind": "builtin", "name": "digit", "domain": "ascii", "negated": false}
    ]);
    let unicode_builtin_scalar = json!([
        {"kind": "literal", "value": "a"},
        {"kind": "builtin", "name": "word", "domain": "unicode", "negated": false}
    ]);
    let cases = [
        ("scalar", scalar, false, false, true, true),
        ("range", range, false, false, true, true),
        ("builtin", builtin_scalar, true, true, true, true),
        ("unicode", unicode_builtin_scalar, true, false, true, false),
    ];
    let ecmascript = profile(ECMASCRIPT);
    let pcre2 = profile(PCRE2);
    let python = profile(PYTHON_RE);
    for (name, members, ecma_expected, pcre_expected, python_expected, python_supported) in cases {
        let semantic = negated_set(&format!("node:{name}"), members);

        let ecma_source = plan_for(&semantic, &ecmascript);
        let ecma = lower_ecmascript(&semantic, &ecmascript, &ecma_source).expect("ECMAScript");
        let ecma_introduced = &ecma.requirements[ecma.semantic_requirements.len()..];
        assert_eq!(
            ecma_introduced.iter().any(|requirement| {
                requirement.identity.capability_id.as_str() == "assertions.lookahead"
            }),
            ecma_expected,
            "ECMAScript {name}"
        );

        let pcre_source = plan_for(&semantic, &pcre2);
        let pcre = lower_pcre2(&semantic, &pcre2, &pcre_source).expect("PCRE2");
        let pcre_introduced = &pcre.requirements[pcre.semantic_requirements.len()..];
        assert_eq!(
            pcre_introduced.iter().any(|requirement| {
                requirement.identity.capability_id.as_str() == "assertions.lookahead"
            }),
            pcre_expected,
            "PCRE2 {name}"
        );

        let python_source = plan_for(&semantic, &python);
        if !python_supported {
            assert_eq!(
                lower_python_re(&semantic, &python, &python_source)
                    .expect_err("non-equivalent Unicode word semantics must fail")
                    .code,
                PythonReLoweringErrorCode::UnsupportedRequirement
            );
            continue;
        }
        let python_lowered =
            lower_python_re(&semantic, &python, &python_source).expect("Python re");
        let python_introduced =
            &python_lowered.requirements[python_lowered.semantic_requirements.len()..];
        assert_eq!(
            python_introduced.iter().any(|requirement| {
                requirement.identity.capability_id.as_str() == "assertions.lookahead"
            }),
            python_expected,
            "Python re {name}"
        );
    }
}

#[test]
fn artifact_requirements_are_deterministic_authoritative_identity_material() {
    let target = profile(ECMASCRIPT);
    let semantic = position("node:input-end", "input_end");
    let portability = plan_for(&semantic, &target);
    let first_plan = lower_ecmascript(&semantic, &target, &portability).expect("first lower");
    let second_plan = lower_ecmascript(&semantic, &target, &portability).expect("second lower");
    assert_eq!(first_plan, second_plan);
    let first = serialize_ecmascript(&first_plan).expect("first artifact");
    let second = serialize_ecmascript(&second_plan).expect("second artifact");
    assert_eq!(first, second);
    assert_eq!(
        first
            .requirements
            .iter()
            .map(|requirement| requirement.requirement_id.as_str())
            .collect::<Vec<_>>(),
        [
            "requirement:lowering.0000000000",
            "requirement:semantic.0000000000"
        ]
    );
    assert!(first.requirements.iter().any(|requirement| {
        requirement.resolution_code.as_str() == "lowering_introduced_profile_capability_resolved"
    }));

    let original = artifact_digest(&first);
    let mut mutated = first.clone();
    mutated.requirements.remove(0);
    assert_ne!(artifact_digest(&mutated), original);
}

#[test]
fn malformed_or_missing_requirement_evidence_fails_closed() {
    let target = profile(ECMASCRIPT);
    let semantic = position("node:input-end", "input_end");
    let portability = plan_for(&semantic, &target);
    let mut lowered = lower_ecmascript(&semantic, &target, &portability).expect("lower");
    lowered.requirements.pop();
    assert!(lowered.validate().is_err());
    assert!(serialize_ecmascript(&lowered).is_err());

    let lowered = lower_ecmascript(&semantic, &target, &portability).expect("lower again");
    let mut artifact = serialize_ecmascript(&lowered).expect("artifact");
    let incomplete = remove_capability(&target, "assertions.lookahead");
    artifact.target_profile = incomplete.reference().expect("synthetic profile reference");
    let failure = artifact
        .validate_against_profile(&incomplete)
        .expect_err("unlisted emitted requirement must fail closed");
    assert!(failure
        .errors
        .iter()
        .any(|error| error.path.starts_with("$.requirements")));
}

#[test]
fn target_ast_mutation_cannot_escape_requirement_completeness() {
    let target = profile(ECMASCRIPT);
    let semantic = program(json!({"node_id": "node:literal", "kind": "literal", "text": "a"}));
    let portability = plan_for(&semantic, &target);
    let mut lowered = lower_ecmascript(&semantic, &target, &portability).expect("lower");
    assert!(lowered.requirements.is_empty());
    lowered.root.operation = EcmascriptOperation::Position(EcmascriptPosition::LineStart);
    assert!(lowered.validate().is_err());
    assert!(serialize_ecmascript(&lowered).is_err());
}
