# STRling Testing — Conformance, Parity, and Verification

> **Scope:** This file governs test strategy, conformance fixtures, cross-binding parity, and verification requirements. It does NOT cover pipeline architecture, fluent API philosophy, or contributor workflow.

---

## Spec-Driven, Test-Driven Development

STRling enforces a **specifications → tests → features** workflow:

1. **Specifications First:** All features must be fully specified before implementation begins.
2. **Tests Second:** Comprehensive tests are written based on the specification.
3. **Implementation Last:** Code is written to make the tests pass.

---

## The JSON Conformance Suite

All bindings are validated against a shared set of JSON fixtures in `tests/spec/`. These fixtures are the **golden master** — generated from the TypeScript reference implementation.

### Fixture Schema

```json
{
    "id": "plus_greedy",
    "input_dsl": "a+",
    "input_ast": {
        "type": "Quantifier",
        "target": { "...": "..." },
        "min": 1,
        "max": null
    },
    "expected_ir": {
        "ir": "Quant",
        "child": { "...": "..." },
        "min": 1,
        "max": "Inf",
        "mode": "Greedy"
    },
    "expected_codegen": { "pcre": "a+" }
}
```

### Conformance Test Contract

- Parse `input_ast` → Compile → Assert IR matches `expected_ir`.
- Error fixtures include `expected_error` and `expected_hint` fields validated against the fixture schema in `spec/schema/conformance-fixture.schema.json`.
- Every binding must pass the **same** fixtures with **identical** output states. There is no tolerance for silent divergence.

---

## The Iron Law of Test Parity

**TypeScript tests define the contract.** All other bindings must match 1:1.

### Requirements

1. Every TypeScript test must have a corresponding test in every other binding with identical behavior.
2. Same test names (adapted to language conventions), same test cases, same assertions, same edge cases.
3. New features are not considered complete until TypeScript has them and the generated specs pass in all bindings.

### Exceptions

Engine-specific features may have unique tests, but these must be clearly marked (e.g., `@pytest.mark.pcre2_only`).

---

## The 4-Test Standard

Every feature must have coverage across four test types:

1. **Unit Tests:** Isolated verification of a single function or method. Minimum 3 test cases per unit.
2. **Semantic Verification Tests:** Validate that the AST and IR carry the correct semantic meaning.
3. **Conformance Tests:** Cross-binding parity against the JSON golden master fixtures.
4. **End-to-End Tests:** Full pipeline validation from DSL input to compiled regex output.

---

## Fixture Regeneration

When the TypeScript reference implementation changes, fixtures must be regenerated:

```bash
cd bindings/typescript && npm run build:specs
```

After regeneration, run the conformance suite across all affected bindings to verify parity:

```bash
python3 tooling/audit_omega.py
```

---

## Verification Commands

```bash
# Run binding-specific tests
cd bindings/python && pytest
cd bindings/go && go test ./...
cd bindings/rust && cargo test
cd bindings/typescript && npm test

# Run full certification audit across all 17 bindings
python3 tooling/audit_omega.py
```

---

## Debugging Conformance Failures

- **IR Mismatch:** Compare `expected_ir` vs actual output using the binding's `compileWithMetadata()` method.
- **Emitter Issues:** Check `_escapeLiteral()` and `_escapeClassChar()` in the PCRE2 emitter.
- **Failure Logs:** Inspect `tooling/test_logs/` for per-binding results.

---

## Anti-Regression Rules

- **Do not** skip or ignore conformance tests. The Omega Audit enforces zero skips.
- **Do not** modify golden master fixtures by hand. They are generated from TypeScript only.
- **Do not** introduce flaky tests. Tests must pass consistently and execute quickly.
- **Do not** merge a PR that reduces the conformance pass count below the current baseline (~594+ tests).
- **Do not** add a feature to a non-TypeScript binding without first verifying that the corresponding spec fixtures exist.
