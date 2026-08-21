#include <R.h>
#include <Rinternals.h>
#include <R_ext/Rdynload.h>
#include <R_ext/Visibility.h>

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <windows.h>
#else
#include <dlfcn.h>
#endif

#define STRLING_ABI_VERSION 1u
#define STRLING_MAX_REQUEST_BYTES 10485760u
#define STRLING_MAX_RESPONSE_BYTES 33554432u

typedef uint32_t (*strling_abi_fn)(void);
typedef uint32_t (*strling_execute_fn)(const uint8_t *, size_t, void *);
typedef uint32_t (*strling_free_fn)(void *);

typedef struct {
    uint8_t *data;
    size_t len;
} strling_owned_bytes;

typedef struct {
#if defined(_WIN32)
    HMODULE handle;
#else
    void *handle;
#endif
    strling_execute_fn execute;
    strling_free_fn release;
    char *path;
    int active;
    int closed;
} strling_r_client;

static int strling_is_absolute(const char *path) {
#if defined(_WIN32)
    return (path[0] != '\0' && path[1] == ':' && (path[2] == '\\' || path[2] == '/')) ||
           (path[0] == '\\' && path[1] == '\\');
#else
    return path[0] == '/';
#endif
}

static int strling_valid_utf8(const uint8_t *data, size_t len) {
    size_t index = 0;
    while (index < len) {
        uint8_t lead = data[index++];
        uint32_t value;
        size_t continuation;
        uint32_t minimum;
        if (lead <= 0x7fu) continue;
        if ((lead & 0xe0u) == 0xc0u) {
            value = lead & 0x1fu; continuation = 1; minimum = 0x80u;
        } else if ((lead & 0xf0u) == 0xe0u) {
            value = lead & 0x0fu; continuation = 2; minimum = 0x800u;
        } else if ((lead & 0xf8u) == 0xf0u) {
            value = lead & 0x07u; continuation = 3; minimum = 0x10000u;
        } else {
            return 0;
        }
        if (continuation > len - index) return 0;
        while (continuation-- != 0) {
            uint8_t byte = data[index++];
            if ((byte & 0xc0u) != 0x80u) return 0;
            value = (value << 6) | (byte & 0x3fu);
        }
        if (value < minimum || value > 0x10ffffu || (value >= 0xd800u && value <= 0xdfffu)) return 0;
    }
    return 1;
}

static void strling_close_client(strling_r_client *client) {
    if (client == NULL || client->closed) return;
    client->closed = 1;
#if defined(_WIN32)
    if (client->handle != NULL) FreeLibrary(client->handle);
    client->handle = NULL;
#else
    if (client->handle != NULL) dlclose(client->handle);
    client->handle = NULL;
#endif
    client->execute = NULL;
    client->release = NULL;
    free(client->path);
    client->path = NULL;
}

static void strling_finalizer(SEXP pointer) {
    strling_r_client *client = (strling_r_client *)R_ExternalPtrAddr(pointer);
    if (client != NULL) {
        if (client->active == 0) strling_close_client(client);
        free(client);
        R_ClearExternalPtr(pointer);
    }
}

static strling_r_client *strling_get_client(SEXP pointer) {
    if (TYPEOF(pointer) != EXTPTRSXP) Rf_error("native STRling client pointer is invalid");
    strling_r_client *client = (strling_r_client *)R_ExternalPtrAddr(pointer);
    if (client == NULL || client->closed) Rf_error("native STRling client is closed");
    return client;
}

SEXP strling_r_open(SEXP path_value) {
    if (TYPEOF(path_value) != STRSXP || XLENGTH(path_value) != 1) Rf_error("native STRling library path must be one string");
    const char *path = Rf_translateCharUTF8(STRING_ELT(path_value, 0));
    FILE *file;
    strling_abi_fn abi;
    uint32_t actual;
    strling_r_client *client;
    if (!strling_is_absolute(path)) Rf_error("native STRling library path must be absolute");
    file = fopen(path, "rb");
    if (file == NULL) Rf_error("native STRling library not found: %s", path);
    fclose(file);
    client = (strling_r_client *)calloc(1, sizeof(*client));
    if (client == NULL) Rf_error("cannot allocate native STRling client");
    client->path = (char *)malloc(strlen(path) + 1u);
    if (client->path == NULL) {
        free(client);
        Rf_error("cannot allocate native STRling path");
    }
    strcpy(client->path, path);
#if defined(_WIN32)
    client->handle = LoadLibraryA(path);
    if (client->handle != NULL) {
        abi = (strling_abi_fn)(void *)GetProcAddress(client->handle, "strling_interop_abi_version_v1");
        client->execute = (strling_execute_fn)(void *)GetProcAddress(client->handle, "strling_interop_execute_v1");
        client->release = (strling_free_fn)(void *)GetProcAddress(client->handle, "strling_interop_owned_bytes_free_v1");
    } else {
        abi = NULL;
    }
#else
    client->handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (client->handle != NULL) {
        *(void **)(&abi) = dlsym(client->handle, "strling_interop_abi_version_v1");
        *(void **)(&client->execute) = dlsym(client->handle, "strling_interop_execute_v1");
        *(void **)(&client->release) = dlsym(client->handle, "strling_interop_owned_bytes_free_v1");
    } else {
        abi = NULL;
    }
#endif
    if (client->handle == NULL || abi == NULL || client->execute == NULL || client->release == NULL) {
        strling_close_client(client);
        free(client);
        Rf_error("cannot load the complete strling.c-abi v1");
    }
    actual = abi();
    if (actual != STRLING_ABI_VERSION) {
        strling_close_client(client);
        free(client);
        Rf_error("expected strling.c-abi %u (status %u)", STRLING_ABI_VERSION, actual);
    }
    SEXP pointer = PROTECT(R_MakeExternalPtr(client, R_NilValue, R_NilValue));
    R_RegisterCFinalizerEx(pointer, strling_finalizer, TRUE);
    UNPROTECT(1);
    return pointer;
}

SEXP strling_r_execute(SEXP pointer, SEXP request) {
    strling_r_client *client = strling_get_client(pointer);
    strling_owned_bytes output = {NULL, 0};
    uint32_t status;
    uint32_t release_status;
    const char *failure = NULL;
    SEXP result = R_NilValue;
    if (TYPEOF(request) != RAWSXP) Rf_error("interop request must be raw UTF-8 JSON bytes");
    if ((size_t)XLENGTH(request) > STRLING_MAX_REQUEST_BYTES) Rf_error("interop request exceeds %u bytes", STRLING_MAX_REQUEST_BYTES);
    client->active += 1;
    status = client->execute(RAW(request), (size_t)XLENGTH(request), &output);
    if (status != 0u) {
        failure = "native STRling execution failed";
    } else if (output.data == NULL || output.len == 0 || output.len > STRLING_MAX_RESPONSE_BYTES) {
        failure = "native STRling returned an invalid or oversized response";
    } else if (!strling_valid_utf8(output.data, output.len)) {
        failure = "native STRling response is not strict UTF-8";
    } else {
        result = PROTECT(Rf_allocVector(RAWSXP, (R_xlen_t)output.len));
        memcpy(RAW(result), output.data, output.len);
    }
    release_status = client->release(&output);
    client->active -= 1;
    if (result != R_NilValue) UNPROTECT(1);
    if (failure != NULL) Rf_error("%s (status %u)", failure, status);
    if (release_status != 0u) Rf_error("native STRling response release failed (status %u)", release_status);
    return result;
}

SEXP strling_r_close(SEXP pointer) {
    strling_r_client *client;
    if (TYPEOF(pointer) != EXTPTRSXP) Rf_error("native STRling client pointer is invalid");
    client = (strling_r_client *)R_ExternalPtrAddr(pointer);
    if (client == NULL || client->closed) return R_NilValue;
    if (client->active != 0) Rf_error("cannot close native STRling client during an active call");
    strling_close_client(client);
    return R_NilValue;
}

SEXP strling_r_is_closed(SEXP pointer) {
    strling_r_client *client;
    if (TYPEOF(pointer) != EXTPTRSXP) return Rf_ScalarLogical(1);
    client = (strling_r_client *)R_ExternalPtrAddr(pointer);
    return Rf_ScalarLogical(client == NULL || client->closed);
}

static const R_CallMethodDef call_methods[] = {
    {"strling_r_open", (DL_FUNC)&strling_r_open, 1},
    {"strling_r_execute", (DL_FUNC)&strling_r_execute, 2},
    {"strling_r_close", (DL_FUNC)&strling_r_close, 1},
    {"strling_r_is_closed", (DL_FUNC)&strling_r_is_closed, 1},
    {NULL, NULL, 0}
};

void attribute_visible R_init_strling(DllInfo *dll) {
    R_registerRoutines(dll, NULL, call_methods, NULL, NULL);
    R_useDynamicSymbols(dll, FALSE);
    R_forceSymbols(dll, TRUE);
}
