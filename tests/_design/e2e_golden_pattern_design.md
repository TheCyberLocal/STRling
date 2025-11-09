# E2E Test Standard: Golden Pattern Validation

## Purpose

This document defines STRling's normative end-to-end (E2E) golden pattern testing standard. These tests validate STRling's ability to solve real-world, production-grade problems by compiling complex, practical patterns correctly.

## Philosophy

Unlike systematic testing (unit tests and combinatorial tests), golden pattern tests are **qualitative recipes** that demonstrate STRling can handle real-world use cases. These tests:

- Are **not exhaustive** — they sample representative patterns from real-world usage
- Focus on **practical value** — validate patterns developers actually need
- Serve as **living documentation** — demonstrate STRling's capabilities
- Provide **regression protection** — ensure complex patterns continue to work

Golden patterns are the "proof" that STRling delivers on its promise to make regex development more maintainable while producing correct, efficient output.

## Categories of Coverage

Golden pattern tests must cover three distinct categories to demonstrate comprehensive real-world applicability:

### Category 1: Common Validation Patterns

**Purpose:** Verify STRling can compile patterns for validating user input in common scenarios.

**Required Patterns:**

1. **Email Address** (RFC 5322 subset)
   - Pattern: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
   - Use case: User registration, contact forms
   - Features tested: Character classes, quantifiers, literals

2. **Phone Number** (US format)
   - Pattern: `(?<area>\d{3}) - (?<exchange>\d{3}) - (?<line>\d{4})`
   - Use case: Contact information validation
   - Features tested: Named groups, exact quantifiers, literals

3. **UUID v4**
   - Pattern: `[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}`
   - Use case: Unique identifier validation
   - Features tested: Character classes, exact quantifiers, literal hyphens

4. **Semantic Version (SemVer)**
   - Pattern: `(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)(?:-(?<prerelease>[0-9A-Za-z-.]+))?(?:\+(?<build>[0-9A-Za-z-.]+))?`
   - Use case: Version string parsing
   - Features tested: Named groups, optional groups, character classes

5. **URL / URI** (HTTP/HTTPS)
   - Pattern: `(?<scheme>https?)://(?<host>[a-zA-Z0-9.-]+)(?::(?<port>\d+))?(?<path>/\S*)?`
   - Use case: URL validation and parsing
   - Features tested: Named groups, alternation, optional groups, non-whitespace class

6. **IPv4 Address**
   - Pattern: `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`
   - Use case: IP address validation
   - Features tested: Quantifier ranges, escaped dots

7. **Credit Card** (generic format)
   - Pattern: `\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}`
   - Use case: Payment form validation
   - Features tested: Exact quantifiers, optional character classes

**Testing Requirements:**
- Pattern must compile without errors
- Emitted regex must be syntactically correct
- Pattern should match valid inputs (spot-check)
- Pattern should reject invalid inputs (spot-check)

### Category 2: Common Parsing/Extraction Patterns

**Purpose:** Verify STRling can compile patterns for extracting structured data from text.

**Required Patterns:**

1. **HTML/XML Tag**
   - Pattern: `<(?<tag>\w+)>.*?</\k<tag>>`
   - Use case: HTML parsing, XML extraction
   - Features tested: Named groups, backreferences, lazy quantifiers

2. **Log File Line** (Nginx access log)
   - Pattern: `(?<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) - (?<user>\S+) \[(?<time>[^\]]+)\] "(?<method>\w+) (?<path>\S+) HTTP/(?<version>[\d.]+)" (?<status>\d+) (?<size>\d+)`
   - Use case: Server log analysis
   - Features tested: Named groups, negated classes, multiple captures

3. **ISO 8601 Timestamp**
   - Pattern: `(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})T(?<hour>\d{2}):(?<minute>\d{2}):(?<second>\d{2})(?:\.(?<fraction>\d+))?(?<tz>Z|[+\-]\d{2}:\d{2})?`
   - Use case: Timestamp parsing
   - Features tested: Named groups, optional groups, alternation

4. **CSV Field** (quoted, with escapes)
   - Pattern: `"(?:[^"\\]|\\.)*"`
   - Use case: CSV parsing
   - Features tested: Non-capturing groups, negated classes, alternation, escapes

5. **Markdown Link**
   - Pattern: `\[(?<text>[^\]]+)\]\((?<url>[^)]+)\)`
   - Use case: Markdown parsing
   - Features tested: Named groups, negated classes, escaped brackets

6. **Environment Variable** (shell-style)
   - Pattern: `(?<name>[A-Z_][A-Z0-9_]*)=(?<value>.*)`
   - Use case: Configuration file parsing
   - Features tested: Named groups, character classes, greedy match

**Testing Requirements:**
- Pattern must compile without errors
- Emitted regex must be syntactically correct
- Named groups must extract correct data
- Pattern should handle edge cases (empty values, special characters)

### Category 3: Advanced Feature Stress Tests

**Purpose:** Verify STRling correctly handles complex, advanced patterns that stress-test the compiler.

**Required Patterns:**

1. **Password Policy** (multiple lookaheads)
   - Pattern: `(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}`
   - Use case: Password validation with multiple criteria
   - Features tested: Multiple positive lookaheads, character classes, quantifiers
   - Complexity: Multiple lookaheads in sequence

2. **ReDoS-Safe Pattern** (atomic group)
   - Pattern: `(?>a+)b`
   - Use case: Preventing catastrophic backtracking
   - Features tested: Atomic groups, quantifiers
   - Complexity: Advanced PCRE2 extension feature

3. **ReDoS-Safe Pattern** (possessive quantifier)
   - Pattern: `a*+b`
   - Use case: Preventing catastrophic backtracking
   - Features tested: Possessive quantifiers
   - Complexity: Advanced PCRE2 extension feature

4. **Complex Free-Spacing Pattern**
   - Pattern:
     ```
     %flags x
     (?<tag> \w+ )    # Tag name
     \s* = \s*        # Equals with optional whitespace
     (?<value> [^>]+ ) # Value (anything except >)
     \k<tag>          # Matching closing tag
     ```
   - Use case: XML/HTML tag matching with readable formatting
   - Features tested: Free-spacing flag, comments, named groups, backreferences
   - Complexity: Multiple features with whitespace and comments

5. **Unicode Pattern** (Unicode properties)
   - Pattern: `%flags u\n\p{L}+`
   - Use case: Matching Unicode letters
   - Features tested: Unicode flag, Unicode properties
   - Complexity: Unicode support

6. **Deeply Nested Quantifiers**
   - Pattern: `((a+)+)+`
   - Use case: Stress-testing nested quantification
   - Features tested: Nested groups, nested quantifiers
   - Complexity: Known ReDoS risk pattern

7. **Multiple Lookarounds in Sequence**
   - Pattern: `(?=test)(?!fail)result`
   - Use case: Complex conditional matching
   - Features tested: Positive lookahead, negative lookahead, sequence
   - Complexity: Multiple lookaround assertions

8. **Nested Alternation**
   - Pattern: `(a|(b|c))`
   - Use case: Complex choice structures
   - Features tested: Nested groups, alternation
   - Complexity: Nested alternation precedence

**Testing Requirements:**
- Pattern must compile without errors
- Emitted regex must be syntactically correct
- Complex features must be preserved in output
- Pattern behavior must be correct (verified with test inputs)

## Pattern Selection Criteria

Golden patterns are selected based on:

1. **Real-World Usage:** Pattern appears frequently in production code
2. **Feature Coverage:** Pattern demonstrates important STRling capabilities
3. **Complexity:** Pattern exercises multiple features in combination
4. **Regression Risk:** Pattern has failed or been problematic in the past
5. **Documentation Value:** Pattern serves as a useful example for users

## Test Organization

Golden pattern tests are organized in a single file per language:

```
bindings/{language}/tests/e2e/
└── test_pcre2_emitter.{py,ts}
```

Within this file, tests are organized by category:

```
class TestCategoryACoreLanguageFeatures:
    """Canonical patterns demonstrating core DSL features."""
    def test_golden_patterns()

class TestCategoryBEmitterSpecificSyntax:
    """Emitter-specific syntax generation (flags, escaping)."""
    def test_all_flags_are_generated_correctly()
    def test_all_metacharacters_are_escaped()

class TestCategoryCExtensionFeatures:
    """PCRE2-specific extension features."""
    def test_pcre2_extensions()

class TestCategoryDGoldenPatterns:
    """Real-world golden patterns for validation, parsing, and advanced features."""
    def test_golden_patterns_real_world()
```

## Test Case Structure

Each golden pattern test should follow this pattern:

```
# Python
@pytest.mark.parametrize(
    "input_dsl, expected_regex, description",
    [
        (
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
            "Email address validation (simplified RFC 5322)",
        ),
        (
            r"(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})",
            r"(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})",
            "ISO 8601 date parsing",
        ),
    ],
    ids=["golden_email", "golden_iso8601_date"]
)
def test_golden_patterns_real_world(
    input_dsl: str, expected_regex: str, description: str
):
    """Tests that STRling can compile real-world patterns."""
    assert compile_to_pcre(input_dsl) == expected_regex

# JavaScript
test.each([
    [
        "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
        /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/,
        "Email validation"
    ],
])('Golden pattern: %s', (inputDsl, expectedRegex, description) => {
    expect(compileToPcre(inputDsl)).toBe(expectedRegex.source);
});
```

## Verification Requirements

All golden pattern tests MUST:
- ✅ Compile without errors through the full pipeline
- ✅ Assert the exact emitted regex string is correct
- ✅ Include a description of the pattern's real-world use case
- ✅ Use descriptive test IDs
- ✅ Cover all three categories (validation, parsing, advanced)
- ✅ Be maintainable (avoid testing too many variations of the same pattern)

## What NOT to Test

To keep golden pattern tests focused:

- ❌ Systematic coverage of all feature combinations (that's combinatorial testing)
- ❌ Individual feature syntax (that's unit testing)
- ❌ Runtime matching behavior (that's conformance testing)
- ❌ Obscure patterns unlikely to be used in production
- ❌ Multiple minor variations of the same pattern

## Updating Golden Patterns

When adding a new golden pattern:

1. **Justify the addition:** Explain why this pattern is valuable
2. **Categorize correctly:** Place it in validation, parsing, or advanced category
3. **Document the use case:** Add a clear description
4. **Verify correctness:** Test against real inputs
5. **Check for duplicates:** Ensure it's not redundant with existing patterns

## Coverage Goals

- **Category 1 (Validation):** Minimum 5-7 common validation patterns
- **Category 2 (Parsing):** Minimum 5-6 common parsing/extraction patterns
- **Category 3 (Advanced):** Minimum 7-8 advanced stress test patterns
- **Total:** Approximately 20-25 golden patterns per language binding

## Related Documentation

- **[Test Suite Guide](../README.md)**: Test directory structure and execution
- **[Testing Standard](../../docs/testing_standard.md)**: Complete testing philosophy
- **[Unit Test Design](unit_test_design.md)**: Individual feature testing
- **[E2E Combinatorial Design](e2e_combinatorial_design.md)**: Feature interaction testing
