#include "strling/strling.hpp"

#include <array>
#include <string_view>
#include <thread>
#include <vector>

namespace {

bool run_requests()
{
    constexpr std::string_view request =
        "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
        "\"payload\":{}}";
    const strling::client client;
    for (int iteration = 0; iteration < 64; ++iteration) {
        strling::response result = client.execute_json(request);
        if (result.transport_status() !=
                STRLING_INTEROP_STATUS_RESPONSE_WRITTEN ||
            result.bytes().find("\"status\":\"completed\"") ==
                std::string_view::npos) {
            return false;
        }
    }
    return true;
}

} // namespace

int main()
{
    constexpr std::size_t thread_count = 8;
    std::array<bool, thread_count> results{};
    std::vector<std::thread> threads;
    threads.reserve(thread_count);
    for (std::size_t index = 0; index < thread_count; ++index) {
        threads.emplace_back([&results, index] { results[index] = run_requests(); });
    }
    for (std::thread &thread : threads) {
        thread.join();
    }
    for (bool result : results) {
        if (!result) {
            return 1;
        }
    }
    return 0;
}
