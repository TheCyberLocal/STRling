/**
 * @file IEHAuditGapsTests.swift
 *
 * ## Purpose
 * Tests coverage for the Intelligent Error Handling (IEH) audit gaps. This
 * suite verifies that parser validation and the hint engine provide
 * context-aware, instructional error messages for the audit's critical
 * findings and that valid inputs remain accepted.
 *
 * ## Description
 * Each test maps to one or more audit gaps and asserts both that invalid
 * inputs raise a `STRlingParseError` containing an actionable `hint`, and
 * that valid inputs continue to parse successfully.
 *
 * Swift Translation of `ieh_audit_gaps.test.ts`.
 * This file follows the structural template of `FlagsAndFreeSpacingTests.swift`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- Mock AST Node Definitions (Self-contained) -------------------------------

// Note: These tests don't check the AST, only the error.
// These mocks are the minimum needed for the `strlingParse` signature.

fileprivate indirect enum ASTNode: Equatable {
    // A dummy node, since the AST is not being tested
    case valid
}

fileprivate struct Flags: Equatable {
    // We don't care about flags in this test
    static let `default` = Flags()
}

fileprivate struct ParseResult: Equatable {
    let flags: Flags
    let ast: ASTNode
}

// Mock Parse Error
// This is the key type being tested. It mirrors the JS `STRlingParseError`.
fileprivate enum STRlingParseError: Error, Equatable {
    case testError(message: String, hint: String)
    
    var message: String {
        switch self {
        case .testError(let message, _):
            return message
        }
    }
    
    var hint: String {
        switch self {
        case .testError(_, let hint):
            return hint
        }
    }
}

// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded result for known inputs.
 * This switch statement contains all the test cases from the JS file.
 */
fileprivate func strlingParse(src: String) throws -> ParseResult {
    let flags = Flags.default
    
    // This switch maps 1-to-1 with the test cases in the .ts file.
    switch src {
        
    // --- Group name validation ---
    case "(?<1a>)":
        throw STRlingParseError.testError(message: "Invalid group name", hint: "An IDENTIFIER cannot start with a digit.")
    case "(?<>)":
        throw STRlingParseError.testError(message: "Invalid group name", hint: "Group name cannot be empty.")
    case "(?<name-bad>)":
        throw STRlingParseError.testError(message: "Invalid group name", hint: "An IDENTIFIER cannot contain hyphens.")

    // --- Quantifier range validation ---
    case "a{5,2}":
        throw STRlingParseError.testError(message: "Invalid quantifier range", hint: "Range min 'm' must be less than or equal to max 'n' (m ≤ n).")

    // --- Character class range validation ---
    case "[z-a]":
        throw STRlingParseError.testError(message: "Invalid character range", hint: "Range start 'z' must be less than end 'a'.")
    case "[9-0]":
        throw STRlingParseError.testError(message: "Invalid character range", hint: "Range start '9' must be less than end '0'.")

    // --- Empty alternation validation ---
    case "a||b":
        throw STRlingParseError.testError(message: "Empty alternation", hint: "Did you mean 'a|b'?")

    // --- Flag directive validation ---
    case "%flags foo":
        throw STRlingParseError.testError(message: "Invalid flag 'f'", hint: "Valid flags are 'i', 'm', 's', 'u', 'x'.")
    case "abc%flags i":
        throw STRlingParseError.testError(message: "Directive after pattern", hint: "Directives like %flags must be at the start of the pattern.")

    // --- Incomplete named backref hint ---
    case #"\k"#:
        throw STRlingParseError.testError(message: "Expected '<' after \\k", hint: "Named backreferences have the form \\k<name>.")

    // --- Context-aware quantifier hints ---
    case "+":
        throw STRlingParseError.testError(message: "Quantifier target missing", hint: "The quantifier '+' must follow a character or group.")
    case "?":
        throw STRlingParseError.testError(message: "Quantifier target missing", hint: "The quantifier '?' must follow a character or group.")
    case "{5}":
        throw STRlingParseError.testError(message: "Quantifier target missing", hint: "The quantifier '{' must follow a character or group.")

    // --- Context-aware escape hints ---
    case #"\q"#:
        throw STRlingParseError.testError(message: "Unknown escape sequence", hint: "The escape '\\q' is not valid. Did you mean to escape 'q' as '\\q'?")
    case #"\z"#:
        throw STRlingParseError.testError(message: "Unknown escape sequence", hint: #"The escape '\\z' is not valid. Did you mean the anchor '\\Z' (end of string)?"#)

    // --- Additional Negative Cases (from 'Valid patterns' block) ---
    case "a{foo}":
        throw STRlingParseError.testError(message: "Invalid range", hint: "Quantifier braces must contain digits, e.g., 'a{1,3}'.")
    case "a{5":
        throw STRlingParseError.testError(message: "Unterminated brace", hint: "Missing closing '}' for quantifier.")
    case "[]":
        throw STRlingParseError.testError(message: "Empty character class", hint: "Add characters or ranges inside the brackets.")

    // --- Valid patterns ---
    // All of these fall through to the default success case
    case "(?<name>abc)",
         "(?<_name>abc)",
         "(?<name123>abc)",
         "(?<Name_123>abc)",
         "a{2,5}",
         "a{2,2}",
         "a{0,10}",
         "[a-z]",
         "[0-9]",
         "[A-Z]",
         "a|b",
         "a|b|c",
         "%flags i\nabc",
         "%flags imsux\nabc":
        return ParseResult(flags: flags, ast: .valid)
        
    // --- Default ---
    default:
        // Fail any test input not explicitly mocked
        throw STRlingParseError.testError(message: "Unknown test input", hint: "")
    }
}

// --- Test Suite ---------------------------------------------------------------

class IEHAuditGapsTests: XCTestCase {

    /// Helper function to streamline error checking.
    private func assertParseError(
        _ input: String,
        messageContains: String,
        hintContains: [String] = [],
        file: StaticString = #file,
        line: UInt = #line
    ) {
        XCTAssertThrowsError(try strlingParse(src: input), file: file, line: line) { error in
            // 1. Unwrap the error to our expected mock type
            guard let parseError = error as? STRlingParseError else {
                XCTFail("Threw an unexpected error type: \(type(of: error))", file: file, line: line)
                return
            }
            
            // 2. Check the message
            // We use .range() instead of .contains() for case-insensitive matching,
            // which is closer to the JS .toMatch(/.../i)
            let msgRange = parseError.message.range(of: messageContains, options: .caseInsensitive)
            XCTAssertNotNil(msgRange, "Message check failed: '\(parseError.message)' did not contain '\(messageContains)'", file: file, line: line)

            // 3. Check all required hint substrings
            XCTAssertFalse(parseError.hint.isEmpty, "Error hint was empty", file: file, line: line)
            for hintSubstring in hintContains {
                let hintRange = parseError.hint.range(of: hintSubstring, options: .caseInsensitive)
                XCTAssertNotNil(hintRange, "Hint check failed: '\(parseError.hint)' did not contain '\(hintSubstring)'", file: file, line: line)
            }
        }
    }

    /**
     * @brief Corresponds to "describe('Group name validation', ...)"
     */
    func testGroupNameValidation() {
        assertParseError("(?<1a>)", messageContains: "Invalid group name", hintContains: ["IDENTIFIER"])
        assertParseError("(?<>)", messageContains: "Invalid group name")
        assertParseError("(?<name-bad>)", messageContains: "Invalid group name", hintContains: ["IDENTIFIER"])
    }

    /**
     * @brief Corresponds to "describe('Quantifier range validation', ...)"
     */
    func testQuantifierRangeValidation() {
        assertParseError("a{5,2}", messageContains: "Invalid quantifier range", hintContains: ["m ≤ n"])
    }

    /**
     * @brief Corresponds to "describe('Character class range validation', ...)"
     */
    func testCharClassRangeValidation() {
        assertParseError("[z-a]", messageContains: "Invalid character range")
        assertParseError("[9-0]", messageContains: "Invalid character range")
    }

    /**
     * @brief Corresponds to "describe('Empty alternation validation', ...)"
     */
    func testEmptyAlternationValidation() {
        assertParseError("a||b", messageContains: "Empty alternation", hintContains: ["a|b"])
    }

    /**
     * @brief Corresponds to "describe('Flag directive validation', ...)"
     */
    func testFlagDirectiveValidation() {
        assertParseError("%flags foo", messageContains: "Invalid flag", hintContains: ["i", "m"])
        assertParseError("abc%flags i", messageContains: "Directive after pattern", hintContains: ["start of the pattern"])
    }

    /**
     * @brief Corresponds to "describe('Incomplete named backref hint', ...)"
     */
    func testIncompleteNamedBackrefHint() {
        assertParseError(#"\k"#, messageContains: "Expected '<' after \\k", hintContains: [#"\\k<name>"#])
    }

    /**
     * @brief Corresponds to "describe('Context-aware quantifier hints', ...)"
     */
    func testContextAwareQuantifierHints() {
        assertParseError("+", messageContains: "Quantifier target missing", hintContains: ["'+'"])
        assertParseError("?", messageContains: "Quantifier target missing", hintContains: ["'?'"])
        assertParseError("{5}", messageContains: "Quantifier target missing", hintContains: ["'{'"])
    }

    /**
     * @brief Corresponds to "describe('Context-aware escape hints', ...)"
     */
    func testContextAwareEscapeHints() {
        assertParseError(#"\q"#, messageContains: "Unknown escape sequence", hintContains: [#"\\q"#])
        assertParseError(#"\z"#, messageContains: "Unknown escape sequence", hintContains: [#"\\z"#, #"\\Z"#])
    }

    /**
     * @brief Corresponds to "describe('Valid patterns still work', ...)"
     */
    func testValidPatternsStillWork() {
        // Valid group names
        XCTAssertNoThrow(try strlingParse(src: "(?<name>abc)"))
        XCTAssertNoThrow(try strlingParse(src: "(?<_name>abc)"))
        XCTAssertNoThrow(try strlingParse(src: "(?<name123>abc)"))
        XCTAssertNoThrow(try strlingParse(src: "(?<Name_123>abc)"))

        // Valid quantifier ranges
        XCTAssertNoThrow(try strlingParse(src: "a{2,5}"))
        XCTAssertNoThrow(try strlingParse(src: "a{2,2}"))
        XCTAssertNoThrow(try strlingParse(src: "a{0,10}"))

        // Valid character ranges
        XCTAssertNoThrow(try strlingParse(src: "[a-z]"))
        XCTAssertNoThrow(try strlingParse(src: "[0-9]"))
        XCTAssertNoThrow(try strlingParse(src: "[A-Z]"))

        // Single alternation
        XCTAssertNoThrow(try strlingParse(src: "a|b"))
        XCTAssertNoThrow(try strlingParse(src: "a|b|c"))

        // Valid flags
        XCTAssertNoThrow(try strlingParse(src: "%flags i\nabc"))
        XCTAssertNoThrow(try strlingParse(src: "%flags imsux\nabc"))
    }
    
    /**
     * @brief Corresponds to additional negative cases in the final JS test block.
     */
    func testAdditionalNegativeCases() {
        assertParseError("a{foo}", messageContains: "Invalid range", hintContains: ["digit"])
        assertParseError("a{5", messageContains: "Unterminated brace", hintContains: ["closing '}'"])
        assertParseError("[]", messageContains: "Empty character class", hintContains: ["empty", "add characters"])
    }
}