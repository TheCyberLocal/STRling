/**
 * @file error_formatting_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests error message formatting.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cmocka.h>
#include "strling.h"

/**
 * Test that errors have required fields
 */
static void test_error_structure(void** state) {
    (void)state;
    
    /* Invalid JSON should produce error */
    STRlingResult* result = strling_compile("{invalid}", NULL);
    
    /* Should have error */
    assert_non_null(result->error);
    assert_null(result->pattern);
    
    /* Error should have message */
    assert_non_null(result->error->message);
    
    /* Cleanup */
    strling_result_free(result);
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_error_structure),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
