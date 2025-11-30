/**
 * @file us_phone_test.c
 * @brief Test for US Phone Number Pattern using Simply API
 *
 * This test validates the Simply API by constructing a US phone number
 * pattern using the fluent builder functions.
 * 
 * NOTE: The C binding currently compiles from JSON AST, not from the AST
 * data structures directly. This test validates that the Simply API can
 * construct the correct AST structure, then demonstrates the equivalent
 * JSON compilation to verify correctness.
 */

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>
#include <stdio.h>

#include "strling.h"
#include "strling_simply.h"
#include "../src/core/nodes.h"  /* For testing internal AST structure */

/**
 * Test: US Phone Number Pattern with Simply API - AST Construction
 * 
 * Pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
 * Example matches: 555-0199, 555.0199, 555 0199, 5550199
 * 
 * This test verifies that the Simply API can construct the AST correctly.
 * Since we don't have AST->JSON serialization yet, we validate the structure
 * by building it and then verifying it doesn't crash on cleanup.
 */
static void test_us_phone_simply_api_construction(void **state)
{
    (void)state; /* unused */

    /* Build pattern using Simply API */
    sl_pattern_t phone = sl_merge(7,
        sl_start(),
        sl_capture(sl_digit(3)),
        sl_may(sl_any_of("-. ")),
        sl_capture(sl_digit(3)),
        sl_may(sl_any_of("-. ")),
        sl_capture(sl_digit(4)),
        sl_end()
    );

    assert_non_null(phone);
    
    /* Verify the AST structure is correct */
    assert_int_equal(phone->type, AST_TYPE_SEQ);
    assert_int_equal(phone->u.seq.nparts, 7);
    
    /* Verify first element is Start anchor */
    assert_non_null(phone->u.seq.parts[0]);
    assert_int_equal(phone->u.seq.parts[0]->type, AST_TYPE_ANCHOR);
    
    /* Verify second element is a Group (capture) */
    assert_non_null(phone->u.seq.parts[1]);
    assert_int_equal(phone->u.seq.parts[1]->type, AST_TYPE_GROUP);
    assert_true(phone->u.seq.parts[1]->u.group.capturing);
    
    /* Verify last element is End anchor */
    assert_non_null(phone->u.seq.parts[6]);
    assert_int_equal(phone->u.seq.parts[6]->type, AST_TYPE_ANCHOR);

    /* Cleanup - single root free for the AST */
    strling_ast_node_free(phone);
}

/**
 * Test: US Phone Number Pattern - JSON Compilation Reference
 * 
 * This test verifies that the equivalent JSON AST compiles to the expected
 * PCRE2 pattern. This serves as the reference implementation that the
 * Simply API should match.
 * 
 * NOTE: The JSON is intentionally hardcoded rather than generated from the
 * Simply API AST because:
 * 1. It serves as a known-good reference pattern
 * 2. The C binding doesn't yet have AST->JSON serialization
 * 3. This validates that when AST->JSON is added, it produces the expected output
 */
static void test_us_phone_json_reference(void **state)
{
    (void)state; /* unused */

    /* The equivalent JSON AST for the Simply API pattern */
    const char* phone_json =
        "{\"type\":\"Sequence\",\"parts\":["
        "{\"type\":\"Anchor\",\"at\":\"Start\"},"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":3,\"max\":3,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Escape\",\"kind\":\"digit\"}]}}},"
        "{\"type\":\"Quantifier\",\"min\":0,\"max\":1,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Literal\",\"value\":\"-\"},{\"type\":\"Literal\",\"value\":\".\"},{\"type\":\"Literal\",\"value\":\" \"}]}},"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":3,\"max\":3,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Escape\",\"kind\":\"digit\"}]}}},"
        "{\"type\":\"Quantifier\",\"min\":0,\"max\":1,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Literal\",\"value\":\"-\"},{\"type\":\"Literal\",\"value\":\".\"},{\"type\":\"Literal\",\"value\":\" \"}]}},"
        "{\"type\":\"Group\",\"capturing\":true,\"body\":{\"type\":\"Quantifier\",\"min\":4,\"max\":4,\"mode\":\"Greedy\",\"target\":{\"type\":\"CharacterClass\",\"negated\":false,\"members\":[{\"type\":\"Escape\",\"kind\":\"digit\"}]}}},"
        "{\"type\":\"Anchor\",\"at\":\"End\"}]}";

    /* Compile JSON to PCRE2 */
    strling_result_t result = strling_compile_compat(phone_json, NULL);
    
    /* Verify compilation succeeded */
    if (result.error_code != STRling_OK) {
        printf("FAIL: Compilation error: %s\n", result.error_message);
    }
    assert_int_equal(result.error_code, STRling_OK);
    assert_non_null(result.pcre2_pattern);

    /* Expected output - C binding emits character classes slightly differently */
    const char* expected_pcre = "^([\\d]{3})[\\-. ]?([\\d]{3})[\\-. ]?([\\d]{4})$";
    
    if (strcmp(result.pcre2_pattern, expected_pcre) != 0) {
        printf("FAIL: Pattern mismatch.\nExpected: '%s'\nGot:      '%s'\n",
               expected_pcre, result.pcre2_pattern);
    }
    assert_string_equal(result.pcre2_pattern, expected_pcre);

    strling_result_free_compat(&result);
}

/**
 * Test: Memory Hygiene - Single Root Free
 * 
 * Verifies that all memory allocated by Simply API can be freed
 * with a single call to strling_ast_node_free on the root.
 */
static void test_simply_memory_hygiene(void **state)
{
    (void)state; /* unused */

    /* Build a complex pattern */
    sl_pattern_t complex = sl_seq(5,
        sl_start(),
        sl_literal("prefix"),
        sl_capture(sl_digit(5)),
        sl_optional(sl_any_of("abc")),
        sl_end()
    );

    assert_non_null(complex);
    
    /* Single root free should handle all child nodes */
    strling_ast_node_free(complex);
    /* If we reach here without crash, memory hygiene is good */
}

/**
 * Test: Simple Literal Pattern
 */
static void test_simple_literal(void **state)
{
    (void)state; /* unused */

    sl_pattern_t lit = sl_literal("hello");
    assert_non_null(lit);
    
    assert_int_equal(lit->type, AST_TYPE_LIT);
    assert_string_equal(lit->u.lit.value, "hello");
    
    strling_ast_node_free(lit);
}

/**
 * Test: Digit Pattern with Count
 */
static void test_digit_pattern(void **state)
{
    (void)state; /* unused */

    /* Single digit */
    sl_pattern_t digit1 = sl_digit(1);
    assert_non_null(digit1);
    assert_int_equal(digit1->type, AST_TYPE_CHARCLASS);
    strling_ast_node_free(digit1);
    
    /* Multiple digits - should be wrapped in quantifier */
    sl_pattern_t digit3 = sl_digit(3);
    assert_non_null(digit3);
    assert_int_equal(digit3->type, AST_TYPE_QUANT);
    assert_int_equal(digit3->u.quant.min, 3);
    assert_int_equal(digit3->u.quant.max, 3);
    strling_ast_node_free(digit3);
}

/**
 * Test: Character Class with any_of
 */
static void test_any_of_pattern(void **state)
{
    (void)state; /* unused */

    sl_pattern_t separators = sl_any_of("-. ");
    assert_non_null(separators);
    
    assert_int_equal(separators->type, AST_TYPE_CHARCLASS);
    assert_int_equal(separators->u.charclass.nitems, 3);
    assert_false(separators->u.charclass.negated);
    
    strling_ast_node_free(separators);
}

/**
 * Test: Anchors
 */
static void test_anchors(void **state)
{
    (void)state; /* unused */

    sl_pattern_t start_anchor = sl_start();
    sl_pattern_t end_anchor = sl_end();
    
    assert_non_null(start_anchor);
    assert_non_null(end_anchor);
    
    assert_int_equal(start_anchor->type, AST_TYPE_ANCHOR);
    assert_string_equal(start_anchor->u.anchor.at, "Start");
    
    assert_int_equal(end_anchor->type, AST_TYPE_ANCHOR);
    assert_string_equal(end_anchor->u.anchor.at, "End");
    
    strling_ast_node_free(start_anchor);
    strling_ast_node_free(end_anchor);
}

/**
 * Test: Capture and Optional
 */
static void test_combinators(void **state)
{
    (void)state; /* unused */

    sl_pattern_t digit = sl_digit(1);
    sl_pattern_t captured = sl_capture(digit);
    
    assert_non_null(captured);
    assert_int_equal(captured->type, AST_TYPE_GROUP);
    assert_true(captured->u.group.capturing);
    
    sl_pattern_t sep = sl_any_of("-");
    sl_pattern_t optional_sep = sl_optional(sep);
    
    assert_non_null(optional_sep);
    assert_int_equal(optional_sep->type, AST_TYPE_QUANT);
    assert_int_equal(optional_sep->u.quant.min, 0);
    assert_int_equal(optional_sep->u.quant.max, 1);
    
    strling_ast_node_free(captured);
    strling_ast_node_free(optional_sep);
}

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_us_phone_simply_api_construction),
        cmocka_unit_test(test_us_phone_json_reference),
        cmocka_unit_test(test_simply_memory_hygiene),
        cmocka_unit_test(test_simple_literal),
        cmocka_unit_test(test_digit_pattern),
        cmocka_unit_test(test_any_of_pattern),
        cmocka_unit_test(test_anchors),
        cmocka_unit_test(test_combinators),
    };

    return cmocka_run_group_tests(tests, NULL, NULL);
}
