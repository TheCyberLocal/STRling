use std::fs;
use std::path::PathBuf;

use serde::Deserialize;
use serde_json::{json, Value};
use strling_kernel::diagnostic::{CompilerPhase, DiagnosticCategory};
use strling_kernel::semantic::Node;
use strling_kernel::semantic_frontend::{
    format, parse, SemanticFrontendErrorCode, SemanticFrontendFailure, DIALECT_VERSION,
    FRONTEND_ID, MAX_SOURCE_BYTES, MEDIA_TYPE,
};
use strling_kernel::source::{SourceContent, SourceDocument};

#[derive(Debug, Deserialize)]
struct CaseSet {
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
struct Case {
    id: String,
    source: String,
    expected: Expected,
}

#[derive(Debug, Deserialize)]
struct Expected {
    status: String,
    #[serde(default)]
    diagnostic_code: Option<String>,
    #[serde(default)]
    byte_offset: Option<u64>,
}

fn repository_file(path: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join(path)
}

fn cases(path: &str) -> CaseSet {
    let path = repository_file(path);
    let source = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    serde_json::from_str(&source)
        .unwrap_or_else(|error| panic!("deserialize {}: {error}", path.display()))
}

fn document(source: &str) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": "src:semantic.fixture",
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": FRONTEND_ID,
            "dialect_version": DIALECT_VERSION
        },
        "display_name": "fixture.strling",
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": MEDIA_TYPE,
            "text": source
        },
        "provenance": {
            "kind": "authored",
            "description": "P13-T05 Semantic STRling parser fixture"
        }
    }))
    .expect("valid Semantic STRling source document")
}

fn semantic_projection(program: &strling_kernel::semantic::SemanticProgram) -> Value {
    fn clean(value: &mut Value) {
        match value {
            Value::Object(object) => {
                object.remove("node_id");
                object.remove("capture_id");
                object.remove("origin");
                object.remove("sources");
                for value in object.values_mut() {
                    clean(value);
                }
            }
            Value::Array(values) => {
                for value in values {
                    clean(value);
                }
            }
            _ => {}
        }
    }
    let mut value = serde_json::to_value(program).expect("serialize Semantic IR");
    clean(&mut value);
    value
}

fn visit_nodes<'a>(node: &'a Node, nodes: &mut Vec<&'a Node>) {
    nodes.push(node);
    match node {
        Node::Sequence { items, .. } => {
            for child in items {
                visit_nodes(child, nodes);
            }
        }
        Node::Alternation { branches, .. } => {
            for child in branches {
                visit_nodes(child, nodes);
            }
        }
        Node::Repeat { body, .. }
        | Node::Capture { body, .. }
        | Node::Lookaround { body, .. }
        | Node::Atomic { body, .. } => visit_nodes(body, nodes),
        Node::Empty { .. }
        | Node::Literal { .. }
        | Node::Wildcard { .. }
        | Node::CharacterSet { .. }
        | Node::Position { .. }
        | Node::Backreference { .. } => {}
    }
}

#[test]
fn all_positive_contract_cases_parse_format_and_reparse_stably() {
    let fixtures = cases("spec/frontends/semantic/1.0/fixtures/positive.json");
    assert_eq!(fixtures.cases.len(), 12);
    for case in fixtures.cases {
        assert_eq!(case.expected.status, "accepted", "{}", case.id);
        let source = document(&case.source);
        let first = parse(&source).unwrap_or_else(|error| panic!("{}: {error}", case.id));
        let repeated = parse(&source).expect("deterministic repeated parse");
        assert_eq!(first, repeated, "{}", case.id);

        let formatted = format(&first);
        assert!(formatted.ends_with('\n'), "{}", case.id);
        assert!(!formatted.contains('\r'), "{}", case.id);
        let reparsed = parse(&document(&formatted))
            .unwrap_or_else(|error| panic!("formatted {}: {error}\n{formatted}", case.id));
        assert_eq!(format(&reparsed), formatted, "{}", case.id);
        assert_eq!(
            semantic_projection(&reparsed.program),
            semantic_projection(&first.program),
            "{}",
            case.id
        );

        let mut nodes = Vec::new();
        visit_nodes(&first.program.root, &mut nodes);
        for node in nodes {
            let origin = node.origin().expect("parsed node origin");
            let spans = origin.source_spans.as_ref().expect("material source span");
            assert!(!spans.is_empty(), "{}", case.id);
            for span in spans {
                assert!(span.start <= span.end, "{}", case.id);
                assert!(span.end <= case.source.len() as u64, "{}", case.id);
            }
        }
    }
}

#[test]
fn all_negative_contract_cases_reject_with_exact_identity_and_offset() {
    let fixtures = cases("spec/frontends/semantic/1.0/fixtures/negative.json");
    assert_eq!(fixtures.cases.len(), 30);
    for case in fixtures.cases {
        assert_eq!(case.expected.status, "rejected", "{}", case.id);
        let failure = match parse(&document(&case.source)) {
            Ok(_) => panic!("{} must be rejected", case.id),
            Err(failure) => failure,
        };
        let error = failure
            .diagnostic()
            .unwrap_or_else(|| panic!("{} must have a frontend diagnostic", case.id));
        assert_eq!(
            error.code.id(),
            case.expected.diagnostic_code.as_deref().expect("code"),
            "{}",
            case.id
        );
        assert_eq!(
            error.byte_offset,
            case.expected.byte_offset.expect("offset"),
            "{}",
            case.id
        );
        assert_eq!(
            error.diagnostic.code.as_str(),
            error.code.id(),
            "{}",
            case.id
        );
        assert_eq!(error.diagnostic.phase, error.code.phase(), "{}", case.id);
        assert_eq!(
            error.diagnostic.category,
            error.code.category(),
            "{}",
            case.id
        );
        assert_eq!(
            error
                .diagnostic
                .primary_location
                .as_ref()
                .expect("location")
                .start,
            error.byte_offset,
            "{}",
            case.id
        );
    }
}

#[test]
fn resource_and_source_boundaries_are_typed_and_deterministic() {
    let oversized = " ".repeat(MAX_SOURCE_BYTES + 1);
    let failure = parse(&document(&oversized)).expect_err("oversized source");
    let diagnostic = failure.diagnostic().expect("resource diagnostic");
    assert_eq!(diagnostic.code, SemanticFrontendErrorCode::ResourceLimit);
    assert_eq!(diagnostic.byte_offset, MAX_SOURCE_BYTES as u64);
    assert_eq!(diagnostic.diagnostic.phase, CompilerPhase::FrontendParse);
    assert_eq!(
        diagnostic.diagnostic.category,
        DiagnosticCategory::ResourceLimit
    );

    let mut wrong_dialect = document("semantic strling 1.0;\ncase sensitive;\npattern empty;\n");
    wrong_dialect.frontend.dialect_version =
        strling_kernel::source::DialectVersion::try_from("2.0.0").expect("dialect");
    assert_eq!(
        parse(&wrong_dialect)
            .expect_err("wrong dialect")
            .diagnostic()
            .expect("diagnostic")
            .code,
        SemanticFrontendErrorCode::InvalidHeader
    );

    let mut referenced = document("semantic strling 1.0;\ncase sensitive;\npattern empty;\n");
    referenced.content = serde_json::from_value(json!({
        "kind": "reference",
        "encoding": "utf-8",
        "media_type": MEDIA_TYPE,
        "uri": "urn:strling:semantic:fixture",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }))
    .expect("valid reference");
    assert!(matches!(
        referenced.content,
        SourceContent::Reference { .. }
    ));
    assert!(matches!(
        parse(&referenced),
        Err(SemanticFrontendFailure::ReferencedSourceUnavailable)
    ));
}

#[test]
fn canonical_formatter_preserves_comment_order_and_authored_set_order() {
    let source = "# first\r\nsemantic strling 1.0;\r\ncase sensitive;\r\n# second\r\npattern character from { unicode word; scalar \"_\"; } # last\r\n";
    let parsed = parse(&document(source)).expect("commented source");
    let formatted = format(&parsed);
    assert_eq!(
        formatted,
        "semantic strling 1.0;\ncase sensitive;\n\n# first\n# second\npattern character from {\n    unicode word;\n    scalar \"_\";\n}\n# last\n"
    );
    let reparsed = parse(&document(&formatted)).expect("formatted comments");
    assert_eq!(format(&reparsed), formatted);
}
