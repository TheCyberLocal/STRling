package com.strling.core;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * STRling Hint Engine - Context-Aware Error Hints
 *
 * <p>This module provides intelligent, beginner-friendly hints for common syntax errors.
 * The hint engine maps specific error types and contexts to instructional messages
 * that help users understand and fix their mistakes.</p>
 */
public final class HintEngine {

    private HintEngine() {}

    /**
     * Functional interface for hint generators.
     */
    @FunctionalInterface
    private interface HintGenerator {
        String generate(String msg, String text, int pos);
    }

    private static final Map<String, HintGenerator> HINT_GENERATORS = new LinkedHashMap<>();

    static {
        HINT_GENERATORS.put("Unterminated group", HintEngine::hintUnterminatedGroup);
        HINT_GENERATORS.put("Empty character class", HintEngine::hintEmptyCharacterClass);
        HINT_GENERATORS.put("Unterminated character class", HintEngine::hintUnterminatedCharClass);
        HINT_GENERATORS.put("Unterminated named backref", HintEngine::hintUnterminatedNamedBackref);
        HINT_GENERATORS.put("Unterminated group name", HintEngine::hintUnterminatedGroupName);
        HINT_GENERATORS.put("Unterminated lookahead", HintEngine::hintUnterminatedLookahead);
        HINT_GENERATORS.put("Unterminated lookbehind", HintEngine::hintUnterminatedLookbehind);
        HINT_GENERATORS.put("Unterminated atomic group", HintEngine::hintUnterminatedAtomicGroup);
        HINT_GENERATORS.put("Unterminated {m,n}", HintEngine::hintUnterminatedBraceQuant);
        HINT_GENERATORS.put("Unterminated {n}", HintEngine::hintUnterminatedBraceQuant);
        HINT_GENERATORS.put("Incomplete quantifier", HintEngine::hintUnterminatedBraceQuant);  // Maps to same hint
        HINT_GENERATORS.put("Unexpected token", HintEngine::hintUnexpectedToken);
        HINT_GENERATORS.put("Unexpected trailing input", HintEngine::hintUnexpectedTrailing);
        HINT_GENERATORS.put("Cannot quantify anchor", HintEngine::hintCannotQuantifyAnchor);
        HINT_GENERATORS.put("Backreference to undefined group", HintEngine::hintUndefinedBackref);
        HINT_GENERATORS.put("Duplicate group name", HintEngine::hintDuplicateGroupName);
        HINT_GENERATORS.put("Alternation lacks left-hand side", HintEngine::hintAlternationNoLhs);
        HINT_GENERATORS.put("Alternation lacks right-hand side", HintEngine::hintAlternationNoRhs);
        HINT_GENERATORS.put("Inline modifiers", HintEngine::hintInlineModifiers);
        HINT_GENERATORS.put("Invalid \\xHH escape", HintEngine::hintInvalidHex);
        HINT_GENERATORS.put("Invalid \\uHHHH", HintEngine::hintInvalidUnicode);
        HINT_GENERATORS.put("Unterminated \\x{...}", HintEngine::hintUnterminatedHexBrace);
        HINT_GENERATORS.put("Unterminated \\u{...}", HintEngine::hintUnterminatedUnicodeBrace);
        HINT_GENERATORS.put("Unterminated \\p{...}", HintEngine::hintUnterminatedUnicodeProperty);
        HINT_GENERATORS.put("Expected { after \\p/\\P", HintEngine::hintUnicodePropertyMissingBrace);
        HINT_GENERATORS.put("Invalid brace quantifier content", HintEngine::hintInvalidBraceQuantContent);
        HINT_GENERATORS.put("Invalid group name", HintEngine::hintInvalidGroupName);
        HINT_GENERATORS.put("Invalid quantifier range", HintEngine::hintInvalidQuantifierRange);
        HINT_GENERATORS.put("Invalid character range", HintEngine::hintInvalidCharacterRange);
        HINT_GENERATORS.put("Invalid flag", HintEngine::hintInvalidFlag);
        HINT_GENERATORS.put("Directive after pattern", HintEngine::hintDirectiveAfterPattern);
        HINT_GENERATORS.put("Malformed directive", HintEngine::hintMalformedDirective);
        HINT_GENERATORS.put("Empty alternation", HintEngine::hintEmptyAlternation);
        HINT_GENERATORS.put("Unknown escape sequence", HintEngine::hintUnknownEscape);
        HINT_GENERATORS.put("Invalid quantifier", HintEngine::hintInvalidQuantifier);
        HINT_GENERATORS.put("Expected '<' after \\k", HintEngine::hintUnterminatedNamedBackref);
    }

    /**
     * Get a hint for the given error.
     *
     * <p>This method analyzes the error type and parser context to generate
     * helpful, instructional messages that guide users toward correct syntax.</p>
     *
     * @param errorMessage The error message from the parser
     * @param text The full input text being parsed
     * @param pos The position where the error occurred
     * @return A helpful hint, or null if no hint is available
     */
    public static String getHint(String errorMessage, String text, int pos) {
        if (errorMessage == null) {
            return null;
        }

        // Try to match error message to a hint generator
        for (Map.Entry<String, HintGenerator> entry : HINT_GENERATORS.entrySet()) {
            if (errorMessage.contains(entry.getKey())) {
                return entry.getValue().generate(errorMessage, text, pos);
            }
        }

        // No specific hint available
        return null;
    }

    // Hint generators for specific error types

    private static String hintUnterminatedGroup(String msg, String text, int pos) {
        return "This group was opened with '(' but never closed. " +
               "Add a matching ')' to close the group.";
    }

    private static String hintUnterminatedCharClass(String msg, String text, int pos) {
        return "This character class was opened with '[' but never closed. " +
               "Add a matching ']' to close the character class.";
    }

    private static String hintUnterminatedNamedBackref(String msg, String text, int pos) {
        return "Named backreferences use the syntax \\k<name>. " +
               "Make sure to close the '<name>' with '>';";
    }

    private static String hintUnterminatedGroupName(String msg, String text, int pos) {
        return "Named groups use the syntax (?<name>...). " +
               "Make sure to close the '<name>' with '>' before the group content.";
    }

    private static String hintUnterminatedLookahead(String msg, String text, int pos) {
        return "This lookahead was opened with '(?=' or '(?!' but never closed. " +
               "Add a matching ')' to close the lookahead.";
    }

    private static String hintUnterminatedLookbehind(String msg, String text, int pos) {
        return "This lookbehind was opened with '(?<=' or '(?<!' but never closed. " +
               "Add a matching ')' to close the lookbehind.";
    }

    private static String hintUnterminatedAtomicGroup(String msg, String text, int pos) {
        return "This atomic group was opened with '(?>' but never closed. " +
               "Add a matching ')' to close the atomic group.";
    }

    private static String hintUnterminatedBraceQuant(String msg, String text, int pos) {
        return "Brace quantifiers use the syntax {m,n} or {n}. " +
               "Make sure to include the closing '}'.";
    }

    private static String hintUnexpectedToken(String msg, String text, int pos) {
        // Try to identify the unexpected character
        if (pos < text.length()) {
            char ch = text.charAt(pos);
            if (ch == ')') {
                return "This ')' character does not have a matching opening '('. " +
                       "Did you mean to escape it with '\\)'?";
            } else if (ch == '|') {
                return "The alternation operator '|' requires expressions on both sides. " +
                       "Use 'a|b' to match either 'a' or 'b'.";
            }
        }
        return "This character appeared in an unexpected context.";
    }

    private static String hintUnexpectedTrailing(String msg, String text, int pos) {
        return "There is unexpected content after the pattern ended. " +
               "Check for unmatched parentheses or extra characters.";
    }

    private static String hintCannotQuantifyAnchor(String msg, String text, int pos) {
        return "Anchors like ^, $, \\b, \\B match positions, not characters, " +
               "so they cannot be quantified with *, +, ?, or {}.";
    }

    private static String hintUndefinedBackref(String msg, String text, int pos) {
        return "Backreferences refer to previously captured groups. " +
               "Make sure the group is defined before referencing it. " +
               "STRling does not support forward references.";
    }

    private static String hintDuplicateGroupName(String msg, String text, int pos) {
        return "Each named group must have a unique name. " +
               "Use different names for different groups, or use unnamed groups ().";
    }

    private static String hintAlternationNoLhs(String msg, String text, int pos) {
        return "The alternation operator '|' requires an expression on the left side. " +
               "Use 'a|b' to match either 'a' or 'b'.";
    }

    private static String hintAlternationNoRhs(String msg, String text, int pos) {
        return "The alternation operator '|' requires an expression on the right side. " +
               "Use 'a|b' to match either 'a' or 'b'.";
    }

    private static String hintInlineModifiers(String msg, String text, int pos) {
        return "STRling does not support inline modifiers like (?i) for case-insensitivity. " +
               "Instead, use the %flags directive at the start of your pattern: '%flags i'";
    }

    private static String hintInvalidHex(String msg, String text, int pos) {
        return "Hex escapes must use valid hexadecimal digits (0-9, A-F). " +
               "Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').";
    }

    private static String hintInvalidUnicode(String msg, String text, int pos) {
        return "Unicode escapes must use valid hexadecimal digits (0-9, A-F). " +
               "Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.";
    }

    private static String hintUnterminatedHexBrace(String msg, String text, int pos) {
        return "Variable-length hex escapes use the syntax \\x{...}. " +
               "Make sure to close the escape with '}'.";
    }

    private static String hintUnterminatedUnicodeBrace(String msg, String text, int pos) {
        return "Variable-length unicode escapes use the syntax \\u{...}. " +
               "Make sure to close the escape with '}'.";
    }

    private static String hintUnterminatedUnicodeProperty(String msg, String text, int pos) {
        return "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. " +
               "Make sure to close the property name with '}'.";
    }

    private static String hintInvalidGroupName(String msg, String text, int pos) {
        return "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. " +
               "Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.";
    }

    private static String hintInvalidQuantifierRange(String msg, String text, int pos) {
        return "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). " +
               "For example, use '{2,5}' or '{2,2}', not '{5,2}'.";
    }

    private static String hintInvalidCharacterRange(String msg, String text, int pos) {
        return "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. " +
               "Reversed ranges like '[z-a]' are invalid.";
    }

    private static String hintInvalidFlag(String msg, String text, int pos) {
        return "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).";
    }

    private static String hintEmptyAlternation(String msg, String text, int pos) {
        return "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.";
    }

    private static String hintDirectiveAfterPattern(String msg, String text, int pos) {
        return "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). " +
               "Move the directive to the top of the input on its own line.";
    }

    private static String hintMalformedDirective(String msg, String text, int pos) {
        return "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, " +
               "for example '%flags i' on a line by itself.";
    }

    private static String hintUnknownEscape(String msg, String text, int pos) {
        // msg typically includes the specific escape like "Unknown escape sequence \z"
        Pattern p = Pattern.compile("Unknown escape sequence \\\\\\\\?(.)" );
        Matcher m = p.matcher(msg);
        String ch = m.find() ? m.group(1) : "\\z";
        
        if ("z".equals(ch)) {
            return "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?";
        }
        return "Unknown escape sequence '\\" + ch + "'. If you intended a literal '" + ch + "', remove the backslash or use a recognized escape.";
    }

    private static String hintInvalidQuantifier(String msg, String text, int pos) {
        Pattern p = Pattern.compile("Invalid quantifier '(.)'");
        Matcher m = p.matcher(msg);
        String ch = m.find() ? m.group(1) : "*";
        return "The quantifier '" + ch + "' must follow an atom (a character or group). Place '" + ch + "' after the thing it should quantify, e.g., 'a" + ch + "'.";
    }

    private static String hintInvalidBraceQuantContent(String msg, String text, int pos) {
        return "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. " +
               "Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'.";
    }

    private static String hintEmptyCharacterClass(String msg, String text, int pos) {
        return "Empty character class '[]' detected. " +
               "Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. " +
               "If you meant a literal '[', escape it with '\\['.";
    }

    private static String hintUnicodePropertyMissingBrace(String msg, String text, int pos) {
        return "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. " +
               "Use \\p{L} for letters, \\p{N} for numbers, etc.";
    }
}
