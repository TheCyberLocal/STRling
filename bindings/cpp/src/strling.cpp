#include "strling/native.hpp"

#include <cstdint>
#include <stdexcept>
#include <utility>

namespace {

strling_c_result_v1 empty_native() noexcept
{
    strling_c_result_v1 value{};
    value.transport_status = STRLING_INTEROP_STATUS_INVALID_ARGUMENT;
    return value;
}

std::string nul_terminated(std::string_view value)
{
    if (value.find('\0') != std::string_view::npos) {
        throw std::invalid_argument("canonical JSON contains an embedded NUL byte");
    }
    return std::string(value);
}

} // namespace

namespace strling {

response::response() noexcept : native_(empty_native()) {}

response::response(strling_c_result_v1 native) noexcept : native_(native) {}

response::~response() noexcept
{
    reset();
}

response::response(response &&other) noexcept : native_(other.native_)
{
    other.native_ = empty_native();
}

response &response::operator=(response &&other) noexcept
{
    if (this != &other) {
        reset();
        native_ = other.native_;
        other.native_ = empty_native();
    }
    return *this;
}

strling_interop_status_v1 response::transport_status() const noexcept
{
    return native_.transport_status;
}

bool response::owns_bytes() const noexcept
{
    return native_.response.data != nullptr;
}

std::string_view response::bytes() const noexcept
{
    if (native_.response.data == nullptr) {
        return {};
    }
    return {reinterpret_cast<const char *>(native_.response.data),
            native_.response.len};
}

std::string response::text() const
{
    return std::string(bytes());
}

void response::reset() noexcept
{
    if (native_.response.data != nullptr) {
        (void)strling_c_result_free_v1(&native_);
    }
    native_ = empty_native();
}

response client::execute(std::string_view request_bytes) const
{
    const auto *data = reinterpret_cast<const std::uint8_t *>(request_bytes.data());
    return response(strling_execute_v1(data, request_bytes.size()));
}

response client::execute_json(std::string_view request_json) const
{
    return execute(request_json);
}

response client::compile_json(
    std::string_view compile_request_json,
    std::optional<std::string_view> target_profile_json) const
{
    const std::string request = nul_terminated(compile_request_json);
    const std::optional<std::string> profile =
        target_profile_json.has_value()
            ? std::optional<std::string>(nul_terminated(*target_profile_json))
            : std::nullopt;
    return response(strling_compile_json_v1(
        request.c_str(), profile.has_value() ? profile->c_str() : nullptr));
}

response client::simply_compile_json(
    std::string_view builder_request_json,
    std::optional<std::string_view> target_profile_json) const
{
    const std::string request = nul_terminated(builder_request_json);
    const std::optional<std::string> profile =
        target_profile_json.has_value()
            ? std::optional<std::string>(nul_terminated(*target_profile_json))
            : std::nullopt;
    return response(strling_simply_compile_json_v1(
        request.c_str(), profile.has_value() ? profile->c_str() : nullptr));
}

std::string_view version() noexcept
{
    return package_version;
}

} // namespace strling
