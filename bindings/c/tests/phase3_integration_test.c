/**
 * @file phase3_integration_test.c
 * 
 * Integration tests combining character classes with other features
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/strling.h"

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

/* Test: Character class with quantifier */
static void test_char_class_with_quantifier(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Quantifier\","
        "    \"target\": {"
        "      \"type\": \"CharacterClass\","
        "      \"negated\": false,"
        "      \"members\": ["
        "        {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "      ]"
        "    },"
        "    \"min\": 1,"
        "    \"max\": null,"
        "    \"lazy\": false,"
        "    \"possessive\": false"
        "  }"
        "}";
    
    test_compile(json, "[a-z]+", "char_class_with_quantifier");
}

/* Test: Quantified character class with flags */
static void test_quantified_char_class_with_flags(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Quantifier\","
        "    \"target\": {"
        "      \"type\": \"CharacterClass\","
        "      \"negated\": false,"
        "      \"members\": ["
        "        {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "      ]"
        "    },"
        "    \"min\": 0,"
        "    \"max\": null,"
        "    \"lazy\": false,"
        "    \"possessive\": false"
        "  },"
        "  \"flags\": {"
        "    \"ignoreCase\": true,"
        "    \"multiline\": false,"
        "    \"dotAll\": false,"
        "    \"unicode\": false,"
        "    \"extended\": false"
        "  }"
        "}";
    
    test_compile(json, "(?i)[a-z]*", "quantified_char_class_with_flags");
}

/* Test: Character class in alternation */
static void test_char_class_in_alternation(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Alternation\","
        "    \"alternatives\": ["
        "      {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "        {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "      ]},"
        "      {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "        {\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}"
        "      ]}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "([a-z]|[0-9])", "char_class_in_alternation");
}

/* Test: Sequence with anchors, character classes, and quantifiers */
static void test_complex_pattern(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Sequence\","
        "    \"parts\": ["
        "      {\"type\": \"Anchor\", \"at\": \"Start\"},"
        "      {\"type\": \"Quantifier\", \"target\": {"
        "        \"type\": \"CharacterClass\","
        "        \"negated\": false,"
        "        \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]"
        "      }, \"min\": 1, \"max\": null, \"lazy\": false, \"possessive\": false},"
        "      {\"type\": \"Literal\", \"value\": \"@\"},"
        "      {\"type\": \"Quantifier\", \"target\": {"
        "        \"type\": \"CharacterClass\","
        "        \"negated\": false,"
        "        \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]"
        "      }, \"min\": 1, \"max\": null, \"lazy\": false, \"possessive\": false},"
        "      {\"type\": \"Anchor\", \"at\": \"End\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "^[a-z]+@[a-z]+$", "complex_pattern");
}

/* Test: Negated character class with meta characters */
static void test_negated_with_meta(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": true,"
        "    \"members\": ["
        "      {\"type\": \"Meta\", \"value\": \"w\"},"
        "      {\"type\": \"Meta\", \"value\": \"s\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[^\\w\\s]", "negated_with_meta");
}

/* Test: All meta character types */
static void test_all_meta_types(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Meta\", \"value\": \"d\"},"
        "      {\"type\": \"Meta\", \"value\": \"s\"},"
        "      {\"type\": \"Meta\", \"value\": \"w\"}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[\\d\\s\\w]", "all_meta_types");
}

/* Test: Character class with all member types */
static void test_all_member_types(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"CharacterClass\","
        "    \"negated\": false,"
        "    \"members\": ["
        "      {\"type\": \"Literal\", \"value\": \"x\"},"
        "      {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"},"
        "      {\"type\": \"Meta\", \"value\": \"d\"},"
        "      {\"type\": \"UnicodeProperty\", \"value\": \"L\", \"negated\": false}"
        "    ]"
        "  }"
        "}";
    
    test_compile(json, "[xa-z\\d\\p{L}]", "all_member_types");
}

/* Test: Lazy quantifier on character class */
static void test_lazy_quantified_char_class(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Quantifier\","
        "    \"target\": {"
        "      \"type\": \"CharacterClass\","
        "      \"negated\": false,"
        "      \"members\": ["
        "        {\"type\": \"Meta\", \"value\": \"w\"}"
        "      ]"
        "    },"
        "    \"min\": 0,"
        "    \"max\": null,"
        "    \"lazy\": true,"
        "    \"possessive\": false"
        "  }"
        "}";
    
    test_compile(json, "[\\w]*?", "lazy_quantified_char_class");
}

/* Test: Possessive quantifier on character class */
static void test_possessive_quantified_char_class(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Quantifier\","
        "    \"target\": {"
        "      \"type\": \"CharacterClass\","
        "      \"negated\": false,"
        "      \"members\": ["
        "        {\"type\": \"Meta\", \"value\": \"d\"}"
        "      ]"
        "    },"
        "    \"min\": 1,"
        "    \"max\": null,"
        "    \"lazy\": false,"
        "    \"possessive\": true"
        "  }"
        "}";
    
    test_compile(json, "[\\d]++", "possessive_quantified_char_class");
}

/* Test: Dot with flags */
static void test_dot_with_flags(void) {
    const char* json = 
        "{"
        "  \"pattern\": {"
        "    \"type\": \"Dot\""
        "  },"
        "  \"flags\": {"
        "    \"ignoreCase\": false,"
        "    \"multiline\": false,"
        "    \"dotAll\": true,"
        "    \"unicode\": false,"
        "    \"extended\": false"
        "  }"
        "}";
    
    test_compile(json, "(?s).", "dot_with_flags");
}

int main(void) {
    printf("\n=== Phase 3 Integration Tests ===\n\n");
    
    test_char_class_with_quantifier();
    test_quantified_char_class_with_flags();
    test_char_class_in_alternation();
    test_complex_pattern();
    test_negated_with_meta();
    test_all_meta_types();
    test_all_member_types();
    test_lazy_quantified_char_class();
    test_possessive_quantified_char_class();
    test_dot_with_flags();
    
    printf("\n=== All Integration Tests Passed! ===\n\n");
    return 0;
}
