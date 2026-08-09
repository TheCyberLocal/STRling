/**
 * @file interaction_test.cpp
 * @brief Interaction Tests - Parser → Compiler → Emitter handoffs
 *
 * ## Purpose
 * This test suite validates the handoff between pipeline stages:
 * - Parser → Compiler: Ensures AST is correctly consumed
 * - Compiler → Emitter: Ensures IR is correctly transformed to regex
 *
 * ## Scope
 * Tests the integration between components rather than individual component logic.
 */

#include <gtest/gtest.h>
#include "strling/core/parser.hpp"
#include "strling/core/compiler.hpp"
#include "strling/emitters/pcre2.hpp"
#include <memory>
#include <string>

using namespace strling;

class InteractionTest : public ::testing::Test {
protected:
    core::Parser parser;
    core::Compiler compiler;
    emitters::Pcre2Emitter emitter;
};

// ============================================================================
// Parser → Compiler Handoff Tests
// ============================================================================

TEST_F(InteractionTest, ParserCompiler_SimpleLiteral) {
    auto ast = parser.parse("hello");
    ASSERT_NE(ast, nullptr);

    auto ir = compiler.compile(ast);
    ASSERT_NE(ir, nullptr);
    EXPECT_EQ(ir->type(), "Lit");
}

TEST_F(InteractionTest, ParserCompiler_Quantifier) {
    auto ast = parser.parse("a+");
    ASSERT_NE(ast, nullptr);

    auto ir = compiler.compile(ast);
    ASSERT_NE(ir, nullptr);
    EXPECT_EQ(ir->type(), "Quant");
}

TEST_F(InteractionTest, ParserCompiler_CharacterClass) {
    auto ast = parser.parse("[abc]");
    ASSERT_NE(ast, nullptr);

    auto ir = compiler.compile(ast);
    ASSERT_NE(ir, nullptr);
    EXPECT_EQ(ir->type(), "CharClass");
}

TEST_F(InteractionTest, ParserCompiler_CapturingGroup) {
    auto ast = parser.parse("(abc)");
    ASSERT_NE(ast, nullptr);

    auto ir = compiler.compile(ast);
    ASSERT_NE(ir, nullptr);
    EXPECT_EQ(ir->type(), "Group");
}

TEST_F(InteractionTest, ParserCompiler_Alternation) {
    auto ast = parser.parse("a|b");
    ASSERT_NE(ast, nullptr);

    auto ir = compiler.compile(ast);
    ASSERT_NE(ir, nullptr);
    EXPECT_EQ(ir->type(), "Alt");
}

TEST_F(InteractionTest, ParserCompiler_NamedGroup) {
    auto ast = parser.parse("(?<name>abc)");
    ASSERT_NE(ast, nullptr);

    auto ir = compiler.compile(ast);
    ASSERT_NE(ir, nullptr);
    EXPECT_EQ(ir->type(), "Group");
}

TEST_F(InteractionTest, ParserCompiler_Lookahead) {
    auto ast = parser.parse("(?=abc)");
    ASSERT_NE(ast, nullptr);

    auto ir = compiler.compile(ast);
    ASSERT_NE(ir, nullptr);
    EXPECT_EQ(ir->type(), "Look");
}

TEST_F(InteractionTest, ParserCompiler_Lookbehind) {
    auto ast = parser.parse("(?<=abc)");
    ASSERT_NE(ast, nullptr);

    auto ir = compiler.compile(ast);
    ASSERT_NE(ir, nullptr);
    EXPECT_EQ(ir->type(), "Look");
}

// ============================================================================
// Compiler → Emitter Handoff Tests
// ============================================================================

TEST_F(InteractionTest, CompilerEmitter_SimpleLiteral) {
    auto ast = parser.parse("hello");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "hello");
}

TEST_F(InteractionTest, CompilerEmitter_DigitShorthand) {
    auto ast = parser.parse("\\d+");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "\\d+");
}

TEST_F(InteractionTest, CompilerEmitter_CharacterClass) {
    auto ast = parser.parse("[abc]");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "[abc]");
}

TEST_F(InteractionTest, CompilerEmitter_CharacterClassRange) {
    auto ast = parser.parse("[a-z]");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "[a-z]");
}

TEST_F(InteractionTest, CompilerEmitter_NegatedClass) {
    auto ast = parser.parse("[^abc]");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "[^abc]");
}

TEST_F(InteractionTest, CompilerEmitter_QuantifierPlus) {
    auto ast = parser.parse("a+");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "a+");
}

TEST_F(InteractionTest, CompilerEmitter_QuantifierStar) {
    auto ast = parser.parse("a*");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "a*");
}

TEST_F(InteractionTest, CompilerEmitter_QuantifierOptional) {
    auto ast = parser.parse("a?");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "a?");
}

TEST_F(InteractionTest, CompilerEmitter_QuantifierExact) {
    auto ast = parser.parse("a{3}");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "a{3}");
}

TEST_F(InteractionTest, CompilerEmitter_QuantifierRange) {
    auto ast = parser.parse("a{2,5}");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "a{2,5}");
}

TEST_F(InteractionTest, CompilerEmitter_QuantifierLazy) {
    auto ast = parser.parse("a+?");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "a+?");
}

TEST_F(InteractionTest, CompilerEmitter_CapturingGroup) {
    auto ast = parser.parse("(abc)");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "(abc)");
}

TEST_F(InteractionTest, CompilerEmitter_NonCapturingGroup) {
    auto ast = parser.parse("(?:abc)");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "(?:abc)");
}

TEST_F(InteractionTest, CompilerEmitter_NamedGroup) {
    auto ast = parser.parse("(?<name>abc)");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "(?<name>abc)");
}

TEST_F(InteractionTest, CompilerEmitter_Alternation) {
    auto ast = parser.parse("cat|dog");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "cat|dog");
}

TEST_F(InteractionTest, CompilerEmitter_Anchors) {
    auto ast = parser.parse("^abc$");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "^abc$");
}

TEST_F(InteractionTest, CompilerEmitter_PositiveLookahead) {
    auto ast = parser.parse("foo(?=bar)");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "foo(?=bar)");
}

TEST_F(InteractionTest, CompilerEmitter_NegativeLookahead) {
    auto ast = parser.parse("foo(?!bar)");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "foo(?!bar)");
}

TEST_F(InteractionTest, CompilerEmitter_PositiveLookbehind) {
    auto ast = parser.parse("(?<=foo)bar");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "(?<=foo)bar");
}

TEST_F(InteractionTest, CompilerEmitter_NegativeLookbehind) {
    auto ast = parser.parse("(?<!foo)bar");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "(?<!foo)bar");
}

// ============================================================================
// Semantic Edge Case Tests
// ============================================================================

TEST_F(InteractionTest, Semantic_DuplicateNames) {
    // Duplicate named groups should produce an error
    EXPECT_THROW({
        parser.parse("(?<name>a)(?<name>b)");
    }, std::runtime_error);
}

TEST_F(InteractionTest, Semantic_InvalidRange) {
    // Invalid range [z-a] should produce an error
    EXPECT_THROW({
        parser.parse("[z-a]");
    }, std::runtime_error);
}

// ============================================================================
// Full Pipeline Tests
// ============================================================================

TEST_F(InteractionTest, FullPipeline_PhoneNumber) {
    auto ast = parser.parse("(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})");
}

TEST_F(InteractionTest, FullPipeline_IPv4) {
    auto ast = parser.parse("(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})");
    auto ir = compiler.compile(ast);
    auto regex = emitter.emit(ir, core::Flags{});

    EXPECT_EQ(regex, "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})");
}
