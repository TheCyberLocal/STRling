/**
 * @file pcre2_emitter_test.c
 *
 * Refactored to test the real STRling C library API.
 * End-to-end tests for PCRE2 pattern generation.
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
 * Test PCRE2 specific features
 */
static void test_pcre2_features(void** state) {
    (void)state;
    
    /* Email pattern */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, "
        "\"target\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "]}},"
        "{\"type\": \"Literal\", \"value\": \"@\"},"
        "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, "
        "\"target\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "]}}"
        "]}}",
        "[a-z]+@[a-z]+"
    );
    
    /* URL pattern with named groups */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Group\", \"name\": \"scheme\", \"body\": "
        "{\"type\": \"Literal\", \"value\": \"http\"}},"
        "{\"type\": \"Literal\", \"value\": \"://\"},"
        "{\"type\": \"Group\", \"name\": \"host\", \"body\": "
        "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, "
        "\"target\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "]}}}"
        "]}}",
        "(?<scheme>http)://(?<host>[a-z]+)"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_pcre2_features),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
