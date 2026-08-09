# STRling Architecture — Pipeline, SSOT, and Structural Invariants

> **Scope:** This file governs the compiler pipeline, AST/IR structures, emitter contracts, grammar alignment, and the reference implementation. It does NOT cover fluent API philosophy, test strategy, or contributor workflow.

---

## The Compilation Pipeline

STRling follows a strict three-stage compiler architecture:

```
DSL String → Parse → AST → Compile → IR → Emit → Target Regex (PCRE2/JS/Python)
```

Each binding implements the same pipeline in `bindings/<lang>/src/`:

-   **Parser** (`core/parser.*`): DSL text → AST nodes
-   **Compiler** (`core/compiler.*`): AST → target-agnostic Intermediate Representation (IR)
-   **Emitter** (`emitters/pcre2.*`): IR → serialized regex string for a specific engine

### Separation Guarantees

-   **Portability:** New target engines are added by writing a new emitter — the parser and IR remain unchanged.
-   **Testability:** Each stage can be tested in isolation.
-   **Maintainability:** Changes to one stage do not cascade to others.

---

## The Iron Law of Emitters

Emitters are **pure functions** with the signature:

```
emit(ir, flags) → string
```

### Requirements

1. No side effects. Emitters return strings or write to provided streams — nothing else.
2. Deterministic output for a given IR model and configuration.
3. Shared concerns (escaping, format helpers, validation) live in `core/` or `emitters/utils/` — never duplicated per emitter.

### Structural Invariant

If you modify an emitter and the same IR input produces different output without an intentional specification change, you have introduced a regression.

---

## Reference Implementation: TypeScript

The **TypeScript binding** (`bindings/typescript/`) is the normative reference implementation for all logic.

### What This Means

1. **All features start in TypeScript.** A feature is not considered complete until the TypeScript binding implements it.
2. **TypeScript generates the spec fixtures.** The JSON files in `tests/spec/` are produced by `cd bindings/typescript && npm run build:specs`. These fixtures are the golden master for all other bindings.
3. **Other bindings mirror TypeScript logic exactly.** When implementing a feature, check `bindings/typescript/src/STRling/core/compiler.ts` for IR generation patterns and match them.
4. **If behavior is undefined, TypeScript's behavior is the standard.**

---

## Grammar and Semantics Alignment

The EBNF grammar (`spec/grammar/dsl.ebnf`) and the semantics specification (`spec/grammar/semantics.md`) are **both normative** and must evolve in lockstep.

### The Contract

-   The **grammar** defines **syntax** (what is parsable).
-   The **semantics** define **behavior** (what parsed constructs mean).
-   Both are versioned together and are equally authoritative.

### Any New Feature Must Include

1. Grammar update in `spec/grammar/dsl.ebnf`
2. Semantics update in `spec/grammar/semantics.md` (including portability rules)
3. Impact assessment on target artifact schemas in `spec/schema/`

---

## Version Management

**Single Source of Truth for versions:** `bindings/python/pyproject.toml`

Never manually edit version fields in `package.json`, `Cargo.toml`, or other manifests. Use:

```bash
python3 tooling/sync_versions.py --write
```

This propagates the canonical version to all 17 bindings.

---

## Key Files and Directories

| Path                        | Purpose                                                 |
| --------------------------- | ------------------------------------------------------- |
| `bindings/typescript/`      | **Reference Implementation** — all features start here  |
| `tests/spec/*.json`         | Golden master test fixtures (generated from TypeScript) |
| `spec/grammar/dsl.ebnf`     | Canonical grammar definition                            |
| `spec/grammar/semantics.md` | Normative semantics for all constructs                  |
| `tooling/audit_omega.py`    | Final certification audit (validates all 17 bindings)   |
| `tooling/sync_versions.py`  | Propagates version from Python SSOT                     |

---

## Adding a New Feature (Structural Checklist)

1. **Grammar First:** Update `spec/grammar/dsl.ebnf` and `spec/grammar/semantics.md`.
2. **TypeScript Implementation:** Add to `bindings/typescript/src/STRling/`.
3. **Generate Specs:** `cd bindings/typescript && npm run build:specs`.
4. **Implement in Other Bindings:** Match the TypeScript logic exactly.
5. **Verify Conformance:** `python3 tooling/audit_omega.py`.

---

## Anti-Regression Rules

-   **Do not** bypass the pipeline stages. All regex output must flow through Parse → Compile → Emit.
-   **Do not** add engine-specific logic to the parser or compiler. Engine awareness belongs exclusively in emitters.
-   **Do not** modify the IR schema without updating the TypeScript reference implementation first and regenerating spec fixtures.
-   **Do not** introduce mutable state in emitters.
