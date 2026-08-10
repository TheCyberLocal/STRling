use serde_json::{json, Value};
use strling_kernel::safety_analysis::{analyze_safety, SafetyAnalysisErrorCode, MAX_SAFETY_NODES};
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::{analyze_structure, MAX_STRUCTURE_DEPTH};

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

fn prerequisites(
    semantic: &SemanticProgram,
) -> (
    strling_kernel::semantic_analysis::SemanticFacts,
    strling_kernel::structural_analysis::StructuralFacts,
) {
    let foundational = analyze(semantic).expect("test program needs foundational facts");
    let structural =
        analyze_structure(semantic, &foundational).expect("test program needs structural facts");
    (foundational, structural)
}

#[test]
fn valid_program_has_a_deterministic_empty_framework_result() {
    let semantic = program(literal("node:safety.literal", "a"));
    let unchanged = semantic.clone();
    let (foundational, structural) = prerequisites(&semantic);
    let foundational_unchanged = foundational.clone();
    let structural_unchanged = structural.clone();

    let first = analyze_safety(&semantic, &foundational, &structural).expect("analysis succeeds");
    let second = analyze_safety(&semantic, &foundational, &structural).expect("analysis repeats");

    assert!(first.is_empty());
    assert_eq!(first, second);
    assert_eq!(semantic, unchanged);
    assert_eq!(foundational, foundational_unchanged);
    assert_eq!(structural, structural_unchanged);
}

#[test]
fn mismatched_foundational_store_is_rejected() {
    let semantic = program(literal("node:safety.left", "a"));
    let other = program(literal("node:safety.right", "b"));
    let foreign_foundational = analyze(&other).expect("foreign facts");
    let (foundational, structural) = prerequisites(&semantic);

    let errors = analyze_safety(&semantic, &foreign_foundational, &structural)
        .expect_err("foreign foundational facts must fail");
    assert_eq!(
        errors.errors[0].code,
        SafetyAnalysisErrorCode::MismatchedSemanticFacts
    );
    assert_ne!(foundational, foreign_foundational);
}

#[test]
fn mismatched_structural_store_is_rejected_even_with_matching_versions() {
    let semantic = program(literal("node:safety.left", "a"));
    let other = program(literal("node:safety.right", "b"));
    let (foundational, _) = prerequisites(&semantic);
    let (_, foreign_structural) = prerequisites(&other);

    let errors = analyze_safety(&semantic, &foundational, &foreign_structural)
        .expect_err("foreign structural facts must fail");
    assert_eq!(
        errors.errors[0].code,
        SafetyAnalysisErrorCode::MismatchedStructuralFacts
    );
}

#[test]
fn depth_limit_precedes_fact_store_correspondence() {
    let shallow = program(literal("node:safety.shallow", "a"));
    let (foundational, structural) = prerequisites(&shallow);
    let mut root = Node::Empty {
        node_id: strling_kernel::source::NodeId::try_from("node:safety.deep.0")
            .expect("valid identity"),
        origin: None,
    };
    for depth in 1..=MAX_STRUCTURE_DEPTH {
        root = Node::Atomic {
            node_id: strling_kernel::source::NodeId::try_from(format!("node:safety.deep.{depth}"))
                .expect("valid identity"),
            origin: None,
            body: Box::new(root),
        };
    }
    let deep = SemanticProgram { root, ..shallow };

    let errors = analyze_safety(&deep, &foundational, &structural)
        .expect_err("over-depth input must fail before correspondence");
    assert_eq!(
        errors.errors[0].code,
        SafetyAnalysisErrorCode::DepthLimitExceeded
    );
}

#[test]
fn node_limit_precedes_fact_store_correspondence() {
    let shallow = program(literal("node:safety.shallow", "a"));
    let (foundational, structural) = prerequisites(&shallow);
    let items = (0..MAX_SAFETY_NODES)
        .map(|index| Node::Empty {
            node_id: strling_kernel::source::NodeId::try_from(format!("node:safety.wide.{index}"))
                .expect("valid identity"),
            origin: None,
        })
        .collect();
    let wide = SemanticProgram {
        root: Node::Sequence {
            node_id: strling_kernel::source::NodeId::try_from("node:safety.wide.root")
                .expect("valid identity"),
            origin: None,
            items,
        },
        ..shallow
    };

    let errors = analyze_safety(&wide, &foundational, &structural)
        .expect_err("over-wide input must fail before correspondence");
    assert_eq!(
        errors.errors[0].code,
        SafetyAnalysisErrorCode::NodeLimitExceeded
    );
}
