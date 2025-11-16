"""
STRling Error Classes - Rich Error Handling for Instructional Diagnostics

This module provides enhanced error classes that deliver context-aware,
instructional error messages. The STRlingParseError class stores detailed
information about syntax errors including position, context, and beginner-friendly
hints for resolution.
"""

from __future__ import annotations
from typing import Optional


class STRlingParseError(Exception):
    """
    Rich parse error with position tracking and instructional hints.
    
    This error class transforms parse failures into learning opportunities by
    providing:
    - The specific error message
    - The exact position where the error occurred
    - The full line of text containing the error
    - A beginner-friendly hint explaining how to fix the issue
    
    Attributes
    ----------
    message : str
        A concise description of what went wrong
    pos : int
        The character position (0-indexed) where the error occurred
    text : str
        The full input text being parsed
    hint : str, optional
        An instructional hint explaining how to fix the error
    """
    
    def __init__(
        self,
        message: str,
        pos: int,
        text: str = "",
        hint: Optional[str] = None
    ):
        """
        Initialize a STRlingParseError.
        
        Parameters
        ----------
        message : str
            A concise description of what went wrong
        pos : int
            The character position (0-indexed) where the error occurred
        text : str, optional
            The full input text being parsed (default: "")
        hint : str, optional
            An instructional hint explaining how to fix the error (default: None)
        """
        self.message = message
        self.pos = pos
        self.text = text
        self.hint = hint
        
        # Call parent constructor with formatted message
        super().__init__(self._format_error())
    
    def _format_error(self) -> str:
        """
        Format the error in the visionary state format.
        
        Returns
        -------
        str
            A formatted error message with context and hints
        """
        if not self.text:
            # Fallback to simple format if no text provided
            return f"{self.message} at position {self.pos}"
        
        # Find the line containing the error
        lines = self.text.splitlines(keepends=False)
        current_pos = 0
        line_num = 1
        line_text = ""
        col = self.pos
        
        for i, line in enumerate(lines):
            line_len = len(line) + 1  # +1 for newline
            if current_pos + line_len > self.pos:
                line_num = i + 1
                line_text = line
                col = self.pos - current_pos
                break
            current_pos += line_len
        else:
            # Error is beyond the last line
            if lines:
                line_num = len(lines)
                line_text = lines[-1]
                col = len(line_text)
            else:
                line_text = self.text
                col = self.pos
        
        # Build the formatted error message
        parts = [f"STRling Parse Error: {self.message}", ""]
        parts.append(f"> {line_num} | {line_text}")
        parts.append(f">   | {' ' * col}^")
        
        if self.hint:
            parts.append("")
            parts.append(f"Hint: {self.hint}")
        
        return "\n".join(parts)
    
    def __str__(self) -> str:
        """Return the formatted error message."""
        return self._format_error()

    def to_formatted_string(self) -> str:
        """
        Backwards/JS-friendly alias for getting the formatted error string.

        Returns
        -------
        str
            The formatted error message (same as `str(error)`).
        """
        return self._format_error()
