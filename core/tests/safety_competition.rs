use serde_json::{json, Value};
use strling_kernel::safety_analysis::{
    analyze_safety, SafetyEvidence, SafetyFindingCode, SafetyUncertaintyCode,
    SafetyUncertaintyReason,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::NodeId;
use strling_kernel::structural_analysis::analyze_structure;

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

fn literal(id: &str, text: &str) -> Value {
    json!({"node_id": id, "kind": "literal", "text": text})
}

fn repeat(id: &str, body: Value, minimum: u64, maximum: Value, mode: &str) -> Value {
    json!({
        "node_id": id,
        "kind": "repeat",
        "body": body,
        "min": minimum,
        "max": maximum,
        "mode": mode
    })
}

fn alternation(id: &str, branches: Vec<Value>) -> Value {
    json!({"node_id": id, "kind": "alternation", "branches": branches})
}

fn sequence(id: &str, items: Vec<Value>) -> Value {
    json!({"node_id": id, "kind": "sequence", "items": items})
}

fn property(id: &str, property: &str) -> Value {
    json!({
        "node_id": id,
        "kind": "character_set",
        "negated": false,
        "members": [{
            "kind": "unicode_property",
            "property": property,
            "negated": false
        }]
    })
}

fn wildcard(id: &str, line_terminators: &str) -> Value {
    json!({
        "node_id": id,
        "kind": "wildcard",
        "line_terminators": line_terminators
    })
}

fn analyze_program(semantic: &SemanticProgram) -> strling_kernel::safety_analysis::SafetyAnalysis {
    let foundational = analyze(semantic).expect("test program needs foundational facts");
    let structural =
        analyze_structure(semantic, &foundational).expect("test program needs structural facts");
    analyze_safety(semantic, &foundational, &structural).expect("safety analysis must succeed")
}

fn has_finding(
    analysis: &strling_kernel::safety_analysis::SafetyAnalysis,
    code: SafetyFindingCode,
) -> bool {
    analysis.findings().any(|finding| finding.code == code)
}

fn node_id(value: &str) -> NodeId {
    NodeId::try_from(value).expect("test node identity must be valid")
}

#[test]
fn repeated_alternatives_distinguish_disjoint_overlap_and_identical_prefix() {
    let disjoint = program(repeat(
        "node:repeat",
        alternation(
            "node:alt",
            vec![literal("node:left", "a"), literal("node:right", "b")],
        ),
        0,
        Value::Null,
        "greedy",
    ));
    assert!(!has_finding(
        &analyze_program(&disjoint),
        SafetyFindingCode::RepeatedAlternationOverlap
    ));

    for right in [literal("node:right", "a"), literal("node:right", "ab")] {
        let overlapping = program(repeat(
            "node:repeat",
            alternation("node:alt", vec![literal("node:left", "a"), right]),
            0,
            Value::Null,
            "lazy",
        ));
        let analysis = analyze_program(&overlapping);
        let finding = analysis
            .findings()
            .find(|finding| finding.code == SafetyFindingCode::RepeatedAlternationOverlap)
            .expect("proved branch overlap must produce a finding");
        let SafetyEvidence::RepeatedAlternation {
            left_branch_index,
            right_branch_index,
            relationship,
            ..
        } = &finding.evidence
        else {
            panic!("alternation finding requires alternation evidence");
        };
        assert_eq!((*left_branch_index, *right_branch_index), (0, 1));
        assert_eq!(relationship.left_node_id, node_id("node:left"));
        assert_eq!(relationship.right_node_id, node_id("node:right"));
    }
}

#[test]
fn unknown_property_and_wildcard_relations_remain_uncertain() {
    let properties = program(repeat(
        "node:repeat",
        alternation(
            "node:alt",
            vec![
                property("node:left", "General_Category"),
                property("node:right", "Script"),
            ],
        ),
        0,
        Value::Null,
        "greedy",
    ));
    let analysis = analyze_program(&properties);
    assert!(!has_finding(
        &analysis,
        SafetyFindingCode::RepeatedAlternationOverlap
    ));
    assert!(analysis.uncertainties().any(|uncertainty| {
        uncertainty.code == SafetyUncertaintyCode::RepeatedAlternationNotProven
            && matches!(
                uncertainty.reason,
                SafetyUncertaintyReason::StructuralOverlap(_)
            )
    }));

    let wildcard_unknown = program(repeat(
        "node:repeat",
        alternation(
            "node:alt",
            vec![wildcard("node:left", "exclude"), literal("node:right", "q")],
        ),
        0,
        Value::Null,
        "greedy",
    ));
    let analysis = analyze_program(&wildcard_unknown);
    assert!(!has_finding(
        &analysis,
        SafetyFindingCode::RepeatedAlternationOverlap
    ));
    assert!(
        analysis
            .uncertainties()
            .any(|uncertainty| uncertainty.code
                == SafetyUncertaintyCode::RepeatedAlternationNotProven)
    );

    let wildcard_proven = program(repeat(
        "node:repeat",
        alternation(
            "node:alt",
            vec![wildcard("node:left", "include"), literal("node:right", "q")],
        ),
        0,
        Value::Null,
        "greedy",
    ));
    assert!(has_finding(
        &analyze_program(&wildcard_proven),
        SafetyFindingCode::RepeatedAlternationOverlap
    ));
}

#[test]
fn empty_only_branch_overlap_is_not_promoted_to_ambiguity() {
    let semantic = program(repeat(
        "node:repeat",
        alternation(
            "node:alt",
            vec![
                json!({"node_id": "node:left", "kind": "empty"}),
                json!({"node_id": "node:right", "kind": "empty"}),
            ],
        ),
        0,
        Value::Null,
        "greedy",
    ));
    let analysis = analyze_program(&semantic);
    assert!(!has_finding(
        &analysis,
        SafetyFindingCode::RepeatedAlternationOverlap
    ));
    assert!(analysis.uncertainties().any(|uncertainty| {
        uncertainty.code == SafetyUncertaintyCode::RepeatedAlternationNotProven
            && uncertainty.reason == SafetyUncertaintyReason::NullableOnlyOverlap
    }));
}

#[test]
fn alternation_requires_a_repeated_non_atomic_region() {
    let once = program(repeat(
        "node:repeat",
        alternation(
            "node:alt",
            vec![literal("node:left", "a"), literal("node:right", "a")],
        ),
        1,
        json!(1),
        "greedy",
    ));
    assert!(!has_finding(
        &analyze_program(&once),
        SafetyFindingCode::RepeatedAlternationOverlap
    ));

    let twice = program(repeat(
        "node:repeat",
        alternation(
            "node:alt",
            vec![literal("node:left", "a"), literal("node:right", "a")],
        ),
        2,
        json!(2),
        "greedy",
    ));
    assert!(has_finding(
        &analyze_program(&twice),
        SafetyFindingCode::RepeatedAlternationOverlap
    ));

    let atomic = program(repeat(
        "node:repeat",
        json!({
            "node_id": "node:atomic",
            "kind": "atomic",
            "body": alternation(
                "node:alt",
                vec![literal("node:left", "a"), literal("node:right", "a")]
            )
        }),
        0,
        Value::Null,
        "greedy",
    ));
    assert!(!has_finding(
        &analyze_program(&atomic),
        SafetyFindingCode::RepeatedAlternationOverlap
    ));
}

#[test]
fn repetition_follower_competition_uses_only_certified_immediate_relationships() {
    let disjoint = program(sequence(
        "node:sequence",
        vec![
            repeat(
                "node:repeat",
                literal("node:operand", "a"),
                0,
                Value::Null,
                "greedy",
            ),
            literal("node:follower", "b"),
        ],
    ));
    assert!(!has_finding(
        &analyze_program(&disjoint),
        SafetyFindingCode::RepetitionFollowerOverlap
    ));

    let overlapping = program(sequence(
        "node:sequence",
        vec![
            repeat(
                "node:repeat",
                literal("node:operand", "a"),
                0,
                Value::Null,
                "greedy",
            ),
            literal("node:follower", "a"),
        ],
    ));
    let analysis = analyze_program(&overlapping);
    let finding = analysis
        .findings()
        .find(|finding| finding.code == SafetyFindingCode::RepetitionFollowerOverlap)
        .expect("overlapping follower must produce a finding");
    assert_eq!(finding.primary_node_id, node_id("node:repeat"));
    assert!(matches!(
        finding.evidence,
        SafetyEvidence::RepetitionFollower { .. }
    ));
}

#[test]
fn nullable_follower_can_compete_with_an_always_consuming_operand() {
    let semantic = program(sequence(
        "node:sequence",
        vec![
            repeat(
                "node:repeat",
                literal("node:operand", "a"),
                0,
                Value::Null,
                "greedy",
            ),
            repeat(
                "node:follower",
                literal("node:follower.body", "a"),
                0,
                json!(1),
                "greedy",
            ),
        ],
    ));
    assert!(has_finding(
        &analyze_program(&semantic),
        SafetyFindingCode::RepetitionFollowerOverlap
    ));
}

#[test]
fn follower_competition_requires_variable_non_possessive_repetition_count() {
    let cases = [
        ("node:bounded", 0, json!(2), "greedy", true),
        ("node:exact", 2, json!(2), "greedy", false),
        ("node:possessive", 0, Value::Null, "possessive", false),
    ];
    for (id, minimum, maximum, mode, expected) in cases {
        let semantic = program(sequence(
            "node:sequence",
            vec![
                repeat(
                    id,
                    literal(&format!("{id}.operand"), "a"),
                    minimum,
                    maximum,
                    mode,
                ),
                literal(&format!("{id}.follower"), "a"),
            ],
        ));
        assert_eq!(
            has_finding(
                &analyze_program(&semantic),
                SafetyFindingCode::RepetitionFollowerOverlap
            ),
            expected,
            "unexpected follower conclusion for {id}"
        );
    }
}

#[test]
fn follower_unknowns_from_properties_and_wildcards_are_preserved() {
    for operand in [
        property("node:operand", "General_Category"),
        wildcard("node:operand", "exclude"),
    ] {
        let semantic = program(sequence(
            "node:sequence",
            vec![
                repeat("node:repeat", operand, 0, Value::Null, "greedy"),
                literal("node:follower", "q"),
            ],
        ));
        let analysis = analyze_program(&semantic);
        assert!(!has_finding(
            &analysis,
            SafetyFindingCode::RepetitionFollowerOverlap
        ));
        assert!(analysis
            .uncertainties()
            .any(|uncertainty| uncertainty.code
                == SafetyUncertaintyCode::RepetitionFollowerNotProven));
    }

    let wildcard = program(sequence(
        "node:sequence",
        vec![
            repeat(
                "node:repeat",
                wildcard("node:operand", "include"),
                0,
                Value::Null,
                "greedy",
            ),
            literal("node:follower", "q"),
        ],
    ));
    assert!(has_finding(
        &analyze_program(&wildcard),
        SafetyFindingCode::RepetitionFollowerOverlap
    ));
}

#[test]
fn competition_evidence_order_is_deterministic() {
    let semantic = program(sequence(
        "node:sequence",
        vec![
            repeat(
                "node:repeat",
                alternation(
                    "node:alt",
                    vec![
                        literal("node:branch.z", "a"),
                        literal("node:branch.a", "a"),
                        literal("node:branch.m", "a"),
                    ],
                ),
                0,
                Value::Null,
                "greedy",
            ),
            literal("node:follower", "a"),
        ],
    ));
    let first = analyze_program(&semantic);
    let second = analyze_program(&semantic);
    assert_eq!(first, second);
    assert!(first.findings().all(|finding| finding
        .evidence_node_ids
        .windows(2)
        .all(|pair| pair[0] < pair[1])));
}
