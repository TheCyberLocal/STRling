/*
 * STRling Hint Engine — Context-Aware Error Hints (C Binding)
 *
 * Mirrors the TypeScript reference implementation pattern-for-pattern.
 * All hint strings are static constants — zero heap allocation.
 */

#include "hint_engine.h"
#include <string.h>
#include <stdio.h>

/* ============================================================================
 * Static hint strings (exact mirrors of TypeScript hint_engine.ts)
 * ============================================================================ */

static const char HINT_UNTERMINATED_GROUP[] =
    "This group was opened with '(' but never closed. "
    "Add a matching ')' to close the group.";

static const char HINT_EMPTY_CHAR_CLASS[] =
    "Empty character class '[]' detected. "
    "Character classes must contain at least one element (e.g., [a-z]) — do not leave them empty. "
    "If you meant a literal '[', escape it with '\\['.";

static const char HINT_UNTERMINATED_CHAR_CLASS[] =
    "This character class was opened with '[' but never closed. "
    "Add a matching ']' to close the character class.";

static const char HINT_UNTERMINATED_NAMED_BACKREF[] =
    "Named backreferences use the syntax \\k<name>. "
    "Make sure to close the '<name>' with '>'.";

static const char HINT_UNTERMINATED_GROUP_NAME[] =
    "Named groups use the syntax (?<name>...). "
    "Make sure to close the '<name>' with '>' before the group content.";

static const char HINT_UNTERMINATED_LOOKAHEAD[] =
    "This lookahead was opened with '(?=' or '(?!' but never closed. "
    "Add a matching ')' to close the lookahead.";

static const char HINT_UNTERMINATED_LOOKBEHIND[] =
    "This lookbehind was opened with '(?<=' or '(?<!' but never closed. "
    "Add a matching ')' to close the lookbehind.";

static const char HINT_UNTERMINATED_ATOMIC_GROUP[] =
    "This atomic group was opened with '(?>' but never closed. "
    "Add a matching ')' to close the atomic group.";

static const char HINT_UNTERMINATED_BRACE_QUANT[] =
    "Brace quantifiers use the syntax {m,n} or {n}. "
    "Make sure to close the quantifier with '}'.";

static const char HINT_UNEXPECTED_TOKEN_DEFAULT[] =
    "This character appeared in an unexpected context.";

static const char HINT_UNEXPECTED_TOKEN_PAREN[] =
    "This ')' character does not have a matching opening '('. "
    "Did you mean to escape it with '\\)'?";

static const char HINT_UNEXPECTED_TOKEN_PIPE[] =
    "The alternation operator '|' requires expressions on both sides. "
    "Use 'a|b' to match either 'a' or 'b'.";

static const char HINT_UNEXPECTED_TRAILING[] =
    "There is unexpected content after the pattern ended. "
    "Check for unmatched parentheses or extra characters.";

static const char HINT_CANNOT_QUANTIFY_ANCHOR[] =
    "Anchors like ^, $, \\b, \\B match positions, not characters, "
    "so they cannot be quantified with *, +, ?, or {}.";

static const char HINT_UNDEFINED_BACKREF[] =
    "Backreferences refer to previously captured groups. "
    "Make sure the group is defined before referencing it. "
    "STRling does not support forward references.";

static const char HINT_DUPLICATE_GROUP_NAME[] =
    "Each named group must have a unique name. "
    "Use different names for different groups, or use unnamed groups ().";

static const char HINT_ALTERNATION_NO_LHS[] =
    "The alternation operator '|' requires an expression on the left side. "
    "Use 'a|b' to match either 'a' or 'b'.";

static const char HINT_ALTERNATION_NO_RHS[] =
    "The alternation operator '|' requires an expression on the right side. "
    "Use 'a|b' to match either 'a' or 'b'.";

static const char HINT_INLINE_MODIFIERS[] =
    "STRling does not support inline modifiers like (?i) for case-insensitivity. "
    "Instead, use the %flags directive at the start of your pattern: '%flags i'";

static const char HINT_INVALID_HEX[] =
    "Hex escapes must use valid hexadecimal digits (0-9, A-F). "
    "Use \\xHH for 2-digit hex codes (e.g., \\x41 for 'A').";

static const char HINT_INVALID_UNICODE[] =
    "Unicode escapes must use valid hexadecimal digits (0-9, A-F). "
    "Use \\uHHHH for 4-digit codes or \\u{...} for variable-length codes.";

static const char HINT_UNTERMINATED_HEX_BRACE[] =
    "Variable-length hex escapes use the syntax \\x{...}. "
    "Make sure to close the escape with '}'.";

static const char HINT_UNTERMINATED_UNICODE_BRACE[] =
    "Variable-length unicode escapes use the syntax \\u{...}. "
    "Make sure to close the escape with '}'.";

static const char HINT_UNTERMINATED_UNICODE_PROPERTY[] =
    "Unicode property escapes use the syntax \\p{Property} or \\P{Property}. "
    "Make sure to close the property name with '}'.";

static const char HINT_UNICODE_PROPERTY_MISSING_BRACE[] =
    "Unicode property escapes require braces: \\p{Letter} or \\P{Letter}. "
    "Use \\p{L} for letters, \\p{N} for numbers, etc.";

static const char HINT_INVALID_BRACE_QUANT_CONTENT[] =
    "Brace quantifiers require numeric digits: use {n}, {m,n}, or {m,}. "
    "Only numbers are valid inside braces — to match a literal '{', escape it with '\\{'.";

static const char HINT_INVALID_GROUP_NAME[] =
    "Named groups require identifiers: IDENTIFIER = letter or '_' followed by letters, digits or '_'. "
    "Choose a name that starts with a letter or underscore and contains only letters, digits, or underscores.";

static const char HINT_INVALID_QUANTIFIER_RANGE[] =
    "Quantifier ranges must have the minimum less than or equal to the maximum (m <= n). "
    "For example, use '{2,5}' or '{2,2}', not '{5,2}'.";

static const char HINT_INVALID_CHAR_RANGE[] =
    "Character ranges must be ascending, e.g., '[a-z]' or '[0-9]'. "
    "Reversed ranges like '[z-a]' are invalid.";

static const char HINT_INVALID_FLAG[] =
    "Unknown flag. Valid flags are: i (case-insensitive), m (multiline), s (dotAll), u (unicode), x (extended/free-spacing).";

static const char HINT_EMPTY_ALTERNATION[] =
    "One of the alternation branches is empty. Remove the empty branch or provide an expression, e.g., 'a|b' instead of 'a||b'.";

static const char HINT_DIRECTIVE_AFTER_PATTERN[] =
    "Directives such as '%flags' must appear at the start of the pattern (before any pattern content). "
    "Move the directive to the top of the input on its own line.";

static const char HINT_MALFORMED_DIRECTIVE[] =
    "This directive looks malformed. Directives begin with '%' and must be one of the supported forms, "
    "for example '%flags i' on a line by itself.";

static const char HINT_INCOMPLETE_QUANTIFIER[] =
    "Brace quantifiers require a complete form: {n}, {m,n}, or {m,}. "
    "Make sure to close the quantifier with '}' and provide valid numbers.";

static const char HINT_INVALID_UNICODE_LONG[] =
    "8-digit Unicode escapes must use valid hexadecimal digits (0-9, A-F). "
    "Use \\UHHHHHHHH for 8-digit codes or \\u{...} for variable-length codes.";

static const char HINT_UNMATCHED_CLOSE_PAREN[] =
    "This ')' does not have a matching opening '('. "
    "Remove the extra ')' or add an opening '(' earlier in the pattern.";

/* ============================================================================
 * Pattern table: error message substring → static hint pointer
 *
 * Order matters: first match wins (same as TS iteration over Map).
 * ============================================================================ */

typedef struct {
    const char* pattern;
    const char* hint;
} HintMapping;

static const HintMapping HINT_TABLE[] = {
    { "Unterminated group",                  HINT_UNTERMINATED_GROUP },
    { "Empty character class",               HINT_EMPTY_CHAR_CLASS },
    { "Unterminated character class",        HINT_UNTERMINATED_CHAR_CLASS },
    { "Unterminated named backref",          HINT_UNTERMINATED_NAMED_BACKREF },
    { "Unterminated group name",             HINT_UNTERMINATED_GROUP_NAME },
    { "Unterminated lookahead",              HINT_UNTERMINATED_LOOKAHEAD },
    { "Unterminated lookbehind",             HINT_UNTERMINATED_LOOKBEHIND },
    { "Unterminated atomic group",           HINT_UNTERMINATED_ATOMIC_GROUP },
    { "Unterminated {m,n}",                  HINT_UNTERMINATED_BRACE_QUANT },
    { "Unterminated {n}",                    HINT_UNTERMINATED_BRACE_QUANT },
    { "Unexpected token",                    NULL }, /* handled specially */
    { "Unexpected trailing input",           HINT_UNEXPECTED_TRAILING },
    { "Cannot quantify anchor",              HINT_CANNOT_QUANTIFY_ANCHOR },
    { "Backreference to undefined group",    HINT_UNDEFINED_BACKREF },
    { "Duplicate group name",                HINT_DUPLICATE_GROUP_NAME },
    { "Alternation lacks left-hand side",    HINT_ALTERNATION_NO_LHS },
    { "Alternation lacks right-hand side",   HINT_ALTERNATION_NO_RHS },
    { "Inline modifiers",                    HINT_INLINE_MODIFIERS },
    { "Invalid \\xHH escape",               HINT_INVALID_HEX },
    { "Invalid \\uHHHH",                    HINT_INVALID_UNICODE },
    { "Unterminated \\x{...}",              HINT_UNTERMINATED_HEX_BRACE },
    { "Unterminated \\u{...}",              HINT_UNTERMINATED_UNICODE_BRACE },
    { "Unterminated \\p{...}",              HINT_UNTERMINATED_UNICODE_PROPERTY },
    { "Expected { after \\p/\\P",           HINT_UNICODE_PROPERTY_MISSING_BRACE },
    { "Invalid brace quantifier content",    HINT_INVALID_BRACE_QUANT_CONTENT },
    { "Invalid group name",                  HINT_INVALID_GROUP_NAME },
    { "Invalid quantifier range",            HINT_INVALID_QUANTIFIER_RANGE },
    { "Invalid character range",             HINT_INVALID_CHAR_RANGE },
    { "Invalid flag",                        HINT_INVALID_FLAG },
    { "Directive after pattern",             HINT_DIRECTIVE_AFTER_PATTERN },
    { "Malformed directive",                 HINT_MALFORMED_DIRECTIVE },
    { "Empty alternation",                   HINT_EMPTY_ALTERNATION },
    { "Unknown escape sequence",             NULL }, /* handled specially */
    { "Invalid quantifier",                  NULL }, /* handled specially */
    { "Expected '<' after \\k",             HINT_UNTERMINATED_NAMED_BACKREF },
    { "Incomplete quantifier",               HINT_INCOMPLETE_QUANTIFIER },
    { "Invalid \\UHHHHHHHH escape",         HINT_INVALID_UNICODE_LONG },
    { "Unmatched ')'",                       HINT_UNMATCHED_CLOSE_PAREN },
    { NULL, NULL } /* sentinel */
};

/* ============================================================================
 * Dynamic hint generators (for patterns that need context)
 * ============================================================================ */

/*
 * Generate hint for "Unexpected token" — context-dependent on the char
 * at the error position.
 */
static const char* hint_unexpected_token(const char* pattern, size_t fail_index) {
    if (pattern && fail_index < strlen(pattern)) {
        char ch = pattern[fail_index];
        if (ch == ')') return HINT_UNEXPECTED_TOKEN_PAREN;
        if (ch == '|') return HINT_UNEXPECTED_TOKEN_PIPE;
    }
    return HINT_UNEXPECTED_TOKEN_DEFAULT;
}

/*
 * Generate hint for "Unknown escape sequence" — builds a dynamic message.
 * Returns a pointer to a thread-local static buffer.
 */
static const char* hint_unknown_escape(const char* error_message) {
    static char buf[256];
    /* Try to extract the escape character from the message */
    const char* prefix = "Unknown escape sequence \\";
    const char* p = strstr(error_message, prefix);
    if (p) {
        p += strlen(prefix);
        /* Skip an extra backslash if present */
        if (*p == '\\') p++;
        char ch = *p;
        if (ch == 'z') {
            snprintf(buf, sizeof(buf),
                "'\\z' is not a recognized escape sequence. "
                "Did you mean '\\Z' (end of string) or escape the literal 'z' as 'z'?");
            return buf;
        }
        if (ch) {
            snprintf(buf, sizeof(buf),
                "Unknown escape sequence '\\%c'. "
                "If you intended a literal '%c', remove the backslash or use a recognized escape.",
                ch, ch);
            return buf;
        }
    }
    snprintf(buf, sizeof(buf),
        "Unknown escape sequence '\\z'. "
        "If you intended a literal 'z', remove the backslash or use a recognized escape.");
    return buf;
}

/*
 * Generate hint for "Invalid quantifier" — extracts the quantifier char.
 * Returns a pointer to a thread-local static buffer.
 */
static const char* hint_invalid_quantifier(const char* error_message) {
    static char buf[256];
    /* Try to extract the quantifier character from "Invalid quantifier 'X'" */
    const char* q = strstr(error_message, "Invalid quantifier '");
    char ch = '*';
    if (q) {
        q += strlen("Invalid quantifier '");
        if (*q) ch = *q;
    }
    snprintf(buf, sizeof(buf),
        "The quantifier '%c' must follow an atom (a character or group). "
        "Place '%c' after the thing it should quantify, e.g., 'a%c'.",
        ch, ch, ch);
    return buf;
}

/* ============================================================================
 * Public API
 * ============================================================================ */

const char* strling_get_hint_static(const char* error_message,
                                    const char* pattern,
                                    size_t fail_index) {
    if (!error_message) return NULL;

    for (const HintMapping* m = HINT_TABLE; m->pattern; m++) {
        if (strstr(error_message, m->pattern)) {
            /* Static hint available directly */
            if (m->hint) return m->hint;

            /* Dynamic hint generators */
            if (strstr(m->pattern, "Unexpected token"))
                return hint_unexpected_token(pattern, fail_index);
            if (strstr(m->pattern, "Unknown escape sequence"))
                return hint_unknown_escape(error_message);
            if (strstr(m->pattern, "Invalid quantifier"))
                return hint_invalid_quantifier(error_message);

            return NULL;
        }
    }
    return NULL;
}

size_t strling_get_hint(const char* error_message,
                        const char* pattern,
                        size_t fail_index,
                        char* hint_buffer,
                        size_t buffer_size) {
    if (!error_message || !hint_buffer || buffer_size == 0) return 0;

    const char* hint = strling_get_hint_static(error_message, pattern, fail_index);
    if (!hint) hint = STRLING_GENERIC_HINT_FALLBACK;

    size_t len = strlen(hint);
    if (len < buffer_size) {
        memcpy(hint_buffer, hint, len + 1);
    } else {
        memcpy(hint_buffer, hint, buffer_size - 1);
        hint_buffer[buffer_size - 1] = '\0';
    }
    return len;
}
