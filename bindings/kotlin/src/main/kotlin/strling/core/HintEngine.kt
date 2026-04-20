package strling.core

/**
 * STRling Hint Engine - Context-Aware Error Hints
 *
 * Provides intelligent, beginner-friendly hints for common syntax errors.
 * Maps specific error types and contexts to instructional messages that
 * help users understand and fix their mistakes.
 *
 * Mirrors the TypeScript reference: bindings/typescript/src/STRling/core/hint_engine.ts
 */
object HintEngine {

    /**
     * Get a hint for the given error.
     *
     * @param errorMessage The error message from the parser
     * @param text The full input text being parsed
     * @param pos The position where the error occurred
     * @return A helpful hint string (never null — returns a generic fallback)
     */
    fun getHint(errorMessage: String, text: String, pos: Int): String {
        for ((pattern, generator) in hintGenerators) {
            if (errorMessage.contains(pattern)) {
                return generator(errorMessage, text, pos)
            }
        }
        return "Check your pattern syntax near position $pos. Refer to the STRling documentation for correct usage."
    }

    private val hintGenerators: List<Pair<String, (String, String, Int) -> String>> = listOf(
        "Unterminated group" to ::hintUnterminatedGroup,
        "Empty character class" to ::hintEmptyCharacterClass,
        "Unterminated character class" to ::hintUnterminatedCharClass,
        "Unterminated named backref" to ::hintUnterminatedNamedBackref,
        "Unterminated group name" to ::hintUnterminatedGroupName,
        "Unterminated lookahead" to ::hintUnterminatedLookahead,
        "Unterminated lookbehind" to ::hintUnterminatedLookbehind,
        "Unterminated atomic group" to ::hintUnterminatedAtomicGroup,
        "Unterminated {m,n}" to ::hintUnterminatedBraceQuant,
        "Unterminated {n}" to ::hintUnterminatedBraceQuant,
        "Incomplete quantifier" to ::hintUnterminatedBraceQuant,
        "Unexpected token" to ::hintUnexpectedToken,
        "Unexpected trailing input" to ::hintUnexpectedTrailing,
        "Cannot quantify anchor" to ::hintCannotQuantifyAnchor,
        "Backreference to undefined group" to ::hintUndefinedBackref,
        "Duplicate group name" to ::hintDuplicateGroupName,
        "Alternation lacks left-hand side" to ::hintAlternationNoLhs,
        "Alternation lacks right-hand side" to ::hintAlternationNoRhs,
        "Empty alternation" to ::hintEmptyAlternation,
        "Inline modifiers" to ::hintInlineModifiers,
        "Invalid \\xHH escape" to ::hintInvalidHex,
        "Invalid \\uHHHH" to ::hintInvalidUnicode,
        "Unterminated \\x{...}" to ::hintUnterminatedHexBrace,
        "Unterminated \\u{...}" to ::hintUnterminatedUnicodeBrace,
        "Unterminated \\p{...}" to ::hintUnterminatedUnicodeProperty,
        "Expected { after \\p/\\P" to ::hintUnicodePropertyMissingBrace,
        "Expected '<' after \\p/\\P" to ::hintUnicodePropertyMissingBrace,
        "Invalid brace quantifier content" to ::hintInvalidBraceQuantContent,
        "Invalid group name" to ::hintInvalidGroupName,
        "Invalid quantifier range" to ::hintInvalidQuantifierRange,
        "Invalid character range" to ::hintInvalidCharacterRange,
        "Invalid flag" to ::hintInvalidFlag,
        "Directive after pattern" to ::hintDirectiveAfterPattern,
        "Directive must appear" to ::hintDirectiveAfterPattern,
        "Malformed directive" to ::hintMalformedDirective,
        "Unknown escape sequence" to ::hintUnknownEscape,
        "Invalid quantifier" to ::hintInvalidQuantifier,
        "Expected '<' after \\k" to ::hintUnterminatedNamedBackref,
        "Invalid \\UHHHHHHHH escape" to ::hintInvalidUnicodeLong,
        "Unmatched ')'" to ::hintUnmatchedCloseParen,
    )

    private fun hintUnterminatedGroup(msg: String, text: String, pos: Int): String =
        "This group was opened with '(' but never closed. Add a matching ')' to close the group."

    private fun hintEmptyCharacterClass(msg: String, text: String, pos: Int): String =
        "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. If you meant a literal '[', escape it with '\\['."

    private fun hintUnterminatedCharClass(msg: String, text: String, pos: Int): String =
        "This character class was opened with '[' but never closed. Add a matching ']' to close the character class."

    private fun hintUnterminatedNamedBackref(msg: String, text: String, pos: Int): String =
        "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'."

    private fun hintUnterminatedGroupName(msg: String, text: String, pos: Int): String =
        "Named groups use the syntax (?<name>...). Make sure to close the '<name>' with '>' before the group content."

    private fun hintUnterminatedLookahead(msg: String, text: String, pos: Int): String =
        "This lookahead was opened with '(?=' or '(?!' but never closed. Add a matching ')' to close the lookahead."

    private fun hintUnterminatedLookbehind(msg: String, text: String, pos: Int): String =
        "This lookbehind was opened with '(?<=' or '(?<!' but never closed. Add a matching ')' to close the lookbehind."

    private fun hintUnterminatedAtomicGroup(msg: String, text: String, pos: Int): String =
        "This atomic group was opened with '(?>' but never closed. Add a matching ')' to close the atomic group."

    private fun hintUnterminatedBraceQuant(msg: String, text: String, pos: Int): String =
        "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers."

    private fun hintUnexpectedToken(msg: String, text: String, pos: Int): String {
        if (pos < text.length) {
            return when (text[pos]) {
                ')' -> "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern."
                '|' -> "The alternation operator '|' requires expressions on both sides. Use 'a|b' to match either 'a' or 'b'."
                else -> "This character appeared in an unexpected context."
            }
        }
        return "This character appeared in an unexpected context."
    }

    private fun hintUnexpectedTrailing(msg: String, text: String, pos: Int): String =
        "There is unexpected content after the pattern ended. Check for unmatched parentheses or extra characters."

    private fun hintCannotQuantifyAnchor(msg: String, text: String, pos: Int): String =
        "Anchors like ^, \$, \\b, \\B match positions, not characters, so they cannot be quantified with *, +, ?, or {}."

    private fun hintUndefinedBackref(msg: String, text: String, pos: Int): String =
        "Backreferences refer to previously captured groups. Make sure the group is defined before referencing it. STRling does not support forward references."

    private fun hintDuplicateGroupName(msg: String, text: String, pos: Int): String =
        "Each named group must have a unique name. Use different names for different groups, or use unnamed groups ()."

    private fun hintAlternationNoLhs(msg: String, text: String, pos: Int): String =
        "The alternation operator '|' requires an expression on the left side. Use 'a|b' to match either 'a' or 'b'."

    private fun hintAlternationNoRhs(msg: String, text: String, pos: Int): String =
        "The alternation operator '|' requires an expression on the right side. Use 'a|b' to match either 'a' or 'b'."

    private fun hintEmptyAlternation(msg: String, text: String, pos: Int): String =
        "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'."

    private fun hintInlineModifiers(msg: String, text: String, pos: Int): String =
        "STRling does not support inline modifiers like (?i) for case-insensitivity. Instead, use the %flags directive at the start of your pattern: '%flags i'"

    private fun hintInvalidHex(msg: String, text: String, pos: Int): String =
        "Hex escapes must use valid hexadecimal digits (0-9, A-F). Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A')."

    private fun hintInvalidUnicode(msg: String, text: String, pos: Int): String =
        "Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes."

    private fun hintUnterminatedHexBrace(msg: String, text: String, pos: Int): String =
        "Variable-length hex escapes use the syntax \\x{...}. Make sure to close the escape with '}'."

    private fun hintUnterminatedUnicodeBrace(msg: String, text: String, pos: Int): String =
        "Variable-length unicode escapes use the syntax \\u{...}. Make sure to close the escape with '}'."

    private fun hintUnterminatedUnicodeProperty(msg: String, text: String, pos: Int): String =
        "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. Make sure to close the property name with '}'."

    private fun hintUnicodePropertyMissingBrace(msg: String, text: String, pos: Int): String =
        "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. Use \\p{L} for letters, \\p{N} for numbers, etc."

    private fun hintInvalidBraceQuantContent(msg: String, text: String, pos: Int): String =
        "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'."

    private fun hintInvalidGroupName(msg: String, text: String, pos: Int): String =
        "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores."

    private fun hintInvalidQuantifierRange(msg: String, text: String, pos: Int): String =
        "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). For example, use '{2,5}' or '{2,2}', not '{5,2}'."

    private fun hintInvalidCharacterRange(msg: String, text: String, pos: Int): String =
        "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. Reversed ranges like '[z-a]' are invalid."

    private fun hintInvalidFlag(msg: String, text: String, pos: Int): String =
        "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing)."

    private fun hintDirectiveAfterPattern(msg: String, text: String, pos: Int): String =
        "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). Move the directive to the top of the input on its own line."

    private fun hintMalformedDirective(msg: String, text: String, pos: Int): String =
        "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, for example '%flags i' on a line by itself."

    private fun hintUnknownEscape(msg: String, text: String, pos: Int): String {
        val m = Regex("""Unknown escape sequence \\\\?(.)""").find(msg)
        val ch = m?.groupValues?.getOrNull(1) ?: return "Unknown escape sequence. If you intended a literal character, remove the backslash or use a recognized escape."
        if (ch == "z") {
            return "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?"
        }
        return "Unknown escape sequence '\\$ch'. If you intended a literal '$ch', remove the backslash or use a recognized escape."
    }

    private fun hintInvalidQuantifier(msg: String, text: String, pos: Int): String {
        val m = Regex("""Invalid quantifier '(.)'""").find(msg)
        val ch = m?.groupValues?.getOrNull(1) ?: "*"
        return "The quantifier '$ch' must follow an atom (a character or group). Place '$ch' after the thing it should quantify, e.g., 'a$ch'."
    }

    private fun hintUnmatchedCloseParen(msg: String, text: String, pos: Int): String =
        "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern."

    private fun hintInvalidUnicodeLong(msg: String, text: String, pos: Int): String =
        "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes."
}
