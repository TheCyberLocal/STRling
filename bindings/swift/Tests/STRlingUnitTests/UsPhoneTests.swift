import XCTest
@testable import STRling

/// Tests for the Simply API demonstrating US phone number pattern
final class UsPhoneTests: XCTestCase {
    
    func testUsPhonePattern() throws {
        // Build a US phone number pattern using the Simply API
        // Expected format: 555-0199 or 555.0199 or 555 0199 or 5550199
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
        
        // The emitter produces simplified form
        XCTAssertEqual(regex, "^([\\d]{3})[\\-. ]?([\\d]{3})[\\-. ]?([\\d]{4})$")
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
        XCTAssertNotNil(pattern.firstMatch(in: "555-555-0199", options: [], range: NSRange(location: 0, length: 12)))
        XCTAssertNotNil(pattern.firstMatch(in: "555.555.0199", options: [], range: NSRange(location: 0, length: 12)))
        XCTAssertNotNil(pattern.firstMatch(in: "555 555 0199", options: [], range: NSRange(location: 0, length: 12)))
        XCTAssertNotNil(pattern.firstMatch(in: "5555550199", options: [], range: NSRange(location: 0, length: 10)))
        
        // Test invalid phone numbers
        XCTAssertNil(pattern.firstMatch(in: "55-555-0199", options: [], range: NSRange(location: 0, length: 11)))
        XCTAssertNil(pattern.firstMatch(in: "555-555-019", options: [], range: NSRange(location: 0, length: 11)))
        XCTAssertNil(pattern.firstMatch(in: "abc-def-ghij", options: [], range: NSRange(location: 0, length: 12)))
    }
    
    func testDigit() throws {
        let pattern = Simply.digit(3)
        let regex = try pattern.compile()
        XCTAssertEqual(regex, "[\\d]{3}")
    }
    
    func testAnyOf() throws {
        let pattern = Simply.anyOf("-. ")
        let regex = try pattern.compile()
        XCTAssertEqual(regex, "[\\-. ]")
    }
    
    func testCapture() throws {
        let pattern = Simply.capture(Simply.digit(3))
        let regex = try pattern.compile()
        XCTAssertEqual(regex, "([\\d]{3})")
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
        XCTAssertEqual(regex, "[\\d]{3}[\\-][\\d]{4}")
    }
}
