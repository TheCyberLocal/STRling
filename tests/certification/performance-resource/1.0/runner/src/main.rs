use std::env;
use std::hint::black_box;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::Instant;

use serde_json::{json, Value};
use strling_interop::execute_bytes;
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::ecmascript_lowering::lower_ecmascript;
use strling_kernel::ecmascript_serialization::serialize_ecmascript;
use strling_kernel::editor_intelligence::{
    project as project_editor, EditorFrontend, EditorRequest, EDITOR_EVIDENCE_CONTRACT_VERSION,
};
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::protocol::CompileRequest;
use strling_kernel::python_re_lowering::lower_python_re;
use strling_kernel::python_re_serialization::serialize_python_re;
use strling_kernel::regex_frontend;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::semantic_frontend;
use strling_kernel::source::SourceDocument;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::TargetProfile;
use strling_kernel::target_lowering::lower_pcre2;
use strling_kernel::target_serialization::serialize_pcre2;
use strling_kernel::validation::Validate;

type RunResult<T> = Result<T, String>;
type PreparedOperation = Box<dyn Fn() -> RunResult<usize>>;

const RUNNER_VERSION: &str = "1.0.0";

#[derive(Debug)]
struct Arguments {
    operation: String,
    fixture: String,
    warmups: usize,
    samples: usize,
    batch_iterations: Option<usize>,
    minimum_sample_nanoseconds: Option<u64>,
    maximum_batch_iterations: usize,
    expected_logical_cpu: Option<usize>,
    kernel_bin: Option<PathBuf>,
    ping: bool,
}

#[derive(Clone)]
struct MaterializedFixture {
    id: String,
    source: Option<String>,
    source_document: Option<SourceDocument>,
    semantic: SemanticProgram,
    request: CompileRequest,
    request_bytes: Vec<u8>,
    interop_request: Vec<u8>,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("strling-performance-runner: {error}");
        std::process::exit(1);
    }
}

fn run() -> RunResult<()> {
    let arguments = parse_arguments()?;
    if arguments.ping {
        println!(
            "{}",
            json!({"runner_version": RUNNER_VERSION, "status": "passed"})
        );
        return Ok(());
    }
    if arguments.warmups == 0 || arguments.samples == 0 {
        return Err("warmups and samples must be positive".to_owned());
    }
    let effective_cpu_affinity = match arguments.expected_logical_cpu {
        Some(expected) => {
            let effective = effective_cpu_affinity()?;
            if effective != [expected] {
                return Err(format!(
                    "effective CPU affinity {} does not equal expected logical CPU {expected}",
                    format_cpu_set(&effective)
                ));
            }
            effective
        }
        None => Vec::new(),
    };
    let fixture = materialize_fixture(&arguments.fixture)?;
    let operation = prepare_operation(
        &arguments.operation,
        &fixture,
        arguments.kernel_bin.as_deref(),
    )?;
    let batch_iterations = match (
        arguments.batch_iterations,
        arguments.minimum_sample_nanoseconds,
    ) {
        (Some(batch_iterations), None) => batch_iterations,
        (None, Some(minimum_sample_nanoseconds)) => select_batch_iterations(
            &operation,
            minimum_sample_nanoseconds,
            arguments.maximum_batch_iterations,
        )?,
        (None, None) => 1,
        (Some(_), Some(_)) => {
            return Err(
                "--batch-iterations and --minimum-sample-nanoseconds are mutually exclusive"
                    .to_owned(),
            )
        }
    };
    if batch_iterations == 0 || batch_iterations > arguments.maximum_batch_iterations {
        return Err("batch iterations are outside the governed range".to_owned());
    }
    for _ in 0..arguments.warmups {
        black_box(execute_batch(&operation, batch_iterations)?);
    }
    let mut samples = Vec::with_capacity(arguments.samples);
    let mut batch_elapsed_samples = Vec::with_capacity(arguments.samples);
    let mut checksum = 0usize;
    for _ in 0..arguments.samples {
        let started = Instant::now();
        checksum ^= black_box(execute_batch(&operation, batch_iterations)?);
        let nanoseconds = started.elapsed().as_nanos().max(1);
        let batch_elapsed = u64::try_from(nanoseconds).map_err(|_| "sample overflow")?;
        let divisor = u64::try_from(batch_iterations).map_err(|_| "batch overflow")?;
        let normalized = batch_elapsed
            .saturating_add(divisor / 2)
            .checked_div(divisor)
            .ok_or_else(|| "batch divisor is zero".to_owned())?
            .max(1);
        batch_elapsed_samples.push(batch_elapsed);
        samples.push(normalized);
    }
    println!(
        "{}",
        serde_json::to_string(&json!({
            "runner_version": RUNNER_VERSION,
            "operation_id": arguments.operation,
            "fixture_id": fixture.id,
            "unit": "nanoseconds",
            "warmup_iterations": arguments.warmups,
            "sample_iterations": arguments.samples,
            "batch_iterations": batch_iterations,
            "selected_logical_cpu": arguments.expected_logical_cpu,
            "effective_cpu_affinity": effective_cpu_affinity,
            "effective_cpuset": format_cpu_set(&effective_cpu_affinity),
            "batch_elapsed_samples": batch_elapsed_samples,
            "samples": samples,
            "checksum": checksum,
        }))
        .map_err(|error| error.to_string())?
    );
    Ok(())
}

fn parse_arguments() -> RunResult<Arguments> {
    let values = env::args().skip(1).collect::<Vec<_>>();
    if values == ["--ping"] {
        return Ok(Arguments {
            operation: String::new(),
            fixture: String::new(),
            warmups: 1,
            samples: 1,
            batch_iterations: None,
            minimum_sample_nanoseconds: None,
            maximum_batch_iterations: 1,
            expected_logical_cpu: None,
            kernel_bin: None,
            ping: true,
        });
    }
    let mut operation = None;
    let mut fixture = None;
    let mut warmups = None;
    let mut samples = None;
    let mut batch_iterations = None;
    let mut minimum_sample_nanoseconds = None;
    let mut maximum_batch_iterations = None;
    let mut expected_logical_cpu = None;
    let mut kernel_bin = None;
    let mut index = 0;
    while index < values.len() {
        let flag = &values[index];
        let value = values
            .get(index + 1)
            .ok_or_else(|| format!("missing value for {flag}"))?;
        match flag.as_str() {
            "--operation" => operation = Some(value.clone()),
            "--fixture" => fixture = Some(value.clone()),
            "--warmups" => warmups = Some(value.parse().map_err(|_| "invalid --warmups")?),
            "--samples" => samples = Some(value.parse().map_err(|_| "invalid --samples")?),
            "--batch-iterations" => {
                batch_iterations = Some(value.parse().map_err(|_| "invalid --batch-iterations")?)
            }
            "--minimum-sample-nanoseconds" => {
                minimum_sample_nanoseconds = Some(
                    value
                        .parse()
                        .map_err(|_| "invalid --minimum-sample-nanoseconds")?,
                )
            }
            "--maximum-batch-iterations" => {
                maximum_batch_iterations = Some(
                    value
                        .parse()
                        .map_err(|_| "invalid --maximum-batch-iterations")?,
                )
            }
            "--expected-logical-cpu" => {
                expected_logical_cpu = Some(
                    value
                        .parse()
                        .map_err(|_| "invalid --expected-logical-cpu")?,
                )
            }
            "--kernel-bin" => kernel_bin = Some(PathBuf::from(value)),
            _ => return Err(format!("unknown argument {flag}")),
        }
        index += 2;
    }
    Ok(Arguments {
        operation: operation.ok_or_else(|| "missing --operation".to_owned())?,
        fixture: fixture.ok_or_else(|| "missing --fixture".to_owned())?,
        warmups: warmups.ok_or_else(|| "missing --warmups".to_owned())?,
        samples: samples.ok_or_else(|| "missing --samples".to_owned())?,
        batch_iterations,
        minimum_sample_nanoseconds,
        maximum_batch_iterations: maximum_batch_iterations.unwrap_or(1),
        expected_logical_cpu,
        kernel_bin,
        ping: false,
    })
}

fn effective_cpu_affinity() -> RunResult<Vec<usize>> {
    if !cfg!(target_os = "linux") {
        return Err("governed CPU affinity is available only on Linux".to_owned());
    }
    let status = std::fs::read_to_string("/proc/self/status")
        .map_err(|error| format!("read /proc/self/status: {error}"))?;
    let value = status
        .lines()
        .find_map(|line| line.strip_prefix("Cpus_allowed_list:"))
        .ok_or_else(|| "Cpus_allowed_list is absent from /proc/self/status".to_owned())?;
    parse_cpu_set(value.trim())
}

fn parse_cpu_set(value: &str) -> RunResult<Vec<usize>> {
    if value.is_empty() {
        return Ok(Vec::new());
    }
    let mut cpus = Vec::new();
    for part in value.split(',') {
        let mut bounds = part.split('-');
        let start = bounds
            .next()
            .ok_or_else(|| "CPU range is empty".to_owned())?
            .parse::<usize>()
            .map_err(|_| format!("invalid CPU range {part}"))?;
        let end = bounds
            .next()
            .map(|bound| {
                bound
                    .parse::<usize>()
                    .map_err(|_| format!("invalid CPU range {part}"))
            })
            .transpose()?
            .unwrap_or(start);
        if bounds.next().is_some() || end < start {
            return Err(format!("invalid CPU range {part}"));
        }
        cpus.extend(start..=end);
    }
    cpus.sort_unstable();
    cpus.dedup();
    Ok(cpus)
}

fn format_cpu_set(cpus: &[usize]) -> String {
    cpus.iter()
        .map(usize::to_string)
        .collect::<Vec<_>>()
        .join(",")
}

fn execute_batch(operation: &PreparedOperation, iterations: usize) -> RunResult<usize> {
    let mut checksum = 0usize;
    for iteration in 0..iterations {
        checksum ^= black_box(operation()?).rotate_left((iteration % usize::BITS as usize) as u32);
    }
    Ok(checksum)
}

fn select_batch_iterations(
    operation: &PreparedOperation,
    minimum_sample_nanoseconds: u64,
    maximum_batch_iterations: usize,
) -> RunResult<usize> {
    if minimum_sample_nanoseconds == 0 || maximum_batch_iterations == 0 {
        return Err("batch selection bounds must be positive".to_owned());
    }
    let mut iterations = 1usize;
    loop {
        let started = Instant::now();
        black_box(execute_batch(operation, iterations)?);
        let elapsed = started.elapsed().as_nanos().max(1);
        if elapsed >= u128::from(minimum_sample_nanoseconds) {
            return Ok(iterations);
        }
        if iterations == maximum_batch_iterations {
            return Ok(iterations);
        }
        let target = u128::from(minimum_sample_nanoseconds);
        let proportional = (iterations as u128)
            .saturating_mul(target)
            .saturating_add(elapsed - 1)
            / elapsed;
        let proposed = proportional.max((iterations + 1) as u128);
        iterations = usize::try_from(proposed)
            .unwrap_or(maximum_batch_iterations)
            .min(maximum_batch_iterations);
    }
}

fn repository_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../../..")
        .canonicalize()
        .expect("repository root")
}

fn target_profile(file: &str) -> RunResult<TargetProfile> {
    let path = repository_root().join("spec/targets/profiles").join(file);
    let source = std::fs::read_to_string(&path)
        .map_err(|error| format!("read {}: {error}", path.display()))?;
    serde_json::from_str(&source).map_err(|error| format!("parse {}: {error}", path.display()))
}

fn semantic_document(source: &str) -> RunResult<SourceDocument> {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": "src:performance.semantic",
        "specification_version": "1.0-draft.1",
        "frontend": {"id": "strling.semantic", "dialect_version": "1.0.0"},
        "display_name": "performance.strling",
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": "text/x-strling-semantic",
            "text": source,
        },
        "provenance": {"kind": "authored", "description": "governed performance fixture"},
    }))
    .map_err(|error| error.to_string())
}

fn legacy_document(source: &str) -> RunResult<SourceDocument> {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": "src:performance.legacy",
        "specification_version": "1.0-draft.1",
        "frontend": {"id": "strling.regex-compat", "dialect_version": "1.0.0"},
        "display_name": "performance.regex",
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": "text/strling-regex",
            "text": source,
        },
        "provenance": {"kind": "imported"},
    }))
    .map_err(|error| error.to_string())
}

fn semantic_source(fixture: &str) -> RunResult<String> {
    let pattern = match fixture {
        "fixture:semantic-tiny" => "text \"a\";".to_owned(),
        "fixture:semantic-common" => {
            let mut items = Vec::new();
            for index in 0..12 {
                if index % 3 == 0 {
                    items.push("any character excluding line terminators;".to_owned());
                } else {
                    items.push(format!("text \"item-{index}\";"));
                }
            }
            format!("sequence {{ {} }}", items.join(" "))
        }
        "fixture:semantic-large" => {
            let items = (0..2048)
                .map(|index| {
                    if index % 2 == 0 {
                        format!("text \"item-{index:04}-xxxxxx\";")
                    } else {
                        "any character excluding line terminators;".to_owned()
                    }
                })
                .collect::<Vec<_>>();
            format!("sequence {{ {} }}", items.join(" "))
        }
        "fixture:semantic-pathological" => {
            let mut node = "text \"z\";".to_owned();
            for _ in 0..127 {
                node = format!("without backtracking {{ {node} }}");
            }
            node
        }
        _ => return Err(format!("{fixture} is not a semantic fixture")),
    };
    Ok(format!(
        "semantic strling 1.0;\ncase sensitive;\npattern {pattern}\n"
    ))
}

fn legacy_source(fixture: &str) -> RunResult<String> {
    match fixture {
        "fixture:legacy-tiny" => Ok("a".to_owned()),
        "fixture:legacy-common" => Ok("(?<word>[A-Za-z]{1,32})-(cat|dog|bird)".to_owned()),
        "fixture:legacy-large" => Ok((0..2048)
            .map(|index| format!("item{index:04}xxxx"))
            .collect::<Vec<_>>()
            .join("|")),
        _ => Err(format!("{fixture} is not a legacy fixture")),
    }
}

fn literal(index: usize) -> Value {
    json!({
        "node_id": format!("node:performance.literal-{index}"),
        "kind": "literal",
        "text": format!("v{index:04}"),
    })
}

fn ascii_digit(index: usize) -> Value {
    json!({
        "node_id": format!("node:performance.set-{index}"),
        "kind": "character_set",
        "negated": false,
        "members": [{"kind": "builtin", "name": "digit", "domain": "ascii", "negated": false}],
    })
}

fn simply_program(fixture: &str) -> RunResult<SemanticProgram> {
    let (nodes, requirements) = match fixture {
        "fixture:simply-tiny" => (1, 0),
        "fixture:simply-common" => (32, 8),
        "fixture:simply-large" => (4096, 1024),
        _ => return Err(format!("{fixture} is not a Simply fixture")),
    };
    let root = if nodes == 1 {
        literal(0)
    } else {
        let requirement_interval = if requirements == 0 {
            usize::MAX
        } else {
            nodes / requirements
        };
        let items = (0..nodes)
            .map(|index| {
                if index % requirement_interval == 0 {
                    ascii_digit(index)
                } else {
                    literal(index)
                }
            })
            .collect::<Vec<_>>();
        json!({
            "node_id": "node:performance.root",
            "kind": "sequence",
            "items": items,
        })
    };
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root,
    }))
    .map_err(|error| error.to_string())
}

fn compile_request(program: &SemanticProgram) -> RunResult<CompileRequest> {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": {"kind": "semantic", "program": program},
        "requested_outputs": ["semantic", "analysis"],
        "compiler_options": {
            "partial_semantics": "forbid",
            "diagnostic_policy": {"minimum_severity": "warning"},
        },
    }))
    .map_err(|error| error.to_string())
}

fn interop_request(request: &CompileRequest) -> RunResult<Vec<u8>> {
    serde_json::to_vec(&json!({
        "interop_protocol_version": "1.0.0",
        "operation": "compile",
        "payload": {"compile_request": request},
    }))
    .map_err(|error| error.to_string())
}

fn materialize_fixture(fixture: &str) -> RunResult<MaterializedFixture> {
    let (source, source_document, semantic) = if fixture.starts_with("fixture:semantic-") {
        let source = semantic_source(fixture)?;
        let document = semantic_document(&source)?;
        let semantic = semantic_frontend::parse(&document)
            .map_err(|error| error.to_string())?
            .program;
        (Some(source), Some(document), semantic)
    } else if fixture.starts_with("fixture:legacy-") {
        let source = legacy_source(fixture)?;
        let document = legacy_document(&source)?;
        let semantic = regex_frontend::parse(&document)
            .map_err(|error| error.to_string())?
            .program;
        (Some(source), Some(document), semantic)
    } else if fixture.starts_with("fixture:simply-") {
        let generated = simply_program(fixture)?;
        let semantic = normalize(&generated).map_err(|errors| format!("{errors:?}"))?;
        (None, None, semantic)
    } else if fixture == "fixture:protocol-common" {
        let generated = simply_program("fixture:simply-common")?;
        let semantic = normalize(&generated).map_err(|errors| format!("{errors:?}"))?;
        (None, None, semantic)
    } else {
        return Err(format!(
            "fixture {fixture} is not executable by the benchmark runner"
        ));
    };
    let request = compile_request(&semantic)?;
    let request_bytes = serde_json::to_vec(&request).map_err(|error| error.to_string())?;
    let interop_request = interop_request(&request)?;
    Ok(MaterializedFixture {
        id: fixture.to_owned(),
        source,
        source_document,
        semantic,
        request,
        request_bytes,
        interop_request,
    })
}

fn prepared_target_operation(
    fixture: &MaterializedFixture,
    profile_file: &str,
    target: &str,
) -> RunResult<PreparedOperation> {
    let semantic = fixture.semantic.clone();
    let foundational = analyze(&semantic).map_err(|error| error.to_string())?;
    let structural =
        analyze_structure(&semantic, &foundational).map_err(|error| error.to_string())?;
    let profile = target_profile(profile_file)?;
    let evaluation = evaluate_capabilities(&semantic, &foundational, &structural, &profile)
        .map_err(|error| error.to_string())?;
    let plan = plan_portability(&semantic, &foundational, &structural, &profile, &evaluation)
        .map_err(|error| error.to_string())?;
    match target {
        "pcre2" => Ok(Box::new(move || {
            let lowered =
                lower_pcre2(&semantic, &profile, &plan).map_err(|error| error.to_string())?;
            let artifact = serialize_pcre2(&lowered).map_err(|error| error.to_string())?;
            Ok(artifact.pattern.text.len())
        })),
        "ecmascript" => Ok(Box::new(move || {
            let lowered =
                lower_ecmascript(&semantic, &profile, &plan).map_err(|error| error.to_string())?;
            let artifact = serialize_ecmascript(&lowered).map_err(|error| error.to_string())?;
            Ok(artifact.pattern.text.len())
        })),
        "python-re" => Ok(Box::new(move || {
            let lowered =
                lower_python_re(&semantic, &profile, &plan).map_err(|error| error.to_string())?;
            let artifact = serialize_python_re(&lowered).map_err(|error| error.to_string())?;
            Ok(artifact.pattern.text.len())
        })),
        _ => Err(format!("unsupported target operation {target}")),
    }
}

fn prepare_cli_operation(
    fixture: &MaterializedFixture,
    kernel_bin: Option<&Path>,
) -> RunResult<PreparedOperation> {
    let executable = kernel_bin
        .ok_or_else(|| "latency:cli-startup requires --kernel-bin".to_owned())?
        .to_owned();
    if !executable.is_file() {
        return Err(format!(
            "kernel executable is absent: {}",
            executable.display()
        ));
    }
    let (arguments, input) = if let Some(source) = &fixture.source {
        if fixture.id.starts_with("fixture:semantic-") {
            (
                vec![
                    "check",
                    "--input",
                    "-",
                    "--frontend",
                    "semantic",
                    "--format",
                    "json",
                ],
                source.as_bytes().to_vec(),
            )
        } else {
            (
                vec![
                    "check",
                    "--input",
                    "-",
                    "--frontend",
                    "regex",
                    "--format",
                    "json",
                ],
                source.as_bytes().to_vec(),
            )
        }
    } else {
        (
            vec!["check", "--request", "-", "--format", "json"],
            fixture.request_bytes.clone(),
        )
    };
    Ok(Box::new(move || {
        let mut child = Command::new(&executable)
            .args(&arguments)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| error.to_string())?;
        child
            .stdin
            .take()
            .ok_or_else(|| "CLI stdin unavailable".to_owned())?
            .write_all(&input)
            .map_err(|error| error.to_string())?;
        let output = child
            .wait_with_output()
            .map_err(|error| error.to_string())?;
        if !output.status.success() {
            return Err(format!(
                "CLI failed with {}: {}",
                output.status,
                String::from_utf8_lossy(&output.stderr)
            ));
        }
        Ok(output.stdout.len())
    }))
}

fn prepare_operation(
    operation: &str,
    fixture: &MaterializedFixture,
    kernel_bin: Option<&Path>,
) -> RunResult<PreparedOperation> {
    match operation {
        "latency:semantic-parse" => {
            let document = fixture
                .source_document
                .clone()
                .ok_or_else(|| "semantic parse requires a source document".to_owned())?;
            Ok(Box::new(move || {
                let parsed =
                    semantic_frontend::parse(&document).map_err(|error| error.to_string())?;
                Ok(parsed.program.root.node_id().as_str().len())
            }))
        }
        "latency:legacy-import" => {
            let document = fixture
                .source_document
                .clone()
                .ok_or_else(|| "legacy import requires a source document".to_owned())?;
            Ok(Box::new(move || {
                let parsed = regex_frontend::parse(&document).map_err(|error| error.to_string())?;
                Ok(parsed.program.root.node_id().as_str().len())
            }))
        }
        "latency:kernel-request" => {
            let bytes = fixture.request_bytes.clone();
            Ok(Box::new(move || {
                let request: CompileRequest =
                    serde_json::from_slice(&bytes).map_err(|error| error.to_string())?;
                request.validate().map_err(|errors| format!("{errors:?}"))?;
                Ok(request.requested_outputs.len())
            }))
        }
        "latency:normalization" => {
            let semantic = fixture.semantic.clone();
            Ok(Box::new(move || {
                let normalized = normalize(&semantic).map_err(|errors| errors.to_string())?;
                Ok(normalized.root.node_id().as_str().len())
            }))
        }
        "latency:semantic-analysis" => {
            let semantic = fixture.semantic.clone();
            Ok(Box::new(move || {
                let facts = analyze(&semantic).map_err(|errors| errors.to_string())?;
                Ok(facts.len())
            }))
        }
        "latency:structural-safety" => {
            let semantic = fixture.semantic.clone();
            let foundational = analyze(&semantic).map_err(|errors| errors.to_string())?;
            Ok(Box::new(move || {
                let structural = analyze_structure(&semantic, &foundational)
                    .map_err(|errors| errors.to_string())?;
                let safety = analyze_safety(&semantic, &foundational, &structural)
                    .map_err(|errors| errors.to_string())?;
                let finding_count = safety.findings().len();
                Ok(structural.len() ^ finding_count)
            }))
        }
        "latency:capability-portability" => {
            let semantic = fixture.semantic.clone();
            let foundational = analyze(&semantic).map_err(|errors| errors.to_string())?;
            let structural =
                analyze_structure(&semantic, &foundational).map_err(|errors| errors.to_string())?;
            let profile = target_profile("pcre2-10.43.json")?;
            Ok(Box::new(move || {
                let evaluation =
                    evaluate_capabilities(&semantic, &foundational, &structural, &profile)
                        .map_err(|errors| errors.to_string())?;
                let plan =
                    plan_portability(&semantic, &foundational, &structural, &profile, &evaluation)
                        .map_err(|errors| errors.to_string())?;
                Ok(plan.decisions.len())
            }))
        }
        "latency:pcre2-lower-serialize" => {
            prepared_target_operation(fixture, "pcre2-10.43.json", "pcre2")
        }
        "latency:ecmascript-lower-serialize" => {
            prepared_target_operation(fixture, "ecmascript-2024.json", "ecmascript")
        }
        "latency:python-re-lower-serialize" => {
            prepared_target_operation(fixture, "python-re-3.11.json", "python-re")
        }
        "latency:end-to-end" | "memory:kernel-peak-rss" => {
            let request = fixture.request.clone();
            Ok(Box::new(move || {
                let result =
                    strling_kernel::compile(&request, None).map_err(|error| error.to_string())?;
                serde_json::to_vec(&result)
                    .map(|bytes| bytes.len())
                    .map_err(|error| error.to_string())
            }))
        }
        "latency:cli-startup" => prepare_cli_operation(fixture, kernel_bin),
        "latency:editor-interaction" => {
            let source = fixture
                .source
                .clone()
                .ok_or_else(|| "editor interaction requires source text".to_owned())?;
            let request = EditorRequest {
                contract_version: EDITOR_EVIDENCE_CONTRACT_VERSION.to_owned(),
                source_id: "src:performance.editor".to_owned(),
                frontend: if fixture.id.starts_with("fixture:legacy-") {
                    EditorFrontend::Regex
                } else {
                    EditorFrontend::Semantic
                },
                cursor_byte: Some(source.len()),
                source,
            };
            Ok(Box::new(move || {
                let evidence = project_editor(&request).map_err(|error| error.to_string())?;
                Ok(evidence.tokens.len()
                    ^ evidence.completions.len()
                    ^ evidence.symbols.len()
                    ^ evidence.rewrite_actions.len())
            }))
        }
        "latency:interop-roundtrip" => {
            let bytes = fixture.interop_request.clone();
            Ok(Box::new(move || Ok(execute_bytes(&bytes).len())))
        }
        "latency:supported-host-overhead" => {
            let request = fixture.request.clone();
            Ok(Box::new(move || {
                let result =
                    strling_host::compile(&request, None).map_err(|error| error.to_string())?;
                serde_json::to_vec(&result)
                    .map(|bytes| bytes.len())
                    .map_err(|error| error.to_string())
            }))
        }
        other => Err(format!("unsupported runner operation {other}")),
    }
}

#[cfg(test)]
mod affinity_tests {
    use super::{format_cpu_set, parse_cpu_set};

    #[test]
    fn cpu_sets_are_parsed_and_rendered_deterministically() {
        assert_eq!(parse_cpu_set("0-2,5,7-8").unwrap(), vec![0, 1, 2, 5, 7, 8]);
        assert_eq!(format_cpu_set(&[20]), "20");
        assert!(parse_cpu_set("4-2").is_err());
    }
}
