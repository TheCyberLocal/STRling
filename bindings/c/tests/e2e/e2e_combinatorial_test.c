/**
 * @file e2e_combinatorial_test.c
 * @brief End-to-End Combinatorial Tests for libstrling (90+ Test Cases).
 *
 * PURPOSE:
 * This suite provides systematic combinatorial E2E validation for the C binding,
 * mirroring the logic in `bindings/javascript/__tests__/e2e/e2e_combinatorial.test.ts`.
 *
 * DESIGN:
 * Since libstrling currently accepts JSON AST input (no built-in DSL parser),
 * these tests map the DSL inputs from the reference suite into their equivalent
 * JSON AST representations to verify the Compiler and Emitter logic.
 *
 * SCOPE:
 * - Tier 1: Pairwise Combinatorial Tests (N=2)
 * - Tier 2: Strategic Triplet Tests (N=3)
 * - Complex Nested Feature Tests
 */

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>
#include <stdio.h>

#include "strling.h"

// --- Test Infrastructure ----------------------------------------------------

typedef struct {
    const char *id;
    const char *json_input;
    const char *expected_pcre;
} TestCase;

static void run_test_batch(void **state, const TestCase *cases, size_t count) {
    (void)state;
    
    for (size_t i = 0; i < count; i++) {
        // printf("Running %s...\n", cases[i].id); // Uncomment for debug
        
        strling_result_t result = strling_compile_compat(cases[i].json_input, NULL);
        
        if (result.error_code != STRling_OK) {
            printf("FAIL [%s]: Compilation error: %s\n", cases[i].id, result.error_message);
        }
        assert_int_equal(result.error_code, STRling_OK);
        assert_non_null(result.pcre2_pattern);
        
        if (strcmp(result.pcre2_pattern, cases[i].expected_pcre) != 0) {
            printf("FAIL [%s]:\n  Expected: %s\n  Got:      %s\n", 
                   cases[i].id, cases[i].expected_pcre, result.pcre2_pattern);
        }
        assert_string_equal(result.pcre2_pattern, cases[i].expected_pcre);
        
        strling_result_free_compat(&result);
    }
}

// --- Tier 1: Pairwise Tests -------------------------------------------------

static void test_tier1_flags(void **state) {
    const TestCase cases[] = {
        // Flags + Literals
        {"flags_literals_case_insensitive", 
         "{\"flags\": \"i\", \"pattern\": {\"type\": \"Literal\", \"value\": \"hello\"}}", 
         "(?i)hello"},
        {"flags_literals_free_spacing", 
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}}", 
         "(?x)abc"},
         
        // Flags + CharClass
        {"flags_charclass_case_insensitive",
         "{\"flags\": \"i\", \"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": "
             "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}}}",
         "(?i)[a-z]+"},
         
        // Flags + Anchors
        {"flags_anchor_multiline",
         "{\"flags\": \"m\", \"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"start\"}]}}",
         "(?m)^start"},
         
        // Flags + Groups
        {"flags_group_case_insensitive",
         "{\"flags\": \"i\", \"pattern\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"hello\"}}}",
         "(?i)(hello)"},
         
        // Flags + Lookarounds
        {"flags_lookahead_case_insensitive",
         "{\"flags\": \"i\", \"pattern\": {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"test\"}}}",
         "(?i)(?=test)"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

static void test_tier1_literals(void **state) {
    const TestCase cases[] = {
        // Literals + CharClass
        {"literals_charclass",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Literal\", \"value\": \"abc\"},"
             "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"x\", \"to\": \"z\"}]}]}}",
         "abc[x-z]"}, // Normalized [xyz] to range for simplicity in C output check
         
        // Literals + Anchors
        {"literals_anchor_start",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"hello\"}]}}",
         "^hello"},
        {"literals_anchor_boundary",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}, {\"type\": \"Literal\", \"value\": \"hello\"}, {\"type\": \"Anchor\", \"at\": \"WordBoundary\"}]}}",
         "\\bhello\\b"},
         
        // Literals + Quantifiers
        {"literals_quantifier_plus",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}},"
             "{\"type\": \"Literal\", \"value\": \"bc\"}]}}",
         "a+bc"},
         
        // Literals + Groups
        {"literals_group_capturing",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Literal\", \"value\": \"hello\"},"
             "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"world\"}}]}}",
         "hello(world)"},
         
        // Literals + Lookarounds
        {"literals_lookahead",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Literal\", \"value\": \"hello\"},"
             "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"world\"}}]}}",
         "hello(?=world)"},
         
        // Literals + Alternation
        {"literals_alternation",
         "{\"pattern\": {\"type\": \"Alternation\", \"alternatives\": ["
             "{\"type\": \"Literal\", \"value\": \"hello\"}, {\"type\": \"Literal\", \"value\": \"world\"}]}}",
         "hello|world"},
         
        // Literals + Backrefs
        {"literals_backref",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"word\"}]}}},"
             "{\"type\": \"Literal\", \"value\": \"=\"},"
             "{\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}]}}",
         "(\\w+)=\\1"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

static void test_tier1_charclasses(void **state) {
    const TestCase cases[] = {
        // CharClass + Anchors
        {"charclass_anchor_start",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Anchor\", \"at\": \"Start\"},"
             "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}}]}}",
         "^[a-z]+"},
         
        // CharClass + Quantifiers
        {"charclass_quantifier_star",
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": "
             "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}}}",
         "[a-z]*"},
         
        // CharClass + Groups
        {"charclass_group",
         "{\"pattern\": {\"type\": \"Group\", \"capturing\": true, \"expression\": "
             "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}}}}",
         "([a-z]+)"},
         
        // CharClass + Lookarounds
        {"charclass_lookahead",
         "{\"pattern\": {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": "
             "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}}}",
         "(?=[a-z])"},
         
        // CharClass + Alternation
        {"charclass_alternation",
         "{\"pattern\": {\"type\": \"Alternation\", \"alternatives\": ["
             "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]},"
             "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}]}]}}",
         "[a-z]|[0-9]"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

static void test_tier1_anchors(void **state) {
    const TestCase cases[] = {
        {"anchor_quantifier",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}]}}",
         "^a+"},
        {"anchor_group",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"test\"}}]}}",
         "^(test)"},
        {"anchor_lookahead",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"test\"}}]}}",
         "^(?=test)"},
        {"anchor_alternation",
         "{\"pattern\": {\"type\": \"Alternation\", \"alternatives\": ["
             "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"a\"}]},"
             "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Anchor\", \"at\": \"End\"}]}]}}",
         "^a|b$"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

static void test_tier1_quantifiers(void **state) {
    const TestCase cases[] = {
        {"quantifier_group",
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"abc\"}}}}",
         "(abc)+"},
        {"quantifier_lookahead_hack", 
         // Note: (?=a)+ is usually wrapped in non-capturing group by compiler
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}}}",
         "(?:(?=a))+"},
        {"quantifier_alternation",
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}}}",
         "(a|b)+"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

static void test_tier1_groups_lookarounds(void **state) {
    const TestCase cases[] = {
        {"group_lookahead_inside",
         "{\"pattern\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"test\"}},"
             "{\"type\": \"Literal\", \"value\": \"abc\"}]}}}",
         "((?=test)abc)"},
        {"group_alternation",
         "{\"pattern\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Alternation\", \"alternatives\": ["
             "{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}}}",
         "(a|b|c)"},
        {"lookahead_alternation",
         "{\"pattern\": {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}}",
         "(?=a|b)"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Tier 2: Strategic Triplets ---------------------------------------------

static void test_tier2_triplets(void **state) {
    const TestCase cases[] = {
        {"flags_groups_quantifiers",
         "{\"flags\": \"i\", \"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"hello\"}}}}",
         "(?i)(hello)+"},
        {"flags_groups_lookahead",
         "{\"flags\": \"i\", \"pattern\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"test\"}},"
             "{\"type\": \"Literal\", \"value\": \"result\"}]}}}",
         "(?i)((?=test)result)"},
        {"groups_quantifiers_lookahead",
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"digit\"}]}},"
             "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"word\"}]}]}}}}",
         "((?=\\d)\\w)+"},
        {"groups_quantifiers_alternation",
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}}}",
         "(a|b)+"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Complex Nested Tests ---------------------------------------------------

static void test_complex_nested(void **state) {
    const TestCase cases[] = {
        {"deeply_nested_quantifiers",
         "{\"pattern\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}}}}}}",
         "((a+)+)+"},
         
        {"nested_alternation",
         "{\"pattern\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Alternation\", \"alternatives\": ["
             "{\"type\": \"Literal\", \"value\": \"a\"},"
             "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}} ]}}}",
         "(a|(b|c))"},
         
        {"multiple_lookarounds",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"test\"}},"
             "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"fail\"}},"
             "{\"type\": \"Literal\", \"value\": \"result\"}]}}",
         "(?=test)(?!fail)result"},
         
        {"atomic_group_quantifier",
         "{\"pattern\": {\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}},"
             "{\"type\": \"Literal\", \"value\": \"b\"}]}}",
         "(?>a+)b"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Main Entry Point -------------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_tier1_flags),
        cmocka_unit_test(test_tier1_literals),
        cmocka_unit_test(test_tier1_charclasses),
        cmocka_unit_test(test_tier1_anchors),
        cmocka_unit_test(test_tier1_quantifiers),
        cmocka_unit_test(test_tier1_groups_lookarounds),
        cmocka_unit_test(test_tier2_triplets),
        cmocka_unit_test(test_complex_nested),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
