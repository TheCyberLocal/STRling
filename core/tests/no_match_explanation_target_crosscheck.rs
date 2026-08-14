use std::fs;
use std::path::{Path, PathBuf};

use serde_json::Value;
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::explanation::{explain_semantics, explain_target, ExplanationDocument};
use strling_kernel::no_match_explanation::{
    explain_no_match, NoMatchExecutionMode, NoMatchExplanationDisposition, NoMatchLimits,
    NoMatchOutcome, NoMatchReasonCode, NoMatchTargetStatus,
};
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;

const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");
const PYTHON_RE: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");
const PYTHON_RE_BYTES: &str = include_str!("../../spec/targets/profiles/python-re-3.11-bytes.json");

fn repository_path(path: impl AsRef<Path>) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join(path)
}

fn repository_json(path: impl AsRef<Path>) -> Value {
    let path = repository_path(path);
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    serde_json::from_str(&text).unwrap_or_else(|error| panic!("parse {}: {error}", path.display()))
}

fn explain(input: &SemanticProgram) -> (SemanticProgram, ExplanationDocument) {
    let normalized = normalize(input).expect("normalize");
    let foundational = analyze(&normalized).expect("foundational analysis");
    let structural = analyze_structure(&normalized, &foundational).expect("structural analysis");
    let safety = analyze_safety(&normalized, &foundational, &structural).expect("safety analysis");
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .expect("diagnostic generation");
    let semantic = explain_semantics(
        &normalized,
        &foundational,
        &structural,
        &safety,
        &diagnostics,
    )
    .expect("semantic explanation");
    (normalized, semantic)
}

fn project_target(
    input: &SemanticProgram,
    semantic: &ExplanationDocument,
    profile: &TargetProfile,
) -> ExplanationDocument {
    let foundational = analyze(input).expect("foundational analysis");
    let structural = analyze_structure(input, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(input, &foundational, &structural, profile)
        .expect("capability evaluation");
    let plan = plan_portability(input, &foundational, &structural, profile, &evaluation)
        .expect("portability plan");
    explain_target(semantic, &evaluation, &plan).expect("target explanation")
}

fn profile(profile_id: &str) -> TargetProfile {
    let source = match profile_id {
        "profile:ecmascript/2024" => ECMASCRIPT,
        "profile:pcre2/10.42" => PCRE2_1042,
        "profile:pcre2/10.43" => PCRE2_1043,
        "profile:python-re/3.11" => PYTHON_RE,
        "profile:python-re/3.11-bytes" => PYTHON_RE_BYTES,
        other => panic!("unregistered target profile {other}"),
    };
    serde_json::from_str(source).expect("governed target profile")
}

fn subjects(case: &Value) -> Vec<&str> {
    ["positive", "negative"]
        .into_iter()
        .flat_map(|disposition| {
            case["expectations"]["matches"][disposition]
                .as_array()
                .expect("subject cases")
                .iter()
                .map(|entry| entry["subject"].as_str().expect("subject"))
        })
        .collect()
}

#[test]
fn representative_canonical_results_agree_with_governed_real_engine_evidence() {
    let evidence =
        repository_json("tests/conformance/evidence/shared-cross-engine-observations.json");
    assert_eq!(evidence["evidence_version"], "1.0.0");
    assert_eq!(evidence["corpus"]["case_count"], 20);
    assert_eq!(evidence["runtimes"]["node"]["node"], "v22.23.2");
    assert_eq!(evidence["runtimes"]["python"]["version"], "3.11.15");
    assert_eq!(
        evidence["runtimes"]["pcre2"]["10.43"]["engine_version"],
        "10.43 2024-02-16"
    );

    let cases = [
        (
            "case:matching/alternation",
            "spec/conformance/cases/alternation-match.json",
        ),
        (
            "case:matching/ascii-character-class",
            "spec/conformance/cases/ascii-character-class.json",
        ),
        (
            "case:matching/positive-lookahead",
            "spec/conformance/cases/positive-lookahead.json",
        ),
        (
            "case:matching/backreference",
            "spec/conformance/cases/backreference-match.json",
        ),
        (
            "case:matching/input-anchors-word-boundaries",
            "spec/conformance/cases/input-anchors-word-boundaries.json",
        ),
    ];
    let observations = evidence["observations"].as_array().expect("observations");
    let mut executed_subjects = 0_usize;
    let mut unsupported_plans = 0_usize;

    for (case_id, case_path) in cases {
        let case = repository_json(case_path);
        assert_eq!(case["case_id"], case_id);
        assert_eq!(case["expectations"]["matches"]["operation"], "full_match");
        let input: SemanticProgram =
            serde_json::from_value(case["input"]["program"].clone()).expect("semantic program");
        let (input, neutral) = explain(&input);
        let subjects = subjects(&case);

        for observation in observations
            .iter()
            .filter(|observation| observation["case_id"] == case_id)
        {
            let profile_id = observation["profile_id"].as_str().expect("profile ID");
            let profile = profile(profile_id);
            let targeted = project_target(&input, &neutral, &profile);
            let target_status = targeted.target.as_ref().expect("target details").status;
            let state = observation["state"].as_str().expect("application state");

            if state == "unsupported" {
                let actual = explain_no_match(
                    &input,
                    &targeted,
                    subjects[0],
                    NoMatchExecutionMode::Search,
                    NoMatchLimits::default(),
                )
                .expect("unsupported target result");
                assert_eq!(actual.outcome, NoMatchOutcome::Unavailable);
                assert_eq!(
                    actual.explanation_disposition,
                    NoMatchExplanationDisposition::Unavailable
                );
                assert_eq!(
                    actual.target.expect("target").status,
                    NoMatchTargetStatus::Unsupported
                );
                assert_eq!(
                    actual.findings[0].reason_code,
                    NoMatchReasonCode::TargetUnsupported
                );
                unsupported_plans += 1;
                continue;
            }

            assert_eq!(state, "execute", "{case_id}/{profile_id}: state");
            let normalized = observation["normalized"]
                .as_array()
                .expect("normalized runtime observations");
            assert_eq!(normalized.len(), subjects.len());
            assert_eq!(
                serde_json::to_value(target_status).expect("target status"),
                observation["portability_status"]
            );
            for (subject, engine) in subjects.iter().zip(normalized) {
                let actual = explain_no_match(
                    &input,
                    &targeted,
                    subject,
                    NoMatchExecutionMode::Search,
                    NoMatchLimits::default(),
                )
                .unwrap_or_else(|errors| panic!("{case_id}/{profile_id}/{subject:?}: {errors:?}"));
                let expected = if engine["span"].is_null() {
                    NoMatchOutcome::NoMatch
                } else {
                    NoMatchOutcome::Matched
                };
                assert_eq!(
                    actual.outcome, expected,
                    "{case_id}/{profile_id}/{subject:?}"
                );
                executed_subjects += 1;
            }
        }
    }

    assert_eq!(executed_subjects, 67);
    assert_eq!(unsupported_plans, 1);
}
