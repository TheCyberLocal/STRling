/*
 * Phase 4 Tests: Groups, Backreferences, and Lookarounds
 * Tests the implementation of all grouping constructs, backreferences, and lookarounds
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "../include/strling.h"

typedef struct {
    const char* name;
    const char* json;
    const char* expected;
} TestCase;

void run_test(const TestCase* test) {
    STRlingResult* result = strling_compile(test->json, NULL);
    
    if (result->error) {
        printf("FAIL [%s]: Error: %s\n", test->name, result->error->message);
        strling_result_free(result);
        exit(1);
    }
    
    if (strcmp(result->pattern, test->expected) != 0) {
        printf("FAIL [%s]: Expected '%s', got '%s'\n", 
               test->name, test->expected, result->pattern);
        strling_result_free(result);
        exit(1);
    }
    
    printf("PASS [%s]\n", test->name);
    strling_result_free(result);
}

int main(void) {
    printf("=== Phase 4 Tests: Groups, Backreferences, and Lookarounds ===\n\n");
    
    /* === Anchor Tests === */
    printf("--- Extended Anchor Tests ---\n");
    TestCase anchor_tests[] = {
        {"word_boundary", 
         "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"WordBoundary\"}}", 
         "\\b"},
        {"non_word_boundary", 
         "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"NonWordBoundary\"}}", 
         "\\B"},
        {"absolute_start", 
         "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"AbsoluteStart\"}}", 
         "\\A"},
        {"absolute_end", 
         "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"AbsoluteEnd\"}}", 
         "\\Z"},
        {"absolute_end_only", 
         "{\"pattern\": {\"type\": \"Anchor\", \"at\": \"AbsoluteEndOnly\"}}", 
         "\\z"},
        {NULL, NULL, NULL}
    };
    
    for (int i = 0; anchor_tests[i].name != NULL; i++) {
        run_test(&anchor_tests[i]);
    }
    
    /* === Meta Tests === */
    printf("\n--- Standalone Meta Tests ---\n");
    TestCase meta_tests[] = {
        {"meta_b", 
         "{\"pattern\": {\"type\": \"Meta\", \"value\": \"b\"}}", 
         "\\b"},
        {"meta_d", 
         "{\"pattern\": {\"type\": \"Meta\", \"value\": \"d\"}}", 
         "\\d"},
        {"meta_w", 
         "{\"pattern\": {\"type\": \"Meta\", \"value\": \"w\"}}", 
         "\\w"},
        {"meta_s", 
         "{\"pattern\": {\"type\": \"Meta\", \"value\": \"s\"}}", 
         "\\s"},
        {NULL, NULL, NULL}
    };
    
    for (int i = 0; meta_tests[i].name != NULL; i++) {
        run_test(&meta_tests[i]);
    }
    
    /* === Group Tests === */
    printf("\n--- Group Tests ---\n");
    TestCase group_tests[] = {
        {"capturing_group", 
         "{\"pattern\": {\"type\": \"Group\", \"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}", 
         "(abc)"},
        {"non_capturing_group", 
         "{\"pattern\": {\"type\": \"Group\", \"capturing\": false, \"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}", 
         "(?:abc)"},
        {"named_group", 
         "{\"pattern\": {\"type\": \"Group\", \"name\": \"myname\", \"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}", 
         "(?<myname>abc)"},
        {"atomic_group", 
         "{\"pattern\": {\"type\": \"Group\", \"atomic\": true, \"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}", 
         "(?>abc)"},
        {"nested_groups",
         "{\"pattern\": {\"type\": \"Group\", \"body\": {\"type\": \"Group\", \"capturing\": false, \"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}}",
         "((?:x))"},
        {NULL, NULL, NULL}
    };
    
    for (int i = 0; group_tests[i].name != NULL; i++) {
        run_test(&group_tests[i]);
    }
    
    /* === Backreference Tests === */
    printf("\n--- Backreference Tests ---\n");
    TestCase backref_tests[] = {
        {"numeric_backref_1", 
         "{\"pattern\": {\"type\": \"Backreference\", \"index\": 1}}", 
         "\\1"},
        {"numeric_backref_2", 
         "{\"pattern\": {\"type\": \"Backreference\", \"index\": 2}}", 
         "\\2"},
        {"numeric_backref_10", 
         "{\"pattern\": {\"type\": \"Backreference\", \"index\": 10}}", 
         "\\10"},
        {"named_backref", 
         "{\"pattern\": {\"type\": \"Backreference\", \"name\": \"foo\"}}", 
         "\\k<foo>"},
        {"named_backref_long", 
         "{\"pattern\": {\"type\": \"Backreference\", \"name\": \"longname\"}}", 
         "\\k<longname>"},
        {NULL, NULL, NULL}
    };
    
    for (int i = 0; backref_tests[i].name != NULL; i++) {
        run_test(&backref_tests[i]);
    }
    
    /* === Lookaround Tests === */
    printf("\n--- Lookaround Tests ---\n");
    TestCase lookaround_tests[] = {
        {"lookahead", 
         "{\"pattern\": {\"type\": \"Lookahead\", \"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}", 
         "(?=x)"},
        {"negative_lookahead", 
         "{\"pattern\": {\"type\": \"NegativeLookahead\", \"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}", 
         "(?!x)"},
        {"lookbehind", 
         "{\"pattern\": {\"type\": \"Lookbehind\", \"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}", 
         "(?<=x)"},
        {"negative_lookbehind", 
         "{\"pattern\": {\"type\": \"NegativeLookbehind\", \"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}", 
         "(?<!x)"},
        {"complex_lookahead",
         "{\"pattern\": {\"type\": \"Lookahead\", \"body\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}}",
         "(?=ab)"},
        {NULL, NULL, NULL}
    };
    
    for (int i = 0; lookaround_tests[i].name != NULL; i++) {
        run_test(&lookaround_tests[i]);
    }
    
    /* === Integration Tests === */
    printf("\n--- Integration Tests ---\n");
    TestCase integration_tests[] = {
        {"group_with_backref",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Group\", \"body\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Backreference\", \"index\": 1}"
         "]}}",
         "(a)\\1"},
        {"named_group_with_backref",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Group\", \"name\": \"test\", \"body\": {\"type\": \"Literal\", \"value\": \"hello\"}},"
         "{\"type\": \"Backreference\", \"name\": \"test\"}"
         "]}}",
         "(?<test>hello)\\k<test>"},
        {"word_boundary_sequence",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
         "{\"type\": \"Literal\", \"value\": \"word\"},"
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}"
         "]}}",
         "\\bword\\b"},
        {"group_with_lookahead",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Group\", \"body\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Lookahead\", \"body\": {\"type\": \"Literal\", \"value\": \"b\"}}"
         "]}}",
         "(a)(?=b)"},
        {"alternation_with_groups",
         "{\"pattern\": {\"type\": \"Alternation\", \"alternatives\": ["
         "{\"type\": \"Group\", \"body\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Group\", \"name\": \"x\", \"body\": {\"type\": \"Literal\", \"value\": \"b\"}}"
         "]}}",
         "((a)|(?<x>b))"},
        {"quantified_group",
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"target\": {\"type\": \"Group\", \"body\": {\"type\": \"Literal\", \"value\": \"abc\"}}}}",
         "(abc)+"},
        {"atomic_group_with_quantifier",
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"target\": {\"type\": \"Group\", \"atomic\": true, \"body\": {\"type\": \"Literal\", \"value\": \"x\"}}}}",
         "(?>x)*"},
        {NULL, NULL, NULL}
    };
    
    for (int i = 0; integration_tests[i].name != NULL; i++) {
        run_test(&integration_tests[i]);
    }
    
    printf("\n=== All Phase 4 Tests Passed! ===\n");
    return 0;
}
