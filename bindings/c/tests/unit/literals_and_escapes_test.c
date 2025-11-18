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
    
    /* Sequence of literals - spaces are escaped */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"hello\"},"
        "{\"type\": \"Literal\", \"value\": \" \"},"
        "{\"type\": \"Literal\", \"value\": \"world\"}"
        "]}}",
        "hello\\ world"
    );
}

/**
 * Test Category E: Control Character Escapes
 */
static void test_control_escapes(void** state) {
    (void)state;
    
    /* Newline */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\n\"}}",
        "\\n"
    );
    
    /* Carriage return */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\r\"}}",
        "\\r"
    );
    
    /* Tab */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\t\"}}",
        "\\t"
    );
    
    /* Form feed */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\f\"}}",
        "\\f"
    );
    
    /* Vertical tab */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u000b\"}}",
        "\\v"
    );
}

/**
 * Test Category F: Hexadecimal Escapes
 */
static void test_hex_escapes(void** state) {
    (void)state;
    
    /* Hex escape - letter A (0x41) */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"A\"}}",
        "A"
    );
    
    /* Hex escape - SOH (0x01) */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u0001\"}}",
        "\\x01"
    );
    
    /* Hex escape - space (0x20) */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \" \"}}",
        "\\ "
    );
    
    /* Hex escape - DEL (0x7F) */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u007f\"}}",
        "\\x7f"
    );
    
    /* Hex escape - non-printable (0x02) */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u0002\"}}",
        "\\x02"
    );
    
    /* Hex escape - non-printable (0x1F) */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u001f\"}}",
        "\\x1f"
    );
}

/**
 * Test Category G: Unicode Escapes
 */
static void test_unicode_escapes(void** state) {
    (void)state;
    
    /* Unicode BMP character - copyright symbol */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u00a9\"}}",
        "\\x{a9}"
    );
    
    /* Unicode BMP character - Euro sign */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u20ac\"}}",
        "\\x{20ac}"
    );
    
    /* Unicode emoji - grinning face */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\ud83d\\ude00\"}}",
        "\\x{1f600}"
    );
    
    /* Unicode high surrogate range handling */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\ud83d\\udc4d\"}}",
        "\\x{1f44d}"
    );
}

/**
 * Test Category H: Mixed Literals and Escapes
 */
static void test_mixed_content(void** state) {
    (void)state;
    
    /* Literal with metachar and control char */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"hello\"},"
        "{\"type\": \"Literal\", \"value\": \"\\n\"},"
        "{\"type\": \"Literal\", \"value\": \"world\"}"
        "]}}",
        "hello\\nworld"
    );
    
    /* Literal with special chars */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"a\"},"
        "{\"type\": \"Literal\", \"value\": \"*\"},"
        "{\"type\": \"Literal\", \"value\": \"b\"}"
        "]}}",
        "a\\*b"
    );
    
    /* Multiple control characters */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"\\t\"},"
        "{\"type\": \"Literal\", \"value\": \"\\n\"},"
        "{\"type\": \"Literal\", \"value\": \"\\r\"}"
        "]}}",
        "\\t\\n\\r"
    );
}

/**
 * Test Category I: Edge Cases
 */
static void test_edge_cases(void** state) {
    (void)state;
    
    /* Empty literal */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\"}}",
        ""
    );
    
    /* Single space */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \" \"}}",
        "\\ "
    );
    
    /* Multiple spaces */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"   \"}}",
        "\\ \\ \\ "
    );
    
    /* Hash symbol (comment char in extended mode) */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"#\"}}",
        "\\#"
    );
    
    /* Tilde */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"~\"}}",
        "\\~"
    );
    
    /* Ampersand */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"&\"}}",
        "\\&"
    );
    
    /* Hyphen (minus) - not escaped in literal context */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"-\"}}",
        "-"
    );
}

/**
 * Test Category J: Special Character Combinations
 */
static void test_special_combinations(void** state) {
    (void)state;
    
    /* Backslash and metachar */
    test_compile(
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Literal\", \"value\": \"\\\\\"},"
        "{\"type\": \"Literal\", \"value\": \".\"}"
        "]}}",
        "\\\\\\."
    );
    
    /* Multiple backslashes */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\\\\\\\\"}}",
        "\\\\\\\\"
    );
    
    /* Quote marks */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\\"\"}}",
        "\\\""
    );
    
    /* Apostrophe */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"'\"}}",
        "'"
    );
}

/**
 * Test Category K: Non-ASCII Characters
 */
static void test_non_ascii(void** state) {
    (void)state;
    
    /* Latin-1 character - é */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u00e9\"}}",
        "\\x{e9}"
    );
    
    /* Latin-1 character - ñ */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u00f1\"}}",
        "\\x{f1}"
    );
    
    /* Latin-1 character - ü */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"\\u00fc\"}}",
        "\\x{fc}"
    );
}

/**
 * Test Category L: Additional Metacharacters
 */
static void test_additional_metachars(void** state) {
    (void)state;
    
    /* Less than */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"<\"}}",
        "<"
    );
    
    /* Greater than */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \">\"}}",
        ">"
    );
    
    /* Equals */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"=\"}}",
        "="
    );
    
    /* Exclamation */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \"!\"}}",
        "!"
    );
    
    /* Colon */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \":\"}}",
        ":"
    );
    
    /* Semicolon */
    test_compile(
        "{\"pattern\": {\"type\": \"Literal\", \"value\": \";\"}}",
        ";"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        {"test_basic_literals", test_basic_literals, NULL, NULL, NULL},
        {"test_escaped_metacharacters", test_escaped_metacharacters, NULL, NULL, NULL},
        {"test_dot", test_dot, NULL, NULL, NULL},
        {"test_literal_sequences", test_literal_sequences, NULL, NULL, NULL},
        {"test_control_escapes", test_control_escapes, NULL, NULL, NULL},
        {"test_hex_escapes", test_hex_escapes, NULL, NULL, NULL},
        {"test_unicode_escapes", test_unicode_escapes, NULL, NULL, NULL},
        {"test_mixed_content", test_mixed_content, NULL, NULL, NULL},
        {"test_edge_cases", test_edge_cases, NULL, NULL, NULL},
        {"test_special_combinations", test_special_combinations, NULL, NULL, NULL},
        {"test_non_ascii", test_non_ascii, NULL, NULL, NULL},
        {"test_additional_metachars", test_additional_metachars, NULL, NULL, NULL},
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
