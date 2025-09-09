r"""
Test Design — test_groups_backrefs_lookarounds.py

## Purpose
This test suite validates the parser's handling of all grouping constructs,
backreferences, and lookarounds. It ensures that different group types are
parsed correctly into their corresponding AST nodes, that backreferences are
validated against defined groups, that lookarounds are constructed properly,
and that all syntactic errors raise the correct `ParseError`.

## Description
Groups, backreferences, and lookarounds are the primary features for defining
structure and context within a pattern.
-   **Groups** `(...)` are used to create sub-patterns, apply quantifiers to
    sequences, and capture text for later use.
-   **Backreferences** `\1`, `\k<name>` match the exact text previously
    captured by a group.
-   **Lookarounds** `(?=...)`, `(?<=...)`, etc., are zero-width assertions that
    check for patterns before or after the current position without consuming
    characters.

This suite verifies that the parser correctly implements the rich syntax and
validation rules for these powerful features.

## Scope
-   **In scope:**
    -   Parsing of all group types: capturing `()`, non-capturing `(?:...)`,
        named `(?<name>...)`, and atomic `(?>...)`.
    -   Parsing of numeric (`\1`) and named (`\k<name>`) backreferences.

    -   Validation of backreferences (e.g., ensuring no forward references).

    -   Parsing of all four lookaround types: positive/negative lookahead and
        positive/negative lookbehind.
    -   Error handling for unterminated constructs and invalid backreferences.

    -   The structure of the resulting `nodes.Group`, `nodes.Backref`, and
        `nodes.Look` AST nodes.
-   **Out of scope:**
    -   Quantification of these constructs (covered in `test_quantifiers.py`).

    -   Semantic validation of lookbehind contents (e.g., the fixed-length
        requirement).
    -   Emitter-specific syntax transformations (e.g., Python's `(?P<name>...)`).

"""

import pytest
from typing import Optional, cast

from STRling.core.parser import parse, ParseError
from STRling.core.nodes import Group, Backref, Look, Seq, Lit, Quant

# --- Test Suite -----------------------------------------------------------------


class TestCategoryAPositiveCases:
    """
    Covers all positive cases for valid group, backreference, and lookaround syntax.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_capturing, expected_name, expected_atomic",
        [
            ("(a)", True, None, None),
            ("(?:a)", False, None, None),
            ("(?<name>a)", True, "name", None),
            ("(?>a)", False, None, True),
        ],
        ids=["capturing", "non_capturing", "named_capturing", "atomic_ext"],
    )
    def test_group_types_are_parsed_correctly(
        self,
        input_dsl: str,
        expected_capturing: bool,
        expected_name: Optional[str],
        expected_atomic: Optional[bool],
    ):
        """Tests that various group types are parsed with the correct attributes."""
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Group)
        assert ast.capturing == expected_capturing
        assert ast.name == expected_name
        assert ast.atomic == expected_atomic
        assert isinstance(ast.body, Lit)

    @pytest.mark.parametrize(
        "input_dsl, expected_backref",
        [
            (r"(a)\1", Backref(byIndex=1)),
            (r"(?<A>a)\k<A>", Backref(byName="A")),
        ],
        ids=["numeric_backref", "named_backref"],
    )
    def test_backreferences_are_parsed_correctly(
        self, input_dsl: str, expected_backref: Backref
    ):
        """Tests that valid backreferences are parsed into the correct Backref node."""
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Seq)
        assert ast.parts[1] == expected_backref

    @pytest.mark.parametrize(
        "input_dsl, expected_dir, expected_neg",
        [
            ("a(?=b)", "Ahead", False),
            ("a(?!b)", "Ahead", True),
            ("(?<=a)b", "Behind", False),
            ("(?<!a)b", "Behind", True),
        ],
        ids=["lookahead_pos", "lookahead_neg", "lookbehind_pos", "lookbehind_neg"],
    )
    def test_lookarounds_are_parsed_correctly(
        self, input_dsl: str, expected_dir: str, expected_neg: bool
    ):
        """Tests that all four lookaround types are parsed correctly."""
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Seq)
        look_node = ast.parts[1] if expected_dir == "Ahead" else ast.parts[0]
        assert isinstance(look_node, Look)
        assert look_node.dir == expected_dir
        assert look_node.neg == expected_neg


class TestCategoryBNegativeCases:
    """
    Covers all negative cases for malformed or invalid syntax.
    """

    @pytest.mark.parametrize(
        "invalid_dsl, error_message_prefix, error_position",
        [
            # B.1: Unterminated constructs
            ("(a", "Unterminated group", 2),
            ("(?<name", "Unterminated group name", 8),
            ("(?=a", "Unterminated lookahead", 4),
            (r"\k<A", "Unterminated named backref", 4),
            # B.2: Invalid backreferences
            (r"\k<A>(?<A>a)", "Backreference to undefined group <A>", 0),
            (r"\2(a)(b)", "Backreference to undefined group \\2", 0),
            (r"(a)\2", "Backreference to undefined group \\2", 3),
            # B.3: Invalid syntax
            ("(?i)a", "Inline modifiers", 1),
        ],
        ids=[
            "unterminated_group",
            "unterminated_named_group",
            "unterminated_lookahead",
            "unterminated_named_backref",
            "forward_ref_by_name",
            "forward_ref_by_index",
            "nonexistent_ref_by_index",
            "disallowed_inline_modifier",
        ],
    )
    def test_invalid_syntax_raises_parse_error(
        self, invalid_dsl: str, error_message_prefix: str, error_position: int
    ):
        """
        Tests that invalid syntax for groups and backrefs raises a ParseError.
        """
        with pytest.raises(ParseError, match=error_message_prefix) as excinfo:
            parse(invalid_dsl)
        assert excinfo.value.pos == error_position

    @pytest.mark.xfail(reason="Parser does not yet check for duplicate group names.")
    def test_duplicate_group_name_raises_error(self):
        """
        Tests that duplicate group names raise a semantic error.

        """
        # This should ideally raise a ValidationError, not a ParseError.
        with pytest.raises(Exception, match="Duplicate group name"):
            parse("(?<a>x)(?<a>y)")


class TestCategoryCEdgeCases:
    """
    Covers edge cases for groups and backreferences.
    """

    @pytest.mark.parametrize(
        "input_dsl, expected_capturing, expected_name",
        [
            ("()", True, None),
            ("(?:)", False, None),
            ("(?<A>)", True, "A"),
        ],
        ids=["empty_capturing", "empty_noncapturing", "empty_named"],
    )
    def test_empty_groups_are_parsed_correctly(
        self, input_dsl: str, expected_capturing: bool, expected_name: Optional[str]
    ):
        """Tests that empty groups parse into a Group node with an empty body."""
        _flags, ast = parse(input_dsl)
        assert isinstance(ast, Group)
        assert ast.capturing == expected_capturing
        assert ast.name == expected_name
        assert ast.body == Seq(parts=[])

    def test_backreference_to_optional_group_is_valid_syntax(self):
        """
        Tests that a backreference to an optional group is syntactically valid.
        """
        _flags, ast = parse(r"(a)?\1")
        assert isinstance(ast, Seq)
        quant_node = cast(Quant, ast.parts[0])
        assert isinstance(quant_node.child, Group)
        assert ast.parts[1] == Backref(byIndex=1)

    def test_null_byte_is_not_a_backreference(self):
        """
        Tests that \0 is parsed as a literal null byte, not backreference 0.

        """
        _flags, ast = parse(r"\0")
        assert ast == Lit("\x00")


class TestCategoryDInteractionCases:
    """
    Covers interactions between groups, lookarounds, and other DSL features.
    """

    def test_backreference_inside_lookaround(self):
        """
        Tests that a backreference can refer to a group defined before a lookaround.
        """
        _flags, ast = parse(r"(?<A>a)(?=\k<A>)")
        assert isinstance(ast, Seq)
        assert isinstance(ast.parts[0], Group)
        look_node = cast(Look, ast.parts[1])
        assert isinstance(look_node.body, Backref)
        assert look_node.body.byName == "A"

    def test_free_spacing_mode_inside_groups(self):
        """
        Tests that free-spacing and comments work correctly inside groups.
        """
        _flags, ast = parse("%flags x\n(?<name> a #comment\n b)")
        assert isinstance(ast, Group)
        assert ast.name == "name"
        assert ast.body == Seq(parts=[Lit("a"), Lit("b")])
