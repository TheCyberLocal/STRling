use serde_json::{json, Value};
use strling_kernel::capability_evaluation::evaluate_capabilities;
use strling_kernel::ecmascript_lowering::lower_ecmascript;
use strling_kernel::ecmascript_serialization::serialize_ecmascript;
use strling_kernel::portability_planning::plan_portability;
use strling_kernel::protocol::{CompileOutcome, CompileRequest};
use strling_kernel::python_re_lowering::lower_python_re;
use strling_kernel::python_re_serialization::serialize_python_re;
use strling_kernel::semantic::SemanticProgram;
use strling_kernel::semantic_analysis::analyze;
use strling_kernel::structural_analysis::analyze_structure;
use strling_kernel::target::{PortabilityStatus, TargetArtifact, TargetProfile};
use strling_kernel::target_lowering::lower_pcre2;
use strling_kernel::target_serialization::serialize_pcre2;
use strling_kernel::validation::{from_json, Validate};
use strling_kernel::{compile, compile_with_evidence};

const PROFILES: &[(&str, &str)] = &[
    (
        "profile:pcre2/10.42",
        include_str!("../../spec/targets/profiles/pcre2-10.42.json"),
    ),
    (
        "profile:pcre2/10.43",
        include_str!("../../spec/targets/profiles/pcre2-10.43.json"),
    ),
    (
        "profile:ecmascript/2024",
        include_str!("../../spec/targets/profiles/ecmascript-2024.json"),
    ),
    (
        "profile:python-re/3.11",
        include_str!("../../spec/targets/profiles/python-re-3.11.json"),
    ),
    (
        "profile:python-re/3.11-bytes",
        include_str!("../../spec/targets/profiles/python-re-3.11-bytes.json"),
    ),
];

fn program(root: Value) -> SemanticProgram {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "normalization": "canonical-v1",
        "case_matching": "sensitive",
        "root": root
    }))
    .expect("test Semantic IR")
}

fn request(program: &SemanticProgram, profile: &TargetProfile) -> CompileRequest {
    let mut request: CompileRequest = serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": { "kind": "semantic", "program": program },
        "requested_outputs": ["semantic", "analysis", "portability", "target_artifact"],
        "compiler_options": {
            "partial_semantics": "forbid",
            "diagnostic_policy": { "minimum_severity": "hint" }
        }
    }))
    .expect("compile request");
    request.target_profile = Some(profile.reference().expect("profile reference"));
    request
}

fn direct_artifact(program: &SemanticProgram, profile: &TargetProfile) -> TargetArtifact {
    let foundational = analyze(program).expect("foundational analysis");
    let structural = analyze_structure(program, &foundational).expect("structural analysis");
    let evaluation = evaluate_capabilities(program, &foundational, &structural, profile)
        .expect("capability evaluation");
    let plan = plan_portability(program, &foundational, &structural, profile, &evaluation)
        .expect("portability plan");
    match profile.engine.id.as_str() {
        "pcre2" => serialize_pcre2(&lower_pcre2(program, profile, &plan).expect("PCRE2 lowering"))
            .expect("PCRE2 serialization"),
        "ecmascript" => serialize_ecmascript(
            &lower_ecmascript(program, profile, &plan).expect("ECMAScript lowering"),
        )
        .expect("ECMAScript serialization"),
        "python_re" => serialize_python_re(
            &lower_python_re(program, profile, &plan).expect("Python re lowering"),
        )
        .expect("Python re serialization"),
        engine => panic!("unexpected governed engine {engine}"),
    }
}

#[test]
fn facade_artifacts_equal_each_registered_lowerer_serializer_path() {
    let semantic = program(json!({
        "node_id": "node:orchestration.root",
        "kind": "sequence",
        "items": [
            { "node_id": "node:orchestration.literal", "kind": "literal", "text": "a.b" },
            {
                "node_id": "node:orchestration.repeat",
                "kind": "repeat",
                "body": {
                    "node_id": "node:orchestration.repeat.body",
                    "kind": "literal",
                    "text": "x"
                },
                "min": 1,
                "max": 3,
                "mode": "greedy"
            }
        ]
    }));

    for (expected_id, fixture) in PROFILES {
        let profile: TargetProfile = from_json(fixture).expect("governed profile");
        assert_eq!(profile.profile_id.as_str(), *expected_id);
        let request = request(&semantic, &profile);

        let first = compile_with_evidence(&request, Some(&profile)).expect("facade output");
        let second = compile_with_evidence(&request, Some(&profile)).expect("repeated output");
        let compatibility = compile(&request, Some(&profile)).expect("compatibility facade");

        assert_eq!(first, second, "{expected_id} must be deterministic");
        assert_eq!(first.result, compatibility);
        assert_eq!(first.result.outcome, CompileOutcome::Succeeded);
        assert_eq!(
            first.result.artifact.as_ref(),
            Some(&direct_artifact(&semantic, &profile)),
            "{expected_id} facade artifact must equal the certified direct path"
        );
        assert!(first.explanation.is_some());
        assert_eq!(
            serde_json::to_vec(&first.explanation).expect("explanation bytes"),
            serde_json::to_vec(&second.explanation).expect("repeated explanation bytes")
        );
        first.result.validate().expect("result validates");
    }
}

#[test]
fn unsupported_artifact_is_explicit_and_keeps_completed_explanation() {
    let profile: TargetProfile = from_json(include_str!(
        "../../spec/targets/profiles/python-re-3.11.json"
    ))
    .expect("Python re profile");
    let semantic = program(json!({
        "node_id": "node:orchestration.unsupported",
        "kind": "lookaround",
        "direction": "behind",
        "polarity": "positive",
        "body": {
            "node_id": "node:orchestration.unsupported.body",
            "kind": "alternation",
            "branches": [
                { "node_id": "node:orchestration.short", "kind": "literal", "text": "x" },
                { "node_id": "node:orchestration.long", "kind": "literal", "text": "yyy" }
            ]
        }
    }));
    let request = request(&semantic, &profile);

    let output = compile_with_evidence(&request, Some(&profile)).expect("unsupported result");

    assert_eq!(output.result.outcome, CompileOutcome::Failed);
    assert_eq!(
        output.result.portability.as_ref().map(|value| value.status),
        Some(PortabilityStatus::Unsupported)
    );
    assert!(output.result.artifact.is_none());
    assert!(output.explanation.is_some());
    assert!(output
        .result
        .diagnostics
        .iter()
        .any(|diagnostic| diagnostic.code.as_str() == "STRL-PROTOCOL-0005"));
    assert_eq!(
        output.result,
        compile(&request, Some(&profile)).expect("compatibility facade")
    );
    output.result.validate().expect("result validates");
}
