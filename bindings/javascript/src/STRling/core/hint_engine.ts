/**
 * STRling Hint Engine - Context-Aware Error Hints
 *
 * This module provides intelligent, beginner-friendly hints for common syntax errors.
 * The hint engine maps specific error types and contexts to instructional messages
 * that help users understand and fix their mistakes.
 */

type HintGenerator = (msg: string, text: string, pos: number) => string;

/**
 * Provides context-aware hints for parse errors.
 *
 * The hint engine analyzes the error type and parser context to generate
 * helpful, instructional messages that guide users toward correct syntax.
 */
class HintEngine {
    private hintGenerators: Map<string, HintGenerator>;

    /**
     * Initialize the hint engine with error pattern mappings.
     */
    constructor() {
        this.hintGenerators = new Map<string, HintGenerator>([
            ["Unterminated group", this.hintUnterminatedGroup],
            ["Unterminated character class", this.hintUnterminatedCharClass],
            ["Unterminated named backref", this.hintUnterminatedNamedBackref],
            ["Unterminated group name", this.hintUnterminatedGroupName],
            ["Unterminated lookahead", this.hintUnterminatedLookahead],
            ["Unterminated lookbehind", this.hintUnterminatedLookbehind],
            ["Unterminated atomic group", this.hintUnterminatedAtomicGroup],
            ["Unterminated {m,n}", this.hintUnterminatedBraceQuant],
            ["Unterminated {n}", this.hintUnterminatedBraceQuant],
            ["Unexpected token", this.hintUnexpectedToken],
            ["Unexpected trailing input", this.hintUnexpectedTrailing],
            ["Cannot quantify anchor", this.hintCannotQuantifyAnchor],
            ["Backreference to undefined group", this.hintUndefinedBackref],
            ["Duplicate group name", this.hintDuplicateGroupName],
            ["Alternation lacks left-hand side", this.hintAlternationNoLhs],
            ["Alternation lacks right-hand side", this.hintAlternationNoRhs],
            ["Inline modifiers", this.hintInlineModifiers],
            ["Invalid \\xHH escape", this.hintInvalidHex],
            ["Invalid \\uHHHH", this.hintInvalidUnicode],
            ["Unterminated \\x{...}", this.hintUnterminatedHexBrace],
            ["Unterminated \\u{...}", this.hintUnterminatedUnicodeBrace],
            ["Unterminated \\p{...}", this.hintUnterminatedUnicodeProperty],
            ["Expected { after \\p/\\P", this.hintUnicodePropertyMissingBrace],
            ["Invalid group name", this.hintInvalidGroupName],
            ["Invalid quantifier range", this.hintInvalidQuantifierRange],
            ["Invalid character range", this.hintInvalidCharacterRange],
            ["Invalid flag", this.hintInvalidFlag],
            ["Directive after pattern", this.hintDirectiveAfterPattern],
            ["Malformed directive", this.hintMalformedDirective],
            ["Empty alternation", this.hintEmptyAlternation],
            ["Unknown escape sequence", this.hintUnknownEscape],
            ["Invalid quantifier", this.hintInvalidQuantifier],
            ["Expected '<' after \\k", this.hintUnterminatedNamedBackref],
        ]);
    }

    /**
     * Get a hint for the given error.
     *
     * @param errorMessage - The error message from the parser
     * @param text - The full input text being parsed
     * @param pos - The position where the error occurred
     * @returns A helpful hint, or null if no hint is available
     */
    getHint(errorMessage: string, text: string, pos: number): string | null {
        // Try to match error message to a hint generator
        for (const [pattern, generator] of this.hintGenerators) {
            if (errorMessage.includes(pattern)) {
                return generator.call(this, errorMessage, text, pos);
            }
        }

        // No specific hint available
        return null;
    }

    // Hint generators for specific error types

    private hintUnterminatedGroup(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "This group was opened with '(' but never closed. " +
            "Add a matching ')' to close the group."
        );
    }

    private hintUnterminatedCharClass(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "This character class was opened with '[' but never closed. " +
            "Add a matching ']' to close the character class."
        );
    }

    private hintUnterminatedNamedBackref(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Named backreferences use the syntax \\k<name>. " +
            "Make sure to close the '<name>' with '>'."
        );
    }

    private hintUnterminatedGroupName(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Named groups use the syntax (?<name>...). " +
            "Make sure to close the '<name>' with '>' before the group content."
        );
    }

    private hintUnterminatedLookahead(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "This lookahead was opened with '(?=' or '(?!' but never closed. " +
            "Add a matching ')' to close the lookahead."
        );
    }

    private hintUnterminatedLookbehind(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "This lookbehind was opened with '(?<=' or '(?<!' but never closed. " +
            "Add a matching ')' to close the lookbehind."
        );
    }

    private hintUnterminatedAtomicGroup(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "This atomic group was opened with '(?>' but never closed. " +
            "Add a matching ')' to close the atomic group."
        );
    }

    private hintUnterminatedBraceQuant(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Brace quantifiers use the syntax {m,n} or {n}. " +
            "Make sure to close the quantifier with '}'."
        );
    }

    private hintUnexpectedToken(
        msg: string,
        text: string,
        pos: number
    ): string {
        // Try to identify the unexpected character
        if (pos < text.length) {
            const char = text[pos];
            if (char === ")") {
                return (
                    "This ')' character does not have a matching opening '('. " +
                    "Did you mean to escape it with '\\)'?"
                );
            } else if (char === "|") {
                return (
                    "The alternation operator '|' requires expressions on both sides. " +
                    "Use 'a|b' to match either 'a' or 'b'."
                );
            }
        }
        return "This character appeared in an unexpected context.";
    }

    private hintUnexpectedTrailing(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "There is unexpected content after the pattern ended. " +
            "Check for unmatched parentheses or extra characters."
        );
    }

    private hintCannotQuantifyAnchor(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Anchors like ^, $, \\b, \\B match positions, not characters, " +
            "so they cannot be quantified with *, +, ?, or {}."
        );
    }

    private hintUndefinedBackref(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Backreferences refer to previously captured groups. " +
            "Make sure the group is defined before referencing it. " +
            "STRling does not support forward references."
        );
    }

    private hintDuplicateGroupName(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Each named group must have a unique name. " +
            "Use different names for different groups, or use unnamed groups ()."
        );
    }

    private hintAlternationNoLhs(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "The alternation operator '|' requires an expression on the left side. " +
            "Use 'a|b' to match either 'a' or 'b'."
        );
    }

    private hintAlternationNoRhs(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "The alternation operator '|' requires an expression on the right side. " +
            "Use 'a|b' to match either 'a' or 'b'."
        );
    }

    private hintInlineModifiers(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "STRling does not support inline modifiers like (?i) for case-insensitivity. " +
            "Instead, use the %flags directive at the start of your pattern: '%flags i'"
        );
    }

    private hintInvalidHex(msg: string, text: string, pos: number): string {
        return (
            "Hex escapes must use valid hexadecimal digits (0-9, A-F). " +
            "Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A')."
        );
    }

    private hintInvalidUnicode(msg: string, text: string, pos: number): string {
        return (
            "Unicode escapes must use valid hexadecimal digits (0-9, A-F). " +
            "Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes."
        );
    }

    private hintUnterminatedHexBrace(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Variable-length hex escapes use the syntax \\x{...}. " +
            "Make sure to close the escape with '}'."
        );
    }

    private hintUnterminatedUnicodeBrace(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Variable-length unicode escapes use the syntax \\u{...}. " +
            "Make sure to close the escape with '}'."
        );
    }

    private hintUnterminatedUnicodeProperty(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. " +
            "Make sure to close the property name with '}'."
        );
    }

    private hintInvalidGroupName(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. " +
            "Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores."
        );
    }

    private hintInvalidQuantifierRange(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). " +
            "For example, use '{2,5}' or '{2,2}', not '{5,2}'."
        );
    }

    private hintInvalidCharacterRange(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. " +
            "Reversed ranges like '[z-a]' are invalid."
        );
    }

    private hintInvalidFlag(msg: string, text: string, pos: number): string {
        return "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).";
    }

    private hintEmptyAlternation(
        msg: string,
        text: string,
        pos: number
    ): string {
        return "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.";
    }

    private hintDirectiveAfterPattern(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). " +
            "Move the directive to the top of the input on its own line."
        );
    }

    private hintMalformedDirective(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, " +
            "for example '%flags i' on a line by itself."
        );
    }

    private hintUnknownEscape(msg: string, text: string, pos: number): string {
        // msg typically includes the specific escape like "Unknown escape sequence \z"
        const m = msg.match(/Unknown escape sequence \\\\?(.)/);
        const ch = m ? m[1] : "\\z";
        if (ch === "z") {
            return "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?";
        }
        return `Unknown escape sequence '\\${ch}'. If you intended a literal '${ch}', remove the backslash or use a recognized escape.`;
    }

    private hintInvalidQuantifier(
        msg: string,
        text: string,
        pos: number
    ): string {
        const m = msg.match(/Invalid quantifier '(.)'/);
        const ch = m ? m[1] : "*";
        return `The quantifier '${ch}' must follow an atom (a character or group). Place '${ch}' after the thing it should quantify, e.g., 'a${ch}'.`;
    }

    private hintUnicodePropertyMissingBrace(
        msg: string,
        text: string,
        pos: number
    ): string {
        return (
            "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. " +
            "Use \\p{L} for letters, \\p{N} for numbers, etc."
        );
    }
}

// Global hint engine instance
const hintEngineInstance = new HintEngine();

/**
 * Get a hint for the given error.
 *
 * This is a convenience function that uses the global hint engine instance.
 *
 * @param errorMessage - The error message from the parser
 * @param text - The full input text being parsed
 * @param pos - The position where the error occurred
 * @returns A helpful hint, or null if no hint is available
 */
export function getHint(
    errorMessage: string,
    text: string,
    pos: number
): string | null {
    return hintEngineInstance.getHint(errorMessage, text, pos);
}
