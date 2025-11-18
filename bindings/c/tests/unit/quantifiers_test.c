/**
 * @file quantifiers_test.c
 *
 * Refactored to test the real STRling C library API.
 * Tests quantifier compilation from JSON AST to PCRE2 patterns.
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
 * Test Category A: Standard Quantifiers (*, +, ?)
 */
static void test_standard_quantifiers(void** state) {
    (void)state;
    
    /* a* - Zero or more */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a*"
    );
    
    /* a+ - One or more */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a+"
    );
    
    /* a? - Zero or one */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a?"
    );
}

/**
 * Test Category B: Brace Quantifiers ({m,n})
 */
static void test_brace_quantifiers(void** state) {
    (void)state;
    
    /* a{3} - Exactly 3 */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 3, \"max\": 3, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a{3}"
    );
    
    /* a{2,} - At least 2 */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 2, \"max\": null, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a{2,}"
    );
    
    /* a{1,5} - Between 1 and 5 */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": 5, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a{1,5}"
    );
}

/**
 * Test Category C: Lazy Quantifiers
 */
static void test_lazy_quantifiers(void** state) {
    (void)state;
    
    /* a*? - Zero or more (lazy) */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, "
        "\"lazy\": true, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a*?"
    );
    
    /* a+? - One or more (lazy) */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, "
        "\"lazy\": true, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a+?"
    );
    
    /* a?? - Zero or one (lazy) */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, "
        "\"lazy\": true, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a??"
    );
    
    /* a{2,}? - At least 2 (lazy) */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 2, \"max\": null, "
        "\"lazy\": true, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a{2,}?"
    );
}

/**
 * Test Category D: Possessive Quantifiers
 */
static void test_possessive_quantifiers(void** state) {
    (void)state;
    
    /* a*+ - Zero or more (possessive) */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, "
        "\"possessive\": true, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a*+"
    );
    
    /* a++ - One or more (possessive) */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, "
        "\"possessive\": true, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a++"
    );
    
    /* a?+ - Zero or one (possessive) */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, "
        "\"possessive\": true, "
        "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
        "a?+"
    );
}

/**
 * Test Category E: Quantified Groups and Classes
 */
static void test_quantified_groups_and_classes(void** state) {
    (void)state;
    
    /* (abc)+ - Quantified group */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, "
        "\"target\": {\"type\": \"Group\", \"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}}",
        "(abc)+"
    );
    
    /* [a-z]* - Quantified character class */
    test_compile(
        "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, "
        "\"target\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": ["
        "{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}"
        "]}}}",
        "[a-z]*"
    );
}

/* Main test runner */
int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_standard_quantifiers),
        cmocka_unit_test(test_brace_quantifiers),
        cmocka_unit_test(test_lazy_quantifiers),
        cmocka_unit_test(test_possessive_quantifiers),
        cmocka_unit_test(test_quantified_groups_and_classes),
    };
    
    return cmocka_run_group_tests(tests, NULL, NULL);
}
