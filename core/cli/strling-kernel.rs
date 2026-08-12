//! Deterministic JSON transport for the canonical in-process compiler facade.

use std::env;
use std::fs::File;
use std::io::{self, Read, Write};
use std::process::ExitCode;

use strling_kernel::compile;
use strling_kernel::kernel::{MAX_REQUEST_CONTRACT_BYTES, MAX_TARGET_PROFILE_BYTES};
use strling_kernel::protocol::{CompileOutcome, CompileRequest};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::from_json;

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
    let target_profile_path = parse_args(env::args().skip(1))?;
    if target_profile_path.as_deref() == Some("") {
        print_help()?;
        return Ok(0);
    }

    let request_json = read_limited(
        io::stdin().lock(),
        MAX_REQUEST_CONTRACT_BYTES,
        "compile request",
    )?;
    let request: CompileRequest = from_json(&request_json)
        .map_err(|error| (EXIT_USAGE, format!("invalid compile request: {error}")))?;

    let target_profile = target_profile_path
        .as_deref()
        .map(read_target_profile)
        .transpose()?;
    let result = compile(&request, target_profile.as_ref())
        .map_err(|error| (EXIT_KERNEL, error.to_string()))?;

    let stdout = io::stdout();
    let mut output = stdout.lock();
    serde_json::to_writer(&mut output, &result)
        .map_err(|error| (EXIT_IO, format!("cannot encode compile result: {error}")))?;
    output
        .write_all(b"\n")
        .map_err(|error| (EXIT_IO, format!("cannot write compile result: {error}")))?;

    Ok(if result.outcome == CompileOutcome::Succeeded {
        0
    } else {
        EXIT_COMPILE_FAILED
    })
}

fn parse_args(args: impl Iterator<Item = String>) -> Result<Option<String>, (u8, String)> {
    let arguments: Vec<String> = args.collect();
    match arguments.as_slice() {
        [] => Ok(None),
        [flag] if flag == "--help" || flag == "-h" => Ok(Some(String::new())),
        [flag, path] if flag == "--target-profile" && !path.is_empty() => Ok(Some(path.clone())),
        _ => Err((
            EXIT_USAGE,
            "usage: strling-kernel [--target-profile PATH]".to_owned(),
        )),
    }
}

fn print_help() -> Result<(), (u8, String)> {
    let mut stdout = io::stdout().lock();
    stdout
        .write_all(
            b"Usage: strling compile [--target-profile PATH]\n\nRead one canonical CompileRequest JSON document from standard input and write one canonical CompileResult JSON document to standard output.\n",
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
