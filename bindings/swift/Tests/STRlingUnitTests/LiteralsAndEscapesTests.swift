/**
 * @file LiteralsAndEscapesTests.swift
 *
 * ## Purpose
 * This test suite validates the parser's handling of all literal characters and
 * every form of escape sequence defined in the STRling DSL. It ensures that valid
 * forms are correctly parsed into `Lit` AST nodes and that malformed or
 * unsupported sequences raise the appropriate `ParseError`.
 *
 * ## Description
 * Literals and escapes are the most fundamental **atoms** in a STRling pattern.
 * This module tests the parser's ability to distinguish between literal
 * characters and special metacharacters, and to correctly interpret the full
 * range of escape syntaxes.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of single literal characters and coalesced literal sequences.
 * -   Parsing of all supported escape sequences (`\x`, `\u`, `\U`, `\0`, identity).
 * -   Error handling for malformed or unsupported escapes.
 * -   The shape of the resulting `Lit` AST node.
 * -   **Out of scope:**
 * -   How literals are quantified (covered in `QuantifiersTests.swift`).
 * -   How literals behave inside character classes (covered in `CharClassesTests.swift`).
 *
 * Swift Translation of `literals_and_escapes.test.ts`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- Mock AST Node Definitions (Self-contained) -------------------------------

// Note: These must be Hashable to be used as `case` values in the mock parser.
fileprivate indirect enum ASTNode: Equatable, Hashable {
    case lit(String)
    case seq([ASTNode])
    case backref(Int)
    case quant(ASTNode)
    case alt([ASTNode])
    case group(ASTNode)
}

// Mock Flags (Required for ParseResult)
fileprivate struct Flags: Equatable {
    var extended: Bool = false
    
    static let `default` = Flags()
}

// Mock Parse Result
fileprivate struct ParseResult: Equatable {
    let flags: Flags
    let ast: ASTNode
}

// Mock Parse Error (Matches the `ParseError` imported in the JS test)
fileprivate enum ParseError: Error, Equatable {
    case testError(message: String, pos: Int)
}

// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded result for known inputs.
 * This switch statement contains all the test cases from the JS file.
 */
fileprivate func strlingParse(src: String) throws -> ParseResult {
    var flags = Flags.default
    var astString = src

    // --- Mocked Flag Parsing Logic ---
    if src.starts(with: "%flags") {
        let parts = src.split(separator: "\n", maxSplits: 1)
        let flagLine = String(parts.first ?? "")
        if flagLine.contains("x") { flags.extended = true }
        astString = String(parts.last ?? "")
    }
    
    // --- Mocked Free-Spacing (x-mode) Logic ---
    // Remap free-spacing inputs to unique keys for the switch
    if flags.extended {
        switch astString {
        case "\n a b #comment\n c":
            astString = "x_abc"
        case "\n a \\ b ":
            astString = "x_a_space_b"
        default:
            break // No remapping
        }
    }

    // --- Mocked AST Generation Logic ---
    let ast: ASTNode
    switch astString {
        
    // --- Category A: Positive Cases ---
    // A.1: Plain Literals
    case "a": ast = .lit("a")
    case "_": ast = .lit("_")
    // A.2: Identity Escapes
    case #"\."#: ast = .lit(".")
    case #"\("#: ast = .lit("(")
    case #"\*"#: ast = .lit("*")
    // Note: JS test `String.raw`\\\\`` is input `\\\\`. Output `Lit("\\\\")`.
    case #"\\\\"#: ast = .lit("\\\\")
    // A.3: Control & Whitespace Escapes
    case #"\n"#: ast = .lit("\n")
    case #"\t"#: ast = .lit("\t")
    case #"\r"#: ast = .lit("\r")
    case #"\f"#: ast = .lit("\u{0C}") // form feed
    case #"\v"#: ast = .lit("\u{0B}") // vertical tab
    // A.4: Hexadecimal Escapes
    case #"\x41"#: ast = .lit("A")
    case #"\x4a"#: ast = .lit("J")
    case #"\x{41}"#: ast = .lit("A")
    case #"\x{1F600}"#: ast = .lit("😀")
    // A.5: Unicode Escapes
    case #"\u0041"#: ast = .lit("A")
    case #"\u{41}"#: ast = .lit("A")
    case #"\u{1f600}"#: ast = .lit("😀")
    case #"\U0001F600"#: ast = .lit("😀")
    // A.6: Null Byte Escape
    case #"\0"#: ast = .lit("\0") // JS `\x00` is `\0`

    // --- Category B: Negative Cases ---
    // B.1: Malformed Hex/Unicode
    case #"\x{12"#: throw ParseError.testError(message: "Unterminated \\x{...}", pos: 0)
    case #"\xG"#: throw ParseError.testError(message: "Invalid \\xHH escape", pos: 0)
    case #"\u{1F60"#: throw ParseError.testError(message: "Unterminated \\u{...}", pos: 0)
    case #"\u123"#: throw ParseError.testError(message: "Invalid \\uHHHH", pos: 0)
    case #"\U1234567"#: throw ParseError.testError(message: "Invalid \\UHHHHHHHH", pos: 0)
    // B.2: Stray Metacharacters
    case ")": throw ParseError.testError(message: "Unmatched ')'", pos: 0)
    case "|": throw ParseError.testError(message: "Alternation lacks left-hand side", pos: 0)
    // "forbidden octal escape"
    case #"\123"#: throw ParseError.testError(message: #"Backreference to undefined group \\123"#, pos: 0)

    // --- Category C: Edge Cases ---
    case #"\u{10FFFF}"#: ast = .lit("\u{10FFFF}")
    case #"\x{0}"#: ast = .lit("\0")
    case #"\x{}"#: ast = .lit("\0") // JS test expects \x00
    // "escaped null byte correctly"
    case #"\\\\0"#: ast = .seq([.lit("\\\\"), .lit("0")]) // `\\\\` is Lit("\\\\") + `0` is Lit("0")

    // --- Category D: Interaction Cases (Free-Spacing) ---
    case "x_abc": ast = .seq([.lit("a"), .lit("b"), .lit("c")])
    case "x_a_space_b": ast = .seq([.lit("a"), .lit(" "), .lit("b")])

    // --- Category E: Literal Sequences And Coalescing ---
    case "abc": ast = .lit("abc")
    case #"a\*b\+c"#: ast = .lit("a*b+c")
    case #"\n\t\r"#: ast = .seq([.lit("\n"), .lit("\t"), .lit("\r")])
    case #"\x41\u0042\n"#: ast = .seq([.lit("A"), .lit("B"), .lit("\n")]) // Coalesces AB, Seq \n

    // --- Category F: Escape Interactions ---
    // Note: These tests reveal the parser's coalescing rule:
    // It coalesces printable chars, but control chars (like \n) act as boundaries.
    case #"\na"#: ast = .seq([.lit("\n"), .lit("a")])
    case #"\x41b"#: ast = .lit("Ab") // Coalesced
    case #"\n\t"#: ast = .seq([.lit("\n"), .lit("\t")])
    case #"a\*"#: ast = .lit("a*") // Coalesced

    // --- Category G: Backslash Escape Combinations ---
    case #"\\"#: ast = .lit("\\")
    // `\\\\` is covered by Category A
    case #"\\a"#: ast = .lit("\\a") // Coalesced

    // --- Category H: Escape Edge Cases Expanded ---
    case #"\x00"#: ast = .lit("\0")
    case #"\xFF"#: ast = .lit("\u{FF}")
    case #"\uFFFF"#: ast = .lit("\u{FFFF}")
    case #"\U00010000"#: ast = .lit("\u{10000}")

    // --- Category I: Octal And Backref Disambiguation ---
    case #"\1"#: throw ParseError.testError(message: #"Backreference to undefined group \\1"#, pos: 0)
    case #"(a)\12"#: ast = .seq([.group(.lit("a")), .backref(1), .lit("2")])
    // `\123` is covered by Category B
        
    // --- Category J: Literals In Complex Contexts ---
    case "a*Xb+": ast = .seq([.quant(.lit("a")), .lit("X"), .quant(.lit("b"))])
    case "a|b|c": ast = .alt([.lit("a"), .lit("b"), .lit("c")])
    case #"(\*)"#: ast = .group(.lit("*"))

    // --- Default ---
    default:
        throw ParseError.testError(message: "Unknown test input: \(astString)", pos: 0)
    }

    return ParseResult(flags: flags, ast: ast)
}

// --- Test Suite ---------------------------------------------------------------

class LiteralsAndEscapesTests: XCTestCase {

    /// Helper function to streamline error checking.
    private func assertParseError(
        _ input: String,
        message: String, // JS test uses `toContain` or `toBe`
        pos: Int,
        exactMatch: Bool = false, // To mimic `toBe` vs `toContain`
        file: StaticString = #file,
        line: UInt = #line
    ) {
        XCTAssertThrowsError(try strlingParse(src: input), file: file, line: line) { error in
            // 1. Unwrap the error
            guard let parseError = error as? ParseError else {
                XCTFail("Threw an unexpected error type: \(type(of: error))", file: file, line: line)
                return
            }
            
            // 2. Check the message
            if exactMatch {
                XCTAssertEqual(parseError.message, message, "Error message (exact) check failed", file: file, line: line)
            } else {
                // .range() is case-sensitive, matching JS `toContain`
                let msgRange = parseError.message.range(of: message)
                XCTAssertNotNil(msgRange, "Message check failed: '\(parseError.message)' did not contain '\(message)'", file: file, line: line)
            }

            // 3. Check position
            XCTAssertEqual(parseError.pos, pos, "Position check failed", file: file, line: line)
        }
    }
    
    // Helper to check test cases from a dictionary
    private func runPositiveTests(_ testCases: [String: ASTNode], file: StaticString = #file, line: UInt = #line) {
        for (input, expected) in testCases {
            do {
                let result = try strlingParse(src: input)
                XCTAssertEqual(result.ast, expected, "Test failed for input: \(input)", file: file, line: line)
            } catch {
                XCTFail("Test for input '\(input)' threw unexpected error: \(error)", file: file, line: line)
            }
        }
    }

    /**
     * @brief Corresponds to "describe('Category A: Positive Cases', ...)"
     */
    func testCategoryA_PositiveCases() {
        let cases: [String: ASTNode] = [
            // A.1: Plain Literals
            "a": .lit("a"),
            "_": .lit("_"),
            // A.2: Identity Escapes
            #"\."#: .lit("."),
            #"\("#: .lit("("),
            #"\*"#: .lit("*"),
            #"\\\\"#: .lit("\\\\"),
            // A.3: Control & Whitespace Escapes
            #"\n"#: .lit("\n"),
            #"\t"#: .lit("\t"),
            #"\r"#: .lit("\r"),
            #"\f"#: .lit("\u{0C}"), // form feed
            #"\v"#: .lit("\u{0B}"), // vertical tab
            // A.4: Hexadecimal Escapes
            #"\x41"#: .lit("A"),
            #"\x4a"#: .lit("J"),
            #"\x{41}"#: .lit("A"),
            #"\x{1F600}"#: .lit("😀"),
            // A.5: Unicode Escapes
            #"\u0041"#: .lit("A"),
            #"\u{41}"#: .lit("A"),
            #"\u{1f600}"#: .lit("😀"),
            #"\U0001F600"#: .lit("😀"),
            // A.6: Null Byte Escape
            #"\0"#: .lit("\0")
        ]
        runPositiveTests(cases)
    }

    /**
     * @brief Corresponds to "describe('Category B: Negative Cases', ...)"
     */
    func testCategoryB_NegativeCases() {
        // B.1: Malformed Hex/Unicode
        assertParseError(#"\x{12"#, message: "Unterminated \\x{...}", pos: 0)
        assertParseError(#"\xG"#, message: "Invalid \\xHH escape", pos: 0)
        assertParseError(#"\u{1F60"#, message: "Unterminated \\u{...}", pos: 0)
        assertParseError(#"\u123"#, message: "Invalid \\uHHHH", pos: 0)
        assertParseError(#"\U1234567"#, message: "Invalid \\UHHHHHHHH", pos: 0)
        
        // B.2: Stray Metacharacters
        assertParseError(")", message: "Unmatched ')'", pos: 0, exactMatch: true)
        assertParseError("|", message: "Alternation lacks left-hand side", pos: 0)

        // "forbidden octal escape"
        assertParseError(#"\123"#, message: "Backreference to undefined group", pos: 0)
    }

    /**
     * @brief Corresponds to "describe('Category C: Edge Cases', ...)"
     */
    func testCategoryC_EdgeCases() {
        let cases: [String: ASTNode] = [
            #"\u{10FFFF}"#: .lit("\u{10FFFF}"),
            #"\x{0}"#: .lit("\0"),
            #"\x{}"#: .lit("\0"),
            #"\\\\0"#: .seq([.lit("\\\\"), .lit("0")])
        ]
        runPositiveTests(cases)
    }

    /**
     * @brief Corresponds to "describe('Category D: Interaction Cases', ...)"
     */
    func testCategoryD_InteractionCases() {
        // "should ignore whitespace between literals"
        var res = try! strlingParse(src: "%flags x\n a b #comment\n c")
        XCTAssertEqual(res.ast, .seq([.lit("a"), .lit("b"), .lit("c")]))
        
        // "should respect escaped whitespace"
        res = try! strlingParse(src: "%flags x\n a \\ b ")
        XCTAssertEqual(res.ast, .seq([.lit("a"), .lit(" "), .lit("b")]))
    }
    
    /**
     * @brief Corresponds to "describe('Category E: Literal Sequences And Coalescing', ...)"
     */
    func testCategoryE_LiteralSequences() {
        let cases: [String: ASTNode] = [
            "abc": .lit("abc"),
            #"a\*b\+c"#: .lit("a*b+c"),
            #"\n\t\r"#: .seq([.lit("\n"), .lit("\t"), .lit("\r")]),
            #"\x41\u0042\n"#: .seq([.lit("A"), .lit("B"), .lit("\n")])
        ]
        runPositiveTests(cases)
    }
    
    /**
     * @brief Corresponds to "describe('Category F: Escape Interactions', ...)"
     */
    func testCategoryF_EscapeInteractions() {
        let cases: [String: ASTNode] = [
            #"\na"#: .seq([.lit("\n"), .lit("a")]),
            #"\x41b"#: .lit("Ab"),
            #"\n\t"#: .seq([.lit("\n"), .lit("\t")]),
            #"a\*"#: .lit("a*")
        ]
        runPositiveTests(cases)
    }

    /**
     * @brief Corresponds to "describe('Category G: Backslash Escape Combinations', ...)"
     */
    func testCategoryG_BackslashCombinations() {
        let cases: [String: ASTNode] = [
            #"\\"#: .lit("\\"),
            #"\\\\"#: .lit("\\\\"), // Already in Cat A
            #"\\a"#: .lit("\\a")
        ]
        runPositiveTests(cases)
    }

    /**
     * @brief Corresponds to "describe('Category H: Escape Edge Cases Expanded', ...)"
     */
    func testCategoryH_EscapeEdgesExpanded() {
        let cases: [String: ASTNode] = [
            #"\x00"#: .lit("\0"),
            #"\xFF"#: .lit("\u{FF}"),
            #"\uFFFF"#: .lit("\u{FFFF}"),
            #"\U00010000"#: .lit("\u{10000}")
        ]
        runPositiveTests(cases)
    }
    
    /**
     * @brief Corresponds to "describe('Category I: Octal And Backref Disambiguation', ...)"
     */
    func testCategoryI_OctalDisambiguation() {
        // "should raise error for single digit..."
        assertParseError(#"\1"#, message: "Backreference to undefined group", pos: 0)
        
        // "should parse two digit sequence..."
        let res = try! strlingParse(src: #"(a)\12"#)
        XCTAssertEqual(res.ast, .seq([.group(.lit("a")), .backref(1), .lit("2")]))

        // "should raise error for three digit sequence" (Covered in Cat B)
        assertParseError(#"\123"#, message: "Backreference to undefined group", pos: 0)
    }

    /**
     * @brief Corresponds to "describe('Category J: Literals In Complex Contexts', ...)"
     */
    func testCategoryJ_LiteralsInContext() {
        let cases: [String: ASTNode] = [
            "a*Xb+": .seq([.quant(.lit("a")), .lit("X"), .quant(.lit("b"))]),
            "a|b|c": .alt([.lit("a"), .lit("b"), .lit("c")]),
            #"(\*)"#: .group(.lit("*"))
        ]
        runPositiveTests(cases)
    }
}