/* Main public API implementation for STRling C binding */
#include "../include/strling.h"
#include "core/nodes.h"
#include "core/errors.h"
#include <stdlib.h>
#include <string.h>
#include <jansson.h>

const char* strling_version(void) {
    return "0.1.0";
}

/* ==================== Error Handling ==================== */

void strling_error_free(STRlingError* error) {
    if (!error) return;
    free(error->message);
    free(error->hint);
    free(error);
}

/* ==================== Flags ==================== */

STRlingFlags* strling_flags_create(void) {
    STRlingFlags* flags = (STRlingFlags*)calloc(1, sizeof(STRlingFlags));
    if (!flags) return NULL;
    /* All flags default to false */
    return flags;
}

void strling_flags_free(STRlingFlags* flags) {
    free(flags);
}

/* ==================== Compilation ==================== */

/* Helper to create error result */
static STRlingResult* create_error_result(const char* message, int position, const char* hint) {
    STRlingResult* result = (STRlingResult*)calloc(1, sizeof(STRlingResult));
    if (!result) return NULL;
    
    result->error = (STRlingError*)malloc(sizeof(STRlingError));
    if (!result->error) {
        free(result);
        return NULL;
    }
    
    result->error->message = message ? strdup(message) : NULL;
    result->error->position = position;
    result->error->hint = hint ? strdup(hint) : NULL;
    result->pattern = NULL;
    
    return result;
}

/* Helper to create success result */
static STRlingResult* create_success_result(const char* pattern) {
    STRlingResult* result = (STRlingResult*)calloc(1, sizeof(STRlingResult));
    if (!result) return NULL;
    
    result->pattern = pattern ? strdup(pattern) : NULL;
    result->error = NULL;
    
    return result;
}

/* Parse JSON and extract node type */
static const char* get_node_type(json_t* node) {
    json_t* type = json_object_get(node, "type");
    if (!type || !json_is_string(type)) return NULL;
    return json_string_value(type);
}

/* Simple recursive compiler for basic nodes */
static char* compile_node_to_pcre2(json_t* node, const STRlingFlags* flags) {
    if (!node) return NULL;
    
    const char* type = get_node_type(node);
    if (!type) return strdup("");
    
    /* Handle Literal */
    if (strcmp(type, "Literal") == 0) {
        json_t* value = json_object_get(node, "value");
        if (!value || !json_is_string(value)) return strdup("");
        const char* lit = json_string_value(value);
        
        /* Escape special regex characters */
        size_t len = strlen(lit);
        char* result = (char*)malloc(len * 2 + 1);
        char* p = result;
        for (size_t i = 0; i < len; i++) {
            char c = lit[i];
            /* Escape special PCRE2 characters */
            if (strchr(".^$*+?{}[]()\\|", c)) {
                *p++ = '\\';
            }
            *p++ = c;
        }
        *p = '\0';
        return result;
    }
    
    /* Handle Sequence */
    if (strcmp(type, "Sequence") == 0) {
        json_t* parts = json_object_get(node, "parts");
        if (!parts || !json_is_array(parts)) return strdup("");
        
        size_t n = json_array_size(parts);
        
        /* Handle empty sequence */
        if (n == 0) {
            return strdup("");
        }
        
        size_t result_len = 0;
        char** part_strs = (char**)malloc(n * sizeof(char*));
        
        for (size_t i = 0; i < n; i++) {
            part_strs[i] = compile_node_to_pcre2(json_array_get(parts, i), flags);
            result_len += strlen(part_strs[i]);
        }
        
        char* result = (char*)malloc(result_len + 1);
        char* p = result;
        for (size_t i = 0; i < n; i++) {
            strcpy(p, part_strs[i]);
            p += strlen(part_strs[i]);
            free(part_strs[i]);
        }
        *p = '\0'; /* Ensure null termination */
        free(part_strs);
        return result;
    }
    
    /* Handle Anchor */
    if (strcmp(type, "Anchor") == 0) {
        json_t* at = json_object_get(node, "at");
        if (!at || !json_is_string(at)) return strdup("");
        const char* anchor_type = json_string_value(at);
        
        if (strcmp(anchor_type, "Start") == 0) return strdup("^");
        if (strcmp(anchor_type, "End") == 0) return strdup("$");
        if (strcmp(anchor_type, "WordBoundary") == 0) return strdup("\\b");
        if (strcmp(anchor_type, "NonWordBoundary") == 0) return strdup("\\B");
        if (strcmp(anchor_type, "AbsoluteStart") == 0) return strdup("\\A");
        if (strcmp(anchor_type, "AbsoluteEnd") == 0) return strdup("\\Z");
        if (strcmp(anchor_type, "AbsoluteEndOnly") == 0) return strdup("\\z");
        return strdup("");
    }
    
    /* Handle Dot (any character) */
    if (strcmp(type, "Dot") == 0) {
        return strdup(".");
    }
    
    /* Handle Quantifier */
    if (strcmp(type, "Quantifier") == 0) {
        json_t* target = json_object_get(node, "target");
        json_t* min_obj = json_object_get(node, "min");
        json_t* max_obj = json_object_get(node, "max");
        json_t* lazy_obj = json_object_get(node, "lazy");
        json_t* possessive_obj = json_object_get(node, "possessive");
        
        if (!target || !min_obj) return strdup("");
        
        /* Compile the target first */
        char* target_str = compile_node_to_pcre2(target, flags);
        if (!target_str) return strdup("");
        
        /* Get min and max values */
        int min = json_integer_value(min_obj);
        int max = -1; /* -1 represents null/infinity */
        if (max_obj && json_is_integer(max_obj)) {
            max = json_integer_value(max_obj);
        }
        
        /* Check for lazy and possessive modifiers */
        bool lazy = lazy_obj && json_is_true(lazy_obj);
        bool possessive = possessive_obj && json_is_true(possessive_obj);
        
        /* Build the quantifier string */
        char quantifier[32] = "";
        
        /* Special case: {1,1} means no quantifier needed */
        if (min == 1 && max == 1) {
            /* No quantifier needed, just return target */
            return target_str;
        }
        /* Standard quantifiers */
        else if (min == 0 && max == -1) {
            strcpy(quantifier, "*");
        }
        else if (min == 1 && max == -1) {
            strcpy(quantifier, "+");
        }
        else if (min == 0 && max == 1) {
            strcpy(quantifier, "?");
        }
        /* Brace quantifiers */
        else if (min == max) {
            snprintf(quantifier, sizeof(quantifier), "{%d}", min);
        }
        else if (max == -1) {
            snprintf(quantifier, sizeof(quantifier), "{%d,}", min);
        }
        else {
            snprintf(quantifier, sizeof(quantifier), "{%d,%d}", min, max);
        }
        
        /* Add lazy or possessive modifier */
        if (lazy) {
            strcat(quantifier, "?");
        }
        else if (possessive) {
            strcat(quantifier, "+");
        }
        
        /* Combine target and quantifier */
        size_t result_len = strlen(target_str) + strlen(quantifier) + 1;
        char* result = (char*)malloc(result_len);
        strcpy(result, target_str);
        strcat(result, quantifier);
        
        free(target_str);
        return result;
    }
    
    /* Handle Alternation */
    if (strcmp(type, "Alternation") == 0) {
        json_t* alternatives = json_object_get(node, "alternatives");
        if (!alternatives || !json_is_array(alternatives)) return strdup("");
        
        size_t n = json_array_size(alternatives);
        if (n == 0) return strdup("");
        
        /* Compile all alternatives */
        char** alt_strs = (char**)malloc(n * sizeof(char*));
        size_t total_len = 0;
        
        for (size_t i = 0; i < n; i++) {
            alt_strs[i] = compile_node_to_pcre2(json_array_get(alternatives, i), flags);
            total_len += strlen(alt_strs[i]);
        }
        
        /* Add space for separators and parentheses: ( alt1 | alt2 | ... ) */
        /* We need (n-1) separators of " | " (but we'll use just "|" for compactness) */
        total_len += (n - 1); /* for | separators */
        total_len += 2; /* for parentheses */
        total_len += 1; /* for null terminator */
        
        char* result = (char*)malloc(total_len);
        char* p = result;
        
        /* Add opening parenthesis */
        *p++ = '(';
        
        /* Join alternatives with | */
        for (size_t i = 0; i < n; i++) {
            strcpy(p, alt_strs[i]);
            p += strlen(alt_strs[i]);
            if (i < n - 1) {
                *p++ = '|';
            }
            free(alt_strs[i]);
        }
        
        /* Add closing parenthesis */
        *p++ = ')';
        *p = '\0';
        
        free(alt_strs);
        return result;
    }
    
    /* Handle CharacterClass */
    if (strcmp(type, "CharacterClass") == 0) {
        json_t* negated_obj = json_object_get(node, "negated");
        json_t* members = json_object_get(node, "members");
        
        if (!members || !json_is_array(members)) return strdup("");
        
        bool negated = negated_obj && json_is_true(negated_obj);
        size_t n = json_array_size(members);
        
        /* Build the character class string */
        size_t result_capacity = 256; /* Initial capacity */
        char* result = (char*)malloc(result_capacity);
        size_t result_len = 0;
        
        /* Start with [ */
        result[result_len++] = '[';
        
        /* Add ^ if negated */
        if (negated) {
            result[result_len++] = '^';
        }
        
        /* Process each member */
        for (size_t i = 0; i < n; i++) {
            json_t* member = json_array_get(members, i);
            if (!member) continue;
            
            const char* member_type = get_node_type(member);
            if (!member_type) continue;
            
            /* Ensure we have enough space (conservative estimate) */
            if (result_len + 50 > result_capacity) {
                result_capacity *= 2;
                char* new_result = (char*)realloc(result, result_capacity);
                if (!new_result) {
                    free(result);
                    return strdup("");
                }
                result = new_result;
            }
            
            /* Handle Range: {"type": "Range", "from": "a", "to": "z"} */
            if (strcmp(member_type, "Range") == 0) {
                json_t* from_obj = json_object_get(member, "from");
                json_t* to_obj = json_object_get(member, "to");
                
                if (from_obj && json_is_string(from_obj) && 
                    to_obj && json_is_string(to_obj)) {
                    const char* from = json_string_value(from_obj);
                    const char* to = json_string_value(to_obj);
                    
                    /* Ensure strings are not empty before accessing [0] */
                    if (from && from[0] && to && to[0]) {
                        /* Emit as "from-to" */
                        result[result_len++] = from[0];
                        result[result_len++] = '-';
                        result[result_len++] = to[0];
                    }
                }
            }
            /* Handle Meta: {"type": "Meta", "value": "d"} */
            else if (strcmp(member_type, "Meta") == 0) {
                json_t* value_obj = json_object_get(member, "value");
                if (value_obj && json_is_string(value_obj)) {
                    const char* value = json_string_value(value_obj);
                    /* Ensure string is not empty before accessing [0] */
                    if (value && value[0]) {
                        /* Emit as \value */
                        result[result_len++] = '\\';
                        result[result_len++] = value[0];
                    }
                }
            }
            /* Handle Literal: {"type": "Literal", "value": "x"} */
            else if (strcmp(member_type, "Literal") == 0) {
                json_t* value_obj = json_object_get(member, "value");
                if (value_obj && json_is_string(value_obj)) {
                    const char* value = json_string_value(value_obj);
                    /* Ensure string is not empty before accessing [0] */
                    if (value && value[0]) {
                        /* Special characters in character classes that need escaping */
                        char c = value[0];
                        if (c == ']' || c == '\\' || c == '^') {
                            result[result_len++] = '\\';
                        }
                        result[result_len++] = c;
                    }
                }
            }
            /* Handle UnicodeProperty: {"type": "UnicodeProperty", "name": "Script", "value": "Latin", "negated": false} */
            else if (strcmp(member_type, "UnicodeProperty") == 0) {
                json_t* name_obj = json_object_get(member, "name");
                json_t* value_obj = json_object_get(member, "value");
                json_t* neg_obj = json_object_get(member, "negated");
                
                bool is_negated = neg_obj && json_is_true(neg_obj);
                
                if (value_obj && json_is_string(value_obj)) {
                    const char* value = json_string_value(value_obj);
                    const char* name = NULL;
                    size_t value_len = value ? strlen(value) : 0;
                    size_t name_len = 0;
                    
                    if (name_obj && json_is_string(name_obj)) {
                        name = json_string_value(name_obj);
                        name_len = name ? strlen(name) : 0;
                    }
                    
                    /* Calculate total space needed: \p{name=value} or \p{value} */
                    size_t needed = 4 + value_len + name_len + (name ? 1 : 0); /* \p{} + name= + value */
                    
                    /* Ensure we have enough space */
                    while (result_len + needed >= result_capacity) {
                        result_capacity *= 2;
                        char* new_result = (char*)realloc(result, result_capacity);
                        if (!new_result) {
                            free(result);
                            return strdup("");
                        }
                        result = new_result;
                    }
                    
                    /* Start with \p or \P */
                    result[result_len++] = '\\';
                    result[result_len++] = is_negated ? 'P' : 'p';
                    result[result_len++] = '{';
                    
                    /* Add name=value if name is present, otherwise just value */
                    if (name && name_len > 0) {
                        memcpy(result + result_len, name, name_len);
                        result_len += name_len;
                        result[result_len++] = '=';
                    }
                    
                    if (value && value_len > 0) {
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
        
        return result;
    }
    
    /* Handle Meta (standalone escape sequences like \b, \d, etc.) */
    if (strcmp(type, "Meta") == 0) {
        json_t* value_obj = json_object_get(node, "value");
        if (value_obj && json_is_string(value_obj)) {
            const char* value = json_string_value(value_obj);
            if (value && value[0]) {
                /* Emit as \value */
                char* result = (char*)malloc(3); /* \ + char + \0 */
                result[0] = '\\';
                result[1] = value[0];
                result[2] = '\0';
                return result;
            }
        }
        return strdup("");
    }
    
    /* Handle Group */
    if (strcmp(type, "Group") == 0) {
        json_t* body = json_object_get(node, "body");
        json_t* capturing_obj = json_object_get(node, "capturing");
        json_t* name_obj = json_object_get(node, "name");
        json_t* atomic_obj = json_object_get(node, "atomic");
        
        if (!body) return strdup("");
        
        /* Compile the body */
        char* body_str = compile_node_to_pcre2(body, flags);
        if (!body_str) return strdup("");
        
        /* Determine group type */
        bool capturing = true; /* Default is capturing */
        bool atomic = false;
        const char* name = NULL;
        
        if (capturing_obj && json_is_boolean(capturing_obj)) {
            capturing = json_boolean_value(capturing_obj);
        }
        if (atomic_obj && json_is_boolean(atomic_obj)) {
            atomic = json_boolean_value(atomic_obj);
        }
        if (name_obj && json_is_string(name_obj)) {
            name = json_string_value(name_obj);
        }
        
        /* Build the group string */
        size_t body_len = strlen(body_str);
        size_t result_len;
        char* result;
        
        if (atomic) {
            /* Atomic group: (?>...) */
            result_len = 4 + body_len + 1; /* (?> + body + ) + \0 */
            result = (char*)malloc(result_len);
            snprintf(result, result_len, "(?>%s)", body_str);
        } else if (name) {
            /* Named capturing group: (?<name>...) */
            size_t name_len = strlen(name);
            result_len = 4 + name_len + body_len + 2; /* (?< + name + > + body + ) + \0 */
            result = (char*)malloc(result_len);
            snprintf(result, result_len, "(?<%s>%s)", name, body_str);
        } else if (!capturing) {
            /* Non-capturing group: (?:...) */
            result_len = 4 + body_len + 1; /* (?: + body + ) + \0 */
            result = (char*)malloc(result_len);
            snprintf(result, result_len, "(?:%s)", body_str);
        } else {
            /* Capturing group: (...) */
            result_len = 2 + body_len + 1; /* ( + body + ) + \0 */
            result = (char*)malloc(result_len);
            snprintf(result, result_len, "(%s)", body_str);
        }
        
        free(body_str);
        return result;
    }
    
    /* Handle Backreference */
    if (strcmp(type, "Backreference") == 0) {
        json_t* index_obj = json_object_get(node, "index");
        json_t* name_obj = json_object_get(node, "name");
        
        if (name_obj && json_is_string(name_obj)) {
            /* Named backreference: \k<name> */
            const char* name = json_string_value(name_obj);
            size_t name_len = strlen(name);
            size_t result_len = 4 + name_len + 1; /* \k< + name + > + \0 */
            char* result = (char*)malloc(result_len);
            snprintf(result, result_len, "\\k<%s>", name);
            return result;
        } else if (index_obj && json_is_integer(index_obj)) {
            /* Numeric backreference: \1, \2, etc. */
            int index = json_integer_value(index_obj);
            char* result = (char*)malloc(16); /* Enough for \<digits> */
            snprintf(result, 16, "\\%d", index);
            return result;
        }
        return strdup("");
    }
    
    /* Handle Lookahead */
    if (strcmp(type, "Lookahead") == 0) {
        json_t* body = json_object_get(node, "body");
        if (!body) return strdup("");
        
        char* body_str = compile_node_to_pcre2(body, flags);
        if (!body_str) return strdup("");
        
        /* Positive lookahead: (?=...) */
        size_t body_len = strlen(body_str);
        size_t result_len = 4 + body_len + 1; /* (?= + body + ) + \0 */
        char* result = (char*)malloc(result_len);
        snprintf(result, result_len, "(?=%s)", body_str);
        
        free(body_str);
        return result;
    }
    
    /* Handle NegativeLookahead */
    if (strcmp(type, "NegativeLookahead") == 0) {
        json_t* body = json_object_get(node, "body");
        if (!body) return strdup("");
        
        char* body_str = compile_node_to_pcre2(body, flags);
        if (!body_str) return strdup("");
        
        /* Negative lookahead: (?!...) */
        size_t body_len = strlen(body_str);
        size_t result_len = 4 + body_len + 1; /* (?! + body + ) + \0 */
        char* result = (char*)malloc(result_len);
        snprintf(result, result_len, "(?!%s)", body_str);
        
        free(body_str);
        return result;
    }
    
    /* Handle Lookbehind */
    if (strcmp(type, "Lookbehind") == 0) {
        json_t* body = json_object_get(node, "body");
        if (!body) return strdup("");
        
        char* body_str = compile_node_to_pcre2(body, flags);
        if (!body_str) return strdup("");
        
        /* Positive lookbehind: (?<=...) */
        size_t body_len = strlen(body_str);
        size_t result_len = 5 + body_len + 1; /* (?<= + body + ) + \0 */
        char* result = (char*)malloc(result_len);
        snprintf(result, result_len, "(?<=%s)", body_str);
        
        free(body_str);
        return result;
    }
    
    /* Handle NegativeLookbehind */
    if (strcmp(type, "NegativeLookbehind") == 0) {
        json_t* body = json_object_get(node, "body");
        if (!body) return strdup("");
        
        char* body_str = compile_node_to_pcre2(body, flags);
        if (!body_str) return strdup("");
        
        /* Negative lookbehind: (?<!...) */
        size_t body_len = strlen(body_str);
        size_t result_len = 5 + body_len + 1; /* (?<! + body + ) + \0 */
        char* result = (char*)malloc(result_len);
        snprintf(result, result_len, "(?<!%s)", body_str);
        
        free(body_str);
        return result;
    }
    
    /* Unsupported node types return empty for now */
    return strdup("");
}

STRlingResult* strling_compile(const char* json_str, const STRlingFlags* flags) {
    if (!json_str) {
        return create_error_result("NULL JSON input", 0, "Provide a valid JSON string");
    }
    
    /* Parse JSON */
    json_error_t error;
    json_t* root = json_loads(json_str, 0, &error);
    if (!root) {
        char msg[256];
        snprintf(msg, sizeof(msg), "JSON parse error: %s", error.text);
        return create_error_result(msg, error.position, NULL);
    }
    
    /* Check for STRling AST structure */
    json_t* pattern_node = json_object_get(root, "pattern");
    if (!pattern_node) {
        json_decref(root);
        return create_error_result("Missing 'pattern' field in JSON", 0, 
                                   "Expected JSON object with 'pattern' field containing AST");
    }
    
    /* Compile the pattern */
    char* pcre2_pattern = compile_node_to_pcre2(pattern_node, flags);
    
    /* Determine which flags to use */
    json_t* flags_obj = json_object_get(root, "flags");
    STRlingFlags local_flags = {0};
    if (flags) {
        local_flags = *flags;
    } else if (flags_obj && json_is_object(flags_obj)) {
        json_t* ic = json_object_get(flags_obj, "ignoreCase");
        json_t* ml = json_object_get(flags_obj, "multiline");
        json_t* da = json_object_get(flags_obj, "dotAll");
        json_t* un = json_object_get(flags_obj, "unicode");
        json_t* ex = json_object_get(flags_obj, "extended");
        
        if (ic && json_is_boolean(ic)) local_flags.ignoreCase = json_boolean_value(ic);
        if (ml && json_is_boolean(ml)) local_flags.multiline = json_boolean_value(ml);
        if (da && json_is_boolean(da)) local_flags.dotAll = json_boolean_value(da);
        if (un && json_is_boolean(un)) local_flags.unicode = json_boolean_value(un);
        if (ex && json_is_boolean(ex)) local_flags.extended = json_boolean_value(ex);
    }
    
    /* Build flag prefix string if any flags are set */
    char flag_prefix[16] = "";
    int flag_count = 0;
    
    if (local_flags.ignoreCase || local_flags.multiline || local_flags.dotAll || local_flags.extended) {
        flag_prefix[flag_count++] = '(';
        flag_prefix[flag_count++] = '?';
        
        if (local_flags.ignoreCase) flag_prefix[flag_count++] = 'i';
        if (local_flags.multiline) flag_prefix[flag_count++] = 'm';
        if (local_flags.dotAll) flag_prefix[flag_count++] = 's';
        if (local_flags.extended) flag_prefix[flag_count++] = 'x';
        
        flag_prefix[flag_count++] = ')';
        flag_prefix[flag_count] = '\0';
    }
    
    /* Build final pattern with flags prefix */
    size_t final_len = strlen(pcre2_pattern) + strlen(flag_prefix) + 1;
    char* final_pattern = (char*)malloc(final_len);
    
    if (flag_prefix[0] != '\0') {
        strcpy(final_pattern, flag_prefix);
        strcat(final_pattern, pcre2_pattern);
    } else {
        strcpy(final_pattern, pcre2_pattern);
    }
    
    free(pcre2_pattern);
    
    json_decref(root);
    STRlingResult* result = create_success_result(final_pattern);
    free(final_pattern); /* Free since create_success_result makes a copy */
    return result;
}

void strling_result_free(STRlingResult* result) {
    if (!result) return;
    free(result->pattern);
    strling_error_free(result->error);
    free(result);
}
