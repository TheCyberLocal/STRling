use serde_json::{json, Value};
use strling_kernel::capability_evaluation::{
    evaluate_capabilities, evaluate_capabilities_for_reference, CapabilityDisposition,
    CapabilityEvaluation, CapabilityEvaluationErrorCode, ConstraintDisposition, ConstraintEvidence,
    ConstraintFactValue,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::{Sha256Digest, SpecificationVersion};
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{
    ConstraintScalar, ProfileVersion, TargetProfile, TargetProfileReference, TargetProfileSet,
};

const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");
const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PYTHON_RE_311: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("test program must deserialize")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn profile(fixture: &str) -> TargetProfile {
    serde_json::from_str(fixture).expect("authored target profile must deserialize")
}

fn evaluate(semantic: &SemanticProgram, target: &TargetProfile) -> CapabilityEvaluation {
    let foundational = analyze(semantic).expect("program must have foundational facts");
    let structural =
        analyze_structure(semantic, &foundational).expect("program must have structural facts");
    evaluate_capabilities(semantic, &foundational, &structural, target)
        .expect("capability evaluation must succeed")
}

fn variable_lookbehind(maximum: usize) -> SemanticProgram {
    program(json!({
        "node_id": "node:lookbehind",
        "kind": "lookaround",
        "direction": "behind",
        "polarity": "positive",
        "body": {
            "node_id": "node:lookbehind.body",
            "kind": "repeat",
            "body": literal("node:lookbehind.repeated", "x"),
            "min": 1,
            "max": maximum,
            "mode": "greedy"
        }
    }))
}

fn bounded_only_profile() -> TargetProfile {
    let mut target = profile(PCRE2_1043);
    let capability = target
        .capabilities
        .iter_mut()
        .find(|candidate| {
            candidate.capability_id.as_str() == "assertions.lookbehind.variable_length"
        })
        .expect("profile must declare variable lookbehind");
    capability
        .constraints
        .retain(|constraint| constraint.constraint_id.as_str() == "bounded_maximum");
    target
}

#[test]
fn lookup_distinguishes_supported_unsupported_and_absent_capabilities() {
    let atomic = program(json!({
        "node_id": "node:atomic",
        "kind": "atomic",
        "body": literal("node:atomic.body", "a")
    }));
    assert_eq!(
        evaluate(&atomic, &profile(PCRE2_1042)).results[0].disposition,
        CapabilityDisposition::Supported
    );
    assert_eq!(
        evaluate(&atomic, &profile(ECMASCRIPT)).results[0].disposition,
        CapabilityDisposition::Unsupported
    );

    let lookahead = program(json!({
        "node_id": "node:lookahead",
        "kind": "lookaround",
        "direction": "ahead",
        "polarity": "positive",
        "body": literal("node:lookahead.body", "a")
    }));
    let supported = evaluate(&lookahead, &profile(PCRE2_1042));
    assert_eq!(
        supported.results[0].disposition,
        CapabilityDisposition::Supported
    );
    assert!(supported.results[0].profile_capability.is_some());

    let mut incomplete = profile(PCRE2_1042);
    incomplete
        .capabilities
        .retain(|capability| capability.capability_id.as_str() != "assertions.lookahead");
    let absent = evaluate(&lookahead, &incomplete);
    assert_eq!(
        absent.results[0].disposition,
        CapabilityDisposition::Unknown
    );
    assert!(absent.results[0].profile_capability.is_none());
}

#[test]
fn profile_versions_change_results_without_changing_requirements() {
    let semantic = variable_lookbehind(3);
    let earlier = evaluate(&semantic, &profile(PCRE2_1042));
    let modern = evaluate(&semantic, &profile(PCRE2_1043));

    assert_eq!(earlier.requirements, modern.requirements);
    assert_eq!(
        earlier.results[0].disposition,
        CapabilityDisposition::Unsupported
    );
    assert_eq!(
        modern.results[0].disposition,
        CapabilityDisposition::Supported
    );
    assert_eq!(
        modern.results[0]
            .constraint_evaluations
            .iter()
            .map(|result| result.disposition)
            .collect::<Vec<_>>(),
        [
            ConstraintDisposition::Satisfied,
            ConstraintDisposition::Satisfied
        ]
    );
    assert_ne!(earlier.target_engine.version, modern.target_engine.version);
}

#[test]
fn fixed_alternatives_respect_profile_width_rules() {
    let semantic = program(json!({
        "node_id": "node:lookbehind.fixed-alternatives",
        "kind": "lookaround",
        "direction": "behind",
        "polarity": "negative",
        "body": {
            "node_id": "node:lookbehind.fixed-alternatives.body",
            "kind": "alternation",
            "branches": [
                literal("node:lookbehind.fixed-alternatives.short", "x"),
                literal("node:lookbehind.fixed-alternatives.long", "yz")
            ]
        }
    }));
    for target in [profile(PCRE2_1042), profile(PCRE2_1043)] {
        let result = evaluate(&semantic, &target);
        assert_eq!(
            result.requirements.requirements[0].capability_id.as_str(),
            "assertions.lookbehind.fixed_length"
        );
        assert_eq!(
            result.results[0].disposition,
            CapabilityDisposition::Supported
        );
        assert!(result.results[0].constraint_facts.iter().any(|fact| {
            fact.constraint_id.as_str() == "common_fixed_width"
                && fact.value == ConstraintFactValue::Scalar(ConstraintScalar::Boolean(false))
        }));
    }

    let python = evaluate(&semantic, &profile(PYTHON_RE_311));
    assert_eq!(
        python.results[0].disposition,
        CapabilityDisposition::ConstraintViolation
    );
    assert_eq!(
        python.results[0].constraint_evaluations[0].disposition,
        ConstraintDisposition::Violated
    );
}

#[test]
fn capture_name_shape_and_length_are_profile_constraints() {
    fn named_capture(name: &str) -> SemanticProgram {
        program(json!({
            "node_id": "node:capture",
            "kind": "capture",
            "capture_id": "capture:named",
            "name": name,
            "body": literal("node:capture.body", "x")
        }))
    }

    let target = profile(PCRE2_1042);
    assert_eq!(
        evaluate(&named_capture(&"a".repeat(32)), &target).results[0].disposition,
        CapabilityDisposition::Supported
    );
    for name in [&"a".repeat(33), "bad-name"] {
        assert_eq!(
            evaluate(&named_capture(name), &target).results[0].disposition,
            CapabilityDisposition::ConstraintViolation
        );
    }
}

#[test]
fn bounded_constraint_is_supported_or_violated_from_structural_evidence() {
    let target = bounded_only_profile();
    let satisfied = evaluate(&variable_lookbehind(255), &target);
    assert_eq!(
        satisfied.results[0].disposition,
        CapabilityDisposition::Supported
    );
    assert_eq!(
        satisfied.results[0].constraint_evaluations[0].disposition,
        ConstraintDisposition::Satisfied
    );

    let violated = evaluate(&variable_lookbehind(256), &target);
    assert_eq!(
        violated.results[0].disposition,
        CapabilityDisposition::ConstraintViolation
    );
    let evidence = &violated.results[0].constraint_evaluations[0].evidence;
    assert!(matches!(evidence, ConstraintEvidence::RequirementFact(_)));
    assert_eq!(
        violated.results[0].constraint_evaluations[0].disposition,
        ConstraintDisposition::Violated
    );
}

#[test]
fn required_profile_option_satisfies_unicode_property_constraint() {
    let semantic = program(json!({
        "node_id": "node:unicode",
        "kind": "character_set",
        "negated": false,
        "members": [{
            "kind": "unicode_property",
            "property": "General_Category",
            "value": "Letter",
            "negated": false
        }]
    }));
    let result = evaluate(&semantic, &profile(PCRE2_1042));
    assert_eq!(
        result.results[0].disposition,
        CapabilityDisposition::Supported
    );
    assert!(matches!(
        result.results[0].constraint_evaluations[0].evidence,
        ConstraintEvidence::ProfileOption(_)
    ));
}

#[test]
fn malformed_and_incompatible_profiles_are_rejected_before_lookup() {
    let semantic = program(json!({
        "node_id": "node:atomic",
        "kind": "atomic",
        "body": literal("node:atomic.body", "a")
    }));
    let foundational = analyze(&semantic).expect("foundational facts");
    let structural = analyze_structure(&semantic, &foundational).expect("structural facts");

    let mut malformed = profile(PCRE2_1042);
    malformed.capabilities.reverse();
    let errors = evaluate_capabilities(&semantic, &foundational, &structural, &malformed)
        .expect_err("noncanonical profile must fail");
    assert!(errors
        .errors
        .iter()
        .all(|error| error.code == CapabilityEvaluationErrorCode::InvalidTargetProfile));

    let mut incompatible = profile(PCRE2_1042);
    incompatible.compatible_specification_versions =
        vec![SpecificationVersion::try_from("1.1").expect("valid version")];
    let errors = evaluate_capabilities(&semantic, &foundational, &structural, &incompatible)
        .expect_err("incompatible profile must fail");
    assert_eq!(
        errors.errors[0].code,
        CapabilityEvaluationErrorCode::IncompatibleTargetProfile
    );
}

#[test]
fn reference_lookup_rejects_revision_and_fingerprint_mismatches() {
    let semantic = program(json!({
        "node_id": "node:atomic",
        "kind": "atomic",
        "body": literal("node:atomic.body", "a")
    }));
    let foundational = analyze(&semantic).expect("foundational facts");
    let structural = analyze_structure(&semantic, &foundational).expect("structural facts");
    let target = profile(PCRE2_1042);
    let reference = target.reference().expect("canonical reference");
    let profiles = TargetProfileSet::new(vec![target]).expect("valid profile set");

    let mut wrong_revision = reference.clone();
    wrong_revision.profile_version =
        ProfileVersion::try_from("2.0.0").expect("valid profile revision");
    let errors = evaluate_capabilities_for_reference(
        &semantic,
        &foundational,
        &structural,
        &wrong_revision,
        &profiles,
    )
    .expect_err("unknown revision must fail");
    assert_eq!(
        errors.errors[0].code,
        CapabilityEvaluationErrorCode::TargetProfileResolution
    );

    let wrong_fingerprint = TargetProfileReference {
        sha256: Sha256Digest::try_from("0".repeat(64)).expect("valid digest shape"),
        ..reference
    };
    let errors = evaluate_capabilities_for_reference(
        &semantic,
        &foundational,
        &structural,
        &wrong_fingerprint,
        &profiles,
    )
    .expect_err("wrong fingerprint must fail");
    assert_eq!(
        errors.errors[0].code,
        CapabilityEvaluationErrorCode::TargetProfileResolution
    );
}
