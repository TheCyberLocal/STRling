# Project Architecture & Strategy

[← Back to Developer Hub](index.md)

This document consolidates the durable architecture and operating principles that used to live in the ecosystem status report. It keeps the long-lived design rules in permanent documentation and leaves time-sensitive audit notes out of the main docs.

---

## Architecture Snapshot

STRling is organized as a compiler pipeline:

1. **Parse** the STRling DSL into an Abstract Syntax Tree (AST).
2. **Compile** the AST into a target-agnostic Intermediate Representation (IR).
3. **Emit** a target regex string from the IR.

That pipeline is the core project contract. New features should fit into it rather than bypass it.

### Source of Truth Rules

-   The **TypeScript binding** is the logic reference implementation.
-   The **Python binding** (`bindings/python/pyproject.toml`) is the version source of truth.
-   Spec changes should keep grammar, semantics, schemas, and generated fixtures aligned.

### Binding Responsibilities

-   **Specification** lives in `spec/`.
-   **Core compiler logic** lives in each binding's `src/core/` area.
-   **Emitters** are pure transformations from IR to target regex output.
-   **Bindings** provide language-specific APIs and convenience wrappers.
-   **Tests** verify syntax, semantics, conformance, and end-to-end behavior.

### Emitter Contract

Emitters must be deterministic and side-effect free. The same IR and flags should always produce the same output, and shared escaping or validation logic should live in common helpers instead of being duplicated in each emitter.

### Diagnostics Architecture

Real-time diagnostics follow a binding-agnostic flow:

**Editor -> LSP Server -> CLI Server -> Parser**

The parser remains authoritative. The CLI server normalizes parser output into a stable diagnostic contract, and the LSP server handles editor protocol concerns.

### Simply API

The Simply API is the fluent, programmatic layer over the same IR model. It exists so developers can build patterns through chainable method calls instead of raw DSL strings, while still compiling through the same architecture.

---

## Strategy System Design

STRling's operating model is intentionally staged. The project is expected to move through these durable phases whenever a major capability is being introduced or stabilized:

1. **Functional Remediation** - make the core feature work in the reference implementation first.
2. **Pipeline Parity** - mirror that behavior across the other bindings.
3. **Test Hardening** - add the unit, semantic, E2E, and conformance coverage required to keep the feature stable.
4. **Documentation Standardization** - document the feature in junior-friendly, permanent docs so the behavior stays understandable.

This model is useful because it keeps the work sequenced. The project does not treat implementation as complete until the behavior, tests, and documentation all line up.

### Release Readiness Rule

Certification should be treated as a gate, not a summary. The Omega Audit and related test suites are the mechanism that prove the system is ready for release.

### Canary Strategy

For registry or release validation, the preferred pattern is a sandbox canary:

1. Publish the candidate version to a controlled test registry or sandbox.
2. Install the exact published version in a separate validation environment.
3. Compile a fixed corpus and compare emitted IR or regex snapshots against expected fixtures.
4. Promote the release only if the sandbox run matches expectations.

This keeps final release decisions based on observable behavior instead of on assumptions about the build.

---

## Related Documentation

-   [Architectural Principles](architecture.md)
-   [Testing Philosophy & Contribution Workflow](testing_workflow.md)
-   [Test Design Standard](testing_design.md)
-   [Releasing STRling](releasing.md)
-   [CI/CD Pipeline Setup Guide](ci_cd_setup.md)
-   [Contribution & Documentation Guidelines](guidelines.md)
