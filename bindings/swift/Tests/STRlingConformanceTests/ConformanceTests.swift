import XCTest
@testable import STRling

final class ConformanceTests: XCTestCase {

    let compiler = Compiler()

    func testConformance() throws {
        // Locate the tests/spec directory relative to this file
        // Path: bindings/swift/Tests/STRlingConformanceTests/ConformanceTests.swift
        let thisFile = URL(fileURLWithPath: #file)
        let specDir = thisFile
            .deletingLastPathComponent() // STRlingConformanceTests
            .deletingLastPathComponent() // Tests
            .deletingLastPathComponent() // swift
            .deletingLastPathComponent() // bindings
            .deletingLastPathComponent() // root
            .appendingPathComponent("tests")
            .appendingPathComponent("spec")

        let fileManager = FileManager.default
        guard fileManager.fileExists(atPath: specDir.path) else {
            print("Spec directory not found at \(specDir.path). Skipping conformance tests.")
            return
        }

        let files = try fileManager.contentsOfDirectory(atPath: specDir.path)
        var passedCount = 0
        var totalCount = 0

        for file in files where file.hasSuffix(".json") {
            totalCount += 1
            let url = specDir.appendingPathComponent(file)
            let data = try Data(contentsOf: url)

            struct TestFixture: Decodable {
                let input_ast: Node
                let expected_ir: IROp
            }

            do {
                let fixture = try JSONDecoder().decode(TestFixture.self, from: data)
                let compiledIR = try compiler.compile(node: fixture.input_ast)
                
                if compiledIR == fixture.expected_ir {
                    passedCount += 1
                } else {
                    print("Mismatch in file: \(file)")
                    XCTFail("Mismatch in file: \(file)")
                }
            } catch {
                print("Failed to decode or test \(file): \(error)")
                XCTFail("Failed to decode \(file): \(error)")
            }
        }

        print("Passed \(passedCount)/\(totalCount) tests")
    }
}
