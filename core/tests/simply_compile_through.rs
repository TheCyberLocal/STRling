use std::convert::TryFrom;

use serde_json::{json, Value};
use strling_kernel::compile;
use strling_kernel::protocol::{CompileInput, CompileRequest, CompilerOptions, RequestedOutput};
use strling_kernel::semantic::{AssertionPolarity, LookaroundDirection, SemanticProgram};
use strling_kernel::source::{ContractVersion, SpecificationVersion};
use strling_kernel::target::{PortabilityStatus, TargetProfile};
use strling_kernel::{SimplyBuilder, SimplyCompileProjection, SimplyOptions, SimplyValue};

const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const ECMASCRIPT_2024: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");
const PYTHON_RE_311: &str = include_str!("../../spec/targets/profiles/python-re-3.11.json");

fn version() -> SpecificationVersion {
    SpecificationVersion::try_from("1.0-draft.1").expect("specification version")
}

fn compiler_options() -> CompilerOptions {
    serde_json::from_value(json!({
        "partial_semantics": "forbid",
        "diagnostic_policy": { "minimum_severity": "hint" }
    }))
    .expect("compiler options")
}

fn direct_program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("direct semantic program")
}

fn direct_request(
    program: SemanticProgram,
    profile: Option<&TargetProfile>,
    outputs: Vec<RequestedOutput>,
) -> CompileRequest {
    CompileRequest {
        contract_version: ContractVersion::V1_0_0,
        specification_version: version(),
        input: CompileInput::Semantic {
            program: Box::new(program),
        },
        target_profile: profile.map(|profile| profile.reference().expect("profile reference")),
        requested_outputs: outputs,
        compiler_options: compiler_options(),
    }
}

fn simply_request(
    builder: SimplyBuilder,
    root: &SimplyValue,
    profile: Option<&TargetProfile>,
    outputs: Vec<RequestedOutput>,
) -> CompileRequest {
    builder
        .finish_request(
            root,
            SimplyCompileProjection {
                target_profile: profile
                    .map(|profile| profile.reference().expect("profile reference")),
                requested_outputs: outputs,
                compiler_options: compiler_options(),
            },
        )
        .expect("Simply request")
}

fn assert_compile_through(
    direct: CompileRequest,
    simply: CompileRequest,
    profile: Option<&TargetProfile>,
) -> Value {
    assert_eq!(
        direct, simply,
        "construction must project the direct request"
    );
    let direct_result = compile(&direct, profile).expect("direct request compiles");
    let simply_result = compile(&simply, profile).expect("Simply request compiles");
    let direct_json = serde_json::to_value(direct_result).expect("direct result JSON");
    let simply_json = serde_json::to_value(simply_result).expect("Simply result JSON");
    assert_eq!(direct_json, simply_json, "kernel results must be identical");
    simply_json
}

#[test]
fn nested_capture_request_matches_target_neutral_diagnostics_and_analysis() {
    let mut builder =
        SimplyBuilder::new("through/neutral", version(), SimplyOptions::default()).unwrap();
    let body = builder.literal("body", "x").unwrap();
    let capture = builder
        .capture("capture", "word", Some("word"), &body)
        .unwrap();
    let reference = builder.backreference("reference", "word").unwrap();
    let root = builder.sequence("root", &[capture, reference]).unwrap();
    let outputs = vec![RequestedOutput::Semantic, RequestedOutput::Analysis];
    let simply = simply_request(builder, &root, None, outputs.clone());
    let direct = direct_request(
        direct_program(json!({
            "node_id": "node:simply/through/neutral/root",
            "kind": "sequence",
            "items": [
                {
                    "node_id": "node:simply/through/neutral/capture",
                    "kind": "capture",
                    "capture_id": "capture:simply/through/neutral/word",
                    "name": "word",
                    "body": {
                        "node_id": "node:simply/through/neutral/body",
                        "kind": "literal",
                        "text": "x"
                    }
                },
                {
                    "node_id": "node:simply/through/neutral/reference",
                    "kind": "backreference",
                    "capture_id": "capture:simply/through/neutral/word"
                }
            ]
        })),
        None,
        outputs,
    );
    let result = assert_compile_through(direct, simply, None);
    assert!(result["semantic_result"].is_object());
    assert!(result["analysis"].is_object());
}

#[test]
fn native_portability_matches_direct_semantics() {
    let profile: TargetProfile = serde_json::from_str(PCRE2_1042).expect("PCRE2 profile");
    let mut builder =
        SimplyBuilder::new("through/native", version(), SimplyOptions::default()).unwrap();
    let root = builder.literal("root", "portable").unwrap();
    let outputs = vec![RequestedOutput::Portability];
    let simply = simply_request(builder, &root, Some(&profile), outputs.clone());
    let direct = direct_request(
        direct_program(json!({
            "node_id": "node:simply/through/native/root",
            "kind": "literal",
            "text": "portable"
        })),
        Some(&profile),
        outputs,
    );
    let result = assert_compile_through(direct, simply, Some(&profile));
    assert_eq!(
        serde_json::to_value(PortabilityStatus::Native).unwrap(),
        result["portability"]["status"]
    );
}

#[test]
fn certified_rewrite_matches_direct_semantics() {
    let profile: TargetProfile = serde_json::from_str(ECMASCRIPT_2024).expect("ECMAScript profile");
    let mut builder =
        SimplyBuilder::new("through/rewrite", version(), SimplyOptions::default()).unwrap();
    let body = builder.literal("body", "x").unwrap();
    let root = builder.atomic("root", &body).unwrap();
    let outputs = vec![RequestedOutput::Semantic, RequestedOutput::Portability];
    let simply = simply_request(builder, &root, Some(&profile), outputs.clone());
    let direct = direct_request(
        direct_program(json!({
            "node_id": "node:simply/through/rewrite/root",
            "kind": "atomic",
            "body": {
                "node_id": "node:simply/through/rewrite/body",
                "kind": "literal",
                "text": "x"
            }
        })),
        Some(&profile),
        outputs,
    );
    let result = assert_compile_through(direct, simply, Some(&profile));
    assert_eq!(
        serde_json::to_value(PortabilityStatus::EquivalentRewrite).unwrap(),
        result["portability"]["status"]
    );
}

#[test]
fn unsupported_variable_lookbehind_matches_direct_semantics() {
    let profile: TargetProfile = serde_json::from_str(PYTHON_RE_311).expect("Python re profile");
    let mut builder =
        SimplyBuilder::new("through/unsupported", version(), SimplyOptions::default()).unwrap();
    let short = builder.literal("short", "x").unwrap();
    let long = builder.literal("long", "yyy").unwrap();
    let alternatives = builder.alternation("alternatives", &[short, long]).unwrap();
    let root = builder
        .lookaround(
            "root",
            LookaroundDirection::Behind,
            AssertionPolarity::Positive,
            &alternatives,
        )
        .unwrap();
    let outputs = vec![RequestedOutput::Portability];
    let simply = simply_request(builder, &root, Some(&profile), outputs.clone());
    let direct = direct_request(
        direct_program(json!({
            "node_id": "node:simply/through/unsupported/root",
            "kind": "lookaround",
            "direction": "behind",
            "polarity": "positive",
            "body": {
                "node_id": "node:simply/through/unsupported/alternatives",
                "kind": "alternation",
                "branches": [
                    {
                        "node_id": "node:simply/through/unsupported/short",
                        "kind": "literal",
                        "text": "x"
                    },
                    {
                        "node_id": "node:simply/through/unsupported/long",
                        "kind": "literal",
                        "text": "yyy"
                    }
                ]
            }
        })),
        Some(&profile),
        outputs,
    );
    let result = assert_compile_through(direct, simply, Some(&profile));
    assert_eq!(
        serde_json::to_value(PortabilityStatus::Unsupported).unwrap(),
        result["portability"]["status"]
    );
}

#[test]
fn target_artifact_request_matches_direct_kernel_availability() {
    let profile: TargetProfile = serde_json::from_str(PCRE2_1042).expect("PCRE2 profile");
    let mut builder =
        SimplyBuilder::new("through/artifact", version(), SimplyOptions::default()).unwrap();
    let root = builder.literal("root", "artifact").unwrap();
    let outputs = vec![
        RequestedOutput::Semantic,
        RequestedOutput::Portability,
        RequestedOutput::TargetArtifact,
    ];
    let simply = simply_request(builder, &root, Some(&profile), outputs.clone());
    let direct = direct_request(
        direct_program(json!({
            "node_id": "node:simply/through/artifact/root",
            "kind": "literal",
            "text": "artifact"
        })),
        Some(&profile),
        outputs,
    );
    let result = assert_compile_through(direct, simply, Some(&profile));
    assert!(result["artifact"].is_null());
    assert!(result["diagnostics"]
        .as_array()
        .expect("diagnostics")
        .iter()
        .any(|diagnostic| diagnostic["code"] == "STRL-PROTOCOL-0005"));
}
