r"""
Test Design — test_error_formatting.py

## Purpose
This module tests the `STRlingParseError` formatting and the hint engine's
behavior. Tests assert that formatted errors include position indicators,
source context, and that hints are generated when appropriate.

## Description
The suite validates string formatting for single-line and multi-line source
text, checks caret positioning, and ensures that the hint engine returns
useful, contextual hints for known parse failures and `None` for unknown
errors.

## Scope
- **In scope:**
    - `STRlingParseError` string formatting and helper methods.
    - `get_hint` responses for common parse failures (unterminated groups,
      character classes, unexpected tokens, quantifier/anchor hints, inline
      modifier guidance).
- **Out of scope:**
    - Emitter or runtime behavior unrelated to error formatting.

"""

import pytest
from STRling.core.errors import STRlingParseError
from STRling.core.hint_engine import get_hint


class TestSTRlingParseError:
    """Test the rich error formatting."""
    
    def test_simple_error_without_text(self):
        """Test fallback format when no text is provided."""
        err = STRlingParseError("Test error", 5)
        assert "Test error at position 5" in str(err)
    
    def test_error_with_text_and_hint(self):
        """Test formatted error with text and hint."""
        text = "(a|b))"
        err = STRlingParseError(
            "Unmatched ')'",
            5,
            text,
            "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
        )
        formatted = str(err)
        
        # Check that it contains the expected parts
        assert "STRling Parse Error: Unmatched ')'" in formatted
        assert "> 1 | (a|b))" in formatted
        assert "^" in formatted
        assert "Hint:" in formatted
        assert "does not have a matching opening '('" in formatted
    
    def test_error_position_indicator(self):
        """Test that the caret points to the right position."""
        text = "abc def"
        err = STRlingParseError("Error at d", 4, text)
        formatted = str(err)
        
        # The caret should be under 'd' (position 4)
        lines = formatted.split("\n")
        for i, line in enumerate(lines):
            if line.startswith(">   |"):
                # Count spaces before ^
                caret_line = line[6:]  # Remove ">   | "
                spaces_before_caret = len(caret_line) - len(caret_line.lstrip())
                assert spaces_before_caret == 4
                break
    
    def test_multiline_error(self):
        """Test error on second line."""
        text = "abc\ndef\nghi"
        err = STRlingParseError("Error on line 2", 5, text)
        formatted = str(err)
        
        # Should show line 2
        assert "> 2 | def" in formatted

    def test_to_formatted_string_method(self):
        """Test the `to_formatted_string` alias returns same as str()."""
        err = STRlingParseError("Test", 0, "abc")
        assert err.to_formatted_string() == str(err)


class TestHintEngine:
    """Test the hint engine."""
    
    def test_unterminated_group_hint(self):
        """Test hint for unterminated group."""
        hint = get_hint("Unterminated group", "(abc", 4)
        assert hint is not None
        assert "opened with '('" in hint
        assert "Add a matching ')'" in hint
    
    def test_unterminated_char_class_hint(self):
        """Test hint for unterminated character class."""
        hint = get_hint("Unterminated character class", "[abc", 4)
        assert hint is not None
        assert "opened with '['" in hint
        assert "Add a matching ']'" in hint
    
    def test_unexpected_token_hint_closing_paren(self):
        """Test hint for unexpected closing paren."""
        hint = get_hint("Unexpected token", "abc)", 3)
        assert hint is not None
        assert "does not have a matching opening '('" in hint
        assert "escape it with '\\)'" in hint
    
    def test_cannot_quantify_anchor_hint(self):
        """Test hint for quantifying anchor."""
        hint = get_hint("Cannot quantify anchor", "^*", 1)
        assert hint is not None
        assert "Anchors" in hint
        assert "match positions" in hint
        assert "cannot be quantified" in hint
    
    def test_inline_modifiers_hint(self):
        """Test hint for inline modifiers."""
        hint = get_hint("Inline modifiers `(?imsx)` are not supported", "(?i)abc", 1)
        assert hint is not None
        assert "%flags" in hint
        assert "directive" in hint
    
    def test_no_hint_for_unknown_error(self):
        """Test that unknown errors return None."""
        hint = get_hint("Some unknown error message", "abc", 0)
        assert hint is None
