#include "strling.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *read_text(const char *path)
{
    FILE *file = fopen(path, "rb");
    long length;
    char *text;
    size_t read;
    if (file == NULL || fseek(file, 0, SEEK_END) != 0) {
        return NULL;
    }
    length = ftell(file);
    if (length < 0 || fseek(file, 0, SEEK_SET) != 0) {
        (void)fclose(file);
        return NULL;
    }
    text = (char *)malloc((size_t)length + 1);
    if (text == NULL) {
        (void)fclose(file);
        return NULL;
    }
    read = fread(text, 1, (size_t)length, file);
    if (read != (size_t)length || fclose(file) != 0) {
        free(text);
        return NULL;
    }
    text[read] = '\0';
    return text;
}

int main(int argc, char **argv)
{
    char *request;
    char *profile = NULL;
    strling_c_result_v1 result;
    int ok;
    if (argc < 3 || argc > 4) {
        return 2;
    }
    request = read_text(argv[2]);
    if (request == NULL) {
        return 2;
    }
    if (argc == 4) {
        profile = read_text(argv[3]);
        if (profile == NULL) {
            free(request);
            return 2;
        }
    }
    if (strcmp(argv[1], "compile") == 0) {
        result = strling_compile_json_v1(request, profile);
    } else if (strcmp(argv[1], "simply") == 0) {
        result = strling_simply_compile_json_v1(request, profile);
    } else {
        free(profile);
        free(request);
        return 2;
    }
    ok = result.transport_status == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN &&
         result.response.data != NULL &&
         fwrite(result.response.data, 1, result.response.len, stdout) ==
             result.response.len &&
         fputc('\n', stdout) != EOF;
    if (strling_c_result_free_v1(&result) !=
        STRLING_INTEROP_STATUS_RESPONSE_WRITTEN) {
        ok = 0;
    }
    free(profile);
    free(request);
    return ok ? 0 : 1;
}
