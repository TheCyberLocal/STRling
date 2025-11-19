/**
 * @file errors_test.c
 * @brief Unit Tests for Error Handling Contract (20 Tests).
 *
 * PURPOSE:
 * Validates that the library enforces the error handling contract defined in
 * 'bindings/javascript/__tests__/unit/errors.test.ts'.
 *
 * ADAPTATION NOTE:
 * The reference JS tests validate the *DSL Parser* (e.g., "Unterminated group '('").
 * Since the C library accepts *JSON AST*, these tests verify the equivalent
 * *AST Validation* logic (e.g., "Group node missing 'expression' field") or
 * *Semantic Analysis* logic (e.g., "Backreference to undefined group").
 *
 * COVERAGE:
 * - Grouping & Lookaround Errors (Structural/Validation)
 * - Backreference & Naming Errors (Semantic)
 * - Character Class Errors (Structural)
 * - Escape & Codepoint Errors (Value Validation)
 * - Quantifier Errors (Semantic/Validation)
 * - Error Priority Invariant
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

/**
 * @brief Asserts that compilation fails and the error message contains the expected substring.
 */
static void verify_error(const char *json_input, const char *expected_substring) {
    strling_result_t result = strling_compile_compat(json_input, NULL);

    // 1. Assert Failure
    if (result.error_code == STRling_OK) {
        printf("FAIL: Expected error but got success.\nInput: %s\nOutput: %s\n", 
               json_input, result.pcre2_pattern);
    }
    assert_int_not_equal(result.error_code, STRling_OK);
    assert_non_null(result.error_message);

    // 2. Assert Message Match
    if (strstr(result.error_message, expected_substring) == NULL) {
        printf("FAIL: Error message mismatch.\n"
               "Expected part: '%s'\n"
               "Got message:   '%s'\n", 
               expected_substring, result.error_message);
    }
    assert_non_null(strstr(result.error_message, expected_substring));

    // 3. Cleanup
    strling_result_free_compat(&result);
}

// --- Group 1: Grouping & Lookaround Errors (5 Tests) ------------------------

static void test_unterminated_group(void **state) {
    (void)state;
    // JS: "(abc" -> Unterminated group
    // C: Group node missing required 'expression' field
    const char *input = "{\"type\": \"Group\", \"capturing\": true}";
    verify_error(input, "expression"); // or "Missing required field"
}

static void test_unterminated_named_group(void **state) {
    (void)state;
    // JS: "(?<nameabc)" -> Unterminated group name
    // C: Group name contains invalid characters or is malformed
    const char *input = "{\"type\": \"Group\", \"capturing\": true, \"name\": \"invalid name!\", \"expression\": {\"type\": \"Dot\"}}";
    verify_error(input, "Invalid group name");
}

static void test_unterminated_lookahead(void **state) {
    (void)state;
    // JS: "(?=abc" -> Unterminated lookahead
    // C: Lookaround node missing 'expression'
    const char *input = "{\"type\": \"Lookaround\", \"kind\": \"lookahead\", \"negated\": false}";
    verify_error(input, "expression");
}

static void test_unterminated_lookbehind(void **state) {
    (void)state;
    // JS: "(?<=abc" -> Unterminated lookbehind
    // C: Lookaround node missing 'expression'
    const char *input = "{\"type\": \"Lookaround\", \"kind\": \"lookbehind\", \"negated\": false}";
    verify_error(input, "expression");
}

static void test_inline_modifiers(void **state) {
    (void)state;
    // JS: "(?i)abc" -> Inline modifiers
    // C: 'flags' field must be top-level. If we try to put flags in a node where strictly not allowed?
    // Or an AST node "Modifier" that isn't supported?
    // Let's simulate an invalid field/node attempt.
    const char *input = "{\"type\": \"InlineModifier\", \"value\": \"i\"}";
    verify_error(input, "Unknown node type");
}

// --- Group 2: Backreference & Naming Errors (5 Tests) -----------------------

static void test_forward_reference_by_name(void **state) {
    (void)state;
    // JS: "\k<later>(?<later>a)" -> Undefined group
    const char *input = 
        "{\"type\": \"Sequence\", \"parts\": ["
            "{\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"later\"},"
            "{\"type\": \"Group\", \"capturing\": true, \"name\": \"later\", \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}}"
        "]}";
    verify_error(input, "undefined group");
}

static void test_forward_reference_by_index(void **state) {
    (void)state;
    // JS: "\2(a)(b)" -> Undefined group \2 (at time of parsing/compile)
    const char *input = 
        "{\"type\": \"Sequence\", \"parts\": ["
            "{\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 2},"
            "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}},"
            "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}"
        "]}";
    // Assuming C compiler enforces declaration before reference or checks count
    verify_error(input, "undefined group"); // or "Invalid backreference"
}

static void test_nonexistent_reference_by_index(void **state) {
    (void)state;
    // JS: "(a)\2" -> Undefined group \2
    const char *input = 
        "{\"type\": \"Sequence\", \"parts\": ["
            "{\"type\": \"Group\", \"capturing\": true, \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}},"
            "{\"type\": \"BackReference\", \"kind\": \"numbered\", \"ref\": 2}"
        "]}";
    verify_error(input, "undefined group");
}

static void test_unterminated_named_backref(void **state) {
    (void)state;
    // JS: "\k<" -> Unterminated
    // C: Backreference node missing 'name'
    const char *input = "{\"type\": \"BackReference\", \"kind\": \"named\"}";
    verify_error(input, "name"); // "Missing required field 'name'"
}

static void test_duplicate_group_name(void **state) {
    (void)state;
    // JS: "(?<name>a)(?<name>b)" -> Duplicate group name
    const char *input = 
        "{\"type\": \"Sequence\", \"parts\": ["
            "{\"type\": \"Group\", \"capturing\": true, \"name\": \"foo\", \"expression\": {\"type\": \"Literal\", \"value\": \"a\"}},"
            "{\"type\": \"Group\", \"capturing\": true, \"name\": \"foo\", \"expression\": {\"type\": \"Literal\", \"value\": \"b\"}}"
        "]}";
    verify_error(input, "Duplicate group name");
}

// --- Group 3: Character Class Errors (3 Tests) ------------------------------

static void test_unterminated_class(void **state) {
    (void)state;
    // JS: "[abc" -> Unterminated
    // C: CharClass missing 'members' array
    const char *input = "{\"type\": \"CharacterClass\", \"negated\": false}";
    verify_error(input, "members");
}

static void test_unterminated_unicode_property(void **state) {
    (void)state;
    // JS: "[\p{L" -> Unterminated prop
    // C: Escape node with kind='unicode_property' missing 'property' value
    const char *input = "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\"}]}";
    verify_error(input, "property");
}

static void test_missing_braces_on_unicode_property(void **state) {
    (void)state;
    // JS: "[\pL]" -> Expected {
    // C: 'property' value is malformed (e.g., empty or invalid format validation)
    const char *input = "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Escape\", \"kind\": \"unicode_property\", \"property\": \"\"}]}";
    verify_error(input, "property"); // "Invalid unicode property"
}

// --- Group 4: Escape & Codepoint Errors (4 Tests) ---------------------------

static void test_invalid_hex_digit(void **state) {
    (void)state;
    // JS: "\xG1" -> Invalid hex
    // C: Literal containing invalid hex escape? Or Escape node validation.
    // Assuming checking Escape node 'value' validation if explicit.
    // Or if value is "G1" for a hex escape node.
    const char *input = "{\"type\": \"Escape\", \"kind\": \"hex\", \"value\": \"G1\"}";
    verify_error(input, "Invalid hex");
}

static void test_invalid_unicode_digit(void **state) {
    (void)state;
    // JS: "\u12Z4" -> Invalid unicode
    const char *input = "{\"type\": \"Escape\", \"kind\": \"unicode\", \"value\": \"12Z4\"}";
    verify_error(input, "Invalid unicode");
}

static void test_unterminated_hex_brace_empty(void **state) {
    (void)state;
    // JS: "\x{" -> Empty brace
    const char *input = "{\"type\": \"Escape\", \"kind\": \"hex\", \"value\": \"\"}";
    verify_error(input, "Invalid hex");
}

static void test_unterminated_hex_brace_with_digits(void **state) {
    (void)state;
    // JS: "\x{FFFF" -> Unterminated
    // C: Escape value validation (assuming validation logic checks format)
    // Since C input is pre-parsed string, this might be "Invalid format"
    const char *input = "{\"type\": \"Escape\", \"kind\": \"hex_brace\", \"value\": \"FFFF_broken\"}"; 
    verify_error(input, "Invalid");
}

// --- Group 5: Quantifier Errors (2 Tests) -----------------------------------

static void test_unterminated_brace_quantifier(void **state) {
    (void)state;
    // JS: "a{2,5" -> Incomplete
    // C: Quantifier missing min/max, or invalid values
    const char *input = "{\"type\": \"Quantifier\", \"greedy\": true, \"target\": {\"type\": \"Dot\"}}"; // Missing min
    verify_error(input, "min"); // "Missing required field 'min'"
}

static void test_quantify_anchor(void **state) {
    (void)state;
    // JS: "^*" -> Cannot quantify anchor
    // C: Quantifier target is Anchor node
    const char *input = 
        "{\"type\": \"Quantifier\", \"min\": 0, \"max\": null, \"greedy\": true, \"target\": {\"type\": \"Anchor\", \"at\": \"Start\"}}";
    verify_error(input, "Cannot quantify anchor");
}

// --- Group 6: Invariant: First Error Wins (1 Test) --------------------------

static void test_first_error_wins(void **state) {
    (void)state;
    // JS: "[a|b(" -> Reports unterminated class (pos 0) before group (pos 5)
    // C: We provide AST with TWO errors. 1. Missing 'min' in Quantifier (top), 2. Invalid Anchor Quantification (nested).
    // We expect the validator to fail fast or report the first/outer one.
    const char *input = 
        "{\"type\": \"Quantifier\", \"greedy\": true, \"target\": " // Error 1: Missing min
            "{\"type\": \"Quantifier\", \"min\": 1, \"target\": {\"type\": \"Anchor\", \"at\": \"Start\"}}" // Error 2: Anchor target
        "}";
    
    // Should complain about 'min' (structure) before analyzing deep semantic logic
    verify_error(input, "min"); 
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_unterminated_group),
        cmocka_unit_test(test_unterminated_named_group),
        cmocka_unit_test(test_unterminated_lookahead),
        cmocka_unit_test(test_unterminated_lookbehind),
        cmocka_unit_test(test_inline_modifiers),
        cmocka_unit_test(test_forward_reference_by_name),
        cmocka_unit_test(test_forward_reference_by_index),
        cmocka_unit_test(test_nonexistent_reference_by_index),
        cmocka_unit_test(test_unterminated_named_backref),
        cmocka_unit_test(test_duplicate_group_name),
        cmocka_unit_test(test_unterminated_class),
        cmocka_unit_test(test_unterminated_unicode_property),
        cmocka_unit_test(test_missing_braces_on_unicode_property),
        cmocka_unit_test(test_invalid_hex_digit),
        cmocka_unit_test(test_invalid_unicode_digit),
        cmocka_unit_test(test_unterminated_hex_brace_empty),
        cmocka_unit_test(test_unterminated_hex_brace_with_digits),
        cmocka_unit_test(test_unterminated_brace_quantifier),
        cmocka_unit_test(test_quantify_anchor),
        cmocka_unit_test(test_first_error_wins),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}