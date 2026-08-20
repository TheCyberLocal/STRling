# PCRE2 Emitter Edge-Case Hardening Audit

**Date:** 2026-04-21
**Scope:** All 17 language bindings (`bindings/<lang>/`), the `Pcre2Emitter` of each, and dedicated edge-case test files (`emitter_edges_test.*`, `test_pcre2_emitter.py`, `E2EPCRE2EmitterTests.swift`, etc.).
**Goal:** Establish whether STRling guarantees a valid AST cannot crash the underlying PCRE2 engine, and whether the emitter cannot silently produce ReDoS-vulnerable output.

> **TL;DR:** The **specification** ([`spec/grammar/semantics.md`](../../spec/grammar/semantics.md#L218-L398)) already mandates `REDOS_RISK` warnings, variable-length-lookbehind diagnostics, and a `compat` block. **Enforcement is missing in the emitters.** Schemas and conformance fixtures (`compat.variableLengthLookbehind: false`) declare the limitation; no emitter actively detects, rejects, or warns about a violating AST. There is also **no AST depth guard** anywhere in the repository.

---

## 1. Summary Coverage Matrix

Legend: ✅ explicit test • ⚠️ partial / schema-only • ❌ missing

| Binding                | Emitter                                                                                                                                        | Edge-case tests                                                                                        |    VL-Lookbehind    |             AST Depth             | Atomic Groups | Possessive Quant | ReDoS (overlap+nested) |     Unicode Props     | Fuzzing |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | :-----------------: | :-------------------------------: | :-----------: | :--------------: | :--------------------: | :-------------------: | :-----: |
| C                      | [bindings/c/src/strling.c](../../bindings/c/src/strling.c)                                                                                     | [adapter_test.c](../../bindings/c/tests/adapter_test.c)                                                |         ❌          |                ❌                 |      ✅       |        ✅        |           ❌           |   ⚠️ surrogate only   |   ❌    |
| Python                 | [bindings/python/src/STRling/emitters/pcre2.py](../../bindings/python/src/STRling/emitters/pcre2.py)                                           | [test_pcre2_emitter.py](../../bindings/python/tests/e2e/test_pcre2_emitter.py)                         |  ⚠️ docstring only  |                ❌                 |      ✅       |        ✅        | ⚠️ golden fixture only |   ⚠️ basic `\p{L}`    |   ❌    |
| Swift                  | [bindings/swift/Sources/STRling/Emitters/PCRE2Emitter.swift](../../bindings/swift/Sources/STRling/Emitters/PCRE2Emitter.swift)                 | [E2EPCRE2EmitterTests.swift](../../bindings/swift/Tests/STRlingE2ETests/E2EPCRE2EmitterTests.swift)    | ⚠️ schema flag only |                ❌                 |      ✅       |        ✅        |           ❌           |     ⚠️ `\p{...}`      |   ❌    |
| TypeScript (reference) | [bindings/typescript/src/STRling/emitters/pcre2.ts](../../bindings/typescript/src/STRling/emitters/pcre2.ts)                                   | [pcre2_emitter.test.ts](../../bindings/typescript/__tests__/e2e/pcre2_emitter.test.ts)                 | ⚠️ schema flag only | ⚠️ `deeply_nested_quantifiers` ID |      ✅       |        ✅        |           ❌           |       ⚠️ basic        |   ❌    |
| Rust                   | [core/src/target_serialization.rs](../../core/src/target_serialization.rs)                                                                     | [pcre2_serialization.rs](../../core/tests/pcre2_serialization.rs)                                      |         ❌          |                ❌                 |      ✅       |        ✅        |           ❌           |       ⚠️ basic        |   ❌    |
| Go                     | [bindings/go/emitters/pcre2.go](../../bindings/go/emitters/pcre2.go)                                                                           | [pcre2_test.go](../../bindings/go/emitters/pcre2_test.go)                                              |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |
| Java                   | [bindings/java/src/main/java/com/strling/emitters/Pcre2Emitter.java](../../bindings/java/src/main/java/com/strling/emitters/Pcre2Emitter.java) | [PCRE2EmitterTest.java](../../bindings/java/src/test/java/com/strling/tests/e2e/PCRE2EmitterTest.java) |         ❌          |                ❌                 |      ✅       |        ✅        | ⚠️ golden fixture only | ⚠️ runtime validation |   ❌    |
| C#                     | [bindings/csharp/src/STRling/Emit/Pcre2Emitter.cs](../../bindings/csharp/src/STRling/Emit/Pcre2Emitter.cs)                                     | [ConformanceTests.cs](../../bindings/csharp/tests/STRling.Tests/ConformanceTests.cs)                   |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |
| C++                    | [bindings/cpp/src/strling.cpp](../../bindings/cpp/src/strling.cpp)                                                                             | [adapter_test.cpp](../../bindings/cpp/tests/adapter_test.cpp)                                          |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |
| Ruby                   | [bindings/ruby/lib/strling/emitters/pcre2.rb](../../bindings/ruby/lib/strling/emitters/pcre2.rb)                                               | [interaction_test.rb](../../bindings/ruby/test/interaction_test.rb)                                    |         ❌          |                ❌                 |      ✅       |        ✅        |           ❌           |       ⚠️ basic        |   ❌    |
| Kotlin                 | [bindings/kotlin/src/main/kotlin/strling/emitters/Pcre2Emitter.kt](../../bindings/kotlin/src/main/kotlin/strling/emitters/Pcre2Emitter.kt)     | bindings/kotlin/src/test/kotlin/strling/                                                               |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |
| Lua                    | [bindings/lua/src/pcre2.lua](../../bindings/lua/src/pcre2.lua)                                                                                 | [e2e_spec.lua](../../bindings/lua/spec/e2e_spec.lua)                                                   |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |
| Perl                   | [bindings/perl/lib/STRling/Simply.pm](../../bindings/perl/lib/STRling/Simply.pm)                                                               | bindings/perl/t/                                                                                       |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |
| PHP                    | [bindings/php/src/Emitters/Pcre2Emitter.php](../../bindings/php/src/Emitters/Pcre2Emitter.php)                                                 | [InteractionTest.php](../../bindings/php/tests/InteractionTest.php)                                    |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |
| R                      | [bindings/r/R/pcre2.R](../../bindings/r/R/pcre2.R)                                                                                             | bindings/r/tests/testthat/                                                                             |         ❌          |                ❌                 |      ✅       |        ✅        |           ❌           |       ⚠️ basic        |   ❌    |
| Dart                   | [bindings/dart/lib/src/emitters/pcre2.dart](../../bindings/dart/lib/src/emitters/pcre2.dart)                                                   | bindings/dart/test/                                                                                    |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |
| F#                     | [bindings/fsharp/src/STRling/Emitters/Pcre2.fs](../../bindings/fsharp/src/STRling/Emitters/Pcre2.fs)                                           | bindings/fsharp/tests/                                                                                 |         ❌          |                ❌                 |      ⚠️       |        ⚠️        |           ❌           |       ⚠️ basic        |   ❌    |

---

## 2. Phase 1 — The Known-Limits Audit

### 2.1 Variable-Length Lookbehinds — **SYSTEMIC GAP**

**Spec mandate** ([`spec/grammar/semantics.md#L325-L361`](../../spec/grammar/semantics.md#L325)):

> _"Emitters must validate lookbehind patterns and issue diagnostics for variable-length lookbehind when targeting engines with this limitation."_

**Schema mandate** ([`spec/schema/pcre2.v1.schema.json#L15`](../../spec/schema/pcre2.v1.schema.json#L15)):

```json
"variableLengthLookbehind": { "const": false }
```

**Reality:**

-   The flag is **declared** in conformance fixtures ([`tests/conformance/expected/pcre2/simple-lookbehind.json#L36`](../../tests/conformance/expected/pcre2/simple-lookbehind.json#L36)) but never **asserted as a rejection vector**.
-   A planned validation test exists in design notes only: [`tests/_design/unit/test_errors.md#L41`](../../tests/_design/unit/test_errors.md#L41) ("Test that a variable-length lookbehind `(?<=a+)` raises a `ValidationError`") — **not implemented in any binding**.
-   Python and Java ship a docstring warning on `Lookarounds.behind()` but **no runtime detection**.
-   An AST containing `Lookbehind(Quantifier(Literal('a'), '+'))` will be silently emitted as `(?<=a+)` and crash inside `pcre2_compile()`. STRling will surface the raw native error — a violation of the **Signpost Pattern** ([`workflow.instructions.md#L13-L25`](../../.github/instructions/workflow.instructions.md#L13)).

**Verdict:** ❌ **All 17 bindings fail this requirement.**

### 2.2 AST Depth / Recursion Limits — **TOTAL ABSENCE**

A repo-wide regex search for `MAX_DEPTH | max_depth | maxDepth | DEPTH_LIMIT | depth.limit | recursion.limit | RecursionLimit` returns **zero matches**.

-   No `MAX_AST_DEPTH` constant in any compiler or emitter.
-   No test pumps a 1,000-deep `Group(Group(Group(...)))` AST through an emitter.
-   TypeScript has a single test ID `deeply_nested_quantifiers` in [e2e_combinatorial.test.ts](../../bindings/typescript/__tests__/e2e/e2e_combinatorial.test.ts) — but it tests _output correctness_, not _bounded recursion_.

**Risk:** A pathological AST can exhaust the host stack during emission (especially in recursive emitters: C, Python, Swift, Rust) **before PCRE2 ever sees the pattern**. `MATCH_LIMIT` / `DEPTH_LIMIT` configuration of the PCRE2 runtime is also untested.

**Verdict:** ❌ **No depth guard exists. No depth test exists.**

### 2.3 Unicode Property Edge Cases — **PARTIAL**

-   Basic `\p{L}` / `\p{Letter}` round-trips are covered by golden fixtures.
-   One single C test references high-surrogate range handling.
-   **Not covered anywhere:** newly added Unicode 16 scripts (e.g. `\p{Garay}`, `\p{Tulu_Tigalari}`), `\P{...}` negation edge cases, invalid property names rejection (must produce a `STRlingParseError`, not a `pcre2_compile` failure), `\p{Emoji}` mapping, surrogate-pair literal handling in non-UCS-2 bindings.

**Verdict:** ⚠️ **Property mapping is unverified beyond the smoke test.**

---

## 3. Phase 2 — The ReDoS Audit

### 3.1 Spec Mandate

[`spec/grammar/semantics.md#L218`](../../spec/grammar/semantics.md#L218):

> _"When nested unbounded quantifiers are detected (e.g., `(a+)_`), emitters should emit a **`REDOS\*RISK`\*\* warning…"\_

[`spec/grammar/semantics.md#L372-L393`](../../spec/grammar/semantics.md#L372) defines the warning code and example payload.

### 3.2 Reality

-   **No emitter implements `REDOS_RISK` detection.** Grep returns zero hits for the literal token `REDOS_RISK` in any `bindings/*/` source.
-   The only ReDoS-adjacent fixtures are `golden_redos_safe_atomic` and `golden_redos_safe_possessive` ([`test_pcre2_emitter.py#L230`](../../bindings/python/tests/e2e/test_pcre2_emitter.py#L230)). These prove the **safe form compiles**; they do **not** prove the **unsafe form is detected and warned**.
-   **Overlapping alternation** (e.g. `Alt("a", "a+")`, `Alt("a|a")`): no test in any binding asserts atomic-group rewriting or warning emission.
-   **Nested quantifiers** (`(a+)+`, `(a*)*`): no test asserts detection. AST allows construction; emitter emits verbatim.
-   **Possessive mapping** (`*+`, `++`, `?+`, `{n,m}+`): atomic & possessive emission is well-tested for the _positive_ path in 8 bindings (✅ above), but no test confirms the mapping for the **bounded** form `{n,m}+` or for `?+` specifically.

**Verdict:** ❌ **The emitter can produce known-ReDoS-vulnerable output without warning.** The `REDOS_RISK` warning channel exists in spec but is wired up nowhere.

---

## 4. Phase 3 — Fuzzing & Cross-Language Parity

### 4.1 Fuzzing

Repo-wide search for `hypothesis | proptest | quickcheck | jqwik | fuzz | fast-check`:

-   ❌ **Zero property-based or fuzz tests targeting any emitter** in any binding.
-   The Python test infra includes `pytest` but no `hypothesis` strategy for AST generation.
-   Rust crate has no `proptest` dependency.

### 4.2 Cross-Language Parity for Edge Cases

-   [`tooling/audit_omega.py`](../../tooling/audit_omega.py) verifies **conformance count and pass rate**, not edge-case coverage parity.
-   [`tooling/audit_hint_parity.py`](../../tooling/audit_hint_parity.py) verifies **parser hint** parity only — emitter warnings (`REDOS_RISK`, `vlb`) are out of scope.
-   **No tool exists** to assert that an edge-case test (e.g. "atomic group emission") that passes in C also passes in Swift. The audit matrix in §1 demonstrates the drift: 8 bindings have explicit atomic-group tests; 9 do not.

**Verdict:** ❌ **No fuzzing. No parity audit for emitter edges.**

---

## 5. Definition of Done — Status

| #   | Requirement                                               | Status                                                   |
| --- | --------------------------------------------------------- | -------------------------------------------------------- |
| 1   | Audit report identifying gaps                             | ✅ This document                                         |
| 2   | Child issues scaffolded for missing tests                 | ✅ See `docs/audits/pcre2_emitter_edges_child_issues.md` |
| 3   | Mathematical confidence that valid AST cannot crash PCRE2 | ❌ **NOT YET** — gaps must be closed first               |

The third criterion requires resolution of **at minimum** the variable-length-lookbehind detector, the AST depth guard, and the `REDOS_RISK` detector. Until those land in the reference TypeScript binding and propagate to all 17 bindings (verified by a new emitter-edges parity audit), STRling cannot claim execution-safety for arbitrary user ASTs.
