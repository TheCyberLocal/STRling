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

/* Free a compilation result (pointer-based API) */
void strling_result_free_ptr(STRlingResult* result);

/* ==================== Compatibility Layer (tests) ==================== */
/*
 * The test-suite expects a small, value-oriented API named `strling_compile`
 * returning `strling_result_t` and helpers like `strling_result_free()` that
 * operate on that value. The implementation in `src/strling.c` exposes a
 * pointer-based API (`STRlingResult* strling_compile(...)`). To provide a
 * seamless compatibility layer without changing tests, we expose a wrapper
 * function and map the public `strling_compile` symbol to it via a macro.
 *
 * The wrapper is implemented in `src/compat.c` as `strling_compile_compat`.
 */

typedef struct {
    int error_code;         /* 0 on success */
    char* error_message;    /* NULL on success */
    char* pcre2_pattern;    /* Compiled pattern (NULL on error) */
    int error_position;     /* Position in input, if available */
} strling_result_t;

#define STRling_OK 0

/* Compatibility wrapper prototype (implemented in src/compat.c) */
strling_result_t strling_compile_compat(const char* json_str, const STRlingFlags* flags);

/* Compatibility free (value-based). Implemented in src/compat.c. */
void strling_result_free_compat(strling_result_t* result);

/* Note: We deliberately DO NOT map `strling_compile` or `strling_result_free`
 * to the compatibility layer via macros. Tests that want the value-based
 * API should explicitly call `strling_compile_compat` and
 * `strling_result_free_compat`. This avoids fragile global macro
 * substitution and keeps the public API explicit and maintainable.
 */

#ifdef __cplusplus
}
#endif

#endif /* STRLING_H */
