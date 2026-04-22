/**
 * @file emitter_edges_conformance_test.c
 * @brief C runner for the global pathological-AST fixture.
 *
 * Mirrors `bindings/typescript/__tests__/unit/emitter_edges_conformance.test.ts`,
 * driving the same three pathological vectors through the C PCRE2 emitter
 * to verify each safety guard fires:
 *
 *   1. Variable-Length Lookbehind Rejection  — error: VLB_NOT_SUPPORTED
 *   2. AST Depth Limit Exceeded              — error: MAX_DEPTH
 *   3. ReDoS Risk Warning (nested `(a+)+`)   — non-fatal warning: REDOS_RISK
 *
 * The TypeScript runner consumes
 * `tests/conformance/inputs/emitter_edges/pathological.json` directly via
 * an `astToIR` adapter. The C emitter consumes JSON ASTs (not IR), so we
 * reproduce the equivalent ASTs verbatim as JSON literals here — the
 * function of `astToIR` is fulfilled by selecting the field names the C
 * AST shape expects (Lookbehind/Quantifier accept a `content` alias).
 *
 * Keep the JSON literals in lock-step with `pathological.json` so any
 * future fixture edits surface as test failures rather than silent drift.
 */

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <string.h>
#include <stdio.h>

#include "strling.h"

/* --- Vector 1: Variable-Length Lookbehind Rejection ---------------------
 * AST equivalent of:
 *   { type: "Lookbehind", content: { type: "Quantifier", min: 1, max: null,
 *                                    content: { type: "Literal", value: "a" } } }
 */
static const char *VLB_AST =
    "{\"type\":\"Lookbehind\",\"content\":"
    "{\"type\":\"Quantifier\",\"min\":1,\"max\":null,"
    "\"content\":{\"type\":\"Literal\",\"value\":\"a\"}}}";

/* --- Vector 2: AST Depth Limit Exceeded ---------------------------------
 * Three nested Groups — exceeds the test depth override of 2.
 */
static const char *DEPTH_AST =
    "{\"type\":\"Group\",\"body\":"
    "{\"type\":\"Group\",\"body\":"
    "{\"type\":\"Group\",\"body\":"
    "{\"type\":\"Literal\",\"value\":\"deep\"}}}}";

/* --- Vector 3: ReDoS Risk Warning ----------------------------------------
 * Outer unbounded quantifier wrapping an inner unbounded quantifier — `(a+)+`.
 */
static const char *REDOS_AST =
    "{\"type\":\"Quantifier\",\"min\":1,\"max\":null,"
    "\"content\":{\"type\":\"Quantifier\",\"min\":1,\"max\":null,"
    "\"content\":{\"type\":\"Literal\",\"value\":\"a\"}}}";

/* Substring expected to appear in the VLB error message. */
static const char *VLB_NEEDLE =
    "PCRE2 does not support variable-length lookbehinds.";

/* Substring expected to appear in the depth-limit error message. */
static const char *DEPTH_NEEDLE = "Maximum AST depth exceeded";

/* Substring expected to appear in the ReDoS warning text. Encoded as
 * "REDOS_RISK: ...nested unbounded quantifiers..." by the C emitter. */
static const char *REDOS_CODE = "REDOS_RISK";
static const char *REDOS_NEEDLE =
    "nested unbounded quantifiers";

static bool _result_has_warning_substr(const strling_result_t *r,
                                       const char *code,
                                       const char *needle)
{
    if (!r || !r->warnings) return false;
    for (size_t i = 0; i < r->nwarnings; ++i) {
        const char *w = r->warnings[i];
        if (!w) continue;
        if (strstr(w, code) && strstr(w, needle)) return true;
    }
    return false;
}

/* --- Tests --------------------------------------------------------------- */

static void test_variable_length_lookbehind_rejection(void **state)
{
    (void)state;
    strling_result_t r = strling_compile_compat(VLB_AST, NULL);

    assert_int_not_equal(r.error_code, STRling_OK);
    assert_non_null(r.error_message);

    if (!strstr(r.error_message, VLB_NEEDLE)) {
        printf("VLB error did not contain expected needle.\n  Got: '%s'\n",
               r.error_message);
    }
    assert_non_null(strstr(r.error_message, VLB_NEEDLE));

    strling_result_free_compat(&r);
}

static void test_ast_depth_limit_exceeded(void **state)
{
    (void)state;
    /* Depth override of 2 mirrors the fixture's `depth_override_for_test`. */
    strling_result_t r = strling_compile_compat_ex(DEPTH_AST, NULL, 2);

    assert_int_not_equal(r.error_code, STRling_OK);
    assert_non_null(r.error_message);

    if (!strstr(r.error_message, DEPTH_NEEDLE)) {
        printf("Depth error did not contain expected needle.\n  Got: '%s'\n",
               r.error_message);
    }
    assert_non_null(strstr(r.error_message, DEPTH_NEEDLE));

    strling_result_free_compat(&r);
}

static void test_redos_risk_warning(void **state)
{
    (void)state;
    strling_result_t r = strling_compile_compat(REDOS_AST, NULL);

    /* Warnings do not abort emission — the pattern must still be produced. */
    assert_int_equal(r.error_code, STRling_OK);
    assert_non_null(r.pcre2_pattern);
    assert_true(strlen(r.pcre2_pattern) > 0);

    if (!_result_has_warning_substr(&r, REDOS_CODE, REDOS_NEEDLE)) {
        printf("Expected REDOS_RISK warning was not surfaced.\n");
        for (size_t i = 0; i < r.nwarnings; ++i) {
            printf("  warning[%zu]: %s\n", i,
                   r.warnings[i] ? r.warnings[i] : "(null)");
        }
    }
    assert_true(_result_has_warning_substr(&r, REDOS_CODE, REDOS_NEEDLE));

    /* Sanity: a non-pathological pattern must not raise REDOS_RISK. */
    strling_result_free_compat(&r);

    strling_result_t plain =
        strling_compile_compat("{\"type\":\"Literal\",\"value\":\"abc\"}", NULL);
    assert_int_equal(plain.error_code, STRling_OK);
    assert_int_equal((int)plain.nwarnings, 0);
    strling_result_free_compat(&plain);
}

/* Ensure the depth override does not fire spuriously below the threshold. */
static void test_depth_override_under_limit(void **state)
{
    (void)state;
    /* Two nested groups under a depth cap of 5 must compile cleanly. */
    const char *shallow =
        "{\"type\":\"Group\",\"body\":"
        "{\"type\":\"Group\",\"body\":"
        "{\"type\":\"Literal\",\"value\":\"ok\"}}}";
    strling_result_t r = strling_compile_compat_ex(shallow, NULL, 5);
    assert_int_equal(r.error_code, STRling_OK);
    assert_non_null(r.pcre2_pattern);
    strling_result_free_compat(&r);
}

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_variable_length_lookbehind_rejection),
        cmocka_unit_test(test_ast_depth_limit_exceeded),
        cmocka_unit_test(test_redos_risk_warning),
        cmocka_unit_test(test_depth_override_under_limit),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
