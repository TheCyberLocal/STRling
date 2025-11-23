#!/usr/bin/env python3
"""
STRling Language Server - Real-Time Diagnostics via LSP

This module implements a Language Server Protocol (LSP) server for STRling,
providing real-time diagnostics and error feedback in code editors (VS Code, etc.).

The server is **binding-agnostic**, communicating with the STRling parser through
a standardized CLI/JSON contract. This architecture ensures compatibility with
future implementations (e.g., Rust core) and maintains separation of concerns.

Architecture:
    - LSP Server (this file) ← handles LSP protocol
    - CLI Server (cli_server.py) ← provides JSON diagnostics
    - Parser (parser.py) ← core parsing logic

Usage:
    python server.py [--tcp]
    python server.py --stdio (default)
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
import os

from lsprotocol import types as lsp
from pygls.server import JsonRPCServer
from pygls.protocol import LanguageServerProtocol, default_converter


# Define the server with proper protocol
class STRlingLanguageServer(JsonRPCServer):
    """STRling Language Server using JsonRPCServer."""

    def __init__(self):
        self.name = "strling-lsp"
        self.version = "v1.0.0"
        super().__init__(
            protocol_cls=LanguageServerProtocol, converter_factory=default_converter
        )


# Initialize the language server
server = STRlingLanguageServer()


def get_diagnostics_from_cli(content: str) -> List[lsp.Diagnostic]:
    """
    Get diagnostics from the STRling CLI server.

    This function communicates with the CLI server via subprocess,
    maintaining binding-agnostic architecture.

    Parameters
    ----------
    content : str
        The STRling pattern content to analyze

    Returns
    -------
    List[Diagnostic]
        List of LSP Diagnostic objects
    """
    try:
        # Find the Python module path
        # In production, this would be installed as a package
        # Ensure the subprocess can import the STRling package in-tree by
        # adding the Python binding source dir to PYTHONPATH. This is required
        # when tests run using system Python without a project-installed package.
        env = os.environ.copy()
        repo_root = Path(__file__).resolve().parents[2]
        python_src = str(repo_root / "bindings" / "python" / "src")
        prev = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = python_src + (os.pathsep + prev if prev else "")

        result = subprocess.run(
            [sys.executable, "-m", "STRling.cli_server", "--diagnostics-stdin"],
            input=content,
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )

        # Parse JSON output
        response = json.loads(result.stdout)

        # Convert JSON diagnostics to LSP Diagnostic objects
        diagnostics = []
        for diag in response.get("diagnostics", []):
            range_data = diag.get("range", {})
            start = range_data.get("start", {"line": 0, "character": 0})
            end = range_data.get("end", {"line": 0, "character": 1})

            diagnostic = lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(
                        line=start["line"], character=start["character"]
                    ),
                    end=lsp.Position(line=end["line"], character=end["character"]),
                ),
                message=diag.get("message", "Unknown error"),
                severity=lsp.DiagnosticSeverity(diag.get("severity", 1)),
                source=diag.get("source", "STRling"),
                code=diag.get("code"),
            )
            diagnostics.append(diagnostic)

        return diagnostics

    except subprocess.TimeoutExpired:
        return [
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
                message="Diagnostic timeout - pattern analysis took too long",
                severity=lsp.DiagnosticSeverity.Error,
                source="STRling",
                code="timeout",
            )
        ]
    except Exception as e:
        server.show_message_log(f"Error getting diagnostics: {str(e)}")
        return [
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
                message=f"Internal error: {str(e)}",
                severity=lsp.DiagnosticSeverity.Error,
                source="STRling",
                code="internal_error",
            )
        ]


def validate_document(ls: STRlingLanguageServer, uri: str):
    """
    Validate a STRling document and publish diagnostics.

    Parameters
    ----------
    ls : STRlingLanguageServer
        The language server instance
    uri : str
        The document URI to validate
    """
    try:
        doc = ls.workspace.get_text_document(uri)
        content = doc.source

        # Get diagnostics from CLI server
        diagnostics = get_diagnostics_from_cli(content)

        # Publish diagnostics to the client
        ls.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
        )

    except Exception as e:
        ls.show_message_log(f"Error validating document: {str(e)}")


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: STRlingLanguageServer, params: lsp.DidOpenTextDocumentParams):
    """Handle document open event."""
    ls.show_message_log(f"Document opened: {params.text_document.uri}")
    validate_document(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: STRlingLanguageServer, params: lsp.DidChangeTextDocumentParams):
    """Handle document change event."""
    validate_document(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: STRlingLanguageServer, params: lsp.DidSaveTextDocumentParams):
    """Handle document save event."""
    validate_document(ls, params.text_document.uri)


@server.feature(lsp.INITIALIZE)
def initialize(ls: STRlingLanguageServer, params: lsp.InitializeParams):
    """Handle initialization request."""
    ls.show_message_log("STRling Language Server initialized")


def main():
    """Main entry point for the language server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="STRling Language Server Protocol Implementation"
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        default=False,
        help="Use stdio for communication",
    )
    parser.add_argument("--tcp", action="store_true", help="Use TCP for communication")
    parser.add_argument(
        "--host", default="127.0.0.1", help="TCP host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=2087, help="TCP port (default: 2087)"
    )

    args = parser.parse_args()

    # Default to stdio if neither --stdio nor --tcp is specified
    if not args.tcp and not args.stdio:
        args.stdio = True

    if args.tcp:
        server.start_tcp(args.host, args.port)
    else:
        server.start_io()


if __name__ == "__main__":
    main()
