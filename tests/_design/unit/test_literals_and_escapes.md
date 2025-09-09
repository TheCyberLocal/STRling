# Test Design — `unit/test_literals_and_escapes.py`

## Purpose

This test suite validates the parser's handling of all literal characters and every form of escape sequence defined in the STRling DSL. It ensures that valid forms are correctly parsed into `Lit` AST nodes and that malformed or unsupported sequences raise the appropriate `ParseError`.

## Description

Literals and escapes are the most fundamental **atoms** in a STRling pattern, representing single, concrete characters. This module tests the parser's ability to distinguish between literal characters and special metacharacters, and to correctly interpret the full range of escape syntaxes (identity, control, hex, and Unicode). The expected behavior is for the parser to consume these tokens and produce a `nodes.Lit` object containing the corresponding character value.

## Scope

-   **In scope:**

    -   Parsing of single, non-metacharacter literals.
    -   [cite_start]Parsing of all supported escape sequences: identity (`\.`, `\\`, etc.), control (`\n`, `\t`), hex (`\xHH`, `\x{...}`), Unicode (`\uHHHH`, `\U...`, `\u{...}`), and the null byte (`\0`). [cite: 59, 60, 61, 62]
    -   [cite_start]Error handling for invalid, malformed, or explicitly forbidden escape sequences (e.g., incomplete hex escapes, octal escapes). [cite: 72]
    -   The structure and value of the resulting `nodes.Lit` AST node.

-   **Out of scope:**
    -   Quantification of literals (covered in `test_quantifiers.py`).
    -   [cite_start]Behavior of literals and escapes inside a character class (covered in `test_char_classes.py`). [cite: 41]
    -   Emitter-specific escaping of literals (covered in `test_emitter_edges.py`).

## Categories of Tests

### Category A — Positive Cases (Valid Syntax)

-   **Plain Literals**: Test that non-metacharacters like `a`, `Z`, `1`, `_`, and `-` are parsed into a `Lit` node with the same character value.
-   [cite_start]**Identity Escapes**: Test that escaped metacharacters (`\.`, `\(`, `\|`, `\^`, `\$`, `\*`, `\+`, `\?`, `\{`, `\[`, `\\`) are parsed as `Lit` nodes of the literal character. [cite: 65, 66]
-   [cite_start]**Control & Whitespace Escapes**: Test that `\n`, `\r`, `\t`, `\f`, and `\v` are parsed as `Lit` nodes containing their respective control characters. [cite: 63]
-   **Hexadecimal Escapes**:
    -   [cite_start]Test the fixed-width form `\xHH` (e.g., `\x41` → `Lit('A')`). [cite: 67]
    -   [cite_start]Test the variable-width brace form `\x{...}` with varying numbers of digits (e.g., `\x{41}` → `Lit('A')`, `\x{1F600}` → `Lit('😀')`). [cite: 68]
-   **Unicode Escapes**:
    -   [cite_start]Test the fixed-width BMP form `\uHHHH` (e.g., `\u0041` → `Lit('A')`). [cite: 69]
    -   [cite_start]Test the fixed-width supplementary plane form `\UHHHHHHHH` (e.g., `\U0001F600` → `Lit('😀')`). [cite: 71]
    -   [cite_start]Test the variable-width brace form `\u{...}` for both BMP and supplementary plane characters (e.g., `\u{41}` → `Lit('A')`, `\u{1f600}` → `Lit('😀')`). [cite: 70]
-   [cite_start]**Null Byte Escape**: Test that `\0` is correctly parsed as a `Lit` node containing the null character (`\x00`). [cite: 72]

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
    -   [cite_start]Unsupported control escapes like `\a` or `\e` should parse as identity escapes (`Lit('a')`, `Lit('e')`). [cite: 64]
-   **Stray Metacharacters**: An unescaped `)` that doesn't close a group should raise `ParseError("Unexpected token", 0)`.

### Category C — Edge Cases

-   **Max Unicode Value**: Test the highest valid Unicode code point: `\u{10FFFF}`.
-   **Empty Brace Escapes**: Test `\x{}` and `\u{}`. [cite_start]The parser should treat these as `\x00`. [cite: 68, 70]
-   [cite_start]**Case Insensitivity**: Hex escape forms should be case-insensitive (e.g., `\x4a` and `\x4A` should both parse to `Lit('J')`). [cite: 4, 5, 6]
-   **Escaped Null Byte**: Test that the sequence `\\0` is parsed as a `Seq` of `Lit('\\')` and `Lit('0')`, not as a single null character.

### Category D — Cross-Semantics / Interaction

-   **Literals in Free-Spacing Mode (`%flags x`)**: Test that a pattern like `a b` is parsed as a sequence of two separate nodes, `Seq(parts=[Lit('a'), Lit('b')])`.
-   **Escapes in Free-Spacing Mode (`%flags x`)**: Test that an escaped space `\ ` is parsed as a `Lit(' ')` and is not ignored like unescaped whitespace.

## Completion Criteria

-   [ ] All grammar rules from `dsl.ebnf` related to literals and escapes are covered (`Literal`, `EscapeSequence`, `HexEscape`, `UnicodeEscape`, `NullByteEscape`, `ControlEscape`, `IdentityEscape`).
-   [ ] All valid escape forms listed in `semantics.md` are tested.
-   [ ] All explicitly forbidden or malformed escape sequences documented in `semantics.md` and `parser.py` are tested and raise the correct `ParseError` with the expected message prefix and position.
-   [ ] The AST shape (`nodes.Lit`) and its `value` are asserted for all positive cases.
-   [ ] No redundant tests exist for inputs that fall into the same equivalence partition (e.g., testing `a` and `b` is sufficient; `c`, `d`, `e` are not needed).
