---
name: Remediate: Dart binding — implement "simply" API
about: Add fluent builder API to Dart binding and update README/tests
---

Title: Task: Implement simply builder for Dart binding

Goal: Provide a `simply` builder for Dart and update README examples to avoid raw AST Node creation.

Target Vectors:

-   bindings/dart/README.md
-   bindings/dart/lib/

Implementation Plan:

1. Add `bindings/dart/lib/simply.dart` with builder helpers that produce high-level builder objects.
2. Provide internal mapping to existing AST classes for test/emit.
3. Update README example and tests with `simply` usage.

Acceptance Criteria:

-   `simply` API implemented, README updated, tests added to demonstrate parity with TypeScript.
