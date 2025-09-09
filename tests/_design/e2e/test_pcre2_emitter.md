# Test Design — `e2e/test_pcre2_emitter.py`

## Purpose

This test suite provides end-to-end (E2E) validation of the entire STRling compiler pipeline, from a source DSL string to the final PCRE2 regex string. It serves as a high-level integration test to ensure that the parser, compiler, and emitter work together correctly to produce valid output for a set of canonical "golden" patterns.

## Description

Unlike the unit tests which inspect individual components, this E2E suite treats the compiler as a black box. It provides a STRling DSL string as input and asserts that the final emitted string is exactly as expected for the PCRE2 target. These tests are designed to catch regressions and verify the correct integration of all core components, including the handling of PCRE2-specific extension features like atomic groups.

## Scope

-   **In scope:**

    -   The final string output of the full `parse -> compile -> emit` pipeline for a curated list of representative patterns.
    -   Verification that the emitted string is syntactically correct for the PCRE2 engine.
    -   End-to-end testing of PCRE2-supported extension features (e.g., atomic groups, possessive quantifiers).
    -   Verification that flags are correctly translated into the `(?imsux)` prefix in the final string.

-   **Out of scope:**
    -   Exhaustive testing of every possible DSL feature (this is the role of the unit tests).
    -   The runtime behavior of the generated regex string in a live PCRE2 engine (this is the purpose of the Sprint 7 conformance suite).
    -   Detailed validation of the intermediate AST or IR structures.

## Categories of Tests

### Category A — Core Language Features (Golden Patterns)

These tests use a set of canonical patterns to verify the correct end-to-end compilation of the most important and commonly used DSL features.

-   **Complex Pattern with Groups, Classes, and Quantifiers**:
    -   **Input DSL**: `%flags x \n (?<area>\d{3}) - (?<exchange>\d{3}) - (?<line>\d{4})`
    -   **Expected Output**: `(?x)(?<area>\d{3})-(?<exchange>\d{3})-(?<line>\d{4})`
-   **Alternation and Precedence**:
    -   **Input DSL**: `start(?:a|b|c)end`
    -   **Expected Output**: `start(?:a|b|c)end` (ensuring the alternation is correctly grouped within the sequence).
-   **Lookarounds and Anchors**:
    -   **Input DSL**: `(?<=^foo)\w+`
    -   **Expected Output**: `(?<=^foo)\w+`
-   **Unicode Properties**:
    -   **Input DSL**: `%flags u \n \p{Script=Greek}+`
    -   **Expected Output**: `(?u)\p{Script=Greek}+`
-   **Backreferences**:
    -   **Input DSL**: `<(?<tag>\w+)>.*?</\k<tag>>`
    -   **Expected Output**: `<(?<tag>\w+)>.*?</\k<tag>>`

### Category B — Emitter-Specific Syntax

These tests verify that the emitter produces the correct syntax for features specific to the PCRE2 engine.

-   **Flag Generation**:
    -   **Input DSL**: `%flags imsux`
    -   **Expected Output**: `(?imsux)`
-   **Named Group Syntax**: The test for the "Golden Pattern" above already confirms the `(?<name>...)` syntax.
-   **Escaping**:
    -   **Input DSL**: `a.b*c+d?e|f(g)h[i]j{k}l\\m`
    -   **Expected Output**: `a\.b\*c\+d\?e\|f\(g\)h\[i\]j\{k\}l\\m` (confirming all metacharacters in a literal context are escaped).

### Category C — Extension Features (`xfail` as needed)

These tests cover features supported by PCRE2 but not necessarily by other engines. They should pass for the PCRE2 emitter.

-   **Atomic Groups**:
    -   **Input DSL**: `(?>a+)b`
    -   **Expected Output**: `(?>a+)b`
-   **Possessive Quantifiers**:
    -   **Input DSL**: `a*+`
    -   **Expected Output**: `a*+`
-   **Absolute Anchors**:
    -   **Input DSL**: `\Astart...end\z`
    -   **Expected Output**: `\Astart...end\z`

### Category D — End-to-End Error Handling

-   **Invalid DSL**: Pass a syntactically incorrect DSL string (e.g., `a(b`) to the full compilation pipeline and assert that it raises a `ParseError`.

## Completion Criteria

-   [ ] A representative set of "golden" patterns covering the main DSL features is tested end-to-end.
-   [ ] The final emitted string is asserted for correctness in all test cases.
-   [ ] PCRE2-specific syntax (flag prefixes, group syntax) is explicitly verified.
-   [ ] All supported PCRE2 extension features (atomic groups, possessive quantifiers, absolute anchors) are tested.
-   [ ] The test suite confirms that a parse error in the DSL is correctly propagated through the entire pipeline.
