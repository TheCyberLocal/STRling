# E2E Test Standard: Combinatorial Interaction Testing

## Purpose

This document defines STRling's normative end-to-end (E2E) combinatorial testing standard. These tests validate that different features work correctly when combined, using a risk-based, tiered approach to manage complexity while achieving comprehensive coverage of feature interactions.

## Philosophy

While unit tests validate features in isolation, combinatorial E2E tests ensure features interact correctly when combined. The challenge is that exhaustive testing of all feature combinations is impractical:

- **N=2 combinations:** ~45 combinations for 10 features
- **N=3 combinations:** ~120 combinations for 10 features  
- **N=4+ combinations:** Exponential explosion, infeasible

STRling employs a **pragmatic, risk-based approach** that balances coverage with maintainability.

## Tiered Testing Strategy

### Tier 1: Pragmatic Pairwise (N=2) — REQUIRED

**Definition:** Test all meaningful N=2 (pairwise) combinations of core features.

**Purpose:** Catch the majority of interaction bugs with manageable test suite size. Research shows that pairwise testing detects 70-90% of defects.

**Core Features for Pairwise Coverage:**
1. Flags (`%flags imsux`)
2. Literals (`abc`, `hello`)
3. Character classes (`[a-z]`, `\d`, `\w`)
4. Quantifiers (`*`, `+`, `?`, `{m,n}`)
5. Groups (Capturing `()`, Non-capturing `(?:)`, Named `(?<name>)`, Atomic `(?>)`)
6. Anchors (`^`, `$`, `\b`, `\A`, `\z`)
7. Lookarounds (`(?=)`, `(?<=)`, `(?!)`, `(?<!)`)
8. Alternation (`a|b|c`)
9. Backreferences (`\1`, `\k<name>`)

**Testing Matrix (N=2):**

Each feature must be tested in combination with every other feature:

| Feature A | Feature B | Example Pattern | Purpose |
|-----------|-----------|-----------------|---------|
| Flags | Groups | `%flags i\n(test)` | Verify flags affect group matching |
| Flags | Quantifiers | `%flags x\n a + b` | Verify free-spacing with quantifiers |
| Flags | Backrefs | `%flags i\n(a)\1` | Verify case-insensitive backrefs |
| Literals | Character Classes | `abc[xyz]` | Verify sequence with class |
| Literals | Anchors | `^hello`, `world$` | Verify anchored literals |
| Literals | Quantifiers | `test\d{3}` | Verify literal with quantified class |
| Literals | Groups | `hello(world)` | Verify literal with captured group |
| Literals | Lookarounds | `hello(?=world)` | Verify literal with lookahead |
| Literals | Alternation | `hello\|world` | Verify alternation of literals |
| Literals | Backreferences | `(\w+)=\1` | Verify backref to captured group |
| Character Classes | Anchors | `^[a-z]+`, `[0-9]+$` | Verify anchored classes |
| Character Classes | Quantifiers | `[a-z]*`, `[0-9]{2,4}` | Verify quantified classes |
| Character Classes | Groups | `([a-z]+)` | Verify grouped classes |
| Character Classes | Lookarounds | `(?=[a-z])` | Verify class in lookaround |
| Character Classes | Alternation | `[a-z]\|[0-9]` | Verify alternation of classes |
| Character Classes | Backreferences | `([a-z])\1` | Verify backref to class match |
| Quantifiers | Groups | `(abc)+`, `(?:test)*` | Verify quantified groups |
| Quantifiers | Anchors | `^\w+$` | Verify quantifier with anchors |
| Quantifiers | Lookarounds | `(?=a)+` | Verify quantified lookaround |
| Quantifiers | Alternation | `(?:a\|b)*` | Verify quantified alternation |
| Groups | Anchors | `^(test)$` | Verify anchored groups |
| Groups | Lookarounds | `((?=test)\w+)` | Verify group with lookaround |
| Groups | Alternation | `(a\|b\|c)` | Verify grouped alternation |
| Groups | Backreferences | `(a)\1`, `(?<tag>a)\k<tag>` | Verify capturing and backref |
| Anchors | Lookarounds | `(?<=^foo)\w+` | Verify lookbehind with anchor |
| Anchors | Alternation | `^a\|b$` | Verify alternation with anchors |
| Lookarounds | Alternation | `(?=a\|b)` | Verify alternation in lookaround |
| Lookarounds | Backreferences | `(a)(?=\1)` | Verify backref in lookaround |

**Implementation Requirements:**
- Each combination must have at least 2-3 test cases covering different variations
- Tests must verify the full compile pipeline: `parse → compile → emit`
- Tests must assert the final emitted regex string is correct
- Tests must be organized by feature families for maintainability

### Tier 2: Strategic Triplets (N=3) — RECOMMENDED

**Definition:** Test N=3 combinations for HIGH-RISK feature triplets only.

**Purpose:** Validate interactions between features known to be complex or error-prone when combined.

**High-Risk Triplets:**

1. **Flags + Groups + Quantifiers**
   - Example: `%flags x\n ( test ) +`
   - Risk: Free-spacing with grouped, quantified patterns
   - Validates: Flag semantics preserved through grouping and quantification

2. **Flags + Groups + Backreferences**
   - Example: `%flags i\n(?<tag>a)\k<tag>`
   - Risk: Case-insensitive matching with backreferences
   - Validates: Backrefs respect flag semantics

3. **Groups + Quantifiers + Lookarounds**
   - Example: `(a)(?=\1)+`
   - Risk: Quantified lookaround with backreferences
   - Validates: Complex precedence and backref scope

4. **Groups + Quantifiers + Alternation**
   - Example: `(a|b)+`, `((a+)+)+`
   - Risk: Nested quantifiers, ReDoS potential
   - Validates: Correct precedence, emitter adds non-capturing groups

5. **Character Classes + Quantifiers + Anchors**
   - Example: `^[a-z]+$`
   - Risk: Common pattern structure
   - Validates: Anchored quantified classes work correctly

6. **Lookarounds + Quantifiers + Backreferences**
   - Example: `(\w)(?=\1)+`
   - Risk: Complex interaction of advanced features
   - Validates: Quantifier applies to lookaround, not backref

**Implementation Requirements:**
- Only test triplets with documented interaction risks
- Each triplet should have 1-2 representative test cases
- Focus on validating correct precedence and semantic behavior
- Document the specific risk being validated

## Complex Nested Feature Tests

Beyond pairwise and triplet testing, specific complex nested patterns MUST be tested:

### Deep Nesting
- **Nested quantifiers:** `((a+)+)+`
- **Nested groups:** `(((inner)))`
- **Nested lookarounds:** `(?=(?!(?<=foo)))`

### Multiple Sequential Features
- **Multiple lookarounds:** `(?=test)(?!fail)result`
- **Multiple anchors:** `\A^\w+$\z`
- **Chained alternations:** `a|b|c|d|e`

### Real-World Complex Patterns
- **Free-spacing with all features:** `%flags x\n(?<tag> \w+ ) \s* = \s* (?<value> [^>]+ ) \k<tag>`
- **Atomic groups with quantifiers:** `(?>a+)b`
- **Possessive quantifiers in groups:** `(a*+)b`

## Test Organization

E2E combinatorial tests are organized in a single file per language:

```
bindings/{language}/tests/e2e/
└── test_e2e_combinatorial.{py,ts}
```

Within this file, tests are organized by tier and feature family:

```
class TestTier1PairwiseCombinations:
    class TestFlagsCombinations:
        def test_flags_combined_with_groups()
        def test_flags_combined_with_quantifiers()
        ...
    
    class TestLiteralsCombinations:
        def test_literals_combined_with_char_classes()
        def test_literals_combined_with_anchors()
        ...
    
    # ... other feature families

class TestTier2StrategyTriplets:
    def test_flags_groups_quantifiers()
    def test_groups_quantifiers_lookarounds()
    ...

class TestComplexNestedFeatures:
    def test_deeply_nested_quantifiers()
    def test_multiple_lookarounds_sequence()
    ...
```

## Verification Requirements

All E2E combinatorial tests MUST:
- ✅ Test the complete compile pipeline (parse → compile → emit)
- ✅ Assert the final emitted regex string is exactly correct
- ✅ Use parametrized tests to test multiple variations efficiently
- ✅ Include descriptive test IDs explaining what combination is tested
- ✅ Document the specific interaction being validated
- ✅ Execute in reasonable time (< 1 second per test)

## Test Case Structure

Each test case should follow this pattern:

```
# Python
@pytest.mark.parametrize(
    "input_dsl, expected_regex",
    [
        ("^[a-z]+$", r"^[a-z]+$"),
        ("%flags i\n(test)", r"(?i)(test)"),
    ],
    ids=["anchored_quantified_class", "flag_with_group"]
)
def test_feature_combination(input_dsl: str, expected_regex: str):
    """Tests that Feature A + Feature B compile correctly."""
    assert compile_to_pcre(input_dsl) == expected_regex

# JavaScript
test.each([
    ["^[a-z]+$", /^[a-z]+$/],
    ["%flags i\n(test)", /(?i)(test)/],
])('Feature A + Feature B: %s', (inputDsl, expectedRegex) => {
    expect(compileToPcre(inputDsl)).toBe(expectedRegex);
});
```

## Coverage Goals

- **Tier 1 (Pairwise):** 100% of N=2 combinations of core features
- **Tier 2 (Triplets):** All documented high-risk N=3 combinations
- **Complex Nesting:** All known problematic nesting patterns
- **Regression:** Any interaction bugs found in production

## What NOT to Test

To keep the test suite maintainable:

- ❌ Exhaustive N=3+ combinations (beyond strategic triplets)
- ❌ Duplicate coverage of interactions already tested in unit tests
- ❌ Runtime behavior (that's conformance testing)
- ❌ Individual feature syntax (that's unit testing)

## Related Documentation

- **[Test Suite Guide](../README.md)**: Test directory structure and execution
- **[Testing Standard](../../docs/testing_standard.md)**: Complete testing philosophy
- **[Unit Test Design](unit_test_design.md)**: Individual feature testing
- **[E2E Golden Pattern Design](e2e_golden_pattern_design.md)**: Real-world pattern validation
