/**
 * @file cli_smoke.test.ts
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

import { spawnSync, SpawnSyncOptions } from "child_process";
import fs from "fs";
import path from "path";

// --- Path setup (mirrors the Python test layout) ------------------------------

const PYTHON_EXEC = process.env.PYTHON_EXEC || process.env.PYTHON || "python3";

const TEST_DIR = __dirname;
// Assumes the test file is in a directory like build/tests/e2e
// Adjust relative path as needed if the directory structure is different.
// This path aims to find the project root from the test file's location.
const PROJECT_ROOT = path.resolve(TEST_DIR, "..", "..", "..", "..");
const CLI_PATH = path.join(PROJECT_ROOT, "tooling", "parse_strl.py");
const SPEC_DIR = path.join(PROJECT_ROOT, "spec", "schema");
const BASE_SCHEMA_PATH = path.join(SPEC_DIR, "base.schema.json");

const TEMP_DIR = path.join(TEST_DIR, "tmp_cli_smoke");

// --- Helpers ------------------------------------------------------------------

interface CliResult {
    code: number | null;
    stdout: string;
    stderr: string;
}

/**
 * Runs the Python CLI script as a subprocess.
 */
function runCli(args: string[], stdin?: string): CliResult {
    const pythonPath = path.join(PROJECT_ROOT, "bindings", "python", "src");
    const options: SpawnSyncOptions = {
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"], // [stdin, stdout, stderr]
        env: {
            ...process.env,
            PYTHONPATH: pythonPath,
        },
    };

    const result = spawnSync(PYTHON_EXEC!, [CLI_PATH, ...args], {
        ...options,
        input: stdin,
    });

    return {
        code: result.status,
        stdout: (result.stdout as string) ?? "",
        stderr: (result.stderr as string) ?? "",
    };
}

/**
 * Helper to write a temporary .strl file.
 * Mirrors the pytest fixtures.
 */
function writeTempFile(name: string, content: string): string {
    if (!fs.existsSync(TEMP_DIR)) {
        fs.mkdirSync(TEMP_DIR, { recursive: true });
    }
    const filePath = path.join(TEMP_DIR, name);
    fs.writeFileSync(filePath, content, { encoding: "utf-8" });
    return filePath;
}

// --- Global setup / teardown --------------------------------------------------

// Create a temp directory for our test files
beforeAll(() => {
    if (!fs.existsSync(TEMP_DIR)) {
        fs.mkdirSync(TEMP_DIR, { recursive: true });
    }
});

// Clean up the temp directory
afterAll(() => {
    if (fs.existsSync(TEMP_DIR)) {
        fs.rmSync(TEMP_DIR, { recursive: true, force: true });
    }
});

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Happy Path", () => {
    /**
     * Covers successful CLI invocation and output generation.
     */

    test("file input with emission produces JSON and exit code 0", () => {
        /**
         * Tests that the CLI can parse a file and emit a valid JSON object
         * to stdout.
         * Equivalent to: test_file_input_with_emission
         */
        const filePath = writeTempFile("valid_file_input.strl", "a(?<b>c)");

        const { code, stdout, stderr } = runCli(["--emit", "pcre2", filePath]);

        expect(code).toBe(0);
        expect(stderr).toBe("");

        const output = JSON.parse(stdout);
        expect(output).toHaveProperty("artifact");
        expect(output).toHaveProperty("emitted");
        expect(output.emitted).toBe("a(?<b>c)");
    });

    test("stdin input with emission produces JSON and exit code 0", () => {
        /**
         * Tests that the CLI can parse from stdin and emit a valid JSON object.
         * Equivalent to: test_stdin_input_with_emission
         */
        const inputContent = "a(?<b>c)";

        const { code, stdout, stderr } = runCli(
            ["--emit", "pcre2", "-"],
            inputContent
        );

        expect(code).toBe(0);
        expect(stderr).toBe("");

        const output = JSON.parse(stdout);
        expect(output).toHaveProperty("artifact");
        expect(output).toHaveProperty("emitted");
    });
});

describe("Category B: Feature Flags", () => {
    /**
     * Covers behavior of specific CLI flags like --schema.
     */

    test("successful schema validation is silent with exit code 0", () => {
        /**
         * Tests that a successful schema validation produces exit code 0 and no
         * output, per the script's logic.
         * Equivalent to: test_successful_schema_validation_is_silent
         */
        const filePath = writeTempFile("valid_schema_input.strl", "a(?<b>c)");

        const { code, stdout, stderr } = runCli([
            "--schema",
            BASE_SCHEMA_PATH,
            filePath,
        ]);

        expect(code).toBe(0);
        expect(stdout).toBe("");
        expect(stderr).toBe("");
    });
});

describe("Category C: Error Handling", () => {
    /**
     * Covers specific failure modes and their corresponding exit codes.
     */

    test("parse error exits with code 2 and returns JSON error with position", () => {
        /**
         * Tests that a file with a syntax error results in exit code 2 and a
         * JSON error object.
         * Equivalent to: test_parse_error_exits_with_code_2
         */
        const filePath = writeTempFile("invalid_parse_error.strl", "a(b"); // Unterminated group

        const { code, stdout, stderr } = runCli([filePath]);

        expect(code).toBe(2);
        expect(stderr).toBe(""); // Errors are reported to stdout as JSON

        const output = JSON.parse(stdout);
        expect(output).toHaveProperty("error");
        expect(output.error).toHaveProperty("message");
        expect(output.error.pos).toBe(3);
    });

    test("schema validation error exits with code 3 and returns validation_error", () => {
        /**
         * Tests that a schema validation failure results in exit code 3 and a
         * JSON error object.
         * Equivalent to: test_schema_validation_error_exits_with_code_3
         */
        const filePath = writeTempFile(
            "valid_for_invalid_schema.strl",
            "a(?<b>c)"
        );

        // Create a deliberately broken schema
        const invalidSchemaContent = {
            $schema: "https://json-schema.org/draft/2020-12/schema",
            type: "object",
            properties: {
                root: false, // This will fail validation
            },
        };
        const invalidSchemaPath = writeTempFile(
            "invalid.schema.json",
            JSON.stringify(invalidSchemaContent)
        );

        const { code, stdout, stderr } = runCli([
            "--schema",
            invalidSchemaPath,
            filePath,
        ]);

        expect(code).toBe(3);
        expect(stderr).toBe(""); // Errors are reported to stdout as JSON

        const output = JSON.parse(stdout);
        expect(output).toHaveProperty("validation_error");
    });

    test("file not found exits with non-zero code and writes error to stderr", () => {
        /**
         * Tests that a non-existent input file results in a non-zero exit code
         * and an error message on stderr.
         * Equivalent to: test_file_not_found_exits_with_code_1
         */
        const missingPath = path.join(TEMP_DIR, "non_existent_file.strl");

        const { code, stdout, stderr } = runCli([missingPath]);

        expect(code).not.toBe(0); // Exit code 1 (or 2 on Windows)
        expect(stdout).toBe("");
        // Check for the Python FileNotFoundError message
        expect(stderr).toContain("No such file or directory");
    });
});
