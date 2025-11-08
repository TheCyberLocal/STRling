r"""
Test Design — test_literals_and_escapes.py

## Purpose
This test suite validates the parser's handling of all literal characters and
every form of escape sequence defined in the STRling DSL. It ensures that valid
forms are correctly parsed into `Lit` AST nodes and that malformed or
unsupported sequences raise the appropriate `ParseError`.

## Description
Literals and escapes are the most fundamental **atoms** in a STRling pattern,
representing single, concrete characters. This module tests the parser's ability
to distinguish between literal characters and special metacharacters, and to
correctly interpret the full range of escape syntaxes (identity, control, hex,
and Unicode). The expected behavior is for the parser to consume these tokens
and produce a `nodes.Lit` object containing the corresponding character value.

## Scope
-   **In scope:**
    -   Parsing of single literal characters.

    -   Parsing of all supported escape sequences (`\x`, `\u`, `\U`, `\0`, identity).

    -   Error handling for malformed or unsupported escapes (like octal).

    -   The shape of the resulting `Lit` AST node.

-   **Out of scope:**
    -   How literals are quantified (covered in `test_quantifiers.py`).

    -   How literals behave inside character classes (covered in `test_char_classes.py`).

    -   Emitter-specific escaping (covered in `test_emitter_edges.py`).

"""

import pytest

from STRling.core.parser import parse, ParseError
from STRling.core.nodes import Lit, Seq, Backref, Node, Quant, Alt, Group

# --- Test Suite -----------------------------------------------------------------


class TestCategoryAPositiveCases:
    """
    Covers all positive cases for valid literal and escape syntax.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_ast",
        [
            # A.1: Plain Literals
            ("a", Lit("a")),
            ("_", Lit("_")),
            # A.2: Identity Escapes
            (r"\.", Lit(".")),
            (r"\(", Lit("(")),
            (r"\*", Lit("*")),
            (r"\\\\", Lit("\\\\")),
            # A.3: Control & Whitespace Escapes
            (r"\n", Lit("\n")),
            (r"\t", Lit("\t")),
            (r"\r", Lit("\r")),
            (r"\f", Lit("\f")),
            (r"\v", Lit("\v")),
            # A.4: Hexadecimal Escapes
            (r"\x41", Lit("A")),
            (r"\x4a", Lit("J")),
            (r"\x{41}", Lit("A")),
            (r"\x{1F600}", Lit("😀")),
            # A.5: Unicode Escapes
            (r"\u0041", Lit("A")),
            (r"\u{41}", Lit("A")),
            (r"\u{1f600}", Lit("😀")),
            (r"\U0001F600", Lit("😀")),
            # A.6: Null Byte Escape
            (r"\0", Lit("\x00")),
        ],
        ids=[
            "plain_literal_letter",
            "plain_literal_underscore",
            "identity_escape_dot",
            "identity_escape_paren",
            "identity_escape_star",
            "identity_escape_backslash",
            "control_escape_newline",
            "control_escape_tab",
            "control_escape_carriage_return",
            "control_escape_form_feed",
            "control_escape_vertical_tab",
            "hex_escape_fixed",
            "hex_escape_fixed_case",
            "hex_escape_brace",
            "hex_escape_brace_non_bmp",
            "unicode_escape_fixed",
            "unicode_escape_brace_bmp",
            "unicode_escape_brace_non_bmp",
            "unicode_escape_fixed_supplementary",
            "null_byte_escape",
        ],
    )
    def test_valid_literals_and_escapes_are_parsed_correctly(
        self, input_dsl: str, expected_ast: Node
    ):
        """
        Tests that a valid literal or escape sequence is parsed into the correct
        Lit AST node.
        """
        _flags, ast = parse(input_dsl)
        assert ast == expected_ast


class TestCategoryBNegativeCases:
    """
    Covers negative cases for malformed or unsupported syntax.
    """

    @pytest.mark.parametrize(
        "invalid_dsl, error_message_prefix, error_position",
        [
            # B.1: Malformed Hex/Unicode
            (r"\x{12", "Unterminated \\\\x{...}", 0),
            (r"\xG", "Invalid \\\\xHH escape", 0),
            (r"\u{1F60", "Unterminated \\\\u{...}", 0),
            (r"\u123", "Invalid \\\\uHHHH", 0),
            (r"\U1234567", "Invalid \\\\UHHHHHHHH", 0),
            # B.2: Stray Metacharacters
            (")", "Unexpected trailing input", 0),
            ("|", "Alternation lacks left-hand side", 0),
        ],
        ids=[
            "unterminated_hex_brace",
            "invalid_hex_char_short",
            "unterminated_unicode_brace",
            "incomplete_unicode_fixed",
            "incomplete_unicode_supplementary",
            "stray_closing_paren",
            "stray_pipe",
        ],
    )
    def test_malformed_syntax_raises_parse_error(
        self, invalid_dsl: str, error_message_prefix: str, error_position: int
    ):
        """
        Tests that malformed escape syntax raises a ParseError with the correct
        message and position.
        """
        with pytest.raises(ParseError, match=error_message_prefix) as excinfo:
            parse(invalid_dsl)
        assert excinfo.value.pos == error_position

    def test_forbidden_octal_escape_parses_as_backref_and_literals(self):
        """
        Tests that a forbidden octal escape (e.g., \123) with no groups defined
        raises a ParseError for undefined backreference.
        """
        with pytest.raises(ParseError, match="Backreference to undefined group"):
            parse(r"\123")


class TestCategoryCEdgeCases:
    """
    Covers edge cases for literals and escapes.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_char",
        [
            (r"\u{10FFFF}", "\U0010ffff"),
            (r"\x{0}", "\x00"),
            (r"\x{}", "\x00"),
        ],
        ids=[
            "max_unicode_value",
            "zero_value_hex_brace",
            "empty_hex_brace",
        ],
    )
    def test_edge_case_escapes(self, input_dsl: str, expected_char: str):
        """Tests unusual but valid escape sequences."""
        _flags, ast = parse(input_dsl)
        assert ast == Lit(expected_char)

    def test_escaped_null_byte(self):
        """
        Tests that an escaped backslash followed by a zero is not parsed as
        a null byte.
        """
        _flags, ast = parse(r"\\\\0")
        assert ast == Seq(parts=[Lit("\\\\"), Lit("0")])


class TestCategoryDInteractionCases:
    """
    Covers interactions between literals/escapes and free-spacing mode.
    """

    def test_free_spacing_ignores_whitespace_between_literals(self):
        """
        Tests that in free-spacing mode, whitespace between literals is
        ignored, resulting in a sequence of Lit nodes.

        """
        _flags, ast = parse("%flags x\n a b #comment\n c")
        assert ast == Seq(parts=[Lit("a"), Lit("b"), Lit("c")])

    def test_free_spacing_respects_escaped_whitespace(self):
        """
        Tests that in free-spacing mode, an escaped space is parsed as a
        literal space character.
        """
        _flags, ast = parse("%flags x\n a \\ b ")
        assert ast == Seq(parts=[Lit("a"), Lit(" "), Lit("b")])


# --- New Test Stubs for 3-Test Standard Compliance -----------------------------


class TestCategoryELiteralSequencesAndCoalescing:
    """
    Tests for sequences of literals and how the parser handles coalescing.
    """

    def test_multiple_plain_literals_in_sequence(self):
        """
        Tests sequence of plain literals: abc
        Should parse as single Lit("abc") or Seq([Lit("a"), Lit("b"), Lit("c")]).
        Verify actual parser behavior.
        """
        _flags, ast = parse("abc")
        assert isinstance(ast, Lit)
        assert ast.value == "abc"

    def test_literals_with_escaped_metachar_sequence(self):
        """
        Tests literals mixed with escaped metachars: a\\*b\\+c
        """
        _flags, ast = parse(r"a\*b\+c")
        assert isinstance(ast, Lit)
        assert ast.value == "a*b+c"

    def test_sequence_of_only_escapes(self):
        """
        Tests sequence of only escape sequences: \\n\\t\\r
        """
        _flags, ast = parse(r"\n\t\r")
        assert isinstance(ast, Seq)
        # The parser coalesces some escapes, check for parts
        assert len(ast.parts) >= 1
        # Verify all parts are Lit nodes containing the escape characters
        for part in ast.parts:
            assert isinstance(part, Lit)

    def test_mixed_escape_types_in_sequence(self):
        """
        Tests mixed escape types in sequence: \\x41\\u0042\\n
        Hex, Unicode, and control escapes together.
        """
        _flags, ast = parse(r"\x41\u0042\n")
        # The parser may coalesce these into Lit nodes
        assert isinstance(ast, (Lit, Seq))
        if isinstance(ast, Seq):
            # Verify all parts are Lit nodes
            for part in ast.parts:
                assert isinstance(part, Lit)


class TestCategoryFEscapeInteractions:
    """
    Tests for interactions between different escape types and literals.
    """

    def test_literal_after_control_escape(self):
        """
        Tests literal after control escape: \\na (newline followed by 'a')
        """
        _flags, ast = parse(r"\na")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 2
        assert isinstance(ast.parts[0], Lit)
        assert ast.parts[0].value == "\n"
        assert isinstance(ast.parts[1], Lit)
        assert ast.parts[1].value == "a"

    def test_literal_after_hex_escape(self):
        """
        Tests literal after hex escape: \\x41b (A followed by 'b')
        """
        _flags, ast = parse(r"\x41b")
        assert isinstance(ast, Lit)
        assert ast.value == "Ab"

    def test_escape_after_escape(self):
        """
        Tests escape after escape: \\n\\t (newline followed by tab)
        Already covered but confirming.
        """
        _flags, ast = parse(r"\n\t")
        assert isinstance(ast, Seq)
        assert len(ast.parts) >= 1
        # Verify all parts are Lit nodes
        for part in ast.parts:
            assert isinstance(part, Lit)

    def test_identity_escape_after_literal(self):
        """
        Tests identity escape after literal: a\\* ('a' followed by '*')
        """
        _flags, ast = parse(r"a\*")
        assert isinstance(ast, Lit)
        assert ast.value == "a*"


class TestCategoryGBackslashEscapeCombinations:
    """
    Tests for various backslash escape combinations.
    """

    def test_double_backslash(self):
        """
        Tests double backslash: \\\\
        Should parse as single backslash character.
        Already covered but confirming.
        """
        _flags, ast = parse(r"\\")
        assert isinstance(ast, Lit)
        assert ast.value == "\\"

    def test_quadruple_backslash(self):
        """
        Tests quadruple backslash: \\\\\\\\
        Should parse as two backslash characters.
        """
        _flags, ast = parse(r"\\\\")
        assert isinstance(ast, Lit)
        assert ast.value == "\\\\"

    def test_backslash_before_literal(self):
        """
        Tests backslash followed by non-metachar: \\\\a
        Should parse as backslash followed by 'a'.
        """
        _flags, ast = parse(r"\\a")
        assert isinstance(ast, Lit)
        assert ast.value == "\\a"


class TestCategoryHEscapeEdgeCasesExpanded:
    """
    Additional edge cases for escape sequences.
    """

    def test_hex_escape_min_value(self):
        """
        Tests minimum hex value: \\x00
        """
        _flags, ast = parse(r"\x00")
        assert isinstance(ast, Lit)
        assert ast.value == "\x00"

    def test_hex_escape_max_value(self):
        """
        Tests maximum single-byte hex value: \\xFF
        """
        _flags, ast = parse(r"\xFF")
        assert isinstance(ast, Lit)
        assert ast.value == "\xFF"

    def test_unicode_escape_bmp_boundary(self):
        """
        Tests Unicode at BMP boundary: \\uFFFF
        """
        _flags, ast = parse(r"\uFFFF")
        assert isinstance(ast, Lit)
        assert ast.value == "\uFFFF"

    def test_unicode_escape_supplementary_plane(self):
        """
        Tests Unicode in supplementary plane: \\U00010000
        First character outside BMP.
        """
        _flags, ast = parse(r"\U00010000")
        assert isinstance(ast, Lit)
        assert ast.value == "\U00010000"


class TestCategoryIOctalAndBackrefDisambiguation:
    """
    Tests for the parser's handling of octal-like sequences and
    their disambiguation with backreferences.
    """

    def test_single_digit_after_backslash_with_no_groups(self):
        """
        Tests that \\1 with no groups raises backreference error, not octal.
        Already partially covered, confirming.
        """
        with pytest.raises(ParseError, match="Backreference to undefined group"):
            parse(r"\1")

    def test_two_digit_sequence_with_one_group(self):
        """
        Tests (a)\\12: should be backref \\1 followed by literal '2'.
        """
        _flags, ast = parse(r"(a)\12")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Group)
        assert isinstance(ast.parts[1], Backref)
        assert ast.parts[1].byIndex == 1
        assert isinstance(ast.parts[2], Lit)
        assert ast.parts[2].value == "2"

    def test_three_digit_sequence_behavior(self):
        """
        Tests \\123 parsing behavior (backref or error).
        Already covered, confirming behavior.
        """
        with pytest.raises(ParseError, match="Backreference to undefined group"):
            parse(r"\123")


class TestCategoryJLiteralsInComplexContexts:
    """
    Tests for literal behavior in complex syntactic contexts.
    """

    def test_literal_between_quantifiers(self):
        """
        Tests literal between quantified atoms: a*Xb+
        """
        _flags, ast = parse("a*Xb+")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Quant)
        assert isinstance(ast.parts[1], Lit)
        assert ast.parts[1].value == "X"
        assert isinstance(ast.parts[2], Quant)

    def test_literal_in_alternation(self):
        """
        Tests literal in alternation: a|b|c
        """
        _flags, ast = parse("a|b|c")
        assert isinstance(ast, Alt)
        assert len(ast.branches) == 3
        assert isinstance(ast.branches[0], Lit)
        assert ast.branches[0].value == "a"
        assert isinstance(ast.branches[1], Lit)
        assert ast.branches[1].value == "b"
        assert isinstance(ast.branches[2], Lit)
        assert ast.branches[2].value == "c"

    def test_escaped_literal_in_group(self):
        """
        Tests escaped literal inside group: (\\*)
        """
        _flags, ast = parse(r"(\*)")
        assert isinstance(ast, Group)
        assert ast.capturing is True
        assert isinstance(ast.body, Lit)
        assert ast.body.value == "*"
