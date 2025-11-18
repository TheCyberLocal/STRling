/**
 * @file parser_errors_test.c
 *
 * NOTE: This test file is a stub because the C binding does not expose
 * a parser. The C API takes JSON AST directly via strling_compile().
 */

#include <stdio.h>
#include <cmocka.h>

static void test_stub(void** state) {
    (void)state;
    /* No-op - parser not exposed in C API */
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_stub),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
