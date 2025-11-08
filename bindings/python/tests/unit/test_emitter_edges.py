r"""
Test Design — unit/test_emitter_edges.py

## Purpose
This test suite validates the logic of the PCRE2 emitter, focusing on its
specific responsibilities: correct character escaping, shorthand optimizations,
flag prefix generation, and the critical automatic-grouping logic required to
preserve operator precedence.

## Description
The emitter (`pcre2.py`) is the final backend stage in the STRling compiler
pipeline. It translates the clean, language-agnostic Intermediate
Representation (IR) into a syntactically correct PCRE2 regex string. This suite
does not test the IR's correctness but verifies that a given valid IR tree is
always transformed into the correct and most efficient string representation,
with a heavy focus on edge cases where incorrect output could alter a pattern's
meaning.

## Scope
-   **In scope:**
    -   The emitter's character escaping logic, both for general literals and
        within character classes.
    -   Shorthand optimizations, such as converting `IRCharClass` nodes into
        `\d` or `\P{Letter}` where appropriate.
    -   The automatic insertion of non-capturing groups `(?:...)` to maintain
        correct precedence.
    -   Generation of the flag prefix `(?imsux)` based on the provided `Flags`
        object.
    -   Correct string generation for all PCRE2-supported extension features.

-   **Out of scope:**
    -   The correctness of the input IR tree (this is covered by
        `test_ir_compiler.py`).
    -   The runtime behavior of the generated regex string in a live PCRE2
        engine (this is covered by end-to-end and conformance tests).

"""

import pytest
from typing import List

from STRling.emitters.pcre2 import emit
from STRling.core.nodes import Flags
from STRling.core.ir import (
    IRLit,
    IRCharClass,
    IRClassItem,
    IRClassLiteral,
    IRClassEscape,
    IRQuant,
    IRSeq,
    IRAlt,
    IRDot,
    IRGroup,
    IRBackref,
    IRAnchor,
    IROp,
)

# Add these imports at the top if not already present
import re
from STRling.emitters.pcre2 import _escape_literal, _escape_class_char

# Add these new test functions within a test class (e.g., TestCategoryAEscapingLogic)
# or as standalone test functions in the file.

# --- Temporary Tests for _escape_literal (outside class) ---


def test_escape_literal_dot():
    """Verify how _escape_literal handles '.'"""
    assert _escape_literal(".") == re.escape(".")  # Expected: r'\.'


def test_escape_literal_backslash():
    """Verify how _escape_literal handles '\'"""
    assert _escape_literal("\\") == re.escape("\\")  # Expected: r'\\'


def test_escape_literal_bracket():
    """Verify how _escape_literal handles '['"""
    assert _escape_literal("[") == re.escape("[")  # Expected: r'\['


def test_escape_literal_brace():
    """Verify how _escape_literal handles '{'"""
    assert _escape_literal("{") == re.escape("{")  # Expected: r'\{'


def test_escape_literal_plain():
    """Verify how _escape_literal handles a plain char 'a'"""
    assert _escape_literal("a") == re.escape("a")  # Expected: 'a'


# --- Temporary Tests for _escape_class_char (inside class) ---


def test_escape_class_char_closing_bracket():
    """Verify how _escape_class_char handles ']' inside class"""
    assert _escape_class_char("]") == r"\]"  # Expected: \]


def test_escape_class_char_backslash():
    """Verify how _escape_class_char handles '\' inside class"""
    assert _escape_class_char("\\") == r"\\"  # Expected: \\


def test_escape_class_char_hyphen():
    """Verify how _escape_class_char handles '-' inside class"""
    # Assuming _emit_class handles placement, this should only escape if needed
    # Let's test the current function's direct output
    assert _escape_class_char("-") == r"\-"  # Expected based on last attempt: \-


def test_escape_class_char_caret():
    """Verify how _escape_class_char handles '^' inside class"""
    # We always escape ^ for safety, even though it's only special at the start
    assert _escape_class_char("^") == r"\^"  # Expected: \^


def test_escape_class_char_opening_bracket():
    """Verify how _escape_class_char handles '[' inside class"""
    # Should be literal inside a class
    assert _escape_class_char("[") == "["  # Expected: [ (unescaped)


def test_escape_class_char_dot():
    """Verify how _escape_class_char handles '.' inside class"""
    # Should be literal
    assert _escape_class_char(".") == "."  # Expected: . (unescaped)


def test_escape_class_char_newline():
    """Verify how _escape_class_char handles '\n' inside class"""
    assert _escape_class_char("\n") == r"\n"  # Expected: \n


# --- Test Suite -----------------------------------------------------------------


class TestCategoryAEscapingLogic:
    """
    Covers the emitter's character escaping logic.
    """

    def test_literal_metacharacters_are_escaped(self):
        """
        Tests that all PCRE2 metacharacters are escaped when in an IRLit node.
        """
        metachars = ".^$|()?*+{}[]\\"
        expected = r"\.\^\$\|\(\)\?\*\+\{\}\[\]\\"
        assert emit(IRLit(metachars)) == expected

    def test_char_class_metacharacters_are_escaped(self):
        """
        Tests that special characters inside a character class are escaped.
        """
        metachars = "]-^"
        expected = r"[\]\-\^]"
        items: List[IRClassItem] = [IRClassLiteral(c) for c in metachars]
        assert emit(IRCharClass(negated=False, items=items)) == expected


class TestCategoryBShorthandOptimizations:
    """
    Covers the emitter's logic for optimizing character classes.
    """

    @pytest.mark.parametrize(
        "ir_node, expected_str",
        [
            (IRCharClass(negated=False, items=[IRClassEscape("d")]), r"\d"),
            (IRCharClass(negated=True, items=[IRClassEscape("d")]), r"\D"),
            (IRCharClass(negated=False, items=[IRClassEscape("p", "L")]), r"\p{L}"),
            (IRCharClass(negated=True, items=[IRClassEscape("p", "L")]), r"\P{L}"),
            (IRCharClass(negated=False, items=[IRClassEscape("S")]), r"\S"),
            (IRCharClass(negated=True, items=[IRClassEscape("S")]), r"\s"),
        ],
        ids=[
            "positive_d_to_shorthand",
            "negated_d_to_D_shorthand",
            "positive_p_to_shorthand",
            "negated_p_to_P_shorthand",
            "positive_neg_shorthand_S",
            "negated_neg_shorthand_S_to_s",
        ],
    )
    def test_shorthand_optimizations_are_applied(
        self, ir_node: IRCharClass, expected_str: str
    ):
        """
        Tests that single-item character classes are collapsed into their
        shorthand equivalents.
        """
        assert emit(ir_node) == expected_str

    def test_optimization_is_not_applied_for_multi_item_class(self):
        """
        Tests that the shorthand optimization is correctly skipped for a class
        with more than one item.
        """
        ir_node = IRCharClass(
            negated=False, items=[IRClassEscape("d"), IRClassLiteral("_")]
        )
        assert emit(ir_node) == r"[\d_]"


class TestCategoryCAutomaticGrouping:
    """
    Covers the critical logic for preserving operator precedence.
    """

    @pytest.mark.parametrize(
        "ir_node, expected_str",
        [
            (IRQuant(child=IRLit("ab"), min=0, max="Inf", mode="Greedy"), "(?:ab)*"),
            (IRQuant(child=IRSeq([IRLit("a")]), min=1, max="Inf", mode="Greedy"), "a+"),
            (IRSeq([IRLit("a"), IRAlt([IRLit("b"), IRLit("c")])]), "a(?:b|c)"),
        ],
        ids=[
            "quantified_multichar_literal",
            "quantified_single_item_sequence",
            "alternation_in_sequence",
        ],
    )
    def test_grouping_is_added_when_needed(self, ir_node: IROp, expected_str: str):
        """
        Tests that non-capturing groups are added to preserve precedence.
        """
        assert emit(ir_node) == expected_str

    @pytest.mark.parametrize(
        "ir_node, expected_str",
        [
            (
                IRQuant(
                    child=IRCharClass(False, [IRClassLiteral("a")]),
                    min=0,
                    max="Inf",
                    mode="Greedy",
                ),
                "[a]*",
            ),
            (IRQuant(child=IRDot(), min=1, max="Inf", mode="Greedy"), ".+"),
            (
                IRQuant(child=IRGroup(True, IRLit("a")), min=0, max=1, mode="Greedy"),
                "(a)?",
            ),
        ],
        ids=["quantified_char_class", "quantified_dot", "quantified_group"],
    )
    def test_grouping_is_not_added_unnecessarily(
        self, ir_node: IROp, expected_str: str
    ):
        """
        Tests that quantifiers on single atoms do not get extra grouping.
        """
        assert emit(ir_node) == expected_str


class TestCategoryDFlagsAndEmitterDirectives:
    """
    Covers flag prefixes and other PCRE2-specific syntax.
    """

    @pytest.mark.parametrize(
        "flags, expected_prefix",
        [
            (Flags(ignoreCase=True, multiline=True), "(?im)"),
            (Flags(dotAll=True, unicode=True, extended=True), "(?sux)"),
            (Flags(), ""),
            (None, ""),
        ],
        ids=["im_flags", "sux_flags", "default_flags", "no_flags_object"],
    )
    def test_flag_prefix_generation(self, flags: Flags, expected_prefix: str):
        """Tests that the correct (?...) prefix is generated from a Flags object."""
        assert emit(IRLit("a"), flags) == expected_prefix + "a"

    def test_named_group_and_backref_syntax(self):
        """Tests that PCRE2-specific named group syntax is generated."""
        ir = IRSeq(
            [
                IRGroup(True, IRLit("a"), name="x"),
                IRBackref(byName="x"),
            ]
        )
        assert emit(ir) == r"(?<x>a)\k<x>"


class TestCategoryEExtensionFeatures:
    """
    Covers the emission of PCRE2 extension features.
    """

    @pytest.mark.parametrize(
        "ir_node, expected_str",
        [
            (IRGroup(False, IRQuant(IRLit("a"), 1, "Inf", "Greedy"), atomic=True), "(?>a+)"),
            (IRQuant(IRLit("a"), 0, "Inf", "Possessive"), "a*+"),
            (IRQuant(IRCharClass(False, []), 1, "Inf", "Possessive"), "[]++"),
            (IRAnchor("AbsoluteStart"), r"\A"),
        ],
        ids=[
            "atomic_group",
            "possessive_star",
            "possessive_plus",
            "absolute_start_anchor",
        ],
    )
    def test_extension_features_are_emitted_correctly(
        self, ir_node: IROp, expected_str: str
    ):
        """
        Tests that extension features like atomic groups and possessive
        quantifiers are emitted with the correct PCRE2 syntax.
        """
        assert emit(ir_node) == expected_str
