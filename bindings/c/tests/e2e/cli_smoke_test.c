/**
 * @file cli_smoke_test.c
 *
 * NOTE: This test file is a stub because the C binding does not provide
 * a CLI. The C binding is a library (libstrling.a) only.
 */

#include <stdio.h>
#include <cmocka.h>

static void test_stub(void** state) {
    (void)state;
    /* No-op - CLI not provided in C binding */
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_stub),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
