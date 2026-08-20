#include "strling.h"

#include <stddef.h>
#include <string.h>

#if defined(_WIN32)
#include <windows.h>
#else
#include <pthread.h>
#endif

static int response_contains(const strling_c_result_v1 *result,
                             const char *needle)
{
    size_t needle_length = strlen(needle);
    size_t index;
    if (result->response.len < needle_length) {
        return 0;
    }
    for (index = 0; index <= result->response.len - needle_length; ++index) {
        if (memcmp(result->response.data + index, needle, needle_length) == 0) {
            return 1;
        }
    }
    return 0;
}

static int run_requests(void)
{
    static const char request[] =
        "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
        "\"payload\":{}}";
    int iteration;
    for (iteration = 0; iteration < 64; ++iteration) {
        strling_c_result_v1 result = strling_execute_json_v1(request);
        if (result.transport_status != STRLING_INTEROP_STATUS_RESPONSE_WRITTEN ||
            !response_contains(&result, "\"status\":\"completed\"") ||
            strling_c_result_free_v1(&result) !=
                STRLING_INTEROP_STATUS_RESPONSE_WRITTEN) {
            return 0;
        }
    }
    return 1;
}

#if defined(_WIN32)
static DWORD WINAPI thread_main(LPVOID context)
{
    int *result = (int *)context;
    *result = run_requests();
    return 0;
}
#else
static void *thread_main(void *context)
{
    int *result = (int *)context;
    *result = run_requests();
    return NULL;
}
#endif

int main(void)
{
    enum { THREAD_COUNT = 8 };
    int results[THREAD_COUNT] = {0};
    int index;
#if defined(_WIN32)
    HANDLE threads[THREAD_COUNT];
    for (index = 0; index < THREAD_COUNT; ++index) {
        threads[index] = CreateThread(NULL, 0, thread_main, &results[index], 0,
                                      NULL);
        if (threads[index] == NULL) {
            return 1;
        }
    }
    if (WaitForMultipleObjects(THREAD_COUNT, threads, TRUE, INFINITE) !=
        WAIT_OBJECT_0) {
        return 1;
    }
    for (index = 0; index < THREAD_COUNT; ++index) {
        CloseHandle(threads[index]);
    }
#else
    pthread_t threads[THREAD_COUNT];
    for (index = 0; index < THREAD_COUNT; ++index) {
        if (pthread_create(&threads[index], NULL, thread_main,
                           &results[index]) != 0) {
            return 1;
        }
    }
    for (index = 0; index < THREAD_COUNT; ++index) {
        if (pthread_join(threads[index], NULL) != 0) {
            return 1;
        }
    }
#endif
    for (index = 0; index < THREAD_COUNT; ++index) {
        if (!results[index]) {
            return 1;
        }
    }
    return 0;
}
