---
name: Remediate: Swift binding — implement "simply" API
about: Add a fluent `simply` builder to Swift and update README/examples/tests
---

Title: Task: Implement simply builder for Swift binding

Goal: Provide an ergonomic Swift `simply` API so the README and public examples stop constructing AST enums directly.

Target Vectors:

-   bindings/swift/README.md
-   bindings/swift/Sources/STRling/ (or similar source path)

Implementation Plan:

1. Implement a `Simply` module that provides static constructors and method-chaining helpers for building patterns.
2. Translate the builders into the AST internally for emission and conformance tests.
3. Update README and unit tests demonstrating the US phone example with `Simply` instead of AST enum values.

Acceptance Criteria:

-   `simply` API is present and discoverable, examples updated in README, and tests added to mirror TypeScript output.
