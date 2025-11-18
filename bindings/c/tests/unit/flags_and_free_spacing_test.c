/**
 * @file flags_and_free_spacing_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests compilation with various flags.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cmocka.h>
#include "strling.h"

/* Helper to run a test case */
static void test_compile(const char* json, const STRlingFlags* flags, const char* expected_pattern) {
    STRlingResult* result = strling_compile(json, flags);
    
    /* Should succeed */
    if (result->error) {
        printf("Unexpected error: %s\n", result->error->message);
    }
    assert_null(result->error);
    assert_non_null(result->pattern);
    assert_string_equal(result->pattern, expected_pattern);
    
    /* Cleanup */
    strling_result_free(result);
}

/**
 * Test compilation with default flags
 */
static void test_default_flags(void** state) {
    (void)state;
    
    /* Compile with NULL flags (defaults) */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"hello\"}}",
        NULL,
        "hello"
    );
}

/**
 * Test with specific flags
 */
static void test_with_flags(void** state) {
    (void)state;
    
    /* Create flags */
    STRlingFlags* flags = strling_flags_create();
    flags->ignoreCase = true;
    
    /* Test compilation - flags should emit prefix */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"hello\"}}",
        flags,
        "(?i)hello"  /* (?i) prefix for case-insensitive */
    );
    
    strling_flags_free(flags);
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_default_flags),
        cmocka_unit_test(test_with_flags),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
