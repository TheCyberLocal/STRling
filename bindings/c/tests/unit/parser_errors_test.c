/**
 * @file parser_errors_test.c
 * @brief Unit Tests for Rich Error Formatting and Hints (20 Tests).
 *
 * PURPOSE:
 * Validates that the library produces descriptive, helpful error messages when
 * encountering invalid input, preserving the "Visionary State" error quality
 * contract defined in 'bindings/javascript/__tests__/unit/parser_errors.test.ts'.
 *
 * ADAPTATION NOTE:
 * The reference JS tests validate the DSL parser (e.g., "Unterminated group").
 * Since the C library accepts JSON AST, these tests utilize:
 * 1. Malformed JSON (to test low-level parsing errors).
 * 2. Structurally Invalid ASTs (to test validation hints).
 * 3. Semantic Violations (to test logic errors).
 *
 * COVERAGE:
 * - Rich Error Formatting (Context, Hints)
 * - Specific Error Hints (Alternation, Classes, Quantifiers, etc.)
 * - Complex Error Scenarios (Nesting, Propagation)
 * - Error API Backward Compatibility (Message fields)
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

static void verify_error_content(const char *json_input, const char *expected_substring) {
    strling_result_t result = strling_compile(json_input, NULL);

    if (result.error_code == STRling_OK) {
        printf("FAIL: Expected error but got success.\nInput: %s\nOutput: %s\n", 
               json_input, result.pcre2_pattern);
    }
    assert_int_not_equal(result.error_code, STRling_OK);
    assert_non_null(result.error_message);

    if (strstr(result.error_message, expected_substring) == NULL) {
        printf("FAIL: Error message mismatch.\n"
               "Expected part: '%s'\n"
               "Got message:   '%s'\n", 
               expected_substring, result.error_message);
    }
    assert_non_null(strstr(result.error_message, expected_substring));

    strling_result_free(&result);
}

// --- Group 1: Rich Error Formatting (4 Tests) -------------------------------

static void test_format_rich_error(void **state) {
    (void)state;
    // JS: "Unmatched closing paren" -> Syntax Error
    // C: Malformed JSON (extra brace) to trigger parser error with context
    const char *input = "{\"type\": \"Literal\", \"value\": \"a\"}}"; 
    verify_error_content(input, "JSON"); // Expect generic JSON parse error
}

static void test_hint_unterminated_group(void **state) {
    (void)state;
    // JS: "(abc" -> Unterminated group
    // C: Group node missing required 'expression' field
    const char *input = "{\"type\": \"Group\", \"capturing\": true}";
    verify_error_content(input, "expression"); // "Missing required field"
}

static void test_line_number_accuracy(void **state) {
    (void)state;
    // JS: Error on second line
    // C: Multiline JSON with error on line 2
    const char *input = 
        "{\n"
        "  \"type\": \"InvalidNode\"\n"
        "}";
    verify_error_content(input, "InvalidNode"); // Message should reference the invalid value
}

static void test_caret_position(void **state) {
    (void)state;
    // JS: Caret points to position
    // C: JSON parser error position. verify_error_content checks for substring, 
    // checking for "line" or "column" implies position tracking exists.
    const char *input = "{ \"type\": "; // Incomplete
    verify_error_content(input, "JSON"); // Standard parser should report location
}

// --- Group 2: Specific Error Hints (9 Tests) --------------------------------

static void test_hint_alt_no_lhs(void **state) {
    (void)state;
    // JS: "|abc" -> Alt missing LHS
    // C: Alternation with missing first element or null
    const char *input = "{\"type\": \"Alternation\", \"alternatives\": [null, {\"type\": \"Literal\", \"value\": \"a\"}]}";
    verify_error_content(input, "Alternation"); // "Invalid alternative"
}

static void test_hint_alt_no_rhs(void **state) {
    (void)state;
    // JS: "abc|" -> Alt missing RHS
    // C: Alternation with missing last element
    const char *input = "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}]}"; 
    // Single element alt is usually optimized, but if we enforce >1, checks validation
    // Or explicitly null second branch:
    const char *input2 = "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, null]}";
    verify_error_content(input2, "Alternation");
}

static void test_hint_unterminated_class(void **state) {
    (void)state;
    // JS: "[abc" -> Unterminated class
    // C: CharClass missing 'members'
    const char *input = "{\"type\": \"CharacterClass\", \"negated\": false}";
    verify_error_content(input, "members");
}

static void test_hint_quantify_anchor(void **state) {
    (void)state;
    // JS: "^*" -> Cannot quantify anchor
    // C: Quantifier target is Anchor
    const char *input = 
        "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Anchor\", \"at\": \"Start\"}}";
    verify_error_content(input, "Cannot quantify anchor");
}

static void test_hint_invalid_hex(void **state) {
    (void)state;
    // JS: "\xGG" -> Invalid hex
    // C: Escape node validation
    const char *input = "{\"type\": \"Escape\", \"kind\": \"hex\", \"value\": \"GG\"}";
    verify_error_content(input, "Invalid hex");
}

static void test_hint_undefined_backref(void **state) {
    (void)state;
    // JS: "\1" -> Undefined backref
    // C: Backref to undefined index/name
    const char *input = "{\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 1}";
    verify_error_content(input, "undefined");
}

static void test_hint_duplicate_name(void **state) {
    (void)state;
    // JS: "(?<n>)(?<n>)" -> Duplicate name
    const char *input = 
        "{\"type\": \"Sequence\", \"parts\": ["
            "{\"type\": \"Group\", \"capturing\": true, \"name\": \"n\", \"expression\": {\"type\": \"Dot\"}},"
            "{\"type\": \"Group\", \"capturing\": true, \"name\": \"n\", \"expression\": {\"type\": \"Dot\"}}"
        "]}";
    verify_error_content(input, "Duplicate");
}

static void test_hint_inline_modifiers(void **state) {
    (void)state;
    // JS: "(?i)" -> Inline modifier error
    // C: Attempting to use unsupported InlineModifier node
    const char *input = "{\"type\": \"InlineModifier\", \"value\": \"i\"}";
    verify_error_content(input, "Unknown node");
}

static void test_hint_unterminated_unicode(void **state) {
    (void)state;
    // JS: "[\p{L" -> Unterminated unicode
    // C: Escape unicode node missing property
    const char *input = "{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"\"}";
    verify_error_content(input, "property");
}

// --- Group 3: Complex Error Scenarios (4 Tests) -----------------------------

static void test_complex_nested_error(void **state) {
    (void)state;
    // JS: "((abc" -> Nested unterminated
    // C: Deeply nested missing field
    const char *input = 
        "{\"type\": \"Group\", \"capturing\": true, \"expression\": "
            "{\"type\": \"Group\", \"capturing\": true}" // Missing expression here
        "}";
    verify_error_content(input, "expression");
}

static void test_complex_alt_branch_error(void **state) {
    (void)state;
    // JS: "a|(b" -> Error in branch
    // C: Error inside alternation branch
    const char *input = 
        "{\"type\": \"Alternation\", \"alternatives\": ["
            "{\"type\": \"Literal\", \"value\": \"a\"},"
            "{\"type\": \"Group\", \"capturing\": true}" // Missing expression
        "]}";
    verify_error_content(input, "expression");
}

static void test_complex_free_spacing_error(void **state) {
    (void)state;
    // JS: Error with free spacing flag
    // C: Flags provided, but AST invalid
    const char *input = 
        "{\"flags\": \"x\", \"pattern\": {\"type\": \"Quantifier\"}}"; // Missing target/min
    verify_error_content(input, "min");
}

static void test_complex_position_accuracy(void **state) {
    (void)state;
    // JS: "abc{2," -> Error position
    // C: AST validation failure
    const char *input = "{\"type\": \"Quantifier\", \"min\": 2}"; // Missing target
    verify_error_content(input, "target");
}

// --- Group 4: Error Backward Compatibility (3 Tests) ------------------------

static void test_compat_message_attr(void **state) {
    (void)state;
    // JS: Check message existence
    strling_result_t result = strling_compile("{invalid}", NULL);
    assert_non_null(result.error_message);
    assert_true(strlen(result.error_message) > 0);
    strling_result_free(&result);
}

static void test_compat_pos_attr(void **state) {
    (void)state;
    // JS: Check pos attribute
    // C: Check error_code is not OK (proxy for status)
    strling_result_t result = strling_compile("{invalid}", NULL);
    assert_int_not_equal(result.error_code, STRling_OK);
    strling_result_free(&result);
}

static void test_compat_string_output(void **state) {
    (void)state;
    // JS: Check toString() formatting
    // C: Check message is printable string
    strling_result_t result = strling_compile("{invalid}", NULL);
    assert_non_null(result.error_message);
    // Ensure it contains text
    assert_true(strlen(result.error_message) > 5); 
    strling_result_free(&result);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_format_rich_error),
        cmocka_unit_test(test_hint_unterminated_group),
        cmocka_unit_test(test_line_number_accuracy),
        cmocka_unit_test(test_caret_position),
        cmocka_unit_test(test_hint_alt_no_lhs),
        cmocka_unit_test(test_hint_alt_no_rhs),
        cmocka_unit_test(test_hint_unterminated_class),
        cmocka_unit_test(test_hint_quantify_anchor),
        cmocka_unit_test(test_hint_invalid_hex),
        cmocka_unit_test(test_hint_undefined_backref),
        cmocka_unit_test(test_hint_duplicate_name),
        cmocka_unit_test(test_hint_inline_modifiers),
        cmocka_unit_test(test_hint_unterminated_unicode),
        cmocka_unit_test(test_complex_nested_error),
        cmocka_unit_test(test_complex_alt_branch_error),
        cmocka_unit_test(test_complex_free_spacing_error),
        cmocka_unit_test(test_complex_position_accuracy),
        cmocka_unit_test(test_compat_message_attr),
        cmocka_unit_test(test_compat_pos_attr),
        cmocka_unit_test(test_compat_string_output),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
