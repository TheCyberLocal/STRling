#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "strling.h"

int main(void)
{
    static const char request[] =
        "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
        "\"payload\":{}}";
    strling_c_result_v1 result = strling_execute_v1(
        (const uint8_t *)request, strlen(request));
    int succeeded =
        result.transport_status == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN &&
        result.response.data != NULL && result.response.len != 0;
    if (strling_c_result_free_v1(&result) !=
        STRLING_INTEROP_STATUS_RESPONSE_WRITTEN) {
        return 1;
    }
    return succeeded ? 0 : 1;
}
