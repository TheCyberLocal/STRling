# Test Design — `unit/test_char_classes.py`

## Purpose

This test suite validates the correct parsing of character classes, ensuring all forms—including literals, ranges, shorthands, and Unicode properties—are correctly transformed into `CharClass` AST nodes. It also verifies that negation, edge cases involving special characters, and invalid syntax are handled according to the DSL's semantics.

## Description

Character classes (`[...]`) are a fundamental feature of the STRling DSL, allowing a pattern to match any single character from a specified set. This suite tests the parser's ability to correctly handle the various components that can make up these sets: literal characters, character ranges (`a-z`), shorthand escapes (`\d`, `\w`), and Unicode property escapes (`\p{L}`). It also ensures that class-level negation (`[^...]`) and the special rules for metacharacters (`-`, `]`, `^`) within classes are parsed correctly.

## Scope

-   **In scope:**

    -   Parsing of positive `[abc]` and negative `[^abc]` character classes.
    -   Parsing of character ranges (`[a-z]`, `[0-9]`) and their validation.
    -   Parsing of all supported shorthand (`\d`, `\s`, `\w` and their negated counterparts) and Unicode property (`\p{...}`, `\P{...}`) escapes within a class.
    -   The special syntactic rules for `]`, `-`, `^`, and escapes like `\b` when they appear inside a class.
    -   Error handling for malformed classes (e.g., unterminated `[` or invalid ranges `[z-a]`).
    -   The structure of the resulting `nodes.CharClass` AST node and its list of `items`.

-   **Out of scope:**
    -   Quantification of an entire character class (covered in `test_quantifiers.py`).
    -   The behavior of character classes within groups or lookarounds.
    -   Emitter-specific optimizations or translations (e.g., folding `[^\d]` to `\D`), which are covered in `test_emitter_edges.py`.
    -   POSIX classes like `[[:alpha:]]`, which are defined as non-core extensions in `semantics.md`.

## Categories of Tests

### Category A — Positive Cases (Valid Syntax)

-   **Basic Classes**:
    -   Test simple sets of literals: `[abc]` → `CharClass(negated=False, items=[ClassLiteral('a'), ...])`.
    -   Test negated sets: `[^abc]` → `CharClass(negated=True, items=[...])`.
-   **Ranges**:
    -   Test standard ranges: `[a-z]`, `[A-Z]`, `[0-9]`.
    -   Test combinations of ranges and literals: `[A-Za-z_]`.
-   **Shorthand Escapes**:
    -   Test that shorthand escapes `\d`, `\w`, `\s` and their negated counterparts `\D`, `\W`, `\S` are parsed correctly as `ClassEscape` items within a class. Example: `[\d\s]` → `CharClass(items=[ClassEscape('d'), ClassEscape('s')])`.
-   **Unicode Property Escapes**:
    -   Test basic property: `[\p{Letter}]` → `CharClass(items=[ClassEscape('p', property='Letter')])`.
    -   Test negated property: `[\P{Letter}]`.
    -   Test property with value: `[\p{Script=Greek}]`.
-   **Special Character Handling (per `semantics.md` and `parser.py`)**:
    -   A literal hyphen `-` when it is the first or last character: `[-az]`, `[az-]`.
    -   A literal closing bracket `]` when it is the first character after the opening `[` or `[^`: `[]a]`, `[^]a]`.
    -   A literal caret `^` when it is not the first character: `[a^b]`.
    -   Test that `\b` inside a class is parsed as a literal backspace (`\x08`), not a word boundary anchor.

### Category B — Negative Cases (Parse Errors)

-   **Unterminated Class**: `[abc` must raise `ParseError("Unterminated character class", 4)`.
-   **Invalid Range**: `[z-a]` should be parsed as three literals (`z`, `-`, `a`) according to the parser's logic, but a semantic check later could flag it. The test should confirm the current parsing behavior.
-   **Malformed Unicode Property**:
    -   Unterminated property: `[\p{Letter` must raise `ParseError("Unterminated \\p{...}", 10)`.
    -   Missing curly braces: `\pL` must raise `ParseError("Expected { after \\p/\\P", 3)`.

### Category C — Edge Cases

-   **Empty Classes**:
    -   `[]` should parse as a class that matches a literal `]`. The parser logic indicates the first `]` closes the class, making it an empty class, which is an interesting edge case to test.
    -   `[^]` should parse as a negated class that matches a literal `]`.
-   **Classes with only Escapes**: Test a class containing only escapes, like `[\n\t\r]`.
-   **Ranges with Escaped Endpoints**: Test ranges where one or both endpoints are hex or Unicode escapes, e.g., `[\x41-\x5A]`.
-   **Escaped Hyphen in Range Position**: Test that `[a\-z]` is parsed as three literals (`a`, `-`, `z`), not a range.

### Category D — Cross-Semantics / Interaction

-   **Free-Spacing Mode (`%flags x`)**: Test that whitespace and `#` comments inside a character class are treated as literal characters and are not ignored, as specified in `semantics.md`. Example: `[a #b]` should parse to `CharClass(items=[ClassLiteral('a'), ClassLiteral(' '), ClassLiteral('#'), ClassLiteral('b')])`.

### Category E — Minimal Character Classes

-   **Single Character Classes**:
    -   Test minimal positive classes with a single literal, like `[a]`.
    -   Test minimal negated classes, like `[^a]`.
-   **Two-Character Classes**:
    -   Test classes with exactly two characters, like `[ab]` and `[^ab]`.

### Category F — Escaped Metacharacters in Classes

-   **Escaping Special Characters**:
    -   Test escaped metacharacters that have special meaning in classes, such as `[\[\]]` for literal brackets.
    -   Test escaped backslash within classes, like `[\\]`.
-   **Escaped Hyphen**:
    -   Test that escaped hyphen `\-` is parsed as a literal hyphen even in range position.
-   **Escaped Caret**:
    -   Test escaped caret `\^` within a class.

### Category G — Complex Range Combinations

-   **Multiple Ranges**:
    -   Test classes with multiple ranges, like `[a-zA-Z0-9]`.
-   **Overlapping Ranges**:
    -   Test classes with overlapping ranges, such as `[a-mh-z]`.
-   **Adjacent Ranges**:
    -   Test adjacent ranges like `[a-z0-9]` to ensure correct parsing without merging.
-   **Ranges with Mixed Content**:
    -   Test ranges intermixed with literals and escapes, like `[a-z\d_-]`.

### Category H — Unicode Property Combinations

-   **Multiple Unicode Properties**:
    -   Test classes containing multiple Unicode properties, like `[\p{L}\p{N}]`.
-   **Mixed Unicode and Shorthand**:
    -   Test combinations of Unicode properties and shorthand escapes, such as `[\p{L}\d]`.
-   **Unicode Property with Literals**:
    -   Test Unicode properties mixed with literal characters, like `[\p{L}abc]`.
-   **Script-Specific Properties**:
    -   Test Unicode properties with script values, like `[\p{Script=Greek}]`.

### Category I — Negated Class Variations

-   **Negated Classes with Ranges**:
    -   Test negated classes containing ranges, like `[^a-z]`.
-   **Negated Classes with Shorthand**:
    -   Test negated classes with shorthand escapes, such as `[^\d]`.
-   **Negated Classes with Unicode Properties**:
    -   Test negated classes containing Unicode properties, like `[^\p{L}]`.
-   **Complex Negated Classes**:
    -   Test negated classes with mixed content, such as `[^a-z\d\p{P}]`.

### Category J — Character Class Error Cases

-   **Unterminated Classes**:
    -   Test various unterminated class scenarios beyond the basic case.
-   **Invalid Unicode Property Syntax**:
    -   Test malformed Unicode properties with various error conditions.
-   **Empty or Minimal Error Conditions**:
    -   Test edge cases that might trigger parse errors in character class context.

## Completion Criteria

-   [x] All grammar rules from `dsl.ebnf` related to `CharClass` and `ClassItem` are covered.
-   [x] Both positive (`[...]`) and negative (`[^...]`) forms are tested.
-   [x] All supported shorthands (`\d`, `\w`, etc.) and Unicode properties (`\p{...}`) are tested inside a class.
-   [x] All special character rules (`-`, `]`, `^`, `\b`) defined in `semantics.md` are verified.
-   [x] All expected `ParseError` conditions from `parser.py` are tested.
-   [x] The AST shape (`nodes.CharClass` with a list of `ClassItem` objects) is asserted for all positive cases.
-   [x] The interaction with free-spacing mode is explicitly tested.
-   [x] Minimal character classes (single and two-character) are validated.
-   [x] Escaped metacharacters within classes are thoroughly tested.
-   [x] Complex range combinations including overlapping and adjacent ranges are covered.
-   [x] Unicode property combinations with mixed content are tested.
-   [x] Negated class variations with all content types are verified.
-   [x] Comprehensive error cases for character classes are validated.
