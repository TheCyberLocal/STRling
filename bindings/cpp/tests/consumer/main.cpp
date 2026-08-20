#include "strling/strling.hpp"

#include <string_view>

int main()
{
    constexpr std::string_view request =
        "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
        "\"payload\":{}}";
    strling::response result = strling::client{}.execute_json(request);
    if (result.transport_status() != STRLING_INTEROP_STATUS_RESPONSE_WRITTEN ||
        !result.owns_bytes()) {
        return 1;
    }
    strling::simply::pattern helper = strling::essential::email();
    return helper.builder_request().find("stdlib.email") == std::string::npos;
}
