r"""
Test Design — test_anchors.py

## Purpose
This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
with the proper type and that its parsing is unaffected by flags or surrounding
constructs.

## Description
Anchors are zero-width assertions that do not consume characters but instead
match a specific **position** within the input string, such as the start of a
line or a boundary between a word and a space. This suite tests the parser's
ability to correctly identify all supported core and extension anchors and
produce the corresponding `nodes.Anchor` AST object.

## Scope
-   **In scope:**
    -   Parsing of core line anchors (`^`, `$`) and word boundary anchors
        (`\b`, `\B`).
    -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`, `\z`).

    -   The structure and `at` value of the resulting `nodes.Anchor` AST node.

    -   How anchors are parsed when placed at the start, middle, or end of a sequence.

    -   Ensuring the parser's output for `^` and `$` is consistent regardless
        of the multiline (`m`) flag's presence.
-   **Out of scope:**
    -   The runtime *behavioral change* of `^` and `$` when the `m` flag is
        active (this is an emitter/engine concern).
    -   Quantification of anchors.
    -   The behavior of `\b` inside a character class, where it represents a
        backspace literal (covered in `test_char_classes.py`).
"""

import pytest
from typing import Type, cast

from STRling.core.parser import parse
from STRling.core.nodes import Node, Anchor, Seq, Group, Look

# --- Test Suite -----------------------------------------------------------------


class TestCategoryAPositiveCases:
    """
    Covers all positive cases for valid anchor syntax. These tests verify
    that each anchor token is parsed into the correct Anchor node with the
    expected `at` value.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_at_value",
        [
            # A.1: Core Line Anchors
            ("^", "Start"),
            ("$", "End"),
            # A.2: Core Word Boundary Anchors
            (r"\b", "WordBoundary"),
            (r"\B", "NotWordBoundary"),
            # A.3: Absolute Anchors (Extension Features)
            (r"\A", "AbsoluteStart"),
            (r"\Z", "EndBeforeFinalNewline"),
            (r"\z", "AbsoluteEnd"),
        ],
        ids=[
            "line_start",
            "line_end",
            "word_boundary",
            "not_word_boundary",
            "absolute_start_ext",
            "end_before_newline_ext",
            "absolute_end_ext",
        ],
    )
    def test_all_anchor_types_are_parsed_correctly(
        self, input_dsl: str, expected_at_value: str
    ):
        """
        Tests that each individual anchor token is parsed into the correct
        Anchor AST node.
        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Anchor)
        assert ast.at == expected_at_value


class TestCategoryBNegativeCases:
    """
    This category is intentionally empty. Anchors are single, unambiguous
    tokens, and there are no anchor-specific parse errors. Invalid escape
    sequences are handled by the literal/escape parser and are tested in
    that suite.
    """

    pass


class TestCategoryCEdgeCases:
    """
    Covers edge cases related to the position and combination of anchors.
    """

    def test_pattern_with_only_anchors(self):
        """
        Tests that a pattern containing multiple anchors is parsed into a
        correct sequence of Anchor nodes.
        """
        _flags, ast = parse(r"^\A\b$")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 4
        # Add type check and cast to inform the type checker
        assert all(isinstance(part, Anchor) for part in ast.parts)
        assert [cast(Anchor, part).at for part in ast.parts] == [
            "Start",
            "AbsoluteStart",
            "WordBoundary",
            "End",
        ]

    @pytest.mark.parametrize(
        "input_dsl, expected_position, expected_at_value",
        [
            (r"^a", 0, "Start"),
            (r"a\bb", 1, "WordBoundary"),
            (r"ab$", 2, "End"),
        ],
        ids=["at_start", "in_middle", "at_end"],
    )
    def test_anchors_in_different_positions(
        self, input_dsl: str, expected_position: int, expected_at_value: str
    ):
        """
        Tests that anchors are correctly parsed as part of a sequence at
        various positions.
        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Seq)
        anchor_node = ast.parts[expected_position]
        assert isinstance(anchor_node, Anchor)
        assert anchor_node.at == expected_at_value


class TestCategoryDInteractionCases:
    """
    Covers how anchors interact with other DSL features, such as flags
    and grouping constructs.
    """

    def test_multiline_flag_does_not_change_parsed_ast(self):
        """
        A critical test to ensure the parser's output for `^` and `$` is
        identical regardless of the multiline flag. The flag's semantic
        effect is a runtime concern for the regex engine.
        """
        _flags_no_m, ast_no_m = parse("^a$")
        _flags_with_m, ast_with_m = parse("%flags m\n^a$")

        assert ast_no_m == ast_with_m

        # Add isinstance checks to help the type checker
        assert isinstance(ast_no_m, Seq)
        assert isinstance(ast_no_m.parts[0], Anchor)
        assert isinstance(ast_no_m.parts[2], Anchor)
        assert ast_no_m.parts[0].at == "Start"
        assert ast_no_m.parts[2].at == "End"

    @pytest.mark.parametrize(
        "input_dsl, container_type, expected_at_value",
        [
            (r"(^a)", Group, "Start"),
            (r"(?:a\b)", Group, "WordBoundary"),
            (r"(?=a$)", Look, "End"),
            (r"(?<=^a)", Look, "Start"),
        ],
        ids=[
            "in_capturing_group",
            "in_noncapturing_group",
            "in_lookahead",
            "in_lookbehind",
        ],
    )
    def test_anchors_inside_groups_and_lookarounds(
        self, input_dsl: str, container_type: Type[Node], expected_at_value: str
    ):
        """
        Tests that anchors are correctly parsed when nested inside other
        syntactic constructs.
        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, container_type)

        # Add isinstance check for the container before accessing `.body`
        assert isinstance(ast, (Group, Look))

        # The anchor may be part of a sequence inside the container
        inner_node = ast.body.parts[0] if isinstance(ast.body, Seq) else ast.body

        assert isinstance(inner_node, Anchor)
        assert inner_node.at == expected_at_value
