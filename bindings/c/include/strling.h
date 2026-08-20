/* Canonical STRling C adapter over strling.c-abi v1. */
#ifndef STRLING_H
#define STRLING_H

#include <stddef.h>
#include <stdint.h>

#include "strling_interop.h"

#ifdef __cplusplus
extern "C" {
#endif

#define STRLING_C_ADAPTER_ABI_VERSION 1
#define STRLING_C_PACKAGE_VERSION "3.0.0"

/*
 * A transport status and, on RESPONSE_WRITTEN, one response buffer owned by
 * the interop library. Canonical failed compilations are JSON result values;
 * they do not change transport_status.
 */
typedef struct strling_c_result_v1 {
    strling_interop_status_v1 transport_status;
    strling_interop_owned_bytes_v1 response;
} strling_c_result_v1;

/* Host-package version. Compiler, protocol, and target versions are separate. */
const char *strling_version(void);

/* Execute exact borrowed request bytes through strling.c-abi v1. */
strling_c_result_v1 strling_execute_v1(const uint8_t *request_data,
                                      size_t request_len);

/* Execute one NUL-terminated UTF-8 interop envelope. */
strling_c_result_v1 strling_execute_json_v1(const char *request_json);

/*
 * Mechanically wrap a canonical CompileRequest JSON value and optional exact
 * TargetProfile JSON value in a strling.interop compile envelope.
 */
strling_c_result_v1 strling_compile_json_v1(const char *compile_request_json,
                                           const char *target_profile_json);

/*
 * Mechanically wrap a Simply 1.0/1.1 BuilderRequest JSON value and optional
 * exact TargetProfile JSON value in a strling.interop simply.compile envelope.
 */
strling_c_result_v1 strling_simply_compile_json_v1(
    const char *builder_request_json,
    const char *target_profile_json);

/* Release and zero the same owned response descriptor. Repeated free is safe. */
strling_interop_status_v1 strling_c_result_free_v1(strling_c_result_v1 *result);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_H */
