import XCTest
@testable import STRling

/// Emitter Edges Conformance — Swift bridge.
///
/// Drives the global pathological-AST fixture
/// `tests/conformance/inputs/emitter_edges/pathological.json` through
/// the Swift `PCRE2Emitter` and asserts each safety guard fires:
///   1. Variable-Length Lookbehind Rejection — `STRlingCompilationError`
///   2. AST Depth Limit Exceeded             — `STRlingCompilationError`
///   3. ReDoS Risk Warning (`(a+)+`)         — non-fatal `STRlingWarning`
///
/// The local `astToNode` adapter mirrors the TypeScript bridge so the
/// test targets the emitter without coupling to the parser/compiler
/// stages. Keep it minimal — supporting only node types currently
/// appearing in `pathological.json` — so adapter omissions cannot mask
/// emitter bugs by silently dropping nodes.
final class EmitterEdgesConformanceTests: XCTestCase {

    /// Locate the workspace root by climbing from this source file until
    /// `toolchain.json` is found.
    private func fixturePath() -> URL {
        var dir = URL(fileURLWithPath: #file).deletingLastPathComponent()
        for _ in 0..<12 {
            let marker = dir.appendingPathComponent("toolchain.json")
            if FileManager.default.fileExists(atPath: marker.path) {
                return dir
                    .appendingPathComponent("tests")
                    .appendingPathComponent("conformance")
                    .appendingPathComponent("inputs")
                    .appendingPathComponent("emitter_edges")
                    .appendingPathComponent("pathological.json")
            }
            dir = dir.deletingLastPathComponent()
        }
        fatalError("Could not locate workspace root from \(#file)")
    }

    /// User-facing AST -> AST Node adapter. Extend only as new node
    /// types appear in `pathological.json`.
    private func astToNode(_ obj: [String: Any]) -> Node {
        let type = obj["type"] as? String ?? ""
        switch type {
        case "Literal":
            return .lit(Lit(value: obj["value"] as? String ?? ""))
        case "Group":
            let inner = obj["content"] as? [String: Any] ?? [:]
            return .group(Group(capturing: false, body: astToNode(inner)))
        case "Quantifier":
            let inner = obj["content"] as? [String: Any] ?? [:]
            let minV = obj["min"] as? Int ?? 0
            let maxQ: QuantMax
            if let raw = obj["max"], !(raw is NSNull) {
                if let n = raw as? Int {
                    maxQ = .count(n)
                } else {
                    maxQ = .inf
                }
            } else {
                // null / missing in the user-facing AST means unbounded.
                maxQ = .inf
            }
            let mode = obj["mode"] as? String ?? "Greedy"
            return .quant(Quant(child: astToNode(inner), min: minV, max: maxQ, mode: mode))
        case "Lookbehind":
            let inner = obj["content"] as? [String: Any] ?? [:]
            return .look(Look(dir: "Behind", neg: false, body: astToNode(inner)))
        case "NegativeLookbehind":
            let inner = obj["content"] as? [String: Any] ?? [:]
            return .look(Look(dir: "Behind", neg: true, body: astToNode(inner)))
        case "Lookahead":
            let inner = obj["content"] as? [String: Any] ?? [:]
            return .look(Look(dir: "Ahead", neg: false, body: astToNode(inner)))
        case "NegativeLookahead":
            let inner = obj["content"] as? [String: Any] ?? [:]
            return .look(Look(dir: "Ahead", neg: true, body: astToNode(inner)))
        default:
            fatalError("astToNode: unsupported pathological AST node type \"\(type)\". Extend the adapter when new pathological vectors are added.")
        }
    }

    private func expectedSubstring(_ prefixed: String) -> String {
        if prefixed.hasPrefix("STRlingCompilationError:") {
            return String(prefixed.dropFirst("STRlingCompilationError:".count))
                .trimmingCharacters(in: .whitespaces)
        }
        if prefixed.hasPrefix("STRlingWarning"),
           let idx = prefixed.firstIndex(of: "]") {
            return String(prefixed[prefixed.index(after: idx)...])
                .trimmingCharacters(in: CharacterSet(charactersIn: ": "))
        }
        return prefixed
    }

    func testPathologicalCases() throws {
        let url = fixturePath()
        let raw = try Data(contentsOf: url)
        let json = try JSONSerialization.jsonObject(with: raw) as? [String: Any]
        let cases = (json?["tests"] as? [[String: Any]]) ?? []
        XCTAssertFalse(cases.isEmpty, "fixture is empty: \(url.path)")
        let emitter = PCRE2Emitter()
        for tc in cases {
            let name = tc["name"] as? String ?? "<unnamed>"
            let astMap = tc["ast"] as? [String: Any] ?? [:]
            let node = astToNode(astMap)
            let maxDepth = tc["depth_override_for_test"] as? Int ?? 0

            if let ee = tc["expected_error"] as? String {
                let needle = expectedSubstring(ee)
                do {
                    _ = try emitter.emitWithDiagnostics(node: node, maxDepth: maxDepth)
                    XCTFail("[\(name)] expected STRlingCompilationError, got success")
                } catch let err as STRlingCompilationError {
                    XCTAssertTrue(err.message.contains(needle),
                                  "[\(name)] error missing \"\(needle)\": \(err.message)")
                } catch {
                    XCTFail("[\(name)] expected STRlingCompilationError, got \(error)")
                }
            } else if let ew = tc["expected_warning"] as? String {
                let needle = expectedSubstring(ew)
                let result = try emitter.emitWithDiagnostics(node: node, maxDepth: maxDepth)
                // Warnings must NOT abort emission — the pattern is still produced.
                XCTAssertFalse(result.pattern.isEmpty,
                               "[\(name)] expected non-empty pattern when only a warning fires")
                XCTAssertTrue(
                    result.warnings.contains(where: { $0.code == "REDOS_RISK" && $0.message.contains(needle) }),
                    "[\(name)] missing REDOS_RISK warning containing \"\(needle)\"; got \(result.warnings)"
                )
            } else {
                XCTFail("[\(name)] declares neither expected_error nor expected_warning")
            }
        }
    }

    // --- Negative controls -------------------------------------------------

    func testNonPathologicalEmitsNoWarnings() throws {
        let result = try PCRE2Emitter().emitWithDiagnostics(node: .lit(Lit(value: "abc")))
        XCTAssertEqual(result.pattern, "abc")
        XCTAssertTrue(result.warnings.isEmpty)
    }

    func testDepthCapDoesNotFireUnderLimit() throws {
        let inner = Node.group(Group(capturing: false, body: .lit(Lit(value: "ok"))))
        let outer = Node.group(Group(capturing: false, body: inner))
        let result = try PCRE2Emitter().emitWithDiagnostics(node: outer, maxDepth: 5)
        XCTAssertTrue(result.warnings.isEmpty)
        XCTAssertTrue(result.pattern.contains("ok"))
    }
}
