namespace Strling.Core;

/// <summary>
/// STRling Hint Engine - Context-Aware Error Hints
/// 
/// This module provides intelligent, beginner-friendly hints for common syntax errors.
/// The hint engine maps specific error types and contexts to instructional messages
/// that help users understand and fix their mistakes.
/// </summary>
public static class HintEngine
{
    /// <summary>
    /// Get a hint for the given error.
    /// </summary>
    /// <param name="errorMessage">The error message from the parser</param>
    /// <param name="text">The full input text being parsed</param>
    /// <param name="pos">The position where the error occurred</param>
    /// <returns>A helpful hint, or null if no hint is available</returns>
    public static string? GetHint(string errorMessage, string text, int pos)
    {
        // Match error message patterns to hints
        if (errorMessage.Contains("Unknown escape sequence"))
        {
            return "Valid escape sequences include: \\n, \\r, \\t, \\d, \\w, \\s, \\b, \\B, \\A, \\Z, and character class escapes like [\\n\\r\\t].";
        }
        else if (errorMessage.Contains("Cannot quantify anchor"))
        {
            return "Anchors like ^, $, \\b, and \\B match positions, not characters, and cannot be repeated with quantifiers like *, +, or ?.";
        }
        else if (errorMessage.Contains("Unterminated group"))
        {
            return "Each opening parenthesis '(' must have a corresponding closing parenthesis ')'.";
        }
        else if (errorMessage.Contains("Unterminated character class"))
        {
            return "Character classes must be closed with ']'. Example: [a-z].";
        }
        else if (errorMessage.Contains("Invalid flag"))
        {
            return "Valid flags are: i (ignoreCase), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).";
        }
        else if (errorMessage.Contains("Directive after pattern content"))
        {
            return "Directives like %flags must appear at the start of the pattern, before any regex content.";
        }
        else if (errorMessage.Contains("Unexpected token"))
        {
            return "Check for unescaped special characters or misplaced metacharacters.";
        }
        else if (errorMessage.Contains("Unexpected trailing input"))
        {
            return "The pattern ended unexpectedly. Check for unmatched parentheses or brackets.";
        }
        else if (errorMessage.Contains("Invalid quantifier"))
        {
            return "Quantifiers must follow an atom (literal, group, or character class). They cannot appear at the start of a pattern or after another quantifier.";
        }
        else if (errorMessage.Contains("Backreference to undefined group"))
        {
            return "Backreferences like \\1 or \\k<name> must refer to a capturing group that appears earlier in the pattern.";
        }

        return null; // No specific hint available
    }
}
