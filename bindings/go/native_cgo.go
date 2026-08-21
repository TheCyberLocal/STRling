//go:build cgo

package strling

/*
#cgo linux LDFLAGS: -ldl
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <windows.h>
#else
#include <dlfcn.h>
#endif

typedef struct {
    uint8_t *data;
    size_t len;
} sl_owned_bytes;

typedef uint32_t (*sl_abi_fn)(void);
typedef uint32_t (*sl_execute_fn)(const uint8_t *, size_t, sl_owned_bytes *);
typedef uint32_t (*sl_free_fn)(sl_owned_bytes *);

typedef struct {
    void *library;
    sl_abi_fn abi;
    sl_execute_fn execute;
    sl_free_fn free_owned;
} sl_native_state;

static void sl_error(char *output, size_t capacity, const char *message) {
    if (capacity == 0) return;
    strncpy(output, message, capacity - 1);
    output[capacity - 1] = '\0';
}

static void *sl_load_library(const char *path) {
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

static void *sl_symbol(void *library, const char *name) {
#if defined(_WIN32)
    return (void *)GetProcAddress((HMODULE)library, name);
#else
    return dlsym(library, name);
#endif
}

static void sl_unload_library(void *library) {
#if defined(_WIN32)
    FreeLibrary((HMODULE)library);
#else
    dlclose(library);
#endif
}

static sl_native_state *sl_open(const char *path, char *error, size_t error_capacity) {
    void *library = sl_load_library(path);
    if (library == NULL) {
        sl_error(error, error_capacity, "cannot load native STRling library");
        return NULL;
    }
    sl_abi_fn abi = (sl_abi_fn)(uintptr_t)sl_symbol(library, "strling_interop_abi_version_v1");
    sl_execute_fn execute = (sl_execute_fn)(uintptr_t)sl_symbol(library, "strling_interop_execute_v1");
    sl_free_fn free_owned = (sl_free_fn)(uintptr_t)sl_symbol(library, "strling_interop_owned_bytes_free_v1");
    if (abi == NULL || execute == NULL || free_owned == NULL) {
        sl_unload_library(library);
        sl_error(error, error_capacity, "native library does not export the complete strling.c-abi v1");
        return NULL;
    }
    sl_native_state *state = (sl_native_state *)calloc(1, sizeof(sl_native_state));
    if (state == NULL) {
        sl_unload_library(library);
        sl_error(error, error_capacity, "cannot allocate native STRling client state");
        return NULL;
    }
    state->library = library;
    state->abi = abi;
    state->execute = execute;
    state->free_owned = free_owned;
    return state;
}

static uint32_t sl_abi_version(sl_native_state *state) { return state->abi(); }
static uint32_t sl_execute(sl_native_state *state, const uint8_t *input, size_t input_len, sl_owned_bytes *output) {
    return state->execute(input, input_len, output);
}
static uint32_t sl_free_response(sl_native_state *state, sl_owned_bytes *output) {
    return state->free_owned(output);
}
static void sl_close(sl_native_state *state) {
    if (state == NULL) return;
    sl_unload_library(state->library);
    free(state);
}
*/
import "C"

import (
	"fmt"
	"unsafe"
)

type nativeState struct {
	pointer *C.sl_native_state
}

func loadNativeState(path string) (*nativeState, error) {
	cPath := C.CString(path)
	defer C.free(unsafe.Pointer(cPath))
	errorBuffer := (*C.char)(C.calloc(512, 1))
	if errorBuffer == nil {
		return nil, &NativeError{Kind: ErrorLoad, Detail: "cannot allocate loader error buffer"}
	}
	defer C.free(unsafe.Pointer(errorBuffer))
	pointer := C.sl_open(cPath, errorBuffer, 512)
	if pointer == nil {
		return nil, &NativeError{Kind: ErrorLoad, Detail: C.GoString(errorBuffer)}
	}
	actual := uint32(C.sl_abi_version(pointer))
	if actual != NativeABIVersion {
		C.sl_close(pointer)
		return nil, &NativeError{Kind: ErrorABI, Status: actual, Detail: fmt.Sprintf("expected strling.c-abi %d", NativeABIVersion)}
	}
	return &nativeState{pointer: pointer}, nil
}

func (state *nativeState) execute(request []byte) (response []byte, resultErr error) {
	output := (*C.sl_owned_bytes)(C.calloc(1, C.sizeof_sl_owned_bytes))
	if output == nil {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "cannot allocate response descriptor"}
	}
	defer C.free(unsafe.Pointer(output))
	var input *C.uint8_t
	if len(request) != 0 {
		input = (*C.uint8_t)(unsafe.Pointer(&request[0]))
	}
	defer func() {
		status := uint32(C.sl_free_response(state.pointer, output))
		if resultErr == nil && status != 0 {
			resultErr = &NativeError{Kind: ErrorABI, Status: status, Detail: "native STRling response release failed"}
		}
	}()
	status := uint32(C.sl_execute(state.pointer, input, C.size_t(len(request)), output))
	if status != 0 {
		return nil, &NativeError{Kind: ErrorABI, Status: status, Detail: "native STRling execution failed"}
	}
	length := uint64(output.len)
	if output.data == nil || length == 0 || length > MaxInteropResponseBytes {
		return nil, &NativeError{Kind: ErrorTransport, Detail: "native STRling returned an invalid or oversized response"}
	}
	return C.GoBytes(unsafe.Pointer(output.data), C.int(length)), nil
}

func (state *nativeState) close() error {
	C.sl_close(state.pointer)
	state.pointer = nil
	return nil
}
