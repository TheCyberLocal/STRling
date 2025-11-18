/**
 * @file ieh_audit_gaps_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests various features to ensure audit coverage.
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
    assert_null(result->error);
    assert_non_null(result->pattern);
    assert_string_equal(result->pattern, expected_pattern);
    
    /* Cleanup */
    strling_result_free(result);
}

/**
 * Test various feature combinations
 */
static void test_feature_coverage(void** state) {
    (void)state;
    
    /* Alternation */
    test_compile(
        "{\"pattern\": {\"type\": \"Alternation\", \"alternatives\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Literal\", \"value\": \"b\"}"
        "]}}",
        "(a|b)"
    );
    
    /* Meta characters */
    test_compile(
        "{\"pattern\": {\"type\": \"Meta\", \"value\": \"d\"}}",
        "\\d"
    );
    
    test_compile(
        "{\"pattern\": {\"type\": \"Meta\", \"value\": \"w\"}}",
        "\\w"
    );
    
    test_compile(
        "{\"pattern\": {\"type\": \"Meta\", \"value\": \"s\"}}",
        "\\s"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_feature_coverage),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
