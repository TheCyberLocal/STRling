/**
 * @file groups_backrefs_lookarounds_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests groups, backreferences, and lookarounds from JSON AST to PCRE2 patterns.
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
    
    /* Check the pattern */
    if (strcmp(result->pattern, expected_pattern) != 0) {
        printf("Expected: %s\nGot: %s\n", expected_pattern, result->pattern);
    }
    assert_string_equal(result->pattern, expected_pattern);
    
    /* Cleanup */
    strling_result_free(result);
}

/**
 * Test Category A: Capturing Groups
 */
static void test_capturing_groups(void** state) {
    (void)state;
    
    /* Basic capturing group */
    test_compile(
        "{\"pattern\": {\"type\": \"Group\", "
        "\"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}",
        "(abc)"
    );
    
    /* Non-capturing group */
    test_compile(
        "{\"pattern\": {\"type\": \"Group\", \"capturing\": false, "
        "\"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}",
        "(?:abc)"
    );
    
    /* Named capturing group */
    test_compile(
        "{\"pattern\": {\"type\": \"Group\", \"name\": \"mygroup\", "
        "\"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}",
        "(?<mygroup>abc)"
    );
    
    /* Atomic group */
    test_compile(
        "{\"pattern\": {\"type\": \"Group\", \"atomic\": true, "
        "\"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}",
        "(?>abc)"
    );
}

/**
 * Test Category B: Backreferences
 */
static void test_backreferences(void** state) {
    (void)state;
    
    /* Numeric backreference */
    test_compile(
        "{\"pattern\": {\"type\": \"Backreference\", \"index\": 1}}",
        "\\1"
    );
    
    test_compile(
        "{\"pattern\": {\"type\": \"Backreference\", \"index\": 2}}",
        "\\2"
    );
    
    test_compile(
        "{\"pattern\": {\"type\": \"Backreference\", \"index\": 10}}",
        "\\10"
    );
    
    /* Named backreference */
    test_compile(
        "{\"pattern\": {\"type\": \"Backreference\", \"name\": \"foo\"}}",
        "\\k<foo>"
    );
}

/**
 * Test Category C: Lookarounds
 */
static void test_lookarounds(void** state) {
    (void)state;
    
    /* Positive lookahead */
    test_compile(
        "{\"pattern\": {\"type\": \"Lookahead\", "
        "\"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}",
        "(?=x)"
    );
    
    /* Negative lookahead */
    test_compile(
        "{\"pattern\": {\"type\": \"NegativeLookahead\", "
        "\"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}",
        "(?!x)"
    );
    
    /* Positive lookbehind */
    test_compile(
        "{\"pattern\": {\"type\": \"Lookbehind\", "
        "\"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}",
        "(?<=x)"
    );
    
    /* Negative lookbehind */
    test_compile(
        "{\"pattern\": {\"type\": \"NegativeLookbehind\", "
        "\"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}",
        "(?<!x)"
    );
}

/**
 * Test Category D: Integration tests
 */
static void test_integration(void** state) {
    (void)state;
    
    /* Group with backreference */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Group\", \"body\": {\"type\": \"Literal\", \"value\": \"a\"}},"
        "{\"type\": \"Backreference\", \"index\": 1}"
        "]}}",
        "(a)\\1"
    );
    
    /* Named group with named backreference */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Group\", \"name\": \"test\", \"body\": {\"type\": \"Literal\", \"value\": \"hello\"}},"
        "{\"type\": \"Backreference\", \"name\": \"test\"}"
        "]}}",
        "(?<test>hello)\\k<test>"
    );
    
    /* Nested groups */
    test_compile(
        "{\"pattern\": {\"type\": \"Group\", \"body\": "
        "{\"type\": \"Group\", \"capturing\": false, \"body\": "
        "{\"type\": \"Literal\", \"value\": \"x\"}"
        "}}}",
        "((?:x))"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_capturing_groups),
        cmocka_unit_test(test_backreferences),
        cmocka_unit_test(test_lookarounds),
        cmocka_unit_test(test_integration),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
