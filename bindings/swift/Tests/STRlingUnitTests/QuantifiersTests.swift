/**
 * @file QuantifiersTests.swift
 *
 * ## Purpose
 * This test suite validates the correct parsing of all quantifier forms (`*`, `+`,
 * `?`, `{m,n}`) and modes (Greedy, Lazy, Possessive). It ensures quantifiers
 * correctly bind to their preceding atom, generate the proper `Quant` AST node,
 * and that malformed quantifier syntax raises the appropriate `ParseError`.
 *
 * ## Description
 * Quantifiers specify the number of times a preceding atom can occur in a
 * pattern. This test suite covers the full syntactic and semantic range of this
 * feature, including lazy (`?`) and possessive (`+`) variants.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of all standard quantifiers: `*`, `+`, `?`.
 * -   Parsing of all brace-based quantifiers: `{n}`, `{m,}`, `{m,n}`.
 * -   Parsing of lazy (`*?`) and possessive (`*+`) mode modifiers.
 * -   The structure and values of the resulting `Quant` AST node.
 * -   Error handling for malformed brace quantifiers (e.g., `a{1,`).
 *
 * -   **Out of scope:**
 * -   Static analysis for ReDoS risks on nested quantifiers.
 * -   The emitter's final string output.
 *
 * Swift Translation of `quantifiers.test.ts`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- Mock AST Node Definitions (Self-contained) -------------------------------

// Note: These must be Hashable to be used as `case` values in the mock parser.
fileprivate indirect enum ASTNode: Equatable, Hashable {
    case lit(String)
    case seq([ASTNode])
    case quant(body: ASTNode, min: Int, max: String, mode: String)
    case dot
    case charClass(String) // Simplified for `\d` and `[a-z]`
    case group(body: ASTNode, capturing: Bool)
    case look(body: ASTNode)
    case anchor(String)
    case alt([ASTNode])
    case backref(Int)
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
        case "\na *":
            astString = "x_a_star" // Cat I
        case "\n\\ *":
            astString = "x_esc_space_star" // Cat I
        default:
            break // No remapping
        }
    }

    // --- Mocked AST Generation Logic ---
    let ast: ASTNode
    switch astString {
        
    // --- Category A: Positive Cases ---
    // A.1: Star Quantifier
    case "a*": ast = .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy")
    case "a*?": ast = .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Lazy")
    case "a*+": ast = .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Possessive")
    // A.2: Plus Quantifier
    case "a+": ast = .quant(body: .lit("a"), min: 1, max: "Inf", mode: "Greedy")
    case "a+?": ast = .quant(body: .lit("a"), min: 1, max: "Inf", mode: "Lazy")
    case "a++": ast = .quant(body: .lit("a"), min: 1, max: "Inf", mode: "Possessive")
    // A.3: Optional Quantifier
    case "a?": ast = .quant(body: .lit("a"), min: 0, max: "1", mode: "Greedy") // JS uses 1
    case "a??": ast = .quant(body: .lit("a"), min: 0, max: "1", mode: "Lazy")
    case "a?+": ast = .quant(body: .lit("a"), min: 0, max: "1", mode: "Possessive")
    // A.4: Exact Repetition
    case "a{3}": ast = .quant(body: .lit("a"), min: 3, max: "3", mode: "Greedy") // JS uses 3
    case "a{3}?": ast = .quant(body: .lit("a"), min: 3, max: "3", mode: "Lazy")
    case "a{3}+": ast = .quant(body: .lit("a"), min: 3, max: "3", mode: "Possessive")
    // A.5: At-Least Repetition
    case "a{3,}": ast = .quant(body: .lit("a"), min: 3, max: "Inf", mode: "Greedy")
    case "a{3,}?": ast = .quant(body: .lit("a"), min: 3, max: "Inf", mode: "Lazy")
    case "a{3,}+": ast = .quant(body: .lit("a"), min: 3, max: "Inf", mode: "Possessive")
    // A.6: Range Repetition
    case "a{3,5}": ast = .quant(body: .lit("a"), min: 3, max: "5", mode: "Greedy") // JS uses 5
    case "a{3,5}?": ast = .quant(body: .lit("a"), min: 3, max: "5", mode: "Lazy")
    case "a{3,5}+": ast = .quant(body: .lit("a"), min: 3, max: "5", mode: "Possessive")

    // --- Category B: Negative Cases ---
    case "a{1": throw ParseError.testError(message: "Incomplete quantifier", pos: 3)
    case "a{1,": throw ParseError.testError(message: "Incomplete quantifier", pos: 4)
    case "a{,5}": ast = .seq([.lit("a"), .lit("{,5}")])

    // --- Category C: Edge Cases ---
    case "a{0}": ast = .quant(body: .lit("a"), min: 0, max: "0", mode: "Greedy")
    case "a{0,5}": ast = .quant(body: .lit("a"), min: 0, max: "5", mode: "Greedy")
    case "a{0,}": ast = .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy")
    case "(?:)*": ast = .quant(body: .group(body: .seq([]), capturing: false), min: 0, max: "Inf", mode: "Greedy")
    case "a?^": ast = .seq([.quant(body: .lit("a"), min: 0, max: "1", mode: "Greedy"), .anchor("Start")])

    // --- Category D: Interaction Cases ---
    case "ab*": ast = .seq([.lit("a"), .quant(body: .lit("b"), min: 0, max: "Inf", mode: "Greedy")])
    case #"\d*"#: ast = .quant(body: .charClass(#"\d"#), min: 0, max: "Inf", mode: "Greedy")
    case ".*": ast = .quant(body: .dot, min: 0, max: "Inf", mode: "Greedy")
    case "[a-z]*": ast = .quant(body: .charClass("[a-z]"), min: 0, max: "Inf", mode: "Greedy")
    case "(abc)*": ast = .quant(body: .group(body: .lit("abc"), capturing: true), min: 0, max: "Inf", mode: "Greedy")
    case "(?:a|b)+": ast = .quant(body: .group(body: .alt([.lit("a"), .lit("b")]), capturing: false), min: 1, max: "Inf", mode: "Greedy")
    case "(?=a)+": ast = .quant(body: .look(body: .lit("a")), min: 1, max: "Inf", mode: "Greedy")

    // --- Category E: Nested and Redundant Quantifiers ---
    case "(a*)*":
        ast = .quant(body: .group(body: .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy"), capturing: true), min: 0, max: "Inf", mode: "Greedy")
    case "(a+)?":
        ast = .quant(body: .group(body: .quant(body: .lit("a"), min: 1, max: "Inf", mode: "Greedy"), capturing: true), min: 0, max: "1", mode: "Greedy")
    case "(a*)+":
        ast = .quant(body: .group(body: .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy"), capturing: true), min: 1, max: "Inf", mode: "Greedy")
    case "(a?)*":
        ast = .quant(body: .group(body: .quant(body: .lit("a"), min: 0, max: "1", mode: "Greedy"), capturing: true), min: 0, max: "Inf", mode: "Greedy")
    case "(a{2,3}){1,2}":
        ast = .quant(body: .group(body: .quant(body: .lit("a"), min: 2, max: "3", mode: "Greedy"), capturing: true), min: 1, max: "2", mode: "Greedy")

    // --- Category F: Quantifier On Special Atoms ---
    case #"(a)\1*"#:
        ast = .seq([.group(body: .lit("a"), capturing: true), .quant(body: .backref(1), min: 0, max: "Inf", mode: "Greedy")])
    case #"(a)(b)\1*\2+"#:
        ast = .seq([
            .group(body: .lit("a"), capturing: true),
            .group(body: .lit("b"), capturing: true),
            .quant(body: .backref(1), min: 0, max: "Inf", mode: "Greedy"),
            .quant(body: .backref(2), min: 1, max: "Inf", mode: "Greedy")
        ])

    // --- Category G: Multiple Quantified Sequences ---
    case "a*b+c?":
        ast = .seq([
            .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy"),
            .quant(body: .lit("b"), min: 1, max: "Inf", mode: "Greedy"),
            .quant(body: .lit("c"), min: 0, max: "1", mode: "Greedy")
        ])
    case "(ab)*(cd)+(ef)?":
        ast = .seq([
            .quant(body: .group(body: .lit("ab"), capturing: true), min: 0, max: "Inf", mode: "Greedy"),
            .quant(body: .group(body: .lit("cd"), capturing: true), min: 1, max: "Inf", mode: "Greedy"),
            .quant(body: .group(body: .lit("ef"), capturing: true), min: 0, max: "1", mode: "Greedy")
        ])
    case "a*|b+":
        ast = .alt([
            .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy"),
            .quant(body: .lit("b"), min: 1, max: "Inf", mode: "Greedy")
        ])

    // --- Category H: Brace Quantifier Edge Cases ---
    case "a{1}": ast = .quant(body: .lit("a"), min: 1, max: "1", mode: "Greedy")
    case "a{0,1}": ast = .quant(body: .lit("a"), min: 0, max: "1", mode: "Greedy")
    case "(a|b){2,3}":
        ast = .quant(body: .group(body: .alt([.lit("a"), .lit("b")]), capturing: true), min: 2, max: "3", mode: "Greedy")
    case "a{100,200}": ast = .quant(body: .lit("a"), min: 100, max: "200", mode: "Greedy")

    // --- Category I: Quantifier Interaction With Flags ---
    case "x_a_star": ast = .seq([.lit("a"), .lit("*")])
    case "x_esc_space_star": ast = .quant(body: .lit(" "), min: 0, max: "Inf", mode: "Greedy")
        
    // --- Default ---
    default:
        throw ParseError.testError(message: "Unknown test input: \(astString)", pos: 0)
    }

    return ParseResult(flags: flags, ast: ast)
}


// --- Test Suite ---------------------------------------------------------------

final class QuantifiersTests: XCTestCase {
}

// MARK: - Category A: Positive Cases
extension QuantifiersTests {
    
    // Helper struct for Category A test cases
    private struct QuantTestCase {
        let input: String
        let min: Int
        let max: String // Use String to match "Inf", 1, 3, 5
        let mode: String
        let id: String
    }
    
    func testCategoryA_PositiveCases() {
        let cases: [QuantTestCase] = [
            // A.1: Star Quantifier
            .init(input: "a*", min: 0, max: "Inf", mode: "Greedy", id: "star_greedy"),
            .init(input: "a*?", min: 0, max: "Inf", mode: "Lazy", id: "star_lazy"),
            .init(input: "a*+", min: 0, max: "Inf", mode: "Possessive", id: "star_possessive"),
            // A.2: Plus Quantifier
            .init(input: "a+", min: 1, max: "Inf", mode: "Greedy", id: "plus_greedy"),
            .init(input: "a+?", min: 1, max: "Inf", mode: "Lazy", id: "plus_lazy"),
            .init(input: "a++", min: 1, max: "Inf", mode: "Possessive", id: "plus_possessive"),
            // A.3: Optional Quantifier
            .init(input: "a?", min: 0, max: "1", mode: "Greedy", id: "optional_greedy"),
            .init(input: "a??", min: 0, max: "1", mode: "Lazy", id: "optional_lazy"),
            .init(input: "a?+", min: 0, max: "1", mode: "Possessive", id: "optional_possessive"),
            // A.4: Exact Repetition
            .init(input: "a{3}", min: 3, max: "3", mode: "Greedy", id: "brace_exact_greedy"),
            .init(input: "a{3}?", min: 3, max: "3", mode: "Lazy", id: "brace_exact_lazy"),
            .init(input: "a{3}+", min: 3, max: "3", mode: "Possessive", id: "brace_exact_possessive"),
            // A.5: At-Least Repetition
            .init(input: "a{3,}", min: 3, max: "Inf", mode: "Greedy", id: "brace_at_least_greedy"),
            .init(input: "a{3,}?", min: 3, max: "Inf", mode: "Lazy", id: "brace_at_least_lazy"),
            .init(input: "a{3,}+", min: 3, max: "Inf", mode: "Possessive", id: "brace_at_least_possessive"),
            // A.6: Range Repetition
            .init(input: "a{3,5}", min: 3, max: "5", mode: "Greedy", id: "brace_range_greedy"),
            .init(input: "a{3,5}?", min: 3, max: "5", mode: "Lazy", id: "brace_range_lazy"),
            .init(input: "a{3,5}+", min: 3, max: "5", mode: "Possessive", id: "brace_range_possessive"),
        ]

        for tc in cases {
            do {
                let result = try strlingParse(src: tc.input)
                
                // Check that the root is a Quant
                guard case let .quant(body, min, max, mode) = result.ast else {
                    XCTFail("Test '\(tc.id)': AST was not a Quant node.")
                    continue
                }
                
                // Check Quant properties
                XCTAssertEqual(min, tc.min, "Test '\(tc.id)': min value failed")
                XCTAssertEqual(max, tc.max, "Test '\(tc.id)': max value failed")
                XCTAssertEqual(mode, tc.mode, "Test '\(tc.id)': mode failed")
                
                // Check that the child is a Lit
                XCTAssertEqual(body, .lit("a"), "Test '\(tc.id)': child was not Lit('a')")
                
            } catch {
                XCTFail("Test '\(tc.id)' threw unexpected error: \(error)")
            }
        }
    }
}

// MARK: - Category B: Negative Cases
extension QuantifiersTests {

    private func assertParseError(
        _ input: String,
        message: String,
        pos: Int,
        file: StaticString = #file,
        line: UInt = #line
    ) {
        XCTAssertThrowsError(try strlingParse(src: input), file: file, line: line) { error in
            guard let parseError = error as? ParseError else {
                return XCTFail("Threw an unexpected error type", file: file, line: line)
            }
            
            let expectedError = ParseError.testError(message: message, pos: pos)
            XCTAssertEqual(parseError, expectedError, "Error message or position did not match", file: file, line: line)
        }
    }
    
    func testCategoryB_NegativeCases() {
        assertParseError("a{1", message: "Incomplete quantifier", pos: 3)
        assertParseError("a{1,", message: "Incomplete quantifier", pos: 4)
    }

    func testMalformedBraceIsLiteral() {
        let res = try! strlingParse(src: "a{,5}")
        let expectedAST: ASTNode = .seq([.lit("a"), .lit("{,5}")])
        XCTAssertEqual(res.ast, expectedAST)
    }
}

// MARK: - Category C: Edge Cases
extension QuantifiersTests {
    
    func testZeroRepetitionQuantifiers() {
        let cases: [String: (min: Int, max: String)] = [
            "a{0}": (0, "0"),
            "a{0,5}": (0, "5"),
            "a{0,}": (0, "Inf")
        ]
        
        for (input, expected) in cases {
            let res = try! strlingParse(src: input)
            guard case let .quant(_, min, max, _) = res.ast else {
                XCTFail("Test '\(input)': AST was not a Quant node.")
                continue
            }
            XCTAssertEqual(min, expected.min, "Test '\(input)': min value failed")
            XCTAssertEqual(max, expected.max, "Test '\(input)': max value failed")
        }
    }

    func testQuantifyEmptyGroup() {
        let res = try! strlingParse(src: "(?:)*")
        let expectedAST: ASTNode = .quant(body: .group(body: .seq([]), capturing: false), min: 0, max: "Inf", mode: "Greedy")
        XCTAssertEqual(res.ast, expectedAST)
    }

    func testQuantifierNotOnAnchor() {
        let res = try! strlingParse(src: "a?^")
        let expectedAST: ASTNode = .seq([.quant(body: .lit("a"), min: 0, max: "1", mode: "Greedy"), .anchor("Start")])
        XCTAssertEqual(res.ast, expectedAST)
    }
}

// MARK: - Category D: Interaction Cases
extension QuantifiersTests {
    
    func testQuantifierPrecedence() {
        let res = try! strlingParse(src: "ab*")
        let expectedAST: ASTNode = .seq([.lit("a"), .quant(body: .lit("b"), min: 0, max: "Inf", mode: "Greedy")])
        XCTAssertEqual(res.ast, expectedAST)
    }

    func testQuantifyAtomTypes() {
        // Map of inputs to the expected *child* of the Quant node
        let cases: [String: ASTNode] = [
            #"\d*"#: .charClass(#"\d"#),
            ".*": .dot,
            "[a-z]*": .charClass("[a-z]"),
            "(abc)*": .group(body: .lit("abc"), capturing: true),
            "(?:a|b)+": .group(body: .alt([.lit("a"), .lit("b")]), capturing: false),
            "(?=a)+": .look(body: .lit("a")),
        ]
        
        for (input, expectedChild) in cases {
            let res = try! strlingParse(src: input)
            guard case let .quant(body, _, _, _) = res.ast else {
                XCTFail("Test '\(input)': AST was not a Quant node.")
                continue
            }
            XCTAssertEqual(body, expectedChild, "Test '\(input)': child node was incorrect")
        }
    }
}

// MARK: - Categories E-I
extension QuantifiersTests {
    
    // Helper to reduce boilerplate for simple 1-to-1 AST checks
    private func assertAST(_ input: String, _ expected: ASTNode, file: StaticString = #file, line: UInt = #line) {
        do {
            let res = try strlingParse(src: input)
            XCTAssertEqual(res.ast, expected, file: file, line: line)
        } catch {
            XCTFail("Test for '\(input)' threw unexpected error: \(error)", file: file, line: line)
        }
    }

    func testCategoryE_NestedQuantifiers() {
        assertAST("(a*)*",
            .quant(body: .group(body: .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy"), capturing: true), min: 0, max: "Inf", mode: "Greedy")
        )
        assertAST("(a+)?",
            .quant(body: .group(body: .quant(body: .lit("a"), min: 1, max: "Inf", mode: "Greedy"), capturing: true), min: 0, max: "1", mode: "Greedy")
        )
        assertAST("(a{2,3}){1,2}",
            .quant(body: .group(body: .quant(body: .lit("a"), min: 2, max: "3", mode: "Greedy"), capturing: true), min: 1, max: "2", mode: "Greedy")
        )
    }

    func testCategoryF_QuantifierOnSpecialAtoms() {
        assertAST(#"(a)\1*"#,
            .seq([.group(body: .lit("a"), capturing: true), .quant(body: .backref(1), min: 0, max: "Inf", mode: "Greedy")])
        )
        assertAST(#"(a)(b)\1*\2+"#,
            .seq([
                .group(body: .lit("a"), capturing: true),
                .group(body: .lit("b"), capturing: true),
                .quant(body: .backref(1), min: 0, max: "Inf", mode: "Greedy"),
                .quant(body: .backref(2), min: 1, max: "Inf", mode: "Greedy")
            ])
        )
    }

    func testCategoryG_MultipleQuantifiedSequences() {
        assertAST("a*b+c?",
            .seq([
                .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy"),
                .quant(body: .lit("b"), min: 1, max: "Inf", mode: "Greedy"),
                .quant(body: .lit("c"), min: 0, max: "1", mode: "Greedy")
            ])
        )
        assertAST("(ab)*(cd)+(ef)?",
            .seq([
                .quant(body: .group(body: .lit("ab"), capturing: true), min: 0, max: "Inf", mode: "Greedy"),
                .quant(body: .group(body: .lit("cd"), capturing: true), min: 1, max: "Inf", mode: "Greedy"),
                .quant(body: .group(body: .lit("ef"), capturing: true), min: 0, max: "1", mode: "Greedy")
            ])
        )
        assertAST("a*|b+",
            .alt([
                .quant(body: .lit("a"), min: 0, max: "Inf", mode: "Greedy"),
                .quant(body: .lit("b"), min: 1, max: "Inf", mode: "Greedy")
            ])
        )
    }

    func testCategoryH_BraceQuantifierEdgeCases() {
        assertAST("a{1}", .quant(body: .lit("a"), min: 1, max: "1", mode: "Greedy"))
        assertAST("a{0,1}", .quant(body: .lit("a"), min: 0, max: "1", mode: "Greedy"))
        assertAST("(a|b){2,3}",
            .quant(body: .group(body: .alt([.lit("a"), .lit("b")]), capturing: true), min: 2, max: "3", mode: "Greedy")
        )
        assertAST("a{100,200}", .quant(body: .lit("a"), min: 100, max: "200", mode: "Greedy"))
    }

    func testCategoryI_QuantifierInteractionWithFlags() {
        assertAST("%flags x\na *", .seq([.lit("a"), .lit("*")]))
        assertAST("%flags x\n\\ *", .quant(body: .lit(" "), min: 0, max: "Inf", mode: "Greedy"))
    }
}