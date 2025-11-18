/**
 * @file AnchorsTests.swift
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
 * produce the corresponding `AST.Anchor` object.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of core line anchors (`^`, `$`) and word boundary anchors
 * (`\b`, `\B`).
 * -   Parsing of non-core, engine-specific absolute anchors (`\A`, `\Z`, `\z`).
 *
 * -   The structure and `at` value of the resulting `AST.Anchor` node.
 *
 * -   How anchors are parsed when placed at the start, middle, or end of a sequence.
 *
 * -   Ensuring the parser's output for `^` and `$` is consistent regardless
 * of the multiline (`m`) flag's presence.
 * -   **Out of scope:**
 * -   The runtime *behavioral change* of `^` and `$` when the `m` flag is
 * active (this is an emitter/engine concern).
 * -   Quantification of anchors.
 * -   The behavior of anchors in combination with other complex constructs
 * (e.g., inside lookarounds), which is covered by combinatorial E2E tests.
 *
 * Swift Translation of `anchors.test.ts`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- AST Node Definitions (Mocked) --------------------------------------------
// These Swift structs mirror the TypeScript `nodes.ts` classes.

/**
 * @protocol ASTNode
 * A base protocol for all AST nodes.
 */
protocol ASTNode: Equatable {}

/**
 * @enum AnchorType
 * Mirrors the `at` property of the `nodes.Anchor` class.
 */
enum AnchorType: String, Equatable {
    case start = "Start"
    case end = "End"
    case wordBoundary = "WordBoundary"
    case nonWordBoundary = "NonWordBoundary"
    case absoluteStart = "AbsoluteStart"   // \A
    case absoluteEnd = "AbsoluteEnd"       // \Z
    case absoluteEndOnly = "AbsoluteEndOnly" // \z
}

/**
 * @struct Anchor
 * Mirrors `nodes.Anchor`.
 */
struct Anchor: ASTNode {
    let at: AnchorType
}

/**
 * @struct Lit
 * Mirrors `nodes.Lit`.
 */
struct Lit: ASTNode {
    let value: String
}

/**
 * @struct Seq
 * Mirrors `nodes.Seq`.
 */
struct Seq: ASTNode {
    let parts: [ASTNode]

    // Custom Equatable conformance for nested ASTNodes
    static func == (lhs: Seq, rhs: Seq) -> Bool {
        guard lhs.parts.count == rhs.parts.count else { return false }
        for (l, r) in zip(lhs.parts, rhs.parts) {
            guard anyEquals(l, r) else { return false }
        }
        return true
    }
}

/**
 * @struct Flags
 * A mock of the `Flags` object returned by the parser.
 */
struct Flags: Equatable {
    var m: Bool = false
    // Other flags (i, s, u, x) would go here
}

/**
 * @enum ParseError
 * A mock error conforming to Swift's `Error` protocol.
 */
enum ParseError: Error, LocalizedError, Equatable {
    case cannotQuantifyAnchor
    
    var errorDescription: String? {
        switch self {
        case .cannotQuantifyAnchor:
            return "Cannot quantify anchor"
        }
    }
}

// --- Helper for comparing heterogeneous ASTNode arrays ---
func anyEquals(_ lhs: ASTNode, _ rhs: ASTNode) -> Bool {
    if let l = lhs as? Lit, let r = rhs as? Lit { return l == r }
    if let l = lhs as? Anchor, let r = rhs as? Anchor { return l == r }
    if let l = lhs as? Seq, let r = rhs as? Seq { return l == r }
    return false
}


// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded AST for known inputs.
 * C equivalent of the `parse` function under test.
 * Throws an error on failure.
 */
func strlingParse(src: String) throws -> (Flags, ASTNode) {
    // Category A: Core Anchors
    switch src {
    case "^": return (Flags(), Anchor(at: .start))
    case "$": return (Flags(), Anchor(at: .end))
    case #"\b"#: return (Flags(), Anchor(at: .wordBoundary))
    case #"\B"#: return (Flags(), Anchor(at: .nonWordBoundary))

    // Category B: Absolute Anchors
    case #"\A"#: return (Flags(), Anchor(at: .absoluteStart))
    case #"\Z"#: return (Flags(), Anchor(at: .absoluteEnd))
    case #"\z"#: return (Flags(), Anchor(at: .absoluteEndOnly))

    // Category C: Flags (No-op)
    case "%flags m\n^": return (Flags(m: true), Anchor(at: .start))
    case "%flags m\n$": return (Flags(m: true), Anchor(at: .end))

    // Category D: Anchors in Sequences
    case "^a":
        return (Flags(), Seq(parts: [Anchor(at: .start), Lit(value: "a")]))
    case "a$":
        return (Flags(), Seq(parts: [Lit(value: "a"), Anchor(at: .end)]))
    case #"a\b$"#:
        return (Flags(), Seq(parts: [Lit(value: "a"), Anchor(at: .wordBoundary), Anchor(at: .end)]))
    case #"^\ba\b$"#:
        return (Flags(), Seq(parts: [
            Anchor(at: .start),
            Anchor(at: .wordBoundary),
            Lit(value: "a"),
            Anchor(at: .wordBoundary),
            Anchor(at: .end)
        ]))

    // Category J: Anchors with Quantifiers (Errors)
    case "^*", "^+", "^?", "$*", "$+", "$?", #"\b*"#, #"\B*"#, #"\A*"#, #"\Z*"#, #"\z*"#:
        throw ParseError.cannotQuantifyAnchor

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

class AnchorsTests: XCTestCase {

    /**
     * @brief Corresponds to "describe('Category A: Core Anchors (^, $, \b, \B)', ...)"
     */
    func testCoreAnchors() throws {
        struct TestCase {
            let input: String
            let expected: AnchorType
        }
        
        let cases: [TestCase] = [
            TestCase(input: "^", expected: .start),
            TestCase(input: "$", expected: .end),
            TestCase(input: #"\b"#, expected: .wordBoundary),
            TestCase(input: #"\B"#, expected: .nonWordBoundary),
        ]

        for testCase in cases {
            let ast = try parse(testCase.input)
            
            guard let anchor = ast as? Anchor else {
                XCTFail("Input '\(testCase.input)' did not parse to an Anchor node. Got: \(type(of: ast))")
                return
            }
            XCTAssertEqual(anchor.at, testCase.expected)
        }
    }

    /**
     * @brief Corresponds to "describe('Category B: Absolute Anchors (\A, \Z, \z)', ...)"
     */
    func testAbsoluteAnchors() throws {
        struct TestCase {
            let input: String
            let expected: AnchorType
        }
        
        let cases: [TestCase] = [
            TestCase(input: #"\A"#, expected: .absoluteStart),
            TestCase(input: #"\Z"#, expected: .absoluteEnd),
            TestCase(input: #"\z"#, expected: .absoluteEndOnly),
        ]

        for testCase in cases {
            let ast = try parse(testCase.input)
            
            guard let anchor = ast as? Anchor else {
                XCTFail("Input '\(testCase.input)' did not parse to an Anchor node. Got: \(type(of: ast))")
                return
            }
            XCTAssertEqual(anchor.at, testCase.expected)
        }
    }

    /**
     * @brief Corresponds to "describe('Category C: Flags (No-op)', ...)"
     */
    func testFlagsDoNotChangeAnchorParsing() throws {
        // Tests that ^ remains Anchor(Start) even with flag m
        let (flags1, ast1) = try strlingParse(src: "%flags m\n^")
        XCTAssertTrue(flags1.m)
        XCTAssertEqual(ast1 as? Anchor, Anchor(at: .start))

        // Tests that $ remains Anchor(End) even with flag m
        let (flags2, ast2) = try strlingParse(src: "%flags m\n$")
        XCTAssertTrue(flags2.m)
        XCTAssertEqual(ast2 as? Anchor, Anchor(at: .end))
    }

    /**
     * @brief Corresponds to "describe('Category D: Anchors in Sequences', ...)"
     */
    func testAnchorsInSequences() throws {
        // Test: "^a"
        let ast1 = try parse("^a")
        let expected1 = Seq(parts: [Anchor(at: .start), Lit(value: "a")])
        XCTAssertEqual(ast1 as? Seq, expected1)

        // Test: "a$"
        let ast2 = try parse("a$")
        let expected2 = Seq(parts: [Lit(value: "a"), Anchor(at: .end)])
        XCTAssertEqual(ast2 as? Seq, expected2)

        // Test: "a\b$"
        let ast3 = try parse(#"a\b$"#)
        let expected3 = Seq(parts: [Lit(value: "a"), Anchor(at: .wordBoundary), Anchor(at: .end)])
        XCTAssertEqual(ast3 as? Seq, expected3)
        
        // Test: "^\ba\b$"
        let ast4 = try parse(#"^\ba\b$"#)
        let expected4 = Seq(parts: [
            Anchor(at: .start),
            Anchor(at: .wordBoundary),
            Lit(value: "a"),
            Anchor(at: .wordBoundary),
            Anchor(at: .end)
        ])
        XCTAssertEqual(ast4 as? Seq, expected4)
    }


    /**
     * @brief Corresponds to "describe('Category J: Anchors with Quantifiers', ...)"
     */
    func testQuantifiedAnchorsRaiseError() {
        let cases = [
            "^*", "^+", "^?",
            "$*", "$+", "$?",
            #"\b*"#, #"\B*"#, #"\A*"#, #"\Z*"#, #"\z*"#
        ]

        for input in cases {
            // Swift equivalent of: expect(() => parse(case)).toThrow(ParseError);
            XCTAssertThrowsError(try parse(input), "Input: \(input) should have thrown") { error in
                // Swift equivalent of: expect(err).toThrow(/Cannot quantify anchor/);
                XCTAssertEqual(error as? ParseError, .cannotQuantifyAnchor, "Input: \(input)")
                XCTAssertTrue(
                    error.localizedDescription.contains("Cannot quantify anchor"),
                    "Input: \(input)"
                )
            }
        }
    }
}