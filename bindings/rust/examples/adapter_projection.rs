use std::env;
use std::fs;
use std::process::ExitCode;

use strling::simply::{
    decode_simply_builder_request, replay_simply_builder_request, SimplyAdapterResponse,
};
use strling::{compile, CompileRequest, TargetProfile};

fn read(path: &str) -> Result<String, String> {
    fs::read_to_string(path).map_err(|error| format!("cannot read {path}: {error}"))
}

fn profile(path: Option<&String>) -> Result<Option<TargetProfile>, String> {
    path.map(|value| {
        serde_json::from_str(&read(value)?)
            .map_err(|error| format!("cannot decode target profile: {error}"))
    })
    .transpose()
}

fn run(arguments: &[String]) -> Result<String, String> {
    if arguments.len() < 3 || arguments.len() > 4 {
        return Err("usage: adapter_projection <compile|simply> REQUEST [PROFILE]".into());
    }
    let request_json = read(&arguments[2])?;
    let target = profile(arguments.get(3))?;
    if arguments[1] == "compile" {
        let request: CompileRequest = serde_json::from_str(&request_json)
            .map_err(|error| format!("cannot decode compile request: {error}"))?;
        let result = compile(&request, target.as_ref())
            .map_err(|error| format!("canonical compile failed: {error}"))?;
        serde_json::to_string(&result).map_err(|error| error.to_string())
    } else if arguments[1] == "simply" {
        let decoded = decode_simply_builder_request(&request_json)
            .map_err(|error| format!("cannot decode Simply request: {error}"))?;
        let protocol_version = decoded.protocol_version().to_owned();
        let compile_request = replay_simply_builder_request(decoded)
            .map_err(|error| format!("cannot replay Simply request: {error}"))?;
        let compile_result = compile(&compile_request, target.as_ref())
            .map_err(|error| format!("canonical Simply compile failed: {error}"))?;
        serde_json::to_string(&SimplyAdapterResponse::Success {
            protocol_version,
            compile_request,
            compile_result,
        })
        .map_err(|error| error.to_string())
    } else {
        Err(format!("unknown operation: {}", arguments[1]))
    }
}

fn main() -> ExitCode {
    match run(&env::args().collect::<Vec<_>>()) {
        Ok(value) => {
            println!("{value}");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(1)
        }
    }
}
