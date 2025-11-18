/**
 * @file cli_smoke_test.c
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
 *
 * NOTE: This is a C translation of the cli_smoke.test.ts jest suite.
 * It uses cmocka for testing and jansson for JSON parsing.
 * It is POSIX-specific.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h> // For cmocka assertions

// Includes for testing framework
#include <cmocka.h> 

// Includes for JSON parsing
#include <jansson.h> 

// Includes for process and file management
#include <unistd.h>     // for pipe, fork, execvp, write, read, close
#include <sys/wait.h>   // for waitpid
#include <sys/stat.h>   // for mkdir
#include <fcntl.h>      // for fcntl, F_SETFL, O_NONBLOCK
#include <errno.h>

// --- Path setup (mirrors the Python test layout) ------------------------------
// NOTE: Assumes the test is run from the PROJECT_ROOT.
const char* PYTHON_EXEC = NULL; // Will be set from getenv
const char* PROJECT_ROOT = "."; // Assumed to be current working directory
const char* CLI_PATH = "tooling/parse_strl.py";
const char* SPEC_DIR = "spec/schema";
char BASE_SCHEMA_PATH[1024];
const char* TEMP_DIR = "tmp_cli_smoke";


// --- Helpers ------------------------------------------------------------------

typedef struct {
    int code;
    char* stdout_str;
    char* stderr_str;
} CliResult;

// Helper to free the CliResult
void free_cli_result(CliResult* result) {
    if (result) {
        free(result->stdout_str);
        free(result->stderr_str);
        free(result);
    }
}

/**
 * Reads all data from a file descriptor into a dynamically allocated string.
 * Returns NULL on failure. Caller must free the returned string.
 */
char* read_all_from_fd(int fd) {
    size_t capacity = 4096;
    size_t size = 0;
    char* buffer = (char*)malloc(capacity);
    if (!buffer) return NULL;

    // Set fd to non-blocking
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);

    ssize_t bytes_read;
    while (1) {
        if (size + 4096 > capacity) {
            capacity *= 2;
            char* new_buffer = (char*)realloc(buffer, capacity);
            if (!new_buffer) {
                free(buffer);
                return NULL;
            }
            buffer = new_buffer;
        }

        bytes_read = read(fd, buffer + size, 4095);
        if (bytes_read > 0) {
            size += bytes_read;
        } else if (bytes_read == 0) {
            // End of file
            break;
        } else {
            // No more data right now (EAGAIN/EWOULDBLOCK) or actual error
            if (errno != EAGAIN && errno != EWOULDBLOCK) {
                // Real error
                free(buffer);
                return NULL;
            }
            // If we got EAGAIN, but the process hasn't exited, we should wait.
            // But since we call this *after* waitpid, EOF should be the only exit.
            // For simplicity, we'll just break if we're not getting data.
            break; 
        }
    }
    
    buffer[size] = '\0'; // Null-terminate
    return buffer;
}


/**
 * Runs the Python CLI script as a subprocess.
 * Replaces the TypeScript runCli function.
 * This is a POSIX-specific implementation using fork/exec/pipe.
 */
CliResult* runCli(const char* args[], const char* stdin_data) {
    CliResult* result = (CliResult*)calloc(1, sizeof(CliResult));
    if (!result) return NULL;

    int stdout_pipe[2];
    int stderr_pipe[2];
    int stdin_pipe[2];

    if (pipe(stdout_pipe) == -1 || pipe(stderr_pipe) == -1 || pipe(stdin_pipe) == -1) {
        perror("pipe");
        free_cli_result(result);
        return NULL;
    }

    pid_t pid = fork();
    if (pid == -1) {
        perror("fork");
        free_cli_result(result);
        return NULL;
    }

    if (pid == 0) {
        // --- Child Process ---

        // Set PYTHONPATH env variable
        char python_path[2048];
        snprintf(python_path, sizeof(python_path), "%s/bindings/python/src", PROJECT_ROOT);
        setenv("PYTHONPATH", python_path, 1);
        
        // Redirect stdin
        close(stdin_pipe[1]);
        dup2(stdin_pipe[0], STDIN_FILENO);
        close(stdin_pipe[0]);

        // Redirect stdout
        close(stdout_pipe[0]);
        dup2(stdout_pipe[1], STDOUT_FILENO);
        close(stdout_pipe[1]);

        // Redirect stderr
        close(stderr_pipe[0]);
        dup2(stderr_pipe[1], STDERR_FILENO);
        close(stderr_pipe[1]);

        // Execute the command
        // Note: args[0] should be PYTHON_EXEC
        execvp(args[0], (char* const*)args);

        // If execvp returns, it failed
        perror("execvp");
        exit(127); 

    } else {
        // --- Parent Process ---
        close(stdin_pipe[0]);
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);

        // Write to child's stdin if data is provided
        if (stdin_data) {
            write(stdin_pipe[1], stdin_data, strlen(stdin_data));
        }
        close(stdin_pipe[1]); // Close stdin to signal EOF to child

        // Wait for child to exit
        int status;
        waitpid(pid, &status, 0);
        if (WIFEXITED(status)) {
            result->code = WEXITSTATUS(status);
        } else {
            result->code = -1; // Indicate non-exit (e.g., signal)
        }
        
        // Read stdout and stderr from pipes
        result->stdout_str = read_all_from_fd(stdout_pipe[0]);
        result->stderr_str = read_all_from_fd(stderr_pipe[0]);
        
        close(stdout_pipe[0]);
        close(stderr_pipe[0]);

        // Ensure strings are non-null even if read failed
        if (!result->stdout_str) result->stdout_str = strdup("");
        if (!result->stderr_str) result->stderr_str = strdup("");

        return result;
    }
}

/**
 * Helper to write a temporary .strl file.
 * Mirrors the pytest fixtures and TS helper.
 * Returns a heap-allocated path to the file. Caller must free.
 */
char* writeTempFile(const char* name, const char* content) {
    char file_path[2048];
    snprintf(file_path, sizeof(file_path), "%s/%s", TEMP_DIR, name);
    
    FILE* f = fopen(file_path, "w");
    if (!f) {
        perror("fopen");
        return NULL;
    }
    fprintf(f, "%s", content);
    fclose(f);

    return strdup(file_path);
}

// --- Global setup / teardown (for cmocka) -------------------------------------

/**
 * Create a temp directory for our test files.
 * Replaces jest.beforeAll()
 */
static int global_setup(void** state) {
    // Get Python executable
    PYTHON_EXEC = getenv("PYTHON_EXEC");
    if (!PYTHON_EXEC) PYTHON_EXEC = getenv("PYTHON");
    if (!PYTHON_EXEC) PYTHON_EXEC = "python3";
    
    // Build schema path
    snprintf(BASE_SCHEMA_PATH, sizeof(BASE_SCHEMA_PATH), "%s/%s/base.schema.json", PROJECT_ROOT, SPEC_DIR);
    
    // Create temp directory
    mkdir(TEMP_DIR, 0777); // 0777 permissions
    return 0;
}

/**
 * Clean up the temp directory.
 * Replaces jest.afterAll()
 */
static int global_teardown(void** state) {
    // Use system("rm -rf ...") as a direct equivalent to fs.rmSync(..., { recursive: true })
    char command[1024];
    snprintf(command, sizeof(command), "rm -rf %s", TEMP_DIR);
    system(command);
    return 0;
}

// --- Test Suite (Helper functions for assertions) ---------------------------

// Helper to parse JSON and fail test if invalid
json_t* assert_json_loads(const char* text) {
    json_error_t error;
    json_t* root = json_loads(text, 0, &error);
    if (!root) {
        fail_msg("Failed to parse JSON: %s (line %d, col %d)\nFull text: %s", 
                 error.text, error.line, error.column, text);
    }
    assert_non_null(root);
    return root;
}

// Helper to get a JSON object property and fail test if missing
json_t* assert_json_object_get(json_t* obj, const char* key) {
    json_t* value = json_object_get(obj, key);
    if (!value) {
        fail_msg("JSON object missing required key: '%s'", key);
    }
    assert_non_null(value);
    return value;
}


// --- Test Suite (Category A: Happy Path) ------------------------------------

/**
 * Covers successful CLI invocation and output generation.
 * (Corresponds to "describe('Category A: Happy Path', ...)")
 */

/**
 * Tests that the CLI can parse a file and emit a valid JSON object
 * to stdout.
 * Equivalent to: test_file_input_with_emission
 */
static void test_file_input_with_emission_produces_JSON_and_exit_code_0(void** state) {
    char* file_path = writeTempFile("valid_file_input.strl", "a(?<b>c)");
    assert_non_null(file_path);

    const char* args[] = { PYTHON_EXEC, CLI_PATH, "--emit", "pcre2", file_path, NULL };
    CliResult* result = runCli(args, NULL);
    
    assert_non_null(result);
    assert_int_equal(result->code, 0);
    assert_string_equal(result->stderr_str, "");

    // Parse stdout JSON
    json_t* root = assert_json_loads(result->stdout_str);
    json_t* artifact = assert_json_object_get(root, "artifact");
    json_t* emitted = assert_json_object_get(root, "emitted");
    
    assert_string_equal(json_string_value(emitted), "a(?<b>c)");

    // Cleanup
    json_decref(root);
    free_cli_result(result);
    free(file_path);
}

/**
 * Tests that the CLI can parse from stdin and emit a valid JSON object.
 * Equivalent to: test_stdin_input_with_emission
 */
static void test_stdin_input_with_emission_produces_JSON_and_exit_code_0(void** state) {
    const char* input_content = "a(?<b>c)";
    const char* args[] = { PYTHON_EXEC, CLI_PATH, "--emit", "pcre2", "-", NULL };
    
    CliResult* result = runCli(args, input_content);

    assert_non_null(result);
    assert_int_equal(result->code, 0);
    assert_string_equal(result->stderr_str, "");

    // Parse stdout JSON
    json_t* root = assert_json_loads(result->stdout_str);
    assert_json_object_get(root, "artifact");
    assert_json_object_get(root, "emitted");

    // Cleanup
    json_decref(root);
    free_cli_result(result);
}


// --- Test Suite (Category B: Feature Flags) ---------------------------------

/**
 * Covers behavior of specific CLI flags like --schema.
 * (Corresponds to "describe('Category B: Feature Flags', ...)")
 */

/**
 * Tests that a successful schema validation produces exit code 0 and no
 * output, per the script's logic.
 * Equivalent to: test_successful_schema_validation_is_silent
 */
static void test_successful_schema_validation_is_silent_with_exit_code_0(void** state) {
    char* file_path = writeTempFile("valid_schema_input.strl", "a(?<b>c)");
    assert_non_null(file_path);

    const char* args[] = { PYTHON_EXEC, CLI_PATH, "--schema", BASE_SCHEMA_PATH, file_path, NULL };
    CliResult* result = runCli(args, NULL);

    assert_non_null(result);
    assert_int_equal(result->code, 0);
    assert_string_equal(result->stdout_str, "");
    assert_string_equal(result->stderr_str, "");

    // Cleanup
    free_cli_result(result);
    free(file_path);
}


// --- Test Suite (Category C: Error Handling) --------------------------------

/**
 * Covers specific failure modes and their corresponding exit codes.
 * (Corresponds to "describe('Category C: Error Handling', ...)")
 */

/**
 * Tests that a file with a syntax error results in exit code 2 and a
 * JSON error object.
 * Equivalent to: test_parse_error_exits_with_code_2
 */
static void test_parse_error_exits_with_code_2_and_returns_JSON_error(void** state) {
    char* file_path = writeTempFile("invalid_parse_error.strl", "a(b"); // Unterminated group
    assert_non_null(file_path);

    const char* args[] = { PYTHON_EXEC, CLI_PATH, file_path, NULL };
    CliResult* result = runCli(args, NULL);

    assert_non_null(result);
    assert_int_equal(result->code, 2);
    assert_string_equal(result->stderr_str, ""); // Errors are reported to stdout as JSON

    // Parse stdout JSON
    json_t* root = assert_json_loads(result->stdout_str);
    json_t* error = assert_json_object_get(root, "error");
    assert_json_object_get(error, "message");
    json_t* pos = assert_json_object_get(error, "pos");
    
    assert_true(json_is_integer(pos));
    assert_int_equal(json_integer_value(pos), 3);

    // Cleanup
    json_decref(root);
    free_cli_result(result);
    free(file_path);
}

/**
 * Tests that a schema validation failure results in exit code 3 and a
 * JSON error object.
 * Equivalent to: test_schema_validation_error_exits_with_code_3
 */
static void test_schema_validation_error_exits_with_code_3(void** state) {
    char* file_path = writeTempFile("valid_for_invalid_schema.strl", "a(?<b>c)");
    assert_non_null(file_path);

    // Create a deliberately broken schema
    const char* invalid_schema_content = 
        "{"
        "  \"$schema\": \"https://json-schema.org/draft/2020-12/schema\","
        "  \"type\": \"object\","
        "  \"properties\": {"
        "    \"root\": false" // This will fail validation
        "  }"
        "}";
    char* invalid_schema_path = writeTempFile("invalid.schema.json", invalid_schema_content);
    assert_non_null(invalid_schema_path);

    const char* args[] = { PYTHON_EXEC, CLI_PATH, "--schema", invalid_schema_path, file_path, NULL };
    CliResult* result = runCli(args, NULL);

    assert_non_null(result);
    assert_int_equal(result->code, 3);
    assert_string_equal(result->stderr_str, ""); // Errors are reported to stdout as JSON

    // Parse stdout JSON
    json_t* root = assert_json_loads(result->stdout_str);
    assert_json_object_get(root, "validation_error");

    // Cleanup
    json_decref(root);
    free_cli_result(result);
    free(file_path);
    free(invalid_schema_path);
}

/**
 * Tests that a non-existent input file results in a non-zero exit code
 * and an error message on stderr.
 * Equivalent to: test_file_not_found_exits_with_code_1
 */
static void test_file_not_found_exits_with_non_zero_code(void** state) {
    char missing_path[2048];
    snprintf(missing_path, sizeof(missing_path), "%s/non_existent_file.strl", TEMP_DIR);

    const char* args[] = { PYTHON_EXEC, CLI_PATH, missing_path, NULL };
    CliResult* result = runCli(args, NULL);

    assert_non_null(result);
    assert_int_not_equal(result->code, 0); // Exit code 1 (or 2 on Windows)
    assert_string_equal(result->stdout_str, "");
    
    // Check for the Python FileNotFoundError message
    assert_non_null(strstr(result->stderr_str, "No such file or directory"));

    // Cleanup
    free_cli_result(result);
}


// --- Test Runner (main) -----------------------------------------------------

int main(void) {
    const struct CMUnitTest tests[] = {
        // Category A
        cmocka_unit_test(test_file_input_with_emission_produces_JSON_and_exit_code_0),
        cmocka_unit_test(test_stdin_input_with_emission_produces_JSON_and_exit_code_0),
        // Category B
        cmocka_unit_test(test_successful_schema_validation_is_silent_with_exit_code_0),
        // Category C
        cmocka_unit_test(test_parse_error_exits_with_code_2_and_returns_JSON_error),
        cmocka_unit_test(test_schema_validation_error_exits_with_code_3),
        cmocka_unit_test(test_file_not_found_exits_with_non_zero_code),
    };

    // Run the tests with global setup/teardown
    return cmocka_run_group_tests(tests, global_setup, global_teardown);
}
