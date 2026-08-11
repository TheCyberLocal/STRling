use serde_json::{json, Value};
use strling_kernel::capability_evaluation::MAX_CAPABILITY_REQUIREMENTS;
use strling_kernel::diagnostic::DiagnosticCategory;
use strling_kernel::kernel::{
    MAX_KERNEL_SEMANTIC_DEPTH, MAX_KERNEL_SEMANTIC_NODES, MAX_REQUEST_CONTRACT_BYTES,
    MAX_TARGET_PROFILE_BYTES, RESOURCE_EXHAUSTED_DIAGNOSTIC,
};
use strling_kernel::protocol::{
    CompileInput, CompileOutcome, CompileRequest, CompileResult, ResourceLimits,
};
use strling_kernel::semantic::Node;
use strling_kernel::source::{NodeId, SourceContent};
use strling_kernel::target::TargetProfile;
use strling_kernel::validation::{from_json, Validate};
use strling_kernel::{compile, KernelCompileError};

const SOURCE_REQUEST: &str =
    include_str!("../../spec/contracts/1.0/examples/compile-request/source-success.json");
const ECMASCRIPT_2024: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

fn semantic_request(root: Value, outputs: Vec<&str>) -> CompileRequest {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": {
            "kind": "semantic",
            "program": {
                "contract_version": "1.0.0",
                "specification_version": "1.0-draft.1",
                "normalization": "canonical-v1",
                "case_matching": "sensitive",
                "root": root
            }
        },
        "requested_outputs": outputs,
        "compiler_options": {
            "partial_semantics": "forbid",
            "diagnostic_policy": { "minimum_severity": "hint" }
        }
    }))
    .expect("semantic request shape")
}

fn minimal_request() -> CompileRequest {
    semantic_request(
        json!({
            "node_id": "node:resource.minimal",
            "kind": "literal",
            "text": "x"
        }),
        vec!["semantic"],
    )
}

fn set_limits(request: &mut CompileRequest, nodes: Option<u64>, diagnostics: Option<u64>) {
    request.compiler_options.resource_limits = Some(ResourceLimits {
        max_semantic_nodes: nodes,
        max_diagnostics: diagnostics,
    });
}

fn assert_resource_failure(result: &CompileResult) {
    assert_eq!(result.outcome, CompileOutcome::Failed);
    assert!(result.semantic_result.is_none());
    assert!(result.analysis.is_none());
    assert!(result.portability.is_none());
    assert!(result.artifact.is_none());
    assert_eq!(result.diagnostics.len(), 1);
    assert_eq!(
        result.diagnostics[0].code.as_str(),
        RESOURCE_EXHAUSTED_DIAGNOSTIC
    );
    assert_eq!(
        result.diagnostics[0].category,
        DiagnosticCategory::ResourceLimit
    );
    result.validate().expect("resource result validates");
}

fn nested_request(depth: usize) -> CompileRequest {
    let mut request = minimal_request();
    let mut root = Node::Empty {
        node_id: NodeId::try_from("node:resource.depth.0").expect("node id"),
        origin: None,
    };
    for index in 1..depth {
        root = Node::Atomic {
            node_id: NodeId::try_from(format!("node:resource.depth.{index}")).expect("node id"),
            origin: None,
            body: Box::new(root),
        };
    }
    let CompileInput::Semantic { program } = &mut request.input else {
        panic!("semantic input");
    };
    program.root = root;
    request
}

fn wide_request(nodes: usize) -> CompileRequest {
    assert!(nodes >= 3);
    let items = (0..nodes - 1)
        .map(|index| Node::Empty {
            node_id: NodeId::try_from(format!("node:resource.wide.{index}")).expect("node id"),
            origin: None,
        })
        .collect();
    let mut request = minimal_request();
    let CompileInput::Semantic { program } = &mut request.input else {
        panic!("semantic input");
    };
    program.root = Node::Sequence {
        node_id: NodeId::try_from("node:resource.wide.root").expect("node id"),
        origin: None,
        items,
    };
    request
}

fn source_request_at_size(target: usize) -> CompileRequest {
    let mut request: CompileRequest = from_json(SOURCE_REQUEST).expect("source request");
    let current = serde_json::to_vec(&request)
        .expect("serialize request")
        .len();
    let CompileInput::Source { document } = &mut request.input else {
        panic!("source input");
    };
    let SourceContent::Inline { text, .. } = &mut document.content else {
        panic!("inline source");
    };
    let new_length = target
        .checked_sub(current)
        .and_then(|difference| difference.checked_add(text.len()))
        .expect("target must fit");
    *text = "x".repeat(new_length);
    assert_eq!(
        serde_json::to_vec(&request)
            .expect("serialize request")
            .len(),
        target
    );
    request
}

fn profile_at_size(target: usize) -> TargetProfile {
    let mut profile: TargetProfile = from_json(ECMASCRIPT_2024).expect("profile");
    let current = serde_json::to_vec(&profile)
        .expect("serialize profile")
        .len();
    let additional = target.checked_sub(current).expect("target must fit");
    profile
        .evidence
        .last_mut()
        .expect("profile evidence")
        .locator
        .push_str(&"x".repeat(additional));
    assert_eq!(
        serde_json::to_vec(&profile)
            .expect("serialize profile")
            .len(),
        target
    );
    profile
}

fn targeted_request(root: Value, profile: &TargetProfile) -> CompileRequest {
    let mut request = semantic_request(root, vec!["portability"]);
    request.target_profile = Some(profile.reference().expect("profile reference"));
    request
}

fn unicode_set_request(requirements: usize, profile: &TargetProfile) -> CompileRequest {
    let members: Vec<_> = (0..requirements)
        .map(|index| {
            let scalar = char::from_u32(0x1000 + u32::try_from(index).expect("index"))
                .expect("unicode scalar");
            json!({"kind": "literal", "value": scalar.to_string()})
        })
        .collect();
    targeted_request(
        json!({
            "node_id": "node:resource.requirements",
            "kind": "character_set",
            "negated": false,
            "members": members
        }),
        profile,
    )
}

#[test]
fn caller_semantic_node_limit_accepts_exact_and_rejects_one_over() {
    let mut exact = minimal_request();
    set_limits(&mut exact, Some(1), None);
    let exact_result = compile(&exact, None).expect("exact caller limit");
    assert_eq!(exact_result.outcome, CompileOutcome::Succeeded);

    let mut over = nested_request(2);
    set_limits(&mut over, Some(1), None);
    let over_result = compile(&over, None).expect("resource result");
    assert_resource_failure(&over_result);
    assert!(over_result.diagnostics[0].message.contains("observed 2"));
}

#[test]
fn invalid_zero_caller_limit_remains_a_typed_contract_failure() {
    let mut request = minimal_request();
    set_limits(&mut request, Some(0), None);

    assert!(matches!(
        compile(&request, None),
        Err(KernelCompileError::InvalidRequest(_))
    ));
}

#[test]
fn semantic_depth_hard_limit_accepts_exact_and_rejects_one_over() {
    let exact = nested_request(MAX_KERNEL_SEMANTIC_DEPTH);
    assert_eq!(
        compile(&exact, None).expect("exact depth").outcome,
        CompileOutcome::Succeeded
    );

    let over = nested_request(MAX_KERNEL_SEMANTIC_DEPTH + 1);
    assert_resource_failure(&compile(&over, None).expect("depth exhaustion"));
}

#[test]
fn semantic_node_hard_limit_accepts_exact_and_rejects_one_over() {
    let exact = wide_request(MAX_KERNEL_SEMANTIC_NODES);
    assert_eq!(
        compile(&exact, None).expect("exact node ceiling").outcome,
        CompileOutcome::Succeeded
    );

    let over = wide_request(MAX_KERNEL_SEMANTIC_NODES + 1);
    assert_resource_failure(&compile(&over, None).expect("node exhaustion"));
}

#[test]
fn diagnostic_limit_accepts_exact_and_rejects_one_over_without_truncation() {
    let root = json!({
        "node_id": "node:resource.diagnostics",
        "kind": "sequence",
        "items": [
            {
                "node_id": "node:resource.diagnostics.first",
                "kind": "repeat",
                "body": {
                    "node_id": "node:resource.diagnostics.first.empty",
                    "kind": "empty"
                },
                "min": 0,
                "max": null,
                "mode": "greedy"
            },
            {
                "node_id": "node:resource.diagnostics.second",
                "kind": "repeat",
                "body": {
                    "node_id": "node:resource.diagnostics.second.empty",
                    "kind": "empty"
                },
                "min": 0,
                "max": null,
                "mode": "greedy"
            }
        ]
    });
    let mut exact = semantic_request(root.clone(), vec!["analysis"]);
    set_limits(&mut exact, None, Some(2));
    let exact_result = compile(&exact, None).expect("exact diagnostic limit");
    assert_eq!(exact_result.diagnostics.len(), 2);
    assert_eq!(exact_result.outcome, CompileOutcome::Succeeded);

    let mut over = semantic_request(root, vec!["analysis"]);
    set_limits(&mut over, None, Some(1));
    let over_result = compile(&over, None).expect("diagnostic exhaustion");
    assert_resource_failure(&over_result);
}

#[test]
fn request_byte_limit_accepts_exact_and_rejects_one_over() {
    let exact = source_request_at_size(MAX_REQUEST_CONTRACT_BYTES);
    let exact_result = compile(&exact, None).expect("exact request bytes");
    assert_eq!(
        exact_result.diagnostics[0].code.as_str(),
        "STRL-PROTOCOL-0002"
    );

    let over = source_request_at_size(MAX_REQUEST_CONTRACT_BYTES + 1);
    assert_resource_failure(&compile(&over, None).expect("request byte exhaustion"));
}

#[test]
fn target_profile_byte_limit_accepts_exact_and_rejects_one_over() {
    let exact_profile = profile_at_size(MAX_TARGET_PROFILE_BYTES);
    let exact_request = targeted_request(
        json!({
            "node_id": "node:resource.profile.exact",
            "kind": "literal",
            "text": "x"
        }),
        &exact_profile,
    );
    assert_eq!(
        compile(&exact_request, Some(&exact_profile))
            .expect("exact profile bytes")
            .outcome,
        CompileOutcome::Succeeded
    );

    let over_profile = profile_at_size(MAX_TARGET_PROFILE_BYTES + 1);
    let over_request = targeted_request(
        json!({
            "node_id": "node:resource.profile.over",
            "kind": "literal",
            "text": "x"
        }),
        &over_profile,
    );
    assert_resource_failure(
        &compile(&over_request, Some(&over_profile)).expect("profile byte exhaustion"),
    );
}

#[test]
fn capability_requirement_limit_accepts_exact_and_rejects_one_over() {
    let profile: TargetProfile = from_json(ECMASCRIPT_2024).expect("profile");
    let exact = unicode_set_request(MAX_CAPABILITY_REQUIREMENTS, &profile);
    let exact_result = compile(&exact, Some(&profile)).expect("exact requirement ceiling");
    assert!(exact_result
        .diagnostics
        .iter()
        .all(|diagnostic| diagnostic.code.as_str() != RESOURCE_EXHAUSTED_DIAGNOSTIC));

    let over = unicode_set_request(MAX_CAPABILITY_REQUIREMENTS + 1, &profile);
    assert_resource_failure(&compile(&over, Some(&profile)).expect("requirement exhaustion"));
}

#[test]
fn certified_structural_limit_is_projected_as_resource_exhaustion() {
    let branches: Vec<_> = (0..92)
        .map(|index| {
            json!({
                "node_id": format!("node:resource.relationship.{index}"),
                "kind": "literal",
                "text": format!("{index:03}")
            })
        })
        .collect();
    let request = semantic_request(
        json!({
            "node_id": "node:resource.relationship.root",
            "kind": "alternation",
            "branches": branches
        }),
        vec!["analysis"],
    );

    assert_resource_failure(&compile(&request, None).expect("relationship exhaustion"));
}
