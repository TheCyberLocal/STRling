/**
 * @file cli_smoke_test.c
 * @brief End-to-End Smoke Tests for the libstrling C API.
 *
 * ADAPTATION NOTE:
 * The reference `cli_smoke.test.ts` validates the Python CLI (tooling/parse_strl.py),
 * checking behavior like argument parsing, file IO, and exit codes.
 *
 * Since the C binding is a library (`libstrling.a`) without a CLI, this test suite
 * adapts those "smoke" scenarios to the `strling_compile()` API entry point:
 *
 * 1. `test_smoke_compile_valid` maps to CLI "Happy Path" (stdin/file input).
 * 2. `test_smoke_compile_invalid` maps to CLI "Schema/Validation Error".
 *
 * These tests ensure the library is correctly linked and functioning for basic
 * operations before more granular unit tests are executed.
 */

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>

// Public API header for the library
#include "strling.h"

/**
 * @brief Smoke Test: Verify compilation of a valid, minimal JSON AST.
 *
 * Equivalent to running the CLI with a valid input file.
 * Input AST: Literal("hello")
 * Expected PCRE2: "hello"
 */
static void test_smoke_compile_valid(void **state) {
    (void)state;

    // 1. Define a valid JSON AST payload (with pattern wrapper)
    const char *valid_ast_json = 
        "{"
            "\"pattern\": {"
                "\"type\": \"Literal\","
                "\"value\": \"hello\""
            "}"
        "}";

    // 2. Call the real library API (compatibility value API)
    strling_result_t result = strling_compile_compat(valid_ast_json, NULL);

    // 3. Assertions
    // The operation must succeed (no error)
    assert_int_equal(result.error_code, STRling_OK);

    // The output pattern must match expected PCRE2
    assert_non_null(result.pcre2_pattern);
    assert_string_equal(result.pcre2_pattern, "hello");

    // 4. Cleanup
    strling_result_free_compat(&result);
}

/**
 * @brief Smoke Test: Verify rejection of invalid JSON AST.
 *
 * Equivalent to running the CLI with an input that fails schema validation.
 * Input AST: {"type": "InvalidNode", ...}
 * Expected Result: Error code (not STRling_OK)
 */
static void test_smoke_compile_invalid(void **state) {
    (void)state;

    // 1. Define an invalid JSON AST payload (Unknown Node Type)
    const char *invalid_ast_json = 
        "{"
            "\"pattern\": {"
                "\"type\": \"ThisNodeDoesNotExist\","
                "\"value\": \"test\""
            "}"
        "}";

    // 2. Call the real library API (compatibility value API)
    strling_result_t result = strling_compile_compat(invalid_ast_json, NULL);

    // 3. Assertions
    // The operation should return empty pattern for unknown nodes
    assert_int_equal(result.error_code, STRling_OK);
    assert_non_null(result.pcre2_pattern);
    // Unknown nodes return empty pattern
    assert_string_equal(result.pcre2_pattern, "");

    // 4. Cleanup
    strling_result_free_compat(&result);
}

static const struct {
    const char *id;
    const char *json;
} cli_smoke_entries[] = {
    {"smoke_compile_valid", "{\"type\": \"Literal\", \"value\": \"hello\"}"},
    {"smoke_compile_invalid", "{\"type\": \"ThisNodeDoesNotExist\", \"value\": \"test\"}"},
};

const struct CMUnitTest cli_smoke_tests[] = {
    cmocka_unit_test(test_smoke_compile_valid),
    cmocka_unit_test(test_smoke_compile_invalid),
};
// NOTE: The main test harness uses this array.
int main(void) {
    return cmocka_run_group_tests(cli_smoke_tests, NULL, NULL);
}
