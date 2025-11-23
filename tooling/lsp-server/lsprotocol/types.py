from dataclasses import dataclass
from typing import List, Optional, Any


@dataclass
class Position:
    line: int = 0
    character: int = 0


@dataclass
class Range:
    start: Position
    end: Position


class DiagnosticSeverity(int):
    Error = 1
    Warning = 2
    Information = 3
    Hint = 4

    def __new__(cls, value: int = 1):
        return int.__new__(cls, value)


@dataclass
class Diagnostic:
    range: Range
    message: str
    severity: Optional[int] = DiagnosticSeverity.Error
    source: Optional[str] = None
    code: Optional[Any] = None


@dataclass
class PublishDiagnosticsParams:
    uri: str
    diagnostics: List[Diagnostic]


@dataclass
class DidOpenTextDocumentParams:
    text_document: Any


@dataclass
class DidChangeTextDocumentParams:
    text_document: Any


@dataclass
class DidSaveTextDocumentParams:
    text_document: Any


@dataclass
class InitializeParams:
    pass


# LSP-like event constants used by the server module (simple placeholders)
TEXT_DOCUMENT_DID_OPEN = "textDocument/didOpen"
TEXT_DOCUMENT_DID_CHANGE = "textDocument/didChange"
TEXT_DOCUMENT_DID_SAVE = "textDocument/didSave"
INITIALIZE = "initialize"
