"""
STRling Hint Engine - Context-Aware Error Hints

This module provides intelligent, beginner-friendly hints for common syntax errors.
The hint engine maps specific error types and contexts to instructional messages
that help users understand and fix their mistakes.
"""

from typing import Optional, Dict, Callable


class HintEngine:
    """
    Provides context-aware hints for parse errors.
    
    The hint engine analyzes the error type and parser context to generate
    helpful, instructional messages that guide users toward correct syntax.
    """
    
    def __init__(self):
        """Initialize the hint engine with error pattern mappings."""
        # Map error message patterns to hint generators
        # NOTE: More specific patterns must come before more general ones
        self._hint_generators: Dict[str, Callable[[str, str, int], str]] = {
            "Unterminated group": self._hint_unterminated_group,
            "Unterminated character class": self._hint_unterminated_char_class,
            "Unterminated named backref": self._hint_unterminated_named_backref,
            "Unterminated group name": self._hint_unterminated_group_name,
            "Unterminated lookahead": self._hint_unterminated_lookahead,
            "Unterminated lookbehind": self._hint_unterminated_lookbehind,
            "Unterminated atomic group": self._hint_unterminated_atomic_group,
            "Unterminated {m,n}": self._hint_unterminated_brace_quant,
            "Unterminated {n}": self._hint_unterminated_brace_quant,
            "Invalid quantifier range": self._hint_invalid_quantifier_range,  # More specific, comes first
            "Invalid quantifier": self._hint_invalid_quantifier,  # More general, comes second
            "Invalid character range": self._hint_invalid_character_range,
            "Invalid flag": self._hint_invalid_flag,
            "Directive after pattern content": self._hint_directive_after_pattern,
            "Unknown escape sequence": self._hint_unknown_escape,
            "Unexpected token": self._hint_unexpected_token,
            "Unexpected trailing input": self._hint_unexpected_trailing,
            "Cannot quantify anchor": self._hint_cannot_quantify_anchor,
            "Backreference to undefined group": self._hint_undefined_backref,
            "Duplicate group name": self._hint_duplicate_group_name,
            "Invalid group name": self._hint_invalid_group_name,
            "Empty alternation branch": self._hint_empty_alternation,
            "Alternation lacks left-hand side": self._hint_alternation_no_lhs,
            "Alternation lacks right-hand side": self._hint_alternation_no_rhs,
            "Expected '<' after \\k": self._hint_incomplete_named_backref,
            "Inline modifiers": self._hint_inline_modifiers,
            "Invalid \\xHH escape": self._hint_invalid_hex,
            "Invalid \\uHHHH": self._hint_invalid_unicode,
            "Unterminated \\x{...}": self._hint_unterminated_hex_brace,
            "Unterminated \\u{...}": self._hint_unterminated_unicode_brace,
            "Unterminated \\p{...}": self._hint_unterminated_unicode_property,
            "Expected { after \\p/\\P": self._hint_unicode_property_missing_brace,
        }
    
    def get_hint(self, error_message: str, text: str, pos: int) -> Optional[str]:
        """
        Get a hint for the given error.
        
        Parameters
        ----------
        error_message : str
            The error message from the parser
        text : str
            The full input text being parsed
        pos : int
            The position where the error occurred
        
        Returns
        -------
        str or None
            A helpful hint, or None if no hint is available
        """
        # Try to match error message to a hint generator
        for pattern, generator in self._hint_generators.items():
            if pattern in error_message:
                return generator(error_message, text, pos)
        
        # No specific hint available
        return None
    
    # Hint generators for specific error types
    
    def _hint_unterminated_group(self, msg: str, text: str, pos: int) -> str:
        return (
            "This group was opened with '(' but never closed. "
            "Add a matching ')' to close the group."
        )
    
    def _hint_unterminated_char_class(self, msg: str, text: str, pos: int) -> str:
        return (
            "This character class was opened with '[' but never closed. "
            "Add a matching ']' to close the character class."
        )
    
    def _hint_unterminated_named_backref(self, msg: str, text: str, pos: int) -> str:
        return (
            "Named backreferences use the syntax \\k<name>. "
            "Make sure to close the '<name>' with '>'."
        )
    
    def _hint_unterminated_group_name(self, msg: str, text: str, pos: int) -> str:
        return (
            "Named groups use the syntax (?<name>...). "
            "Make sure to close the '<name>' with '>' before the group content."
        )
    
    def _hint_unterminated_lookahead(self, msg: str, text: str, pos: int) -> str:
        return (
            "This lookahead was opened with '(?=' or '(?!' but never closed. "
            "Add a matching ')' to close the lookahead."
        )
    
    def _hint_unterminated_lookbehind(self, msg: str, text: str, pos: int) -> str:
        return (
            "This lookbehind was opened with '(?<=' or '(?<!' but never closed. "
            "Add a matching ')' to close the lookbehind."
        )
    
    def _hint_unterminated_atomic_group(self, msg: str, text: str, pos: int) -> str:
        return (
            "This atomic group was opened with '(?>' but never closed. "
            "Add a matching ')' to close the atomic group."
        )
    
    def _hint_unterminated_brace_quant(self, msg: str, text: str, pos: int) -> str:
        return (
            "Brace quantifiers use the syntax {m,n} or {n}. "
            "Make sure to close the quantifier with '}'."
        )
    
    def _hint_invalid_quantifier_range(self, msg: str, text: str, pos: int) -> str:
        return (
            "Quantifier range {m,n} must have m ≤ n. "
            "Check that the minimum value is not greater than the maximum value."
        )
    
    def _hint_invalid_quantifier(self, msg: str, text: str, pos: int) -> str:
        # Extract the actual quantifier from the message
        # Message format: "Invalid quantifier 'X'"
        import re
        match = re.search(r"'([*+?{])'", msg)
        quant = match.group(1) if match else "*"
        return (
            f"The quantifier '{quant}' cannot be at the start of a pattern or group. "
            f"It must follow a character or group it can quantify."
        )
    
    def _hint_invalid_character_range(self, msg: str, text: str, pos: int) -> str:
        return (
            "Character ranges must be in ascending order. "
            "For example, use [a-z] instead of [z-a], or [0-9] instead of [9-0]."
        )
    
    def _hint_invalid_flag(self, msg: str, text: str, pos: int) -> str:
        return (
            "Unknown flag. Valid flags are: "
            "i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing)."
        )
    
    def _hint_directive_after_pattern(self, msg: str, text: str, pos: int) -> str:
        return (
            "Directives like %flags must appear at the start of the pattern, "
            "before any regex content."
        )
    
    def _hint_unknown_escape(self, msg: str, text: str, pos: int) -> str:
        # Extract the actual escape character from the message
        # Message format: "Unknown escape sequence \X"
        import re
        match = re.search(r'\\(.)', msg)
        if match:
            ch = match.group(1)
            # Provide context-specific hints for common mistakes
            if ch == 'z':
                return (
                    "'\\z' is not a recognized escape sequence. "
                    "Did you mean '\\Z' (end of string) or just 'z' (a literal 'z')?"
                )
            elif ch.isupper():
                # Suggest lowercase version
                return (
                    f"'\\{ch}' is not a recognized escape sequence. "
                    f"To match literal '{ch}', use '{ch}' without the backslash."
                )
            else:
                return (
                    f"'\\{ch}' is not a recognized escape sequence. "
                    f"To match literal '{ch}', use '{ch}' or escape special characters with '\\'."
                )
        return "This is not a recognized escape sequence."
    
    def _hint_unexpected_token(self, msg: str, text: str, pos: int) -> str:
        # Try to identify the unexpected character
        if pos < len(text):
            char = text[pos]
            if char == ')':
                return (
                    "This ')' character does not have a matching opening '('. "
                    "Did you mean to escape it with '\\)'?"
                )
            elif char == '|':
                return (
                    "The alternation operator '|' requires expressions on both sides. "
                    "Use 'a|b' to match either 'a' or 'b'."
                )
        return "This character appeared in an unexpected context."
    
    def _hint_unexpected_trailing(self, msg: str, text: str, pos: int) -> str:
        return (
            "There is unexpected content after the pattern ended. "
            "Check for unmatched parentheses or extra characters."
        )
    
    def _hint_cannot_quantify_anchor(self, msg: str, text: str, pos: int) -> str:
        return (
            "Anchors like ^, $, \\b, \\B match positions, not characters, "
            "so they cannot be quantified with *, +, ?, or {}."
        )
    
    def _hint_undefined_backref(self, msg: str, text: str, pos: int) -> str:
        return (
            "Backreferences refer to previously captured groups. "
            "Make sure the group is defined before referencing it. "
            "STRling does not support forward references."
        )
    
    def _hint_duplicate_group_name(self, msg: str, text: str, pos: int) -> str:
        return (
            "Each named group must have a unique name. "
            "Use different names for different groups, or use unnamed groups ()."
        )
    
    def _hint_invalid_group_name(self, msg: str, text: str, pos: int) -> str:
        return (
            "Group names must follow the IDENTIFIER rule: start with a letter or "
            "underscore, followed by letters, digits, or underscores. "
            "Use (?<name>...) with a valid identifier."
        )
    
    def _hint_empty_alternation(self, msg: str, text: str, pos: int) -> str:
        return (
            "Empty alternation branch detected (consecutive '|' operators). "
            "Use 'a|b' instead of 'a||b', or '(a|)b' if you want to match optional 'a'."
        )
    
    def _hint_alternation_no_lhs(self, msg: str, text: str, pos: int) -> str:
        return (
            "The alternation operator '|' requires an expression on the left side. "
            "Use 'a|b' to match either 'a' or 'b'."
        )
    
    def _hint_alternation_no_rhs(self, msg: str, text: str, pos: int) -> str:
        return (
            "The alternation operator '|' requires an expression on the right side. "
            "Use 'a|b' to match either 'a' or 'b'."
        )
    
    def _hint_incomplete_named_backref(self, msg: str, text: str, pos: int) -> str:
        return (
            "Named backreferences use the syntax \\k<name>. "
            "The '<' is required after \\k, like \\k<groupname>."
        )
    
    def _hint_inline_modifiers(self, msg: str, text: str, pos: int) -> str:
        return (
            "STRling does not support inline modifiers like (?i) for case-insensitivity. "
            "Instead, use the %flags directive at the start of your pattern: '%flags i'"
        )
    
    def _hint_invalid_hex(self, msg: str, text: str, pos: int) -> str:
        return (
            "Hex escapes must use valid hexadecimal digits (0-9, A-F). "
            "Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A')."
        )
    
    def _hint_invalid_unicode(self, msg: str, text: str, pos: int) -> str:
        return (
            "Unicode escapes must use valid hexadecimal digits (0-9, A-F). "
            "Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes."
        )
    
    def _hint_unterminated_hex_brace(self, msg: str, text: str, pos: int) -> str:
        return (
            "Variable-length hex escapes use the syntax \\x{...}. "
            "Make sure to close the escape with '}'."
        )
    
    def _hint_unterminated_unicode_brace(self, msg: str, text: str, pos: int) -> str:
        return (
            "Variable-length unicode escapes use the syntax \\u{...}. "
            "Make sure to close the escape with '}'."
        )
    
    def _hint_unterminated_unicode_property(self, msg: str, text: str, pos: int) -> str:
        return (
            "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. "
            "Make sure to close the property name with '}'."
        )
    
    def _hint_unicode_property_missing_brace(self, msg: str, text: str, pos: int) -> str:
        return (
            "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. "
            "Use \\p{L} for letters, \\p{N} for numbers, etc."
        )


# Global hint engine instance
_hint_engine = HintEngine()


def get_hint(error_message: str, text: str, pos: int) -> Optional[str]:
    """
    Get a hint for the given error.
    
    This is a convenience function that uses the global hint engine instance.
    
    Parameters
    ----------
    error_message : str
        The error message from the parser
    text : str
        The full input text being parsed
    pos : int
        The position where the error occurred
    
    Returns
    -------
    str or None
        A helpful hint, or None if no hint is available
    """
    return _hint_engine.get_hint(error_message, text, pos)
