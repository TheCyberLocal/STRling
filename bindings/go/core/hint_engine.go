// Package core contains the fundamental data structures and types for the STRling
// compiler, including AST nodes, IR nodes, and error types.
package core

import (
	"fmt"
	"strings"
)

// GenericHintFallback is the contractual default for expected_hint in conformance
// fixtures when no specific hint pattern matches.
const GenericHintFallback = "Check the STRling documentation for help with this syntax."

// hintMapping associates an error message substring with a static hint string.
// A nil hintFunc and empty staticHint means "use dynamic generator".
type hintMapping struct {
	pattern    string
	staticHint string
	dynamic    bool
}

var hintTable = []hintMapping{
	{"Unterminated group",
		"This group was opened with '(' but never closed. " +
			"Add a matching ')' to close the group.", false},
	{"Empty character class",
		"Empty character class '[]' detected. " +
			"Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. " +
			"If you meant a literal '[', escape it with '\\['.", false},
	{"Unterminated character class",
		"This character class was opened with '[' but never closed. " +
			"Add a matching ']' to close the character class.", false},
	{"Unterminated named backref",
		"Named backreferences use the syntax \\k<name>. " +
			"Make sure to close the '<name>' with '>'.", false},
	{"Unterminated group name",
		"Named groups use the syntax (?<name>...). " +
			"Make sure to close the '<name>' with '>' before the group content.", false},
	{"Unterminated lookahead",
		"This lookahead was opened with '(?=' or '(?!' but never closed. " +
			"Add a matching ')' to close the lookahead.", false},
	{"Unterminated lookbehind",
		"This lookbehind was opened with '(?<=' or '(?<!' but never closed. " +
			"Add a matching ')' to close the lookbehind.", false},
	{"Unterminated atomic group",
		"This atomic group was opened with '(?>' but never closed. " +
			"Add a matching ')' to close the atomic group.", false},
	{"Unterminated {m,n}",
		"Brace quantifiers use the syntax {m,n} or {n}. " +
			"Make sure to close the quantifier with '}'.", false},
	{"Unterminated {n}",
		"Brace quantifiers use the syntax {m,n} or {n}. " +
			"Make sure to close the quantifier with '}'.", false},
	{"Unexpected token", "", true},
	{"Unexpected trailing input",
		"There is unexpected content after the pattern ended. " +
			"Check for unmatched parentheses or extra characters.", false},
	{"Cannot quantify anchor",
		"Anchors like ^, $, \\b, \\B match positions, not characters, " +
			"so they cannot be quantified with *, +, ?, or {}.", false},
	{"Backreference to undefined group",
		"Backreferences refer to previously captured groups. " +
			"Make sure the group is defined before referencing it. " +
			"STRling does not support forward references.", false},
	{"Duplicate group name",
		"Each named group must have a unique name. " +
			"Use different names for different groups, or use unnamed groups ().", false},
	{"Alternation lacks left-hand side",
		"The alternation operator '|' requires an expression on the left side. " +
			"Use 'a|b' to match either 'a' or 'b'.", false},
	{"Alternation lacks right-hand side",
		"The alternation operator '|' requires an expression on the right side. " +
			"Use 'a|b' to match either 'a' or 'b'.", false},
	{"Inline modifiers",
		"STRling does not support inline modifiers like (?i) for case-insensitivity. " +
			"Instead, use the %flags directive at the start of your pattern: '%flags i'", false},
	{"Invalid \\xHH escape",
		"Hex escapes must use valid hexadecimal digits (0-9, A-F). " +
			"Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').", false},
	{"Invalid \\uHHHH",
		"Unicode escapes must use valid hexadecimal digits (0-9, A-F). " +
			"Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.", false},
	{"Unterminated \\x{...}",
		"Variable-length hex escapes use the syntax \\x{...}. " +
			"Make sure to close the escape with '}'.", false},
	{"Unterminated \\u{...}",
		"Variable-length unicode escapes use the syntax \\u{...}. " +
			"Make sure to close the escape with '}'.", false},
	{"Unterminated \\p{...}",
		"Unicode property escapes use the syntax \\p{Property} or \\P{Property}. " +
			"Make sure to close the property name with '}'.", false},
	{"Expected { after \\p/\\P",
		"Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. " +
			"Use \\p{L} for letters, \\p{N} for numbers, etc.", false},
	{"Invalid brace quantifier content",
		"Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. " +
			"Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'.", false},
	{"Invalid group name",
		"Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. " +
			"Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.", false},
	{"Invalid quantifier range",
		"Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). " +
			"For example, use '{2,5}' or '{2,2}', not '{5,2}'.", false},
	{"Invalid character range",
		"Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. " +
			"Reversed ranges like '[z-a]' are invalid.", false},
	{"Invalid flag",
		"Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).", false},
	{"Directive after pattern",
		"Directives such as '%flags' must appear at the start of the pattern (before any pattern content). " +
			"Move the directive to the top of the input on its own line.", false},
	{"Malformed directive",
		"This directive looks malformed. Directives begin with '%' and must be one of the supported forms, " +
			"for example '%flags i' on a line by itself.", false},
	{"Empty alternation",
		"One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.", false},
	{"Unknown escape sequence", "", true},
	{"Invalid quantifier", "", true},
	{"Expected '<' after \\k",
		"Named backreferences use the syntax \\k<name>. " +
			"Make sure to close the '<name>' with '>'.", false},
	{"Incomplete quantifier",
		"Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. " +
			"Make sure to close the quantifier with '}' and provide valid numbers.", false},
	{"Invalid \\UHHHHHHHH escape",
		"8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). " +
			"Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.", false},
	{"Unmatched ')'",
		"This ')' does not have a matching opening '('. " +
			"Remove the extra ')' or add an opening '(' earlier in the pattern.", false},
}

// GetHint returns an instructional hint for a parse error.
// Returns empty string if no specific hint matches.
func GetHint(message, text string, pos int) string {
	for _, m := range hintTable {
		if strings.Contains(message, m.pattern) {
			if !m.dynamic {
				return m.staticHint
			}
			// Dynamic generators
			switch m.pattern {
			case "Unexpected token":
				return hintUnexpectedToken(text, pos)
			case "Unknown escape sequence":
				return hintUnknownEscape(message)
			case "Invalid quantifier":
				return hintInvalidQuantifier(message)
			}
			return ""
		}
	}
	return ""
}

// GetHintOrFallback returns a hint, falling back to GenericHintFallback.
func GetHintOrFallback(message, text string, pos int) string {
	hint := GetHint(message, text, pos)
	if hint == "" {
		return GenericHintFallback
	}
	return hint
}

func hintUnexpectedToken(text string, pos int) string {
	if pos < len(text) {
		ch := text[pos]
		if ch == ')' {
			return "This ')' character does not have a matching opening '('. " +
				"Did you mean to escape it with '\\)'?"
		}
		if ch == '|' {
			return "The alternation operator '|' requires expressions on both sides. " +
				"Use 'a|b' to match either 'a' or 'b'."
		}
	}
	return "This character appeared in an unexpected context."
}

func hintUnknownEscape(msg string) string {
	prefix := "Unknown escape sequence \\"
	idx := strings.Index(msg, prefix)
	if idx >= 0 {
		rest := msg[idx+len(prefix):]
		// Skip extra backslash if present
		if len(rest) > 0 && rest[0] == '\\' {
			rest = rest[1:]
		}
		if len(rest) > 0 {
			ch := rest[0]
			if ch == 'z' {
				return "'\\z' is not a recognized escape sequence. " +
					"Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?"
			}
			return fmt.Sprintf("Unknown escape sequence '\\%c'. "+
				"If you intended a literal '%c', remove the backslash or use a recognized escape.", ch, ch)
		}
	}
	return "Unknown escape sequence '\\z'. " +
		"If you intended a literal 'z', remove the backslash or use a recognized escape."
}

func hintInvalidQuantifier(msg string) string {
	ch := '*'
	prefix := "Invalid quantifier '"
	idx := strings.Index(msg, prefix)
	if idx >= 0 {
		rest := msg[idx+len(prefix):]
		if len(rest) > 0 {
			ch = rune(rest[0])
		}
	}
	return fmt.Sprintf("The quantifier '%c' must follow an atom (a character or group). "+
		"Place '%c' after the thing it should quantify, e.g., 'a%c'.", ch, ch, ch)
}
