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
from STRling.core.nodes import Group, Backref, Look, Seq, Lit, Quant, Alt

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
            ("(?<name", "Unterminated group name", 7),
            ("(?=a", "Unterminated lookahead", 4),
            (r"\k<A", "Unterminated named backref", 0),
            # B.2: Invalid backreferences
            (r"\k<A>(?<A>a)", "Backreference to undefined group <A>", 0),
            (r"\2(a)(b)", "Backreference to undefined group \\\\2", 0),
            (r"(a)\2", "Backreference to undefined group \\\\2", 3),
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

    def test_duplicate_group_name_raises_error(self):
        """
        Tests that duplicate group names raise a semantic error.

        """
        with pytest.raises(ParseError, match="Duplicate group name"):
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


# --- New Test Stubs for 3-Test Standard Compliance -----------------------------


class TestCategoryENestedGroups:
    """
    Tests for nested groups of the same and different types.
    Validates that the parser correctly handles deep nesting.
    """

    def test_nested_capturing_groups(self):
        """
        Tests nested capturing groups: ((a))
        """
        _flags, ast = parse("((a))")
        assert isinstance(ast, Group)
        assert ast.capturing is True
        assert isinstance(ast.body, Group)
        assert ast.body.capturing is True
        assert isinstance(ast.body.body, Lit)
        assert ast.body.body.value == "a"

    def test_nested_non_capturing_groups(self):
        """
        Tests nested non-capturing groups: (?:(?:a))
        """
        _flags, ast = parse("(?:(?:a))")
        assert isinstance(ast, Group)
        assert ast.capturing is False
        assert isinstance(ast.body, Group)
        assert ast.body.capturing is False
        assert isinstance(ast.body.body, Lit)
        assert ast.body.body.value == "a"

    def test_nested_atomic_groups(self):
        """
        Tests nested atomic groups: (?>(?>(a)))
        """
        _flags, ast = parse("(?>(?>(a)))")
        assert isinstance(ast, Group)
        assert ast.atomic is True
        assert isinstance(ast.body, Group)
        assert ast.body.atomic is True
        assert isinstance(ast.body.body, Group)
        assert ast.body.body.capturing is True
        assert isinstance(ast.body.body.body, Lit)

    def test_mixed_nesting_capturing_in_non_capturing(self):
        """
        Tests capturing group inside non-capturing: (?:(a))
        """
        _flags, ast = parse("(?:(a))")
        assert isinstance(ast, Group)
        assert ast.capturing is False
        assert isinstance(ast.body, Group)
        assert ast.body.capturing is True
        assert isinstance(ast.body.body, Lit)
        assert ast.body.body.value == "a"

    def test_mixed_nesting_named_in_capturing(self):
        """
        Tests named group inside capturing: ((?<name>a))
        """
        _flags, ast = parse("((?<name>a))")
        assert isinstance(ast, Group)
        assert ast.capturing is True
        assert ast.name is None
        assert isinstance(ast.body, Group)
        assert ast.body.capturing is True
        assert ast.body.name == "name"
        assert isinstance(ast.body.body, Lit)

    def test_mixed_nesting_atomic_in_non_capturing(self):
        """
        Tests atomic group inside non-capturing: (?:(?>a))
        """
        _flags, ast = parse("(?:(?>a))")
        assert isinstance(ast, Group)
        assert ast.capturing is False
        assert isinstance(ast.body, Group)
        assert ast.body.atomic is True
        assert isinstance(ast.body.body, Lit)
        assert ast.body.body.value == "a"

    def test_deeply_nested_groups_three_levels(self):
        """
        Tests deeply nested groups (3+ levels): ((?:(?<x>(?>a))))
        """
        _flags, ast = parse("((?:(?<x>(?>a))))")
        assert isinstance(ast, Group)
        assert ast.capturing is True
        # Level 2
        assert isinstance(ast.body, Group)
        assert ast.body.capturing is False
        # Level 3
        assert isinstance(ast.body.body, Group)
        assert ast.body.body.capturing is True
        assert ast.body.body.name == "x"
        # Level 4
        assert isinstance(ast.body.body.body, Group)
        assert ast.body.body.body.atomic is True
        assert isinstance(ast.body.body.body.body, Lit)


class TestCategoryFLookaroundWithComplexContent:
    """
    Tests for lookarounds containing complex patterns like alternations
    and nested lookarounds.
    """

    def test_lookahead_with_alternation(self):
        """
        Tests positive lookahead with alternation: (?=a|b)
        """
        _flags, ast = parse("(?=a|b)")
        assert isinstance(ast, Look)
        assert ast.dir == "Ahead"
        assert ast.neg is False
        assert isinstance(ast.body, Alt)
        assert len(ast.body.branches) == 2

    def test_lookbehind_with_alternation(self):
        """
        Tests positive lookbehind with alternation: (?<=x|y)
        """
        _flags, ast = parse("(?<=x|y)")
        assert isinstance(ast, Look)
        assert ast.dir == "Behind"
        assert ast.neg is False
        assert isinstance(ast.body, Alt)
        assert len(ast.body.branches) == 2

    def test_negative_lookahead_with_alternation(self):
        """
        Tests negative lookahead with alternation: (?!a|b|c)
        """
        _flags, ast = parse("(?!a|b|c)")
        assert isinstance(ast, Look)
        assert ast.dir == "Ahead"
        assert ast.neg is True
        assert isinstance(ast.body, Alt)
        assert len(ast.body.branches) == 3

    def test_nested_lookaheads(self):
        """
        Tests nested positive lookaheads: (?=(?=a))
        """
        _flags, ast = parse("(?=(?=a))")
        assert isinstance(ast, Look)
        assert ast.dir == "Ahead"
        assert isinstance(ast.body, Look)
        assert ast.body.dir == "Ahead"
        assert isinstance(ast.body.body, Lit)

    def test_nested_lookbehinds(self):
        """
        Tests nested lookbehinds: (?<=(?<!a))
        """
        _flags, ast = parse("(?<=(?<!a))")
        assert isinstance(ast, Look)
        assert ast.dir == "Behind"
        assert ast.neg is False
        assert isinstance(ast.body, Look)
        assert ast.body.dir == "Behind"
        assert ast.body.neg is True
        assert isinstance(ast.body.body, Lit)

    def test_mixed_nested_lookarounds(self):
        """
        Tests lookahead inside lookbehind: (?<=a(?=b))
        """
        _flags, ast = parse("(?<=a(?=b))")
        assert isinstance(ast, Look)
        assert ast.dir == "Behind"
        assert isinstance(ast.body, Seq)
        assert len(ast.body.parts) == 2
        assert isinstance(ast.body.parts[0], Lit)
        assert isinstance(ast.body.parts[1], Look)
        assert ast.body.parts[1].dir == "Ahead"


class TestCategoryGAtomicGroupEdgeCases:
    """
    Tests for atomic groups with complex content.
    """

    def test_atomic_group_with_alternation(self):
        """
        Tests atomic group with alternation: (?>(a|b))
        """
        _flags, ast = parse("(?>(a|b))")
        assert isinstance(ast, Group)
        assert ast.atomic is True
        # The atomic group contains a capturing group with alternation
        assert isinstance(ast.body, Group)
        assert ast.body.capturing is True
        assert isinstance(ast.body.body, Alt)
        assert len(ast.body.body.branches) == 2

    def test_atomic_group_with_quantified_content(self):
        """
        Tests atomic group with quantified atoms: (?>a+b*)
        """
        _flags, ast = parse("(?>a+b*)")
        assert isinstance(ast, Group)
        assert ast.atomic is True
        assert isinstance(ast.body, Seq)
        assert len(ast.body.parts) == 2
        assert isinstance(ast.body.parts[0], Quant)
        assert isinstance(ast.body.parts[1], Quant)

    def test_atomic_group_empty(self):
        """
        Tests empty atomic group: (?>)
        Edge case: should parse correctly.
        """
        _flags, ast = parse("(?>)")
        assert isinstance(ast, Group)
        assert ast.atomic is True
        assert isinstance(ast.body, Seq)
        assert len(ast.body.parts) == 0


class TestCategoryHMultipleBackreferences:
    """
    Tests for patterns with multiple backreferences and complex
    backreference interactions.
    """

    def test_multiple_numeric_backrefs_sequential(self):
        """
        Tests multiple sequential backreferences: (a)(b)\\1\\2
        """
        _flags, ast = parse(r"(a)(b)\1\2")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 4
        assert isinstance(ast.parts[0], Group)
        assert isinstance(ast.parts[1], Group)
        assert isinstance(ast.parts[2], Backref)
        assert ast.parts[2].byIndex == 1
        assert isinstance(ast.parts[3], Backref)
        assert ast.parts[3].byIndex == 2

    def test_multiple_named_backrefs(self):
        """
        Tests multiple named backreferences: (?<x>a)(?<y>b)\\k<x>\\k<y>
        """
        _flags, ast = parse(r"(?<x>a)(?<y>b)\k<x>\k<y>")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 4
        assert isinstance(ast.parts[0], Group)
        assert ast.parts[0].name == "x"
        assert isinstance(ast.parts[1], Group)
        assert ast.parts[1].name == "y"
        assert isinstance(ast.parts[2], Backref)
        assert ast.parts[2].byName == "x"
        assert isinstance(ast.parts[3], Backref)
        assert ast.parts[3].byName == "y"

    def test_mixed_numeric_and_named_backrefs(self):
        """
        Tests mixed backreference types: (a)(?<x>b)\\1\\k<x>
        """
        _flags, ast = parse(r"(a)(?<x>b)\1\k<x>")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 4
        assert isinstance(ast.parts[0], Group)
        assert isinstance(ast.parts[1], Group)
        assert ast.parts[1].name == "x"
        assert isinstance(ast.parts[2], Backref)
        assert ast.parts[2].byIndex == 1
        assert isinstance(ast.parts[3], Backref)
        assert ast.parts[3].byName == "x"

    def test_backref_in_alternation(self):
        """
        Tests backreference in alternation: (a)(\\1|b)
        """
        _flags, ast = parse(r"(a)(\1|b)")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 2
        assert isinstance(ast.parts[0], Group)
        assert isinstance(ast.parts[1], Group)
        assert isinstance(ast.parts[1].body, Alt)
        assert len(ast.parts[1].body.branches) == 2
        assert isinstance(ast.parts[1].body.branches[0], Backref)
        assert ast.parts[1].body.branches[0].byIndex == 1

    def test_backref_to_earlier_alternation_branch(self):
        """
        Tests backreference to group in alternation: (a|b)c\\1
        """
        _flags, ast = parse(r"(a|b)c\1")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Group)
        assert isinstance(ast.parts[0].body, Alt)
        assert isinstance(ast.parts[1], Lit)
        assert isinstance(ast.parts[2], Backref)
        assert ast.parts[2].byIndex == 1

    def test_repeated_backreference(self):
        """
        Tests same backreference used multiple times: (a)\\1\\1
        """
        _flags, ast = parse(r"(a)\1\1")
        assert isinstance(ast, Seq)
        assert len(ast.parts) == 3
        assert isinstance(ast.parts[0], Group)
        assert isinstance(ast.parts[1], Backref)
        assert ast.parts[1].byIndex == 1
        assert isinstance(ast.parts[2], Backref)
        assert ast.parts[2].byIndex == 1


class TestCategoryIGroupsInAlternation:
    """
    Tests for groups and lookarounds inside alternation patterns.
    """

    def test_groups_in_alternation_branches(self):
        """
        Tests capturing groups in alternation: (a)|(b)
        """
        _flags, ast = parse("(a)|(b)")
        assert isinstance(ast, Alt)
        assert len(ast.branches) == 2
        assert isinstance(ast.branches[0], Group)
        assert ast.branches[0].capturing is True
        assert isinstance(ast.branches[1], Group)
        assert ast.branches[1].capturing is True

    def test_lookarounds_in_alternation(self):
        """
        Tests lookarounds in alternation: (?=a)|(?=b)
        """
        _flags, ast = parse("(?=a)|(?=b)")
        assert isinstance(ast, Alt)
        assert len(ast.branches) == 2
        assert isinstance(ast.branches[0], Look)
        assert ast.branches[0].dir == "Ahead"
        assert isinstance(ast.branches[1], Look)
        assert ast.branches[1].dir == "Ahead"

    def test_mixed_group_types_in_alternation(self):
        """
        Tests mixed group types in alternation: (a)|(?:b)|(?<x>c)
        """
        _flags, ast = parse("(a)|(?:b)|(?<x>c)")
        assert isinstance(ast, Alt)
        assert len(ast.branches) == 3
        assert isinstance(ast.branches[0], Group)
        assert ast.branches[0].capturing is True
        assert ast.branches[0].name is None
        assert isinstance(ast.branches[1], Group)
        assert ast.branches[1].capturing is False
        assert isinstance(ast.branches[2], Group)
        assert ast.branches[2].capturing is True
        assert ast.branches[2].name == "x"
