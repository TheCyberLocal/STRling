//! Deterministic command-line transport for the canonical compiler facade.

use std::collections::BTreeSet;
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::Path;
use std::process::ExitCode;

use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use strling_kernel::kernel::{MAX_REQUEST_CONTRACT_BYTES, MAX_TARGET_PROFILE_BYTES};
use strling_kernel::no_match_explanation::{explain_no_match, NoMatchExecutionMode, NoMatchLimits};
use strling_kernel::protocol::{CompileOutcome, CompileRequest};
use strling_kernel::semantic_conversion::{
    convert_semantic_program, SemanticConversionDestination, SemanticConversionOutput,
    SemanticConversionStatus,
};
use strling_kernel::simply::{
    decode_simply_builder_request, replay_simply_builder_request,
    supported_simply_protocol_version, SimplyAdapterResponse, SimplyBuilderRequestDecodeError,
};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::from_json;
use strling_kernel::{compile_with_evidence, KernelCompileOutput, SIMPLY_PROTOCOL_VERSION};

const CLI_CONTRACT_VERSION: &str = "1.0.0";
const SPECIFICATION_VERSION: &str = "1.0-draft.1";
const EXIT_COMPILE_FAILED: u8 = 2;
const EXIT_USAGE: u8 = 64;
const EXIT_UNAVAILABLE: u8 = 69;
const EXIT_KERNEL: u8 = 70;
const EXIT_IO: u8 = 74;

const PROFILE_FIXTURES: &[(&str, &str)] = &[
    (
        "ecmascript-2024",
        include_str!("../../spec/targets/profiles/ecmascript-2024.json"),
    ),
    (
        "pcre2-10.42",
        include_str!("../../spec/targets/profiles/pcre2-10.42.json"),
    ),
    (
        "pcre2-10.43",
        include_str!("../../spec/targets/profiles/pcre2-10.43.json"),
    ),
    (
        "python-re-3.11",
        include_str!("../../spec/targets/profiles/python-re-3.11.json"),
    ),
    (
        "python-re-3.11-bytes",
        include_str!("../../spec/targets/profiles/python-re-3.11-bytes.json"),
    ),
];

type CliResult<T> = Result<T, CliError>;

#[derive(Debug)]
struct CliError {
    code: u8,
    message: String,
}

impl CliError {
    fn new(code: u8, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }

    fn usage(message: impl Into<String>) -> Self {
        Self::new(EXIT_USAGE, message)
    }

    fn cancelled() -> Self {
        Self::new(0, String::new())
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(code) => ExitCode::from(code),
        Err(error) => {
            if !error.message.is_empty() {
                eprintln!("strling: {}", error.message);
            }
            ExitCode::from(error.code)
        }
    }
}

fn run() -> CliResult<u8> {
    let arguments = parse_args(env::args().skip(1))?;
    match arguments.command {
        Command::Help => {
            write_stdout(HELP.as_bytes())?;
            Ok(0)
        }
        Command::TargetList => run_target_list(arguments.format),
        Command::TargetInspect => run_target_inspect(&arguments),
        Command::Simply => run_simply(&arguments),
        Command::Compile
        | Command::Import
        | Command::Explain
        | Command::Migrate
        | Command::Check => run_semantic_command(&arguments),
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Command {
    Compile,
    Import,
    Explain,
    Migrate,
    Check,
    TargetList,
    TargetInspect,
    Simply,
    Help,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputFormat {
    Json,
    Human,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Frontend {
    Semantic,
    Regex,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum MigrationDestination {
    Semantic,
    Simply,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Arguments {
    command: Command,
    input: Option<String>,
    request: Option<String>,
    frontend: Option<Frontend>,
    source_id: Option<String>,
    specification_version: String,
    requested_outputs: Vec<String>,
    minimum_severity: String,
    partial_semantics: String,
    max_semantic_nodes: Option<u64>,
    max_diagnostics: Option<u64>,
    target_alias: Option<String>,
    target_profile_path: Option<String>,
    format: OutputFormat,
    output_file: Option<String>,
    subject: Option<String>,
    subject_file: Option<String>,
    no_match_limits: NoMatchLimits,
    migration_destination: MigrationDestination,
    inspect_selector: Option<String>,
}

impl Arguments {
    fn new(command: Command) -> Self {
        let format = match command {
            Command::Check | Command::TargetList | Command::TargetInspect => OutputFormat::Human,
            _ => OutputFormat::Json,
        };
        Self {
            command,
            input: None,
            request: None,
            frontend: None,
            source_id: None,
            specification_version: SPECIFICATION_VERSION.to_owned(),
            requested_outputs: Vec::new(),
            minimum_severity: "hint".to_owned(),
            partial_semantics: "forbid".to_owned(),
            max_semantic_nodes: None,
            max_diagnostics: None,
            target_alias: None,
            target_profile_path: None,
            format,
            output_file: None,
            subject: None,
            subject_file: None,
            no_match_limits: NoMatchLimits::default(),
            migration_destination: MigrationDestination::Semantic,
            inspect_selector: None,
        }
    }
}

fn parse_args(args: impl Iterator<Item = String>) -> CliResult<Arguments> {
    let mut values: Vec<String> = args.collect();
    if values.is_empty() {
        return Ok(Arguments::new(Command::Compile));
    }
    if values == ["--help"] || values == ["-h"] || values == ["help"] {
        return Ok(Arguments::new(Command::Help));
    }
    if values.first().is_some_and(|value| value == "--simply") {
        values[0] = "simply".to_owned();
    } else if values
        .first()
        .is_some_and(|value| value == "--target-profile")
    {
        values.insert(0, "compile".to_owned());
    }

    let (command, consumed) = match values.as_slice() {
        [first, ..] if first == "compile" => (Command::Compile, 1),
        [first, ..] if first == "import" => (Command::Import, 1),
        [first, ..] if first == "explain" => (Command::Explain, 1),
        [first, ..] if first == "migrate" => (Command::Migrate, 1),
        [first, ..] if first == "check" => (Command::Check, 1),
        [first, ..] if first == "simply" => (Command::Simply, 1),
        [first, second, ..] if first == "target" && second == "list" => (Command::TargetList, 2),
        [first, second, ..] if first == "target" && second == "inspect" => {
            (Command::TargetInspect, 2)
        }
        _ => return Err(CliError::usage(format!("unknown command; {SHORT_USAGE}"))),
    };
    let mut parsed = Arguments::new(command);
    let mut seen_options = BTreeSet::new();
    let mut index = consumed;
    while index < values.len() {
        let flag = values[index].as_str();
        if flag == "--help" || flag == "-h" {
            return Ok(Arguments::new(Command::Help));
        }
        if command == Command::TargetInspect && !flag.starts_with('-') {
            set_once(
                &mut parsed.inspect_selector,
                values[index].clone(),
                "target selector",
            )?;
            index += 1;
            continue;
        }
        if flag != "--output" && !seen_options.insert(flag.to_owned()) {
            return Err(CliError::usage(format!("duplicate {flag}")));
        }
        let value = |position: usize| -> CliResult<String> {
            values
                .get(position)
                .filter(|value| !value.is_empty())
                .cloned()
                .ok_or_else(|| CliError::usage(format!("{flag} requires a value")))
        };
        match flag {
            "--input" => {
                let next = value(index + 1)?;
                set_once(&mut parsed.input, next, flag)?;
                index += 2;
            }
            "--request" => {
                let next = value(index + 1)?;
                set_once(&mut parsed.request, next, flag)?;
                index += 2;
            }
            "--frontend" => {
                let next = value(index + 1)?;
                let frontend = match next.as_str() {
                    "semantic" | "strling.semantic" => Frontend::Semantic,
                    "regex" | "strling.regex-compat" => Frontend::Regex,
                    _ => return Err(CliError::usage("--frontend must be semantic or regex")),
                };
                set_once(&mut parsed.frontend, frontend, flag)?;
                index += 2;
            }
            "--source-id" => {
                let next = value(index + 1)?;
                set_once(&mut parsed.source_id, next, flag)?;
                index += 2;
            }
            "--specification-version" => {
                if parsed.specification_version != SPECIFICATION_VERSION {
                    return Err(CliError::usage("duplicate --specification-version"));
                }
                parsed.specification_version = value(index + 1)?;
                index += 2;
            }
            "--output" => {
                let next = value(index + 1)?;
                if !matches!(
                    next.as_str(),
                    "semantic" | "analysis" | "portability" | "target_artifact"
                ) {
                    return Err(CliError::usage(
                        "--output must be semantic, analysis, portability, or target_artifact",
                    ));
                }
                if parsed.requested_outputs.contains(&next) {
                    return Err(CliError::usage(format!("duplicate --output {next}")));
                }
                parsed.requested_outputs.push(next);
                index += 2;
            }
            "--minimum-severity" => {
                let next = value(index + 1)?;
                if !matches!(next.as_str(), "hint" | "info" | "warning" | "error") {
                    return Err(CliError::usage(
                        "--minimum-severity must be hint, info, warning, or error",
                    ));
                }
                if parsed.minimum_severity != "hint" {
                    return Err(CliError::usage("duplicate --minimum-severity"));
                }
                parsed.minimum_severity = next;
                index += 2;
            }
            "--partial-semantics" => {
                let next = value(index + 1)?;
                if !matches!(next.as_str(), "forbid" | "allow_for_diagnostics") {
                    return Err(CliError::usage(
                        "--partial-semantics must be forbid or allow_for_diagnostics",
                    ));
                }
                if parsed.partial_semantics != "forbid" {
                    return Err(CliError::usage("duplicate --partial-semantics"));
                }
                parsed.partial_semantics = next;
                index += 2;
            }
            "--max-semantic-nodes" => {
                let next = positive_u64(&value(index + 1)?, flag)?;
                set_once(&mut parsed.max_semantic_nodes, next, flag)?;
                index += 2;
            }
            "--max-diagnostics" => {
                let next = positive_u64(&value(index + 1)?, flag)?;
                set_once(&mut parsed.max_diagnostics, next, flag)?;
                index += 2;
            }
            "--target" => {
                let next = value(index + 1)?;
                set_once(&mut parsed.target_alias, next, flag)?;
                index += 2;
            }
            "--target-profile" => {
                let next = value(index + 1)?;
                set_once(&mut parsed.target_profile_path, next, flag)?;
                index += 2;
            }
            "--format" => {
                let next = value(index + 1)?;
                parsed.format = match next.as_str() {
                    "json" => OutputFormat::Json,
                    "human" => OutputFormat::Human,
                    _ => return Err(CliError::usage("--format must be json or human")),
                };
                index += 2;
            }
            "--output-file" => {
                let next = value(index + 1)?;
                set_once(&mut parsed.output_file, next, flag)?;
                index += 2;
            }
            "--subject" => {
                let next = value(index + 1)?;
                set_once(&mut parsed.subject, next, flag)?;
                index += 2;
            }
            "--subject-file" => {
                let next = value(index + 1)?;
                set_once(&mut parsed.subject_file, next, flag)?;
                index += 2;
            }
            "--max-subject-bytes" => {
                parsed.no_match_limits.max_subject_utf8_bytes =
                    positive_usize(&value(index + 1)?, flag)?;
                index += 2;
            }
            "--max-subject-scalars" => {
                parsed.no_match_limits.max_subject_unicode_scalars =
                    positive_usize(&value(index + 1)?, flag)?;
                index += 2;
            }
            "--max-steps" => {
                parsed.no_match_limits.max_steps = positive_u64(&value(index + 1)?, flag)?;
                index += 2;
            }
            "--max-depth" => {
                parsed.no_match_limits.max_depth = positive_usize(&value(index + 1)?, flag)?;
                index += 2;
            }
            "--max-branch-expansions" => {
                parsed.no_match_limits.max_branch_expansions =
                    positive_u64(&value(index + 1)?, flag)?;
                index += 2;
            }
            "--max-findings" => {
                parsed.no_match_limits.max_findings = positive_usize(&value(index + 1)?, flag)?;
                index += 2;
            }
            "--max-elapsed-milliseconds" => {
                parsed.no_match_limits.max_elapsed_milliseconds =
                    positive_u64(&value(index + 1)?, flag)?;
                index += 2;
            }
            "--to" => {
                let next = value(index + 1)?;
                parsed.migration_destination = match next.as_str() {
                    "semantic" | "semantic_strling" => MigrationDestination::Semantic,
                    "simply" | "simply_builder" => MigrationDestination::Simply,
                    _ => return Err(CliError::usage("--to must be semantic or simply")),
                };
                index += 2;
            }
            "--schema" => {
                return Err(CliError::usage(
                    "--schema is retired; canonical contract validation is mandatory",
                ));
            }
            "--emit" => {
                return Err(CliError::usage(
                    "--emit is retired; select an exact --target and --output target_artifact",
                ));
            }
            _ => return Err(CliError::usage(format!("unknown option {flag:?}"))),
        }
    }
    validate_arguments(&parsed)?;
    Ok(parsed)
}

fn set_once<T>(slot: &mut Option<T>, value: T, name: &str) -> CliResult<()> {
    if slot.is_some() {
        return Err(CliError::usage(format!("duplicate {name}")));
    }
    *slot = Some(value);
    Ok(())
}

fn positive_u64(value: &str, name: &str) -> CliResult<u64> {
    value
        .parse::<u64>()
        .ok()
        .filter(|value| *value > 0)
        .ok_or_else(|| CliError::usage(format!("{name} must be a positive integer")))
}

fn positive_usize(value: &str, name: &str) -> CliResult<usize> {
    value
        .parse::<usize>()
        .ok()
        .filter(|value| *value > 0)
        .ok_or_else(|| CliError::usage(format!("{name} must be a positive integer")))
}

fn validate_arguments(arguments: &Arguments) -> CliResult<()> {
    if arguments.input.is_some() && arguments.request.is_some() {
        return Err(CliError::usage(
            "--input and --request are mutually exclusive",
        ));
    }
    if arguments.target_alias.is_some() && arguments.target_profile_path.is_some() {
        return Err(CliError::usage(
            "--target and --target-profile are mutually exclusive",
        ));
    }
    if arguments.subject.is_some() && arguments.subject_file.is_some() {
        return Err(CliError::usage(
            "--subject and --subject-file are mutually exclusive",
        ));
    }
    if arguments.input.as_deref() == Some("-") && arguments.subject_file.as_deref() == Some("-") {
        return Err(CliError::usage(
            "source input and subject cannot both consume standard input",
        ));
    }

    let source_shaping = arguments.frontend.is_some()
        || arguments.source_id.is_some()
        || arguments.specification_version != SPECIFICATION_VERSION
        || !arguments.requested_outputs.is_empty()
        || arguments.minimum_severity != "hint"
        || arguments.partial_semantics != "forbid"
        || arguments.max_semantic_nodes.is_some()
        || arguments.max_diagnostics.is_some();
    if arguments.request.is_some() && source_shaping {
        return Err(CliError::usage(
            "canonical --request input cannot be combined with source-construction options",
        ));
    }

    match arguments.command {
        Command::Compile => {
            if arguments.input.is_none() && arguments.request.is_none() && source_shaping {
                return Err(CliError::usage(
                    "source-construction options require explicit --input",
                ));
            }
        }
        Command::Import => {
            if arguments.input.is_none() || arguments.request.is_some() {
                return Err(CliError::usage("import requires exactly one --input"));
            }
            if arguments
                .frontend
                .is_some_and(|value| value != Frontend::Regex)
            {
                return Err(CliError::usage("import always uses the regex frontend"));
            }
        }
        Command::Explain | Command::Migrate | Command::Check => {
            if arguments.input.is_none() && arguments.request.is_none() {
                return Err(CliError::usage(format!(
                    "{} requires --input or --request",
                    command_name(arguments.command)
                )));
            }
        }
        Command::Simply => {
            if arguments.input.is_some()
                || arguments.request.is_some()
                || source_shaping
                || arguments.output_file.is_some()
                || arguments.subject.is_some()
                || arguments.subject_file.is_some()
            {
                return Err(CliError::usage(
                    "simply accepts only --target, --target-profile, and --format json",
                ));
            }
            if arguments.format != OutputFormat::Json {
                return Err(CliError::usage("simply supports only --format json"));
            }
        }
        Command::TargetList => {
            if arguments.input.is_some()
                || arguments.request.is_some()
                || source_shaping
                || arguments.target_alias.is_some()
                || arguments.target_profile_path.is_some()
                || arguments.output_file.is_some()
            {
                return Err(CliError::usage("target list accepts only --format"));
            }
        }
        Command::TargetInspect => {
            let selectors = usize::from(arguments.inspect_selector.is_some())
                + usize::from(arguments.target_alias.is_some())
                + usize::from(arguments.target_profile_path.is_some());
            if selectors != 1 {
                return Err(CliError::usage(
                    "target inspect requires exactly one alias, --target, or --target-profile",
                ));
            }
            if arguments.input.is_some()
                || arguments.request.is_some()
                || source_shaping
                || arguments.output_file.is_some()
            {
                return Err(CliError::usage(
                    "target inspect accepts only a selector and --format",
                ));
            }
        }
        Command::Help => {}
    }
    if arguments.command != Command::Explain
        && (arguments.subject.is_some() || arguments.subject_file.is_some())
    {
        return Err(CliError::usage(
            "--subject and --subject-file are valid only for explain",
        ));
    }
    if arguments.command != Command::Migrate
        && arguments.migration_destination != MigrationDestination::Semantic
    {
        return Err(CliError::usage("--to is valid only for migrate"));
    }
    if arguments.output_file.is_some()
        && !matches!(
            arguments.command,
            Command::Compile | Command::Import | Command::Migrate
        )
    {
        return Err(CliError::usage(
            "--output-file is valid only for an artifact compile/import or exact migration",
        ));
    }
    Ok(())
}

fn run_semantic_command(arguments: &Arguments) -> CliResult<u8> {
    let target = resolve_selected_profile(arguments)?;
    let request = load_compile_request(arguments, target.as_ref())?;
    let output = compile_with_evidence(&request, target.as_ref())
        .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
    match arguments.command {
        Command::Compile | Command::Import | Command::Check => {
            run_compile_result(arguments, &output)
        }
        Command::Explain => run_explain(arguments, request, output),
        Command::Migrate => run_migrate(arguments, request, output),
        _ => unreachable!("semantic dispatch is closed"),
    }
}

fn load_compile_request(
    arguments: &Arguments,
    target: Option<&TargetProfile>,
) -> CliResult<CompileRequest> {
    if let Some(path) = &arguments.request {
        let json = read_path_or_stdin(path, MAX_REQUEST_CONTRACT_BYTES, "compile request")?;
        return from_json(&json)
            .map_err(|error| CliError::usage(format!("invalid compile request: {error}")));
    }
    if let Some(path) = &arguments.input {
        let text = read_path_or_stdin(path, MAX_REQUEST_CONTRACT_BYTES, "source input")?;
        return build_source_request(arguments, path, &text, target);
    }
    let json = read_limited(
        io::stdin().lock(),
        MAX_REQUEST_CONTRACT_BYTES,
        "compile request",
    )?;
    from_json(&json).map_err(|error| CliError::usage(format!("invalid compile request: {error}")))
}

fn build_source_request(
    arguments: &Arguments,
    path: &str,
    text: &str,
    target: Option<&TargetProfile>,
) -> CliResult<CompileRequest> {
    let frontend = if arguments.command == Command::Import {
        Frontend::Regex
    } else {
        arguments.frontend.unwrap_or(Frontend::Semantic)
    };
    let (frontend_id, dialect_version, media_type, provenance) = match frontend {
        Frontend::Semantic => (
            "strling.semantic",
            "1.0.0",
            "text/x-strling-semantic",
            "authored",
        ),
        Frontend::Regex => (
            "strling.regex-compat",
            "1.0.0",
            "text/x-strling-regex-compat",
            "imported",
        ),
    };
    let source_id = arguments
        .source_id
        .clone()
        .unwrap_or_else(|| content_source_id(text));
    let mut outputs = if arguments.requested_outputs.is_empty() {
        default_outputs(arguments.command)
    } else {
        arguments.requested_outputs.clone()
    };
    if matches!(
        arguments.command,
        Command::Import | Command::Explain | Command::Migrate
    ) && !outputs.iter().any(|output| output == "semantic")
    {
        outputs.push("semantic".to_owned());
    }
    if target.is_some()
        && !outputs
            .iter()
            .any(|output| matches!(output.as_str(), "portability" | "target_artifact"))
    {
        outputs.push("portability".to_owned());
    }
    outputs.sort_by_key(|output| match output.as_str() {
        "semantic" => 0,
        "analysis" => 1,
        "portability" => 2,
        "target_artifact" => 3,
        _ => unreachable!("requested output parser is closed"),
    });
    let target_reference = target
        .map(|profile| profile.reference())
        .transpose()
        .map_err(|error| CliError::usage(format!("invalid target profile: {error}")))?;
    let mut document = json!({
        "contract_version": "1.0.0",
        "source_id": source_id,
        "specification_version": arguments.specification_version,
        "frontend": {
            "id": frontend_id,
            "dialect_version": dialect_version
        },
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": media_type,
            "text": text
        },
        "provenance": { "kind": provenance }
    });
    if path != "-" {
        document["display_name"] = Value::String(path.to_owned());
    }
    let mut compiler_options = json!({
        "partial_semantics": arguments.partial_semantics,
        "diagnostic_policy": { "minimum_severity": arguments.minimum_severity }
    });
    if arguments.max_semantic_nodes.is_some() || arguments.max_diagnostics.is_some() {
        let mut limits = serde_json::Map::new();
        if let Some(value) = arguments.max_semantic_nodes {
            limits.insert("max_semantic_nodes".to_owned(), json!(value));
        }
        if let Some(value) = arguments.max_diagnostics {
            limits.insert("max_diagnostics".to_owned(), json!(value));
        }
        compiler_options["resource_limits"] = Value::Object(limits);
    }
    let mut request = json!({
        "contract_version": "1.0.0",
        "specification_version": arguments.specification_version,
        "input": { "kind": "source", "document": document },
        "requested_outputs": outputs,
        "compiler_options": compiler_options
    });
    if let Some(reference) = target_reference {
        request["target_profile"] = serde_json::to_value(reference)
            .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
    }
    from_json(&serde_json::to_string(&request).map_err(|error| {
        CliError::new(
            EXIT_KERNEL,
            format!("cannot encode compile request: {error}"),
        )
    })?)
    .map_err(|error| CliError::usage(format!("invalid source compile options: {error}")))
}

fn default_outputs(command: Command) -> Vec<String> {
    match command {
        Command::Import | Command::Migrate => vec!["semantic".to_owned()],
        _ => vec!["semantic".to_owned(), "analysis".to_owned()],
    }
}

fn run_compile_result(arguments: &Arguments, output: &KernelCompileOutput) -> CliResult<u8> {
    let exit = compile_exit_code(output.result.outcome);
    if let Some(path) = &arguments.output_file {
        if exit == 0 {
            let artifact = output.result.artifact.as_ref().ok_or_else(|| {
                CliError::usage(
                    "--output-file requires --output target_artifact and an exact target profile",
                )
            })?;
            write_new_file(Path::new(path), artifact.pattern.text.as_bytes())?;
        }
    }
    match arguments.format {
        OutputFormat::Json => write_json_stdout(&output.result)?,
        OutputFormat::Human => write_compile_human(arguments.command, &output.result)?,
    }
    Ok(exit)
}

fn run_explain(
    arguments: &Arguments,
    request: CompileRequest,
    output: KernelCompileOutput,
) -> CliResult<u8> {
    let Some(explanation) = output.explanation else {
        let response = json!({
            "cli_contract_version": CLI_CONTRACT_VERSION,
            "command": "explain",
            "status": "compile_failed",
            "compile_request": request,
            "compile_result": output.result
        });
        render_envelope(arguments.format, &response, "Explanation unavailable.")?;
        return Ok(EXIT_COMPILE_FAILED);
    };
    let no_match = load_subject(arguments)?.map(|subject| {
        let semantic = output
            .result
            .semantic_result
            .as_ref()
            .ok_or_else(|| CliError::new(EXIT_KERNEL, "explanation lacks semantic result"))?;
        explain_no_match(
            &semantic.program,
            &explanation,
            &subject,
            NoMatchExecutionMode::Search,
            arguments.no_match_limits,
        )
        .map_err(|error| CliError::usage(format!("invalid no-match request: {error}")))
    });
    let no_match = no_match.transpose()?;
    let mut response = json!({
        "cli_contract_version": CLI_CONTRACT_VERSION,
        "command": "explain",
        "status": "completed",
        "compile_request": request,
        "compile_result": output.result,
        "explanation": explanation
    });
    if let Some(no_match) = no_match {
        response["no_match"] = serde_json::to_value(no_match)
            .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
    }
    render_envelope(arguments.format, &response, "Explanation completed.")?;
    Ok(0)
}

fn run_migrate(
    arguments: &Arguments,
    request: CompileRequest,
    output: KernelCompileOutput,
) -> CliResult<u8> {
    let Some(semantic) = output.result.semantic_result.as_ref() else {
        let response = json!({
            "cli_contract_version": CLI_CONTRACT_VERSION,
            "command": "migrate",
            "status": "compile_failed",
            "compile_request": request,
            "compile_result": output.result
        });
        render_envelope(arguments.format, &response, "Migration unavailable.")?;
        return Ok(EXIT_COMPILE_FAILED);
    };
    let destination = match arguments.migration_destination {
        MigrationDestination::Semantic => SemanticConversionDestination::SemanticStrling,
        MigrationDestination::Simply => SemanticConversionDestination::SimplyBuilder,
    };
    let conversion =
        convert_semantic_program(&semantic.program, destination, output.explanation.as_ref())
            .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
    let exact = conversion.status == SemanticConversionStatus::Exact
        && output.result.outcome == CompileOutcome::Succeeded;
    if let Some(path) = &arguments.output_file {
        if exact {
            let bytes = conversion_output_bytes(&conversion.output)?;
            write_new_file(Path::new(path), &bytes)?;
        }
    }
    let response = json!({
        "cli_contract_version": CLI_CONTRACT_VERSION,
        "command": "migrate",
        "status": "completed",
        "compile_request": request,
        "compile_result": output.result,
        "conversion": conversion
    });
    match arguments.format {
        OutputFormat::Json => write_json_stdout(&response)?,
        OutputFormat::Human => {
            if exact {
                write_stdout(&conversion_output_bytes(&conversion.output)?)?;
            } else {
                write_stdout(b"Migration was not exact.\n")?;
            }
        }
    }
    Ok(if exact { 0 } else { EXIT_COMPILE_FAILED })
}

fn conversion_output_bytes(output: &Option<SemanticConversionOutput>) -> CliResult<Vec<u8>> {
    match output {
        Some(SemanticConversionOutput::SemanticStrling { text, .. }) => {
            let mut bytes = text.as_bytes().to_vec();
            if !bytes.ends_with(b"\n") {
                bytes.push(b'\n');
            }
            Ok(bytes)
        }
        Some(SemanticConversionOutput::SimplyBuilder { request, .. }) => {
            let mut bytes = serde_json::to_vec(request)
                .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
            bytes.push(b'\n');
            Ok(bytes)
        }
        None => Err(CliError::new(
            EXIT_KERNEL,
            "exact migration did not produce destination material",
        )),
    }
}

fn render_envelope(format: OutputFormat, value: &Value, human: &str) -> CliResult<()> {
    match format {
        OutputFormat::Json => write_json_stdout(value),
        OutputFormat::Human => {
            let mut line = human.as_bytes().to_vec();
            line.push(b'\n');
            write_stdout(&line)
        }
    }
}

fn load_subject(arguments: &Arguments) -> CliResult<Option<String>> {
    if let Some(subject) = &arguments.subject {
        return Ok(Some(subject.clone()));
    }
    arguments
        .subject_file
        .as_deref()
        .map(|path| {
            read_path_or_stdin(
                path,
                arguments.no_match_limits.max_subject_utf8_bytes,
                "subject",
            )
        })
        .transpose()
}

fn run_simply(arguments: &Arguments) -> CliResult<u8> {
    let request_json = read_limited(
        io::stdin().lock(),
        MAX_REQUEST_CONTRACT_BYTES,
        "Simply builder request",
    )?;
    let target = resolve_selected_profile(arguments)?;
    let response_protocol_version =
        supported_simply_protocol_version(&request_json).unwrap_or(SIMPLY_PROTOCOL_VERSION);
    let builder_request = match decode_simply_builder_request(&request_json) {
        Ok(request) => request,
        Err(SimplyBuilderRequestDecodeError::Construction(errors)) => {
            write_json_stdout(&SimplyAdapterResponse::Failure {
                protocol_version: response_protocol_version.to_owned(),
                errors: errors.errors,
            })?;
            return Ok(EXIT_COMPILE_FAILED);
        }
        Err(SimplyBuilderRequestDecodeError::Malformed(message)) => {
            return Err(CliError::usage(format!(
                "invalid Simply builder request: {message}"
            )));
        }
    };
    let response_protocol_version = builder_request.protocol_version().to_owned();
    let request = match replay_simply_builder_request(builder_request) {
        Ok(request) => request,
        Err(errors) => {
            write_json_stdout(&SimplyAdapterResponse::Failure {
                protocol_version: response_protocol_version,
                errors: errors.errors,
            })?;
            return Ok(EXIT_COMPILE_FAILED);
        }
    };
    let result = strling_kernel::compile(&request, target.as_ref())
        .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
    let outcome = result.outcome;
    write_json_stdout(&SimplyAdapterResponse::Success {
        protocol_version: response_protocol_version,
        compile_request: request,
        compile_result: result,
    })?;
    Ok(compile_exit_code(outcome))
}

fn run_target_list(format: OutputFormat) -> CliResult<u8> {
    let profiles = bundled_profiles()?;
    match format {
        OutputFormat::Json => {
            let references = profiles
                .iter()
                .map(|(_, profile)| profile.reference())
                .collect::<Result<Vec<_>, _>>()
                .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
            write_json_stdout(&json!({
                "cli_contract_version": CLI_CONTRACT_VERSION,
                "command": "target.list",
                "profiles": references
            }))?;
        }
        OutputFormat::Human => {
            let mut text = String::new();
            for (alias, profile) in profiles {
                let reference = profile
                    .reference()
                    .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
                text.push_str(&format!(
                    "{alias}\t{}\t{}\n",
                    reference.profile_id.as_str(),
                    reference.profile_version.as_str()
                ));
            }
            write_stdout(text.as_bytes())?;
        }
    }
    Ok(0)
}

fn run_target_inspect(arguments: &Arguments) -> CliResult<u8> {
    let profile = if let Some(path) = &arguments.target_profile_path {
        read_target_profile(path)?
    } else {
        let selector = arguments
            .target_alias
            .as_ref()
            .or(arguments.inspect_selector.as_ref())
            .expect("validated selector");
        if let Some(profile) = bundled_profile(selector)? {
            profile
        } else if Path::new(selector).is_file() {
            read_target_profile(selector)?
        } else {
            return Err(CliError::new(
                EXIT_UNAVAILABLE,
                format!("target profile {selector:?} is unavailable"),
            ));
        }
    };
    let reference = profile
        .reference()
        .map_err(|error| CliError::new(EXIT_KERNEL, error.to_string()))?;
    match arguments.format {
        OutputFormat::Json => write_json_stdout(&json!({
            "cli_contract_version": CLI_CONTRACT_VERSION,
            "command": "target.inspect",
            "profile_reference": reference,
            "profile": profile
        }))?,
        OutputFormat::Human => {
            let text = format!(
                "Profile: {}\nVersion: {}\nSHA-256: {}\nEngine: {}\n",
                reference.profile_id.as_str(),
                reference.profile_version.as_str(),
                reference.sha256.as_str(),
                profile.engine.id.as_str()
            );
            write_stdout(text.as_bytes())?;
        }
    }
    Ok(0)
}

fn resolve_selected_profile(arguments: &Arguments) -> CliResult<Option<TargetProfile>> {
    if let Some(alias) = &arguments.target_alias {
        return bundled_profile(alias)?.map(Some).ok_or_else(|| {
            CliError::new(
                EXIT_UNAVAILABLE,
                format!("bundled target profile {alias:?} is unavailable"),
            )
        });
    }
    arguments
        .target_profile_path
        .as_deref()
        .map(read_target_profile)
        .transpose()
}

fn bundled_profiles() -> CliResult<Vec<(&'static str, TargetProfile)>> {
    PROFILE_FIXTURES
        .iter()
        .map(|(alias, fixture)| {
            from_json(fixture)
                .map(|profile| (*alias, profile))
                .map_err(|error| {
                    CliError::new(
                        EXIT_KERNEL,
                        format!("bundled target profile {alias:?} is invalid: {error}"),
                    )
                })
        })
        .collect()
}

fn bundled_profile(alias: &str) -> CliResult<Option<TargetProfile>> {
    let Some((_, fixture)) = PROFILE_FIXTURES.iter().find(|(name, _)| *name == alias) else {
        return Ok(None);
    };
    from_json(fixture)
        .map(Some)
        .map_err(|error| CliError::new(EXIT_KERNEL, format!("invalid bundled profile: {error}")))
}

fn read_target_profile(path: &str) -> CliResult<TargetProfile> {
    let json = read_path(path, MAX_TARGET_PROFILE_BYTES, "target profile")?;
    from_json(&json).map_err(|error| CliError::usage(format!("invalid target profile: {error}")))
}

fn read_path_or_stdin(path: &str, limit: usize, label: &str) -> CliResult<String> {
    if path == "-" {
        read_limited(io::stdin().lock(), limit, label)
    } else {
        read_path(path, limit, label)
    }
}

fn read_path(path: &str, limit: usize, label: &str) -> CliResult<String> {
    let file = File::open(path).map_err(|error| {
        CliError::new(EXIT_IO, format!("cannot open {label} {path:?}: {error}"))
    })?;
    read_limited(file, limit, label)
}

fn read_limited(reader: impl Read, limit: usize, label: &str) -> CliResult<String> {
    let byte_limit = u64::try_from(limit).map_err(|_| {
        CliError::new(
            EXIT_KERNEL,
            format!("{label} byte limit is not representable"),
        )
    })?;
    let mut bytes = Vec::new();
    reader
        .take(byte_limit.saturating_add(1))
        .read_to_end(&mut bytes)
        .map_err(|error| CliError::new(EXIT_IO, format!("cannot read {label}: {error}")))?;
    if bytes.len() > limit {
        return Err(CliError::usage(format!(
            "{label} exceeds the {limit}-byte transport limit"
        )));
    }
    String::from_utf8(bytes)
        .map_err(|error| CliError::usage(format!("{label} is not UTF-8: {error}")))
}

fn content_source_id(text: &str) -> String {
    let digest = Sha256::digest(text.as_bytes());
    let mut hex = String::with_capacity(64);
    for byte in digest {
        use std::fmt::Write as _;
        let _ = write!(hex, "{byte:02x}");
    }
    format!("src:cli.{hex}")
}

fn write_json_stdout(value: &impl Serialize) -> CliResult<()> {
    let mut bytes = serde_json::to_vec(value)
        .map_err(|error| CliError::new(EXIT_KERNEL, format!("cannot encode JSON: {error}")))?;
    bytes.push(b'\n');
    write_stdout(&bytes)
}

fn write_stdout(bytes: &[u8]) -> CliResult<()> {
    let mut output = io::stdout().lock();
    match output.write_all(bytes) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == io::ErrorKind::BrokenPipe => Err(CliError::cancelled()),
        Err(error) => Err(CliError::new(
            EXIT_IO,
            format!("cannot write standard output: {error}"),
        )),
    }
}

fn write_stderr(bytes: &[u8]) -> CliResult<()> {
    io::stderr()
        .lock()
        .write_all(bytes)
        .map_err(|error| CliError::new(EXIT_IO, format!("cannot write diagnostics: {error}")))
}

fn write_compile_human(
    command: Command,
    result: &strling_kernel::protocol::CompileResult,
) -> CliResult<()> {
    let label = match command {
        Command::Check => "Check",
        Command::Import => "Import",
        _ => "Compilation",
    };
    let status = if result.outcome == CompileOutcome::Succeeded {
        "succeeded"
    } else {
        "failed"
    };
    write_stdout(format!("{label} {status}.\n").as_bytes())?;
    if !result.diagnostics.is_empty() {
        let mut diagnostics = String::new();
        for diagnostic in &result.diagnostics {
            diagnostics.push_str(&format!(
                "{}: {}\n",
                diagnostic.code.as_str(),
                diagnostic.message
            ));
        }
        write_stderr(diagnostics.as_bytes())?;
    }
    Ok(())
}

fn write_new_file(path: &Path, bytes: &[u8]) -> CliResult<()> {
    if path.exists() {
        return Err(CliError::new(
            EXIT_IO,
            format!("refusing to overwrite existing output {path:?}"),
        ));
    }
    let parent = path
        .parent()
        .filter(|value| !value.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| CliError::new(EXIT_IO, "output path requires a UTF-8 file name"))?;
    let mut temporary = None;
    for ordinal in 0..100_u32 {
        let candidate = parent.join(format!(
            ".{name}.strling-tmp-{}-{ordinal}",
            std::process::id()
        ));
        match OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&candidate)
        {
            Ok(file) => {
                temporary = Some((candidate, file));
                break;
            }
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {}
            Err(error) => {
                return Err(CliError::new(
                    EXIT_IO,
                    format!("cannot create output temporary file: {error}"),
                ));
            }
        }
    }
    let (temporary_path, mut file) = temporary
        .ok_or_else(|| CliError::new(EXIT_IO, "cannot reserve a unique output temporary file"))?;
    let write_result = (|| -> io::Result<()> {
        file.write_all(bytes)?;
        file.sync_all()?;
        drop(file);
        fs::hard_link(&temporary_path, path)?;
        fs::remove_file(&temporary_path)?;
        Ok(())
    })();
    if let Err(error) = write_result {
        let _ = fs::remove_file(&temporary_path);
        return Err(CliError::new(
            EXIT_IO,
            format!("cannot publish output {path:?}: {error}"),
        ));
    }
    Ok(())
}

const fn compile_exit_code(outcome: CompileOutcome) -> u8 {
    if matches!(outcome, CompileOutcome::Succeeded) {
        0
    } else {
        EXIT_COMPILE_FAILED
    }
}

const fn command_name(command: Command) -> &'static str {
    match command {
        Command::Compile => "compile",
        Command::Import => "import",
        Command::Explain => "explain",
        Command::Migrate => "migrate",
        Command::Check => "check",
        Command::TargetList => "target list",
        Command::TargetInspect => "target inspect",
        Command::Simply => "simply",
        Command::Help => "help",
    }
}

const SHORT_USAGE: &str = "usage: strling <compile|import|explain|migrate|check|target|simply>";

const HELP: &str = "Usage: strling <command> [options]\n\nProduct commands:\n  compile                         Compile a canonical request or Semantic STRling source\n  import                          Import regex-compatible source into canonical semantics\n  explain                         Return canonical semantic and optional no-match evidence\n  migrate                         Convert canonical semantics to Semantic STRling or Simply\n  check --input PATH|--request PATH  Check source through canonical compiler diagnostics\n  target list                     List exact bundled target profiles\n  target inspect PROFILE          Inspect one bundled alias or explicit profile path\n  simply                          Compile a Simply BuilderRequest through the canonical kernel\n\nCommon options:\n  --input PATH|-                  Read source shorthand from a file or standard input\n  --request PATH|-                Read a canonical CompileRequest from a file or standard input\n  --frontend semantic|regex       Select the explicit source frontend\n  --source-id ID                  Set canonical source identity (otherwise content-derived)\n  --output KIND                   Request semantic, analysis, portability, or target_artifact\n  --target ALIAS                  Select one exact bundled target profile\n  --target-profile PATH           Select one explicit target profile JSON file\n  --format json|human             Select structured or presentation output\n  --output-file PATH              Safely create exact artifact or migration material\n  --minimum-severity LEVEL        Set hint, info, warning, or error\n  --partial-semantics POLICY      Set forbid or allow_for_diagnostics\n  --max-semantic-nodes N          Set a positive canonical resource limit\n  --max-diagnostics N             Set a positive canonical resource limit\n\nExplain options:\n  --subject TEXT | --subject-file PATH|-\n\nMigrate options:\n  --to semantic|simply\n";
