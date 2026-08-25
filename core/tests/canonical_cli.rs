use std::env;
use std::fs;
use std::io::{ErrorKind, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};

use serde_json::Value;
use strling_kernel::protocol::{CompileRequest, CompileResult};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::from_json;

const SEMANTIC_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/semantic-input.json");
const TARGET_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/target-artifact.json");
const PCRE2_1043_PATH: &str = "../../spec/targets/profiles/pcre2-10.43.json";
const PCRE2_1043: &str = include_str!("../../spec/targets/profiles/pcre2-10.43.json");
const SIMPLE_SOURCE: &str = "semantic strling 1.0;\ncase sensitive;\npattern text \"a\";\n";

static TEMP_ORDINAL: AtomicU64 = AtomicU64::new(0);

struct TestDirectory(PathBuf);

impl TestDirectory {
    fn new() -> Self {
        let base = env::var_os("CARGO_TARGET_TMPDIR")
            .map(PathBuf::from)
            .unwrap_or_else(env::temp_dir);
        let path = base.join(format!(
            "strling-cli-{}-{}",
            std::process::id(),
            TEMP_ORDINAL.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&path).expect("create CLI test directory");
        Self(path)
    }

    fn path(&self, name: &str) -> PathBuf {
        self.0.join(name)
    }
}

impl Drop for TestDirectory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn cli(arguments: &[&str], stdin: &str) -> Output {
    let mut child = Command::new(env!("CARGO_BIN_EXE_strling-kernel"))
        .args(arguments)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn canonical CLI");
    let mut child_stdin = child.stdin.take().expect("stdin pipe");
    if let Err(error) = child_stdin.write_all(stdin.as_bytes()) {
        assert_eq!(
            error.kind(),
            ErrorKind::BrokenPipe,
            "write CLI stdin: {error}"
        );
    }
    drop(child_stdin);
    child.wait_with_output().expect("collect CLI output")
}

fn stdout_json(output: &Output) -> Value {
    serde_json::from_slice(&output.stdout).unwrap_or_else(|error| {
        panic!(
            "invalid stdout JSON: {error}; stdout={}; stderr={}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        )
    })
}

fn path_text(path: &Path) -> String {
    path.to_str().expect("UTF-8 test path").to_owned()
}

#[test]
fn raw_compile_is_result_identical_to_the_library_facade() {
    let request: CompileRequest = from_json(SEMANTIC_REQUEST).expect("semantic request");
    let expected = strling_kernel::compile(&request, None).expect("library compile");

    let output = cli(&["compile"], SEMANTIC_REQUEST);

    assert_eq!(output.status.code(), Some(0));
    assert!(output.stderr.is_empty());
    let actual: CompileResult =
        serde_json::from_slice(&output.stdout).expect("canonical CompileResult");
    assert_eq!(actual, expected);
}

#[test]
fn target_artifact_is_result_identical_and_safely_published() {
    let directory = TestDirectory::new();
    let artifact_path = directory.path("artifact.regex");
    let profile_path = Path::new(env!("CARGO_MANIFEST_DIR")).join(PCRE2_1043_PATH);
    let request: CompileRequest = from_json(TARGET_REQUEST).expect("target request");
    let profile: TargetProfile = from_json(PCRE2_1043).expect("target profile");
    let expected = strling_kernel::compile(&request, Some(&profile)).expect("library compile");
    let arguments = [
        "compile",
        "--target-profile",
        profile_path.to_str().expect("profile path"),
        "--output-file",
        artifact_path.to_str().expect("artifact path"),
    ];

    let first = cli(&arguments, TARGET_REQUEST);

    assert_eq!(first.status.code(), Some(0));
    let actual: CompileResult = serde_json::from_slice(&first.stdout).expect("CompileResult");
    assert_eq!(actual, expected);
    assert_eq!(
        fs::read_to_string(&artifact_path).expect("artifact material"),
        expected.artifact.expect("artifact").pattern.text
    );

    let second = cli(&arguments, TARGET_REQUEST);
    assert_eq!(second.status.code(), Some(74));
    assert!(second.stdout.is_empty());
    assert!(String::from_utf8_lossy(&second.stderr).contains("refusing to overwrite"));
    assert_eq!(fs::read_to_string(&artifact_path).unwrap(), "abc");
}

#[test]
fn source_shorthand_is_deterministic_and_preserves_file_provenance() {
    let directory = TestDirectory::new();
    let source_path = directory.path("pattern.strl");
    fs::write(&source_path, SIMPLE_SOURCE).expect("write source");
    let arguments = ["compile", "--input", source_path.to_str().unwrap()];

    let first = cli(&arguments, "");
    let second = cli(&arguments, "");

    assert_eq!(first.status.code(), Some(0));
    assert_eq!(first.stdout, second.stdout);
    let result = stdout_json(&first);
    let source = &result["semantic_result"]["program"]["sources"][0];
    assert_eq!(source["display_name"], path_text(&source_path));
    assert_eq!(source["provenance"]["kind"], "authored");
    assert!(source["source_id"]
        .as_str()
        .expect("source id")
        .starts_with("src:cli."));
}

#[test]
fn regex_import_uses_imported_provenance() {
    let output = cli(&["import", "--input", "-"], "a+");

    assert_eq!(output.status.code(), Some(0));
    assert!(output.stderr.is_empty());
    let result = stdout_json(&output);
    let source = &result["semantic_result"]["program"]["sources"][0];
    assert_eq!(source["frontend"]["id"], "strling.regex-compat");
    assert_eq!(source["provenance"]["kind"], "imported");
}

#[test]
fn explanation_reuses_compile_evidence_and_never_echoes_subject_text() {
    let directory = TestDirectory::new();
    let source_path = directory.path("pattern.strl");
    fs::write(&source_path, SIMPLE_SOURCE).expect("write source");
    let secret = "do-not-echo-this-subject";
    let output = cli(
        &[
            "explain",
            "--input",
            source_path.to_str().unwrap(),
            "--subject",
            secret,
        ],
        "",
    );

    assert_eq!(output.status.code(), Some(0));
    assert!(output.stderr.is_empty());
    assert!(!String::from_utf8_lossy(&output.stdout).contains(secret));
    let response = stdout_json(&output);
    assert_eq!(response["cli_contract_version"], "1.0.0");
    assert_eq!(response["command"], "explain");
    assert_eq!(response["status"], "completed");
    assert!(response["explanation"].is_object());
    assert!(response["no_match"].is_object());
}

#[test]
fn exact_migration_writes_only_create_new_destination_material() {
    let directory = TestDirectory::new();
    let source_path = directory.path("pattern.strl");
    let output_path = directory.path("migrated.strl");
    fs::write(&source_path, SIMPLE_SOURCE).expect("write source");
    let arguments = [
        "migrate",
        "--input",
        source_path.to_str().unwrap(),
        "--to",
        "semantic",
        "--output-file",
        output_path.to_str().unwrap(),
    ];

    let first = cli(&arguments, "");
    assert_eq!(first.status.code(), Some(0));
    assert!(fs::read_to_string(&output_path)
        .expect("migration material")
        .starts_with("semantic strling 1.0;"));
    let response = stdout_json(&first);
    assert_eq!(response["status"], "completed");
    assert_eq!(response["conversion"]["status"], "exact");

    let original = fs::read(&output_path).unwrap();
    let second = cli(&arguments, "");
    assert_eq!(second.status.code(), Some(74));
    assert_eq!(fs::read(&output_path).unwrap(), original);
}

#[test]
fn failed_migration_never_creates_output() {
    let directory = TestDirectory::new();
    let source_path = directory.path("broken.strl");
    let output_path = directory.path("must-not-exist.strl");
    fs::write(&source_path, "not semantic strling").expect("write broken source");
    let output = cli(
        &[
            "migrate",
            "--input",
            source_path.to_str().unwrap(),
            "--output-file",
            output_path.to_str().unwrap(),
        ],
        "",
    );

    assert_eq!(output.status.code(), Some(2));
    assert!(!output_path.exists());
    assert_eq!(stdout_json(&output)["status"], "compile_failed");
}

#[test]
fn target_list_and_inspect_cover_the_exact_bundled_registry() {
    let first = cli(&["target", "list", "--format", "json"], "");
    let second = cli(&["target", "list", "--format", "json"], "");
    assert_eq!(first.status.code(), Some(0));
    assert_eq!(first.stdout, second.stdout);
    let list = stdout_json(&first);
    let profiles = list["profiles"].as_array().expect("profile list");
    assert_eq!(profiles.len(), 5);

    let inspect = cli(
        &[
            "target",
            "inspect",
            "python-re-3.11-bytes",
            "--format",
            "json",
        ],
        "",
    );
    assert_eq!(inspect.status.code(), Some(0));
    let inspect = stdout_json(&inspect);
    assert_eq!(inspect["command"], "target.inspect");
    assert_eq!(
        inspect["profile_reference"]["profile_id"],
        "profile:python-re/3.11-bytes"
    );
    assert_eq!(
        inspect["profile_reference"]["profile_id"],
        inspect["profile"]["profile_id"]
    );
}

#[test]
fn usage_unavailable_and_human_diagnostic_exits_are_stable() {
    let duplicate = cli(&["compile", "--input", "-", "--input", "-"], SIMPLE_SOURCE);
    assert_eq!(duplicate.status.code(), Some(64));
    assert!(duplicate.stdout.is_empty());

    let ambiguous_raw = cli(&["compile", "--output", "semantic"], SEMANTIC_REQUEST);
    assert_eq!(ambiguous_raw.status.code(), Some(64));
    assert!(String::from_utf8_lossy(&ambiguous_raw.stderr)
        .contains("source-construction options require explicit --input"));

    let unavailable = cli(&["target", "inspect", "not-a-profile"], "");
    assert_eq!(unavailable.status.code(), Some(69));
    assert!(unavailable.stdout.is_empty());

    let directory = TestDirectory::new();
    let source_path = directory.path("broken.strl");
    fs::write(&source_path, "not semantic strling").unwrap();
    let checked = cli(&["check", "--input", source_path.to_str().unwrap()], "");
    assert_eq!(checked.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&checked.stdout).contains("Check failed."));
    assert!(String::from_utf8_lossy(&checked.stderr).contains("STRL-DSL-1001"));
}

#[test]
fn source_output_options_are_canonicalized_independently_of_flag_order() {
    let first = cli(
        &[
            "compile",
            "--input",
            "-",
            "--output",
            "target_artifact",
            "--output",
            "semantic",
            "--target",
            "pcre2-10.43",
        ],
        SIMPLE_SOURCE,
    );
    let second = cli(
        &[
            "compile",
            "--input",
            "-",
            "--target",
            "pcre2-10.43",
            "--output",
            "semantic",
            "--output",
            "target_artifact",
        ],
        SIMPLE_SOURCE,
    );

    assert_eq!(first.status.code(), Some(0));
    assert_eq!(second.status.code(), Some(0));
    assert_eq!(first.stdout, second.stdout);
    let result = stdout_json(&first);
    assert_eq!(result["outcome"], "succeeded");
    assert_eq!(result["artifact"]["pattern"]["text"], "a");
}

#[test]
fn retired_python_options_are_rejected_without_ambiguity() {
    let schema = cli(&["import", "--input", "-", "--schema", "legacy.json"], "a");
    assert_eq!(schema.status.code(), Some(64));
    assert!(String::from_utf8_lossy(&schema.stderr).contains("--schema is retired"));

    let emit = cli(&["import", "--input", "-", "--emit", "pcre2"], "a");
    assert_eq!(emit.status.code(), Some(64));
    assert!(String::from_utf8_lossy(&emit.stderr).contains("--emit is retired"));
}
