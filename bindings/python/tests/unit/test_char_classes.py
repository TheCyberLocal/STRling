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
            (r"[\p{L", "Unterminated \\\\p{...}", 1),
            (r"[\pL]", "Expected { after \\\\p/\\\\P", 1),
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


# --- New Test Stubs for 3-Test Standard Compliance -----------------------------


class TestCategoryEMinimalCharClasses:
    """
    Tests for character classes with minimal content.
    """

    def test_single_literal_in_class(self):
        """
        Tests character class with single literal: [a]
        """
        _flags, ast = parse("[a]")
        assert isinstance(ast, CharClass)
        assert ast.negated is False
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassLiteral)
        assert ast.items[0].ch == "a"

    def test_single_literal_negated_class(self):
        """
        Tests negated class with single literal: [^x]
        """
        _flags, ast = parse("[^x]")
        assert isinstance(ast, CharClass)
        assert ast.negated is True
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassLiteral)
        assert ast.items[0].ch == "x"

    def test_single_range_in_class(self):
        """
        Tests class with only a single range: [a-z]
        Already exists but validating explicit simple case.
        """
        _flags, ast = parse("[a-z]")
        assert isinstance(ast, CharClass)
        assert ast.negated is False
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassRange)
        assert ast.items[0].from_ch == "a"
        assert ast.items[0].to_ch == "z"


class TestCategoryFEscapedMetacharsInClasses:
    """
    Tests for escaped metacharacters inside character classes.
    """

    def test_escaped_dot_in_class(self):
        """
        Tests escaped dot in class: [\\.]
        The dot should be literal, not a wildcard.
        """
        _flags, ast = parse(r"[\.]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassLiteral)
        assert ast.items[0].ch == "."

    def test_escaped_star_in_class(self):
        """
        Tests escaped star in class: [\\*]
        """
        _flags, ast = parse(r"[\*]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassLiteral)
        assert ast.items[0].ch == "*"

    def test_escaped_plus_in_class(self):
        """
        Tests escaped plus in class: [\\+]
        """
        _flags, ast = parse(r"[\+]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassLiteral)
        assert ast.items[0].ch == "+"

    def test_multiple_escaped_metachars(self):
        """
        Tests multiple escaped metacharacters: [\\.\\*\\+\\?]
        """
        _flags, ast = parse(r"[\.\*\+\?]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 4
        assert all(isinstance(item, ClassLiteral) for item in ast.items)
        chars = [item.ch for item in ast.items]
        assert chars == [".", "*", "+", "?"]

    def test_escaped_backslash_in_class(self):
        """
        Tests escaped backslash in class: [\\\\]
        """
        _flags, ast = parse(r"[\\]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassLiteral)
        assert ast.items[0].ch == "\\"


class TestCategoryGComplexRangeCombinations:
    """
    Tests for character classes with complex range combinations.
    """

    def test_multiple_non_overlapping_ranges(self):
        """
        Tests multiple separate ranges: [a-zA-Z0-9]
        Already covered but validating as typical case.
        """
        _flags, ast = parse("[a-zA-Z0-9]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 3
        assert isinstance(ast.items[0], ClassRange)
        assert ast.items[0].from_ch == "a" and ast.items[0].to_ch == "z"
        assert isinstance(ast.items[1], ClassRange)
        assert ast.items[1].from_ch == "A" and ast.items[1].to_ch == "Z"
        assert isinstance(ast.items[2], ClassRange)
        assert ast.items[2].from_ch == "0" and ast.items[2].to_ch == "9"

    def test_range_with_literals_mixed(self):
        """
        Tests ranges mixed with literals: [a-z_0-9-]
        """
        _flags, ast = parse("[a-z_0-9-]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 4
        assert isinstance(ast.items[0], ClassRange)
        assert ast.items[0].from_ch == "a" and ast.items[0].to_ch == "z"
        assert isinstance(ast.items[1], ClassLiteral)
        assert ast.items[1].ch == "_"
        assert isinstance(ast.items[2], ClassRange)
        assert ast.items[2].from_ch == "0" and ast.items[2].to_ch == "9"
        assert isinstance(ast.items[3], ClassLiteral)
        assert ast.items[3].ch == "-"

    def test_adjacent_ranges(self):
        """
        Tests adjacent character ranges: [a-z][A-Z]
        Note: This is two separate classes, not one.
        """
        _flags, ast = parse("[a-z][A-Z]")
        from STRling.core.nodes import Seq
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 2
        assert isinstance(ast.parts[0], CharClass)
        assert len(ast.parts[0].items) == 1
        assert isinstance(ast.parts[0].items[0], ClassRange)
        assert isinstance(ast.parts[1], CharClass)
        assert len(ast.parts[1].items) == 1
        assert isinstance(ast.parts[1].items[0], ClassRange)


class TestCategoryHUnicodePropertyCombinations:
    """
    Tests for combinations of Unicode property escapes.
    """

    def test_multiple_unicode_properties(self):
        """
        Tests multiple Unicode properties in one class: [\\p{L}\\p{N}]
        """
        _flags, ast = parse(r"[\p{L}\p{N}]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 2
        assert isinstance(ast.items[0], ClassEscape)
        assert ast.items[0].type == "p"
        assert ast.items[0].property == "L"
        assert isinstance(ast.items[1], ClassEscape)
        assert ast.items[1].type == "p"
        assert ast.items[1].property == "N"

    def test_unicode_property_with_literals(self):
        """
        Tests Unicode property mixed with literals: [\\p{L}abc]
        """
        _flags, ast = parse(r"[\p{L}abc]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 4
        assert isinstance(ast.items[0], ClassEscape)
        assert ast.items[0].type == "p"
        assert isinstance(ast.items[1], ClassLiteral)
        assert ast.items[1].ch == "a"
        assert isinstance(ast.items[2], ClassLiteral)
        assert ast.items[2].ch == "b"
        assert isinstance(ast.items[3], ClassLiteral)
        assert ast.items[3].ch == "c"

    def test_unicode_property_with_range(self):
        """
        Tests Unicode property mixed with range: [\\p{L}0-9]
        """
        _flags, ast = parse(r"[\p{L}0-9]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 2
        assert isinstance(ast.items[0], ClassEscape)
        assert ast.items[0].type == "p"
        assert ast.items[0].property == "L"
        assert isinstance(ast.items[1], ClassRange)
        assert ast.items[1].from_ch == "0"
        assert ast.items[1].to_ch == "9"

    def test_negated_unicode_property_in_class(self):
        """
        Tests negated Unicode property: [\\P{L}]
        Already exists but confirming coverage.
        """
        _flags, ast = parse(r"[\P{L}]")
        assert isinstance(ast, CharClass)
        assert ast.negated is False  # The class itself is not negated
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassEscape)
        assert ast.items[0].type == "P"  # P is the negated property
        assert ast.items[0].property == "L"


class TestCategoryINegatedClassVariations:
    """
    Tests for negated character classes with various contents.
    """

    def test_negated_class_with_range(self):
        """
        Tests negated class with range: [^a-z]
        """
        _flags, ast = parse("[^a-z]")
        assert isinstance(ast, CharClass)
        assert ast.negated is True
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassRange)
        assert ast.items[0].from_ch == "a"
        assert ast.items[0].to_ch == "z"

    def test_negated_class_with_shorthand(self):
        """
        Tests negated class with shorthand: [^\\d\\s]
        """
        _flags, ast = parse(r"[^\d\s]")
        assert isinstance(ast, CharClass)
        assert ast.negated is True
        assert len(ast.items) == 2
        assert isinstance(ast.items[0], ClassEscape)
        assert ast.items[0].type == "d"
        assert isinstance(ast.items[1], ClassEscape)
        assert ast.items[1].type == "s"

    def test_negated_class_with_unicode_property(self):
        """
        Tests negated class with Unicode property: [^\\p{L}]
        """
        _flags, ast = parse(r"[^\p{L}]")
        assert isinstance(ast, CharClass)
        assert ast.negated is True
        assert len(ast.items) == 1
        assert isinstance(ast.items[0], ClassEscape)
        assert ast.items[0].type == "p"
        assert ast.items[0].property == "L"


class TestCategoryJCharClassErrorCases:
    """
    Additional error cases for character classes.
    """

    def test_truly_empty_class_raises_error(self):
        """
        Tests that [] without the special ] handling raises an error.
        Note: []a] is valid (] is literal), but [] alone should error.
        """
        with pytest.raises(ParseError, match="Unterminated character class"):
            parse("[]")

    def test_invalid_range_reversed_endpoints(self):
        """
        Tests invalid range with reversed endpoints: [z-a]
        Per IEH audit, the parser should reject this with a validation error.
        """
        with pytest.raises(ParseError, match="Invalid character range"):
            parse("[z-a]")

    def test_incomplete_range_at_end(self):
        """
        Tests incomplete range at class end: [a-]
        This is valid (hyphen is literal), confirm behavior.
        """
        _flags, ast = parse("[a-]")
        assert isinstance(ast, CharClass)
        assert len(ast.items) == 2
        assert isinstance(ast.items[0], ClassLiteral)
        assert ast.items[0].ch == "a"
        assert isinstance(ast.items[1], ClassLiteral)
        assert ast.items[1].ch == "-"
