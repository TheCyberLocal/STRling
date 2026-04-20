namespace Strling.Core;

using System.Text.RegularExpressions;

/// <summary>
/// STRling Hint Engine - Context-Aware Error Hints
/// 
/// This module provides intelligent, beginner-friendly hints for common syntax errors.
/// The hint engine maps specific error types and contexts to instructional messages
/// that help users understand and fix their mistakes.
/// </summary>
public static class HintEngine
{
    private static readonly List<(string Pattern, Func<string, string, int, string> Generator)> HintGenerators = new()
    {
        ("Unterminated group", HintUnterminatedGroup),
        ("Empty character class", HintEmptyCharacterClass),
        ("Unterminated character class", HintUnterminatedCharClass),
        ("Unterminated named backref", HintUnterminatedNamedBackref),
        ("Unterminated group name", HintUnterminatedGroupName),
        ("Unterminated lookahead", HintUnterminatedLookahead),
        ("Unterminated lookbehind", HintUnterminatedLookbehind),
        ("Unterminated atomic group", HintUnterminatedAtomicGroup),
        ("Unterminated {m,n}", HintUnterminatedBraceQuant),
        ("Unterminated {n}", HintUnterminatedBraceQuant),
        ("Unexpected token", HintUnexpectedToken),
        ("Unexpected trailing input", HintUnexpectedTrailing),
        ("Cannot quantify anchor", HintCannotQuantifyAnchor),
        ("Backreference to undefined group", HintUndefinedBackref),
        ("Duplicate group name", HintDuplicateGroupName),
        ("Alternation lacks left-hand side", HintAlternationNoLhs),
        ("Alternation lacks right-hand side", HintAlternationNoRhs),
        ("Inline modifiers", HintInlineModifiers),
        ("Invalid \\xHH escape", HintInvalidHex),
        ("Invalid \\uHHHH", HintInvalidUnicode),
        ("Unterminated \\x{...}", HintUnterminatedHexBrace),
        ("Unterminated \\u{...}", HintUnterminatedUnicodeBrace),
        ("Unterminated \\p{...}", HintUnterminatedUnicodeProperty),
        ("Expected { after \\p/\\P", HintUnicodePropertyMissingBrace),
        ("Invalid brace quantifier content", HintInvalidBraceQuantContent),
        ("Invalid group name", HintInvalidGroupName),
        ("Invalid quantifier range", HintInvalidQuantifierRange),
        ("Invalid character range", HintInvalidCharacterRange),
        ("Invalid flag", HintInvalidFlag),
        ("Directive after pattern", HintDirectiveAfterPattern),
        ("Malformed directive", HintMalformedDirective),
        ("Empty alternation", HintEmptyAlternation),
        ("Unknown escape sequence", HintUnknownEscape),
        ("Invalid quantifier", HintInvalidQuantifier),
        ("Expected '<' after \\k", HintUnterminatedNamedBackref),
        ("Incomplete quantifier", HintIncompleteQuantifier),
        ("Invalid \\UHHHHHHHH escape", HintInvalidUnicodeLong),
        ("Unmatched ')'", HintUnmatchedCloseParen),
    };

    /// <summary>
    /// Get a hint for the given error.
    /// </summary>
    /// <param name="errorMessage">The error message from the parser</param>
    /// <param name="text">The full input text being parsed</param>
    /// <param name="pos">The position where the error occurred</param>
    /// <returns>A helpful hint, or null if no hint is available</returns>
    public static string? GetHint(string errorMessage, string text, int pos)
    {
        foreach (var (pattern, generator) in HintGenerators)
        {
            if (errorMessage.Contains(pattern))
            {
                return generator(errorMessage, text, pos);
            }
        }

        return null;
    }

    private static string HintUnterminatedGroup(string msg, string text, int pos) =>
        "This group was opened with '(' but never closed. Add a matching ')' to close the group.";

    private static string HintEmptyCharacterClass(string msg, string text, int pos) =>
        "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. If you meant a literal '[', escape it with '\\['.";

    private static string HintUnterminatedCharClass(string msg, string text, int pos) =>
        "This character class was opened with '[' but never closed. Add a matching ']' to close the character class.";

    private static string HintUnterminatedNamedBackref(string msg, string text, int pos) =>
        "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'.";

    private static string HintUnterminatedGroupName(string msg, string text, int pos) =>
        "Named groups use the syntax (?<name>...). Make sure to close the '<name>' with '>' before the group content.";

    private static string HintUnterminatedLookahead(string msg, string text, int pos) =>
        "This lookahead was opened with '(?=' or '(?!' but never closed. Add a matching ')' to close the lookahead.";

    private static string HintUnterminatedLookbehind(string msg, string text, int pos) =>
        "This lookbehind was opened with '(?<=' or '(?<!' but never closed. Add a matching ')' to close the lookbehind.";

    private static string HintUnterminatedAtomicGroup(string msg, string text, int pos) =>
        "This atomic group was opened with '(?>' but never closed. Add a matching ')' to close the atomic group.";

    private static string HintUnterminatedBraceQuant(string msg, string text, int pos) =>
        "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.";

    private static string HintUnexpectedToken(string msg, string text, int pos)
    {
        if (pos < text.Length)
        {
            var ch = text[pos];
            if (ch == ')')
                return "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern. '\\)'?";
            if (ch == '|')
                return "The alternation operator '|' requires expressions on both sides. Use 'a|b' to match either 'a' or 'b'.";
        }
        return "This character appeared in an unexpected context.";
    }

    private static string HintUnexpectedTrailing(string msg, string text, int pos) =>
        "There is unexpected content after the pattern ended. Check for unmatched parentheses or extra characters.";

    private static string HintCannotQuantifyAnchor(string msg, string text, int pos) =>
        "Anchors like ^, $, \\b, \\B match positions, not characters, so they cannot be quantified with *, +, ?, or {}.";

    private static string HintUndefinedBackref(string msg, string text, int pos) =>
        "Backreferences refer to previously captured groups. Make sure the group is defined before referencing it. STRling does not support forward references.";

    private static string HintDuplicateGroupName(string msg, string text, int pos) =>
        "Each named group must have a unique name. Use different names for different groups, or use unnamed groups ().";

    private static string HintAlternationNoLhs(string msg, string text, int pos) =>
        "The alternation operator '|' requires an expression on the left side. Use 'a|b' to match either 'a' or 'b'.";

    private static string HintAlternationNoRhs(string msg, string text, int pos) =>
        "The alternation operator '|' requires an expression on the right side. Use 'a|b' to match either 'a' or 'b'.";

    private static string HintInlineModifiers(string msg, string text, int pos) =>
        "STRling does not support inline modifiers like (?i) for case-insensitivity. Instead, use the %flags directive at the start of your pattern: '%flags i'";

    private static string HintInvalidHex(string msg, string text, int pos) =>
        "Hex escapes must use valid hexadecimal digits (0-9, A-F). Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').";

    private static string HintInvalidUnicode(string msg, string text, int pos) =>
        "Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.";

    private static string HintUnterminatedHexBrace(string msg, string text, int pos) =>
        "Variable-length hex escapes use the syntax \\x{...}. Make sure to close the escape with '}'.";

    private static string HintUnterminatedUnicodeBrace(string msg, string text, int pos) =>
        "Variable-length unicode escapes use the syntax \\u{...}. Make sure to close the escape with '}'.";

    private static string HintUnterminatedUnicodeProperty(string msg, string text, int pos) =>
        "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. Make sure to close the property name with '}'.";

    private static string HintUnicodePropertyMissingBrace(string msg, string text, int pos) =>
        "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. Use \\p{L} for letters, \\p{N} for numbers, etc.";

    private static string HintInvalidBraceQuantContent(string msg, string text, int pos) =>
        "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'.";

    private static string HintInvalidGroupName(string msg, string text, int pos) =>
        "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.";

    private static string HintInvalidQuantifierRange(string msg, string text, int pos) =>
        "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). For example, use '{2,5}' or '{2,2}', not '{5,2}'.";

    private static string HintInvalidCharacterRange(string msg, string text, int pos) =>
        "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. Reversed ranges like '[z-a]' are invalid.";

    private static string HintInvalidFlag(string msg, string text, int pos) =>
        "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).";

    private static string HintDirectiveAfterPattern(string msg, string text, int pos) =>
        "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). Move the directive to the top of the input on its own line.";

    private static string HintMalformedDirective(string msg, string text, int pos) =>
        "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, for example '%flags i' on a line by itself.";

    private static string HintEmptyAlternation(string msg, string text, int pos) =>
        "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.";

    private static string HintUnknownEscape(string msg, string text, int pos)
    {
        var m = Regex.Match(msg, @"Unknown escape sequence \\?(.)", RegexOptions.None, TimeSpan.FromSeconds(1));
        var ch = m.Success ? m.Groups[1].Value : "\\z";
        if (ch == "z")
            return "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?";
        return $"Unknown escape sequence '\\{ch}'. If you intended a literal '{ch}', remove the backslash or use a recognized escape.";
    }

    private static string HintInvalidQuantifier(string msg, string text, int pos)
    {
        var m = Regex.Match(msg, @"Invalid quantifier '(.)'", RegexOptions.None, TimeSpan.FromSeconds(1));
        var ch = m.Success ? m.Groups[1].Value : "*";
        return $"The quantifier '{ch}' must follow an atom (a character or group). Place '{ch}' after the thing it should quantify, e.g., 'a{ch}'.";
    }

    private static string HintIncompleteQuantifier(string msg, string text, int pos) =>
        "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.";

    private static string HintInvalidUnicodeLong(string msg, string text, int pos) =>
        "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.";

    private static string HintUnmatchedCloseParen(string msg, string text, int pos) =>
        "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.";
}
