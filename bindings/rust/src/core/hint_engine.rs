//! STRling Hint Engine - Context-Aware Error Hints
//!
//! This module provides intelligent, beginner-friendly hints for common syntax errors.
//! The hint engine maps specific error types and contexts to instructional messages
//! that help users understand and fix their mistakes.

use regex::Regex;

/// Hint generator function type
type HintGenerator = fn(&str, &str, usize) -> String;

/// Registry of error-pattern keys mapped to hint generator functions.
static HINT_GENERATORS: &[(&str, HintGenerator)] = &[
    ("Unterminated group", hint_unterminated_group),
    ("Empty character class", hint_empty_character_class),
    ("Unterminated character class", hint_unterminated_char_class),
    ("Unterminated named backref", hint_unterminated_named_backref),
    ("Unterminated group name", hint_unterminated_group_name),
    ("Unterminated lookahead", hint_unterminated_lookahead),
    ("Unterminated lookbehind", hint_unterminated_lookbehind),
    ("Unterminated atomic group", hint_unterminated_atomic_group),
    ("Unterminated {m,n}", hint_unterminated_brace_quant),
    ("Unterminated {n}", hint_unterminated_brace_quant),
    ("Unexpected token", hint_unexpected_token),
    ("Unexpected trailing input", hint_unexpected_trailing),
    ("Cannot quantify anchor", hint_cannot_quantify_anchor),
    ("Backreference to undefined group", hint_undefined_backref),
    ("Duplicate group name", hint_duplicate_group_name),
    ("Alternation lacks left-hand side", hint_alternation_no_lhs),
    ("Alternation lacks right-hand side", hint_alternation_no_rhs),
    ("Inline modifiers", hint_inline_modifiers),
    ("Invalid \\xHH escape", hint_invalid_hex),
    ("Invalid \\uHHHH", hint_invalid_unicode),
    ("Unterminated \\x{...}", hint_unterminated_hex_brace),
    ("Unterminated \\u{...}", hint_unterminated_unicode_brace),
    ("Unterminated \\p{...}", hint_unterminated_unicode_property),
    ("Expected { after \\p/\\P", hint_unicode_property_missing_brace),
    ("Invalid brace quantifier content", hint_invalid_brace_quant_content),
    ("Invalid group name", hint_invalid_group_name),
    ("Invalid quantifier range", hint_invalid_quantifier_range),
    ("Invalid character range", hint_invalid_character_range),
    ("Invalid flag", hint_invalid_flag),
    ("Directive after pattern", hint_directive_after_pattern),
    ("Malformed directive", hint_malformed_directive),
    ("Empty alternation", hint_empty_alternation),
    ("Unknown escape sequence", hint_unknown_escape),
    ("Invalid quantifier", hint_invalid_quantifier),
    ("Expected '<' after \\k", hint_unterminated_named_backref),
    ("Incomplete quantifier", hint_incomplete_quantifier),
    ("Invalid \\UHHHHHHHH escape", hint_invalid_unicode_long),
    ("Unmatched ')'", hint_unmatched_close_paren),
];

/// Get a hint for a given error message and context
///
/// # Arguments
///
/// * `error_message` - The error message from the parser
/// * `text` - The full input text being parsed
/// * `pos` - The position where the error occurred
///
/// # Returns
///
/// An optional hint string providing guidance on how to fix the error
pub fn get_hint(error_message: &str, text: &str, pos: usize) -> Option<String> {
    for (pattern, generator) in HINT_GENERATORS {
        if error_message.contains(pattern) {
            return Some(generator(error_message, text, pos));
        }
    }
    None
}

fn hint_unterminated_group(_msg: &str, _text: &str, _pos: usize) -> String {
    "This group was opened with '(' but never closed. Add a matching ')' to close the group.".to_string()
}

fn hint_empty_character_class(_msg: &str, _text: &str, _pos: usize) -> String {
    "Empty character class '[]' detected. Character classes must contain at least one element (e.g., [a-z]) \u{2014} do not leave them empty. If you meant a literal '[', escape it with '\\['.".to_string()
}

fn hint_unterminated_char_class(_msg: &str, _text: &str, _pos: usize) -> String {
    "This character class was opened with '[' but never closed. Add a matching ']' to close the character class.".to_string()
}

fn hint_unterminated_named_backref(_msg: &str, _text: &str, _pos: usize) -> String {
    "Named backreferences use the syntax \\k<name>. Make sure to close the '<name>' with '>'.".to_string()
}

fn hint_unterminated_group_name(_msg: &str, _text: &str, _pos: usize) -> String {
    "Named groups use the syntax (?<name>...). Make sure to close the '<name>' with '>' before the group content.".to_string()
}

fn hint_unterminated_lookahead(_msg: &str, _text: &str, _pos: usize) -> String {
    "This lookahead was opened with '(?=' or '(?!' but never closed. Add a matching ')' to close the lookahead.".to_string()
}

fn hint_unterminated_lookbehind(_msg: &str, _text: &str, _pos: usize) -> String {
    "This lookbehind was opened with '(?<=' or '(?<!' but never closed. Add a matching ')' to close the lookbehind.".to_string()
}

fn hint_unterminated_atomic_group(_msg: &str, _text: &str, _pos: usize) -> String {
    "This atomic group was opened with '(?>' but never closed. Add a matching ')' to close the atomic group.".to_string()
}

fn hint_unterminated_brace_quant(_msg: &str, _text: &str, _pos: usize) -> String {
    "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.".to_string()
}

fn hint_unexpected_token(_msg: &str, text: &str, pos: usize) -> String {
    if pos < text.len() {
        let ch = text.as_bytes()[pos] as char;
        if ch == ')' {
            return "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.".to_string();
        } else if ch == '|' {
            return "The alternation operator '|' requires expressions on both sides. Use 'a|b' to match either 'a' or 'b'.".to_string();
        }
    }
    "This character appeared in an unexpected context.".to_string()
}

fn hint_unexpected_trailing(_msg: &str, _text: &str, _pos: usize) -> String {
    "There is unexpected content after the pattern ended. Check for unmatched parentheses or extra characters.".to_string()
}

fn hint_cannot_quantify_anchor(_msg: &str, _text: &str, _pos: usize) -> String {
    "Anchors like ^, $, \\b, \\B match positions, not characters, so they cannot be quantified with *, +, ?, or {}.".to_string()
}

fn hint_undefined_backref(_msg: &str, _text: &str, _pos: usize) -> String {
    "Backreferences refer to previously captured groups. Make sure the group is defined before referencing it. STRling does not support forward references.".to_string()
}

fn hint_duplicate_group_name(_msg: &str, _text: &str, _pos: usize) -> String {
    "Each named group must have a unique name. Use different names for different groups, or use unnamed groups ().".to_string()
}

fn hint_alternation_no_lhs(_msg: &str, _text: &str, _pos: usize) -> String {
    "The alternation operator '|' requires an expression on the left side. Use 'a|b' to match either 'a' or 'b'.".to_string()
}

fn hint_alternation_no_rhs(_msg: &str, _text: &str, _pos: usize) -> String {
    "The alternation operator '|' requires an expression on the right side. Use 'a|b' to match either 'a' or 'b'.".to_string()
}

fn hint_inline_modifiers(_msg: &str, _text: &str, _pos: usize) -> String {
    "STRling does not support inline modifiers like (?i) for case-insensitivity. Instead, use the %flags directive at the start of your pattern: '%flags i'".to_string()
}

fn hint_invalid_hex(_msg: &str, _text: &str, _pos: usize) -> String {
    "Hex escapes must use valid hexadecimal digits (0-9, A-F). Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').".to_string()
}

fn hint_invalid_unicode(_msg: &str, _text: &str, _pos: usize) -> String {
    "Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.".to_string()
}

fn hint_unterminated_hex_brace(_msg: &str, _text: &str, _pos: usize) -> String {
    "Variable-length hex escapes use the syntax \\x{...}. Make sure to close the escape with '}'.".to_string()
}

fn hint_unterminated_unicode_brace(_msg: &str, _text: &str, _pos: usize) -> String {
    "Variable-length unicode escapes use the syntax \\u{...}. Make sure to close the escape with '}'.".to_string()
}

fn hint_unterminated_unicode_property(_msg: &str, _text: &str, _pos: usize) -> String {
    "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. Make sure to close the property name with '}'.".to_string()
}

fn hint_unicode_property_missing_brace(_msg: &str, _text: &str, _pos: usize) -> String {
    "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. Use \\p{L} for letters, \\p{N} for numbers, etc.".to_string()
}

fn hint_invalid_brace_quant_content(_msg: &str, _text: &str, _pos: usize) -> String {
    "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. Only numbers are valid inside braces \u{2014} to match a literal '{', escape it with '\\{'.".to_string()
}

fn hint_invalid_group_name(_msg: &str, _text: &str, _pos: usize) -> String {
    "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.".to_string()
}

fn hint_invalid_quantifier_range(_msg: &str, _text: &str, _pos: usize) -> String {
    "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). For example, use '{2,5}' or '{2,2}', not '{5,2}'.".to_string()
}

fn hint_invalid_character_range(_msg: &str, _text: &str, _pos: usize) -> String {
    "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. Reversed ranges like '[z-a]' are invalid.".to_string()
}

fn hint_invalid_flag(_msg: &str, _text: &str, _pos: usize) -> String {
    "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).".to_string()
}

fn hint_directive_after_pattern(_msg: &str, _text: &str, _pos: usize) -> String {
    "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). Move the directive to the top of the input on its own line.".to_string()
}

fn hint_malformed_directive(_msg: &str, _text: &str, _pos: usize) -> String {
    "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, for example '%flags i' on a line by itself.".to_string()
}

fn hint_empty_alternation(_msg: &str, _text: &str, _pos: usize) -> String {
    "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.".to_string()
}

fn hint_unknown_escape(msg: &str, _text: &str, _pos: usize) -> String {
    let re = Regex::new(r"Unknown escape sequence \\?(.)")
        .expect("valid regex");
    let ch = re.captures(msg)
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().to_string())
        .unwrap_or_else(|| "\\z".to_string());
    if ch == "z" {
        return "'\\z' is not a recognized escape sequence. Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?".to_string();
    }
    format!("Unknown escape sequence '\\{ch}'. If you intended a literal '{ch}', remove the backslash or use a recognized escape.")
}

fn hint_invalid_quantifier(msg: &str, _text: &str, _pos: usize) -> String {
    let re = Regex::new(r"Invalid quantifier '(.)'")
        .expect("valid regex");
    let ch = re.captures(msg)
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().to_string())
        .unwrap_or_else(|| "*".to_string());
    format!("The quantifier '{ch}' must follow an atom (a character or group). Place '{ch}' after the thing it should quantify, e.g., 'a{ch}'.")
}

fn hint_incomplete_quantifier(_msg: &str, _text: &str, _pos: usize) -> String {
    "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. Make sure to close the quantifier with '}' and provide valid numbers.".to_string()
}

fn hint_invalid_unicode_long(_msg: &str, _text: &str, _pos: usize) -> String {
    "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.".to_string()
}

fn hint_unmatched_close_paren(_msg: &str, _text: &str, _pos: usize) -> String {
    "This ')' does not have a matching opening '('. Remove the extra ')' or add an opening '(' earlier in the pattern.".to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_unterminated_group_hint() {
        let hint = get_hint("Unterminated group", "test", 0);
        assert!(hint.is_some());
        assert!(hint.unwrap().contains("matching ')'"));
    }

    #[test]
    fn test_invalid_flag_hint() {
        let hint = get_hint("Invalid flag 'z'", "test", 0);
        assert!(hint.is_some());
        assert!(hint.unwrap().contains("Valid flags"));
    }

    #[test]
    fn test_no_hint_for_unknown_error() {
        let hint = get_hint("Some unknown error", "test", 0);
        assert!(hint.is_none());
    }
}
