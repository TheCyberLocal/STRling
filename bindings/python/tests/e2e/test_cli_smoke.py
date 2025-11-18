"""
Test Design — e2e/test_cli_smoke.py

## Purpose
This test suite provides a high-level "smoke test" for the
`tooling/parse_strl.py` command-line interface. Its goal is to verify that
the CLI application can be executed, that it correctly handles basic arguments
for input and emission, and that it produces the expected output and exit codes
for simple success and failure scenarios.

## Description
A smoke test is not exhaustive; it's a quick, broad check to ensure the core
functionality of an application is working and hasn't suffered a major
regression. This suite treats the CLI as a black box, invoking it as a
subprocess and inspecting its `stdout`, `stderr`, and exit code. It confirms
that the main features—parsing from a file, parsing from `stdin`, emitting to a
target format, and validating against a schema—are all wired up and functional.

## Scope
-   **In scope:**
    -   Invoking the `tooling/parse_strl.py` script as an external process.
    -   Testing file-based input and `stdin` input (`-`).
    -   Testing the `--emit pcre2` option.
    -   Testing the `--schema <path>` argument for both successful and failed
        validation.
    -   Verifying `stdout`, `stderr`, and specific process exit codes for success
        (0) and different failure modes (1, 2, 3).
-   **Out of scope:**
    -   Exhaustive validation of the compiler's output for all DSL features
        (this is covered by other E2E and unit tests).
    -   Unit testing the internal logic of the `parse_strl.py` script itself.
    -   Testing performance or complex shell interactions.
"""

import pytest
import subprocess
import sys
import json
from pathlib import Path

# --- Test Suite Setup -----------------------------------------------------------

# Define robust paths relative to this test file
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent.parent.parent.parent
CLI_PATH = str(PROJECT_ROOT / "tooling" / "parse_strl.py")
SPEC_DIR = PROJECT_ROOT / "spec" / "schema"
BASE_SCHEMA_PATH = str(SPEC_DIR / "base.schema.json")


# Pytest fixture to create a temporary, valid .strl file
@pytest.fixture
def valid_strl_file(tmp_path: Path) -> Path:
    p = tmp_path / "valid.strl"
    p.write_text("a(?<b>c)")
    return p


# Pytest fixture to create a temporary, invalid .strl file
@pytest.fixture
def invalid_strl_file(tmp_path: Path) -> Path:
    p = tmp_path / "invalid.strl"
    p.write_text("a(b")  # Unterminated group
    return p


# --- Test Suite -----------------------------------------------------------------


class TestCategoryAHappyPath:
    """
    Covers successful CLI invocation and output generation.
    """

    def test_file_input_with_emission(self, valid_strl_file: Path):
        """
        Tests that the CLI can parse a file and emit a valid JSON object
        to stdout.
        """
        result = subprocess.run(
            [sys.executable, CLI_PATH, "--emit", "pcre2", str(valid_strl_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stderr == ""
        output = json.loads(result.stdout)
        assert "artifact" in output
        assert "emitted" in output
        assert output["emitted"] == "a(?<b>c)"

    def test_stdin_input_with_emission(self, valid_strl_file: Path):
        """
        Tests that the CLI can parse from stdin and emit a valid JSON object.
        """
        input_content = valid_strl_file.read_text()
        result = subprocess.run(
            [sys.executable, CLI_PATH, "--emit", "pcre2", "-"],
            input=input_content,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stderr == ""
        output = json.loads(result.stdout)
        assert "artifact" in output
        assert "emitted" in output


class TestCategoryBFeatureFlags:
    """
    Covers behavior of specific CLI flags like --schema.
    """

    def test_successful_schema_validation_is_silent(self, valid_strl_file: Path):
        """
        Tests that a successful schema validation produces exit code 0 and no
        output, per the script's logic.
        """
        result = subprocess.run(
            [
                sys.executable,
                CLI_PATH,
                "--schema",
                BASE_SCHEMA_PATH,
                str(valid_strl_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""


class TestCategoryCErrorHandling:
    """
    Covers specific failure modes and their corresponding exit codes.
    """

    def test_parse_error_exits_with_code_2(self, invalid_strl_file: Path):
        """
        Tests that a file with a syntax error results in exit code 2 and a
        JSON error object.
        """
        result = subprocess.run(
            [sys.executable, CLI_PATH, str(invalid_strl_file)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        output = json.loads(result.stdout)
        assert "error" in output
        assert "message" in output["error"]
        assert output["error"]["pos"] == 3

    def test_schema_validation_error_exits_with_code_3(
        self, valid_strl_file: Path, tmp_path: Path
    ):
        """
        Tests that a schema validation failure results in exit code 3 and a
        JSON error object.
        """
        # Create a deliberately broken schema
        from typing import Dict

        invalid_schema_content: Dict[str, object] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {"root": False},  # This will fail validation
        }
        invalid_schema_path = tmp_path / "invalid.schema.json"
        invalid_schema_path.write_text(json.dumps(invalid_schema_content))

        result = subprocess.run(
            [
                sys.executable,
                CLI_PATH,
                "--schema",
                str(invalid_schema_path),
                str(valid_strl_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 3
        output = json.loads(result.stdout)
        assert "validation_error" in output

    def test_file_not_found_exits_with_code_1(self):
        """
        Tests that a non-existent input file results in a non-zero exit code
        and an error message on stderr.
        """
        result = subprocess.run(
            [sys.executable, CLI_PATH, "non_existent_file.strl"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0  # Typically 1 for FileNotFoundError
        assert result.stdout == ""
        assert "No such file or directory" in result.stderr
