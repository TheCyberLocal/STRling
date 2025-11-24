/*
 * STRling Simply API - Implementation
 *
 * This file implements the high-level fluent API for pattern construction.
 * Each function wraps the verbose AST construction logic into ergonomic
 * helpers that match the TypeScript reference implementation.
 */

#include "../include/strling_simply.h"
#include "core/nodes.h"
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

/* ==================== Factory Functions ==================== */

sl_pattern_t sl_literal(const char* text) {
    return strling_ast_lit_create(text);
}

sl_pattern_t sl_digit(int count) {
    /* Validate count is positive */
    if (count <= 0) return NULL;
    
    /* Create a digit character class using escape sequence */
    STRlingClassItem* digit_escape = strling_class_escape_create("d", NULL);
    if (!digit_escape) return NULL;
    
    STRlingClassItem* items[1] = { digit_escape };
    STRlingASTNode* char_class = strling_ast_charclass_create(false, items, 1);
    if (!char_class) {
        strling_class_item_free(digit_escape);
        return NULL;
    }
    
    /* If count is 1, return the character class directly */
    if (count == 1) {
        return char_class;
    }
    
    /* Otherwise, wrap in a quantifier */
    return strling_ast_quant_create(char_class, count, count, "Greedy");
}

sl_pattern_t sl_any_of(const char* chars) {
    if (!chars || !*chars) return NULL;
    
    size_t len = strlen(chars);
    STRlingClassItem** items = (STRlingClassItem**)malloc(sizeof(STRlingClassItem*) * len);
    if (!items) return NULL;
    
    /* Create a literal class item for each character */
    for (size_t i = 0; i < len; i++) {
        char single_char[2] = { chars[i], '\0' };
        items[i] = strling_class_literal_create(single_char);
        if (!items[i]) {
            /* Cleanup on failure */
            for (size_t j = 0; j < i; j++) {
                strling_class_item_free(items[j]);
            }
            free(items);
            return NULL;
        }
    }
    
    STRlingASTNode* char_class = strling_ast_charclass_create(false, items, len);
    if (!char_class) {
        for (size_t i = 0; i < len; i++) {
            strling_class_item_free(items[i]);
        }
        free(items);
        return NULL;
    }
    
    free(items); /* The char_class now owns the items */
    return char_class;
}

sl_pattern_t sl_dot(void) {
    return strling_ast_dot_create();
}

/* ==================== Anchors ==================== */

sl_pattern_t sl_start(void) {
    return strling_ast_anchor_create("Start");
}

sl_pattern_t sl_end(void) {
    return strling_ast_anchor_create("End");
}

/* ==================== Combinators ==================== */

sl_pattern_t sl_capture(sl_pattern_t inner) {
    if (!inner) return NULL;
    return strling_ast_group_create(true, inner, NULL, false);
}

sl_pattern_t sl_optional(sl_pattern_t inner) {
    if (!inner) return NULL;
    return strling_ast_quant_create(inner, 0, 1, "Greedy");
}

sl_pattern_t sl_seq(int count, ...) {
    if (count <= 0) return NULL;
    
    /* Allocate array for patterns */
    STRlingASTNode** parts = (STRlingASTNode**)malloc(sizeof(STRlingASTNode*) * count);
    if (!parts) return NULL;
    
    /* Collect variadic arguments */
    va_list args;
    va_start(args, count);
    
    for (int i = 0; i < count; i++) {
        parts[i] = va_arg(args, STRlingASTNode*);
        if (!parts[i]) {
            /* On NULL pattern, cleanup previously collected patterns and fail */
            for (int j = 0; j < i; j++) {
                strling_ast_node_free(parts[j]);
            }
            va_end(args);
            free(parts);
            return NULL;
        }
    }
    
    va_end(args);
    
    /* Create sequence node */
    STRlingASTNode* seq = strling_ast_seq_create(parts, count);
    free(parts); /* The sequence now owns the parts array */
    
    return seq;
}

/* ==================== Memory Management ==================== */

void sl_free(sl_pattern_t pattern) {
    strling_ast_node_free(pattern);
}
