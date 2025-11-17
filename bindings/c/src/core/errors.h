/*
 * STRling Parse Error - ported from Python
 *
 * Provides a rich error struct describing parse failures. Callers are
 * responsible for freeing returned strings and error objects using the
 * corresponding free functions.
 */
#ifndef STRLING_ERRORS_H
#define STRLING_ERRORS_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct STRlingParseError {
    /* Concise error message */
    char* message;
    /* Character offset (0-indexed) where the error occurred */
    int pos;
    /* Optional full input text */
    char* text;
    /* Optional instructional hint */
    char* hint;
} STRlingParseError;

/* Allocate and initialize a parse error. Strings are copied; caller keeps ownership of inputs. */
STRlingParseError* strling_parse_error_create(const char* message, int pos, const char* text, const char* hint);
/* Free the parse error and owned strings */
void strling_parse_error_free(STRlingParseError* err);
/* Format error into a newly allocated string. Caller must free it. */
char* strling_parse_error_format(const STRlingParseError* err);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_ERRORS_H */
