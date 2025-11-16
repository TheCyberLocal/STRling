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

from STRling.core.parser import parse, ParseError
from STRling.core.nodes import Node, Anchor, Seq, Group, Look, Lit, Quant, Alt, Dot, CharClass

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
        ],
        ids=[
            "line_start",
            "line_end",
            "word_boundary",
            "not_word_boundary",
            "absolute_start_ext",
            "end_before_newline_ext",
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


    def test_z_escape_is_unknown(self):
        """
        The lowercase `\z` is not a recognized escape sequence and should
        raise a ParseError indicating an unknown escape sequence.
        """
        with pytest.raises(ParseError, match=r"Unknown escape sequence \\z"):
            parse(r"\z")


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
            (r"ab$", 1, "End"),
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

        # The anchor may be part of a sequence inside the container, find it
        if isinstance(ast.body, Seq):
            # Find the anchor in the sequence
            anchor = None
            for part in ast.body.parts:
                if isinstance(part, Anchor):
                    anchor = part
                    break
            assert anchor is not None, f"No anchor found in sequence: {ast.body.parts}"
            assert anchor.at == expected_at_value
        else:
            # Direct anchor
            assert isinstance(ast.body, Anchor)
            assert ast.body.at == expected_at_value


# --- New Test Stubs for 3-Test Standard Compliance -----------------------------


class TestCategoryEAnchorsInComplexSequences:
    """
    Tests for anchors in complex sequences with quantified atoms.
    """

    def test_anchor_between_quantified_atoms(self):
        """
        Tests anchor between quantified atoms: a*^b+
        The ^ anchor appears between two quantified literals.
        """
        _flags, ast = parse("a*^b+")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Quant)
        assert isinstance(ast.parts[1], Anchor)
        assert ast.parts[1].at == "Start"
        assert isinstance(ast.parts[2], Quant)

    def test_anchor_after_quantified_group(self):
        """
        Tests anchor after quantified group: (ab)*$
        """
        _flags, ast = parse("(ab)*$")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 2
        assert isinstance(ast.parts[0], Quant)
        assert isinstance(ast.parts[1], Anchor)
        assert ast.parts[1].at == "End"

    def test_multiple_anchors_of_same_type(self):
        """
        Tests multiple same anchors: ^^
        Edge case: semantically redundant but syntactically valid.
        """
        _flags, ast = parse("^^")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 2
        assert isinstance(ast.parts[0], Anchor)
        assert ast.parts[0].at == "Start"
        assert isinstance(ast.parts[1], Anchor)
        assert ast.parts[1].at == "Start"

    def test_multiple_end_anchors(self):
        """
        Tests multiple end anchors: $$
        """
        _flags, ast = parse("$$")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 2
        assert isinstance(ast.parts[0], Anchor)
        assert ast.parts[0].at == "End"
        assert isinstance(ast.parts[1], Anchor)
        assert ast.parts[1].at == "End"


class TestCategoryFAnchorsInAlternation:
    """
    Tests for anchors used in alternation patterns.
    """

    def test_anchor_in_alternation_branch(self):
        """
        Tests anchor in one branch of alternation: ^a|b$
        Parses as (^a)|(b$).
        """
        _flags, ast = parse("^a|b$")
        assert isinstance(ast, Alt)
        assert len(ast.branches) == 2
        # First branch: ^a
        assert isinstance(ast.branches[0], Seq)
        assert len(ast.branches[0].parts) == 2
        assert isinstance(ast.branches[0].parts[0], Anchor)
        assert ast.branches[0].parts[0].at == "Start"
        assert isinstance(ast.branches[0].parts[1], Lit)
        # Second branch: b$
        assert isinstance(ast.branches[1], Seq)
        assert len(ast.branches[1].parts) == 2
        assert isinstance(ast.branches[1].parts[0], Lit)
        assert isinstance(ast.branches[1].parts[1], Anchor)
        assert ast.branches[1].parts[1].at == "End"

    def test_anchors_in_group_alternation(self):
        """
        Tests anchors in grouped alternation: (^|$)
        """
        _flags, ast = parse("(^|$)")
        assert isinstance(ast, Group)
        assert ast.capturing is True
        assert isinstance(ast.body, Alt)
        assert len(ast.body.branches) == 2
        assert isinstance(ast.body.branches[0], Anchor)
        assert ast.body.branches[0].at == "Start"
        assert isinstance(ast.body.branches[1], Anchor)
        assert ast.body.branches[1].at == "End"

    def test_word_boundary_in_alternation(self):
        """
        Tests word boundary in alternation: \\ba|\\bb
        """
        _flags, ast = parse(r"\ba|\bb")
        assert isinstance(ast, Alt)
        assert len(ast.branches) == 2
        # First branch: \ba
        assert isinstance(ast.branches[0], Seq)
        assert len(ast.branches[0].parts) == 2
        assert isinstance(ast.branches[0].parts[0], Anchor)
        assert ast.branches[0].parts[0].at == "WordBoundary"
        # Second branch: \bb
        assert isinstance(ast.branches[1], Seq)
        assert len(ast.branches[1].parts) == 2
        assert isinstance(ast.branches[1].parts[0], Anchor)
        assert ast.branches[1].parts[0].at == "WordBoundary"


class TestCategoryGAnchorsInAtomicGroups:
    """
    Tests for anchors inside atomic groups.
    """

    def test_start_anchor_in_atomic_group(self):
        """
        Tests start anchor in atomic group: (?>^a)
        """
        _flags, ast = parse("(?>^a)")
        assert isinstance(ast, Group)
        assert ast.atomic is True
        assert isinstance(ast.body, Seq)
        assert len(ast.body.parts) == 2
        assert isinstance(ast.body.parts[0], Anchor)
        assert ast.body.parts[0].at == "Start"
        assert isinstance(ast.body.parts[1], Lit)

    def test_end_anchor_in_atomic_group(self):
        """
        Tests end anchor in atomic group: (?>a$)
        """
        _flags, ast = parse("(?>a$)")
        assert isinstance(ast, Group)
        assert ast.atomic is True
        assert isinstance(ast.body, Seq)
        assert len(ast.body.parts) == 2
        assert isinstance(ast.body.parts[0], Lit)
        assert isinstance(ast.body.parts[1], Anchor)
        assert ast.body.parts[1].at == "End"

    def test_word_boundary_in_atomic_group(self):
        """
        Tests word boundary in atomic group: (?>\\ba)
        """
        _flags, ast = parse(r"(?>\ba)")
        assert isinstance(ast, Group)
        assert ast.atomic is True
        assert isinstance(ast.body, Seq)
        assert len(ast.body.parts) == 2
        assert isinstance(ast.body.parts[0], Anchor)
        assert ast.body.parts[0].at == "WordBoundary"
        assert isinstance(ast.body.parts[1], Lit)


class TestCategoryHWordBoundaryEdgeCases:
    """
    Tests for word boundary anchors in various contexts.
    """

    def test_word_boundary_with_non_word_char(self):
        """
        Tests word boundary with non-word character: \\b.\\b
        The dot matches any character, boundaries on both sides.
        """
        _flags, ast = parse(r"\b.\b")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Anchor)
        assert ast.parts[0].at == "WordBoundary"
        assert isinstance(ast.parts[1], Dot)
        assert isinstance(ast.parts[2], Anchor)
        assert ast.parts[2].at == "WordBoundary"

    def test_word_boundary_with_digit(self):
        """
        Tests word boundary with digit: \\b\\d\\b
        """
        _flags, ast = parse(r"\b\d\b")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Anchor)
        assert ast.parts[0].at == "WordBoundary"
        assert isinstance(ast.parts[1], CharClass)
        assert isinstance(ast.parts[2], Anchor)
        assert ast.parts[2].at == "WordBoundary"

    def test_not_word_boundary_usage(self):
        """
        Tests not-word-boundary: \\Ba\\B
        """
        _flags, ast = parse(r"\Ba\B")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Anchor)
        assert ast.parts[0].at == "NotWordBoundary"
        assert isinstance(ast.parts[1], Lit)
        assert ast.parts[1].value == "a"
        assert isinstance(ast.parts[2], Anchor)
        assert ast.parts[2].at == "NotWordBoundary"


class TestCategoryIMultipleAnchorTypes:
    """
    Tests for patterns combining different anchor types.
    """

    def test_start_and_end_anchors(self):
        """
        Tests both start and end anchors: ^abc$
        Already covered but confirming as typical case.
        """
        _flags, ast = parse("^abc$")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Anchor)
        assert ast.parts[0].at == "Start"
        assert isinstance(ast.parts[1], Lit)
        assert ast.parts[1].value == "abc"
        assert isinstance(ast.parts[2], Anchor)
        assert ast.parts[2].at == "End"

    def test_absolute_and_line_anchors(self):
        """
        The trailing `\z` in this sequence is an unknown escape sequence and
        should raise a ParseError.
        """
        with pytest.raises(ParseError, match=r"Unknown escape sequence \\z"):
            parse(r"\A^abc$\z")

    def test_word_boundaries_and_line_anchors(self):
        """
        Tests word boundaries with line anchors: ^\\ba\\b$
        """
        _flags, ast = parse(r"^\ba\b$")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 5
        assert isinstance(ast.parts[0], Anchor)
        assert ast.parts[0].at == "Start"
        assert isinstance(ast.parts[1], Anchor)
        assert ast.parts[1].at == "WordBoundary"
        assert isinstance(ast.parts[2], Lit)
        assert ast.parts[2].value == "a"
        assert isinstance(ast.parts[3], Anchor)
        assert ast.parts[3].at == "WordBoundary"
        assert isinstance(ast.parts[4], Anchor)
        assert ast.parts[4].at == "End"


class TestCategoryJAnchorsWithQuantifiers:
    """
    Tests confirming that anchors themselves cannot be quantified.
    """

    def test_anchor_not_quantified_directly(self):
        """
        Tests that ^* raises an error (cannot quantify anchor).
        """
        with pytest.raises(ParseError, match="Cannot quantify anchor"):
            parse("^*")

    def test_end_anchor_followed_by_quantifier(self):
        """
        Tests $+ raises an error (cannot quantify anchor).
        """
        with pytest.raises(ParseError, match="Cannot quantify anchor"):
            parse("$+")
