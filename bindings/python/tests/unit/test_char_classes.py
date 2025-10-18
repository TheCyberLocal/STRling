r"""
Test Design — test_char_classes.py

## Purpose
This test suite validates the correct parsing of character classes, ensuring
all forms—including literals, ranges, shorthands, and Unicode properties—are
correctly transformed into `CharClass` AST nodes. It also verifies that
negation, edge cases involving special characters, and invalid syntax are
handled according to the DSL's semantics.

## Description
Character classes (`[...]`) are a fundamental feature of the STRling DSL,
allowing a pattern to match any single character from a specified set. This
suite tests the parser's ability to correctly handle the various components
that can make up these sets: literal characters, character ranges (`a-z`),
shorthand escapes (`\d`, `\w`), and Unicode property escapes (`\p{L}`). It also
ensures that class-level negation (`[^...]`) and the special rules for
metacharacters (`-`, `]`, `^`) within classes are parsed correctly.

## Scope
-   **In scope:**
    -   Parsing of positive `[abc]` and negative `[^abc]` character classes.

    -   Parsing of character ranges (`[a-z]`, `[0-9]`) and their validation.

    -   Parsing of all supported shorthand (`\d`, `\s`, `\w` and their negated
        counterparts) and Unicode property (`\p{...}`, `\P{...}`) escapes
        within a class.
    -   The special syntactic rules for `]`, `-`, `^`, and escapes like `\b`
        when they appear inside a class.
    -   Error handling for malformed classes (e.g., unterminated `[` or invalid
        ranges `[z-a]`).
    -   The structure of the resulting `nodes.CharClass` AST node and its list
        of `items`.
-   **Out of scope:**
    -   Quantification of an entire character class (covered in
        `test_quantifiers.py`).
    -   The behavior of character classes within groups or lookarounds.

    -   Emitter-specific optimizations or translations (covered in
        `test_emitter_edges.py`).
"""

import pytest
from typing import List

from STRling.core.parser import parse, ParseError
from STRling.core.nodes import (
    CharClass,
    ClassItem,
    ClassLiteral,
    ClassRange,
    ClassEscape,
)

# --- Test Suite -----------------------------------------------------------------


class TestCategoryAPositiveCases:
    """
    Covers all positive cases for valid character class syntax.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_negated, expected_items",
        [
            # A.1: Basic Classes
            ("[abc]", False, [ClassLiteral("a"), ClassLiteral("b"), ClassLiteral("c")]),
            ("[^abc]", True, [ClassLiteral("a"), ClassLiteral("b"), ClassLiteral("c")]),
            # A.2: Ranges
            ("[a-z]", False, [ClassRange("a", "z")]),
            (
                "[A-Za-z0-9]",
                False,
                [ClassRange("A", "Z"), ClassRange("a", "z"), ClassRange("0", "9")],
            ),
            # A.3: Shorthand Escapes
            (
                r"[\d\s\w]",
                False,
                [ClassEscape("d"), ClassEscape("s"), ClassEscape("w")],
            ),
            (
                r"[\D\S\W]",
                False,
                [ClassEscape("D"), ClassEscape("S"), ClassEscape("W")],
            ),
            # A.4: Unicode Property Escapes
            (r"[\p{L}]", False, [ClassEscape("p", property="L")]),
            (r"[\p{Letter}]", False, [ClassEscape("p", property="Letter")]),
            (r"[\P{Number}]", False, [ClassEscape("P", property="Number")]),
            (r"[\p{Script=Greek}]", False, [ClassEscape("p", property="Script=Greek")]),
            # A.5: Special Character Handling
            ("[]a]", False, [ClassLiteral("]"), ClassLiteral("a")]),
            ("[^]a]", True, [ClassLiteral("]"), ClassLiteral("a")]),
            ("[-az]", False, [ClassLiteral("-"), ClassLiteral("a"), ClassLiteral("z")]),
            ("[az-]", False, [ClassLiteral("a"), ClassLiteral("z"), ClassLiteral("-")]),
            ("[a^b]", False, [ClassLiteral("a"), ClassLiteral("^"), ClassLiteral("b")]),
            (r"[\b]", False, [ClassLiteral("\x08")]),  # \b is backspace inside class
        ],
        ids=[
            "simple_class",
            "negated_simple_class",
            "range_lowercase",
            "range_alphanum",
            "shorthand_positive",
            "shorthand_negated",
            "unicode_property_short",
            "unicode_property_long",
            "unicode_property_negated",
            "unicode_property_with_value",
            "special_char_bracket_at_start",
            "special_char_bracket_at_start_negated",
            "special_char_hyphen_at_start",
            "special_char_hyphen_at_end",
            "special_char_caret_in_middle",
            "special_char_backspace_escape",
        ],
    )
    def test_valid_char_classes_are_parsed_correctly(
        self, input_dsl: str, expected_negated: bool, expected_items: List[ClassItem]
    ):
        """
        Tests that various valid character classes are parsed into the correct
        CharClass AST node with the expected items.
        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, CharClass)
        assert ast.negated == expected_negated
        assert ast.items == expected_items


class TestCategoryBNegativeCases:
    """
    Covers all negative cases for malformed character class syntax.
    """

    @pytest.mark.parametrize(
        "invalid_dsl, error_message_prefix, error_position",
        [
            # B.1: Unterminated classes
            ("[abc", "Unterminated character class", 4),
            ("[", "Unterminated character class", 1),
            ("[^", "Unterminated character class", 2),
            # B.2: Malformed Unicode properties
            (r"[\p{L", "Unterminated \\\\p{...}", 5),
            (r"[\pL]", "Expected { after \\\\p/\\\\P", 3),
        ],
        ids=[
            "unterminated_class",
            "unterminated_empty_class",
            "unterminated_negated_empty_class",
            "unterminated_unicode_property",
            "missing_braces_on_unicode_property",
        ],
    )
    def test_invalid_char_classes_raise_parse_error(
        self, invalid_dsl: str, error_message_prefix: str, error_position: int
    ):
        """
        Tests that invalid character class syntax raises a ParseError with the
        correct message and position.
        """
        with pytest.raises(ParseError, match=error_message_prefix) as excinfo:
            parse(invalid_dsl)
        assert excinfo.value.pos == error_position


class TestCategoryCEdgeCases:
    """
    Covers edge cases for character class parsing.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_items",
        [
            (r"[a\-c]", [ClassLiteral("a"), ClassLiteral("-"), ClassLiteral("c")]),
            (r"[\x41-\x5A]", [ClassRange("A", "Z")]),
            (r"[\n\t\d]", [ClassLiteral("\n"), ClassLiteral("\t"), ClassEscape("d")]),
        ],
        ids=[
            "escaped_hyphen_is_literal",
            "range_with_escaped_endpoints",
            "class_with_only_escapes",
        ],
    )
    def test_edge_case_classes(self, input_dsl: str, expected_items: List[ClassItem]):
        """
        Tests unusual but valid character class constructs.
        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, CharClass)
        assert ast.items == expected_items


class TestCategoryDInteractionCases:
    """
    Covers how character classes interact with other DSL features, specifically
    the free-spacing mode flag.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_items",
        [
            (
                "%flags x\n[a b]",
                [ClassLiteral("a"), ClassLiteral(" "), ClassLiteral("b")],
            ),
            (
                "%flags x\n[a#b]",
                [ClassLiteral("a"), ClassLiteral("#"), ClassLiteral("b")],
            ),
        ],
        ids=["whitespace_is_literal", "comment_char_is_literal"],
    )
    def test_free_spacing_mode_is_ignored_inside_class(
        self, input_dsl: str, expected_items: List[ClassItem]
    ):
        """
        Tests that in free-spacing mode, whitespace and '#' are treated as
        literal characters inside a class, per the specification.

        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, CharClass)
        assert ast.items == expected_items
