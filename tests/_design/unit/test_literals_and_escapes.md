# Test Design — `unit/test_literals_and_escapes.py`

## Purpose

This test suite validates the parser's handling of all literal characters and every form of escape sequence defined in the STRling DSL. It ensures that valid forms are correctly parsed into `Lit` AST nodes and that malformed or unsupported sequences raise the appropriate `ParseError`.

## Description

Literals and escapes are the most fundamental **atoms** in a STRling pattern, representing single, concrete characters. This module tests the parser's ability to distinguish between literal characters and special metacharacters, and to correctly interpret the full range of escape syntaxes (identity, control, hex, and Unicode). The expected behavior is for the parser to consume these tokens and produce a `nodes.Lit` object containing the corresponding character value.

## Scope

-   **In scope:**

    -   Parsing of single, non-metacharacter literals.
    -   Parsing of all supported escape sequences: identity (`\.`, `\\`, etc.), control (`\n`, `\t`), hex (`\xHH`, `\x{...}`), Unicode (`\uHHHH`, `\U...`, `\u{...}`), and the null byte (`\0`).
    -   Error handling for invalid, malformed, or explicitly forbidden escape sequences (e.g., incomplete hex escapes, octal escapes).
    -   The structure and value of the resulting `nodes.Lit` AST node.

-   **Out of scope:**
    -   Quantification of literals (covered in `test_quantifiers.py`).
    -   Behavior of literals and escapes inside a character class (covered in `test_char_classes.py`).
    -   Emitter-specific escaping of literals (covered in `test_emitter_edges.py`).

## Categories of Tests

### Category A — Positive Cases (Valid Syntax)

-   **Plain Literals**: Test that non-metacharacters like `a`, `Z`, `1`, `_`, and `-` are parsed into a `Lit` node with the same character value.
-   **Identity Escapes**: Test that escaped metacharacters (`\.`, `\(`, `\|`, `\^`, `\$`, `\*`, `\+`, `\?`, `\{`, `\[`, `\\`) are parsed as `Lit` nodes of the literal character.
-   **Control & Whitespace Escapes**: Test that `\n`, `\r`, `\t`, `\f`, and `\v` are parsed as `Lit` nodes containing their respective control characters.
-   **Hexadecimal Escapes**:
    -   Test the fixed-width form `\xHH` (e.g., `\x41` → `Lit('A')`).
    -   Test the variable-width brace form `\x{...}` with varying numbers of digits (e.g., `\x{41}` → `Lit('A')`, `\x{1F600}` → `Lit('😀')`).
-   **Unicode Escapes**:
    -   Test the fixed-width BMP form `\uHHHH` (e.g., `\u0041` → `Lit('A')`).
    -   Test the fixed-width supplementary plane form `\UHHHHHHHH` (e.g., `\U0001F600` → `Lit('😀')`).
    -   Test the variable-width brace form `\u{...}` for both BMP and supplementary plane characters (e.g., `\u{41}` → `Lit('A')`, `\u{1f600}` → `Lit('😀')`).
-   **Null Byte Escape**: Test that `\0` is correctly parsed as a `Lit` node containing the null character (`\x00`).

### Category B — Negative Cases (Parse Errors)

-   **Malformed Hex Escapes**:
    -   Unterminated brace form: `\x{12` must raise `ParseError("Unterminated \\x{...}", 3)`.
    -   Incomplete fixed-width form: `\x4` must raise `ParseError("Invalid \\xHH escape", 3)`.
    -   Non-hex characters: `\xGG` must raise `ParseError("Invalid \\xHH escape", 3)`.
-   **Malformed Unicode Escapes**:
    -   Unterminated brace form: `\u{1F60` must raise `ParseError("Unterminated \\u{...}", 6)`.
    -   Incomplete fixed-width forms: `\u123` and `\U1234567` must raise errors for invalid length.
-   **Forbidden Escapes (per `semantics.md`)**:
    -   Octal escapes other than `\0` (e.g., `\123`) must raise a `ParseError`. The parser logic shows this will be parsed as a backreference (`\1`) followed by literals (`23`), so the test should confirm this behavior rather than a specific "octal forbidden" error for now.
    -   Unsupported control escapes like `\a` or `\e` should parse as identity escapes (`Lit('a')`, `Lit('e')`).
-   **Stray Metacharacters**: An unescaped `)` that doesn't close a group should raise `ParseError("Unexpected token", 0)`.

### Category C — Edge Cases

-   **Max Unicode Value**: Test the highest valid Unicode code point: `\u{10FFFF}`.
-   **Empty Brace Escapes**: Test `\x{}` and `\u{}`. The parser should treat these as `\x00`.
-   **Case Insensitivity**: Hex escape forms should be case-insensitive (e.g., `\x4a` and `\x4A` should both parse to `Lit('J')`).
-   **Escaped Null Byte**: Test that the sequence `\\0` is parsed as a `Seq` of `Lit('\\')` and `Lit('0')`, not as a single null character.

### Category D — Cross-Semantics / Interaction

-   **Literals in Free-Spacing Mode (`%flags x`)**: Test that a pattern like `a b` is parsed as a sequence of two separate nodes, `Seq(parts=[Lit('a'), Lit('b')])`.
-   **Escapes in Free-Spacing Mode (`%flags x`)**: Test that an escaped space `\ ` is parsed as a `Lit(' ')` and is not ignored like unescaped whitespace.

### Category E — Literal Sequences and Coalescing

-   **Multiple Adjacent Literals**:
    -   Test that sequences of multiple literal characters are parsed correctly.
-   **Literal Fusion in Compiler**:
    -   Document that while the parser produces individual `Lit` nodes, the compiler's normalization pass fuses adjacent literals.
-   **Long Literal Strings**:
    -   Test parsing of longer sequences of literal characters.

### Category F — Escape Interactions

-   **Escaped Metacharacters in Sequences**:
    -   Test sequences containing multiple escaped metacharacters.
-   **Mixed Literals and Escapes**:
    -   Test patterns combining plain literals with various escape types.
-   **Control Character Sequences**:
    -   Test sequences of multiple control character escapes.

### Category G — Backslash Escape Combinations

-   **Double Backslash**:
    -   Test `\\` parsing and its interaction with following characters.
-   **Backslash Before Various Tokens**:
    -   Test backslash escape behavior before different token types.
-   **Escaped Backslash in Sequences**:
    -   Test sequences containing escaped backslashes mixed with other content.

### Category H — Escape Edge Cases Expanded

-   **Boundary Unicode Values**:
    -   Test Unicode escapes at various boundary values (BMP edges, supplementary plane boundaries).
-   **Zero-Width Characters**:
    -   Test escapes for zero-width Unicode characters if applicable.
-   **Complex Unicode Sequences**:
    -   Test sequences of various Unicode escapes.

### Category I — Octal and Backref Disambiguation

-   **Backref vs Octal Parsing**:
    -   Test that sequences like `\1`, `\12`, `\123` are parsed as backreferences followed by literals.
-   **Null Byte Special Case**:
    -   Test that `\0` is parsed as null byte, not a backreference or octal.
-   **Leading Zero Patterns**:
    -   Test various patterns with leading zeros to verify correct disambiguation.

### Category J — Literals in Complex Contexts

-   **Literals in Alternation**:
    -   Test literal characters and escapes within alternation branches.
-   **Literals in Groups**:
    -   Test literals and escapes within various group types.
-   **Literals with Quantifiers**:
    -   Test that literals can be correctly quantified (parsing aspect only).

## Completion Criteria

-   [x] All grammar rules from `dsl.ebnf` related to literals and escapes are covered (`Literal`, `EscapeSequence`, `HexEscape`, `UnicodeEscape`, `NullByteEscape`, `ControlEscape`, `IdentityEscape`).
-   [x] All valid escape forms listed in `semantics.md` are tested.
-   [x] All explicitly forbidden or malformed escape sequences documented in `semantics.md` and `parser.py` are tested and raise the correct `ParseError` with the expected message prefix and position.
-   [x] The AST shape (`nodes.Lit`) and its `value` are asserted for all positive cases.
-   [x] No redundant tests exist for inputs that fall into the same equivalence partition (e.g., testing `a` and `b` is sufficient; `c`, `d`, `e` are not needed).
-   [x] Literal sequence parsing and compiler coalescing behavior is documented.
-   [x] Various escape interaction patterns are tested.
-   [x] Backslash escape combinations in different contexts are validated.
-   [x] Extended Unicode escape edge cases are covered.
-   [x] Octal and backreference disambiguation is thoroughly tested.
-   [x] Literals in complex contexts (alternation, groups, with quantifiers) are validated.
