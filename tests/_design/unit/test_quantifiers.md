# Test Design — `unit/test_quantifiers.py`

## Purpose

This test suite validates the correct parsing of all quantifier forms (`*`, `+`, `?`, `{m,n}`) and modes (Greedy, Lazy, Possessive). It ensures quantifiers correctly bind to their preceding atom, generate the proper `Quant` AST node, and that malformed quantifier syntax raises the appropriate `ParseError`.

## Description

Quantifiers specify the number of times a preceding atom can occur in a pattern. This test suite covers the full syntactic and semantic range of this feature. It verifies that the parser correctly interprets the different quantifier syntaxes and their greedy (default), lazy (`?` suffix), and possessive (`+` suffix) variants. A key focus is testing operator precedence—ensuring that a quantifier correctly associates with a single preceding atom (like a literal, group, or class) rather than an entire sequence.

## Scope

-   **In scope:**

    -   Parsing of all standard quantifiers: `*`, `+`, `?`.
    -   Parsing of all brace-based quantifiers: `{n}`, `{m,}`, `{m,n}`.
    -   Parsing of lazy (`*?`) and possessive (`*+`) mode modifiers.
    -   The structure and values of the resulting `nodes.Quant` AST node (including `min`, `max`, and `mode` fields).
    -   Error handling for malformed brace quantifiers (e.g., `a{1,`).
    -   The parser's correct identification of the atom to be quantified, which informs the emitter's automatic-grouping logic (e.g., in `(a|b)*`).

-   **Out of scope:**
    -   Static analysis for ReDoS risks on nested quantifiers (this is a Sprint 6 feature).
    -   The emitter's final string output, such as adding non-capturing groups like `(?:...)` before a quantifier (covered in `test_emitter_edges.py`).

## Categories of Tests

### Category A — Positive Cases (Valid Syntax & AST Shape)

-   **Star Quantifier (`*`)**: Test `a*` and `a*?` and `a*+`. Verify the `Quant` node has `min=0`, `max='Inf'`, and the correct `mode`.
-   **Plus Quantifier (`+`)**: Test `a+` and `a+?` and `a++`. Verify `min=1`, `max='Inf'`, and correct `mode`.
-   **Optional Quantifier (`?`)**: Test `a?` and `a??` and `a?+`. Verify `min=0`, `max=1`, and correct `mode`.
-   **Exact Repetition (`{n}`)**: Test `a{3}` and its lazy/possessive forms. Verify `min=3`, `max=3`, and correct `mode`.
-   **At-Least Repetition (`{n,}`)**: Test `a{3,}` and its lazy/possessive forms. Verify `min=3`, `max='Inf'`, and correct `mode`.
-   **Range Repetition (`{n,m}`)**: Test `a{3,5}` and its lazy/possessive forms. Verify `min=3`, `max=5`, and correct `mode`.

### Category B — Negative Cases (Parse Errors)

-   **Malformed Brace Quantifiers**: Verify that the following raise a `ParseError` with the expected message and position:
    -   Unterminated brace: `a{`
    -   Unterminated brace after one number: `a{3`
    -   Unterminated brace after comma: `a{3,`
    -   Missing first number: `a{,5}` (the parser will treat this as a literal `{,5}`). The test should confirm this literal interpretation.

### Category C — Edge Cases

-   **Zero Repetitions**: Test quantifiers with zero: `a{0}`, `a{0,5}`, `a{0,}`.
-   **Quantifier on Empty Group**: Test `(?:)*`. The AST should show a `Quant` node wrapping an empty `Group`.
-   **Quantifier on Anchor**: Test `a^?`. The parser should apply the quantifier to `a` and treat `^` as the next atom in a sequence, not quantify the anchor.

### Category D — Cross-Semantics / Interaction

-   **Quantifier Precedence**: This is a critical test of the parser's core logic.
    -   Test `ab*`. The resulting AST must be `Seq(parts=[Lit('a'), Quant(child=Lit('b'))])`, not `Quant(child=Seq(parts=[Lit('a'), Lit('b')]))`. This confirms the fix for the quantifier association bug.
-   **Quantifying Different Atom Types**:
    -   **Single-character atoms**: `\d*`, `.*`, `[a-z]*`. The `Quant` node should directly wrap the `CharClass`, `Dot`, etc.
    -   **Groups**: `(abc)*`. The `Quant` node must wrap the `Group` node.
    -   **Alternations**: `(?:a|b)+`. The `Quant` node must wrap the `Group` node that contains the `Alt` node.
    -   **Lookarounds**: `(?=a)+`. The `Quant` node must wrap the `Look` node.

### Category E — Nested and Redundant Quantifiers

-   **Nested Quantifiers**:
    -   Test patterns with nested quantifiers like `(a*)*` to verify correct AST structure.
    -   Test multiple levels of nesting in quantified groups.
-   **Redundant Quantifiers**:
    -   Test semantically redundant but syntactically valid patterns like `a**` or `(a+)+`.
-   **Quantifiers on Quantified Expressions**:
    -   Test quantifiers applied to already-quantified atoms within groups.

### Category F — Quantifiers on Special Atoms

-   **Quantifiers on Dot**:
    -   Test dot quantification patterns like `.*`, `.+`, `.?`, `.{3,5}`.
-   **Quantifiers on Character Classes**:
    -   Test various character class quantifications like `[a-z]*`, `[\d\s]+`.
-   **Quantifiers on Lookarounds**:
    -   Test quantified lookahead and lookbehind assertions, such as `(?=a)*` (though semantically unusual).
-   **Quantifiers on Atomic Groups**:
    -   Test possessive/atomic group quantification like `(?>a+)*`.

### Category G — Multiple Quantified Sequences

-   **Adjacent Quantified Atoms**:
    -   Test sequences of multiple quantified atoms, like `a*b+c?`.
-   **Quantified Atoms with Literals**:
    -   Test mixed sequences like `abc*def+`.
-   **Complex Sequences**:
    -   Test longer sequences with multiple quantified and non-quantified atoms.

### Category H — Brace Quantifier Edge Cases

-   **Large Numbers in Braces**:
    -   Test brace quantifiers with large numeric values, like `a{100}` or `a{10,1000}`.
-   **Equal Min and Max**:
    -   Test redundant range syntax where min equals max, like `a{3,3}`.
-   **Zero-Based Ranges**:
    -   Test ranges starting from zero, such as `a{0,5}`.
-   **Open-Ended Ranges**:
    -   Test various open-ended ranges like `a{5,}`.

### Category I — Quantifier Interaction with Flags

-   **Quantifiers with Free-Spacing**:
    -   Test that quantifiers work correctly with free-spacing mode (`%flags x`).
-   **Quantifiers with Case-Insensitive Flag**:
    -   Test quantified patterns with case-insensitive flag to verify no AST changes.
-   **Quantifiers with Other Flags**:
    -   Test quantifier behavior remains consistent across different flag combinations.

## Completion Criteria

-   [x] All quantifier syntax forms from `dsl.ebnf` are tested (`GreedyQuant`, `LazyQuant`, `PossessiveQuant`).
-   [x] The AST shape (`nodes.Quant`) is verified for all valid forms, checking `min`, `max`, and `mode` values.
-   [x] The specified `ParseError` conditions for malformed quantifiers are tested.
-   [x] The critical test for quantifier precedence (`ab*`) is included.
-   [x] Tests cover quantifying all major atom types (literals, classes, groups, etc.) to ensure correct AST structure.
-   [x] Possessive quantifiers are tested and marked as an extension feature as noted in `semantics.md`.
-   [x] Nested and redundant quantifier patterns are validated.
-   [x] Quantifiers on all special atom types (dot, character classes, lookarounds, atomic groups) are tested.
-   [x] Multiple quantified sequences and complex combinations are covered.
-   [x] Brace quantifier edge cases including large numbers and zero-based ranges are verified.
-   [x] Quantifier interaction with all flags is tested to ensure consistent behavior.
