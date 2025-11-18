/* Edge case tests for Phase 4 implementation */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/strling.h"

void test_deeply_nested_groups() {
    /* Test: (((...))) */
    const char* json = 
        "{\"pattern\": {\"type\": \"Group\", \"body\": "
        "{\"type\": \"Group\", \"body\": "
        "{\"type\": \"Group\", \"body\": "
        "{\"type\": \"Literal\", \"value\": \"x\"}}}}}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(strcmp(result->pattern, "(((x)))") == 0);
    printf("✓ Deeply nested groups: %s\n", result->pattern);
    strling_result_free(result);
}

void test_mixed_group_types_nested() {
    /* Test: ((?:(?<name>...))) */
    const char* json = 
        "{\"pattern\": {\"type\": \"Group\", \"body\": "
        "{\"type\": \"Group\", \"capturing\": false, \"body\": "
        "{\"type\": \"Group\", \"name\": \"inner\", \"body\": "
        "{\"type\": \"Literal\", \"value\": \"test\"}}}}}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(strcmp(result->pattern, "((?:(?<inner>test)))") == 0);
    printf("✓ Mixed nested groups: %s\n", result->pattern);
    strling_result_free(result);
}

void test_lookaround_with_group() {
    /* Test: (?=(a)) */
    const char* json = 
        "{\"pattern\": {\"type\": \"Lookahead\", \"body\": "
        "{\"type\": \"Group\", \"body\": "
        "{\"type\": \"Literal\", \"value\": \"a\"}}}}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(strcmp(result->pattern, "(?=(a))") == 0);
    printf("✓ Lookahead with group: %s\n", result->pattern);
    strling_result_free(result);
}

void test_complex_pattern() {
    /* Test: ^(?<word>\b\w+\b)\s+\k<word>$ */
    const char* json = 
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Anchor\", \"at\": \"Start\"},"
        "{\"type\": \"Group\", \"name\": \"word\", \"body\": "
            "{\"type\": \"Sequence\", \"parts\": ["
            "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
            "{\"type\": \"Meta\", \"value\": \"w\"},"
            "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}"
            "]}},"
        "{\"type\": \"Meta\", \"value\": \"s\"},"
        "{\"type\": \"Backreference\", \"name\": \"word\"},"
        "{\"type\": \"Anchor\", \"at\": \"End\"}"
        "]}}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    printf("✓ Complex pattern: %s\n", result->pattern);
    strling_result_free(result);
}

void test_all_lookarounds_sequence() {
    /* Test: (?=a)(?!b)(?<=c)(?<!d) */
    const char* json = 
        "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
        "{\"type\": \"Lookahead\", \"body\": {\"type\": \"Literal\", \"value\": \"a\"}},"
        "{\"type\": \"NegativeLookahead\", \"body\": {\"type\": \"Literal\", \"value\": \"b\"}},"
        "{\"type\": \"Lookbehind\", \"body\": {\"type\": \"Literal\", \"value\": \"c\"}},"
        "{\"type\": \"NegativeLookbehind\", \"body\": {\"type\": \"Literal\", \"value\": \"d\"}}"
        "]}}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(strcmp(result->pattern, "(?=a)(?!b)(?<=c)(?<!d)") == 0);
    printf("✓ All lookarounds: %s\n", result->pattern);
    strling_result_free(result);
}

void test_empty_group() {
    /* Test: () with empty sequence */
    const char* json = 
        "{\"pattern\": {\"type\": \"Group\", \"body\": "
        "{\"type\": \"Sequence\", \"parts\": []}}}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(strcmp(result->pattern, "()") == 0);
    printf("✓ Empty group: %s\n", result->pattern);
    strling_result_free(result);
}

int main(void) {
    printf("=== Phase 4 Edge Case Tests ===\n\n");
    
    test_deeply_nested_groups();
    test_mixed_group_types_nested();
    test_lookaround_with_group();
    test_complex_pattern();
    test_all_lookarounds_sequence();
    test_empty_group();
    
    printf("\n=== All Edge Case Tests Passed! ===\n");
    return 0;
}
