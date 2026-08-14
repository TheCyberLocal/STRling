use std::fs;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::path::PathBuf;

use serde::Deserialize;
use serde_json::json;
use strling_kernel::diagnostic::{CompilerPhase, DiagnosticCategory, Severity, SeverityBasis};
use strling_kernel::normalization::normalize;
use strling_kernel::regex_frontend::{
    parse, RegexFrontendErrorCode, RegexFrontendFailure, MAX_CAPTURE_GROUPS, MAX_NESTING_DEPTH,
    MAX_SOURCE_BYTES,
};
use strling_kernel::semantic::{
    BuiltinClassName, CaseMatching, CharacterDomain, CharacterSetMember, LineTerminators, Node,
    PositionKind,
};
use strling_kernel::source::{SourceDocument, SourceOrigin};
use strling_kernel::validation::Validate;

#[derive(Debug, Deserialize)]
struct FixtureSet {
    cases: Vec<FixtureCase>,
}

#[derive(Debug, Deserialize)]
struct FixtureCase {
    id: String,
    source: String,
    expected: FixtureExpectation,
}

#[derive(Debug, Deserialize)]
struct FixtureExpectation {
    #[serde(default)]
    active_flags: Vec<String>,
    #[serde(default)]
    diagnostic_id: Option<String>,
    #[serde(default)]
    byte_offset: Option<u64>,
}

#[derive(Debug, Deserialize)]
struct CorrespondenceSet {
    case_set_version: String,
    frontend: String,
    authorship: String,
    authority: String,
    cases: Vec<CorrespondenceCase>,
}

#[derive(Debug, Deserialize)]
struct CorrespondenceCase {
    id: String,
    source: String,
    expected_status: String,
}

#[derive(Debug, Deserialize)]
struct ProvenanceSet {
    case_set_version: String,
    frontend: String,
    authorship: String,
    authority: String,
    cases: Vec<ProvenanceCase>,
}

#[derive(Debug, Deserialize)]
struct ProvenanceCase {
    id: String,
    source: String,
    expected: ProvenanceExpectation,
}

#[derive(Debug, Deserialize)]
struct ProvenanceExpectation {
    status: String,
    #[serde(default)]
    root_spans: Vec<[u64; 2]>,
    #[serde(default)]
    directive_span: Option<[u64; 2]>,
    #[serde(default)]
    diagnostic_code: Option<String>,
    #[serde(default)]
    primary_span: Option<[u64; 2]>,
    #[serde(default)]
    related_spans: Vec<[u64; 2]>,
}

fn fixture_set(name: &str) -> FixtureSet {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../spec/frontends/legacy-regex/1.0/fixtures")
        .join(name);
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    serde_json::from_str(&text)
        .unwrap_or_else(|error| panic!("deserialize {}: {error}", path.display()))
}

fn provenance_set() -> ProvenanceSet {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../spec/frontends/legacy-regex/1.0/provenance/cases.json");
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    serde_json::from_str(&text)
        .unwrap_or_else(|error| panic!("deserialize {}: {error}", path.display()))
}

fn document(source: impl Into<String>) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": "src:regex-compat.test",
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": "strling.regex-compat",
            "dialect_version": "1.0.0"
        },
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": "text/strling-regex",
            "text": source.into()
        },
        "provenance": { "kind": "imported" }
    }))
    .expect("valid regex compatibility source document")
}

fn diagnostic(error: RegexFrontendFailure) -> (RegexFrontendErrorCode, u64) {
    let error = error.diagnostic().expect("frontend diagnostic");
    (error.code, error.byte_offset)
}

#[test]
fn accepts_the_complete_frozen_positive_corpus_deterministically() {
    let fixtures = fixture_set("positive.json");
    assert_eq!(fixtures.cases.len(), 30, "frozen positive corpus changed");

    for fixture in fixtures.cases {
        let source = document(fixture.source);
        let first = parse(&source)
            .unwrap_or_else(|error| panic!("{} must be accepted: {error}", fixture.id));
        let second = parse(&source)
            .unwrap_or_else(|error| panic!("{} must remain deterministic: {error}", fixture.id));
        assert_eq!(first, second, "{} produced unstable output", fixture.id);
        let active: Vec<String> = first
            .flags
            .active_letters()
            .into_iter()
            .map(|flag| flag.to_string())
            .collect();
        assert_eq!(
            active, fixture.expected.active_flags,
            "{} flags",
            fixture.id
        );
    }
}

#[test]
fn rejects_the_complete_frozen_negative_corpus_exactly() {
    let fixtures = fixture_set("negative.json");
    assert_eq!(fixtures.cases.len(), 45, "frozen negative corpus changed");

    for fixture in fixtures.cases {
        let source = document(fixture.source);
        let error =
            parse(&source).unwrap_err_or_else(|_| panic!("{} must be rejected", fixture.id));
        let frontend = error.diagnostic().expect("frontend diagnostic");
        let (code, offset) = (frontend.code, frontend.byte_offset);
        assert_eq!(
            code.id(),
            fixture
                .expected
                .diagnostic_id
                .as_deref()
                .expect("diagnostic id"),
            "{} diagnostic",
            fixture.id
        );
        assert_eq!(
            offset,
            fixture.expected.byte_offset.expect("byte offset"),
            "{} offset",
            fixture.id
        );
        frontend
            .diagnostic
            .validate()
            .unwrap_or_else(|errors| panic!("{} canonical diagnostic: {errors}", fixture.id));
        assert_eq!(
            frontend.diagnostic.code.as_str(),
            code.id(),
            "{} code",
            fixture.id
        );
        assert_eq!(
            frontend.diagnostic.severity,
            Severity::Error,
            "{} severity",
            fixture.id
        );
        assert_eq!(
            frontend.diagnostic.severity_basis,
            SeverityBasis::Normative,
            "{} severity authority",
            fixture.id
        );
        assert_eq!(frontend.diagnostic.phase, CompilerPhase::FrontendParse);
        assert_eq!(
            frontend.diagnostic.message,
            code.message(),
            "{} message",
            fixture.id
        );
        let location = frontend
            .diagnostic
            .primary_location
            .as_ref()
            .expect("frontend location");
        assert_eq!(location.start, offset, "{} location start", fixture.id);
        assert_eq!(
            location.source_id, source.source_id,
            "{} source",
            fixture.id
        );
        assert_eq!(
            frontend.frontend, source.frontend,
            "{} frontend identity",
            fixture.id
        );
        assert_eq!(
            frontend.source_provenance, source.provenance,
            "{} source provenance",
            fixture.id
        );
    }
}

fn origin(node: &Node) -> &SourceOrigin {
    node.origin().expect("parsed node source origin")
}

fn only_span(node: &Node) -> (u64, u64) {
    let spans = origin(node).source_spans.as_ref().expect("source spans");
    assert_eq!(spans.len(), 1);
    (spans[0].start, spans[0].end)
}

fn spans(node: &Node) -> Vec<(u64, u64)> {
    origin(node)
        .source_spans
        .as_ref()
        .expect("source spans")
        .iter()
        .map(|span| (span.start, span.end))
        .collect()
}

#[test]
fn covers_the_specification_authored_provenance_set() {
    let cases = provenance_set();
    assert_eq!(cases.case_set_version, "1.0.0");
    assert_eq!(cases.frontend, "strling.regex-compat@1.0.0");
    assert_eq!(cases.authorship, "specification-authored");
    assert_eq!(cases.authority, "legacy-regex-compatibility-provenance");

    for case in cases.cases {
        let source = document(&case.source);
        match case.expected.status.as_str() {
            "accepted" => {
                let parsed = parse(&source)
                    .unwrap_or_else(|error| panic!("{} must parse: {error}", case.id));
                let expected_spans = case
                    .expected
                    .root_spans
                    .iter()
                    .map(|span| (span[0], span[1]))
                    .collect::<Vec<_>>();
                assert_eq!(spans(&parsed.program.root), expected_spans, "{}", case.id);
                if let Some(expected) = case.expected.directive_span {
                    let actual = parsed
                        .flags_directive
                        .as_ref()
                        .expect("expected directive source span");
                    assert_eq!([actual.start, actual.end], expected, "{}", case.id);
                }
                let normalized = normalize(&parsed.program)
                    .unwrap_or_else(|errors| panic!("{} must normalize: {errors:?}", case.id));
                assert_eq!(spans(&normalized.root), expected_spans, "{}", case.id);
            }
            "diagnostic" => {
                let error = parse(&source)
                    .unwrap_err()
                    .diagnostic()
                    .expect("expected canonical frontend diagnostic")
                    .clone();
                assert_eq!(
                    error.code.id(),
                    case.expected.diagnostic_code.as_deref().expect("code"),
                    "{}",
                    case.id
                );
                let primary = error
                    .diagnostic
                    .primary_location
                    .as_ref()
                    .expect("primary location");
                assert_eq!(
                    [primary.start, primary.end],
                    case.expected.primary_span.expect("primary span"),
                    "{}",
                    case.id
                );
                let related = error
                    .diagnostic
                    .related_locations
                    .as_deref()
                    .unwrap_or_default()
                    .iter()
                    .map(|location| [location.location.start, location.location.end])
                    .collect::<Vec<_>>();
                assert_eq!(related, case.expected.related_spans, "{}", case.id);
            }
            status => panic!("{} has unsupported expected status {status}", case.id),
        }
    }
}

#[test]
fn preserves_multibyte_nested_and_directive_provenance() {
    let source = document("%flags x\n(?<word>éλ)(?=😀) # trailing\n");
    let parsed = parse(&source).expect("accepted Unicode source");

    let directive = parsed.flags_directive.expect("flags directive provenance");
    assert_eq!((directive.start, directive.end), (0, 8));
    assert_eq!(directive.source_id, source.source_id);

    assert_eq!(only_span(&parsed.program.root), (9, 30));
    let Node::Sequence { items, .. } = &parsed.program.root else {
        panic!("expected sequence");
    };
    assert_eq!(items.len(), 2);
    assert_eq!(only_span(&items[0]), (9, 22));
    assert_eq!(only_span(&items[1]), (22, 30));
    let Node::Capture { body, .. } = &items[0] else {
        panic!("expected named capture");
    };
    assert_eq!(only_span(body), (17, 21));
    let Node::Literal { text, .. } = body.as_ref() else {
        panic!("expected Unicode literal");
    };
    assert_eq!(text, "éλ");

    let normalized = normalize(&parsed.program).expect("parsed provenance normalizes");
    assert_eq!(normalized.sources, parsed.program.sources);
    assert_eq!(origin(&normalized.root), origin(&parsed.program.root));
}

#[test]
fn preserves_discontiguous_literal_provenance_across_extended_layout() {
    let parsed = parse(&document("%flags x\na # comment\nb")).expect("accepted extended source");
    let Node::Literal { text, .. } = &parsed.program.root else {
        panic!("expected merged literal");
    };
    assert_eq!(text, "ab");
    assert_eq!(spans(&parsed.program.root), vec![(9, 10), (21, 22)]);

    let normalized = normalize(&parsed.program).expect("discontiguous provenance normalizes");
    assert_eq!(spans(&normalized.root), vec![(9, 10), (21, 22)]);
}

#[test]
fn eof_and_duplicate_definitions_have_canonical_locations() {
    let eof_source = document("é(");
    let eof = parse(&eof_source).expect_err("unterminated Unicode group");
    let eof = eof.diagnostic().expect("frontend diagnostic");
    assert_eq!(eof.code, RegexFrontendErrorCode::UnterminatedGroup);
    let location = eof
        .diagnostic
        .primary_location
        .as_ref()
        .expect("EOF location");
    assert_eq!((location.start, location.end), (3, 3));
    assert_eq!(eof.diagnostic.category, DiagnosticCategory::Syntax);

    let duplicate = parse(&document("(?<x>a)(?<x>b)"))
        .expect_err("duplicate named capture")
        .diagnostic()
        .expect("frontend diagnostic")
        .clone();
    assert_eq!(duplicate.code, RegexFrontendErrorCode::DuplicateCaptureName);
    let related = duplicate
        .diagnostic
        .related_locations
        .as_ref()
        .expect("first definition evidence");
    assert_eq!(related.len(), 1);
    assert_eq!((related[0].location.start, related[0].location.end), (0, 1));
}

#[test]
fn lowers_global_flags_into_target_neutral_semantics() {
    let parsed = parse(&document("%flags imsu\n^.\\d$")).expect("accepted source");
    assert_eq!(parsed.program.case_matching, CaseMatching::Insensitive);

    let Node::Sequence { items, .. } = parsed.program.root else {
        panic!("expected semantic sequence");
    };
    assert!(matches!(
        items.as_slice(),
        [
            Node::Position {
                position: PositionKind::LineStart,
                ..
            },
            Node::Wildcard {
                line_terminators: LineTerminators::Include,
                ..
            },
            Node::CharacterSet {
                negated: false,
                members,
                ..
            },
            Node::Position {
                position: PositionKind::LineEnd,
                ..
            }
        ] if matches!(
            members.as_slice(),
            [CharacterSetMember::Builtin {
                name: BuiltinClassName::Digit,
                domain: CharacterDomain::Unicode,
                negated: false,
            }]
        )
    ));
}

#[test]
fn canonically_orders_multiple_builtin_class_members() {
    for source in [r"[^\w\s]", r"[^\W\D\S]"] {
        let parsed = parse(&document(source))
            .unwrap_or_else(|error| panic!("{source} must lower to valid Semantic IR: {error}"));
        parsed
            .program
            .validate()
            .unwrap_or_else(|errors| panic!("{source} must remain canonical: {errors}"));
    }
}

#[test]
fn enforces_frozen_resource_limits() {
    let too_large = "a".repeat(MAX_SOURCE_BYTES + 1);
    assert_eq!(
        diagnostic(parse(&document(too_large)).expect_err("oversized source")),
        (
            RegexFrontendErrorCode::SourceTooLarge,
            MAX_SOURCE_BYTES as u64
        )
    );

    let too_deep = format!(
        "{}a{}",
        "(?:".repeat(MAX_NESTING_DEPTH + 1),
        ")".repeat(MAX_NESTING_DEPTH + 1)
    );
    assert_eq!(
        diagnostic(parse(&document(too_deep)).expect_err("excessive depth")).0,
        RegexFrontendErrorCode::NestingTooDeep
    );

    let too_many_captures = "()".repeat(MAX_CAPTURE_GROUPS + 1);
    assert_eq!(
        diagnostic(parse(&document(too_many_captures)).expect_err("excessive capture count")).0,
        RegexFrontendErrorCode::TooManyCaptures
    );
}

#[test]
fn arbitrary_utf8_inputs_do_not_panic() {
    const ALPHABET: &[char] = &[
        'a', 'Z', '0', ' ', '\n', '#', '%', '\\', '(', ')', '[', ']', '{', '}', '|', '*', '+', '?',
        '<', '>', '-', '^', '$', ',', '=', 'é', 'λ', '😀', '\0',
    ];
    let mut state = 0x9e37_79b9_u32;

    for case_index in 0..2_048 {
        state = state.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
        let length = (state as usize % 96) + 1;
        let mut source = String::new();
        for _ in 0..length {
            state = state.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
            source.push(ALPHABET[state as usize % ALPHABET.len()]);
        }
        let source = document(source);
        let outcome = catch_unwind(AssertUnwindSafe(|| parse(&source)));
        assert!(
            outcome.is_ok(),
            "parser panicked for generated case {case_index}"
        );
    }
}

#[test]
fn covers_the_specification_authored_correspondence_set() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../spec/frontends/legacy-regex/1.0/correspondence/canonical-parser-cases.json");
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    let case_set: CorrespondenceSet = serde_json::from_str(&text)
        .unwrap_or_else(|error| panic!("deserialize {}: {error}", path.display()));

    assert_eq!(case_set.case_set_version, "1.0.0");
    assert_eq!(case_set.frontend, "strling.regex-compat@1.0.0");
    assert_eq!(case_set.authorship, "specification-authored");
    assert_eq!(
        case_set.authority,
        "spec/frontends/legacy-regex/1.0/dialect.json"
    );
    assert_eq!(case_set.cases.len(), 5, "correspondence coverage changed");

    for case in case_set.cases {
        let accepted = match case.expected_status.as_str() {
            "accepted" => true,
            "rejected" => false,
            status => panic!("{} has unknown status {status}", case.id),
        };
        assert_eq!(
            parse(&document(case.source)).is_ok(),
            accepted,
            "{} compatibility status",
            case.id
        );
    }
}

trait ResultExt<T, E> {
    fn unwrap_err_or_else<F: FnOnce(T) -> E>(self, failure: F) -> E;
}

impl<T, E> ResultExt<T, E> for Result<T, E> {
    fn unwrap_err_or_else<F: FnOnce(T) -> E>(self, failure: F) -> E {
        match self {
            Ok(value) => failure(value),
            Err(error) => error,
        }
    }
}
