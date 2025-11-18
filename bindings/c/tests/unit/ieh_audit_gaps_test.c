/**
 * @file ieh_audit_gaps_test.c
 * @brief Unit Tests for Intelligent Error Handling Audit Gaps (23 Tests).
 *
 * PURPOSE:
 * Validates that the library provides context-aware, instructional error messages
 * for critical audit findings (Intelligent Error Handling) and that valid inputs
 * remain accepted.
 * Matches the test count (23) of 'bindings/javascript/__tests__/unit/ieh_audit_gaps.test.ts'.
 *
 * COVERAGE:
 * - Group Name Validation (Digits, Empty, Hyphens)
 * - Quantifier Range Validation (Min > Max)
 * - Character Class Range Validation (Reversed)
 * - Empty Alternation Validation
 * - Flag Directive Validation
 * - Incomplete Backref Hints
 * - Context-Aware Quantifier Hints (+, ?, {})
 * - Context-Aware Escape Hints (\q, \z)
 * - Valid Pattern Acceptance
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
 * @brief Asserts that compilation fails and the error message contains
 * BOTH the error type/message AND the specific hint text.
 */
static void verify_error_with_hint(const char *json_input, 
                                   const char *expected_msg_part, 
                                   const char *expected_hint_part) {
    strling_result_t result = strling_compile(json_input, NULL);

    // 1. Assert Failure
    if (result.error_code == STRling_OK) {
        printf("FAIL: Expected error but got success.\nInput: %s\nOutput: %s\n", 
               json_input, result.pcre2_pattern);
    }
    assert_int_not_equal(result.error_code, STRling_OK);
    assert_non_null(result.error_message);

    // 2. Assert Message Match
    if (strstr(result.error_message, expected_msg_part) == NULL) {
        printf("FAIL: Error message missing expected text.\n"
               "Expected: '%s'\n"
               "Got:      '%s'\n", 
               expected_msg_part, result.error_message);
    }
    assert_non_null(strstr(result.error_message, expected_msg_part));

    // 3. Assert Hint Match
    // Note: libstrling appends hints to the error message.
    if (strstr(result.error_message, expected_hint_part) == NULL) {
        printf("FAIL: Error message missing expected hint.\n"
               "Expected Hint Part: '%s'\n"
               "Got Full Message:   '%s'\n", 
               expected_hint_part, result.error_message);
    }
    assert_non_null(strstr(result.error_message, expected_hint_part));

    strling_result_free(&result);
}

/**
 * @brief Asserts that compilation succeeds.
 */
static void verify_success(const char *json_input) {
    strling_result_t result = strling_compile(json_input, NULL);
    
    if (result.error_code != STRling_OK) {
        printf("FAIL: Unexpected compilation error.\nMessage: %s\n", result.error_message);
    }
    assert_int_equal(result.error_code, STRling_OK);
    
    strling_result_free(&result);
}

// --- Group 1: Group Name Validation (3 Tests) -------------------------------

static void test_group_name_starts_with_digit(void **state) {
    (void)state;
    // (?<1a>) -> Invalid group name
    const char *input = "{\"type\": \"Group\", \"capturing\": true, \"name\": \"1a\", \"expression\": {\"type\": \"Sequence\", \"parts\": []}}";
    verify_error_with_hint(input, "Invalid group name", "IDENTIFIER"); 
}

static void test_group_name_empty(void **state) {
    (void)state;
    // (?<>) -> Invalid group name
    const char *input = "{\"type\": \"Group\", \"capturing\": true, \"name\": \"\", \"expression\": {\"type\": \"Sequence\", \"parts\": []}}";
    // Note: JS test doesn't enforce a specific hint for empty, just the error.
    // Using verify_error_with_hint with same string for hint check loosely.
    verify_error_with_hint(input, "Invalid group name", "Invalid group name"); 
}

static void test_group_name_hyphens(void **state) {
    (void)state;
    // (?<name-bad>) -> Invalid group name
    const char *input = "{\"type\": \"Group\", \"capturing\": true, \"name\": \"name-bad\", \"expression\": {\"type\": \"Sequence\", \"parts\": []}}";
    verify_error_with_hint(input, "Invalid group name", "IDENTIFIER");
}

// --- Group 2: Quantifier Range Validation (1 Test) --------------------------

static void test_quantifier_min_exceeds_max(void **state) {
    (void)state;
    // a{5,2}
    const char *input = "{\"type\": \"Quantifier\", \"min\": 5, \"max\": 2, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}";
    // Hint regex in JS: /m.*<=.*n|m <= n|m ≤ n/
    verify_error_with_hint(input, "Invalid quantifier range", "m <= n");
}

// --- Group 3: Character Class Range Validation (2 Tests) --------------------

static void test_range_reversed_letter(void **state) {
    (void)state;
    // [z-a]
    const char *input = "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"z\", \"to\": \"a\"}]}";
    verify_error_with_hint(input, "Invalid character range", "Invalid character range");
}

static void test_range_reversed_digit(void **state) {
    (void)state;
    // [9-0]
    const char *input = "{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"9\", \"to\": \"0\"}]}";
    verify_error_with_hint(input, "Invalid character range", "Invalid character range");
}

// --- Group 4: Empty Alternation Validation (1 Test) -------------------------

static void test_alternation_empty_branch(void **state) {
    (void)state;
    // a||b -> Alternation where middle option is empty/null
    // Representing empty branch in AST usually means explicit Empty node or structure check.
    // Adapted: Alternation with null/missing alternative in list.
    const char *input = "{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, null]}";
    // If parser rejects "||", AST validator should reject malformed alternative list.
    // Error: "Empty alternation" or "Invalid node".
    // Hint: "a|b"
    verify_error_with_hint(input, "Alternation", "a|b"); 
}

// --- Group 5: Flag Directive Validation (2 Tests) ---------------------------

static void test_flag_invalid_letter(void **state) {
    (void)state;
    // %flags foo -> flags: "foo"
    const char *input = "{\"flags\": \"foo\", \"pattern\": {\"type\": \"Literal\", \"value\": \"a\"}}";
    // Should mention 'i', 'm' as valid flags in hint
    verify_error_with_hint(input, "Invalid flag", "i");
}

static void test_directive_after_pattern(void **state) {
    (void)state;
    // This is a Parser-level test (textual order). 
    // Since C receives JSON, the order is struct-defined. 
    // However, we can simulate the "Flags must be top-level" validation if user puts flags inside pattern?
    // Actually, in JSON AST, 'flags' is a top-level key. If a user tries to put a Directive node inside Sequence?
    // Let's simulate: Sequence [ Literal, Directive ].
    const char *input = "{\"type\": \"Sequence\", \"parts\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Directive\", \"kind\": \"flags\", \"value\": \"i\"}]}";
    verify_error_with_hint(input, "Directive", "start of the pattern");
}

// --- Group 6: Incomplete Named Backref Hint (1 Test) ------------------------

static void test_incomplete_named_backref(void **state) {
    (void)state;
    // \k -> Incomplete. In AST, BackReference node missing 'name'.
    const char *input = "{\"type\": \"BackReference\", \"kind\": \"named\", \"name\": \"\"}"; 
    // OR if parser failed earlier.
    // Assuming AST validator catches empty name or missing name field.
    verify_error_with_hint(input, "Expected '<'", "\\k<name>");
}

// --- Group 7: Context-Aware Quantifier Hints (3 Tests) ----------------------

static void test_quantifier_plus_hint(void **state) {
    (void)state;
    // "+" at start -> Quantifier without target.
    // In AST: Quantifier with null target?
    const char *input = "{\"type\": \"Quantifier\", \"min\": 1, \"max\": null, \"greedy\": true, \"target\": null}";
    verify_error_with_hint(input, "Quantifier", "'+'");
}

static void test_quantifier_question_hint(void **state) {
    (void)state;
    // "?" at start
    const char *input = "{\"type\": \"Quantifier\", \"min\": 0, \"max\": 1, \"greedy\": true, \"target\": null}";
    verify_error_with_hint(input, "Quantifier", "'?'");
}

static void test_quantifier_brace_hint(void **state) {
    (void)state;
    // "{5}" at start
    const char *input = "{\"type\": \"Quantifier\", \"min\": 5, \"max\": 5, \"greedy\": true, \"target\": null}";
    verify_error_with_hint(input, "Quantifier", "'{'");
}

// --- Group 8: Context-Aware Escape Hints (2 Tests) --------------------------

static void test_escape_unknown_q(void **state) {
    (void)state;
    // \q -> Unknown escape
    const char *input = "{\"type\": \"Escape\", \"kind\": \"unknown\", \"value\": \"q\"}";
    // Or Literal "\q" depending on parser. If it's an error:
    verify_error_with_hint(input, "Unknown escape", "\\q");
}

static void test_escape_unknown_z_hint(void **state) {
    (void)state;
    // \z (lowercase) -> Unknown in JS, Suggest \Z.
    const char *input = "{\"type\": \"Escape\", \"kind\": \"unknown\", \"value\": \"z\"}";
    verify_error_with_hint(input, "Unknown escape", "\\Z");
}

// --- Group 9: Valid Patterns (8 Tests) --------------------------------------

static void test_valid_group_names(void **state) {
    (void)state;
    // (?<name>abc)
    verify_success("{\"type\": \"Group\", \"capturing\": true, \"name\": \"name\", \"expression\": {\"type\": \"Literal\", \"value\": \"abc\"}}");
    // (?<_name>abc)
    verify_success("{\"type\": \"Group\", \"capturing\": true, \"name\": \"_name\", \"expression\": {\"type\": \"Literal\", \"value\": \"abc\"}}");
    // (?<name123>abc)
    verify_success("{\"type\": \"Group\", \"capturing\": true, \"name\": \"name123\", \"expression\": {\"type\": \"Literal\", \"value\": \"abc\"}}");
    // (?<Name_123>abc)
    verify_success("{\"type\": \"Group\", \"capturing\": true, \"name\": \"Name_123\", \"expression\": {\"type\": \"Literal\", \"value\": \"abc\"}}");
}

static void test_valid_quantifier_ranges(void **state) {
    (void)state;
    // a{2,5}
    verify_success("{\"type\": \"Quantifier\", \"min\": 2, \"max\": 5, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}");
    // a{2,2}
    verify_success("{\"type\": \"Quantifier\", \"min\": 2, \"max\": 2, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}");
    // a{0,10}
    verify_success("{\"type\": \"Quantifier\", \"min\": 0, \"max\": 10, \"greedy\": true, \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}");
}

static void test_valid_char_ranges(void **state) {
    (void)state;
    // [a-z]
    verify_success("{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"a\", \"to\": \"z\"}]}");
    // [0-9]
    verify_success("{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"0\", \"to\": \"9\"}]}");
    // [A-Z]
    verify_success("{\"type\": \"CharacterClass\", \"members\": [{\"type\": \"Range\", \"from\": \"A\", \"to\": \"Z\"}]}");
}

static void test_valid_alternation(void **state) {
    (void)state;
    // a|b
    verify_success("{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}]}");
    // a|b|c
    verify_success("{\"type\": \"Alternation\", \"alternatives\": [{\"type\": \"Literal\", \"value\": \"a\"}, {\"type\": \"Literal\", \"value\": \"b\"}, {\"type\": \"Literal\", \"value\": \"c\"}]}");
}

static void test_valid_flags(void **state) {
    (void)state;
    // %flags i
    verify_success("{\"flags\": \"i\", \"pattern\": {\"type\": \"Literal\", \"value\": \"abc\"}}");
    // %flags imsux
    verify_success("{\"flags\": \"imsux\", \"pattern\": {\"type\": \"Literal\", \"value\": \"abc\"}}");
}

static void test_brace_rejects_non_digits(void **state) {
    (void)state;
    // a{foo} -> Parser failure in JS. 
    // In C (JSON AST), 'min'/'max' are ints. JSON parser itself fails if string provided where int expected.
    // Or if 'max' is "foo"?
    // Adapted: Validation fails if numbers aren't valid.
    const char *input = "{\"type\": \"Quantifier\", \"min\": \"foo\", \"target\": {\"type\": \"Literal\", \"value\": \"a\"}}";
    verify_error_with_hint(input, "Invalid", "digit"); // JSON parse error or schema validation
}

static void test_unterminated_brace(void **state) {
    (void)state;
    // a{5 -> Parser failure.
    // Malformed JSON AST node? Missing max or close?
    // Simulating: Missing 'max' field but not 'min' (Open ended requires max: null)
    // OR Malformed JSON string.
    const char *input = "{\"type\": \"Quantifier\", \"min\": 5"; // Malformed JSON
    verify_error_with_hint(input, "JSON", "Unterminated"); // or closing '}'
}

static void test_empty_char_class_hint(void **state) {
    (void)state;
    // [] -> Empty members array
    const char *input = "{\"type\": \"CharacterClass\", \"members\": []}";
    verify_error_with_hint(input, "Empty character class", "add characters");
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_group_name_starts_with_digit),
        cmocka_unit_test(test_group_name_empty),
        cmocka_unit_test(test_group_name_hyphens),
        cmocka_unit_test(test_quantifier_min_exceeds_max),
        cmocka_unit_test(test_range_reversed_letter),
        cmocka_unit_test(test_range_reversed_digit),
        cmocka_unit_test(test_alternation_empty_branch),
        cmocka_unit_test(test_flag_invalid_letter),
        cmocka_unit_test(test_directive_after_pattern),
        cmocka_unit_test(test_incomplete_named_backref),
        cmocka_unit_test(test_quantifier_plus_hint),
        cmocka_unit_test(test_quantifier_question_hint),
        cmocka_unit_test(test_quantifier_brace_hint),
        cmocka_unit_test(test_escape_unknown_q),
        cmocka_unit_test(test_escape_unknown_z_hint),
        cmocka_unit_test(test_valid_group_names),
        cmocka_unit_test(test_valid_quantifier_ranges),
        cmocka_unit_test(test_valid_char_ranges),
        cmocka_unit_test(test_valid_alternation),
        cmocka_unit_test(test_valid_flags),
        cmocka_unit_test(test_brace_rejects_non_digits),
        cmocka_unit_test(test_unterminated_brace),
        cmocka_unit_test(test_empty_char_class_hint),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}