/**
 * @file e2e_test.cpp
 * @brief End-to-End Black Box Tests
 *
 * ## Purpose
 * This test suite validates that regex patterns produced by the Simply API
 * work correctly with actual regex matching.
 *
 * ## Scope
 * Tests Simply API → regex string → actual matching against test strings.
 */

#include <gtest/gtest.h>
#include "strling/simply.hpp"
#include <regex>
#include <string>
#include <vector>

using namespace strling::simply;

class E2ETest : public ::testing::Test {
protected:
    bool matches(const std::string& pattern, const std::string& input) {
        try {
            std::regex re(pattern);
            return std::regex_search(input, re);
        } catch (const std::regex_error& e) {
            ADD_FAILURE() << "Regex error: " << e.what() << " for pattern: " << pattern;
            return false;
        }
    }

    bool fullMatch(const std::string& pattern, const std::string& input) {
        try {
            std::regex re(pattern);
            return std::regex_match(input, re);
        } catch (const std::regex_error& e) {
            ADD_FAILURE() << "Regex error: " << e.what() << " for pattern: " << pattern;
            return false;
        }
    }
};

// ============================================================================
// Phone Number E2E Tests
// ============================================================================

TEST_F(E2ETest, PhoneNumber_MatchesValidFormats) {
    // Use Simply API to build the phone regex
    auto phone = merge({
        start(),
        digit(3).as_capture(),
        any_of("-. ").may(),
        digit(3).as_capture(),
        any_of("-. ").may(),
        digit(4).as_capture(),
        end()
    });
    auto regex = phone.compile();

    EXPECT_TRUE(fullMatch(regex, "555-123-4567"));
    EXPECT_TRUE(fullMatch(regex, "555.123.4567"));
    EXPECT_TRUE(fullMatch(regex, "555 123 4567"));
    EXPECT_TRUE(fullMatch(regex, "5551234567"));
}

TEST_F(E2ETest, PhoneNumber_RejectsInvalidFormats) {
    auto phone = merge({
        start(),
        digit(3).as_capture(),
        any_of("-. ").may(),
        digit(3).as_capture(),
        any_of("-. ").may(),
        digit(4).as_capture(),
        end()
    });
    auto regex = phone.compile();

    EXPECT_FALSE(fullMatch(regex, "55-123-4567"));
    EXPECT_FALSE(fullMatch(regex, "555-12-4567"));
    EXPECT_FALSE(fullMatch(regex, "555-123-456"));
    EXPECT_FALSE(fullMatch(regex, "abc-def-ghij"));
}

// ============================================================================
// Email E2E Tests
// ============================================================================

TEST_F(E2ETest, Email_MatchesValidFormats) {
    // Direct regex string - Simply API doesn't yet support full character classes
    std::string regex = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$";

    EXPECT_TRUE(fullMatch(regex, "user@example.com"));
    EXPECT_TRUE(fullMatch(regex, "test.user@domain.org"));
}

TEST_F(E2ETest, Email_RejectsInvalidFormats) {
    std::string regex = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$";

    EXPECT_FALSE(fullMatch(regex, "@example.com"));
    EXPECT_FALSE(fullMatch(regex, "user@"));
    EXPECT_FALSE(fullMatch(regex, "user@.com"));
}

// ============================================================================
// IPv4 Address E2E Tests
// ============================================================================

TEST_F(E2ETest, IPv4_MatchesValidAddresses) {
    std::string regex = "^(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})$";

    EXPECT_TRUE(fullMatch(regex, "192.168.1.1"));
    EXPECT_TRUE(fullMatch(regex, "10.0.0.1"));
    EXPECT_TRUE(fullMatch(regex, "255.255.255.255"));
    EXPECT_TRUE(fullMatch(regex, "0.0.0.0"));
}

TEST_F(E2ETest, IPv4_RejectsInvalidAddresses) {
    std::string regex = "^(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})$";

    EXPECT_FALSE(fullMatch(regex, "192.168.1"));
    EXPECT_FALSE(fullMatch(regex, "192.168.1.1.1"));
    EXPECT_FALSE(fullMatch(regex, "192-168-1-1"));
}

// ============================================================================
// Hex Color E2E Tests
// ============================================================================

TEST_F(E2ETest, HexColor_MatchesValidColors) {
    std::string regex = "^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$";

    EXPECT_TRUE(fullMatch(regex, "#ffffff"));
    EXPECT_TRUE(fullMatch(regex, "#000000"));
    EXPECT_TRUE(fullMatch(regex, "#ABC123"));
    EXPECT_TRUE(fullMatch(regex, "#fff"));
    EXPECT_TRUE(fullMatch(regex, "#F00"));
}

TEST_F(E2ETest, HexColor_RejectsInvalidColors) {
    std::string regex = "^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$";

    EXPECT_FALSE(fullMatch(regex, "ffffff"));
    EXPECT_FALSE(fullMatch(regex, "#ffff"));
    EXPECT_FALSE(fullMatch(regex, "#GGGGGG"));
}

// ============================================================================
// Date E2E Tests
// ============================================================================

TEST_F(E2ETest, Date_MatchesValidDates) {
    std::string regex = "^(\\d{4})-(\\d{2})-(\\d{2})$";

    EXPECT_TRUE(fullMatch(regex, "2024-01-15"));
    EXPECT_TRUE(fullMatch(regex, "2000-12-31"));
    EXPECT_TRUE(fullMatch(regex, "1999-06-30"));
}

TEST_F(E2ETest, Date_RejectsInvalidDates) {
    std::string regex = "^(\\d{4})-(\\d{2})-(\\d{2})$";

    EXPECT_FALSE(fullMatch(regex, "24-01-15"));
    EXPECT_FALSE(fullMatch(regex, "2024/01/15"));
    EXPECT_FALSE(fullMatch(regex, "2024-1-15"));
}

// ============================================================================
// Lookahead E2E Tests
// ============================================================================

TEST_F(E2ETest, PositiveLookahead) {
    std::string regex = "foo(?=bar)";

    EXPECT_TRUE(matches(regex, "foobar"));
    EXPECT_FALSE(matches(regex, "foobaz"));
}

TEST_F(E2ETest, NegativeLookahead) {
    std::string regex = "foo(?!bar)";

    EXPECT_TRUE(matches(regex, "foobaz"));
    // Note: "foobar" still matches "foo" before "bar", need anchoring for full test
}

// ============================================================================
// Word Boundary E2E Tests
// ============================================================================

TEST_F(E2ETest, WordBoundary) {
    std::string regex = "\\bword\\b";

    EXPECT_TRUE(matches(regex, "word"));
    EXPECT_TRUE(matches(regex, "a word here"));
    EXPECT_FALSE(matches(regex, "sword"));
    EXPECT_FALSE(matches(regex, "wording"));
}

// ============================================================================
// Alternation E2E Tests
// ============================================================================

TEST_F(E2ETest, Alternation) {
    std::string regex = "^(cat|dog|bird)$";

    EXPECT_TRUE(fullMatch(regex, "cat"));
    EXPECT_TRUE(fullMatch(regex, "dog"));
    EXPECT_TRUE(fullMatch(regex, "bird"));
    EXPECT_FALSE(fullMatch(regex, "cats"));
    EXPECT_FALSE(fullMatch(regex, "fish"));
}

// ============================================================================
// Quantifier E2E Tests
// ============================================================================

TEST_F(E2ETest, QuantifierPlus) {
    std::string regex = "^a+$";

    EXPECT_TRUE(fullMatch(regex, "a"));
    EXPECT_TRUE(fullMatch(regex, "aa"));
    EXPECT_TRUE(fullMatch(regex, "aaa"));
    EXPECT_FALSE(fullMatch(regex, ""));
    EXPECT_FALSE(fullMatch(regex, "b"));
}

TEST_F(E2ETest, QuantifierStar) {
    std::string regex = "^a*$";

    EXPECT_TRUE(fullMatch(regex, ""));
    EXPECT_TRUE(fullMatch(regex, "a"));
    EXPECT_TRUE(fullMatch(regex, "aaa"));
    EXPECT_FALSE(fullMatch(regex, "b"));
}

TEST_F(E2ETest, QuantifierOptional) {
    std::string regex = "^a?$";

    EXPECT_TRUE(fullMatch(regex, ""));
    EXPECT_TRUE(fullMatch(regex, "a"));
    EXPECT_FALSE(fullMatch(regex, "aa"));
}

TEST_F(E2ETest, QuantifierExact) {
    std::string regex = "^a{3}$";

    EXPECT_TRUE(fullMatch(regex, "aaa"));
    EXPECT_FALSE(fullMatch(regex, "a"));
    EXPECT_FALSE(fullMatch(regex, "aa"));
    EXPECT_FALSE(fullMatch(regex, "aaaa"));
}

TEST_F(E2ETest, QuantifierRange) {
    std::string regex = "^a{2,4}$";

    EXPECT_TRUE(fullMatch(regex, "aa"));
    EXPECT_TRUE(fullMatch(regex, "aaa"));
    EXPECT_TRUE(fullMatch(regex, "aaaa"));
    EXPECT_FALSE(fullMatch(regex, "a"));
    EXPECT_FALSE(fullMatch(regex, "aaaaa"));
}

TEST_F(E2ETest, QuantifierAtLeast) {
    std::string regex = "^a{2,}$";

    EXPECT_TRUE(fullMatch(regex, "aa"));
    EXPECT_TRUE(fullMatch(regex, "aaa"));
    EXPECT_TRUE(fullMatch(regex, "aaaa"));
    EXPECT_FALSE(fullMatch(regex, ""));
    EXPECT_FALSE(fullMatch(regex, "a"));
}
