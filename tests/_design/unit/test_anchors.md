# Test Design — `unit/test_anchors.py`

## Purpose

This test suite validates the correct parsing of all anchor tokens (`^`, `$`, `\b`, `\B`, etc.). It ensures that each anchor is correctly mapped to a corresponding `Anchor` AST node with the proper type and that its parsing is unaffected by flags or surrounding constructs.

## Description

Anchors are zero-width assertions that do not consume characters but instead match a specific **position** within the input string, such as the start of a line or a boundary between a word and a space. This suite tests the parser's ability to correctly identify all supported core and extension anchors and produce the corresponding `nodes.Anchor` AST object.

## Scope

-   **In scope:**

    -   Parsing of core line anchors (`^`, `$`) and word boundary anchors (`\b`, `\B`).
    -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`, `\z`).
    -   The structure and `at` value of the resulting `nodes.Anchor` AST node.
    -   How anchors are parsed when placed at the start, middle, or end of a sequence.
    -   Ensuring the parser's output for `^` and `$` is consistent regardless of the multiline (`m`) flag's presence.

-   **Out of scope:**
    -   The runtime _behavioral change_ of `^` and `$` when the `m` flag is active (this is an emitter/engine concern).
    -   Quantification of anchors (the parser design correctly prevents this by treating anchors as atoms that cannot be quantified).
    -   The behavior of `\b` inside a character class, where it represents a backspace literal, not an anchor (covered in `test_char_classes.py`).

## Categories of Tests

### Category A — Positive Cases (Valid Syntax)

-   **Line Anchors**:
    -   Test `^` is parsed as `Anchor(at='Start')`.
    -   Test `$` is parsed as `Anchor(at='End')`.
-   **Word Boundary Anchors**:
    -   Test `\b` is parsed as `Anchor(at='WordBoundary')`.
    -   Test `\B` is parsed as `Anchor(at='NotWordBoundary')`.
-   **Absolute Anchors (Extensions)**:
    -   Test `\A` is parsed as `Anchor(at='AbsoluteStart')`.
    -   Test `\Z` is parsed as `Anchor(at='EndBeforeFinalNewline')`.
    -   Test `\z` is parsed as `Anchor(at='AbsoluteEnd')`.

### Category B — Negative Cases (Parse Errors)

-   Anchors are single, unambiguous tokens, so there are few anchor-specific parse errors. Tests should confirm that invalid escape sequences near anchors (e.g., `^\c`) are handled by the escape parser, not the anchor parser.

### Category C — Edge Cases

-   **Anchor-Only Patterns**:
    -   Test a pattern consisting of a single anchor, like `^`.
    -   Test a pattern consisting of only anchors, like `^\A\b$`.
-   **Positional Parsing**:
    -   Test anchors at the beginning of a sequence: `^a`.
    -   Test anchors in the middle of a sequence: `a\bb`.
    -   Test anchors at the end of a sequence: `a$`.

### Category D — Cross-Semantics / Interaction

-   **Interaction with Multiline Flag**:
    -   A critical test to ensure the parser's behavior is independent of flags. The AST for `^a$` and `%flags m\n^a$` should be identical. The flag's semantic effect is handled at runtime by the regex engine, not during parsing.
-   **Anchors Inside Groups**:
    -   Test that anchors are parsed correctly inside all group types. Examples: `(^a)`, `(?:^a$)`, `(?<name>\b)`.
-   **Anchors Inside Lookarounds**:
    -   Test that anchors are parsed correctly within lookarounds. Examples: `(?=^a)`, `(?<!\b)`.

### Category E — Anchors in Complex Sequences

-   **Anchors Between Quantified Atoms**:
    -   Test anchors appearing between quantified atoms in a sequence, such as `a*^b+`.
-   **Anchors After Quantified Groups**:
    -   Test anchors following quantified groups, like `(ab)*$`.
-   **Multiple Identical Anchors**:
    -   Test patterns with multiple same anchors (e.g., `^^`, `$$`), which are semantically redundant but syntactically valid.

### Category F — Anchors in Alternation

-   **Anchors in Alternation Branches**:
    -   Test anchors appearing in one or more branches of an alternation, such as `^a|b$`.
-   **Anchors in Grouped Alternation**:
    -   Test anchors within alternation inside a group, like `(^|$)`.
-   **Word Boundaries in Alternation**:
    -   Test word boundary anchors in alternation patterns, such as `\ba|\bb`.

### Category G — Anchors in Atomic Groups

-   **Start Anchor in Atomic Group**:
    -   Test start anchor within an atomic group, like `(?>^a)`.
-   **End Anchor in Atomic Group**:
    -   Test end anchor within an atomic group, like `(?>a$)`.
-   **Word Boundary in Atomic Group**:
    -   Test word boundary anchors in atomic groups, such as `(?>\ba)`.

### Category H — Word Boundary Edge Cases

-   **Word Boundary with Non-Word Character**:
    -   Test word boundaries around non-word characters, like `\b.\b`.
-   **Word Boundary with Character Classes**:
    -   Test word boundaries with character class shorthands, such as `\b\d\b`.
-   **Not-Word-Boundary Usage**:
    -   Test the `\B` anchor in various contexts, like `\Ba\B`.

### Category I — Multiple Anchor Types

-   **Start and End Anchors Together**:
    -   Test patterns combining line start and end anchors, like `^abc$`.
-   **Absolute and Line Anchors**:
    -   Test patterns combining absolute and line anchors, such as `\A^abc$\z`.
-   **Word Boundaries with Line Anchors**:
    -   Test combinations of word boundaries and line anchors, like `^\ba\b$`.

### Category J — Anchors with Quantifiers

-   **Error Cases**:
    -   Test that attempting to quantify anchors (e.g., `^*`, `$+`) correctly raises a parse error with message "Cannot quantify anchor".

## Completion Criteria

-   [x] All anchor forms from `dsl.ebnf` are tested (`^`, `$`, `CoreAnchorEscape`, `AbsoluteAnchorEscape`).
-   [x] The AST shape (`nodes.Anchor`) and its `at` property are verified for all valid forms, matching the `enum` in `base.schema.json`.
-   [x] The parser correctly handles anchors in different positions within a sequence.
-   [x] The test suite confirms that the presence of the `m` flag does not change the parsed AST for `^` and `$`.
-   [x] The non-core status of absolute anchors (`\A`, `\Z`, `\z`) is noted in the test design.
-   [x] Tests confirm that anchors are parsed correctly when nested inside groups and lookarounds.
-   [x] Complex sequences with anchors between quantified atoms are tested.
-   [x] Anchors in alternation patterns (both simple and grouped) are validated.
-   [x] Atomic group support for anchors is verified.
-   [x] Word boundary edge cases with various character types are covered.
-   [x] Combinations of multiple anchor types in single patterns are tested.
-   [x] Error handling for invalid anchor quantification is verified.
