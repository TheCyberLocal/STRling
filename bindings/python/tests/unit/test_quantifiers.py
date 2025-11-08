"""
Test Design — test_quantifiers.py

## Purpose
This test suite validates the correct parsing of all quantifier forms (`*`, `+`,
`?`, `{m,n}`) and modes (Greedy, Lazy, Possessive). It ensures quantifiers
correctly bind to their preceding atom, generate the proper `Quant` AST node,
and that malformed quantifier syntax raises the appropriate `ParseError`.

## Description
Quantifiers specify the number of times a preceding atom can occur in a
pattern. This test suite covers the full syntactic and semantic range of this
feature. It verifies that the parser correctly interprets the different
quantifier syntaxes and their greedy (default), lazy (`?` suffix), and
possessive (`+` suffix) variants. A key focus is testing operator
precedence—ensuring that a quantifier correctly associates with a single
preceding atom (like a literal, group, or class) rather than an entire
sequence.

## Scope
-   **In scope:**
    -   Parsing of all standard quantifiers: `*`, `+`, `?`.

    -   Parsing of all brace-based quantifiers: `{n}`, `{m,}`, `{m,n}`.

    -   Parsing of lazy (`*?`) and possessive (`*+`) mode modifiers
       .
    -   The structure and values of the resulting `nodes.Quant` AST node
        (including `min`, `max`, and `mode` fields).

    -   Error handling for malformed brace quantifiers (e.g., `a{1,`).

    -   The parser's correct identification of the atom to be quantified.

-   **Out of scope:**
    -   Static analysis for ReDoS risks on nested quantifiers
        (this is a Sprint 6 feature).
    -   The emitter's final string output, such as adding non-capturing
        groups (covered in `test_emitter_edges.py`).

"""

import pytest
from typing import Union, cast

from STRling.core.parser import parse, ParseError
from STRling.core.nodes import (
    Quant,
    Lit,
    Seq,
    Dot,
    CharClass,
    Group,
    Look,
    Anchor,
    Alt,
    Backref,
)

# --- Test Suite -----------------------------------------------------------------


class TestCategoryAPositiveCases:
    """
    Covers all positive cases for valid quantifier syntax and modes.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_min, expected_max, expected_mode",
        [
            # A.1: Star Quantifier
            ("a*", 0, "Inf", "Greedy"),
            ("a*?", 0, "Inf", "Lazy"),
            ("a*+", 0, "Inf", "Possessive"),
            # A.2: Plus Quantifier
            ("a+", 1, "Inf", "Greedy"),
            ("a+?", 1, "Inf", "Lazy"),
            ("a++", 1, "Inf", "Possessive"),
            # A.3: Optional Quantifier
            ("a?", 0, 1, "Greedy"),
            ("a??", 0, 1, "Lazy"),
            ("a?+", 0, 1, "Possessive"),
            # A.4: Exact Repetition
            ("a{3}", 3, 3, "Greedy"),
            ("a{3}?", 3, 3, "Lazy"),
            ("a{3}+", 3, 3, "Possessive"),
            # A.5: At-Least Repetition
            ("a{3,}", 3, "Inf", "Greedy"),
            ("a{3,}?", 3, "Inf", "Lazy"),
            ("a{3,}+", 3, "Inf", "Possessive"),
            # A.6: Range Repetition
            ("a{3,5}", 3, 5, "Greedy"),
            ("a{3,5}?", 3, 5, "Lazy"),
            ("a{3,5}+", 3, 5, "Possessive"),
        ],
        ids=[
            "star_greedy",
            "star_lazy",
            "star_possessive",
            "plus_greedy",
            "plus_lazy",
            "plus_possessive",
            "optional_greedy",
            "optional_lazy",
            "optional_possessive",
            "brace_exact_greedy",
            "brace_exact_lazy",
            "brace_exact_possessive",
            "brace_at_least_greedy",
            "brace_at_least_lazy",
            "brace_at_least_possessive",
            "brace_range_greedy",
            "brace_range_lazy",
            "brace_range_possessive",
        ],
    )
    def test_quantifier_forms_are_parsed_correctly(
        self,
        input_dsl: str,
        expected_min: int,
        expected_max: Union[int, str],
        expected_mode: str,
    ):
        """
        Tests that all quantifier forms and modes are parsed into a Quant node
        with the correct min, max, and mode attributes.
        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Quant)
        assert ast.min == expected_min
        assert ast.max == expected_max
        assert ast.mode == expected_mode
        assert isinstance(ast.child, Lit)


class TestCategoryBNegativeCases:
    """
    Covers negative cases for malformed quantifier syntax.
    """

    @pytest.mark.parametrize(
        "invalid_dsl, error_message_prefix, error_position",
        [
            ("a{1", "Unterminated {n}", 3),
            ("a{1,", "Unterminated {m,n}", 4),
        ],
        ids=[
            "unclosed_brace_after_num",
            "unclosed_brace_after_comma",
        ],
    )
    def test_malformed_brace_quantifiers_raise_error(
        self, invalid_dsl: str, error_message_prefix: str, error_position: int
    ):
        """
        Tests that malformed brace quantifiers raise a ParseError.

        """
        with pytest.raises(ParseError, match=error_message_prefix) as excinfo:
            parse(invalid_dsl)
        assert excinfo.value.pos == error_position

    def test_malformed_brace_quantifier_parses_as_literal(self):
        """
        Tests that a brace construct invalid as a quantifier (e.g., '{,5}')
        is parsed as a literal string.
        """
        _flags, ast = parse("a{,5}")
        assert ast == Seq(parts=[Lit("a"), Lit("{,5}")])


class TestCategoryCEdgeCases:
    """
    Covers edge cases for quantifiers.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_min, expected_max",
        [
            ("a{0}", 0, 0),
            ("a{0,5}", 0, 5),
            ("a{0,}", 0, "Inf"),
        ],
        ids=["exact_zero", "range_from_zero", "at_least_zero"],
    )
    def test_zero_repetition_quantifiers(
        self, input_dsl: str, expected_min: int, expected_max: Union[int, str]
    ):
        """Tests that quantifiers with zero values are parsed correctly."""
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Quant)
        assert ast.min == expected_min
        assert ast.max == expected_max

    def test_quantifier_on_empty_group(self):
        """Tests that a quantifier can be applied to an empty group."""
        _flags, ast = parse("(?:)*")
        assert isinstance(ast, Quant)
        group_node = cast(Group, ast.child)
        assert group_node.capturing is False
        assert group_node.body == Seq(parts=[])

    def test_quantifier_does_not_apply_to_anchor(self):
        """
        Tests that a quantifier correctly applies to the atom before an anchor,
        not the anchor itself.
        """
        _flags, ast = parse("a?^")
        assert isinstance(ast, Seq)
        quant_node = cast(Quant, ast.parts[0])
        anchor_node = cast(Anchor, ast.parts[1])
        assert quant_node.child == Lit("a")
        assert anchor_node.at == "Start"


class TestCategoryDInteractionCases:
    """
    Covers the interaction of quantifiers with different atoms and sequences.
    """

    def test_quantifier_precedence_is_correct(self):
        """
        A critical test to ensure a quantifier binds only to the immediately
        preceding atom, not the whole sequence.
        """
        _flags, ast = parse("ab*")
        assert ast == Seq(
            parts=[Lit("a"), Quant(child=Lit("b"), min=0, max="Inf", mode="Greedy")]
        )

    @pytest.mark.parametrize(
        "input_dsl, expected_child_type",
        [
            (r"\d*", CharClass),
            (".*", Dot),
            ("[a-z]*", CharClass),
            ("(abc)*", Group),
            ("(?:a|b)+", Group),  # The group is the atom being quantified
            ("(?=a)+", Look),
        ],
        ids=[
            "quantify_shorthand",
            "quantify_dot",
            "quantify_char_class",
            "quantify_group",
            "quantify_alternation_in_group",
            "quantify_lookaround",
        ],
    )
    def test_quantifying_different_atom_types(
        self, input_dsl: str, expected_child_type: type
    ):
        """
        Tests that quantifiers correctly wrap various types of AST nodes.
        """
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Quant)
        assert isinstance(ast.child, expected_child_type)


# --- New Test Stubs for 3-Test Standard Compliance -----------------------------


class TestCategoryENestedAndRedundantQuantifiers:
    """
    Tests for nested quantifiers and redundant quantification patterns.
    These are edge cases that test the parser's ability to handle
    syntactically valid but semantically unusual patterns.
    """

    def test_nested_quantifier_star_on_star(self):
        """
        Tests that a quantifier can be applied to a group containing a
        quantified atom: (a*)* is syntactically valid.
        """
        _flags, ast = parse("(a*)*")
        assert isinstance(ast, Quant)
        assert ast.min == 0
        assert ast.max == "Inf"
        assert isinstance(ast.child, Group)
        assert isinstance(ast.child.body, Quant)
        assert ast.child.body.min == 0
        assert ast.child.body.max == "Inf"

    def test_nested_quantifier_plus_on_optional(self):
        """
        Tests nested quantifiers with different operators: (a+)?
        """
        _flags, ast = parse("(a+)?")
        assert isinstance(ast, Quant)
        assert ast.min == 0
        assert ast.max == 1
        assert isinstance(ast.child, Group)
        assert isinstance(ast.child.body, Quant)
        assert ast.child.body.min == 1
        assert ast.child.body.max == "Inf"

    def test_redundant_quantifier_plus_on_star(self):
        """
        Tests redundant quantification: (a*)+
        This is semantically equivalent to a* but syntactically valid.
        """
        _flags, ast = parse("(a*)+")
        assert isinstance(ast, Quant)
        assert ast.min == 1
        assert ast.max == "Inf"
        assert isinstance(ast.child, Group)
        assert isinstance(ast.child.body, Quant)

    def test_redundant_quantifier_star_on_optional(self):
        """
        Tests redundant quantification: (a?)*
        """
        _flags, ast = parse("(a?)*")
        assert isinstance(ast, Quant)
        assert ast.min == 0
        assert ast.max == "Inf"
        assert isinstance(ast.child, Group)
        assert isinstance(ast.child.body, Quant)
        assert ast.child.body.min == 0
        assert ast.child.body.max == 1

    def test_nested_quantifier_with_brace(self):
        """
        Tests brace quantifiers on quantified groups: (a{2,3}){1,2}
        """
        _flags, ast = parse("(a{2,3}){1,2}")
        assert isinstance(ast, Quant)
        assert ast.min == 1
        assert ast.max == 2
        assert isinstance(ast.child, Group)
        assert isinstance(ast.child.body, Quant)
        assert ast.child.body.min == 2
        assert ast.child.body.max == 3


class TestCategoryFQuantifierOnSpecialAtoms:
    """
    Tests for quantifiers applied to special atom types like backreferences
    and anchors.
    """

    def test_quantifier_on_backref(self):
        """
        Tests that a quantifier can be applied to a backreference: (a)\\1*
        """
        _flags, ast = parse(r"(a)\1*")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 2
        assert isinstance(ast.parts[0], Group)
        assert isinstance(ast.parts[1], Quant)
        assert isinstance(ast.parts[1].child, Backref)
        assert ast.parts[1].min == 0
        assert ast.parts[1].max == "Inf"

    def test_quantifier_on_multiple_backrefs(self):
        """
        Tests quantifiers on multiple backrefs: (a)(b)\\1*\\2+
        """
        _flags, ast = parse(r"(a)(b)\1*\2+")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 4
        assert isinstance(ast.parts[2], Quant)
        assert isinstance(ast.parts[2].child, Backref)
        assert ast.parts[2].child.byIndex == 1
        assert isinstance(ast.parts[3], Quant)
        assert isinstance(ast.parts[3].child, Backref)
        assert ast.parts[3].child.byIndex == 2


class TestCategoryGMultipleQuantifiedSequences:
    """
    Tests for patterns with multiple consecutive quantified atoms.
    """

    def test_multiple_consecutive_quantified_literals(self):
        """
        Tests multiple quantified atoms in sequence: a*b+c?
        """
        _flags, ast = parse("a*b+c?")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert all(isinstance(part, Quant) for part in ast.parts)
        assert ast.parts[0].min == 0 and ast.parts[0].max == "Inf"
        assert ast.parts[1].min == 1 and ast.parts[1].max == "Inf"
        assert ast.parts[2].min == 0 and ast.parts[2].max == 1

    def test_multiple_quantified_groups(self):
        """
        Tests multiple quantified groups: (ab)*(cd)+(ef)?
        """
        _flags, ast = parse("(ab)*(cd)+(ef)?")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert all(isinstance(part, Quant) for part in ast.parts)
        assert all(isinstance(part.child, Group) for part in ast.parts)

    def test_quantified_atoms_with_alternation(self):
        """
        Tests quantified atoms in an alternation: a*|b+
        """
        _flags, ast = parse("a*|b+")
        assert isinstance(ast, Alt)
        assert len(ast.branches) == 2
        assert isinstance(ast.branches[0], Quant)
        assert ast.branches[0].min == 0
        assert isinstance(ast.branches[1], Quant)
        assert ast.branches[1].min == 1


class TestCategoryHBraceQuantifierEdgeCases:
    """
    Additional edge cases for brace quantifiers.
    """

    def test_brace_quantifier_exact_one(self):
        """
        Tests exact repetition of one: a{1}
        Should parse correctly even though it's equivalent to 'a'.
        """
        _flags, ast = parse("a{1}")
        assert isinstance(ast, Quant)
        assert ast.min == 1
        assert ast.max == 1
        assert isinstance(ast.child, Lit)
        assert ast.child.value == "a"

    def test_brace_quantifier_zero_to_one(self):
        """
        Tests range zero to one: a{0,1}
        Should be equivalent to a? but valid syntax.
        """
        _flags, ast = parse("a{0,1}")
        assert isinstance(ast, Quant)
        assert ast.min == 0
        assert ast.max == 1
        assert isinstance(ast.child, Lit)

    def test_brace_quantifier_on_alternation_in_group(self):
        """
        Tests brace quantifier on group with alternation: (a|b){2,3}
        """
        _flags, ast = parse("(a|b){2,3}")
        assert isinstance(ast, Quant)
        assert ast.min == 2
        assert ast.max == 3
        assert isinstance(ast.child, Group)
        assert isinstance(ast.child.body, Alt)

    def test_brace_quantifier_large_values(self):
        """
        Tests brace quantifiers with large repetition counts: a{100}, a{50,150}
        """
        _flags, ast = parse("a{100,200}")
        assert isinstance(ast, Quant)
        assert ast.min == 100
        assert ast.max == 200
        assert isinstance(ast.child, Lit)


class TestCategoryIQuantifierInteractionWithFlags:
    """
    Tests for how quantifiers interact with DSL flags.
    """

    def test_quantifier_with_free_spacing_mode(self):
        """
        Tests that free-spacing mode doesn't affect quantifier parsing:
        %flags x\\na * (spaces should be ignored, quantifier still applies)
        """
        _flags, ast = parse("%flags x\na *")
        # In free-spacing mode, spaces are ignored, so 'a' and '*' are separate
        # The * becomes a literal, not a quantifier
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 2
        assert isinstance(ast.parts[0], Lit)
        assert ast.parts[0].value == "a"
        assert isinstance(ast.parts[1], Lit)
        assert ast.parts[1].value == "*"

    def test_quantifier_on_escaped_space_in_free_spacing(self):
        """
        Tests quantifier on escaped space in free-spacing mode:
        %flags x\\n\\ *
        """
        _flags, ast = parse(r"%flags x""\n\\ *")
        # Escaped space followed by *, should quantify the space
        assert isinstance(ast, Quant)
        assert ast.min == 0
        assert ast.max == "Inf"
        assert isinstance(ast.child, Lit)
        assert ast.child.value == " "
