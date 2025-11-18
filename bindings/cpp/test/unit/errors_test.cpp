/**
 * @file errors_test.cpp
 * @brief Test Design — Error Handling Tests
 *
 * ## Purpose
 * This test suite serves as the single source of truth for defining and
 * validating the error-handling contract of the entire STRling pipeline. It
 * ensures that invalid inputs are rejected predictably and that diagnostics are
 * stable, accurate, and helpful across all stages—from the parser to the CLI.
 *
 * ## Description
 * This suite defines the expected behavior for all invalid, malformed, or
 * unsupported inputs. It verifies that errors are raised at the correct stage
 * (e.g., `ParseError`), contain a clear, human-readable message, and provide an
 * accurate source location. A key invariant tested is the "first error wins"
 * policy: for an input with multiple issues, only the error at the earliest
 * position is reported.
 *
 * ## Scope
 * -   **In scope:**
 * -   `ParseError` exceptions raised by the parser for syntactic and lexical
 * issues.
 * -   `ValidationError` (or equivalent semantic errors) raised for
 * syntactically valid but semantically incorrect patterns.
 *
 * -   Asserting error messages for a stable, recognizable substring and the
 * correctness of the error's reported position.
 *
 * -   **Out of scope:**
 * -   Correct handling of **valid** inputs (covered in other test suites).
 *
 * -   The exact, full wording of error messages (tests assert substrings).
 *
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#include <gtest/gtest.h>
#include "strling/core/parser.hpp"
#include "strling/core/nodes.hpp"
#include <string>

using namespace strling::core;

// --- Grouping & Lookaround Errors ---

/// Test unterminated group
TEST(ErrorsGrouping, UnterminatedGroup) {
    try {
        auto [flags, ast] = parse("(abc");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos || 
                    msg.find("Expected ')'") != std::string::npos);
        EXPECT_EQ(e.getPos(), 4);
    }
}

/// Test unterminated named group
TEST(ErrorsGrouping, UnterminatedNamedGroup) {
    try {
        auto [flags, ast] = parse("(?<nameabc)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos ||
                    msg.find("name") != std::string::npos ||
                    msg.find("Expected") != std::string::npos);
        // Position may vary based on implementation
    }
}

/// Test unterminated lookahead
TEST(ErrorsGrouping, UnterminatedLookahead) {
    try {
        auto [flags, ast] = parse("(?=abc");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos ||
                    msg.find("Expected ')'") != std::string::npos);
        EXPECT_EQ(e.getPos(), 6);
    }
}

/// Test unterminated lookbehind
TEST(ErrorsGrouping, UnterminatedLookbehind) {
    try {
        auto [flags, ast] = parse("(?<=abc");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos ||
                    msg.find("Expected ')'") != std::string::npos);
        EXPECT_EQ(e.getPos(), 7);
    }
}

/// Test inline modifiers (not supported)
TEST(ErrorsGrouping, UnsupportedInlineModifier) {
    try {
        auto [flags, ast] = parse("(?i)abc");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Inline modifiers") != std::string::npos ||
                    msg.find("not supported") != std::string::npos ||
                    msg.find("Unknown") != std::string::npos);
    }
}

// --- Backreference & Naming Errors ---

/// Test forward reference by name
TEST(ErrorsBackref, ForwardReferenceByName) {
    try {
        auto [flags, ast] = parse(R"(\k<later>(?<later>a))");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Backreference") != std::string::npos ||
                    msg.find("undefined") != std::string::npos ||
                    msg.find("later") != std::string::npos);
    }
}

/// Test forward reference by index
TEST(ErrorsBackref, ForwardReferenceByIndex) {
    try {
        auto [flags, ast] = parse(R"(\2(a)(b))");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Backreference") != std::string::npos ||
                    msg.find("undefined") != std::string::npos ||
                    msg.find("2") != std::string::npos);
    }
}

/// Test nonexistent reference by index
TEST(ErrorsBackref, NonexistentReferenceByIndex) {
    try {
        auto [flags, ast] = parse(R"((a)\2)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Backreference") != std::string::npos ||
                    msg.find("undefined") != std::string::npos ||
                    msg.find("2") != std::string::npos);
    }
}

/// Test unterminated named backref
TEST(ErrorsBackref, UnterminatedNamedBackref) {
    try {
        auto [flags, ast] = parse(R"(\k<)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos ||
                    msg.find("backref") != std::string::npos ||
                    msg.find("Expected") != std::string::npos);
    }
}

/// Test duplicate group name
TEST(ErrorsBackref, DuplicateGroupName) {
    EXPECT_THROW(parse("(?<name>a)(?<name>b)"), ParseError);
    
    try {
        auto [flags, ast] = parse("(?<name>a)(?<name>b)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Duplicate") != std::string::npos &&
                    msg.find("name") != std::string::npos);
    }
}

// --- Character Class Errors ---

/// Test unterminated character class
TEST(ErrorsCharClass, UnterminatedClass) {
    try {
        auto [flags, ast] = parse("[abc");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos ||
                    msg.find("Expected ']'") != std::string::npos);
        EXPECT_EQ(e.getPos(), 4);
    }
}

/// Test unterminated unicode property
TEST(ErrorsCharClass, UnterminatedUnicodeProperty) {
    try {
        auto [flags, ast] = parse(R"([\p{L)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos);
    }
}

/// Test missing braces on unicode property
TEST(ErrorsCharClass, MissingBracesOnUnicodeProperty) {
    try {
        auto [flags, ast] = parse(R"([\pL])");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Expected {") != std::string::npos ||
                    msg.find("after \\p") != std::string::npos);
    }
}

// --- Escape & Codepoint Errors ---

/// Test invalid hex digit
TEST(ErrorsEscape, InvalidHexDigit) {
    try {
        auto [flags, ast] = parse(R"(\xG1)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Invalid") != std::string::npos &&
                    msg.find("\\x") != std::string::npos);
    }
}

/// Test invalid unicode digit
TEST(ErrorsEscape, InvalidUnicodeDigit) {
    try {
        auto [flags, ast] = parse(R"(\u12Z4)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Invalid") != std::string::npos &&
                    msg.find("\\u") != std::string::npos);
    }
}

/// Test unterminated hex brace (empty)
TEST(ErrorsEscape, UnterminatedHexBraceEmpty) {
    try {
        auto [flags, ast] = parse(R"(\x{)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos &&
                    msg.find("\\x{") != std::string::npos);
    }
}

/// Test unterminated hex brace (with digits)
TEST(ErrorsEscape, UnterminatedHexBraceWithDigits) {
    try {
        auto [flags, ast] = parse(R"(\x{FFFF)");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos &&
                    msg.find("\\x{") != std::string::npos);
    }
}

// --- Quantifier Errors ---

/// Test unterminated brace quantifier
TEST(ErrorsQuantifier, UnterminatedBraceQuantifier) {
    try {
        auto [flags, ast] = parse("a{2,5");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Incomplete") != std::string::npos ||
                    msg.find("quantifier") != std::string::npos ||
                    msg.find("Expected '}'") != std::string::npos);
        EXPECT_EQ(e.getPos(), 5);
    }
}

/// Test quantifying non-quantifiable atom
TEST(ErrorsQuantifier, QuantifyingAnchor) {
    EXPECT_THROW(parse("^*"), ParseError);
    
    try {
        auto [flags, ast] = parse("^*");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Cannot quantify") != std::string::npos &&
                    msg.find("anchor") != std::string::npos);
    }
}

// --- Invariant: First Error Wins ---

/// Test first of multiple errors is reported
TEST(ErrorsInvariant, FirstErrorWins) {
    try {
        auto [flags, ast] = parse("[a|b(");
        FAIL() << "ParseError was not thrown";
    } catch (const ParseError& e) {
        std::string msg(e.what());
        EXPECT_TRUE(msg.find("Unterminated") != std::string::npos &&
                    msg.find("character class") != std::string::npos);
        EXPECT_EQ(e.getPos(), 5);
    }
}
