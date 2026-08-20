#include "strling.h"
#include "strling_essential.h"
#include "strling_simply.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void require_true(int condition,
                         const char *expression,
                         const char *file,
                         int line)
{
    if (!condition) {
        fprintf(stderr, "%s:%d: requirement failed: %s\n", file, line,
                expression);
        abort();
    }
}

#undef assert
#define assert(expression) require_true((expression), #expression, __FILE__, __LINE__)

static char *read_text(const char *path)
{
    FILE *file = fopen(path, "rb");
    long length;
    char *text;
    size_t read;
    assert(file != NULL);
    assert(fseek(file, 0, SEEK_END) == 0);
    length = ftell(file);
    assert(length >= 0);
    assert(fseek(file, 0, SEEK_SET) == 0);
    text = (char *)malloc((size_t)length + 1);
    assert(text != NULL);
    read = fread(text, 1, (size_t)length, file);
    assert(read == (size_t)length);
    text[read] = '\0';
    assert(fclose(file) == 0);
    return text;
}

static int response_contains(const strling_c_result_v1 *result,
                             const char *needle)
{
    size_t needle_length = strlen(needle);
    size_t index;
    if (needle_length == 0 || result->response.len < needle_length) {
        return 0;
    }
    for (index = 0; index <= result->response.len - needle_length; ++index) {
        if (memcmp(result->response.data + index, needle, needle_length) == 0) {
            return 1;
        }
    }
    return 0;
}

static void assert_completed(strling_c_result_v1 *result)
{
    assert(result->transport_status == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
    assert(result->response.data != NULL);
    if (!response_contains(result, "\"status\":\"completed\"")) {
        (void)fwrite(result->response.data, 1, result->response.len, stderr);
        (void)fputc('\n', stderr);
    }
    assert(response_contains(result, "\"status\":\"completed\""));
}

static void release(strling_c_result_v1 *result)
{
    assert(strling_c_result_free_v1(result) ==
           STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
    assert(result->response.data == NULL);
    assert(result->response.len == 0);
}

static void test_describe_and_ownership(void)
{
    char request[] =
        "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
        "\"payload\":{}}";
    strling_c_result_v1 result = strling_execute_json_v1(request);
    request[0] = 'X';
    assert_completed(&result);
    assert(response_contains(&result, "\"contract_id\":\"strling.interop\""));
    release(&result);
    release(&result);
    assert(strling_c_result_free_v1(NULL) ==
           STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
}

static void test_compile_results_and_profiles(void)
{
    char *success = read_text(
        "spec/contracts/1.0/examples/compile-request/regex-compat-success.json");
    char *failure = read_text(
        "spec/contracts/1.0/examples/compile-request/regex-compat-malformed.json");
    char *target = read_text(
        "spec/contracts/1.0/examples/compile-request/target-artifact.json");
    char *profile_1042 = read_text("spec/targets/profiles/pcre2-10.42.json");
    char *profile_1043 = read_text("spec/targets/profiles/pcre2-10.43.json");
    strling_c_result_v1 result = strling_compile_json_v1(success, NULL);

    assert_completed(&result);
    assert(response_contains(&result, "\"outcome\":\"succeeded\""));
    release(&result);

    result = strling_compile_json_v1(failure, NULL);
    assert_completed(&result);
    assert(response_contains(&result, "\"outcome\":\"failed\""));
    release(&result);

    result = strling_compile_json_v1(target, profile_1043);
    assert_completed(&result);
    assert(response_contains(&result, "\"outcome\":\"succeeded\""));
    assert(response_contains(
        &result, "\"profile_id\":\"profile:pcre2/10.43\""));
    release(&result);

    result = strling_compile_json_v1(target, NULL);
    assert(result.transport_status == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
    assert(response_contains(&result, "\"code\":\"STRL-INTEROP-0008\""));
    release(&result);

    result = strling_compile_json_v1(target, profile_1042);
    assert(result.transport_status == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
    assert(response_contains(&result, "\"code\":\"STRL-INTEROP-0008\""));
    release(&result);

    free(success);
    free(failure);
    free(target);
    free(profile_1042);
    free(profile_1043);
}

static void test_simply_and_registry_delegation(void)
{
    sl_options_v1 options = sl_options_default_v1();
    sl_pattern_t pattern;
    char *builder_request;
    strling_c_result_v1 result;

    options.case_insensitive = 1;
    pattern = sl_merge(3, sl_start(),
                       sl_capture(sl_literal("\xF0\x9F\xA6\x80" "e\xCC\x81")),
                       sl_end());
    assert(pattern != NULL);
    builder_request = sl_builder_request_json_v1(pattern, &options);
    assert(builder_request != NULL);
    assert(strstr(builder_request, "\"case_matching\":\"insensitive\"") !=
           NULL);
    assert(strstr(builder_request, "\xF0\x9F\xA6\x80" "e\xCC\x81") != NULL);
    sl_string_free_v1(builder_request);
    result = sl_compile_v1(pattern, &options);
    assert_completed(&result);
    assert(response_contains(&result, "\"status\":\"success\""));
    release(&result);
    sl_free(pattern);

    pattern = sl_email();
    assert(pattern != NULL);
    builder_request = sl_builder_request_json_v1(pattern, NULL);
    assert(builder_request != NULL);
    assert(strstr(builder_request, "\"helper_id\":\"stdlib.email\"") != NULL);
    sl_string_free_v1(builder_request);
    result = sl_compile_v1(pattern, NULL);
    assert_completed(&result);
    assert(response_contains(&result, "\"status\":\"success\""));
    release(&result);
    sl_free(pattern);

    pattern = sl_stdlib_helper_v1("stdlib.unknown", SL_STDLIB_NO_VERSION);
    assert(pattern != NULL);
    result = sl_compile_v1(pattern, NULL);
    assert_completed(&result);
    assert(response_contains(&result, "\"status\":\"failure\""));
    assert(response_contains(&result, "\"code\":\"STRL-SIMPLY-0010\""));
    release(&result);
    sl_free(pattern);

    pattern = sl_merge(2, sl_literal("owned-before-refusal"), NULL);
    assert(pattern == NULL);
}

static void assert_stdlib_helper(sl_pattern_t pattern, const char *helper_id)
{
    char *builder_request;
    strling_c_result_v1 result;

    assert(pattern != NULL);
    builder_request = sl_builder_request_json_v1(pattern, NULL);
    assert(builder_request != NULL);
    assert(strstr(builder_request, helper_id) != NULL);
    sl_string_free_v1(builder_request);
    result = sl_compile_v1(pattern, NULL);
    assert_completed(&result);
    assert(response_contains(&result, "\"status\":\"success\""));
    release(&result);
    sl_free(pattern);
}

static void test_stdlib_fixture_delegation(void)
{
    char *corpus = read_text("spec/stdlib/essential_5.json");

    assert(strstr(corpus, "STRling Essential 5") != NULL);
    assert(strstr(corpus, "\"dateTime\"") != NULL);
    assert(strstr(corpus, "\"email\"") != NULL);
    assert(strstr(corpus, "\"ip\"") != NULL);
    assert(strstr(corpus, "\"url\"") != NULL);
    assert(strstr(corpus, "\"uuid\"") != NULL);
    free(corpus);

    assert_stdlib_helper(sl_date_time(), "stdlib.date_time");
    assert_stdlib_helper(sl_email(), "stdlib.email");
    assert_stdlib_helper(sl_ip_v4(), "stdlib.ip");
    assert_stdlib_helper(sl_ip_v6(), "stdlib.ip");
    assert_stdlib_helper(sl_ip_any(), "stdlib.ip");
    assert_stdlib_helper(sl_url(), "stdlib.url");
    assert_stdlib_helper(sl_uuid(), "stdlib.uuid");
    assert_stdlib_helper(sl_uuid_v4(), "stdlib.uuid");
}

static void test_native_failures_are_distinct(void)
{
    const uint8_t invalid_utf8[] = {0xff};
    strling_c_result_v1 result = strling_execute_v1(invalid_utf8, 1);
    assert(result.transport_status == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
    assert(response_contains(&result, "\"code\":\"STRL-INTEROP-0001\""));
    release(&result);

    result = strling_execute_v1(NULL, 1);
    assert(result.transport_status == STRLING_INTEROP_STATUS_INVALID_ARGUMENT);
    assert(result.response.data == NULL);
    assert(result.response.len == 0);
}

int main(void)
{
    assert(strcmp(strling_version(), "3.0.0") == 0);
    assert(strling_interop_abi_version_v1() == STRLING_C_ADAPTER_ABI_VERSION);
    test_describe_and_ownership();
    test_compile_results_and_profiles();
    test_simply_and_registry_delegation();
    test_stdlib_fixture_delegation();
    test_native_failures_are_distinct();
    return 0;
}
