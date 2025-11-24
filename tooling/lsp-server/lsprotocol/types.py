from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, Union


@dataclass
class Position:
    line: int = 0
    character: int = 0


@dataclass
class Range:
    start: Position
    end: Position


class DiagnosticSeverity(IntEnum):
    Error = 1
    Warning = 2
    Information = 3
    Hint = 4


@dataclass
class Diagnostic:
    range: Range
    message: str
    severity: Optional[DiagnosticSeverity] = DiagnosticSeverity.Error
    source: Optional[str] = None
    # LSP allows string or numeric codes
    code: Optional[Union[str, int]] = None


@dataclass
class PublishDiagnosticsParams:
    uri: str
    diagnostics: List[Diagnostic]


@dataclass
class TextDocument:
    uri: str
    # some implementations include text/source; keep optional for stubs/tests
    text: Optional[str] = None
    language_id: Optional[str] = None


@dataclass
class DidOpenTextDocumentParams:
    text_document: TextDocument


@dataclass
@dataclass
class DidChangeTextDocumentParams:
    text_document: TextDocument


@dataclass
@dataclass
class DidSaveTextDocumentParams:
    text_document: TextDocument


@dataclass
class InitializeParams:
    pass


# LSP-like event constants used by the server module (simple placeholders)
TEXT_DOCUMENT_DID_OPEN = "textDocument/didOpen"
TEXT_DOCUMENT_DID_CHANGE = "textDocument/didChange"
TEXT_DOCUMENT_DID_SAVE = "textDocument/didSave"
INITIALIZE = "initialize"
