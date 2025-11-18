/**
 * @file char_classes_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests character class compilation from JSON AST to PCRE2 patterns.
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
 * Test Category A: Positive and Negative Classes
 */
static void test_positive_and_negative_classes(void** state) {
    (void)state;
    
    /* [a] - Single character class */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"}"
        "]}}",
        "[a]"
    );
    
    /* [abc] - Multiple character class */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Literal\", \"value\": \"b\"},"
        "{\"type\": \"Literal\", \"value\": \"c\"}"
        "]}}",
        "[abc]"
    );
    
    /* [^a] - Negated single character */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": true, \"members\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"}"
        "]}}",
        "[^a]"
    );
    
    /* [^abc] - Negated multiple characters */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": true, \"members\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Literal\", \"value\": \"b\"},"
        "{\"type\": \"Literal\", \"value\": \"c\"}"
        "]}}",
        "[^abc]"
    );
}

/**
 * Test Category B: Class Contents (Literals, Ranges, Shorthands)
 */
static void test_class_contents(void** state) {
    (void)state;
    
    /* [a-z] - Character range */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "]}}",
        "[a-z]"
    );
    
    /* [a-zA-Z0-9] - Multiple ranges */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"},"
        "{\"type\": \"Range\", \"from\": \"A\", \"to\": \"Z\"},"
        "{\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}"
        "]}}",
        "[a-zA-Z0-9]"
    );
    
    /* [\d] - Digit shorthand */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Meta\", \"value\": \"d\"}"
        "]}}",
        "[\\d]"
    );
    
    /* [\D] - Negated digit shorthand */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Meta\", \"value\": \"D\"}"
        "]}}",
        "[\\D]"
    );
    
    /* [\w\s] - Multiple shorthands */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Meta\", \"value\": \"w\"},"
        "{\"type\": \"Meta\", \"value\": \"s\"}"
        "]}}",
        "[\\w\\s]"
    );
    
    /* [a-f\d] - Range and shorthand */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Range\", \"from\": \"a\", \"to\": \"f\"},"
        "{\"type\": \"Meta\", \"value\": \"d\"}"
        "]}}",
        "[a-f\\d]"
    );
    
    /* [^\S] - Negated class with negated shorthand */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": true, \"members\": ["
        "{\"type\": \"Meta\", \"value\": \"S\"}"
        "]}}",
        "[^\\S]"
    );
}

/**
 * Test Category D: Special Character Handling (-, ], ^)
 */
static void test_special_characters(void** state) {
    (void)state;
    
    /* [-a] - Dash at start (literal) - doesn't need escaping in PCRE2 */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Literal\", \"value\": \"-\"},"
        "{\"type\": \"Literal\", \"value\": \"a\"}"
        "]}}",
        "[-a]"
    );
    
    /* [a-] - Dash at end (literal) - doesn't need escaping in PCRE2 */
    test_compile(
        "{\"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Literal\", \"value\": \"-\"}"
        "]}}",
        "[a-]"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_positive_and_negative_classes),
        cmocka_unit_test(test_class_contents),
        cmocka_unit_test(test_special_characters),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
