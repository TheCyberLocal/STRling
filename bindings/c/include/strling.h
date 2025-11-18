/*
 * Public API header for STRling C binding
 *
 * This header defines the public API for the STRling library. Core
 * implementation details live under `src/core/` and are not exposed here.
 */
#ifndef STRLING_H
#define STRLING_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>
#include <stdbool.h>

/* Library version */
const char* strling_version(void);

/* ==================== Error Handling ==================== */

typedef struct STRlingError {
    char* message;
    int position;
    char* hint;
} STRlingError;

/* Free an error object */
void strling_error_free(STRlingError* error);

/* ==================== Pattern Compilation ==================== */

/* Compilation result - either a pattern or an error */
typedef struct STRlingResult {
    char* pattern;        /* Compiled PCRE2 pattern (NULL on error) */
    STRlingError* error;  /* Error details (NULL on success) */
} STRlingResult;

/* Compilation flags */
typedef struct STRlingFlags {
    bool ignoreCase;
    bool multiline;
    bool dotAll;
    bool unicode;
    bool extended;
} STRlingFlags;

/* Create default flags */
STRlingFlags* strling_flags_create(void);

/* Free flags */
void strling_flags_free(STRlingFlags* flags);

/* Compile a JSON AST to a PCRE2 pattern 
 * json_str: JSON string containing STRling AST
 * flags: Compilation flags (can be NULL for defaults)
 * Returns: Result containing pattern or error. Caller must free with strling_result_free()
 */
STRlingResult* strling_compile(const char* json_str, const STRlingFlags* flags);

/* Free a compilation result */
void strling_result_free(STRlingResult* result);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_H */
