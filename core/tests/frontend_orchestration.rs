use std::collections::BTreeSet;
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

use serde_json::{json, Value};
use strling_kernel::diagnostic::{CompilerPhase, DiagnosticCategory};
use strling_kernel::protocol::{
    validate_exchange, CompileInput, CompileOutcome, CompileRequest, CompileResult,
};
use strling_kernel::source::{FrontendId, SourceContent};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::from_json;
use strling_kernel::{compile, KernelCompileError};

const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");
const FIXTURE_SUCCESS_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/regex-compat-success.json");
const FIXTURE_SUCCESS_RESULT: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-result/regex-compat-success.json");
const FIXTURE_MALFORMED_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/regex-compat-malformed.json");
const FIXTURE_MALFORMED_RESULT: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-result/regex-compat-malformed.json");
const FIXTURE_DIRECTIVE_REQUEST: &str = include_str!(
    "../../spec/contracts/1.0/examples/compile-request/regex-compat-unsupported-directive.json"
);
const FIXTURE_DIRECTIVE_RESULT: &str = include_str!(
    "../../spec/contracts/1.0/examples/compile-result/regex-compat-unsupported-directive.json"
);
const FIXTURE_REFERENCE_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/regex-compat-reference.json");
const FIXTURE_REFERENCE_RESULT: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-result/regex-compat-reference.json");
const FIXTURE_PORTABILITY_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/regex-compat-portability.json");
const FIXTURE_PORTABILITY_RESULT: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-result/regex-compat-portability.json");

#[derive(Debug, serde::Deserialize)]
struct OrchestrationSet {
    case_set_version: String,
    frontend: String,
    authorship: String,
    authority: String,
    cases: Vec<OrchestrationCase>,
}

#[derive(Debug, serde::Deserialize)]
struct OrchestrationCase {
    id: String,
    source: String,
    expected: OrchestrationExpectation,
}

#[derive(Debug, serde::Deserialize)]
struct OrchestrationExpectation {
    outcome: String,
    #[serde(default)]
    diagnostic_code: Option<String>,
}

fn repository_file(path: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join(path)
}

fn orchestration_set() -> OrchestrationSet {
    let path = repository_file("spec/frontends/legacy-regex/1.0/orchestration/cases.json");
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    serde_json::from_str(&text)
        .unwrap_or_else(|error| panic!("deserialize {}: {error}", path.display()))
}

fn source_request(source: &str, outputs: &[&str]) -> CompileRequest {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": {
            "kind": "source",
            "document": {
                "contract_version": "1.0.0",
                "source_id": "src:orchestration.regex",
                "specification_version": "1.0-draft.1",
                "frontend": {
                    "id": "strling.regex-compat",
                    "dialect_version": "1.0.0"
                },
                "display_name": "fixture.regex",
                "content": {
                    "kind": "inline",
                    "encoding": "utf-8",
                    "media_type": "text/strling-regex",
                    "text": source
                },
                "provenance": {
                    "kind": "imported",
                    "description": "P08-T04 canonical orchestration fixture"
                }
            }
        },
        "requested_outputs": outputs,
        "compiler_options": {
            "partial_semantics": "forbid",
            "diagnostic_policy": { "minimum_severity": "hint" }
        }
    }))
    .expect("valid regex source compile request")
}

fn run_cli(request: &CompileRequest, args: &[&str]) -> std::process::Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_strling-kernel"))
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn canonical JSON CLI");
    serde_json::to_writer(child.stdin.as_mut().expect("CLI stdin"), request)
        .expect("write request");
    child
        .wait_with_output()
        .expect("wait for canonical JSON CLI")
}

#[test]
fn supported_source_compiles_through_the_canonical_semantic_pipeline() {
    let request = source_request("%flags im\n^(?<word>[A-Z]+)$", &["semantic", "analysis"]);
    let expected_document = match &request.input {
        CompileInput::Source { document } => document.as_ref(),
        CompileInput::Semantic { .. } => panic!("source request expected"),
    };

    let result = compile(&request, None).expect("supported source compiles");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    let semantic = result.semantic_result.expect("requested semantic result");
    let sources = semantic
        .program
        .sources
        .expect("source identity is retained");
    assert_eq!(sources.as_slice(), std::slice::from_ref(expected_document));
    assert!(semantic.program.root.origin().is_some());
    assert!(result.analysis.is_some());
    assert!(result.portability.is_none());
    assert!(result.artifact.is_none());
}

#[test]
fn malformed_source_projects_the_frozen_frontend_diagnostic_unchanged() {
    let request = source_request("a(b", &["semantic"]);

    let result = compile(&request, None).expect("syntax rejection is a compile result");

    assert_eq!(result.outcome, CompileOutcome::Failed);
    assert!(result.semantic_result.is_none());
    assert_eq!(result.diagnostics.len(), 1);
    let diagnostic = &result.diagnostics[0];
    assert_eq!(diagnostic.code.as_str(), "STRL-FRONTEND-2012");
    assert_eq!(diagnostic.phase, CompilerPhase::FrontendParse);
    assert_eq!(diagnostic.category, DiagnosticCategory::Syntax);
    assert_eq!(
        diagnostic
            .primary_location
            .as_ref()
            .expect("source location")
            .source_id
            .as_str(),
        "src:orchestration.regex"
    );
}

#[test]
fn unsupported_directive_and_dialect_are_explicit_frontend_diagnostics() {
    let directive = compile(&source_request("%engine pcre2\na", &["semantic"]), None)
        .expect("unsupported directive is a result");
    assert_eq!(directive.diagnostics[0].code.as_str(), "STRL-FRONTEND-1002");

    let mut request = source_request("abc", &["semantic"]);
    let CompileInput::Source { document } = &mut request.input else {
        panic!("source request expected");
    };
    document.frontend.dialect_version =
        strling_kernel::source::DialectVersion::try_from("2.0.0").expect("dialect version");
    let dialect = compile(&request, None).expect("unsupported dialect is a result");
    assert_eq!(dialect.diagnostics[0].code.as_str(), "STRL-FRONTEND-0003");
}

#[test]
fn unsupported_frontend_and_unresolved_content_remain_structured() {
    let mut unsupported = source_request("abc", &["semantic"]);
    let CompileInput::Source { document } = &mut unsupported.input else {
        panic!("source request expected");
    };
    document.frontend.id =
        strling_kernel::source::FrontendId::try_from("future_frontend").expect("frontend id");
    let result = compile(&unsupported, None).expect("unsupported frontend is a result");
    assert_eq!(result.diagnostics[0].code.as_str(), "STRL-PROTOCOL-0002");

    let mut referenced = source_request("abc", &["semantic"]);
    let CompileInput::Source { document } = &mut referenced.input else {
        panic!("source request expected");
    };
    document.content = serde_json::from_value(json!({
        "kind": "reference",
        "encoding": "utf-8",
        "media_type": "text/strling-regex",
        "uri": "urn:strling:source:orchestration",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }))
    .expect("valid referenced content");
    assert!(matches!(document.content, SourceContent::Reference { .. }));
    let result = compile(&referenced, None).expect("unresolved content is a result");
    assert_eq!(result.diagnostics[0].code.as_str(), "STRL-PROTOCOL-0006");
    assert_eq!(result.diagnostics[0].phase, CompilerPhase::Protocol);
}

#[test]
fn parsed_semantics_obey_the_caller_resource_limit() {
    let mut request = source_request("a|b", &["semantic"]);
    request.compiler_options.resource_limits = serde_json::from_value(json!({
        "max_semantic_nodes": 1
    }))
    .expect("valid resource limits");

    let result = compile(&request, None).expect("resource exhaustion is a result");

    assert_eq!(result.outcome, CompileOutcome::Failed);
    assert_eq!(result.diagnostics[0].code.as_str(), "STRL-PROTOCOL-0003");
    assert!(result.diagnostics[0].message.contains("semantic nodes"));
}

#[test]
fn exact_target_profile_is_required_and_reused_for_source_portability() {
    let profile: TargetProfile = from_json(PCRE2_1043).expect("certified target profile");
    let mut request = source_request("abc", &["semantic", "portability"]);
    request.target_profile = Some(profile.reference().expect("profile reference"));

    assert!(matches!(
        compile(&request, None),
        Err(KernelCompileError::TargetProfileRequired { .. })
    ));
    let result = compile(&request, Some(&profile)).expect("exact target profile compiles");
    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert_eq!(
        result
            .portability
            .expect("requested portability")
            .target_profile,
        request.target_profile.expect("request profile")
    );
}

#[test]
fn result_serialization_is_deterministic_for_source_requests() {
    let request = source_request("%flags x\na # comment\n b", &["semantic", "analysis"]);
    let first = compile(&request, None).expect("first compile");
    let second = compile(&request, None).expect("second compile");

    assert_eq!(
        serde_json::to_vec(&first).expect("serialize first"),
        serde_json::to_vec(&second).expect("serialize second")
    );
}

#[test]
fn cli_success_and_compile_failure_use_stable_exit_codes_and_json() {
    let success = run_cli(&source_request("abc", &["semantic"]), &[]);
    assert_eq!(success.status.code(), Some(0));
    assert!(success.stderr.is_empty());
    let value: Value = serde_json::from_slice(&success.stdout).expect("success JSON");
    assert_eq!(value["outcome"], "succeeded");
    assert!(success.stdout.ends_with(b"\n"));

    let failure = run_cli(&source_request("a(b", &["semantic"]), &[]);
    assert_eq!(failure.status.code(), Some(2));
    assert!(failure.stderr.is_empty());
    let value: Value = serde_json::from_slice(&failure.stdout).expect("failure JSON");
    assert_eq!(value["outcome"], "failed");
    assert_eq!(value["diagnostics"][0]["code"], "STRL-FRONTEND-2012");
}

#[test]
fn cli_help_and_malformed_contract_use_stable_transport_semantics() {
    let help = Command::new(env!("CARGO_BIN_EXE_strling-kernel"))
        .arg("--help")
        .output()
        .expect("run CLI help");
    assert_eq!(help.status.code(), Some(0));
    assert!(String::from_utf8_lossy(&help.stdout).contains("Usage: strling compile"));
    assert!(help.stderr.is_empty());

    let mut child = Command::new(env!("CARGO_BIN_EXE_strling-kernel"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn malformed CLI request");
    child
        .stdin
        .as_mut()
        .expect("CLI stdin")
        .write_all(b"{not-json}")
        .expect("write malformed request");
    let output = child
        .wait_with_output()
        .expect("wait for malformed request");
    assert_eq!(output.status.code(), Some(64));
    assert!(output.stdout.is_empty());
    assert!(String::from_utf8_lossy(&output.stderr).contains("invalid compile request"));
}

#[test]
fn cli_requires_and_accepts_the_exact_explicit_target_profile() {
    let request: CompileRequest = from_json(FIXTURE_PORTABILITY_REQUEST).expect("fixture request");

    let absent = run_cli(&request, &[]);
    assert_eq!(absent.status.code(), Some(70));
    assert!(absent.stdout.is_empty());
    assert!(String::from_utf8_lossy(&absent.stderr).contains("requires the exact target profile"));

    let profile_path = repository_file("spec/targets/profiles/pcre2-10.43.json");
    let profile_argument = profile_path.to_str().expect("UTF-8 profile path");
    let present = run_cli(&request, &["--target-profile", profile_argument]);
    assert_eq!(present.status.code(), Some(0));
    assert!(present.stderr.is_empty());
    let result: CompileResult =
        serde_json::from_slice(&present.stdout).expect("profile-aware result JSON");
    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert!(result.portability.is_some());
}

#[test]
fn covers_every_governed_historical_source_through_compile_request() {
    let corpus = orchestration_set();
    assert_eq!(corpus.case_set_version, "1.0.0");
    assert_eq!(corpus.frontend, "strling.regex-compat@1.0.0");
    assert_eq!(corpus.authorship, "specification-authored");
    assert!(corpus
        .authority
        .contains("historical implementations remain evidence only"));
    assert_eq!(corpus.cases.len(), 22);

    let mut source_ids = BTreeSet::new();
    for case in &corpus.cases {
        assert!(
            source_ids.insert(case.source.as_str()),
            "duplicate source: {}",
            case.id
        );
        let result = compile(
            &source_request(&case.source, &["semantic", "analysis"]),
            None,
        )
        .unwrap_or_else(|error| panic!("{} orchestration failed: {error}", case.id));
        match case.expected.outcome.as_str() {
            "succeeded" => {
                assert_eq!(result.outcome, CompileOutcome::Succeeded, "{}", case.id);
                assert!(result.semantic_result.is_some(), "{}", case.id);
                assert!(result.analysis.is_some(), "{}", case.id);
                assert!(case.expected.diagnostic_code.is_none(), "{}", case.id);
            }
            "failed" => {
                assert_eq!(result.outcome, CompileOutcome::Failed, "{}", case.id);
                assert_eq!(result.diagnostics.len(), 1, "{}", case.id);
                assert_eq!(
                    Some(result.diagnostics[0].code.as_str()),
                    case.expected.diagnostic_code.as_deref(),
                    "{}",
                    case.id
                );
            }
            outcome => panic!("{} has unknown outcome {outcome}", case.id),
        }
    }
}

#[test]
fn public_request_and_result_fixtures_are_exact_executable_exchanges() {
    let profile: TargetProfile = from_json(PCRE2_1043).expect("certified target profile");
    let supported = [FrontendId::try_from("strling.regex-compat").expect("frontend id")];
    let fixtures = [
        (FIXTURE_SUCCESS_REQUEST, FIXTURE_SUCCESS_RESULT, None),
        (FIXTURE_MALFORMED_REQUEST, FIXTURE_MALFORMED_RESULT, None),
        (FIXTURE_DIRECTIVE_REQUEST, FIXTURE_DIRECTIVE_RESULT, None),
        (FIXTURE_REFERENCE_REQUEST, FIXTURE_REFERENCE_RESULT, None),
        (
            FIXTURE_PORTABILITY_REQUEST,
            FIXTURE_PORTABILITY_RESULT,
            Some(&profile),
        ),
    ];

    for (request_json, result_json, target_profile) in fixtures {
        let request: CompileRequest = from_json(request_json).expect("fixture request");
        let expected: CompileResult = from_json(result_json).expect("fixture result");
        validate_exchange(&request, &expected, &supported).expect("valid fixture exchange");

        let actual = compile(&request, target_profile).expect("fixture executes");
        assert_eq!(actual, expected);
        assert_eq!(
            serde_json::to_vec(&actual).expect("serialize actual"),
            serde_json::to_vec(&expected).expect("serialize expected")
        );
    }
}
