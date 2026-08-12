use std::collections::BTreeSet;

use serde_json::{json, Value};
use strling_kernel::capability_evaluation::{
    evaluate_capabilities, extract_requirements, CapabilityDisposition, CapabilityEvaluation,
    LookbehindLength, RequirementKind,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;

const PROFILES: [(&str, &str); 4] = [
    (
        "pcre2-10.42",
        include_str!("../../spec/targets/profiles/pcre2-10.42.json"),
    ),
    (
        "pcre2-10.43",
        include_str!("../../spec/targets/profiles/pcre2-10.43.json"),
    ),
    (
        "ecmascript-2024",
        include_str!("../../spec/targets/profiles/ecmascript-2024.json"),
    ),
    (
        "python-re-3.11",
        include_str!("../../spec/targets/profiles/python-re-3.11.json"),
    ),
];

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("fixture program must deserialize")
}

fn literal(node_id: &str, text: &str) -> Value {
    json!({"node_id": node_id, "kind": "literal", "text": text})
}

fn profile(name: &str) -> TargetProfile {
    let fixture = PROFILES
        .iter()
        .find_map(|(candidate, fixture)| (*candidate == name).then_some(*fixture))
        .expect("profile fixture must exist");
    serde_json::from_str(fixture).expect("authored profile must deserialize")
}

fn evaluate(semantic: &SemanticProgram, target: &TargetProfile) -> CapabilityEvaluation {
    let foundational = analyze(semantic).expect("foundational facts");
    let structural = analyze_structure(semantic, &foundational).expect("structural facts");
    evaluate_capabilities(semantic, &foundational, &structural, target)
        .expect("capability evaluation")
}

fn result_for<'a>(
    evaluation: &'a CapabilityEvaluation,
    node_id: &str,
) -> &'a strling_kernel::capability_evaluation::CapabilityResult {
    evaluation
        .results
        .iter()
        .find(|result| result.node_id.as_str() == node_id)
        .expect("fixture node must have a result")
}

fn mixed_program() -> SemanticProgram {
    program(json!({
        "node_id": "node:mixed.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:mixed.capture",
                "kind": "capture",
                "capture_id": "capture:mixed.word",
                "name": "word",
                "body": literal("node:mixed.capture.body", "a")
            },
            {
                "node_id": "node:mixed.reference",
                "kind": "backreference",
                "capture_id": "capture:mixed.word"
            },
            {
                "node_id": "node:mixed.lookahead",
                "kind": "lookaround",
                "direction": "ahead",
                "polarity": "negative",
                "body": literal("node:mixed.lookahead.body", "b")
            },
            {
                "node_id": "node:mixed.lookbehind.fixed",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "positive",
                "body": literal("node:mixed.lookbehind.fixed.body", "cd")
            },
            {
                "node_id": "node:mixed.lookbehind.variable",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "positive",
                "body": {
                    "node_id": "node:mixed.lookbehind.variable.body",
                    "kind": "repeat",
                    "body": literal("node:mixed.lookbehind.variable.operand", "e"),
                    "min": 1,
                    "max": 3,
                    "mode": "greedy"
                }
            },
            {
                "node_id": "node:mixed.atomic",
                "kind": "atomic",
                "body": literal("node:mixed.atomic.body", "i")
            },
            {
                "node_id": "node:mixed.possessive",
                "kind": "repeat",
                "body": literal("node:mixed.possessive.body", "j"),
                "min": 1,
                "max": null,
                "mode": "possessive"
            },
            {
                "node_id": "node:mixed.characters",
                "kind": "character_set",
                "negated": false,
                "members": [
                    {"kind": "literal", "value": "é"},
                    {
                        "kind": "builtin",
                        "name": "word",
                        "domain": "unicode",
                        "negated": false
                    },
                    {
                        "kind": "unicode_property",
                        "property": "Script",
                        "value": "Greek",
                        "negated": false
                    }
                ]
            },
            {
                "node_id": "node:mixed.boundary",
                "kind": "position",
                "position": "word_boundary"
            },
            literal("node:mixed.unicode_literal", "λ")
        ]
    }))
}

#[test]
fn mixed_source_less_program_has_one_ordered_result_per_requirement() {
    let semantic = mixed_program();
    assert!(semantic.sources.is_none());

    for (name, _) in PROFILES {
        let evaluation = evaluate(&semantic, &profile(name));
        assert_eq!(evaluation.requirements.len(), 12, "{name}");
        assert_eq!(
            evaluation.results.len(),
            evaluation.requirements.len(),
            "{name}"
        );
        assert!(evaluation
            .results
            .iter()
            .zip(evaluation.requirements.iter())
            .all(|(result, requirement)| result.requirement == *requirement));
        let unique: BTreeSet<_> = evaluation.requirements.iter().cloned().collect();
        assert_eq!(unique.len(), evaluation.requirements.len(), "{name}");
    }
}

#[test]
fn canonical_profiles_produce_expected_feature_differentials() {
    let semantic = mixed_program();
    let pcre_1042 = evaluate(&semantic, &profile("pcre2-10.42"));
    let pcre_1043 = evaluate(&semantic, &profile("pcre2-10.43"));
    let ecmascript = evaluate(&semantic, &profile("ecmascript-2024"));
    let python = evaluate(&semantic, &profile("python-re-3.11"));

    assert_eq!(
        result_for(&pcre_1042, "node:mixed.lookbehind.variable").disposition,
        CapabilityDisposition::Unsupported
    );
    assert_eq!(
        result_for(&pcre_1043, "node:mixed.lookbehind.variable").disposition,
        CapabilityDisposition::Supported
    );
    assert_eq!(
        result_for(&ecmascript, "node:mixed.lookbehind.variable").disposition,
        CapabilityDisposition::Supported
    );
    assert_eq!(
        result_for(&python, "node:mixed.lookbehind.variable").disposition,
        CapabilityDisposition::Unsupported
    );

    for evaluation in [&pcre_1042, &pcre_1043, &python] {
        assert_eq!(
            result_for(evaluation, "node:mixed.atomic").disposition,
            CapabilityDisposition::Supported
        );
        assert_eq!(
            result_for(evaluation, "node:mixed.possessive").disposition,
            CapabilityDisposition::Supported
        );
    }
    assert_eq!(
        result_for(&ecmascript, "node:mixed.atomic").disposition,
        CapabilityDisposition::Unsupported
    );
    assert_eq!(
        result_for(&ecmascript, "node:mixed.possessive").disposition,
        CapabilityDisposition::Unsupported
    );

    for evaluation in [&pcre_1042, &pcre_1043, &ecmascript, &python] {
        assert_eq!(
            result_for(evaluation, "node:mixed.lookbehind.fixed").disposition,
            CapabilityDisposition::Supported
        );
    }
    for evaluation in [&pcre_1042, &pcre_1043, &ecmascript] {
        let unicode_property = evaluation
            .results
            .iter()
            .find(|result| {
                result.node_id.as_str() == "node:mixed.characters"
                    && result.evaluated_capability.as_str() == "character_properties.unicode"
            })
            .expect("Unicode property result");
        assert_eq!(
            unicode_property.disposition,
            CapabilityDisposition::Supported
        );
    }
    let python_unicode_property = python
        .results
        .iter()
        .find(|result| {
            result.node_id.as_str() == "node:mixed.characters"
                && result.evaluated_capability.as_str() == "character_properties.unicode"
        })
        .expect("Python Unicode property result");
    assert_eq!(
        python_unicode_property.disposition,
        CapabilityDisposition::Unsupported
    );
    for evaluation in [&pcre_1042, &pcre_1043, &ecmascript, &python] {
        assert_eq!(
            result_for(evaluation, "node:mixed.lookahead").disposition,
            CapabilityDisposition::Supported
        );
    }
}

#[test]
fn unbounded_and_indeterminate_lookbehind_use_certified_length_facts() {
    let unbounded = program(json!({
        "node_id": "node:unbounded.lookbehind",
        "kind": "lookaround",
        "direction": "behind",
        "polarity": "positive",
        "body": {
            "node_id": "node:unbounded.body",
            "kind": "repeat",
            "body": literal("node:unbounded.operand", "x"),
            "min": 0,
            "max": null,
            "mode": "greedy"
        }
    }));
    let unbounded_evaluation = evaluate(&unbounded, &profile("pcre2-10.43"));
    assert!(matches!(
        unbounded_evaluation.results[0].requirement.kind,
        RequirementKind::Lookbehind {
            length: LookbehindLength::Unbounded { minimum: 0 },
            ..
        }
    ));
    assert_eq!(
        unbounded_evaluation.results[0].disposition,
        CapabilityDisposition::ConstraintViolation
    );

    let indeterminate = program(json!({
        "node_id": "node:indeterminate.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:indeterminate.capture",
                "kind": "capture",
                "capture_id": "capture:indeterminate.self",
                "body": {
                    "node_id": "node:indeterminate.capture.reference",
                    "kind": "backreference",
                    "capture_id": "capture:indeterminate.self"
                }
            },
            {
                "node_id": "node:indeterminate.lookbehind",
                "kind": "lookaround",
                "direction": "behind",
                "polarity": "negative",
                "body": {
                    "node_id": "node:indeterminate.lookbehind.reference",
                    "kind": "backreference",
                    "capture_id": "capture:indeterminate.self"
                }
            }
        ]
    }));
    let foundational = analyze(&indeterminate).expect("cyclic facts remain conservative");
    let structural = analyze_structure(&indeterminate, &foundational).expect("structural facts");
    let requirements =
        extract_requirements(&indeterminate, &foundational, &structural).expect("requirements");
    let lookbehind = requirements
        .iter()
        .find(|requirement| requirement.node_id.as_str() == "node:indeterminate.lookbehind")
        .expect("lookbehind requirement");
    assert!(matches!(
        lookbehind.kind,
        RequirementKind::Lookbehind {
            length: LookbehindLength::Indeterminate { .. },
            ..
        }
    ));
    let evaluation = evaluate_capabilities(
        &indeterminate,
        &foundational,
        &structural,
        &profile("pcre2-10.43"),
    )
    .expect("capability evaluation");
    assert_eq!(
        result_for(&evaluation, "node:indeterminate.lookbehind").disposition,
        CapabilityDisposition::Unknown
    );
}
