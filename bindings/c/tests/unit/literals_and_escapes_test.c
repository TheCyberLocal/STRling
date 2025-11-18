/**
 * @file literals_and_escapes_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests literal and escape sequence compilation from JSON AST to PCRE2 patterns.
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
 * Test Category A: Basic Literals
 */
static void test_basic_literals(void** state) {
    (void)state;
    
    /* Single character literal */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}",
        "a"
    );
    
    /* Multiple character literal */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"hello\"}}",
        "hello"
    );
    
    /* Literal with digits */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"abc123\"}}",
        "abc123"
    );
}

/**
 * Test Category B: Escaped Metacharacters
 */
static void test_escaped_metacharacters(void** state) {
    (void)state;
    
    /* Escape dot */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \".\"}}",
        "\\."
    );
    
    /* Escape star */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"*\"}}",
        "\\*"
    );
    
    /* Escape plus */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"+\"}}",
        "\\+"
    );
    
    /* Escape question mark */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"?\"}}",
        "\\?"
    );
    
    /* Escape caret */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"^\"}}",
        "\\^"
    );
    
    /* Escape dollar */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"$\"}}",
        "\\$"
    );
    
    /* Escape pipe */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"|\"}}",
        "\\|"
    );
    
    /* Escape parentheses */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"(\"}}",
        "\\("
    );
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \")\"}}",
        "\\)"
    );
    
    /* Escape brackets */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"[\"}}",
        "\\["
    );
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"]\"}}",
        "\\]"
    );
    
    /* Escape braces */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"{\"}}",
        "\\{"
    );
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"}\"}}",
        "\\}"
    );
    
    /* Escape backslash */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\\\\"}}",
        "\\\\"
    );
}

/**
 * Test Category C: Dot (any character)
 */
static void test_dot(void** state) {
    (void)state;
    
    /* Dot matches any character */
    test_compile(
        "{\"pattern\": {\"type\": \"Dot\"}}",
        "."
    );
}

/**
 * Test Category D: Sequences of Literals
 */
static void test_literal_sequences(void** state) {
    (void)state;
    
    /* Sequence of literals */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"hello\"},"
        "{\"type\": \"Literal\", \"value\": \" \"},"
        "{\"type\": \"Literal\", \"value\": \"world\"}"
        "]}}",
        "hello world"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        {"test_basic_literals", test_basic_literals, NULL, NULL, NULL},
        {"test_escaped_metacharacters", test_escaped_metacharacters, NULL, NULL, NULL},
        {"test_dot", test_dot, NULL, NULL, NULL},
        {"test_literal_sequences", test_literal_sequences, NULL, NULL, NULL},
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
