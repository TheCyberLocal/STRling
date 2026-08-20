#include "strling/essential.hpp"
#include "strling/simply.hpp"
#include "strling/strling.hpp"

#include <cassert>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

namespace {

void require_true(bool condition,
                  const char *expression,
                  const char *file,
                  int line)
{
    if (!condition) {
        std::fprintf(stderr, "%s:%d: requirement failed: %s\n", file, line,
                     expression);
        std::abort();
    }
}

} // namespace

#undef assert
#define assert(expression) require_true((expression), #expression, __FILE__, __LINE__)

namespace {

std::string read_text(const char *path)
{
    std::ifstream input(path, std::ios::binary);
    assert(input.good());
    return {std::istreambuf_iterator<char>(input),
            std::istreambuf_iterator<char>()};
}

bool contains(const strling::response &value, std::string_view needle)
{
    return value.bytes().find(needle) != std::string_view::npos;
}

void assert_completed(const strling::response &value)
{
    assert(value.transport_status() == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
    assert(value.owns_bytes());
    if (!contains(value, "\"status\":\"completed\"")) {
        std::fprintf(stderr, "%s\n", value.text().c_str());
    }
    assert(contains(value, "\"status\":\"completed\""));
}

void test_raii_move_once()
{
    static_assert(!std::is_copy_constructible_v<strling::response>);
    static_assert(!std::is_copy_assignable_v<strling::response>);
    static_assert(std::is_nothrow_move_constructible_v<strling::response>);
    static_assert(std::is_nothrow_move_assignable_v<strling::response>);

    const std::string request =
        "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
        "\"payload\":{}}";
    strling::response first = strling::client{}.execute_json(request);
    assert_completed(first);
    strling::response second(std::move(first));
    assert(!first.owns_bytes());
    assert_completed(second);
    strling::response third;
    third = std::move(second);
    assert(!second.owns_bytes());
    assert_completed(third);
}

void test_canonical_results_and_profiles()
{
    const std::string success = read_text(
        "spec/contracts/1.0/examples/compile-request/regex-compat-success.json");
    const std::string failure = read_text(
        "spec/contracts/1.0/examples/compile-request/regex-compat-malformed.json");
    const std::string target = read_text(
        "spec/contracts/1.0/examples/compile-request/target-artifact.json");
    const std::string profile =
        read_text("spec/targets/profiles/pcre2-10.43.json");
    const strling::client client;

    strling::response result = client.compile_json(success);
    assert_completed(result);
    assert(contains(result, "\"outcome\":\"succeeded\""));

    result = client.compile_json(failure);
    assert_completed(result);
    assert(contains(result, "\"outcome\":\"failed\""));

    result = client.compile_json(target, profile);
    assert_completed(result);
    assert(contains(result, "\"profile_id\":\"profile:pcre2/10.43\""));

    result = client.compile_json(target);
    assert(result.transport_status() == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
    assert(contains(result, "\"code\":\"STRL-INTEROP-0008\""));
}

void test_simply_registry_and_unicode()
{
    using namespace strling::simply;
    options value_options;
    value_options.case_insensitive = true;
    pattern value = merge(start(),
                          literal("\xF0\x9F\xA6\x80" "e\xCC\x81").as_capture(),
                          end());
    const std::string request = value.builder_request(value_options);
    assert(request.find("\"case_matching\":\"insensitive\"") !=
           std::string::npos);
    assert(request.find("\xF0\x9F\xA6\x80" "e\xCC\x81") !=
           std::string::npos);
    strling::response result = value.compile(value_options);
    assert_completed(result);
    assert(contains(result, "\"status\":\"success\""));

    pattern helper = strling::essential::email();
    assert(helper.builder_request().find("\"helper_id\":\"stdlib.email\"") !=
           std::string::npos);
    result = helper.compile();
    assert_completed(result);
    assert(contains(result, "\"status\":\"success\""));

    pattern unknown = stdlib_helper("stdlib.unknown");
    result = unknown.compile();
    assert_completed(result);
    assert(contains(result, "\"status\":\"failure\""));
    assert(contains(result, "\"code\":\"STRL-SIMPLY-0010\""));
}

void assert_stdlib_helper(strling::simply::pattern helper,
                          std::string_view helper_id)
{
    assert(helper.builder_request().find(helper_id) != std::string::npos);
    strling::response result = helper.compile();
    assert_completed(result);
    assert(contains(result, "\"status\":\"success\""));
}

void test_stdlib_fixture_delegation()
{
    const std::string corpus = read_text("spec/stdlib/essential_5.json");
    assert(corpus.find("STRling Essential 5") != std::string::npos);
    assert(corpus.find("\"dateTime\"") != std::string::npos);
    assert(corpus.find("\"email\"") != std::string::npos);
    assert(corpus.find("\"ip\"") != std::string::npos);
    assert(corpus.find("\"url\"") != std::string::npos);
    assert(corpus.find("\"uuid\"") != std::string::npos);

    assert_stdlib_helper(strling::essential::date_time(), "stdlib.date_time");
    assert_stdlib_helper(strling::essential::email(), "stdlib.email");
    assert_stdlib_helper(strling::essential::ip_v4(), "stdlib.ip");
    assert_stdlib_helper(strling::essential::ip_v6(), "stdlib.ip");
    assert_stdlib_helper(strling::essential::ip_any(), "stdlib.ip");
    assert_stdlib_helper(strling::essential::url(), "stdlib.url");
    assert_stdlib_helper(strling::essential::uuid(), "stdlib.uuid");
    assert_stdlib_helper(strling::essential::uuid_v4(), "stdlib.uuid");
}

void test_native_and_host_refusals()
{
    const std::string invalid_utf8(1, static_cast<char>(0xff));
    strling::response result = strling::client{}.execute(invalid_utf8);
    assert(result.transport_status() == STRLING_INTEROP_STATUS_RESPONSE_WRITTEN);
    assert(contains(result, "\"code\":\"STRL-INTEROP-0001\""));

    bool rejected = false;
    try {
        (void)strling::simply::literal(std::string_view("a\0b", 3));
    } catch (const std::invalid_argument &) {
        rejected = true;
    }
    assert(rejected);
}

} // namespace

int main()
{
    assert(strling::version() == "3.0.0");
    test_raii_move_once();
    test_canonical_results_and_profiles();
    test_simply_registry_and_unicode();
    test_stdlib_fixture_delegation();
    test_native_and_host_refusals();
    return 0;
}
