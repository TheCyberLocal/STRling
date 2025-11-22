/**
 * @file quantifiers_test.c
 * @brief Unit Tests for Quantifier Compilation (49 Tests).
 *
 * PURPOSE:
 * Validates the translation of Quantifier nodes from the JSON AST into PCRE2 patterns.
 * Matches the test count (49) of 'bindings/javascript/__tests__/unit/quantifiers.test.ts'.
 *
 * ADAPTATION NOTE:
 * The reference JS tests parse DSL strings. Since the C library accepts JSON AST,
 * 'Syntax Errors' (e.g. unterminated braces) are adapted into 'Validation Errors'
 * (e.g. missing fields or invalid values in the AST).
 *
 * COVERAGE:
 * - Category A: Positive Cases (18 tests: 6 forms * 3 modes)
 * - Category B: Negative/Validation Cases (3 tests)
 * - Category C: Edge Cases (5 tests)
 * - Category D: Interaction Cases (7 tests)
 * - Category E: Nested/Redundant (5 tests)
 * - Category F: Special Atoms (2 tests)
 * - Category G: Multiple Sequences (3 tests)
 * - Category H: Brace Edges (4 tests)
 * - Category I: Flag Interactions (2 tests)
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
    const char *expected_pcre;
    int expected_error; // 1 = expect error, 0 = expect success
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

// --- Category A: Positive Cases (18 Tests) ----------------------------------

static void test_category_a_star(void **state)
{
    const TestCase cases[] = {
        {"star_greedy", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a*"},
        {"star_lazy", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": false, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a*?"},
        {"star_possessive", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a*+"}};
    run_test_batch(state, cases, 3);
}

static void test_category_a_plus(void **state)
{
    const TestCase cases[] = {
        {"plus_greedy", "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a+"},
        {"plus_lazy", "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": false, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a+?"},
        {"plus_possessive", "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a++"}};
    run_test_batch(state, cases, 3);
}

static void test_category_a_optional(void **state)
{
    const TestCase cases[] = {
        {"opt_greedy", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a?"},
        {"opt_lazy", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": false, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a??"},
        {"opt_possessive", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a?+"}};
    run_test_batch(state, cases, 3);
}

static void test_category_a_exact(void **state)
{
    const TestCase cases[] = {
        {"exact_greedy", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": 3, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3}"},
        {"exact_lazy", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": 3, \"greedy\": false, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3}?"},
        {"exact_possessive", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": 3, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3}+"}};
    run_test_batch(state, cases, 3);
}

static void test_category_a_at_least(void **state)
{
    const TestCase cases[] = {
        {"at_least_greedy", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3,}"},
        {"at_least_lazy", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": null, \"greedy\": false, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3,}?"},
        {"at_least_possessive", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": null, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3,}+"}};
    run_test_batch(state, cases, 3);
}

static void test_category_a_range(void **state)
{
    const TestCase cases[] = {
        {"range_greedy", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": 5, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3,5}"},
        {"range_lazy", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": 5, \"greedy\": false, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3,5}?"},
        {"range_possessive", "{\"type\": \"Quantifier\", \"min\": 3, \"max\": 5, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{3,5}+"}};
    run_test_batch(state, cases, 3);
}

// --- Category B: Validation/Syntax Errors (3 Tests) -------------------------

static void test_category_b_validation(void **state)
{
    const TestCase cases[] = {
        // B.1: Min > Max
        {"val_min_gt_max", "{\"type\": \"Quantifier\", \"min\": 5, \"max\": 2, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", NULL, 1},

        // B.2: Negative Min
        {"val_neg_min", "{\"type\": \"Quantifier\", \"min\": -1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", NULL, 1},

        // B.3: Missing Min (Defaults to 0)
        {"val_missing_min", "{\"type\": \"Quantifier\", \"max\": 5, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{0,5}", 0}};
    run_test_batch(state, cases, 3);
}

// --- Category C: Edge Cases (5 Tests) ---------------------------------------

static void test_category_c_edges(void **state)
{
    const TestCase cases[] = {
        // C.1: Zero Exact 'a{0}'
        {"zero_exact", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 0, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{0}"},

        // C.2: Zero Range 'a{0,5}'
        {"zero_range", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 5, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{0,5}"},

        // C.3: Zero Min Open 'a{0,}' -> Same as *
        {"zero_min_open", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a*"},

        // C.4: Quantify Empty Group '(?:)*'
        {"quant_empty_group",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Sequence\", \"parts\": []}}}",
         "(?:)*"},

        // C.5: Quantifier before Anchor 'a?^'
        {"quant_before_anchor",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Anchor\", \"at\": \"Start\"}"
         "]}",
         "a?^"}};
    run_test_batch(state, cases, 5);
}

// --- Category D: Interaction Cases (7 Tests) --------------------------------

static void test_category_d_interactions(void **state)
{
    const TestCase cases[] = {
        // D.1: Precedence 'ab*'
        {"prec_sequence",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"b\"}}]}",
         "ab*"},

        // D.2: Quantify Shorthand '\d*'
        {"quant_shorthand",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Escape\", \"kind\": \"digit\"}]}}",
         "[\\d]*"},

        // D.3: Quantify Dot '.*'
        {"quant_dot",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Dot\"}}",
         ".*"},

        // D.4: Quantify Class '[a-z]*'
        {"quant_class",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}}",
         "[a-z]*"},

        // D.5: Quantify Group '(abc)*'
        {"quant_group",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"abc\"}}}",
         "(abc)*"},

        // D.6: Quantify Alternation '(?:a|b)+'
        {"quant_alt",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}}",
         "(?:a|b)+"},

        // D.7: Quantify Lookaround '(?=a)+' -> '(?:(?=a))+'
        {"quant_lookaround",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}}",
         "(?:(?=a))+"}};
    run_test_batch(state, cases, 7);
}

// --- Category E: Nested/Redundant (5 Tests) ---------------------------------

static void test_category_e_nested(void **state)
{
    const TestCase cases[] = {
        // E.1: (a*)*
        {"nested_star_star",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}}",
         "(a*)*"},

        // E.2: (a+)?
        {"nested_plus_opt",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}}",
         "(a+)?"},

        // E.3: (a*)+
        {"nested_star_plus",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}}",
         "(a*)+"},

        // E.4: (a?)*
        {"nested_opt_star",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}}",
         "(a?)*"},

        // E.5: (a{2,3}){1,2}
        {"nested_braces",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": 2, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Quantifier\", \"min\": 2, \"max\": 3, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}}",
         "(a{2,3}){1,2}"}};
    run_test_batch(state, cases, 5);
}

// --- Category F: Special Atoms (2 Tests) ------------------------------------

static void test_category_f_special(void **state)
{
    const TestCase cases[] = {
        // F.1: Quantified Backref '(a)\1*'
        {"quant_backref",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}}"
         "]}",
         "(a)\\1*"},

        // F.2: Multiple Backrefs '(a)(b)\1*\2+'
        {"quant_multi_backref",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}},"
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}},"
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 2}}"
         "]}",
         "(a)(b)\\1*\\2+"}};
    run_test_batch(state, cases, 2);
}

// --- Category G: Multiple Sequences (3 Tests) -------------------------------

static void test_category_g_sequences(void **state)
{
    const TestCase cases[] = {
        // G.1: a*b+c?
        {"seq_literals",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"b\"}},"
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"c\"}}"
         "]}",
         "a*b+c?"},

        // G.2: (ab)*(cd)+(ef)?
        {"seq_groups",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"ab\"}}},"
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"cd\"}}},"
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"ef\"}}}"
         "]}",
         "(ab)*(cd)+(ef)?"},

        // G.3: a*|b+
        {"seq_alt",
         "{\"type\": \"Alternation\", \"alternatives\": ["
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"b\"}}"
         "]}",
         "a*|b+"}};
    run_test_batch(state, cases, 3);
}

// --- Category H: Brace Edges (4 Tests) --------------------------------------

static void test_category_h_brace_edges(void **state)
{
    const TestCase cases[] = {
        // H.1: Exact One 'a{1}'
        {"brace_one", "{\"type\": \"Quantifier\", \"min\": 1, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{1}"},

        // H.2: Zero to One 'a{0,1}'
        {"brace_zero_one", "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a?"},

        // H.3: Alternation in Group '(a|b){2,3}'
        {"brace_alt_group",
         "{\"type\": \"Quantifier\", \"min\": 2, \"max\": 3, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}}",
         "(a|b){2,3}"},

        // H.4: Large Values 'a{100,200}'
        {"brace_large", "{\"type\": \"Quantifier\", \"min\": 100, \"max\": 200, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", "a{100,200}"}};
    run_test_batch(state, cases, 4);
}

// --- Category I: Flag Interactions (2 Tests) --------------------------------

static void test_category_i_flags(void **state)
{
    const TestCase cases[] = {
        // I.1: Free spacing, space ignored, * literal
        // Input AST: Literal("a"), Literal("*")
        {"flag_x_space_ignored",
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"*\"}]}}",
         "(?x)a\\*"},

        // I.2: Free spacing, escaped space quantified
        // Input AST: Quantifier(Literal(" "))
        {"flag_x_escaped_space",
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \" \"}}}",
         "(?x)\\ *"}};
    run_test_batch(state, cases, 2);
}

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_category_a_star),
        cmocka_unit_test(test_category_a_plus),
        cmocka_unit_test(test_category_a_optional),
        cmocka_unit_test(test_category_a_exact),
        cmocka_unit_test(test_category_a_at_least),
        cmocka_unit_test(test_category_a_range),
        cmocka_unit_test(test_category_b_validation),
        cmocka_unit_test(test_category_c_edges),
        cmocka_unit_test(test_category_d_interactions),
        cmocka_unit_test(test_category_e_nested),
        cmocka_unit_test(test_category_f_special),
        cmocka_unit_test(test_category_g_sequences),
        cmocka_unit_test(test_category_h_brace_edges),
        cmocka_unit_test(test_category_i_flags),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
