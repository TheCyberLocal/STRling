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
        
        size_t result_len = 0;
        size_t n = json_array_size(parts);
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
    
    /* Add flags if present */
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
    
    /* Build final pattern with flags */
    size_t final_len = strlen(pcre2_pattern) + 20; /* room for flags */
    char* final_pattern = (char*)malloc(final_len);
    strcpy(final_pattern, pcre2_pattern);
    free(pcre2_pattern);
    
    /* PCRE2 inline flags would go here if needed */
    /* For now, just return the pattern as-is */
    
    json_decref(root);
    return create_success_result(final_pattern);
}

void strling_result_free(STRlingResult* result) {
    if (!result) return;
    free(result->pattern);
    strling_error_free(result->error);
    free(result);
}
