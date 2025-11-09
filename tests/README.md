# STRling Test Suite

This guide explains the **directory layout** and **test execution philosophy** for developers working in the `tests/` directory.

For comprehensive testing philosophy, standards, and the complete development workflow, see the [Documentation Hub](../docs/README.md#testing-philosophy).

## Quick Reference

### Test Directory Structure

```
tests/
├── _design/           # Test Charter documents (human-readable test plans)
│   ├── unit/         # Unit test charters
│   ├── e2e/          # E2E test charters
│   └── __template.md # Template for new Test Charters
└── conformance/       # Cross-engine conformance tests
```

### Binding-Specific Tests

Each language binding maintains its own test directory:

- **Python**: `bindings/python/tests/` (unit/ and e2e/ subdirectories)
- **JavaScript**: `bindings/javascript/__tests__/` (unit/ and e2e/ subdirectories)

## Test Execution Philosophy

STRling follows a **spec-driven, test-driven development workflow**: **specifications → tests → features**.

### The 3-Test Standard

Every feature must pass three types of tests:

1. **Unit Tests**: Validate individual components in isolation
2. **E2E Tests**: Validate complete workflows from input to output
3. **Conformance Tests**: Ensure consistent behavior across regex engines

**See the [Testing Philosophy](../docs/README.md#testing-philosophy) section in the Documentation Hub for detailed explanations of each test type.**

## Test Design Documents

### Purpose

Before writing any test code, create a **Test Charter** in `tests/_design/`. This document:

- Defines the scope and purpose of the test suite
- Enumerates all test cases
- Specifies the "definition of done" for the feature
- Serves as living documentation

### Creating a Test Charter

1. Copy `tests/_design/__template.md` to the appropriate subdirectory
2. Fill in the charter following the template structure
3. Review with the team before implementing tests
4. Use the charter as a guide when writing actual test code

## Conformance Testing

### Purpose

Conformance tests verify that STRling patterns produce **identical behavior** across multiple regex engines (PCRE2, ECMAScript, etc.).

### Location

- **Directory**: `tests/conformance/`
- **Scope**: Project-wide (not binding-specific)

### How It Works

1. Define a STRling pattern
2. Compile it to multiple target engines
3. Run identical test inputs against each compiled pattern
4. Assert that matching behavior is identical across all engines

### When to Add Conformance Tests

- When implementing core features that should work across all engines
- When discovering engine-specific quirks or incompatibilities
- When adding support for a new regex engine

## Running Tests

### Global Conformance Tests

```bash
# Run conformance tests
cd tests/conformance
# Follow binding-specific instructions for test execution
```

### Python Tests

```bash
cd bindings/python
pytest tests/unit          # Run unit tests
pytest tests/e2e           # Run E2E tests
pytest tests               # Run all Python tests
```

### JavaScript Tests

```bash
cd bindings/javascript
npm test                   # Run all JavaScript tests
npm test -- unit          # Run unit tests
npm test -- e2e           # Run E2E tests
```

## Test Development Workflow

The complete test-driven development workflow:

1. **Specification**: Define feature in `spec/grammar/dsl.ebnf` and `spec/grammar/semantics.md`
2. **Test Design**: Create Test Charter in `tests/_design/`
3. **Test Implementation**: Write failing tests in appropriate directories
4. **Feature Implementation**: Write minimal code to pass tests
5. **Verification**: Ensure coverage and mutation testing pass
6. **Refinement**: Refactor while keeping tests green

**For complete details, see the [Development Workflow](../docs/README.md#development-workflow) in the Documentation Hub.**

## Additional Resources

- **[Developer Hub](../docs/index.md)**: Complete testing philosophy and development workflow
- **[Specification Hub](../spec/README.md)**: Formal grammar and semantics
- **[Contribution Guidelines](../docs/guidelines.md)**: Development workflow and documentation standards
