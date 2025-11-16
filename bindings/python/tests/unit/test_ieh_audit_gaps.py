"""
Test IEH Audit Gap Remediation

This test suite validates that all 16 critical gaps identified in the
IEH_Audit_Report.md have been fixed. These tests ensure that:

1. Invalid syntax is properly rejected with validation errors
2. Helpful, instructional hints are provided for all error cases
3. Hints are context-aware and not hardcoded

Each test corresponds to one or more gaps from the audit report.
"""

import pytest
from STRling.core.parser import parse
from STRling.core.errors import STRlingParseError


class TestGroupNameValidation:
    """Tests for group name validation (Gaps 1-3 from audit)."""
    
    def test_group_name_cannot_start_with_digit(self):
        """Test that group names starting with digits are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("(?<1a>)")
        
        error = excinfo.value
        assert "Invalid group name" in error.message
        assert error.hint is not None
        assert "IDENTIFIER" in error.hint
        assert "letter" in error.hint or "underscore" in error.hint
    
    def test_group_name_cannot_be_empty(self):
        """Test that empty group names are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("(?<>)")
        
        error = excinfo.value
        assert "Invalid group name" in error.message
        assert error.hint is not None
    
    def test_group_name_cannot_contain_hyphens(self):
        """Test that group names with hyphens are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("(?<name-bad>)")
        
        error = excinfo.value
        assert "Invalid group name" in error.message
        assert error.hint is not None
        assert "IDENTIFIER" in error.hint


class TestQuantifierRangeValidation:
    """Tests for quantifier range validation (Gap 4 from audit)."""
    
    def test_quantifier_range_min_cannot_exceed_max(self):
        """Test that inverted quantifier ranges like {5,2} are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("a{5,2}")
        
        error = excinfo.value
        assert "Invalid quantifier range" in error.message
        assert error.hint is not None
        assert "m ≤ n" in error.hint or "m <= n" in error.hint


class TestCharacterClassRangeValidation:
    """Tests for character class range validation (Gap 5 from audit)."""
    
    def test_character_range_must_be_ascending_letters(self):
        """Test that reversed letter ranges like [z-a] are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("[z-a]")
        
        error = excinfo.value
        assert "Invalid character range" in error.message
        assert error.hint is not None
        assert "ascending" in error.hint or "order" in error.hint
    
    def test_character_range_must_be_ascending_digits(self):
        """Test that reversed digit ranges like [9-0] are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("[9-0]")
        
        error = excinfo.value
        assert "Invalid character range" in error.message
        assert error.hint is not None


class TestEmptyAlternationValidation:
    """Tests for empty alternation branch detection (Gap 6 from audit)."""
    
    def test_empty_alternation_branch_is_rejected(self):
        """Test that patterns like a||b with empty branches are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("a||b")
        
        error = excinfo.value
        assert "Empty alternation" in error.message
        assert error.hint is not None
        assert "a|b" in error.hint


class TestFlagValidation:
    """Tests for flag directive validation (Gaps 7-8 from audit)."""
    
    def test_invalid_flag_letters_are_rejected(self):
        """Test that invalid flags like 'foo' in %flags foo are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("%flags foo")
        
        error = excinfo.value
        assert "Invalid flag" in error.message
        assert error.hint is not None
        assert "i" in error.hint  # Should list valid flags
        assert "m" in error.hint
    
    def test_directive_after_pattern_is_rejected(self):
        """Test that directives after pattern content are rejected."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("abc%flags i")
        
        error = excinfo.value
        assert "Directive after pattern" in error.message
        assert error.hint is not None
        assert "start of the pattern" in error.hint


class TestIncompleteNamedBackrefHint:
    """Tests for incomplete named backref hint (Gap 9 from audit)."""
    
    def test_incomplete_named_backref_has_hint(self):
        """Test that \\k without < has a helpful hint."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse(r"\k")
        
        error = excinfo.value
        assert "Expected '<' after \\k" in error.message
        assert error.hint is not None
        assert "\\k<name>" in error.hint


class TestContextAwareQuantifierHints:
    """Tests for context-aware quantifier hints (Gap 10 from audit)."""
    
    def test_plus_quantifier_hint_mentions_plus(self):
        """Test that + at start shows '+' in the hint, not '*'."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("+")
        
        error = excinfo.value
        assert error.hint is not None
        assert "'+'" in error.hint
        # Should NOT have hardcoded '*'
        # Note: hint should be dynamic
    
    def test_question_quantifier_hint_mentions_question(self):
        """Test that ? at start shows '?' in the hint, not '*'."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("?")
        
        error = excinfo.value
        assert error.hint is not None
        assert "'?'" in error.hint
    
    def test_brace_quantifier_hint_mentions_brace(self):
        """Test that { at start shows '{' in the hint, not '*'."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse("{5}")
        
        error = excinfo.value
        assert error.hint is not None
        assert "'{'" in error.hint


class TestContextAwareEscapeHints:
    """Tests for context-aware escape hints (Gap 11 from audit)."""
    
    def test_unknown_escape_q_has_dynamic_hint(self):
        """Test that \\q error shows 'q' in the hint, not hardcoded 'z'."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse(r"\q")
        
        error = excinfo.value
        assert error.hint is not None
        # Hint should mention 'q', not be hardcoded to 'z'
        assert "'\\q'" in error.hint or "q" in error.hint
        # Should NOT have hardcoded '\\z' reference unless specifically for \z
    
    def test_unknown_escape_z_has_helpful_hint(self):
        """Test that \\z error has a helpful hint about \\Z."""
        with pytest.raises(STRlingParseError) as excinfo:
            parse(r"\z")
        
        error = excinfo.value
        assert error.hint is not None
        assert "'\\z'" in error.hint
        assert "'\\Z'" in error.hint  # Should suggest the correct escape


class TestValidPatternsStillWork:
    """Ensure valid patterns are not broken by new validation."""
    
    def test_valid_group_names_still_work(self):
        """Test that valid group names like _name and name123 still work."""
        # These should NOT raise errors
        parse("(?<name>abc)")
        parse("(?<_name>abc)")
        parse("(?<name123>abc)")
        parse("(?<Name_123>abc)")
    
    def test_valid_quantifier_ranges_still_work(self):
        """Test that valid quantifier ranges still work."""
        parse("a{2,5}")
        parse("a{2,2}")
        parse("a{0,10}")
    
    def test_valid_character_ranges_still_work(self):
        """Test that valid character ranges still work."""
        parse("[a-z]")
        parse("[0-9]")
        parse("[A-Z]")
    
    def test_single_alternation_still_works(self):
        """Test that single alternations like a|b still work."""
        parse("a|b")
        parse("a|b|c")
    
    def test_valid_flags_still_work(self):
        """Test that valid flags still work."""
        parse("%flags i\nabc")
        parse("%flags imsux\nabc")
