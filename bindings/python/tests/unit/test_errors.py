"""
Test Design — test_errors.py

## Purpose
This test suite serves as the single source of truth for defining and
validating the error-handling contract of the entire STRling pipeline. It
ensures that invalid inputs are rejected predictably and that diagnostics are
stable, accurate, and helpful across all stages—from the parser to the CLI.

## Description
This suite defines the expected behavior for all invalid, malformed, or
unsupported inputs. It verifies that errors are raised at the correct stage
(e.g., `ParseError`), contain a clear, human-readable message, and provide an
accurate source location. A key invariant tested is the "first error wins"
policy: for an input with multiple issues, only the error at the earliest
position is reported.

## Scope
-   **In scope:**
    -   `ParseError` exceptions raised by the parser for syntactic and lexical
        issues.
    -   `ValidationError` (or equivalent semantic errors) raised for
        syntactically valid but semantically incorrect patterns.

    -   Asserting error messages for a stable, recognizable substring and the
        correctness of the error's reported position.

-   **Out of scope:**
    -   Correct handling of **valid** inputs (covered in other test suites).

    -   The exact, full wording of error messages (tests assert substrings).

"""

import pytest

from STRling.core.parser import parse, ParseError

# --- Test Suite -----------------------------------------------------------------


class TestGroupingAndLookaroundErrors:
    """
    Covers errors related to groups, named groups, and lookarounds.
    """

    @pytest.mark.parametrize(
        "invalid_dsl, error_message_prefix, error_position",
        [
            ("(abc", "Unterminated group", 4),
            ("(?<nameabc)", "Unterminated group name", 11),
            ("(?=abc", "Unterminated lookahead", 6),
            ("(?<=abc", "Unterminated lookbehind", 7),
            ("(?i)abc", "Inline modifiers", 1),
        ],
        ids=[
            "unterminated_group",
            "unterminated_named_group",
            "unterminated_lookahead",
            "unterminated_lookbehind",
            "unsupported_inline_modifier",
        ],
    )
    def test_grouping_syntax_errors(
        self, invalid_dsl: str, error_message_prefix: str, error_position: int
    ):
        """Tests that various unterminated group/lookaround forms raise ParseError."""
        with pytest.raises(ParseError, match=error_message_prefix) as excinfo:
            parse(invalid_dsl)
        assert excinfo.value.pos == error_position


class TestBackreferenceAndNamingErrors:
    """
    Covers errors related to invalid backreferences and group naming.
    """

    @pytest.mark.parametrize(
        "invalid_dsl, error_message_prefix, error_position",
        [
            (r"\k<later>(?<later>a)", "Backreference to undefined group <later>", 0),
            (r"\2(a)(b)", "Backreference to undefined group \\2", 0),
            (r"(a)\2", "Backreference to undefined group \\2", 3),
            (r"\k<", "Expected '<' after \\k", 2),
        ],
        ids=[
            "forward_reference_by_name",
            "forward_reference_by_index",
            "nonexistent_reference_by_index",
            "unterminated_named_backref",
        ],
    )
    def test_backreference_validation_errors(
        self, invalid_dsl: str, error_message_prefix: str, error_position: int
    ):
        """Tests that invalid backreferences are caught at parse time."""
        with pytest.raises(ParseError, match=error_message_prefix) as excinfo:
            parse(invalid_dsl)
        assert excinfo.value.pos == error_position

    @pytest.mark.xfail(reason="Parser does not yet check for duplicate group names.")
    def test_duplicate_group_name_raises_error(self):
        """
        Tests that duplicate group names raise a semantic error.

        """
        with pytest.raises(Exception, match="Duplicate group name"):
            parse("(?<name>a)(?<name>b)")


class TestCharacterClassErrors:
    """
    Covers errors related to character class syntax.
    """

    @pytest.mark.parametrize(
        "invalid_dsl, error_message_prefix, error_position",
        [
            ("[abc", "Unterminated character class", 4),
            (r"[\p{L", "Unterminated \\p{...}", 5),
            (r"[\pL]", "Expected { after \\p/\\P", 3),
        ],
        ids=[
            "unterminated_class",
            "unterminated_unicode_property",
            "missing_braces_on_unicode_property",
        ],
    )
    def test_char_class_syntax_errors(
        self, invalid_dsl: str, error_message_prefix: str, error_position: int
    ):
        """Tests that malformed character classes raise a ParseError."""
        with pytest.raises(ParseError, match=error_message_prefix) as excinfo:
            parse(invalid_dsl)
        assert excinfo.value.pos == error_position


class TestEscapeAndCodepointErrors:
    """
    Covers errors related to malformed escape sequences.
    """

    @pytest.mark.parametrize(
        "invalid_dsl, error_message_prefix, error_position",
        [
            (r"\xG1", "Invalid \\xHH escape", 3),
            (r"\u12Z4", "Invalid \\uHHHH", 5),
            (r"\x{", "Unterminated \\x{...}", 3),
            (r"\x{FFFF}", "Unterminated \\x{...}", 7),
        ],
        ids=[
            "invalid_hex_digit",
            "invalid_unicode_digit",
            "unterminated_hex_brace_empty",
            "unterminated_hex_brace_with_digits",
        ],
    )
    def test_malformed_escapes(
        self, invalid_dsl: str, error_message_prefix: str, error_position: int
    ):
        """Tests that malformed hex/unicode escapes raise a ParseError."""
        with pytest.raises(ParseError, match=error_message_prefix) as excinfo:
            parse(invalid_dsl)
        assert excinfo.value.pos == error_position


class TestQuantifierErrors:
    """
    Covers errors related to malformed quantifiers.
    """

    def test_unterminated_brace_quantifier_raises_error(self):
        """
        Tests that an unterminated brace quantifier like {m,n raises an error.

        """
        with pytest.raises(ParseError, match="Unterminated {m,n}") as excinfo:
            parse("a{2,5")
        assert excinfo.value.pos == 5

    @pytest.mark.xfail(
        reason="Parser does not yet perform semantic validation on quantifiers."
    )
    def test_quantifying_non_quantifiable_atom_raises_error(self):
        """
        Tests that attempting to quantify an anchor raises a semantic error.

        """
        with pytest.raises(Exception, match="Cannot quantify anchor"):
            parse("^*")


class TestInvariantFirstErrorWins:
    """
    Tests the invariant that only the first error in a string is reported.
    """

    def test_first_of_multiple_errors_is_reported(self):
        """
        In the string '[a|b(', the unterminated class at position 0 should be
        reported, not the unterminated group at position 4.

        """
        with pytest.raises(ParseError, match="Unterminated character class") as excinfo:
            parse("[a|b(")
        assert excinfo.value.pos == 4
