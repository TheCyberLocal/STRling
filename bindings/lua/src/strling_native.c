#include <lua.h>
#include <lauxlib.h>

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

#if LUA_VERSION_NUM == 501
#define luaL_newlib(L, functions) (lua_newtable(L), luaL_register(L, NULL, functions))
#define lua_rawlen lua_objlen
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
} strling_client;

static const char *STRLING_CLIENT_METATABLE = "strling.native.client.v1";

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

static strling_client *strling_check_client(lua_State *state, int index) {
    return (strling_client *)luaL_checkudata(state, index, STRLING_CLIENT_METATABLE);
}

static void strling_close_handle(strling_client *client) {
    if (client->closed) return;
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

static int strling_close(lua_State *state) {
    strling_client *client = strling_check_client(state, 1);
    if (client->active != 0) return luaL_error(state, "cannot close native STRling client during an active call");
    strling_close_handle(client);
    return 0;
}

static int strling_gc(lua_State *state) {
    strling_client *client = strling_check_client(state, 1);
    if (client->active == 0) strling_close_handle(client);
    return 0;
}

static int strling_is_closed(lua_State *state) {
    strling_client *client = strling_check_client(state, 1);
    lua_pushboolean(state, client->closed);
    return 1;
}

static int strling_library_path(lua_State *state) {
    strling_client *client = strling_check_client(state, 1);
    if (client->path == NULL) lua_pushnil(state); else lua_pushstring(state, client->path);
    return 1;
}

static int strling_execute(lua_State *state) {
    strling_client *client = strling_check_client(state, 1);
    size_t request_len = 0;
    const char *request = luaL_checklstring(state, 2, &request_len);
    strling_owned_bytes output = {NULL, 0};
    uint32_t status;
    uint32_t release_status;
    if (client->closed || client->execute == NULL || client->release == NULL) {
        return luaL_error(state, "native STRling client is closed");
    }
    if (request_len > STRLING_MAX_REQUEST_BYTES) {
        return luaL_error(state, "interop request exceeds %u bytes", STRLING_MAX_REQUEST_BYTES);
    }
    client->active += 1;
    status = client->execute((const uint8_t *)request, request_len, &output);
    if (status != 0u) {
        client->release(&output);
        client->active -= 1;
        return luaL_error(state, "native STRling execution failed (status %u)", status);
    }
    if (output.data == NULL || output.len == 0 || output.len > STRLING_MAX_RESPONSE_BYTES) {
        client->release(&output);
        client->active -= 1;
        return luaL_error(state, "native STRling returned an invalid or oversized response");
    }
    if (!strling_valid_utf8(output.data, output.len)) {
        client->release(&output);
        client->active -= 1;
        return luaL_error(state, "native STRling response is not strict UTF-8");
    }
    lua_pushlstring(state, (const char *)output.data, output.len);
    release_status = client->release(&output);
    client->active -= 1;
    if (release_status != 0u) {
        lua_pop(state, 1);
        return luaL_error(state, "native STRling response release failed (status %u)", release_status);
    }
    return 1;
}

static int strling_open(lua_State *state) {
    size_t path_len = 0;
    const char *path = luaL_checklstring(state, 1, &path_len);
    strling_client *client;
    strling_abi_fn abi;
    uint32_t actual;
    FILE *file;
    if (strlen(path) != path_len) return luaL_error(state, "native STRling library path contains a null byte");
    if (!strling_is_absolute(path)) return luaL_error(state, "native STRling library path must be absolute");
    file = fopen(path, "rb");
    if (file == NULL) return luaL_error(state, "native STRling library not found: %s", path);
    fclose(file);
    client = (strling_client *)lua_newuserdata(state, sizeof(*client));
    memset(client, 0, sizeof(*client));
    client->path = (char *)malloc(strlen(path) + 1u);
    if (client->path == NULL) return luaL_error(state, "cannot allocate native STRling path");
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
        strling_close_handle(client);
        return luaL_error(state, "cannot load the complete strling.c-abi v1");
    }
    actual = abi();
    if (actual != STRLING_ABI_VERSION) {
        strling_close_handle(client);
        return luaL_error(state, "expected strling.c-abi %u (status %u)", STRLING_ABI_VERSION, actual);
    }
    luaL_getmetatable(state, STRLING_CLIENT_METATABLE);
    lua_setmetatable(state, -2);
    return 1;
}

static const luaL_Reg strling_client_methods[] = {
    {"execute", strling_execute},
    {"close", strling_close},
    {"is_closed", strling_is_closed},
    {"library_path", strling_library_path},
    {NULL, NULL}
};

static const luaL_Reg strling_module_functions[] = {
    {"open", strling_open},
    {NULL, NULL}
};

int luaopen_strling_native(lua_State *state) {
    luaL_newmetatable(state, STRLING_CLIENT_METATABLE);
    lua_pushcfunction(state, strling_gc);
    lua_setfield(state, -2, "__gc");
    lua_newtable(state);
#if LUA_VERSION_NUM == 501
    luaL_register(state, NULL, strling_client_methods);
#else
    luaL_setfuncs(state, strling_client_methods, 0);
#endif
    lua_setfield(state, -2, "__index");
    lua_pop(state, 1);
    luaL_newlib(state, strling_module_functions);
    return 1;
}
