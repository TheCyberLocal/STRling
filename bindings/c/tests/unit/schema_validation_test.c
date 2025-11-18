/**
 * @file schema_validation_test.c
 * @brief Unit Tests for Input Schema Validation (10 Tests).
 *
 * PURPOSE:
 * Validates that the library strictly enforces the expected JSON Schema on inputs passed
 * to `strling_compile()`. This ensures robustness against malformed or invalid ASTs.
 * Matches the test count (10) of 'bindings/javascript/__tests__/unit/schema_validation.test.ts'.
 *
 * ADAPTATION NOTE:
 * The JS tests validate output artifacts against a JSON schema file.
 * The C tests validate that the C library (the consumer) correctly rejects inputs
 * that would fail that schema validation.
 *
 * COVERAGE:
 * - Category A: Valid Schemas (3 tests)
 * - Category B: Schema Violations (5 tests)
 * - Category C: Edge Cases (2 tests)
 */

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>
#include <stdio.h>

#include "strling.h"

// --- Test Infrastructure ----------------------------------------------------

static void verify_valid(const char *json_input) {
    strling_result_t result = strling_compile(json_input, NULL);
    
    if (result.error_code != STRling_OK) {
        printf("FAIL: Expected valid schema but got error: %s\nInput: %s\n", 
               result.error_message, json_input);
    }
    assert_int_equal(result.error_code, STRling_OK);
    assert_non_null(result.pcre2_pattern);
    
    strling_result_free(&result);
}

static void verify_invalid(const char *json_input, const char *expected_error_part) {
    strling_result_t result = strling_compile(json_input, NULL);
    
    if (result.error_code == STRling_OK) {
        printf("FAIL: Expected schema validation error but got success.\nInput: %s\nOutput: %s\n", 
               json_input, result.pcre2_pattern);
    }
    assert_int_not_equal(result.error_code, STRling_OK);
    assert_non_null(result.error_message);
    
    if (expected_error_part && strstr(result.error_message, expected_error_part) == NULL) {
        printf("FAIL: Error message mismatch.\n"
               "Expected part: '%s'\n"
               "Got message:   '%s'\n", 
               expected_error_part, result.error_message);
    }
    if (expected_error_part) {
        assert_non_null(strstr(result.error_message, expected_error_part));
    }
    
    strling_result_free(&result);
}

// --- Category A: Valid Schemas (3 Tests) ------------------------------------

static void test_valid_simple_literal(void **state) {
    (void)state;
    // Minimal valid AST
    verify_valid("{\"type\": \"Literal\", \"value\": \"a\"}");
}

static void test_valid_complex_structure(void **state) {
    (void)state;
    // Complex nested structure
    const char *input = 
        "{"
            "\"type\": \"Sequence\", \"parts\": ["
                "{\"type\": \"Anchor\", \"at\": \"Start\"},"
                "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Dot\"}}"
            "]"
        "}";
    verify_valid(input);
}

static void test_valid_with_flags(void **state) {
    (void)state;
    // Valid structure with top-level flags
    const char *input = 
        "{"
            "\"flags\": \"im\", "
            "\"pattern\": {\"type\": \"Literal\", \"value\": \"test\"}"
        "}";
    verify_valid(input);
}

// --- Category B: Schema Violations (5 Tests) --------------------------------

static void test_invalid_node_type(void **state) {
    (void)state;
    // Unknown "type" value (Enum violation)
    verify_invalid("{\"type\": \"UnknownNode\", \"value\": \"a\"}", "Unknown");
}

static void test_invalid_field_type(void **state) {
    (void)state;
    // "min" should be integer, provided as string (Type violation)
    const char *input = 
        "{"
            "\"type\": \"Quantifier\", "
            "\"min\": \"one\", " // Error
            "\"target\": {\"type\": \"Dot\"}"
        "}";
    verify_invalid(input, "type"); // Expecting type mismatch error
}

static void test_missing_required_field(void **state) {
    (void)state;
    // Literal node missing "value" (Required field violation)
    verify_invalid("{\"type\": \"Literal\"}", "value");
}

static void test_invalid_structure_array(void **state) {
    (void)state;
    // "parts" should be array, provided as object (Type violation)
    const char *input = 
        "{"
            "\"type\": \"Sequence\", "
            "\"parts\": {}" // Error
        "}";
    verify_invalid(input, "array");
}

static void test_invalid_root_structure(void **state) {
    (void)state;
    // Root must be an object, provided array
    verify_invalid("[]", "JSON"); // or schema root error
}

// --- Category C: Edge Cases (2 Tests) ---------------------------------------

static void test_edge_empty_pattern(void **state) {
    (void)state;
    // Empty pattern (valid, matches empty string)
    // Represented as empty Sequence
    verify_valid("{\"type\": \"Sequence\", \"parts\": []}");
}

static void test_edge_flags_only(void **state) {
    (void)state;
    // Pattern from source "%flags i" (valid, empty match with flags)
    // "pattern" field usually required or implied empty
    const char *input = 
        "{"
            "\"flags\": \"i\", "
            "\"pattern\": {\"type\": \"Sequence\", \"parts\": []}"
        "}";
    verify_valid(input);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_valid_simple_literal),
        cmocka_unit_test(test_valid_complex_structure),
        cmocka_unit_test(test_valid_with_flags),
        cmocka_unit_test(test_invalid_node_type),
        cmocka_unit_test(test_invalid_field_type),
        cmocka_unit_test(test_missing_required_field),
        cmocka_unit_test(test_invalid_structure_array),
        cmocka_unit_test(test_invalid_root_structure),
        cmocka_unit_test(test_edge_empty_pattern),
        cmocka_unit_test(test_edge_flags_only),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
