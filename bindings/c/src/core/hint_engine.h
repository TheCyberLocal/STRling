/*
 * STRling Hint Engine — Context-Aware Error Hints (C Binding)
 *
 * Provides intelligent, beginner-friendly hints for common syntax errors.
 * Maps specific error types and contexts to instructional messages that
 * help users understand and fix their mistakes.
 *
 * Design: zero heap allocation, error-path-only. All output is written
 * to caller-provided buffers.
 */
#ifndef STRLING_HINT_ENGINE_H
#define STRLING_HINT_ENGINE_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Generic fallback hint used when no specific hint pattern matches.
 * Contractual default for `expected_hint` in conformance fixtures.
 */
#define STRLING_GENERIC_HINT_FALLBACK \
    "Check the STRling documentation for help with this syntax."

/*
 * Get a context-aware hint for the given parse error.
 *
 * Writes a helpful, instructional message into `hint_buffer` based on
 * the error message and context. If no specific hint matches, the
 * generic fallback is written.
 *
 * Parameters:
 *   error_message - The error message string from the parser
 *   pattern       - The full input text being parsed (may be NULL)
 *   fail_index    - The position where the error occurred
 *   hint_buffer   - Caller-provided buffer for the hint output
 *   buffer_size   - Size of hint_buffer in bytes
 *
 * Returns:
 *   The number of bytes written (excluding NUL terminator), or the
 *   number of bytes that would have been written if the buffer were
 *   large enough (like snprintf). Returns 0 on NULL inputs.
 */
size_t strling_get_hint(const char* error_message,
                        const char* pattern,
                        size_t fail_index,
                        char* hint_buffer,
                        size_t buffer_size);

/*
 * Get a hint for the given error, returning NULL if no specific hint
 * matches (does not fall back to the generic hint).
 *
 * Returns a pointer to a static string, or NULL.
 * The returned pointer must NOT be freed.
 */
const char* strling_get_hint_static(const char* error_message,
                                    const char* pattern,
                                    size_t fail_index);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_HINT_ENGINE_H */
