/*
 * Test helpers for C tests (fixture loading and assertions)
 */
#ifndef TEST_HELPERS_H
#define TEST_HELPERS_H

#include <stdbool.h>
#include <stdarg.h>

/* Read an entire file as a newly allocated string. Caller must free. */
char* read_file_to_string(const char* path);

/* Assert that compiling the JSON AST file produces a pattern matching expected_pattern.
 * This function will call cmocka assertion helpers for pass/fail and free result.
 */
void assert_compile_equals_from_json(const char* json_path, const char* expected_pattern);

/* Assert that compiling the JSON AST file succeeds (no error) */
void assert_compile_success(const char* json_path);

/* Assert that compiling the JSON AST file produces an error that contains expected_substring */
void assert_compile_error_contains(const char* json_path, const char* expected_substring);

/* Read expected metadata from JSON fixture and assert accordingly.
 * This will dispatch to assert_compile_success, assert_compile_equals_from_json,
 * or assert_compile_error_contains depending on the 'expected' field.
 */
void assert_compile_matches_expected(const char* json_path);

#endif /* TEST_HELPERS_H */
