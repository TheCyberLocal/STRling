<?php

declare(strict_types=1);

namespace STRling\Core;

/**
 * STRling Hint Engine - Context-Aware Error Hints
 *
 * Provides intelligent, beginner-friendly hints for common syntax errors.
 * Maps specific error types and contexts to instructional messages that
 * help users understand and fix their mistakes.
 *
 * Mirrors the TypeScript reference: bindings/typescript/src/STRling/core/hint_engine.ts
 */
final class HintEngine
{
    /**
     * Get a hint for the given error.
     *
     * @param string $errorMessage The error message from the parser
     * @param string $text The full input text being parsed
     * @param int $pos The position where the error occurred
     * @return string A helpful hint string (never null — returns a generic fallback)
     */
    public static function getHint(string $errorMessage, string $text, int $pos): string
    {
        $generators = self::hintGenerators();
        foreach ($generators as [$pattern, $method]) {
            if (str_contains($errorMessage, $pattern)) {
                return self::$method($errorMessage, $text, $pos);
            }
        }
        return "Check your pattern syntax near position {$pos}. Refer to the STRling documentation for correct usage.";
    }

    /**
     * @return list<array{0: string, 1: string}>
     */
    private static function hintGenerators(): array
    {
        return [
            ['Unterminated group', 'hintUnterminatedGroup'],
            ['Empty character class', 'hintEmptyCharacterClass'],
            ['Unterminated character class', 'hintUnterminatedCharClass'],
            ['Unterminated named backref', 'hintUnterminatedNamedBackref'],
            ['Unterminated group name', 'hintUnterminatedGroupName'],
            ['Unterminated lookahead', 'hintUnterminatedLookahead'],
            ['Unterminated lookbehind', 'hintUnterminatedLookbehind'],
            ['Unterminated atomic group', 'hintUnterminatedAtomicGroup'],
            ['Unterminated {m,n}', 'hintUnterminatedBraceQuant'],
            ['Unterminated {n}', 'hintUnterminatedBraceQuant'],
            ['Incomplete quantifier', 'hintUnterminatedBraceQuant'],
            ['Unexpected token', 'hintUnexpectedToken'],
            ['Unexpected trailing input', 'hintUnexpectedTrailing'],
            ['Cannot quantify anchor', 'hintCannotQuantifyAnchor'],
            ['Backreference to undefined group', 'hintUndefinedBackref'],
            ['Duplicate group name', 'hintDuplicateGroupName'],
            ['Alternation lacks left-hand side', 'hintAlternationNoLhs'],
            ['Alternation lacks right-hand side', 'hintAlternationNoRhs'],
            ['Empty alternation', 'hintEmptyAlternation'],
            ['Inline modifiers', 'hintInlineModifiers'],
            ['Invalid \\xHH escape', 'hintInvalidHex'],
            ['Invalid \\uHHHH', 'hintInvalidUnicode'],
            ['Unterminated \\x{...}', 'hintUnterminatedHexBrace'],
            ['Unterminated \\u{...}', 'hintUnterminatedUnicodeBrace'],
            ['Unterminated \\p{...}', 'hintUnterminatedUnicodeProperty'],
            ['Expected { after \\p/\\P', 'hintUnicodePropertyMissingBrace'],
            ["Expected '<' after \\p/\\P", 'hintUnicodePropertyMissingBrace'],
            ['Invalid brace quantifier content', 'hintInvalidBraceQuantContent'],
            ['Invalid group name', 'hintInvalidGroupName'],
            ['Invalid quantifier range', 'hintInvalidQuantifierRange'],
            ['Invalid character range', 'hintInvalidCharacterRange'],
            ['Invalid flag', 'hintInvalidFlag'],
            ['Directive after pattern', 'hintDirectiveAfterPattern'],
            ['Directive must appear', 'hintDirectiveAfterPattern'],
            ['Malformed directive', 'hintMalformedDirective'],
            ['Unknown escape sequence', 'hintUnknownEscape'],
            ['Invalid quantifier', 'hintInvalidQuantifier'],
            ["Expected '<' after \\k", 'hintUnterminatedNamedBackref'],
            ['Invalid \\UHHHHHHHH escape', 'hintInvalidUnicodeLong'],
            ["Unmatched ')'", 'hintUnmatchedCloseParen'],
        ];
    }

    private static function hintUnterminatedGroup(string $msg, string $text, int $pos): string
    {
        return "This group was opened with '(' but never closed. Add a matching ')' to close the group.";
    }

    private static function hintEmptyCharacterClass(string $msg, string $text, int $pos): string
    {
        return "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. If you meant a literal '[', escape it with '\\['.";
    }

    private static function hintUnterminatedCharClass(string $msg, string $text, int $pos): string
    {
        return "This character class was opened with '[' but never closed. Add a matching ']' to close the character class.";
    }

    private static function hintUnterminatedNamedBackref(string $msg, string $text, int $pos): string
    {
        return "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'.";
    }

    private static function hintUnterminatedGroupName(string $msg, string $text, int $pos): string
    {
        return "Named groups use the syntax (?<name>...). Make sure to close the '<name>' with '>' before the group content.";
    }

    private static function hintUnterminatedLookahead(string $msg, string $text, int $pos): string
    {
        return "This lookahead was opened with '(?=' or '(?!' but never closed. Add a matching ')' to close the lookahead.";
    }

    private static function hintUnterminatedLookbehind(string $msg, string $text, int $pos): string
    {
        return "This lookbehind was opened with '(?<=' or '(?<!' but never closed. Add a matching ')' to close the lookbehind.";
    }

    private static function hintUnterminatedAtomicGroup(string $msg, string $text, int $pos): string
    {
        return "This atomic group was opened with '(?>' but never closed. Add a matching ')' to close the atomic group.";
    }

    private static function hintUnterminatedBraceQuant(string $msg, string $text, int $pos): string
    {
        return "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.";
    }

    private static function hintUnexpectedToken(string $msg, string $text, int $pos): string
    {
        if ($pos < strlen($text)) {
            $ch = $text[$pos];
            if ($ch === ')') {
                return "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.";
            } elseif ($ch === '|') {
                return "The alternation operator '|' requires expressions on both sides. Use 'a|b' to match either 'a' or 'b'.";
            }
        }
        return "This character appeared in an unexpected context.";
    }

    private static function hintUnexpectedTrailing(string $msg, string $text, int $pos): string
    {
        return "There is unexpected content after the pattern ended. Check for unmatched parentheses or extra characters.";
    }

    private static function hintCannotQuantifyAnchor(string $msg, string $text, int $pos): string
    {
        return "Anchors like ^, \$, \\b, \\B match positions, not characters, so they cannot be quantified with *, +, ?, or {}.";
    }

    private static function hintUndefinedBackref(string $msg, string $text, int $pos): string
    {
        return "Backreferences refer to previously captured groups. Make sure the group is defined before referencing it. STRling does not support forward references.";
    }

    private static function hintDuplicateGroupName(string $msg, string $text, int $pos): string
    {
        return "Each named group must have a unique name. Use different names for different groups, or use unnamed groups ().";
    }

    private static function hintAlternationNoLhs(string $msg, string $text, int $pos): string
    {
        return "The alternation operator '|' requires an expression on the left side. Use 'a|b' to match either 'a' or 'b'.";
    }

    private static function hintAlternationNoRhs(string $msg, string $text, int $pos): string
    {
        return "The alternation operator '|' requires an expression on the right side. Use 'a|b' to match either 'a' or 'b'.";
    }

    private static function hintEmptyAlternation(string $msg, string $text, int $pos): string
    {
        return "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.";
    }

    private static function hintInlineModifiers(string $msg, string $text, int $pos): string
    {
        return "STRling does not support inline modifiers like (?i) for case-insensitivity. Instead, use the %flags directive at the start of your pattern: '%flags i'";
    }

    private static function hintInvalidHex(string $msg, string $text, int $pos): string
    {
        return "Hex escapes must use valid hexadecimal digits (0-9, A-F). Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').";
    }

    private static function hintInvalidUnicode(string $msg, string $text, int $pos): string
    {
        return "Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.";
    }

    private static function hintUnterminatedHexBrace(string $msg, string $text, int $pos): string
    {
        return "Variable-length hex escapes use the syntax \\x{...}. Make sure to close the escape with '}'.";
    }

    private static function hintUnterminatedUnicodeBrace(string $msg, string $text, int $pos): string
    {
        return "Variable-length unicode escapes use the syntax \\u{...}. Make sure to close the escape with '}'.";
    }

    private static function hintUnterminatedUnicodeProperty(string $msg, string $text, int $pos): string
    {
        return "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. Make sure to close the property name with '}'.";
    }

    private static function hintUnicodePropertyMissingBrace(string $msg, string $text, int $pos): string
    {
        return "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. Use \\p{L} for letters, \\p{N} for numbers, etc.";
    }

    private static function hintInvalidBraceQuantContent(string $msg, string $text, int $pos): string
    {
        return "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'.";
    }

    private static function hintInvalidGroupName(string $msg, string $text, int $pos): string
    {
        return "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.";
    }

    private static function hintInvalidQuantifierRange(string $msg, string $text, int $pos): string
    {
        return "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). For example, use '{2,5}' or '{2,2}', not '{5,2}'.";
    }

    private static function hintInvalidCharacterRange(string $msg, string $text, int $pos): string
    {
        return "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. Reversed ranges like '[z-a]' are invalid.";
    }

    private static function hintInvalidFlag(string $msg, string $text, int $pos): string
    {
        return "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).";
    }

    private static function hintDirectiveAfterPattern(string $msg, string $text, int $pos): string
    {
        return "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). Move the directive to the top of the input on its own line.";
    }

    private static function hintMalformedDirective(string $msg, string $text, int $pos): string
    {
        return "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, for example '%flags i' on a line by itself.";
    }

    private static function hintUnknownEscape(string $msg, string $text, int $pos): string
    {
        if (preg_match('/Unknown escape sequence \\\\?(.)/', $msg, $m)) {
            $ch = $m[1];
            if ($ch === 'z') {
                return "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?";
            }
            return "Unknown escape sequence '\\{$ch}'. If you intended a literal '{$ch}', remove the backslash or use a recognized escape.";
        }
        return "Unknown escape sequence. If you intended a literal character, remove the backslash or use a recognized escape.";
    }

    private static function hintInvalidQuantifier(string $msg, string $text, int $pos): string
    {
        if (preg_match("/Invalid quantifier '(.)'/", $msg, $m)) {
            $ch = $m[1];
            return "The quantifier '{$ch}' must follow an atom (a character or group). Place '{$ch}' after the thing it should quantify, e.g., 'a{$ch}'.";
        }
        return "Quantifiers must follow an atom (a character or group). Place the quantifier after the thing it should quantify.";
    }

    private static function hintUnmatchedCloseParen(string $msg, string $text, int $pos): string
    {
        return "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.";
    }

    private static function hintInvalidUnicodeLong(string $msg, string $text, int $pos): string
    {
        return "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). "
             . "Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.";
    }
}
