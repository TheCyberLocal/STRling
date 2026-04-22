import XCTest
@testable import STRling

final class Essential5Tests: XCTestCase {

    private static var spec: [String: Any] = {
        let thisFile = URL(fileURLWithPath: #file)
        let path = thisFile
            .deletingLastPathComponent() // STRlingUnitTests
            .deletingLastPathComponent() // Tests
            .deletingLastPathComponent() // swift
            .deletingLastPathComponent() // bindings
            .deletingLastPathComponent() // root
            .appendingPathComponent("spec")
            .appendingPathComponent("stdlib")
            .appendingPathComponent("essential_5.json")
        let data = try! Data(contentsOf: path)
        return try! JSONSerialization.jsonObject(with: data) as! [String: Any]
    }()

    private func fixtures(_ pat: String, _ key: String) -> [String] {
        let patterns = Self.spec["patterns"] as! [String: Any]
        let entry = patterns[pat] as! [String: Any]
        let fx = entry["fixtures"] as! [String: Any]
        return fx[key] as! [String]
    }

    private func compile(_ node: Node) throws -> NSRegularExpression {
        let body = try Essential.compile(node)
        return try NSRegularExpression(pattern: "^(?:\(body))$")
    }

    private func assertAllMatch(_ node: Node, _ samples: [String]) throws {
        let re = try compile(node)
        for s in samples {
            let range = NSRange(s.startIndex..., in: s)
            XCTAssertNotNil(re.firstMatch(in: s, range: range), "expected match: \(s)")
        }
    }

    private func assertNoneMatch(_ node: Node, _ samples: [String]) throws {
        let re = try compile(node)
        for s in samples {
            let range = NSRange(s.startIndex..., in: s)
            XCTAssertNil(re.firstMatch(in: s, range: range), "unexpected match: \(s)")
        }
    }

    func testEmailValid()    throws { try assertAllMatch(Essential.email(), fixtures("email", "valid")) }
    func testEmailInvalid()  throws { try assertNoneMatch(Essential.email(), fixtures("email", "invalid")) }
    func testUrlValid()      throws { try assertAllMatch(Essential.url(), fixtures("url", "valid")) }
    func testUrlInvalid()    throws { try assertNoneMatch(Essential.url(), fixtures("url", "invalid")) }
    func testUuidValid()     throws { try assertAllMatch(Essential.uuid(), fixtures("uuid", "valid_default")) }
    func testUuidInvalid()   throws { try assertNoneMatch(Essential.uuid(), fixtures("uuid", "invalid_default")) }
    func testUuidV4Valid()   throws { try assertAllMatch(Essential.uuid(version: 4), fixtures("uuid", "valid_v4")) }
    func testUuidV4Invalid() throws { try assertNoneMatch(Essential.uuid(version: 4), fixtures("uuid", "invalid_v4")) }
    func testIpV4Valid()     throws { try assertAllMatch(Essential.ip(version: 4), fixtures("ip", "valid_v4")) }
    func testIpV4Invalid()   throws { try assertNoneMatch(Essential.ip(version: 4), fixtures("ip", "invalid_v4")) }
    func testIpV6Valid()     throws { try assertAllMatch(Essential.ip(version: 6), fixtures("ip", "valid_v6")) }
    func testIpV6Invalid()   throws { try assertNoneMatch(Essential.ip(version: 6), fixtures("ip", "invalid_v6")) }
    func testIpAnyV4()       throws { try assertAllMatch(Essential.ip(), fixtures("ip", "valid_v4")) }
    func testIpAnyV6()       throws { try assertAllMatch(Essential.ip(), fixtures("ip", "valid_v6")) }
    func testDateTimeValid()   throws { try assertAllMatch(Essential.dateTime(), fixtures("dateTime", "valid")) }
    func testDateTimeInvalid() throws { try assertNoneMatch(Essential.dateTime(), fixtures("dateTime", "invalid")) }
}
