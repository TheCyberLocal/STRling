use std::collections::BTreeSet;
use std::fs;
use std::hint::black_box;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::path::Path;
use std::time::{Duration, Instant};

use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::{plan_portability, PortabilityPlan};
use strling_kernel::semantic::{Node, SemanticProgram};
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::NodeId;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{TargetArtifact, TargetProfile};
use strling_kernel::target_lowering::{
    lower_pcre2, Pcre2LoweringErrorCode, MAX_PCRE2_LOWERING_DEPTH,
};
use strling_kernel::target_serialization::{
    serialize_pcre2, Pcre2SerializationErrorCode, MAX_PCRE2_PATTERN_COUNT,
};
use strling_kernel::validation::canonical_sha256;

const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");

fn target() -> TargetProfile {
    serde_json::from_str(PCRE2_1043).expect("governed PCRE2 10.43 profile")
}

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

fn literal(node_id: impl Into<String>, text: impl Into<String>) -> Value {
    json!({"node_id": node_id.into(), "kind": "literal", "text": text.into()})
}

fn plan_for(
    semantic: &SemanticProgram,
    profile: &TargetProfile,
) -> Result<PortabilityPlan, String> {
    let foundational = analyze(semantic).map_err(|error| error.to_string())?;
    let structural =
        analyze_structure(semantic, &foundational).map_err(|error| error.to_string())?;
    let evaluation = evaluate_capabilities(semantic, &foundational, &structural, profile)
        .map_err(|error| error.to_string())?;
    plan_portability(semantic, &foundational, &structural, profile, &evaluation)
        .map_err(|error| error.to_string())
}

fn artifact(semantic: &SemanticProgram, profile: &TargetProfile) -> Result<TargetArtifact, String> {
    let plan = plan_for(semantic, profile)?;
    let lowered = lower_pcre2(semantic, profile, &plan).map_err(|error| error.to_string())?;
    serialize_pcre2(&lowered).map_err(|error| error.to_string())
}

fn runtime_corpus() -> Value {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../tests/conformance/pcre2-runtime-certification.json");
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("runtime corpus {}: {error}", path.display()));
    serde_json::from_str(&text).expect("runtime corpus JSON")
}

#[test]
fn pathological_serializer_inputs_are_bounded_deterministic_and_panic_free() {
    let corpus = runtime_corpus();
    let expected_pathologies = BTreeSet::from([
        "conflicting_options",
        "deeply_nested_groups",
        "dense_character_class",
        "empty_construct",
        "escape_palette",
        "legal_and_illegal_capture_names",
        "malformed_lowered_artifact",
        "maximum_bounded_quantifier",
    ]);
    let declared_pathologies = corpus["serializer_pathologies"]
        .as_array()
        .expect("pathology manifest")
        .iter()
        .map(|item| item.as_str().expect("pathology ID"))
        .collect::<BTreeSet<_>>();
    assert_eq!(expected_pathologies, declared_pathologies);
    assert_eq!(
        canonical_sha256(&corpus).expect("runtime corpus fingerprint"),
        canonical_sha256(&corpus).expect("repeated runtime corpus fingerprint")
    );

    let profile = target();
    let empty = artifact(
        &program(json!({"node_id": "node:pathology.empty", "kind": "empty"})),
        &profile,
    )
    .expect("empty artifact");
    assert_eq!("", empty.pattern.text);

    let escaped_text = ".^$|?*+()[]{}\\ #\t\n\r\u{000b}\u{000c}\0éλ界";
    let escaped = artifact(
        &program(literal("node:pathology.escapes", escaped_text)),
        &profile,
    )
    .expect("escape-heavy artifact");
    let escaped_again = artifact(
        &program(literal("node:pathology.escapes", escaped_text)),
        &profile,
    )
    .expect("repeated escape-heavy artifact");
    assert_eq!(escaped, escaped_again);
    assert!(escaped
        .pattern
        .text
        .is_char_boundary(escaped.pattern.text.len()));

    let members = (0..64_u32)
        .map(|offset| {
            let value = char::from_u32(0x100 + offset).expect("bounded Unicode scalar");
            json!({"kind": "literal", "value": value.to_string()})
        })
        .collect::<Vec<_>>();
    let dense_class = artifact(
        &program(json!({
            "node_id": "node:pathology.class",
            "kind": "character_set",
            "negated": false,
            "members": members
        })),
        &profile,
    )
    .expect("dense class artifact");
    assert!(dense_class.pattern.text.starts_with('['));
    assert!(dense_class.pattern.text.ends_with(']'));

    let maximum_quantifier = artifact(
        &program(json!({
            "node_id": "node:pathology.quantifier",
            "kind": "repeat",
            "body": literal("node:pathology.quantifier.body", "q"),
            "min": 0,
            "max": MAX_PCRE2_PATTERN_COUNT,
            "mode": "greedy"
        })),
        &profile,
    )
    .expect("maximum bounded quantifier artifact");
    assert!(maximum_quantifier.pattern.text.contains("{0,65535}"));

    let legal_name = "a".repeat(32);
    let legal_capture = artifact(
        &program(json!({
            "node_id": "node:pathology.capture.legal",
            "kind": "capture",
            "capture_id": "capture:pathology.legal",
            "name": legal_name,
            "body": literal("node:pathology.capture.legal.body", "a")
        })),
        &profile,
    )
    .expect("32-code-unit capture name");
    assert!(legal_capture.pattern.text.contains(&"a".repeat(32)));

    for invalid_name in ["bad-name".to_owned(), "a".repeat(33)] {
        let invalid = program(json!({
            "node_id": format!("node:pathology.capture.invalid.{}", invalid_name.len()),
            "kind": "capture",
            "capture_id": format!("capture:pathology.invalid.{}", invalid_name.len()),
            "name": invalid_name,
            "body": literal("node:pathology.capture.invalid.body", "a")
        }));
        let result = catch_unwind(AssertUnwindSafe(|| artifact(&invalid, &profile)));
        assert!(result.is_ok(), "invalid capture input must not panic");
        assert!(result.expect("panic-free invalid capture").is_err());
    }

    let shallow = program(literal("node:pathology.depth.base", "a"));
    let shallow_plan = plan_for(&shallow, &profile).expect("shallow plan");
    let mut deep = shallow.clone();
    let mut root = deep.root;
    for depth in 0..MAX_PCRE2_LOWERING_DEPTH {
        root = Node::Atomic {
            node_id: NodeId::try_from(format!("node:pathology.depth.wrapper-{depth}"))
                .expect("node ID"),
            origin: None,
            body: Box::new(root),
        };
    }
    deep.root = root;
    assert_eq!(
        lower_pcre2(&deep, &profile, &shallow_plan)
            .expect_err("over-depth input")
            .code,
        Pcre2LoweringErrorCode::ResourceLimitExceeded
    );

    let capture_program = program(json!({
        "node_id": "node:pathology.capture.valid",
        "kind": "capture",
        "capture_id": "capture:pathology.valid",
        "name": "valid",
        "body": literal("node:pathology.capture.valid.body", "a")
    }));
    let capture_plan = plan_for(&capture_program, &profile).expect("capture plan");
    let mut malformed =
        lower_pcre2(&capture_program, &profile, &capture_plan).expect("capture lowering");
    malformed.captures[0].slot = 2;
    assert_eq!(
        serialize_pcre2(&malformed)
            .expect_err("malformed capture slot")
            .code,
        Pcre2SerializationErrorCode::InvalidLoweringPlan
    );

    let plain = program(literal("node:pathology.options", "a"));
    let plain_plan = plan_for(&plain, &profile).expect("plain plan");
    let mut conflicting = lower_pcre2(&plain, &profile, &plain_plan).expect("plain lowering");
    conflicting.options[1].option_id = conflicting.options[0].option_id.clone();
    assert_eq!(
        serialize_pcre2(&conflicting)
            .expect_err("conflicting options")
            .code,
        Pcre2SerializationErrorCode::InvalidLoweringPlan
    );
}

fn performance_program() -> SemanticProgram {
    program(json!({
        "node_id": "node:performance.root",
        "kind": "sequence",
        "items": [
            {"node_id": "node:performance.start", "kind": "position", "position": "input_start"},
            {
                "node_id": "node:performance.capture",
                "kind": "capture",
                "capture_id": "capture:performance.word",
                "name": "word",
                "body": {
                    "node_id": "node:performance.repeat",
                    "kind": "repeat",
                    "body": literal("node:performance.letter", "λ"),
                    "min": 1,
                    "max": 32,
                    "mode": "greedy"
                }
            },
            {
                "node_id": "node:performance.atomic",
                "kind": "atomic",
                "body": {
                    "node_id": "node:performance.alternation",
                    "kind": "alternation",
                    "branches": [
                        literal("node:performance.left", "a"),
                        literal("node:performance.right", "bc")
                    ]
                }
            },
            {"node_id": "node:performance.end", "kind": "position", "position": "input_end"}
        ]
    }))
}

fn median_microseconds(samples: &mut [Duration]) -> u128 {
    samples.sort_unstable();
    samples[samples.len() / 2].as_micros()
}

#[test]
fn compiler_stage_medians_remain_within_governed_baseline_budgets() {
    let corpus = runtime_corpus();
    let budget = &corpus["performance_budget"];
    let warmups = budget["warmup_iterations"].as_u64().expect("warmups");
    let sample_count = budget["sample_iterations"]
        .as_u64()
        .expect("sample iterations");
    let thresholds = &budget["median_microseconds"];
    let analysis_budget = thresholds["analysis_and_planning"]
        .as_u64()
        .expect("analysis budget") as u128;
    let lowering_budget = thresholds["lowering"].as_u64().expect("lowering budget") as u128;
    let serialization_budget = thresholds["serialization"]
        .as_u64()
        .expect("serialization budget") as u128;

    let semantic = performance_program();
    let profile = target();
    for _ in 0..warmups {
        black_box(artifact(&semantic, &profile).expect("warm-up artifact"));
    }

    let mut analysis_samples = Vec::with_capacity(sample_count as usize);
    let mut lowering_samples = Vec::with_capacity(sample_count as usize);
    let mut serialization_samples = Vec::with_capacity(sample_count as usize);
    for _ in 0..sample_count {
        let started = Instant::now();
        let foundational = analyze(&semantic).expect("foundational analysis");
        let structural = analyze_structure(&semantic, &foundational).expect("structural analysis");
        let evaluation = evaluate_capabilities(&semantic, &foundational, &structural, &profile)
            .expect("capability evaluation");
        let plan = plan_portability(&semantic, &foundational, &structural, &profile, &evaluation)
            .expect("portability planning");
        analysis_samples.push(started.elapsed());

        let started = Instant::now();
        let lowered = lower_pcre2(&semantic, &profile, &plan).expect("lowering");
        lowering_samples.push(started.elapsed());

        let started = Instant::now();
        let emitted = serialize_pcre2(&lowered).expect("serialization");
        serialization_samples.push(started.elapsed());
        black_box(emitted);
    }

    let analysis_median = median_microseconds(&mut analysis_samples);
    let lowering_median = median_microseconds(&mut lowering_samples);
    let serialization_median = median_microseconds(&mut serialization_samples);
    println!(
        "{}",
        serde_json::to_string(&json!({
            "measurement_version": "1.0.0",
            "warmup_iterations": warmups,
            "sample_iterations": sample_count,
            "median_microseconds": {
                "analysis_and_planning": analysis_median,
                "lowering": lowering_median,
                "serialization": serialization_median
            },
            "budgets_microseconds": {
                "analysis_and_planning": analysis_budget,
                "lowering": lowering_budget,
                "serialization": serialization_budget
            }
        }))
        .expect("performance evidence JSON")
    );
    assert!(
        analysis_median <= analysis_budget,
        "analysis/planning median {analysis_median}us exceeds {analysis_budget}us"
    );
    assert!(
        lowering_median <= lowering_budget,
        "lowering median {lowering_median}us exceeds {lowering_budget}us"
    );
    assert!(
        serialization_median <= serialization_budget,
        "serialization median {serialization_median}us exceeds {serialization_budget}us"
    );
}
