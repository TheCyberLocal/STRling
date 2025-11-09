# STRling Test Design Standard

[← Back to Developer Hub](index.md)

This document is the **technical, normative standard** for writing new tests in STRling. It defines the formal testing patterns that ensure production-grade coverage.

---

## The 3-Test Standard

Every feature must pass **three types of tests** before being considered complete:

### 1. Unit Tests

**Purpose**: Validate individual components in isolation

**Characteristics:**
- Test single functions, classes, or modules
- Mock dependencies to isolate the unit under test
- Fast execution (milliseconds)
- Located in `bindings/{language}/tests/unit/` (Python) or `bindings/{language}/__tests__/unit/` (JavaScript)

**Required Test Cases (Minimum):**

Each unit must have at least **three test cases** covering:

1. **Simple Case**: Basic functionality with minimal input
2. **Typical Case**: Realistic usage with common parameters
3. **Interaction Case**: How the unit interacts with its dependencies

**Plus**: Any unique edge cases specific to the feature

**Example: Testing a `digit(n)` parser**

**Python:**
```python
def test_digit_parser_simple():
    """Test digit parser with minimal input"""
    result = parse("digit(1)")
    assert result.type == "digit"
    assert result.count == 1

def test_digit_parser_typical():
    """Test digit parser with typical usage"""
    result = parse("digit(3)")
    assert result.type == "digit"
    assert result.count == 3

def test_digit_parser_interaction():
    """Test digit parser within a larger pattern"""
    result = parse("digit(3) '-' digit(4)")
    assert len(result.children) == 3
    assert result.children[0].type == "digit"
    assert result.children[2].type == "digit"

def test_digit_parser_edge_case_zero():
    """Test digit parser rejects zero count"""
    with pytest.raises(ValueError, match="count must be positive"):
        parse("digit(0)")
```

**JavaScript:**
```javascript
test('digit parser simple case', () => {
    const result = parse("digit(1)");
    expect(result.type).toBe("digit");
    expect(result.count).toBe(1);
});

test('digit parser typical case', () => {
    const result = parse("digit(3)");
    expect(result.type).toBe("digit");
    expect(result.count).toBe(3);
});

test('digit parser interaction case', () => {
    const result = parse("digit(3) '-' digit(4)");
    expect(result.children).toHaveLength(3);
    expect(result.children[0].type).toBe("digit");
    expect(result.children[2].type).toBe("digit");
});

test('digit parser edge case - zero count', () => {
    expect(() => parse("digit(0)")).toThrow("count must be positive");
});
```

### 2. End-to-End (E2E) Tests

**Purpose**: Validate complete workflows from user input to final output

**Characteristics:**
- Test the entire compilation pipeline (parse → compile → emit)
- Use real dependencies (no mocking)
- Verify actual regex engine behavior
- Located in `bindings/{language}/tests/e2e/` (Python) or `bindings/{language}/__tests__/e2e/` (JavaScript)

**Required Test Cases:**

For each feature, create E2E tests that exercise:

1. **Compilation**: Pattern compiles successfully
2. **Matching**: Compiled pattern matches expected inputs
3. **Non-Matching**: Compiled pattern rejects invalid inputs
4. **Extraction**: Captures and groups work as expected (if applicable)

**Example: Phone number pattern E2E test**

**Python:**
```python
def test_phone_number_pattern_e2e():
    """Test complete phone number pattern workflow"""
    # Compilation
    pattern = compile_pattern("digit(3) '-' digit(4)")
    
    # Matching positive case
    match = pattern.match("555-1234")
    assert match is not None
    assert match.group(0) == "555-1234"
    
    # Matching negative case
    assert pattern.match("12-34") is None
    assert pattern.match("555-12345") is None
```

**JavaScript:**
```javascript
test('phone number pattern end-to-end', () => {
    // Compilation
    const pattern = compilePattern("digit(3) '-' digit(4)");
    
    // Matching positive case
    const match = pattern.exec("555-1234");
    expect(match).not.toBeNull();
    expect(match[0]).toBe("555-1234");
    
    // Matching negative case
    expect(pattern.exec("12-34")).toBeNull();
    expect(pattern.exec("555-12345")).toBeNull();
});
```

### 3. Conformance Tests

**Purpose**: Ensure consistent behavior across multiple regex engines

**Characteristics:**
- Run identical STRling patterns against multiple backends (PCRE2, ECMAScript, etc.)
- Assert matching behavior is identical across all engines
- Detect engine-specific quirks or incompatibilities
- Located in `tests/conformance/`

**Required Test Cases:**

For portable features, verify:

1. **Identical Match Results**: Same input produces same match/no-match across engines
2. **Identical Capture Groups**: Extracted values are identical
3. **Identical Edge Cases**: Boundary conditions behave the same

**Example: Character class conformance**

```python
def test_character_class_conformance():
    """Verify character class behavior across engines"""
    pattern_str = "in_range('a', 'z')"
    
    # Compile for PCRE2
    pcre2_pattern = compile_pattern(pattern_str, target="pcre2")
    
    # Compile for ECMAScript
    ecmascript_pattern = compile_pattern(pattern_str, target="ecmascript")
    
    # Test identical inputs
    test_inputs = ["a", "z", "m", "A", "1", "!"]
    
    for test_input in test_inputs:
        pcre2_result = bool(pcre2_pattern.match(test_input))
        ecma_result = bool(ecmascript_pattern.match(test_input))
        assert pcre2_result == ecma_result, f"Mismatch for '{test_input}'"
```

---

## Combinatorial E2E Testing

For features with multiple configuration options or parameters, STRling uses **combinatorial testing** to ensure all meaningful combinations are validated.

### Strategy: Pragmatic Pairwise (N=2)

**Definition**: Test all pairwise combinations of feature parameters

**When to Use**: Features with 2-4 independent parameters

**Example: Quantifier testing with 3 parameters**

Parameters:
- `min`: Minimum repetitions (values: 0, 1, 5)
- `max`: Maximum repetitions (values: 1, 5, unlimited)
- `greedy`: Greedy vs. lazy matching (values: true, false)

Rather than testing all 3 × 3 × 2 = 18 combinations, pairwise testing ensures every pair of values appears together at least once, typically requiring ~8-10 test cases.

**Implementation:**

```python
@pytest.mark.parametrize("min,max,greedy", [
    # Pairwise combinations covering all parameter pairs
    (0, 1, True),
    (0, 5, False),
    (0, None, True),
    (1, 1, False),
    (1, 5, True),
    (1, None, False),
    (5, 5, True),
    (5, None, False),
])
def test_quantifier_pairwise_combinations(min, max, greedy):
    """Test pairwise combinations of quantifier parameters"""
    pattern = create_quantifier(min=min, max=max, greedy=greedy)
    # Verify pattern compiles and behaves correctly
    assert pattern is not None
    # Additional assertions based on parameters...
```

### Strategy: Strategic Triplets (N=3)

**Definition**: Test specific 3-way combinations that are known to interact

**When to Use**: Features where certain parameter combinations have special behavior or known edge cases

**Example: Testing specific triplet interactions**

```python
@pytest.mark.parametrize("min,max,greedy,expected_behavior", [
    # Known interaction cases
    (0, 0, True, "matches_empty"),
    (0, 0, False, "matches_empty"),
    (1, 1, True, "matches_exactly_one"),
    (0, None, False, "lazy_unlimited"),
])
def test_quantifier_strategic_triplets(min, max, greedy, expected_behavior):
    """Test specific parameter triplets with known interactions"""
    pattern = create_quantifier(min=min, max=max, greedy=greedy)
    # Verify expected behavior based on the combination
    if expected_behavior == "matches_empty":
        assert pattern.match("")
    # ... other behaviors
```

### Benefits

- **Efficiency**: Catches most bugs with fewer test cases than exhaustive testing
- **Coverage**: Ensures all parameter interactions are tested
- **Maintainability**: Easier to understand and extend than exhaustive tests

---

## Golden Pattern Testing

For complex patterns or emitter outputs, STRling uses **golden pattern testing** to detect regressions.

### Categories

#### 1. Validation Goldens

**Purpose**: Verify that emitted patterns are syntactically correct and semantically equivalent

**Example**: Ensure PCRE2 output is valid PCRE2 syntax

#### 2. Parsing Goldens

**Purpose**: Verify that complex patterns parse to the expected AST structure

**Example**: Ensure nested groups and backreferences produce correct IR

#### 3. Stress Test Goldens

**Purpose**: Verify behavior of pathological or performance-critical patterns

**Example**: Deeply nested patterns, long repetitions, complex backreferences

### Implementation

**Directory Structure:**

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

**Golden Test Implementation:**

**Python:**
```python
from pathlib import Path

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

**Updating Golden Files:**

When intentional behavior changes occur:

1. Review the diff between actual and golden output
2. Verify the new output is correct
3. Update the golden file with the new output
4. Document the reason for the change in the commit message

### Benefits

- **Regression Detection**: Catches unintended behavioral changes
- **Documentation**: Golden files serve as executable documentation
- **Confidence**: Enables refactoring with confidence that behavior is preserved

---

## Test Naming Conventions

### Python

Use descriptive, snake_case names with the `test_` prefix:

```python
def test_feature_simple_case():
    """One-line description of what's being tested"""
    pass

def test_feature_edge_case_negative_input():
    """Test specific edge case with negative input"""
    pass
```

### JavaScript

Use descriptive strings with Jest's `test()` or `describe()` blocks:

```javascript
test('feature simple case', () => {
    // Test implementation
});

describe('feature edge cases', () => {
    test('handles negative input', () => {
        // Test implementation
    });
});
```

---

## Code Coverage Requirements

Before a feature is considered complete:

### Unit Tests
- **100% coverage** of new code
- All branches and edge cases must be exercised

### E2E Tests
- All **user-facing workflows** must be covered
- Happy path and common error cases

### Conformance Tests
- All **portable features** tested across supported engines
- Engine-specific features clearly documented as such

---

## Related Documentation

- **[Developer Hub](index.md)**: Central documentation landing page
- **[Test Setup Guide](testing_setup.md)**: How to run tests
- **[Testing Workflow](testing_workflow.md)**: Testing philosophy and contribution process
- **[Contribution Guidelines](guidelines.md)**: Development workflow and standards
