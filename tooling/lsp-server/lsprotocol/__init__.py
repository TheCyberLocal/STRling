"""Minimal local stub for the `lsprotocol` types used in tests.

This lightweight implementation provides just enough classes and constants
for the tooling/lsp-server tests and local server module to import and use.
It is intentionally simple and not a full implementation of the real
`lsprotocol` package.
"""

from .types import (
    Diagnostic,
    Range,
    Position,
    DiagnosticSeverity,
    PublishDiagnosticsParams,
    DidOpenTextDocumentParams,
    DidChangeTextDocumentParams,
    DidSaveTextDocumentParams,
    InitializeParams,
)

__all__ = [
    "Diagnostic",
    "Range",
    "Position",
    "DiagnosticSeverity",
    "PublishDiagnosticsParams",
    "DidOpenTextDocumentParams",
    "DidChangeTextDocumentParams",
    "DidSaveTextDocumentParams",
    "InitializeParams",
]
