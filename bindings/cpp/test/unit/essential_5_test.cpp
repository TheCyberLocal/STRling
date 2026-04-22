/**
 * @file essential_5_test.cpp
 * @brief Conformance suite for the Essential RFC-grounded patterns.
 *
 * Loads the canonical fixtures from `spec/stdlib/essential_5.json` and
 * validates each compiled pattern against every "valid" / "invalid"
 * sample using std::regex with full-string anchoring.
 */

#include <gtest/gtest.h>
#include <nlohmann/json.hpp>
#include "strling/essential.hpp"

#include <filesystem>
#include <fstream>
#include <regex>
#include <string>

namespace fs = std::filesystem;
using nlohmann::json;

namespace {

fs::path locate_spec() {
    fs::path p = fs::current_path();
    for (int i = 0; i < 10; ++i) {
        fs::path candidate = p / "spec" / "stdlib" / "essential_5.json";
        if (fs::exists(candidate)) return candidate;
        if (!p.has_parent_path()) break;
        p = p.parent_path();
    }
    return {};
}

const json& spec() {
    static json data = []() {
        fs::path path = locate_spec();
        EXPECT_FALSE(path.empty()) << "essential_5.json fixture not found";
        std::ifstream in(path);
        json j;
        in >> j;
        return j;
    }();
    return data;
}

void run_fixture(const std::string& pattern_str,
                 const std::string& key, const std::string& fixture,
                 bool expect_match) {
    const std::regex re("^(?:" + pattern_str + ")$");
    const auto& items = spec().at("patterns").at(key).at("fixtures").at(fixture);
    for (const auto& s : items) {
        const std::string subject = s.get<std::string>();
        bool got = std::regex_match(subject, re);
        EXPECT_EQ(got, expect_match)
            << "[" << key << "/" << fixture << "] '" << subject << "'";
    }
}

} // namespace

TEST(Essential5, EmailValid)   { run_fixture(strling::essential::email(),    "email",    "valid",            true); }
TEST(Essential5, EmailInvalid) { run_fixture(strling::essential::email(),    "email",    "invalid",          false); }
TEST(Essential5, UrlValid)     { run_fixture(strling::essential::url(),      "url",      "valid",            true); }
TEST(Essential5, UrlInvalid)   { run_fixture(strling::essential::url(),      "url",      "invalid",          false); }
TEST(Essential5, UuidValid)    { run_fixture(strling::essential::uuid(),     "uuid",     "valid_default",    true); }
TEST(Essential5, UuidInvalid)  { run_fixture(strling::essential::uuid(),     "uuid",     "invalid_default",  false); }
TEST(Essential5, UuidV4Valid)  { run_fixture(strling::essential::uuid(4),    "uuid",     "valid_v4",         true); }
TEST(Essential5, UuidV4Invalid){ run_fixture(strling::essential::uuid(4),    "uuid",     "invalid_v4",       false); }
TEST(Essential5, IpV4Valid)    { run_fixture(strling::essential::ip(4),      "ip",       "valid_v4",         true); }
TEST(Essential5, IpV4Invalid)  { run_fixture(strling::essential::ip(4),      "ip",       "invalid_v4",       false); }
TEST(Essential5, IpV6Valid)    { run_fixture(strling::essential::ip(6),      "ip",       "valid_v6",         true); }
TEST(Essential5, IpV6Invalid)  { run_fixture(strling::essential::ip(6),      "ip",       "invalid_v6",       false); }
TEST(Essential5, IpAnyV4)      { run_fixture(strling::essential::ip(),       "ip",       "valid_v4",         true); }
TEST(Essential5, IpAnyV6)      { run_fixture(strling::essential::ip(),       "ip",       "valid_v6",         true); }
TEST(Essential5, DateTimeValid){ run_fixture(strling::essential::date_time(),"dateTime", "valid",            true); }
TEST(Essential5, DateTimeInvalid){ run_fixture(strling::essential::date_time(),"dateTime","invalid",        false); }
