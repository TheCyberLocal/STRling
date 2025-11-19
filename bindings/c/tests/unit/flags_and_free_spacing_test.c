/**
 * @file flags_and_free_spacing_test.c
 * @brief Unit Tests for Flags and Free-Spacing Mode (15 Tests).
 *
 * PURPOSE:
 * Validates that the library correctly parses flag strings from the JSON input
 * and emits the correct PCRE2 modifier prefixes. It also verifies that the
 * 'x' (Extended) flag triggers necessary escaping in the emitter to preserve
 * the semantics of Literal nodes (e.g., escaping ' ' to '\ ' so it isn't ignored).
 *
 * MATCHING TS SUITE:
 * bindings/javascript/__tests__/unit/flags_and_free_spacing.test.ts
 *
 * COVERAGE:
 * - Category A: Single Flags (i, m, s, x) - 4 tests
 * - Category B: Combinations & Parsing (Separators, Padding) - 4 tests
 * - Category C: Edge Cases (Duplicates, Empty) - 3 tests
 * - Category D: Free-Spacing Interactions (Literals vs Classes) - 4 tests
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

// --- Category A: Single Flags (4 Tests) -------------------------------------

static void test_category_a_single_flags(void **state) {
    const TestCase cases[] = {
        // 1. Ignore Case (i)
        {"flag_i", 
         "{\"flags\": \"i\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?i)a"},
         
        // 2. Multiline (m)
        {"flag_m", 
         "{\"flags\": \"m\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?m)a"},
         
        // 3. Dot All (s)
        {"flag_s", 
         "{\"flags\": \"s\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?s)a"},

        // 4. Extended (x)
        {"flag_x", 
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?x)a"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category B: Combinations & Parsing (4 Tests) ---------------------------

static void test_category_b_combinations(void **state) {
    const TestCase cases[] = {
        // 5. Combined im
        {"flags_im", 
         "{\"flags\": \"im\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?im)a"},

        // 6. All Flags imsx
        {"flags_all_imsx", 
         "{\"flags\": \"imsx\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?imsx)a"},

        // 7. Separators (Space)
        {"flags_separator_space", 
         "{\"flags\": \"i m\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?im)a"},

        // 8. Separators (Comma)
        {"flags_separator_comma", 
         "{\"flags\": \"s, x\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?sx)a"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category C: Edge Cases (3 Tests) ---------------------------------------

static void test_category_c_edges(void **state) {
    const TestCase cases[] = {
        // 9. Padding Whitespace
        {"flags_padded", 
         "{\"flags\": \"  i  \", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?i)a"},

        // 10. Duplicate Flags (ii -> i)
        {"flags_duplicate", 
         "{\"flags\": \"ii\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "(?i)a"},

        // 11. Empty String Flags
        {"flags_empty_string", 
         "{\"flags\": \"\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}", 
         "a"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

// --- Category D: Free-Spacing Interactions (4 Tests) ------------------------
// Verifies that the emitter appropriately handles literals when 'x' mode is active.

static void test_category_d_free_spacing(void **state) {
    const TestCase cases[] = {
        // 12. x flag with space in Literal
        // Input AST says "match a space". Since 'x' mode ignores unescaped spaces,
        // the emitter MUST escape it to '\ ' to preserve the AST's intent.
        {"x_literal_space_escaped", 
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"Literal\", \"value\": \" \"}}", 
         "(?x)\\ "}, 

        // 13. x flag with hash in Literal
        // Hashes start comments in x mode. Emitter MUST escape it to '\#'.
        {"x_literal_hash_escaped", 
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"Literal\", \"value\": \"#\"}}", 
         "(?x)\\#"},

        // 14. x flag with space in Character Class
        // Spaces are literal inside classes even in x mode. Emitter should NOT escape.
        {"x_class_space_preserved", 
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \" \"}]}}", 
         "(?x)[ ]"},

        // 15. x flag with hash in Character Class
        // Hashes are literal inside classes. Emitter should NOT escape.
        {"x_class_hash_preserved", 
         "{\"flags\": \"x\", \"pattern\": {\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Literal\", \"value\": \"#\"}]}}", 
         "(?x)[#]"}
    };
    run_test_batch(state, cases, sizeof(cases) / sizeof(cases[0]));
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_category_a_single_flags),
        cmocka_unit_test(test_category_b_combinations),
        cmocka_unit_test(test_category_c_edges),
        cmocka_unit_test(test_category_d_free_spacing),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}