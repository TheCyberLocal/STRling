use serde::Deserialize;
use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::{
    certified_rewrite_registry, certify_rewrite_registry, plan_portability,
    RequirementPlanningDisposition, RewriteStrategyId,
};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::source::ContractVersion;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{PortabilityStatus, TargetProfile};

const REGISTRY: &str = include_str!("../../spec/portability/equivalence/1.0/registry.json");
const REGISTRY_SCHEMA: &str =
    include_str!("../../spec/portability/equivalence/1.0/registry.schema.json");
const CASES: &str =
    include_str!("../../spec/portability/equivalence/1.0/atomic-literal-elision.cases.json");
const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");

#[derive(Deserialize)]
struct Suite {
    suite_version: String,
    strategy_id: String,
    cases: Vec<Case>,
    preserved_invariants: Vec<String>,
    execution_hooks: Vec<ExecutionHook>,
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

#[derive(Deserialize)]
struct ExecutionHook {
    hook_id: String,
    status: String,
    obligation: String,
}

#[test]
fn authored_registry_reproduces_strategy_and_conformance_fingerprints() {
    let schema: Value = serde_json::from_str(REGISTRY_SCHEMA).expect("registry schema JSON");
    assert_eq!(
        schema["$id"],
        "https://strling.dev/portability/equivalence/1.0/registry.schema.json"
    );
    let direct = certify_rewrite_registry(REGISTRY.as_bytes(), CASES.as_bytes())
        .expect("authored registry must certify");
    let cached = certified_rewrite_registry().expect("embedded registry must certify");

    assert_eq!(&direct, cached);
    assert_eq!(direct.registry_version, ContractVersion::V1_0_0);
    assert_eq!(direct.strategies.len(), 1);
    let strategy = &direct.strategies[0];
    assert_eq!(
        strategy.strategy_id,
        RewriteStrategyId::ElideAtomicLiteralV1
    );
    assert_eq!(
        strategy.strategy_fingerprint.as_str(),
        "52d1a15ffb3becdde9e33f708539395e395eff752741283d90ff8bb1ccb64cc5"
    );
    assert_eq!(
        strategy.definition.conformance_evidence.sha256.as_str(),
        "5fe61a36f43a50b7ce5f6e2b13f0ac36ded8bda0e6255a66027bcf669a1d3532"
    );
    assert_eq!(
        strategy.definition.required_tests,
        [
            "property.normalized_programs.v1",
            "conformance.atomic_literal_elision.v1"
        ]
    );
    assert_eq!(strategy.definition.execution_hooks.len(), 1);
    assert_eq!(
        strategy.definition.execution_hooks[0].status,
        "deferred_until_target_emitter"
    );
}

#[test]
fn missing_or_stale_authored_evidence_blocks_registry_certification() {
    let mut stale: Value = serde_json::from_str(REGISTRY).expect("registry JSON");
    stale["strategies"][0]["conformance_evidence"]["sha256"] = Value::String("0".repeat(64));
    let stale_bytes = serde_json::to_vec(&stale).expect("stale registry bytes");
    let error = certify_rewrite_registry(&stale_bytes, CASES.as_bytes())
        .expect_err("stale evidence must fail");
    assert!(error.message.contains("missing or stale"));

    let mut missing_tests: Value = serde_json::from_str(REGISTRY).expect("registry JSON");
    missing_tests["strategies"][0]
        .as_object_mut()
        .expect("strategy object")
        .remove("required_tests");
    let missing_test_bytes = serde_json::to_vec(&missing_tests).expect("missing-test bytes");
    assert!(certify_rewrite_registry(&missing_test_bytes, CASES.as_bytes()).is_err());

    let mut missing_cases: Value = serde_json::from_str(CASES).expect("evidence JSON");
    missing_cases["cases"] = json!([]);
    let missing_case_bytes = serde_json::to_vec(&missing_cases).expect("missing-case bytes");
    let error = certify_rewrite_registry(REGISTRY.as_bytes(), &missing_case_bytes)
        .expect_err("missing conformance cases must fail");
    assert!(error.message.contains("missing or stale"));
}

#[test]
fn specification_authored_cases_certify_only_atomic_literal_elision() {
    let suite: Suite = serde_json::from_str(CASES).expect("authored equivalence cases");
    assert_eq!(suite.suite_version, "1.0.0");
    assert_eq!(suite.strategy_id, "rewrite.atomic_literal.elide.v1");
    assert_eq!(suite.cases.len(), 4);
    assert_eq!(suite.preserved_invariants.len(), 4);
    assert_eq!(suite.execution_hooks.len(), 1);
    assert_eq!(
        suite.execution_hooks[0].hook_id,
        "runtime.atomic_literal_elision.differential.v1"
    );
    assert_eq!(
        suite.execution_hooks[0].status,
        "deferred_until_target_emitter"
    );
    assert!(!suite.execution_hooks[0].obligation.is_empty());

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
                "unresolved" => {
                    assert_eq!(plan.status, None);
                    continue;
                }
                other => panic!("unknown expected status: {other}"),
            };
            assert_eq!(
                plan.status,
                Some(expected),
                "case {} on {}",
                case.case_id,
                expectation.profile
            );
            if expected == PortabilityStatus::EquivalentRewrite {
                let RequirementPlanningDisposition::EquivalentRewrite(rewrite) =
                    &plan.decisions[0].disposition
                else {
                    panic!("{} must select the certified rewrite", case.case_id);
                };
                let certified = certified_rewrite_registry()
                    .expect("registry")
                    .strategy(RewriteStrategyId::ElideAtomicLiteralV1)
                    .expect("strategy");
                assert_eq!(
                    rewrite.rewrite_plan.certification.strategy_fingerprint,
                    certified.strategy_fingerprint
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
