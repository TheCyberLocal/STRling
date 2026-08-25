use std::collections::BTreeMap;
use std::convert::TryFrom;
use std::fs;
use std::path::{Path, PathBuf};

use serde::Deserialize;
use serde_json::{json, Value};
use strling_kernel::protocol::{CompileInput, CompileRequest};
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_frontend::{parse, DIALECT_VERSION, FRONTEND_ID, MEDIA_TYPE};
use strling_kernel::simply::{
    decode_simply_builder_request, replay_simply_builder_request, SimplyBuilderRequestDecodeError,
    SimplyOptions,
};
use strling_kernel::source::{SourceDocument, SpecificationVersion};
use strling_kernel::stdlib::{self, StdlibBuildContext};

const NEGATIVE: &str = include_str!("../../spec/frontends/simply/1.1/fixtures/negative.json");

#[derive(Debug, Deserialize)]
struct Corpus {
    counts: Counts,
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
struct Counts {
    cases: usize,
    helpers: usize,
    semantic_validators: usize,
}

#[derive(Debug, Deserialize)]
struct Case {
    case_id: String,
    helper_id: String,
    parameters: BTreeMap<String, Value>,
    semantic_dsl: String,
    variant_id: String,
}

fn repository_file(path: impl AsRef<Path>) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join(path)
}

fn semantic_projection(program: &SemanticProgram) -> Value {
    fn clean(value: &mut Value) {
        match value {
            Value::Object(object) => {
                for key in ["node_id", "capture_id", "origin", "sources"] {
                    object.remove(key);
                }
                for child in object.values_mut() {
                    clean(child);
                }
            }
            Value::Array(values) => {
                for child in values {
                    clean(child);
                }
            }
            _ => {}
        }
    }

    let mut value = serde_json::to_value(program).expect("serialize Semantic IR");
    clean(&mut value);
    value
}

fn simply_program(case: &Case) -> SemanticProgram {
    let request = json!({
        "protocol_version": "1.1.0",
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "identity_namespace": format!("surface.{}", case.variant_id),
        "semantic_options": {
            "case_matching": "sensitive",
            "text_model": "unicode_scalar_values",
            "builtin_character_domain": "unicode",
            "wildcard_line_terminators": "exclude"
        },
        "steps": [{
            "step_id": "root",
            "operation": "stdlib_helper",
            "arguments": {
                "helper_id": case.helper_id,
                "parameters": case.parameters
            }
        }],
        "root_step_id": "root",
        "compile": {
            "requested_outputs": ["semantic"],
            "compiler_options": {
                "partial_semantics": "forbid",
                "diagnostic_policy": {"minimum_severity": "warning"}
            }
        }
    });
    let decoded = decode_simply_builder_request(&request.to_string())
        .unwrap_or_else(|error| panic!("{}: decode failed: {error}", case.case_id));
    let request = replay_simply_builder_request(decoded)
        .unwrap_or_else(|errors| panic!("{}: replay failed: {errors}", case.case_id));
    let CompileRequest {
        input: CompileInput::Semantic { program },
        ..
    } = request
    else {
        panic!(
            "{}: helper replay did not produce Semantic IR",
            case.case_id
        )
    };
    *program
}

fn direct_program(case: &Case) -> SemanticProgram {
    let context = StdlibBuildContext::new(
        format!("surface.{}", case.variant_id),
        SpecificationVersion::try_from("1.0-draft.1").expect("specification version"),
        SimplyOptions::default(),
    );
    let pattern = stdlib::build(&case.helper_id, &case.parameters, &context)
        .unwrap_or_else(|error| panic!("{}: direct build failed: {error}", case.case_id));
    assert_eq!(pattern.variant_id, case.variant_id, "{}", case.case_id);
    pattern.program
}

fn dsl_program(case: &Case) -> SemanticProgram {
    let path = repository_file(&case.semantic_dsl);
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    let document: SourceDocument = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": format!("src:surface.{}", case.variant_id),
        "specification_version": "1.0-draft.1",
        "frontend": {"id": FRONTEND_ID, "dialect_version": DIALECT_VERSION},
        "display_name": format!("{}.strl", case.variant_id),
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": MEDIA_TYPE,
            "text": text
        },
        "provenance": {
            "kind": "authored",
            "description": "canonical standard-library Semantic DSL source projected from the registry"
        }
    }))
    .expect("valid Semantic source document");
    parse(&document)
        .unwrap_or_else(|error| panic!("{}: generated DSL failed: {error}", case.case_id))
        .program
}

#[test]
fn every_generated_frontend_case_delegates_to_one_canonical_semantics() {
    let path = repository_file("tests/convergence/stdlib-frontend-cases.json");
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    let corpus: Corpus = serde_json::from_str(&text).expect("stdlib convergence corpus");
    assert_eq!(corpus.counts.cases, 8);
    assert_eq!(corpus.counts.helpers, 5);
    assert_eq!(corpus.counts.semantic_validators, 0);
    assert_eq!(corpus.cases.len(), 8);

    for case in &corpus.cases {
        let simply = semantic_projection(&simply_program(case));
        assert_eq!(
            simply,
            semantic_projection(&direct_program(case)),
            "{}: Simply diverged from the canonical Rust builder",
            case.case_id
        );
        assert_eq!(
            simply,
            semantic_projection(&dsl_program(case)),
            "{}: generated DSL diverged from canonical semantics",
            case.case_id
        );
    }
}

#[test]
fn helper_failures_and_legacy_protocol_restriction_keep_stable_identities() {
    let negative: Value = serde_json::from_str(NEGATIVE).expect("negative cases");
    for case in negative["cases"].as_array().expect("negative cases") {
        let request = case["request"].to_string();
        let errors = match decode_simply_builder_request(&request) {
            Ok(decoded) => replay_simply_builder_request(decoded)
                .expect_err("negative request must fail during replay"),
            Err(SimplyBuilderRequestDecodeError::Construction(errors)) => errors,
            Err(SimplyBuilderRequestDecodeError::Malformed(message)) => {
                panic!("governed request is malformed: {message}")
            }
        };
        assert_eq!(
            case["expected"]["errors"],
            serde_json::to_value(errors.errors).expect("serialize errors")
        );
    }

    let mut legacy = negative["cases"][0]["request"].clone();
    legacy["protocol_version"] = Value::String("1.0.0".to_owned());
    let errors = match decode_simply_builder_request(&legacy.to_string()) {
        Err(SimplyBuilderRequestDecodeError::Construction(errors)) => errors,
        result => panic!("legacy stdlib_helper must fail during decode: {result:?}"),
    };
    assert_eq!(errors.errors[0].code.as_str(), "STRL-SIMPLY-0010");
    assert_eq!(errors.errors[0].path, "$.steps[0].operation");
}
