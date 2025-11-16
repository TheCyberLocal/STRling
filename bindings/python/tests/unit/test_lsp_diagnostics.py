"""
Tests for STRlingParseError LSP Diagnostic Conversion

This test suite validates that STRlingParseError objects can be correctly
converted to LSP-compatible diagnostic format.
"""

import pytest
from STRling.core.errors import STRlingParseError


class TestLSPDiagnosticConversion:
    """Test conversion of STRlingParseError to LSP Diagnostic format."""
    
    def test_basic_error_conversion(self):
        """Test basic error conversion to LSP diagnostic."""
        error = STRlingParseError(
            message="Test error",
            pos=5,
            text="hello world",
            hint="Fix it like this"
        )
        
        diag = error.to_lsp_diagnostic()
        
        assert diag["message"] == "Test error\n\nHint: Fix it like this"
        assert diag["severity"] == 1
        assert diag["source"] == "STRling"
        assert "range" in diag
        assert "start" in diag["range"]
        assert "end" in diag["range"]
    
    def test_position_mapping(self):
        """Test that positions are correctly mapped to line/character."""
        error = STRlingParseError(
            message="Error at position 5",
            pos=5,
            text="hello world"
        )
        
        diag = error.to_lsp_diagnostic()
        
        # Position 5 in "hello world" is line 0, character 5
        assert diag["range"]["start"]["line"] == 0
        assert diag["range"]["start"]["character"] == 5
    
    def test_multiline_position_mapping(self):
        """Test position mapping for multiline text."""
        text = "line1\nline2\nline3"
        error = STRlingParseError(
            message="Error on line 2",
            pos=12,  # Position 12 is 'l' in "line3"
            text=text
        )
        
        diag = error.to_lsp_diagnostic()
        
        # Position 12 should be line 2, character 0
        assert diag["range"]["start"]["line"] == 2
        assert diag["range"]["start"]["character"] == 0
    
    def test_error_code_generation(self):
        """Test that error codes are generated from messages."""
        error = STRlingParseError(
            message="Unterminated group",
            pos=0,
            text="(abc"
        )
        
        diag = error.to_lsp_diagnostic()
        
        assert diag["code"] == "unterminated_group"
    
    def test_error_code_with_special_chars(self):
        """Test error code generation with special characters."""
        error = STRlingParseError(
            message="Cannot quantify anchor '*'",
            pos=0,
            text="^*"
        )
        
        diag = error.to_lsp_diagnostic()
        
        # Special characters should be removed/replaced
        assert " " not in diag["code"]
        assert "'" not in diag["code"]
    
    def test_hint_included_in_message(self):
        """Test that hints are included in the diagnostic message."""
        error = STRlingParseError(
            message="Unterminated group",
            pos=4,
            text="(abc",
            hint="This group was opened with '(' but never closed."
        )
        
        diag = error.to_lsp_diagnostic()
        
        assert "Hint:" in diag["message"]
        assert "This group was opened" in diag["message"]
    
    def test_error_without_hint(self):
        """Test error conversion without a hint."""
        error = STRlingParseError(
            message="Syntax error",
            pos=0,
            text="abc"
        )
        
        diag = error.to_lsp_diagnostic()
        
        assert diag["message"] == "Syntax error"
        assert "Hint:" not in diag["message"]
    
    def test_severity_is_error(self):
        """Test that all parse errors have Error severity."""
        error = STRlingParseError(
            message="Test error",
            pos=0,
            text="test"
        )
        
        diag = error.to_lsp_diagnostic()
        
        # Severity 1 = Error in LSP
        assert diag["severity"] == 1
    
    def test_source_is_strling(self):
        """Test that the source is always STRling."""
        error = STRlingParseError(
            message="Test error",
            pos=0,
            text="test"
        )
        
        diag = error.to_lsp_diagnostic()
        
        assert diag["source"] == "STRling"
    
    def test_range_end_is_after_start(self):
        """Test that the range end is after the start."""
        error = STRlingParseError(
            message="Test error",
            pos=5,
            text="hello world"
        )
        
        diag = error.to_lsp_diagnostic()
        
        start_char = diag["range"]["start"]["character"]
        end_char = diag["range"]["end"]["character"]
        
        assert end_char == start_char + 1
    
    def test_empty_text_handling(self):
        """Test handling of errors with empty text."""
        error = STRlingParseError(
            message="Test error",
            pos=0,
            text=""
        )
        
        diag = error.to_lsp_diagnostic()
        
        # Should default to line 0, character 0
        assert diag["range"]["start"]["line"] == 0
        assert diag["range"]["start"]["character"] == 0
    
    def test_position_beyond_text(self):
        """Test handling of position beyond text length."""
        error = STRlingParseError(
            message="Test error",
            pos=100,
            text="short"
        )
        
        diag = error.to_lsp_diagnostic()
        
        # Should clamp to last line
        assert diag["range"]["start"]["line"] == 0
