/**
 * @file hint_engine.cpp
 * @brief STRling Hint Engine — Context-Aware Error Hints (C++ Binding)
 *
 * Mirrors the TypeScript reference implementation pattern-for-pattern.
 */

#include "strling/core/hint_engine.hpp"
#include <regex>
#include <vector>
#include <functional>

namespace strling {
namespace core {

// Forward declarations for dynamic hint generators
static std::string hintUnexpectedToken(const std::string& msg, const std::string& text, size_t pos);
static std::string hintUnknownEscape(const std::string& msg);
static std::string hintInvalidQuantifier(const std::string& msg);

// Static hint strings (exact mirrors of TypeScript hint_engine.ts)
struct HintMapping {
    const char* pattern;
    const char* staticHint;  // nullptr means use dynamic generator
};

static const std::vector<HintMapping> HINT_TABLE = {
    {"Unterminated group",
     "This group was opened with '(' but never closed. "
     "Add a matching ')' to close the group."},

    {"Empty character class",
     "Empty character class '[]' detected. "
     "Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. "
     "If you meant a literal '[', escape it with '\\['."},

    {"Unterminated character class",
     "This character class was opened with '[' but never closed. "
     "Add a matching ']' to close the character class."},

    {"Unterminated named backref",
     "Named backreferences use the syntax \\k<name>. "
     "Make sure to close the '<name>' with '>'."},

    {"Unterminated group name",
     "Named groups use the syntax (?<name>...). "
     "Make sure to close the '<name>' with '>' before the group content."},

    {"Unterminated lookahead",
     "This lookahead was opened with '(?=' or '(?!' but never closed. "
     "Add a matching ')' to close the lookahead."},

    {"Unterminated lookbehind",
     "This lookbehind was opened with '(?<=' or '(?<!' but never closed. "
     "Add a matching ')' to close the lookbehind."},

    {"Unterminated atomic group",
     "This atomic group was opened with '(?>' but never closed. "
     "Add a matching ')' to close the atomic group."},

    {"Unterminated {m,n}",
     "Brace quantifiers use the syntax {m,n} or {n}. "
     "Make sure to close the quantifier with '}'."},

    {"Unterminated {n}",
     "Brace quantifiers use the syntax {m,n} or {n}. "
     "Make sure to close the quantifier with '}'."},

    {"Unexpected token", nullptr},  // dynamic

    {"Unexpected trailing input",
     "There is unexpected content after the pattern ended. "
     "Check for unmatched parentheses or extra characters."},

    {"Cannot quantify anchor",
     "Anchors like ^, $, \\b, \\B match positions, not characters, "
     "so they cannot be quantified with *, +, ?, or {}."},

    {"Backreference to undefined group",
     "Backreferences refer to previously captured groups. "
     "Make sure the group is defined before referencing it. "
     "STRling does not support forward references."},

    {"Duplicate group name",
     "Each named group must have a unique name. "
     "Use different names for different groups, or use unnamed groups ()."},

    {"Alternation lacks left-hand side",
     "The alternation operator '|' requires an expression on the left side. "
     "Use 'a|b' to match either 'a' or 'b'."},

    {"Alternation lacks right-hand side",
     "The alternation operator '|' requires an expression on the right side. "
     "Use 'a|b' to match either 'a' or 'b'."},

    {"Inline modifiers",
     "STRling does not support inline modifiers like (?i) for case-insensitivity. "
     "Instead, use the %flags directive at the start of your pattern: '%flags i'"},

    {"Invalid \\xHH escape",
     "Hex escapes must use valid hexadecimal digits (0-9, A-F). "
     "Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A')."},

    {"Invalid \\uHHHH",
     "Unicode escapes must use valid hexadecimal digits (0-9, A-F). "
     "Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes."},

    {"Unterminated \\x{...}",
     "Variable-length hex escapes use the syntax \\x{...}. "
     "Make sure to close the escape with '}'."},

    {"Unterminated \\u{...}",
     "Variable-length unicode escapes use the syntax \\u{...}. "
     "Make sure to close the escape with '}'."},

    {"Unterminated \\p{...}",
     "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. "
     "Make sure to close the property name with '}'."},

    {"Expected { after \\p/\\P",
     "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. "
     "Use \\p{L} for letters, \\p{N} for numbers, etc."},

    {"Invalid brace quantifier content",
     "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. "
     "Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'."},

    {"Invalid group name",
     "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. "
     "Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores."},

    {"Invalid quantifier range",
     "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). "
     "For example, use '{2,5}' or '{2,2}', not '{5,2}'."},

    {"Invalid character range",
     "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. "
     "Reversed ranges like '[z-a]' are invalid."},

    {"Invalid flag",
     "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing)."},

    {"Directive after pattern",
     "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). "
     "Move the directive to the top of the input on its own line."},

    {"Malformed directive",
     "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, "
     "for example '%flags i' on a line by itself."},

    {"Empty alternation",
     "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'."},

    {"Unknown escape sequence", nullptr},  // dynamic

    {"Invalid quantifier", nullptr},  // dynamic

    {"Expected '<' after \\k",
     "Named backreferences use the syntax \\k<name>. "
     "Make sure to close the '<name>' with '>'."},

    {"Incomplete quantifier",
     "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. "
     "Make sure to close the quantifier with '}' and provide valid numbers."},

    {"Invalid \\UHHHHHHHH escape",
     "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). "
     "Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes."},

    {"Unmatched ')'",
     "This ')' does not have a matching opening '('. "
     "Remove the extra ')' or add an opening '(' earlier in the pattern."},
};

static std::string hintUnexpectedToken(const std::string& /*msg*/,
                                        const std::string& text,
                                        size_t pos) {
    if (pos < text.size()) {
        char ch = text[pos];
        if (ch == ')') {
            return "This ')' character does not have a matching opening '('. "
                   "Did you mean to escape it with '\\)'?";
        }
        if (ch == '|') {
            return "The alternation operator '|' requires expressions on both sides. "
                   "Use 'a|b' to match either 'a' or 'b'.";
        }
    }
    return "This character appeared in an unexpected context.";
}

static std::string hintUnknownEscape(const std::string& msg) {
    std::smatch m;
    std::regex re(R"(Unknown escape sequence \\\\?(.))", std::regex::ECMAScript);
    if (std::regex_search(msg, m, re) && m.size() > 1) {
        std::string ch = m[1].str();
        if (ch == "z") {
            return "'\\z' is not a recognized escape sequence. "
                   "Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?";
        }
        return "Unknown escape sequence '\\" + ch + "'. "
               "If you intended a literal '" + ch + "', remove the backslash or use a recognized escape.";
    }
    return "Unknown escape sequence '\\z'. "
           "If you intended a literal 'z', remove the backslash or use a recognized escape.";
}

static std::string hintInvalidQuantifier(const std::string& msg) {
    std::smatch m;
    std::regex re(R"(Invalid quantifier '(.)')", std::regex::ECMAScript);
    std::string ch = "*";
    if (std::regex_search(msg, m, re) && m.size() > 1) {
        ch = m[1].str();
    }
    return "The quantifier '" + ch + "' must follow an atom (a character or group). "
           "Place '" + ch + "' after the thing it should quantify, e.g., 'a" + ch + "'.";
}

std::optional<std::string> getHint(const std::string& errorMessage,
                                    const std::string& text,
                                    size_t pos) {
    for (const auto& mapping : HINT_TABLE) {
        if (errorMessage.find(mapping.pattern) != std::string::npos) {
            if (mapping.staticHint) {
                return std::string(mapping.staticHint);
            }
            // Dynamic generators
            std::string pat(mapping.pattern);
            if (pat == "Unexpected token") {
                return hintUnexpectedToken(errorMessage, text, pos);
            }
            if (pat == "Unknown escape sequence") {
                return hintUnknownEscape(errorMessage);
            }
            if (pat == "Invalid quantifier") {
                return hintInvalidQuantifier(errorMessage);
            }
            return std::nullopt;
        }
    }
    return std::nullopt;
}

std::string getHintOrFallback(const std::string& errorMessage,
                               const std::string& text,
                               size_t pos) {
    auto hint = getHint(errorMessage, text, pos);
    return hint.value_or(GENERIC_HINT_FALLBACK);
}

} // namespace core
} // namespace strling
