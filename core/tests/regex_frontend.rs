use std::fs;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::path::PathBuf;

use serde::Deserialize;
use serde_json::json;
use strling_kernel::regex_frontend::{
    parse, RegexFrontendErrorCode, RegexFrontendFailure, MAX_CAPTURE_GROUPS, MAX_NESTING_DEPTH,
    MAX_SOURCE_BYTES,
};
use strling_kernel::semantic::{
    BuiltinClassName, CaseMatching, CharacterDomain, CharacterSetMember, LineTerminators, Node,
    PositionKind,
};
use strling_kernel::source::SourceDocument;

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

fn fixture_set(name: &str) -> FixtureSet {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../spec/frontends/legacy-regex/1.0/fixtures")
        .join(name);
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
        let (code, offset) = diagnostic(
            parse(&source).unwrap_err_or_else(|_| panic!("{} must be rejected", fixture.id)),
        );
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
    }
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
