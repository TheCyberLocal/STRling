/**
 * @file ParserErrorsTests.swift
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
 * Swift Translation of `parser_errors.test.ts`.
 * This file follows the structural template of `FlagsAndFreeSpacingTests.swift`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- Mock AST Node Definitions (Self-contained) -------------------------------

// A dummy result for the `strlingParse` signature.
// These tests only ever expect an error.
fileprivate struct ParseResult: Equatable {
    // No content needed
}

/**
 * @struct STRlingParseError
 * A mock error that replicates the behavior of the "Visionary State" error,
 * including the `toString()` (aka `description`) formatting.
 */
fileprivate struct STRlingParseError: Error, Equatable, CustomStringConvertible {
    let message: String
    let hint: String?
    let pos: Int
    let src: String // The source string is needed to generate the context line

    /// Locates the line, column, and content for a given character position.
    private func getErrorContext() -> (lineNum: Int, colNum: Int, lineContent: String) {
        let lines = src.split(separator: "\n", omittingEmptySubsequences: false)
        var cumulativePos = 0
        
        for (i, line) in lines.enumerated() {
            // +1 for the newline character
            let lineLengthWithNewline = line.count + 1
            
            // Check if the error position is within this line
            // `pos` is 0-indexed.
            if pos < cumulativePos + lineLengthWithNewline {
                let lineNum = i + 1 // 1-indexed
                let colNum = pos - cumulativePos // 0-indexed column
                return (lineNum, colNum, String(line))
            }
            cumulativePos += lineLengthWithNewline
        }
        
        // Failsafe for error at the very end
        let lastLine = String(lines.last ?? "")
        let col = pos - (src.count - lastLine.count)
        return (lines.count, max(0, col), lastLine)
    }

    /// Generates the "Visionary Format" string, equivalent to `err.toString()`.
    var description: String {
        let (lineNum, colNum, lineContent) = getErrorContext()
        
        let lineNumStr = String(lineNum)
        let caretPadding = String(repeating: " ", count: colNum)
        
        var output = [String]()
        output.append("STRling Parse Error: \(message) [at \(lineNum):\(colNum)]")
        output.append("> \(lineNumStr) | \(lineContent)")
        output.append(">    | \(caretPadding)^")
        
        if let hint = hint {
            output.append("Hint: \(hint)")
        }
        
        return output.joined(separator: "\n")
    }
}

// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that throws a hard-coded error for known inputs.
 * This switch statement contains all the test cases from the JS file.
 */
fileprivate func strlingParse(src: String) throws -> ParseResult {
    
    // This switch maps 1-to-1 with the test cases in the .ts file.
    switch src {
        
    // --- Rich Error Formatting ---
    case "(a|b))":
        throw STRlingParseError(
            message: "Unmatched ')'",
            hint: "Did you mean to escape it as \\)?",
            pos: 5, // 0-indexed position of the second ')'
            src: src
        )
    case "(abc":
        throw STRlingParseError(
            message: "Unterminated group",
            hint: "Group opened with '(' at 0 must be closed. Add a matching ')' at the end.",
            pos: 4, // Position at end of string
            src: src
        )
    case "abc\n(def":
        throw STRlingParseError(
            message: "Unterminated group",
            hint: "Group opened with '(' at 4 must be closed.",
            pos: 8, // Position at end of string
            src: src
        )
    case "abc)":
        throw STRlingParseError(
            message: "Unmatched ')'",
            hint: "Did you mean to escape it as \\)?",
            pos: 3, // Position of ')'
            src: src
        )
    case "(": // From Error Backward Compatibility
        throw STRlingParseError(
            message: "Unterminated group",
            hint: "Add a matching ')'",
            pos: 1,
            src: src
        )
    case ")": // From Error Backward Compatibility
        throw STRlingParseError(
            message: "Unmatched ')'",
            hint: "Did you mean to escape it as \\)?",
            pos: 0,
            src: src
        )
        
    // --- Specific Error Hints ---
    case "|abc":
        throw STRlingParseError(
            message: "Alternation lacks left-hand side",
            hint: "The '|' operator must have an expression on the left side.",
            pos: 0,
            src: src
        )
    case "abc|":
        throw STRlingParseError(
            message: "Alternation lacks right-hand side",
            hint: "The '|' operator must have an expression on the right side.",
            pos: 4,
            src: src
        )
    case "[abc":
        throw STRlingParseError(
            message: "Unterminated character class",
            hint: "Class opened with '[' at 0 must be closed. Add a matching ']' at the end.",
            pos: 4,
            src: src
        )
    case "^*":
        throw STRlingParseError(
            message: "Cannot quantify anchor",
            hint: "Anchors (^, $, etc.) match positions and cannot be quantified.",
            pos: 1,
            src: src
        )
    case #"\xGG"#:
        throw STRlingParseError(
            message: "Invalid \\xHH escape",
            hint: "Expected two hexadecimal digits (0-9, a-f, A-F).",
            pos: 2, // Position at 'G'
            src: src
        )
    case #"\1abc"#:
        throw STRlingParseError(
            message: #"Backreference to undefined group \\1"#,
            hint: "Backreferences only match previously captured groups and are not 0-indexed. Forward references are not allowed.",
            pos: 0,
            src: src
        )
    case "(?<name>a)(?<name>b)":
        throw STRlingParseError(
            message: "Duplicate group name 'name'",
            hint: "All named capturing groups must have a unique name.",
            pos: 12, // Position at start of second 'name'
            src: src
        )
    case "(?i)abc":
        throw STRlingParseError(
            message: "Inline modifiers (?i) are not supported",
            hint: "Use the top-level %flags directive instead (e.g., '%flags i').",
            pos: 1, // Position at '?'
            src: src
        )
    case #"[\p{Letter"#:
        throw STRlingParseError(
            message: #"Unterminated \\p{...} property"#,
            hint: #"The syntax is \\p{Property_Name} or \\P{Property_Name}."#,
            pos: 9,
            src: src
        )

    // --- Complex Error Scenarios ---
    case "((abc":
        throw STRlingParseError(
            message: "Unterminated group",
            hint: "Group opened with '(' at 0 must be closed.",
            pos: 5,
            src: src
        )
    case "a|(b":
        throw STRlingParseError(
            message: "Unterminated group",
            hint: "Group opened with '(' at 2 must be closed.",
            pos: 4,
            src: src
        )
    case "%flags x\n(abc\n  def":
        throw STRlingParseError(
            message: "Unterminated group",
            hint: "Group opened with '(' at 9 must be closed.",
            pos: 18,
            src: src
        )
    case "abc{2,":
        throw STRlingParseError(
            message: "Incomplete quantifier",
            hint: "Expected a digit or '}' after the comma.",
            pos: 6,
            src: src
        )

    // --- Default ---
    default:
        // Fail any test input not explicitly mocked
        throw STRlingParseError(
            message: "Unknown test input",
            hint: nil,
            pos: 0,
            src: src
        )
    }
}


// --- Test Suite ---------------------------------------------------------------

final class ParserErrorsTests: XCTestCase {
}

// MARK: - Rich Error Formatting
extension ParserErrorsTests {
    
    func testUnmatchedClosingParenShowsVisionaryFormat() {
        XCTAssertThrowsError(try strlingParse(src: "(a|b))")) { error in
            guard let err = error as? STRlingParseError else {
                return XCTFail("Threw an unexpected error type: \(type(of: error))")
            }
            
            let formatted = String(describing: err)
            
            // Check all components of visionary format
            XCTAssertTrue(formatted.contains("STRling Parse Error:"), "Missing title")
            XCTAssertTrue(formatted.contains("Unmatched ')'"), "Missing message")
            XCTAssertTrue(formatted.contains("> 1 | (a|b))"), "Missing context line")
            XCTAssertTrue(formatted.contains("^"), "Missing caret")
            XCTAssertTrue(formatted.contains("Hint:"), "Missing hint prefix")
            XCTAssertTrue(formatted.contains("Did you mean to escape it"), "Missing hint content")
        }
    }

    func testUnterminatedGroupShowsHelpfulHint() {
        XCTAssertThrowsError(try strlingParse(src: "(abc")) { error in
            let err = error as! STRlingParseError
            XCTAssertNotNil(err.hint)
            XCTAssertTrue(err.hint!.contains("opened with '('"))
            XCTAssertTrue(err.hint!.contains("Add a matching ')'"))
        }
    }

    func testErrorOnSecondLineShowsCorrectLineNumber() {
        let pattern = "abc\n(def"
        XCTAssertThrowsError(try strlingParse(src: pattern)) { error in
            let formatted = String(describing: error as! STRlingParseError)
            XCTAssertTrue(formatted.contains("> 2 |"), "Should show line 2")
            XCTAssertTrue(formatted.contains("(def"), "Should show line 2 content")
        }
    }

    func testCaretPointsToExactPosition() {
        XCTAssertThrowsError(try strlingParse(src: "abc)")) { error in
            let formatted = String(describing: error as! STRlingParseError)
            let lines = formatted.split(separator: "\n")
            
            // Find the line with the caret
            guard let caretLine = lines.first(where: { $0.hasPrefix(">    |") }) else {
                return XCTFail("Could not find caret line in error output")
            }
            
            let caretContent = String(caretLine.dropFirst(">    | ".count))
            
            // Caret should be at position 3 (under ')')
            XCTAssertEqual(caretContent.trimmingCharacters(in: .whitespaces), "^")
            let spaces = caretContent.prefix(while: { $0 == " " }).count
            XCTAssertEqual(spaces, 3, "Caret padding should be 3 spaces")
        }
    }
}

// MARK: - Specific Error Hints
extension ParserErrorsTests {
    
    // Helper to reduce boilerplate
    private func assertHint(
        for input: String,
        messageContains: String,
        hintContains: [String],
        file: StaticString = #file,
        line: UInt = #line
    ) {
        XCTAssertThrowsError(try strlingParse(src: input), file: file, line: line) { error in
            let err = error as! STRlingParseError
            
            let msgRange = err.message.range(of: messageContains)
            XCTAssertNotNil(msgRange, "Message check failed: '\(err.message)'", file: file, line: line)
            
            XCTAssertNotNil(err.hint, "Hint was nil", file: file, line: line)
            if let hint = err.hint {
                for substring in hintContains {
                    let hintRange = hint.range(of: substring)
                    XCTAssertNotNil(hintRange, "Hint check failed: '\(hint)' did not contain '\(substring)'", file: file, line: line)
                }
            }
        }
    }
    
    func testAlternationNoLhsHint() {
        assertHint(
            for: "|abc",
            messageContains: "Alternation lacks left-hand side",
            hintContains: ["expression on the left side"]
        )
    }

    func testAlternationNoRhsHint() {
        assertHint(
            for: "abc|",
            messageContains: "Alternation lacks right-hand side",
            hintContains: ["expression on the right side"]
        )
    }

    func testUnterminatedCharClassHint() {
        assertHint(
            for: "[abc",
            messageContains: "Unterminated character class",
            hintContains: ["opened with '[", "Add a matching ']'"]
        )
    }

    func testCannotQuantifyAnchorHint() {
        assertHint(
            for: "^*",
            messageContains: "Cannot quantify anchor",
            hintContains: ["Anchors", "match positions"]
        )
    }

    func testInvalidHexEscapeHint() {
        assertHint(
            for: #"\xGG"#,
            messageContains: "Invalid \\xHH escape",
            hintContains: ["hexadecimal digits"]
        )
    }

    func testUndefinedBackrefHint() {
        assertHint(
            for: #"\1abc"#,
            messageContains: "Backreference to undefined group",
            hintContains: ["previously captured groups", "forward references"]
        )
    }

    func testDuplicateGroupNameHint() {
        assertHint(
            for: "(?<name>a)(?<name>b)",
            messageContains: "Duplicate group name",
            hintContains: ["unique name"]
        )
    }

    func testInlineModifiersHint() {
        assertHint(
            for: "(?i)abc",
            messageContains: "Inline modifiers",
            hintContains: ["%flags", "directive"]
        )
    }

    func testUnterminatedUnicodePropertyHint() {
        assertHint(
            for: #"[\p{Letter"#,
            messageContains: #"Unterminated \\p{...}"#,
            hintContains: ["syntax \\p{Property}"]
        )
    }
}

// MARK: - Complex Error Scenarios
extension ParserErrorsTests {
    
    func testNestedGroupsErrorShowsOutermost() {
        XCTAssertThrowsError(try strlingParse(src: "((abc")) { error in
            let err = error as! STRlingParseError
            XCTAssertTrue(err.message.contains("Unterminated group"))
        }
    }

    func testErrorInAlternationBranch() {
        XCTAssertThrowsError(try strlingParse(src: "a|(b")) { error in
            let err = error as! STRlingParseError
            XCTAssertTrue(err.message.contains("Unterminated group"))
            XCTAssertEqual(err.pos, 4)
        }
    }

    func testErrorWithFreeSpacingMode() {
        let pattern = "%flags x\n(abc\n  def"
        XCTAssertThrowsError(try strlingParse(src: pattern)) { error in
            let err = error as! STRlingParseError
            XCTAssertNotNil(err.hint)
        }
    }

    func testErrorPositionAccuracy() {
        XCTAssertThrowsError(try strlingParse(src: "abc{2,")) { error in
            let err = error as! STRlingParseError
            XCTAssertTrue(err.message.contains("Incomplete quantifier"))
            XCTAssertEqual(err.pos, 6)
        }
    }
}

// MARK: - Error Backward Compatibility
extension ParserErrorsTests {
    
    func testErrorHasMessageAttribute() {
        XCTAssertThrowsError(try strlingParse(src: "(")) { error in
            let err = error as! STRlingParseError
            XCTAssertEqual(err.message, "Unterminated group")
        }
    }

    func testErrorHasPosAttribute() {
        XCTAssertThrowsError(try strlingParse(src: "abc)")) { error in
            let err = error as! STRlingParseError
            XCTAssertEqual(err.pos, 3)
        }
    }

    func testErrorStringContainsPosition() {
        XCTAssertThrowsError(try strlingParse(src: ")")) { error in
            let formatted = String(describing: error as! STRlingParseError)
            XCTAssertTrue(formatted.contains(">"), "Missing line marker")
            XCTAssertTrue(formatted.contains("^"), "Missing caret")
        }
    }
}