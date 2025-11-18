/*
 * Test for Quantifier and Alternation support
 * This validates the implementation of Phase 2 features
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/strling.h"

void test_quantifier_star() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 0,"
            "\"max\": null,"
            "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a*") == 0);
    
    printf("✓ Quantifier * test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_quantifier_plus() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 1,"
            "\"max\": null,"
            "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a+") == 0);
    
    printf("✓ Quantifier + test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_quantifier_question() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 0,"
            "\"max\": 1,"
            "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a?") == 0);
    
    printf("✓ Quantifier ? test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_quantifier_exact() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 3,"
            "\"max\": 3,"
            "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a{3}") == 0);
    
    printf("✓ Quantifier {3} test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_quantifier_range() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 2,"
            "\"max\": 5,"
            "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a{2,5}") == 0);
    
    printf("✓ Quantifier {2,5} test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_quantifier_min_only() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 2,"
            "\"max\": null,"
            "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a{2,}") == 0);
    
    printf("✓ Quantifier {2,} test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_quantifier_lazy() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 0,"
            "\"max\": null,"
            "\"lazy\": true,"
            "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a*?") == 0);
    
    printf("✓ Quantifier *? (lazy) test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_quantifier_possessive() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 1,"
            "\"max\": null,"
            "\"possessive\": true,"
            "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a++") == 0);
    
    printf("✓ Quantifier ++ (possessive) test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_alternation_simple() {
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Alternation\","
            "\"alternatives\": ["
                "{\"type\": \"Literal\", \"value\": \"a\"},"
                "{\"type\": \"Literal\", \"value\": \"b\"},"
                "{\"type\": \"Literal\", \"value\": \"c\"}"
            "]"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "(a|b|c)") == 0);
    
    printf("✓ Alternation test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_complex_quantifier_sequence() {
    /* Test: "a*b+c?" */
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Sequence\","
            "\"parts\": ["
                "{"
                    "\"type\": \"Quantifier\","
                    "\"min\": 0,"
                    "\"max\": null,"
                    "\"target\": {\"type\": \"Literal\", \"value\": \"a\"}"
                "},"
                "{"
                    "\"type\": \"Quantifier\","
                    "\"min\": 1,"
                    "\"max\": null,"
                    "\"target\": {\"type\": \"Literal\", \"value\": \"b\"}"
                "},"
                "{"
                    "\"type\": \"Quantifier\","
                    "\"min\": 0,"
                    "\"max\": 1,"
                    "\"target\": {\"type\": \"Literal\", \"value\": \"c\"}"
                "}"
            "]"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "a*b+c?") == 0);
    
    printf("✓ Complex quantifier sequence test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_quantifier_on_alternation() {
    /* Test: (a|b)+ */
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Quantifier\","
            "\"min\": 1,"
            "\"max\": null,"
            "\"target\": {"
                "\"type\": \"Alternation\","
                "\"alternatives\": ["
                    "{\"type\": \"Literal\", \"value\": \"a\"},"
                    "{\"type\": \"Literal\", \"value\": \"b\"}"
                "]"
            "}"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "(a|b)+") == 0);
    
    printf("✓ Quantifier on alternation test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

int main() {
    printf("Running Quantifier and Alternation Tests\n");
    printf("=========================================\n\n");
    
    test_quantifier_star();
    test_quantifier_plus();
    test_quantifier_question();
    test_quantifier_exact();
    test_quantifier_range();
    test_quantifier_min_only();
    test_quantifier_lazy();
    test_quantifier_possessive();
    test_alternation_simple();
    test_complex_quantifier_sequence();
    test_quantifier_on_alternation();
    
    printf("\n=========================================\n");
    printf("All tests passed! ✓\n");
    
    return 0;
}
