# Test Design — `e2e/test_cli_smoke.md`

## Purpose

This test suite provides a high-level "smoke test" for the `tooling/parse_strl.py` command-line interface. Its goal is to verify that the CLI application can be executed, that it correctly handles basic arguments for input and emission, and that it produces the expected output and exit codes for simple success and failure scenarios.

## Description

A smoke test is not exhaustive; it's a quick, broad check to ensure the core functionality of an application is working and hasn't suffered a major regression. This suite treats the CLI as a black box, invoking it as a subprocess and inspecting its `stdout`, `stderr`, and exit code. It confirms that the main features—parsing from a file, parsing from `stdin`, emitting to a target format, and validating against a schema—are all wired up and functional.

## Scope

-   **In scope:**

    -   Invoking the `tooling/parse_strl.py` script as an external process.
    -   Testing file-based input and `stdin` input (`-`).
    -   Testing the `--emit pcre2` option.
    -   Testing the `--schema <path>` argument for both successful and failed validation.
    -   Verifying `stdout`, `stderr`, and specific process exit codes for success (0) and different failure modes (1, 2, 3).

-   **Out of scope:**
    -   Exhaustive validation of the compiler's output for all DSL features (this is covered by other E2E and unit tests).
    -   Unit testing the internal logic of the `parse_strl.py` script itself.
    -   Testing performance or complex shell interactions.

## Categories of Tests

### Category A — Basic Invocation (Happy Path)

-   **File Input with Emission**:
    -   **Action**: Run `python3 tooling/parse_strl.py --emit pcre2 <test_pattern.strl>`.
    -   **Assert**: The process exits with code **0**. `stdout` contains a JSON object with `"artifact"` and `"emitted"` keys.
-   **Stdin Input with Emission**:
    -   **Action**: Run `cat <test_pattern.strl> | python3 tooling/parse_strl.py --emit pcre2 -`.
    -   **Assert**: The process exits with code **0**. `stdout` contains a JSON object with `"artifact"` and `"emitted"` keys.

### Category B — Feature Flag Tests

-   **Successful Schema Validation**:
    -   **Action**: Run `python3 tooling/parse_strl.py --schema spec/schema/base.schema.json <test_pattern.strl>`.
    -   **Assert**: The process exits with code **0** and produces **no output** on `stdout`.

### Category C — Error Handling

-   **Parse Error**:
    -   **Action**: Run the CLI with a syntactically incorrect STRling input file.
    -   **Assert**: The process exits with code **2**. `stdout` contains a JSON object with a top-level `"error"` key containing `"message"` and `"pos"` fields.
-   **Schema Validation Error**:
    -   **Action**: Run the CLI with the `--schema` flag pointing to a schema that the input pattern's artifact will fail to validate against.
    -   **Assert**: The process exits with code **3**. `stdout` contains a JSON object with a `"validation_error"` key.
-   **File Not Found Error**:
    -   **Action**: Run `python3 tooling/parse_strl.py non_existent_file.strl`.
    -   **Assert**: The process exits with a non-zero exit code (typically **1**). `stderr` contains an OS-level "File not found" error message.

### Category D — Cross-Semantics / Interaction

-   This category is not applicable for a CLI smoke test.

## Completion Criteria

-   [ ] The CLI is successfully tested with both file-based and `stdin` input using the `--emit` flag.
-   [ ] The `--schema` functionality is verified for a silent successful validation case.
-   [ ] The specific exit codes (**0, 1, 2, 3**) are asserted for success and all documented failure modes.
-   [ ] The JSON structure of the error output is verified for parse and validation errors.
-   [ ] All tests are performed by executing `parse_strl.py` as a subprocess.
