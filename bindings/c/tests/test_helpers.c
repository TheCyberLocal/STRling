/*
 * Implementation of test helper functions for STRling C tests.
 */
#include "test_helpers.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
#include <cmocka.h>
#include "strling.h"
#include <jansson.h>

char* read_file_to_string(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    long sz = ftell(f);
    if (sz < 0) { fclose(f); return NULL; }
    rewind(f);
    char* buf = (char*)malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { free(buf); fclose(f); return NULL; }
    buf[sz] = '\0';
    fclose(f);
    return buf;
}

static void _assert_common_compile(STRlingResult* res, const char* json_path) {
    if (!res) {
        fail_msg("Null result returned by strling_compile for %s", json_path);
        return;
    }
}

void assert_compile_equals_from_json(const char* json_path, const char* expected_pattern) {
    char* json = read_file_to_string(json_path);
    assert_non_null(json);
    STRlingResult* res = strling_compile(json, NULL);
    _assert_common_compile(res, json_path);
    free(json);
    if (res->error) {
        char buf[512];
        snprintf(buf, sizeof(buf), "Compilation error: %s (pos %d)", res->error->message, res->error->position);
        fail_msg("%s", buf);
    }
    assert_non_null(res->pattern);
    assert_string_equal(res->pattern, expected_pattern);
    strling_result_free_ptr(res);
}

void assert_compile_success(const char* json_path) {
    char* json = read_file_to_string(json_path);
    assert_non_null(json);
    STRlingResult* res = strling_compile(json, NULL);
    _assert_common_compile(res, json_path);
    free(json);
    if (res->error) {
        char buf[512];
        snprintf(buf, sizeof(buf), "Compilation error: %s (pos %d)", res->error->message, res->error->position);
        fail_msg("%s", buf);
    }
    assert_non_null(res->pattern);
    strling_result_free_ptr(res);
}

void assert_compile_error_contains(const char* json_path, const char* expected_substring) {
    char* json = read_file_to_string(json_path);
    assert_non_null(json);
    STRlingResult* res = strling_compile(json, NULL);
    _assert_common_compile(res, json_path);
    free(json);
    assert_non_null(res->error);
    assert_non_null(res->error->message);
    if (strstr(res->error->message, expected_substring) == NULL) {
        fail_msg("Expected error to contain '%s' but got '%s'", expected_substring, res->error->message);
    }
    strling_result_free_ptr(res);
}

void assert_compile_matches_expected(const char* json_path) {
    char* json = read_file_to_string(json_path);
    assert_non_null(json);
    json_error_t err;
    json_t* root = json_loads(json, 0, &err);
    if (!root) {
        free(json);
        fail_msg("Failed to parse fixture JSON %s: %s (line %d)", json_path, err.text, err.line);
        return;
    }
    json_t* expected = json_object_get(root, "expected");
    if (!expected || !json_is_object(expected)) {
        // Default: expect success
        json_decref(root);
        free(json);
        assert_compile_success(json_path);
        return;
    }
    json_t* succ = json_object_get(expected, "success");
    if (succ && json_is_true(succ)) {
        json_t* pcre = json_object_get(expected, "pcre");
        if (pcre && json_is_string(pcre)) {
            const char* expected_pcre = json_string_value(pcre);
            json_decref(root);
            free(json);
            assert_compile_equals_from_json(json_path, expected_pcre);
            return;
        }
        json_decref(root);
        free(json);
        assert_compile_success(json_path);
        return;
    }
    json_t* err_val = json_object_get(expected, "error");
    const char* err_str = err_val && json_is_string(err_val) ? json_string_value(err_val) : "";
    json_decref(root);
    free(json);
    assert_compile_error_contains(json_path, err_str);
}
