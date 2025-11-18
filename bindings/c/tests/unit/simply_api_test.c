/**
 * @file simply_api_test.c
 *
 * NOTE: This test file is a stub because the C binding does not expose
 * the Simply API. The C API only provides strling_compile() for JSON AST.
 */

#include <stdio.h>
#include <cmocka.h>

static void test_stub(void** state) {
    (void)state;
    /* No-op - Simply API not provided in C binding */
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_stub),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
