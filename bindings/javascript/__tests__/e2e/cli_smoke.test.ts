/**
 * @file Test Design — cli_smoke.test.ts
 *
 * ## Purpose
 * This test suite provides a high-level "smoke test" for the
 * `tooling/parse_strl.py` command-line interface. Its goal is to verify that
 * the CLI application can be executed, that it correctly handles basic arguments
 * for input and emission, and that it produces the expected output and exit codes
 * for simple success and failure scenarios.
 *
 * ## Description
 * A smoke test is not exhaustive; it's a quick, broad check to ensure the core
 * functionality of an application is working and hasn't suffered a major
 * regression. This suite treats the CLI as a black box, invoking it as a
 * subprocess and inspecting its `stdout`, `stderr`, and exit code. It confirms
 * that the main features—parsing from a file, parsing from `stdin`, emitting to a
 * target format, and validating against a schema—are all wired up and functional.
 *
 * ## Scope
 * -   **In scope:**
 * -   Invoking the `tooling/parse_strl.py` script as an external process.
 * -   Testing file-based input and `stdin` input (`-`).
 * -   Testing the `--emit pcre2` option.
 * -   Testing the `--schema <path>` argument for both successful and failed
 * validation.
 * -   Verifying `stdout`, `stderr`, and specific process exit codes for success
 * (0) and different failure modes (1, 2, 3).
 * -   **Out of scope:**
 * -   Exhaustive validation of the compiler's output for all DSL features
 * (this is covered by other E2E and unit tests).
 * -   Unit testing the internal logic of the `parse_strl.py` script itself.
 * -   Testing performance or complex shell interactions.
 */

import { execSync, StdioOptions } from "child_process";
import path from "path";
import fs from "fs";

// --- Test Suite Setup -----------------------------------------------------------

// Define robust paths relative to this test file
const TEST_DIR = __dirname;
const PROJECT_ROOT = path.join(TEST_DIR, "../../../..");
const CLI_PATH = path.join(PROJECT_ROOT, "tooling/parse_strl.py");
const SPEC_DIR = path.join(PROJECT_ROOT, "spec/schema");
const BASE_SCHEMA_PATH = path.join(SPEC_DIR, "base.schema.json");

const PYTHON_EXEC = process.platform === "win32" ? "python" : "python3";
const TEMP_DIR = path.join(TEST_DIR, "temp");

// Fixture setup: create a temp directory for test files before all tests
beforeAll(() => {
    if (!fs.existsSync(TEMP_DIR)) {
        fs.mkdirSync(TEMP_DIR);
    }
});

// Fixture teardown: remove the temp directory after all tests
afterAll(() => {
    fs.rmSync(TEMP_DIR, { recursive: true, force: true });
});

// --- Test Suite -----------------------------------------------------------------

describe("Category A: Happy Path", () => {
    /**
     * Covers successful CLI invocation and output generation.
     *
     */

    test("should handle file input with emission", () => {
        /**
         * Tests that the CLI can parse a file and emit a valid JSON object
         * to stdout.
         */
        const validStr = "a(?<b>c)";
        const filePath = path.join(TEMP_DIR, "valid.strl");
        fs.writeFileSync(filePath, validStr);

        const command = `${PYTHON_EXEC} "${CLI_PATH}" --emit pcre2 "${filePath}"`;
        const stdout = execSync(command, { encoding: "utf-8" });

        const output = JSON.parse(stdout);
        expect(output).toHaveProperty("artifact");
        expect(output).toHaveProperty("emitted");
        expect(output.emitted).toBe("a(?<b>c)");
    });

    test("should handle stdin input with emission", () => {
        /**
         * Tests that the CLI can parse from stdin and emit a valid JSON object.
         *
         */
        const inputContent = "a(?<b>c)";
        const command = `${PYTHON_EXEC} "${CLI_PATH}" --emit pcre2 -`;
        const stdout = execSync(command, {
            input: inputContent,
            encoding: "utf-8",
        });

        const output = JSON.parse(stdout);
        expect(output).toHaveProperty("artifact");
        expect(output).toHaveProperty("emitted");
    });
});

describe("Category B: Feature Flags", () => {
    /**
     * Covers behavior of specific CLI flags like --schema.
     *
     */

    test("should be silent on successful schema validation", () => {
        /**
         * Tests that a successful schema validation produces exit code 0 and no
         * output, per the script's logic.
         */
        const validStr = "a(?<b>c)";
        const filePath = path.join(TEMP_DIR, "valid_for_schema.strl");
        fs.writeFileSync(filePath, validStr);

        const command = `${PYTHON_EXEC} "${CLI_PATH}" --schema "${BASE_SCHEMA_PATH}" "${filePath}"`;
        const stdout = execSync(command, { encoding: "utf-8" });

        expect(stdout).toBe("");
    });
});

describe("Category C: Error Handling", () => {
    /**
     * Covers specific failure modes and their corresponding exit codes.
     *
     */

    test("should exit with code 2 on parse error", () => {
        /**
         * Tests that a file with a syntax error results in exit code 2 and a
         * JSON error object.
         */
        const invalidStr = "a(b"; // Unterminated group
        const filePath = path.join(TEMP_DIR, "invalid.strl");
        fs.writeFileSync(filePath, invalidStr);
        const command = `${PYTHON_EXEC} "${CLI_PATH}" "${filePath}"`;

        try {
            execSync(command, {
                encoding: "utf-8",
                stdio: "pipe" as StdioOptions,
            });
            fail("Process should have exited with a non-zero code.");
        } catch (error: any) {
            expect(error.status).toBe(2);
            const output = JSON.parse(error.stdout);
            expect(output).toHaveProperty("error");
            expect(output.error).toHaveProperty(
                "message",
                "Unterminated group"
            );
            expect(output.error.pos).toBe(3);
        }
    });

    test("should exit with code 3 on schema validation error", () => {
        /**
         * Tests that a schema validation failure results in exit code 3 and a
         * JSON error object.
         */
        const validStr = "a";
        const filePath = path.join(TEMP_DIR, "valid_for_bad_schema.strl");
        fs.writeFileSync(filePath, validStr);

        const invalidSchema = {
            $schema: "https://json-schema.org/draft/2020-12/schema",
            properties: { root: false }, // This will fail validation
        };
        const invalidSchemaPath = path.join(TEMP_DIR, "invalid.schema.json");
        fs.writeFileSync(invalidSchemaPath, JSON.stringify(invalidSchema));

        const command = `${PYTHON_EXEC} "${CLI_PATH}" --schema "${invalidSchemaPath}" "${filePath}"`;

        try {
            execSync(command, {
                encoding: "utf-8",
                stdio: "pipe" as StdioOptions,
            });
            fail("Process should have exited with a non-zero code.");
        } catch (error: any) {
            expect(error.status).toBe(3);
            const output = JSON.parse(error.stdout);
            expect(output).toHaveProperty("validation_error");
        }
    });

    test("should exit with non-zero code for a file not found", () => {
        /**
         * Tests that a non-existent input file results in a non-zero exit code
         * and an error message on stderr.
         */
        const command = `${PYTHON_EXEC} "${CLI_PATH}" "non_existent_file.strl"`;

        try {
            execSync(command, {
                encoding: "utf-8",
                stdio: "pipe" as StdioOptions,
            });
            fail("Process should have exited with a non-zero code.");
        } catch (error: any) {
            expect(error.status).not.toBe(0); // Typically 1 for FileNotFoundError
            expect(error.stdout).toBe("");
            expect(error.stderr).toContain("No such file or directory");
        }
    });
});
