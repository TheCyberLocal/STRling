use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

use serde_json::Value;
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{PortabilityStatus, TargetProfile};
use strling_kernel::target_lowering::lower_pcre2;
use strling_kernel::target_serialization::serialize_pcre2;
use strling_kernel::validation::{canonical_sha256, Validate};

const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");
const OPTION_IDS: [&str; 6] = [
    "pcre2.matcher_api",
    "pcre2.max_variable_lookbehind",
    "pcre2.multiline",
    "pcre2.newline",
    "pcre2.ucp",
    "pcre2.utf",
];

fn profile(version: &str) -> TargetProfile {
    serde_json::from_str(match version {
        "10.42" => PCRE2_1042,
        "10.43" => PCRE2_1043,
        other => panic!("unrecognized fixture profile {other}"),
    })
    .expect("authored profile must deserialize")
}

#[test]
fn shared_versioned_feature_matrix_is_complete_and_deterministic() {
    let corpus_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../tests/conformance/pcre2-versioned-features.json");
    let corpus_bytes = fs::read_to_string(&corpus_path).unwrap_or_else(|error| {
        panic!(
            "test-owned feature corpus {} must be readable: {error}",
            corpus_path.display()
        )
    });
    let corpus: Value = serde_json::from_str(&corpus_bytes).expect("feature corpus must be JSON");
    let cases = corpus["cases"]
        .as_array()
        .expect("feature corpus must contain cases");
    assert_eq!(cases.len(), 16);
    assert_eq!(corpus["profiles"], serde_json::json!(["10.42", "10.43"]));
    assert_eq!(
        canonical_sha256(&corpus).expect("corpus fingerprint"),
        canonical_sha256(&corpus).expect("repeated corpus fingerprint")
    );

    let mut ids = BTreeSet::new();
    let mut native_counts = [0_usize; 2];
    let mut unsupported_counts = [0_usize; 2];

    for case in cases {
        let case_id = case["id"].as_str().expect("case ID");
        assert!(ids.insert(case_id), "duplicate feature case {case_id}");
        let program: SemanticProgram =
            serde_json::from_value(case["program"].clone()).expect("semantic program");
        program.validate().expect("semantic program must validate");
        let pattern = case["pattern"].as_str().expect("direct artifact pattern");

        for (profile_index, version) in ["10.42", "10.43"].into_iter().enumerate() {
            let target = profile(version);
            let foundational = analyze(&program).expect("foundational analysis");
            let structural =
                analyze_structure(&program, &foundational).expect("structural analysis");
            let evaluation = evaluate_capabilities(&program, &foundational, &structural, &target)
                .expect("capability evaluation");
            let plan = plan_portability(&program, &foundational, &structural, &target, &evaluation)
                .expect("portability plan");
            let expectation = &case["profiles"][version];
            let status = expectation["status"].as_str().expect("expected status");

            match status {
                "native" => {
                    native_counts[profile_index] += 1;
                    assert_eq!(
                        plan.status,
                        Some(PortabilityStatus::Native),
                        "{case_id} on {version}"
                    );
                    assert!(
                        plan.unresolved_requirements.is_empty(),
                        "{case_id} on {version}"
                    );
                    let lowered =
                        lower_pcre2(&program, &target, &plan).expect("native lowering must work");
                    let first = serialize_pcre2(&lowered).expect("native serialization must work");
                    let second =
                        serialize_pcre2(&lowered).expect("repeated serialization must work");
                    assert_eq!(first, second, "{case_id} on {version}");
                    assert_eq!(first.pattern.text, pattern, "{case_id} on {version}");
                    first.validate().expect("artifact must validate");
                    first
                        .validate_against_profile(&target)
                        .expect("artifact must resolve against exact profile");
                    let expected_options: &[&str] = if version == "10.43" {
                        &OPTION_IDS
                    } else {
                        &[
                            "pcre2.matcher_api",
                            "pcre2.multiline",
                            "pcre2.newline",
                            "pcre2.ucp",
                            "pcre2.utf",
                        ]
                    };
                    assert_eq!(
                        first
                            .engine_options
                            .iter()
                            .map(|option| option.option_id.as_str())
                            .collect::<Vec<_>>(),
                        expected_options,
                        "{case_id} on {version}"
                    );
                }
                "unsupported" => {
                    unsupported_counts[profile_index] += 1;
                    assert_eq!(
                        plan.status,
                        Some(PortabilityStatus::Unsupported),
                        "{case_id} on {version}"
                    );
                    assert!(
                        lower_pcre2(&program, &target, &plan).is_err(),
                        "{case_id} on {version} must fail before artifact emission"
                    );
                }
                other => panic!("unrecognized status {other} for {case_id} on {version}"),
            }
        }
    }

    assert_eq!(native_counts, [11, 14]);
    assert_eq!(unsupported_counts, [5, 2]);
}
