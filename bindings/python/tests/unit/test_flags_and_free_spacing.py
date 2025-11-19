"""
Test Design — test_flags_and_free_spacing.py

## Purpose
This test suite validates the correct parsing of the `%flags` directive and the
behavioral changes it induces, particularly the free-spacing (`x`) mode. It
ensures that flags are correctly identified and stored in the `Flags` object
and that the parser correctly handles whitespace and comments when the
extended mode is active.

## Description
The `%flags` directive is a top-level command in a `.strl` file that modifies
the semantics of the entire pattern. This suite tests the parser's ability to
correctly consume this directive and apply its effects. The primary focus is
on the **`x` flag (extended/free-spacing mode)**, which dramatically alters
how the parser handles whitespace and comments. The tests will verify that the
parser correctly ignores insignificant characters outside of character classes
while treating them as literals inside character classes.

## Scope
-   **In scope:**
    -   Parsing the `%flags` directive with single and multiple flags (`i`,
        `m`, `s`, `u`, `x`).
    -   Handling of various separators (commas, spaces) within the flag
        list.
    -   The parser's behavior in free-spacing mode: ignoring whitespace and
        comments outside character classes.
    -   The parser's behavior inside a character class when free-spacing mode
        is active (i.e., treating whitespace and `#` as literals).

    -   The structure of the `Flags` object produced by the parser and its
        serialization in the final artifact.
-   **Out of scope:**
    -   The runtime *effect* of the `i`, `m`, `s`, and `u` flags on the regex
        engine's matching behavior.
    -   The parsing of other directives like `%engine` or `%lang`.

"""

import pytest
from typing import List

from STRling.core.parser import parse, ParseError
from STRling.core.nodes import (
    Flags,
    Sequence,
    Literal,
    CharacterClass,
    ClassItem,
    ClassLiteral,
)

# --- Test Suite -----------------------------------------------------------------


class TestCategoryAPositiveCases:
    """
    Covers all positive cases for parsing flags and applying free-spacing mode.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_flags",
        [
            ("%flags i", Flags(ignoreCase=True)),
            ("%flags i, m, x", Flags(ignoreCase=True, multiline=True, extended=True)),
            ("%flags u m s", Flags(unicode=True, multiline=True, dotAll=True)),
            (
                "%flags i,m s,u x",
                Flags(
                    ignoreCase=True,
                    multiline=True,
                    dotAll=True,
                    unicode=True,
                    extended=True,
                ),
            ),
            ("  %flags i  ", Flags(ignoreCase=True)),
        ],
        ids=[
            "single_flag",
            "multiple_flags_with_commas",
            "multiple_flags_with_spaces",
            "multiple_flags_mixed_separators",
            "leading_trailing_whitespace",
        ],
    )
    def test_flag_directive_is_parsed_correctly(
        self, input_dsl: str, expected_flags: Flags
    ):
        """
        Tests that the %flags directive is correctly parsed into a Flags object.
        """
        flags, _ast = parse(input_dsl)
        assert flags == expected_flags

    @pytest.mark.parametrize(
        "input_dsl, expected_ast",
        [
            ("%flags x\na b c", Sequence([Literal("a"), Literal("b"), Literal("c")])),
            ("%flags x\na # comment\n b", Sequence([Literal("a"), Literal("b")])),
            ("%flags x\na\\ b", Sequence([Literal("a"), Literal(" "), Literal("b")])),
        ],
        ids=[
            "whitespace_is_ignored",
            "comments_are_ignored",
            "escaped_whitespace_is_literal",
        ],
    )
    def test_free_spacing_mode_behavior(self, input_dsl: str, expected_ast: Sequence):
        """
        Tests that the parser correctly handles whitespace and comments when the
        'x' flag is active.
        """
        _flags, ast = parse(input_dsl)
        assert ast == expected_ast


class TestCategoryBNegativeCases:
    """
    Covers lenient handling of malformed or unknown directives.
    """

    @pytest.mark.parametrize(
        "input_dsl",
        [
            "%flags z",
        ],
        ids=[
            "unknown_flag",
        ],
    )
    def test_invalid_flags_are_rejected(self, input_dsl: str):
        """
        Tests that the parser now rejects unknown flags per IEH audit.
        """
        with pytest.raises(ParseError, match="Invalid flag"):
            parse(input_dsl)
    
    def test_lenient_parsing_of_malformed_directive(self):
        """
        Tests that malformed directives (not starting with %flags exactly) are ignored.
        """
        flags, _ast = parse("%flagg i")
        assert flags == Flags()  # Default flags


class TestCategoryCEdgeCases:
    """
    Covers edge cases for flag parsing and free-spacing mode.
    """

    def test_empty_flags_directive(self):
        """Tests that an empty %flags directive results in default flags."""
        flags, _ast = parse("%flags")
        assert flags == Flags()

    def test_directive_after_content_is_rejected(self):
        """
        Tests that a directive appearing after pattern content is now rejected per IEH audit.
        """
        with pytest.raises(ParseError, match="Directive after pattern"):
            parse("a\n%flags i")

    def test_pattern_with_only_comments_and_whitespace(self):
        """
        Tests that a pattern which becomes empty in free-spacing mode results
        in an empty AST.
        """
        _flags, ast = parse("%flags x\n# comment\n  \n# another")
        assert ast == Sequence(parts=[])


class TestCategoryDInteractionCases:
    """
    Covers the critical interaction between free-spacing mode and character classes.
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
        ids=["whitespace_is_literal_in_class", "comment_char_is_literal_in_class"],
    )
    def test_free_spacing_is_disabled_inside_char_class(
        self, input_dsl: str, expected_items: List[ClassItem]
    ):
        """
        Tests that in free-spacing mode, whitespace and '#' are treated as
        literal characters inside a class, per the specification.

        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, CharacterClass)
        assert ast.items == expected_items
