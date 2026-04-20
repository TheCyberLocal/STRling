/// STRling Hint Engine - Context-Aware Error Hints
///
/// Provides intelligent, beginner-friendly hints for common syntax errors.
/// Maps specific error types and contexts to instructional messages that
/// help users understand and fix their mistakes.
///
/// Mirrors the TypeScript reference: bindings/typescript/src/STRling/core/hint_engine.ts

import Foundation

/// Stateless hint engine that derives instructional guidance from parse failure context.
public enum HintEngine {

    /// Get a hint for the given error.
    ///
    /// - Parameters:
    ///   - errorMessage: The error message from the parser
    ///   - text: The full input text being parsed
    ///   - pos: The position where the error occurred
    /// - Returns: A helpful hint string (never nil — returns a generic fallback)
    public static func getHint(_ errorMessage: String, text: String, pos: Int) -> String {
        // Try each pattern in priority order
        for (pattern, generator) in hintGenerators {
            if errorMessage.contains(pattern) {
                return generator(errorMessage, text, pos)
            }
        }
        // Generic fallback — hint is always present
        return "Check your pattern syntax near position \(pos). Refer to the STRling documentation for correct usage."
    }

    // MARK: - Hint Generator Registry

    private static let hintGenerators: [(String, (String, String, Int) -> String)] = [
        ("Unterminated group", hintUnterminatedGroup),
        ("Empty character class", hintEmptyCharacterClass),
        ("Unterminated character class", hintUnterminatedCharClass),
        ("Unterminated named backref", hintUnterminatedNamedBackref),
        ("Unterminated group name", hintUnterminatedGroupName),
        ("Unterminated lookahead", hintUnterminatedLookahead),
        ("Unterminated lookbehind", hintUnterminatedLookbehind),
        ("Unterminated atomic group", hintUnterminatedAtomicGroup),
        ("Unterminated {m,n}", hintUnterminatedBraceQuant),
        ("Unterminated {n}", hintUnterminatedBraceQuant),
        ("Incomplete quantifier", hintUnterminatedBraceQuant),
        ("Unexpected token", hintUnexpectedToken),
        ("Unexpected trailing input", hintUnexpectedTrailing),
        ("Cannot quantify anchor", hintCannotQuantifyAnchor),
        ("Backreference to undefined group", hintUndefinedBackref),
        ("Duplicate group name", hintDuplicateGroupName),
        ("Alternation lacks left-hand side", hintAlternationNoLhs),
        ("Alternation lacks right-hand side", hintAlternationNoRhs),
        ("Inline modifiers", hintInlineModifiers),
        ("Invalid \\xHH escape", hintInvalidHex),
        ("Invalid \\uHHHH", hintInvalidUnicode),
        ("Unterminated \\x{...}", hintUnterminatedHexBrace),
        ("Unterminated \\u{...}", hintUnterminatedUnicodeBrace),
        ("Unterminated \\p{...}", hintUnterminatedUnicodeProperty),
        ("Expected { after \\p/\\P", hintUnicodePropertyMissingBrace),
        ("Expected '<' after \\p/\\P", hintUnicodePropertyMissingBrace),
        ("Invalid brace quantifier content", hintInvalidBraceQuantContent),
        ("Invalid group name", hintInvalidGroupName),
        ("Invalid quantifier range", hintInvalidQuantifierRange),
        ("Invalid character range", hintInvalidCharacterRange),
        ("Invalid flag", hintInvalidFlag),
        ("Directive after pattern", hintDirectiveAfterPattern),
        ("Directive must appear", hintDirectiveAfterPattern),
        ("Malformed directive", hintMalformedDirective),
        ("Empty alternation", hintEmptyAlternation),
        ("Unknown escape sequence", hintUnknownEscape),
        ("Invalid quantifier", hintInvalidQuantifier),
        ("Expected '<' after \\k", hintUnterminatedNamedBackref),
        ("Invalid \\UHHHHHHHH escape", hintInvalidUnicodeLong),
        ("Unmatched ')'", hintUnmatchedCloseParen),
    ]

    // MARK: - Hint Generators

    private static func hintUnterminatedGroup(_ msg: String, _ text: String, _ pos: Int) -> String {
        "This group was opened with '(' but never closed. Add a matching ')' to close the group."
    }

    private static func hintEmptyCharacterClass(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. If you meant a literal '[', escape it with '\\['."
    }

    private static func hintUnterminatedCharClass(_ msg: String, _ text: String, _ pos: Int) -> String {
        "This character class was opened with '[' but never closed. Add a matching ']' to close the character class."
    }

    private static func hintUnterminatedNamedBackref(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'."
    }

    private static func hintUnterminatedGroupName(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Named groups use the syntax (?<name>...). Make sure to close the '<name>' with '>' before the group content."
    }

    private static func hintUnterminatedLookahead(_ msg: String, _ text: String, _ pos: Int) -> String {
        "This lookahead was opened with '(?=' or '(?!' but never closed. Add a matching ')' to close the lookahead."
    }

    private static func hintUnterminatedLookbehind(_ msg: String, _ text: String, _ pos: Int) -> String {
        "This lookbehind was opened with '(?<=' or '(?<!' but never closed. Add a matching ')' to close the lookbehind."
    }

    private static func hintUnterminatedAtomicGroup(_ msg: String, _ text: String, _ pos: Int) -> String {
        "This atomic group was opened with '(?>' but never closed. Add a matching ')' to close the atomic group."
    }

    private static func hintUnterminatedBraceQuant(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers."
    }

    private static func hintUnexpectedToken(_ msg: String, _ text: String, _ pos: Int) -> String {
        if pos < text.count {
            let idx = text.index(text.startIndex, offsetBy: pos)
            let ch = text[idx]
            if ch == ")" {
                return "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern."
            } else if ch == "|" {
                return "The alternation operator '|' requires expressions on both sides. Use 'a|b' to match either 'a' or 'b'."
            }
        }
        return "This character appeared in an unexpected context."
    }

    private static func hintUnexpectedTrailing(_ msg: String, _ text: String, _ pos: Int) -> String {
        "There is unexpected content after the pattern ended. Check for unmatched parentheses or extra characters."
    }

    private static func hintCannotQuantifyAnchor(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Anchors like ^, $, \\b, \\B match positions, not characters, so they cannot be quantified with *, +, ?, or {}."
    }

    private static func hintUndefinedBackref(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Backreferences refer to previously captured groups. Make sure the group is defined before referencing it. STRling does not support forward references."
    }

    private static func hintDuplicateGroupName(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Each named group must have a unique name. Use different names for different groups, or use unnamed groups ()."
    }

    private static func hintAlternationNoLhs(_ msg: String, _ text: String, _ pos: Int) -> String {
        "The alternation operator '|' requires an expression on the left side. Use 'a|b' to match either 'a' or 'b'."
    }

    private static func hintAlternationNoRhs(_ msg: String, _ text: String, _ pos: Int) -> String {
        "The alternation operator '|' requires an expression on the right side. Use 'a|b' to match either 'a' or 'b'."
    }

    private static func hintInlineModifiers(_ msg: String, _ text: String, _ pos: Int) -> String {
        "STRling does not support inline modifiers like (?i) for case-insensitivity. Instead, use the %flags directive at the start of your pattern: '%flags i'"
    }

    private static func hintInvalidHex(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Hex escapes must use valid hexadecimal digits (0-9, A-F). Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A')."
    }

    private static func hintInvalidUnicode(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes."
    }

    private static func hintUnterminatedHexBrace(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Variable-length hex escapes use the syntax \\x{...}. Make sure to close the escape with '}'."
    }

    private static func hintUnterminatedUnicodeBrace(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Variable-length unicode escapes use the syntax \\u{...}. Make sure to close the escape with '}'."
    }

    private static func hintUnterminatedUnicodeProperty(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. Make sure to close the property name with '}'."
    }

    private static func hintUnicodePropertyMissingBrace(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. Use \\p{L} for letters, \\p{N} for numbers, etc."
    }

    private static func hintInvalidBraceQuantContent(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'."
    }

    private static func hintInvalidGroupName(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores."
    }

    private static func hintInvalidQuantifierRange(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). For example, use '{2,5}' or '{2,2}', not '{5,2}'."
    }

    private static func hintInvalidCharacterRange(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. Reversed ranges like '[z-a]' are invalid."
    }

    private static func hintInvalidFlag(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing)."
    }

    private static func hintDirectiveAfterPattern(_ msg: String, _ text: String, _ pos: Int) -> String {
        "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). Move the directive to the top of the input on its own line."
    }

    private static func hintMalformedDirective(_ msg: String, _ text: String, _ pos: Int) -> String {
        "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, for example '%flags i' on a line by itself."
    }

    private static func hintEmptyAlternation(_ msg: String, _ text: String, _ pos: Int) -> String {
        "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'."
    }

    private static func hintUnknownEscape(_ msg: String, _ text: String, _ pos: Int) -> String {
        // Extract the escape character from the message
        if let range = msg.range(of: #"Unknown escape sequence \\?(.)"#, options: .regularExpression) {
            let match = String(msg[range])
            let ch = String(match.last ?? Character("z"))
            if ch == "z" {
                return "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?"
            }
            return "Unknown escape sequence '\\\(ch)'. If you intended a literal '\(ch)', remove the backslash or use a recognized escape."
        }
        return "Unknown escape sequence. If you intended a literal character, remove the backslash or use a recognized escape."
    }

    private static func hintInvalidQuantifier(_ msg: String, _ text: String, _ pos: Int) -> String {
        // Extract the quantifier character from the message
        if let range = msg.range(of: #"Invalid quantifier '(.)'"#, options: .regularExpression) {
            let match = String(msg[range])
            // The char is at a fixed offset
            if let qIdx = match.firstIndex(of: "'") {
                let chIdx = match.index(after: qIdx)
                if chIdx < match.endIndex {
                    let ch = match[chIdx]
                    return "The quantifier '\(ch)' must follow an atom (a character or group). Place '\(ch)' after the thing it should quantify, e.g., 'a\(ch)'."
                }
            }
        }
        return "Quantifiers must follow an atom (a character or group). Place the quantifier after the thing it should quantify."
    }

    private static func hintUnmatchedCloseParen(_ msg: String, _ text: String, _ pos: Int) -> String {
        "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern."
    }

    private static func hintInvalidUnicodeLong(_ msg: String, _ text: String, _ pos: Int) -> String {
        "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes."
    }
}
