import XCTest
@testable import STRling

final class ConformanceTests: XCTestCase {
    
    let emitter = PCRE2Emitter()
    
    func testConformance() throws {
        // Locate the Resources directory
        // In Swift PM with .process("Resources"), the resources are at the root of the bundle or in a subdirectory
        // We need to find where they are.
        
        guard let resourcePath = Bundle.module.resourcePath else {
            XCTFail("Could not find resource path")
            return
        }
        
        let resourcesUrl = URL(fileURLWithPath: resourcePath).appendingPathComponent("Resources")
        let fileManager = FileManager.default
        
        // Check if Resources dir exists, if not try the root (sometimes flattened)
        let searchUrl: URL
        if fileManager.fileExists(atPath: resourcesUrl.path) {
            searchUrl = resourcesUrl
        } else {
            searchUrl = URL(fileURLWithPath: resourcePath)
        }
        
        let files = try fileManager.contentsOfDirectory(atPath: searchUrl.path)
        
        var passedCount = 0
        var totalCount = 0
        
        for file in files where file.hasSuffix(".json") {
            totalCount += 1
            print("Testing \(file)...")
            let url = searchUrl.appendingPathComponent(file)
            let data = try Data(contentsOf: url)
            
            struct TestFixture: Decodable {
                let pattern: Node
                let expected: Expected
                
                struct Expected: Decodable {
                    let pcre2: String?
                }
            }
            
            do {
                let fixture = try JSONDecoder().decode(TestFixture.self, from: data)
                
                if let expectedPcre2 = fixture.expected.pcre2 {
                    let emitted = try emitter.emit(node: fixture.pattern)
                    XCTAssertEqual(emitted, expectedPcre2, "Mismatch in file: \(file)")
                    if emitted == expectedPcre2 {
                        passedCount += 1
                    }
                } else {
                    print("Skipping \(file): No expected PCRE2 output")
                    passedCount += 1 // Count as passed if we skip? Or just ignore. Let's ignore.
                    totalCount -= 1
                }
            } catch {
                print("Failed to decode or test \(file): \(error)")
                XCTFail("Failed to decode \(file): \(error)")
            }
        }
        
        print("Passed \(passedCount)/\(totalCount) tests")
    }
}
