/**
 * @file flags_and_free_spacing_test.cpp
 * @brief Test Design — Flags and Free-Spacing Mode
 *
 * ## Purpose
 * This test suite validates the correct parsing of the `%flags` directive and the
 * behavioral changes it induces, particularly the free-spacing (`x`) mode. It
 * ensures that flags are correctly identified and stored in the `Flags` object
 * and that the parser correctly handles whitespace and comments when the
 * extended mode is active.
 *
 * ## Description
 * The `%flags` directive is a top-level command in a `.strl` file that modifies
 * the semantics of the entire pattern. This suite tests the parser's ability to
 * correctly consume this directive and apply its effects. The primary focus is
 * on the **`x` flag (extended/free-spacing mode)**, which dramatically alters
 * how the parser handles whitespace and comments. The tests will verify that the
 * parser correctly ignores insignificant characters outside of character classes
 * while treating them as literals inside character classes.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing the `%flags` directive with single and multiple flags (`i`,
 * `m`, `s`, `u`, `x`).
 * -   Handling of various separators (commas, spaces) within the flag
 * list.
 * -   The parser's behavior in free-spacing mode: ignoring whitespace and
 * comments outside character classes.
 * -   The parser's behavior inside a character class when free-spacing mode
 * is active (i.e., treating whitespace and `#` as literals).
 *
 * -   The structure of the `Flags` object produced by the parser and its
 * serialization in the final artifact.
 * -   **Out of scope:**
 * -   The runtime *effect* of the `i`, `m`, `s`, and `u` flags on the regex
 * engine's matching behavior.
 * -   The parsing of other directives like `%engine` or `%lang`.
 *
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#include <gtest/gtest.h>
#include "strling/core/parser.hpp"
#include "strling/core/nodes.hpp"

using namespace strling::core;

// --- Category A: Positive Cases ---

/// Test parsing single flag
TEST(FlagsPositive, ParseSingleFlag) {
    auto [flags, ast] = parse("%flags i");
    EXPECT_TRUE(flags.ignoreCase);
    EXPECT_FALSE(flags.multiline);
    EXPECT_FALSE(flags.dotAll);
    EXPECT_FALSE(flags.unicode);
    EXPECT_FALSE(flags.extended);
}

/// Test parsing multiple flags with commas
TEST(FlagsPositive, ParseMultipleFlagsWithCommas) {
    auto [flags, ast] = parse("%flags i, m, x");
    EXPECT_TRUE(flags.ignoreCase);
    EXPECT_TRUE(flags.multiline);
    EXPECT_FALSE(flags.dotAll);
    EXPECT_FALSE(flags.unicode);
    EXPECT_TRUE(flags.extended);
}

/// Test parsing multiple flags with spaces
TEST(FlagsPositive, ParseMultipleFlagsWithSpaces) {
    auto [flags, ast] = parse("%flags u m s");
    EXPECT_FALSE(flags.ignoreCase);
    EXPECT_TRUE(flags.multiline);
    EXPECT_TRUE(flags.dotAll);
    EXPECT_TRUE(flags.unicode);
    EXPECT_FALSE(flags.extended);
}

/// Test parsing multiple flags with mixed separators
TEST(FlagsPositive, ParseMultipleFlagsMixedSeparators) {
    auto [flags, ast] = parse("%flags i,m s,u x");
    EXPECT_TRUE(flags.ignoreCase);
    EXPECT_TRUE(flags.multiline);
    EXPECT_TRUE(flags.dotAll);
    EXPECT_TRUE(flags.unicode);
    EXPECT_TRUE(flags.extended);
}

/// Test parsing flags with leading/trailing whitespace
TEST(FlagsPositive, ParseFlagsWithWhitespace) {
    auto [flags, ast] = parse("  %flags i  ");
    EXPECT_TRUE(flags.ignoreCase);
    EXPECT_FALSE(flags.multiline);
}

/// Test free-spacing mode ignores whitespace
TEST(FlagsFreespacing, WhitespaceIsIgnored) {
    auto [flags, ast] = parse("%flags x\na b c");
    EXPECT_TRUE(flags.extended);
    
    Seq* seq = dynamic_cast<Seq*>(ast.get());
    ASSERT_NE(seq, nullptr);
    ASSERT_EQ(seq->parts.size(), 3);
    
    Lit* lit0 = dynamic_cast<Lit*>(seq->parts[0].get());
    Lit* lit1 = dynamic_cast<Lit*>(seq->parts[1].get());
    Lit* lit2 = dynamic_cast<Lit*>(seq->parts[2].get());
    
    ASSERT_NE(lit0, nullptr);
    ASSERT_NE(lit1, nullptr);
    ASSERT_NE(lit2, nullptr);
    
    EXPECT_EQ(lit0->value, "a");
    EXPECT_EQ(lit1->value, "b");
    EXPECT_EQ(lit2->value, "c");
}

/// Test free-spacing mode ignores comments
TEST(FlagsFreespacing, CommentsAreIgnored) {
    auto [flags, ast] = parse("%flags x\na # comment\n b");
    EXPECT_TRUE(flags.extended);
    
    Seq* seq = dynamic_cast<Seq*>(ast.get());
    ASSERT_NE(seq, nullptr);
    ASSERT_EQ(seq->parts.size(), 2);
    
    Lit* lit0 = dynamic_cast<Lit*>(seq->parts[0].get());
    Lit* lit1 = dynamic_cast<Lit*>(seq->parts[1].get());
    
    ASSERT_NE(lit0, nullptr);
    ASSERT_NE(lit1, nullptr);
    
    EXPECT_EQ(lit0->value, "a");
    EXPECT_EQ(lit1->value, "b");
}

/// Test escaped whitespace is literal in free-spacing mode
TEST(FlagsFreespacing, EscapedWhitespaceIsLiteral) {
    auto [flags, ast] = parse("%flags x\na\\ b");
    EXPECT_TRUE(flags.extended);
    
    Seq* seq = dynamic_cast<Seq*>(ast.get());
    ASSERT_NE(seq, nullptr);
    ASSERT_EQ(seq->parts.size(), 3);
    
    Lit* lit0 = dynamic_cast<Lit*>(seq->parts[0].get());
    Lit* lit1 = dynamic_cast<Lit*>(seq->parts[1].get());
    Lit* lit2 = dynamic_cast<Lit*>(seq->parts[2].get());
    
    ASSERT_NE(lit0, nullptr);
    ASSERT_NE(lit1, nullptr);
    ASSERT_NE(lit2, nullptr);
    
    EXPECT_EQ(lit0->value, "a");
    EXPECT_EQ(lit1->value, " ");
    EXPECT_EQ(lit2->value, "b");
}

// --- Category B: Negative Cases ---

/// Test rejection of unknown flag
TEST(FlagsNegative, RejectUnknownFlag) {
    EXPECT_THROW(parse("%flags z"), ParseError);
}

/// Test rejection of malformed directive
TEST(FlagsNegative, RejectMalformedDirective) {
    EXPECT_THROW(parse("%flagg i"), ParseError);
}

// --- Category C: Edge Cases ---

/// Test empty flags directive
TEST(FlagsEdgeCases, EmptyFlagsDirective) {
    auto [flags, ast] = parse("%flags");
    EXPECT_FALSE(flags.ignoreCase);
    EXPECT_FALSE(flags.multiline);
    EXPECT_FALSE(flags.dotAll);
    EXPECT_FALSE(flags.unicode);
    EXPECT_FALSE(flags.extended);
}

/// Test directive after content is rejected
TEST(FlagsEdgeCases, DirectiveAfterContent) {
    EXPECT_THROW(parse("a\n%flags i"), ParseError);
}

/// Test pattern with only comments and whitespace
TEST(FlagsEdgeCases, OnlyCommentsAndWhitespace) {
    auto [flags, ast] = parse("%flags x\n# comment\n  \n# another");
    EXPECT_TRUE(flags.extended);
    
    // Should result in empty sequence
    Seq* seq = dynamic_cast<Seq*>(ast.get());
    ASSERT_NE(seq, nullptr);
    EXPECT_EQ(seq->parts.size(), 0);
}

// --- Category D: Interaction Cases ---

/// Test whitespace is literal inside character class
TEST(FlagsInteraction, WhitespaceIsLiteralInClass) {
    auto [flags, ast] = parse("%flags x\n[a b]");
    EXPECT_TRUE(flags.extended);
    
    CharClass* cc = dynamic_cast<CharClass*>(ast.get());
    ASSERT_NE(cc, nullptr);
    ASSERT_EQ(cc->items.size(), 3);
    
    ClassLiteral* lit0 = dynamic_cast<ClassLiteral*>(cc->items[0].get());
    ClassLiteral* lit1 = dynamic_cast<ClassLiteral*>(cc->items[1].get());
    ClassLiteral* lit2 = dynamic_cast<ClassLiteral*>(cc->items[2].get());
    
    ASSERT_NE(lit0, nullptr);
    ASSERT_NE(lit1, nullptr);
    ASSERT_NE(lit2, nullptr);
    
    EXPECT_EQ(lit0->ch, "a");
    EXPECT_EQ(lit1->ch, " ");
    EXPECT_EQ(lit2->ch, "b");
}

/// Test comment char is literal inside character class
TEST(FlagsInteraction, CommentCharIsLiteralInClass) {
    auto [flags, ast] = parse("%flags x\n[a#b]");
    EXPECT_TRUE(flags.extended);
    
    CharClass* cc = dynamic_cast<CharClass*>(ast.get());
    ASSERT_NE(cc, nullptr);
    ASSERT_EQ(cc->items.size(), 3);
    
    ClassLiteral* lit0 = dynamic_cast<ClassLiteral*>(cc->items[0].get());
    ClassLiteral* lit1 = dynamic_cast<ClassLiteral*>(cc->items[1].get());
    ClassLiteral* lit2 = dynamic_cast<ClassLiteral*>(cc->items[2].get());
    
    ASSERT_NE(lit0, nullptr);
    ASSERT_NE(lit1, nullptr);
    ASSERT_NE(lit2, nullptr);
    
    EXPECT_EQ(lit0->ch, "a");
    EXPECT_EQ(lit1->ch, "#");
    EXPECT_EQ(lit2->ch, "b");
}
