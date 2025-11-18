/**
 * @file ir_compiler_test.c
 *
 * NOTE: This test file is a stub because the C binding does not expose
 * the IR compiler. The C API provides strling_compile() which handles
 * compilation internally.
 */

#include <stdio.h>
#include <cmocka.h>

static void test_stub(void** state) {
    (void)state;
    /* No-op - IR compiler is internal to strling_compile() */
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_stub),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
