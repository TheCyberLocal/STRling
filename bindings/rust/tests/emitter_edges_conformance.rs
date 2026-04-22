//! Emitter Edges Conformance — Rust bridge.
//!
//! Drives the global pathological-AST fixture
//! `tests/conformance/inputs/emitter_edges/pathological.json` through
//! the Rust [`PCRE2Emitter`] and asserts each safety guard
//! fires:
//!
//! 1. Variable-Length Lookbehind Rejection — [`STRlingCompilationError`]
//! 2. AST Depth Limit Exceeded             — [`STRlingCompilationError`]
//! 3. ReDoS Risk Warning (`(a+)+`)         — non-fatal [`STRlingWarning`]
//!
//! The fixture's `ast` field is the user-facing AST sketch (not the
//! post-lowering IR), so a small `ast_to_ir` adapter mirrors the
//! TypeScript bridge's `astToIR`. Keep the adapter minimal — supporting
//! only the node types currently appearing in `pathological.json` — so
//! adapter omissions cannot mask emitter bugs by silently dropping nodes.

use serde_json::Value;
use std::fs;
use std::path::PathBuf;

use strling::core::errors::STRlingWarning;
use strling::core::ir::*;
use strling::core::nodes::Flags;
use strling::emitters::pcre2::PCRE2Emitter;

/// Resolve the workspace-shared fixture path. `cargo test` runs from the
/// crate root (`bindings/rust/`), so we climb two parents to reach the
/// repository root.
fn fixture_path() -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.pop(); // bindings
    p.pop(); // repo root
    p.push("tests");
    p.push("conformance");
    p.push("inputs");
    p.push("emitter_edges");
    p.push("pathological.json");
    p
}

/// Convert a pathological-fixture AST sketch into Rust IR. Supports only
/// the node types currently appearing in `pathological.json`. Extend
/// deliberately when new vectors are added so coverage gaps surface as
/// panics rather than silent passes.
fn ast_to_ir(node: &Value) -> IROp {
    let ty = node["type"]
        .as_str()
        .expect("pathological node missing string `type`");

    match ty {
        "Literal" => {
            let value = node
                .get("value")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            IROp::Lit(IRLit { value })
        }
        "Group" => {
            let content = node
                .get("content")
                .expect("Group node missing `content`");
            // Pathological fixtures use non-capturing groups for nesting.
            IROp::Group(IRGroup {
                capturing: false,
                name: None,
                atomic: false,
                body: Box::new(ast_to_ir(content)),
            })
        }
        "Quantifier" => {
            let content = node
                .get("content")
                .expect("Quantifier node missing `content`");
            let child = Box::new(ast_to_ir(content));
            let min = node
                .get("min")
                .and_then(|v| v.as_i64())
                .unwrap_or(0) as i32;
            let max = match node.get("max") {
                // `null` in the user-facing AST means unbounded.
                None | Some(Value::Null) => IRMaxBound::Infinite("Inf".to_string()),
                Some(v) => IRMaxBound::Finite(
                    v.as_i64().expect("Quantifier `max` must be int or null") as i32,
                ),
            };
            let mode = node
                .get("mode")
                .and_then(|v| v.as_str())
                .unwrap_or("Greedy")
                .to_string();
            IROp::Quant(IRQuant { child, min, max, mode })
        }
        "Lookbehind" => IROp::Look(IRLook {
            dir: "Behind".to_string(),
            neg: false,
            body: Box::new(ast_to_ir(node.get("content").expect("Lookbehind missing `content`"))),
        }),
        "NegativeLookbehind" => IROp::Look(IRLook {
            dir: "Behind".to_string(),
            neg: true,
            body: Box::new(ast_to_ir(node.get("content").expect("NegativeLookbehind missing `content`"))),
        }),
        "Lookahead" => IROp::Look(IRLook {
            dir: "Ahead".to_string(),
            neg: false,
            body: Box::new(ast_to_ir(node.get("content").expect("Lookahead missing `content`"))),
        }),
        "NegativeLookahead" => IROp::Look(IRLook {
            dir: "Ahead".to_string(),
            neg: true,
            body: Box::new(ast_to_ir(node.get("content").expect("NegativeLookahead missing `content`"))),
        }),
        other => panic!(
            "ast_to_ir: unsupported pathological AST node type \"{}\". \
             Extend the adapter when new pathological vectors are added.",
            other
        ),
    }
}

/// Strip the `STRlingCompilationError: ` / `STRlingWarning [CODE]: `
/// prefix so the remainder can be substring-matched against the raw
/// emitter message.
fn expected_substring(prefixed: &str) -> &str {
    if let Some(rest) = prefixed.strip_prefix("STRlingCompilationError:") {
        return rest.trim_start();
    }
    if let Some(rest) = prefixed.strip_prefix("STRlingWarning") {
        if let Some(idx) = rest.find(']') {
            let after = &rest[idx + 1..];
            return after.trim_start_matches(':').trim_start();
        }
    }
    prefixed
}

fn load_fixture() -> Value {
    let path = fixture_path();
    let raw = fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("could not read {:?}: {}", path, e));
    serde_json::from_str(&raw)
        .unwrap_or_else(|e| panic!("could not parse {:?}: {}", path, e))
}

/// Drive every entry in the pathological fixture through the emitter.
/// One `#[test]` lets all cases share fixture I/O while still failing
/// with a single, named assertion per vector via the embedded loop.
#[test]
fn pathological_cases() {
    let fixture = load_fixture();
    let cases = fixture["tests"]
        .as_array()
        .expect("fixture missing `tests` array");
    assert!(!cases.is_empty(), "fixture has no test cases");

    let emitter = PCRE2Emitter::new(Flags::default());

    for case in cases {
        let name = case["name"].as_str().unwrap_or("<unnamed>");
        let ir = ast_to_ir(&case["ast"]);
        let max_depth: Option<usize> = case
            .get("depth_override_for_test")
            .and_then(|v| v.as_u64())
            .map(|n| n as usize);

        if let Some(expected) = case.get("expected_error").and_then(|v| v.as_str()) {
            let needle = expected_substring(expected);
            let result = emitter.emit_with_diagnostics(&ir, max_depth);
            match result {
                Err(err) => assert!(
                    err.message.contains(needle),
                    "case `{}`: expected error to contain `{}`, got `{}`",
                    name, needle, err.message
                ),
                Ok(ok) => panic!(
                    "case `{}`: expected STRlingCompilationError, got Ok({:?})",
                    name, ok.pattern
                ),
            }
        } else if let Some(expected) = case.get("expected_warning").and_then(|v| v.as_str()) {
            let needle = expected_substring(expected);
            let result = emitter
                .emit_with_diagnostics(&ir, max_depth)
                .unwrap_or_else(|e| {
                    panic!(
                        "case `{}`: expected Ok with REDOS_RISK warning, got Err({})",
                        name, e
                    )
                });
            // Warnings must NOT abort emission — a pattern is still produced.
            assert!(
                !result.pattern.is_empty(),
                "case `{}`: expected non-empty pattern when only a warning fires",
                name
            );
            let found = result.warnings.iter().any(|w: &STRlingWarning| {
                w.code == "REDOS_RISK" && w.message.contains(needle)
            });
            assert!(
                found,
                "case `{}`: expected REDOS_RISK warning containing `{}`; got {:?}",
                name, needle, result.warnings
            );
        } else {
            panic!(
                "case `{}` declares neither expected_error nor expected_warning",
                name
            );
        }
    }
}

// --- Negative controls -----------------------------------------------------

#[test]
fn non_pathological_pattern_emits_no_warnings() {
    let emitter = PCRE2Emitter::new(Flags::default());
    let ir = IROp::Lit(IRLit { value: "abc".to_string() });
    let result = emitter
        .emit_with_diagnostics(&ir, None)
        .expect("plain literal must compile cleanly");
    assert_eq!(result.pattern, "abc");
    assert!(
        result.warnings.is_empty(),
        "plain literal must not raise diagnostic warnings, got {:?}",
        result.warnings
    );
}

#[test]
fn depth_cap_does_not_fire_under_limit() {
    // Two nested groups under a depth cap of 5 must compile cleanly.
    let emitter = PCRE2Emitter::new(Flags::default());
    let inner = IROp::Group(IRGroup {
        capturing: false,
        name: None,
        atomic: false,
        body: Box::new(IROp::Lit(IRLit { value: "ok".to_string() })),
    });
    let outer = IROp::Group(IRGroup {
        capturing: false,
        name: None,
        atomic: false,
        body: Box::new(inner),
    });
    let result = emitter
        .emit_with_diagnostics(&outer, Some(5))
        .expect("two nested groups must not exceed a depth cap of 5");
    assert!(result.warnings.is_empty());
    assert!(result.pattern.contains("ok"));
}
