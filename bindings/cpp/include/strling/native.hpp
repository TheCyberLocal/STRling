#ifndef STRLING_CPP_NATIVE_HPP
#define STRLING_CPP_NATIVE_HPP

#include <optional>
#include <string>
#include <string_view>

#include "strling.h"

namespace strling {

inline constexpr std::string_view package_version = "3.0.0";

class response final {
public:
    response() noexcept;
    ~response() noexcept;

    response(const response &) = delete;
    response &operator=(const response &) = delete;
    response(response &&other) noexcept;
    response &operator=(response &&other) noexcept;

    [[nodiscard]] strling_interop_status_v1 transport_status() const noexcept;
    [[nodiscard]] bool owns_bytes() const noexcept;
    [[nodiscard]] std::string_view bytes() const noexcept;
    [[nodiscard]] std::string text() const;

private:
    friend class client;
    explicit response(strling_c_result_v1 native) noexcept;
    void reset() noexcept;

    strling_c_result_v1 native_;
};

class client final {
public:
    [[nodiscard]] response execute(std::string_view request_bytes) const;
    [[nodiscard]] response execute_json(std::string_view request_json) const;
    [[nodiscard]] response compile_json(
        std::string_view compile_request_json,
        std::optional<std::string_view> target_profile_json = std::nullopt) const;
    [[nodiscard]] response simply_compile_json(
        std::string_view builder_request_json,
        std::optional<std::string_view> target_profile_json = std::nullopt) const;
};

[[nodiscard]] std::string_view version() noexcept;

} // namespace strling

#endif // STRLING_CPP_NATIVE_HPP
