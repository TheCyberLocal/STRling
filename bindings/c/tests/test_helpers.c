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
#include <stdint.h>
#include <ctype.h>

static char *escape_nulls(const char *str, size_t len);
static char *normalize_expected(const char *input);

char *read_file_to_string(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) != 0)
    {
        fclose(f);
        return NULL;
    }
    long sz = ftell(f);
    if (sz < 0)
    {
        fclose(f);
        return NULL;
    }
    rewind(f);
    char *buf = (char *)malloc((size_t)sz + 1);
    if (!buf)
    {
        fclose(f);
        return NULL;
    }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz)
    {
        free(buf);
        fclose(f);
        return NULL;
    }
    buf[sz] = '\0';
    fclose(f);
    return buf;
}

static void _assert_common_compile(STRlingResult *res, const char *json_path)
{
    if (!res)
    {
        fail_msg("Null result returned by strling_compile for %s", json_path);
        return;
    }
}

void assert_compile_equals_from_json(const char *json_path, const char *expected_pattern)
{
    char *json = read_file_to_string(json_path);
    assert_non_null(json);
    STRlingResult *res = strling_compile(json, NULL);
    _assert_common_compile(res, json_path);
    free(json);
    if (res->error)
    {
        char buf[512];
        snprintf(buf, sizeof(buf), "Compilation error: %s (pos %d)", res->error->message, res->error->position);
        fail_msg("%s", buf);
    }
    assert_non_null(res->pattern);
    
    char *norm_expected = normalize_expected(expected_pattern);
    char *norm_actual = normalize_expected(res->pattern);
    
    if (norm_expected && norm_actual) {
        if (strcmp(norm_actual, norm_expected) != 0) {
            printf("Mismatch!\nActual:   %s\nExpected: %s\n", norm_actual, norm_expected);
            printf("Actual hex: ");
            for (const char *p = norm_actual; *p; p++) printf("%02x ", (unsigned char)*p);
            printf("\nExpected hex: ");
            for (const char *p = norm_expected; *p; p++) printf("%02x ", (unsigned char)*p);
            printf("\n");
        }
        assert_string_equal(norm_actual, norm_expected);
        free(norm_expected);
        free(norm_actual);
    } else {
        // Fallback if normalization fails (shouldn't happen given current impl)
        if (norm_expected) free(norm_expected);
        if (norm_actual) free(norm_actual);
        assert_string_equal(res->pattern, expected_pattern);
    }
    strling_result_free_ptr(res);
}

void assert_compile_success(const char *json_path)
{
    char *json = read_file_to_string(json_path);
    assert_non_null(json);
    STRlingResult *res = strling_compile(json, NULL);
    _assert_common_compile(res, json_path);
    free(json);
    if (res->error)
    {
        char buf[512];
        snprintf(buf, sizeof(buf), "Compilation error: %s (pos %d)", res->error->message, res->error->position);
        fail_msg("%s", buf);
    }
    assert_non_null(res->pattern);
    strling_result_free_ptr(res);
}

void assert_compile_error_contains(const char *json_path, const char *expected_substring)
{
    char *json = read_file_to_string(json_path);
    assert_non_null(json);
    STRlingResult *res = strling_compile(json, NULL);
    _assert_common_compile(res, json_path);
    free(json);
    assert_non_null(res->error);
    assert_non_null(res->error->message);
    if (strstr(res->error->message, expected_substring) == NULL)
    {
        fail_msg("Expected error to contain '%s' but got '%s'", expected_substring, res->error->message);
    }
    strling_result_free_ptr(res);
}

void assert_compile_matches_expected(const char *json_path)
{
    char *json = read_file_to_string(json_path);
    assert_non_null(json);
    json_error_t err;
    json_t *root = json_loads(json, JSON_ALLOW_NUL, &err);
    if (!root)
    {
        free(json);
        fail_msg("Failed to parse fixture JSON %s: %s (line %d)", json_path, err.text, err.line);
        return;
    }

    /* Check if we have an AST to compile */
    json_t *input_ast = json_object_get(root, "input_ast");
    if (!input_ast)
        input_ast = json_object_get(root, "pattern");
    if (!input_ast)
        input_ast = json_object_get(root, "root");

    /* Check for expected_error (new format) */
    json_t *expected_error = json_object_get(root, "expected_error");
    if (expected_error && json_is_string(expected_error))
    {
        if (!input_ast)
        {
            /* This is a parser test (no AST provided), skip it for the C compiler */
            printf("[   SKIP   ] %s (Parser test, no AST)\n", json_path);
            json_decref(root);
            free(json);
            return;
        }
        const char *err_str = json_string_value(expected_error);
        assert_compile_error_contains(json_path, err_str);
        json_decref(root);
        free(json);
        return;
    }

    /* Check for expected_codegen (new format) */
    json_t *expected_codegen = json_object_get(root, "expected_codegen");
    if (expected_codegen && json_is_object(expected_codegen))
    {
        json_t *succ = json_object_get(expected_codegen, "success");
        if (succ && json_is_true(succ))
        {
            json_t *pcre = json_object_get(expected_codegen, "pcre");
            if (pcre && json_is_string(pcre))
            {
                const char *expected_pcre = json_string_value(pcre);
                size_t expected_len = json_string_length(pcre);

                /* If expected string contains nulls, we need to escape them for comparison */
                if (strlen(expected_pcre) != expected_len)
                {
                    char *escaped_expected = escape_nulls(expected_pcre, expected_len);

                    /* Compile and check */
                    STRlingResult *res = strling_compile(json, NULL);
                    _assert_common_compile(res, json_path);
                    if (res->error)
                    {
                        char buf[512];
                        snprintf(buf, sizeof(buf), "Compilation error: %s (pos %d)", res->error->message, res->error->position);
                        fail_msg("%s", buf);
                    }
                    assert_non_null(res->pattern);
                    
                    char *norm_expected = normalize_expected(escaped_expected);
                    if (norm_expected) {
                        assert_string_equal(res->pattern, norm_expected);
                        free(norm_expected);
                    } else {
                        assert_string_equal(res->pattern, escaped_expected);
                    }

                    free(escaped_expected);
                    strling_result_free_ptr(res);
                    json_decref(root);
                    free(json);
                    return;
                }

                assert_compile_equals_from_json(json_path, expected_pcre);
                json_decref(root);
                free(json);
                return;
            }
            assert_compile_success(json_path);
            json_decref(root);
            free(json);
            return;
        }
    }

    /* Legacy 'expected' object support */
    json_t *expected = json_object_get(root, "expected");
    if (expected && json_is_object(expected))
    {
        json_t *succ = json_object_get(expected, "success");
        if (succ && json_is_true(succ))
        {
            json_t *pcre = json_object_get(expected, "pcre");
            if (pcre && json_is_string(pcre))
            {
                const char *expected_pcre = json_string_value(pcre);
                assert_compile_equals_from_json(json_path, expected_pcre);
                json_decref(root);
                free(json);
                return;
            }
            assert_compile_success(json_path);
            json_decref(root);
            free(json);
            return;
        }
        json_t *err_val = json_object_get(expected, "error");
        const char *err_str = err_val && json_is_string(err_val) ? json_string_value(err_val) : "";
        assert_compile_error_contains(json_path, err_str);
        json_decref(root);
        free(json);
        return;
    }

    /* Default: expect success */
    assert_compile_success(json_path);
    json_decref(root);
    free(json);
}

/* Helper to escape null bytes in a string for comparison */
static char *escape_nulls(const char *str, size_t len)
{
    size_t new_len = 0;
    for (size_t i = 0; i < len; i++)
    {
        if (str[i] == '\0')
            new_len += 4; /* \x00 */
        else
            new_len++;
    }
    char *res = malloc(new_len + 1);
    if (!res)
        return NULL;
    char *p = res;
    for (size_t i = 0; i < len; i++)
    {
        if (str[i] == '\0')
        {
            strcpy(p, "\\x00");
            p += 4;
        }
        else
        {
            *p++ = str[i];
        }
    }
    *p = '\0';
    return res;
}

static int is_hex(char c)
{
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
}

static char *normalize_expected(const char *input)
{
    if (!input)
        return NULL;

    size_t len = strlen(input);
    size_t cap = len * 4 + 100; // generous buffer
    char *out = malloc(cap);
    if (!out)
        return NULL;

    const char *p = input;
    char *q = out;
    int in_class = 0;

    while (*p)
    {
        if (*p == '\n') { *q++ = '\\'; *q++ = 'n'; p++; continue; }
        if (*p == '\r') { *q++ = '\\'; *q++ = 'r'; p++; continue; }
        if (*p == '\t') { *q++ = '\\'; *q++ = 't'; p++; continue; }
        if (*p == '\f') { *q++ = '\\'; *q++ = 'f'; p++; continue; }
        if (*p == '\v') { *q++ = '\\'; *q++ = 'v'; p++; continue; }

        if ((unsigned char)*p >= 128)
        {
            // UTF-8 sequence - convert to \x{...}
            uint32_t cp = 0;
            int bytes = 0;
            unsigned char c = (unsigned char)*p;

            if ((c & 0xE0) == 0xC0)
            {
                cp = c & 0x1F;
                bytes = 2;
            }
            else if ((c & 0xF0) == 0xE0)
            {
                cp = c & 0x0F;
                bytes = 3;
            }
            else if ((c & 0xF8) == 0xF0)
            {
                cp = c & 0x07;
                bytes = 4;
            }
            else
            {
                // Invalid or unhandled, just copy
                *q++ = *p++;
                continue;
            }

            // Check if we have enough bytes
            int valid = 1;
            const char *chk = p + 1;
            for (int i = 1; i < bytes; i++)
            {
                if (!*chk || (*chk & 0xC0) != 0x80)
                {
                    valid = 0;
                    break;
                }
                chk++;
            }

            if (!valid)
            {
                *q++ = *p++;
                continue;
            }

            p++;
            for (int i = 1; i < bytes; i++)
            {
                cp = (cp << 6) | (*p & 0x3F);
                p++;
            }

            // Emit \x{...}
            q += sprintf(q, "\\x{%x}", cp);
            continue;
        }

        if (*p == '\\')
        {
            // Escape sequence
            if (p[1] == 'x' && is_hex(p[2]) && is_hex(p[3]))
            {
                // \xNN -> \x{NN}
                q += sprintf(q, "\\x{%c%c}", p[2], p[3]);
                p += 4;
                continue;
            }

            /* Normalization of \d -> [\d] etc */
            if (!in_class && (p[1] == 'd' || p[1] == 'D' || p[1] == 'w' || p[1] == 'W' || p[1] == 's' || p[1] == 'S'))
            {
                *q++ = '[';
                *q++ = '\\';
                *q++ = p[1];
                *q++ = ']';
                p += 2;
                continue;
            }

            /* Normalization of \p -> [\p] */
            if (!in_class && (p[1] == 'p' || p[1] == 'P'))
            {
                 const char *brace = strchr(p, '}');
                 if (brace)
                 {
                     *q++ = '[';
                     size_t len = brace - p + 1;
                     memcpy(q, p, len);
                     q += len;
                     p += len;
                     *q++ = ']';
                     continue;
                 }
            }


            // Copy escape
            *q++ = *p++;
            if (*p)
                *q++ = *p++;
            continue;
        }

        /* Normalization of [^\p{...}] -> [\P{...}] */
        if (!in_class && p[0] == '[' && p[1] == '^' && p[2] == '\\' && p[3] == 'p' && p[4] == '{')
        {
             // Find closing brace of \p{...}
             const char *brace = strchr(p + 5, '}');
             if (brace && brace[1] == ']')
             {
                 // Found [^\p{...}]
                 *q++ = '[';
                 *q++ = '\\';
                 *q++ = 'P';
                 *q++ = '{';
                 // Copy content
                 const char *content = p + 5;
                 size_t len = brace - content;
                 memcpy(q, content, len);
                 q += len;
                 *q++ = '}';
                 *q++ = ']';
                 p = brace + 2; // Skip [^\p{...}]
                 continue;
             }
        }

        if (*p == '[' && !in_class)
            in_class = 1;
        else if (*p == ']' && in_class)
            in_class = 0;

        *q++ = *p++;
    }
    *q = '\0';
    return out;
}
