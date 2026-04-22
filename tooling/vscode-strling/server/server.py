#!/usr/bin/env python3
"""
STRling Language Server - Real-Time Diagnostics via LSP

This module implements a Language Server Protocol (LSP) server for STRling,
providing real-time diagnostics and error feedback in code editors
(VS Code, etc.).

Architecture:
    - LSP Server (this file) ← handles LSP transport, debounce, and host
      coordinate projection.
    - Language Intelligence (``STRling.core.intelligence``) ← owns the
      parse-and-diagnose round-trip and the island-grammar registry. The
      previous out-of-process ``STRling.cli_server`` shadow has been
      removed; the server now imports the same intelligence surface that
      ``tooling/parse_strl.py`` consumes, so there is exactly one place
      where diagnostics are produced.

Usage:
    python server.py [--tcp]
    python server.py --stdio (default)
"""

import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from lsprotocol import types as lsp
from pygls.server import JsonRPCServer
from pygls.protocol import LanguageServerProtocol, default_converter

# Make the in-tree Python binding importable when running the LSP server
# directly out of a repository checkout. The extension package can live at a
# different depth than the sibling tooling workspace, so we walk upward until
# we find the checkout root that contains ``bindings/python/src``. Production
# installs that already have ``STRling`` on ``sys.path`` are unaffected.
_PYTHON_SRC = None
for _candidate in Path(__file__).resolve().parents:
    _maybe_python_src = _candidate / "bindings" / "python" / "src"
    if _maybe_python_src.is_dir():
        _PYTHON_SRC = _maybe_python_src
        break
if _PYTHON_SRC is not None and str(_PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(_PYTHON_SRC))

from STRling.core.intelligence import (  # noqa: E402  (intentional path mutation)
    Island,
    SEMANTIC_TOKEN_MODIFIERS,
    SEMANTIC_TOKEN_TYPES,
    analyze_content,
    emit_pcre2_for_pattern,
    extract_document_symbols,
    extract_islands_for_uri,
    find_registry_definition,
    format_pattern,
    get_completion_items,
    get_registry_documentation,
    language_for_uri,
    tokenize_pattern,
)


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
server: STRlingLanguageServer = STRlingLanguageServer()


def _diagnostic_from_dict(diag: Dict[str, Any]) -> lsp.Diagnostic:
    """Convert one intelligence-layer diagnostic dict to an LSP object.

    The intelligence layer returns plain JSON-serialisable dicts so the
    same shape can flow over a wire protocol or through an in-process
    call. The LSP transport requires concrete ``lsp.Diagnostic`` instances,
    so we adapt at this single boundary instead of leaking dict semantics
    into the rest of the server.
    """
    range_data = diag.get("range", {})
    start = range_data.get("start", {"line": 0, "character": 0})
    end = range_data.get("end", {"line": 0, "character": 1})
    return lsp.Diagnostic(
        range=lsp.Range(
            start=lsp.Position(line=start["line"], character=start["character"]),
            end=lsp.Position(line=end["line"], character=end["character"]),
        ),
        message=diag.get("message", "Unknown error"),
        severity=lsp.DiagnosticSeverity(int(diag.get("severity", 1))),
        source=diag.get("source", "STRling"),
        code=diag.get("code"),
        data=diag.get("data"),
    )


def get_diagnostics_for_pattern(content: str) -> List[lsp.Diagnostic]:
    """Run the unified intelligence layer over ``content`` and adapt the result.

    Calls ``STRling.core.intelligence.analyze_content`` in-process — there
    is no longer a subprocess hop — then converts the JSON-shaped
    diagnostics into ``lsp.Diagnostic`` objects ready for publishing.
    Unexpected exceptions surface as a single internal-error diagnostic
    so the editor never sees a raw traceback.
    """
    try:
        response = analyze_content(content)
    except Exception as e:  # pragma: no cover - defensive guard
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
    return [_diagnostic_from_dict(d) for d in response.get("diagnostics", [])]


# Backwards-compatible alias — some legacy tests import this symbol by name
# even though the underlying transport no longer uses a CLI subprocess.
get_diagnostics_from_cli = get_diagnostics_for_pattern


# --------------------------------------------------------------------------- #
# Island Grammar Bridge                                                       #
# --------------------------------------------------------------------------- #
#
# Host languages (TypeScript/Python/Rust/Java) embed STRling patterns inside
# string-literal arguments to boundary calls such as ``s.parse("...")``. The
# bridge extracts those literals into Virtual Documents, runs the unified
# intelligence layer on each, and then *projects* the diagnostics back onto
# the host file's coordinate system so editors render the squigglies in the
# right place. See ``STRling.core.islands`` for the projection algebra.
#
# Per-URI cache of the most recent island layout — used by hover routing
# without re-scanning the source.
_ISLANDS_BY_URI: Dict[str, List[Island]] = {}

# Per-URI cache of the last published diagnostics. The code-action handler
# consults this cache when the LSP client does not forward the diagnostics
# in ``CodeActionContext`` (older clients, custom hosts) so the lightbulb
# still resolves to the correct quick-fix.
_LAST_DIAGNOSTICS: Dict[str, List["lsp.Diagnostic"]] = {}

# Debounce table: ``uri -> Timer``. Rapid keystrokes only trigger one
# diagnostic pass per quiet window (50 ms by default — tuned to feel
# instantaneous on rapid keystrokes).
_DEBOUNCE_TIMERS: Dict[str, threading.Timer] = {}
_DEBOUNCE_INTERVAL_S: float = 0.05
_DEBOUNCE_LOCK: threading.Lock = threading.Lock()


def _project_diagnostic(diag: lsp.Diagnostic, island: Island) -> lsp.Diagnostic:
    """Translate a virtual-document diagnostic onto host coordinates."""
    start = island.to_host(diag.range.start.line, diag.range.start.character)
    end = island.to_host(diag.range.end.line, diag.range.end.character)
    return lsp.Diagnostic(
        range=lsp.Range(
            start=lsp.Position(line=start.line, character=start.character),
            end=lsp.Position(line=end.line, character=end.character),
        ),
        message=diag.message,
        severity=diag.severity,
        source=diag.source,
        code=diag.code,
        data=diag.data,
    )


def _diagnostics_for_host(uri: str, source: str) -> List[lsp.Diagnostic]:
    """Run the island extractor and return projected diagnostics."""
    islands = extract_islands_for_uri(source, uri)
    _ISLANDS_BY_URI[uri] = islands
    projected: List[lsp.Diagnostic] = []
    for island in islands:
        for diag in get_diagnostics_for_pattern(island.virtual_content):
            projected.append(_project_diagnostic(diag, island))
    return projected


def validate_document(ls: STRlingLanguageServer, uri: str) -> None:
    """
    Validate a document and publish diagnostics.

    For native ``.strl`` files the entire buffer is treated as a STRling
    pattern. For host-language files (``.ts``, ``.py``, ``.rs``, ``.java``)
    the Island Grammar bridge extracts embedded literals before delegating
    to the unified intelligence layer.
    """
    try:
        doc = ls.workspace.get_text_document(uri)
        content = doc.source

        if language_for_uri(uri) is not None:
            diagnostics = _diagnostics_for_host(uri, content)
        else:
            diagnostics = get_diagnostics_for_pattern(content)

        _LAST_DIAGNOSTICS[uri] = diagnostics
        ls.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
        )

    except Exception as e:
        ls.show_message_log(f"Error validating document: {str(e)}")


def _schedule_validation(ls: STRlingLanguageServer, uri: str) -> None:
    """Debounced wrapper around :func:`validate_document`.

    Rapid keystrokes coalesce into a single validation pass once the user
    pauses for ``_DEBOUNCE_INTERVAL_S`` seconds. This keeps the editor
    responsive while typing inside large host files with many islands.
    """
    with _DEBOUNCE_LOCK:
        existing = _DEBOUNCE_TIMERS.pop(uri, None)
        if existing is not None:
            existing.cancel()

        timer = threading.Timer(_DEBOUNCE_INTERVAL_S, validate_document, args=(ls, uri))
        timer.daemon = True
        _DEBOUNCE_TIMERS[uri] = timer
        timer.start()


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: STRlingLanguageServer, params: lsp.DidOpenTextDocumentParams) -> None:
    """Handle document open event."""
    ls.show_message_log(f"Document opened: {params.text_document.uri}")
    # Validate immediately on open so initial diagnostics appear without
    # waiting for the debounce window.
    validate_document(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(
    ls: STRlingLanguageServer, params: lsp.DidChangeTextDocumentParams
) -> None:
    """Handle document change event."""
    _schedule_validation(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: STRlingLanguageServer, params: lsp.DidSaveTextDocumentParams) -> None:
    """Handle document save event."""
    validate_document(ls, params.text_document.uri)


def _word_at(text: str, character: int) -> Optional[str]:
    """Return the identifier under ``character`` in a single line of text."""
    if not text or character < 0 or character > len(text):
        return None
    if character == len(text):
        character -= 1
    if not (text[character].isalnum() or text[character] == "_"):
        return None
    start = character
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
        start -= 1
    end = character
    while end < len(text) and (text[end].isalnum() or text[end] == "_"):
        end += 1
    return text[start:end]


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls: STRlingLanguageServer, params: lsp.HoverParams) -> Optional[lsp.Hover]:
    """Provide hover documentation for STRling stdlib patterns inside islands.

    Routes the host-coordinate cursor through the island coordinate mirror,
    extracts the identifier under the cursor inside the *virtual* document,
    and returns the matching documentation entry from the central registry.
    When no registry entry matches but the surrounding pattern compiles
    cleanly, the hover falls back to a Markdown snippet showing what the
    pattern compiles to in PCRE2.
    """
    uri = params.text_document.uri
    islands = _ISLANDS_BY_URI.get(uri)
    if not islands:
        return None

    line = params.position.line
    character = params.position.character
    for island in islands:
        mapped = island.from_host(line, character)
        if mapped is None:
            continue
        vd_line, vd_char = mapped
        lines = island.virtual_content.split("\n")
        word: Optional[str] = None
        if vd_line < len(lines):
            word = _word_at(lines[vd_line], vd_char)
        if word is not None:
            doc = get_registry_documentation(word)
            if doc is not None:
                return lsp.Hover(
                    contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=doc)
                )
        preview = _compile_preview_markdown(island.virtual_content)
        if preview is not None:
            return lsp.Hover(
                contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=preview)
            )
        return None
    return None


def _compile_preview_markdown(pattern: str) -> Optional[str]:
    """Render a Markdown hover card showing ``pattern`` compiled to PCRE2.

    Returns ``None`` if compilation fails — the hover handler then falls
    back silently rather than surfacing a confusing tooltip.
    """
    if not pattern.strip():
        return None
    result = emit_pcre2_for_pattern(pattern)
    if not result.get("success") or not result.get("emitted"):
        return None
    emitted = str(result["emitted"])
    return (
        "**STRling \u2192 PCRE2**\n\n"
        f"```regex\n{emitted}\n```\n\n"
        "_Compiled live by the STRling language server._"
    )


# --------------------------------------------------------------------------- #
# Semantic Tokens                                                             #
# --------------------------------------------------------------------------- #
#
# We register a single ``textDocument/semanticTokens/full`` provider. For
# native ``.strl`` files we tokenise the entire buffer; for host-language
# files we tokenise each Island and *project* its absolute (line, col)
# spans onto host coordinates before delta-encoding. The resulting stream
# colours STRling syntax independently of the host language's own string
# colouring (DoD #2).

_SEMANTIC_TOKENS_LEGEND = lsp.SemanticTokensLegend(
    token_types=list(SEMANTIC_TOKEN_TYPES),
    token_modifiers=list(SEMANTIC_TOKEN_MODIFIERS),
)


def _delta_encode_tokens(
    tokens: List[tuple],
) -> List[int]:
    """Convert absolute-position tokens into the LSP delta-encoded array.

    The LSP wire format is a flat ``int[]`` of 5-tuples
    ``(deltaLine, deltaStartChar, length, tokenType, tokenModifier)``.
    Tokens must be sorted by (line, character) before encoding.
    """
    sorted_tokens = sorted(tokens, key=lambda t: (t[0], t[1]))
    out: List[int] = []
    prev_line = 0
    prev_char = 0
    for line, char, length, token_type, modifier in sorted_tokens:
        delta_line = line - prev_line
        delta_char = char - prev_char if delta_line == 0 else char
        out.extend([delta_line, delta_char, length, token_type, modifier])
        prev_line = line
        prev_char = char
    return out


def _tokens_for_host(uri: str, source: str) -> List[tuple]:
    """Run the island extractor and return projected absolute tokens."""
    islands = extract_islands_for_uri(source, uri)
    _ISLANDS_BY_URI[uri] = islands
    projected: List[tuple] = []
    for island in islands:
        for line, char, length, token_type, modifier in tokenize_pattern(
            island.virtual_content
        ):
            host = island.to_host(line, char)
            projected.append((host.line, host.character, length, token_type, modifier))
    return projected


@server.feature(
    lsp.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    _SEMANTIC_TOKENS_LEGEND,
)
def semantic_tokens_full(
    ls: STRlingLanguageServer, params: lsp.SemanticTokensParams
) -> lsp.SemanticTokens:
    """Return delta-encoded semantic tokens for the whole document.

    Native ``.strl`` files are tokenised end-to-end; host-language files
    contribute one token stream per Island, projected back to host
    coordinates so STRling colouring lives *inside* the host string
    literals without disturbing the host LSP's own highlighting.
    """
    uri = params.text_document.uri
    try:
        doc = ls.workspace.get_text_document(uri)
        source = doc.source
    except Exception:
        return lsp.SemanticTokens(data=[])

    if language_for_uri(uri) is not None:
        absolute = _tokens_for_host(uri, source)
    else:
        absolute = [
            (line, char, length, ttype, mod)
            for (line, char, length, ttype, mod) in tokenize_pattern(source)
        ]
    return lsp.SemanticTokens(data=_delta_encode_tokens(absolute))


# --------------------------------------------------------------------------- #
# Completion                                                                  #
# --------------------------------------------------------------------------- #
#
# When the user is editing inside a STRling island and types a member-access
# trigger (``.``), the registry is queried for every known stdlib pattern and
# the items are returned as an LSP ``CompletionList``. The trigger character
# is registered alongside the feature so VS Code only invokes the handler at
# the right moments instead of polling on every keystroke.

_COMPLETION_OPTIONS = lsp.CompletionOptions(
    trigger_characters=["."],
    resolve_provider=False,
)


def _completion_item_from_dict(item: Dict[str, Any]) -> lsp.CompletionItem:
    """Adapt the registry-shaped dict into an ``lsp.CompletionItem``."""
    documentation = item.get("documentation")
    if isinstance(documentation, dict):
        documentation = lsp.MarkupContent(
            kind=lsp.MarkupKind.Markdown,
            value=str(documentation.get("value", "")),
        )
    kind_value = item.get("kind", lsp.CompletionItemKind.Function)
    try:
        kind = lsp.CompletionItemKind(int(kind_value))
    except (ValueError, TypeError):
        kind = lsp.CompletionItemKind.Function
    return lsp.CompletionItem(
        label=str(item.get("label", "")),
        kind=kind,
        detail=item.get("detail"),
        documentation=documentation,
        insert_text=item.get("insertText", item.get("label", "")),
        insert_text_format=lsp.InsertTextFormat.PlainText,
        filter_text=item.get("filterText"),
        data=item.get("data"),
    )


def _cursor_inside_island(uri: str, line: int, character: int) -> bool:
    """Return True when the cursor sits inside any cached island for ``uri``.

    Native ``.strl`` files have no host wrapper, so the entire document is
    treated as an island for completion purposes.
    """
    if language_for_uri(uri) is None:
        return True
    for island in _ISLANDS_BY_URI.get(uri, []):
        if island.contains_host(line, character):
            return True
    return False


@server.feature(lsp.TEXT_DOCUMENT_COMPLETION, _COMPLETION_OPTIONS)
def completion(
    ls: STRlingLanguageServer, params: lsp.CompletionParams
) -> lsp.CompletionList:
    """Return registry-backed completion items inside STRling islands.

    The handler stays silent when the cursor is not inside an island so
    the host language server (Pylance, TS Server, etc.) keeps owning
    completion for ordinary host code.
    """
    uri = params.text_document.uri
    if not _cursor_inside_island(uri, params.position.line, params.position.character):
        return lsp.CompletionList(is_incomplete=False, items=[])

    items = [_completion_item_from_dict(d) for d in get_completion_items()]
    return lsp.CompletionList(is_incomplete=False, items=items)


# --------------------------------------------------------------------------- #
# Code actions: REDOS_RISK quick-fixes                                        #
# --------------------------------------------------------------------------- #
#
# When the parser flags a nested unbounded quantifier (the canonical
# ``(a+)+`` shape), the diagnostic carries a ``data.replacements`` payload
# enumerating safe rewrites. The handler turns each replacement into a
# ``CodeAction`` whose ``WorkspaceEdit`` targets the same host range that
# the diagnostic itself already occupies \u2014 so the lightbulb edit is
# pixel-aligned with the squiggly the user clicked, both inside single-
# line literals and inside multi-line raw strings.

_CODE_ACTION_OPTIONS = lsp.CodeActionOptions(
    code_action_kinds=[lsp.CodeActionKind.QuickFix, lsp.CodeActionKind.RefactorRewrite],
    resolve_provider=False,
)


def _ranges_overlap(a: lsp.Range, b: lsp.Range) -> bool:
    """Return True if two LSP ranges overlap on the same coordinate plane."""
    if a.end.line < b.start.line or b.end.line < a.start.line:
        return False
    if a.end.line == b.start.line and a.end.character < b.start.character:
        return False
    if b.end.line == a.start.line and b.end.character < a.start.character:
        return False
    return True


def _redos_actions_for_diagnostic(
    uri: str, diag: lsp.Diagnostic
) -> List[lsp.CodeAction]:
    """Materialise the rewrites attached to a REDOS_RISK diagnostic.

    The diagnostic's ``range`` is already in host coordinates (projected
    by :func:`_project_diagnostic` for host languages, or native for
    ``.strl`` files), so the ``TextEdit`` simply replaces that range with
    the proposed text. The first action is marked ``isPreferred`` so the
    editor's default lightbulb keystroke applies the safest rewrite.
    """
    data = diag.data or {}
    replacements = data.get("replacements") or []
    if not replacements:
        return []
    actions: List[lsp.CodeAction] = []
    for idx, replacement in enumerate(replacements):
        new_text = replacement.get("newText") or replacement.get("text") or ""
        title = replacement.get("title") or "Apply STRling safety rewrite"
        edit = lsp.WorkspaceEdit(
            changes={uri: [lsp.TextEdit(range=diag.range, new_text=new_text)]}
        )
        actions.append(
            lsp.CodeAction(
                title=title,
                kind=lsp.CodeActionKind.QuickFix,
                diagnostics=[diag],
                edit=edit,
                is_preferred=(idx == 0),
            )
        )
    return actions


@server.feature(lsp.TEXT_DOCUMENT_CODE_ACTION, _CODE_ACTION_OPTIONS)
def code_action(
    ls: STRlingLanguageServer, params: lsp.CodeActionParams
) -> List[lsp.CodeAction]:
    """Return quick-fix code actions for STRling-emitted diagnostics.

    Walks ``params.context.diagnostics`` (LSP guarantees these are scoped
    to the requested ``range``) and produces a quick-fix per safety
    rewrite carried in each diagnostic's ``data`` payload. Diagnostics
    without a ``data.replacements`` payload are ignored, leaving room
    for non-actionable warnings to coexist alongside actionable ones.
    """
    uri = params.text_document.uri
    actions: List[lsp.CodeAction] = []
    context = params.context
    diagnostics = list(context.diagnostics) if context else []

    # Fall back to the full per-URI diagnostic cache when the client did
    # not pre-filter (older clients sometimes pass an empty list).
    if not diagnostics:
        diagnostics = list(_LAST_DIAGNOSTICS.get(uri, []))

    for diag in diagnostics:
        if diag.code != "REDOS_RISK":
            continue
        if not _ranges_overlap(diag.range, params.range):
            continue
        actions.extend(_redos_actions_for_diagnostic(uri, diag))
    return actions


# --------------------------------------------------------------------------- #
# Document symbols                                                            #
# --------------------------------------------------------------------------- #
#
# The intelligence layer returns a hierarchical outline in virtual-document
# coordinates. The LSP layer projects each range onto the host file when
# the document is a host language, then converts the dict shape into the
# typed ``DocumentSymbol`` dataclass tree the protocol expects.


def _project_range_dict_to_host(
    range_dict: Dict[str, Any], island: Island
) -> Dict[str, Any]:
    """Translate a virtual-doc LSP range dict onto host coordinates."""
    start = island.to_host(
        range_dict["start"]["line"], range_dict["start"]["character"]
    )
    end = island.to_host(range_dict["end"]["line"], range_dict["end"]["character"])
    return {
        "start": {"line": start.line, "character": start.character},
        "end": {"line": end.line, "character": end.character},
    }


def _project_symbol_dict(
    symbol: Dict[str, Any], island: Optional[Island]
) -> Dict[str, Any]:
    """Recursively project a symbol dict; identity transform when native."""
    if island is None:
        return symbol
    return {
        "name": symbol["name"],
        "detail": symbol.get("detail"),
        "kind": symbol["kind"],
        "range": _project_range_dict_to_host(symbol["range"], island),
        "selectionRange": _project_range_dict_to_host(symbol["selectionRange"], island),
        "children": [
            _project_symbol_dict(c, island) for c in symbol.get("children", [])
        ],
    }


def _symbol_dict_to_lsp(symbol: Dict[str, Any]) -> lsp.DocumentSymbol:
    """Convert a JSON-shaped symbol into an ``lsp.DocumentSymbol`` tree."""
    rng = symbol["range"]
    sel = symbol["selectionRange"]
    return lsp.DocumentSymbol(
        name=symbol["name"],
        detail=symbol.get("detail"),
        kind=lsp.SymbolKind(int(symbol["kind"])),
        range=lsp.Range(
            start=lsp.Position(
                line=rng["start"]["line"], character=rng["start"]["character"]
            ),
            end=lsp.Position(
                line=rng["end"]["line"], character=rng["end"]["character"]
            ),
        ),
        selection_range=lsp.Range(
            start=lsp.Position(
                line=sel["start"]["line"], character=sel["start"]["character"]
            ),
            end=lsp.Position(
                line=sel["end"]["line"], character=sel["end"]["character"]
            ),
        ),
        children=[_symbol_dict_to_lsp(c) for c in symbol.get("children", [])],
    )


@server.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(
    ls: STRlingLanguageServer, params: lsp.DocumentSymbolParams
) -> List[lsp.DocumentSymbol]:
    """Return the structural outline of a STRling document.

    Native ``.strl`` files outline the entire buffer; host-language
    files outline every island and project each symbol's range onto
    host coordinates so the editor's outline view collapses naturally
    into the surrounding source.
    """
    uri = params.text_document.uri
    try:
        doc = ls.workspace.get_text_document(uri)
        source = doc.source
    except Exception:
        return []

    symbols: List[Dict[str, Any]] = []
    if language_for_uri(uri) is not None:
        islands = _ISLANDS_BY_URI.get(uri) or extract_islands_for_uri(source, uri)
        _ISLANDS_BY_URI[uri] = islands
        for island in islands:
            for sym in extract_document_symbols(island.virtual_content):
                symbols.append(_project_symbol_dict(sym, island))
    else:
        symbols = extract_document_symbols(source)

    return [_symbol_dict_to_lsp(s) for s in symbols]


# --------------------------------------------------------------------------- #
# Go-to-definition: registry navigation                                       #
# --------------------------------------------------------------------------- #
#
# The cursor word is matched against the central registry (canonical
# names plus trigger keywords). When an entry is found, the location of
# its ``"name"`` declaration inside ``spec/stdlib/registry.json`` is
# returned. Words inside an island use the virtual-document character
# at the cursor; words in host code use the host buffer directly so
# calls like ``s.email()`` resolve from the host token.


def _word_at_host(content: str, line: int, character: int) -> Optional[str]:
    """Return the identifier under a ``(line, character)`` host coordinate."""
    lines = content.split("\n")
    if line < 0 or line >= len(lines):
        return None
    return _word_at(lines[line], character)


@server.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(
    ls: STRlingLanguageServer, params: lsp.DefinitionParams
) -> Optional[lsp.Location]:
    """Resolve the cursor word to a registry entry and return its location."""
    uri = params.text_document.uri
    try:
        doc = ls.workspace.get_text_document(uri)
        source = doc.source
    except Exception:
        return None

    word: Optional[str] = None
    line = params.position.line
    character = params.position.character

    # Inside a host-language island the cursor coordinate is in host
    # space -- translate it back to virtual space so the word extraction
    # uses the unescaped pattern text.
    if language_for_uri(uri) is not None:
        islands = _ISLANDS_BY_URI.get(uri) or extract_islands_for_uri(source, uri)
        _ISLANDS_BY_URI[uri] = islands
        for island in islands:
            mapped = island.from_host(line, character)
            if mapped is None:
                continue
            vd_line, vd_char = mapped
            vd_lines = island.virtual_content.split("\n")
            if vd_line < len(vd_lines):
                word = _word_at(vd_lines[vd_line], vd_char)
            break
        # Fall back to the host buffer so calls like ``s.email()`` (where
        # ``email`` is *outside* any island) still resolve to the registry.
        if word is None:
            word = _word_at_host(source, line, character)
    else:
        word = _word_at_host(source, line, character)

    if not word:
        return None

    location_dict = find_registry_definition(word)
    if location_dict is None:
        return None
    rng = location_dict["range"]
    return lsp.Location(
        uri=location_dict["uri"],
        range=lsp.Range(
            start=lsp.Position(
                line=rng["start"]["line"], character=rng["start"]["character"]
            ),
            end=lsp.Position(
                line=rng["end"]["line"], character=rng["end"]["character"]
            ),
        ),
    )


# --------------------------------------------------------------------------- #
# Document formatting                                                         #
# --------------------------------------------------------------------------- #
#
# Native ``.strl`` files are formatted end-to-end. Host-language files
# format each island independently and emit one ``TextEdit`` per island
# whose range covers only the *interior* of the literal, leaving the
# host-language quotes, brackets, and surrounding code untouched.


def _island_host_range(island: Island) -> lsp.Range:
    """Return the host-coordinate range covering an island's interior."""
    lines = island.virtual_content.split("\n")
    last_line_idx = max(0, len(lines) - 1)
    last_len = len(lines[last_line_idx])
    end = island.to_host(last_line_idx, last_len)
    return lsp.Range(
        start=lsp.Position(
            line=island.host_start.line, character=island.host_start.character
        ),
        end=lsp.Position(line=end.line, character=end.character),
    )


def _indent_string(options: Optional[lsp.FormattingOptions]) -> str:
    """Build the per-level indent token from the client's options."""
    if options is None:
        return "  "
    if not options.insert_spaces:
        return "\t"
    size = max(1, int(options.tab_size or 2))
    return " " * size


def _format_islands_into_host(islands: List[Island], indent: str) -> List[lsp.TextEdit]:
    """Pretty-print each island and turn the result into host-scoped edits."""
    edits: List[lsp.TextEdit] = []
    for island in islands:
        result = format_pattern(island.virtual_content, indent=indent)
        if not result.get("success"):
            continue
        formatted = str(result.get("formatted") or "").rstrip("\n")
        if formatted == island.virtual_content:
            continue
        edits.append(lsp.TextEdit(range=_island_host_range(island), new_text=formatted))
    return edits


@server.feature(lsp.TEXT_DOCUMENT_FORMATTING)
def formatting(
    ls: STRlingLanguageServer, params: lsp.DocumentFormattingParams
) -> List[lsp.TextEdit]:
    """Format the document and return the minimal set of replacement edits.

    Host-language files only rewrite the *interior* of each island so
    the surrounding quotes, brackets, and host syntax stay intact --
    formatting an embedded pattern can never corrupt the surrounding
    Python/TypeScript/Rust/Java code.
    """
    uri = params.text_document.uri
    try:
        doc = ls.workspace.get_text_document(uri)
        source = doc.source
    except Exception:
        return []

    indent = _indent_string(params.options)

    if language_for_uri(uri) is not None:
        islands = _ISLANDS_BY_URI.get(uri) or extract_islands_for_uri(source, uri)
        _ISLANDS_BY_URI[uri] = islands
        return _format_islands_into_host(islands, indent)

    result = format_pattern(source, indent=indent)
    if not result.get("success"):
        return []
    formatted = str(result.get("formatted") or "")
    if formatted == source:
        return []
    # Replace the entire native document. The end-of-document position is
    # computed from the last line so the edit covers every existing byte.
    lines = source.split("\n")
    end_line = max(0, len(lines) - 1)
    end_char = len(lines[end_line])
    return [
        lsp.TextEdit(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=end_line, character=end_char),
            ),
            new_text=formatted,
        )
    ]


@server.feature(lsp.INITIALIZE)
def initialize(ls: STRlingLanguageServer, params: lsp.InitializeParams) -> None:
    """Handle initialization request."""
    ls.show_message_log("STRling Language Server initialized")


def main() -> None:
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
