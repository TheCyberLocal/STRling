/* Helper tool to call the C binding `strling_compile` function.
 * Usage: inspect_compile <path/to/json>
 * Prints either "SUCCESS: <pattern>\n" or "ERROR: <message> (pos <position>)\n"
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "strling.h"

char* read_file_to_string(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    long sz = ftell(f);
    if (sz < 0) { fclose(f); return NULL; }
    rewind(f);
    char* buf = (char*)malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { free(buf); fclose(f); return NULL; }
    buf[sz] = '\0';
    fclose(f);
    return buf;
}

int main(int argc, char** argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <json_file>\n", argv[0]);
        return 2;
    }
    const char* path = argv[1];
    char* json = read_file_to_string(path);
    if (!json) { fprintf(stderr, "Failed to read %s\n", path); return 2; }
    STRlingResult* res = strling_compile(json, NULL);
    if (!res) { fprintf(stderr, "NULL result from strling_compile\n"); free(json); return 2; }
    if (res->error) {
        fprintf(stdout, "ERROR: %s (pos %d)\n", res->error->message, res->error->position);
    } else {
        fprintf(stdout, "SUCCESS: %s\n", res->pattern ? res->pattern : "");
        if (res->pattern) {
            fprintf(stdout, "HEX:");
            for (size_t i = 0; i < strlen(res->pattern); i++) {
                fprintf(stdout, " %02x", (unsigned char)res->pattern[i]);
            }
            fprintf(stdout, "\n");
        }
    }
    strling_result_free_ptr(res);
    free(json);
    return res->error ? 1 : 0;
}
