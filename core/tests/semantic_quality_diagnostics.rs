use serde_json::{json, Value};
use strling_kernel::diagnostic::{
    AdviceKind, CompilerPhase, DiagnosticCategory, Severity, SeverityBasis,
};
use strling_kernel::diagnostic_generation::{
    generate_diagnostics, DiagnosticEvidence, DiagnosticGeneration,
    QUALITY_CONTRADICTORY_BOUNDARY_ASSERTIONS, QUALITY_CONTRADICTORY_LOOKAROUND_ASSERTIONS,
    QUALITY_DUPLICATE_ALTERNATION_BRANCH, QUALITY_OVERLAPPING_CHARACTER_SET_MEMBERS,
    QUALITY_REDUNDANT_SINGLE_REPETITION, QUALITY_ZERO_MAXIMUM_REPETITION,
    QUALITY_ZERO_WIDTH_BACKREFERENCE, SAFETY_UNBOUNDED_NULLABLE_REPETITION,
};
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::validation::Validate;

const QUALITY_WARNING: &str =
    include_str!("../../spec/contracts/1.0/examples/diagnostic/semantic-quality-warning.json");

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("quality program must deserialize")
}

fn source_program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "sources": [{
            "contract_version": "1.0.0",
            "source_id": "src:quality",
            "specification_version": "1.0-draft.1",
            "frontend": {"id": "semantic_strling", "dialect_version": "1.0-draft.1"},
            "content": {"kind": "inline", "encoding": "utf-8", "text": "a|a"},
            "provenance": {"kind": "authored"}
        }],
        "root": root
    }))
    .expect("source-backed quality program must deserialize")
}

fn origin(start: u64, end: u64) -> Value {
    json!({
        "source_spans": [{
            "source_id": "src:quality",
            "coordinate_system": "utf8-bytes",
            "start": start,
            "end": end
        }]
    })
}

fn generate(semantic: &SemanticProgram) -> DiagnosticGeneration {
    let foundational = analyze(semantic).expect("foundational analysis");
    let structural = analyze_structure(semantic, &foundational).expect("structural analysis");
    let safety = analyze_safety(semantic, &foundational, &structural).expect("safety analysis");
    generate_diagnostics(semantic, &foundational, &structural, &safety)
        .expect("diagnostic generation")
}

fn zero_maximum_repetition() -> SemanticProgram {
    program(json!({
        "node_id": "node:zero.repeat",
        "kind": "repeat",
        "body": {"node_id": "node:zero.body", "kind": "literal", "text": "a"},
        "min": 0,
        "max": 0,
        "mode": "possessive"
    }))
}

fn redundant_single_repetition(mode: &str) -> SemanticProgram {
    program(json!({
        "node_id": format!("node:single.{mode}"),
        "kind": "repeat",
        "body": {
            "node_id": format!("node:single.{mode}.body"),
            "kind": "literal",
            "text": "a"
        },
        "min": 1,
        "max": 1,
        "mode": mode
    }))
}

fn duplicate_alternation(left: &str, right: &str) -> SemanticProgram {
    program(json!({
        "node_id": "node:duplicate.alt",
        "kind": "alternation",
        "branches": [
            {"node_id": "node:duplicate.left", "kind": "literal", "text": left},
            {"node_id": "node:duplicate.right", "kind": "literal", "text": right}
        ]
    }))
}

fn boundary_pair(with_consumption: bool) -> SemanticProgram {
    let mut items = vec![json!({
        "node_id": "node:boundary.word",
        "kind": "position",
        "position": "word_boundary"
    })];
    if with_consumption {
        items.push(json!({
            "node_id": "node:boundary.literal",
            "kind": "literal",
            "text": "a"
        }));
    }
    items.push(json!({
        "node_id": "node:boundary.not",
        "kind": "position",
        "position": "not_word_boundary"
    }));
    program(json!({
        "node_id": "node:boundary.sequence",
        "kind": "sequence",
        "items": items
    }))
}

fn lookaround_pair(right_text: &str) -> SemanticProgram {
    program(json!({
        "node_id": "node:look.sequence",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:look.positive",
                "kind": "lookaround",
                "direction": "ahead",
                "polarity": "positive",
                "body": {"node_id": "node:look.positive.body", "kind": "literal", "text": "a"}
            },
            {
                "node_id": "node:look.negative",
                "kind": "lookaround",
                "direction": "ahead",
                "polarity": "negative",
                "body": {"node_id": "node:look.negative.body", "kind": "literal", "text": right_text}
            }
        ]
    }))
}

fn character_set(overlapping: bool) -> SemanticProgram {
    let second_start = if overlapping { "h" } else { "n" };
    program(json!({
        "node_id": "node:set",
        "kind": "character_set",
        "negated": false,
        "members": [
            {"kind": "range", "start": "a", "end": "m"},
            {"kind": "range", "start": second_start, "end": "z"}
        ]
    }))
}

fn backreference(capture_body: Value) -> SemanticProgram {
    program(json!({
        "node_id": "node:reference.sequence",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:reference.capture",
                "kind": "capture",
                "capture_id": "capture:quality",
                "body": capture_body
            },
            {
                "node_id": "node:reference.use",
                "kind": "backreference",
                "capture_id": "capture:quality"
            }
        ]
    }))
}

#[test]
fn every_closed_quality_proof_has_one_stable_mapping() {
    let cases = [
        (
            zero_maximum_repetition(),
            QUALITY_ZERO_MAXIMUM_REPETITION,
            Severity::Warning,
        ),
        (
            redundant_single_repetition("greedy"),
            QUALITY_REDUNDANT_SINGLE_REPETITION,
            Severity::Info,
        ),
        (
            duplicate_alternation("a", "a"),
            QUALITY_DUPLICATE_ALTERNATION_BRANCH,
            Severity::Warning,
        ),
        (
            boundary_pair(false),
            QUALITY_CONTRADICTORY_BOUNDARY_ASSERTIONS,
            Severity::Warning,
        ),
        (
            lookaround_pair("a"),
            QUALITY_CONTRADICTORY_LOOKAROUND_ASSERTIONS,
            Severity::Warning,
        ),
        (
            character_set(true),
            QUALITY_OVERLAPPING_CHARACTER_SET_MEMBERS,
            Severity::Info,
        ),
        (
            backreference(json!({"node_id": "node:reference.body", "kind": "empty"})),
            QUALITY_ZERO_WIDTH_BACKREFERENCE,
            Severity::Info,
        ),
    ];

    for (semantic, expected_code, expected_severity) in cases {
        let generated = generate(&semantic);
        assert_eq!(generated.len(), 1, "expected one {expected_code} finding");
        let record = generated.records().next().expect("one quality record");
        assert_eq!(record.diagnostic.code.as_str(), expected_code);
        assert_eq!(record.diagnostic.severity, expected_severity);
        assert_eq!(
            record.diagnostic.severity_basis,
            SeverityBasis::CompilerPolicy
        );
        assert_eq!(record.diagnostic.phase, CompilerPhase::SemanticAnalysis);
        assert_eq!(
            record.diagnostic.category,
            DiagnosticCategory::SemanticValidity
        );
        assert!(matches!(
            record.provenance.evidence,
            DiagnosticEvidence::Quality(_)
        ));
        let advice = record.diagnostic.advice.as_ref().expect("quality advice");
        assert_eq!(advice.len(), 2);
        assert_eq!(advice[0].kind, AdviceKind::Note);
        assert_eq!(advice[1].kind, AdviceKind::Help);
        assert!(record.diagnostic.fixes.is_none());
        assert!(record.diagnostic.primary_location.is_none());
    }
}

#[test]
fn exact_proof_preconditions_reject_adversarial_near_misses() {
    let cases = [
        redundant_single_repetition("possessive"),
        duplicate_alternation("a", "ab"),
        boundary_pair(true),
        lookaround_pair("b"),
        character_set(false),
        backreference(json!({
            "node_id": "node:reference.body",
            "kind": "literal",
            "text": "a"
        })),
    ];

    for semantic in cases {
        let generated = generate(&semantic);
        assert!(generated.is_empty(), "near miss must remain silent");
    }
}

#[test]
fn duplicate_branch_projects_later_primary_and_earlier_related_location() {
    let semantic = source_program(json!({
        "node_id": "node:source.alt",
        "kind": "alternation",
        "origin": origin(0, 3),
        "branches": [
            {
                "node_id": "node:source.left",
                "kind": "literal",
                "origin": origin(0, 1),
                "text": "a"
            },
            {
                "node_id": "node:source.right",
                "kind": "literal",
                "origin": origin(2, 3),
                "text": "a"
            }
        ]
    }));
    let generated = generate(&semantic);
    let diagnostic = generated
        .diagnostics()
        .next()
        .expect("duplicate diagnostic");

    let primary = diagnostic
        .primary_location
        .as_ref()
        .expect("later location");
    assert_eq!((primary.start, primary.end), (2, 3));
    let related = diagnostic
        .related_locations
        .as_ref()
        .expect("earlier location");
    assert!(related
        .iter()
        .any(|location| (location.location.start, location.location.end) == (0, 1)));
}

#[test]
fn existing_safety_identity_and_typed_evidence_are_preserved() {
    let semantic = program(json!({
        "node_id": "node:safety.repeat",
        "kind": "repeat",
        "body": {"node_id": "node:safety.body", "kind": "empty"},
        "min": 0,
        "max": null,
        "mode": "greedy"
    }));
    let generated = generate(&semantic);
    let record = generated.records().next().expect("safety record");

    assert_eq!(
        record.diagnostic.code.as_str(),
        SAFETY_UNBOUNDED_NULLABLE_REPETITION
    );
    assert_eq!(record.diagnostic.category, DiagnosticCategory::Safety);
    assert!(matches!(
        record.provenance.evidence,
        DiagnosticEvidence::Safety(_)
    ));
}

#[test]
fn quality_warning_fixture_uses_the_unchanged_diagnostic_contract() {
    let diagnostic: strling_kernel::diagnostic::Diagnostic =
        serde_json::from_str(QUALITY_WARNING).expect("quality fixture must deserialize");

    diagnostic
        .validate()
        .expect("quality fixture must validate");
    assert_eq!(
        diagnostic.code.as_str(),
        QUALITY_DUPLICATE_ALTERNATION_BRANCH
    );
    assert_eq!(diagnostic.category, DiagnosticCategory::SemanticValidity);
    assert!(diagnostic.fixes.is_none());
}
