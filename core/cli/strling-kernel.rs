//! Deterministic JSON transport for the canonical in-process compiler facade.

use std::env;
use std::fs::File;
use std::io::{self, Read, Write};
use std::process::ExitCode;

use serde::Serialize;
use strling_kernel::kernel::{MAX_REQUEST_CONTRACT_BYTES, MAX_TARGET_PROFILE_BYTES};
use strling_kernel::protocol::{CompileOutcome, CompileRequest};
use strling_kernel::simply::{
    decode_simply_builder_request, replay_simply_builder_request, SimplyAdapterResponse,
    SimplyBuilderRequestDecodeError,
};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::from_json;
use strling_kernel::SIMPLY_PROTOCOL_VERSION;

const EXIT_COMPILE_FAILED: u8 = 2;
const EXIT_USAGE: u8 = 64;
const EXIT_KERNEL: u8 = 70;
const EXIT_IO: u8 = 74;

fn main() -> ExitCode {
    match run() {
        Ok(code) => ExitCode::from(code),
        Err((code, message)) => {
            eprintln!("strling-kernel: {message}");
            ExitCode::from(code)
        }
    }
}

fn run() -> Result<u8, (u8, String)> {
    let arguments = parse_args(env::args().skip(1))?;
    if arguments.mode == InputMode::Help {
        print_help()?;
        return Ok(0);
    }

    let label = match arguments.mode {
        InputMode::Compile => "compile request",
        InputMode::Simply => "Simply builder request",
        InputMode::Help => unreachable!("help returned before reading input"),
    };
    let request_json = read_limited(io::stdin().lock(), MAX_REQUEST_CONTRACT_BYTES, label)?;
    let target_profile = arguments
        .target_profile_path
        .as_deref()
        .map(read_target_profile)
        .transpose()?;

    match arguments.mode {
        InputMode::Compile => run_compile(&request_json, target_profile.as_ref()),
        InputMode::Simply => run_simply(&request_json, target_profile.as_ref()),
        InputMode::Help => unreachable!("help returned before dispatch"),
    }
}

fn run_compile(
    request_json: &str,
    target_profile: Option<&TargetProfile>,
) -> Result<u8, (u8, String)> {
    let request: CompileRequest = from_json(request_json)
        .map_err(|error| (EXIT_USAGE, format!("invalid compile request: {error}")))?;
    let result = strling_kernel::compile(&request, target_profile)
        .map_err(|error| (EXIT_KERNEL, error.to_string()))?;
    write_json(&result)?;
    Ok(compile_exit_code(result.outcome))
}

fn run_simply(
    request_json: &str,
    target_profile: Option<&TargetProfile>,
) -> Result<u8, (u8, String)> {
    let builder_request = match decode_simply_builder_request(request_json) {
        Ok(request) => request,
        Err(SimplyBuilderRequestDecodeError::Construction(errors)) => {
            write_json(&SimplyAdapterResponse::Failure {
                protocol_version: SIMPLY_PROTOCOL_VERSION.to_owned(),
                errors: errors.errors,
            })?;
            return Ok(EXIT_COMPILE_FAILED);
        }
        Err(SimplyBuilderRequestDecodeError::Malformed(message)) => {
            return Err((
                EXIT_USAGE,
                format!("invalid Simply builder request: {message}"),
            ));
        }
    };
    let request = match replay_simply_builder_request(builder_request) {
        Ok(request) => request,
        Err(errors) => {
            write_json(&SimplyAdapterResponse::Failure {
                protocol_version: SIMPLY_PROTOCOL_VERSION.to_owned(),
                errors: errors.errors,
            })?;
            return Ok(EXIT_COMPILE_FAILED);
        }
    };
    let result = strling_kernel::compile(&request, target_profile)
        .map_err(|error| (EXIT_KERNEL, error.to_string()))?;
    let outcome = result.outcome;
    write_json(&SimplyAdapterResponse::Success {
        protocol_version: SIMPLY_PROTOCOL_VERSION.to_owned(),
        compile_request: request,
        compile_result: result,
    })?;
    Ok(compile_exit_code(outcome))
}

fn write_json(value: &impl Serialize) -> Result<(), (u8, String)> {
    let stdout = io::stdout();
    let mut output = stdout.lock();
    serde_json::to_writer(&mut output, value)
        .map_err(|error| (EXIT_IO, format!("cannot encode JSON result: {error}")))?;
    output
        .write_all(b"\n")
        .map_err(|error| (EXIT_IO, format!("cannot write JSON result: {error}")))
}

const fn compile_exit_code(outcome: CompileOutcome) -> u8 {
    if matches!(outcome, CompileOutcome::Succeeded) {
        0
    } else {
        EXIT_COMPILE_FAILED
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum InputMode {
    Compile,
    Simply,
    Help,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct Arguments {
    mode: InputMode,
    target_profile_path: Option<String>,
}

fn parse_args(args: impl Iterator<Item = String>) -> Result<Arguments, (u8, String)> {
    let arguments: Vec<String> = args.collect();
    match arguments.as_slice() {
        [] => Ok(Arguments {
            mode: InputMode::Compile,
            target_profile_path: None,
        }),
        [flag] if flag == "--help" || flag == "-h" => Ok(Arguments {
            mode: InputMode::Help,
            target_profile_path: None,
        }),
        [flag] if flag == "--simply" => Ok(Arguments {
            mode: InputMode::Simply,
            target_profile_path: None,
        }),
        [flag, path] if flag == "--target-profile" && !path.is_empty() => Ok(Arguments {
            mode: InputMode::Compile,
            target_profile_path: Some(path.clone()),
        }),
        [mode, flag, path]
            if mode == "--simply" && flag == "--target-profile" && !path.is_empty() =>
        {
            Ok(Arguments {
                mode: InputMode::Simply,
                target_profile_path: Some(path.clone()),
            })
        }
        _ => Err((
            EXIT_USAGE,
            "usage: strling-kernel [--simply] [--target-profile PATH]".to_owned(),
        )),
    }
}

fn print_help() -> Result<(), (u8, String)> {
    let mut stdout = io::stdout().lock();
    stdout
        .write_all(
            b"Usage: strling compile [--target-profile PATH]\n       strling simply [--target-profile PATH]\n\nCompile reads one canonical CompileRequest and writes one CompileResult. Simply reads one Simply BuilderRequest and writes one adapter response containing the canonical request/result or stable construction errors.\n",
        )
        .map_err(|error| (EXIT_IO, format!("cannot write help: {error}")))
}

fn read_target_profile(path: &str) -> Result<TargetProfile, (u8, String)> {
    let file = File::open(path).map_err(|error| {
        (
            EXIT_IO,
            format!("cannot open target profile {path:?}: {error}"),
        )
    })?;
    let json = read_limited(file, MAX_TARGET_PROFILE_BYTES, "target profile")?;
    from_json(&json).map_err(|error| (EXIT_USAGE, format!("invalid target profile: {error}")))
}

fn read_limited(reader: impl Read, limit: usize, label: &str) -> Result<String, (u8, String)> {
    let byte_limit = u64::try_from(limit).map_err(|_| {
        (
            EXIT_KERNEL,
            format!("{label} byte limit is not representable"),
        )
    })?;
    let mut bytes = Vec::new();
    reader
        .take(byte_limit.saturating_add(1))
        .read_to_end(&mut bytes)
        .map_err(|error| (EXIT_IO, format!("cannot read {label}: {error}")))?;
    if bytes.len() > limit {
        return Err((
            EXIT_USAGE,
            format!("{label} exceeds the {limit}-byte transport limit"),
        ));
    }
    String::from_utf8(bytes)
        .map_err(|error| (EXIT_USAGE, format!("{label} is not UTF-8 JSON: {error}")))
}
