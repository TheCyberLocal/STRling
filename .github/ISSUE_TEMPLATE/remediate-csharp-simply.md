---
name: Remediate: C# binding — implement "simply" API
about: Add a fluent `simply` API for C# binding and update README/tests
---

Title: Task: Implement simply builder for C# binding

Goal: Provide a `simply` helper library (namespace) so README and consumers avoid `new Group(...)` AST constructions.

Target Vectors:

-   bindings/csharp/README.md
-   bindings/csharp/src/

Implementation Plan:

1. Add `bindings/csharp/src/STRling/Simply` namespace exposing builder functions and method-chaining.
2. Add conversion helpers to internal AST for tests.
3. Update README and add unit tests mirroring the TypeScript US phone example using `simply`.

Acceptance Criteria:

-   README demonstrates `simply` usage; tests validate parity with TypeScript output.
