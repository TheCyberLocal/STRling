use std::collections::BTreeMap;
use std::panic::{catch_unwind, AssertUnwindSafe};

use serde_json::Value;
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::explanation::{explain_semantics, explain_target, ExplanationDocument};
use strling_kernel::no_match_explanation::{
    explain_no_match, NoMatchExecutionMode, NoMatchExplanationDocument,
    NoMatchExplanationErrorCode, NoMatchLimits,
};
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;

const CORPUS: &str = include_str!("../../spec/explanations/no-match/1.0/verification-corpus.json");
const ECMASCRIPT_2024: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

fn authored_example(case_id: &str) -> Option<&'static str> {
    match case_id {
        "matched-literal" => Some(include_str!(
            "../../spec/explanations/no-match/1.0/examples/matched-literal.json"
        )),
        "proven-literal-mismatch" => Some(include_str!(
            "../../spec/explanations/no-match/1.0/examples/proven-literal-mismatch.json"
        )),
        "input-start-multiple-blockers" => Some(include_str!(
            "../../spec/explanations/no-match/1.0/examples/likely-multiple-blockers.json"
        )),
        "step-limit" => Some(include_str!(
            "../../spec/explanations/no-match/1.0/examples/unknown-step-limit.json"
        )),
        "target-unsupported" => Some(include_str!(
            "../../spec/explanations/no-match/1.0/examples/unavailable-target.json"
        )),
        _ => None,
    }
}

fn explain(input: &SemanticProgram) -> (SemanticProgram, ExplanationDocument) {
    let normalized = normalize(input).expect("normalize");
    let foundational = analyze(&normalized).expect("foundational analysis");
    let structural = analyze_structure(&normalized, &foundational).expect("structural analysis");
    let safety = analyze_safety(&normalized, &foundational, &structural).expect("safety analysis");
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .expect("diagnostic generation");
    let explanation = explain_semantics(
        &normalized,
        &foundational,
        &structural,
        &safety,
        &diagnostics,
    )
    .expect("semantic explanation");
    (normalized, explanation)
}

fn project_ecmascript(
    input: &SemanticProgram,
    semantic: &ExplanationDocument,
) -> ExplanationDocument {
    let foundational = analyze(input).expect("foundational analysis");
    let structural = analyze_structure(input, &foundational).expect("structural analysis");
    let target: TargetProfile = serde_json::from_str(ECMASCRIPT_2024).expect("target profile");
    let evaluation = evaluate_capabilities(input, &foundational, &structural, &target)
        .expect("capability evaluation");
    let plan = plan_portability(input, &foundational, &structural, &target, &evaluation)
        .expect("portability plan");
    explain_target(semantic, &evaluation, &plan).expect("target explanation")
}

#[test]
fn canonical_verification_corpus_executes_against_the_rust_evaluator() {
    let corpus: Value = serde_json::from_str(CORPUS).expect("verification corpus");
    let programs = corpus["programs"]
        .as_array()
        .expect("program array")
        .iter()
        .map(|entry| {
            let id = entry["program_id"].as_str().expect("program id").to_owned();
            let input = serde_json::from_value(entry["program"].clone()).expect("semantic program");
            (id, input)
        })
        .collect::<BTreeMap<String, SemanticProgram>>();
    let mut example_drift = Vec::new();

    for case in corpus["cases"].as_array().expect("case array") {
        let case_id = case["case_id"].as_str().expect("case id");
        let input = programs
            .get(case["program_id"].as_str().expect("program id"))
            .expect("registered program");
        let (normalized, mut semantic) = explain(input);
        if case.get("target").is_some() {
            semantic = project_ecmascript(&normalized, &semantic);
        }
        let mut limits_value = corpus["default_limits"].clone();
        if let Some(overrides) = case.get("limits").and_then(Value::as_object) {
            for (key, value) in overrides {
                limits_value[key] = value.clone();
            }
        }
        let limits: NoMatchLimits =
            serde_json::from_value(limits_value).expect("case limits must be valid");
        let actual = explain_no_match(
            &normalized,
            &semantic,
            case["subject"].as_str().expect("subject"),
            NoMatchExecutionMode::Search,
            limits,
        )
        .unwrap_or_else(|errors| panic!("{case_id}: unexpected errors: {errors:?}"));
        let actual = serde_json::to_value(actual).expect("serialize result");
        let expected = &case["expected"];

        if let Some(example) = authored_example(case_id) {
            let example: Value = serde_json::from_str(example).expect("authored example");
            if actual != example {
                example_drift.push(format!(
                    "{case_id}:\n{}",
                    serde_json::to_string_pretty(&actual).expect("pretty result")
                ));
            }
        }

        let round_trip: NoMatchExplanationDocument =
            serde_json::from_value(actual.clone()).expect("result contract round trip");
        assert!(round_trip.findings.len() <= round_trip.limits.max_findings);
        assert!(round_trip.work.steps <= round_trip.limits.max_steps);
        assert!(round_trip.work.maximum_depth <= round_trip.limits.max_depth);
        assert!(round_trip.work.branch_expansions <= round_trip.limits.max_branch_expansions);

        assert_eq!(actual["outcome"], expected["outcome"], "{case_id}: outcome");
        assert_eq!(
            actual["explanation_disposition"], expected["disposition"],
            "{case_id}: disposition"
        );
        let actual_reasons = actual["findings"]
            .as_array()
            .expect("findings")
            .iter()
            .map(|finding| finding["reason_code"].clone())
            .collect::<Vec<_>>();
        assert_eq!(
            actual_reasons,
            expected["reason_codes"]
                .as_array()
                .expect("reason codes")
                .clone(),
            "{case_id}: reasons"
        );
    }
    assert!(
        example_drift.is_empty(),
        "authored example drift:\n{}",
        example_drift.join("\n")
    );
}

#[test]
fn hard_subject_ceilings_fail_before_evaluation() {
    let corpus: Value = serde_json::from_str(CORPUS).expect("verification corpus");
    let input: SemanticProgram =
        serde_json::from_value(corpus["programs"][7]["program"].clone()).expect("literal program");
    let (normalized, semantic) = explain(&input);

    for subject in ["x".repeat(16_385), "x".repeat(4_097)] {
        let errors = explain_no_match(
            &normalized,
            &semantic,
            &subject,
            NoMatchExecutionMode::Search,
            NoMatchLimits::default(),
        )
        .expect_err("hard subject ceiling");
        assert_eq!(
            errors.errors[0].code,
            NoMatchExplanationErrorCode::SubjectExceedsHardLimit
        );
    }
}

#[test]
fn result_identifies_but_never_embeds_subject_text() {
    let corpus: Value = serde_json::from_str(CORPUS).expect("verification corpus");
    let input: SemanticProgram =
        serde_json::from_value(corpus["programs"][7]["program"].clone()).expect("literal program");
    let (normalized, semantic) = explain(&input);
    let secret = "sentinel-private-subject";
    let result = explain_no_match(
        &normalized,
        &semantic,
        secret,
        NoMatchExecutionMode::Search,
        NoMatchLimits::default(),
    )
    .expect("bounded result");
    let serialized = serde_json::to_string(&result).expect("serialize result");

    assert!(!serialized.contains(secret));
    assert_eq!(result.subject.utf8_bytes, secret.len());
    assert_eq!(result.subject.unicode_scalars, secret.chars().count());
}

#[test]
fn bounded_evaluation_is_deterministic_and_no_panic_across_the_corpus_domain() {
    let corpus: Value = serde_json::from_str(CORPUS).expect("verification corpus");
    let subjects = ["", "a", "dog", "a\nb", "é", "🙂", "aaaa"];

    for entry in corpus["programs"].as_array().expect("program array") {
        let program_id = entry["program_id"].as_str().expect("program id");
        let input: SemanticProgram =
            serde_json::from_value(entry["program"].clone()).expect("semantic program");
        let (normalized, semantic) = explain(&input);
        for subject in subjects {
            let first = catch_unwind(AssertUnwindSafe(|| {
                explain_no_match(
                    &normalized,
                    &semantic,
                    subject,
                    NoMatchExecutionMode::Search,
                    NoMatchLimits::default(),
                )
            }))
            .unwrap_or_else(|_| panic!("{program_id}: evaluator panicked for {subject:?}"))
            .unwrap_or_else(|errors| panic!("{program_id}: unexpected errors: {errors:?}"));
            let second = explain_no_match(
                &normalized,
                &semantic,
                subject,
                NoMatchExecutionMode::Search,
                NoMatchLimits::default(),
            )
            .unwrap_or_else(|errors| panic!("{program_id}: repeated errors: {errors:?}"));

            assert_eq!(first, second, "{program_id}: repeated-byte determinism");
            assert!(first.work.steps <= first.limits.max_steps);
            assert!(first.work.maximum_depth <= first.limits.max_depth);
            assert!(first.work.branch_expansions <= first.limits.max_branch_expansions);
            assert!(first.findings.len() <= first.limits.max_findings);
        }
    }
}

#[test]
fn invalid_limits_and_mismatched_semantic_explanations_are_structured_errors() {
    let corpus: Value = serde_json::from_str(CORPUS).expect("verification corpus");
    let first: SemanticProgram =
        serde_json::from_value(corpus["programs"][7]["program"].clone()).expect("first program");
    let second: SemanticProgram =
        serde_json::from_value(corpus["programs"][0]["program"].clone()).expect("second program");
    let (first, first_explanation) = explain(&first);
    let (_, second_explanation) = explain(&second);

    let mismatch = explain_no_match(
        &first,
        &second_explanation,
        "dog",
        NoMatchExecutionMode::Search,
        NoMatchLimits::default(),
    )
    .expect_err("mismatched explanation");
    assert_eq!(
        mismatch.errors[0].code,
        NoMatchExplanationErrorCode::MismatchedExplanation
    );

    let invalid_limits = explain_no_match(
        &first,
        &first_explanation,
        "dog",
        NoMatchExecutionMode::Search,
        NoMatchLimits {
            max_steps: 0,
            ..NoMatchLimits::default()
        },
    )
    .expect_err("invalid limits");
    assert_eq!(
        invalid_limits.errors[0].code,
        NoMatchExplanationErrorCode::InvalidLimits
    );
}
