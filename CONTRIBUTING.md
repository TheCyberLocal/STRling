# Contributing to STRling

[← Back to Developer Hub](docs/index.md)

Thank you for contributing to STRling! This document covers the essentials for making changes to the project. For the full development workflow, commit standards, PR process, and documentation guidelines, see [docs/guidelines.md](docs/guidelines.md).

## Quick Start

```bash
./strling bootstrap all   # Setup, build, and test every binding
./strling test all        # Re-run all binding test suites
./strling check           # Run the established fast quality baseline
./strling certify         # Run the current certification aggregate
./strling audit           # Run the strict final omega audit
```

Use `./strling environment <binding>` to validate declared tool versions and
append `--json` to a quality command for automation. The
[toolchain and quality-command policy](docs/toolchains.md) defines capability
states, aggregate scope, and transitional conditions.

## The Hint-Spec Requirement

STRling's **pedagogical hint system** is part of the shared conformance contract. Every parser error fixture in `tests/spec/` must include an `expected_hint` field with the **exact** hint string produced by the TypeScript reference implementation.

### When Adding a New Error or Diagnostic

1. **TypeScript first**: Add or update the hint pattern in `bindings/typescript/src/STRling/core/hint_engine.ts`.
2. **Regenerate fixtures**: Run `cd bindings/typescript && npm run build:specs` to regenerate `tests/spec/*.json`. Every error fixture will automatically receive the correct `expected_hint` from the TypeScript HintEngine.
3. **Implement in other bindings**: Each binding's HintEngine must produce the **same exact string** for the same error. The conformance runners assert exact equality.
4. **Verify**: Run the conformance suites for affected bindings to confirm `expected_hint` matches.

### Fixture Schema

Error fixtures are validated against `spec/schema/conformance-fixture.schema.json`. The schema enforces:

-   If `expected_error` is present, `expected_hint` **must** also be present.
-   `expected_hint` is an exact-match contract value, not a substring or approximation.

### Key Principle

> The TypeScript HintEngine is the **Single Source of Truth** for all hint text. Other bindings mirror these strings exactly. The shared spec fixtures enforce cross-binding consistency.

## Additional Resources

-   **[Developer Hub](docs/index.md)**: Architecture, philosophy, and contribution guides
-   **[Contribution Guidelines](docs/guidelines.md)**: Full development workflow, commit standards, and PR process
-   **[Test Suite Guide](tests/README.md)**: Testing strategy and directory structure
-   **[Toolchains and Quality Commands](docs/toolchains.md)**: Runtime policy, canonical commands, and structured results
-   **[Specification Hub](spec/README.md)**: Formal grammar and semantics
