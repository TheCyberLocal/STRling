#include "strling_swift_native.h"

#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <windows.h>
#else
#include <dlfcn.h>
#endif

typedef uint32_t (*strling_abi_fn)(void);
typedef uint32_t (*strling_execute_fn)(const uint8_t *, size_t, strling_swift_owned_bytes *);
typedef uint32_t (*strling_free_fn)(strling_swift_owned_bytes *);

typedef struct strling_swift_native_state {
    void *library;
    strling_abi_fn abi;
    strling_execute_fn execute;
    strling_free_fn free_owned;
} strling_swift_native_state;

static void copy_error(char *output, size_t capacity, const char *message) {
    if (capacity == 0) return;
    strncpy(output, message, capacity - 1);
    output[capacity - 1] = '\0';
}

static void *load_library(const char *path) {
#if defined(_WIN32)
    int length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, NULL, 0);
    if (length == 0) return NULL;
    wchar_t *wide = (wchar_t *)calloc((size_t)length, sizeof(wchar_t));
    if (wide == NULL) return NULL;
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path, -1, wide, length) == 0) {
        free(wide);
        return NULL;
    }
    HMODULE handle = LoadLibraryW(wide);
    free(wide);
    return (void *)handle;
#else
    return dlopen(path, RTLD_NOW | RTLD_LOCAL);
#endif
}

static void *load_symbol(void *library, const char *name) {
#if defined(_WIN32)
    return (void *)GetProcAddress((HMODULE)library, name);
#else
    return dlsym(library, name);
#endif
}

static void unload_library(void *library) {
#if defined(_WIN32)
    FreeLibrary((HMODULE)library);
#else
    dlclose(library);
#endif
}

void *strling_swift_native_open(const char *path, char *error, size_t error_capacity) {
    void *library = load_library(path);
    if (library == NULL) {
        copy_error(error, error_capacity, "cannot load native STRling library");
        return NULL;
    }
    strling_abi_fn abi = (strling_abi_fn)(uintptr_t)load_symbol(library, "strling_interop_abi_version_v1");
    strling_execute_fn execute = (strling_execute_fn)(uintptr_t)load_symbol(library, "strling_interop_execute_v1");
    strling_free_fn free_owned = (strling_free_fn)(uintptr_t)load_symbol(library, "strling_interop_owned_bytes_free_v1");
    if (abi == NULL || execute == NULL || free_owned == NULL) {
        unload_library(library);
        copy_error(error, error_capacity, "native library does not export the complete strling.c-abi v1");
        return NULL;
    }
    strling_swift_native_state *state = (strling_swift_native_state *)calloc(1, sizeof(strling_swift_native_state));
    if (state == NULL) {
        unload_library(library);
        copy_error(error, error_capacity, "cannot allocate native STRling client state");
        return NULL;
    }
    state->library = library;
    state->abi = abi;
    state->execute = execute;
    state->free_owned = free_owned;
    return state;
}

uint32_t strling_swift_native_abi_version(void *opaque) {
    strling_swift_native_state *state = (strling_swift_native_state *)opaque;
    return state->abi();
}

uint32_t strling_swift_native_execute(void *opaque, const uint8_t *input, size_t input_len, strling_swift_owned_bytes *output) {
    strling_swift_native_state *state = (strling_swift_native_state *)opaque;
    return state->execute(input, input_len, output);
}

uint32_t strling_swift_native_free(void *opaque, strling_swift_owned_bytes *output) {
    strling_swift_native_state *state = (strling_swift_native_state *)opaque;
    return state->free_owned(output);
}

void strling_swift_native_close(void *opaque) {
    if (opaque == NULL) return;
    strling_swift_native_state *state = (strling_swift_native_state *)opaque;
    unload_library(state->library);
    free(state);
}
