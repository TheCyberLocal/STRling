#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <ctype.h>
#include <stdint.h>
#include "../deps/parson.h"
#include "../include/strling.h"

/* Helper to read file content */
static char *read_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long length = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buffer = (char *)malloc(length + 1);
    if (buffer) {
        fread(buffer, 1, length, f);
        buffer[length] = '\0';
    }
    fclose(f);
    return buffer;
}

/* Helper to check if string ends with suffix */
static int ends_with(const char *str, const char *suffix) {
    if (!str || !suffix) return 0;
    size_t len_str = strlen(str);
    size_t len_suffix = strlen(suffix);
    if (len_suffix > len_str) return 0;
    return strncmp(str + len_str - len_suffix, suffix, len_suffix) == 0;
}

static int is_hex(char c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
}

/* Normalize pattern for comparison (ported from test_helpers.c) */
static char *normalize_expected(const char *input, size_t len)
{
    if (!input)
        return NULL;

    size_t cap = len * 6 + 100; // generous buffer (null byte -> \x{00} is 6 chars)
    char *out = (char *)malloc(cap);
    if (!out)
        return NULL;

    const char *p = input;
    const char *end = input + len;
    char *q = out;
    int in_class = 0;

    while (p < end)
    {
        if (*p == '\0') { 
            // Handle null byte
            q += sprintf(q, "\\x{00}");
            p++;
            continue;
        }
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

int main(int argc, char **argv) {
    const char *spec_dir_path = "../../tests/spec";
    DIR *dir;
    struct dirent *ent;
    int total_tests = 0;
    int passed_tests = 0;
    int skipped_tests = 0;
    int failed_tests = 0;

    /* Allow overriding spec dir via env var or arg if needed, but default is fine */
    if (argc > 1) {
        spec_dir_path = argv[1];
    }

    dir = opendir(spec_dir_path);
    if (!dir) {
        fprintf(stderr, "Error: Could not open directory %s\n", spec_dir_path);
        return 1;
    }

    printf("Running conformance tests from %s...\n", spec_dir_path);

    while ((ent = readdir(dir)) != NULL) {
        if (!ends_with(ent->d_name, ".json")) {
            continue;
        }

        char file_path[1024];
        snprintf(file_path, sizeof(file_path), "%s/%s", spec_dir_path, ent->d_name);

        char *file_content = read_file(file_path);
        if (!file_content) {
            fprintf(stderr, "Failed to read file: %s\n", file_path);
            continue;
        }

        JSON_Value *root_value = json_parse_string(file_content);
        if (!root_value) {
            fprintf(stderr, "Failed to parse JSON: %s\n", file_path);
            free(file_content);
            continue;
        }

        JSON_Object *root_obj = json_value_get_object(root_value);
        
        /* Check for input_ast */
        if (!json_object_has_value(root_obj, "input_ast")) {
            /* Skip parser-only tests or incomplete tests */
            // printf("Skipped (no input_ast): %s\n", ent->d_name);
            skipped_tests++;
            json_value_free(root_value);
            free(file_content);
            continue;
        }

        /* Check for expected_codegen */
        if (!json_object_has_value(root_obj, "expected_codegen")) {
             // printf("Skipped (no expected_codegen): %s\n", ent->d_name);
             skipped_tests++;
             json_value_free(root_value);
             free(file_content);
             continue;
        }

        JSON_Object *expected_codegen = json_object_get_object(root_obj, "expected_codegen");
        int expected_success = json_object_get_boolean(expected_codegen, "success");
        const char *expected_pcre = json_object_get_string(expected_codegen, "pcre");
        size_t expected_pcre_len = json_object_get_string_len(expected_codegen, "pcre");
        const char *expected_error = json_object_get_string(root_obj, "expected_error");

        /* Run compilation */
        /* Note: strling_compile takes the whole JSON string and looks for 'input_ast' or 'pattern' */
        /* The spec files have 'input_ast', so we can pass the file content directly. */
        
        STRlingResult *result = strling_compile(file_content, NULL);
        
        int test_passed = 0;

        if (expected_success) {
            if (result->error) {
                printf("FAIL: %s\n  Expected success, got error: %s\n", ent->d_name, result->error->message);
            } else if (!result->pattern) {
                printf("FAIL: %s\n  Expected success, got NULL pattern\n", ent->d_name);
            } else {
                char *norm_expected = normalize_expected(expected_pcre, expected_pcre_len);
                char *norm_actual = normalize_expected(result->pattern, result->pattern ? strlen(result->pattern) : 0);
                
                if (norm_expected && norm_actual && strcmp(norm_actual, norm_expected) == 0) {
                    test_passed = 1;
                } else {
                    printf("FAIL: %s\n  Pattern mismatch\n  Expected: %s\n  Actual:   %s\n", 
                           ent->d_name, 
                           norm_expected ? norm_expected : expected_pcre, 
                           norm_actual ? norm_actual : result->pattern);
                }
                
                if (norm_expected) free(norm_expected);
                if (norm_actual) free(norm_actual);
            }
        } else {
            /* Expected failure */
            if (!result->error) {
                printf("FAIL: %s\n  Expected error, got success: %s\n", ent->d_name, result->pattern);
            } else {
                /* Optionally check error message if provided in spec */
                /* For now, just checking that it failed is enough for basic conformance, 
                   but if expected_error is present, we could check it. */
                test_passed = 1;
            }
        }

        if (test_passed) {
            passed_tests++;
        } else {
            failed_tests++;
        }
        total_tests++;

        strling_result_free_ptr(result);
        json_value_free(root_value);
        free(file_content);
    }

    closedir(dir);

    printf("\n--------------------------------------------------\n");
    printf("Conformance Test Summary:\n");
    printf("  Total Tests Run: %d\n", total_tests);
    printf("  Passed:          %d\n", passed_tests);
    printf("  Failed:          %d\n", failed_tests);
    printf("  Skipped:         %d\n", skipped_tests);
    printf("--------------------------------------------------\n");

    if (failed_tests > 0) {
        return 1;
    }
    return 0;
}
