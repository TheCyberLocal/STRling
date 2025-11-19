/**
 * @file error_formatting_test.c
 * @brief Unit Tests for Error Reporting and Formatting (11 Tests).
 *
 * PURPOSE:
 * Validates that the library produces descriptive error messages and correct
 * error codes when encountering invalid input.
 * Matches the test count (11) of 'bindings/javascript/__tests__/unit/error_formatting.test.ts'.
 *
 * ADAPTATION NOTE:
 * The JS tests verify DSL syntax error hints (e.g., "Unterminated group").
 * Since the C library accepts JSON ASTs, these tests have been adapted to verify
 * JSON Parsing Errors and AST Validation Errors (e.g., "Missing required field").
 *
 * COVERAGE:
 * - Base Error Structure (Tests 1-5)
 * - Validation "Hints" / Details (Tests 6-11)
 */

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>
#include <stdio.h>

#include "strling.h"

// --- Helper Functions -------------------------------------------------------

/**
 * @brief Asserts that compilation fails and the error message contains a substring.
 */
static void verify_error_contains(const char *json_input, const char *expected_substring) {
    strling_result_t result = strling_compile_compat(json_input, NULL);

    // 1. Assert Failure
    if (result.error_code == STRling_OK) {
        printf("FAIL: Expected error but got success.\nInput: %s\nOutput: %s\n", 
               json_input, result.pcre2_pattern);
    }
    assert_int_not_equal(result.error_code, STRling_OK);
    
    // 2. Assert Error Message Existence
    assert_non_null(result.error_message);

    // 3. Assert Substring Match
    // We use strstr to check if the expected detail is present in the error message.
    if (strstr(result.error_message, expected_substring) == NULL) {
        printf("FAIL: Error message did not contain expected substring.\n"
               "Expected: '%s'\n"
               "Got:      '%s'\n", 
               expected_substring, result.error_message);
    }
    assert_non_null(strstr(result.error_message, expected_substring));

    // 4. Cleanup
    strling_result_free_compat(&result);
}

// --- Group 1: STRlingParseError Structure (Adapted) -------------------------
// Maps to JS tests verifying the error object's properties and formatting.

/**
 * @brief Test 1: Simple error without text (Adapted to Null Input).
 * Verifies basic error code generation for invalid pointers.
 */
static void test_simple_error_structure(void **state) {
    (void)state;
    // Passing NULL as input should immediately trigger a generic error.
    strling_result_t result = strling_compile_compat(NULL, NULL);
    
    assert_int_not_equal(result.error_code, STRling_OK);
    assert_non_null(result.error_message);
    // Expect a generic "Invalid input" or "NULL" message
    // We check for "Invalid" or empty input related message
    // Note: Exact string depends on implementation, checking for non-empty.
    assert_true(strlen(result.error_message) > 0);

    strling_result_free_compat(&result);
}

/**
 * @brief Test 2: Error with text and context (Adapted to JSON Syntax Error).
 * Verifies the parser reports malformed JSON.
 */
static void test_error_with_context(void **state) {
    (void)state;
    // Malformed JSON (missing closing brace)
    const char *input = "{\"type\": \"Literal\", \"value\": \"a\""; 
    verify_error_contains(input, "JSON"); // Should mention JSON parsing error
}

/**
 * @brief Test 3: Error position indicator (Adapted to JSON Position).
 * Verifies the error message implies a location (syntax error).
 */
static void test_error_position(void **state) {
    (void)state;
    // Invalid char after valid JSON
    const char *input = "{\"type\":\"Literal\",\"value\":\"a\"} garbage";
    // Parser should complain about extra data or invalid JSON
    verify_error_contains(input, "garbage"); // Or "Unexpected"
}

/**
 * @brief Test 4: Multiline error (Adapted to Multiline JSON).
 * Verifies error reporting works with newlines.
 */
static void test_multiline_error(void **state) {
    (void)state;
    const char *input = 
        "{\n"
        "  \"type\": \"Literal\",\n"
        "  \"value\": \n" // Missing value
        "}";
    verify_error_contains(input, "JSON"); // Should catch the syntax error
}

/**
 * @brief Test 5: Formatted String (Adapted to Output Consistency).
 * Verifies that repeated calls produce consistent error strings.
 */
static void test_error_string_consistency(void **state) {
    (void)state;
    const char *input = "{invalid}";
    
    strling_result_t res1 = strling_compile_compat(input, NULL);
    strling_result_t res2 = strling_compile_compat(input, NULL);
    
    assert_string_equal(res1.error_message, res2.error_message);
    
    strling_result_free_compat(&res1);
    strling_result_free_compat(&res2);
}

// --- Group 2: HintEngine (Adapted to Validation Details) --------------------
// Maps to JS tests verifying specific guidance for "Unterminated group", etc.

/**
 * @brief Test 6: Unterminated group (Adapted to Missing 'expression').
 * JS: "Unterminated group" hint.
 * C: "Group node missing required 'expression' field".
 */
static void test_hint_missing_group_expr(void **state) {
    (void)state;
    // Valid JSON, Invalid AST (Group must have expression)
    const char *input = "{\"type\": \"Group\", \"capturing\": true}";
    verify_error_contains(input, "expression"); // Should complain about missing field
}

/**
 * @brief Test 7: Unterminated char class (Adapted to Missing 'members').
 * JS: "Unterminated character class" hint.
 * C: "CharacterClass node missing required 'members' field".
 */
static void test_hint_missing_class_members(void **state) {
    (void)state;
    const char *input = "{\"type\": \"CharacterClass\", \"negated\": false}";
    verify_error_contains(input, "members");
}

/**
 * @brief Test 8: Unexpected token (Adapted to Unknown Node Type).
 * JS: "Unexpected token )" hint.
 * C: "Unknown node type 'UnknownType'".
 */
static void test_hint_unknown_node_type(void **state) {
    (void)state;
    const char *input = "{\"type\": \"ThisTypeDoesNotExist\"}";
    verify_error_contains(input, "Unknown");
}

/**
 * @brief Test 9: Cannot quantify anchor (Adapted to Semantic Validation).
 * JS: "Cannot quantify anchor" hint.
 * C: "Quantifier target cannot be an Anchor".
 */
static void test_hint_quantified_anchor(void **state) {
    (void)state;
    // Semantic violation: Quantifying an Anchor
    const char *input = 
        "{"
            "\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true,"
            "\"target\": {\"type\": \"Anchor\", \"at\": \"Start\"}"
        "}";
    
    // The validation logic should catch this
    verify_error_contains(input, "Anchor"); 
}

/**
 * @brief Test 10: Inline modifiers (Adapted to Flags Validation).
 * JS: "Inline modifiers not supported" hint.
 * C: "Invalid flags format" or similar structural check.
 */
static void test_hint_invalid_literal_structure(void **state) {
    (void)state;
    // Adapted: Literal missing "value"
    const char *input = "{\"type\": \"Literal\"}";
    verify_error_contains(input, "value");
}

/**
 * @brief Test 11: Unknown error (Adapted to Generic Schema Violation).
 * JS: "No hint for unknown error".
 * C: "Schema validation error" for deeply malformed input.
 */
static void test_hint_generic_schema_error(void **state) {
    (void)state;
    // Valid JSON, but wrong types (e.g., 'parts' is a string, not array)
    const char *input = 
        "{"
            "\"type\": \"Sequence\","
            "\"parts\": \"This should be an array\""
        "}";
    
    // Should report type mismatch or schema error
    verify_error_contains(input, "parts");
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_simple_error_structure),
        cmocka_unit_test(test_error_with_context),
        cmocka_unit_test(test_error_position),
        cmocka_unit_test(test_multiline_error),
        cmocka_unit_test(test_error_string_consistency),
        cmocka_unit_test(test_hint_missing_group_expr),
        cmocka_unit_test(test_hint_missing_class_members),
        cmocka_unit_test(test_hint_unknown_node_type),
        cmocka_unit_test(test_hint_quantified_anchor),
        cmocka_unit_test(test_hint_invalid_literal_structure),
        cmocka_unit_test(test_hint_generic_schema_error),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}