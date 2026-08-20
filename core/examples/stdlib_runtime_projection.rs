//! Repository-only projection of canonical standard-library Semantic DSL forms.
//!
//! The exact-runtime controller consumes this bounded JSON projection. Every
//! pattern passes through the existing frontend, analysis, portability,
//! lowering, and serialization stages; this example owns no target semantics.

use std::collections::BTreeMap;
use std::error::Error;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::ecmascript_lowering::lower_ecmascript;
use strling_kernel::ecmascript_serialization::serialize_ecmascript;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::python_re_lowering::{lower_python_re, PythonRePatternKind};
use strling_kernel::python_re_serialization::serialize_python_re;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::semantic_frontend::{parse, DIALECT_VERSION, FRONTEND_ID, MEDIA_TYPE};
use strling_kernel::source::SourceDocument;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{PortabilityStatus, TargetProfile, TargetProfileReference};
use strling_kernel::target_lowering::lower_pcre2;
use strling_kernel::target_serialization::serialize_pcre2;
use strling_kernel::validation::from_json;

fn failure(message: impl Into<String>) -> io::Error {
    io::Error::new(io::ErrorKind::Other, message.into())
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

fn status_value(status: Option<PortabilityStatus>) -> Result<Value, Box<dyn Error>> {
    let status = status.ok_or_else(|| failure("portability plan remained unresolved"))?;
    if status == PortabilityStatus::Unsupported {
        return Err(failure("canonical standard-library pattern is unsupported").into());
    }
    Ok(serde_json::to_value(status)?)
}

fn source_document(entry: &Value) -> Result<SourceDocument, Box<dyn Error>> {
    let variant_id = entry["variant_id"]
        .as_str()
        .ok_or_else(|| failure("variant_id is not a string"))?;
    let lines = entry["semantic_dsl_lines"]
        .as_array()
        .ok_or_else(|| failure("semantic_dsl_lines is not an array"))?;
    let source = lines
        .iter()
        .map(|line| {
            line.as_str()
                .ok_or_else(|| failure("semantic DSL line is not a string"))
        })
        .collect::<Result<Vec<_>, _>>()?
        .join("\n")
        + "\n";
    Ok(serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": format!("src:stdlib.runtime.{variant_id}"),
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": FRONTEND_ID,
            "dialect_version": DIALECT_VERSION
        },
        "display_name": format!("{variant_id}.strling"),
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": MEDIA_TYPE,
            "text": source
        },
        "provenance": {
            "kind": "authored",
            "description": "canonical standard-library runtime projection"
        }
    }))?)
}

fn project_application(
    entry: &Value,
    profile_id: &str,
    profile: &TargetProfile,
) -> Result<Value, Box<dyn Error>> {
    let document = source_document(entry)?;
    let parsed = parse(&document).map_err(|error| {
        failure(format!(
            "{}: canonical Semantic DSL failed to parse: {error:?}",
            entry["variant_id"].as_str().unwrap_or("unknown")
        ))
    })?;
    let program = &parsed.program;
    let foundational = analyze(program).map_err(|error| failure(error.to_string()))?;
    let structural =
        analyze_structure(program, &foundational).map_err(|error| failure(error.to_string()))?;
    let evaluation = evaluate_capabilities(program, &foundational, &structural, profile)
        .map_err(|error| failure(error.to_string()))?;
    let plan = plan_portability(program, &foundational, &structural, profile, &evaluation)
        .map_err(|error| failure(error.to_string()))?;
    let planned_status = status_value(plan.status)?;

    let mut output = json!({
        "profile_id": profile_id,
        "planned_status": planned_status,
    });
    if profile_id.starts_with("profile:pcre2/") {
        let lowered =
            lower_pcre2(program, profile, &plan).map_err(|error| failure(error.to_string()))?;
        if !lowered.captures.is_empty() {
            return Err(
                failure("standard-library projection unexpectedly contains captures").into(),
            );
        }
        output["artifact"] = serde_json::to_value(
            serialize_pcre2(&lowered).map_err(|error| failure(error.to_string()))?,
        )?;
    } else if profile_id.starts_with("profile:ecmascript/") {
        let lowered = lower_ecmascript(program, profile, &plan)
            .map_err(|error| failure(error.to_string()))?;
        if !lowered.captures.is_empty() {
            return Err(
                failure("standard-library projection unexpectedly contains captures").into(),
            );
        }
        output["artifact"] = serde_json::to_value(
            serialize_ecmascript(&lowered).map_err(|error| failure(error.to_string()))?,
        )?;
    } else if profile_id.starts_with("profile:python-re/") {
        let lowered =
            lower_python_re(program, profile, &plan).map_err(|error| failure(error.to_string()))?;
        if !lowered.captures.is_empty() {
            return Err(
                failure("standard-library projection unexpectedly contains captures").into(),
            );
        }
        output["pattern_kind"] = json!(match lowered.pattern_kind {
            PythonRePatternKind::Str => "str",
            PythonRePatternKind::Bytes => "bytes",
        });
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
    contract: &Value,
) -> Result<BTreeMap<String, TargetProfile>, Box<dyn Error>> {
    let mut profiles = BTreeMap::new();
    for entry in contract["runtime_certification"]["profiles"]
        .as_array()
        .ok_or_else(|| failure("runtime profiles must be an array"))?
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
    let contract = load_json(&root.join("spec/stdlib/registry/1.0/canonical-semantics.json"))?;
    let profiles = load_profiles(&root, &contract)?;
    let profile_order = contract["runtime_certification"]["profiles"]
        .as_array()
        .ok_or_else(|| failure("runtime profiles must be an array"))?;
    let mut variants = Vec::new();
    for entry in contract["entries"]
        .as_array()
        .ok_or_else(|| failure("canonical entries must be an array"))?
    {
        let mut applications = Vec::new();
        for profile_entry in profile_order {
            let profile_id = profile_entry["target_profile"]["profile_id"]
                .as_str()
                .ok_or_else(|| failure("profile_id is not a string"))?;
            let profile = profiles
                .get(profile_id)
                .ok_or_else(|| failure(format!("profile {profile_id} was not loaded")))?;
            applications.push(project_application(entry, profile_id, profile)?);
        }
        variants.push(json!({
            "applications": applications,
            "helper_id": entry["helper_id"],
            "variant_id": entry["variant_id"],
        }));
    }

    let contract_sha256 = format!("{:x}", Sha256::digest(serde_json::to_vec(&contract)?));
    let base = json!({
        "projection_version": "1.0.0",
        "registry_version": contract["registry_version"],
        "contract_sha256": contract_sha256,
        "variants": variants,
    });
    let result_sha256 = format!("{:x}", Sha256::digest(serde_json::to_vec(&base)?));
    let mut result = base;
    result["result_sha256"] = json!(result_sha256);
    Ok(result)
}

fn main() -> Result<(), Box<dyn Error>> {
    println!("{}", serde_json::to_string(&run()?)?);
    Ok(())
}
