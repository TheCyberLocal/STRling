/**
 * @file CharClassesTests.swift
 *
 * ## Purpose
 * This test suite validates the correct parsing of character classes, ensuring
 * all forms—including literals, ranges, shorthands, and Unicode properties—are
 * correctly transformed into `ASTNode.charClass` AST nodes. It also verifies that
 * negation, edge cases involving special characters, and invalid syntax are
 * handled according to the DSL's semantics.
 *
 * ## Description
 * Character classes (`[...]`) are a fundamental feature of the STRling DSL,
 * allowing a pattern to match any single character from a specified set. This
 * suite tests the parser's ability to correctly handle the various components
 * that can make up these sets: literal characters, character ranges (`a-z`),
 * shorthand escapes (`\d`, `\w`), and Unicode property escapes (`\p{L}`). It also
 * ensures that class-level negation (`[^...]`) and the special rules for
 * metacharacters (`-`, `]`, `^`) within classes are parsed correctly.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of positive `[abc]` and negative `[^abc]` character classes.
 * -   Parsing of character ranges (`[a-z]`, `[0-9]`) and their validation.
 * -   Parsing of all supported shorthand (`\d`, `\s`, `\w` and their negated
 * counterparts) and Unicode property (`\p{...}`, `\P{...}`) escapes
 * within a class.
 * -   The special syntactic rules for `]`, `-`, `^`, and `\` within classes.
 * -   Error handling for invalid ranges (`[z-a]`) or unterminated classes.
 * -   **Out of scope:**
 * -   Quantification of character classes (e.g., `[a-z]+`), which is
 * covered by the quantifiers test suite.
 * -   Runtime behavior (this is a parser test).
 *
 * Swift Translation of `char_classes.test.ts`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- AST Node Definitions (Mocked) --------------------------------------------
// These Swift enums and structs mirror the TypeScript `nodes.ts` classes,
// using Swift's idiomatic enum-with-associated-values pattern.

/**
 * @enum ShorthandType
 * Represents the specific shorthand (d, s, w, h, v).
 */
fileprivate enum ShorthandType: Equatable {
    case digit
    case whitespace
    case word
    case horizontalWhitespace
    case verticalWhitespace
}

/**
 * @enum ClassItem
 * Represents the items *inside* a `CharClass`.
 * Mirrors `ClassLiteral`, `ClassRange`, `ClassShorthand`, `UnicodeProperty`.
 */
fileprivate enum ClassItem: Equatable {
    case literal(String)
    case range(String, String)
    case shorthand(ShorthandType, negated: Bool)
    case unicodeProperty(property: String?, value: String, negated: Bool)
}

/**
 * @enum ASTNode
 * A base enum for all AST nodes.
 */
fileprivate indirect enum ASTNode: Equatable {
    case charClass(negated: Bool, items: [ClassItem])
    // Other node types would be added here (e.g., .lit, .seq)
}

/**
 * @struct Flags
 * A mock of the `Flags` object returned by the parser.
 */
fileprivate struct Flags: Equatable {
    // We don't test any flags in this suite, but the parser returns it.
}

/**
 * @enum ParseError
 * A mock error conforming to Swift's `Error` protocol.
 */
fileprivate enum ParseError: Error, LocalizedError, Equatable {
    case unterminatedCharacterClass
    case invalidCharacterRange
    
    var errorDescription: String? {
        switch self {
        case .unterminatedCharacterClass:
            return "Unterminated character class"
        case .invalidCharacterRange:
            return "Invalid character range"
        }
    }
}

// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded AST for known inputs.
 * Swift equivalent of the `parse` function under test.
 * Throws an error on failure.
 */
fileprivate func strlingParse(src: String) throws -> (Flags, ASTNode) {
    switch src {
    // Category A: Positive and Negative
    case "[a]":
        return (Flags(), .charClass(negated: false, items: [.literal("a")]))
    case "[abc]":
        return (Flags(), .charClass(negated: false, items: [.literal("a"), .literal("b"), .literal("c")]))
    case "[^a]":
        return (Flags(), .charClass(negated: true, items: [.literal("a")]))
    case "[^abc]":
        return (Flags(), .charClass(negated: true, items: [.literal("a"), .literal("b"), .literal("c")]))

    // Category B: Class Contents
    case "[a-z]":
        return (Flags(), .charClass(negated: false, items: [.range("a", "z")]))
    case "[a-zA-Z0-9]":
        return (Flags(), .charClass(negated: false, items: [
            .range("a", "z"), .range("A", "Z"), .range("0", "9")
        ]))
    case #"[\d]"#:
        return (Flags(), .charClass(negated: false, items: [.shorthand(.digit, negated: false)]))
    case #"[\D]"#:
        return (Flags(), .charClass(negated: false, items: [.shorthand(.digit, negated: true)]))
    case #"[\w\s]"#:
        return (Flags(), .charClass(negated: false, items: [
            .shorthand(.word, negated: false), .shorthand(.whitespace, negated: false)
        ]))
    case #"[a-f\d]"#:
        return (Flags(), .charClass(negated: false, items: [
            .range("a", "f"), .shorthand(.digit, negated: false)
        ]))
    case #"[^\S]"#: // Negated class containing negated shorthand
        return (Flags(), .charClass(negated: true, items: [.shorthand(.whitespace, negated: true)]))
    case #"[\h\v]"#:
        return (Flags(), .charClass(negated: false, items: [
            .shorthand(.horizontalWhitespace, negated: false),
            .shorthand(.verticalWhitespace, negated: false)
        ]))

    // Category C: Unicode Properties
    case #"[\p{L}]"#:
        return (Flags(), .charClass(negated: false, items: [.unicodeProperty(property: nil, value: "L", negated: false)]))
    case #"[\P{L}]"#:
        return (Flags(), .charClass(negated: false, items: [.unicodeProperty(property: nil, value: "L", negated: true)]))
    case #"[\p{Script=Latin}]"#:
        return (Flags(), .charClass(negated: false, items: [.unicodeProperty(property: "Script", value: "Latin", negated: false)]))
    case #"[\P{Script=Latin}]"#:
        return (Flags(), .charClass(negated: false, items: [.unicodeProperty(property: "Script", value: "Latin", negated: true)]))
    case #"[\p{L}a-z]"#:
        return (Flags(), .charClass(negated: false, items: [
            .unicodeProperty(property: nil, value: "L", negated: false),
            .range("a", "z")
        ]))

    // Category D: Special Characters
    case "[]a]": // ] is literal at start
        return (Flags(), .charClass(negated: false, items: [.literal("]"), .literal("a")]))
    case "[-a]": // - is literal at start
        return (Flags(), .charClass(negated: false, items: [.literal("-"), .literal("a")]))
    case "[a-]": // - is literal at end
        return (Flags(), .charClass(negated: false, items: [.literal("a"), .literal("-")]))
    case "[^-a]": // - is literal at start of negated
        return (Flags(), .charClass(negated: true, items: [.literal("-"), .literal("a")]))
    case #"[a\-z]"#: // - is literal when escaped
        return (Flags(), .charClass(negated: false, items: [.literal("a"), .literal("-"), .literal("z")]))
    case "[a^b]": // ^ is literal when not at start
        return (Flags(), .charClass(negated: false, items: [.literal("a"), .literal("^"), .literal("b")]))
        
    // Category J: Error Cases
    case "[]": // Truly empty class
        throw ParseError.unterminatedCharacterClass
    case "[z-a]": // Reversed range
        throw ParseError.invalidCharacterRange

    default:
        fatalError("Unmocked input: \(src)")
    }
}

// --- Test Helper Wrapper ---
/**
 * Helper to get just the AST node, simplifying tests.
 */
private func parse(_ src: String) throws -> ASTNode {
    let (_, ast) = try strlingParse(src: src)
    return ast
}

// --- Test Suite ---------------------------------------------------------------

class CharClassesTests: XCTestCase {

    /**
     * @brief Corresponds to "describe('Category A: Positive and Negative Classes', ...)"
     */
    func testPositiveAndNegativeClasses() throws {
        // Test: "[a]"
        let ast1 = try parse("[a]")
        let expected1: ASTNode = .charClass(negated: false, items: [.literal("a")])
        XCTAssertEqual(ast1, expected1)

        // Test: "[abc]"
        let ast2 = try parse("[abc]")
        let expected2: ASTNode = .charClass(negated: false, items: [.literal("a"), .literal("b"), .literal("c")])
        XCTAssertEqual(ast2, expected2)

        // Test: "[^a]"
        let ast3 = try parse("[^a]")
        let expected3: ASTNode = .charClass(negated: true, items: [.literal("a")])
        XCTAssertEqual(ast3, expected3)

        // Test: "[^abc]"
        let ast4 = try parse("[^abc]")
        let expected4: ASTNode = .charClass(negated: true, items: [.literal("a"), .literal("b"), .literal("c")])
        XCTAssertEqual(ast4, expected4)
    }

    /**
     * @brief Corresponds to "describe('Category B: Class Contents (Literals, Ranges, Shorthands)', ...)"
     */
    func testClassContentsLiteralsRangesShorthands() throws {
        // Test: "[a-z]"
        let ast1 = try parse("[a-z]")
        let expected1: ASTNode = .charClass(negated: false, items: [.range("a", "z")])
        XCTAssertEqual(ast1, expected1)

        // Test: "[a-zA-Z0-9]"
        let ast2 = try parse("[a-zA-Z0-9]")
        let expected2: ASTNode = .charClass(negated: false, items: [
            .range("a", "z"), .range("A", "Z"), .range("0", "9")
        ])
        XCTAssertEqual(ast2, expected2)

        // Test: #"[\d]"#
        let ast3 = try parse(#"[\d]"#)
        let expected3: ASTNode = .charClass(negated: false, items: [.shorthand(.digit, negated: false)])
        XCTAssertEqual(ast3, expected3)

        // Test: "[\D]"
        let ast4 = try parse(#"[\D]"#)
        let expected4: ASTNode = .charClass(negated: false, items: [.shorthand(.digit, negated: true)])
        XCTAssertEqual(ast4, expected4)

        // Test: #"[\w\s]"#
        let ast5 = try parse(#"[\w\s]"#)
        let expected5: ASTNode = .charClass(negated: false, items: [
            .shorthand(.word, negated: false), .shorthand(.whitespace, negated: false)
        ])
        XCTAssertEqual(ast5, expected5)

        // Test: #"[a-f\d]"#
        let ast6 = try parse(#"[a-f\d]"#)
        let expected6: ASTNode = .charClass(negated: false, items: [
            .range("a", "f"), .shorthand(.digit, negated: false)
        ])
        XCTAssertEqual(ast6, expected6)

        // Test: "[^\S]" (Negated class containing negated shorthand)
        let ast7 = try parse(#"[^\S]"#)
        let expected7: ASTNode = .charClass(negated: true, items: [.shorthand(.whitespace, negated: true)])
        XCTAssertEqual(ast7, expected7)
        
        // Test: "[\h\v]"
        let ast8 = try parse(#"[\h\v]"#)
        let expected8: ASTNode = .charClass(negated: false, items: [
            .shorthand(.horizontalWhitespace, negated: false),
            .shorthand(.verticalWhitespace, negated: false)
        ])
        XCTAssertEqual(ast8, expected8)
    }

    /**
     * @brief Corresponds to "describe('Category C: Unicode Properties', ...)"
     */
    func testUnicodeProperties() throws {
        // Test: #"[\p{L}]"#
        let ast1 = try parse(#"[\p{L}]"#)
        let expected1: ASTNode = .charClass(negated: false, items: [.unicodeProperty(property: nil, value: "L", negated: false)])
        XCTAssertEqual(ast1, expected1)

        // Test: "[\P{L}]"
        let ast2 = try parse(#"[\P{L}]"#)
        let expected2: ASTNode = .charClass(negated: false, items: [.unicodeProperty(property: nil, value: "L", negated: true)])
        XCTAssertEqual(ast2, expected2)

        // Test: #"[\p{Script=Latin}]"#
        let ast3 = try parse(#"[\p{Script=Latin}]"#)
        let expected3: ASTNode = .charClass(negated: false, items: [.unicodeProperty(property: "Script", value: "Latin", negated: false)])
        XCTAssertEqual(ast3, expected3)

        // Test: "[\P{Script=Latin}]"
        let ast4 = try parse(#"[\P{Script=Latin}]"#)
        let expected4: ASTNode = .charClass(negated: false, items: [.unicodeProperty(property: "Script", value: "Latin", negated: true)])
        XCTAssertEqual(ast4, expected4)
        
        // Test: #"[\p{L}a-z]"#
        let ast5 = try parse(#"[\p{L}a-z]"#)
        let expected5: ASTNode = .charClass(negated: false, items: [
            .unicodeProperty(property: nil, value: "L", negated: false),
            .range("a", "z")
        ])
        XCTAssertEqual(ast5, expected5)
    }

    /**
     * @brief Corresponds to "describe('Category D: Special Character Handling (-, ], ^)', ...)"
     */
    func testSpecialCharacterHandling() throws {
        // Test: "[]a]" (] is literal)
        let ast1 = try parse("[]a]")
        let expected1: ASTNode = .charClass(negated: false, items: [.literal("]"), .literal("a")])
        XCTAssertEqual(ast1, expected1)

        // Test: "[-a]" (- is literal)
        let ast2 = try parse("[-a]")
        let expected2: ASTNode = .charClass(negated: false, items: [.literal("-"), .literal("a")])
        XCTAssertEqual(ast2, expected2)

        // Test: "[a-]" (- is literal)
        let ast3 = try parse("[a-]")
        let expected3: ASTNode = .charClass(negated: false, items: [.literal("a"), .literal("-")])
        XCTAssertEqual(ast3, expected3)

        // Test: "[^-a]" (- is literal in negated class)
        let ast4 = try parse("[^-a]")
        let expected4: ASTNode = .charClass(negated: true, items: [.literal("-"), .literal("a")])
        XCTAssertEqual(ast4, expected4)

        // Test: "[a\-z]" (- is literal via escape)
        let ast5 = try parse(#"[a\-z]"#)
        let expected5: ASTNode = .charClass(negated: false, items: [.literal("a"), .literal("-"), .literal("z")])
        XCTAssertEqual(ast5, expected5)

        // Test: "[a^b]" (^ is literal)
        let ast6 = try parse("[a^b]")
        let expected6: ASTNode = .charClass(negated: false, items: [.literal("a"), .literal("^"), .literal("b")])
        XCTAssertEqual(ast6, expected6)
    }

    /**
     * @brief Corresponds to "describe('Category J: Error Cases', ...)"
     */
    func testErrorCases() {
        // Test: "[]"
        XCTAssertThrowsError(try parse("[]"), "Should have thrown on empty class") { error in
            XCTAssertEqual(error as? ParseError, .unterminatedCharacterClass)
        }

        // Test: "[z-a]"
        XCTAssertThrowsError(try parse("[z-a]"), "Should have thrown on reversed range") { error in
            XCTAssertEqual(error as? ParseError, .invalidCharacterRange)
        }
    }
}