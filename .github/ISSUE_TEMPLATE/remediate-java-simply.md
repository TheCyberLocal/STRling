---
name: Remediate: Java binding — implement "simply" API
about: Add fluent builder API to Java binding and update README/tests to stop exposing raw AST
---

Title: Task: Implement simply builder for Java binding

Goal: Provide a `simply` package for Java so example usage and library consumers use a fluent, safe builder instead of `new Nodes.*` AST constructors.

Target Vectors:

-   bindings/java/README.md
-   bindings/java/src/main/java/com/strling/simply/
-   bindings/java/src/main/java/com/strling/nodes/ (internal AST types)

Implementation Plan:

1. Create `com.strling.simply` builder classes and static helpers mirroring the TypeScript `simply` semantics.
2. Implement conversion helpers from builder objects into internal AST node types (kept package-private).
3. Update README with `simply` builder example for the US phone number.
4. Add unit tests to assert parity with the reference TypeScript example.

Acceptance Criteria:

-   `bindings/java` exposes a documented `simply` API and hides raw AST constructors from public examples.
-   README examples show `simply` usage and tests cover the US phone case.
