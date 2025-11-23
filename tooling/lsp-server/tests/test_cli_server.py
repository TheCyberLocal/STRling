"""
Tests for the STRling CLI Server JSON Diagnostics Interface

This test suite validates the CLI server's ability to:
- Parse STRling patterns and detect errors
- Convert errors to LSP-compatible JSON format
- Handle file and stdin input modes
- Provide accurate position information
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_cli_diagnostics(content: str) -> dict:
    """
    Run the CLI server with the given content via stdin.

    Parameters
    ----------
    content : str
        The STRling pattern to diagnose

    Returns
    -------
    dict
        The JSON response from the CLI server
    """
    result = subprocess.run(
        [sys.executable, "-m", "STRling.cli_server", "--diagnostics-stdin"],
        input=content,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return json.loads(result.stdout)


class TestCLIDiagnostics:
    """Test the CLI diagnostics endpoint."""

    def test_valid_pattern_returns_success(self):
        """Test that a valid pattern returns success with no diagnostics."""
        result = run_cli_diagnostics("abc")

        assert result["success"] is True
        assert result["diagnostics"] == []
        assert result["version"] == "1.0.0"

    def test_invalid_pattern_returns_diagnostic(self):
        """Test that an invalid pattern returns a diagnostic."""
        result = run_cli_diagnostics("(abc")

        assert result["success"] is False
        assert len(result["diagnostics"]) == 1

        diag = result["diagnostics"][0]
        assert diag["severity"] == 1  # Error
        assert "Unterminated group" in diag["message"]
        assert diag["source"] == "STRling"
        assert diag["code"] == "unterminated_group"

    def test_diagnostic_position_accuracy(self):
        """Test that diagnostic positions are accurate."""
        result = run_cli_diagnostics("(abc")

        diag = result["diagnostics"][0]
        assert diag["range"]["start"]["line"] == 0
        assert diag["range"]["start"]["character"] == 4
        assert diag["range"]["end"]["line"] == 0
        assert diag["range"]["end"]["character"] == 5

    def test_diagnostic_includes_hint(self):
        """Test that diagnostics include helpful hints."""
        result = run_cli_diagnostics("(abc")

        diag = result["diagnostics"][0]
        assert "Hint:" in diag["message"]
        assert "Add a matching ')'" in diag["message"]

    def test_multiline_pattern_position(self):
        """Test position tracking in multiline patterns."""
        pattern = "abc\n(def"
        result = run_cli_diagnostics(pattern)

        diag = result["diagnostics"][0]
        # Error is on line 1 (second line), character 4
        assert diag["range"]["start"]["line"] == 1
        assert diag["range"]["start"]["character"] == 4

    def test_alternation_error(self):
        """Test alternation error handling."""
        result = run_cli_diagnostics("abc|")

        diag = result["diagnostics"][0]
        assert "Alternation" in diag["message"]
        assert diag["severity"] == 1

    def test_character_class_error(self):
        """Test character class error handling."""
        result = run_cli_diagnostics("[abc")

        diag = result["diagnostics"][0]
        assert "Unterminated character class" in diag["message"]

    def test_quantifier_error(self):
        """Test quantifier error handling."""
        result = run_cli_diagnostics("^*")

        diag = result["diagnostics"][0]
        assert "Cannot quantify anchor" in diag["message"]

    def test_escape_sequence_error(self):
        """Test escape sequence error handling."""
        result = run_cli_diagnostics(r"\z")

        diag = result["diagnostics"][0]
        assert "Unknown escape sequence" in diag["message"]


class TestCLIFileMode:
    """Test the CLI file mode."""

    def test_diagnose_file(self, tmp_path):
        """Test diagnosing a file."""
        test_file = tmp_path / "test.strl"
        test_file.write_text("(abc")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "STRling.cli_server",
                "--diagnostics",
                str(test_file),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        response = json.loads(result.stdout)
        assert response["success"] is False
        assert len(response["diagnostics"]) == 1

    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "STRling.cli_server",
                "--diagnostics",
                "/nonexistent/file.strl",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        response = json.loads(result.stdout)
        assert response["success"] is False
        assert "File not found" in response["diagnostics"][0]["message"]


class TestCLIVersionInfo:
    """Test CLI version information."""

    def test_version_flag(self):
        """Test the --version flag."""
        result = subprocess.run(
            [sys.executable, "-m", "STRling.cli_server", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        response = json.loads(result.stdout)
        assert "version" in response
        assert "name" in response
        assert response["name"] == "STRling CLI Server"


class TestDiagnosticFormat:
    """Test LSP diagnostic format compliance."""

    def test_diagnostic_has_required_fields(self):
        """Test that diagnostics have all required LSP fields."""
        result = run_cli_diagnostics("(abc")

        diag = result["diagnostics"][0]

        # Check required LSP Diagnostic fields
        assert "range" in diag
        assert "start" in diag["range"]
        assert "end" in diag["range"]
        assert "line" in diag["range"]["start"]
        assert "character" in diag["range"]["start"]
        assert "severity" in diag
        assert "message" in diag
        assert "source" in diag

    def test_severity_is_valid(self):
        """Test that severity is a valid LSP severity level."""
        result = run_cli_diagnostics("(abc")

        diag = result["diagnostics"][0]
        # LSP severity: 1=Error, 2=Warning, 3=Information, 4=Hint
        assert diag["severity"] in [1, 2, 3, 4]

    def test_error_code_format(self):
        """Test that error codes are properly formatted."""
        result = run_cli_diagnostics("(abc")

        diag = result["diagnostics"][0]
        code = diag["code"]

        # Error codes should be snake_case identifiers
        assert isinstance(code, str)
        assert code.islower() or "_" in code
        assert " " not in code
