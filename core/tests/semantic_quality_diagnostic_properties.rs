use std::collections::BTreeSet;

use serde_json::{json, Value};
use strling_kernel::diagnostic_generation::{
    generate_diagnostics, DiagnosticEvidence, QUALITY_CONTRADICTORY_BOUNDARY_ASSERTIONS,
    QUALITY_CONTRADICTORY_LOOKAROUND_ASSERTIONS, QUALITY_DUPLICATE_ALTERNATION_BRANCH,
    QUALITY_OVERLAPPING_CHARACTER_SET_MEMBERS, QUALITY_REDUNDANT_SINGLE_REPETITION,
    QUALITY_ZERO_MAXIMUM_REPETITION, QUALITY_ZERO_WIDTH_BACKREFERENCE,
};
use strling_kernel::normalization::normalize;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::validation::Validate;

const SEEDS: [u64; 4] = [
    0x5155_414c_4954_5931,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const PROGRAMS_PER_SEED: usize = 32;

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("generated quality candidate must deserialize")
}

fn node(prefix: &str, suffix: &str) -> String {
    format!("node:{prefix}.{suffix}")
}

fn candidate(prefix: &str, kind: usize) -> SemanticProgram {
    match kind {
        0 => program(json!({
            "node_id": node(prefix, "literal"),
            "kind": "literal",
            "text": "safe"
        })),
        1 => program(json!({
            "node_id": node(prefix, "outer.sequence"),
            "kind": "sequence",
            "items": [{
                "node_id": node(prefix, "inner.sequence"),
                "kind": "sequence",
                "items": [
                    {"node_id": node(prefix, "empty"), "kind": "empty"},
                    {
                        "node_id": node(prefix, "zero.repeat"),
                        "kind": "repeat",
                        "body": {"node_id": node(prefix, "zero.body"), "kind": "literal", "text": "a"},
                        "min": 0,
                        "max": 0,
                        "mode": "greedy"
                    }
                ]
            }]
        })),
        2 => program(json!({
            "node_id": node(prefix, "single.repeat"),
            "kind": "repeat",
            "body": {"node_id": node(prefix, "single.body"), "kind": "literal", "text": "a"},
            "min": 1,
            "max": 1,
            "mode": "lazy"
        })),
        3 => program(json!({
            "node_id": node(prefix, "duplicate.alt"),
            "kind": "alternation",
            "branches": [
                {"node_id": node(prefix, "duplicate.left"), "kind": "literal", "text": "a"},
                {"node_id": node(prefix, "duplicate.right"), "kind": "literal", "text": "a"}
            ]
        })),
        4 => program(json!({
            "node_id": node(prefix, "boundary.sequence"),
            "kind": "sequence",
            "items": [
                {"node_id": node(prefix, "boundary.word"), "kind": "position", "position": "word_boundary"},
                {"node_id": node(prefix, "boundary.empty"), "kind": "empty"},
                {"node_id": node(prefix, "boundary.not"), "kind": "position", "position": "not_word_boundary"}
            ]
        })),
        5 => program(json!({
            "node_id": node(prefix, "look.sequence"),
            "kind": "sequence",
            "items": [
                {
                    "node_id": node(prefix, "look.positive"),
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": "positive",
                    "body": {"node_id": node(prefix, "look.positive.body"), "kind": "literal", "text": "a"}
                },
                {
                    "node_id": node(prefix, "look.negative"),
                    "kind": "lookaround",
                    "direction": "behind",
                    "polarity": "negative",
                    "body": {"node_id": node(prefix, "look.negative.body"), "kind": "literal", "text": "a"}
                }
            ]
        })),
        6 => program(json!({
            "node_id": node(prefix, "set"),
            "kind": "character_set",
            "negated": true,
            "members": [
                {"kind": "literal", "value": "h"},
                {"kind": "range", "start": "a", "end": "m"}
            ]
        })),
        7 => program(json!({
            "node_id": node(prefix, "reference.sequence"),
            "kind": "sequence",
            "items": [
                {
                    "node_id": node(prefix, "reference.capture"),
                    "kind": "capture",
                    "capture_id": format!("capture:{prefix}"),
                    "body": {"node_id": node(prefix, "reference.body"), "kind": "position", "position": "input_start"}
                },
                {
                    "node_id": node(prefix, "reference.use"),
                    "kind": "backreference",
                    "capture_id": format!("capture:{prefix}")
                }
            ]
        })),
        _ => unreachable!("quality generator selects eight templates"),
    }
}

#[test]
fn fixed_seed_source_less_candidates_are_deterministic_through_normalization() {
    let expected_codes = BTreeSet::from([
        QUALITY_ZERO_MAXIMUM_REPETITION.to_owned(),
        QUALITY_REDUNDANT_SINGLE_REPETITION.to_owned(),
        QUALITY_DUPLICATE_ALTERNATION_BRANCH.to_owned(),
        QUALITY_CONTRADICTORY_BOUNDARY_ASSERTIONS.to_owned(),
        QUALITY_CONTRADICTORY_LOOKAROUND_ASSERTIONS.to_owned(),
        QUALITY_OVERLAPPING_CHARACTER_SET_MEMBERS.to_owned(),
        QUALITY_ZERO_WIDTH_BACKREFERENCE.to_owned(),
    ]);
    let mut covered_codes = BTreeSet::new();
    let mut program_count = 0_usize;
    let mut diagnostic_count = 0_usize;

    for seed in SEEDS {
        for index in 0..PROGRAMS_PER_SEED {
            let prefix = format!("q{seed:016x}.{index:03}");
            let semantic = candidate(&prefix, index % 8);
            let semantic_before = semantic.clone();
            let first_normalized = normalize(&semantic).expect("first normalization");
            let second_normalized = normalize(&semantic).expect("second normalization");
            assert_eq!(first_normalized, second_normalized);
            assert_eq!(semantic, semantic_before);

            let foundational = analyze(&first_normalized).expect("foundational analysis");
            let structural =
                analyze_structure(&first_normalized, &foundational).expect("structural analysis");
            let safety = analyze_safety(&first_normalized, &foundational, &structural)
                .expect("safety analysis");
            let first =
                generate_diagnostics(&first_normalized, &foundational, &structural, &safety)
                    .expect("first generation");
            let second =
                generate_diagnostics(&first_normalized, &foundational, &structural, &safety)
                    .expect("second generation");
            assert_eq!(first, second);

            let node_ids = first_normalized.node_ids();
            let mut occurrences = BTreeSet::new();
            for record in first.records() {
                assert!(matches!(
                    record.provenance.evidence,
                    DiagnosticEvidence::Quality(_)
                ));
                assert!(node_ids.contains(&record.provenance.primary_node_id));
                assert!(record
                    .provenance
                    .contributing_node_ids
                    .iter()
                    .all(|node_id| node_ids.contains(node_id)));
                assert!(occurrences.insert(record.diagnostic.occurrence));
                assert!(record.diagnostic.primary_location.is_none());
                assert!(record.diagnostic.related_locations.is_none());
                assert!(record.diagnostic.fixes.is_none());
                record.diagnostic.validate().expect("diagnostic contract");
                covered_codes.insert(record.diagnostic.code.as_str().to_owned());
            }
            program_count += 1;
            diagnostic_count += first.len();
        }
    }

    assert_eq!(program_count, SEEDS.len() * PROGRAMS_PER_SEED);
    assert_eq!(diagnostic_count, 7 * 4 * (PROGRAMS_PER_SEED / 8));
    assert_eq!(covered_codes, expected_codes);
}
