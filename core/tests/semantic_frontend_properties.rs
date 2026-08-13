use std::panic::{catch_unwind, AssertUnwindSafe};

use serde_json::{json, Value};
use strling_kernel::semantic_frontend::{
    format, parse, SemanticFrontendErrorCode, DIALECT_VERSION, FRONTEND_ID, MAX_CAPTURES,
    MAX_IDENTIFIER_BYTES, MAX_INTEGER, MAX_MATERIAL_NODES, MAX_NESTING_DEPTH, MAX_SET_MEMBERS,
    MEDIA_TYPE,
};
use strling_kernel::source::SourceDocument;

fn document(source: &str) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": "src:semantic.property",
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": FRONTEND_ID,
            "dialect_version": DIALECT_VERSION
        },
        "display_name": "property.strling",
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": MEDIA_TYPE,
            "text": source
        },
        "provenance": {
            "kind": "authored",
            "description": "P13-T05 deterministic property input"
        }
    }))
    .expect("valid property source document")
}

fn identity_projection(program: &strling_kernel::semantic::SemanticProgram) -> Value {
    fn clean(value: &mut Value) {
        match value {
            Value::Object(object) => {
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

fn source(root: &str, insensitive: bool) -> String {
    format!(
        "semantic strling 1.0;\ncase {};\npattern {root}\n",
        if insensitive {
            "insensitive"
        } else {
            "sensitive"
        }
    )
}

fn expect_code(source: &str, code: SemanticFrontendErrorCode) {
    let failure = parse(&document(source)).expect_err("source must be rejected");
    assert_eq!(
        failure.diagnostic().expect("frontend diagnostic").code,
        code
    );
}

#[test]
fn generated_valid_programs_are_deterministic_idempotent_and_identity_stable() {
    for index in 0..512_u32 {
        let root = match index % 8 {
            0 => "empty;".to_owned(),
            1 => format!("text \"value-{index}\\n\";"),
            2 => "sequence { text \"a\"; text \"b\"; }".to_owned(),
            3 => "choice { text \"x\"; text \"y\"; }".to_owned(),
            4 => "character from { scalar \"_\"; unicode word; }".to_owned(),
            5 => "repeat from 1 to unbounded using greedy { text \"r\"; }".to_owned(),
            6 => "if followed by { text \"look\"; }".to_owned(),
            _ => format!(
                "sequence {{ capture item_{index} {{ text \"c\"; }} same text as item_{index}; }}"
            ),
        };
        let authored = source(&root, index % 2 == 0);
        let first = parse(&document(&authored))
            .unwrap_or_else(|error| panic!("generated case {index} failed: {error}\n{authored}"));
        let repeated = parse(&document(&authored)).expect("repeated parse");
        assert_eq!(first, repeated, "generated case {index}");

        let canonical = format(&first);
        let reparsed = parse(&document(&canonical)).expect("canonical source reparses");
        assert_eq!(format(&reparsed), canonical, "generated case {index}");
        assert_eq!(
            identity_projection(&reparsed.program),
            identity_projection(&first.program),
            "generated case {index}"
        );
    }
}

#[test]
fn comments_align_with_following_constructs_and_enclosing_closures() {
    let authored = "semantic strling 1.0;\ncase sensitive;\npattern sequence {\n# child\ntext \"a\";\ncharacter from {\n# member\nscalar \"_\";\n# set close\n}\n# sequence close\n}\n";
    let parsed = parse(&document(authored)).expect("nested comments parse");
    let canonical = format(&parsed);
    assert_eq!(
        canonical,
        "semantic strling 1.0;\ncase sensitive;\n\npattern sequence {\n    # child\n    text \"a\";\n    character from {\n        # member\n        scalar \"_\";\n    # set close\n    }\n# sequence close\n}\n"
    );
    let reparsed = parse(&document(&canonical)).expect("canonical comments reparse");
    assert_eq!(format(&reparsed), canonical);
}

#[test]
fn deterministic_arbitrary_utf8_inputs_never_panic() {
    const ALPHABET: &[char] = &[
        'a',
        'Z',
        '0',
        '_',
        ' ',
        '\n',
        '\r',
        '#',
        '"',
        '\\',
        ';',
        '{',
        '}',
        '\0',
        'é',
        '中',
        '🙂',
        '\u{10ffff}',
    ];
    let mut state = 0x9e37_79b9_7f4a_7c15_u64;
    for case_index in 0..2_048_u32 {
        state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1);
        let length = (state as usize) % 192;
        let mut input = String::new();
        for _ in 0..length {
            state = state
                .wrapping_mul(2_862_933_555_777_941_757)
                .wrapping_add(3_037_000_493);
            input.push(ALPHABET[(state as usize) % ALPHABET.len()]);
        }
        let result = catch_unwind(AssertUnwindSafe(|| parse(&document(&input))));
        assert!(result.is_ok(), "arbitrary UTF-8 case {case_index} panicked");
    }
}

#[test]
fn nesting_identifier_and_integer_limits_are_exact() {
    let nested = |wrappers: usize| {
        let mut root = "empty;".to_owned();
        for _ in 0..wrappers {
            root = format!("without backtracking {{ {root} }}");
        }
        source(&root, false)
    };
    parse(&document(&nested(MAX_NESTING_DEPTH - 1))).expect("maximum nesting");
    expect_code(
        &nested(MAX_NESTING_DEPTH),
        SemanticFrontendErrorCode::ResourceLimit,
    );

    let maximum_identifier = "a".repeat(MAX_IDENTIFIER_BYTES);
    parse(&document(&source(
        &format!("capture {maximum_identifier} {{ empty; }}"),
        false,
    )))
    .expect("maximum identifier");
    let oversized_identifier = "a".repeat(MAX_IDENTIFIER_BYTES + 1);
    expect_code(
        &source(
            &format!("capture {oversized_identifier} {{ empty; }}"),
            false,
        ),
        SemanticFrontendErrorCode::InvalidIdentifier,
    );

    parse(&document(&source(
        &format!("repeat from {MAX_INTEGER} to unbounded using greedy {{ empty; }}"),
        false,
    )))
    .expect("maximum integer");
    expect_code(
        &source(
            &format!(
                "repeat from {} to unbounded using greedy {{ empty; }}",
                MAX_INTEGER + 1
            ),
            false,
        ),
        SemanticFrontendErrorCode::InvalidInteger,
    );
}

#[test]
fn node_capture_and_set_member_limits_are_exact() {
    let composition = |children: usize| {
        let mut root = String::from("sequence {");
        for _ in 0..children {
            root.push_str(" empty;");
        }
        root.push_str(" }");
        source(&root, false)
    };
    parse(&document(&composition(MAX_MATERIAL_NODES - 1))).expect("maximum material nodes");
    expect_code(
        &composition(MAX_MATERIAL_NODES),
        SemanticFrontendErrorCode::ResourceLimit,
    );

    let captures = |count: usize| {
        let mut root = String::from("sequence {");
        for index in 0..count {
            root.push_str(&format!(" capture c{index} {{ empty; }}"));
        }
        root.push_str(" }");
        source(&root, false)
    };
    parse(&document(&captures(MAX_CAPTURES))).expect("maximum captures");
    expect_code(
        &captures(MAX_CAPTURES + 1),
        SemanticFrontendErrorCode::ResourceLimit,
    );

    let set = |members: usize| {
        let mut root = String::from("character from {");
        for _ in 0..members {
            root.push_str(" scalar \"a\";");
        }
        root.push_str(" }");
        source(&root, false)
    };
    parse(&document(&set(MAX_SET_MEMBERS))).expect("maximum set members");
    expect_code(
        &set(MAX_SET_MEMBERS + 1),
        SemanticFrontendErrorCode::ResourceLimit,
    );
}
