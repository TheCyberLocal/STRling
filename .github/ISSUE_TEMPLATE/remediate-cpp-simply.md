---
name: Remediate: C++ binding — implement "simply" API
about: Add friendly builder helpers to C++ binding and update README/examples to remove pointer boilerplate
---

Title: Task: Implement simply builder for C++ binding

Goal: Add a `simply` namespace and helper functions that avoid exposing `std::unique_ptr` and raw AST plumbing in examples.

Target Vectors:

-   bindings/cpp/README.md
-   bindings/cpp/src/

Implementation Plan:

1. Implement a `simply` namespace that returns small value objects or managed handles wrapping the internal AST.
2. Provide conversion path to internal AST for emission tests.
3. Update README and add tests using the `simply` helpers for the US phone example.

Acceptance Criteria:

-   README and tests use `simply` API; examples do not rely on manual pointer wiring.
