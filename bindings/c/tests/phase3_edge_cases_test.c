/**
 * @file phase3_edge_cases_test.c
 * 
 * Additional edge case tests for Phase 3: Character Classes and Flag Emission
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/strling.h"

/* Test helper to check compiled pattern */
static void test_compile(const char* json_input, const char* expected_pattern, const char* test_name) {
    STRlingResult* result = strling_compile(json_input, NULL);
    
    if (!result) {
        printf("FAIL [%s]: strling_compile returned NULL\n", test_name);
        exit(1);
    }
    
    if (result->error) {
        printf("FAIL [%s]: Compilation error: %s\n", test_name, result->error->message);
        strling_result_free(result);
        exit(1);
    }
    
    if (!result->pattern) {
        printf("FAIL [%s]: Pattern is NULL\n", test_name);
        strling_result_free(result);
        exit(1);
    }
    
    if (strcmp(result->pattern, expected_pattern) != 0) {
        printf("FAIL [%s]: Expected '%s', got '%s'\n", test_name, expected_pattern, result->pattern);
        strling_result_free(result);
        exit(1);
    }
    
    printf("PASS [%s]\n", test_name);
    strling_result_free(result);
}

/* Test: Hyphen as literal at start */
static void test_hyphen_at_start(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"-\"},"
        "      {\"type\": \"Literal\", \"value\": \"a\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[-a]", "hyphen_at_start");
}

/* Test: Hyphen as literal at end */
static void test_hyphen_at_end(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"a\"},"
        "      {\"type\": \"Literal\", \"value\": \"-\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[a-]", "hyphen_at_end");
}

/* Test: Backslash literal */
static void test_backslash_literal(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"\\\\\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[\\\\]", "backslash_literal");
}

/* Test: Caret as literal (not at start of class content) */
static void test_caret_literal(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"a\"},"
        "      {\"type\": \"Literal\", \"value\": \"^\"},"
        "      {\"type\": \"Literal\", \"value\": \"b\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[a\\^b]", "caret_literal");
}

/* Test: Empty character class */
static void test_empty_char_class(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": []"
        "  }"
        "}";
    
    test_compile(json, "[]", "empty_char_class");
}

/* Test: Negated empty character class */
static void test_negated_empty_char_class(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": true,"
        "    \"members\": []"
        "  }"
        "}";
    
    test_compile(json, "[^]", "negated_empty_char_class");
}

/* Test: Complex mixed members */
static void test_complex_mixed(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"},"
        "      {\"type\": \"Meta\", \"value\": \"d\"},"
        "      {\"type\": \"Literal\", \"value\": \"_\"},"
        "      {\"type\": \"UnicodeProperty\", \"value\": \"L\", \"negated\": false}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[a-z\\d_\\p{L}]", "complex_mixed");
}

/* Test: Negated class with complex content */
static void test_negated_complex(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": true,"
        "    \"members\": ["
        "      {\"type\": \"Meta\", \"value\": \"s\"},"
        "      {\"type\": \"Meta\", \"value\": \"d\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[^\\s\\d]", "negated_complex");
}

/* Test: Character class in sequence */
static void test_char_class_in_sequence(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Sequence\","
        "    \"parts\": ["
        "      {\"type\": \"Anchor\", \"at\": \"Start\"},"
        "      {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "        {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "      ]},"
        "      {\"type\": \"Anchor\", \"at\": \"End\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "^[a-z]$", "char_class_in_sequence");
}

/* Test: No flags set */
static void test_no_flags(void) {
    STRlingFlags* flags = strling_flags_create();
    /* All flags default to false */
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  }"
        "}";
    
    STRlingResult* result = strling_compile(json, flags);
    
    if (!result || result->error) {
        printf("FAIL [no_flags]: Compilation failed\n");
        if (result) strling_result_free(result);
        strling_flags_free(flags);
        exit(1);
    }
    
    /* Should not have any flag prefix */
    if (strcmp(result->pattern, "test") != 0) {
        printf("FAIL [no_flags]: Expected 'test', got '%s'\n", result->pattern);
        strling_result_free(result);
        strling_flags_free(flags);
        exit(1);
    }
    
    printf("PASS [no_flags]\n");
    strling_result_free(result);
    strling_flags_free(flags);
}

/* Test: Unicode flag (should be ignored as it's not in PCRE2 inline flags) */
static void test_unicode_flag_ignored(void) {
    STRlingFlags* flags = strling_flags_create();
    flags->unicode = true;
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  }"
        "}";
    
    STRlingResult* result = strling_compile(json, flags);
    
    if (!result || result->error) {
        printf("FAIL [unicode_flag_ignored]: Compilation failed\n");
        if (result) strling_result_free(result);
        strling_flags_free(flags);
        exit(1);
    }
    
    /* Unicode flag doesn't have a PCRE2 inline equivalent, so pattern should be unchanged */
    if (strcmp(result->pattern, "test") != 0) {
        printf("FAIL [unicode_flag_ignored]: Expected 'test', got '%s'\n", result->pattern);
        strling_result_free(result);
        strling_flags_free(flags);
        exit(1);
    }
    
    printf("PASS [unicode_flag_ignored]\n");
    strling_result_free(result);
    strling_flags_free(flags);
}

int main(void) {
    printf("\n=== Phase 3 Edge Case Tests ===\n\n");
    
    test_hyphen_at_start();
    test_hyphen_at_end();
    test_backslash_literal();
    test_caret_literal();
    test_empty_char_class();
    test_negated_empty_char_class();
    test_complex_mixed();
    test_negated_complex();
    test_char_class_in_sequence();
    test_no_flags();
    test_unicode_flag_ignored();
    
    printf("\n=== All Edge Case Tests Passed! ===\n\n");
    return 0;
}
