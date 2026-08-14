/* Generated from spec/interop/1.0/abi.json. Do not edit. */
#ifndef STRLING_INTEROP_H
#define STRLING_INTEROP_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32) && defined(STRLING_INTEROP_SHARED)
#  if defined(STRLING_INTEROP_BUILD)
#    define STRLING_INTEROP_API __declspec(dllexport)
#  else
#    define STRLING_INTEROP_API __declspec(dllimport)
#  endif
#elif defined(__GNUC__) && defined(STRLING_INTEROP_SHARED)
#  define STRLING_INTEROP_API __attribute__((visibility("default")))
#else
#  define STRLING_INTEROP_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef uint32_t strling_interop_status_v1;

enum {
    STRLING_INTEROP_STATUS_RESPONSE_WRITTEN = 0,
    STRLING_INTEROP_STATUS_INVALID_ARGUMENT = 1,
    STRLING_INTEROP_STATUS_OUTPUT_NOT_EMPTY = 2,
    STRLING_INTEROP_STATUS_PANIC = 3,
    STRLING_INTEROP_STATUS_INTERNAL_FAILURE = 4,
};

typedef struct strling_interop_owned_bytes_v1 {
    uint8_t *data;
    size_t len;
} strling_interop_owned_bytes_v1;

STRLING_INTEROP_API uint32_t strling_interop_abi_version_v1(void);
STRLING_INTEROP_API strling_interop_status_v1 strling_interop_execute_v1(const uint8_t *request_data, size_t request_len, strling_interop_owned_bytes_v1 *output);
STRLING_INTEROP_API strling_interop_status_v1 strling_interop_owned_bytes_free_v1(strling_interop_owned_bytes_v1 *output);

#ifdef __cplusplus
}
#endif

#endif /* STRLING_INTEROP_H */
