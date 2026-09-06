use serde::Deserialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::{
    certified_rewrite_registry, certify_rewrite_registry, certify_rewrite_registry_with_evidence,
    plan_portability, RequirementPlanningDisposition, RewriteApplicationKind, RewriteStrategyId,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::ContractVersion;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{PortabilityStatus, TargetProfile};

const REGISTRY: &str = include_str!("../../spec/portability/equivalence/1.0/registry.json");
const REGISTRY_SCHEMA: &str =
    include_str!("../../spec/portability/equivalence/1.0/registry.schema.json");
const ATOMIC_CASES: &str =
    include_str!("../../spec/portability/equivalence/1.0/atomic-literal-elision.cases.json");
const EXACT_ONCE_CASES: &str =
    include_str!("../../spec/portability/equivalence/1.0/exact-once-repetition-elision.cases.json");
const ECMASCRIPT_EXECUTION: &str =
    include_str!("../../tests/conformance/ecmascript-runtime-certification.json");
const PCRE2_EXECUTION: &str =
    include_str!("../../tests/conformance/pcre2-runtime-certification.json");
const PYTHON_RE_EXECUTION: &str =
    include_str!("../../tests/conformance/python-re-runtime-certification.json");
const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");

#[derive(Deserialize)]
struct Suite {
    suite_version: String,
    strategy_id: String,
    cases: Vec<Case>,
    preserved_invariants: Vec<String>,
}

#[derive(Deserialize)]
struct Case {
    case_id: String,
    semantic_root: Value,
    target_expectations: Vec<TargetExpectation>,
}

#[derive(Deserialize)]
struct TargetExpectation {
    profile: String,
    status: String,
}

fn certify_all(
    registry: &[u8],
    atomic: &[u8],
    exact_once: &[u8],
    ecma: &[u8],
) -> Result<
    strling_kernel::portability_planning::CertifiedRewriteRegistry,
    strling_kernel::portability_planning::RewriteRegistryError,
> {
    certify_rewrite_registry_with_evidence(
        registry,
        atomic,
        exact_once,
        ecma,
        PCRE2_EXECUTION.as_bytes(),
        PYTHON_RE_EXECUTION.as_bytes(),
    )
}

#[test]
fn authored_library_reproduces_complete_strategy_and_evidence_fingerprints() {
    let schema: Value = serde_json::from_str(REGISTRY_SCHEMA).expect("registry schema JSON");
    assert_eq!(
        schema["$id"],
        "https://strling.dev/portability/equivalence/1.0/registry.schema.json"
    );
    let direct = certify_all(
        REGISTRY.as_bytes(),
        ATOMIC_CASES.as_bytes(),
        EXACT_ONCE_CASES.as_bytes(),
        ECMASCRIPT_EXECUTION.as_bytes(),
    )
    .expect("authored rewrite library must certify");
    let cached = certified_rewrite_registry().expect("embedded registry must certify");

    assert_eq!(&direct, cached);
    assert_eq!(direct.registry_version, ContractVersion::V1_0_0);
    assert_eq!(direct.strategies.len(), 2);
    assert_eq!(
        direct.strategy_ids(),
        [
            RewriteStrategyId::ElideAtomicLiteralV1,
            RewriteStrategyId::ElideExactOnceRepetitionV1,
        ]
    );
    assert_eq!(
        direct.portability_strategy_ids(),
        [RewriteStrategyId::ElideAtomicLiteralV1]
    );
    assert_eq!(
        direct.strategies[0].definition.application_kind,
        RewriteApplicationKind::MandatoryPortability
    );
    assert_eq!(
        direct.strategies[1].definition.application_kind,
        RewriteApplicationKind::OptionalOptimization
    );
    assert_eq!(
        direct.strategies[0].strategy_fingerprint.as_str(),
        "6fdd5fc1daf500727be8dd84170f07691a6f3f9f644c671afe095ef454bebb5e"
    );
    assert_eq!(
        direct.strategies[1].strategy_fingerprint.as_str(),
        "6aca0899f54a7d2154bff4dd96fa14bf8147d250ffe1d63cef0a572dced0b71e"
    );
    for strategy in &direct.strategies {
        assert_eq!(strategy.definition.execution_evidence.len(), 3);
        assert_eq!(strategy.definition.target_applicability.profiles.len(), 5);
    }

    let compatible = certify_rewrite_registry(REGISTRY.as_bytes(), ATOMIC_CASES.as_bytes())
        .expect("legacy atomic mutation hook must certify the complete embedded library");
    assert_eq!(compatible, direct);
}

#[test]
fn missing_stale_widened_or_profile_incomplete_evidence_blocks_registration() {
    let mut stale: Value = serde_json::from_str(REGISTRY).expect("registry JSON");
    stale["strategies"][1]["conformance_evidence"]["sha256"] = Value::String("0".repeat(64));
    let error = certify_all(
        &serde_json::to_vec(&stale).expect("stale registry"),
        ATOMIC_CASES.as_bytes(),
        EXACT_ONCE_CASES.as_bytes(),
        ECMASCRIPT_EXECUTION.as_bytes(),
    )
    .expect_err("stale exact-once evidence must fail");
    assert!(error.message.contains("missing or stale"));

    let mut missing_cases: Value = serde_json::from_str(EXACT_ONCE_CASES).expect("cases");
    missing_cases["cases"] = json!([]);
    assert!(certify_all(
        REGISTRY.as_bytes(),
        ATOMIC_CASES.as_bytes(),
        &serde_json::to_vec(&missing_cases).expect("missing cases"),
        ECMASCRIPT_EXECUTION.as_bytes(),
    )
    .is_err());

    let mut missing_runtime: Value =
        serde_json::from_str(ECMASCRIPT_EXECUTION).expect("runtime corpus");
    missing_runtime["rewrite_cases"]
        .as_array_mut()
        .expect("rewrite cases")
        .retain(|case| case["strategy_id"] != "rewrite.repeat_exactly_once.elide.v1");
    let missing_runtime_bytes =
        serde_json::to_vec(&missing_runtime).expect("missing-runtime bytes");
    let mut matching_hash: Value = serde_json::from_str(REGISTRY).expect("registry");
    matching_hash["strategies"][1]["execution_evidence"][0]["sha256"] =
        Value::String(format!("{:x}", Sha256::digest(&missing_runtime_bytes)));
    assert!(certify_all(
        &serde_json::to_vec(&matching_hash).expect("matching registry"),
        ATOMIC_CASES.as_bytes(),
        EXACT_ONCE_CASES.as_bytes(),
        &missing_runtime_bytes,
    )
    .is_err());

    let mut widened: Value = serde_json::from_str(REGISTRY).expect("registry");
    widened["strategies"][1]["preconditions"][4]["id"] =
        Value::String("precondition.mode_any".to_owned());
    assert!(certify_all(
        &serde_json::to_vec(&widened).expect("widened registry"),
        ATOMIC_CASES.as_bytes(),
        EXACT_ONCE_CASES.as_bytes(),
        ECMASCRIPT_EXECUTION.as_bytes(),
    )
    .is_err());

    let mut incomplete_profiles: Value = serde_json::from_str(REGISTRY).expect("registry");
    incomplete_profiles["strategies"][1]["target_applicability"]["profiles"]
        .as_array_mut()
        .expect("profiles")
        .pop();
    assert!(certify_all(
        &serde_json::to_vec(&incomplete_profiles).expect("incomplete registry"),
        ATOMIC_CASES.as_bytes(),
        EXACT_ONCE_CASES.as_bytes(),
        ECMASCRIPT_EXECUTION.as_bytes(),
    )
    .is_err());
}

#[test]
fn unknown_removed_or_reordered_strategy_sets_fail_closed() {
    let mut unknown: Value = serde_json::from_str(REGISTRY).expect("registry");
    unknown["strategies"][1]["strategy_id"] = Value::String("rewrite.unknown.v1".to_owned());
    assert!(certify_all(
        &serde_json::to_vec(&unknown).expect("unknown registry"),
        ATOMIC_CASES.as_bytes(),
        EXACT_ONCE_CASES.as_bytes(),
        ECMASCRIPT_EXECUTION.as_bytes(),
    )
    .is_err());

    let mut removed: Value = serde_json::from_str(REGISTRY).expect("registry");
    removed["strategies"]
        .as_array_mut()
        .expect("strategies")
        .pop();
    assert!(certify_all(
        &serde_json::to_vec(&removed).expect("removed registry"),
        ATOMIC_CASES.as_bytes(),
        EXACT_ONCE_CASES.as_bytes(),
        ECMASCRIPT_EXECUTION.as_bytes(),
    )
    .is_err());

    let mut reordered: Value = serde_json::from_str(REGISTRY).expect("registry");
    reordered["strategies"]
        .as_array_mut()
        .expect("strategies")
        .reverse();
    assert!(certify_all(
        &serde_json::to_vec(&reordered).expect("reordered registry"),
        ATOMIC_CASES.as_bytes(),
        EXACT_ONCE_CASES.as_bytes(),
        ECMASCRIPT_EXECUTION.as_bytes(),
    )
    .is_err());
}

#[test]
fn specification_cases_preserve_atomic_literal_portability_selection() {
    let suite: Suite = serde_json::from_str(ATOMIC_CASES).expect("authored equivalence cases");
    assert_eq!(suite.suite_version, "1.0.0");
    assert_eq!(suite.strategy_id, "rewrite.atomic_literal.elide.v1");
    assert_eq!(suite.cases.len(), 4);
    assert_eq!(suite.preserved_invariants.len(), 4);

    let mut expectation_count = 0;
    for case in suite.cases {
        let raw: SemanticProgram = serde_json::from_value(json!({
            "contract_version": "1.0.0",
            "specification_version": "1.0-draft.1",
            "normalization": "canonical-v1",
            "case_matching": "sensitive",
            "root": case.semantic_root
        }))
        .unwrap_or_else(|error| panic!("{} must deserialize: {error}", case.case_id));
        let semantic = normalize(&raw)
            .unwrap_or_else(|error| panic!("{} must normalize: {error}", case.case_id));
        let foundational = analyze(&semantic).expect("foundational facts");
        let structural = analyze_structure(&semantic, &foundational).expect("structural facts");

        for expectation in case.target_expectations {
            expectation_count += 1;
            let target: TargetProfile = serde_json::from_str(profile_fixture(&expectation.profile))
                .expect("authored target profile");
            let evaluation = evaluate_capabilities(&semantic, &foundational, &structural, &target)
                .expect("capability evaluation");
            let plan =
                plan_portability(&semantic, &foundational, &structural, &target, &evaluation)
                    .expect("portability plan");
            let expected = match expectation.status.as_str() {
                "native" => PortabilityStatus::Native,
                "equivalent_rewrite" => PortabilityStatus::EquivalentRewrite,
                "unsupported" => PortabilityStatus::Unsupported,
                other => panic!("unknown expected status: {other}"),
            };
            assert_eq!(plan.status, Some(expected));
            if expected == PortabilityStatus::EquivalentRewrite {
                let RequirementPlanningDisposition::EquivalentRewrite(rewrite) =
                    &plan.decisions[0].disposition
                else {
                    panic!("{} must select the certified rewrite", case.case_id);
                };
                assert_eq!(
                    rewrite.rewrite_plan.strategy_id,
                    RewriteStrategyId::ElideAtomicLiteralV1
                );
            }
        }
    }
    assert_eq!(expectation_count, 6);
}

fn profile_fixture(name: &str) -> &'static str {
    match name {
        "ecmascript-2024.json" => ECMASCRIPT,
        "pcre2-10.42.json" => PCRE2_1042,
        "pcre2-10.43.json" => PCRE2_1043,
        other => panic!("unregistered profile fixture: {other}"),
    }
}
