use std::panic::catch_unwind;

use serde_json::{json, Value};
use strling_kernel::diagnostic::DiagnosticCategory;
use strling_kernel::kernel::RESOURCE_EXHAUSTED_DIAGNOSTIC;
use strling_kernel::normalization::normalize;
use strling_kernel::protocol::{
    CompileInput, CompileOutcome, CompileRequest, CompileResult, RequestedOutput, ResourceLimits,
};
use strling_kernel::target::{PortabilityStatus, TargetProfile};
use strling_kernel::validation::{from_json, Validate};
use strling_kernel::{compile, KernelCompileError};

const VALID_SEEDS: [u64; 4] = [
    0x4b45_524e_454c_0001,
    0x9e37_79b9_7f4a_7c15,
    0xd1b5_4a32_d192_ed03,
    0x94d0_49bb_1331_11eb,
];
const VALID_CASES_PER_SEED: usize = 64;
const GENERATED_VALID_CASES: usize = VALID_SEEDS.len() * VALID_CASES_PER_SEED;

const PROFILE_SEED: u64 = 0x5052_4f46_494c_4501;
const PROFILE_CASES: usize = 64;

const MALFORMED_TYPED_SEED: u64 = 0x4d41_4c46_4f52_4d01;
const MALFORMED_TYPED_CASES: usize = 256;

const EXHAUSTION_SEED: u64 = 0x5245_534f_5552_4301;
const EXHAUSTION_CASES: usize = 32;

const FUZZ_SEEDS: [u64; 4] = [
    0x4655_5a5a_0000_0001,
    0x4655_5a5a_0000_0002,
    0x4655_5a5a_0000_0003,
    0x4655_5a5a_0000_0004,
];
const FUZZ_CASES_PER_SEED: usize = 128;
const FUZZ_SMOKE_CASES: usize = FUZZ_SEEDS.len() * FUZZ_CASES_PER_SEED;
const FUZZ_VALID_CASES: usize = FUZZ_SMOKE_CASES / 8;
const FUZZ_MALFORMED_CASES: usize = FUZZ_SMOKE_CASES - FUZZ_VALID_CASES;

const PCRE2_1042: &str = include_str!("../../spec/targets/profiles/pcre2-10.42.json");
const ECMASCRIPT_2024: &str = include_str!("../../spec/targets/profiles/ecmascript-2024.json");

struct Generator {
    state: u64,
    next_node: u64,
}

impl Generator {
    fn new(seed: u64) -> Self {
        Self {
            state: seed,
            next_node: 0,
        }
    }

    fn next(&mut self) -> u64 {
        self.state = self
            .state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        self.state
    }

    fn pick(&mut self, count: usize) -> usize {
        (self.next() % count as u64) as usize
    }

    fn boolean(&mut self) -> bool {
        self.pick(2) == 1
    }

    fn node_id(&mut self) -> String {
        let id = format!("node:kernel.generated.{}", self.next_node);
        self.next_node += 1;
        id
    }

    fn node(&mut self, depth: usize) -> Value {
        let choice = if depth == 0 {
            self.pick(2)
        } else {
            self.pick(7)
        };
        let node_id = self.node_id();
        match choice {
            0 => json!({"node_id": node_id, "kind": "empty"}),
            1 => {
                const LITERALS: [&str; 6] = ["a", "ß", "λ", "😀", "中", "xyz"];
                let text = LITERALS[self.pick(LITERALS.len())];
                json!({"node_id": node_id, "kind": "literal", "text": text})
            }
            2 => {
                let child_depth = depth.saturating_sub(1);
                json!({
                    "node_id": node_id,
                    "kind": "sequence",
                    "items": [self.node(child_depth), self.node(child_depth)]
                })
            }
            3 => {
                let child_depth = depth.saturating_sub(1);
                json!({
                    "node_id": node_id,
                    "kind": "alternation",
                    "branches": [self.node(child_depth), self.node(child_depth)]
                })
            }
            4 => {
                let maximum = if self.boolean() {
                    Value::Null
                } else {
                    json!(1 + self.pick(4))
                };
                let mode = ["greedy", "lazy", "possessive"][self.pick(3)];
                json!({
                    "node_id": node_id,
                    "kind": "repeat",
                    "body": self.node(depth.saturating_sub(1)),
                    "min": self.pick(2),
                    "max": maximum,
                    "mode": mode
                })
            }
            5 => json!({
                "node_id": node_id,
                "kind": "atomic",
                "body": self.node(depth.saturating_sub(1))
            }),
            _ => json!({
                "node_id": node_id,
                "kind": "lookaround",
                "direction": if self.boolean() { "ahead" } else { "behind" },
                "polarity": if self.boolean() { "positive" } else { "negative" },
                "body": self.node(depth.saturating_sub(1))
            }),
        }
    }

    fn request(&mut self, outputs: &[&str]) -> CompileRequest {
        let mut request = semantic_request(
            self.node(3),
            outputs,
            if self.boolean() {
                "sensitive"
            } else {
                "insensitive"
            },
        );
        let CompileInput::Semantic { program } = &mut request.input else {
            unreachable!("generated request is semantic")
        };
        **program = normalize(program).expect("generated program normalizes");
        request
    }

    fn bytes(&mut self) -> Vec<u8> {
        let length = 1 + self.pick(64);
        (0..length)
            .map(|_| u8::try_from(32 + self.pick(95)).expect("printable byte"))
            .collect()
    }
}

fn semantic_request(root: Value, outputs: &[&str], case_matching: &str) -> CompileRequest {
    serde_json::from_value(json!({
        "contract_version": "1.0.0",
        "specification_version": "1.0-draft.1",
        "input": {
            "kind": "semantic",
            "program": {
                "contract_version": "1.0.0",
                "specification_version": "1.0-draft.1",
                "normalization": "canonical-v1",
                "case_matching": case_matching,
                "root": root
            }
        },
        "requested_outputs": outputs,
        "compiler_options": {
            "partial_semantics": "forbid",
            "diagnostic_policy": { "minimum_severity": "hint" }
        }
    }))
    .expect("generated request shape")
}

fn atomic_request(text: &str, profile: &TargetProfile) -> CompileRequest {
    let mut request = semantic_request(
        json!({
            "node_id": "node:kernel.profile.atomic",
            "kind": "atomic",
            "body": {
                "node_id": "node:kernel.profile.literal",
                "kind": "literal",
                "text": text
            }
        }),
        &["semantic", "analysis", "portability"],
        "sensitive",
    );
    request.target_profile = Some(profile.reference().expect("profile reference"));
    request
}

fn wide_request(total_nodes: usize) -> CompileRequest {
    assert!(total_nodes >= 3);
    let items: Vec<_> = (0..total_nodes - 1)
        .map(|index| {
            if index % 2 == 0 {
                json!({
                    "node_id": format!("node:kernel.exhaustion.{index}"),
                    "kind": "literal",
                    "text": "x"
                })
            } else {
                json!({
                    "node_id": format!("node:kernel.exhaustion.{index}"),
                    "kind": "wildcard",
                    "line_terminators": "include"
                })
            }
        })
        .collect();
    semantic_request(
        json!({
            "node_id": "node:kernel.exhaustion.root",
            "kind": "sequence",
            "items": items
        }),
        &["semantic", "analysis"],
        "sensitive",
    )
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

#[test]
fn generated_source_less_requests_are_deterministic_immutable_and_self_validating() {
    let mut generated = 0;
    for seed in VALID_SEEDS {
        let mut generator = Generator::new(seed);
        for case in 0..VALID_CASES_PER_SEED {
            let request = generator.request(&["semantic", "analysis"]);
            request.validate().unwrap_or_else(|errors| {
                panic!("seed {seed:#x} case {case} request invalid: {errors:?}")
            });
            let request_before = request.clone();

            let first = catch_unwind(|| compile(&request, None))
                .unwrap_or_else(|_| panic!("seed {seed:#x} case {case} panicked"))
                .unwrap_or_else(|error| panic!("seed {seed:#x} case {case} failed: {error}"));
            let second = catch_unwind(|| compile(&request, None))
                .unwrap_or_else(|_| panic!("seed {seed:#x} case {case} repeat panicked"))
                .unwrap_or_else(|error| {
                    panic!("seed {seed:#x} case {case} repeat failed: {error}")
                });

            assert_eq!(first, second, "seed {seed:#x} case {case}");
            assert_eq!(request, request_before, "seed {seed:#x} case {case}");
            assert_eq!(first.outcome, CompileOutcome::Succeeded);
            assert!(first.semantic_result.is_some());
            assert!(first.analysis.is_some());
            assert!(first.portability.is_none());
            assert!(first.artifact.is_none());
            first
                .validate()
                .unwrap_or_else(|errors| panic!("seed {seed:#x} case {case}: {errors:?}"));
            generated += 1;
        }
    }

    assert_eq!(generated, GENERATED_VALID_CASES);
    eprintln!(
        "KERNEL_PROPERTIES valid_seeds={VALID_SEEDS:?} generated={generated} unexplained_failures=0"
    );
}

#[test]
fn changing_only_profile_authority_preserves_target_neutral_evidence() {
    let pcre2: TargetProfile = from_json(PCRE2_1042).expect("PCRE2 profile");
    let ecmascript: TargetProfile = from_json(ECMASCRIPT_2024).expect("ECMAScript profile");
    let pcre2_before = pcre2.clone();
    let ecmascript_before = ecmascript.clone();
    let mut generator = Generator::new(PROFILE_SEED);

    for case in 0..PROFILE_CASES {
        const TEXT: [&str; 4] = ["a", "abc", "x", "profile"];
        let text = format!(
            "{}{}",
            TEXT[generator.pick(TEXT.len())],
            generator.pick(10_000)
        );
        let pcre2_request = atomic_request(&text, &pcre2);
        let ecmascript_request = atomic_request(&text, &ecmascript);
        assert_eq!(pcre2_request.input, ecmascript_request.input);

        let pcre2_result = catch_unwind(|| compile(&pcre2_request, Some(&pcre2)))
            .unwrap_or_else(|_| panic!("profile seed {PROFILE_SEED:#x} case {case} panicked"))
            .expect("PCRE2 compile");
        let ecmascript_result = catch_unwind(|| compile(&ecmascript_request, Some(&ecmascript)))
            .unwrap_or_else(|_| {
                panic!("profile seed {PROFILE_SEED:#x} case {case} ECMAScript panicked")
            })
            .expect("ECMAScript compile");

        assert_eq!(
            pcre2_result.semantic_result,
            ecmascript_result.semantic_result
        );
        assert_eq!(pcre2_result.analysis, ecmascript_result.analysis);
        assert_eq!(
            pcre2_result
                .portability
                .as_ref()
                .unwrap_or_else(|| {
                    panic!("PCRE2 portability missing for case {case}: {pcre2_result:?}")
                })
                .status,
            PortabilityStatus::Native
        );
        assert_eq!(
            ecmascript_result
                .portability
                .as_ref()
                .unwrap_or_else(|| {
                    panic!("ECMAScript portability missing for case {case}: {ecmascript_result:?}")
                })
                .status,
            PortabilityStatus::EquivalentRewrite
        );
        pcre2_result.validate().expect("PCRE2 result validates");
        ecmascript_result
            .validate()
            .expect("ECMAScript result validates");
    }

    assert_eq!(pcre2, pcre2_before);
    assert_eq!(ecmascript, ecmascript_before);
    eprintln!(
        "KERNEL_PROFILE_PROPERTIES seed={PROFILE_SEED:#x} cases={PROFILE_CASES} unexplained_failures=0"
    );
}

#[test]
fn malformed_typed_requests_are_rejected_without_panics_or_mutation() {
    let mut generator = Generator::new(MALFORMED_TYPED_SEED);
    let mut malformed = 0;
    for case in 0..MALFORMED_TYPED_CASES {
        let mut request = generator.request(&["semantic"]);
        match case % 4 {
            0 => request.requested_outputs.clear(),
            1 => {
                request.requested_outputs =
                    vec![RequestedOutput::Semantic, RequestedOutput::Semantic];
            }
            2 => {
                request.compiler_options.resource_limits = Some(ResourceLimits {
                    max_semantic_nodes: None,
                    max_diagnostics: None,
                });
            }
            _ => {
                request.compiler_options.resource_limits = Some(ResourceLimits {
                    max_semantic_nodes: Some(0),
                    max_diagnostics: None,
                });
            }
        }
        let request_before = request.clone();
        let outcome = catch_unwind(|| compile(&request, None))
            .unwrap_or_else(|_| panic!("typed malformed case {case} panicked"));
        assert!(
            matches!(outcome, Err(KernelCompileError::InvalidRequest(_))),
            "typed malformed case {case} returned {outcome:?}"
        );
        assert_eq!(request, request_before);
        malformed += 1;
    }

    assert_eq!(malformed, MALFORMED_TYPED_CASES);
    eprintln!(
        "KERNEL_MALFORMED_PROPERTIES seed={MALFORMED_TYPED_SEED:#x} malformed={malformed} unexplained_failures=0"
    );
}

#[test]
fn generated_limit_crossings_fail_whole_without_panics() {
    let mut generator = Generator::new(EXHAUSTION_SEED);
    let mut limits: Vec<usize> = (1..=EXHAUSTION_CASES).collect();
    for index in (1..limits.len()).rev() {
        let swap = generator.pick(index + 1);
        limits.swap(index, swap);
    }

    let mut exhausted = 0;
    for limit in limits {
        let mut request = wide_request(limit + 2);
        request.compiler_options.resource_limits = Some(ResourceLimits {
            max_semantic_nodes: Some(u64::try_from(limit).expect("limit")),
            max_diagnostics: None,
        });
        request.validate().expect("generated exhaustion request");
        let request_before = request.clone();

        let result = catch_unwind(|| compile(&request, None))
            .unwrap_or_else(|_| panic!("exhaustion limit {limit} panicked"))
            .expect("resource failure is a result");
        assert_resource_failure(&result);
        assert_eq!(request, request_before);
        exhausted += 1;
    }

    assert_eq!(exhausted, EXHAUSTION_CASES);
    eprintln!(
        "KERNEL_RESOURCE_PROPERTIES seed={EXHAUSTION_SEED:#x} exhaustion_cases={exhausted} unexplained_failures=0"
    );
}

fn fuzz_input(generator: &mut Generator, case: usize) -> String {
    let request = generator.request(&["semantic", "analysis"]);
    let serialized = serde_json::to_string(&request).expect("serialize fuzz seed");
    match case % 8 {
        0 => serialized,
        1 => format!("!{}", String::from_utf8_lossy(&generator.bytes())),
        2 => {
            let mut value = serde_json::to_value(request).expect("request value");
            value["unknown_field"] = json!(generator.next());
            serde_json::to_string(&value).expect("unknown-field mutation")
        }
        3 => {
            let mut value = serde_json::to_value(request).expect("request value");
            value["requested_outputs"] = json!(["future_output"]);
            serde_json::to_string(&value).expect("future-output mutation")
        }
        4 => serialized.replacen("1.0.0", "2.0.0", 1),
        5 => {
            let mut value = serde_json::to_value(request).expect("request value");
            value["target_profile"] = Value::Null;
            serde_json::to_string(&value).expect("null mutation")
        }
        6 => {
            let mut value = serde_json::to_value(request).expect("request value");
            value["requested_outputs"] = json!([]);
            serde_json::to_string(&value).expect("empty-output mutation")
        }
        _ => {
            let end = 1 + generator.pick(serialized.len() - 1);
            serialized[..end].to_owned()
        }
    }
}

#[test]
fn serialized_mutation_fuzz_smoke_contains_malformed_inputs_and_panics() {
    let mut valid = 0;
    let mut malformed = 0;

    for seed in FUZZ_SEEDS {
        let mut generator = Generator::new(seed);
        for case in 0..FUZZ_CASES_PER_SEED {
            let input = fuzz_input(&mut generator, case);
            let outcome = catch_unwind(|| match from_json::<CompileRequest>(&input) {
                Ok(request) => Some((request.clone(), compile(&request, None))),
                Err(_) => None,
            })
            .unwrap_or_else(|_| panic!("fuzz seed {seed:#x} case {case} panicked"));

            match outcome {
                Some((request, Ok(result))) => {
                    assert_eq!(case % 8, 0, "unexpected accepted mutation");
                    request.validate().expect("accepted request validates");
                    result.validate().expect("accepted result validates");
                    valid += 1;
                }
                Some((_, Err(error))) => {
                    panic!("fuzz seed {seed:#x} case {case} boundary error: {error}")
                }
                None => {
                    assert_ne!(case % 8, 0, "valid seed rejected");
                    malformed += 1;
                }
            }
        }
    }

    assert_eq!(valid, FUZZ_VALID_CASES);
    assert_eq!(malformed, FUZZ_MALFORMED_CASES);
    assert_eq!(valid + malformed, FUZZ_SMOKE_CASES);
    eprintln!(
        "KERNEL_FUZZ_SMOKE seeds={FUZZ_SEEDS:?} total={} valid={valid} malformed={malformed} unexplained_failures=0",
        valid + malformed
    );
}
