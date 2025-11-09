# Unit Test Standard: The "3-Test Standard"

## Purpose

This document defines STRling's normative unit testing standard. Unit tests validate individual components (atoms, nodes, operators) in isolation, ensuring each feature is correctly parsed, compiled to IR, and generates valid AST/IR structures.

## Philosophy

Unit tests form the foundation of STRling's testing pyramid. They:
- Execute in milliseconds for rapid feedback during development
- Test features in isolation with mocked dependencies
- Validate both valid (positive) and invalid (negative) inputs
- Ensure comprehensive coverage of all grammar rules

## The 3-Test Standard

Every core feature MUST be validated through at least three distinct test cases:

### 1. Simple Case

**Definition:** The feature's most minimal, valid form.

**Purpose:** Verify the feature works in its simplest possible usage.

**Examples:**
- Quantifier: `a?` (optional single character)
- Group: `(a)` (single-element capturing group)
- Character class: `[a]` (single-character class)
- Anchor: `^` (start anchor alone)

**What to verify:**
- Feature parses without error
- AST/IR structure is correct
- Basic attribute values are set properly

### 2. Typical Case

**Definition:** The feature's most common, real-world usage pattern.

**Purpose:** Validate the feature handles standard use cases correctly.

**Examples:**
- Quantifier: `[a-z]+` (one-or-more alphas)
- Group: `(?<name>[a-z]+)` (named capture group with class and quantifier)
- Character class: `[a-z0-9_]` (alphanumeric with underscore)
- Anchor: `\bword\b` (word boundaries around literal)

**What to verify:**
- Feature works with typical parameters/combinations
- Common patterns compile correctly
- Practical use cases are supported

### 3. Interaction Case

**Definition:** The feature combined with one adjacent, related feature.

**Purpose:** Verify the feature correctly interacts with neighboring features.

**Examples:**
- Quantifier: `(a|b)*` (quantifier on alternation group)
- Group: `((?:inner)+)` (capturing group containing non-capturing group)
- Character class: `[a-z]{3}` (character class with quantifier)
- Anchor: `^(?:start)` (anchor with non-capturing group)

**What to verify:**
- Feature precedence is correct
- AST structure shows proper parent-child relationships
- The combination parses and compiles correctly

## Unique Edge Cases

Beyond the 3-Test Standard, each feature has specific boundary conditions that MUST be tested:

### Quantifiers
- **Zero repetitions:** `a{0}`, `a{0,5}`
- **Infinite max:** `a{3,}`, `a*`
- **Mode variations:** Greedy `a*`, lazy `a*?`, possessive `a*+`
- **Quantifier on empty:** `(?:)*`
- **Malformed syntax:** `a{`, `a{3`, `a{,5}`
- **Precedence:** `ab*` must quantify only `b`, not `ab`

### Groups
- **Empty groups:** `()`, `(?:)`, `(?<name>)`
- **Nested groups:** `((inner))`
- **Group types:** Capturing `()`, non-capturing `(?:)`, named `(?<name>)`, atomic `(?>)`
- **Lookarounds:** Lookahead `(?=)`, lookbehind `(?<=)`, negative variants
- **Backreferences:** `(a)\1`, `(?<tag>a)\k<tag>`
- **Unterminated:** `(abc` must raise `ParseError`

### Character Classes
- **Empty class:** `[]` (behavior depends on engine)
- **Single character:** `[a]`
- **Ranges:** `[a-z]`, `[0-9]`
- **Multiple ranges:** `[a-zA-Z0-9]`
- **Negation:** `[^a-z]`
- **Escape sequences:** `[\d]`, `[\w]`, `[\s]`
- **Special characters:** `[.]`, `[-]`, `[^]`, `[\]]`
- **Unicode:** `[\p{L}]`, `[\u{1F600}]`
- **Unterminated:** `[abc` must raise `ParseError`

### Literals and Escapes
- **Single character:** `a`
- **Sequences:** `abc`, `hello world`
- **Escape sequences:** `\d`, `\w`, `\s`, `\t`, `\n`
- **Metacharacter escaping:** `\.`, `\*`, `\+`, `\?`, `\(`, `\)`
- **Unicode escapes:** `\u0041`, `\u{1F600}`
- **Backslash escaping:** `\\`

### Anchors
- **Line boundaries:** `^`, `$`
- **String boundaries:** `\A`, `\z`, `\Z`
- **Word boundaries:** `\b`, `\B`
- **Multiple anchors:** `^\w+$`
- **Anchors with quantifiers:** Test that `^*` correctly handles the precedence

### Flags
- **Individual flags:** `%flags i`, `%flags m`, `%flags s`, `%flags u`, `%flags x`
- **Combined flags:** `%flags imsux`
- **Flag interactions:** Case-insensitive with backreferences, free-spacing with whitespace
- **Empty pattern with flags:** `%flags i\n` (just the flag, no pattern)

### Alternation
- **Two alternatives:** `a|b`
- **Multiple alternatives:** `a|b|c|d`
- **Empty alternatives:** `|a`, `a|`, `a||b`
- **Nested alternation:** `a|(b|c)`
- **Alternation with groups:** `(?:a|b)`, `(a|b|c)`
- **Alternation precedence:** `a|bc` vs `(a|b)c`

## Test Organization

Unit tests are organized by feature/module:

```
bindings/{language}/tests/unit/
├── test_literals_and_escapes.{py,ts}
├── test_char_classes.{py,ts}
├── test_quantifiers.{py,ts}
├── test_groups_backrefs_lookarounds.{py,ts}
├── test_anchors.{py,ts}
├── test_flags_and_free_spacing.{py,ts}
├── test_errors.{py,ts}
├── test_ir_compiler.{py,ts}
├── test_schema_validation.{py,ts}
└── test_emitter_edges.{py,ts}
```

## Verification Requirements

All unit tests MUST:
- ✅ Execute in < 100ms per test
- ✅ Be completely isolated (no shared state)
- ✅ Have descriptive test names that explain what is being tested
- ✅ Use parametrized tests to avoid duplication
- ✅ Test both positive (valid) and negative (invalid) cases
- ✅ Verify AST/IR structure, not just that parsing succeeds
- ✅ Include clear assertions with meaningful failure messages

## Error Testing Standard

Invalid inputs MUST be tested to verify proper error handling:

### Error Properties to Verify
1. **Error type:** Correct exception class (e.g., `ParseError`, `CompileError`)
2. **Error message:** Contains expected descriptive text
3. **Error position:** Identifies the correct location in the input (when applicable)

### Example Error Tests
```
# Python
with pytest.raises(ParseError, match="Unterminated group"):
    parse("a(b")

# JavaScript
expect(() => parse("a(b")).toThrow("Unterminated group");
```

## Coverage Goals

- **Line coverage:** 100% of feature implementation code
- **Branch coverage:** All conditional paths tested
- **Mutation score:** High kill rate (tests fail when code is intentionally broken)

## Related Documentation

- **[Test Suite Guide](../README.md)**: Test directory structure and execution
- **[Testing Standard](../../docs/testing_standard.md)**: Complete testing philosophy
- **[E2E Combinatorial Design](e2e_combinatorial_design.md)**: Feature interaction testing
- **[E2E Golden Pattern Design](e2e_golden_pattern_design.md)**: Real-world pattern validation
