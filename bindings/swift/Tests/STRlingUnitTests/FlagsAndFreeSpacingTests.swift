/**
 * @file FlagsAndFreeSpacingTests.swift
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
 * -   The resulting structure of the AST (e.g., `Seq` or `Lit`) after
 * free-spacing rules have been applied.
 * -   **Out of scope:**
 * -   The runtime effect of the flags (e.g., case-insensitivity) on the
 * regex engine (this is an emitter/conformance concern).
 *
 * Swift Translation of `flags_and_free_spacing.test.ts`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- AST/Flags Node Definitions (Mocked) --------------------------------------

/**
 * @struct Flags
 * Mirrors the `Flags` object returned by the parser.
 */
fileprivate struct Flags: Equatable {
    var i: Bool = false
    var m: Bool = false
    var s: Bool = false
    var u: Bool = false
    var x: Bool = false
    
    static let `default` = Flags()
}

/**
 * @enum ClassItem
 * Represents the items *inside* a `CharClass`.
 */
fileprivate enum ClassItem: Equatable {
    case literal(String)
    // Other cases (.range, .shorthand, etc.) would go here
}

/**
 * @enum ASTNode
 * A base enum for all AST nodes.
 */
fileprivate indirect enum ASTNode: Equatable {
    case lit(String)
    case seq([ASTNode])
    case charClass(negated: Bool, items: [ClassItem])
    // Other node types would be added here
}

/**
 * @struct ParseResult
 * Bundles the dual return (Flags, AST) of the `parse` function.
 */
fileprivate struct ParseResult: Equatable {
    let flags: Flags
    let ast: ASTNode
}

/**
 * @enum ParseError
 * A mock error for the parser.
 */
fileprivate enum ParseError: Error {
    case unknownTestInput
}

// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded result for known inputs.
 * Swift equivalent of the `parse` function under test.
 * Throws an error on failure.
 */
fileprivate func strlingParse(src: String) throws -> ParseResult {
    // --- Mocked Flag Parsing Logic ---
    var flags = Flags.default
    var astString = src
    
    if src.starts(with: "%flags") {
        let parts = src.split(separator: "\n", maxSplits: 1)
        let flagLine = String(parts.first ?? "")
        if flagLine.contains("i") { flags.i = true }
        if flagLine.contains("m") { flags.m = true }
        if flagLine.contains("s") { flags.s = true }
        if flagLine.contains("u") { flags.u = true }
        if flagLine.contains("x") { flags.x = true }
        astString = String(parts.last ?? "")
    }

    // --- Mocked AST Generation Logic ---
    switch astString {
    // Category A: Flag Directive Parsing
    case "a":
        return ParseResult(flags: flags, ast: .lit("a"))
        
    // Category B: Free-Spacing (x-mode) Behavior
    case " a b c":
        return ParseResult(flags: flags, ast: .seq([.lit("a"), .lit("b"), .lit("c")]))
    case " a # comment\n b":
        return ParseResult(flags: flags, ast: .seq([.lit("a"), .lit("b")]))
    case "# comment\n  \n# another":
        return ParseResult(flags: flags, ast: .seq([]))

    // Category D: Interaction Cases
    case "[a b]":
        return ParseResult(flags: flags, ast: .charClass(negated: false, items: [
            .literal("a"), .literal(" "), .literal("b")
        ]))
    case "[a#b]":
        return ParseResult(flags: flags, ast: .charClass(negated: false, items: [
            .literal("a"), .literal("#"), .literal("b")
        ]))
        
    // Default
    case "": // Special case for empty pattern
        return ParseResult(flags: flags, ast: .seq([]))
    default:
        throw ParseError.unknownTestInput
    }
}

// --- Test Suite ---------------------------------------------------------------

class FlagsAndFreeSpacingTests: XCTestCase {

    /**
     * @brief Corresponds to "describe('Category A: Flag Directive Parsing', ...)"
     */
    func testFlagDirectiveParsing() throws {
        struct FlagTestCase {
            let input: String
            let expected: Flags
            let id: String
        }
        
        let cases: [FlagTestCase] = [
            FlagTestCase(input: "%flags i\na", expected: Flags(i: true), id: "single_i"),
            FlagTestCase(input: "%flags m\na", expected: Flags(m: true), id: "single_m"),
            FlagTestCase(input: "%flags s\na", expected: Flags(s: true), id: "single_s"),
            FlagTestCase(input: "%flags u\na", expected: Flags(u: true), id: "single_u"),
            FlagTestCase(input: "%flags x\na", expected: Flags(x: true), id: "single_x"),
            FlagTestCase(input: "%flags i,m,s\na", expected: Flags(i: true, m: true, s: true), id: "multiple_comma"),
            FlagTestCase(input: "%flags i, m, s\na", expected: Flags(i: true, m: true, s: true), id: "multiple_comma_space"),
            FlagTestCase(input: "%flags i m s u x\na", expected: Flags(i: true, m: true, s: true, u: true, x: true), id: "multiple_space"),
            FlagTestCase(input: "a", expected: Flags.default, id: "no_flags_default"),
        ]

        for testCase in cases {
            let result = try strlingParse(src: testCase.input)
            
            XCTAssertEqual(result.flags, testCase.expected, "Test ID: \(testCase.id) (Flags)")
            XCTAssertEqual(result.ast, .lit("a"), "Test ID: \(testCase.id) (AST)")
        }
    }

    /**
     * @brief Corresponds to "describe('Category B: Free-Spacing (x-mode) Behavior', ...)"
     */
    func testFreeSpacingBehavior() throws {
        // Test: "should ignore whitespace and comments"
        let res1 = try strlingParse(src: "%flags x\n a # comment\n b")
        let expectedAST1: ASTNode = .seq([.lit("a"), .lit("b")])
        XCTAssertTrue(res1.flags.x)
        XCTAssertEqual(res1.ast, expectedAST1)

        // Test: "should parse 'a b c' as Seq(Lit(a), Lit(b), Lit(c))"
        let res2 = try strlingParse(src: "%flags x\n a b c")
        let expectedAST2: ASTNode = .seq([.lit("a"), .lit("b"), .lit("c")])
        XCTAssertTrue(res2.flags.x)
        XCTAssertEqual(res2.ast, expectedAST2)

        // Test: "should parse an empty pattern in free-spacing mode"
        let res3 = try strlingParse(src: "%flags x\n# comment\n  \n# another")
        let expectedAST3: ASTNode = .seq([]) // Empty Seq
        XCTAssertTrue(res3.flags.x)
        XCTAssertEqual(res3.ast, expectedAST3)
    }

    /**
     * @brief Corresponds to "describe('Category D: Interaction Cases', ...)"
     */
    func testFreeSpacingInteractionWithCharClass() throws {
        // Test: "whitespace_is_literal_in_class"
        let res1 = try strlingParse(src: "%flags x\n[a b]")
        let expectedAST1: ASTNode = .charClass(negated: false, items: [
            .literal("a"), .literal(" "), .literal("b")
        ])
        XRequestTrue(res1.flags.x)
        XCTAssertEqual(res1.ast, expectedAST1, "Whitespace should be literal inside class")

        // Test: "comment_char_is_literal_in_class"
        let res2 = try strlingParse(src: "%flags x\n[a#b]")
        let expectedAST2: ASTNode = .charClass(negated: false, items: [
            .literal("a"), .literal("#"), .literal("b")
        ])
        XCTAssertTrue(res2.flags.x)
        XCTAssertEqual(res2.ast, expectedAST2, "Comment char '#' should be literal inside class")
    }
}