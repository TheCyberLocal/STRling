#include "strling.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static strling_c_result_v1 empty_result(strling_interop_status_v1 status)
{
    strling_c_result_v1 result;
    result.transport_status = status;
    result.response.data = NULL;
    result.response.len = 0;
    return result;
}

static int checked_add(size_t *total, size_t value)
{
    if (value > SIZE_MAX - *total) {
        return 0;
    }
    *total += value;
    return 1;
}

static strling_c_result_v1 execute_wrapped(const char *prefix,
                                           const char *value,
                                           const char *profile,
                                           const char *suffix)
{
    static const char profile_key[] = ",\"target_profile\":";
    size_t prefix_len;
    size_t value_len;
    size_t profile_len = 0;
    size_t suffix_len;
    size_t total = 0;
    char *request;
    char *cursor;
    strling_c_result_v1 result;

    if (prefix == NULL || value == NULL || suffix == NULL) {
        return empty_result(STRLING_INTEROP_STATUS_INVALID_ARGUMENT);
    }

    prefix_len = strlen(prefix);
    value_len = strlen(value);
    suffix_len = strlen(suffix);
    if (profile != NULL) {
        profile_len = strlen(profile);
    }
    if (!checked_add(&total, prefix_len) || !checked_add(&total, value_len) ||
        (profile != NULL &&
         (!checked_add(&total, sizeof(profile_key) - 1) ||
          !checked_add(&total, profile_len))) ||
        !checked_add(&total, suffix_len) || !checked_add(&total, 1)) {
        return empty_result(STRLING_INTEROP_STATUS_INVALID_ARGUMENT);
    }

    request = (char *)malloc(total);
    if (request == NULL) {
        return empty_result(STRLING_INTEROP_STATUS_INTERNAL_FAILURE);
    }
    cursor = request;
    memcpy(cursor, prefix, prefix_len);
    cursor += prefix_len;
    memcpy(cursor, value, value_len);
    cursor += value_len;
    if (profile != NULL) {
        memcpy(cursor, profile_key, sizeof(profile_key) - 1);
        cursor += sizeof(profile_key) - 1;
        memcpy(cursor, profile, profile_len);
        cursor += profile_len;
    }
    memcpy(cursor, suffix, suffix_len);
    cursor += suffix_len;
    *cursor = '\0';

    result = strling_execute_v1((const uint8_t *)request, total - 1);
    free(request);
    return result;
}

const char *strling_version(void)
{
    return STRLING_C_PACKAGE_VERSION;
}

strling_c_result_v1 strling_execute_v1(const uint8_t *request_data,
                                      size_t request_len)
{
    strling_c_result_v1 result =
        empty_result(STRLING_INTEROP_STATUS_INVALID_ARGUMENT);
    result.transport_status = strling_interop_execute_v1(
        request_data, request_len, &result.response);
    return result;
}

strling_c_result_v1 strling_execute_json_v1(const char *request_json)
{
    if (request_json == NULL) {
        return empty_result(STRLING_INTEROP_STATUS_INVALID_ARGUMENT);
    }
    return strling_execute_v1((const uint8_t *)request_json,
                             strlen(request_json));
}

strling_c_result_v1 strling_compile_json_v1(const char *compile_request_json,
                                           const char *target_profile_json)
{
    return execute_wrapped(
        "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"compile\","
        "\"payload\":{\"compile_request\":",
        compile_request_json,
        target_profile_json,
        "}}");
}

strling_c_result_v1 strling_simply_compile_json_v1(
    const char *builder_request_json,
    const char *target_profile_json)
{
    return execute_wrapped(
        "{\"interop_protocol_version\":\"1.0.0\","
        "\"operation\":\"simply.compile\",\"payload\":{\"builder_request\":",
        builder_request_json,
        target_profile_json,
        "}}");
}

strling_interop_status_v1 strling_c_result_free_v1(strling_c_result_v1 *result)
{
    strling_interop_status_v1 status;
    if (result == NULL) {
        return strling_interop_owned_bytes_free_v1(NULL);
    }
    status = strling_interop_owned_bytes_free_v1(&result->response);
    result->transport_status = status;
    return status;
}
