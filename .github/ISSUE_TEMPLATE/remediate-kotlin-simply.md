---
name: Remediate: Kotlin binding — implement "simply" API
about: Add fluent `simply` API to Kotlin binding and update examples/tests
---

Title: Task: Implement simply builder for Kotlin binding

Goal: Add an idiomatic `simply` DSL for Kotlin so users don't manually instantiate AST data classes.

Target Vectors:

-   bindings/kotlin/README.md
-   bindings/kotlin/src/

Implementation Plan:

1. Implement `bindings/kotlin/src/main/kotlin/STRling/Simply.kt` exposing builder functions and extension functions for idiomatic use.
2. Internally map builders to AST types that remain internal-only.
3. Update README/examples and add a unit test for the US phone example.

Acceptance Criteria:

-   `simply` DSL present, README updated, and tests show the builder matching the reference output.
