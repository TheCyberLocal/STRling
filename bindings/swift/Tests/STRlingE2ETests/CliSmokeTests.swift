/**
 * @file CliSmokeTests.swift
 *
 * High-level smoke tests for the `tooling/parse_strl.py` CLI.
 *
 * This suite treats the CLI as a black box: it invokes the Python script as a
 * subprocess and validates stdout, stderr, and exit codes for the core happy
 * paths and failure modes.
 *
 * Scenarios covered (mirroring the Python tests):
 * - File input with `--emit pcre2`
 * - Stdin input with `--emit pcre2`
 * - `--schema <base.schema.json>` success (silent, exit 0)
 * - Parse error (exit 2, JSON error object with position)
 * - Schema validation error (exit 3, JSON validation_error)
 * - File not found (non-zero exit, message on stderr)
 */

import XCTest
import Foundation

// --- Path setup (mirrors the Python test layout) ------------------------------
// NOTE: Assumes the test is run from the PROJECT_ROOT.

private let PYTHON_EXEC = ProcessInfo.processInfo.environment["PYTHON_EXEC"] ?? ProcessInfo.processInfo.environment["PYTHON"] ?? "python3"

// Get the project root assuming the test is run from the root directory.
private let PROJECT_ROOT_URL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
private let CLI_PATH = "tooling/parse_strl.py"
private let SPEC_DIR = "spec/schema"
private let BASE_SCHEMA_PATH = PROJECT_ROOT_URL.appendingPathComponent(SPEC_DIR).appendingPathComponent("base.schema.json").path
private let TEMP_DIR_URL = PROJECT_ROOT_URL.appendingPathComponent("tmp_cli_smoke_swift")

// --- Test Suite ---------------------------------------------------------------

class CliSmokeTests: XCTestCase {

    // --- Test Lifecycle (replaces beforeAll/afterAll) ---

    /**
     * Create a temp directory for our test files.
     * Replaces jest.beforeAll()
     */
    override class func setUp() {
        super.setUp()
        do {
            try FileManager.default.createDirectory(at: TEMP_DIR_URL, withIntermediateDirectories: true, attributes: nil)
        } catch {
            XCTFail("Failed to create temp directory at \(TEMP_DIR_URL.path): \(error)")
        }
    }

    /**
     * Clean up the temp directory.
     * Replaces jest.afterAll()
     */
    override class func tearDown() {
        do {
            if FileManager.default.fileExists(atPath: TEMP_DIR_URL.path) {
                try FileManager.default.removeItem(at: TEMP_DIR_URL)
            }
        } catch {
            // Non-fatal, just log it.
            print("Could not clean up temp directory: \(error)")
        }
        super.tearDown()
    }

    // --- Helpers (replaces internal functions) ---

    /**
     * A simple struct to hold the results of a subprocess execution.
     */
    struct CliResult {
        let code: Int32
        let stdout: String
        let stderr: String
    }

    /**
     * Runs the Python CLI script as a subprocess.
     * Replaces the TypeScript runCli function using Swift's `Process`.
     */
    func runCli(args: [String], stdinData: String? = nil) -> CliResult {
        let process = Process()
        
        // We use /usr/bin/env to find the python executable on the system PATH
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = [PYTHON_EXEC, CLI_PATH] + args
        
        // Set PYTHONPATH env variable so the script can find the `src` modules
        let pythonPath = PROJECT_ROOT_URL.appendingPathComponent("bindings/python/src").path
        process.environment = ["PYTHONPATH": pythonPath]

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        let stdinPipe = Pipe()

        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe
        process.standardInput = stdinPipe

        do {
            try process.run()
        } catch {
            XCTFail("Failed to launch process: \(error)")
            return CliResult(code: -1, stdout: "", stderr: error.localizedDescription)
        }

        // Write to stdin if data is provided
        if let stdinData = stdinData {
            let inputData = Data(stdinData.utf8)
            do {
                try stdinPipe.fileHandleForWriting.write(contentsOf: inputData)
            } catch {
                // Handle broken pipe, e.g., if process exited early
                print("Error writing to stdin: \(error)")
            }
        }
        // Close stdin to signal EOF
        try? stdinPipe.fileHandleForWriting.close()

        process.waitUntilExit()

        let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
        let stderrData = stderrPipe.fileHandleForReading.readDataToEndOfFile()

        let stdoutString = String(data: stdoutData, encoding: .utf8) ?? ""
        let stderrString = String(data: stderrData, encoding: .utf8) ?? ""

        return CliResult(
            code: process.terminationStatus,
            stdout: stdoutString.trimmingCharacters(in: .whitespacesAndNewlines),
            stderr: stderrString.trimmingCharacters(in: .whitespacesAndNewlines)
        )
    }

    /**
     * Helper to write a temporary .strl file.
     * Mirrors the TypeScript helper.
     */
    func writeTempFile(name: String, content: String) -> URL {
        let fileURL = TEMP_DIR_URL.appendingPathComponent(name)
        do {
            try content.write(to: fileURL, atomically: true, encoding: .utf8)
        } catch {
            XCTFail("Failed to write temp file \(name): \(error)")
        }
        return fileURL
    }
    
    /**
     * Helper to parse a JSON string and fail the test if invalid.
     */
    func assertJsonLoads(_ data: String) -> [String: Any]? {
        guard let jsonData = data.data(using: .utf8) else {
            XCTFail("Failed to convert stdout string to Data.")
            return nil
        }
        
        do {
            let json = try JSONSerialization.jsonObject(with: jsonData, options: [])
            guard let dict = json as? [String: Any] else {
                XCTFail("Parsed JSON was not a dictionary. Got: \(json)")
                return nil
            }
            return dict
        } catch {
            XCTFail("Failed to parse JSON: \(error). \nString was: \(data)")
            return nil
        }
    }


    // --- Test Cases (Category A: Happy Path) ---
    
    /**
     * Tests that the CLI can parse a file and emit a valid JSON object
     * to stdout.
     * Equivalent to: test_file_input_with_emission
     */
    func testFileInputWithEmissionProducesJSONAndExitCode0() {
        let fileURL = writeTempFile(name: "valid_file_input.strl", content: "a(?<b>c)")

        let result = runCli(args: ["--emit", "pcre2", fileURL.path])

        XCTAssertEqual(result.code, 0)
        XCTAssertEqual(result.stderr, "")

        guard let output = assertJsonLoads(result.stdout) else { return }
        XCTAssertNotNil(output["artifact"])
        XCTAssertNotNil(output["emitted"])
        XCTAssertEqual(output["emitted"] as? String, "a(?<b>c)")
    }

    /**
     * Tests that the CLI can parse from stdin and emit a valid JSON object.
     * Equivalent to: test_stdin_input_with_emission
     */
    func testStdinInputWithEmissionProducesJSONAndExitCode0() {
        let inputContent = "a(?<b>c)"
        let result = runCli(args: ["--emit", "pcre2", "-"], stdinData: inputContent)

        XCTAssertEqual(result.code, 0)
        XCTAssertEqual(result.stderr, "")

        guard let output = assertJsonLoads(result.stdout) else { return }
        XCTAssertNotNil(output["artifact"])
        XCTAssertNotNil(output["emitted"])
    }

    // --- Test Cases (Category B: Feature Flags) ---

    /**
     * Tests that a successful schema validation produces exit code 0 and no
     * output, per the script's logic.
     * Equivalent to: test_successful_schema_validation_is_silent
     */
    func testSuccessfulSchemaValidationIsSilentWithExitCode0() {
        let fileURL = writeTempFile(name: "valid_schema_input.strl", content: "a(?<b>c)")

        let result = runCli(args: ["--schema", BASE_SCHEMA_PATH, fileURL.path])

        XCTAssertEqual(result.code, 0)
        XCTAssertEqual(result.stdout, "")
        XCTAssertEqual(result.stderr, "")
    }

    // --- Test Cases (Category C: Error Handling) ---

    /**
     * Tests that a file with a syntax error results in exit code 2 and a
     * JSON error object.
     * Equivalent to: test_parse_error_exits_with_code_2
     */
    func testParseErrorExitsWithCode2AndReturnsJSONError() {
        let fileURL = writeTempFile(name: "invalid_parse_error.strl", content: "a(b") // Unterminated group

        let result = runCli(args: [fileURL.path])

        XCTAssertEqual(result.code, 2)
        XCTAssertEqual(result.stderr, "") // Errors are reported to stdout as JSON

        guard let output = assertJsonLoads(result.stdout) else { return }
        guard let error = output["error"] as? [String: Any] else {
            XCTFail("JSON output missing 'error' object")
            return
        }
        XCTAssertNotNil(error["message"])
        XCTAssertEqual(error["pos"] as? Int, 3)
    }

    /**
     * Tests that a schema validation failure results in exit code 3 and a
     * JSON error object.
     * Equivalent to: test_schema_validation_error_exits_with_code_3
     */
    func testSchemaValidationErrorExitsWithCode3() {
        let fileURL = writeTempFile(name: "valid_for_invalid_schema.strl", content: "a(?<b>c)")

        // Create a deliberately broken schema
        let invalidSchemaContent = """
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "root": false
            }
        }
        """
        let invalidSchemaURL = writeTempFile(name: "invalid.schema.json", content: invalidSchemaContent)

        let result = runCli(args: ["--schema", invalidSchemaURL.path, fileURL.path])

        XCTAssertEqual(result.code, 3)
        XCTAssertEqual(result.stderr, "") // Errors are reported to stdout as JSON

        guard let output = assertJsonLoads(result.stdout) else { return }
        XCTAssertNotNil(output["validation_error"])
    }

    /**
     * Tests that a non-existent input file results in a non-zero exit code
     * and an error message on stderr.
     * Equivalent to: test_file_not_found_exits_with_code_1
     */
    func testFileNotFoundExitsWithNonZeroCode() {
        let missingPath = TEMP_DIR_URL.appendingPathComponent("non_existent_file.strl").path

        let result = runCli(args: [missingPath])

        XCTAssertNotEqual(result.code, 0) // Exit code 1 (or 2 on Windows)
        XCTAssertEqual(result.stdout, "")
        
        // Check for the Python FileNotFoundError message
        XCTAssertTrue(result.stderr.contains("No such file or directory"), "stderr was: \(result.stderr)")
    }
}