# Test Design — `e2e/test_e2e_combinatorial.py`

## Purpose

This test suite provides systematic combinatorial end-to-end validation to ensure that different STRling features work correctly when combined. It follows a risk-based, tiered approach to manage test complexity while achieving comprehensive coverage of feature interactions.

## Description

Unlike unit tests that test individual features in isolation, this E2E suite tests feature interactions using two complementary strategies:

1. **Tier 1 (Pragmatic Pairwise - N=2)**: Tests all pairwise combinations of core features to detect basic interaction bugs.
2. **Tier 2 (Strategic Triplets - N=3)**: Tests three-way combinations of high-risk features known to have complex interactions.

The tests verify that the full compilation pipeline (parse → compile → emit) correctly handles feature interactions and produces the expected PCRE2 output. This combinatorial approach provides high coverage of potential interaction bugs without the exponential explosion of exhaustive testing.

## Scope

-   **In scope:**

    -   Pairwise (N=2) combinations of all core STRling features.
    -   Strategic triplet (N=3) combinations of high-risk features that are known to have complex interactions.
    -   End-to-end validation from DSL input to PCRE2 string output.
    -   Detection of interaction bugs that would not be caught by unit tests.
    -   Verification that feature combinations produce syntactically valid and semantically correct PCRE2 patterns.

-   **Out of scope:**
    -   Exhaustive N³ or higher combinations (the combinatorial explosion makes this impractical).
    -   Runtime behavior validation against actual regex engines (this is covered by conformance tests).
    -   Individual feature testing in isolation (this is the role of unit tests).
    -   Detailed validation of intermediate AST or IR structures (unit tests handle this).

## Categories of Tests

### Category A — Tier 1: Pairwise Combinations (N=2)

Tests all pairwise combinations of core STRling features to ensure basic interoperability.

-   **Flags with Every Feature**:
    -   Flags + Literals (case-insensitive, free-spacing)
    -   Flags + Character Classes (unicode properties, case-insensitive)
    -   Flags + Anchors (multiline mode with line anchors)
    -   Flags + Quantifiers (dotall with any-char quantifiers)
    -   Flags + Groups (case-insensitive with named groups)
    -   Flags + Lookarounds (multiline with lookarounds containing anchors)
    -   Flags + Alternation (free-spacing with alternation)
    -   Flags + Backreferences (case-insensitive with backreferences)

-   **Literals with Every Feature**:
    -   Literals + Character Classes
    -   Literals + Anchors (start/end anchors, word boundaries)
    -   Literals + Quantifiers
    -   Literals + Groups (capturing and non-capturing)
    -   Literals + Lookarounds
    -   Literals + Alternation
    -   Literals + Backreferences

-   **Character Classes with Every Feature**:
    -   Character Classes + Anchors
    -   Character Classes + Quantifiers (greedy, lazy, possessive)
    -   Character Classes + Groups
    -   Character Classes + Lookarounds
    -   Character Classes + Alternation
    -   Character Classes + Backreferences

-   **Anchors with Every Feature**:
    -   Anchors + Quantifiers (confirming anchors cannot be quantified)
    -   Anchors + Groups
    -   Anchors + Lookarounds
    -   Anchors + Alternation
    -   Anchors + Backreferences

-   **Quantifiers with Every Feature**:
    -   Quantifiers + Groups
    -   Quantifiers + Lookarounds
    -   Quantifiers + Alternation
    -   Quantifiers + Backreferences

-   **Groups with Every Feature**:
    -   Groups + Lookarounds
    -   Groups + Alternation
    -   Groups + Backreferences

-   **Lookarounds with Every Feature**:
    -   Lookarounds + Alternation
    -   Lookarounds + Backreferences

-   **Alternation with Backreferences**:
    -   Tests alternation branches containing backreferences.

### Category B — Tier 2: Strategic Triplets (N=3)

Tests three-way combinations of features known to have complex interactions or high risk of bugs.

-   **High-Risk Triplets**:
    -   Groups + Quantifiers + Alternation (e.g., `(a|b)+`)
    -   Lookarounds + Groups + Backreferences (e.g., `(?<a>x)(?=\k<a>)`)
    -   Flags + Anchors + Lookarounds (e.g., `%flags m\n(?<=^a)b`)
    -   Character Classes + Quantifiers + Groups
    -   Anchors + Lookarounds + Alternation

-   **Nested Structure Triplets**:
    -   Nested Groups + Quantifiers + Alternation
    -   Lookarounds + Nested Groups + Quantifiers
    -   Alternation + Groups + Backreferences

### Category C — Complex Nested Features

Tests patterns with multiple levels of nesting and complex feature interactions.

-   **Deep Nesting**:
    -   Multiple levels of nested groups with quantifiers and alternation.
    -   Lookarounds containing groups containing lookarounds.
    -   Complex alternation with nested groups and backreferences.

-   **Mixed Complex Patterns**:
    -   Patterns combining many features at once (approaching real-world complexity).
    -   Stress tests for the compilation pipeline with highly nested structures.

## Completion Criteria

-   [x] All N=2 (pairwise) combinations of core features are tested with representative examples.
-   [x] Strategic N=3 (triplet) combinations of high-risk features are tested.
-   [x] Each test verifies the complete pipeline from DSL input to PCRE2 output.
-   [x] Test IDs clearly indicate which features are being combined.
-   [x] Complex nested patterns are tested to validate the compiler's handling of deep structures.
-   [x] The test suite provides systematic coverage without redundant exhaustive testing.
-   [x] All tests produce syntactically valid PCRE2 output that matches the expected pattern structure.
