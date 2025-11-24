import XCTest
@testable import STRling

/// Tests for the Simply API demonstrating US phone number pattern
final class UsPhoneTests: XCTestCase {
    
    func testUsPhonePattern() throws {
        // Build a US phone number pattern using the Simply API
        // Expected format: 555-555-0199 (3-3-4 format)
        let phone = Simply.merge([
            Simply.start(),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(Simply.digit(4)),
            Simply.end()
        ])
        
        let regex = try phone.compile()
        
        // Strict parity with TypeScript reference output
        XCTAssertEqual(regex, "^(\\d{3})[-. ]?(\\d{3})[-. ]?(\\d{4})$")
    }
    
    func testUsPhonePatternMatches() throws {
        let phone = Simply.merge([
            Simply.start(),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(Simply.digit(3)),
            Simply.may(Simply.anyOf("-. ")),
            Simply.capture(Simply.digit(4)),
            Simply.end()
        ])
        
        let regex = try phone.compile()
        let pattern = try NSRegularExpression(pattern: regex)
        
        // Test valid phone numbers (3-3-4 format)
        let validNumbers = ["555-555-0199", "555.555.0199", "555 555 0199", "5555550199"]
        for number in validNumbers {
            let range = NSRange(location: 0, length: number.utf16.count)
            XCTAssertNotNil(pattern.firstMatch(in: number, options: [], range: range), "Should match '\(number)'")
        }
        
        // Test invalid phone numbers
        let invalidNumbers = ["55-555-0199", "555-555-019", "abc-def-ghij"]
        for number in invalidNumbers {
            let range = NSRange(location: 0, length: number.utf16.count)
            XCTAssertNil(pattern.firstMatch(in: number, options: [], range: range), "Should not match '\(number)'")
        }
    }
    
    func testDigit() throws {
        let pattern = Simply.digit(3)
        let regex = try pattern.compile()
        XCTAssertEqual(regex, "\\d{3}")
    }
    
    func testAnyOf() throws {
        let pattern = Simply.anyOf("-. ")
        let regex = try pattern.compile()
        XCTAssertEqual(regex, "[-. ]")
    }
    
    func testCapture() throws {
        let pattern = Simply.capture(Simply.digit(3))
        let regex = try pattern.compile()
        XCTAssertEqual(regex, "(\\d{3})")
    }
    
    func testMay() throws {
        let pattern = Simply.may(Simply.anyOf("abc"))
        let regex = try pattern.compile()
        XCTAssertEqual(regex, "[abc]?")
    }
    
    func testMerge() throws {
        let pattern = Simply.merge([
            Simply.digit(3),
            Simply.anyOf("-"),
            Simply.digit(4)
        ])
        let regex = try pattern.compile()
        XCTAssertEqual(regex, "\\d{3}[-]\\d{4}")
    }
}
