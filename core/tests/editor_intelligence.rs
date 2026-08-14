use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

use serde_json::{json, Value};
use strling_kernel::editor_intelligence::{
    project, semantic_keyword_terminals, EditorEvidence, EditorFrontend, EditorRequest,
    EditorTokenType, EDITOR_EVIDENCE_CONTRACT_VERSION, EDITOR_PROJECTION_VERSION,
};

fn manifest() -> Value {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../tooling/lsp-server/tests/fixtures/canonical-intelligence/manifest.json");
    serde_json::from_str(&std::fs::read_to_string(path).expect("read editor manifest"))
        .expect("parse editor manifest")
}

fn request(frontend: EditorFrontend, source: &str, cursor_byte: Option<usize>) -> EditorRequest {
    EditorRequest {
        contract_version: EDITOR_EVIDENCE_CONTRACT_VERSION.to_owned(),
        source_id: "src:editor.test".to_owned(),
        frontend,
        source: source.to_owned(),
        cursor_byte,
    }
}

fn materialize_template(template: &str) -> (String, usize) {
    let (before, after) = template
        .split_once("<CURSOR>")
        .expect("one completion cursor marker");
    assert!(!after.contains("<CURSOR>"));
    (format!("{before}{after}"), before.len())
}

fn labels(evidence: &EditorEvidence) -> Vec<&str> {
    evidence
        .completions
        .iter()
        .map(|completion| completion.label.as_str())
        .collect()
}

#[test]
fn canonical_frontends_match_every_authored_completion_context() {
    for case in manifest()["completion_cases"]
        .as_array()
        .expect("completion cases")
    {
        let frontend = match case["frontend"].as_str().expect("frontend") {
            "semantic" => EditorFrontend::Semantic,
            "regex" => EditorFrontend::Regex,
            "host" => continue,
            other => panic!("unexpected frontend {other}"),
        };
        let (source, cursor) =
            materialize_template(case["source_template"].as_str().expect("source template"));
        let evidence = project(&request(frontend, &source, Some(cursor)))
            .unwrap_or_else(|error| panic!("{}: {error}", case["id"]));
        let expected: Vec<&str> = case["expected_labels"]
            .as_array()
            .expect("expected labels")
            .iter()
            .map(|label| label.as_str().expect("label"))
            .collect();
        assert_eq!(labels(&evidence), expected, "{}", case["id"]);
        let replacement = evidence.replacement_span.expect("replacement span");
        let prefix = case
            .get("replacement_prefix")
            .and_then(Value::as_str)
            .unwrap_or("");
        if !expected.is_empty() || !prefix.is_empty() {
            assert_eq!(replacement.start, cursor - prefix.len(), "{}", case["id"]);
        }
        assert!(replacement.start <= cursor && cursor <= replacement.end);
    }
}

#[test]
fn semantic_editor_keyword_catalog_matches_the_authored_language_contract() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../spec/frontends/semantic/1.0/language.json");
    let language: Value = serde_json::from_str(
        &std::fs::read_to_string(path).expect("read Semantic STRling language contract"),
    )
    .expect("parse Semantic STRling language contract");
    let authored: Vec<&str> = language["keyword_terminals"]
        .as_array()
        .expect("keyword terminals")
        .iter()
        .map(|value| value.as_str().expect("keyword terminal"))
        .collect();
    assert_eq!(semantic_keyword_terminals(), authored);
}

fn token_name(token_type: EditorTokenType) -> &'static str {
    match token_type {
        EditorTokenType::String => "string",
        EditorTokenType::Number => "number",
        EditorTokenType::Operator => "operator",
        EditorTokenType::Regexp => "regexp",
        EditorTokenType::Keyword => "keyword",
        EditorTokenType::Function => "function",
        EditorTokenType::Variable => "variable",
        EditorTokenType::Comment => "comment",
    }
}

fn expected_tokens(case: &Value) -> Vec<(usize, usize, &str)> {
    let source = case["source"].as_str().expect("token source");
    let mut cursor = 0;
    case["tokens"]
        .as_array()
        .expect("tokens")
        .iter()
        .map(|token| {
            let text = token["text"].as_str().expect("token text");
            let start = cursor
                + source[cursor..]
                    .find(text)
                    .unwrap_or_else(|| panic!("missing token {text:?}"));
            let end = start + text.len();
            cursor = end;
            (start, end, token["type"].as_str().expect("token type"))
        })
        .collect()
}

#[test]
fn canonical_frontends_match_every_authored_token_stream() {
    for case in manifest()["token_cases"].as_array().expect("token cases") {
        let frontend = match case["frontend"].as_str().expect("frontend") {
            "semantic" => EditorFrontend::Semantic,
            "regex" => EditorFrontend::Regex,
            other => panic!("unexpected frontend {other}"),
        };
        let source = case["source"].as_str().expect("source");
        let evidence = project(&request(frontend, source, None))
            .unwrap_or_else(|error| panic!("{}: {error}", case["id"]));
        let actual: Vec<(usize, usize, &str)> = evidence
            .tokens
            .iter()
            .map(|token| {
                (
                    token.span.start,
                    token.span.end,
                    token_name(token.token_type),
                )
            })
            .collect();
        assert_eq!(actual, expected_tokens(case), "{}", case["id"]);
    }
}

fn flatten_symbols<'a>(
    symbols: &'a [strling_kernel::editor_intelligence::EditorSymbol],
    parent: Option<&'a str>,
    output: &mut Vec<(&'a str, &'a str, usize, usize, Option<&'a str>)>,
) {
    for symbol in symbols {
        output.push((
            &symbol.node_id,
            &symbol.kind,
            symbol.span.start,
            symbol.span.end,
            parent,
        ));
        flatten_symbols(&symbol.children, Some(&symbol.node_id), output);
    }
}

#[test]
fn canonical_symbol_trees_and_capture_links_match_authored_identity_evidence() {
    let evidence_manifest = manifest();
    let navigation = evidence_manifest["navigation_cases"]
        .as_array()
        .expect("navigation cases");
    for case in navigation.iter().filter(|case| case["kind"] == "symbols") {
        let frontend = if case["frontend"] == "semantic" {
            EditorFrontend::Semantic
        } else {
            EditorFrontend::Regex
        };
        let evidence = project(&request(
            frontend,
            case["source"].as_str().expect("source"),
            None,
        ))
        .expect("project symbol evidence");
        let mut actual = Vec::new();
        flatten_symbols(&evidence.symbols, None, &mut actual);
        let expected: Vec<(&str, &str, usize, usize, Option<&str>)> = case["expected_nodes"]
            .as_array()
            .expect("expected nodes")
            .iter()
            .map(|node| {
                (
                    node["node_id"].as_str().expect("node id"),
                    node["kind"].as_str().expect("kind"),
                    node["span"][0].as_u64().expect("start") as usize,
                    node["span"][1].as_u64().expect("end") as usize,
                    node["parent"].as_str(),
                )
            })
            .collect();
        assert_eq!(actual, expected, "{}", case["id"]);
    }

    for case in navigation
        .iter()
        .filter(|case| matches!(case["kind"].as_str(), Some("definition" | "references")))
    {
        let frontend = if case["frontend"] == "semantic" {
            EditorFrontend::Semantic
        } else {
            EditorFrontend::Regex
        };
        let evidence = project(&request(
            frontend,
            case["source"].as_str().expect("source"),
            None,
        ))
        .expect("project capture evidence");
        let capture = evidence
            .captures
            .iter()
            .find(|capture| capture.capture_id == case["capture_id"])
            .expect("capture identity");
        if let Some(expected) = case.get("expected_declaration") {
            assert_eq!(
                capture.declaration.start,
                expected[0].as_u64().unwrap() as usize
            );
            assert_eq!(
                capture.declaration.end,
                expected[1].as_u64().unwrap() as usize
            );
        }
        if let Some(expected) = case.get("expected_locations") {
            let mut locations = capture.references.clone();
            if case["include_declaration"] == true {
                locations.insert(0, capture.declaration);
            }
            let expected: Vec<(usize, usize)> = expected
                .as_array()
                .expect("locations")
                .iter()
                .map(|span| {
                    (
                        span[0].as_u64().unwrap() as usize,
                        span[1].as_u64().unwrap() as usize,
                    )
                })
                .collect();
            assert_eq!(
                locations
                    .iter()
                    .map(|span| (span.start, span.end))
                    .collect::<Vec<_>>(),
                expected,
                "{}",
                case["id"]
            );
        }
    }
}

#[test]
fn editor_transport_is_versioned_json_and_rejects_invalid_cursor_boundaries() {
    let source = "é";
    assert!(project(&request(EditorFrontend::Regex, source, Some(1))).is_err());

    let executable = env!("CARGO_BIN_EXE_strling-editor-core");
    let mut child = Command::new(executable)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn editor transport");
    child
        .stdin
        .take()
        .expect("stdin")
        .write_all(
            serde_json::to_string(&request(EditorFrontend::Regex, "a+", Some(1)))
                .expect("serialize request")
                .as_bytes(),
        )
        .expect("write request");
    let output = child.wait_with_output().expect("wait for editor transport");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let value: Value = serde_json::from_slice(&output.stdout).expect("editor JSON");
    assert_eq!(value["contract_version"], EDITOR_EVIDENCE_CONTRACT_VERSION);
    assert_eq!(value["projection_version"], EDITOR_PROJECTION_VERSION);
    assert_eq!(value["source_id"], "src:editor.test");
    assert_eq!(value["frontend"], "regex");
    assert_eq!(value["parse_status"], "complete");
    assert_eq!(value["truncated"], false);
    assert_eq!(value["replacement_span"], json!({ "start": 0, "end": 1 }));
}
