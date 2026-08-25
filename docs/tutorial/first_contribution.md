# Your First Semantic STRling Contribution

[← Back to Developer Hub](../index.md)

This tutorial adds a focused compiler regression for US ZIP-code intent. It
uses STRling's authoring hierarchy directly:

1. Semantic STRling for flagship textual intent;
2. Simply when the same intent is built programmatically; and
3. regex-compatible source only for an explicit import obligation.

The example uses existing language semantics. Adding a new construct or
changing meaning requires specification work before implementation or tests.

## 1. Write the intent in Semantic STRling

Create `zip.semantic.strling` in a temporary working directory:

```strling
semantic strling 1.0;
case sensitive;

pattern sequence {
    at input start;
    repeat from 5 to 5 using greedy {
        character from { unicode digit; }
    }
    choice {
        empty;
        sequence {
            text "-";
            repeat from 4 to 4 using greedy {
                character from { unicode digit; }
            }
        }
    }
    at input end;
}
```

Composition and repetition are explicit. There is no implicit concatenation,
postfix quantifier, target flag, or target regex fragment in Semantic STRling.

## 2. Send one canonical compile request

The repository CLI reads a canonical JSON request from standard input. Create
`zip-request.json`, embedding the source above as the `text` value:

```json
{
    "contract_version": "1.0.0",
    "specification_version": "1.0-draft.1",
    "input": {
        "kind": "source",
        "document": {
            "contract_version": "1.0.0",
            "source_id": "src:tutorial.zip",
            "specification_version": "1.0-draft.1",
            "frontend": {
                "id": "strling.semantic",
                "dialect_version": "1.0.0"
            },
            "display_name": "zip.semantic.strling",
            "content": {
                "kind": "inline",
                "encoding": "utf-8",
                "media_type": "text/x-strling-semantic",
                "text": "semantic strling 1.0;\ncase sensitive;\npattern sequence {\n    at input start;\n    repeat from 5 to 5 using greedy {\n        character from { unicode digit; }\n    }\n    choice {\n        empty;\n        sequence {\n            text \"-\";\n            repeat from 4 to 4 using greedy {\n                character from { unicode digit; }\n            }\n        }\n    }\n    at input end;\n}\n"
            },
            "provenance": {
                "kind": "authored",
                "description": "first-contribution tutorial"
            }
        }
    },
    "requested_outputs": ["semantic", "analysis"],
    "compiler_options": {
        "partial_semantics": "forbid",
        "diagnostic_policy": { "minimum_severity": "hint" }
    }
}
```

From the repository root, run:

```bash
./strling compile < zip-request.json
```

A successful result has `outcome: "succeeded"`, a complete normalized semantic
program, and semantic analysis. This request deliberately does not select a
target; targets belong to explicit profile-aware compiler routing.

For interactive work, save the source from step 1 as `zip.semantic.strling`
and use the source shorthand. The CLI constructs the same canonical request,
assigns deterministic content-based source identity, and records authored
provenance before calling the same kernel facade:

```bash
./strling compile --input zip.semantic.strling --format json
```

Use `./strling import --input pattern.regex` only for regex-compatible source.
Target artifacts additionally require an exact `--target` alias or
`--target-profile` file and `--output target_artifact`; the CLI never guesses a
target engine.

## 3. Add the regression at the owning boundary

For a source-parser or orchestration regression, add a narrow Rust integration
test beside the existing Semantic source tests in
`core/tests/frontend_orchestration.rs`. Reuse its `semantic_source_request`
helper, request only the outputs the test needs, and assert canonical behavior:

```rust
#[test]
fn semantic_zip_code_intent_reaches_the_canonical_pipeline() {
    let request = semantic_source_request(ZIP_SOURCE, &["semantic", "analysis"]);
    let result = compile(&request, None).expect("Semantic source compiles");

    assert_eq!(result.outcome, CompileOutcome::Succeeded);
    assert!(result.semantic_result.is_some());
    assert!(result.analysis.is_some());
    assert!(result.diagnostics.is_empty());
}
```

Keep `ZIP_SOURCE` in the test module. Do not generate a specification fixture
from the implementation. If the change affects normative syntax, mappings, or
diagnostics, update and review the controlling frontend contract and its
content-addressed authored fixtures first.

## 4. Verify the affected boundaries

Run the focused parser, formatter, orchestration, and contract checks:

```bash
cargo test --manifest-path core/internal/Cargo.toml --test semantic_frontend --locked
cargo test --manifest-path core/internal/Cargo.toml --test semantic_frontend_properties --locked
cargo test --manifest-path core/internal/Cargo.toml --test frontend_orchestration --locked
python3 tooling/semantic_strling_contract.py
./strling profile local
git diff --check
```

If the same intent needs a programmatic API regression, express it through the
ratified Simply operations and route it through the Rust builder or Preview
transport. The shared convergence corpus under `tests/convergence/` shows the
exact host-neutral request shape and proves TypeScript and Python reconstruct
it without owning semantics.

Add a regex-compatible case only when the change is explicitly about importing
or preserving regex-shaped source. Label it as compatibility evidence and use
the governed legacy disposition taxonomy; do not present it as Semantic
STRling.

## 5. Commit the smallest coherent change

Review the diff, confirm that tests and documentation agree with the controlling
contract, and use a domain-oriented subject such as:

```bash
git commit -m "test(frontend): cover Semantic ZIP-code intent"
```

You have now contributed at the canonical boundary: authored semantic intent,
one compiler pipeline, and evidence that does not promote a binding or generated
fixture into semantic authority.
