use serde_json::{json, Value};
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::NodeId;
use strling_kernel::structural_analysis::{
    analyze_structure, OverlapRelation, OverlapUnknownReason, StructuralAnalysisErrorCode,
    MAX_STRUCTURE_DEPTH,
};

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

fn insensitive_program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "insensitive",
        "root": root
    }))
    .expect("test program must deserialize")
}

fn literal(id: &str, text: &str) -> Value {
    json!({"node_id": id, "kind": "literal", "text": text})
}

fn node_id(value: &str) -> NodeId {
    NodeId::try_from(value).expect("test node identity must be valid")
}

fn analyze_program(
    semantic: &SemanticProgram,
) -> strling_kernel::structural_analysis::StructuralFacts {
    let foundational = analyze(semantic).expect("test program must have foundational facts");
    analyze_structure(semantic, &foundational).expect("test program must have structural facts")
}

#[test]
fn literal_overlap_is_exact_and_pair_order_is_canonical() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            literal("node:branch.0", "a"),
            literal("node:branch.1", "a"),
            literal("node:branch.2", "b"),
            literal("node:branch.3", "c")
        ]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .alternation_branch_overlaps;

    let pairs: Vec<_> = relationships
        .iter()
        .map(|relationship| {
            (
                relationship.left_branch_index,
                relationship.right_branch_index,
                relationship.relation,
            )
        })
        .collect();
    assert_eq!(
        pairs,
        vec![
            (0, 1, OverlapRelation::Overlapping),
            (0, 2, OverlapRelation::Disjoint),
            (0, 3, OverlapRelation::Disjoint),
            (1, 2, OverlapRelation::Disjoint),
            (1, 3, OverlapRelation::Disjoint),
            (2, 3, OverlapRelation::Disjoint),
        ]
    );
}

#[test]
fn finite_sets_and_ranges_prove_intersection_or_disjointness() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            {
                "node_id": "node:set.left",
                "kind": "character_set",
                "negated": false,
                "members": [{"kind": "range", "start": "a", "end": "f"}]
            },
            {
                "node_id": "node:set.middle",
                "kind": "character_set",
                "negated": false,
                "members": [{"kind": "range", "start": "d", "end": "m"}]
            },
            {
                "node_id": "node:set.right",
                "kind": "character_set",
                "negated": false,
                "members": [{"kind": "range", "start": "x", "end": "z"}]
            }
        ]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .alternation_branch_overlaps;
    assert_eq!(relationships[0].relation, OverlapRelation::Overlapping);
    assert_eq!(relationships[1].relation, OverlapRelation::Disjoint);
    assert_eq!(relationships[2].relation, OverlapRelation::Disjoint);
}

#[test]
fn literal_set_relations_handle_positive_and_negative_finite_sets() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            literal("node:literal.in", "b"),
            {
                "node_id": "node:set.positive",
                "kind": "character_set",
                "negated": false,
                "members": [{"kind": "range", "start": "a", "end": "c"}]
            },
            literal("node:literal.out", "z"),
            {
                "node_id": "node:set.negative",
                "kind": "character_set",
                "negated": true,
                "members": [{"kind": "range", "start": "a", "end": "c"}]
            }
        ]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .alternation_branch_overlaps;
    assert_eq!(relationships[0].relation, OverlapRelation::Overlapping);
    assert_eq!(relationships[1].relation, OverlapRelation::Disjoint);
    assert_eq!(relationships[2].relation, OverlapRelation::Disjoint);
    assert_eq!(relationships[5].relation, OverlapRelation::Overlapping);
}

#[test]
fn wildcard_and_category_relations_preserve_conservative_unknowns() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            {
                "node_id": "node:wild.include",
                "kind": "wildcard",
                "line_terminators": "include"
            },
            literal("node:literal", "q"),
            {
                "node_id": "node:wild.exclude",
                "kind": "wildcard",
                "line_terminators": "exclude"
            },
            {
                "node_id": "node:category",
                "kind": "character_set",
                "negated": false,
                "members": [{
                    "kind": "builtin",
                    "name": "digit",
                    "domain": "unicode",
                    "negated": false
                }]
            }
        ]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .alternation_branch_overlaps;
    assert_eq!(relationships[0].relation, OverlapRelation::Overlapping);
    assert_eq!(
        relationships[3].relation,
        OverlapRelation::Unknown(OverlapUnknownReason::LineTerminatorExclusion)
    );
    assert_eq!(
        relationships[4].relation,
        OverlapRelation::Unknown(OverlapUnknownReason::CharacterCategory)
    );
}

#[test]
fn insensitive_distinct_scalars_are_not_guessed_disjoint() {
    let semantic = insensitive_program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [literal("node:left", "a"), literal("node:right", "A")]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .alternation_branch_overlaps;
    assert_eq!(
        relationships[0].relation,
        OverlapRelation::Unknown(OverlapUnknownReason::CaseFolding)
    );
}

#[test]
fn nullable_branches_compare_empty_without_borrowing_inner_consumption() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            {"node_id": "node:empty.0", "kind": "empty"},
            {"node_id": "node:empty.1", "kind": "empty"},
            literal("node:literal", "x")
        ]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .alternation_branch_overlaps;
    assert_eq!(relationships[0].relation, OverlapRelation::Overlapping);
    assert_eq!(relationships[1].relation, OverlapRelation::Disjoint);
    assert_eq!(relationships[2].relation, OverlapRelation::Disjoint);
}

#[test]
fn nested_wrappers_and_nullable_prefixes_feed_branch_relationships() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            {
                "node_id": "node:atomic",
                "kind": "atomic",
                "body": literal("node:atomic.body", "x")
            },
            {
                "node_id": "node:sequence",
                "kind": "sequence",
                "items": [
                    {
                        "node_id": "node:position",
                        "kind": "position",
                        "position": "input_start"
                    },
                    {
                        "node_id": "node:capture",
                        "kind": "capture",
                        "capture_id": "capture:nested",
                        "name": "nested",
                        "body": literal("node:capture.body", "x")
                    }
                ]
            }
        ]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .alternation_branch_overlaps;
    assert_eq!(relationships[0].relation, OverlapRelation::Overlapping);
}

#[test]
fn repeated_operands_are_compared_with_immediate_followers_only() {
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:repeat.a",
                "kind": "repeat",
                "body": literal("node:repeat.a.body", "a"),
                "min": 0,
                "max": null,
                "mode": "greedy"
            },
            literal("node:follow.a", "a"),
            {
                "node_id": "node:separator",
                "kind": "position",
                "position": "word_boundary"
            },
            {
                "node_id": "node:repeat.b",
                "kind": "repeat",
                "body": literal("node:repeat.b.body", "b"),
                "min": 1,
                "max": 3,
                "mode": "lazy"
            },
            literal("node:follow.z", "z")
        ]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .repetition_follow_overlaps;

    assert_eq!(relationships.len(), 2);
    assert_eq!(
        (
            relationships[0].repetition_index,
            relationships[0].following_index,
            relationships[0].relation,
        ),
        (0, 1, OverlapRelation::Overlapping)
    );
    assert_eq!(
        (
            relationships[1].repetition_index,
            relationships[1].following_index,
            relationships[1].relation,
        ),
        (3, 4, OverlapRelation::Disjoint)
    );
}

#[test]
fn relationship_limit_is_a_stable_structured_error() {
    let branches: Vec<_> = (0..92)
        .map(|index| literal(&format!("node:branch.{index}"), &format!("{index:03}")))
        .collect();
    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": branches
    }));
    let foundational = analyze(&semantic).expect("large alternation must have foundational facts");
    let error = analyze_structure(&semantic, &foundational)
        .expect_err("pair limit must reject excessive relationship materialization");
    assert_eq!(
        error.errors[0].code,
        StructuralAnalysisErrorCode::RelationshipLimitExceeded
    );
}

#[test]
fn overlap_comparison_limit_returns_typed_uncertainty() {
    fn inner(id: &str, base: u32) -> Value {
        let branches: Vec<_> = (0..65)
            .map(|index| {
                let scalar = char::from_u32(base + index).expect("test scalar must be valid");
                literal(&format!("{id}.literal.{index}"), &scalar.to_string())
            })
            .collect();
        json!({
            "node_id": format!("{id}.alternation"),
            "kind": "alternation",
            "branches": branches
        })
    }

    let semantic = program(json!({
        "node_id": "node:root",
        "kind": "alternation",
        "branches": [
            {
                "node_id": "node:left",
                "kind": "atomic",
                "body": inner("node:left", 0x1000)
            },
            {
                "node_id": "node:right",
                "kind": "atomic",
                "body": inner("node:right", 0x2000)
            }
        ]
    }));
    let facts = analyze_program(&semantic);
    let relationships = &facts
        .get(&node_id("node:root"))
        .expect("root facts")
        .alternation_branch_overlaps;
    assert_eq!(
        relationships[0].relation,
        OverlapRelation::Unknown(OverlapUnknownReason::ComparisonLimitExceeded)
    );
}

#[test]
fn depth_limit_precedes_mismatched_fact_store_validation() {
    let shallow = program(literal("node:shallow", "x"));
    let foundational = analyze(&shallow).expect("shallow facts");

    let mut root = Node::Literal {
        node_id: node_id("node:deep.literal"),
        origin: None,
        text: "x".to_owned(),
    };
    for depth in 0..=MAX_STRUCTURE_DEPTH {
        root = Node::Atomic {
            node_id: node_id(&format!("node:deep.atomic.{depth}")),
            origin: None,
            body: Box::new(root),
        };
    }
    let mut deep = shallow;
    deep.root = root;

    let error = analyze_structure(&deep, &foundational)
        .expect_err("structural depth limit must return a typed error");
    assert_eq!(
        error.errors[0].code,
        StructuralAnalysisErrorCode::DepthLimitExceeded
    );
}
