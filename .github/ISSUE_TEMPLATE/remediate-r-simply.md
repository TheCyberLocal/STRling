---
name: Remediate: R binding — implement "simply" API
about: Add a friendly `simply` API for R and update README/tests to avoid raw AST constructors
---

Title: Task: Implement simply builder for R binding

Goal: Add `simply`-style functions to R binding to hide raw AST constructors from users.

Target Vectors:

-   bindings/r/README.md
-   bindings/r/R/ (source)

Implementation Plan:

1. Implement an R-friendly `simply` package (R functions) that produce builder objects or lists which are converted into internal AST structures.
2. Update README US phone example and unit tests.

Acceptance Criteria:

-   README refactors the US phone example to use `simply`, and tests verify equivalence.
