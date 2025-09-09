# Test Design — `unit/test_flags_and_free_spacing.py`

## Purpose

This test suite validates the correct parsing of the `%flags` directive and the behavioral changes it induces, particularly the free-spacing (`x`) mode. It ensures that flags are correctly identified and stored in the `Flags` object and that the parser correctly handles whitespace and comments when the extended mode is active.

## Description

The `%flags` directive is a top-level command in a `.strl` file that modifies the semantics of the entire pattern. This suite tests the parser's ability to correctly consume this directive and apply its effects. The primary focus is on the **`x` flag (extended/free-spacing mode)**, which dramatically alters how the parser handles whitespace and comments. The tests will verify that the parser correctly ignores insignificant characters outside of character classes while treating them as literals inside character classes.

## Scope

-   **In scope:**

    -   Parsing the `%flags` directive with single and multiple flags (`i`, `m`, `s`, `u`, `x`).
    -   Handling of various separators (commas, spaces) within the flag list.
    -   The parser's behavior in free-spacing mode: ignoring whitespace and comments outside character classes.
    -   The parser's behavior inside a character class when free-spacing mode is active (i.e., treating whitespace and `#` as literals).
    -   The structure of the `Flags` object produced by the parser and its serialization in the final artifact.

-   **Out of scope:**
    -   The runtime _effect_ of the `i`, `m`, `s`, and `u` flags on the regex engine's matching behavior. This is an integration or conformance-level concern.
    -   The parsing of other directives like `%engine` or `%lang`.

## Categories of Tests

### Category A — Positive Cases (Valid Syntax)

-   **Flag Parsing**:
    -   Test a single flag: `%flags i` → `Flags(ignoreCase=True)`.
    -   Test multiple flags with commas: `%flags i, m, x` → `Flags(ignoreCase=True, multiline=True, extended=True)`.
    -   Test multiple flags with spaces and no commas.
    -   Test with leading/trailing whitespace around the directive and flags.
    -   Assert the final `Flags` object has the correct boolean attributes for each test.
-   **Free-Spacing Mode (`x` flag) Behavior**:
    -   **Whitespace Ignored**: Test a pattern like `a b c` with `%flags x`. The AST must be `Seq(parts=[Lit('a'), Lit('b'), Lit('c')])`.
    -   **Comments Ignored**: Test a pattern like `a # comment \n b`. The AST must be `Seq(parts=[Lit('a'), Lit('b')])`.
    -   **Escaped Whitespace**: Test a pattern like `a\ b` with `%flags x`. The AST must be `Seq(parts=[Lit('a'), Lit(' ')])`, confirming the escaped space is treated as a literal.

### Category B — Negative Cases (Error Handling)

-   **Unknown Flags**: Test `%flags z`. The parser should ignore the unknown flag and produce a default `Flags` object.
-   **Malformed Directives**: Test `%flagg i`. The parser should ignore the entire line and produce a default `Flags` object.

### Category C — Edge Cases

-   **Empty Flags Directive**: Test a line with just `%flags`. The parser should produce a default `Flags` object.
-   **Directive After Content**: Test a file where `%flags` appears after a pattern element. The parser should ignore the directive as it only processes directives at the beginning of the file.
-   **Pattern with Only Comments/Whitespace**: Test a pattern that, in free-spacing mode, becomes empty (e.g., `# comment`). The parser should produce an empty `Seq` or `Alt` node.

### Category D — Cross-Semantics / Interaction

-   **Free-Spacing vs. Character Classes**: This is the most critical interaction test for this module.
    -   Test a pattern like `[a b]` with `%flags x`. The AST **must** be `CharClass(items=[ClassLiteral('a'), ClassLiteral(' '), ClassLiteral('b')])`.
    -   Test a pattern like `[a#b]` with `%flags x`. The AST **must** be `CharClass(items=[ClassLiteral('a'), ClassLiteral('#'), ClassLiteral('b')])`.
    -   These tests verify that the special free-spacing rules **do not apply** inside a character class, as specified in the semantics.

## Completion Criteria

-   [ ] All valid flag letters from `dsl.ebnf` (`i`, `m`, `s`, `u`, `x`) are tested.
-   [ ] The parser's lenient handling of unknown flags/directives is confirmed.
-   [ ] The structure of the `Flags` object and its artifact serialization are asserted for all positive cases.
-   [ ] The core behaviors of free-spacing mode (ignoring whitespace and comments) are tested.
-   [ ] The critical interaction where free-spacing rules are disabled inside a character class is exhaustively tested.
