use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::diagnostic_generation::generate_diagnostics;
use strling_kernel::ecmascript_lowering::lower_ecmascript;
use strling_kernel::ecmascript_serialization::serialize_ecmascript;
use strling_kernel::explanation::{explain_semantics, ExplanationDocument};
use strling_kernel::no_match_explanation::{explain_no_match, NoMatchExecutionMode, NoMatchLimits};
use strling_kernel::normalization::normalize;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::protocol::CompileInput;
use strling_kernel::regex_frontend;
use strling_kernel::safety_analysis::analyze_safety;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::semantic_conversion::{
    convert_semantic_program, SemanticConversionDestination, SemanticConversionIssueCode,
    SemanticConversionOutput, SemanticConversionStatus, SemanticEquivalenceStatus,
};
use strling_kernel::semantic_frontend;
use strling_kernel::simply::{decode_simply_builder_request, replay_simply_builder_request};
use strling_kernel::source::SourceDocument;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{TargetArtifact, TargetProfile};

const ECMASCRIPT: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

fn repository_path(path: impl AsRef<Path>) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join(path)
}

fn repository_json(path: impl AsRef<Path>) -> Value {
    let path = repository_path(path);
    let text = fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    serde_json::from_str(&text).unwrap_or_else(|error| panic!("parse {}: {error}", path.display()))
}

fn source_document(source_id: &str, text: &str) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": source_id,
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": regex_frontend::FRONTEND_ID,
            "dialect_version": regex_frontend::DIALECT_VERSION
        },
        "display_name": "migration-explanation-certification.regex",
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": "text/strling-regex",
            "text": text
        },
        "provenance": {
            "kind": "imported",
            "description": "P15-T04 joined certification evidence"
        }
    }))
    .expect("regex source document")
}

fn semantic_source_document(source_id: &str, text: &str) -> SourceDocument {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "source_id": source_id,
        "specification_version": "1.0-draft.1",
        "frontend": {
            "id": semantic_frontend::FRONTEND_ID,
            "dialect_version": semantic_frontend::DIALECT_VERSION
        },
        "display_name": "migration-explanation-certification.semantic",
        "content": {
            "kind": "inline",
            "encoding": "utf-8",
            "media_type": semantic_frontend::MEDIA_TYPE,
            "text": text
        },
        "provenance": {
            "kind": "imported",
            "description": "P15-T04 destination reconstruction"
        }
    }))
    .expect("Semantic STRling source document")
}

fn explain(input: &SemanticProgram) -> (SemanticProgram, ExplanationDocument) {
    let normalized = normalize(input).expect("normalize");
    let foundational = analyze(&normalized).expect("foundational analysis");
    let structural = analyze_structure(&normalized, &foundational).expect("structural analysis");
    let safety = analyze_safety(&normalized, &foundational, &structural).expect("safety analysis");
    let diagnostics = generate_diagnostics(&normalized, &foundational, &structural, &safety)
        .expect("diagnostic generation");
    let explanation = explain_semantics(
        &normalized,
        &foundational,
        &structural,
        &safety,
        &diagnostics,
    )
    .expect("semantic explanation");
    (normalized, explanation)
}

fn gather_identities(
    value: &Value,
    nodes: &mut BTreeMap<String, String>,
    captures: &mut BTreeMap<String, String>,
) {
    match value {
        Value::Object(object) => {
            if let Some(identity) = object.get("node_id").and_then(Value::as_str) {
                let replacement = format!("node:alpha/{}", nodes.len() + 1);
                nodes.entry(identity.to_owned()).or_insert(replacement);
            }
            if let Some(identity) = object.get("capture_id").and_then(Value::as_str) {
                let replacement = format!("capture:alpha/{}", captures.len() + 1);
                captures.entry(identity.to_owned()).or_insert(replacement);
            }
            for child in object.values() {
                gather_identities(child, nodes, captures);
            }
        }
        Value::Array(items) => {
            for item in items {
                gather_identities(item, nodes, captures);
            }
        }
        _ => {}
    }
}

fn replace_representation(
    value: &mut Value,
    nodes: &BTreeMap<String, String>,
    captures: &BTreeMap<String, String>,
) {
    match value {
        Value::Object(object) => {
            for excluded in [
                "origin",
                "origins",
                "sources",
                "source_id",
                "source_range",
                "source_span",
            ] {
                object.remove(excluded);
            }
            for child in object.values_mut() {
                replace_representation(child, nodes, captures);
            }
        }
        Value::Array(items) => {
            for item in items {
                replace_representation(item, nodes, captures);
            }
        }
        Value::String(text) => {
            let mut identities: Vec<_> = nodes.iter().chain(captures.iter()).collect();
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

fn alpha_projection(input: &SemanticProgram) -> Value {
    let mut value = serde_json::to_value(input).expect("serialize Semantic IR");
    let mut nodes = BTreeMap::new();
    let mut captures = BTreeMap::new();
    gather_identities(&value, &mut nodes, &mut captures);
    replace_representation(&mut value, &nodes, &captures);
    value
}

fn reconstruct_semantic(text: &str, case_id: &str) -> SemanticProgram {
    let identity = case_id
        .strip_prefix("case:convergence/")
        .unwrap_or(case_id)
        .replace('/', ".");
    semantic_frontend::parse(&semantic_source_document(
        &format!("src:certification.semantic.{identity}"),
        text,
    ))
    .unwrap_or_else(|errors| panic!("{case_id}: Semantic STRling reconstruction: {errors:?}"))
    .program
}

fn reconstruct_simply(request: &impl serde::Serialize, case_id: &str) -> SemanticProgram {
    let encoded = serde_json::to_string(request).expect("serialize generated Simply request");
    let decoded = decode_simply_builder_request(&encoded)
        .unwrap_or_else(|error| panic!("{case_id}: decode generated Simply request: {error}"));
    let replay = replay_simply_builder_request(decoded)
        .unwrap_or_else(|errors| panic!("{case_id}: replay generated Simply request: {errors:?}"));
    let CompileInput::Semantic { program } = replay.input else {
        panic!("{case_id}: generated Simply request must project Semantic IR")
    };
    *program
}

fn find_frontend_case<'a>(corpus: &'a Value, case_id: &str) -> &'a Value {
    corpus["cases"]
        .as_array()
        .expect("frontend case array")
        .iter()
        .find(|case| case["id"] == case_id)
        .unwrap_or_else(|| panic!("missing frontend case {case_id}"))
}

fn parse_round_trip_case(corpus: &Value, case_id: &str) -> SemanticProgram {
    let case = find_frontend_case(corpus, case_id);
    let source = case["legacy"]["source"]
        .as_str()
        .unwrap_or_else(|| panic!("{case_id}: legacy source"));
    let identity = case_id
        .strip_prefix("case:convergence/")
        .unwrap_or(case_id)
        .replace('/', ".");
    regex_frontend::parse(&source_document(
        &format!("src:certification.regex.{identity}"),
        source,
    ))
    .unwrap_or_else(|errors| panic!("{case_id}: regex import: {errors:?}"))
    .program
}

fn ecmascript_artifact(input: &SemanticProgram) -> TargetArtifact {
    let target: TargetProfile = serde_json::from_str(ECMASCRIPT).expect("ECMAScript profile");
    let foundational = analyze(input).expect("foundational analysis");
    let structural = analyze_structure(input, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(input, &foundational, &structural, &target)
        .expect("capability evaluation");
    let portability = plan_portability(input, &foundational, &structural, &target, &evaluation)
        .expect("portability planning");
    let lowering = lower_ecmascript(input, &target, &portability).expect("ECMAScript lowering");
    serialize_ecmascript(&lowering).expect("ECMAScript serialization")
}

fn mutate_first_kind(
    value: &mut Value,
    kind: &str,
    mutate: &impl Fn(&mut serde_json::Map<String, Value>),
) -> bool {
    match value {
        Value::Object(object) => {
            if object.get("kind").and_then(Value::as_str) == Some(kind) {
                mutate(object);
                return true;
            }
            object
                .values_mut()
                .any(|child| mutate_first_kind(child, kind, mutate))
        }
        Value::Array(items) => items
            .iter_mut()
            .any(|child| mutate_first_kind(child, kind, mutate)),
        _ => false,
    }
}

fn capture_definition_ids(value: &Value, captures: &mut Vec<String>) {
    match value {
        Value::Object(object) => {
            if object.get("kind").and_then(Value::as_str) == Some("capture") {
                captures.push(
                    object["capture_id"]
                        .as_str()
                        .expect("capture definition identity")
                        .to_owned(),
                );
            }
            for child in object.values() {
                capture_definition_ids(child, captures);
            }
        }
        Value::Array(items) => {
            for item in items {
                capture_definition_ids(item, captures);
            }
        }
        _ => {}
    }
}

fn normalized_mutation(
    input: &SemanticProgram,
    kind: &str,
    mutate: impl Fn(&mut serde_json::Map<String, Value>),
) -> SemanticProgram {
    let mut value = serde_json::to_value(input).expect("serialize mutation input");
    assert!(mutate_first_kind(&mut value, kind, &mutate));
    let mutated: SemanticProgram = serde_json::from_value(value).expect("typed mutation");
    normalize(&mutated).expect("valid semantic mutation")
}

#[test]
fn every_regex_import_explains_and_round_trips_through_both_destinations() {
    let manifest = repository_json("tests/certification/migration-explanation/1.0/manifest.json");
    let corpus = repository_json("tests/convergence/frontend-convergence.json");
    let evidence =
        repository_json("tests/conformance/evidence/shared-cross-engine-observations.json");
    let observations = evidence["observations"]
        .as_array()
        .expect("target observations");
    let cases = manifest["corpora"]["round_trip_cases"]
        .as_array()
        .expect("round-trip cases");
    assert_eq!(cases.len(), 9);

    for case in cases {
        let case_id = case["source_case_id"].as_str().expect("source case ID");
        let imported = parse_round_trip_case(&corpus, case_id);
        let (normalized, explanation) = explain(&imported);
        let repeated_explanation = explain(&imported).1;
        assert_eq!(
            serde_json::to_vec(&explanation).expect("serialize explanation"),
            serde_json::to_vec(&repeated_explanation).expect("serialize repeated explanation"),
            "{case_id}: semantic explanation is nondeterministic"
        );

        let semantic = convert_semantic_program(
            &normalized,
            SemanticConversionDestination::SemanticStrling,
            Some(&explanation),
        )
        .unwrap_or_else(|errors| panic!("{case_id}: Semantic STRling conversion: {errors:?}"));
        let repeated_semantic = convert_semantic_program(
            &normalized,
            SemanticConversionDestination::SemanticStrling,
            Some(&explanation),
        )
        .expect("repeated Semantic STRling conversion");
        assert_eq!(semantic.status, SemanticConversionStatus::Exact);
        assert_eq!(
            semantic.equivalence.status,
            SemanticEquivalenceStatus::Proven
        );
        assert_eq!(
            &semantic.equivalence.source_fingerprint,
            semantic
                .equivalence
                .reconstructed_fingerprint
                .as_ref()
                .expect("exact proof fingerprint")
        );
        assert_eq!(
            serde_json::to_vec(&semantic).expect("serialize Semantic STRling conversion"),
            serde_json::to_vec(&repeated_semantic).expect("serialize repeated conversion"),
            "{case_id}: Semantic STRling conversion is nondeterministic"
        );
        let Some(SemanticConversionOutput::SemanticStrling { text, .. }) = semantic.output.as_ref()
        else {
            panic!("{case_id}: expected Semantic STRling output")
        };
        let semantic_reconstructed = normalize(&reconstruct_semantic(text, case_id))
            .expect("normalize Semantic STRling reconstruction");
        assert_eq!(
            alpha_projection(&normalized),
            alpha_projection(&semantic_reconstructed),
            "{case_id}: Semantic STRling reconstruction changed semantics"
        );

        let simply = convert_semantic_program(
            &normalized,
            SemanticConversionDestination::SimplyBuilder,
            Some(&explanation),
        )
        .unwrap_or_else(|errors| panic!("{case_id}: Simply conversion: {errors:?}"));
        assert_eq!(simply.status, SemanticConversionStatus::Exact);
        assert_eq!(simply.equivalence.status, SemanticEquivalenceStatus::Proven);
        assert_eq!(
            &simply.equivalence.source_fingerprint,
            simply
                .equivalence
                .reconstructed_fingerprint
                .as_ref()
                .expect("exact proof fingerprint")
        );
        let Some(SemanticConversionOutput::SimplyBuilder { request, .. }) = simply.output.as_ref()
        else {
            panic!("{case_id}: expected Simply output")
        };
        let simply_reconstructed = normalize(&reconstruct_simply(request, case_id))
            .expect("normalize Simply reconstruction");
        assert_eq!(
            alpha_projection(&normalized),
            alpha_projection(&simply_reconstructed),
            "{case_id}: Simply reconstruction changed semantics"
        );

        let no_match = explain_no_match(
            &normalized,
            &explanation,
            "certification-subject",
            NoMatchExecutionMode::Search,
            NoMatchLimits::default(),
        )
        .unwrap_or_else(|errors| panic!("{case_id}: no-match explanation: {errors:?}"));
        let repeated_no_match = explain_no_match(
            &normalized,
            &explanation,
            "certification-subject",
            NoMatchExecutionMode::Search,
            NoMatchLimits::default(),
        )
        .expect("repeated no-match explanation");
        let serialized = serde_json::to_vec(&no_match).expect("serialize no-match explanation");
        assert_eq!(
            serialized,
            serde_json::to_vec(&repeated_no_match)
                .expect("serialize repeated no-match explanation")
        );
        assert!(!String::from_utf8(serialized)
            .expect("UTF-8 JSON")
            .contains("certification-subject"));

        for target_case_id in case["target_evidence_case_ids"]
            .as_array()
            .expect("target evidence IDs")
        {
            let target_case_id = target_case_id.as_str().expect("target evidence ID");
            assert_eq!(
                observations
                    .iter()
                    .filter(|item| item["case_id"] == target_case_id)
                    .count(),
                5,
                "{case_id}: incomplete five-profile evidence for {target_case_id}"
            );
        }
    }
}

#[test]
fn controlled_semantic_mutations_cannot_hide_inside_alpha_or_target_projections() {
    let manifest = repository_json("tests/certification/migration-explanation/1.0/manifest.json");
    let mutation_ids = manifest["mutations"]
        .as_array()
        .expect("mutation array")
        .iter()
        .map(|entry| entry["id"].as_str().expect("mutation ID"))
        .collect::<BTreeSet<_>>();
    let corpus = repository_json("tests/convergence/frontend-convergence.json");

    assert!(mutation_ids.contains("mutation/capture-relationship"));
    let capture = normalize(&parse_round_trip_case(
        &corpus,
        "case:convergence/captures-and-references",
    ))
    .expect("normalize capture case");
    let mut capture_ids = Vec::new();
    capture_definition_ids(
        &serde_json::to_value(&capture).expect("serialize capture case"),
        &mut capture_ids,
    );
    assert_eq!(capture_ids.len(), 2);
    let retargeted_capture = capture_ids[1].clone();
    let capture_mutation = normalized_mutation(&capture, "backreference", |node| {
        node.insert(
            "capture_id".to_owned(),
            Value::String(retargeted_capture.clone()),
        );
    });
    assert_ne!(
        alpha_projection(&capture),
        alpha_projection(&capture_mutation)
    );

    assert!(mutation_ids.contains("mutation/branch-order"));
    let alternation = normalize(&parse_round_trip_case(
        &corpus,
        "case:convergence/composition-and-empty",
    ))
    .expect("normalize alternation case");
    let alternation_mutation = normalized_mutation(&alternation, "alternation", |node| {
        node.get_mut("branches")
            .and_then(Value::as_array_mut)
            .expect("alternation branches")
            .reverse();
    });
    assert_ne!(
        alpha_projection(&alternation),
        alpha_projection(&alternation_mutation)
    );

    assert!(mutation_ids.contains("mutation/repetition-bound"));
    let repetition = normalize(&parse_round_trip_case(
        &corpus,
        "case:convergence/repetition-modes",
    ))
    .expect("normalize repetition case");
    let repetition_mutation = normalized_mutation(&repetition, "repeat", |node| {
        node.insert("min".to_owned(), Value::from(7));
    });
    assert_ne!(
        alpha_projection(&repetition),
        alpha_projection(&repetition_mutation)
    );

    assert!(mutation_ids.contains("mutation/case-option"));
    let options = normalize(&parse_round_trip_case(
        &corpus,
        "case:convergence/flags-layout-and-escapes",
    ))
    .expect("normalize options case");
    let mut options_value = serde_json::to_value(&options).expect("serialize options case");
    options_value["case_matching"] = Value::String("sensitive".to_owned());
    let options_mutation: SemanticProgram =
        serde_json::from_value(options_value).expect("typed options mutation");
    let options_mutation = normalize(&options_mutation).expect("normalize options mutation");
    assert_ne!(
        alpha_projection(&options),
        alpha_projection(&options_mutation)
    );
    let original_artifact = ecmascript_artifact(&options);
    let mutated_artifact = ecmascript_artifact(&options_mutation);
    assert_ne!(original_artifact.pattern, mutated_artifact.pattern);
}

#[test]
fn partial_unsupported_and_resource_evidence_remain_explicit() {
    let manifest = repository_json("tests/certification/migration-explanation/1.0/manifest.json");
    assert_eq!(manifest["anti_shrinkage"]["conversion_cases"], 4);
    assert_eq!(manifest["anti_shrinkage"]["no_match_cases"], 24);
    assert_eq!(manifest["anti_shrinkage"]["pathological_cases"], 9);

    let unnamed_capture: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {
            "node_id": "node:partial.capture",
            "kind": "capture",
            "capture_id": "capture:partial",
            "body": {"node_id": "node:partial.body", "kind": "literal", "text": "a"}
        }
    }))
    .expect("partial semantic program");
    let partial = convert_semantic_program(
        &unnamed_capture,
        SemanticConversionDestination::SemanticStrling,
        None,
    )
    .expect("partial conversion");
    assert_eq!(partial.status, SemanticConversionStatus::Partial);
    assert!(partial.output.is_some());
    assert!(partial.equivalence.reconstructed_fingerprint.is_none());
    assert_eq!(
        partial
            .issues
            .iter()
            .map(|issue| issue.code)
            .collect::<Vec<_>>(),
        [
            SemanticConversionIssueCode::CaptureNameSubstituted,
            SemanticConversionIssueCode::ManualCaptureNameRequired,
        ]
    );

    let forward_reference: SemanticProgram = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": {
            "node_id": "node:unsupported.root",
            "kind": "sequence",
            "items": [
                {"node_id": "node:unsupported.ref", "kind": "backreference", "capture_id": "capture:later"},
                {
                    "node_id": "node:unsupported.capture",
                    "kind": "capture",
                    "capture_id": "capture:later",
                    "name": "later",
                    "body": {"node_id": "node:unsupported.body", "kind": "literal", "text": "a"}
                }
            ]
        }
    }))
    .expect("unsupported semantic program");
    let unsupported = convert_semantic_program(
        &forward_reference,
        SemanticConversionDestination::SemanticStrling,
        None,
    )
    .expect("unsupported conversion result");
    assert_eq!(unsupported.status, SemanticConversionStatus::Unsupported);
    assert!(unsupported.output.is_none());
    assert_eq!(
        unsupported.issues[0].code,
        SemanticConversionIssueCode::ForwardBackreferenceUnsupported
    );
}
