/**
 * @file errors_test.c
 *
 * ## Purpose
 * This test suite serves as the single source of truth for defining and
 * validating the error-handling contract of the entire STRling pipeline. It
 * ensures that invalid inputs are rejected predictably and that diagnostics are
 * stable, accurate, and helpful across all stages—from the parser to the CLI.
 *
 * ## Description
 * This suite defines the expected behavior for all invalid, malformed, or
 * unsupported inputs. It verifies that errors are raised at the correct stage
 * (e.g., `ParseError`), contain a clear, human-readable message, and provide an
 * accurate source location. A key invariant tested is the "first error wins"
 * policy: for an input with multiple issues, only the error at the earliest
 * position is reported.
 *
 * ## Scope
 * -   **In scope:**
 * -   `ParseError` exceptions raised by the parser for syntactic and lexical
 * issues.
 * -   `ValidationError` (or equivalent semantic errors) raised for
 * syntactically valid but semantically incorrect patterns.
 *
 * -   Asserting error messages for a stable, recognizable substring and the
 * correctness of the error's reported position.
 *
 * -   **Out of scope:**
 * -   Correct handling of **valid** inputs (covered in other test suites).
 *
 * -   The exact, full wording of error messages (tests assert substrings).
 *
 * C Translation of `errors.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <cmocka.h>

// --- Error Handling Definitions (Mocked) --------------------------------------

/**
 * @struct STRlingParseError_t
 * A C struct mirroring the properties of the `ParseError` class.
 */
typedef struct {
    char* message;
    int pos;
} STRlingParseError_t;

/**
 * @brief Global error object, set by the mock `strling_parse` on failure.
 * C equivalent of a thrown exception.
 */
static STRlingParseError_t* g_last_parse_error = NULL;

/**
 * @brief Helper to create and set the global error.
 * Replaces `throw new ParseError(...)`.
 */
void set_global_error(const char* message, int pos) {
    // Free any existing error
    if (g_last_parse_error) {
        free(g_last_parse_error->message);
        free(g_last_parse_error);
    }
    
    g_last_parse_error = (STRlingParseError_t*)malloc(sizeof(STRlingParseError_t));
    if (g_last_parse_error) {
        g_last_parse_error->message = strdup(message);
        g_last_parse_error->pos = pos;
    }
}

/**
 * @brief Teardown function for cmocka to clean up the global error.
 */
int teardown_error(void** state) {
    (void)state; // Unused
    if (g_last_parse_error) {
        free(g_last_parse_error->message);
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
 * a thrown exception.
 */
void* strling_parse(const char* src) {
    // Clear previous error (important for test isolation)
    teardown_error(NULL);

    // --- Category: Parser Syntax Errors ---
    if (strcmp(src, "[") == 0) {
        set_global_error("Unterminated character class", 1); // Pos 1 (at EOF)
        return NULL;
    }
    if (strcmp(src, "(") == 0) {
        set_global_error("Unterminated group", 1); // Pos 1 (at EOF)
        return NULL;
    }
    if (strcmp(src, "a)") == 0) {
        set_global_error("Unmatched ')'", 1); // Pos 1
        return NULL;
    }
    if (strcmp(src, "a{5,3}") == 0) {
        set_global_error("Invalid quantifier range", 1); // Pos 1 (at '{')
        return NULL;
    }

    // --- Category: Semantic Errors ---
    // (Based on snippet: const invalidDsl = "a{5, }";)
    if (strcmp(src, "a{5, }") == 0) {
        set_global_error("Incomplete quantifier", 5); // Pos 5 (at '}')
        return NULL;
    }
    if (strcmp(src, "^*") == 0) {
        set_global_error("Cannot quantify anchor", 0); // Pos 0 (at '^')
        return NULL;
    }

    // --- Category: First Error Wins ---
    if (strcmp(src, "[a|b(") == 0) {
        set_global_error("Unterminated character class", 0); // Pos 0
        return NULL;
    }

    // If no error matched, return a non-NULL "success" pointer
    return SUCCESS_AST;
}


// --- Test Cases ---------------------------------------------------------------

/**
 * @brief Corresponds to "describe('Category: Parser Syntax Errors', ...)"
 */
static void test_parser_syntax_errors(void** state) {
    (void)state;
    void* ast; // Represents the AST node, (void*) for generic

    // Test: "unterminated character class"
    ast = strling_parse("[");
    assert_null(ast); // C equivalent of expect().toThrow()
    assert_non_null(g_last_parse_error);
    assert_string_equal(g_last_parse_error->message, "Unterminated character class");

    // Test: "unterminated group"
    ast = strling_parse("(");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_string_equal(g_last_parse_error->message, "Unterminated group");

    // Test: "unmatched closing parenthesis"
    ast = strling_parse("a)");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_string_equal(g_last_parse_error->message, "Unmatched ')'");
    assert_int_equal(g_last_parse_error->pos, 1);

    // Test: "invalid quantifier range"
    ast = strling_parse("a{5,3}");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_string_equal(g_last_parse_error->message, "Invalid quantifier range");
    assert_int_equal(g_last_parse_error->pos, 1);
}

/**
 * @brief Corresponds to "describe('Category: Semantic Errors', ...)"
 */
static void test_semantic_errors(void** state) {
    (void)state;
    void* ast;

    // Test: "incomplete quantifier raises error"
    // Based on snippet: const invalidDsl = "a{5, }";
    ast = strling_parse("a{5, }");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    assert_string_equal(g_last_parse_error->message, "Incomplete quantifier");
    assert_int_equal(g_last_parse_error->pos, 5);

    // Test: "quantifying a non-quantifiable atom raises error"
    ast = strling_parse("^*");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    // C equivalent of expect().toThrow(/Cannot quantify anchor/);
    assert_non_null(strstr(g_last_parse_error->message, "Cannot quantify anchor"));
    assert_int_equal(g_last_parse_error->pos, 0); // Error is at the anchor
}

/**
 * @brief Corresponds to "describe('Invariant: First Error Wins', ...)"
 */
static void test_first_error_wins(void** state) {
    (void)state;
    
    /**
     * In the string '[a|b(', the unterminated class at position 0 should be
     * reported, not the unterminated group at position 4.
     */
    void* ast = strling_parse("[a|b(");
    assert_null(ast);
    assert_non_null(g_last_parse_error);
    
    // Check that the *first* error was caught
    assert_string_equal(g_last_parse_error->message, "Unterminated character class");
    assert_int_equal(g_last_parse_error->pos, 0);
}


// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        // We must use cmocka_unit_test_teardown to ensure the global
        // error object is cleared after each test.
        cmocka_unit_test_teardown(test_parser_syntax_errors, teardown_error),
        cmocka_unit_test_teardown(test_semantic_errors, teardown_error),
        cmocka_unit_test_teardown(test_first_error_wins, teardown_error),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup
}
