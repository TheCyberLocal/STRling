use std::collections::{BTreeMap, BTreeSet};

use serde_json::{json, Value};
use strling_kernel::diagnostic::Diagnostic;
use strling_kernel::diagnostic_generation::{
    generate_diagnostics, DiagnosticGenerationErrorCode, SAFETY_NESTED_REPETITION_OVERLAP,
    SAFETY_REPEATED_ALTERNATION_OVERLAP, SAFETY_REPETITION_FOLLOWER_OVERLAP,
    SAFETY_UNBOUNDED_INDETERMINATE_PROGRESS, SAFETY_UNBOUNDED_NULLABLE_REPETITION,
};
use strling_kernel::safety_analysis::{analyze_safety, SafetyAnalysis, SafetyFindingCode};
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::SourceSpan;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::validation::Validate;

const SEEDS: [u64; 4] = [
    0x4449_4147_5f50_5231,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const PROGRAMS_PER_SEED: usize = 64;

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("generated program must deserialize")
}

fn node(prefix: &str, suffix: &str) -> String {
    format!("node:{prefix}.{suffix}")
}

fn next(state: &mut u64) -> u64 {
    *state ^= state.wrapping_shl(13);
    *state ^= state.wrapping_shr(7);
    *state ^= state.wrapping_shl(17);
    *state
}

fn generated_program(prefix: &str, kind: u64) -> SemanticProgram {
    match kind {
        0 => program(json!({
            "node_id": node(prefix, "literal"),
            "kind": "literal",
            "text": "safe"
        })),
        1 => program(json!({
            "node_id": node(prefix, "nullable"),
            "kind": "repeat",
            "body": {"node_id": node(prefix, "nullable.body"), "kind": "empty"},
            "min": 0,
            "max": null,
            "mode": "greedy"
        })),
        2 => program(json!({
            "node_id": node(prefix, "nested.outer"),
            "kind": "repeat",
            "body": {
                "node_id": node(prefix, "nested.inner"),
                "kind": "repeat",
                "body": {
                    "node_id": node(prefix, "nested.atom"),
                    "kind": "literal",
                    "text": "a"
                },
                "min": 1,
                "max": null,
                "mode": "greedy"
            },
            "min": 0,
            "max": null,
            "mode": "greedy"
        })),
        3 => program(json!({
            "node_id": node(prefix, "alternation.repeat"),
            "kind": "repeat",
            "body": {
                "node_id": node(prefix, "alternation"),
                "kind": "alternation",
                "branches": [
                    {
                        "node_id": node(prefix, "alternation.left"),
                        "kind": "literal",
                        "text": "a"
                    },
                    {
                        "node_id": node(prefix, "alternation.right"),
                        "kind": "literal",
                        "text": "ab"
                    }
                ]
            },
            "min": 0,
            "max": null,
            "mode": "greedy"
        })),
        4 => program(json!({
            "node_id": node(prefix, "follower.root"),
            "kind": "sequence",
            "items": [
                {
                    "node_id": node(prefix, "follower.repeat"),
                    "kind": "repeat",
                    "body": {
                        "node_id": node(prefix, "follower.operand"),
                        "kind": "literal",
                        "text": "a"
                    },
                    "min": 0,
                    "max": null,
                    "mode": "greedy"
                },
                {
                    "node_id": node(prefix, "follower.following"),
                    "kind": "literal",
                    "text": "a"
                }
            ]
        })),
        5 => program(json!({
            "node_id": node(prefix, "indeterminate.root"),
            "kind": "sequence",
            "items": [
                {
                    "node_id": node(prefix, "indeterminate.capture"),
                    "kind": "capture",
                    "capture_id": format!("capture:{prefix}"),
                    "body": {
                        "node_id": node(prefix, "indeterminate.optional"),
                        "kind": "repeat",
                        "body": {
                            "node_id": node(prefix, "indeterminate.literal"),
                            "kind": "literal",
                            "text": "a"
                        },
                        "min": 0,
                        "max": 1,
                        "mode": "greedy"
                    }
                },
                {
                    "node_id": node(prefix, "indeterminate.repeat"),
                    "kind": "repeat",
                    "body": {
                        "node_id": node(prefix, "indeterminate.reference"),
                        "kind": "backreference",
                        "capture_id": format!("capture:{prefix}")
                    },
                    "min": 1,
                    "max": null,
                    "mode": "greedy"
                }
            ]
        })),
        6 => program(json!({
            "node_id": node(prefix, "unknown.repeat"),
            "kind": "repeat",
            "body": {
                "node_id": node(prefix, "unknown.alternation"),
                "kind": "alternation",
                "branches": [
                    {
                        "node_id": node(prefix, "unknown.left"),
                        "kind": "character_set",
                        "negated": false,
                        "members": [{
                            "kind": "unicode_property",
                            "property": "General_Category",
                            "value": "Letter",
                            "negated": false
                        }]
                    },
                    {
                        "node_id": node(prefix, "unknown.right"),
                        "kind": "character_set",
                        "negated": false,
                        "members": [{
                            "kind": "unicode_property",
                            "property": "General_Category",
                            "value": "Number",
                            "negated": false
                        }]
                    }
                ]
            },
            "min": 0,
            "max": null,
            "mode": "greedy"
        })),
        _ => unreachable!("generator selects seven templates"),
    }
}

fn diagnostic_code(code: SafetyFindingCode) -> &'static str {
    match code {
        SafetyFindingCode::UnboundedNullableRepetition => SAFETY_UNBOUNDED_NULLABLE_REPETITION,
        SafetyFindingCode::UnboundedIndeterminateProgress => {
            SAFETY_UNBOUNDED_INDETERMINATE_PROGRESS
        }
        SafetyFindingCode::NestedRepetitionOverlap => SAFETY_NESTED_REPETITION_OVERLAP,
        SafetyFindingCode::RepeatedAlternationOverlap => SAFETY_REPEATED_ALTERNATION_OVERLAP,
        SafetyFindingCode::RepetitionFollowerOverlap => SAFETY_REPETITION_FOLLOWER_OVERLAP,
    }
}

#[test]
fn generated_programs_certify_diagnostic_properties() {
    let mut program_count = 0_usize;
    let mut diagnostic_count = 0_usize;
    let mut uncertainty_count = 0_usize;
    let mut uncertainty_only_count = 0_usize;
    let mut covered_findings = BTreeSet::new();

    for seed in SEEDS {
        let mut state = seed;
        for index in 0..PROGRAMS_PER_SEED {
            let kind = next(&mut state) % 7;
            let prefix = format!("p{seed:016x}.{index:03}");
            let semantic = generated_program(&prefix, kind);
            let foundational = analyze(&semantic).expect("foundational analysis");
            let structural = analyze_structure(&semantic, &foundational).expect("structure");
            let safety =
                analyze_safety(&semantic, &foundational, &structural).expect("safety analysis");
            let semantic_before = semantic.clone();
            let foundational_before = foundational.clone();
            let structural_before = structural.clone();
            let safety_before = safety.clone();

            let first = generate_diagnostics(&semantic, &foundational, &structural, &safety)
                .expect("first generation");
            let second = generate_diagnostics(&semantic, &foundational, &structural, &safety)
                .expect("second generation");
            assert_eq!(first, second);
            assert_eq!(semantic, semantic_before);
            assert_eq!(foundational, foundational_before);
            assert_eq!(structural, structural_before);
            assert_eq!(safety, safety_before);

            let node_ids = semantic.node_ids();
            let mut expected_codes = BTreeMap::new();
            for finding in safety.findings() {
                covered_findings.insert(finding.code);
                *expected_codes
                    .entry(diagnostic_code(finding.code))
                    .or_insert(0_usize) += 1;
            }
            let mut actual_codes = BTreeMap::new();
            let mut occurrences = BTreeSet::new();
            for record in first.records() {
                assert!(node_ids.contains(&record.provenance.primary_node_id));
                assert!(record
                    .provenance
                    .contributing_node_ids
                    .iter()
                    .all(|node_id| node_ids.contains(node_id)));
                assert!(occurrences.insert(record.diagnostic.occurrence));
                assert!(record.diagnostic.primary_location.is_none());
                assert!(record.diagnostic.related_locations.is_none());
                record.diagnostic.validate().expect("diagnostic contract");
                let round_trip: Diagnostic = serde_json::from_value(
                    serde_json::to_value(&record.diagnostic).expect("serialize diagnostic"),
                )
                .expect("deserialize diagnostic");
                assert_eq!(round_trip, record.diagnostic);
                *actual_codes
                    .entry(record.diagnostic.code.as_str())
                    .or_insert(0_usize) += 1;
            }
            assert_eq!(actual_codes, expected_codes);
            assert_eq!(first.len(), safety.findings().count());

            let uncertainties = safety.uncertainties().count();
            uncertainty_count += uncertainties;
            if uncertainties > 0 && safety.findings().count() == 0 {
                uncertainty_only_count += 1;
                assert!(first.is_empty());
            }
            program_count += 1;
            diagnostic_count += first.len();
        }
    }

    assert_eq!(program_count, SEEDS.len() * PROGRAMS_PER_SEED);
    assert_eq!(covered_findings.len(), 5);
    assert_eq!(diagnostic_count, 189);
    assert_eq!(uncertainty_count, 34);
    assert_eq!(uncertainty_only_count, 34);
}

#[test]
fn emitted_locations_are_exact_canonical_origins() {
    let semantic: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "sources": [{
            "contract_version": "1.0.0",
            "source_id": "src:property",
            "specification_version": "1.0-draft.1",
            "frontend": {"id": "semantic_strling", "dialect_version": "1.0-draft.1"},
            "content": {"kind": "inline", "encoding": "utf-8", "text": "α😀x"},
            "provenance": {"kind": "authored"}
        }],
        "root": {
            "node_id": "node:property.repeat",
            "kind": "repeat",
            "origin": {"source_spans": [
                {"source_id": "src:property", "coordinate_system": "utf8-bytes", "start": 0, "end": 2},
                {"source_id": "src:property", "coordinate_system": "utf8-bytes", "start": 2, "end": 6}
            ]},
            "body": {
                "node_id": "node:property.body",
                "kind": "empty",
                "origin": {"source_spans": [
                    {"source_id": "src:property", "coordinate_system": "utf8-bytes", "start": 6, "end": 7}
                ]}
            },
            "min": 0,
            "max": null,
            "mode": "greedy"
        }
    }))
    .expect("source property program");
    let foundational = analyze(&semantic).expect("foundational analysis");
    let structural = analyze_structure(&semantic, &foundational).expect("structure");
    let safety = analyze_safety(&semantic, &foundational, &structural).expect("safety");
    let generated =
        generate_diagnostics(&semantic, &foundational, &structural, &safety).expect("diagnostics");
    let origins = semantic_origins(&semantic.root);

    for diagnostic in generated.diagnostics() {
        assert!(diagnostic
            .primary_location
            .as_ref()
            .map_or(true, |span| origins.contains(span)));
        assert!(diagnostic
            .related_locations
            .as_ref()
            .into_iter()
            .flatten()
            .all(|related| origins.contains(&related.location)));
    }
}

fn semantic_origins(root: &Node) -> BTreeSet<SourceSpan> {
    let mut origins = BTreeSet::new();
    let mut pending = vec![root];
    while let Some(node) = pending.pop() {
        if let Some(spans) = node
            .origin()
            .and_then(|origin| origin.source_spans.as_ref())
        {
            origins.extend(spans.iter().cloned());
        }
        match node {
            Node::Sequence { items, .. } => pending.extend(items),
            Node::Alternation { branches, .. } => pending.extend(branches),
            Node::Repeat { body, .. }
            | Node::Capture { body, .. }
            | Node::Lookaround { body, .. }
            | Node::Atomic { body, .. } => pending.push(body),
            Node::Empty { .. }
            | Node::Literal { .. }
            | Node::Wildcard { .. }
            | Node::CharacterSet { .. }
            | Node::Position { .. }
            | Node::Backreference { .. } => {}
        }
    }
    origins
}

#[test]
fn controlled_malformed_evidence_cases_fail_without_partial_output() {
    let semantic = generated_program("malformed", 3);
    let foundational = analyze(&semantic).expect("foundational analysis");
    let structural = analyze_structure(&semantic, &foundational).expect("structure");
    let safety = analyze_safety(&semantic, &foundational, &structural).expect("safety");

    for mutation in 0..2 {
        let mut value = serde_json::to_value(&safety).expect("serialize safety");
        if mutation == 0 {
            value["findings"][0]["primary_node_id"] = json!("node:missing");
        } else {
            value["findings"][0]["evidence"]["relationship"]["right_node_id"] =
                json!("node:alternation.left");
        }
        let malformed: SafetyAnalysis =
            serde_json::from_value(value).expect("malformed shape deserializes");
        let errors = generate_diagnostics(&semantic, &foundational, &structural, &malformed)
            .expect_err("malformed evidence must fail");
        assert_eq!(
            errors.errors[0].code,
            DiagnosticGenerationErrorCode::MalformedEvidenceReference
        );
    }
}
