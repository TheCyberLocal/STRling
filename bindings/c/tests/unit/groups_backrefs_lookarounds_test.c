/**
 * @file groups_backrefs_lookarounds_test.c
 * @brief Unit Tests for Groups, Backreferences, and Lookarounds (51 Tests).
 *
 * PURPOSE:
 * Validates the translation of grouping constructs and assertions.
 * Matches the test count (51) of 'bindings/javascript/__tests__/unit/groups_backrefs_lookarounds.test.ts'.
 *
 * COVERAGE:
 * - Category A: Capturing Groups (Basic, Nested, Interaction)
 * - Category B: Non-Capturing Groups (Basic, Optimization)
 * - Category C: Named Groups (Definition, Mixed)
 * - Category D: Atomic Groups (Syntax)
 * - Category E: Numeric Backreferences (Valid, Logic)
 * - Category F: Named Backreferences (Valid, Logic)
 * - Category G: Lookaheads (Positive, Negative)
 * - Category H: Lookbehinds (Positive, Negative)
 * - Category I: Complex/Integration (Combinations)
 * - Category J: Validation Errors (Invalid references)
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

typedef struct
{
    const char *id;
    const char *json_input;
    const char *expected_pcre; // For positive tests
    int expected_error;        // For negative tests (1=expect error)
} TestCase;

static void run_test_batch(void **state, const TestCase *cases, size_t count)
{
    (void)state;

    for (size_t i = 0; i < count; i++)
    {
        strling_result_t result = strling_compile_compat(cases[i].json_input, NULL);

        if (cases[i].expected_error)
        {
            if (result.error_code == STRling_OK)
            {
                printf("FAIL [%s]: Expected error but got success. Output: %s\n",
                       cases[i].id, result.pcre2_pattern);
            }
            assert_int_not_equal(result.error_code, STRling_OK);
        }
        else
        {
            if (result.error_code != STRling_OK)
            {
                printf("FAIL [%s]: Compilation error: %s\n", cases[i].id, result.error_message);
            }
            assert_int_equal(result.error_code, STRling_OK);
            assert_non_null(result.pcre2_pattern);

            if (strcmp(result.pcre2_pattern, cases[i].expected_pcre) != 0)
            {
                printf("FAIL [%s]:\n  Expected: '%s'\n  Got:      '%s'\n",
                       cases[i].id, cases[i].expected_pcre, result.pcre2_pattern);
            }
            assert_string_equal(result.pcre2_pattern, cases[i].expected_pcre);
        }

        strling_result_free_compat(&result);
    }
}

// --- Category A: Capturing Groups (5 Tests) ---------------------------------

static void test_category_a_capturing(void **state)
{
    const TestCase cases[] = {
        {"cap_basic",
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(a)"},
        {"cap_nested",
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}}",
         "((b))"},
        {"cap_sequence",
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}",
         "(ab)"},
        {"cap_empty",
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": []}}",
         "()"}, // Valid empty group
        {"cap_quantified",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
         "(a)+"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category B: Non-Capturing Groups (5 Tests) -----------------------------

static void test_category_b_non_capturing(void **state)
{
    const TestCase cases[] = {
        {"nocap_basic",
         "{\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?:a)"},
        {"nocap_nested",
         "{\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}}",
         "(?:(?:b))"},
        {"nocap_inside_cap",
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"c\"}}}",
         "((?:c))"},
        {"cap_inside_nocap",
         "{\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"d\"}}}",
         "(?:(d))"},
        {"nocap_quantified",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"e\"}}}",
         "(?:e)?"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category C: Named Groups (6 Tests) -------------------------------------

static void test_category_c_named(void **state)
{
    const TestCase cases[] = {
        {"named_basic",
         "{\"type\": \"Group\", \"capturing\": true, \"name\": \"foo\", \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?<foo>a)"},
        {"named_nested_named",
         "{\"type\": \"Group\", \"capturing\": true, \"name\": \"outer\", \"expression\": {\"type\": \"Group\", \"capturing\": true, \"name\": \"inner\", \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}}",
         "(?<outer>(?<inner>b))"},
        {"named_with_underscore",
         "{\"type\": \"Group\", \"capturing\": true, \"name\": \"my_group\", \"expression\": {\"type\": \"Literal\", \"value\": \"c\"}}",
         "(?<my_group>c)"},
        {"named_with_digits",
         "{\"type\": \"Group\", \"capturing\": true, \"name\": \"group1\", \"expression\": {\"type\": \"Literal\", \"value\": \"d\"}}",
         "(?<group1>d)"},
        {"named_inside_nocap",
         "{\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Group\", \"capturing\": true, \"name\": \"x\", \"expression\": {\"type\": \"Literal\", \"value\": \"e\"}}}",
         "(?:(?<x>e))"},
        {"named_sequence",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Group\", \"capturing\": true, \"name\": \"a\", \"expression\": {\"type\": \"Literal\", \"value\": \"1\"}}, {\"type\": \"Group\", \"capturing\": true, \"name\": \"b\", \"expression\": {\"type\": \"Literal\", \"value\": \"2\"}}]}",
         "(?<a>1)(?<b>2)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category D: Atomic Groups (4 Tests) ------------------------------------

static void test_category_d_atomic(void **state)
{
    const TestCase cases[] = {
        {"atomic_basic",
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?>a)"},
        {"atomic_nested_cap",
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}}",
         "(?>(b))"},
        {"atomic_quantified",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"c\"}}}",
         "(?>c)+"},
        {"atomic_complex",
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"b\"}}]}}",
         "(?>ab*)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category E: Numeric Backreferences (5 Tests) ---------------------------

static void test_category_e_numeric_backrefs(void **state)
{
    const TestCase cases[] = {
        {"backref_1",
         "{\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}",
         "\\1"},
        {"backref_99",
         "{\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 99}",
         "\\99"},
        {"backref_seq",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}, {\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}]}",
         "(a)\\1"},
        {"backref_relative",
         "{\"type\": \"BackReference\", \"kind\": \"relative\", \"ref\": -1}",
         "\\g{-1}"}, // PCRE2 relative syntax
        {"backref_nested",
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}]}}",
         "(a\\1)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category F: Named Backreferences (5 Tests) -----------------------------

static void test_category_f_named_backrefs(void **state)
{
    const TestCase cases[] = {
        {"named_ref_basic",
         "{\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"foo\"}",
         "\\k<foo>"},
        {"named_ref_defined",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Group\", \"capturing\": true, \"name\": \"foo\", \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}, {\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"foo\"}]}",
         "(?<foo>a)\\k<foo>"},
        {"named_ref_underscore",
         "{\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"my_val\"}",
         "\\k<my_val>"},
        {"named_ref_recursion",
         "{\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"recurse\"}",
         "\\k<recurse>"}, // Logic handled by engine, syntax verified here
        {"named_ref_inside_group",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Group\", \"capturing\": true, \"name\": \"x\", \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}, {\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"x\"}}]}",
         "(?<x>a)(?:\\k<x>)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category G: Lookaheads (6 Tests) ---------------------------------------

static void test_category_g_lookaheads(void **state)
{
    const TestCase cases[] = {
        {"lookahead_pos",
         "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?=a)"},
        {"lookahead_neg",
         "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}",
         "(?!b)"},
        {"lookahead_seq",
         "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}",
         "(?=ab)"},
        {"lookahead_nested",
         "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"c\"}}}",
         "(?=(?!c))"},
        {"lookahead_quantified_error",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
         "(?:(?=a))+"}, // Compiler usually wraps assertions in group if quantified
        {"lookahead_empty",
         "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Sequence\", \"parts\": []}}",
         "(?=)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category H: Lookbehinds (6 Tests) --------------------------------------

static void test_category_h_lookbehinds(void **state)
{
    const TestCase cases[] = {
        {"lookbehind_pos",
         "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(?<=a)"},
        {"lookbehind_neg",
         "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}",
         "(?<!b)"},
        {"lookbehind_fixed_length",
         "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": false, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}",
         "(?<=ab)"},
        {"lookbehind_nested_lookahead",
         "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": false, \"expression\": {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"c\"}}}",
         "(?<=(?=c))"},
        {"lookbehind_alternation",
         "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": false, \"expression\": {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}",
         "(?<=a|b)"},
        {"lookbehind_empty",
         "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": []}}",
         "(?<!)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category I: Integration (5 Tests) --------------------------------------

static void test_category_i_integration(void **state)
{
    const TestCase cases[] = {
        {"complex_nested_all",
         "{\"type\": \"Group\", \"capturing\": true, \"name\": \"all\", \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"start\"}}, {\"type\": \"Literal\", \"value\": \"body\"}, {\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"all\"}]}}",
         "(?<all>(?=start)body\\k<all>)"},
        {"alternation_groups",
         "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}, {\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}]}",
         "(a)|(?:b)"},
        {"quantified_named_group",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"name\": \"q\", \"expression\": {\"type\": \"Literal\", \"value\": \"x\"}}}",
         "(?<q>x)*"},
        {"atomic_lookbehind",
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
         "(?>(?<=a))"},
        {"multiple_backrefs",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}, {\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}, {\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}]}",
         "(a)\\1\\1"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category J: Validation Errors (4 Tests) --------------------------------

static void test_category_j_validation(void **state)
{
    const TestCase cases[] = {
        // Missing name in named group
        {"error_missing_name",
         "{\"type\": \"Group\", \"capturing\": true, \"name\": null, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}",
         "(a)", 0}, // Technically valid as unnamed capturing, so expect success or error depending on if code checks 'named' intent?
                    // Actually, AST usually implies Named if name field is present/checked.
                    // If name is NULL, it's just a capturing group.
                    // Let's test an invalid node structure instead.

        // Named backref missing name
        {"error_backref_no_name",
         "{\"type\": \"BackReference\", \"kind\": \"named\"}",
         NULL, 1}, // Expect error

        // Numbered backref 0 (usually invalid or whole match, STRling might reject as explicit ref)
        {"error_backref_0",
         "{\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 0}",
         NULL, 1}, // Expect error, \0 is octal or recurse, specific node usually ref > 0

        // Lookaround missing expression
        {"error_lookaround_no_expr",
         "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false}",
         NULL, 1}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_category_a_capturing),
        cmocka_unit_test(test_category_b_non_capturing),
        cmocka_unit_test(test_category_c_named),
        cmocka_unit_test(test_category_d_atomic),
        cmocka_unit_test(test_category_e_numeric_backrefs),
        cmocka_unit_test(test_category_f_named_backrefs),
        cmocka_unit_test(test_category_g_lookaheads),
        cmocka_unit_test(test_category_h_lookbehinds),
        cmocka_unit_test(test_category_i_integration),
        cmocka_unit_test(test_category_j_validation),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}