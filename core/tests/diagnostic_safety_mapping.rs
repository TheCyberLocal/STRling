use serde_json::{json, Value};
use strling_kernel::diagnostic::{
    AdviceKind, CompilerPhase, DiagnosticCategory, Severity, SeverityBasis,
};
use strling_kernel::diagnostic_generation::{
    generate_diagnostics, DiagnosticGeneration, SAFETY_NESTED_REPETITION_OVERLAP,
    SAFETY_REPEATED_ALTERNATION_OVERLAP, SAFETY_REPETITION_FOLLOWER_OVERLAP,
    SAFETY_UNBOUNDED_INDETERMINATE_PROGRESS, SAFETY_UNBOUNDED_NULLABLE_REPETITION,
};
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;

const SOURCE_TEXT: &str = "α😀abcdefghij";

fn origin(start: u64, end: u64) -> Value {
    json!({
        "source_spans": [{
            "source_id": "src:diagnostic",
            "coordinate_system": "utf8-bytes",
            "start": start,
            "end": end
        }]
    })
}

fn source_program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "sources": [{
            "contract_version": "1.0.0",
            "source_id": "src:diagnostic",
            "specification_version": "1.0-draft.1",
            "frontend": {
                "id": "semantic_strling",
                "dialect_version": "1.0-draft.1"
            },
            "content": {
                "kind": "inline",
                "encoding": "utf-8",
                "text": SOURCE_TEXT
            },
            "provenance": {"kind": "authored"}
        }],
        "root": root
    }))
    .expect("source-backed semantic program must deserialize")
}

fn generate(semantic: &SemanticProgram) -> DiagnosticGeneration {
    let foundational = analyze(semantic).expect("foundational analysis must succeed");
    let structural =
        analyze_structure(semantic, &foundational).expect("structural analysis must succeed");
    let safety =
        analyze_safety(semantic, &foundational, &structural).expect("safety analysis must succeed");
    generate_diagnostics(semantic, &foundational, &structural, &safety)
        .expect("diagnostic generation must succeed")
}

fn nullable_program() -> SemanticProgram {
    source_program(json!({
        "node_id": "node:nullable",
        "kind": "repeat",
        "origin": {
            "source_spans": [
                {
                    "source_id": "src:diagnostic",
                    "coordinate_system": "utf8-bytes",
                    "start": 0,
                    "end": 2
                },
                {
                    "source_id": "src:diagnostic",
                    "coordinate_system": "utf8-bytes",
                    "start": 2,
                    "end": 6
                }
            ]
        },
        "body": {
            "node_id": "node:nullable.body",
            "kind": "empty",
            "origin": origin(2, 6)
        },
        "min": 0,
        "max": null,
        "mode": "greedy"
    }))
}

fn indeterminate_program() -> SemanticProgram {
    source_program(json!({
        "node_id": "node:indeterminate.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:indeterminate.capture",
                "kind": "capture",
                "capture_id": "capture:optional",
                "body": {
                    "node_id": "node:indeterminate.optional",
                    "kind": "repeat",
                    "body": {
                        "node_id": "node:indeterminate.literal",
                        "kind": "literal",
                        "text": "a"
                    },
                    "min": 0,
                    "max": 1,
                    "mode": "greedy"
                }
            },
            {
                "node_id": "node:indeterminate.repeat",
                "kind": "repeat",
                "origin": origin(2, 6),
                "body": {
                    "node_id": "node:indeterminate.reference",
                    "kind": "backreference",
                    "origin": origin(6, 7),
                    "capture_id": "capture:optional"
                },
                "min": 1,
                "max": null,
                "mode": "greedy"
            }
        ]
    }))
}

fn nested_program() -> SemanticProgram {
    source_program(json!({
        "node_id": "node:nested.outer",
        "kind": "repeat",
        "origin": origin(0, 2),
        "body": {
            "node_id": "node:nested.inner",
            "kind": "repeat",
            "origin": origin(2, 6),
            "body": {
                "node_id": "node:nested.atom",
                "kind": "literal",
                "origin": origin(6, 7),
                "text": "a"
            },
            "min": 1,
            "max": null,
            "mode": "greedy"
        },
        "min": 0,
        "max": null,
        "mode": "greedy"
    }))
}

fn alternation_program() -> SemanticProgram {
    source_program(json!({
        "node_id": "node:alternation.repeat",
        "kind": "repeat",
        "origin": origin(0, 2),
        "body": {
            "node_id": "node:alternation",
            "kind": "alternation",
            "branches": [
                {
                    "node_id": "node:alternation.left",
                    "kind": "literal",
                    "origin": origin(2, 6),
                    "text": "a"
                },
                {
                    "node_id": "node:alternation.right",
                    "kind": "literal",
                    "origin": origin(6, 8),
                    "text": "ab"
                }
            ]
        },
        "min": 0,
        "max": null,
        "mode": "greedy"
    }))
}

fn follower_program() -> SemanticProgram {
    source_program(json!({
        "node_id": "node:follower.root",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:follower.repeat",
                "kind": "repeat",
                "origin": origin(0, 2),
                "body": {
                    "node_id": "node:follower.operand",
                    "kind": "literal",
                    "origin": origin(2, 6),
                    "text": "a"
                },
                "min": 0,
                "max": null,
                "mode": "greedy"
            },
            {
                "node_id": "node:follower.following",
                "kind": "literal",
                "origin": origin(6, 7),
                "text": "a"
            }
        ]
    }))
}

#[test]
fn every_certified_finding_has_one_stable_mapping() {
    let cases = [
        (
            nullable_program(),
            SAFETY_UNBOUNDED_NULLABLE_REPETITION,
            Severity::Warning,
            "Unbounded repetition has an operand that can match without consuming input.",
        ),
        (
            indeterminate_program(),
            SAFETY_UNBOUNDED_INDETERMINATE_PROGRESS,
            Severity::Info,
            "Unbounded repetition has an operand whose progress could not be determined.",
        ),
        (
            nested_program(),
            SAFETY_NESTED_REPETITION_OVERLAP,
            Severity::Warning,
            "An outer repetition can repartition input with an overlapping inner repetition.",
        ),
        (
            alternation_program(),
            SAFETY_REPEATED_ALTERNATION_OVERLAP,
            Severity::Warning,
            "A repeated alternation has branches with overlapping leading consumption.",
        ),
        (
            follower_program(),
            SAFETY_REPETITION_FOLLOWER_OVERLAP,
            Severity::Warning,
            "A repetition and its immediate follower can consume overlapping leading input.",
        ),
    ];

    for (semantic, code, severity, message) in cases {
        let generated = generate(&semantic);
        assert_eq!(generated.len(), 1, "expected one diagnostic for {code}");
        let diagnostic = generated.diagnostics().next().expect("one diagnostic");
        assert_eq!(diagnostic.code.as_str(), code);
        assert_eq!(diagnostic.severity, severity);
        assert_eq!(diagnostic.severity_basis, SeverityBasis::CompilerPolicy);
        assert_eq!(diagnostic.phase, CompilerPhase::SemanticAnalysis);
        assert_eq!(diagnostic.category, DiagnosticCategory::Safety);
        assert_eq!(diagnostic.message, message);
        assert_eq!(diagnostic.advice.as_ref().expect("advice").len(), 2);
        assert_eq!(
            diagnostic.advice.as_ref().expect("advice")[0].kind,
            AdviceKind::Note
        );
        assert_eq!(
            diagnostic.advice.as_ref().expect("advice")[1].kind,
            AdviceKind::Help
        );
        assert!(diagnostic.fixes.is_none());
        assert!(diagnostic.primary_location.is_some());
    }
}

#[test]
fn multibyte_and_discontiguous_origins_are_projected_without_merging() {
    let generated = generate(&nullable_program());
    let diagnostic = generated.diagnostics().next().expect("one diagnostic");

    assert_eq!(
        serde_json::to_value(diagnostic).expect("diagnostic must serialize"),
        json!({
            "contract_version": "1.0.0",
            "occurrence": 0,
            "code": "STRL-SAFETY-0001",
            "severity": "warning",
            "severity_basis": "compiler_policy",
            "phase": "semantic_analysis",
            "category": "safety",
            "message": "Unbounded repetition has an operand that can match without consuming input.",
            "primary_location": {
                "source_id": "src:diagnostic",
                "coordinate_system": "utf8-bytes",
                "start": 0,
                "end": 2
            },
            "related_locations": [
                {
                    "role": "context",
                    "message": "Additional source region for the primary safety finding.",
                    "location": {
                        "source_id": "src:diagnostic",
                        "coordinate_system": "utf8-bytes",
                        "start": 2,
                        "end": 6
                    }
                },
                {
                    "role": "cause",
                    "message": "This operand does not have guaranteed consuming progress.",
                    "location": {
                        "source_id": "src:diagnostic",
                        "coordinate_system": "utf8-bytes",
                        "start": 2,
                        "end": 6
                    }
                }
            ],
            "advice": [
                {
                    "kind": "note",
                    "message": "This proves a target-neutral non-progress structure, not universal runtime vulnerability."
                },
                {
                    "kind": "help",
                    "message": "Require the repeated operand to consume input before another unbounded iteration."
                }
            ]
        })
    );
}

#[test]
fn relationship_findings_project_related_nodes_in_explanatory_order() {
    let nested = generate(&nested_program());
    let nested_related = nested
        .diagnostics()
        .next()
        .expect("nested diagnostic")
        .related_locations
        .as_ref()
        .expect("nested related locations");
    assert_eq!(nested_related.len(), 2);
    assert_eq!(nested_related[0].location.start, 2);
    assert_eq!(nested_related[1].location.start, 6);

    let alternation = generate(&alternation_program());
    let branch_related = alternation
        .diagnostics()
        .next()
        .expect("alternation diagnostic")
        .related_locations
        .as_ref()
        .expect("branch locations");
    assert_eq!(branch_related.len(), 2);
    assert_eq!(branch_related[0].location.start, 2);
    assert_eq!(branch_related[1].location.start, 6);

    let follower = generate(&follower_program());
    let follower_related = follower
        .diagnostics()
        .next()
        .expect("follower diagnostic")
        .related_locations
        .as_ref()
        .expect("follower locations");
    assert_eq!(follower_related.len(), 2);
    assert_eq!(follower_related[0].location.start, 6);
    assert_eq!(follower_related[1].location.start, 2);
}
