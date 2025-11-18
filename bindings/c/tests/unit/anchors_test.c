/**
 * @file anchors_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests anchor compilation from JSON AST to PCRE2 patterns.
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
    
    /* Check the pattern */
    assert_string_equal(result->pattern, expected_pattern);
    
    /* Cleanup */
    strling_result_free(result);
}

/* Helper to test error cases */
static void test_compile_error(const char* json, const char* expected_error_substring) {
    STRlingResult* result = strling_compile(json, NULL);
    
    /* Should fail */
    assert_non_null(result->error);
    assert_null(result->pattern);
    
    /* Check error message contains expected substring */
    assert_non_null(strstr(result->error->message, expected_error_substring));
    
    /* Cleanup */
    strling_result_free(result);
}

/**
 * Test Category A: Core Anchors (^, $, \b, \B)
 */
static void test_core_anchors(void** state) {
    (void)state;
    
    /* ^ - Start anchor */
    test_compile(
        "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"Start\"}}",
        "^"
    );
    
    /* $ - End anchor */
    test_compile(
        "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"End\"}}",
        "$"
    );
    
    /* \b - Word boundary */
    test_compile(
        "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"WordBoundary\"}}",
        "\\b"
    );
    
    /* \B - Non-word boundary */
    test_compile(
        "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"NonWordBoundary\"}}",
        "\\B"
    );
}

/**
 * Test Category B: Absolute Anchors (\A, \Z, \z)
 */
static void test_absolute_anchors(void** state) {
    (void)state;
    
    /* \A - Absolute start */
    test_compile(
        "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"AbsoluteStart\"}}",
        "\\A"
    );
    
    /* \Z - Absolute end */
    test_compile(
        "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"AbsoluteEnd\"}}",
        "\\Z"
    );
    
    /* \z - Absolute end only */
    test_compile(
        "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"AbsoluteEndOnly\"}}",
        "\\z"
    );
}

/**
 * Test Category D: Anchors in Sequences
 */
static void test_anchors_in_sequences(void** state) {
    (void)state;
    
    /* ^a - Start anchor followed by literal */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Anchor\", \"at\": \"Start\"},"
        "{\"type\": \"Literal\", \"value\": \"a\"}"
        "]}}",
        "^a"
    );
    
    /* a$ - Literal followed by end anchor */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Anchor\", \"at\": \"End\"}"
        "]}}",
        "a$"
    );
    
    /* a\b$ - Literal, word boundary, end anchor */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
        "{\"type\": \"Anchor\", \"at\": \"End\"}"
        "]}}",
        "a\\b$"
    );
    
    /* ^\ba\b$ - Complete word anchor pattern */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Anchor\", \"at\": \"Start\"},"
        "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
        "{\"type\": \"Anchor\", \"at\": \"End\"}"
        "]}}",
        "^\\ba\\b$"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_core_anchors),
        cmocka_unit_test(test_absolute_anchors),
        cmocka_unit_test(test_anchors_in_sequences),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
