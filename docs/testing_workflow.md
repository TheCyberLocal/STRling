# Testing Philosophy & Contribution Workflow

[← Back to Developer Hub](index.md)

This document defines STRling's **high-level engineering principles** and **contribution process** for testing. It explains _why_ we test the way we do and _how_ testing fits into the contribution workflow.

---

## Testing Philosophy

### Spec-Driven, Test-Driven Development

STRling employs a **specifications → tests → features** workflow:

1. **Specifications First**: All features must be fully specified before implementation begins
2. **Tests Second**: Comprehensive tests are written based on the specification
3. **Implementation Last**: Code is written to make the tests pass

This ensures:

-   Features are well-designed before coding starts
-   Implementation is validated against a clear contract
-   Changes don't break existing behavior
-   Documentation stays synchronized with code

### Why Test-Driven Development?

**Quality**: Writing tests first forces clear thinking about requirements and edge cases

**Confidence**: Comprehensive tests enable fearless refactoring and evolution

**Documentation**: Tests serve as executable documentation of expected behavior

**Regression Prevention**: Tests catch unintended changes before they reach production

---

## The Iron Law of Test Parity

**The Python binding is the normative reference implementation.**

### What This Means

1. **Python tests define the contract**: All STRling features are first implemented and tested in Python
2. **JavaScript tests must match 1:1**: Every Python test must have a corresponding JavaScript test with identical behavior
3. **New features start in Python**: Features are not considered complete until both bindings have matching tests

### Why Python is Normative

-   **Development velocity**: Python's dynamic nature allows faster iteration
-   **Expressiveness**: Python's syntax is closer to STRling's DSL design
-   **Tooling maturity**: Python testing ecosystem is more established
-   **Consistency**: A single source of truth prevents divergence between bindings

### Maintaining Test Parity

When adding a feature:

1. Implement and test in Python first
2. Translate tests to JavaScript, ensuring:
    - Same test names (adapted to language conventions)
    - Same test cases
    - Same assertions and expected values
    - Same edge cases and error conditions

**Example of Test Parity:**

**Python (`tests/unit/test_parser.py`):**

```python
def test_digit_parser_simple():
    """Test digit parser with minimal input"""
    result = parse("digit(1)")
    assert result.type == "digit"
    assert result.count == 1
```

**JavaScript (`__tests__/unit/parser.test.js`):**

```javascript
test("digit parser simple case", () => {
    const result = parse("digit(1)");
    expect(result.type).toBe("digit");
    expect(result.count).toBe(1);
});
```

### Exceptions to the Iron Law

Engine-specific features may have unique tests, but these must be clearly documented:

```python
@pytest.mark.pcre2_only
def test_pcre2_specific_feature():
    """Test PCRE2-specific feature (not available in ECMAScript)"""
    # PCRE2-only test
```

```javascript
test("ECMAScript-specific feature", () => {
    // ECMAScript-only test
});
```

---

## Contribution Workflow

### For All Pull Requests

**All PRs must include tests.** No exceptions.

Specifically:

1. **New features** must include:

    - Unit tests following the 3-Test Standard (see Test Design Standard via Developer Hub)
    - E2E tests covering the complete workflow
    - Conformance tests if the feature is portable across engines
    - Tests in both Python and JavaScript

2. **Bug fixes** must include:

    - A test that reproduces the bug (fails before the fix)
    - Verification that the test passes after the fix
    - Tests in both bindings if the bug affects both

3. **Refactoring** must include:
    - Verification that all existing tests still pass
    - New tests if coverage gaps are discovered
    - No behavioral changes (unless intentional and documented)

### Before Submitting a PR

Run the complete test suite for both bindings:

**Python:**

```bash
cd bindings/python
pytest
```

**JavaScript:**

```bash
cd bindings/javascript
npm test
```

Ensure:

-   All tests pass
-   No new warnings or errors
-   Code coverage meets requirements (see Test Design Standard via Developer Hub)

### Test Charter Process

For significant features, create a **Test Charter** before writing tests:

1. **Create** a test charter in `tests/_design/`
2. **Document**:
    - Feature description and scope
    - Test case enumeration (unit, E2E, conformance)
    - Acceptance criteria
    - Edge cases and error conditions
3. **Review** the charter with maintainers
4. **Implement** tests based on the approved charter

See existing test charters in `tests/_design/` for examples.

---

## Verification Requirements

### Before Merge

Every PR must meet these verification requirements:

#### 1. Code Coverage

-   **Unit tests**: 100% coverage of new code
-   **E2E tests**: All user-facing workflows covered
-   **Conformance tests**: All portable features tested across engines

Use coverage tools to verify:

**Python:**

```bash
pytest --cov=src --cov-report=html
```

**JavaScript:**

```bash
npm test -- --coverage
```

#### 2. Test Quality

Tests must:

-   **Pass consistently**: No flaky tests
-   **Execute quickly**: Unit tests in milliseconds, E2E in seconds
-   **Be isolated**: No dependencies between tests
-   **Clean up resources**: Proper setup and teardown
-   **Have clear assertions**: One logical assertion per test
-   **Be maintainable**: Clear naming, good documentation

#### 3. Mutation Testing (Recommended)

Mutation testing validates that tests are effective:

-   Tests should fail when code is intentionally broken
-   High mutation score indicates strong tests
-   Low mutation score indicates weak tests that need strengthening

**Python:**

```bash
mutmut run
mutmut results
```

### CI Pipeline

All PRs are automatically verified by the CI pipeline:

1. **Linting**: Code style and quality checks
2. **Type checking**: Static type verification (TypeScript for JavaScript)
3. **Unit tests**: All unit tests must pass
4. **E2E tests**: All E2E tests must pass
5. **Conformance tests**: All conformance tests must pass
6. **Coverage**: Coverage reports generated and reviewed

---

## Test Maintenance

### Keeping Tests Green

-   **Fix broken tests immediately**: Don't let them pile up
-   **Don't disable failing tests**: Fix the root cause instead
-   **Update tests with code changes**: Keep them synchronized
-   **Remove obsolete tests**: Clean up when features are removed

### Test Refactoring

As the codebase evolves, tests need refactoring too:

-   **Extract common setup**: Use fixtures (pytest) or setup functions (Jest)
-   **Remove duplication**: Share test utilities and helpers
-   **Improve readability**: Clear names, good documentation, logical organization
-   **Optimize performance**: Reduce test execution time without sacrificing coverage

### Test Helpers and Utilities

Create reusable test utilities in:

-   `bindings/python/tests/helpers/` (Python)
-   `bindings/javascript/__tests__/helpers/` (JavaScript)

Example utilities:

-   Pattern compilation helpers
-   Common test data generators
-   Assertion helpers for complex objects
-   Mock objects for external dependencies

---

## Testing Best Practices

### Do's

✅ **Write tests first** (test-driven development)

✅ **Test behavior, not implementation**: Focus on what the code does, not how it does it

✅ **Use descriptive test names**: Name should explain what's being tested

✅ **Keep tests simple**: One logical assertion per test

✅ **Test edge cases**: Boundary values, empty inputs, null values, etc.

✅ **Use parameterized tests**: For testing multiple inputs efficiently

✅ **Mock external dependencies**: Isolate the unit under test

✅ **Test error conditions**: Verify errors are raised appropriately

### Don'ts

❌ **Don't test third-party code**: Trust that libraries work (or write conformance tests)

❌ **Don't write dependent tests**: Each test should be independent

❌ **Don't test private methods directly**: Test through public interfaces

❌ **Don't make tests brittle**: Avoid over-specification of implementation details

❌ **Don't ignore test failures**: Investigate and fix immediately

❌ **Don't skip tests**: Remove or fix them instead

❌ **Don't write tests without assertions**: Every test must verify something

---

## Related Documentation

-   **[Developer Hub](index.md)**: Return to the central documentation hub for all testing guides and standards

## LSP & Diagnostics Testing Requirements

Changes that affect parsing, error messages, or diagnostics now require an expanded verification set in addition to the existing unit and E2E tests. Specifically:

-   **Parser unit tests**: Validate parser behavior and `STRlingParseError` shapes.
-   **CLI conversion tests**: Verify the CLI Server or diagnostic normalization layer converts parser errors into the binding-agnostic diagnostic schema.
-   **LSP functional tests**: Exercise the LSP server end-to-end so editors receive diagnostics and (where applicable) code-actions/quickfixes produced by `to_lsp_diagnostic()`.

Required test commands:

**Run parser unit tests:**

```bash
pytest tests/unit
```

**Run CLI/LSP tests:**

```bash
pytest tooling/lsp-server/tests
```

Notes:

-   LSP functional tests should run in CI and locally before merging changes that touch the parser or diagnostic conversion.
-   New diagnostic messages must include unit tests asserting the exact `to_lsp_diagnostic()` output and at least one LSP-level test showing the editor receives the diagnostic with intended severity and message text.
-   When adding or modifying diagnostics, update `tests/_design/` with a brief test charter describing the acceptance criteria for the new messages.
