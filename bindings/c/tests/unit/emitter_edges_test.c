/**
 * @file emitter_edges_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests edge cases in PCRE2 emitter.
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
 * Test edge cases
 */
static void test_edge_cases(void** state) {
    (void)state;
    
    /* Empty sequence */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": []}}",
        ""
    );
    
    /* Single element sequence */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"}"
        "]}}",
        "a"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_edge_cases),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
