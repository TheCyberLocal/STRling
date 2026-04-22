"""Minimal LSP types used by the bundled STRling language server.

This is not a full copy of the upstream ``lsprotocol`` package. It only carries
the dataclasses, enums, and constants required by STRling's extension runtime.
"""

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
    code: Optional[Union[str, int]] = None
    data: Optional[dict] = None


@dataclass
class PublishDiagnosticsParams:
    uri: str
    diagnostics: List[Diagnostic]


@dataclass
class TextDocument:
    uri: str
    text: Optional[str] = None
    language_id: Optional[str] = None


@dataclass
class DidOpenTextDocumentParams:
    text_document: TextDocument


@dataclass
class DidChangeTextDocumentParams:
    text_document: TextDocument


@dataclass
class DidSaveTextDocumentParams:
    text_document: TextDocument


@dataclass
class InitializeParams:
    pass


class MarkupKind(str):
    PlainText = "plaintext"
    Markdown = "markdown"


@dataclass
class MarkupContent:
    kind: str
    value: str


@dataclass
class Hover:
    contents: Union[MarkupContent, str]
    range: Optional[Range] = None


@dataclass
class HoverParams:
    text_document: TextDocument
    position: Position


TEXT_DOCUMENT_DID_OPEN = "textDocument/didOpen"
TEXT_DOCUMENT_DID_CHANGE = "textDocument/didChange"
TEXT_DOCUMENT_DID_SAVE = "textDocument/didSave"
TEXT_DOCUMENT_HOVER = "textDocument/hover"
TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL = "textDocument/semanticTokens/full"
TEXT_DOCUMENT_COMPLETION = "textDocument/completion"
TEXT_DOCUMENT_CODE_ACTION = "textDocument/codeAction"
TEXT_DOCUMENT_DOCUMENT_SYMBOL = "textDocument/documentSymbol"
TEXT_DOCUMENT_DEFINITION = "textDocument/definition"
TEXT_DOCUMENT_FORMATTING = "textDocument/formatting"
INITIALIZE = "initialize"


class SymbolKind(IntEnum):
    File = 1
    Module = 2
    Namespace = 3
    Package = 4
    Class = 5
    Method = 6
    Property = 7
    Field = 8
    Constructor = 9
    Enum = 10
    Interface = 11
    Function = 12
    Variable = 13
    Constant = 14
    String = 15
    Number = 16
    Boolean = 17
    Array = 18
    Object = 19
    Key = 20
    Null = 21
    EnumMember = 22
    Struct = 23
    Event = 24
    Operator = 25
    TypeParameter = 26


@dataclass
class DocumentSymbol:
    name: str
    kind: SymbolKind
    range: Range
    selection_range: Range
    detail: Optional[str] = None
    children: Optional[List["DocumentSymbol"]] = None


@dataclass
class DocumentSymbolParams:
    text_document: TextDocument


@dataclass
class Location:
    uri: str
    range: Range


@dataclass
class DefinitionParams:
    text_document: TextDocument
    position: Position


@dataclass
class FormattingOptions:
    tab_size: int = 4
    insert_spaces: bool = True


@dataclass
class DocumentFormattingParams:
    text_document: TextDocument
    options: FormattingOptions


class CodeActionKind(str):
    QuickFix = "quickfix"
    Refactor = "refactor"
    RefactorRewrite = "refactor.rewrite"
    Source = "source"


@dataclass
class TextEdit:
    range: Range
    new_text: str


@dataclass
class WorkspaceEdit:
    changes: dict


@dataclass
class CodeActionContext:
    diagnostics: List[Diagnostic]
    only: Optional[List[str]] = None
    trigger_kind: Optional[int] = None


@dataclass
class CodeActionParams:
    text_document: TextDocument
    range: Range
    context: CodeActionContext


@dataclass
class CodeAction:
    title: str
    kind: Optional[str] = None
    diagnostics: Optional[List[Diagnostic]] = None
    edit: Optional[WorkspaceEdit] = None
    is_preferred: Optional[bool] = None


@dataclass
class CodeActionOptions:
    code_action_kinds: Optional[List[str]] = None
    resolve_provider: bool = False


class CompletionItemKind(IntEnum):
    Text = 1
    Method = 2
    Function = 3
    Constructor = 4
    Field = 5
    Variable = 6
    Class = 7
    Interface = 8
    Module = 9
    Property = 10
    Snippet = 15


class InsertTextFormat(IntEnum):
    PlainText = 1
    Snippet = 2


@dataclass
class CompletionItem:
    label: str
    kind: Optional[CompletionItemKind] = None
    detail: Optional[str] = None
    documentation: Optional[Union[str, MarkupContent]] = None
    insert_text: Optional[str] = None
    insert_text_format: Optional[InsertTextFormat] = None
    filter_text: Optional[str] = None
    sort_text: Optional[str] = None
    data: Optional[dict] = None


@dataclass
class CompletionList:
    is_incomplete: bool
    items: List[CompletionItem]


@dataclass
class CompletionContext:
    trigger_kind: int = 1
    trigger_character: Optional[str] = None


@dataclass
class CompletionParams:
    text_document: TextDocument
    position: Position
    context: Optional[CompletionContext] = None


@dataclass
class CompletionOptions:
    trigger_characters: Optional[List[str]] = None
    resolve_provider: bool = False


@dataclass
class SemanticTokensLegend:
    token_types: List[str]
    token_modifiers: List[str]


@dataclass
class SemanticTokens:
    data: List[int]


@dataclass
class SemanticTokensParams:
    text_document: TextDocument
