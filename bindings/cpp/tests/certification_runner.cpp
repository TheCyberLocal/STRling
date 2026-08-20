#include "strling/strling.hpp"

#include <fstream>
#include <iostream>
#include <iterator>
#include <optional>
#include <string>

namespace {

std::optional<std::string> read_text(const char *path)
{
    std::ifstream input(path, std::ios::binary);
    if (!input.good()) {
        return std::nullopt;
    }
    return std::string(std::istreambuf_iterator<char>(input),
                       std::istreambuf_iterator<char>());
}

} // namespace

int main(int argc, char **argv)
{
    if (argc < 3 || argc > 4) {
        return 2;
    }
    const std::optional<std::string> request = read_text(argv[2]);
    const std::optional<std::string> profile =
        argc == 4 ? read_text(argv[3]) : std::nullopt;
    if (!request.has_value() || (argc == 4 && !profile.has_value())) {
        return 2;
    }
    const strling::client client;
    strling::response result;
    if (std::string_view(argv[1]) == "compile") {
        result = client.compile_json(
            *request,
            profile.has_value()
                ? std::optional<std::string_view>(*profile)
                : std::nullopt);
    } else if (std::string_view(argv[1]) == "simply") {
        result = client.simply_compile_json(
            *request,
            profile.has_value()
                ? std::optional<std::string_view>(*profile)
                : std::nullopt);
    } else {
        return 2;
    }
    if (result.transport_status() != STRLING_INTEROP_STATUS_RESPONSE_WRITTEN ||
        !result.owns_bytes()) {
        return 1;
    }
    std::cout << result.bytes() << '\n';
    return std::cout.good() ? 0 : 1;
}
