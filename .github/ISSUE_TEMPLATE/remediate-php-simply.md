---
name: Remediate: PHP binding — implement "simply" API
about: Add fluent builder API for PHP binding and update README/tests
---

Title: Task: Implement simply builder for PHP binding

Goal: Provide `simply` helper functions/classes in `bindings/php` to remove the need for `new Group(...)` style AST usage by consumers.

Target Vectors:

-   bindings/php/README.md
-   bindings/php/src/

Implementation Plan:

1. Add `bindings/php/src/STRling/Simply.php` with fluent helpers.
2. Map the builder internals to the AST for emission and testing.
3. Update README to use `simply` and add tests demonstrating the US phone example.

Acceptance Criteria:

-   README and tests use `simply` builder and no longer show direct AST `new` constructors for user examples.
