import STRling
import XCTest

final class AdapterTests: XCTestCase {
    func testSourceRequestContainsCanonicalEnvelopeData() {
        let request = sourceCompileRequest("'hello'")
        XCTAssertEqual(request["contract_version"] as? String, "1.0.0")
        let input = request["input"] as? [String: Any]
        let document = input?["document"] as? [String: Any]
        XCTAssertEqual(document?["source_id"] as? String, "src:swift.adapter")
    }

    func testStdlibHelperRecordsIdentityWithoutSemantics() {
        let step = Essential.email("root")
        XCTAssertEqual(step["step_id"] as? String, "root")
        XCTAssertEqual(step["operation"] as? String, "stdlib_helper")
        let arguments = step["arguments"] as? [String: Any]
        XCTAssertEqual(arguments?["helper_id"] as? String, "stdlib.email")
    }

    func testStdlibHelpersConsumeCanonicalEssentialFixture() throws {
        let fixtureURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("../../spec/stdlib/essential_5.json")
            .standardizedFileURL
        let fixture = try XCTUnwrap(
            JSONSerialization.jsonObject(with: Data(contentsOf: fixtureURL)) as? [String: Any]
        )
        let patterns = try XCTUnwrap(fixture["patterns"] as? [String: Any])
        let steps = [
            Essential.dateTime("date-time"),
            Essential.email("email"),
            Essential.ip("ip"),
            Essential.url("url"),
            Essential.uuid("uuid"),
        ]
        XCTAssertEqual(patterns.count, steps.count)
        XCTAssertEqual(
            steps.compactMap { step in
                (step["arguments"] as? [String: Any])?["helper_id"] as? String
            },
            Essential.helperIDs
        )
    }

    func testRelativeNativePathFailsClosed() {
        XCTAssertThrowsError(try NativeClient(libraryPath: "relative/strling")) { error in
            XCTAssertEqual((error as? NativeAdapterError)?.kind, .load)
        }
    }

    func testNativeAdapterPreservesCanonicalOperationsAndLifecycle() throws {
        guard let configured = ProcessInfo.processInfo.environment["STRLING_NATIVE_LIBRARY"],
              !configured.isEmpty
        else {
            throw XCTSkip("STRLING_NATIVE_LIBRARY is required for governed integration execution")
        }
        let nativePath = URL(fileURLWithPath: configured).standardizedFileURL.path
        let client = try NativeClient(libraryPath: nativePath)
        let describe = try client.describe()
        var options = SourceOptions()
        options.sourceID = "src:adapter.parity"
        let compile = try client.compile(
            sourceCompileRequest("literal \"héllo\0世界\"", options: options)
        )
        let profileURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("../../spec/targets/profiles/pcre2-10.43.json")
            .standardizedFileURL
        let profileData = try Data(contentsOf: profileURL)
        let profile = try XCTUnwrap(
            JSONSerialization.jsonObject(with: profileData) as? [String: Any]
        )
        let inspected = try client.inspectTargetProfile(profile)
        var builder = simplyBuilderRequest([Essential.email("parity-root")], rootStepID: "parity-root")
        builder["identity_namespace"] = "adapter-parity"
        let simply = try client.simplyCompile(builder)

        let concurrentErrors = ThreadSafeErrors()
        DispatchQueue.concurrentPerform(iterations: 32) { _ in
            do {
                _ = try client.describe()
            } catch {
                concurrentErrors.append(error)
            }
        }
        XCTAssertTrue(
            concurrentErrors.isEmpty,
            "concurrent describe failed: \(concurrentErrors.snapshot)"
        )

        try writeEvidence([
            "describe": describe,
            "compile": compile,
            "target_profile": inspected,
            "simply": simply,
        ])
        client.close()
        client.close()
        XCTAssertThrowsError(try client.describe()) { error in
            XCTAssertEqual((error as? NativeAdapterError)?.kind, .closed)
        }
    }

    func testNativeReleaseProbeRequiresSameDescriptorFree() throws {
        let client = try loadProbe("STRLING_GDS_RELEASE_PROBE")
        defer { client.close() }
        XCTAssertNotNil(try client.describe())
        XCTAssertNotNil(try client.describe())
    }

    func testNativeABIMismatchFailsBeforeExecution() throws {
        guard let configured = ProcessInfo.processInfo.environment["STRLING_GDS_ABI_PROBE"],
              !configured.isEmpty
        else { throw XCTSkip("STRLING_GDS_ABI_PROBE is required for governed ABI execution") }
        XCTAssertThrowsError(
            try NativeClient(libraryPath: URL(fileURLWithPath: configured).standardizedFileURL.path)
        ) { error in
            XCTAssertEqual((error as? NativeAdapterError)?.kind, .abi)
            XCTAssertEqual((error as? NativeAdapterError)?.status, 2)
        }
    }

    func testNativeOversizedResponseFailsClosed() throws {
        let client = try loadProbe("STRLING_GDS_OVERSIZE_PROBE")
        defer { client.close() }
        XCTAssertThrowsError(try client.describe()) { error in
            XCTAssertEqual((error as? NativeAdapterError)?.kind, .transport)
        }
    }

    func testNativeDuplicateResponseFailsClosed() throws {
        try assertTransportProbe("STRLING_GDS_DUPLICATE_PROBE")
    }

    func testNativeInvalidUTF8ResponseFailsClosed() throws {
        try assertTransportProbe("STRLING_GDS_INVALID_UTF8_PROBE")
    }

    private func loadProbe(_ environmentName: String) throws -> NativeClient {
        guard let configured = ProcessInfo.processInfo.environment[environmentName],
              !configured.isEmpty
        else { throw XCTSkip("\(environmentName) is required for governed native execution") }
        return try NativeClient(
            libraryPath: URL(fileURLWithPath: configured).standardizedFileURL.path
        )
    }

    private func assertTransportProbe(_ environmentName: String) throws {
        let client = try loadProbe(environmentName)
        defer { client.close() }
        XCTAssertThrowsError(try client.describe()) { error in
            XCTAssertEqual((error as? NativeAdapterError)?.kind, .transport)
        }
    }

    private func writeEvidence(_ observations: [String: Any]) throws {
        guard let root = ProcessInfo.processInfo.environment["STRLING_GDS_EVIDENCE_DIR"],
              !root.isEmpty
        else { return }
        let directory = URL(fileURLWithPath: root).appendingPathComponent("swift")
        try FileManager.default.createDirectory(
            at: directory,
            withIntermediateDirectories: true
        )
        for (operation, observation) in observations {
            let data = try JSONSerialization.data(
                withJSONObject: observation,
                options: [.sortedKeys]
            )
            try data.write(to: directory.appendingPathComponent("\(operation).json"))
        }
    }
}

private final class ThreadSafeErrors: @unchecked Sendable {
    private let lock = NSLock()
    private var values: [Error] = []

    var isEmpty: Bool { snapshot.isEmpty }

    var snapshot: [Error] {
        lock.lock()
        defer { lock.unlock() }
        return values
    }

    func append(_ error: Error) {
        lock.lock()
        values.append(error)
        lock.unlock()
    }
}
