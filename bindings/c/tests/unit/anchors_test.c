/**
 * @file anchors_test.c
 * @brief Unit Tests for Anchor Compilation (34 Tests).
 *
 * PURPOSE:
 * Validates the translation of Anchor nodes from the JSON AST into PCRE2 patterns.
 * Matches the test count (34) and logic of 'bindings/javascript/__tests__/unit/anchors.test.ts'.
 *
 * COVERAGE:
 * - Category A: Positive Cases (Core & Extension Anchors)
 * - Category C: Edge Cases (Positioning, Combinations)
 * - Category D: Interaction Cases (Flags, Groups, Lookarounds)
 * - Category E: Complex Sequences (Quantifiers, Multiple Anchors)
 * - Category F: Alternation
 * - Category G: Atomic Groups
 * - Category H: Word Boundary Edge Cases
 * - Category I: Multiple Anchor Types (Mixed)
 * - Category J: Negative Cases (Quantified Anchors)
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
    int expected_error;        // For negative tests (1=expect error, 0=expect success)
} TestCase;

static void run_test_batch(void **state, const TestCase *cases, size_t count)
{
    (void)state;

    for (size_t i = 0; i < count; i++)
    {
        // printf("Running %s...\n", cases[i].id); // Uncomment for debug

        strling_result_t result = strling_compile_compat(cases[i].json_input, NULL);

        if (cases[i].expected_error)
        {
            // Negative Test: Expect Error
            if (result.error_code == STRling_OK)
            {
                printf("FAIL [%s]: Expected error but got success. Pattern: %s\n",
                       cases[i].id, result.pcre2_pattern);
            }
            assert_int_not_equal(result.error_code, STRling_OK);
        }
        else
        {
            // Positive Test: Expect Success
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

// --- Category A: Positive Cases (6 Tests) -----------------------------------

static void test_category_a_positive_cases(void **state)
{
    const TestCase cases[] = {
        // A.1: Core Line Anchors
        {"A1_start",
         "{\"type\": \"Anchor\", \"at\": \"Start\"}",
         "^"},
        {"A2_end",
         "{\"type\": \"Anchor\", \"at\": \"End\"}",
         "$"},

        // A.2: Core Word Boundary Anchors
        {"A3_word_boundary",
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}",
         "\\b"},
        {"A4_not_word_boundary",
         "{\"type\": \"Anchor\", \"at\": \"NotWordBoundary\"}",
         "\\B"},

        // A.3: Absolute Anchors
        {"A5_absolute_start",
         "{\"type\": \"Anchor\", \"at\": \"AbsoluteStart\"}",
         "\\A"},
        {"A6_end_before_newline",
         "{\"type\": \"Anchor\", \"at\": \"EndBeforeFinalNewline\"}",
         "\\Z"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category C: Edge Cases (4 Tests) ---------------------------------------

static void test_category_c_edge_cases(void **state)
{
    const TestCase cases[] = {
        // Sequence of anchors only
        {"C1_seq_anchors",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Anchor\", \"at\": \"Start\"},"
         "{\"type\": \"Anchor\", \"at\": \"AbsoluteStart\"},"
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
         "{\"type\": \"Anchor\", \"at\": \"End\"}]}",
         "^\\A\\b$"},

        // Position: At Start (^a)
        {"C2_pos_start",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"a\"}]}",
         "^a"},

        // Position: In Middle (a\bb)
        {"C3_pos_middle",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Literal\", \"value\": \"a\"},"
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
         "{\"type\": \"Literal\", \"value\": \"b\"}]}",
         "a\\bb"},

        // Position: At End (ab$)
        {"C4_pos_end",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"ab\"}, {\"type\": \"Anchor\", \"at\": \"End\"}]}",
         "ab$"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category D: Interaction Cases (5 Tests) --------------------------------

static void test_category_d_interactions(void **state)
{
    const TestCase cases[] = {
        // Flags interaction (should verify ^ emits ^ even with m flag)
        {"D1_flag_multiline",
         "{\"flags\": \"m\", \"pattern\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Anchor\", \"at\": \"End\"}]}}",
         "(?m)^a$"},

        // Inside Capturing Group (^a)
        {"D2_in_group",
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"a\"}]}}",
         "(^a)"},

        // Inside Non-Capturing Group (?:a\b)
        {"D3_in_non_capturing",
         "{\"type\": \"Group\", \"capturing\": false, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Anchor\", \"at\": \"WordBoundary\"}]}}",
         "(?:a\\b)"},

        // Inside Lookahead (?=a$)
        {"D4_in_lookahead",
         "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Anchor\", \"at\": \"End\"}]}}",
         "(?=a$)"},

        // Inside Lookbehind (?<=^a)
        {"D5_in_lookbehind",
         "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": false, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"a\"}]}}",
         "(?<=^a)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category E: Complex Sequences (4 Tests) --------------------------------

static void test_category_e_complex(void **state)
{
    const TestCase cases[] = {
        // Between quantified atoms (a*^b+)
        {"E1_between_quantifiers",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}},"
         "{\"type\": \"Anchor\", \"at\": \"Start\"},"
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"b\"}}]}",
         "a*^b+"},

        // After quantified group ((ab)*$)
        {"E2_after_quantified_group",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"ab\"}}},"
         "{\"type\": \"Anchor\", \"at\": \"End\"}]}",
         "(ab)*$"},

        // Multiple same anchors (^^)
        {"E3_double_start",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Anchor\", \"at\": \"Start\"}]}",
         "^^"},

        // Multiple end anchors ($$)
        {"E4_double_end",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"End\"}, {\"type\": \"Anchor\", \"at\": \"End\"}]}",
         "$$"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category F: Alternation (3 Tests) --------------------------------------

static void test_category_f_alternation(void **state)
{
    const TestCase cases[] = {
        // Anchor in one branch (^a|b$)
        {"F1_alt_branch",
         "{\"type\": \"Alternation\", \"alternatives\": ["
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"a\"}]},"
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Anchor\", \"at\": \"End\"}]}]}",
         "^a|b$"},

        // Group alternation (^|$)
        {"F2_group_alt",
         "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Alternation\", \"alternatives\": ["
         "{\"type\": \"Anchor\", \"at\": \"Start\"},"
         "{\"type\": \"Anchor\", \"at\": \"End\"}]}}",
         "(^|$)"},

        // Word boundary in alternation (\ba|\bb)
        {"F3_boundary_alt",
         "{\"type\": \"Alternation\", \"alternatives\": ["
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}, {\"type\": \"Literal\", \"value\": \"a\"}]},"
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}]}",
         "\\ba|\\bb"} // Normalized output. Note: Input \bb might act as backspace in CharClass, but here it's an anchor in sequence.
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category G: Atomic Groups (3 Tests) ------------------------------------

static void test_category_g_atomic(void **state)
{
    const TestCase cases[] = {
        // (?>^a)
        {"G1_atomic_start",
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"a\"}]}}",
         "(?>^a)"},

        // (?>a$)
        {"G2_atomic_end",
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Anchor\", \"at\": \"End\"}]}}",
         "(?>a$)"},

        // (?>\ba)
        {"G3_atomic_boundary",
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}, {\"type\": \"Literal\", \"value\": \"a\"}]}}",
         "(?>\\ba)"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category H: Word Boundary Edge Cases (3 Tests) -------------------------

static void test_category_h_boundary_edges(void **state)
{
    const TestCase cases[] = {
        // \b.\b
        {"H1_boundary_dot",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}, {\"type\": \"Dot\"}, {\"type\": \"Anchor\", \"at\": \"WordBoundary\"}]}",
         "\\b.\\b"},

        // \b\d\b
        {"H2_boundary_digit",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"digit\"}]},"
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"}]}",
         "\\b[\\d]\\b"}, // Assuming \d emits as \d or [0-9] depending on implementation. Standard is \d.

        // \Ba\B
        {"H3_not_boundary",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"NotWordBoundary\"}, {\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Anchor\", \"at\": \"NotWordBoundary\"}]}",
         "\\Ba\\B"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category I: Multiple Types & Misc (4 Tests) ----------------------------

static void test_category_i_misc(void **state)
{
    const TestCase cases[] = {
        // ^abc$
        {"I1_start_end",
         "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Anchor\", \"at\": \"Start\"}, {\"type\": \"Literal\", \"value\": \"abc\"}, {\"type\": \"Anchor\", \"at\": \"End\"}]}",
         "^abc$"},

        // \A^abc$\z (Tests 30 & 31 equivalent - verifying \z handling)
        // Note: JS tests 30 & 31 reject \z as "Unknown escape".
        // The C library (libstrling) targets PCRE2 where \z is valid (AbsoluteEnd).
        // We test for Success here to verify the library supports the full PCRE2 spec.
        {"I2_complex_absolute",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Anchor\", \"at\": \"AbsoluteStart\"},"
         "{\"type\": \"Anchor\", \"at\": \"Start\"},"
         "{\"type\": \"Literal\", \"value\": \"abc\"},"
         "{\"type\": \"Anchor\", \"at\": \"End\"},"
         "{\"type\": \"Anchor\", \"at\": \"AbsoluteEnd\"}]}", // \z
         "\\A^abc$\\z"},

        // Just \z
        {"I3_absolute_end_only",
         "{\"type\": \"Anchor\", \"at\": \"AbsoluteEnd\"}",
         "\\z"},

        // ^\ba\b$
        {"I4_all_mixed",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"Anchor\", \"at\": \"Start\"},"
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
         "{\"type\": \"Literal\", \"value\": \"a\"},"
         "{\"type\": \"Anchor\", \"at\": \"WordBoundary\"},"
         "{\"type\": \"Anchor\", \"at\": \"End\"}]}",
         "^\\ba\\b$"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category J: Negative Cases (2 Tests) -----------------------------------

static void test_category_j_negative(void **state)
{
    const TestCase cases[] = {
        // Quantified Anchor: ^* (Invalid)
        // Attempting to quantify an anchor should raise a validation error.
        {"J1_quantified_start",
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Anchor\", \"at\": \"Start\"}}",
         NULL, 1}, // Expect Error

        // Quantified Anchor: $+ (Invalid)
        {"J2_quantified_end",
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Anchor\", \"at\": \"End\"}}",
         NULL, 1} // Expect Error
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_category_a_positive_cases),
        cmocka_unit_test(test_category_c_edge_cases),
        cmocka_unit_test(test_category_d_interactions),
        cmocka_unit_test(test_category_e_complex),
        cmocka_unit_test(test_category_f_alternation),
        cmocka_unit_test(test_category_g_atomic),
        cmocka_unit_test(test_category_h_boundary_edges),
        cmocka_unit_test(test_category_i_misc),
        cmocka_unit_test(test_category_j_negative),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
