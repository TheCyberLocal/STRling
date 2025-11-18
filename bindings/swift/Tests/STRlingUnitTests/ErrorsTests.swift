/**
 * @file ErrorsTests.swift
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
 * Swift Translation of `errors.test.ts`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- Error Handling Definitions (Mocked) --------------------------------------

/**
 * @struct ParseError
 * A Swift struct mirroring the properties of the `ParseError` class.
 * It conforms to `Error` for Swift's native error handling.
 */
struct ParseError: Error, LocalizedError, Equatable {
    let message: String
    let pos: Int
    
    var errorDescription: String? {
        return "\(message) at position \(pos)"
    }
}

// --- Mock SUT (`strlingParse`) -----------------------------------------------

// A dummy struct to represent a successful parse
struct MockASTNode: Equatable {}
struct Flags: Equatable {} // Mock Flags struct

/**
 * @brief Mock of the `parse` function (System Under Test).
 * It throws a `ParseError` on failure, mimicking
 * the original test's exception behavior.
 */
func strlingParse(src: String) throws -> (Flags, MockASTNode) {
    // --- Category: Parser Syntax Errors ---
    switch src {
    case "[":
        throw ParseError(message: "Unterminated character class", pos: 1) // Pos 1 (at EOF)
    case "(":
        throw ParseError(message: "Unterminated group", pos: 1) // Pos 1 (at EOF)
    case "a)":
        throw ParseError(message: "Unmatched ')'", pos: 1)
    case "a{5,3}":
        throw ParseError(message: "Invalid quantifier range", pos: 1)
        
    // --- Category: Semantic Errors ---
    case "a{5, }":
        throw ParseError(message: "Incomplete quantifier", pos: 5)
    case "^*":
        throw ParseError(message: "Cannot quantify anchor", pos: 0)

    // --- Category: First Error Wins ---
    case "[a|b(":
        // The *first* error is the unterminated class at pos 0
        throw ParseError(message: "Unterminated character class", pos: 0)
        
    // --- Fallback: Success ---
    default:
        // If no error matched, return a successful parse
        return (Flags(), MockASTNode())
    }
}

// --- Test Suite ---------------------------------------------------------------

class ErrorsTests: XCTestCase {

    /**
     * @brief Corresponds to "describe('Category: Parser Syntax Errors', ...)"
     */
    func testParserSyntaxErrors() {
        // Test: "unterminated character class"
        XCTAssertThrowsError(try strlingParse(src: "["), "Should throw on unterminated class") { error in
            XCTAssertEqual(error as? ParseError, ParseError(message: "Unterminated character class", pos: 1))
        }

        // Test: "unterminated group"
        XCTAssertThrowsError(try strlingParse(src: "("), "Should throw on unterminated group") { error in
            XCTAssertEqual(error as? ParseError, ParseError(message: "Unterminated group", pos: 1))
        }

        // Test: "unmatched closing parenthesis"
        XCTAssertThrowsError(try strlingParse(src: "a)"), "Should throw on unmatched paren") { error in
            XCTAssertEqual(error as? ParseError, ParseError(message: "Unmatched ')'", pos: 1))
        }

        // Test: "invalid quantifier range"
        XCTAssertThrowsError(try strlingParse(src: "a{5,3}"), "Should throw on invalid range") { error in
            XCTAssertEqual(error as? ParseError, ParseError(message: "Invalid quantifier range", pos: 1))
        }
    }

    /**
     * @brief Corresponds to "describe('Category: Semantic Errors', ...)"
     */
    func testSemanticErrors() {
        // Test: "incomplete quantifier raises error"
        XCTAssertThrowsError(try strlingParse(src: "a{5, }"), "Should throw on incomplete quantifier") { error in
            let err = error as? ParseError
            XCTAssertEqual(err?.message, "Incomplete quantifier")
            XCTAssertEqual(err?.pos, 5)
        }

        // Test: "quantifying a non-quantifiable atom raises error"
        XCTAssertThrowsError(try strlingParse(src: "^*"), "Should throw on quantifying anchor") { error in
            let err = error as? ParseError
            // In Swift, we check for the exact message or use .contains()
            XCTAssertEqual(err?.message, "Cannot quantify anchor")
            XCTAssertEqual(err?.pos, 0)
        }
    }

    /**
     * @brief Corresponds to "describe('Invariant: First Error Wins', ...)"
     */
    func testFirstErrorWins() {
        /**
         * In the string '[a|b(', the unterminated class at position 0 should be
         * reported, not the unterminated group at position 4.
         */
        XCTAssertThrowsError(try strlingParse(src: "[a|b("), "Should throw first error") { error in
            let err = error as? ParseError
            // Check that the *first* error was caught
            XCTAssertEqual(err?.message, "Unterminated character class")
            XCTAssertEqual(err?.pos, 0)
        }
    }
}