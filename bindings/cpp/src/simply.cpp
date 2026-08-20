#include "strling/simply.hpp"

#include <memory>
#include <stdexcept>

namespace {

sl_options_v1 native_options(strling::simply::options value) noexcept
{
    sl_options_v1 native = sl_options_default_v1();
    native.case_insensitive = value.case_insensitive ? 1U : 0U;
    native.ascii_character_domain = value.ascii_character_domain ? 1U : 0U;
    native.include_line_terminators = value.include_line_terminators ? 1U : 0U;
    return native;
}

std::string c_string(std::string_view value)
{
    if (value.find('\0') != std::string_view::npos) {
        throw std::invalid_argument("Simply text contains an embedded NUL byte");
    }
    return std::string(value);
}

} // namespace

namespace strling::simply {

pattern::pattern(sl_pattern_t handle) : handle_(handle)
{
    if (handle_ == nullptr) {
        throw std::invalid_argument("invalid Simply construction value");
    }
}

pattern::~pattern() noexcept
{
    sl_free(handle_);
}

pattern::pattern(pattern &&other) noexcept : handle_(other.release()) {}

pattern &pattern::operator=(pattern &&other) noexcept
{
    if (this != &other) {
        sl_free(handle_);
        handle_ = other.release();
    }
    return *this;
}

sl_pattern_t pattern::release() noexcept
{
    sl_pattern_t value = handle_;
    handle_ = nullptr;
    return value;
}

pattern pattern::as_capture() &&
{
    return capture(std::move(*this));
}

pattern pattern::may() &&
{
    return simply::may(std::move(*this));
}

std::string pattern::builder_request(options value) const
{
    const sl_options_v1 native = native_options(value);
    using owned_string = std::unique_ptr<char, decltype(&sl_string_free_v1)>;
    owned_string request(sl_builder_request_json_v1(handle_, &native),
                         &sl_string_free_v1);
    if (!request) {
        throw std::invalid_argument("Simply construction cannot be serialized");
    }
    return std::string(request.get());
}

response pattern::compile(options value) const
{
    return client{}.simply_compile_json(builder_request(value));
}

pattern literal(std::string_view text)
{
    const std::string native = c_string(text);
    return pattern(sl_literal(native.c_str()));
}

pattern digit(int count)
{
    if (count <= 0) {
        throw std::invalid_argument("digit count must be positive");
    }
    return pattern(sl_digit(count));
}

pattern any_of(std::string_view characters)
{
    const std::string native = c_string(characters);
    return pattern(sl_any_of(native.c_str()));
}

pattern dot()
{
    return pattern(sl_dot());
}

pattern start()
{
    return pattern(sl_start());
}

pattern end()
{
    return pattern(sl_end());
}

pattern capture(pattern value)
{
    sl_pattern_t captured = sl_capture(value.handle_);
    if (captured == nullptr) {
        throw std::invalid_argument("capture construction failed");
    }
    (void)value.release();
    return pattern(captured);
}

pattern may(pattern value)
{
    sl_pattern_t repeated = sl_may(value.handle_);
    if (repeated == nullptr) {
        throw std::invalid_argument("optional construction failed");
    }
    (void)value.release();
    return pattern(repeated);
}

pattern stdlib_helper(std::string_view helper_id, int version)
{
    const std::string native = c_string(helper_id);
    if (native.empty()) {
        throw std::invalid_argument("standard-library helper id must not be empty");
    }
    return pattern(sl_stdlib_helper_v1(native.c_str(), version));
}

pattern merge(std::vector<pattern> values)
{
    if (values.empty()) {
        throw std::invalid_argument("sequence must contain at least one value");
    }
    std::vector<sl_pattern_t> handles;
    handles.reserve(values.size());
    for (const pattern &value : values) {
        handles.push_back(value.handle_);
    }
    sl_pattern_t merged = sl_merge_array_v1(handles.size(), handles.data());
    if (merged == nullptr) {
        throw std::invalid_argument("sequence construction failed");
    }
    for (pattern &value : values) {
        (void)value.release();
    }
    return pattern(merged);
}

} // namespace strling::simply
