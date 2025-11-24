---
name: Remediate: Go binding — implement friendly "simply" API
about: Add fluent builder API to Go binding and update README/tests to remove direct AST usage
---

Title: Task: Implement simply builder for Go binding

Goal: Provide a fluent, idiomatic `simply` package in `bindings/go` so library consumers do not need to construct raw AST nodes (NodeWrapper / pointer-heavy struct literals) when building patterns.

Target Vectors:

-   bindings/go/README.md
-   bindings/go/src/ (or top-level go package files under bindings/go)
-   new path: bindings/go/simply/
-   tests: bindings/go/tests/ (or existing test files)

Implementation Plan:

1. Add `bindings/go/simply` package exposing builder functions `Start()`, `Digit(n)`, `Capture(...)`, `Merge(...)`, `Quantifier(...)`, `Group(...)`, etc., returning friendly Go structs (not raw internal AST types) or types that wrap AST privately.
2. Provide conversion from the high-level builder objects into the internal AST (kept private) for existing emission/conformance tests.
3. Replace the US phone example in `bindings/go/README.md` with the `simply` usage example.
4. Add unit tests verifying that the builder produces identical IR/regex to the TypeScript reference for the US phone example.
5. Add a short migration note in README indicating previous AST-style idioms are now internal.

Acceptance Criteria:

-   `bindings/go/simply` exists with builder functions clearly documented.
-   `bindings/go/README.md` US phone example uses `simply` instead of direct AST constructions.
-   Tests under `bindings/go` include one that builds the US phone example using `simply` and validates parity with reference.
-   Public docs and exported symbols do not expose raw AST node constructors as recommended for user code.
