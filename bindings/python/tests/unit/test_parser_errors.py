"""
Test Parser Error Messages - Comprehensive Validation of Rich Error Output

This test suite validates that the parser produces rich, instructional error
messages in the "Visionary State" format with:
  - Context line showing the error location
  - Caret (^) pointing to the exact position
  - Helpful hints explaining how to fix the error

These tests intentionally pass invalid syntax to ensure the error messages
are helpful and educational.
"""

import pytest
from STRling.core.parser import parse
from STRling.core.errors import STRlingParseError


class TestRichErrorFormatting:
    """Test that errors are formatted in the visionary state format."""
    
    def test_unmatched_closing_paren_shows_visionary_format(self):
        """Test that unmatched ')' shows full formatted error."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("(a|b))")
        
        error = excinfo.value
        formatted = str(error)
        
        # Check all components of visionary format
        assert "STRling Parse Error:" in formatted
        assert "Unmatched ')'" in formatted
        assert "> 1 | (a|b))" in formatted
        assert "^" in formatted
        assert "Hint:" in formatted
        assert "Did you mean to escape it" in formatted
    
    def test_unterminated_group_shows_helpful_hint(self):
        """Test unterminated group error includes hint."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("(abc")
        
        error = excinfo.value
        assert error.hint is not None
        assert "opened with '('" in error.hint
        assert "Add a matching ')'" in error.hint
    
    def test_error_on_second_line_shows_correct_line_number(self):
        """Test multiline pattern shows correct line number."""
        pattern = "abc\n(def"
        with pytest.raises(STRlingParseError) as excinfo:
            parse(pattern)
        
        formatted = str(excinfo.value)
        assert "> 2 |" in formatted  # Should show line 2
        assert "(def" in formatted
    
    def test_caret_points_to_exact_position(self):
        """Test that caret is positioned correctly."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("abc)")
        
        formatted = str(excinfo.value)
        lines = formatted.split("\n")
        
        # Find the line with the caret
        for i, line in enumerate(lines):
            if line.startswith(">   |"):
                caret_line = line[6:]  # Remove ">   | "
                # Caret should be at position 3 (under ')')
                assert caret_line.strip() == "^"
                spaces = len(caret_line) - len(caret_line.lstrip())
                assert spaces == 3


class TestSpecificErrorHints:
    """Test specific error types have appropriate hints."""
    
    def test_alternation_no_lhs_hint(self):
        """Test alternation without left-hand side."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("|abc")
        
        error = excinfo.value
        assert "Alternation lacks left-hand side" in error.message
        assert error.hint is not None
        assert "expression on the left side" in error.hint
    
    def test_alternation_no_rhs_hint(self):
        """Test alternation without right-hand side."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("abc|")
        
        error = excinfo.value
        assert "Alternation lacks right-hand side" in error.message
        assert error.hint is not None
        assert "expression on the right side" in error.hint
    
    def test_unterminated_char_class_hint(self):
        """Test unterminated character class."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("[abc")
        
        error = excinfo.value
        assert "Unterminated character class" in error.message
        assert error.hint is not None
        assert "opened with '['" in error.hint
        assert "Add a matching ']'" in error.hint
    
    def test_cannot_quantify_anchor_hint(self):
        """Test error when trying to quantify an anchor."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("^*")
        
        error = excinfo.value
        assert "Cannot quantify anchor" in error.message
        assert error.hint is not None
        assert "Anchors" in error.hint
        assert "match positions" in error.hint
    
    def test_invalid_hex_escape_hint(self):
        """Test invalid hex escape sequence."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse(r"\xGG")
        
        error = excinfo.value
        assert "Invalid \\xHH escape" in error.message
        assert error.hint is not None
        assert "hexadecimal digits" in error.hint
    
    def test_undefined_backref_hint(self):
        """Test backreference to undefined group."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse(r"\1abc")
        
        error = excinfo.value
        assert "Backreference to undefined group" in error.message
        assert error.hint is not None
        assert "previously captured groups" in error.hint
        assert "forward references" in error.hint
    
    def test_duplicate_group_name_hint(self):
        """Test duplicate named group."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("(?<name>a)(?<name>b)")
        
        error = excinfo.value
        assert "Duplicate group name" in error.message
        assert error.hint is not None
        assert "unique name" in error.hint
    
    def test_inline_modifiers_hint(self):
        """Test unsupported inline modifiers."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("(?i)abc")
        
        error = excinfo.value
        assert "Inline modifiers" in error.message
        assert error.hint is not None
        assert "%flags" in error.hint
        assert "directive" in error.hint
    
    def test_unterminated_unicode_property_hint(self):
        """Test unterminated unicode property."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse(r"[\p{Letter")
        
        error = excinfo.value
        assert "Unterminated \\p{...}" in error.message
        assert error.hint is not None
        assert "syntax \\p{Property}" in error.hint


class TestComplexErrorScenarios:
    """Test error handling in complex scenarios."""
    
    def test_nested_groups_error_shows_outermost(self):
        """Test that nested unterminated groups show the first error."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("((abc")
        
        # Should report the first unterminated group
        error = excinfo.value
        assert "Unterminated group" in error.message
    
    def test_error_in_alternation_branch(self):
        """Test error within an alternation branch."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("a|(b")
        
        error = excinfo.value
        assert "Unterminated group" in error.message
        # Position should point to the end where ')' is expected
        assert error.pos == 4
    
    def test_error_with_free_spacing_mode(self):
        """Test error in free-spacing mode still provides good context."""
        pattern = "%flags x\n(abc\n  def"
        with pytest.raises(STRlingParseError) as excinfo:
            parse(pattern)
        
        error = excinfo.value
        assert error.hint is not None
    
    def test_error_position_accuracy(self):
        """Test that error position is accurate."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("abc{2,")
        
        error = excinfo.value
        assert "Incomplete quantifier" in error.message
        # Position should be at the end where '}' is expected
        assert error.pos == 6


class TestErrorBackwardCompatibility:
    """Test that ParseError maintains backward compatibility."""
    
    def test_error_has_message_attribute(self):
        """Test that error has message attribute for backward compatibility."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("(")
        
        error = excinfo.value
        assert hasattr(error, 'message')
        assert error.message == "Unterminated group"
    
    def test_error_has_pos_attribute(self):
        """Test that error has pos attribute for backward compatibility."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("abc)")
        
        error = excinfo.value
        assert hasattr(error, 'pos')
        assert error.pos == 3
    
    def test_error_string_contains_position(self):
        """Test that error string representation includes position info."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse(")")
        
        formatted = str(excinfo.value)
        # Should contain position information in the formatted output
        assert ">" in formatted  # Line markers
        assert "^" in formatted  # Caret pointer
