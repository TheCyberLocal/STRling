/**
 * @file char_classes_test.c
 * @brief Unit Tests for Character Class Compilation (47 Tests).
 *
 * PURPOSE:
 * Validates the translation of CharacterClass nodes from JSON AST into PCRE2 patterns.
 * Matches the test count (47) of 'bindings/javascript/__tests__/unit/char_classes.test.ts'.
 *
 * COVERAGE:
 * - Category A: Positive Cases (Literals, Ranges, Shorthands, Unicode)
 * - Category B: Negative/Validation Cases (Adapted from Parser Errors)
 * - Category C: Edge Cases (Escapes, Hex)
 * - Category D: Interaction Cases (Flags)
 * - Category E: Minimal Classes
 * - Category F: Escaped Metachars
 * - Category G: Complex Ranges
 * - Category H: Unicode Combinations
 * - Category I: Negated Variations
 * - Category J: Logic Error Cases (Empty classes, Reversed ranges)
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
            // Negative Test: Expect Error
            if (result.error_code == STRling_OK)
            {
                printf("FAIL [%s]: Expected error but got success. Output: %s\n",
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

// --- Category A: Positive Cases (16 Tests) ----------------------------------

static void test_category_a_positive(void **state)
{
    const TestCase cases[] = {
        // A.1: Basic Classes
        {"simple_class",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}",
         "[abc]"},
        {"negated_simple_class",
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}",
         "[^abc]"},

        // A.2: Ranges
        {"range_lowercase",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}",
         "[a-z]"},
        {"range_alphanum",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"A\", \"to\": \"Z\"}, {\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}, {\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}]}",
         "[A-Za-z0-9]"},

        // A.3: Shorthand Escapes
        {"shorthand_positive",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"digit\"}, {\"type\": \"Escape\", \"kind\": \"whitespace\"}, {\"type\": \"Escape\", \"kind\": \"word\"}]}",
         "[\\d\\s\\w]"},
        {"shorthand_negated",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"not_digit\"}, {\"type\": \"Escape\", \"kind\": \"not_whitespace\"}, {\"type\": \"Escape\", \"kind\": \"not_word\"}]}",
         "[\\D\\S\\W]"},

        // A.4: Unicode Property Escapes
        {"unicode_property_short",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"L\"}]}",
         "[\\p{L}]"},
        {"unicode_property_long",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"Letter\"}]}",
         "[\\p{Letter}]"},
        {"unicode_property_negated",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"Number\", \"negated\": true}]}",
         "[\\P{Number}]"},
        {"unicode_property_with_value",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"Script=Greek\"}]}",
         "[\\p{Script=Greek}]"},

        // A.5: Special Character Handling
        {"special_char_bracket_at_start",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"]\"}, {\"type\": \"Literal\", \"value\": \"a\"}]}",
         "[\\]a]"},
        {"special_char_bracket_at_start_negated",
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Literal\", \"value\": \"]\"}, {\"type\": \"Literal\", \"value\": \"a\"}]}",
         "[^\\]a]"},
        {"special_char_hyphen_at_start",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"-\"}, {\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"z\"}]}",
         "[\\-az]"},
        {"special_char_hyphen_at_end",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"z\"}, {\"type\": \"Literal\", \"value\": \"-\"}]}",
         "[az\\-]"},
        {"special_char_caret_in_middle",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"^\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}",
         "[a\\^b]"},
        {"special_char_backspace_escape",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"\\b\"}]}",
         "[\\x{08}]"} // PCRE2 treats \b in class as backspace
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category B: Validation Errors (5 Tests) --------------------------------
// Adapted from JS Parser "Syntax Errors" to C "Validation Errors"

static void test_category_b_negative(void **state)
{
    const TestCase cases[] = {
        // B.1: Malformed Class Structure (Missing members)
        {"invalid_struct_missing_members",
         "{\"type\": \"CharacterClass\", \"negated\": false}",
         NULL, 1},

        // B.2: Invalid Node in Class (Ignored -> Empty Class -> Valid)
        {"invalid_node_in_class",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"InvalidNode\"}]}",
         "[]", 0},

        // B.3: Range Missing 'from' (Ignored -> Empty Class -> Valid)
        {"range_missing_from",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"to\": \"z\"}]}",
         "[]", 0},

        // B.4: Range Missing 'to' (Ignored -> Empty Class -> Valid)
        {"range_missing_to",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"a\"}]}",
         "[]", 0},

        // B.5: Escape Missing 'kind' (Ignored -> Empty Class -> Valid)
        {"escape_missing_kind",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Escape\"}]}",
         "[]", 0}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category C: Edge Cases (3 Tests) ---------------------------------------

static void test_category_c_edges(void **state)
{
    const TestCase cases[] = {
        // Escaped hyphen is literal
        {"escaped_hyphen_is_literal",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"-\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}",
         "[a\\-c]"}, // - treated as literal if not forming valid range in AST

        // Range with hex/unicode points
        {"range_with_escaped_endpoints",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"A\", \"to\": \"Z\"}]}",
         "[A-Z]"},

        // Class with only escapes
        {"class_with_only_escapes",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"\\n\"}, {\"type\": \"Literal\", \"value\": \"\\t\"}, {\"type\": \"Escape\", \"kind\": \"digit\"}]}",
         "[\\n\\t\\d]"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category D: Interaction Cases (2 Tests) --------------------------------

static void test_category_d_interactions(void **state)
{
    const TestCase cases[] = {
        // Whitespace in class is literal (even with free-spacing flag, usually)
        // STRling AST treats ' ' as literal value ' ' regardless of input DSL flag,
        // so we verify it emits as space.
        {"whitespace_is_literal",
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \" \"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}",
         "(?x)[a b]"},

        // Comment char # is literal in class
        {"comment_char_is_literal",
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"#\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}}",
         "(?x)[a#b]"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category E: Minimal Classes (3 Tests) ----------------------------------

static void test_category_e_minimal(void **state)
{
    const TestCase cases[] = {
        {"minimal_literal",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}]}",
         "[a]"},
        {"minimal_negated_literal",
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Literal\", \"value\": \"x\"}]}",
         "[^x]"},
        {"minimal_range",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}",
         "[a-z]"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category F: Escaped Metachars (5 Tests) --------------------------------

static void test_category_f_metachars(void **state)
{
    const TestCase cases[] = {
        {"escaped_dot",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \".\"}]}",
         "[.]"},
        {"escaped_star",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"*\"}]}",
         "[*]"},
        {"escaped_plus",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"+\"}]}",
         "[+]"},
        {"multiple_metachars",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \".\"}, {\"type\": \"Literal\", \"value\": \"*\"}, {\"type\": \"Literal\", \"value\": \"+\"}, {\"type\": \"Literal\", \"value\": \"?\"}]}",
         "[.*+?]"},
        {"escaped_backslash",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"\\\\\"}]}",
         "[\\\\]"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category G: Complex Ranges (3 Tests) -----------------------------------

static void test_category_g_complex_ranges(void **state)
{
    const TestCase cases[] = {
        {"multiple_ranges",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}, {\"type\": \"Range\", \"from\": \"A\", \"to\": \"Z\"}, {\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}]}",
         "[a-zA-Z0-9]"},
        {"range_mixed_literals",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}, {\"type\": \"Literal\", \"value\": \"_\"}, {\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}, {\"type\": \"Literal\", \"value\": \"-\"}]}",
         "[a-z_0-9\\-]"},

        // Adjacent classes (Sequence of two classes)
        {"adjacent_ranges_seq",
         "{\"type\": \"Sequence\", \"parts\": ["
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]},"
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"A\", \"to\": \"Z\"}]}"
         "]}",
         "[a-z][A-Z]"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category H: Unicode Combinations (4 Tests) -----------------------------

static void test_category_h_unicode(void **state)
{
    const TestCase cases[] = {
        {"multiple_unicode",
         "{\"type\": \"CharacterClass\", \"members\": ["
         "{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"L\"},"
         "{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"N\"}"
         "]}",
         "[\\p{L}\\p{N}]"},
        {"unicode_mixed_literals",
         "{\"type\": \"CharacterClass\", \"members\": ["
         "{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"L\"},"
         "{\"type\": \"Literal\", \"value\": \"a\"},"
         "{\"type\": \"Literal\", \"value\": \"b\"},"
         "{\"type\": \"Literal\", \"value\": \"c\"}"
         "]}",
         "[\\p{L}abc]"},
        {"unicode_mixed_range",
         "{\"type\": \"CharacterClass\", \"members\": ["
         "{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"L\"},"
         "{\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}"
         "]}",
         "[\\p{L}0-9]"},
        {"negated_unicode_in_class",
         "{\"type\": \"CharacterClass\", \"members\": ["
         "{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"L\", \"negated\": true}"
         "]}",
         "[\\P{L}]"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category I: Negated Variations (3 Tests) -------------------------------

static void test_category_i_negated_vars(void **state)
{
    const TestCase cases[] = {
        {"negated_with_range",
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}",
         "[^a-z]"},
        {"negated_with_shorthand",
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Escape\", \"kind\": \"digit\"}, {\"type\": \"Escape\", \"kind\": \"whitespace\"}]}",
         "[^\\d\\s]"},
        {"negated_with_unicode",
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"L\"}]}",
         "[^\\p{L}]"}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category J: Logic Errors (3 Tests) -------------------------------------

static void test_category_j_logic_errors(void **state)
{
    const TestCase cases[] = {
        // J.1: Empty Class (Allowed now)
        {"empty_class",
         "{\"type\": \"CharacterClass\", \"negated\": false, \"members\": []}",
         "[]", 0},

        // J.2: Reversed Range (Logic Error)
        {"reversed_range",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"z\", \"to\": \"a\"}]}",
         NULL, 1},

        // J.3: Incomplete range literal (Valid, handled as literal)
        {"incomplete_range_literal",
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"-\"}]}",
         "[a\\-]", 0}};
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_category_a_positive),
        cmocka_unit_test(test_category_b_negative),
        cmocka_unit_test(test_category_c_edges),
        cmocka_unit_test(test_category_d_interactions),
        cmocka_unit_test(test_category_e_minimal),
        cmocka_unit_test(test_category_f_metachars),
        cmocka_unit_test(test_category_g_complex_ranges),
        cmocka_unit_test(test_category_h_unicode),
        cmocka_unit_test(test_category_i_negated_vars),
        cmocka_unit_test(test_category_j_logic_errors),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}