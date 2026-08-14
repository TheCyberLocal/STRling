//! Bounded JSON transport for the non-normative canonical editor projection.

use std::io::{self, Read, Write};
use std::process::ExitCode;

use strling_kernel::editor_intelligence::{project, EditorRequest};

// JSON escaping can expand one source byte to six transport bytes. Keep the
// wire cap bounded without rejecting a valid one-mebibyte source document.
const MAX_REQUEST_BYTES: usize = 6 * 1_048_576 + 4_096;

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("strling-editor-core: {message}");
            ExitCode::from(64)
        }
    }
}

fn run() -> Result<(), String> {
    if std::env::args().len() != 1 {
        return Err("the editor transport accepts one JSON request on standard input".to_owned());
    }
    let mut input = Vec::new();
    io::stdin()
        .take((MAX_REQUEST_BYTES + 1) as u64)
        .read_to_end(&mut input)
        .map_err(|error| format!("cannot read request: {error}"))?;
    if input.len() > MAX_REQUEST_BYTES {
        return Err("request exceeds the editor transport byte limit".to_owned());
    }
    let request: EditorRequest =
        serde_json::from_slice(&input).map_err(|error| format!("invalid request: {error}"))?;
    let evidence = project(&request).map_err(|error| error.to_string())?;
    let output = serde_json::to_vec(&evidence)
        .map_err(|error| format!("cannot serialize editor evidence: {error}"))?;
    let mut stdout = io::stdout().lock();
    stdout
        .write_all(&output)
        .and_then(|()| stdout.write_all(b"\n"))
        .map_err(|error| format!("cannot write response: {error}"))
}
