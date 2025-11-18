/*
 * Simple integration test for STRling C binding
 * This demonstrates basic usage of the public API
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/strling.h"

void test_version() {
    const char* version = strling_version();
    assert(version != NULL);
    assert(strcmp(version, "0.1.0") == 0);
    printf("✓ Version test passed: %s\n", version);
}

void test_simple_literal() {
    /* Test JSON: {"pattern": {"type": "Literal", "value": "hello"}} */
    const char* json = "{\"pattern\": {\"type\": \"Literal\", \"value\": \"hello\"}}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    
    if (result->error) {
        printf("✗ Literal test failed: %s\n", result->error->message);
        strling_result_free(result);
        exit(1);
    }
    
    assert(result->pattern != NULL);
    /* The literal "hello" should be escaped if needed */
    printf("✓ Literal test passed: '%s'\n", result->pattern);
    
    strling_result_free(result);
}

void test_anchor() {
    /* Test JSON: {"pattern": {"type": "Anchor", "at": "Start"}} */
    const char* json = "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"Start\"}}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    assert(result->error == NULL);
    assert(result->pattern != NULL);
    assert(strcmp(result->pattern, "^") == 0);
    
    printf("✓ Anchor test passed: '%s'\n", result->pattern);
    strling_result_free(result);
}

void test_sequence() {
    /* Test JSON: {"pattern": {"type": "Sequence", "parts": [
     *   {"type": "Anchor", "at": "Start"},
     *   {"type": "Literal", "value": "test"},
     *   {"type": "Anchor", "at": "End"}
     * ]}} */
    const char* json = "{"
        "\"pattern\": {"
            "\"type\": \"Sequence\", "
            "\"parts\": ["
                "{\"type\": \"Anchor\", \"at\": \"Start\"},"
                "{\"type\": \"Literal\", \"value\": \"test\"},"
                "{\"type\": \"Anchor\", \"at\": \"End\"}"
            "]"
        "}"
    "}";
    
    STRlingResult* result = strling_compile(json, NULL);
    assert(result != NULL);
    
    if (result->error) {
        printf("✗ Sequence test failed: %s\n", result->error->message);
        strling_result_free(result);
        exit(1);
    }
    
    assert(result->pattern != NULL);
    /* Should produce: ^test$ */
    printf("✓ Sequence test passed: '%s'\n", result->pattern);
    
    strling_result_free(result);
}

void test_error_handling() {
    /* Test with invalid JSON */
    const char* bad_json = "{invalid json";
    
    STRlingResult* result = strling_compile(bad_json, NULL);
    assert(result != NULL);
    assert(result->error != NULL);
    assert(result->pattern == NULL);
    
    printf("✓ Error handling test passed: %s\n", result->error->message);
    strling_result_free(result);
}

void test_flags() {
    STRlingFlags* flags = strling_flags_create();
    assert(flags != NULL);
    assert(flags->ignoreCase == false);
    assert(flags->multiline == false);
    
    flags->ignoreCase = true;
    assert(flags->ignoreCase == true);
    
    strling_flags_free(flags);
    printf("✓ Flags test passed\n");
}

int main() {
    printf("Running STRling C Binding Tests\n");
    printf("================================\n\n");
    
    test_version();
    test_simple_literal();
    test_anchor();
    test_sequence();
    test_error_handling();
    test_flags();
    
    printf("\n================================\n");
    printf("All tests passed! ✓\n");
    
    return 0;
}
