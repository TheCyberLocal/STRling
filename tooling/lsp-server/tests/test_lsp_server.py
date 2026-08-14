"""
Module Pedagogy:
These smoke tests pin the language server's boot path to the normalized
`tooling/lsp-server/server/` source package. They catch regressions where the
build or test harness accidentally falls back to the old flat layout before we
pay the cost of packaging a VSIX.
"""

import sys
import subprocess
from pathlib import Path


class TestLSPServerStartup:
    """Test basic LSP server startup and functionality."""

    def test_server_module_imports(self):
        """Test that the server module can be imported."""
        # This tests the imports without starting the server
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, '.'); from server.server import server",
            ],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, f"Import failed: {result.stderr}"

    def test_cli_integration(self):
        """Test that the server projects a canonical CLI diagnostic."""
        # Test the get_diagnostics_from_cli function
        test_code = """
import sys
sys.path.insert(0, ".")
from server.server import get_diagnostics_from_cli

diagnostics = get_diagnostics_from_cli("(abc")
print(len(diagnostics))
print(diagnostics[0].message if diagnostics else "No diagnostics")
"""

        result = subprocess.run(
            [sys.executable, "-c", test_code],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"CLI integration failed: {result.stderr}"
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 2
        assert lines[0] == "1"  # One diagnostic
        assert lines[1] == "group or lookaround is not closed"

    def test_server_help_message(self):
        """Test that the server prints help."""
        result = subprocess.run(
            [sys.executable, "server/server.py", "--help"],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0
        assert (
            "STRling Language Server" in result.stdout
            or "usage:" in result.stdout.lower()
        )
