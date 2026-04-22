/**
 * @file essential_5_test.c
 * @brief Essential 5 conformance — verifies email, URL, UUID, IP, dateTime
 *        helpers compile to the correct PCRE2 patterns and accept/reject the
 *        canonical fixtures shipped under spec/stdlib/essential_5.json.
 *
 * The fixtures define the RFC-grounded expectations; this test consumes them
 * via PCRE2 (libpcre2-8) and validates that every compiled pattern matches
 * every "valid" sample and rejects every "invalid" sample.
 */

#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <cmocka.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>
#include <jansson.h>

#include "strling.h"
#include "strling_essential.h"

static char *g_spec_path = NULL;
static json_t *g_spec = NULL;

static int find_spec(void)
{
    char path[1024];
    strcpy(path, "spec/stdlib/essential_5.json");
    for (int i = 0; i < 10; i++) {
        FILE *f = fopen(path, "r");
        if (f) { fclose(f); g_spec_path = strdup(path); return 0; }
        char tmp[1024];
        snprintf(tmp, sizeof(tmp), "../%s", path);
        strcpy(path, tmp);
    }
    return -1;
}

static int setup_spec(void **state) {
    (void)state;
    if (find_spec() != 0) return -1;
    json_error_t err;
    g_spec = json_load_file(g_spec_path, 0, &err);
    return g_spec ? 0 : -1;
}

static int teardown_spec(void **state) {
    (void)state;
    if (g_spec) { json_decref(g_spec); g_spec = NULL; }
    free(g_spec_path); g_spec_path = NULL;
    return 0;
}

/* Compile JSON AST to PCRE2 then anchor it for full-string matching. */
static pcre2_code *compile_anchored(const char *json_ast)
{
    strling_result_t r = strling_compile_compat(json_ast, NULL);
    assert_int_equal(r.error_code, STRling_OK);
    assert_non_null(r.pcre2_pattern);

    char anchored[4096];
    snprintf(anchored, sizeof(anchored), "^(?:%s)$", r.pcre2_pattern);

    int errnum;
    PCRE2_SIZE erroffset;
    pcre2_code *re = pcre2_compile((PCRE2_SPTR)anchored, PCRE2_ZERO_TERMINATED,
                                   0, &errnum, &erroffset, NULL);
    if (!re) {
        PCRE2_UCHAR buf[256];
        pcre2_get_error_message(errnum, buf, sizeof(buf));
        fprintf(stderr, "pcre2_compile failed: %s @%zu\n  pattern: %s\n", buf, erroffset, anchored);
    }
    assert_non_null(re);

    strling_result_free_compat(&r);
    return re;
}

static int matches(pcre2_code *re, const char *subject)
{
    pcre2_match_data *md = pcre2_match_data_create_from_pattern(re, NULL);
    int rc = pcre2_match(re, (PCRE2_SPTR)subject, strlen(subject), 0, 0, md, NULL);
    pcre2_match_data_free(md);
    return rc >= 0;
}

static void run_pattern(const char *json_ast,
                        const char *pattern_key, const char *fixture_key,
                        int expect_match)
{
    pcre2_code *re = compile_anchored(json_ast);
    json_t *patterns = json_object_get(g_spec, "patterns");
    json_t *entry = json_object_get(patterns, pattern_key);
    json_t *fx = json_object_get(json_object_get(entry, "fixtures"), fixture_key);
    assert_non_null(fx);
    size_t i;
    json_t *v;
    json_array_foreach(fx, i, v) {
        const char *s = json_string_value(v);
        int got = matches(re, s);
        if (got != expect_match) {
            fprintf(stderr, "[%s/%s] expected=%d got=%d for '%s'\n",
                    pattern_key, fixture_key, expect_match, got, s);
        }
        assert_int_equal(got, expect_match);
    }
    pcre2_code_free(re);
}

#define CASE(name, fn, key, fxkey, expect) \
    static void test_##name(void **st) { (void)st; char *j = fn(); run_pattern(j, key, fxkey, expect); free(j); }

CASE(email_valid,    sl_email,     "email",    "valid",            1)
CASE(email_invalid,  sl_email,     "email",    "invalid",          0)
CASE(url_valid,      sl_url,       "url",      "valid",            1)
CASE(url_invalid,    sl_url,       "url",      "invalid",          0)
CASE(uuid_valid,     sl_uuid,      "uuid",     "valid_default",    1)
CASE(uuid_invalid,   sl_uuid,      "uuid",     "invalid_default",  0)
CASE(uuid_v4_valid,  sl_uuid_v4,   "uuid",     "valid_v4",         1)
CASE(uuid_v4_invalid,sl_uuid_v4,   "uuid",     "invalid_v4",       0)
CASE(ip_v4_valid,    sl_ip_v4,     "ip",       "valid_v4",         1)
CASE(ip_v4_invalid,  sl_ip_v4,     "ip",       "invalid_v4",       0)
CASE(ip_v6_valid,    sl_ip_v6,     "ip",       "valid_v6",         1)
CASE(ip_v6_invalid,  sl_ip_v6,     "ip",       "invalid_v6",       0)
CASE(ip_any_v4,      sl_ip_any,    "ip",       "valid_v4",         1)
CASE(ip_any_v6,      sl_ip_any,    "ip",       "valid_v6",         1)
CASE(date_time_valid,   sl_date_time, "dateTime", "valid",          1)
CASE(date_time_invalid, sl_date_time, "dateTime", "invalid",        0)

int main(void)
{
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_email_valid),
        cmocka_unit_test(test_email_invalid),
        cmocka_unit_test(test_url_valid),
        cmocka_unit_test(test_url_invalid),
        cmocka_unit_test(test_uuid_valid),
        cmocka_unit_test(test_uuid_invalid),
        cmocka_unit_test(test_uuid_v4_valid),
        cmocka_unit_test(test_uuid_v4_invalid),
        cmocka_unit_test(test_ip_v4_valid),
        cmocka_unit_test(test_ip_v4_invalid),
        cmocka_unit_test(test_ip_v6_valid),
        cmocka_unit_test(test_ip_v6_invalid),
        cmocka_unit_test(test_ip_any_v4),
        cmocka_unit_test(test_ip_any_v6),
        cmocka_unit_test(test_date_time_valid),
        cmocka_unit_test(test_date_time_invalid),
    };
    return cmocka_run_group_tests(tests, setup_spec, teardown_spec);
}
