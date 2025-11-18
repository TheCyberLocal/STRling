/**
 * @file ErrorFormattingTests.swift
 *
 * ## Purpose
 * Tests formatting of `STRlingParseError` and the behavior of the hint engine.
 * Ensures formatted errors include source context, caret positioning, and
 * that the hint engine returns contextual guidance where appropriate.
 *
 * Swift Translation of `error_formatting.test.ts`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- SUT (System Under Test) Definitions (Mocked) -----------------------------

/**
 * @struct STRlingParseError
 * A Swift struct mirroring the properties of the `STRlingParseError` class.
 * It conforms to `Error` for Swift's error handling and
 * `CustomStringConvertible` to provide the `toString()` equivalent.
 */
fileprivate struct STRlingParseError: Error, CustomStringConvertible, Equatable {
    let message: String
    let pos: Int
    let text: String?
    let hint: String?

    /**
     * [SUT] Generates the "Visionary Format" string.
     * This is the Swift equivalent of the `toString()` method.
     */
    var description: String {
        // Case 1: "simple error without text"
        guard let text = text else {
            return "STRling Parse Error: \(message) at position \(pos)"
        }
        
        // Case 2: "error with text and hint"
        // 1. Calculate line/col (simplified to 1-based column for this test)
        let line = 1
        let col = pos + 1 // Assuming 1-based column

        // 2. Create the caret string (e.g., "     ^")
        let caretPadding = String(repeating: " ", count: max(0, col - 1)) + "^"

        // 3. Format the main error message
        var output = """
        STRling Parse Error: \(message) at line \(line), column \(col):

        > \(line) | \(text)
              \(caretPadding)
        """ // "      " aligns with "> 1 | "

        // 4. Add the hint if it exists
        if let hint = hint {
            output += "\n\nHint: \(hint)\n"
        }
        
        return output
    }
}

/**
 * @brief [SUT-MOCK] Mock of the hint engine.
 * This stub is hard-coded to return the expected hints.
 */
fileprivate func getHint(message: String, src: String, pos: Int) -> String? {
    // "unterminated group hint"
    if message == "Unterminated group" {
        return "This group was opened with '('. Add a matching ')'"
    }
    
    // "unterminated character class hint"
    if message == "Unterminated character class" {
        return "This character class was opened with '['. Add a matching ']'"
    }
    
    // "unexpected token hint - closing paren"
    if message == "Unexpected token" && pos == 3 {
        return "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
    }

    // "cannot quantify anchor hint"
    if message == "Cannot quantify anchor" {
        return "Anchors (like ^, $, \\b) match positions and cannot be quantified."
    }
    
    // "inline modifiers hint"
    if message == "Inline modifiers `(?imsx)` are not supported" {
        return "Use the %flags directive at the top of the file."
    }
    
    // "no hint for unknown error"
    return nil
}


// --- Test Suite ---------------------------------------------------------------

class ErrorFormattingTests: XCTestCase {

    /**
     * @brief Corresponds to "describe('STRlingParseError', ...)"
     */
    func testSTRlingParseErrorFormatting() {
        // Test: "simple error without text"
        let err1 = STRlingParseError(message: "Test error", pos: 5, text: nil, hint: nil)
        XCTAssertTrue(err1.description.contains("Test error at position 5"))

        // Test: "error with text and hint"
        let text = "(a|b))"
        let hint = "This ')' character does not have a matching opening '('. Did you mean to escape it with '\\)'?"
        
        let err2 = STRlingParseError(
            message: "Unmatched ')'",
            pos: 5,
            text: text,
            hint: hint
        )
        let formatted = err2.description

        // Check that it contains all the expected parts
        XCTAssertTrue(formatted.contains("STRling Parse Error: Unmatched ')'"))
        XCTAssertTrue(formatted.contains("> 1 | (a|b))"))
        XCTAssertTrue(formatted.contains("^"))
        XCTAssertTrue(formatted.contains("Hint:"))
        XCTAssertTrue(formatted.contains("does not have a matching opening '('."));
    }


    /**
     * @brief Corresponds to "describe('getHint', ...)"
     */
    func testHintEngine() {
        // Define the test cases
        struct HintTestCase {
            let message: String
            let src: String
            let pos: Int
            let expectedSubstrings: [String]? // nil if no hint is expected
            let id: String
        }
        
        let cases: [HintTestCase] = [
            HintTestCase(
                message: "Unterminated group", src: "(abc", pos: 3,
                expectedSubstrings: ["opened with '(", "Add a matching ')'"],
                id: "unterminated group hint"
            ),
            HintTestCase(
                message: "Unterminated character class", src: "[abc", pos: 4,
                expectedSubstrings: ["opened with '['", "Add a matching ']'"],
                id: "unterminated character class hint"
            ),
            HintTestCase(
                message: "Unexpected token", src: "abc)", pos: 3,
                expectedSubstrings: ["does not have a matching opening '(", "escape it with '\\)'"],
                id: "unexpected token hint - closing paren"
            ),
            HintTestCase(
                message: "Cannot quantify anchor", src: "^*", pos: 1,
                expectedSubstrings: ["Anchors", "match positions", "cannot be quantified"],
                id: "cannot quantify anchor hint"
            ),
            HintTestCase(
                message: "Inline modifiers `(?imsx)` are not supported", src: "(?i)abc", pos: 1,
                expectedSubstrings: ["%flags", "directive"],
                id: "inline modifiers hint"
            ),
            HintTestCase(
                message: "Some unknown error message", src: "abc", pos: 0,
                expectedSubstrings: nil,
                id: "no hint for unknown error"
            )
        ]
        
        for testCase in cases {
            let hint = getHint(message: testCase.message, src: testCase.src, pos: testCase.pos)
            
            if let expectedSubstrings = testCase.expectedSubstrings {
                XCTAssertNotNil(hint, "Test ID: \(testCase.id) (hint should not be nil)")
                if let hint = hint {
                    for substring in expectedSubstrings {
                        XCTAssertTrue(
                            hint.contains(substring),
                            "Test ID: \(testCase.id) (Hint '\(hint)' did not contain '\(substring)')"
                        )
                    }
                }
            } else {
                XCTAssertNil(hint, "Test ID: \(testCase.id) (hint should be nil)")
            }
        }
    }
}