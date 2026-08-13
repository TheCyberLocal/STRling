use std::convert::TryFrom;
use std::panic::{catch_unwind, AssertUnwindSafe};

use serde_json::Value;
use strling_kernel::semantic::{
    AssertionPolarity, CaseMatching, CharacterDomain, LineTerminators, LookaroundDirection, Node,
    PositionKind, RepetitionMaximum, RepetitionMode, SemanticProgram,
};
use strling_kernel::source::{SourceDocument, SpecificationVersion};
use strling_kernel::validation::Validate;
use strling_kernel::{SimplyBuilder, SimplyCharacterSetMember, SimplyErrorCode, SimplyOptions};

const POSITIVE: &str = include_str!("../../spec/frontends/simply/1.0/fixtures/positive.json");

fn version() -> SpecificationVersion {
    SpecificationVersion::try_from("1.0-draft.1").expect("specification version")
}

fn options(seed: u64) -> SimplyOptions {
    SimplyOptions {
        case_matching: if seed & 1 == 0 {
            CaseMatching::Sensitive
        } else {
            CaseMatching::Insensitive
        },
        builtin_character_domain: if seed & 2 == 0 {
            CharacterDomain::Unicode
        } else {
            CharacterDomain::Ascii
        },
        wildcard_line_terminators: if seed & 4 == 0 {
            LineTerminators::Exclude
        } else {
            LineTerminators::Include
        },
    }
}

fn generated_program(seed: u64) -> SemanticProgram {
    let namespace = format!("property/s{seed:016x}");
    let mut builder = SimplyBuilder::new(&namespace, version(), options(seed)).unwrap();
    let literal = builder
        .literal("literal", if seed & 8 == 0 { "λ" } else { "a.b" })
        .unwrap();
    let wildcard = builder
        .wildcard(
            "wildcard",
            (seed & 16 != 0).then_some(LineTerminators::Include),
        )
        .unwrap();
    let pair = if seed & 32 == 0 {
        builder.sequence("pair", &[literal, wildcard]).unwrap()
    } else {
        builder.alternation("pair", &[literal, wildcard]).unwrap()
    };
    let wrapped = match (seed >> 6) & 3 {
        0 => builder.atomic("wrapped", &pair).unwrap(),
        1 => builder
            .lookaround(
                "wrapped",
                LookaroundDirection::Ahead,
                AssertionPolarity::Positive,
                &pair,
            )
            .unwrap(),
        2 => builder
            .repeat(
                "wrapped",
                &pair,
                seed % 3,
                if seed & 256 == 0 {
                    RepetitionMaximum::Unbounded
                } else {
                    RepetitionMaximum::Bounded(seed % 3 + 2)
                },
                match (seed >> 9) % 3 {
                    0 => RepetitionMode::Greedy,
                    1 => RepetitionMode::Lazy,
                    _ => RepetitionMode::Possessive,
                },
            )
            .unwrap(),
        _ => builder.group("wrapped", &pair).unwrap(),
    };

    let root = if seed & 2048 == 0 {
        let captured = builder
            .capture("captured", "value", Some("value"), &wrapped)
            .unwrap();
        let reference = builder.backreference("reference", "value").unwrap();
        builder.sequence("root", &[captured, reference]).unwrap()
    } else {
        let position = builder
            .position("position", PositionKind::InputEnd)
            .unwrap();
        builder.sequence("root", &[wrapped, position]).unwrap()
    };
    builder.finish_program(&root).expect("generated program")
}

#[test]
fn fixed_seed_graphs_are_deterministic_canonical_and_serializable() {
    for seed in 0..256 {
        let first = generated_program(seed);
        let second = generated_program(seed);
        assert_eq!(first, second, "seed {seed}");
        first
            .validate()
            .unwrap_or_else(|errors| panic!("seed {seed}: {errors}"));
        let first_json = serde_json::to_string(&first).expect("first serialization");
        let second_json = serde_json::to_string(&second).expect("second serialization");
        assert_eq!(first_json, second_json, "seed {seed}: serialization");
        let round_trip: SemanticProgram = serde_json::from_str(&first_json).expect("round trip");
        assert_eq!(first, round_trip, "seed {seed}: round trip");
    }
}

fn fixture<'a>(suite: &'a Value, case_id: &str) -> &'a Value {
    suite["cases"]
        .as_array()
        .expect("cases")
        .iter()
        .find(|case| case["case_id"] == case_id)
        .expect("fixture")
}

#[test]
fn imports_preserve_inputs_and_sort_mixed_sources_by_identity() {
    let suite: Value = serde_json::from_str(POSITIVE).expect("positive suite");
    let node_case = fixture(&suite, "imported-node-provenance");
    let node: Node =
        serde_json::from_value(node_case["request"]["steps"][0]["arguments"]["node"].clone())
            .expect("node");
    let node_sources: Vec<SourceDocument> =
        serde_json::from_value(node_case["request"]["steps"][0]["arguments"]["sources"].clone())
            .expect("node sources");
    let program_case = fixture(&suite, "imported-program-mixed-provenance");
    let program: SemanticProgram =
        serde_json::from_value(program_case["request"]["steps"][0]["arguments"]["program"].clone())
            .expect("program");
    let original_node = node.clone();
    let original_sources = node_sources.clone();
    let original_program = program.clone();

    let mut builder = SimplyBuilder::new("mixed", version(), SimplyOptions::default()).unwrap();
    let imported_program = builder
        .import_program("program", program.clone())
        .expect("program import");
    let imported_node = builder
        .import_node("node", node.clone(), node_sources.clone())
        .expect("node import");
    let root = builder
        .alternation("root", &[imported_program, imported_node])
        .expect("composition");
    let result = builder.finish_program(&root).expect("mixed program");

    assert_eq!(original_node, node);
    assert_eq!(original_sources, node_sources);
    assert_eq!(original_program, program);
    let source_ids: Vec<_> = result
        .sources
        .expect("mixed sources")
        .into_iter()
        .map(|source| source.source_id.as_str().to_owned())
        .collect();
    assert_eq!(
        vec![
            "src:simply.imported-node".to_owned(),
            "src:simply.imported-program".to_owned()
        ],
        source_ids
    );
}

#[test]
fn set_inputs_and_cloned_handles_remain_immutable() {
    let members = vec![
        SimplyCharacterSetMember::Range {
            start: 'z',
            end: 'z',
        },
        SimplyCharacterSetMember::Literal { value: '_' },
    ];
    let original = members.clone();
    let mut builder = SimplyBuilder::new("immutable", version(), SimplyOptions::default()).unwrap();
    let set = builder
        .character_set("set", &members, false)
        .expect("character set");
    let cloned = set.clone();
    let root = builder.group("root", &set).expect("group");
    assert_eq!("set", cloned.step_id());
    assert_eq!(original, members);
    assert_eq!(
        SimplyErrorCode::ReusedValue,
        builder
            .atomic("reused", &cloned)
            .expect_err("clone does not clone a subtree")
            .errors[0]
            .code
    );
    builder
        .finish_program(&root)
        .expect("failed reuse is atomic");
}

#[test]
fn bounded_malformed_host_inputs_never_panic() {
    let invalid_keys = ["", "Upper", "two//parts", "trailing-", "é", "has space"];
    for (index, key) in invalid_keys.iter().enumerate() {
        let result = catch_unwind(AssertUnwindSafe(|| {
            let mut builder =
                SimplyBuilder::new("no-panic", version(), SimplyOptions::default()).unwrap();
            builder.literal(key, &"x".repeat(index * 257))
        }));
        let operation = result.unwrap_or_else(|_| panic!("invalid key {key:?} panicked"));
        assert_eq!(
            SimplyErrorCode::InvalidArgument,
            operation.expect_err("invalid key must fail").errors[0].code
        );
    }

    let long_key = format!("a{}", "b".repeat(256));
    let result = catch_unwind(AssertUnwindSafe(|| {
        let mut builder =
            SimplyBuilder::new("no-panic", version(), SimplyOptions::default()).unwrap();
        builder.empty(&long_key)
    }));
    assert_eq!(
        SimplyErrorCode::InvalidArgument,
        result
            .expect("long identity must not panic")
            .expect_err("opaque identity limit")
            .errors[0]
            .code
    );
}
