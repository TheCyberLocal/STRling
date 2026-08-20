use strling::contract::{CompileOutcome, RequestedOutput};
use strling::source::SpecificationVersion;
use strling::{
    check, compile, stdlib, CompileRequest, KernelCompileError, SimplyBuilder, SimplyOptions,
    TargetProfile,
};

fn request(fixture: &str) -> CompileRequest {
    let text = match fixture {
        "source" => include_str!(
            "../../../spec/contracts/1.0/examples/compile-request/regex-compat-success.json"
        ),
        "failed" => include_str!(
            "../../../spec/contracts/1.0/examples/compile-request/regex-compat-malformed.json"
        ),
        "target" => include_str!(
            "../../../spec/contracts/1.0/examples/compile-request/target-artifact.json"
        ),
        _ => panic!("unknown fixture"),
    };
    serde_json::from_str(text).expect("canonical request fixture")
}

fn profile(version: &str) -> TargetProfile {
    let text = match version {
        "10.42" => include_str!("../../../spec/targets/profiles/pcre2-10.42.json"),
        "10.43" => include_str!("../../../spec/targets/profiles/pcre2-10.43.json"),
        _ => panic!("unknown profile"),
    };
    serde_json::from_str(text).expect("canonical target profile fixture")
}

#[test]
fn compile_and_check_are_the_same_canonical_execution() {
    let request = request("source");
    let compiled = compile(&request, None).expect("canonical compile");
    let checked = check(&request, None).expect("canonical check");
    assert_eq!(compiled, checked);
    assert_eq!(CompileOutcome::Succeeded, compiled.outcome);
    assert!(compiled.artifact.is_none());
}

#[test]
fn failed_compile_is_a_result_value() {
    let result = compile(&request("failed"), None).expect("completed compile");
    assert_eq!(CompileOutcome::Failed, result.outcome);
    assert!(!result.diagnostics.is_empty());
}

#[test]
fn target_aware_calls_require_the_exact_profile() {
    let request = request("target");
    let result = compile(&request, Some(&profile("10.43"))).expect("exact target");
    assert_eq!(CompileOutcome::Succeeded, result.outcome);
    assert!(result.artifact.is_some());

    assert!(matches!(
        compile(&request, None),
        Err(KernelCompileError::TargetProfileRequired { .. })
    ));
    assert!(matches!(
        compile(&request, Some(&profile("10.42"))),
        Err(KernelCompileError::TargetProfileMismatch { .. })
    ));
}

#[test]
fn simply_facade_builds_canonical_semantics() {
    let specification =
        SpecificationVersion::try_from("1.0-draft.1").expect("governed specification identity");
    let mut builder =
        SimplyBuilder::new("rust.facade.test", specification, SimplyOptions::default())
            .expect("builder");
    let value = builder.literal("literal", "🦀").expect("literal");
    let program = builder.finish_program(&value).expect("canonical program");
    assert_eq!(
        "node:simply/rust.facade.test/literal",
        program.root.node_id().as_str()
    );
}

#[test]
fn standard_helpers_retain_registered_lexical_guarantees() {
    let corpus = include_str!("../../../spec/stdlib/essential_5.json");
    assert!(corpus.contains("STRling Essential 5"));
    for helper in ["dateTime", "email", "ip", "url", "uuid"] {
        assert!(corpus.contains(&format!("\"{helper}\"")));
    }

    let email = stdlib::email().expect("canonical email helper");
    assert_eq!("stdlib.email", email.helper_id);
    assert_eq!("email.default", email.variant_id);
    let variants = [
        stdlib::date_time().expect("canonical date-time helper"),
        email,
        stdlib::ip(Some(4)).expect("canonical IPv4 helper"),
        stdlib::ip(Some(6)).expect("canonical IPv6 helper"),
        stdlib::ip(None).expect("canonical IP helper"),
        stdlib::url().expect("canonical URL helper"),
        stdlib::uuid(None).expect("canonical UUID helper"),
        stdlib::uuid(Some(4)).expect("canonical UUIDv4 helper"),
    ];
    assert_eq!(stdlib::VARIANT_COUNT, variants.len());
    assert_eq!(5, stdlib::HELPER_COUNT);
    assert_eq!(8, stdlib::VARIANT_COUNT);
    assert_eq!(0, stdlib::SEMANTIC_VALIDATOR_COUNT);
}

#[test]
fn facade_exports_requested_output_contracts() {
    let request = request("source");
    assert_eq!(
        vec![RequestedOutput::Semantic, RequestedOutput::Analysis],
        request.requested_outputs
    );
    assert_eq!("3.0.0", strling::version());
}
