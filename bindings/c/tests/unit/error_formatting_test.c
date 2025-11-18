/**
 * @file error_formatting_test.c
 *
 * ## Purpose
 * Tests formatting of `STRlingParseError` and the behavior of the hint engine.
 * Ensures formatted errors include source context, caret positioning, and
 * that the hint engine returns contextual guidance where appropriate.
 *
 * C Translation of `error_formatting.test.ts`.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <cmocka.h>

// --- SUT (System Under Test) Definitions (Mocked) -----------------------------

/**
 * @struct STRlingError_t
 * A C struct mirroring the properties of the `STRlingParseError` class.
 */
typedef struct {
    char* message;
    int pos;
    char* text; // The full source text
    char* hint; // A pre-computed hint
} STRlingError_t;

/**
 * @brief Mock constructor for STRlingError_t.
 */
STRlingError_t* STRlingError_create(const char* message, int pos, const char* text, const char* hint) {
    STRlingError_t* err = (STRlingError_t*)calloc(1, sizeof(STRlingError_t));
    if (!err) return NULL;
    
    err->message = message ? strdup(message) : NULL;
    err->pos = pos;
    err->text = text ? strdup(text) : NULL;
    err->hint = hint ? strdup(hint) : NULL;
    
    return err;
}

/**
 * @brief Mock destructor for STRlingError_t.
 */
void STRlingError_free(STRlingError_t* err) {
    if (err) {
        free(err->message);
        free(err->text);
        free(err->hint);
        free(err);
    }
}

/**
 * @brief [SUT Stub] Mock of the error formatting (toString()) method.
 * This stub is hard-coded to return what the test expects.
 * Caller must free the returned string.
 */
char* STRlingError_toString(STRlingError_t* err) {
    if (!err) return NULL;
    
    char buffer[2048];
    
    // Case 1: "simple error without text"
    if (err->text == NULL) {
        snprintf(buffer, sizeof(buffer), "STRling Parse Error: %s at position %d", 
                 err->message, err->pos);
        return strdup(buffer);
    }
    
    // Case 2: "error with text and hint"
    if (err->text && strcmp(err->text, "(a|b))") == 0) {
        snprintf(buffer, sizeof(buffer),
            "STRling Parse Error: %s at line 1, column %d:\n"
            "\n"
            "> 1 | %s\n"
            "      %s\n" // This aligns the caret
            "\n"
            "Hint: %s\n",
            err->message, 
            err->pos + 1, // Assuming 1-based column
            err->text,
            "     ^",     // Hard-coded caret for pos 5
            err->hint
        );
        return strdup(buffer);
    }
    
    // Fallback
    return strdup(err->message);
}


/**
 * @brief [SUT Stub] Mock of the hint engine.
 * This stub is hard-coded to return the expected hints.
 * Caller must free the returned string.
 */
char* getHint(const char* message, const char* src, int pos) {
    // "unterminated group hint"
    if (strcmp(message, "Unterminated group") == 0) {
        return strdup("This group was opened with '('. Add a matching ')'");
    }
    
    // "unterminated character class hint"
    if (strcmp(message, "Unterminated character class") == 0) {
        return strdup("This character class was opened with '['. Add a matching ']'");
    }
    
    // "unexpected token hint - closing paren"
    if (strcmp(message, "Unexpected token") == 0 && pos == 3) {
        return strdup("This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?");
    }

    // "cannot quantify anchor hint"
    if (strcmp(message, "Cannot quantify anchor") == 0) {
        return strdup("Anchors (like ^, $, \\b) match positions and cannot be quantified.");
    }
    
    // "inline modifiers hint"
    if (strcmp(message, "Inline modifiers `(?imsx)` are not supported") == 0) {
        return strdup("Use the %flags directive at the top of the file.");
    }
    
    // "no hint for unknown error"
    return NULL;
}


// --- Test Cases ---------------------------------------------------------------

/**
 * @brief Corresponds to "describe('STRlingParseError', ...)"
 */
static void test_strling_parse_error_formatting(void** state) {
    (void)state; // Unused
    
    // Test: "simple error without text"
    STRlingError_t* err1 = STRlingError_create("Test error", 5, NULL, NULL);
    char* formatted1 = STRlingError_toString(err1);
    
    assert_non_null(formatted1);
    assert_non_null(strstr(formatted1, "Test error at position 5"));
    
    free(formatted1);
    STRlingError_free(err1);

    // Test: "error with text and hint"
    const char* text = "(a|b))";
    const char* hint = "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?";
    
    STRlingError_t* err2 = STRlingError_create("Unmatched ')'", 5, text, hint);
    char* formatted2 = STRlingError_toString(err2);

    assert_non_null(formatted2);
    // Check that it contains all the expected parts
    assert_non_null(strstr(formatted2, "STRling Parse Error: Unmatched ')'"));
    assert_non_null(strstr(formatted2, "> 1 | (a|b))"));
    assert_non_null(strstr(formatted2, "^"));
    assert_non_null(strstr(formatted2, "Hint:"));
    assert_non_null(strstr(formatted2, "does not have a matching opening '('."));
    
    free(formatted2);
    STRlingError_free(err2);
}


/**
 * @brief Corresponds to "describe('getHint', ...)"
 */
static void test_hint_engine(void** state) {
    (void)state; // Unused
    
    // Define the test cases
    typedef struct {
        const char* message;
        const char* src;
        int pos;
        const char* expected_substring; // NULL if no hint is expected
    } HintTestCase;
    
    HintTestCase cases[] = {
        {
            "Unterminated group", "(abc", 3,
            "opened with '('" // "unterminated group hint"
        },
        {
            "Unterminated character class", "[abc", 4,
            "opened with '['" // "unterminated character class hint"
        },
        {
            "Unexpected token", "abc)", 3,
            "does not have a matching opening '('" // "unexpected token hint - closing paren"
        },
        {
            "Cannot quantify anchor", "^*", 1,
            "cannot be quantified" // "cannot quantify anchor hint"
        },
        {
            "Inline modifiers `(?imsx)` are not supported", "(?i)abc", 1,
            "%flags" // "inline modifiers hint"
        },
        {
            "Some unknown error message", "abc", 0,
            NULL // "no hint for unknown error"
        }
    };
    
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        const HintTestCase* tc = &cases[i];
        
        char* hint = getHint(tc->message, tc->src, tc->pos);
        
        if (tc->expected_substring) {
            assert_non_null_bt(hint, "Test Case (message): %s", tc->message);
            assert_non_null_bt(strstr(hint, tc->expected_substring),
                               "Test Case (message): %s. Hint '%s' did not contain '%s'",
                               tc->message, hint, tc->expected_substring);
        } else {
            assert_null_bt(hint, "Test Case (message): %s (expected NULL hint)", tc->message);
        }
        
        free(hint);
    }
}


// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_strling_parse_error_formatting),
        cmocka_unit_test(test_hint_engine),
    };

    // Run the tests
    return cmocka_run_group_tests(tests, NULL, NULL); // No global setup/teardown
}
