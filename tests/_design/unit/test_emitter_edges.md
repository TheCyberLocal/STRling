# Test Design — `unit/test_emitter_edges.py`

## Purpose

This test suite validates the logic of the PCRE2 emitter, focusing on its specific responsibilities: correct character escaping, shorthand optimizations, flag prefix generation, and the critical automatic-grouping logic required to preserve operator precedence.

## Description

The emitter (`pcre2.py`) is the final backend stage in the STRling compiler pipeline. It translates the clean, language-agnostic Intermediate Representation (IR) into a syntactically correct PCRE2 regex string. This suite does not test the IR's correctness but verifies that a given valid IR tree is always transformed into the correct and most efficient string representation, with a heavy focus on edge cases where incorrect output could alter a pattern's meaning.

## Scope

-   **In scope:**

    -   The emitter's character escaping logic, both for general literals and within character classes.
    -   Shorthand optimizations, such as converting `IRCharClass` nodes into `\d` or `\P{Letter}` where appropriate.
    -   The automatic insertion of non-capturing groups `(?:...)` to maintain correct precedence for alternations within sequences and for quantified multi-atom expressions.
    -   Generation of the flag prefix `(?imsux)` based on the provided `Flags` object.
    -   Correct string generation for all PCRE2-supported extension features, like atomic groups and possessive quantifiers.

-   **Out of scope:**
    -   The correctness of the input IR tree (this is covered by `test_ir_compiler.py`).
    -   The runtime behavior of the generated regex string in a live PCRE2 engine (this is covered by end-to-end and conformance tests).

## Categories of Tests

### Category A — Escaping Logic

-   **Literal Escaping**: Provide an `IRLit` containing all PCRE2 metacharacters (`.^$|()?*+{}\[]\`). Assert that every character in the output string is correctly preceded by a backslash.
-   **Character Class Escaping**: Provide an `IRCharClass` containing special class metacharacters (`]`, `-`, `^`, `\`). Assert that they are correctly escaped within the `[...]` output.

### Category B — Shorthand Optimizations

-   **Positive Optimizations**: Test that the emitter correctly collapses single-item `IRCharClass` nodes into their shorthand string equivalents:
    -   `IRCharClass(items=[IRClassEscape('d')])` → `\d`.
    -   `IRCharClass(negated=True, items=[IRClassEscape('d')])` → `\D`.
    -   `IRCharClass(items=[IRClassEscape('p', property='L')])` → `\p{L}`.
    -   `IRCharClass(negated=True, items=[IRClassEscape('p', property='L')])` → `\P{L}`.
-   **Negative Optimizations**: Test that the optimization is **not** applied when it would be incorrect:
    -   A class with more than one item: `IRCharClass(items=[IRClassEscape('d'), IRClassLiteral('_')])` must emit the full `[\d_]`.

### Category C — Automatic Grouping (Precedence Preservation)

This is the most critical category, testing the logic from `_needs_group_for_quant` and the `IRAlt` handling.

-   **Alternation in Sequence**: An `IRAlt` that is a child of an `IRSeq` must be wrapped in a non-capturing group. `IRSeq(parts=[IRLit('a'), IRAlt(...)])` must produce `a(?:...|...)`.
-   **Quantified Multi-Character Literals**: `IRQuant(child=IRLit('ab'))` must produce `(?:ab)*`.
-   **Quantified Sequences**: `IRQuant(child=IRSeq(...))` must produce `(?:...)*`.
-   **No Unnecessary Grouping**: Test that quantifiers on atoms that don't require grouping do **not** receive an extra `(?:...)`:
    -   `IRQuant(child=IRCharClass(...))` → `[...]*`.
    -   `IRQuant(child=IRGroup(...))` → `(...)*`.
    -   `IRQuant(child=IRDot())` → `.*`.

### Category D — Flags and Emitter Directives

-   **Flag Prefix Generation**:
    -   Test various combinations of flags (`i`, `m`, `s`, `u`, `x`) and assert that the correct prefix is generated (e.g., `(?imx)`).
    -   Test that providing no flags or an empty flags object results in an empty prefix string.
-   **Emitter-Specific Syntax**:
    -   Test that a named group `IRGroup(name='x', ...)` is emitted with PCRE2's `(?<x>...)` syntax.
    -   Test that a named backreference `IRBackref(byName='x')` is emitted as `\k<x>`.

### Category E — Extension Features

-   **Atomic Groups**: An `IRGroup` with `atomic=True` must be emitted with the `(?>...)` syntax.
-   **Possessive Quantifiers**: An `IRQuant` with `mode='Possessive'` must be emitted with the `+` suffix (e.g., `*+`, `++`, `{1,5}+`).
-   **Absolute Anchors**: An `IRAnchor` with `at='AbsoluteStart'` must be emitted as `\A`.

## Completion Criteria

-   [ ] All specific escaping rules from `_escape_literal` and `_escape_class_char` are tested.
-   [ ] All shorthand optimization cases from `_emit_class` (both positive and negative) are tested.
-   [ ] Every condition for automatic grouping (from `_needs_group_for_quant` and `IRAlt` handling) is verified.
-   [ ] The flag-to-prefix generation logic is tested for correctness.
-   [ ] All supported extension features (atomic groups, possessive quantifiers, etc.) are tested to ensure they produce the correct PCRE2-specific syntax.
