# STRling Test Suite

This guide explains the **directory layout** and **test execution philosophy** for developers working in the `tests/` directory.

For comprehensive testing philosophy, standards, and the complete development workflow, see the [Testing Documentation](../docs/index.md#testing-documentation).

## Quick Reference

### Test Directory Structure

```
tests/
├── spec/              # SHARED SPEC SUITE (Single Source of Truth)
│   ├── *.json         # Generated JSON ASTs for all bindings to verify
│   └── README.md      # Details on the spec format
├── _design/           # Test Charter documents (human-readable test plans)
│   ├── unit/          # Unit test charters
│   ├── e2e/           # E2E test charters
│   └── __template.md  # Template for new Test Charters
└── conformance/       # [LEGACY] Cross-engine conformance tests
```

### Binding-Specific Tests

Each language binding maintains its own test directory:

-   **Python**: `bindings/python/tests/` (unit/ and e2e/ subdirectories)
-   **JavaScript**: `bindings/javascript/__tests__/` (unit/ and e2e/ subdirectories)
-   **Java**: `bindings/java/src/test/`
-   **C**: `bindings/c/tests/`

## Test Execution Philosophy

STRling follows a **spec-driven, test-driven development workflow**: **specifications → tests → features**.

### The Shared Spec Suite (SSOT)

The core logic of STRling is defined in the **Shared Spec Suite** located in `tests/spec/`. This directory contains JSON files that represent the "Golden Master" for parsing and compilation.

**The Golden Master Workflow:**

1.  **Generate**: The JavaScript binding is the reference implementation. When logic changes in JS, run `npm run build:specs` to regenerate the JSON specs in `tests/spec/`.
2.  **Commit**: Commit the updated `tests/spec/*.json` files.
3.  **Verify**: All other bindings (Python, Java, C, etc.) run their test suites against these JSON files to ensure they match the reference implementation.

### The 3-Test Standard

Every feature must pass three types of tests:

1. **Unit Tests**: Validate individual components in isolation
2. **E2E Tests**: Validate complete workflows from input to output
3. **Conformance Tests**: Ensure consistent behavior across regex engines (now largely covered by the Shared Spec Suite)

**See the [Test Design Standard](../docs/testing_design.md#the-3-test-standard) for detailed explanations of each test type.**

## Test Design Documents

### Purpose

Before writing any test code, create a **Test Charter** in `tests/_design/`. This document:

-   Defines the scope and purpose of the test suite
-   Enumerates all test cases
-   Specifies the "definition of done" for the feature
-   Serves as living documentation

### Creating a Test Charter

1. Copy `tests/_design/__template.md` to the appropriate subdirectory
2. Fill in the charter following the template structure
3. Review with the team before implementing tests
4. Use the charter as a guide when writing actual test code

## Running Tests

### Shared Spec Generation (JavaScript)

```bash
cd bindings/javascript
npm run build:specs        # Regenerate tests/spec/*.json
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

### Java Tests

```bash
cd bindings/java
mvn test
```

### C Tests

```bash
cd bindings/c
make tests
```

## Test Development Workflow

The complete test-driven development workflow:

1. **Specification**: Define feature in `spec/grammar/dsl.ebnf` and `spec/grammar/semantics.md`
2. **Test Design**: Create Test Charter in `tests/_design/`
3. **Test Implementation**: Write failing tests in appropriate directories
4. **Feature Implementation**: Write minimal code to pass tests
5. **Verification**: Ensure coverage and mutation testing pass
6. **Refinement**: Refactor while keeping tests green

**For complete details, see the [Testing Philosophy & Workflow](../docs/testing_workflow.md#contribution-workflow).**

## Additional Resources

-   **[Test Setup Guide](../docs/testing_setup.md)**: How to run tests locally
-   **[Test Design Standard](../docs/testing_design.md)**: How to write effective tests
-   **[Testing Philosophy & Workflow](../docs/testing_workflow.md)**: Testing philosophy and contribution process
-   **[Developer Hub](../docs/index.md)**: Central documentation landing page
-   **[Specification Hub](../spec/README.md)**: Formal grammar and semantics
-   **[Contribution Guidelines](../docs/guidelines.md)**: Development workflow and documentation standards
