/**
 * @file schema_validation_test.c
 *
 * NOTE: This test file is a stub because the C binding does not expose
 * schema validation. The C API compiles JSON to PCRE2 patterns directly.
 */

#include <stdio.h>
#include <cmocka.h>

static void test_stub(void** state) {
    (void)state;
    /* No-op - schema validation not exposed in C API */
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_stub),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
