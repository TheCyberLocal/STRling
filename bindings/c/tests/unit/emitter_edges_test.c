/**
 * @file emitter_edges_test.c
 * @brief Unit Tests for PCRE2 Emitter Edge Cases (36 Tests).
 *
 * PURPOSE:
 * Validates the logic of the PCRE2 emitter, focusing on escaping, optimizations,
 * grouping precedence, and extension features.
 * Matches the test count (36) of 'bindings/javascript/__tests__/unit/emitter_edges.test.ts'.
 *
 * COVERAGE:
 * - Helper Logic: Indirectly tested via minimal ASTs (Literals, Class Chars).
 * - Category A: Escaping Logic (Metachars).
 * - Category B: Shorthand Optimizations (\d, \D, \p{L}, etc.).
 * - Category C: Automatic Grouping (Precedence preservation).
 * - Category D: Flags and Directives.
 * - Category E: Extension Features (Atomic groups, Possessive quantifiers).
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
        strling_result_t result = strling_compile_compat(cases[i].json_input, NULL);
        
        if (result.error_code != STRling_OK) {
            printf("FAIL [%s]: Compilation error: %s\n", cases[i].id, result.error_message);
        }
        assert_int_equal(result.error_code, STRling_OK);
        assert_non_null(result.pcre2_pattern);
        
        if (strcmp(result.pcre2_pattern, cases[i].expected_pcre) != 0) {
            printf("FAIL [%s]:\n  Expected: '%s'\n  Got:      '%s'\n", 
                   cases[i].id, cases[i].expected_pcre, result.pcre2_pattern);
        }
        assert_string_equal(result.pcre2_pattern, cases[i].expected_pcre);
        
        strling_result_free_compat(&result);
    }
}

// --- Helper Tests (12 Tests) ------------------------------------------------
// Mapping internal helper tests to public API calls via minimal ASTs.

static void test_helper_literals(void **state) {
    const TestCase cases[] = {
        // _escapeLiteral(".") -> \.
        {"helper_lit_dot", "{\"type\": \"Literal\", \"value\": \".\"}", "\\."},
        // _escapeLiteral("\\") -> \\\\.
        {"helper_lit_backslash", "{\"type\": \"Literal\", \"value\": \"\\\\\"}", "\\\\"},
        // _escapeLiteral("[") -> \[
        {"helper_lit_lbracket", "{\"type\": \"Literal\", \"value\": \"[\"}", "\\["},
        // _escapeLiteral("{") -> \{
        {"helper_lit_lbrace", "{\"type\": \"Literal\", \"value\": \"{\"}", "\\{"},
        // _escapeLiteral("a") -> a
        {"helper_lit_plain", "{\"type\": \"Literal\", \"value\": \"a\"}", "a"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

static void test_helper_class_chars(void **state) {
    const TestCase cases[] = {
        // _escapeClassChar("]") -> [\]]
        {"helper_class_rbracket", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"]\"}]}", 
         "[\\]]"},
        // _escapeClassChar("\") -> [\\]
        {"helper_class_backslash", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"\\\\\"}]}", 
         "[\\\\]"},
        // _escapeClassChar("-") -> [\-]
        {"helper_class_hyphen", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"-\"}]}", 
         "[\\-]"},
        // _escapeClassChar("^") -> [\^]
        {"helper_class_caret", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"^\"}]}", 
         "[\\^]"},
        // _escapeClassChar("[") -> [[] (Unescaped in class)
        {"helper_class_lbracket", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"[\"}]}", 
         "[[]"},
        // _escapeClassChar(".") -> [.] (Unescaped in class)
        {"helper_class_dot", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \".\"}]}", 
         "[.]"},
        // _escapeClassChar("\n") -> [\n]
        {"helper_class_newline", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"\\n\"}]}", 
         "[\\n]"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category A: Escaping Logic (2 Tests) -----------------------------------

static void test_category_a_escaping(void **state) {
    const TestCase cases[] = {
        // Literal metachars: .^$|()?*+{}[] (metachars)
        {"escape_literal_metachars", 
         "{\"type\": \"Literal\", \"value\": \".^$|()?*+{}[]\\\\\"}", 
         "\\.\\^\\$\\|\\(\\)\\?\\*\\+\\{\\}\\[\\]\\\\"},
        
        // Class metachars: ]-^
        {"escape_class_metachars", 
         "{\"type\": \"CharacterClass\", \"members\": ["
            "{\"type\": \"Literal\", \"value\": \"]\"}, "
            "{\"type\": \"Literal\", \"value\": \"-\"}, "
            "{\"type\": \"Literal\", \"value\": \"^\"}]}", 
         "[\\]\\-\\^]"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category B: Shorthand Optimizations (7 Tests) --------------------------

static void test_category_b_shorthand(void **state) {
    const TestCase cases[] = {
        // \d
        {"positive_d_to_shorthand", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Escape\", \"kind\": \"digit\"}]}", 
         "\\d"},
        // \D (Negated \d)
        {"negated_d_to_D_shorthand", 
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Escape\", \"kind\": \"digit\"}]}", 
         "\\D"},
        // \p{L}
        {"positive_p_to_shorthand", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"L\"}]}", 
         "\\p{L}"},
        // \P{L} (Negated \p{L})
        {"negated_p_to_P_shorthand", 
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"L\"}]}", 
         "\\P{L}"},
        // \S (Not Whitespace)
        {"positive_neg_shorthand_S", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Escape\", \"kind\": \"not_whitespace\"}]}", 
         "\\S"},
        // \s (Negated \S -> \s)
        {"negated_neg_shorthand_S_to_s", 
         "{\"type\": \"CharacterClass\", \"negated\": true, \"members\": [{\"type\": \"Escape\", \"kind\": \"not_whitespace\"}]}", 
         "\\s"},
        // No optimization for multi-item class
        {"no_opt_multi_item", 
         "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Escape\", \"kind\": \"digit\"}, {\"type\": \"Literal\", \"value\": \"_\"}]}", 
         "[\\d_]"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category C: Automatic Grouping (6 Tests) -------------------------------

static void test_category_c_grouping(void **state) {
    const TestCase cases[] = {
        // (?:ab)* - Quantified multi-char literal
        {"quantified_multichar_literal", 
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"ab\"}}", 
         "(?:ab)*"},
        // a+ - Quantified single-item sequence
        {"quantified_single_item_sequence", 
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}]}}", 
         "a+"},
        // a(?:b|c) - Alternation in sequence
        {"alternation_in_sequence", 
         "{\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Literal\", \"value\": \"a\"}, "
             "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}]}", 
         "a(?:b|c)"},
        // [a]* - Quantified char class
        {"quantified_char_class", 
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"a\"}]}}", 
         "[a]*"},
        // .+ - Quantified dot
        {"quantified_dot", 
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Dot\"}}", 
         ".+"},
        // (a)? - Quantified group
        {"quantified_group", 
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": {\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}}", 
         "(a)?"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category D: Flags and Directives (5 Tests) -----------------------------

static void test_category_d_flags(void **state) {
    const TestCase cases[] = {
        // (?im)
        {"im_flags", 
         "{\"flags\": \"im\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?im)a"},
        // (?sux)
        {"sux_flags", 
         "{\"flags\": \"sux\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?sux)a"},
        // Default flags (empty)
        {"default_flags", 
         "{\"flags\": \"\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "a"},
        // No flags object
        {"no_flags_object", 
         "{\"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "a"},
        // Named group and backref: (?<x>a)\k<x>
        {"named_group_backref", 
         "{\"type\": \"Sequence\", \"parts\": ["
             "{\"type\": \"Group\", \"capturing\": true, \"name\": \"x\", \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}},"
             "{\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"x\"}]}", 
         "(?<x>a)\\k<x>"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category E: Extension Features (4 Tests) -------------------------------

static void test_category_e_extensions(void **state) {
    const TestCase cases[] = {
        // Atomic group: (?>a+)
        {"atomic_group", 
         "{\"type\": \"Group\", \"atomic\": true, \"expression\": "
            "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}}", 
         "(?>a+)"},
        // Possessive star: a*+
        {"possessive_star", 
         "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "a*+"},
        // Possessive plus on empty class: []++
        {"possessive_plus", 
         "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"possessive\": true, \"target\": {\"type\": \"CharacterClass\", \"members\": []}}", 
         "[]++"},
        // Absolute Start: \A
        {"absolute_start_anchor", 
         "{\"type\": \"Anchor\", \"at\": \"AbsoluteStart\"}", 
         "\\A"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_helper_literals),
        cmocka_unit_test(test_helper_class_chars),
        cmocka_unit_test(test_category_a_escaping),
        cmocka_unit_test(test_category_b_shorthand),
        cmocka_unit_test(test_category_c_grouping),
        cmocka_unit_test(test_category_d_flags),
        cmocka_unit_test(test_category_e_extensions),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}