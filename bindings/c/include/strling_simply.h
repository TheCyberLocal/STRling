/*
 * STRling Simply API - Fluent Pattern Builder for C
 *
 * This header provides a high-level, ergonomic interface for constructing
 * STRling patterns in C. The Simply API wraps the verbose AST construction
 * functions with short, intuitive helpers that follow the TypeScript reference
 * implementation.
 *
 * Key Design Principles:
 * - Short prefix (sl_) for readability
 * - Fluent API with minimal boilerplate
 * - Memory ownership transferred up the chain (single root free)
 * - Direct mapping to TypeScript Simply API
 */

#ifndef STRLING_SIMPLY_H
#define STRLING_SIMPLY_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>
#include <stdbool.h>

/* Forward declaration - actual definition in core/nodes.h */
typedef struct STRlingASTNode STRlingASTNode;

/* Convenience type alias for pattern building */
typedef STRlingASTNode* sl_pattern_t;

/* ==================== Factory Functions ==================== */

/**
 * Create a literal pattern from a string.
 * 
 * @param text The literal text to match
 * @return A new pattern node (must be freed with strling_ast_node_free)
 */
sl_pattern_t sl_literal(const char* text);

/**
 * Create a digit pattern (\d).
 * 
 * @param count Number of digits to match (if count > 1, wraps in quantifier)
 * @return A new pattern node
 */
sl_pattern_t sl_digit(int count);

/**
 * Create a character class pattern from a string.
 * Each character in the string becomes a literal member of the class.
 * 
 * @param chars String of characters to match (e.g., "-. " for separators)
 * @return A new pattern node
 */
sl_pattern_t sl_any_of(const char* chars);

/**
 * Create a dot (any character) pattern.
 * 
 * @return A new pattern node
 */
sl_pattern_t sl_dot(void);

/* ==================== Anchors ==================== */

/**
 * Create a start-of-line anchor (^).
 * 
 * @return A new pattern node
 */
sl_pattern_t sl_start(void);

/**
 * Create an end-of-line anchor ($).
 * 
 * @return A new pattern node
 */
sl_pattern_t sl_end(void);

/* ==================== Combinators ==================== */

/**
 * Create a capturing group around a pattern.
 * 
 * @param inner The pattern to capture
 * @return A new group node
 */
sl_pattern_t sl_capture(sl_pattern_t inner);

/**
 * Create an optional pattern (0 or 1 repetitions).
 * 
 * @param inner The pattern to make optional
 * @return A new quantifier node
 */
sl_pattern_t sl_may(sl_pattern_t inner);

/**
 * Create a sequence pattern from multiple parts.
 * 
 * @param count Number of parts
 * @param ... Variable arguments of type sl_pattern_t
 * @return A new sequence node
 */
sl_pattern_t sl_merge(int count, ...);

/* ==================== Memory Management ==================== */

/**
 * Free a pattern and all its child nodes.
 * 
 * This is the same as strling_ast_node_free but provided here for convenience.
 * Call this on the root pattern to free the entire tree.
 * 
 * @param pattern The root pattern to free
 */
void sl_free(sl_pattern_t pattern);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_SIMPLY_H */
