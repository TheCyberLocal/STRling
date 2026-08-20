#ifndef STRLING_CPP_SIMPLY_HPP
#define STRLING_CPP_SIMPLY_HPP

#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "strling/native.hpp"
#include "strling_simply.h"

namespace strling::simply {

struct options final {
    bool case_insensitive = false;
    bool ascii_character_domain = false;
    bool include_line_terminators = false;
};

class pattern final {
public:
    ~pattern() noexcept;

    pattern(const pattern &) = delete;
    pattern &operator=(const pattern &) = delete;
    pattern(pattern &&other) noexcept;
    pattern &operator=(pattern &&other) noexcept;

    [[nodiscard]] pattern as_capture() &&;
    [[nodiscard]] pattern may() &&;
    [[nodiscard]] std::string builder_request(options value = {}) const;
    [[nodiscard]] response compile(options value = {}) const;

private:
    friend pattern literal(std::string_view);
    friend pattern digit(int);
    friend pattern any_of(std::string_view);
    friend pattern dot();
    friend pattern start();
    friend pattern end();
    friend pattern capture(pattern);
    friend pattern may(pattern);
    friend pattern stdlib_helper(std::string_view, int);
    friend pattern merge(std::vector<pattern>);

    explicit pattern(sl_pattern_t handle);
    [[nodiscard]] sl_pattern_t release() noexcept;

    sl_pattern_t handle_;
};

[[nodiscard]] pattern literal(std::string_view text);
[[nodiscard]] pattern digit(int count = 1);
[[nodiscard]] pattern any_of(std::string_view characters);
[[nodiscard]] pattern dot();
[[nodiscard]] pattern start();
[[nodiscard]] pattern end();
[[nodiscard]] pattern capture(pattern value);
[[nodiscard]] pattern may(pattern value);
[[nodiscard]] pattern stdlib_helper(
    std::string_view helper_id,
    int version = SL_STDLIB_NO_VERSION);
[[nodiscard]] pattern merge(std::vector<pattern> values);

template <typename... Rest>
[[nodiscard]] pattern merge(pattern first, pattern second, Rest... rest)
{
    std::vector<pattern> values;
    values.reserve(2 + sizeof...(Rest));
    values.emplace_back(std::move(first));
    values.emplace_back(std::move(second));
    (values.emplace_back(std::move(rest)), ...);
    return merge(std::move(values));
}

} // namespace strling::simply

#endif // STRLING_CPP_SIMPLY_HPP
