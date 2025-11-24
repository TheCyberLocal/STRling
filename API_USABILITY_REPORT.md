# STRling API Usability Audit

**Date:** 2025-11-23

This audit verifies whether each language binding exposes a high-level, fluent `simply` builder API (gold standard) or forces users to construct raw AST nodes directly. The STRling Promise requires zero-friction, semantic pattern construction — any exposure of raw AST node construction (NodeWrapper, direct struct/class/node constructors, explicit pointer usage, large multi-line initializers) is a hard fail.

| Binding    |   Tier    | Verdict | Evidence (key path)                                                                   | Remediation Plan                                                                           |
| :--------- | :-------: | :------ | :------------------------------------------------------------------------------------ | :----------------------------------------------------------------------------------------- |
| TypeScript | 🥇 Tier 1 | Pass    | `bindings/typescript/README.md` + `bindings/typescript/src/STRling/simply/`           | N/A — friendly `simply` exists and is used in README.                                      |
| Python     | 🥇 Tier 1 | Pass    | `bindings/python/README.md` + `bindings/python/src/STRling/simply/`                   | N/A — friendly `simply` exists and is used in README.                                      |
| Rust       | 🥇 Tier 1 | Pass    | `bindings/rust/README.md` + `bindings/rust/src/simply.rs`                             | N/A — friendly `simply` exists and is used in README.                                      |
| Java       | 💀 Tier 3 | FAIL    | `bindings/java/README.md` shows `new Nodes.*` AST constructors                        | Implement `simply` package and update README to use it (wrap AST types).                   |
| Swift      | 💀 Tier 3 | FAIL    | `bindings/swift/README.md` shows enum/AST construction                                | Provide `simply`-style API and update README to use it.                                    |
| Go         | 💀 Tier 3 | FAIL    | `bindings/go/README.md` shows `NodeWrapper` + pointer-heavy struct literals           | Priority: implement `bindings/go/simply` to expose fluent builder and update README/tests. |
| C++        | 💀 Tier 3 | FAIL    | `bindings/cpp/README.md` uses `std::make_unique` and manual AST wiring                | Add `simply` namespace and helpers to remove pointer plumbing in examples.                 |
| PHP        | 💀 Tier 3 | FAIL    | `bindings/php/README.md` uses `new Group(...)` style constructors                     | Add fluent `simply` builder wrappers and update README.                                    |
| Kotlin     | 💀 Tier 3 | FAIL    | `bindings/kotlin/README.md` constructs AST using data classes                         | Implement `simply` namespace for concise builder use.                                      |
| Dart       | 💀 Tier 3 | FAIL    | `bindings/dart/README.md` shows AST Node construction                                 | Add `simply` builder functions and adjust README/tests.                                    |
| R          | 💀 Tier 3 | FAIL    | `bindings/r/README.md` shows `strling_group` / `strling_sequence` style constructors  | Add idiomatic `simply` functions to hide AST internals.                                    |
| Perl       | 💀 Tier 3 | FAIL    | `bindings/perl/README.md` shows `STRling::Core::Nodes::Group->new` usage              | Add a `simply`-style DSL module and update examples.                                       |
| C          | 💀 Tier 3 | FAIL    | `bindings/c/README.md` uses `strling_ast_*_create` functions / low-level constructors | Provide a friendly C API wrapper (fluent builder macros / helpers).                        |
| C#         | 💀 Tier 3 | FAIL    | `bindings/csharp/README.md` uses `new Group()` and node lists                         | Provide `simply` helpers and update README and tests.                                      |
| F#         | 🥈 Tier 2 | Partial | `bindings/fsharp/README.md` placeholder; AST types exposed in source                  | Create friendly public API wrappers that hide raw AST types; update README.                |
| Lua        | 🥈 Tier 2 | Partial | `bindings/lua/README.md` / source is minimal; no friendly `simply` example            | Implement `simply` idioms in Lua binding or add clearer examples.                          |
| Ruby       | 🥈 Tier 2 | Partial | `bindings/ruby/README.md` appears placeholder; no clear `simply` example              | Add `simply` builder layer or update README to document fluent usage.                      |

---

Summary

-   Total bindings: 17
-   Tier 1 (Gold — friendly `simply` used & implemented): 3 (TypeScript, Python, Rust)
-   Tier 2 (Partial / ambiguous / placeholders): 3 (F# / Lua / Ruby)
-   Tier 3 (Fail — AST leak / raw construction in README): 11 (Java, Swift, Go, C++, PHP, Kotlin, Dart, R, Perl, C, C#)

Evidence notes

-   A binding is marked Tier 3 if the README or primary examples show direct AST construction (e.g., `NodeWrapper`, `new Group`, `&strling.Group`, multi-line struct initializers, pointer or smart-pointer plumbing). Tier 1 requires README usage of a `simply`-style builder and the presence of a `simply` implementation in source or tests. Tier 2 denotes placeholder or partial bindings where the documentation or implementation is incomplete or ambiguous.

Top priority remediation — immediate action items

1. Go (bindings/go): This is a high-priority FAIL: README shows `NodeWrapper` and pointer-heavy struct literals. Priority: implement `bindings/go/simply` exposing a fluent builder, update README with `simply` example, add unit tests replicating the TypeScript US-phone example.
2. Java, Swift, C++, PHP, Kotlin, Dart, R, Perl, C#, C: All failed bindings should be prioritized after Go. Each requires adding a `simply` builder module and updating README examples and tests to stop promoting direct AST usage.

Suggested next steps

-   Create per-binding remediation tasks/issue templates to track and assign work.
-   Implement a proof-of-concept `simply` builder for Go (bindings/go/simply) — lowest friction and high-impact, as Go currently violates the zero-friction promise.
-   Create CI checks that scan README files or example files for AST-signature tokens (`NodeWrapper`, `new Group`, `->new(`, `&strling`) and fail the build for committed READMEs that contain them.

If you want, I can now create per-binding task files for the Tier3 list and start implementing the Go proof-of-concept (builder, README, tests) — next step I recommend is the Go fix.
