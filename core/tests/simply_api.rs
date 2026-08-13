use std::convert::TryFrom;

use serde_json::Value;
use strling_kernel::protocol::{CompileInput, CompileRequest, RequestedOutput, ResourceLimits};
use strling_kernel::semantic::{
    AssertionPolarity, BuiltinClassName, CaseMatching, CharacterDomain, LineTerminators,
    LookaroundDirection, Node, PositionKind, RepetitionMaximum, RepetitionMode, SemanticProgram,
};
use strling_kernel::source::{SourceDocument, SpecificationVersion};
use strling_kernel::{
    SimplyBuilder, SimplyCharacterSetMember, SimplyCompileProjection, SimplyErrorCode,
    SimplyOptions,
};

const POSITIVE: &str = include_str!("../../spec/frontends/simply/1.0/fixtures/positive.json");
const NEGATIVE: &str = include_str!("../../spec/frontends/simply/1.0/fixtures/negative.json");

fn fixture<'a>(suite: &'a Value, case_id: &str) -> &'a Value {
    suite["cases"]
        .as_array()
        .expect("fixture cases")
        .iter()
        .find(|case| case["case_id"] == case_id)
        .unwrap_or_else(|| panic!("missing fixture {case_id}"))
}

fn options(request: &Value) -> SimplyOptions {
    let semantic = &request["semantic_options"];
    SimplyOptions {
        case_matching: match semantic["case_matching"].as_str().expect("case matching") {
            "sensitive" => CaseMatching::Sensitive,
            "insensitive" => CaseMatching::Insensitive,
            value => panic!("unexpected case matching {value}"),
        },
        builtin_character_domain: match semantic["builtin_character_domain"]
            .as_str()
            .expect("character domain")
        {
            "ascii" => CharacterDomain::Ascii,
            "unicode" => CharacterDomain::Unicode,
            value => panic!("unexpected character domain {value}"),
        },
        wildcard_line_terminators: match semantic["wildcard_line_terminators"]
            .as_str()
            .expect("wildcard behavior")
        {
            "exclude" => LineTerminators::Exclude,
            "include" => LineTerminators::Include,
            value => panic!("unexpected wildcard behavior {value}"),
        },
    }
}

fn builder(request: &Value) -> SimplyBuilder {
    SimplyBuilder::new(
        request["identity_namespace"]
            .as_str()
            .expect("identity namespace"),
        SpecificationVersion::try_from(
            request["specification_version"]
                .as_str()
                .expect("specification version"),
        )
        .expect("valid specification version"),
        options(request),
    )
    .expect("valid builder")
}

fn build_case(request: &Value, case_id: &str) -> (SimplyBuilder, strling_kernel::SimplyValue) {
    let mut builder = builder(request);
    let root = match case_id {
        "literal-empty-group-sequence" => {
            let literal = builder.literal("literal", "a.b").expect("literal");
            let empty_text = builder.literal("empty-text", "").expect("empty text");
            let empty = builder.empty("empty").expect("empty");
            let grouped = builder.group("grouped", &literal).expect("group");
            builder
                .sequence("root", &[grouped, empty_text, empty])
                .expect("sequence")
        }
        "alternation-wildcard-options" => {
            let wildcard = builder.wildcard("wildcard", None).expect("wildcard");
            let lambda = builder.literal("lambda", "λ").expect("lambda");
            builder
                .alternation("root", &[wildcard, lambda])
                .expect("alternation")
        }
        "canonical-character-set" => builder
            .character_set(
                "root",
                &[
                    SimplyCharacterSetMember::UnicodeProperty {
                        property: "General_Category".to_owned(),
                        value: Some("Letter".to_owned()),
                        negated: false,
                    },
                    SimplyCharacterSetMember::Builtin {
                        name: BuiltinClassName::Digit,
                        domain: None,
                        negated: false,
                    },
                    SimplyCharacterSetMember::Range {
                        start: 'A',
                        end: 'Z',
                    },
                    SimplyCharacterSetMember::Literal { value: '_' },
                ],
                false,
            )
            .expect("character set"),
        "capture-and-backreference" => {
            let body = builder.literal("body", "λ").expect("capture body");
            let capture = builder
                .capture("capture", "word", Some("word"), &body)
                .expect("capture");
            let reference = builder
                .backreference("reference", "word")
                .expect("backreference");
            builder
                .sequence("root", &[capture, reference])
                .expect("capture sequence")
        }
        "assertion-position-atomic" => {
            let start = builder
                .position("start", PositionKind::InputStart)
                .expect("start");
            let look_body = builder.literal("look-body", "a").expect("look body");
            let look = builder
                .lookaround(
                    "look",
                    LookaroundDirection::Ahead,
                    AssertionPolarity::Positive,
                    &look_body,
                )
                .expect("lookaround");
            let atomic_body = builder.literal("atomic-body", "b").expect("atomic body");
            let atomic = builder.atomic("atomic", &atomic_body).expect("atomic");
            let end = builder
                .position("end", PositionKind::InputEnd)
                .expect("end");
            builder
                .sequence("root", &[start, look, atomic, end])
                .expect("assertion sequence")
        }
        "all-repetition-modes" => {
            let a = builder.literal("a", "a").expect("a");
            let greedy = builder
                .repeat(
                    "greedy",
                    &a,
                    0,
                    RepetitionMaximum::Unbounded,
                    RepetitionMode::Greedy,
                )
                .expect("greedy");
            let b = builder.literal("b", "b").expect("b");
            let lazy = builder
                .repeat(
                    "lazy",
                    &b,
                    1,
                    RepetitionMaximum::Bounded(2),
                    RepetitionMode::Lazy,
                )
                .expect("lazy");
            let c = builder.literal("c", "c").expect("c");
            let possessive = builder
                .repeat(
                    "possessive",
                    &c,
                    1,
                    RepetitionMaximum::Bounded(1),
                    RepetitionMode::Possessive,
                )
                .expect("possessive");
            builder
                .sequence("root", &[greedy, lazy, possessive])
                .expect("repetition sequence")
        }
        "imported-node-provenance" => {
            let arguments = &request["steps"][0]["arguments"];
            let node: Node =
                serde_json::from_value(arguments["node"].clone()).expect("imported node");
            let sources: Vec<SourceDocument> =
                serde_json::from_value(arguments["sources"].clone()).expect("imported sources");
            builder
                .import_node("root", node, sources)
                .expect("node import")
        }
        "imported-program-mixed-provenance" => {
            let program: SemanticProgram =
                serde_json::from_value(request["steps"][0]["arguments"]["program"].clone())
                    .expect("imported program");
            let imported = builder
                .import_program("imported", program)
                .expect("program import");
            let suffix = builder.literal("suffix", "!").expect("suffix");
            builder
                .sequence("root", &[imported, suffix])
                .expect("mixed sequence")
        }
        "target-profile-is-compiler-routing" => {
            builder.literal("root", "x").expect("routing literal")
        }
        value => panic!("unexpected positive case {value}"),
    };
    (builder, root)
}

#[test]
fn all_authored_positive_cases_match_exact_programs_and_requests() {
    let suite: Value = serde_json::from_str(POSITIVE).expect("positive suite");
    let cases = suite["cases"].as_array().expect("positive cases");
    assert_eq!(9, cases.len());

    for case in cases {
        let case_id = case["case_id"].as_str().expect("case id");
        let request = &case["request"];
        let expected_program: SemanticProgram =
            serde_json::from_value(case["expected"]["semantic_program"].clone())
                .unwrap_or_else(|error| panic!("{case_id}: expected program: {error}"));
        let expected_request: CompileRequest =
            serde_json::from_value(case["expected"]["compile_request"].clone())
                .unwrap_or_else(|error| panic!("{case_id}: expected request: {error}"));
        let projection = SimplyCompileProjection {
            target_profile: expected_request.target_profile.clone(),
            requested_outputs: expected_request.requested_outputs.clone(),
            compiler_options: expected_request.compiler_options.clone(),
        };
        let (builder, root) = build_case(request, case_id);
        let actual = builder
            .finish_request(&root, projection)
            .unwrap_or_else(|errors| panic!("{case_id}: finish failed: {errors:?}"));
        assert_eq!(expected_request, actual, "{case_id}: request drift");
        let CompileInput::Semantic { program } = actual.input else {
            panic!("{case_id}: Simply must produce semantic input");
        };
        assert_eq!(expected_program, *program, "{case_id}: program drift");
    }
}

#[test]
fn all_stable_error_codes_keep_the_protocol_serialization() {
    let expected = [
        (SimplyErrorCode::InvalidArgument, "STRL-SIMPLY-0001"),
        (SimplyErrorCode::InvalidBounds, "STRL-SIMPLY-0002"),
        (SimplyErrorCode::DuplicateIdentity, "STRL-SIMPLY-0003"),
        (SimplyErrorCode::DuplicateCaptureName, "STRL-SIMPLY-0004"),
        (SimplyErrorCode::UnresolvedValue, "STRL-SIMPLY-0005"),
        (SimplyErrorCode::UnresolvedCapture, "STRL-SIMPLY-0006"),
        (SimplyErrorCode::ReusedValue, "STRL-SIMPLY-0007"),
        (SimplyErrorCode::IncompatibleImport, "STRL-SIMPLY-0008"),
        (SimplyErrorCode::InvalidProvenance, "STRL-SIMPLY-0009"),
        (SimplyErrorCode::UnsupportedConstruct, "STRL-SIMPLY-0010"),
        (SimplyErrorCode::InvalidCompileRequest, "STRL-SIMPLY-0011"),
        (SimplyErrorCode::ResourceLimit, "STRL-SIMPLY-0012"),
    ];
    for (code, serialized) in expected {
        assert_eq!(serialized, code.as_str());
        assert_eq!(
            format!("\"{serialized}\""),
            serde_json::to_string(&code).unwrap()
        );
    }
}

fn first_error<T: std::fmt::Debug>(
    result: Result<T, strling_kernel::SimplyErrors>,
) -> (SimplyErrorCode, String) {
    let errors = result.expect_err("operation must fail");
    assert_eq!(1, errors.errors.len());
    let error = errors.errors.into_iter().next().expect("one error");
    (error.code, error.path)
}

#[test]
fn typed_operations_return_stable_failures_without_partial_mutation() {
    let version = SpecificationVersion::try_from("1.0-draft.1").unwrap();
    assert_eq!(
        (
            SimplyErrorCode::InvalidArgument,
            "$.identity_namespace".to_owned()
        ),
        first_error(SimplyBuilder::new(
            "Bad",
            version.clone(),
            SimplyOptions::default()
        ))
    );

    let mut duplicate =
        SimplyBuilder::new("duplicate", version.clone(), SimplyOptions::default()).unwrap();
    let root = duplicate.literal("root", "a").unwrap();
    assert_eq!(
        (
            SimplyErrorCode::DuplicateIdentity,
            "$.steps[1].step_id".to_owned()
        ),
        first_error(duplicate.empty("root"))
    );
    duplicate
        .finish_program(&root)
        .expect("duplicate failure is atomic");

    let mut bounds =
        SimplyBuilder::new("bounds", version.clone(), SimplyOptions::default()).unwrap();
    let value = bounds.literal("value", "a").unwrap();
    assert_eq!(
        (
            SimplyErrorCode::InvalidBounds,
            "$.steps[1].arguments.max".to_owned()
        ),
        first_error(bounds.repeat(
            "bad",
            &value,
            2,
            RepetitionMaximum::Bounded(1),
            RepetitionMode::Greedy,
        ))
    );
    let valid = bounds
        .repeat(
            "root",
            &value,
            1,
            RepetitionMaximum::Bounded(2),
            RepetitionMode::Greedy,
        )
        .expect("failed bounds did not consume value");
    bounds.finish_program(&valid).expect("valid retry");

    let mut captures =
        SimplyBuilder::new("names", version.clone(), SimplyOptions::default()).unwrap();
    let first_body = captures.literal("first-body", "a").unwrap();
    let first = captures
        .capture("first", "first", Some("same"), &first_body)
        .unwrap();
    let second_body = captures.literal("second-body", "b").unwrap();
    assert_eq!(
        (
            SimplyErrorCode::DuplicateCaptureName,
            "$.steps[3].arguments.name".to_owned(),
        ),
        first_error(captures.capture("second", "second", Some("same"), &second_body))
    );
    let root = captures.sequence("root", &[first, second_body]).unwrap();
    captures
        .finish_program(&root)
        .expect("duplicate-name failure did not consume body");

    let mut left = SimplyBuilder::new("left", version.clone(), SimplyOptions::default()).unwrap();
    let foreign = left.literal("foreign", "x").unwrap();
    let mut right = SimplyBuilder::new("right", version.clone(), SimplyOptions::default()).unwrap();
    let right_root = right.literal("root", "y").unwrap();
    assert_eq!(
        (
            SimplyErrorCode::UnresolvedValue,
            "$.steps[1].arguments.value".to_owned(),
        ),
        first_error(right.atomic("bad", &foreign))
    );
    right
        .finish_program(&right_root)
        .expect("foreign-handle failure is atomic");

    let mut reused =
        SimplyBuilder::new("reuse", version.clone(), SimplyOptions::default()).unwrap();
    let a = reused.literal("a", "a").unwrap();
    let b = reused.literal("b", "b").unwrap();
    let root = reused.sequence("root", &[a.clone(), b]).unwrap();
    assert_eq!(
        (
            SimplyErrorCode::ReusedValue,
            "$.steps[3].arguments.value".to_owned(),
        ),
        first_error(reused.atomic("bad", &a))
    );
    reused
        .finish_program(&root)
        .expect("reused-handle failure is atomic");

    let mut unresolved =
        SimplyBuilder::new("reference", version.clone(), SimplyOptions::default()).unwrap();
    let reference = unresolved.backreference("root", "missing").unwrap();
    assert_eq!(
        (
            SimplyErrorCode::UnresolvedCapture,
            "$.steps[0].arguments.capture_key".to_owned(),
        ),
        first_error(unresolved.finish_program(&reference))
    );

    let positive: Value = serde_json::from_str(POSITIVE).unwrap();
    let imported: SemanticProgram = serde_json::from_value(
        fixture(&positive, "alternation-wildcard-options")["expected"]["semantic_program"].clone(),
    )
    .unwrap();
    let mut incompatible =
        SimplyBuilder::new("import", version.clone(), SimplyOptions::default()).unwrap();
    assert_eq!(
        (
            SimplyErrorCode::IncompatibleImport,
            "$.steps[0].arguments.program.case_matching".to_owned(),
        ),
        first_error(incompatible.import_program("root", imported))
    );

    let negative: Value = serde_json::from_str(NEGATIVE).unwrap();
    let invalid_origin = fixture(&negative, "unresolved-imported-origin");
    let node: Node =
        serde_json::from_value(invalid_origin["request"]["steps"][0]["arguments"]["node"].clone())
            .unwrap();
    let mut provenance =
        SimplyBuilder::new("provenance", version.clone(), SimplyOptions::default()).unwrap();
    assert_eq!(
        (
            SimplyErrorCode::InvalidProvenance,
            "$.root.origin.source_spans[0].source_id".to_owned(),
        ),
        first_error(provenance.import_node("root", node, Vec::new()))
    );
}

fn compiler_options() -> strling_kernel::protocol::CompilerOptions {
    serde_json::from_value(serde_json::json!({
        "partial_semantics": "forbid",
        "diagnostic_policy": { "minimum_severity": "warning" }
    }))
    .expect("compiler options")
}

#[test]
fn compile_projection_failures_are_explicit_and_target_routing_only() {
    let version = SpecificationVersion::try_from("1.0-draft.1").unwrap();
    let mut missing_profile =
        SimplyBuilder::new("profile", version.clone(), SimplyOptions::default()).unwrap();
    let root = missing_profile.literal("root", "x").unwrap();
    assert_eq!(
        (
            SimplyErrorCode::InvalidCompileRequest,
            "$.compile.target_profile".to_owned(),
        ),
        first_error(missing_profile.finish_request(
            &root,
            SimplyCompileProjection {
                target_profile: None,
                requested_outputs: vec![RequestedOutput::TargetArtifact],
                compiler_options: compiler_options(),
            },
        ))
    );

    let mut limited = SimplyBuilder::new("limit", version, SimplyOptions::default()).unwrap();
    let a = limited.literal("a", "a").unwrap();
    let root = limited.atomic("root", &a).unwrap();
    let mut options = compiler_options();
    options.resource_limits = Some(ResourceLimits {
        max_semantic_nodes: Some(1),
        max_diagnostics: None,
    });
    assert_eq!(
        (
            SimplyErrorCode::ResourceLimit,
            "$.compile.compiler_options.resource_limits.max_semantic_nodes".to_owned(),
        ),
        first_error(limited.finish_request(
            &root,
            SimplyCompileProjection {
                target_profile: None,
                requested_outputs: vec![RequestedOutput::Semantic],
                compiler_options: options,
            },
        ))
    );
}
