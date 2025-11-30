/* us_phone_test.cpp — verifies simply API builds the expected US phone regex */
#include <gtest/gtest.h>
#include "strling/simply.hpp"

using namespace strling::simply;

TEST(SimplyPattern, USPhoneBuilderMatchesReference) {
    // Build the phone example exactly like the README/target API
    auto phone = merge({
        start(),
        digit(3).as_capture(),
        any_of("-. ").may(),
        digit(3).as_capture(),
        any_of("-. ").may(),
        digit(4).as_capture(),
        end()
    });

    std::string actual = phone.compile();

    // Expected builder-style optimized pattern (positional captures + optional separators)
    std::string expected = "^(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})$";

    EXPECT_EQ(actual, expected);
}
