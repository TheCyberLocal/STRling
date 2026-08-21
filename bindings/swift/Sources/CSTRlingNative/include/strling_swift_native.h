#ifndef STRLING_SWIFT_NATIVE_H
#define STRLING_SWIFT_NATIVE_H

#include <stddef.h>
#include <stdint.h>

typedef struct strling_swift_owned_bytes {
    uint8_t *data;
    size_t len;
} strling_swift_owned_bytes;

void *strling_swift_native_open(const char *path, char *error, size_t error_capacity);
uint32_t strling_swift_native_abi_version(void *state);
uint32_t strling_swift_native_execute(void *state, const uint8_t *input, size_t input_len, strling_swift_owned_bytes *output);
uint32_t strling_swift_native_free(void *state, strling_swift_owned_bytes *output);
void strling_swift_native_close(void *state);

#endif
