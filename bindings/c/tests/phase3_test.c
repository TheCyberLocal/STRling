/**
 * @file phase3_test.c
 * 
 * Test suite for Phase 3: Character Classes and Flag Emission
 * 
 * This test verifies that the compiler correctly:
 * 1. Emits PCRE2 flag prefixes ((?i), (?m), (?s), (?x))
 * 2. Compiles CharacterClass nodes to PCRE2 character classes
 * 3. Handles negated character classes
 * 4. Handles ranges, meta-characters, and literals within classes
 * 5. Handles Unicode properties
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

/* Test helper with explicit flags */
static void test_compile_with_flags(const char* json_input, const STRlingFlags* flags, 
                                     const char* expected_pattern, const char* test_name) {
    STRlingResult* result = strling_compile(json_input, flags);
    
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

/* Test 1: Simple character class with single literal */
static void test_simple_char_class(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"a\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[a]", "simple_char_class");
}

/* Test 2: Character class with multiple literals */
static void test_multiple_literals(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"a\"},"
        "      {\"type\": \"Literal\", \"value\": \"b\"},"
        "      {\"type\": \"Literal\", \"value\": \"c\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[abc]", "multiple_literals");
}

/* Test 3: Negated character class */
static void test_negated_char_class(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": true,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"a\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[^a]", "negated_char_class");
}

/* Test 4: Character range */
static void test_char_range(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[a-z]", "char_range");
}

/* Test 5: Multiple ranges */
static void test_multiple_ranges(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"},"
        "      {\"type\": \"Range\", \"from\": \"A\", \"to\": \"Z\"},"
        "      {\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[a-zA-Z0-9]", "multiple_ranges");
}

/* Test 6: Meta character (\d) */
static void test_meta_digit(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Meta\", \"value\": \"d\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[\\d]", "meta_digit");
}

/* Test 7: Multiple meta characters */
static void test_multiple_meta(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Meta\", \"value\": \"w\"},"
        "      {\"type\": \"Meta\", \"value\": \"s\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[\\w\\s]", "multiple_meta");
}

/* Test 8: Mixed range and meta */
static void test_mixed_range_meta(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Range\", \"from\": \"a\", \"to\": \"f\"},"
        "      {\"type\": \"Meta\", \"value\": \"d\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[a-f\\d]", "mixed_range_meta");
}

/* Test 9: Unicode property */
static void test_unicode_property(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"UnicodeProperty\", \"value\": \"L\", \"negated\": false}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[\\p{L}]", "unicode_property");
}

/* Test 10: Negated Unicode property */
static void test_negated_unicode_property(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"UnicodeProperty\", \"value\": \"L\", \"negated\": true}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[\\P{L}]", "negated_unicode_property");
}

/* Test 11: Unicode property with name */
static void test_unicode_property_with_name(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"UnicodeProperty\", \"name\": \"Script\", \"value\": \"Latin\", \"negated\": false}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[\\p{Script=Latin}]", "unicode_property_with_name");
}

/* Test 12: Flag - ignoreCase only */
static void test_flag_ignore_case(void) {
    STRlingFlags* flags = strling_flags_create();
    flags->ignoreCase = true;
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  }"
        "}";
    
    test_compile_with_flags(json, flags, "(?i)test", "flag_ignore_case");
    strling_flags_free(flags);
}

/* Test 13: Flag - multiline only */
static void test_flag_multiline(void) {
    STRlingFlags* flags = strling_flags_create();
    flags->multiline = true;
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  }"
        "}";
    
    test_compile_with_flags(json, flags, "(?m)test", "flag_multiline");
    strling_flags_free(flags);
}

/* Test 14: Flag - dotAll only */
static void test_flag_dotall(void) {
    STRlingFlags* flags = strling_flags_create();
    flags->dotAll = true;
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  }"
        "}";
    
    test_compile_with_flags(json, flags, "(?s)test", "flag_dotall");
    strling_flags_free(flags);
}

/* Test 15: Flag - extended (free spacing) only */
static void test_flag_extended(void) {
    STRlingFlags* flags = strling_flags_create();
    flags->extended = true;
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  }"
        "}";
    
    test_compile_with_flags(json, flags, "(?x)test", "flag_extended");
    strling_flags_free(flags);
}

/* Test 16: Multiple flags combined */
static void test_flags_combined(void) {
    STRlingFlags* flags = strling_flags_create();
    flags->ignoreCase = true;
    flags->multiline = true;
    flags->dotAll = true;
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  }"
        "}";
    
    test_compile_with_flags(json, flags, "(?ims)test", "flags_combined");
    strling_flags_free(flags);
}

/* Test 17: All flags */
static void test_all_flags(void) {
    STRlingFlags* flags = strling_flags_create();
    flags->ignoreCase = true;
    flags->multiline = true;
    flags->dotAll = true;
    flags->extended = true;
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  }"
        "}";
    
    test_compile_with_flags(json, flags, "(?imsx)test", "all_flags");
    strling_flags_free(flags);
}

/* Test 18: Flags from JSON */
static void test_flags_from_json(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Literal\","
        "    \"value\": \"test\""
        "  },"
        "  \"flags\": {"
        "    \"ignoreCase\": true,"
        "    \"multiline\": false,"
        "    \"dotAll\": true,"
        "    \"unicode\": false,"
        "    \"extended\": false"
        "  }"
        "}";
    
    test_compile(json, "(?is)test", "flags_from_json");
}

/* Test 19: Character class with flags */
static void test_char_class_with_flags(void) {
    STRlingFlags* flags = strling_flags_create();
    flags->ignoreCase = true;
    
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile_with_flags(json, flags, "(?i)[a-z]", "char_class_with_flags");
    strling_flags_free(flags);
}

/* Test 20: Special characters in character class */
static void test_special_chars_in_class(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"]\"},"
        "      {\"type\": \"Literal\", \"value\": \"a\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[\\]a]", "special_chars_in_class");
}

int main(void) {
    printf("\n=== Phase 3 Tests: Character Classes and Flags ===\n\n");
    
    printf("--- Character Class Tests ---\n");
    test_simple_char_class();
    test_multiple_literals();
    test_negated_char_class();
    test_char_range();
    test_multiple_ranges();
    test_meta_digit();
    test_multiple_meta();
    test_mixed_range_meta();
    test_unicode_property();
    test_negated_unicode_property();
    test_unicode_property_with_name();
    test_special_chars_in_class();
    
    printf("\n--- Flag Tests ---\n");
    test_flag_ignore_case();
    test_flag_multiline();
    test_flag_dotall();
    test_flag_extended();
    test_flags_combined();
    test_all_flags();
    test_flags_from_json();
    test_char_class_with_flags();
    
    printf("\n=== All Phase 3 Tests Passed! ===\n\n");
    return 0;
}
