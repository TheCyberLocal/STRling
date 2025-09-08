import pytest
from STRling.core.parser import parse_to_artifact as p2a, ParseError


def test_unterminated_group_raises():
    with pytest.raises(ParseError):
        p2a("(abc")


def test_bad_named_group_syntax_raises():
    with pytest.raises(ParseError):
        p2a("(?<name")


def test_invalid_hex_raises():
    with pytest.raises(ParseError):
        p2a(r"\x0G")


def test_invalid_unicode_raises():
    with pytest.raises(ParseError):
        p2a(r"\uZZZZ")


# FIX: Removed xfail marker. The parser now correctly raises a ParseError.
def test_inline_modifiers_forbidden():
    with pytest.raises(ParseError):
        p2a(r"(?i)abc")
