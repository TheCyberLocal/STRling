use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use serde::Deserialize;
use serde_json::{json, Value};
use strling_kernel::compile;
use strling_kernel::protocol::{CompileInput, CompileRequest, CompileResult};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::simply::{decode_simply_builder_request, replay_simply_builder_request};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::from_json;

#[derive(Debug, Deserialize)]
struct Corpus {
    comparison_outputs: Value,
    compiler_options: Value,
    target_profiles: Vec<ProfileEntry>,
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
struct ProfileEntry {
    path: String,
    reference: Value,
}

#[derive(Debug, Deserialize)]
struct Case {
    id: String,
    semantic_source: String,
    identity_namespace: String,
    semantic_options: Value,
    steps: Value,
    root_step_id: String,
    #[serde(default)]
    legacy: Option<Legacy>,
}

#[derive(Debug, Deserialize)]
struct Legacy {
    source: String,
}

fn repository_file(path: impl AsRef<Path>) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join(path)
}

fn load_corpus() -> Corpus {
    let path = repository_file("tests/convergence/frontend-convergence.json");
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    serde_json::from_str(&text)
        .unwrap_or_else(|error| panic!("deserialize {}: {error}", path.display()))
}

fn load_profile(entry: &ProfileEntry) -> TargetProfile {
    let path = repository_file(&entry.path);
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    let profile: TargetProfile =
        from_json(&text).unwrap_or_else(|error| panic!("validate {}: {error}", path.display()));
    assert_eq!(
        serde_json::to_value(profile.reference().expect("profile reference"))
            .expect("serialize profile reference"),
        entry.reference,
        "{}: checked profile reference drift",
        entry.path
    );
    profile
}

fn simply_request(corpus: &Corpus, case: &Case, profile: &ProfileEntry) -> CompileRequest {
    let request = json!({
        "protocol_version": "1.0.0",
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "identity_namespace": case.identity_namespace,
        "semantic_options": case.semantic_options,
        "steps": case.steps,
        "root_step_id": case.root_step_id,
        "compile": {
            "target_profile": profile.reference,
            "requested_outputs": corpus.comparison_outputs,
            "compiler_options": corpus.compiler_options,
        }
    });
    let request = serde_json::to_string(&request).expect("serialize Simply request");
    let decoded = decode_simply_builder_request(&request)
        .unwrap_or_else(|error| panic!("{}: decode Simply request: {error}", case.id));
    replay_simply_builder_request(decoded)
        .unwrap_or_else(|errors| panic!("{}: replay Simply request: {errors:?}", case.id))
}

fn source_request(
    corpus: &Corpus,
    case: &Case,
    profile: &ProfileEntry,
    semantic: bool,
) -> CompileRequest {
    let (frontend, dialect, media_type, display_name, text, provenance) = if semantic {
        (
            "strling.semantic",
            "1.0.0",
            "text/x-strling-semantic",
            "convergence.semantic.strling",
            case.semantic_source.as_str(),
            "authored convergence intent",
        )
    } else {
        let legacy = case.legacy.as_ref().expect("legacy source");
        (
            "strling.regex-compat",
            "1.0.0",
            "text/strling-regex",
            "convergence.regex",
            legacy.source.as_str(),
            "imported convergence intent",
        )
    };
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": {
            "kind": "source",
            "document": {
                "contract_version": "1.0.0",
                "source_id": if semantic { "src:convergence.semantic" } else { "src:convergence.regex" },
                "specification_version": "1.0-draft.1",
                "frontend": { "id": frontend, "dialect_version": dialect },
                "display_name": display_name,
                "content": {
                    "kind": "inline",
                    "encoding": "utf-8",
                    "media_type": media_type,
                    "text": text,
                },
                "provenance": { "kind": if semantic { "authored" } else { "imported" }, "description": provenance }
            }
        },
        "target_profile": profile.reference,
        "requested_outputs": corpus.comparison_outputs,
        "compiler_options": corpus.compiler_options,
    }))
    .unwrap_or_else(|error| panic!("{}: construct source request: {error}", case.id))
}

fn collect_semantic_ids(
    node: &Value,
    node_ids: &mut BTreeMap<String, String>,
    capture_ids: &mut BTreeMap<String, String>,
) {
    let object = node.as_object().expect("semantic node object");
    if let Some(node_id) = object.get("node_id").and_then(Value::as_str) {
        let next = format!("node:{}", node_ids.len() + 1);
        node_ids.entry(node_id.to_owned()).or_insert(next);
    }
    if let Some(capture_id) = object.get("capture_id").and_then(Value::as_str) {
        let next = format!("capture:{}", capture_ids.len() + 1);
        capture_ids.entry(capture_id.to_owned()).or_insert(next);
    }
    match object.get("kind").and_then(Value::as_str) {
        Some("sequence") => {
            for child in object["items"].as_array().expect("sequence items") {
                collect_semantic_ids(child, node_ids, capture_ids);
            }
        }
        Some("alternation") => {
            for child in object["branches"].as_array().expect("alternation branches") {
                collect_semantic_ids(child, node_ids, capture_ids);
            }
        }
        Some("atomic") | Some("capture") | Some("lookaround") | Some("repeat") => {
            collect_semantic_ids(
                object.get("body").expect("unary semantic body"),
                node_ids,
                capture_ids,
            )
        }
        _ => {}
    }
}

fn replace_representation(
    value: &mut Value,
    node_ids: &BTreeMap<String, String>,
    capture_ids: &BTreeMap<String, String>,
) {
    match value {
        Value::Object(object) => {
            for excluded in [
                "origin",
                "sources",
                "primary_location",
                "related_locations",
                "source_id",
                "source_range",
                "source_span",
            ] {
                object.remove(excluded);
            }
            for child in object.values_mut() {
                replace_representation(child, node_ids, capture_ids);
            }
        }
        Value::Array(items) => {
            for item in items {
                replace_representation(item, node_ids, capture_ids);
            }
        }
        Value::String(text) => {
            let mut identities: Vec<_> = node_ids.iter().chain(capture_ids.iter()).collect();
            identities.sort_by_key(|(identity, _)| std::cmp::Reverse(identity.len()));
            for (identity, replacement) in identities {
                if text.contains(identity) {
                    *text = text.replace(identity, replacement);
                }
            }
        }
        _ => {}
    }
}

fn semantic_identity_maps(value: &Value) -> (BTreeMap<String, String>, BTreeMap<String, String>) {
    let root = &value["semantic_result"]["program"]["root"];
    assert!(
        root.is_object(),
        "compile result must contain requested semantics"
    );
    let mut node_ids = BTreeMap::new();
    let mut capture_ids = BTreeMap::new();
    collect_semantic_ids(root, &mut node_ids, &mut capture_ids);
    (node_ids, capture_ids)
}

fn sort_projection_sets(value: &mut Value) {
    match value {
        Value::Object(object) => {
            object.remove("occurrence");
            for child in object.values_mut() {
                sort_projection_sets(child);
            }
            for key in [
                "advice",
                "capture_ids",
                "decisions",
                "diagnostics",
                "feature_requirements",
                "node_facts",
                "node_ids",
            ] {
                if let Some(Value::Array(items)) = object.get_mut(key) {
                    items.sort_by_key(|item| {
                        serde_json::to_string(item).expect("serialize comparison member")
                    });
                    if key == "decisions" {
                        for (index, item) in items.iter_mut().enumerate() {
                            if let Some(decision) = item.as_object_mut() {
                                decision.insert(
                                    "requirement_id".to_owned(),
                                    Value::String(format!("requirement:{}", index + 1)),
                                );
                            }
                        }
                    }
                }
            }
        }
        Value::Array(items) => {
            for item in items {
                sort_projection_sets(item);
            }
        }
        _ => {}
    }
}

fn comparison_projection_value(mut value: Value) -> Value {
    let (node_ids, capture_ids) = semantic_identity_maps(&value);
    replace_representation(&mut value, &node_ids, &capture_ids);
    sort_projection_sets(&mut value);
    value
}

fn comparison_projection(result: &CompileResult) -> Value {
    comparison_projection_value(serde_json::to_value(result).expect("serialize CompileResult"))
}

fn direct_request(simply: &CompileRequest) -> CompileRequest {
    let CompileInput::Semantic { program } = &simply.input else {
        panic!("Simply must produce semantic input")
    };
    let mut value = serde_json::to_value(program.as_ref()).expect("serialize semantic program");
    let mut envelope = json!({ "semantic_result": { "program": value } });
    let (node_ids, capture_ids) = semantic_identity_maps(&envelope);
    replace_representation(&mut envelope, &node_ids, &capture_ids);
    value = envelope["semantic_result"]["program"].take();
    rewrite_direct_ids(&mut value);
    let direct: SemanticProgram = serde_json::from_value(value).expect("source-less Semantic IR");
    let mut request = simply.clone();
    request.input = CompileInput::Semantic {
        program: Box::new(direct),
    };
    request
}

fn rewrite_direct_ids(value: &mut Value) {
    fn gather(value: &Value, nodes: &mut Vec<String>, captures: &mut Vec<String>) {
        match value {
            Value::Object(object) => {
                if let Some(id) = object.get("node_id").and_then(Value::as_str) {
                    if !nodes.iter().any(|known| known == id) {
                        nodes.push(id.to_owned());
                    }
                }
                if let Some(id) = object.get("capture_id").and_then(Value::as_str) {
                    if !captures.iter().any(|known| known == id) {
                        captures.push(id.to_owned());
                    }
                }
                for child in object.values() {
                    gather(child, nodes, captures);
                }
            }
            Value::Array(items) => {
                for item in items {
                    gather(item, nodes, captures);
                }
            }
            _ => {}
        }
    }
    let mut nodes = Vec::new();
    let mut captures = Vec::new();
    gather(value, &mut nodes, &mut captures);
    let node_ids = nodes
        .into_iter()
        .enumerate()
        .map(|(index, id)| (id, format!("node:direct/{}", index + 1)))
        .collect();
    let capture_ids = captures
        .into_iter()
        .enumerate()
        .map(|(index, id)| (id, format!("capture:direct/{}", index + 1)))
        .collect();
    replace_representation(value, &node_ids, &capture_ids);
}

fn compile_deterministically(
    case_id: &str,
    route: &str,
    request: &CompileRequest,
    profile: &TargetProfile,
) -> CompileResult {
    let first = compile(request, Some(profile))
        .unwrap_or_else(|error| panic!("{case_id}/{route}: compile failed: {error}"));
    let second = compile(request, Some(profile))
        .unwrap_or_else(|error| panic!("{case_id}/{route}: repeat compile failed: {error}"));
    assert_eq!(
        serde_json::to_vec(&first).expect("serialize first result"),
        serde_json::to_vec(&second).expect("serialize repeated result"),
        "{case_id}/{route}: nondeterministic CompileResult"
    );
    first
}

fn assert_converges(
    case_id: &str,
    profile_id: &str,
    route: &str,
    expected: &Value,
    actual: &CompileResult,
) {
    let actual = comparison_projection(actual);
    assert_eq!(
        expected,
        &actual,
        "{case_id}/{profile_id}: {route} diverged from native Simply\nexpected={}\nactual={}",
        serde_json::to_string_pretty(expected).expect("pretty expected"),
        serde_json::to_string_pretty(&actual).expect("pretty actual")
    );
}

#[test]
fn every_frontend_converges_on_semantics_facts_diagnostics_and_targets() {
    let corpus = load_corpus();
    assert_eq!(corpus.cases.len(), 11);
    assert_eq!(corpus.target_profiles.len(), 3);
    assert_eq!(
        corpus
            .cases
            .iter()
            .filter(|case| case.legacy.is_some())
            .count(),
        9
    );

    for profile_entry in &corpus.target_profiles {
        let profile = load_profile(profile_entry);
        let profile_id = profile_entry.reference["profile_id"]
            .as_str()
            .expect("profile id");
        for case in &corpus.cases {
            let simply = simply_request(&corpus, case, profile_entry);
            let direct = direct_request(&simply);
            let semantic = source_request(&corpus, case, profile_entry, true);

            let simply_result =
                compile_deterministically(&case.id, "rust-simply", &simply, &profile);
            let expected = comparison_projection(&simply_result);
            assert_converges(
                &case.id,
                profile_id,
                "source-less-semantic-ir",
                &expected,
                &compile_deterministically(&case.id, "source-less-semantic-ir", &direct, &profile),
            );
            assert_converges(
                &case.id,
                profile_id,
                "semantic-source",
                &expected,
                &compile_deterministically(&case.id, "semantic-source", &semantic, &profile),
            );
            if case.legacy.is_some() {
                let legacy = source_request(&corpus, case, profile_entry, false);
                assert_converges(
                    &case.id,
                    profile_id,
                    "regex-compatible-import",
                    &expected,
                    &compile_deterministically(
                        &case.id,
                        "regex-compatible-import",
                        &legacy,
                        &profile,
                    ),
                );
            }
        }
    }
}

#[test]
fn comparison_projection_excludes_only_governed_representation_fields() {
    let corpus = load_corpus();
    let profile_entry = &corpus.target_profiles[0];
    let profile = load_profile(profile_entry);
    let case = &corpus.cases[2];
    let simply = simply_request(&corpus, case, profile_entry);
    let result = compile_deterministically(&case.id, "projection-control", &simply, &profile);
    let baseline = comparison_projection(&result);

    let mut identity_only = serde_json::to_value(&result).expect("serialize control");
    let (nodes, captures) = semantic_identity_maps(&identity_only);
    let renamed_nodes: BTreeMap<_, _> = nodes
        .keys()
        .enumerate()
        .map(|(index, id)| (id.clone(), format!("node:mutation/{}", index + 1)))
        .collect();
    let renamed_captures: BTreeMap<_, _> = captures
        .keys()
        .enumerate()
        .map(|(index, id)| (id.clone(), format!("capture:mutation/{}", index + 1)))
        .collect();
    replace_representation(&mut identity_only, &renamed_nodes, &renamed_captures);
    let identity_only: CompileResult =
        serde_json::from_value(identity_only).expect("renamed control result");
    assert_eq!(baseline, comparison_projection(&identity_only));

    let mut semantic_change = serde_json::to_value(&result).expect("serialize mutation");
    let program = semantic_change["semantic_result"]["program"]
        .as_object_mut()
        .expect("semantic program");
    program.insert(
        "case_matching".to_owned(),
        Value::String("insensitive".to_owned()),
    );
    assert_ne!(baseline, comparison_projection_value(semantic_change));

    let mut diagnostic_change = serde_json::to_value(&result).expect("serialize diagnostic");
    diagnostic_change["diagnostics"] = Value::Array(vec![json!({
        "contract_version": "1.0.0",
        "code": "STRL-QUALITY-9999",
        "severity": "warning",
        "phase": "semantic_analysis",
        "category": "quality",
        "confidence": "certain",
        "message": "controlled convergence mutation"
    })]);
    assert_ne!(baseline, comparison_projection_value(diagnostic_change));
}
