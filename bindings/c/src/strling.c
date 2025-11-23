#include "../include/strling.h"
#undef strling_compile
#undef strling_result_free
#include "core/nodes.h"
#include "core/errors.h"
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <jansson.h>
#include <stdint.h>

/* Forward declarations */
static char *escape_literal_for_pcre2_len(const char *lit, size_t len);

/* Helper to validate group names */
static bool is_valid_group_name(const char *name)
{
    if (!name || !*name)
        return false;
    if (!isalpha((unsigned char)*name) && *name != '_')
        return false;
    for (const char *p = name + 1; *p; p++)
    {
        if (!isalnum((unsigned char)*p) && *p != '_')
            return false;
    }
    return true;
}

const char *strling_version(void)
{
    return "3.0.0-alpha";
}

/* ==================== Error Handling ==================== */

void strling_error_free(STRlingError *error)
{
    if (!error)
        return;
    free(error->message);
    free(error->hint);
    free(error);
}

/* ==================== Flags ==================== */

STRlingFlags *strling_flags_create(void)
{
    STRlingFlags *flags = (STRlingFlags *)calloc(1, sizeof(STRlingFlags));
    if (!flags)
        return NULL;
    /* All flags default to false */
    return flags;
}

void strling_flags_free(STRlingFlags *flags)
{
    free(flags);
}

/* ==================== Compilation ==================== */

/* Helper to create error result */
static STRlingResult *create_error_result(const char *message, int position, const char *hint)
{
    STRlingResult *result = (STRlingResult *)calloc(1, sizeof(STRlingResult));
    if (!result)
        return NULL;

    result->error = (STRlingError *)malloc(sizeof(STRlingError));
    if (!result->error)
    {
        free(result);
        return NULL;
    }

    result->error->message = message ? strdup(message) : NULL;
    result->error->position = position;
    result->error->hint = hint ? strdup(hint) : NULL;
    result->pattern = NULL;

    return result;
}

/* escape_literal_for_pcre2_len - implementation defined later below */
/* Helper to create success result */
static STRlingResult *create_success_result(const char *pattern)
{
    STRlingResult *result = (STRlingResult *)calloc(1, sizeof(STRlingResult));
    if (!result)
        return NULL;

    result->pattern = pattern ? strdup(pattern) : NULL;
    result->error = NULL;

    return result;
}

/* Parse JSON and extract node type */
static const char *get_node_type(json_t *node)
{
    /* Support both 'type' and 'kind' field names for AST nodes to accept
       the JS artifact schema which uses 'kind' and older C JSON AST which
       may use 'type'. */
    json_t *type = json_object_get(node, "type");
    if (type && json_is_string(type))
        return json_string_value(type);
    json_t *kind = json_object_get(node, "kind");
    if (kind && json_is_string(kind))
        return json_string_value(kind);
    return NULL;
}

/* Escape literal string with known length (supports NUL bytes) */
static char *escape_literal_for_pcre2_len(const char *lit, size_t len)
{
    if (!lit)
        return strdup("");
    /* Allocate enough space for worst case: each byte could become \x{...} */
    char *result = (char *)malloc(len * 12 + 1);
    if (!result)
        return strdup("");
    char *p = result;
    for (size_t i = 0; i < len;)
    {
        unsigned char c = (unsigned char)lit[i];

        if (c == '\n')
        {
            *p++ = '\\';
            *p++ = 'n';
            i++;
        }
        else if (c == '\r')
        {
            *p++ = '\\';
            *p++ = 'r';
            i++;
        }
        else if (c == '\t')
        {
            *p++ = '\\';
            *p++ = 't';
            i++;
        }
        else if (c == '\f')
        {
            *p++ = '\\';
            *p++ = 'f';
            i++;
        }
        else if (c == 0x0B)
        {
            *p++ = '\\';
            *p++ = 'v';
            i++;
        }
        else if (c == ' ')
        {
            *p++ = '\\';
            *p++ = ' ';
            i++;
        }
        else if (c == '#'
#ifdef STRLING_DEBUG
                 || c == '[' || c == ']' || c == '{' || c == '}' || c == '(' || c == ')' || c == '|'
#endif
        )
        {
            *p++ = '\\';
            *p++ = c;
            i++;
        }
        else if (c == '~')
        {
            *p++ = '\\';
            *p++ = '~';
            i++;
        }
        else if (c == '&')
        {
            *p++ = '\\';
            *p++ = '&';
            i++;
        }
        else if (c != 0 && strchr(".^$*+?{}[]()\\|\"`", c))
        {
            *p++ = '\\';
            *p++ = c;
            i++;
        }
        /* Explicitly handle NUL (0x00) and other control chars.
         * We use the braced hex form \x{...} universally for consistency
         * with the test suite expectations. */
        else if (c == 0x00)
        {
            p += sprintf(p, "\\x{%02x}", c);
            i++;
        }
        else if (c < 0x20 || (c >= 0x7F && c <= 0x9F))
        {
            p += sprintf(p, "\\x{%02x}", c);
            i++;
        }
        else if (c >= 0x80)
        {
            /* Decode UTF-8 to code point and emit as \x{...} */
            uint32_t codepoint = 0;
            int bytes = 0;
            if ((c & 0xE0) == 0xC0) { bytes = 2; codepoint = c & 0x1F; }
            else if ((c & 0xF0) == 0xE0) { bytes = 3; codepoint = c & 0x0F; }
            else if ((c & 0xF8) == 0xF0) { bytes = 4; codepoint = c & 0x07; }
            else {
                /* Invalid start byte, emit as \x{...} byte */
                p += sprintf(p, "\\x{%x}", c);
                i++;
                continue;
            }

            /* Check if we have enough bytes */
            if (i + bytes > len) {
                 /* Truncated, emit as bytes */
                 p += sprintf(p, "\\x{%x}", c);
                 i++;
                 continue;
            }

            bool valid = true;
            for (int k = 1; k < bytes; k++) {
                unsigned char next = (unsigned char)lit[i + k];
                if ((next & 0xC0) != 0x80) {
                    valid = false;
                    break;
                }
                codepoint = (codepoint << 6) | (next & 0x3F);
            }

            if (valid) {
                p += sprintf(p, "\\x{%x}", codepoint);
                i += bytes;
            } else {
                /* Invalid sequence, emit first byte */
                p += sprintf(p, "\\x{%x}", c);
                i++;
            }
        }
        else
        {
            *p++ = c;
            i++;
        }
    }
    *p = '\0';

    return result;
}

/* Helper to escape a literal string for PCRE2 output */
static char *escape_literal_for_pcre2(const char *lit)
{
    if (!lit)
        return strdup("");

    size_t len = strlen(lit);
    /* Allocate enough space for worst case: each byte could become \x{HHHHHHHH} (12 chars) */
    char *result = (char *)malloc(len * 12 + 1);
    char *p = result;

    for (size_t i = 0; i < len;)
    {
        unsigned char c = (unsigned char)lit[i];

        /* Handle control characters with escape sequences */
        if (c == '\n')
        {
            *p++ = '\\';
            *p++ = 'n';
            i++;
        }
        else if (c == '\r')
        {
            *p++ = '\\';
            *p++ = 'r';
            i++;
        }
        else if (c == '\t')
        {
            *p++ = '\\';
            *p++ = 't';
            i++;
        }
        else if (c == '\f')
        {
            *p++ = '\\';
            *p++ = 'f';
            i++;
        }
        else if (c == 0x0B)
        { /* Vertical tab */
            *p++ = '\\';
            *p++ = 'v';
            i++;
        }
        /* Handle space - escape it */
        else if (c == ' ')
        {
            *p++ = '\\';
            *p++ = ' ';
            i++;
        }
        /* Handle hash - escape it for free-spacing mode */
        else if (c == '#')
        {
            *p++ = '\\';
            *p++ = '#';
            i++;
        }
        /* Handle tilde - escape it */
        else if (c == '~')
        {
            *p++ = '\\';
            *p++ = '~';
            i++;
        }
        /* Handle ampersand - escape it */
        else if (c == '&')
        {
            *p++ = '\\';
            *p++ = '&';
            i++;
        }
        /* Handle regex metacharacters - escape them */
        else if (c != 0 && strchr(".^$*+?{}[]()\\|\"`", c))
        {
            *p++ = '\\';
            *p++ = c;
            i++;
        }
        /* Handle non-printable ASCII (0x00-0x1F, 0x7F-0x9F) */
        else if (c < 0x20 || (c >= 0x7F && c <= 0x9F))
        {
            p += sprintf(p, "\\x{%02x}", c);
            i++;
        }
        /* Handle multi-byte UTF-8 sequences (Unicode characters) */
        else if (c >= 0x80)
        {
            /* Decode UTF-8 to get Unicode code point */
            unsigned int codepoint = 0;
            int bytes = 0;

            if ((c & 0xE0) == 0xC0)
            {
                /* 2-byte sequence */
                codepoint = c & 0x1F;
                bytes = 1;
            }
            else if ((c & 0xF0) == 0xE0)
            {
                /* 3-byte sequence */
                codepoint = c & 0x0F;
                bytes = 2;
            }
            else if ((c & 0xF8) == 0xF0)
            {
                /* 4-byte sequence */
                codepoint = c & 0x07;
                bytes = 3;
            }
            else
            {
                /* Invalid UTF-8, just output the byte as hex */
                p += sprintf(p, "\\x%02x", c);
                i++;
                continue;
            }

            /* Read continuation bytes */
            i++;
            for (int j = 0; j < bytes && i < len; j++, i++)
            {
                unsigned char cont = (unsigned char)lit[i];
                if ((cont & 0xC0) != 0x80)
                    break;
                codepoint = (codepoint << 6) | (cont & 0x3F);
            }

            /* Process single byte value 'c' */
        }
        /* Regular printable ASCII - output as-is */
        else
        {
            *p++ = c;
            i++;
        }
    }

    *p = '\0';
    *p = '\0';
}

/* Recursive compiler with error propagation */
static int compile_node_to_pcre2(json_t *node, const STRlingFlags *flags, char **out_pattern, char **out_error)
{
    if (!node)
    {
        *out_error = strdup("Internal Error: NULL node encountered");
        return 1;
    }

    const char *type = get_node_type(node);
    if (!type)
    {
        *out_error = strdup("Invalid Node: Missing 'type' or 'kind' field");
        return 1;
    }

    /* Handle Literal */
    if (strcmp(type, "Literal") == 0)
    {
        json_t *value = json_object_get(node, "value");
        if (!value || !json_is_string(value))
        {
            *out_error = strdup("Invalid Literal: Missing or invalid 'value'");
            return 1;
        }
        const char *lit = json_string_value(value);
        size_t len = json_string_length(value);
        /* Literal bytes may contain NUL; we rely on json_string_length to iterate. */
        /* Use the enhanced escape function with length (supports NUL and multi-byte chars) */
        *out_pattern = escape_literal_for_pcre2_len(lit, len);
        return 0;
    }

    /* Handle Sequence */
    if (strcmp(type, "Sequence") == 0)
    {
        json_t *parts = json_object_get(node, "parts");
        if (!parts || !json_is_array(parts))
        {
            *out_error = strdup("Invalid Sequence: Missing 'parts' array");
            return 1;
        }

        size_t n = json_array_size(parts);

        /* Handle empty sequence */
        if (n == 0)
        {
            *out_pattern = strdup("");
            return 0;
        }

        size_t result_len = 0;
        char **part_strs = (char **)calloc(n, sizeof(char *));
        if (!part_strs)
        {
            *out_error = strdup("Memory allocation failed");
            return 1;
        }

        for (size_t i = 0; i < n; i++)
        {
            json_t *part = json_array_get(parts, i);
            char *raw_part = NULL;
            if (compile_node_to_pcre2(part, flags, &raw_part, out_error) != 0)
            {
                /* Free already allocated parts */
                for (size_t j = 0; j < i; j++)
                    free(part_strs[j]);
                free(part_strs);
                return 1;
            }

            /* Check if we need to wrap this part (e.g. Alternation inside Sequence needs parens) */
            const char *part_type = get_node_type(part);
            if (part_type && strcmp(part_type, "Alternation") == 0)
            {
                size_t wrapped_len = strlen(raw_part) + 4 + 1; /* (?:...) */
                part_strs[i] = (char *)malloc(wrapped_len);
                snprintf(part_strs[i], wrapped_len, "(?:%s)", raw_part);
                free(raw_part);
            }
            else
            {
                part_strs[i] = raw_part;
            }

            result_len += strlen(part_strs[i]);
        }

        char *result = (char *)malloc(result_len + 1);
        char *p = result;
        for (size_t i = 0; i < n; i++)
        {
            strcpy(p, part_strs[i]);
            p += strlen(part_strs[i]);
            free(part_strs[i]);
        }
        *p = '\0'; /* Ensure null termination */
        free(part_strs);
        *out_pattern = result;
        return 0;
    }

    /* Handle Anchor */
    if (strcmp(type, "Anchor") == 0)
    {
        json_t *at = json_object_get(node, "at");
        if (!at || !json_is_string(at))
        {
            *out_error = strdup("Invalid Anchor: Missing 'at' field");
            return 1;
        }
        const char *anchor_type = json_string_value(at);

        if (strcmp(anchor_type, "Start") == 0)
            *out_pattern = strdup("^");
        else if (strcmp(anchor_type, "End") == 0)
            *out_pattern = strdup("$");
        else if (strcmp(anchor_type, "WordBoundary") == 0)
            *out_pattern = strdup("\\b");
        else if (strcmp(anchor_type, "NonWordBoundary") == 0 || strcmp(anchor_type, "NotWordBoundary") == 0)
            *out_pattern = strdup("\\B");
        else if (strcmp(anchor_type, "AbsoluteStart") == 0)
            *out_pattern = strdup("\\A");
        else if (strcmp(anchor_type, "EndBeforeFinalNewline") == 0)
            *out_pattern = strdup("\\Z");
        else if (strcmp(anchor_type, "AbsoluteEnd") == 0 || strcmp(anchor_type, "AbsoluteEndOnly") == 0)
            *out_pattern = strdup("\\z");
        else
        {
            *out_error = strdup("Invalid Anchor: Unknown type");
            return 1;
        }
        return 0;
    }

    /* Handle Dot (any character) */
    if (strcmp(type, "Dot") == 0)
    {
        *out_pattern = strdup(".");
        return 0;
    }

    /* Handle Quantifier */
    if (strcmp(type, "Quantifier") == 0)
    {
        json_t *min_obj = json_object_get(node, "min");
        json_t *max_obj = json_object_get(node, "max");
        json_t *greedy_obj = json_object_get(node, "greedy");
        json_t *possessive_obj = json_object_get(node, "possessive");
        json_t *target = json_object_get(node, "target");

        if (!target)
        {
            *out_error = strdup("Invalid Quantifier: Missing 'target'");
            return 1;
        }

        /* Check if target is an Anchor */
        const char *target_type_check = get_node_type(target);
        if (target_type_check && (strcmp(target_type_check, "Anchor") == 0 || strcmp(target_type_check, "anchor") == 0))
        {
            *out_error = strdup("Invalid Quantifier: Target cannot be an Anchor");
            return 1;
        }

        char *target_str = NULL;
        if (compile_node_to_pcre2(target, flags, &target_str, out_error) != 0)
        {
            return 1;
        }

        /* Handle empty target (e.g. empty sequence) */
        if (strlen(target_str) == 0)
        {
            free(target_str);
            target_str = strdup("(?:)");
        }
        else
        {
            /* Check if target needs wrapping (nested Quantifier, Alternation, Sequence) */
            const char *target_type = get_node_type(target);
            bool needs_wrap = false;
            if (target_type)
            {
                if (strcmp(target_type, "Quantifier") == 0 ||
                    strcmp(target_type, "Alternation") == 0 ||
                    strcmp(target_type, "Lookahead") == 0 ||
                    strcmp(target_type, "NegativeLookahead") == 0 ||
                    strcmp(target_type, "Lookbehind") == 0 ||
                    strcmp(target_type, "NegativeLookbehind") == 0 ||
                    strcmp(target_type, "Look") == 0 ||
                    strcmp(target_type, "Lookaround") == 0)
                {
                    needs_wrap = true;
                }
                else if (strcmp(target_type, "Literal") == 0)
                {
                    json_t *val = json_object_get(target, "value");
                    if (val && json_is_string(val))
                    {
                        const char *s = json_string_value(val);
                        if (s && strlen(s) > 1)
                            needs_wrap = true;
                    }
                }
                else if (strcmp(target_type, "Sequence") == 0)
                {
                    /* Only wrap Sequence if it has multiple parts */
                    json_t *parts = json_object_get(target, "parts");
                    if (parts && json_is_array(parts) && json_array_size(parts) > 1)
                    {
                        needs_wrap = true;
                    }
                }
            }

            if (needs_wrap)
            {
                size_t wrapped_len = strlen(target_str) + 4 + 1;
                char *wrapped = (char *)malloc(wrapped_len);
                snprintf(wrapped, wrapped_len, "(?:%s)", target_str);
                free(target_str);
                target_str = wrapped;
            }
        }

        int min = 0;
        if (min_obj)
        {
            if (!json_is_integer(min_obj))
            {
                free(target_str);
                *out_error = strdup("Invalid Quantifier: 'min' must be an integer");
                return 1;
            }
            min = json_integer_value(min_obj);
        }
        else if (!max_obj)
        {
            free(target_str);
            *out_error = strdup("Invalid Quantifier: Missing 'min' field");
            return 1;
        }

        if (min < 0)
        {
            free(target_str);
            *out_error = strdup("Invalid Quantifier: 'min' cannot be negative");
            return 1;
        }

        bool greedy = true;
        if (greedy_obj && json_is_boolean(greedy_obj))
            greedy = json_boolean_value(greedy_obj);
        bool possessive = false;
        if (possessive_obj && json_is_boolean(possessive_obj))
            possessive = json_boolean_value(possessive_obj);

        /* Build quantifier string */
        char quantifier[32] = "";

        if (max_obj && json_is_null(max_obj))
        {
            /* Unbounded max */
            if (min == 0)
                strcpy(quantifier, "*");
            else if (min == 1)
                strcpy(quantifier, "+");
            else
                snprintf(quantifier, sizeof(quantifier), "{%d,}", min);
        }
        else if (max_obj && json_is_integer(max_obj))
        {
            int max = json_integer_value(max_obj);
            if (max < min)
            {
                free(target_str);
                char msg[128];
                snprintf(msg, sizeof(msg), "Invalid Quantifier: 'min' (%d) cannot be greater than 'max' (%d)", min, max);
                *out_error = strdup(msg);
                return 1;
            }

            if (min == 0 && max == 1)
                strcpy(quantifier, "?");
            else if (min == max)
                snprintf(quantifier, sizeof(quantifier), "{%d}", min);
            else
                snprintf(quantifier, sizeof(quantifier), "{%d,%d}", min, max);
        }
        else
        {
            /* Default to * if max is missing/invalid (shouldn't happen in valid AST) */
            strcpy(quantifier, "*");
        }

        /* Add lazy modifier if not greedy */
        if (!greedy)
        {
            strcat(quantifier, "?");
        }

        /* Add possessive modifier if requested (e.g. a*+ ) */
        if (possessive)
        {
            strcat(quantifier, "+");
        }

        /* Combine target and quantifier */
        size_t result_len = strlen(target_str) + strlen(quantifier) + 1;
        char *result = (char *)malloc(result_len);
        strcpy(result, target_str);
        strcat(result, quantifier);

        free(target_str);
        *out_pattern = result;
        return 0;
    }

    /* Handle Alternation */
    if (strcmp(type, "Alternation") == 0)
    {
        json_t *alternatives = json_object_get(node, "alternatives");
        if (!alternatives || !json_is_array(alternatives))
        {
            *out_error = strdup("Invalid Alternation: Missing 'alternatives' array");
            return 1;
        }

        size_t n = json_array_size(alternatives);
        if (n == 0)
        {
            *out_error = strdup("Invalid Alternation: Must have at least one alternative");
            return 1;
        }

        /* Optimization: if only 1 alternative, just return it */
        if (n == 1)
        {
            json_t *alt = json_array_get(alternatives, 0);
            return compile_node_to_pcre2(alt, flags, out_pattern, out_error);
        }

        /* Compile all alternatives */
        char **alt_strs = (char **)calloc(n, sizeof(char *));
        if (!alt_strs)
        {
            *out_error = strdup("Memory allocation failed");
            return 1;
        }
        size_t total_len = 0;

        for (size_t i = 0; i < n; i++)
        {
            if (compile_node_to_pcre2(json_array_get(alternatives, i), flags, &alt_strs[i], out_error) != 0)
            {
                for (size_t j = 0; j < i; j++)
                    free(alt_strs[j]);
                free(alt_strs);
                return 1;
            }
            total_len += strlen(alt_strs[i]);
        }

        /* Add space for separators: alt1 | alt2 | ... */
        /* We need (n-1) separators of "|" */
        total_len += (n - 1); /* for | separators */
        total_len += 1;       /* for null terminator */

        char *result = (char *)malloc(total_len);
        char *p = result;

        /* Join alternatives with | */
        for (size_t i = 0; i < n; i++)
        {
            strcpy(p, alt_strs[i]);
            p += strlen(alt_strs[i]);
            if (i < n - 1)
            {
                *p++ = '|';
            }
            free(alt_strs[i]);
        }

        *p = '\0';

        free(alt_strs);
        *out_pattern = result;
        return 0;
    }

    /* Handle UnicodeProperty */
    if (strcmp(type, "UnicodeProperty") == 0)
    {
        json_t *name_obj = json_object_get(node, "name");
        json_t *value_obj = json_object_get(node, "value");
        json_t *negated_obj = json_object_get(node, "negated");

        bool negated = negated_obj && json_is_true(negated_obj);
        const char *name = NULL;
        const char *value = NULL;

        if (name_obj && json_is_string(name_obj))
            name = json_string_value(name_obj);
        if (value_obj && json_is_string(value_obj))
            value = json_string_value(value_obj);

        if (!value)
        {
            *out_error = strdup("Invalid UnicodeProperty: Missing 'value'");
            return 1;
        }

        /* \p{name=value} or \p{value} */
        size_t len = 4 + (name ? strlen(name) + 1 : 0) + strlen(value) + 2; /* \p{...} + \0 */
        char *result = (char *)malloc(len);
        if (!result)
        {
            *out_error = strdup("Memory allocation failed");
            return 1;
        }

        char *p = result;
        *p++ = '\\';
        *p++ = negated ? 'P' : 'p';
        *p++ = '{';
        if (name)
        {
            strcpy(p, name);
            p += strlen(name);
            *p++ = '=';
        }
        strcpy(p, value);
        p += strlen(value);
        *p++ = '}';
        *p = '\0';

        *out_pattern = result;
        return 0;
    }

    /* Handle CharacterClass */
    if (strcmp(type, "CharacterClass") == 0)
    {
        json_t *negated_obj = json_object_get(node, "negated");
        json_t *members = json_object_get(node, "members");

        if (!members || !json_is_array(members))
        {
            *out_error = strdup("Invalid CharacterClass: Missing 'members' array");
            return 1;
        }

        bool negated = negated_obj && json_is_true(negated_obj);
        size_t n = json_array_size(members);

        /* Optimization: Unwrap single-member character classes if safe - REMOVED */


        /* Optimization: Single member character class (negated) - REMOVED */


        /* Build the character class string */
        size_t result_capacity = 256; /* Initial capacity */
        char *result = (char *)malloc(result_capacity);
        if (!result)
        {
            *out_error = strdup("Memory allocation failed");
            return 1;
        }
        size_t result_len = 0;

        /* Start with [ */
        result[result_len++] = '[';

        /* Add ^ if negated */
        if (negated)
        {
            result[result_len++] = '^';
        }

        /* Process each member */
        for (size_t i = 0; i < n; i++)
        {
            json_t *member = json_array_get(members, i);
            if (!member)
                continue;

            const char *member_type = get_node_type(member);
            if (!member_type)
                continue;

            /* Ensure we have enough space (conservative estimate) */
            if (result_len + 50 > result_capacity)
            {
                result_capacity *= 2;
                char *new_result = (char *)realloc(result, result_capacity);
                if (!new_result)
                {
                    free(result);
                    *out_error = strdup("Memory allocation failed");
                    return 1;
                }
                result = new_result;
            }

            /* Handle Range: {"type": "Range", "from": "a", "to": "z"} */
            if (strcmp(member_type, "Range") == 0)
            {
                json_t *from_obj = json_object_get(member, "from");
                json_t *to_obj = json_object_get(member, "to");

                if (from_obj && json_is_string(from_obj) &&
                    to_obj && json_is_string(to_obj))
                {
                    const char *from = json_string_value(from_obj);
                    const char *to = json_string_value(to_obj);

                    /* Ensure strings are not empty before accessing [0] */
                    if (from && from[0] && to && to[0])
                    {
                        if ((unsigned char)from[0] > (unsigned char)to[0])
                        {
                            free(result);
                            *out_error = strdup("Invalid Range: 'from' cannot be greater than 'to'");
                            return 1;
                        }
                        /* Emit as "from-to" */
                        result[result_len++] = from[0];
                        result[result_len++] = '-';
                        result[result_len++] = to[0];
                    }
                }
            }
            /* Handle Meta: {"type": "Meta", "value": "d"} */
            else if (strcmp(member_type, "Meta") == 0)
            {
                json_t *value_obj = json_object_get(member, "value");
                if (value_obj && json_is_string(value_obj))
                {
                    const char *value = json_string_value(value_obj);
                    size_t val_len = json_string_length(value_obj);
                    /* Ensure string is not empty before accessing */
                    if (value && val_len > 0)
                    {
                        /* Emit as \value */
                        result[result_len++] = '\\';
                        result[result_len++] = value[0];
                    }
                }
            }
            /* Handle Literal: {"type": "Literal", "value": "x"} */
            else if (strcmp(member_type, "Literal") == 0)
            {
                json_t *value_obj = json_object_get(member, "value");
                if (value_obj && json_is_string(value_obj))
                {
                    const char *value = json_string_value(value_obj);
                    size_t val_len = json_string_length(value_obj);
                    /* Ensure string is not empty before accessing [0] */
                    if (value && val_len > 0)
                    {
                        /* Special characters in character classes that need escaping */
                        const unsigned char *s = (const unsigned char *)value;
                        size_t i = 0;
                        while (i < val_len)
                        {
                            /* Ensure capacity */
                            if (result_len + 16 > result_capacity)
                            {
                                result_capacity = result_capacity * 2 + 16;
                                char *new_result = (char *)realloc(result, result_capacity);
                                if (!new_result)
                                {
                                    free(result);
                                    *out_error = strdup("Memory allocation failed");
                                    return 1;
                                }
                                result = new_result;
                            }

                            unsigned char c = s[i];

                            /* Handle multi-byte UTF-8 raw */
                            if (c >= 0x80)
                            {
                                int bytes = 0;
                                if ((c & 0xE0) == 0xC0)
                                    bytes = 2;
                                else if ((c & 0xF0) == 0xE0)
                                    bytes = 3;
                                else if ((c & 0xF8) == 0xF0)
                                    bytes = 4;
                                else
                                {
                                    /* Invalid start byte, treat as raw byte */
                                    result[result_len++] = c;
                                    i++;
                                    continue;
                                }

                                /* Copy the sequence */
                                for (int k = 0; k < bytes && i < val_len; k++)
                                {
                                    result[result_len++] = s[i++];
                                }
                                continue;
                            }

                            /* Handle control chars < 0x20 */
                            if (c < 0x20)
                            {
                                if (c == '\n')
                                {
                                    result[result_len++] = '\\';
                                    result[result_len++] = 'n';
                                }
                                else if (c == '\r')
                                {
                                    result[result_len++] = '\\';
                                    result[result_len++] = 'r';
                                }
                                else if (c == '\t')
                                {
                                    result[result_len++] = '\\';
                                    result[result_len++] = 't';
                                }
                                else if (c == '\f')
                                {
                                    result[result_len++] = '\\';
                                    result[result_len++] = 'f';
                                }
                                else if (c == '\v')
                                {
                                    result[result_len++] = '\\';
                                    result[result_len++] = 'v';
                                }
                                else
                                {
                                    /* Use \x{...} format universally for control chars in character classes */
                                    char buf[16];
                                    snprintf(buf, sizeof(buf), "\\x{%02x}", c);
                                    for (size_t k = 0; k < strlen(buf); k++)
                                        result[result_len++] = buf[k];
                                }
                                i++;
                                continue;
                            }

                            /* Handle special chars inside [] */
                            if (c == ']' || c == '\\' || c == '^' || c == '-')
                            {
                                result[result_len++] = '\\';
                            }
                            result[result_len++] = c;
                            i++;
                        }
                    }
                }
            }
            /* Handle Escape shorthand inside character classes: \d, \w, \s
               These are encoded as { "type": "Escape", "kind": "digit" } in the AST
            */
            else if (strcmp(member_type, "Escape") == 0)
            {
                json_t *kind_obj = json_object_get(member, "kind");
                if (kind_obj && json_is_string(kind_obj))
                {
                    const char *kind = json_string_value(kind_obj);
                    if (kind && kind[0])
                    {
                        if (strcmp(kind, "unicode_property") == 0)
                        {
                            json_t *prop_obj = json_object_get(member, "property");
                            json_t *neg_obj = json_object_get(member, "negated");
                            bool is_negated = neg_obj && json_is_true(neg_obj);

                            if (prop_obj && json_is_string(prop_obj))
                            {
                                const char *prop = json_string_value(prop_obj);
                                if (strlen(prop) == 0)
                                {
                                    free(result);
                                    *out_error = strdup("Invalid unicode property: Empty property");
                                    return 1;
                                }
                                size_t prop_len = strlen(prop);
                                size_t needed = 4 + prop_len; /* \p{prop} */

                                while (result_len + needed >= result_capacity)
                                {
                                    result_capacity *= 2;
                                    char *new_result = (char *)realloc(result, result_capacity);
                                    if (!new_result)
                                    {
                                        free(result);
                                        *out_error = strdup("Memory allocation failed");
                                        return 1;
                                    }
                                    result = new_result;
                                }

                                result[result_len++] = '\\';
                                result[result_len++] = is_negated ? 'P' : 'p';
                                result[result_len++] = '{';
                                memcpy(result + result_len, prop, prop_len);
                                result_len += prop_len;
                                result[result_len++] = '}';
                                continue;
                            }
                            else
                            {
                                free(result);
                                *out_error = strdup("Invalid unicode property: Missing 'property' field");
                                return 1;
                            }
                        }

                        char k = 'd';
                        if (strcmp(kind, "digit") == 0)
                            k = 'd';
                        else if (strcmp(kind, "not_digit") == 0 || strcmp(kind, "not-digit") == 0)
                            k = 'D';
                        else if (strcmp(kind, "word") == 0)
                            k = 'w';
                        else if (strcmp(kind, "not_word") == 0 || strcmp(kind, "not-word") == 0)
                            k = 'W';
                        else if (strcmp(kind, "space") == 0 || strcmp(kind, "whitespace") == 0)
                            k = 's';
                        else if (strcmp(kind, "not_space") == 0 || strcmp(kind, "not_whitespace") == 0 || strcmp(kind, "not-space") == 0 || strcmp(kind, "not-whitespace") == 0)
                            k = 'S';
                        else
                            k = kind[0];
                        result[result_len++] = '\\';
                        result[result_len++] = k;
                    }
                }
            }
            /* Handle UnicodeProperty: {"type": "UnicodeProperty", "name": "Script", "value": "Latin", "negated": false} */
            else if (strcmp(member_type, "UnicodeProperty") == 0)
            {
                json_t *name_obj = json_object_get(member, "name");
                json_t *value_obj = json_object_get(member, "value");
                json_t *neg_obj = json_object_get(member, "negated");

                bool is_negated = neg_obj && json_is_true(neg_obj);

                if (value_obj && json_is_string(value_obj))
                {
                    const char *value = json_string_value(value_obj);
                    const char *name = NULL;
                    size_t value_len = value ? strlen(value) : 0;
                    size_t name_len = 0;

                    if (name_obj && json_is_string(name_obj))
                    {
                        name = json_string_value(name_obj);
                        name_len = name ? strlen(name) : 0;
                    }

                    /* Calculate total space needed: \p{name=value} or \p{value} */
                    size_t needed = 4 + value_len + name_len + (name ? 1 : 0); /* \p{} + name= + value */

                    /* Ensure we have enough space */
                    while (result_len + needed >= result_capacity)
                    {
                        result_capacity *= 2;
                        char *new_result = (char *)realloc(result, result_capacity);
                        if (!new_result)
                        {
                            free(result);
                            if (out_error)
                                *out_error = strdup("Memory allocation failed");
                            return -1;
                        }
                        result = new_result;
                    }

                    /* Start with \p or \P */
                    result[result_len++] = '\\';
                    result[result_len++] = is_negated ? 'P' : 'p';
                    result[result_len++] = '{';

                    /* Add name=value if name is present, otherwise just value */
                    if (name && name_len > 0)
                    {
                        memcpy(result + result_len, name, name_len);
                        result_len += name_len;
                        result[result_len++] = '=';
                    }

                    if (value && value_len > 0)
                    {
                        memcpy(result + result_len, value, value_len);
                        result_len += value_len;
                    }
                    result[result_len++] = '}';
                }
            }
        }

        /* Close with ] */
        result[result_len++] = ']';
        result[result_len] = '\0';

        *out_pattern = result;
        return 0;
    }

    /* Handle Escape (standalone) */
    if (strcmp(type, "Escape") == 0)
    {
        json_t *kind_obj = json_object_get(node, "kind");
        json_t *value_obj = json_object_get(node, "value");

        if (kind_obj && json_is_string(kind_obj))
        {
            const char *kind = json_string_value(kind_obj);
            if (strcmp(kind, "unknown") == 0)
            {
                char msg[128];
                const char *val = "";
                if (value_obj && json_is_string(value_obj))
                    val = json_string_value(value_obj);
                snprintf(msg, sizeof(msg), "Unknown escape: \\%s", val);
                *out_error = strdup(msg);
                return 1;
            }
            if (strcmp(kind, "digit") == 0)
            {
                *out_pattern = strdup("\\d");
                return 0;
            }
            if (strcmp(kind, "not-digit") == 0)
            {
                *out_pattern = strdup("\\D");
                return 0;
            }
            if (strcmp(kind, "word") == 0)
            {
                *out_pattern = strdup("\\w");
                return 0;
            }
            if (strcmp(kind, "not-word") == 0)
            {
                *out_pattern = strdup("\\W");
                return 0;
            }
            if (strcmp(kind, "space") == 0 || strcmp(kind, "whitespace") == 0)
            {
                *out_pattern = strdup("\\s");
                return 0;
            }
            if (strcmp(kind, "not-space") == 0 || strcmp(kind, "not-whitespace") == 0)
            {
                *out_pattern = strdup("\\S");
                return 0;
            }
            if (strcmp(kind, "hex") == 0)
            {
                const char *val = "";
                if (value_obj && json_is_string(value_obj))
                    val = json_string_value(value_obj);
                if (strlen(val) == 0)
                {
                    *out_error = strdup("Invalid hex: Empty value");
                    return 1;
                }
                for (size_t i = 0; i < strlen(val); i++)
                {
                    if (!isxdigit((unsigned char)val[i]))
                    {
                        *out_error = strdup("Invalid hex: Non-hex digit");
                        return 1;
                    }
                }
                char *res = (char *)malloc(strlen(val) + 5);
                sprintf(res, "\\x{%s}", val);
                *out_pattern = res;
                return 0;
            }
            if (strcmp(kind, "unicode") == 0)
            {
                const char *val = "";
                if (value_obj && json_is_string(value_obj))
                    val = json_string_value(value_obj);
                if (strlen(val) == 0)
                {
                    *out_error = strdup("Invalid unicode: Empty value");
                    return 1;
                }
                for (size_t i = 0; i < strlen(val); i++)
                {
                    if (!isxdigit((unsigned char)val[i]))
                    {
                        *out_error = strdup("Invalid unicode: Non-hex digit");
                        return 1;
                    }
                }
                char *res = (char *)malloc(strlen(val) + 5);
                sprintf(res, "\\x{%s}", val);
                *out_pattern = res;
                return 0;
            }
        }
        *out_error = strdup("Invalid Escape node");
        return 1;
    }

    /* Handle Meta (standalone escape sequences like \b, \d, etc.) */
    if (strcmp(type, "Meta") == 0)
    {
        json_t *value_obj = json_object_get(node, "value");
        if (value_obj && json_is_string(value_obj))
        {
            const char *value = json_string_value(value_obj);
            if (value && value[0])
            {
                /* Emit as \value */
                char *result = (char *)malloc(3); /* \ + char + \0 */
                result[0] = '\\';
                result[1] = value[0];
                result[2] = '\0';
                *out_pattern = result;
                return 0;
            }
        }
        *out_error = strdup("Invalid Meta: Missing or invalid 'value'");
        return 1;
    }

    /* Handle Group */
    if (strcmp(type, "Group") == 0)
    {
        json_t *body = json_object_get(node, "body");
        if (!body)
            body = json_object_get(node, "expression");

        json_t *capturing_obj = json_object_get(node, "capturing");
        json_t *name_obj = json_object_get(node, "name");
        json_t *atomic_obj = json_object_get(node, "atomic");

        if (!body)
        {
            *out_error = strdup("Invalid Group: Missing 'body' or 'expression'");
            return 1;
        }

        /* Compile the body */
        char *body_str = NULL;
        if (compile_node_to_pcre2(body, flags, &body_str, out_error) != 0)
        {
            return 1;
        }

        /* Determine group type */
        bool capturing = true; /* Default is capturing */
        bool atomic = false;
        const char *name = NULL;

        if (capturing_obj && json_is_boolean(capturing_obj))
        {
            capturing = json_boolean_value(capturing_obj);
        }
        if (atomic_obj && json_is_boolean(atomic_obj))
        {
            atomic = json_boolean_value(atomic_obj);
        }
        if (name_obj && json_is_string(name_obj))
        {
            name = json_string_value(name_obj);
            if (!is_valid_group_name(name))
            {
                free(body_str);
                *out_error = strdup("Invalid group name. Hint: Group names must be valid IDENTIFIERs (alphanumeric + underscore, start with letter/underscore)");
                return 1;
            }
        }

        /* Build the group string */
        size_t body_len = strlen(body_str);
        size_t result_len;
        char *result;

        if (atomic)
        {
            /* Atomic group: (?>...) */
            result_len = 4 + body_len + 1; /* (?> + body + ) + \0 */
            result = (char *)malloc(result_len);
            snprintf(result, result_len, "(?>%s)", body_str);
        }
        else if (name)
        {
            /* Named capturing group: (?<name>...) */
            size_t name_len = strlen(name);
            result_len = 4 + name_len + body_len + 2; /* (?< + name + > + body + ) + \0 */
            result = (char *)malloc(result_len);
            snprintf(result, result_len, "(?<%s>%s)", name, body_str);
        }
        else if (!capturing)
        {
            /* Non-capturing group: (?:...) */
            result_len = 4 + body_len + 1; /* (?: + body + ) + \0 */
            result = (char *)malloc(result_len);
            snprintf(result, result_len, "(?:%s)", body_str);
        }
        else
        {
            /* Capturing group: (...) */
            result_len = 2 + body_len + 1; /* ( + body + ) + \0 */
            result = (char *)malloc(result_len);
            snprintf(result, result_len, "(%s)", body_str);
        }

        free(body_str);
        *out_pattern = result;
        return 0;
    }

    /* Handle Backreference */
    if (strcmp(type, "Backreference") == 0 || strcmp(type, "Backref") == 0 || strcmp(type, "BackReference") == 0)
    {
        json_t *kind_obj = json_object_get(node, "kind");
        if (kind_obj && json_is_string(kind_obj))
        {
            const char *kind = json_string_value(kind_obj);
            if (strcmp(kind, "recursion") == 0)
            {
                *out_pattern = strdup("(?R)");
                return 0;
            }
            if (strcmp(kind, "subroutine") == 0)
            {
                json_t *ref_obj = json_object_get(node, "ref");
                json_t *name_obj = json_object_get(node, "name");

                if (name_obj && json_is_string(name_obj))
                {
                    const char *name = json_string_value(name_obj);
                    size_t len = strlen(name) + 6; /* (?&name) + \0 */
                    char *res = (char *)malloc(len);
                    snprintf(res, len, "(?&%s)", name);
                    *out_pattern = res;
                    return 0;
                }
                if (ref_obj)
                {
                    if (json_is_integer(ref_obj))
                    {
                        int idx = json_integer_value(ref_obj);
                        char *res = (char *)malloc(16);
                        snprintf(res, 16, "(?%d)", idx);
                        *out_pattern = res;
                        return 0;
                    }
                    if (json_is_string(ref_obj))
                    {
                        const char *name = json_string_value(ref_obj);
                        size_t len = strlen(name) + 6;
                        char *res = (char *)malloc(len);
                        snprintf(res, len, "(?&%s)", name);
                        *out_pattern = res;
                        return 0;
                    }
                }
            }
        }

        json_t *index_obj = json_object_get(node, "index");
        json_t *name_obj = json_object_get(node, "name");
        json_t *ref_obj = json_object_get(node, "ref");
        json_t *by_index_obj = json_object_get(node, "byIndex");
        json_t *by_name_obj = json_object_get(node, "byName");

        if (name_obj && json_is_string(name_obj))
        {
            /* Named backreference: \k<name> */
            const char *name = json_string_value(name_obj);
            if (!is_valid_group_name(name))
            {
                *out_error = strdup("Invalid group name. Hint: Group names must be valid IDENTIFIERs (alphanumeric + underscore, start with letter/underscore)");
                return 1;
            }
            size_t name_len = strlen(name);
            size_t result_len = 4 + name_len + 1; /* \k< + name + > + \0 */
            char *result = (char *)malloc(result_len);
            snprintf(result, result_len, "\\k<%s>", name);
            *out_pattern = result;
            return 0;
        }
        else if (by_name_obj && json_is_string(by_name_obj))
        {
            const char *name = json_string_value(by_name_obj);
            if (!is_valid_group_name(name))
            {
                *out_error = strdup("Invalid group name. Hint: Group names must be valid IDENTIFIERs (alphanumeric + underscore, start with letter/underscore)");
                return 1;
            }
            size_t name_len = strlen(name);
            size_t result_len = 4 + name_len + 1;
            char *result = (char *)malloc(result_len);
            snprintf(result, result_len, "\\k<%s>", name);
            *out_pattern = result;
            return 0;
        }
        else if (index_obj && json_is_integer(index_obj))
        {
            /* Numeric backreference: \1, \2, etc. */
            int index = json_integer_value(index_obj);
            if (index == 0)
            {
                *out_error = strdup("Invalid Backreference: Index cannot be 0");
                return 1;
            }
            if (index < 0)
            {
                char *result = (char *)malloc(32);
                snprintf(result, 32, "\\g{%d}", index);
                *out_pattern = result;
                return 0;
            }
            char *result = (char *)malloc(16); /* Enough for \<digits> */
            snprintf(result, 16, "\\%d", index);
            *out_pattern = result;
            return 0;
        }
        else if (by_index_obj && json_is_integer(by_index_obj))
        {
            int index = json_integer_value(by_index_obj);
            if (index == 0)
            {
                *out_error = strdup("Invalid Backreference: Index cannot be 0");
                return 1;
            }
            if (index < 0)
            {
                char *result = (char *)malloc(32);
                snprintf(result, 32, "\\g{%d}", index);
                *out_pattern = result;
                return 0;
            }
            char *result = (char *)malloc(16);
            snprintf(result, 16, "\\%d", index);
            *out_pattern = result;
            return 0;
        }
        else if (ref_obj)
        {
            /* Handle JS-style 'ref' field which can be int or string */
            if (json_is_string(ref_obj))
            {
                const char *name = json_string_value(ref_obj);
                size_t name_len = strlen(name);
                size_t result_len = 4 + name_len + 1;
                char *result = (char *)malloc(result_len);
                snprintf(result, result_len, "\\k<%s>", name);
                *out_pattern = result;
                return 0;
            }
            else if (json_is_integer(ref_obj))
            {
                int index = json_integer_value(ref_obj);
                if (index == 0)
                {
                    *out_error = strdup("Invalid Backreference: Index cannot be 0");
                    return 1;
                }
                if (index < 0)
                {
                    char *result = (char *)malloc(32);
                    snprintf(result, 32, "\\g{%d}", index);
                    *out_pattern = result;
                    return 0;
                }
                char *result = (char *)malloc(16);
                snprintf(result, 16, "\\%d", index);
                *out_pattern = result;
                return 0;
            }
        }
        *out_error = strdup("Invalid Backreference: Missing index or name");
        return 1;
    }

    /* Handle Lookaround */
    if (strcmp(type, "Lookaround") == 0)
    {
        json_t *expression = json_object_get(node, "expression");
        json_t *kind_obj = json_object_get(node, "kind");
        json_t *negated_obj = json_object_get(node, "negated");

        if (!expression)
        {
            *out_error = strdup("Invalid Lookaround: Missing 'expression'");
            return 1;
        }

        char *expr_str = NULL;
        if (compile_node_to_pcre2(expression, flags, &expr_str, out_error) != 0)
        {
            return 1;
        }

        const char *kind = "lookahead";
        if (kind_obj && json_is_string(kind_obj))
        {
            kind = json_string_value(kind_obj);
        }

        bool negated = false;
        if (negated_obj && json_is_boolean(negated_obj))
        {
            negated = json_boolean_value(negated_obj);
        }

        size_t len = strlen(expr_str) + 10;
        char *result = (char *)malloc(len);

        if (strcmp(kind, "lookahead") == 0)
        {
            snprintf(result, len, "(?%c%s)", negated ? '!' : '=', expr_str);
        }
        else if (strcmp(kind, "lookbehind") == 0)
        {
            snprintf(result, len, "(?<%c%s)", negated ? '!' : '=', expr_str);
        }
        else
        {
            free(expr_str);
            free(result);
            *out_error = strdup("Invalid Lookaround: Unknown kind");
            return 1;
        }

        free(expr_str);
        *out_pattern = result;
        return 0;
    }

    /* Handle Lookahead */
    if (strcmp(type, "Lookahead") == 0)
    {
        json_t *body = json_object_get(node, "body");
        if (!body)
            body = json_object_get(node, "expression");
        if (!body)
        {
            *out_error = strdup("Invalid Lookahead: Missing 'expression' or 'body'");
            return 1;
        }

        char *body_str = NULL;
        if (compile_node_to_pcre2(body, flags, &body_str, out_error) != 0)
        {
            return 1;
        }

        /* Positive lookahead: (?=...) */
        size_t body_len = strlen(body_str);
        size_t result_len = 4 + body_len + 1; /* (?= + body + ) + \0 */
        char *result = (char *)malloc(result_len);
        snprintf(result, result_len, "(?=%s)", body_str);

        free(body_str);
        *out_pattern = result;
        return 0;
    }

    /* Handle NegativeLookahead */
    if (strcmp(type, "NegativeLookahead") == 0)
    {
        json_t *body = json_object_get(node, "body");
        if (!body)
            body = json_object_get(node, "expression");
        if (!body)
        {
            *out_error = strdup("Invalid NegativeLookahead: Missing 'body'");
            return 1;
        }

        char *body_str = NULL;
        if (compile_node_to_pcre2(body, flags, &body_str, out_error) != 0)
        {
            return 1;
        }

        /* Negative lookahead: (?!...) */
        size_t body_len = strlen(body_str);
        size_t result_len = 4 + body_len + 1; /* (?! + body + ) + \0 */
        char *result = (char *)malloc(result_len);
        snprintf(result, result_len, "(?!%s)", body_str);

        free(body_str);
        *out_pattern = result;
        return 0;
    }

    /* Handle Lookbehind */
    if (strcmp(type, "Lookbehind") == 0)
    {
        json_t *body = json_object_get(node, "body");
        if (!body)
            body = json_object_get(node, "expression");
        if (!body)
        {
            *out_error = strdup("Invalid Lookbehind: Missing 'body'");
            return 1;
        }

        char *body_str = NULL;
        if (compile_node_to_pcre2(body, flags, &body_str, out_error) != 0)
        {
            return 1;
        }

        /* Positive lookbehind: (?<=...) */
        size_t body_len = strlen(body_str);
        size_t result_len = 5 + body_len + 1; /* (?<= + body + ) + \0 */
        char *result = (char *)malloc(result_len);
        snprintf(result, result_len, "(?<=%s)", body_str);

        free(body_str);
        *out_pattern = result;
        return 0;
    }

    /* Handle NegativeLookbehind */
    if (strcmp(type, "NegativeLookbehind") == 0)
    {
        json_t *body = json_object_get(node, "body");
        if (!body)
            body = json_object_get(node, "expression");
        if (!body)
        {
            *out_error = strdup("Invalid NegativeLookbehind: Missing 'body'");
            return 1;
        }

        char *body_str = NULL;
        if (compile_node_to_pcre2(body, flags, &body_str, out_error) != 0)
        {
            return 1;
        }

        /* Negative lookbehind: (?<!...) */
        size_t body_len = strlen(body_str);
        size_t result_len = 5 + body_len + 1; /* (?<! + body + ) + \0 */
        char *result = (char *)malloc(result_len);
        snprintf(result, result_len, "(?<!%s)", body_str);

        free(body_str);
        *out_pattern = result;
        return 0;
    }

    /* Handle Look (JS AST) */
    if (strcmp(type, "Look") == 0)
    {
        json_t *dir_obj = json_object_get(node, "dir");
        json_t *neg_obj = json_object_get(node, "neg");
        json_t *body = json_object_get(node, "body");
        if (!body)
            body = json_object_get(node, "expression");

        if (!body)
        {
            *out_error = strdup("Invalid Look: Missing 'body'");
            return 1;
        }

        char *body_str = NULL;
        if (compile_node_to_pcre2(body, flags, &body_str, out_error) != 0)
        {
            return 1;
        }

        const char *dir = "Ahead";
        if (dir_obj && json_is_string(dir_obj))
            dir = json_string_value(dir_obj);

        bool neg = false;
        if (neg_obj && json_is_boolean(neg_obj))
            neg = json_boolean_value(neg_obj);

        /* Construct prefix: (?=, (?!, (?<=, (?<! */
        char prefix[5] = "(?";
        if (strcmp(dir, "Behind") == 0)
            strcat(prefix, "<");
        strcat(prefix, neg ? "!" : "=");

        size_t body_len = strlen(body_str);
        size_t result_len = strlen(prefix) + body_len + 1 + 1; /* prefix + body + ) + \0 */
        char *result = (char *)malloc(result_len);
        snprintf(result, result_len, "%s%s)", prefix, body_str);

        free(body_str);
        *out_pattern = result;
        return 0;
    }

    /* Unsupported node types return error */
    char msg[256];
    snprintf(msg, sizeof(msg), "Unknown node type: '%s'", type);
    *out_error = strdup(msg);
    return 1;
}

/* Semantic Validation Context */
typedef struct
{
    char **defined_groups;
    size_t group_count;
    size_t group_capacity;
    int capturing_group_count;
} ValidationContext;

static void ctx_init(ValidationContext *ctx)
{
    ctx->defined_groups = NULL;
    ctx->group_count = 0;
    ctx->group_capacity = 0;
    ctx->capturing_group_count = 0;
}

static void ctx_free(ValidationContext *ctx)
{
    for (size_t i = 0; i < ctx->group_count; i++)
    {
        free(ctx->defined_groups[i]);
    }
    free(ctx->defined_groups);
}

static bool ctx_add_group(ValidationContext *ctx, const char *name)
{
    for (size_t i = 0; i < ctx->group_count; i++)
    {
        if (strcmp(ctx->defined_groups[i], name) == 0)
        {
            return false; // Duplicate
        }
    }
    if (ctx->group_count == ctx->group_capacity)
    {
        ctx->group_capacity = ctx->group_capacity == 0 ? 8 : ctx->group_capacity * 2;
        char **new_groups = (char **)realloc(ctx->defined_groups, ctx->group_capacity * sizeof(char *));
        if (!new_groups)
            return false; // Allocation failure
        ctx->defined_groups = new_groups;
    }
    ctx->defined_groups[ctx->group_count++] = strdup(name);
    return true;
}

static bool ctx_has_group(ValidationContext *ctx, const char *name)
{
    for (size_t i = 0; i < ctx->group_count; i++)
    {
        if (strcmp(ctx->defined_groups[i], name) == 0)
        {
            return true;
        }
    }
    return false;
}

static int validate_semantics_recursive(json_t *node, ValidationContext *ctx, char **out_error, bool is_root)
{
    if (!node || !json_is_object(node))
        return 0;

    const char *type = get_node_type(node);

    if (type)
    {
        if (strcmp(type, "Group") == 0)
        {
            json_t *capturing_obj = json_object_get(node, "capturing");
            bool capturing = true;
            if (capturing_obj && json_is_boolean(capturing_obj))
            {
                capturing = json_boolean_value(capturing_obj);
            }

            if (capturing)
            {
                ctx->capturing_group_count++;
            }

            json_t *name_obj = json_object_get(node, "name");
            if (name_obj && json_is_string(name_obj))
            {
                const char *name = json_string_value(name_obj);
                if (!ctx_add_group(ctx, name))
                {
                    *out_error = strdup("Duplicate group name");
                    return 1;
                }
            }
        }
        else if (strcmp(type, "BackReference") == 0 || strcmp(type, "Backref") == 0 || strcmp(type, "Backreference") == 0)
        {
            if (is_root)
            {
                return 0;
            }

            json_t *name_obj = json_object_get(node, "name");
            json_t *by_name_obj = json_object_get(node, "byName");
            json_t *index_obj = json_object_get(node, "index");
            json_t *by_index_obj = json_object_get(node, "byIndex");
            json_t *ref_obj = json_object_get(node, "ref");

            const char *name = NULL;
            if (name_obj && json_is_string(name_obj))
                name = json_string_value(name_obj);
            else if (by_name_obj && json_is_string(by_name_obj))
                name = json_string_value(by_name_obj);
            else if (ref_obj && json_is_string(ref_obj))
                name = json_string_value(ref_obj);

            if (name)
            {
                if (!ctx_has_group(ctx, name))
                {
                    *out_error = strdup("Invalid Backreference: undefined group");
                    return 1;
                }
            }

            int index = 0;
            if (index_obj && json_is_integer(index_obj))
                index = json_integer_value(index_obj);
            else if (by_index_obj && json_is_integer(by_index_obj))
                index = json_integer_value(by_index_obj);
            else if (ref_obj && json_is_integer(ref_obj))
                index = json_integer_value(ref_obj);

            if (index > 0)
            {
                if (index > ctx->capturing_group_count)
                {
                    *out_error = strdup("Invalid Backreference: undefined group");
                    return 1;
                }
            }
        }
    }

    void *iter = json_object_iter(node);
    while (iter)
    {
        const char *key = json_object_iter_key(iter);
        json_t *value = json_object_iter_value(iter);

        /* Ignore 'expression' if 'body' exists to avoid duplicate traversal */
        if (strcmp(key, "expression") == 0 && json_object_get(node, "body"))
        {
            iter = json_object_iter_next(node, iter);
            continue;
        }

        if (json_is_object(value))
        {
            if (validate_semantics_recursive(value, ctx, out_error, false) != 0)
                return 1;
        }
        else if (json_is_array(value))
        {
            size_t index;
            json_t *elem;
            json_array_foreach(value, index, elem)
            {
                if (json_is_object(elem))
                {
                    if (validate_semantics_recursive(elem, ctx, out_error, false) != 0)
                        return 1;
                }
            }
        }
        iter = json_object_iter_next(node, iter);
    }
    return 0;
}

STRlingResult *strling_compile(const char *json_str, const STRlingFlags *flags)
{
    if (!json_str)
    {
        return create_error_result("NULL JSON input", 0, "Provide a valid JSON string");
    }

    /* Parse JSON */
    json_error_t error;
    json_t *root = json_loads(json_str, JSON_ALLOW_NUL, &error);
    if (!root)
    {
        char msg[256];
        snprintf(msg, sizeof(msg), "JSON parse error: %s", error.text);
        return create_error_result(msg, error.position, NULL);
    }

    /* Check for STRling AST structure.
       Accept either a bare AST node (root object contains a string "type" or "kind" field),
       the envelope form { "pattern": <AST node>, ... }, or the artifact form
       { "root": <AST node>, "flags": {...} } used by parseToArtifact().
    */
    json_t *pattern_node = NULL;
    /* If the root itself looks like an AST node (has a string "type" or "kind" field),
       treat it as the pattern node. */
    json_t *root_type = json_object_get(root, "type");
    json_t *root_kind = json_object_get(root, "kind");
    if (json_is_object(root) && ((root_type && json_is_string(root_type)) || (root_kind && json_is_string(root_kind))))
    {
        pattern_node = root;
    }
    else
    {
        /* Otherwise look for the envelope key or for the 'root' artifact property */
        pattern_node = json_object_get(root, "pattern");
        if (!pattern_node)
            pattern_node = json_object_get(root, "root");
        if (!pattern_node)
            pattern_node = json_object_get(root, "input_ast");
    }

    if (!pattern_node)
    {
        json_decref(root);
        return create_error_result("Missing 'pattern' field in JSON", 0,
                                   "Expected JSON object with 'pattern' field containing AST or a bare AST node");
    }

    /* Compile the pattern */
    char *pcre2_pattern = NULL;
    char *compile_error = NULL;

    /* Perform semantic validation */
    ValidationContext ctx;
    ctx_init(&ctx);
    if (validate_semantics_recursive(pattern_node, &ctx, &compile_error, true) != 0)
    {
        ctx_free(&ctx);
        json_decref(root);
        STRlingResult *res = create_error_result(compile_error, 0, NULL);
        free(compile_error);
        return res;
    }
    ctx_free(&ctx);

    if (compile_node_to_pcre2(pattern_node, flags, &pcre2_pattern, &compile_error) != 0)
    {
        json_decref(root);
        STRlingResult *res = create_error_result(compile_error, 0, NULL);
        free(compile_error);
        return res;
    }

    /* Determine which flags to use */
    json_t *flags_obj = json_object_get(root, "flags");
    STRlingFlags local_flags = {0};
    if (flags)
    {
        local_flags = *flags;
    }
    else if (flags_obj)
    {
        if (json_is_object(flags_obj))
        {
            json_t *ic = json_object_get(flags_obj, "ignoreCase");
            json_t *ml = json_object_get(flags_obj, "multiline");
            json_t *da = json_object_get(flags_obj, "dotAll");
            json_t *un = json_object_get(flags_obj, "unicode");
            json_t *ex = json_object_get(flags_obj, "extended");

            if (ic && json_is_boolean(ic))
                local_flags.ignoreCase = json_boolean_value(ic);
            if (ml && json_is_boolean(ml))
                local_flags.multiline = json_boolean_value(ml);
            if (da && json_is_boolean(da))
                local_flags.dotAll = json_boolean_value(da);
            if (un && json_is_boolean(un))
                local_flags.unicode = json_boolean_value(un);
            if (ex && json_is_boolean(ex))
                local_flags.extended = json_boolean_value(ex);
        }
        else if (json_is_string(flags_obj))
        {
            const char *flags_str = json_string_value(flags_obj);
            if (strchr(flags_str, 'i'))
                local_flags.ignoreCase = true;
            if (strchr(flags_str, 'm'))
                local_flags.multiline = true;
            if (strchr(flags_str, 's'))
                local_flags.dotAll = true;
            if (strchr(flags_str, 'u'))
                local_flags.unicode = true;
            if (strchr(flags_str, 'x'))
                local_flags.extended = true;
        }
    }

    /* Build flag prefix string if any flags are set */
    char flag_prefix[16] = "";
    int flag_count = 0;

    if (local_flags.ignoreCase || local_flags.multiline || local_flags.dotAll || local_flags.unicode || local_flags.extended)
    {
        flag_prefix[flag_count++] = '(';
        flag_prefix[flag_count++] = '?';

        if (local_flags.ignoreCase)
            flag_prefix[flag_count++] = 'i';
        if (local_flags.multiline)
            flag_prefix[flag_count++] = 'm';
        if (local_flags.dotAll)
            flag_prefix[flag_count++] = 's';
        if (local_flags.unicode)
            flag_prefix[flag_count++] = 'u';
        if (local_flags.extended)
            flag_prefix[flag_count++] = 'x';

        flag_prefix[flag_count++] = ')';
        flag_prefix[flag_count] = '\0';
    }

    /* Build final pattern with flags prefix */
    size_t final_len = strlen(pcre2_pattern) + strlen(flag_prefix) + 1;
    char *final_pattern = (char *)malloc(final_len);

    if (flag_prefix[0] != '\0')
    {
        strcpy(final_pattern, flag_prefix);
        strcat(final_pattern, pcre2_pattern);
    }
    else
    {
        strcpy(final_pattern, pcre2_pattern);
    }

    free(pcre2_pattern);

    json_decref(root);
    STRlingResult *result = create_success_result(final_pattern);
    free(final_pattern); /* Free since create_success_result makes a copy */
    return result;
}

void strling_result_free_ptr(STRlingResult *result)
{
    if (!result)
        return;
    free(result->pattern);
    strling_error_free(result->error);
    free(result);
}
