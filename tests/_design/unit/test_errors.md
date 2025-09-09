# Test Design — `unit/test_errors.py`

## Purpose

This test suite serves as the single source of truth for defining and validating the error-handling contract of the entire STRling pipeline. It ensures that invalid inputs are rejected predictably and that diagnostics are stable, accurate, and helpful across all stages—from the parser to the CLI.

## Description

This suite defines the expected behavior for all invalid, malformed, or unsupported inputs. It verifies that errors are raised at the correct stage (`ParseError`, `ValidationError`, etc.), contain a clear, human-readable message, and provide an accurate source location. A key invariant tested is the "first error wins" policy: for an input with multiple issues, only the error at the earliest position is reported.

## Scope

-   **In scope:**

    -   `ParseError` exceptions raised by the parser for syntactic and lexical issues.
    -   `ValidationError` (or equivalent semantic errors) raised for syntactically valid but semantically incorrect patterns (e.g., forward backreferences).
    -   Non-zero exit codes and error messages from the CLI for various failure modes.
    -   Asserting error messages for a stable, recognizable substring.
    -   Asserting the correctness of the reported error position, even in free-spacing mode.

-   **Out of scope:**
    -   Correct handling of **valid** inputs (covered in other, feature-specific test suites).
    -   The exact, full wording of error messages (tests will assert substrings to allow for minor wording changes).

## Categories of Tests

### Category A — Error Cases by Feature

This category covers all expected failures, grouped by the language feature that causes them.

-   **Directive & Flag Errors**:

    -   Test that an unknown flag (e.g., `%flags q`) raises a semantic error.
    -   Test that malformed flag syntax (e.g., `%flags i m`) raises a `ParseError`.
    -   Test that duplicate `%flags` directives are handled according to the documented policy (e.g., "last one wins" or raises an error).

-   **Grouping & Lookaround Errors**:

    -   Test that unterminated groups, named groups, and lookarounds (`(abc`, `(?<name`, `(?=a`) raise a `ParseError` at the end of the input.
    -   Test that an unsupported group prefix (e.g., Python-style `(?P...`) raises a `ParseError`.
    -   Test that a variable-length lookbehind (`(?<=a+)`) raises a `ValidationError`.

-   **Backreference & Naming Errors**:

    -   Test that a forward reference by name (`\k<later>(?<later>a)`) raises a `ValidationError`.
    -   Test that a forward reference by index (`\2(a)(b)`) raises a `ValidationError`.
    -   Test that unterminated named backref syntax (`\k<name`) raises a `ParseError`.
    -   Test that duplicate group names (`(?<n>a)(?<n>b)`) raise a `ValidationError`.

-   **Character Class Errors**:

    -   Test that an unterminated class (`[abc`) raises a `ParseError`.
    -   Test that an invalid range (`[z-a]`) is either parsed as literals or raises a `ValidationError`, per the documented policy.
    -   Test that an unknown Unicode property (`[\p{Unknown}]`) raises a `ValidationError`.
    -   Test that a malformed Unicode property (`[\p{}]`) raises a `ParseError`.

-   **Escape & Codepoint Errors**:

    -   Test malformed hex/Unicode escapes (`\xG1`, `\u12Z4`, `\x{}`) and ensure they raise a `ParseError`.

-   **Quantifier Errors**:

    -   Test malformed brace quantifiers (`a{,2}`, `a{2,1}`, `{2}`) and ensure they raise a `ParseError`.
    -   Test that quantifying a non-quantifiable atom (e.g., `^*`) raises a `ValidationError`.

-   **Alternation Errors**:

    -   Test that an empty branch in an alternation (`|a` or `a|`) raises a `ParseError`.

-   **CLI Errors**:

    -   Test that a non-existent file path results in a non-zero exit code and a message on `stderr`.
    -   Test that a syntax error in an input file results in the specific `ParseError` exit code (2) and a JSON error message.

-   **Multi-Error Invariant**:
    -   Test an input with multiple errors (e.g., `[a|b`) and verify that only the first error (the unterminated class at the start) is reported.

### Category B — Known Gaps & `xfail` Cases

This category lists tests for behaviors that are planned but not yet implemented. These tests should be written but marked with `pytest.mark.xfail`.

-   **Out-of-Range Codepoints**: A test for `\u{110000}` should be marked `xfail` until a codepoint range check is added to the validator.
-   **Possessive Quantifiers**: A test for `a*+` should be marked `xfail` until the emitter supports this extension.
-   **Compiler/Emitter Limits**: Tests that force an unsupported IR node into an emitter should be marked `xfail` until the emitters are fully hardened.

## Completion Criteria

-   [ ] All error cases listed in the categories above are implemented as tests.
-   [ ] Errors are tested at each level of the stack: `ParseError` (parser), `ValidationError` (validator/compiler), and non-zero exit codes (CLI).
-   [ ] The "first error wins" and "correct error position in free-spacing mode" invariants are both explicitly verified.
-   [ ] All planned future error-handling features are represented by tests marked with `xfail`.
-   [ ] Assertions check for a stable substring in the error message and the correct error position.
