/**
 * @file e2e_combinatorial_test.c
 *
 * Refactored to test the real STRling C library API.
 * End-to-end tests with various feature combinations.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cmocka.h>
#include "strling.h"

/* Helper to run a test case */
static void test_compile(const char* json, const char* expected_pattern) {
    STRlingResult* result = strling_compile(json, NULL);
    
    /* Should succeed */
    if (result->error) {
        printf("Unexpected error: %s\n", result->error->message);
    }
    assert_null(result->error);
    assert_non_null(result->pattern);
    
    if (strcmp(result->pattern, expected_pattern) != 0) {
        printf("Expected: %s\nGot: %s\n", expected_pattern, result->pattern);
    }
    assert_string_equal(result->pattern, expected_pattern);
    
    /* Cleanup */
    strling_result_free(result);
}

/**
 * Test complex combinations
 */
static void test_complex_patterns(void** state) {
    (void)state;
    
    /* Quantified alternation */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, "
        "\"target\": {\"type\": \"Alternation\", \"alternatives\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Literal\", \"value\": \"b\"}"
        "]}}}",
        "(a|b)*"
    );
    
    /* Group with quantifier and alternation */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Anchor\", \"at\": \"Start\"},"
        "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, "
        "\"target\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "]}},"
        "{\"type\": \"Anchor\", \"at\": \"End\"}"
        "]}}",
        "^[a-z]+$"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_complex_patterns),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
