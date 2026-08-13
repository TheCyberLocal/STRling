//! Repository-only projection of specification-owned conformance vectors.
//!
//! This adapter is deliberately pure with respect to target runtimes. It reads
//! immutable repository contracts, invokes only canonical compiler stages, and
//! emits bounded JSON artifacts for the isolated Python execution controller.

use std::collections::BTreeMap;
use std::error::Error;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::conformance::ConformanceCase;
use strling_kernel::ecmascript_lowering::lower_ecmascript;
use strling_kernel::ecmascript_serialization::serialize_ecmascript;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::protocol::CompileInput;
use strling_kernel::python_re_lowering::{lower_python_re, PythonRePatternKind};
use strling_kernel::python_re_serialization::serialize_python_re;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{PortabilityStatus, TargetProfile, TargetProfileReference};
use strling_kernel::target_lowering::lower_pcre2;
use strling_kernel::target_serialization::serialize_pcre2;
use strling_kernel::validation::from_json;

fn failure(message: impl Into<String>) -> io::Error {
    io::Error::other(message.into())
}

fn load_text(path: &Path) -> Result<String, Box<dyn Error>> {
    Ok(fs::read_to_string(path)?)
}

fn load_json(path: &Path) -> Result<Value, Box<dyn Error>> {
    Ok(serde_json::from_str(&load_text(path)?)?)
}

fn repository_root() -> Result<PathBuf, Box<dyn Error>> {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest
        .parent()
        .map(Path::to_path_buf)
        .ok_or_else(|| failure("core manifest has no repository parent").into())
}

fn profile_file(profile_id: &str) -> Result<&'static str, Box<dyn Error>> {
    match profile_id {
        "profile:ecmascript/2024" => Ok("ecmascript-2024.json"),
        "profile:pcre2/10.42" => Ok("pcre2-10.42.json"),
        "profile:pcre2/10.43" => Ok("pcre2-10.43.json"),
        "profile:python-re/3.11" => Ok("python-re-3.11.json"),
        "profile:python-re/3.11-bytes" => Ok("python-re-3.11-bytes.json"),
        _ => Err(failure(format!("unsupported governed profile {profile_id}")).into()),
    }
}

fn capture_projection(captures: impl IntoIterator<Item = (u32, String, Option<String>)>) -> Value {
    Value::Array(
        captures
            .into_iter()
            .map(|(slot, capture_id, name)| {
                json!({"slot": slot, "capture_id": capture_id, "name": name})
            })
            .collect(),
    )
}

fn status_value(status: Option<PortabilityStatus>) -> Result<Value, Box<dyn Error>> {
    let status = status.ok_or_else(|| failure("portability plan remained unresolved"))?;
    Ok(serde_json::to_value(status)?)
}

fn project_application(
    case: &ConformanceCase,
    application: &Value,
    profile: &TargetProfile,
) -> Result<Value, Box<dyn Error>> {
    let profile_id = application["target_profile"]["profile_id"]
        .as_str()
        .ok_or_else(|| failure("application profile_id is not a string"))?;
    let state = application["state"]
        .as_str()
        .ok_or_else(|| failure("application state is not a string"))?;
    let mut output = json!({"profile_id": profile_id, "state": state});
    if state == "not_applicable" {
        return Ok(output);
    }

    let CompileInput::Semantic { program } = &case.input else {
        return Err(failure("target application refers to a source-input case").into());
    };
    let foundational = analyze(program).map_err(|error| failure(error.to_string()))?;
    let structural =
        analyze_structure(program, &foundational).map_err(|error| failure(error.to_string()))?;
    let evaluation = evaluate_capabilities(program, &foundational, &structural, profile)
        .map_err(|error| failure(error.to_string()))?;
    let plan = plan_portability(program, &foundational, &structural, profile, &evaluation)
        .map_err(|error| failure(error.to_string()))?;
    let planned_status = status_value(plan.status)?;
    if planned_status != application["portability_status"] {
        return Err(failure(format!(
            "{}/{profile_id}: canonical plan status differs from authored expectation",
            case.case_id.as_str()
        ))
        .into());
    }
    output["planned_status"] = planned_status;
    if state == "unsupported" {
        return Ok(output);
    }
    if state != "execute" {
        return Err(failure(format!("unknown application state {state}")).into());
    }

    if profile_id.starts_with("profile:pcre2/") {
        let lowered =
            lower_pcre2(program, profile, &plan).map_err(|error| failure(error.to_string()))?;
        output["captures"] = capture_projection(lowered.captures.iter().map(|capture| {
            (
                capture.slot,
                capture.capture_id.as_str().to_owned(),
                capture.name.clone(),
            )
        }));
        output["artifact"] = serde_json::to_value(
            serialize_pcre2(&lowered).map_err(|error| failure(error.to_string()))?,
        )?;
    } else if profile_id.starts_with("profile:ecmascript/") {
        let lowered = lower_ecmascript(program, profile, &plan)
            .map_err(|error| failure(error.to_string()))?;
        output["captures"] = capture_projection(lowered.captures.iter().map(|capture| {
            (
                capture.slot,
                capture.capture_id.as_str().to_owned(),
                capture.name.clone(),
            )
        }));
        output["artifact"] = serde_json::to_value(
            serialize_ecmascript(&lowered).map_err(|error| failure(error.to_string()))?,
        )?;
    } else if profile_id.starts_with("profile:python-re/") {
        let lowered =
            lower_python_re(program, profile, &plan).map_err(|error| failure(error.to_string()))?;
        output["pattern_kind"] = json!(match lowered.pattern_kind {
            PythonRePatternKind::Str => "str",
            PythonRePatternKind::Bytes => "bytes",
        });
        output["captures"] = capture_projection(lowered.captures.iter().map(|capture| {
            (
                capture.slot,
                capture.capture_id.as_str().to_owned(),
                capture.name.clone(),
            )
        }));
        output["artifact"] = serde_json::to_value(
            serialize_python_re(&lowered).map_err(|error| failure(error.to_string()))?,
        )?;
    } else {
        return Err(failure(format!("no target stage for {profile_id}")).into());
    }
    Ok(output)
}

fn load_profiles(
    root: &Path,
    corpus: &Value,
) -> Result<BTreeMap<String, TargetProfile>, Box<dyn Error>> {
    let mut profiles = BTreeMap::new();
    for entry in corpus["profiles"]
        .as_array()
        .ok_or_else(|| failure("corpus profiles must be an array"))?
    {
        let reference: TargetProfileReference =
            serde_json::from_value(entry["target_profile"].clone())?;
        let profile_id = reference.profile_id.as_str().to_owned();
        let path = root
            .join("spec/targets/profiles")
            .join(profile_file(&profile_id)?);
        let profile: TargetProfile = from_json(&load_text(&path)?)?;
        if profile.reference()? != reference {
            return Err(failure(format!("{profile_id}: profile reference is stale")).into());
        }
        profiles.insert(profile_id, profile);
    }
    Ok(profiles)
}

fn run() -> Result<Value, Box<dyn Error>> {
    let root = repository_root()?;
    let corpus = load_json(&root.join("spec/conformance/shared-corpus-v1.json"))?;
    let profiles = load_profiles(&root, &corpus)?;
    let mut vectors = Vec::new();
    for vector in corpus["vectors"]
        .as_array()
        .ok_or_else(|| failure("corpus vectors must be an array"))?
    {
        let case_path = vector["path"]
            .as_str()
            .ok_or_else(|| failure("vector path is not a string"))?;
        let case: ConformanceCase = from_json(&load_text(&root.join(case_path))?)?;
        let mut applications = Vec::new();
        for application in vector["applications"]
            .as_array()
            .ok_or_else(|| failure("vector applications must be an array"))?
        {
            let profile_id = application["target_profile"]["profile_id"]
                .as_str()
                .ok_or_else(|| failure("application profile_id is not a string"))?;
            let profile = profiles
                .get(profile_id)
                .ok_or_else(|| failure(format!("profile {profile_id} was not loaded")))?;
            applications.push(project_application(&case, application, profile)?);
        }
        vectors.push(json!({
            "case_id": case.case_id.as_str(),
            "applications": applications,
        }));
    }
    let base = json!({
        "projection_version": "1.0.0",
        "corpus_id": corpus["corpus_id"],
        "vectors": vectors,
    });
    let encoded = serde_json::to_vec(&base)?;
    let result_sha256 = format!("{:x}", Sha256::digest(encoded));
    let mut result = base;
    result["result_sha256"] = json!(result_sha256);
    Ok(result)
}

fn main() -> Result<(), Box<dyn Error>> {
    println!("{}", serde_json::to_string(&run()?)?);
    Ok(())
}
