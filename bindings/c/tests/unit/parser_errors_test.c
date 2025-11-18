/**
 * @file parser_errors_test.c
 *
 * ## Purpose
 * This test suite validates that the parser produces rich, instructional error
 * messages in the "Visionary State" format with:
 * - Context line showing the error location
 * - Caret (^) pointing to the exact position
 * - Helpful hints explaining how to fix the error
 *
 * These tests intentionally pass invalid syntax to ensure the error messages
 * are helpful and educational.
 *
 * C Translation of `parser_errors.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <cmocka.h>

// --- Error Handling Definitions (Mocked) --------------------------------------

/**
 * @struct STRlingParseError_t
 * A C struct mirroring the `STRlingParseError` class, including context.
 */
typedef struct {
    char* message;
    int pos;
    char* text; // The full source text
    char* hint; // The instructional hint
} STRlingParseError_t;

/**
 * @brief Global error object, set by the mock `strling_parse` on failure.
 * C equivalent of a thrown exception.
 */
static STRlingParseError_t* g_last_parse_error = NULL;

/**
 * @brief Helper to create and set the global error.
 * Replaces `throw new STRlingParseError(...)`.
 */
void set_global_error(const char* message, int pos, const char* text, const char* hint) {
    // Free any existing error
    if (g_last_parse_error) {
        free(g_last_parse_error->message);
        free(g_last_parse_error->text);
        free(g_last_parse_error->hint);
        free(g_last_parse_error);
    }
    
    g_last_parse_error = (STRlingParseError_t*)malloc(sizeof(STRlingParseError_t));
    if (g_last_parse_error) {
        g_last_parse_error->message = strdup(message);
        g_last_parse_error->pos = pos;
        g_last_parse_error->text = text ? strdup(text) : NULL;
        g_last_parse_error->hint = hint ? strdup(hint) : NULL;
    }
}

/**
 * @brief Teardown function for cmocka to clean up the global error.
 */
int teardown_error(void** state) {
    (void)state; // Unused
    if (g_last_parse_error) {
        free(g_last_parse_error->message);
        free(g_last_parse_error->text);
        free(g_last_parse_error->hint);
        free(g_last_parse_error);
        g_last_parse_error = NULL;
    }
    return 0;
}

// --- SUT: `STRlingError_toString()` -------------------------------------------

/**
 * @brief [SUT] Generates the "Visionary Format" string from an error.
 * This is the C equivalent of the `toString()` method on the error class.
 * Caller must free the returned string.
 */
char* STRlingError_toString(STRlingParseError_t* err) {
    if (!err) return NULL;

    // Handle simple case (no text context)
    if (!err->text) {
        char* buf = (char*)malloc(1024);
        snprintf(buf, 1024, "STRling Parse Error: %s at position %d", err->message, err->pos);
        return buf;
    }

    // --- Build "Visionary Format" ---

    // 1. Calculate line/col (simplified to 1-based column for this test)
    int line = 1;
    int col = err->pos + 1;

    // 2. Create the caret string (e.g., "      ^")
    char* caret_padding = (char*)malloc(col + 1); // col-1 spaces + '^' + '\0'
    if (col > 1) {
        memset(caret_padding, ' ', col - 1);
    }
    caret_padding[col - 1] = '^';
    caret_padding[col] = '\0';

    // 3. Allocate a large buffer for the final string
    // (A real implementation would use snprintf(NULL, 0) to get size)
    char* output_buf = (char*)malloc(4096);
    int offset = 0;

    // 4. Format the main error message
    offset += snprintf(output_buf, 4096,
        "STRling Parse Error: %s at line %d, column %d:\n"
        "\n"
        "> %d | %s\n"
        "      %s\n", // "      " aligns with "> 1 | "
        err->message, line, col,
        line, err->text,
        caret_padding
    );

    // 5. Add the hint if it exists
    if (err->hint) {
        offset += snprintf(output_buf + offset, 4096 - offset,
            "\nHint: %s\n", err->hint);
    }

    free(caret_padding);
    return output_buf;
}


// --- Mock SUT (`strling_parse`) -----------------------------------------------

// A dummy pointer to represent a successful parse (non-NULL)
static int g_dummy_ast;
#define SUCCESS_AST ((void*)&g_dummy_ast)

/**
 * @brief Mock of the `parse` function (System Under Test).
 * It returns NULL on failure and sets `g_last_parse_error`, mimicking
 * a thrown exception.
 */
void* strling_parse(const char* src) {
    // Clear previous error (important for test isolation)
    teardown_error(NULL);

    if (strcmp(src, "(a|b))") == 0) {
        set_global_error("Unmatched ')'", 5, src, "Did you mean to escape it");
        return NULL;
    }
    if (strcmp(src, "a(b") == 0) {
        set_global_error("Unterminated group", 3, src, "Add a matching ')'");
        return NULL;
    }
    if (strcmp(src, "abc{2,") == 0) {
        set_global_error("Incomplete quantifier", 6, src, "Did you forget the '}'?");
        return NULL;
    }
    if (strcmp(src, "(") == 0) {
        set_global_error("Unterminated group", 1, src, "Add a matching ')'");
        return NULL;
    }
    if (strcmp(src, "abc)") == 0) {
        set_global_error("Unmatched ')'", 3, src, "Did you mean to escape it");
        return NULL;
    }
    if (strcmp(src, ")") == 0) {
        set_global_error("Unmatched ')'", 0, src, "Did you mean to escape it");
        return NULL;
    }

    // If no error matched, return a non-NULL "success" pointer
    return SUCCESS_AST;
}


// --- Test Cases ---------------------------------------------------------------

/**
 * @brief Corresponds to "describe('Rich Error Formatting', ...)"
 */
static void test_rich_error_formatting(void** state) {
    (void)state; // Unused
    
    // Test: "unmatched closing paren shows visionary format"
    void* ast1 = strling_parse("(a|b))");
    assert_null(ast1); // Check for "throw"
    assert_non_null(g_last_parse_error);

    char* formatted1 = STRlingError_toString(g_last_parse_error);
    assert_non_null(formatted1);
    
    // Check all components of visionary format
    assert_non_null(strstr(formatted1, "STRling Parse Error:"));
    assert_non_null(strstr(formatted1, "Unmatched ')'"));
    assert_non_null(strstr(formatted1, "> 1 | (a|b))"));
    assert_non_null(strstr(formatted1, "^"));
    assert_non_null(strstr(formatted1, "Hint:"));
    assert_non_null(strstr(formatted1, "Did you mean to escape it"));
    
    free(formatted1);

    // Test: "unterminated group shows helpful hint"
    void* ast2 = strling_parse("a(b");
    assert_null(ast2);
    assert_non_null(g_last_parse_error);
    assert_non_null(g_last_parse_error->hint);
    assert_non_null(strstr(g_last_parse_error->hint, "Add a matching ')'"));

    // Test: "incomplete quantifier shows helpful hint"
    void* ast3 = strling_parse("abc{2,");
    assert_null(ast3);
    assert_non_null(g_last_parse_error);
    assert_non_null(g_last_parse_error->hint);
    assert_non_null(strstr(g_last_parse_error->hint, "Did you forget the '}'?"));
    assert_int_equal(g_last_parse_error->pos, 6);
}

/**
 * @brief Corresponds to "describe('Error Backward Compatibility', ...)"
 */
static void test_error_backward_compatibility(void** state) {
    (void)state; // Unused

    // Test: "error has message attribute"
    void* ast1 = strling_parse("(");
    assert_null(ast1);
    assert_non_null(g_last_parse_error);
    assert_string_equal(g_last_parse_error->message, "Unterminated group");

    // Test: "error has pos attribute"
    void* ast2 = strling_parse("abc)");
    assert_null(ast2);
    assert_non_null(g_last_parse_error);
    assert_int_equal(g_last_parse_error->pos, 3);

    // Test: "error string contains position"
    void* ast3 = strling_parse(")");
    assert_null(ast3);
    assert_non_null(g_last_parse_error);
    
    char* formatted = STRlingError_toString(g_last_parse_error);
    assert_non_null(formatted);
    assert_non_null(strstr(formatted, ">")); // Line markers
    assert_non_null(strstr(formatted, "^")); // Caret
    free(formatted);
}


// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test_teardown(test_rich_error_formatting, teardown_error),
        cmocka_unit_test_teardown(test_error_backward_compatibility, teardown_error),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup
}
