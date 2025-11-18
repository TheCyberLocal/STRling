/**
 * @file anchors_test.cpp
 * @brief Test Design — Anchor Tests
 *
 * ## Purpose
 * This test suite validates the correct parsing of all anchor tokens (^, $, \b, \B, etc.).
 * It ensures that each anchor is correctly mapped to a corresponding Anchor AST node
 * with the proper type and that its parsing is unaffected by flags or surrounding
 * constructs.
 *
 * ## Description
 * Anchors are zero-width assertions that do not consume characters but instead
 * match a specific **position** within the input string, such as the start of a
 * line or a boundary between a word and a space. This suite tests the parser's
 * ability to correctly identify all supported core and extension anchors and
 * produce the corresponding `nodes::Anchor` AST object.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of core line anchors (`^`, `$`) and word boundary anchors
 * (`\b`, `\B`).
 * -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`, `\z`).
 *
 * -   The structure and `at` value of the resulting `nodes::Anchor` AST node.
 *
 * -   How anchors are parsed when placed at the start, middle, or end of a sequence.
 *
 * -   Ensuring the parser's output for `^` and `$` is consistent regardless
 * of the multiline (`m`) flag's presence.
 * -   **Out of scope:**
 * -   The runtime *behavioral change* of `^` and `$` when the `m` flag is
 * active (this is an emitter/engine concern).
 * -   Quantification of anchors.
 * -   The behavior of `\b` inside a character class, where it represents a
 * backspace literal (covered in `char_classes_test.cpp`).
 * 
 * NOTE: This is a PARTIAL implementation demonstrating the test porting pattern.
 * Full porting would require all 31 test cases from anchors.test.ts.
 * 
 * @copyright Copyright (c) 2024 TheCyberLocal
 * @license MIT License
 */

#include <gtest/gtest.h>
#include "strling/core/parser.hpp"
#include "strling/core/nodes.hpp"
#include <memory>
#include <string>

using namespace strling::core;

// --- Category A: Positive Cases ---

/**
 * @brief Test suite for positive anchor parsing cases
 * 
 * Covers all positive cases for valid anchor syntax. These tests verify
 * that each anchor token is parsed into the correct Anchor node with the
 * expected `at` value.
 */

/// Test parsing of start anchor (^)
TEST(AnchorsPositive, ParseStartAnchor) {
    auto [flags, ast] = parse("^");
    
    // Verify it's an Anchor node
    Anchor* anchor = dynamic_cast<Anchor*>(ast.get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "Start");
}

/// Test parsing of end anchor ($)
TEST(AnchorsPositive, ParseEndAnchor) {
    auto [flags, ast] = parse("$");
    
    Anchor* anchor = dynamic_cast<Anchor*>(ast.get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "End");
}

/// Test parsing of word boundary (\b)
TEST(AnchorsPositive, ParseWordBoundary) {
    auto [flags, ast] = parse(R"(\b)");
    
    Anchor* anchor = dynamic_cast<Anchor*>(ast.get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "WordBoundary");
}

/// Test parsing of not-word-boundary (\B)
TEST(AnchorsPositive, ParseNotWordBoundary) {
    auto [flags, ast] = parse(R"(\B)");
    
    Anchor* anchor = dynamic_cast<Anchor*>(ast.get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "NotWordBoundary");
}

/// Test parsing of absolute start anchor (\A)
TEST(AnchorsPositive, ParseAbsoluteStart) {
    auto [flags, ast] = parse(R"(\A)");
    
    Anchor* anchor = dynamic_cast<Anchor*>(ast.get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "AbsoluteStart");
}

/// Test parsing of end before newline anchor (\Z)
TEST(AnchorsPositive, ParseEndBeforeFinalNewline) {
    auto [flags, ast] = parse(R"(\Z)");
    
    Anchor* anchor = dynamic_cast<Anchor*>(ast.get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "EndBeforeFinalNewline");
}

// --- Category C: Edge Cases ---

/**
 * @brief Test suite for anchor edge cases
 * 
 * Covers edge cases related to the position and combination of anchors.
 */

/// Test parsing a pattern with only anchors
TEST(AnchorsEdgeCases, ParsePatternWithOnlyAnchors) {
    auto [flags, ast] = parse(R"(^\A\b$)");
    
    // Should be a Seq with 4 anchors
    Seq* seq = dynamic_cast<Seq*>(ast.get());
    ASSERT_NE(seq, nullptr);
    ASSERT_EQ(seq->parts.size(), 4);
    
    // Check each anchor
    Anchor* anchor0 = dynamic_cast<Anchor*>(seq->parts[0].get());
    ASSERT_NE(anchor0, nullptr);
    EXPECT_EQ(anchor0->at, "Start");
    
    Anchor* anchor1 = dynamic_cast<Anchor*>(seq->parts[1].get());
    ASSERT_NE(anchor1, nullptr);
    EXPECT_EQ(anchor1->at, "AbsoluteStart");
    
    Anchor* anchor2 = dynamic_cast<Anchor*>(seq->parts[2].get());
    ASSERT_NE(anchor2, nullptr);
    EXPECT_EQ(anchor2->at, "WordBoundary");
    
    Anchor* anchor3 = dynamic_cast<Anchor*>(seq->parts[3].get());
    ASSERT_NE(anchor3, nullptr);
    EXPECT_EQ(anchor3->at, "End");
}

/// Test anchors in different positions
TEST(AnchorsEdgeCases, ParseAnchorAtStart) {
    auto [flags, ast] = parse("^a");
    
    Seq* seq = dynamic_cast<Seq*>(ast.get());
    ASSERT_NE(seq, nullptr);
    ASSERT_GE(seq->parts.size(), 2);
    
    Anchor* anchor = dynamic_cast<Anchor*>(seq->parts[0].get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "Start");
}

TEST(AnchorsEdgeCases, ParseAnchorInMiddle) {
    auto [flags, ast] = parse(R"(a\bb)");
    
    Seq* seq = dynamic_cast<Seq*>(ast.get());
    ASSERT_NE(seq, nullptr);
    ASSERT_GE(seq->parts.size(), 3);
    
    Anchor* anchor = dynamic_cast<Anchor*>(seq->parts[1].get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "WordBoundary");
}

TEST(AnchorsEdgeCases, ParseAnchorAtEnd) {
    auto [flags, ast] = parse("ab$");
    
    Seq* seq = dynamic_cast<Seq*>(ast.get());
    ASSERT_NE(seq, nullptr);
    ASSERT_GE(seq->parts.size(), 2);
    
    Anchor* anchor = dynamic_cast<Anchor*>(seq->parts[seq->parts.size() - 1].get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "End");
}

// --- Category D: Interaction Cases ---

/**
 * @brief Test suite for anchor interaction cases
 * 
 * Covers how anchors interact with other DSL features, such as flags
 * and grouping constructs.
 */

/// Test that multiline flag doesn't change AST structure
TEST(AnchorsInteraction, MultilineFlagDoesNotChangeAST) {
    auto [flags1, ast1] = parse("^a$");
    auto [flags2, ast2] = parse("%flags m\n^a$");
    
    // Both should produce Seq nodes
    Seq* seq1 = dynamic_cast<Seq*>(ast1.get());
    Seq* seq2 = dynamic_cast<Seq*>(ast2.get());
    
    ASSERT_NE(seq1, nullptr);
    ASSERT_NE(seq2, nullptr);
    
    // Both should have 3 parts
    ASSERT_EQ(seq1->parts.size(), 3);
    ASSERT_EQ(seq2->parts.size(), 3);
    
    // First part should be Start anchor
    Anchor* anchor1_0 = dynamic_cast<Anchor*>(seq1->parts[0].get());
    Anchor* anchor2_0 = dynamic_cast<Anchor*>(seq2->parts[0].get());
    ASSERT_NE(anchor1_0, nullptr);
    ASSERT_NE(anchor2_0, nullptr);
    EXPECT_EQ(anchor1_0->at, "Start");
    EXPECT_EQ(anchor2_0->at, "Start");
    
    // Last part should be End anchor
    Anchor* anchor1_2 = dynamic_cast<Anchor*>(seq1->parts[2].get());
    Anchor* anchor2_2 = dynamic_cast<Anchor*>(seq2->parts[2].get());
    ASSERT_NE(anchor1_2, nullptr);
    ASSERT_NE(anchor2_2, nullptr);
    EXPECT_EQ(anchor1_2->at, "End");
    EXPECT_EQ(anchor2_2->at, "End");
}

/// Test anchors inside capturing groups
TEST(AnchorsInteraction, ParseAnchorInCapturingGroup) {
    auto [flags, ast] = parse("(^a)");
    
    Group* group = dynamic_cast<Group*>(ast.get());
    ASSERT_NE(group, nullptr);
    EXPECT_TRUE(group->capturing);
    
    // Body should be a Seq
    Seq* body = dynamic_cast<Seq*>(group->body.get());
    ASSERT_NE(body, nullptr);
    ASSERT_GE(body->parts.size(), 2);
    
    // First part should be Start anchor
    Anchor* anchor = dynamic_cast<Anchor*>(body->parts[0].get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "Start");
}

/// Test anchors inside non-capturing groups
TEST(AnchorsInteraction, ParseAnchorInNonCapturingGroup) {
    auto [flags, ast] = parse(R"((?:a\b))");
    
    Group* group = dynamic_cast<Group*>(ast.get());
    ASSERT_NE(group, nullptr);
    EXPECT_FALSE(group->capturing);
    
    // Body should be a Seq
    Seq* body = dynamic_cast<Seq*>(group->body.get());
    ASSERT_NE(body, nullptr);
    ASSERT_GE(body->parts.size(), 2);
    
    // Second part should be WordBoundary anchor
    Anchor* anchor = dynamic_cast<Anchor*>(body->parts[1].get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "WordBoundary");
}

/// Test anchors in lookahead
TEST(AnchorsInteraction, ParseAnchorInLookahead) {
    auto [flags, ast] = parse("(?=a$)");
    
    Look* look = dynamic_cast<Look*>(ast.get());
    ASSERT_NE(look, nullptr);
    EXPECT_EQ(look->dir, "Ahead");
    EXPECT_FALSE(look->neg);
    
    // Body should be a Seq
    Seq* body = dynamic_cast<Seq*>(look->body.get());
    ASSERT_NE(body, nullptr);
    ASSERT_GE(body->parts.size(), 2);
    
    // Second part should be End anchor
    Anchor* anchor = dynamic_cast<Anchor*>(body->parts[1].get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "End");
}

/// Test anchors in lookbehind
TEST(AnchorsInteraction, ParseAnchorInLookbehind) {
    auto [flags, ast] = parse("(?<=^a)");
    
    Look* look = dynamic_cast<Look*>(ast.get());
    ASSERT_NE(look, nullptr);
    EXPECT_EQ(look->dir, "Behind");
    EXPECT_FALSE(look->neg);
    
    // Body should be a Seq
    Seq* body = dynamic_cast<Seq*>(look->body.get());
    ASSERT_NE(body, nullptr);
    ASSERT_GE(body->parts.size(), 2);
    
    // First part should be Start anchor
    Anchor* anchor = dynamic_cast<Anchor*>(body->parts[0].get());
    ASSERT_NE(anchor, nullptr);
    EXPECT_EQ(anchor->at, "Start");
}

// --- Category J: Anchors with Quantifiers ---

/**
 * @brief Test suite confirming that anchors cannot be quantified
 */

/// Test that quantifying start anchor raises error
TEST(AnchorsQuantifierErrors, CannotQuantifyStartAnchor) {
    EXPECT_THROW(parse("^*"), ParseError);
}

/// Test that quantifying end anchor raises error
TEST(AnchorsQuantifierErrors, CannotQuantifyEndAnchor) {
    EXPECT_THROW(parse("$+"), ParseError);
}

/// Test unknown escape sequence \z
TEST(AnchorsNegative, UnknownEscapeZ) {
    EXPECT_THROW(parse(R"(\z)"), ParseError);
}

/*
 * NOTE: This is a PARTIAL implementation demonstrating the test porting pattern.
 * 
 * The full anchors.test.ts file contains 31 test cases across 10 categories.
 * Additional test cases would include:
 * - Category E: Anchors in Complex Sequences (4 tests)
 * - Category F: Anchors in Alternation (3 tests)
 * - Category G: Anchors in Atomic Groups (3 tests)
 * - Category H: Word Boundary Edge Cases (3 tests)
 * - Category I: Multiple Anchor Types (4 tests)
 * - And more...
 * 
 * To complete the porting:
 * 1. Add remaining test cases from anchors.test.ts
 * 2. Port the other 13 unit test files (char_classes, quantifiers, etc.)
 * 3. Port the 3 E2E test files
 * 4. Implement full parser logic to pass all tests
 * 5. Implement compiler, validator, emitters
 * 6. Implement CLI interface
 */
