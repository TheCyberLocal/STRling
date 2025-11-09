# Normative Testing Standard

[← Back to Developer Hub](index.md)

This document provides the **complete, formal definition** of STRling's testing philosophy: the 3-Test Standard, Combinatorial E2E Testing, and Golden Pattern Testing.

---

## Testing Philosophy

STRling employs a **spec-driven, test-driven development workflow**: **specifications → tests → features**.

All features must be fully specified before implementation begins, and all code must be validated through comprehensive testing at multiple levels.

### Normative Design Standards

The following documents define the formal testing standards that guide all test implementations:

- **[Unit Test Design](../tests/_design/unit_test_design.md)**: The "3-Test Standard" for validating individual features in isolation
- **[E2E Combinatorial Design](../tests/_design/e2e_combinatorial_design.md)**: Risk-based, tiered approach for testing feature interactions
- **[E2E Golden Pattern Design](../tests/_design/e2e_golden_pattern_design.md)**: Real-world pattern validation strategy

These standards are language-agnostic and serve as the authoritative baseline for both Python and JavaScript test suites.

---

## The 3-Test Standard

Every feature must pass **three types of tests** before being considered complete:

### 1. Unit Tests

**Purpose**: Validate individual components in isolation

**Characteristics:**
- Test single functions, classes, or modules
- Mock dependencies to isolate the unit under test
- Fast execution (milliseconds)
- Located in `bindings/{language}/tests/unit/`

**Example**: Testing the `digit(n)` function parses correctly and generates expected IR

**Python:**
```python
def test_digit_parser():
    """Test that digit(3) parses to correct AST node"""
    result = parse("digit(3)")
    assert result.type == "digit"
    assert result.count == 3
```

**JavaScript:**
```javascript
test('digit parser creates correct AST node', () => {
    const result = parse("digit(3)");
    expect(result.type).toBe("digit");
    expect(result.count).toBe(3);
});
```

### 2. End-to-End (E2E) Tests

**Purpose**: Validate complete workflows from user input to final output

**Characteristics:**
- Test the entire compilation pipeline
- Use real dependencies (no mocking)
- Verify actual regex engine behavior
- Located in `bindings/{language}/tests/e2e/`

**Example**: Full pattern compilation, matching against test strings, extracting named groups

**Python:**
```python
def test_phone_number_pattern_e2e():
    """Test complete phone number pattern workflow"""
    pattern = compile_pattern("digit(3) '-' digit(4)")
    match = pattern.match("555-1234")
    assert match is not None
    assert match.group(0) == "555-1234"
```

**JavaScript:**
```javascript
test('phone number pattern end-to-end', () => {
    const pattern = compilePattern("digit(3) '-' digit(4)");
    const match = pattern.exec("555-1234");
    expect(match).not.toBeNull();
    expect(match[0]).toBe("555-1234");
});
```

### 3. Conformance Tests

**Purpose**: Ensure consistent behavior across multiple regex engines

**Characteristics:**
- Run identical STRling patterns against multiple backends (PCRE2, ECMAScript, etc.)
- Assert matching behavior is identical across all engines
- Detect engine-specific quirks or incompatibilities
- Located in `tests/conformance/`

**Example**: Verify that character class `[a-z]` behaves identically in PCRE2 and JavaScript

**Conformance Test Structure:**
```python
def test_character_class_conformance():
    """Verify character class behavior across engines"""
    pattern_str = "in_range('a', 'z')"
    
    # Compile for PCRE2
    pcre2_pattern = compile_pattern(pattern_str, target="pcre2")
    
    # Compile for ECMAScript
    ecmascript_pattern = compile_pattern(pattern_str, target="ecmascript")
    
    # Test identical inputs
    test_inputs = ["a", "z", "A", "1", "!"]
    
    for test_input in test_inputs:
        pcre2_result = bool(pcre2_pattern.match(test_input))
        ecma_result = bool(ecmascript_pattern.match(test_input))
        assert pcre2_result == ecma_result, f"Mismatch for '{test_input}'"
```

---

## Combinatorial Testing

For features with multiple configuration options or edge cases, STRling uses **combinatorial testing** to ensure all meaningful combinations are validated.

### Approach

- Generate test cases covering all meaningful combinations of parameters
- Use property-based testing where appropriate
- Document the combinatorial matrix in test design documents

### Example: Testing Quantifiers

Quantifiers have multiple parameters that can interact:
- `min`: Minimum repetitions (0, 1, 5)
- `max`: Maximum repetitions (1, 5, unlimited)
- `greedy`: Greedy vs. lazy matching (true, false)

A combinatorial test would verify all valid combinations:

```python
@pytest.mark.parametrize("min,max,greedy", [
    (0, 1, True),
    (0, 1, False),
    (1, 5, True),
    (1, 5, False),
    (5, None, True),  # Unlimited
    (5, None, False),
])
def test_quantifier_combinations(min, max, greedy):
    """Test all valid quantifier parameter combinations"""
    pattern = create_quantifier(min=min, max=max, greedy=greedy)
    # Verify pattern compiles and behaves correctly
    assert pattern is not None
```

### Benefits

- Catches edge cases that might be missed with manual test case selection
- Provides comprehensive coverage of the feature space
- Documents all supported parameter combinations

---

## Golden Pattern Testing

For complex patterns or emitter outputs, STRling uses **golden pattern testing** to detect regressions.

### Approach

- Maintain "golden" reference outputs for known-good patterns
- Compare actual output against golden files
- Version control golden files for regression detection
- Update golden files deliberately when behavior changes

### Example Structure

```
tests/golden/
├── pcre2/
│   ├── digit_pattern.golden
│   ├── group_pattern.golden
│   └── complex_pattern.golden
└── ecmascript/
    ├── digit_pattern.golden
    └── group_pattern.golden
```

### Golden Test Implementation

**Python:**
```python
def test_against_golden_output():
    """Verify emitter output matches golden reference"""
    pattern = compile_pattern("digit(3) '-' digit(4)")
    actual_output = pattern.emit_pcre2()
    
    golden_path = Path("tests/golden/pcre2/phone_pattern.golden")
    expected_output = golden_path.read_text()
    
    assert actual_output == expected_output, (
        "Output differs from golden reference. "
        "Review changes and update golden file if intentional."
    )
```

### Updating Golden Files

When intentional behavior changes occur:

1. Review the diff between actual and golden output
2. Verify the new output is correct
3. Update the golden file with the new output
4. Document the reason for the change in the commit message

### Benefits

- Detects unintended behavioral changes
- Provides clear documentation of expected output
- Simplifies regression testing for complex patterns

---

## Test-Driven Development Workflow

Every feature follows this structured workflow:

1. **Specification** (`spec/`): Define syntax in EBNF and behavior in semantics
2. **Test Design** (`tests/_design/`): Create Test Charter documenting scope and test cases
3. **Test Implementation**: Write failing tests in appropriate test suites
4. **Feature Implementation**: Write minimal code to pass tests
5. **Verification**: Ensure code coverage and mutation testing pass
6. **Refinement**: Refactor for clarity and performance

### Test Charter Template

Test Charters are living documents that guide test implementation. See `tests/_design/__template.md` for the complete template structure.

**Key sections:**
- Feature description and scope
- Test case enumeration
- Acceptance criteria
- Edge cases and error conditions

---

## Verification Requirements

Before a feature is considered complete, it must meet these verification requirements:

### Code Coverage

- **Unit tests**: 100% coverage of new code
- **E2E tests**: All user-facing workflows covered
- **Conformance tests**: All portable features tested across engines

### Mutation Testing

- Mutation testing should demonstrate that tests are effective (i.e., mutants are killed)
- Tests should fail when the code is intentionally broken
- Low mutation score indicates weak tests that need strengthening

### Test Execution

All tests must:
- Pass consistently (no flaky tests)
- Execute in reasonable time
- Be isolated (no dependencies between tests)
- Clean up resources properly

---

## Related Documentation

- **[Developer Hub](index.md)**: Central documentation landing page
- **[Test Suite Guide](../tests/README.md)**: Test directory structure and execution
- **[Contribution Guidelines](guidelines.md)**: Development workflow and standards
