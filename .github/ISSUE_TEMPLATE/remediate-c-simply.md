---
name: Remediate: C binding — implement friendly API
about: Provide higher-level helpers and update README to not encourage raw AST creation
---

Title: Task: Implement friendly builder wrapper for C binding

Goal: Create a C-friendly fluent builder layer (macros / helper functions) that hides raw `strling_ast_*_create` C functions and update README/tests.

Target Vectors:

-   bindings/c/README.md
-   bindings/c/src/

Implementation Plan:

1. Add a helper header+source pair `bindings/c/include/strling_simply.h` and `bindings/c/src/strling_simply.c` with concise builder functions.
2. Update README to show the `simply`-style usage and add a test under `bindings/c/tests` demonstrating the US phone example using the builder helpers.

Acceptance Criteria:

-   README shows the builder usage; tests demonstrate parity and prefer helpers over raw `strling_ast_*_create` calls.
