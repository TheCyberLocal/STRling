/* Compatibility wrapper to present a value-oriented API expected by tests */
#include "../include/strling.h"

/* Ensure calls to `strling_compile` here refer to the original pointer-based
 * implementation inside src/strling.c rather than being macro-mapped to this
 * compatibility wrapper. */
#undef strling_compile
#undef strling_result_free

#include <stdlib.h>
#include <string.h>

strling_result_t strling_compile_compat(const char* json_str, const STRlingFlags* flags) {
    strling_result_t out;
    out.error_code = 1;
    out.error_message = NULL;
    out.pcre2_pattern = NULL;
    out.error_position = 0;

    /* Call the original pointer-based API */
    STRlingResult* orig = strling_compile(json_str, flags);
    if (!orig) {
        out.error_code = 1;
        out.error_message = strdup("Internal allocation failure");
        return out;
    }

    if (orig->error == NULL) {
        out.error_code = STRling_OK;
        out.pcre2_pattern = orig->pattern ? strdup(orig->pattern) : NULL;
        out.error_message = NULL;
        out.error_position = 0;
    } else {
        out.error_code = 1;
        out.error_message = orig->error->message ? strdup(orig->error->message) : strdup("Unknown error");
        out.pcre2_pattern = orig->pattern ? strdup(orig->pattern) : NULL;
        out.error_position = orig->error->position;
    }

    /* Free the original pointer-based result */
    strling_result_free_ptr(orig);
    return out;
}

void strling_result_free_compat(strling_result_t* result) {
    if (!result) return;
    free(result->pcre2_pattern);
    free(result->error_message);
    result->pcre2_pattern = NULL;
    result->error_message = NULL;
}
