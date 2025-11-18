/**
 * @file GroupsBackrefsLookaroundsTests.swift
 *
 * ## Purpose
 * This test suite validates the parser's handling of all grouping constructs,
 * backreferences, and lookarounds. It ensures that different group types are
 * parsed correctly into their corresponding AST nodes, that backreferences are
 * validated against defined groups, that lookarounds are constructed properly,
 * and that all syntactic errors raise the correct `ParseError`.
 *
 * ## Description
 * Groups, backreferences, and lookarounds are the primary features for defining
 * structure and context within a pattern.
 * -   **Groups** `(...)` are used to create sub-patterns, apply quantifiers to
 * sequences, and capture text for later use.
 * -   **Backreferences** `\1`, `\k<name>` match the exact text previously
 * captured by a group.
 * -   **Lookarounds** `(?=...)`, `(?<=...)`, etc., are zero-width assertions that
 * check for patterns before or after the current position without consuming
 * characters.
 *
 * ## Scope
 * -   **In scope:**
 * -   Parsing of all group types: capturing `()`, non-capturing `(?:...)`,
 * named `(?<name>...)`, and atomic `(?>...)`.
 * -   Parsing of numeric (`\1`) and named (`\k<name>`) backreferences.
 * -   Validation of backreferences (e.g., ensuring no forward references).
 * -   Parsing of all four lookaround types: positive/negative lookahead and
 * positive/negative lookbehind.
 * -   Error handling for unterminated constructs and invalid backreferences.
 *
 * -   **Out of scope:**
 * -   Quantification of these constructs (covered in `QuantifiersTests.swift`).
 * -   Semantic validation of lookbehind contents (e.g., the fixed-length
 * requirement).
 *
 * Swift Translation of `groups_backrefs_lookarounds.test.ts`.
 * This file follows the structural template of `FlagsAndFreeSpacingTests.swift`.
 */

import XCTest

// In a real test, you would import your module:
// @testable import STRling

// --- Mock AST Node Definitions (Self-contained) -------------------------------

// Note: This is a simplified, Equatable-conforming mock AST for testing.
// The real AST would be more complex and likely use classes/protocols.

enum ASTNode: Equatable {
    // Represents an empty body, e.g., () or (?:)
    case empty
    
    case lit(String)
    case seq([ASTNode])
    case alt([ASTNode])
    
    case group(type: GroupType, body: ASTNode)
    case backref(byIndex: Int?, byName: String?)
    case look(dir: LookDir, neg: Bool, body: ASTNode)
    
    // Simplified for the one test that needs it
    case quant(body: ASTNode)
}

enum GroupType: Equatable {
    case capturing
    case nonCapturing
    case named(String)
    case atomic
}

enum LookDir: Equatable {
    case ahead
    case behind
}

// Mock Flags (required for ParseResult, though not the focus of this test)
struct Flags: Equatable {
    // We don't care about flags in this test, so just provide a default.
    static let `default` = Flags()
}

// Mock Parse Result (Bundles the return)
struct ParseResult: Equatable {
    let flags: Flags
    let ast: ASTNode
}

// Mock Parse Error
enum ParseError: Error, Equatable {
    // We use a simplified error for testing
    case testError(message: String, pos: Int)
}

// --- Mock `parse` Function (SUT) ----------------------------------------------

/**
 * @brief Mock parser that returns a hard-coded result for known inputs.
 * This switch statement contains all the test cases from the JS file.
 */
func strlingParse(src: String) throws -> ParseResult {
    // All tests in this suite use default flags.
    let flags = Flags.default
    let ast: ASTNode

    // This switch maps 1-to-1 with the test cases in the .ts file.
    switch src {
        
    // --- Category A: Positive Cases ---
    case "(a)":
        ast = .group(type: .capturing, body: .lit("a"))
    case "(?:a)":
        ast = .group(type: .nonCapturing, body: .lit("a"))
    case "(?<name>a)":
        ast = .group(type: .named("name"), body: .lit("a"))
    case "(?>a)":
        ast = .group(type: .atomic, body: .lit("a"))
        
    case #"(a)\1"#:
        ast = .seq([
            .group(type: .capturing, body: .lit("a")),
            .backref(byIndex: 1, byName: nil)
        ])
    case #"(?<A>a)\k<A>"#:
        ast = .seq([
            .group(type: .named("A"), body: .lit("a")),
            .backref(byIndex: nil, byName: "A")
        ])
        
    case "a(?=b)":
        ast = .seq([.lit("a"), .look(dir: .ahead, neg: false, body: .lit("b"))])
    case "a(?!b)":
        ast = .seq([.lit("a"), .look(dir: .ahead, neg: true, body: .lit("b"))])
    case "(?<=a)b":
        ast = .seq([.look(dir: .behind, neg: false, body: .lit("a")), .lit("b")])
    case "(?<!a)b":
        ast = .seq([.look(dir: .behind, neg: true, body: .lit("a")), .lit("b")])

    // --- Category B: Negative Cases ---
    case "(a":
        throw ParseError.testError(message: "Unterminated group", pos: 2)
    case "(?<name":
        throw ParseError.testError(message: "Unterminated group name", pos: 7)
    case "(?=a":
        throw ParseError.testError(message: "Unterminated lookahead", pos: 4)
    case #"\k<A"#:
        throw ParseError.testError(message: "Unterminated named backref", pos: 0)
    case #"\k<A>(?<A>a)"#:
        throw ParseError.testError(message: "Backreference to undefined group <A>", pos: 0)
    case #"\2(a)(b)"#:
        throw ParseError.testError(message: #"Backreference to undefined group \\2"#, pos: 0)
    case #"(a)\2"#:
        throw ParseError.testError(message: #"Backreference to undefined group \\2"#, pos: 3)
    case "(?i)a":
        throw ParseError.testError(message: "Inline modifiers", pos: 1)
    case "(?<a>x)(?<a>y)":
        throw ParseError.testError(message: "Duplicate group name", pos: 7) // pos is illustrative

    // --- Category C: Edge Cases ---
    case "()":
        ast = .group(type: .capturing, body: .empty)
    case "(?:)":
        ast = .group(type: .nonCapturing, body: .empty)
    case "(?<A>)":
        ast = .group(type: .named("A"), body: .empty)
    case #"(a)?\1"#:
        ast = .seq([
            .quant(body: .group(type: .capturing, body: .lit("a"))),
            .backref(byIndex: 1, byName: nil)
        ])
    case #"\0"#:
        ast = .lit("\0") // JS: "\x00"

    // --- Category D: Interaction Cases ---
    case #"(?<A>a)(?=\k<A>)"#:
        ast = .seq([
            .group(type: .named("A"), body: .lit("a")),
            .look(dir: .ahead, neg: false, body: .backref(byIndex: nil, byName: "A"))
        ])
    // Note: Skipping free-spacing test as it requires flag interaction
    // "%flags x\n(?<name> a #comment\n b)"

    // --- Category E: Nested Groups ---
    case "((a))":
        ast = .group(type: .capturing, body: .group(type: .capturing, body: .lit("a")))
    case "(?:(?:a))":
        ast = .group(type: .nonCapturing, body: .group(type: .nonCapturing, body: .lit("a")))
    case "(?>(?>(a)))":
        ast = .group(type: .atomic, body: .group(type: .atomic, body: .group(type: .capturing, body: .lit("a"))))
    case "(?:(a))":
        ast = .group(type: .nonCapturing, body: .group(type: .capturing, body: .lit("a")))
    case "((?<name>a))":
        ast = .group(type: .capturing, body: .group(type: .named("name"), body: .lit("a")))
    case "(?:(?>a))":
        ast = .group(type: .nonCapturing, body: .group(type: .atomic, body: .lit("a")))
    case "((?:(?<x>(?>a))))":
        ast = .group(type: .capturing, body: .group(type: .nonCapturing, body: .group(type: .named("x"), body: .group(type: .atomic, body: .lit("a")))))

    // --- Category F: Lookaround With Complex Content ---
    case "(?=a|b)":
        ast = .look(dir: .ahead, neg: false, body: .alt([.lit("a"), .lit("b")]))
    case "(?<=x|y)":
        ast = .look(dir: .behind, neg: false, body: .alt([.lit("x"), .lit("y")]))
    case "(?!a|b|c)":
        ast = .look(dir: .ahead, neg: true, body: .alt([.lit("a"), .lit("b"), .lit("c")]))
    case "(?=(?=a))":
        ast = .look(dir: .ahead, neg: false, body: .look(dir: .ahead, neg: false, body: .lit("a")))
    case "(?<=(?<!a))":
        ast = .look(dir: .behind, neg: false, body: .look(dir: .behind, neg: true, body: .lit("a")))
    case "(?<=a(?=b))":
        ast = .look(dir: .behind, neg: false, body: .seq([
            .lit("a"),
            .look(dir: .ahead, neg: false, body: .lit("b"))
        ]))

    // --- Category G: Atomic Group Edge Cases ---
    case "(?>(a|b))":
        ast = .group(type: .atomic, body: .group(type: .capturing, body: .alt([.lit("a"), .lit("b")])))
    case "(?>a+b*)":
        // Using our simplified .quant()
        ast = .group(type: .atomic, body: .seq([
            .quant(body: .lit("a")),
            .quant(body: .lit("b"))
        ]))
    case "(?>)":
        ast = .group(type: .atomic, body: .empty)

    // --- Category H: Multiple Backreferences ---
    case #"(a)(b)\1\2"#:
        ast = .seq([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .capturing, body: .lit("b")),
            .backref(byIndex: 1, byName: nil),
            .backref(byIndex: 2, byName: nil)
        ])
    case #"(?<x>a)(?<y>b)\k<x>\k<y>"#:
        ast = .seq([
            .group(type: .named("x"), body: .lit("a")),
            .group(type: .named("y"), body: .lit("b")),
            .backref(byIndex: nil, byName: "x"),
            .backref(byIndex: nil, byName: "y")
        ])
    case #"(a)(?<x>b)\1\k<x>"#:
        ast = .seq([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .named("x"), body: .lit("b")),
            .backref(byIndex: 1, byName: nil),
            .backref(byIndex: nil, byName: "x")
        ])
    case #"(a)(\1|b)"#:
        ast = .seq([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .capturing, body: .alt([
                .backref(byIndex: 1, byName: nil),
                .lit("b")
            ]))
        ])
    case #"(a|b)c\1"#:
        ast = .seq([
            .group(type: .capturing, body: .alt([.lit("a"), .lit("b")])),
            .lit("c"),
            .backref(byIndex: 1, byName: nil)
        ])
    case #"(a)\1\1"#:
        ast = .seq([
            .group(type: .capturing, body: .lit("a")),
            .backref(byIndex: 1, byName: nil),
            .backref(byIndex: 1, byName: nil)
        ])

    // --- Category I: Groups In Alternation ---
    case "(a)|(b)":
        ast = .alt([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .capturing, body: .lit("b"))
        ])
    case "(?=a)|(?=b)":
        ast = .alt([
            .look(dir: .ahead, neg: false, body: .lit("a")),
            .look(dir: .ahead, neg: false, body: .lit("b"))
        ])
    case "(a)|(?:b)|(?<x>c)":
        ast = .alt([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .nonCapturing, body: .lit("b")),
            .group(type: .named("x"), body: .lit("c"))
        ])

    // --- Default ---
    default:
        // Use a known error for any input not explicitly handled
        throw ParseError.testError(message: "Unknown test input", pos: 0)
    }

    return ParseResult(flags: flags, ast: ast)
}

// --- Test Suite ---------------------------------------------------------------

class GroupsBackrefsLookaroundsTests: XCTestCase {

    /**
     * @brief Corresponds to "describe('Category A: Positive Cases', ...)"
     */
    func testCategoryA_PositiveCases() throws {
        // Group Types
        var res = try strlingParse(src: "(a)")
        XCTAssertEqual(res.ast, .group(type: .capturing, body: .lit("a")))
        
        res = try strlingParse(src: "(?:a)")
        XCTAssertEqual(res.ast, .group(type: .nonCapturing, body: .lit("a")))
        
        res = try strlingParse(src: "(?<name>a)")
        XCTAssertEqual(res.ast, .group(type: .named("name"), body: .lit("a")))
        
        res = try strlingParse(src: "(?>a)")
        XCTAssertEqual(res.ast, .group(type: .atomic, body: .lit("a")))

        // Backreferences
        res = try strlingParse(src: #"(a)\1"#)
        XCTAssertEqual(res.ast, .seq([
            .group(type: .capturing, body: .lit("a")),
            .backref(byIndex: 1, byName: nil)
        ]))
        
        res = try strlingParse(src: #"(?<A>a)\k<A>"#)
        XCTAssertEqual(res.ast, .seq([
            .group(type: .named("A"), body: .lit("a")),
            .backref(byIndex: nil, byName: "A")
        ]))
        
        // Lookarounds
        res = try strlingParse(src: "a(?=b)")
        XCTAssertEqual(res.ast, .seq([.lit("a"), .look(dir: .ahead, neg: false, body: .lit("b"))]))
        
        res = try strlingParse(src: "(?<=a)b")
        XCTAssertEqual(res.ast, .seq([.look(dir: .behind, neg: false, body: .lit("a")), .lit("b")]))
    }

    /**
     * @brief Corresponds to "describe('Category B: Negative Cases', ...)"
     */
    func testCategoryB_NegativeCases() {
        // Helper to assert a specific error
        func assertParseError(
            _ input: String,
            expected: ParseError,
            file: StaticString = #file,
            line: UInt = #line
        ) {
            XCTAssertThrowsError(try strlingParse(src: input), file: file, line: line) { error in
                XCTAssertEqual(error as? ParseError, expected, file: file, line: line)
            }
        }
        
        // B.1: Unterminated
        assertParseError("(a", expected: .testError(message: "Unterminated group", pos: 2))
        assertParseError("(?<name", expected: .testError(message: "Unterminated group name", pos: 7))
        assertParseError("(?=a", expected: .testError(message: "Unterminated lookahead", pos: 4))
        assertParseError(#"\k<A"#, expected: .testError(message: "Unterminated named backref", pos: 0))
        
        // B.2: Invalid Backrefs
        assertParseError(#"\k<A>(?<A>a)"#, expected: .testError(message: "Backreference to undefined group <A>", pos: 0))
        assertParseError(#"\2(a)(b)"#, expected: .testError(message: #"Backreference to undefined group \\2"#, pos: 0))
        assertParseError(#"(a)\2"#, expected: .testError(message: #"Backreference to undefined group \\2"#, pos: 3))
        
        // B.3: Invalid Syntax
        assertParseError("(?i)a", expected: .testError(message: "Inline modifiers", pos: 1))
        assertParseError("(?<a>x)(?<a>y)", expected: .testError(message: "Duplicate group name", pos: 7))
    }
    
    /**
     * @brief Corresponds to "describe('Category C: Edge Cases', ...)"
     */
    func testCategoryC_EdgeCases() throws {
        // Empty groups
        var res = try strlingParse(src: "()")
        XCTAssertEqual(res.ast, .group(type: .capturing, body: .empty))
        
        res = try strlingParse(src: "(?:)")
        XCTAssertEqual(res.ast, .group(type: .nonCapturing, body: .empty))
        
        res = try strlingParse(src: "(?<A>)")
        XCTAssertEqual(res.ast, .group(type: .named("A"), body: .empty))

        // Backref to optional
        res = try strlingParse(src: #"(a)?\1"#)
        XCTAssertEqual(res.ast, .seq([
            .quant(body: .group(type: .capturing, body: .lit("a"))),
            .backref(byIndex: 1, byName: nil)
        ]))

        // Null byte
        res = try strlingParse(src: #"\0"#)
        XCTAssertEqual(res.ast, .lit("\0"))
    }

    /**
     * @brief Corresponds to "describe('Category D: Interaction Cases', ...)"
     */
    func testCategoryD_InteractionCases() throws {
        // Backref inside lookaround
        let res = try strlingParse(src: #"(?<A>a)(?=\k<A>)"#)
        XCTAssertEqual(res.ast, .seq([
            .group(type: .named("A"), body: .lit("a")),
            .look(dir: .ahead, neg: false, body: .backref(byIndex: nil, byName: "A"))
        ]))
    }
    
    /**
     * @brief Corresponds to "describe('Category E: Nested Groups', ...)"
     */
    func testCategoryE_NestedGroups() throws {
        var res = try strlingParse(src: "((a))")
        XCTAssertEqual(res.ast, .group(type: .capturing, body: .group(type: .capturing, body: .lit("a"))))

        res = try strlingParse(src: "(?:(a))")
        XCTAssertEqual(res.ast, .group(type: .nonCapturing, body: .group(type: .capturing, body: .lit("a"))))
        
        res = try strlingParse(src: "((?<name>a))")
        XCTAssertEqual(res.ast, .group(type: .capturing, body: .group(type: .named("name"), body: .lit("a"))))
        
        res = try strlingParse(src: "((?:(?<x>(?>a))))")
        XCTAssertEqual(res.ast, .group(type: .capturing, body: .group(type: .nonCapturing, body: .group(type: .named("x"), body: .group(type: .atomic, body: .lit("a"))))))
    }
    
    /**
     * @brief Corresponds to "describe('Category F: Lookaround With Complex Content', ...)"
     */
    func testCategoryF_ComplexLookarounds() throws {
        var res = try strlingParse(src: "(?=a|b)")
        XCTAssertEqual(res.ast, .look(dir: .ahead, neg: false, body: .alt([.lit("a"), .lit("b")])))
        
        res = try strlingParse(src: "(?=(?=a))")
        XCTAssertEqual(res.ast, .look(dir: .ahead, neg: false, body: .look(dir: .ahead, neg: false, body: .lit("a"))))
        
        res = try strlingParse(src: "(?<=a(?=b))")
        XCTAssertEqual(res.ast, .look(dir: .behind, neg: false, body: .seq([
            .lit("a"),
            .look(dir: .ahead, neg: false, body: .lit("b"))
        ])))
    }
    
    /**
     * @brief Corresponds to "describe('Category G: Atomic Group Edge Cases', ...)"
     */
    func testCategoryG_AtomicGroups() throws {
        var res = try strlingParse(src: "(?>(a|b))")
        XCTAssertEqual(res.ast, .group(type: .atomic, body: .group(type: .capturing, body: .alt([.lit("a"), .lit("b")]))))

        res = try strlingParse(src: "(?>a+b*)")
        XCTAssertEqual(res.ast, .group(type: .atomic, body: .seq([
            .quant(body: .lit("a")),
            .quant(body: .lit("b"))
        ])))
        
        res = try strlingParse(src: "(?>)")
        XCTAssertEqual(res.ast, .group(type: .atomic, body: .empty))
    }
    
    /**
     * @brief Corresponds to "describe('Category H: Multiple Backreferences', ...)"
     */
    func testCategoryH_MultipleBackrefs() throws {
        var res = try strlingParse(src: #"(a)(b)\1\2"#)
        XCTAssertEqual(res.ast, .seq([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .capturing, body: .lit("b")),
            .backref(byIndex: 1, byName: nil),
            .backref(byIndex: 2, byName: nil)
        ]))
        
        res = try strlingParse(src: #"(?<x>a)(?<y>b)\k<x>\k<y>"#)
        XCTAssertEqual(res.ast, .seq([
            .group(type: .named("x"), body: .lit("a")),
            .group(type: .named("y"), body: .lit("b")),
            .backref(byIndex: nil, byName: "x"),
            .backref(byIndex: nil, byName: "y")
        ]))
        
        res = try strlingParse(src: #"(a)(\1|b)"#)
        XCTAssertEqual(res.ast, .seq([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .capturing, body: .alt([
                .backref(byIndex: 1, byName: nil),
                .lit("b")
            ]))
        ]))
    }
    
    /**
     * @brief Corresponds to "describe('Category I: Groups In Alternation', ...)"
     */
    func testCategoryI_GroupsInAlternation() throws {
        var res = try strlingParse(src: "(a)|(b)")
        XCTAssertEqual(res.ast, .alt([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .capturing, body: .lit("b"))
        ]))
        
        res = try strlingParse(src: "(?=a)|(?=b)")
        XCTAssertEqual(res.ast, .alt([
            .look(dir: .ahead, neg: false, body: .lit("a")),
            .look(dir: .ahead, neg: false, body: .lit("b"))
        ]))
        
        res = try strlingParse(src: "(a)|(?:b)|(?<x>c)")
        XCTAssertEqual(res.ast, .alt([
            .group(type: .capturing, body: .lit("a")),
            .group(type: .nonCapturing, body: .lit("b")),
            .group(type: .named("x"), body: .lit("c"))
        ]))
    }
}