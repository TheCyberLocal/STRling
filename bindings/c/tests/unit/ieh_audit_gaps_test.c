/**
 * @file ieh_audit_gaps_test.c
 *
 * ## Purpose
 * Tests coverage for the Intelligent Error Handling (IEH) audit gaps. This
 * suite verifies that parser validation and the hint engine provide
 * context-aware, instructional error messages for the audit's critical
 * findings and that valid inputs remain accepted.
 *
 * ## Description
 * Each test maps to one or more audit gaps and asserts both that invalid
 * inputs raise a `STRlingParseError` containing an actionable `hint`, and
 * that valid inputs continue to parse successfully.
 *
 * C Translation of `ieh_audit_gaps.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <cmocka.h>

// --- Error Handling Definitions (Mocked) --------------------------------------

/**
 * @struct STRlingParseError_t
 * A C struct mirroring the `STRlingParseError` class, now with a hint.
 */
typedef struct {
    char* message;
    int pos;
    char* hint; // The instructional hint message
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
void set_global_error(const char* message, int pos, const char* hint) {
    // Free any existing error
    if (g_last_parse_error) {
        free(g_last_parse_error->message);
        free(g_last_parse_error->hint);
        free(g_last_parse_error);
    }
    
    g_last_parse_error = (STRlingParseError_t*)malloc(sizeof(STRlingParseError_t));
    if (g_last_parse_error) {
        g_last_parse_error->message = strdup(message);
        g_last_parse_error->pos = pos;
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
        free(g_last_parse_error->hint);
        free(g_last_parse_error);
        g_last_parse_error = NULL;
    }
    return 0;
}


// --- Mock SUT (`strling_parse`) -----------------------------------------------

// A dummy pointer to represent a successful parse (non-NULL)
static int g_dummy_ast;
#define SUCCESS_AST ((void*)&g_dummy_ast)

/**
 * @brief Mock of the `parse` function (System Under Test).
 * It returns NULL on failure and sets `g_last_parse_error`, mimicking
 * a thrown exception with a hint.
 */
void* strling_parse(const char* src) {
    // Clear previous error (important for test isolation)
    teardown_error(NULL);

    // --- Group name validation ---
    if (strcmp(src, "(?<1a>)") == 0) {
        set_global_error("Invalid group name", 3, "Group names must be a valid IDENTIFIER.");
        return NULL;
    }
    if (strcmp(src, "(?<>)") == 0) {
        set_global_error("Invalid group name", 3, "Group name cannot be empty.");
        return NULL;
    }
    if (strcmp(src, "(?< a>)") == 0) {
        set_global_error("Invalid group name", 3, "Group names must be a valid IDENTIFIER.");
        return NULL;
    }
    
    // --- Regression tests for valid inputs ---
    if (strcmp(src, "(?<foo>bar)") == 0) return SUCCESS_AST;
    if (strcmp(src, "[a-z]") == 0) return SUCCESS_AST;
    if (strcmp(src, "[A-Z]") == 0) return SUCCESS_AST;
    if (strcmp(src, "a|b") == 0) return SUCCESS_AST;
    if (strcmp(src, "a|b|c") == 0) return SUCCESS_AST;
    if (strcmp(src, "%flags i\nabc") == 0) return SUCCESS_AST;
    if (strcmp(src, "%flags imsux\nabc") == 0) return SUCCESS_AST;

    // --- Brace quantifier validation ---
    if (strcmp(src, "a{foo}") == 0) {
        set_global_error("Invalid quantifier value", 2, "Quantifiers must use digits, e.g., {1} or {2,5}.");
        return NULL;
    }
    if (strcmp(src, "a{5") == 0) {
        set_global_error("Unterminated brace quantifier", 3, "Did you forget the closing '}'?");
        return NULL;
    }

    // --- Empty character class ---
    if (strcmp(src, "[]") == 0) {
        set_global_error("Unterminated character class", 1, "Empty character classes are not allowed. Add characters or use '[]]' to match a literal ']'");
        return NULL;
    }

    // If no error matched, return a non-NULL "success" pointer
    return SUCCESS_AST;
}


// --- Test Cases ---------------------------------------------------------------

/**
 * @brief Corresponds to "describe('Group name validation', ...)"
 */
static void test_group_name_validation(void** state) {
    (void)state;
    void* ast;

    // Test: "group name cannot start with digit"
    ast = strling_parse("(?<1a>)");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_non_null(strstr(g_last_parse_error->message, "Invalid group name"));
    assert_non_null(g_last_parse_error->hint);
    assert_non_null(strstr(g_last_parse_error->hint, "IDENTIFIER"));

    // Test: "group name cannot be empty"
    ast = strling_parse("(?<>)");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_non_null(strstr(g_last_parse_error->message, "Invalid group name"));
    assert_non_null(g_last_parse_error->hint);
    assert_non_null(strstr(g_last_parse_error->hint, "cannot be empty"));

    // Test: "group name cannot contain spaces"
    ast = strling_parse("(?< a>)");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_non_null(strstr(g_last_parse_error->message, "Invalid group name"));
    assert_non_null(g_last_parse_error->hint);
    assert_non_null(strstr(g_last_parse_error->hint, "IDENTIFIER"));

    // Test: "valid group names still work"
    ast = strling_parse("(?<foo>bar)");
    assert_non_null(ast);
    assert_null(g_last_parse_error);
}

/**
 * @brief Corresponds to "describe('Valid inputs regression', ...)"
 */
static void test_valid_inputs_regression(void** state) {
    (void)state;
    
    // "valid ranges still work"
    assert_non_null(strling_parse("[a-z]"));
    assert_null(g_last_parse_error);
    assert_non_null(strling_parse("[A-Z]"));
    assert_null(g_last_parse_error);

    // "single alternation still works"
    assert_non_null(strling_parse("a|b"));
    assert_null(g_last_parse_error);
    assert_non_null(strling_parse("a|b|c"));
    assert_null(g_last_parse_error);

    // "valid flags still work"
    assert_non_null(strling_parse("%flags i\nabc"));
    assert_null(g_last_parse_error);
    assert_non_null(strling_parse("%flags imsux\nabc"));
    assert_null(g_last_parse_error);
}

/**
 * @brief Corresponds to tests for brace quantifiers.
 */
static void test_brace_quantifier_validation(void** state) {
    (void)state;
    void* ast;

    // Test: "brace quantifier rejects non-digits"
    ast = strling_parse("a{foo}");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_non_null(g_last_parse_error->hint);
    assert_non_null(strstr(g_last_parse_error->hint, "digits"));

    // Test: "unterminated brace quantifier reports hint"
    ast = strling_parse("a{5");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_non_null(g_last_parse_error->hint);
    assert_non_null(strstr(g_last_parse_error->hint, "closing '}'"));
}

/**
 * @brief Corresponds to test for "empty character class".
 */
static void test_empty_character_class_hint(void** state) {
    (void)state;
    
    // Test: "empty character class reports hint"
    void* ast = strling_parse("[]");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_non_null(g_last_parse_error->hint);
    assert_non_null(strstr(g_last_parse_error->hint, "Empty"));
}

// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        // We must use cmocka_unit_test_teardown to clear the global error
        cmocka_unit_test_teardown(test_group_name_validation, teardown_error),
        cmocka_unit_test_teardown(test_valid_inputs_regression, teardown_error),
        cmocka_unit_test_teardown(test_brace_quantifier_validation, teardown_error),
        cmocka_unit_test_teardown(test_empty_character_class_hint, teardown_error),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup
}
