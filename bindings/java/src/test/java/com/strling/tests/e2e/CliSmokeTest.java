package com.strling.tests.e2e;

import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * @file CliSmokeTest.java
 *
 * High-level smoke tests for the `tooling/parse_strl.py` CLI.
 *
 * This suite treats the CLI as a black box: it invokes the Python script as a
 * subprocess and validates stdout, stderr, and exit codes for the core happy
 * paths and failure modes.
 *
 * Scenarios covered (mirroring the Python/JS tests):
 * <ul>
 * <li>File input with {@code --emit pcre2}</li>
 * <li>Stdin input with {@code --emit pcre2}</li>
 * <li>{@code --schema <base.schema.json>} success (silent, exit 0)</li>
 * <li>Parse error (exit 2, JSON error object with position)</li>
 * <li>Schema validation error (exit 3, JSON validation_error)</li>
 * <li>File not found (non-zero exit, message on stderr)</li>
 * </ul>
 */
public class CliSmokeTest {

    // --- Path setup (mirrors the JS/Python test layout) ---------------------

    /**
     * Helper to find the correct python executable, mirroring the JS logic.
     */
    private static String getPythonExec() {
        String exec = System.getenv("PYTHON_EXEC");
        if (exec != null && !exec.isBlank()) return exec;
        exec = System.getenv("PYTHON");
        if (exec != null && !exec.isBlank()) return exec;
        return "python3";
    }

    private static final String PYTHON_EXEC = getPythonExec();

    /**
     * Assumes tests are run from the bindings/java directory.
     * The project root is two levels up from user.dir.
     */
    private static final Path PROJECT_ROOT = Paths.get(System.getProperty("user.dir")).getParent().getParent();
    private static final Path CLI_PATH = PROJECT_ROOT.resolve(Path.of("tooling", "parse_strl.py"));
    private static final Path SPEC_DIR = PROJECT_ROOT.resolve(Path.of("spec", "schema"));
    private static final Path BASE_SCHEMA_PATH = SPEC_DIR.resolve("base.schema.json");
    private static final String PYTHON_PATH_ENV = PROJECT_ROOT
            .resolve(Path.of("bindings", "python", "src"))
            .toAbsolutePath()
            .toString();

    /**
     * Injected by JUnit 5. This directory is created before all tests
     * and automatically cleaned up afterward.
     */
    @TempDir
    static Path tempDir;

    // --- Helpers ------------------------------------------------------------

    /**
     * A simple data carrier for the CLI process result.
     * Equivalent to the `CliResult` interface in TypeScript.
     */
    private record CliResult(int code, String stdout, String stderr) {}

    /**
     * Runs the Python CLI script as a subprocess.
     * Equivalent to the `runCli` helper in TypeScript.
     *
     * @param args  A list of command-line arguments (e.g., "--emit", "pcre2").
     * @param stdin Optional string content to be piped into the process's stdin.
     * @return A {@link CliResult} record with the exit code, stdout, and stderr.
     */
    private CliResult runCli(List<String> args, String stdin) throws IOException, InterruptedException {
        List<String> command = new ArrayList<>();
        command.add(PYTHON_EXEC);
        command.add(CLI_PATH.toAbsolutePath().toString());
        command.addAll(args);

        ProcessBuilder pb = new ProcessBuilder(command);
        
        // Set PYTHONPATH environment variable so imports work
        Map<String, String> env = pb.environment();
        env.put("PYTHONPATH", PYTHON_PATH_ENV);

        Process process = pb.start();

        // Write to stdin if provided
        if (stdin != null) {
            try (OutputStreamWriter writer = new OutputStreamWriter(process.getOutputStream(), StandardCharsets.UTF_8)) {
                writer.write(stdin);
            } // try-with-resources automatically closes the stream, signaling EOF
        }

        // Wait for the process to exit
        int exitCode = process.waitFor();

        // Read stdout and stderr
        String stdout = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        String stderr = new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8);

        return new CliResult(exitCode, stdout, stderr);
    }

    /**
     * Helper to write a temporary .strl file.
     * Mirrors the `writeTempFile` helper in TypeScript.
     *
     * @param name    The name of the file to create (e.g., "test.strl").
     * @param content The string content to write to the file.
     * @return The {@link Path} to the newly created file.
     */
    private Path writeTempFile(String name, String content) throws IOException {
        Path filePath = tempDir.resolve(name);
        Files.writeString(filePath, content, StandardCharsets.UTF_8);
        return filePath;
    }

    // --- Test Suite ---------------------------------------------------------

    @Nested
    class CategoryAHappyPath {
        /**
         * Covers successful CLI invocation and output generation.
         */

        @Test
        void fileInputWithEmissionProducesJsonAndExitCode0() throws IOException, InterruptedException {
            /**
             * Tests that the CLI can parse a file and emit a valid JSON object
             * to stdout.
             * Equivalent to: test_file_input_with_emission (Python)
             * Equivalent to: "file input with emission produces JSON and exit code 0" (JS)
             */
            Path filePath = writeTempFile("valid_file_input.strl", "a(?<b>c)");

            CliResult result = runCli(
                    List.of("--emit", "pcre2", filePath.toAbsolutePath().toString()),
                    null
            );

            assertEquals(0, result.code(), "Exit code should be 0");
            assertTrue(result.stderr().isEmpty(), "Stderr should be empty");

            // Basic JSON structure validation
            assertTrue(result.stdout().contains("\"artifact\":"), "Stdout should contain 'artifact' key");
            assertTrue(result.stdout().contains("\"emitted\":"), "Stdout should contain 'emitted' key");
            assertTrue(result.stdout().contains("\"emitted\": \"a(?<b>c)\""), "Stdout should contain correct emitted value");
        }

        @Test
        void stdinInputWithEmissionProducesJsonAndExitCode0() throws IOException, InterruptedException {
            /**
             * Tests that the CLI can parse from stdin and emit a valid JSON object.
             * Equivalent to: test_stdin_input_with_emission (Python)
             * Equivalent to: "stdin input with emission produces JSON and exit code 0" (JS)
             */
            String inputContent = "a(?<b>c)";

            CliResult result = runCli(List.of("--emit", "pcre2", "-"), inputContent);

            assertEquals(0, result.code(), "Exit code should be 0");
            assertTrue(result.stderr().isEmpty(), "Stderr should be empty");

            // Basic JSON structure validation
            assertTrue(result.stdout().contains("\"artifact\":"), "Stdout should contain 'artifact' key");
            assertTrue(result.stdout().contains("\"emitted\":"), "Stdout should contain 'emitted' key");
        }
    }

    @Nested
    class CategoryBFeatureFlags {
        /**
         * Covers behavior of specific CLI flags like --schema.
         */

        @Test
        void successfulSchemaValidationIsSilentWithExitCode0() throws IOException, InterruptedException {
            /**
             * Tests that a successful schema validation produces exit code 0 and no
             * output, per the script's logic.
             * Equivalent to: test_successful_schema_validation_is_silent (Python)
             * Equivalent to: "successful schema validation is silent with exit code 0" (JS)
             */
            Path filePath = writeTempFile("valid_schema_input.strl", "a(?<b>c)");

            CliResult result = runCli(
                    List.of("--schema", BASE_SCHEMA_PATH.toAbsolutePath().toString(), filePath.toAbsolutePath().toString()),
                    null
            );

            assertEquals(0, result.code(), "Exit code should be 0");
            assertTrue(result.stdout().isEmpty(), "Stdout should be empty");
            assertTrue(result.stderr().isEmpty(), "Stderr should be empty");
        }
    }

    @Nested
    class CategoryCErrorHandling {
        /**
         * Covers specific failure modes and their corresponding exit codes.
         */

        @Test
        void parseErrorExitsWithCode2AndReturnsJsonErrorWithPosition() throws IOException, InterruptedException {
            /**
             * Tests that a file with a syntax error results in exit code 2 and a
             * JSON error object.
             * Equivalent to: test_parse_error_exits_with_code_2 (Python)
             * Equivalent to: "parse error exits with code 2 and returns JSON error with position" (JS)
             */
            Path filePath = writeTempFile("invalid_parse_error.strl", "a(b"); // Unterminated group

            CliResult result = runCli(List.of(filePath.toAbsolutePath().toString()), null);

            assertEquals(2, result.code(), "Exit code should be 2 for parse errors");
            assertTrue(result.stderr().isEmpty(), "Errors should be reported to stdout as JSON");

            // Check for JSON error structure
            assertTrue(result.stdout().contains("\"error\":"), "Stdout should contain 'error' key");
            assertTrue(result.stdout().contains("\"message\":"), "Stdout should contain 'message' key");
            
            // Regex to robustly check for "pos": 3 (allowing for whitespace and newlines)
            assertTrue(
                result.stdout().matches("(?s).*\"pos\"\\s*:\\s*3.*"), 
                "Stdout should contain '\"pos\": 3'"
            );
        }

        @Test
        void schemaValidationErrorExitsWithCode3AndReturnsValidationError() throws IOException, InterruptedException {
            /**
             * Tests that a schema validation failure results in exit code 3 and a
             * JSON error object.
             * Equivalent to: test_schema_validation_error_exits_with_code_3 (Python)
             * Equivalent to: "schema validation error exits with code 3 and returns validation_error" (JS)
             */
            Path filePath = writeTempFile("valid_for_invalid_schema.strl", "a(?<b>c)");

            // Create a deliberately broken schema
            String invalidSchemaContent = """
              {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                  "root": false
                }
              }
            """;
            Path invalidSchemaPath = writeTempFile("invalid.schema.json", invalidSchemaContent);

            CliResult result = runCli(
                    List.of("--schema", invalidSchemaPath.toAbsolutePath().toString(), filePath.toAbsolutePath().toString()),
                    null
            );

            assertEquals(3, result.code(), "Exit code should be 3 for schema validation errors");
            assertTrue(result.stderr().isEmpty(), "Errors should be reported to stdout as JSON");

            // Check for validation error structure
            assertTrue(result.stdout().contains("\"validation_error\":"), "Stdout should contain 'validation_error' key");
        }

        @Test
        void fileNotFoundExitsWithNonZeroCodeAndWritesErrorToStderr() throws IOException, InterruptedException {
            /**
             * Tests that a non-existent input file results in a non-zero exit code
             * and an error message on stderr.
             * Equivalent to: test_file_not_found_exits_with_code_1 (Python)
             * Equivalent to: "file not found exits with non-zero code and writes error to stderr" (JS)
             */
            Path missingPath = tempDir.resolve("non_existent_file.strl");
            // We do not create the file, so it is guaranteed to be missing

            CliResult result = runCli(List.of(missingPath.toAbsolutePath().toString()), null);

            assertNotEquals(0, result.code(), "Exit code should be non-zero");
            assertTrue(result.stdout().isEmpty(), "Stdout should be empty");
            
            // Check for the Python FileNotFoundError message
            assertTrue(result.stderr().contains("No such file or directory"), "Stderr should contain file not found message");
        }
    }
}
