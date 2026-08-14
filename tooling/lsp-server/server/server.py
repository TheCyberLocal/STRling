#!/usr/bin/env python3
"""
STRling Language Server - Real-Time Diagnostics via LSP

This module implements a Language Server Protocol (LSP) server for STRling,
providing real-time diagnostics and error feedback in code editors
(VS Code, etc.).

Architecture:
    - LSP Server (this file) ← handles LSP transport, debounce, and host
      coordinate projection.
    - Canonical Core Bridge (``server.canonical_core``) ← invokes the Rust
      kernel and projects immutable CompileResult evidence.
    - Canonical Editor Bridge (``server.canonical_intelligence``) ← projects
      completion, navigation, symbols, and tokens from canonical frontends.
    - Island Extractor (``server.island_extractor``) ← recognizes governed,
      source-identity-preserving host literal forms.

Usage:
    python server/server.py [--tcp]
    python server/server.py --stdio (default)
"""

import os
import sys
import threading
import time
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple

_SERVER_FILE = os.path.realpath(os.path.abspath(__file__))
_SERVER_DIR = os.path.dirname(_SERVER_FILE)
_SOURCE_ROOT = os.path.dirname(_SERVER_DIR)
_VENDOR_DIR = os.path.join(_SERVER_DIR, "libs")

if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)

if _SOURCE_ROOT not in sys.path:
    # Source-tree runs keep lightweight local shims for pygls and lsprotocol
    # one directory above this module. We add that fallback after the vendored
    # path so packaged dist/server/libs still wins when present.
    insert_index = 1 if sys.path and sys.path[0] == _VENDOR_DIR else 0
    sys.path.insert(insert_index, _SOURCE_ROOT)


def _format_sys_path_matrix() -> str:
    """Render ``sys.path`` as an indexed matrix for stderr forensics."""
    return "\n".join(
        f"  [{index}] {entry or '<empty>'}" for index, entry in enumerate(sys.path)
    )


def _exit_with_import_context(import_target: str, import_error: ImportError) -> None:
    """Terminate with a signpost error that includes path and env forensics."""
    sys.stderr.write(
        f"STRling language server failed to import {import_target}.\n"
        f"ImportError: {import_error}\n"
        f"Server file: {_SERVER_FILE}\n"
        f"Server directory: {_SERVER_DIR}\n"
        f"Target vendor directory: {_VENDOR_DIR}\n"
        f"Vendor directory exists: {os.path.isdir(_VENDOR_DIR)}\n"
        f"Current working directory: {os.getcwd()}\n"
        f"Python executable: {sys.executable}\n"
        f"PYTHONPATH env: {os.environ.get('PYTHONPATH', '<unset>')}\n"
        "sys.path matrix:\n"
        f"{_format_sys_path_matrix()}\n"
        "Next step: rebuild the extension dist folder so dist/server/libs contains "
        "the packaged transport and canonical editor adapters before relaunching the server.\n"
    )
    sys.exit(1)


try:
    from lsprotocol import types as lsp
    from pygls.protocol import LanguageServerProtocol, default_converter

    try:
        from pygls.lsp.server import LanguageServer as _PyglsLanguageServer

        _USING_REAL_PYGLS = True
    except ImportError:
        from pygls.server import JsonRPCServer as _PyglsLanguageServer

        _USING_REAL_PYGLS = False
except ImportError as import_error:
    _exit_with_import_context("its transport dependencies", import_error)

try:
    try:
        from .canonical_core import (
            DEFAULT_POSITION_ENCODING,
            CanonicalCompiler,
            CompilerServiceError,
            HoverEvidence,
            byte_offset_to_position,
            canonical_source_id,
            diagnostic_payload,
            position_to_byte_offset,
            project_span,
            render_hover,
        )
        from .canonical_intelligence import (
            EDITOR_PROJECTION_VERSION,
            MAX_SYMBOLS,
            MAX_TOKENS,
            TOKEN_MODIFIERS,
            TOKEN_TYPES,
            CanonicalIntelligence,
            EditorServiceError,
            catalog_definition,
            host_completion,
        )
        from .island_extractor import (
            Island,
            extract_islands_for_uri,
            language_for_uri,
        )
    except ImportError:
        canonical_core = import_module("canonical_core")
        DEFAULT_POSITION_ENCODING = canonical_core.DEFAULT_POSITION_ENCODING
        CanonicalCompiler = canonical_core.CanonicalCompiler
        CompilerServiceError = canonical_core.CompilerServiceError
        HoverEvidence = canonical_core.HoverEvidence
        byte_offset_to_position = canonical_core.byte_offset_to_position
        canonical_source_id = canonical_core.canonical_source_id
        diagnostic_payload = canonical_core.diagnostic_payload
        position_to_byte_offset = canonical_core.position_to_byte_offset
        project_span = canonical_core.project_span
        render_hover = canonical_core.render_hover

        canonical_intelligence = import_module("canonical_intelligence")
        EDITOR_PROJECTION_VERSION = canonical_intelligence.EDITOR_PROJECTION_VERSION
        MAX_SYMBOLS = canonical_intelligence.MAX_SYMBOLS
        MAX_TOKENS = canonical_intelligence.MAX_TOKENS
        TOKEN_MODIFIERS = canonical_intelligence.TOKEN_MODIFIERS
        TOKEN_TYPES = canonical_intelligence.TOKEN_TYPES
        CanonicalIntelligence = canonical_intelligence.CanonicalIntelligence
        EditorServiceError = canonical_intelligence.EditorServiceError
        catalog_definition = canonical_intelligence.catalog_definition
        host_completion = canonical_intelligence.host_completion

        from island_extractor import (  # type: ignore[no-redef]
            Island,
            extract_islands_for_uri,
            language_for_uri,
        )
except ImportError as import_error:
    _exit_with_import_context("its canonical editor adapters", import_error)


# Define the server with proper protocol
class STRlingLanguageServer(_PyglsLanguageServer):
    """STRling Language Server using JsonRPCServer."""

    def __init__(self):
        self.name = "strling-lsp"
        self.version = "v1.0.0"
        if _USING_REAL_PYGLS:
            super().__init__(
                self.name,
                self.version,
                protocol_cls=LanguageServerProtocol,
                converter_factory=default_converter,
            )
        else:
            super().__init__(
                protocol_cls=LanguageServerProtocol,
                converter_factory=default_converter,
            )


# Initialize the language server
server: STRlingLanguageServer = STRlingLanguageServer()


def _log_message(ls: STRlingLanguageServer, message: str) -> None:
    """Send a log message through either the local shim or real pygls."""
    if hasattr(ls, "show_message_log"):
        ls.show_message_log(message)
        return

    ls.window_log_message(
        lsp.LogMessageParams(type=lsp.MessageType.Log, message=message)
    )


def _diagnostic_from_dict(diag: Dict[str, Any]) -> lsp.Diagnostic:
    """Convert one canonical projection payload to an LSP object."""
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
    """Compile one regex-compatible source unit through the canonical kernel."""
    try:
        result = _compile_cached(content, "regex", _TARGET_PROFILE, _POSITION_ENCODING)
        return _diagnostics_from_result(result, content, _POSITION_ENCODING)
    except (CompilerServiceError, ValueError) as error:
        _log_message(server, f"Canonical compiler service error: {error}")
        return []


# Backwards-compatible name retained for existing editor callers. It now uses
# the canonical CLI subprocess rather than the retired Python semantic path.
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
# right place. ``server.island_extractor`` owns this tooling-only projection.
#
# Per-URI cache of the most recent island layout — used by hover routing
# without re-scanning the source.
_ISLANDS_BY_URI: Dict[str, List[Island]] = {}

# Per-URI cache of the last published diagnostics. Code actions intentionally
# do not consult this cache: the client must return the exact diagnostic for
# the current immutable snapshot before a certified rewrite is materialized.
_LAST_DIAGNOSTICS: Dict[str, List["lsp.Diagnostic"]] = {}

# Debounce table: ``uri -> Timer``. Rapid keystrokes only trigger one
# diagnostic pass per quiet window (50 ms by default — tuned to feel
# instantaneous on rapid keystrokes).
_DEBOUNCE_TIMERS: Dict[str, threading.Timer] = {}
_DEBOUNCE_INTERVAL_S: float = 0.05
# --------------------------------------------------------------------------- #
# Canonical diagnostics and hover                                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _DocumentSnapshot:
    uri: str
    version: Optional[int]
    source: str
    content_id: str
    generation: int
    position_encoding: str
    target_profile: Optional[str]


@dataclass(frozen=True)
class _CompiledUnit:
    source: str
    frontend: str
    result: Dict[str, Any]
    island: Optional[Island]


@dataclass(frozen=True)
class _SnapshotResult:
    snapshot: _DocumentSnapshot
    units: Tuple[_CompiledUnit, ...]
    diagnostics: Tuple[lsp.Diagnostic, ...]
    islands: Tuple[Island, ...]


_COMPILER = CanonicalCompiler()
_EDITOR = CanonicalIntelligence()
_POSITION_ENCODING = DEFAULT_POSITION_ENCODING
_TARGET_PROFILE: Optional[str] = None
_MAX_ISLANDS = 256
_RESULT_CACHE_LIMIT = 128

_CANONICAL_RESULTS_BY_URI: Dict[str, _SnapshotResult] = {}
_SNAPSHOTS_BY_URI: Dict[str, _DocumentSnapshot] = {}
_ACTIVE_PROCESSES: Dict[str, Tuple[int, Any]] = {}
_GENERATIONS: Dict[str, int] = {}
_RESULT_CACHE: Dict[Tuple[str, str, Optional[str], str], Dict[str, Any]] = {}
_RESULT_CACHE_ORDER: List[Tuple[str, str, Optional[str], str]] = []
_EDITOR_CACHE: Dict[
    Tuple[str, str, Optional[int], Optional[str], str, str], Dict[str, Any]
] = {}
_EDITOR_CACHE_ORDER: List[
    Tuple[str, str, Optional[int], Optional[str], str, str]
] = []
_STATE_LOCK = threading.RLock()


def _frontend_for_uri(uri: str) -> str:
    return "semantic" if uri.lower().endswith(".semantic.strling") else "regex"


def _is_host_uri(uri: str) -> bool:
    language = language_for_uri(uri)
    return language is not None and language != "strl"


def _diagnostics_from_result(
    result: Dict[str, Any], source: str, encoding: str
) -> List[lsp.Diagnostic]:
    return [
        _diagnostic_from_dict(diagnostic_payload(diagnostic, source, encoding))
        for diagnostic in result.get("diagnostics", [])
    ]


def _compile_cached(
    source: str,
    frontend: str,
    target: Optional[str],
    encoding: str,
    *,
    timeout_seconds: Optional[float] = None,
    process_observer=None,
) -> Dict[str, Any]:
    key = (canonical_source_id(source), frontend, target, encoding)
    with _STATE_LOCK:
        cached = _RESULT_CACHE.get(key)
        if cached is not None:
            return cached
    result = _COMPILER.compile(
        source,
        frontend=frontend,
        target=target,
        timeout_seconds=timeout_seconds,
        process_observer=process_observer,
    )
    with _STATE_LOCK:
        if key not in _RESULT_CACHE:
            _RESULT_CACHE[key] = result
            _RESULT_CACHE_ORDER.append(key)
            while len(_RESULT_CACHE_ORDER) > _RESULT_CACHE_LIMIT:
                expired = _RESULT_CACHE_ORDER.pop(0)
                _RESULT_CACHE.pop(expired, None)
        return _RESULT_CACHE[key]


def _editor_cached(
    source: str,
    frontend: str,
    cursor_byte: Optional[int],
    target: Optional[str],
    encoding: str,
    *,
    timeout_seconds: Optional[float] = None,
    process_observer=None,
) -> Dict[str, Any]:
    key = (
        canonical_source_id(source),
        frontend,
        cursor_byte,
        target,
        encoding,
        EDITOR_PROJECTION_VERSION,
    )
    with _STATE_LOCK:
        cached = _EDITOR_CACHE.get(key)
        if cached is not None:
            return cached
    result = _EDITOR.project(
        source,
        frontend=frontend,
        cursor_byte=cursor_byte,
        timeout_seconds=timeout_seconds,
        process_observer=process_observer,
    )
    with _STATE_LOCK:
        if key not in _EDITOR_CACHE:
            _EDITOR_CACHE[key] = result
            _EDITOR_CACHE_ORDER.append(key)
            while len(_EDITOR_CACHE_ORDER) > _RESULT_CACHE_LIMIT:
                expired = _EDITOR_CACHE_ORDER.pop(0)
                _EDITOR_CACHE.pop(expired, None)
        return _EDITOR_CACHE[key]


def _project_editor_unit(
    compiled: _SnapshotResult,
    unit: _CompiledUnit,
    cursor_byte: Optional[int],
    *,
    timeout_seconds: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    snapshot = compiled.snapshot
    if not _is_current(snapshot):
        return None
    try:
        result = _editor_cached(
            unit.source,
            unit.frontend,
            cursor_byte,
            snapshot.target_profile,
            snapshot.position_encoding,
            timeout_seconds=timeout_seconds,
            process_observer=lambda process: _observe_process(snapshot, process),
        )
    except EditorServiceError:
        return None
    return result if _is_current(snapshot) else None


def _host_position(position, host_source: str):
    byte_offset = position_to_byte_offset(
        host_source, position.line, position.character, "utf-32"
    )
    projected = byte_offset_to_position(host_source, byte_offset, _POSITION_ENCODING)
    return lsp.Position(line=projected.line, character=projected.character)


def _project_diagnostic(
    diagnostic: lsp.Diagnostic, island: Island, host_source: str
) -> lsp.Diagnostic:
    virtual_start = island.to_host(
        diagnostic.range.start.line, diagnostic.range.start.character
    )
    virtual_end = island.to_host(
        diagnostic.range.end.line, diagnostic.range.end.character
    )
    return lsp.Diagnostic(
        range=lsp.Range(
            start=_host_position(virtual_start, host_source),
            end=_host_position(virtual_end, host_source),
        ),
        message=diagnostic.message,
        severity=diagnostic.severity,
        source=diagnostic.source,
        code=diagnostic.code,
        data=diagnostic.data,
    )


def _diagnostics_for_host(uri: str, source: str) -> List[lsp.Diagnostic]:
    """Synchronously return canonical diagnostics projected into a host file."""
    if not _is_host_uri(uri):
        result = _compile_cached(
            source, _frontend_for_uri(uri), _TARGET_PROFILE, _POSITION_ENCODING
        )
        _ISLANDS_BY_URI[uri] = []
        return _diagnostics_from_result(result, source, _POSITION_ENCODING)
    islands = extract_islands_for_uri(source, uri)
    if len(islands) > _MAX_ISLANDS:
        raise CompilerServiceError(
            "island_limit", "document exceeds the LSP island limit"
        )
    _ISLANDS_BY_URI[uri] = islands
    diagnostics: List[lsp.Diagnostic] = []
    for island in islands:
        result = _compile_cached(
            island.virtual_content, "regex", _TARGET_PROFILE, _POSITION_ENCODING
        )
        for diagnostic in _diagnostics_from_result(
            result, island.virtual_content, "utf-32"
        ):
            diagnostics.append(_project_diagnostic(diagnostic, island, source))
    return diagnostics


def _terminate_process(process: Any) -> None:
    try:
        if process.poll() is None:
            process.terminate()
    except OSError:
        pass


def _cancel_uri_locked(uri: str) -> None:
    timer = _DEBOUNCE_TIMERS.pop(uri, None)
    if timer is not None:
        timer.cancel()
    active = _ACTIVE_PROCESSES.pop(uri, None)
    if active is not None:
        _terminate_process(active[1])


def _capture_snapshot(
    ls: STRlingLanguageServer, uri: str, version: Optional[int] = None
) -> _DocumentSnapshot:
    document = ls.workspace.get_text_document(uri)
    source = document.source
    if version is None:
        version = getattr(document, "version", None)
    with _STATE_LOCK:
        _cancel_uri_locked(uri)
        generation = _GENERATIONS.get(uri, 0) + 1
        _GENERATIONS[uri] = generation
        snapshot = _DocumentSnapshot(
            uri=uri,
            version=version,
            source=source,
            content_id=canonical_source_id(source),
            generation=generation,
            position_encoding=_POSITION_ENCODING,
            target_profile=_TARGET_PROFILE,
        )
        _SNAPSHOTS_BY_URI[uri] = snapshot
        _CANONICAL_RESULTS_BY_URI.pop(uri, None)
        return snapshot


def _is_current(snapshot: _DocumentSnapshot) -> bool:
    with _STATE_LOCK:
        return _SNAPSHOTS_BY_URI.get(snapshot.uri) == snapshot


def _observe_process(snapshot: _DocumentSnapshot, process: Any) -> None:
    with _STATE_LOCK:
        if process is None:
            active = _ACTIVE_PROCESSES.get(snapshot.uri)
            if active is not None and active[0] == snapshot.generation:
                _ACTIVE_PROCESSES.pop(snapshot.uri, None)
            return
        if _SNAPSHOTS_BY_URI.get(snapshot.uri) != snapshot:
            _terminate_process(process)
            return
        _ACTIVE_PROCESSES[snapshot.uri] = (snapshot.generation, process)


def _compile_snapshot(snapshot: _DocumentSnapshot) -> _SnapshotResult:
    if _is_host_uri(snapshot.uri):
        islands = extract_islands_for_uri(snapshot.source, snapshot.uri)
        if len(islands) > _MAX_ISLANDS:
            raise CompilerServiceError(
                "island_limit", "document exceeds the 256-island LSP limit"
            )
        sources = [(island.virtual_content, "regex", island) for island in islands]
    else:
        islands = []
        sources = [(snapshot.source, _frontend_for_uri(snapshot.uri), None)]

    deadline = time.monotonic() + _COMPILER.timeout_seconds
    units: List[_CompiledUnit] = []
    diagnostics: List[lsp.Diagnostic] = []
    for unit_source, frontend, island in sources:
        if not _is_current(snapshot):
            raise CompilerServiceError("cancelled", "document snapshot was superseded")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CompilerServiceError(
                "timeout", "document compiler budget was exhausted"
            )
        result = _compile_cached(
            unit_source,
            frontend,
            snapshot.target_profile,
            snapshot.position_encoding,
            timeout_seconds=remaining,
            process_observer=lambda process: _observe_process(snapshot, process),
        )
        units.append(
            _CompiledUnit(
                source=unit_source,
                frontend=frontend,
                result=result,
                island=island,
            )
        )
        if island is None:
            diagnostics.extend(
                _diagnostics_from_result(
                    result, unit_source, snapshot.position_encoding
                )
            )
        else:
            for diagnostic in _diagnostics_from_result(result, unit_source, "utf-32"):
                diagnostics.append(
                    _project_diagnostic(diagnostic, island, snapshot.source)
                )
    return _SnapshotResult(
        snapshot=snapshot,
        units=tuple(units),
        diagnostics=tuple(diagnostics),
        islands=tuple(islands),
    )


def _publish_snapshot(ls: STRlingLanguageServer, compiled: _SnapshotResult) -> None:
    snapshot = compiled.snapshot
    with _STATE_LOCK:
        if _SNAPSHOTS_BY_URI.get(snapshot.uri) != snapshot:
            return
        _CANONICAL_RESULTS_BY_URI[snapshot.uri] = compiled
        _ISLANDS_BY_URI[snapshot.uri] = list(compiled.islands)
        _LAST_DIAGNOSTICS[snapshot.uri] = list(compiled.diagnostics)
    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(
            uri=snapshot.uri,
            diagnostics=list(compiled.diagnostics),
            version=snapshot.version,
        )
    )


def _execute_snapshot(ls: STRlingLanguageServer, snapshot: _DocumentSnapshot) -> None:
    try:
        compiled = _compile_snapshot(snapshot)
    except CompilerServiceError as error:
        if not _is_current(snapshot):
            return
        _log_message(ls, f"Canonical compiler service error [{error.code}]: {error}")
        with _STATE_LOCK:
            _CANONICAL_RESULTS_BY_URI.pop(snapshot.uri, None)
            _ISLANDS_BY_URI.pop(snapshot.uri, None)
            _LAST_DIAGNOSTICS[snapshot.uri] = []
        ls.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(
                uri=snapshot.uri, diagnostics=[], version=snapshot.version
            )
        )
        return
    except (ValueError, KeyError, TypeError) as error:
        if not _is_current(snapshot):
            return
        _log_message(ls, f"Canonical evidence projection error: {error}")
        with _STATE_LOCK:
            _CANONICAL_RESULTS_BY_URI.pop(snapshot.uri, None)
            _ISLANDS_BY_URI.pop(snapshot.uri, None)
            _LAST_DIAGNOSTICS[snapshot.uri] = []
        ls.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(
                uri=snapshot.uri, diagnostics=[], version=snapshot.version
            )
        )
        return
    _publish_snapshot(ls, compiled)


def validate_document(
    ls: STRlingLanguageServer, uri: str, version: Optional[int] = None
) -> None:
    """Synchronously validate one immutable document snapshot."""
    try:
        snapshot = _capture_snapshot(ls, uri, version)
        _execute_snapshot(ls, snapshot)
    except Exception as error:  # pragma: no cover - transport isolation guard
        _log_message(ls, f"Error validating document: {error}")


def _schedule_validation(
    ls: STRlingLanguageServer,
    uri: str,
    version: Optional[int] = None,
    *,
    delay: float = _DEBOUNCE_INTERVAL_S,
) -> None:
    snapshot = _capture_snapshot(ls, uri, version)
    timer = threading.Timer(delay, _execute_snapshot, args=(ls, snapshot))
    timer.daemon = True
    with _STATE_LOCK:
        if _SNAPSHOTS_BY_URI.get(uri) != snapshot:
            return
        _DEBOUNCE_TIMERS[uri] = timer
    timer.start()


def _document_version(params: Any) -> Optional[int]:
    version = getattr(params.text_document, "version", None)
    return version if isinstance(version, int) else None


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: STRlingLanguageServer, params: lsp.DidOpenTextDocumentParams) -> None:
    """Capture and asynchronously validate the opened document version."""
    _log_message(ls, f"Document opened: {params.text_document.uri}")
    _schedule_validation(
        ls, params.text_document.uri, _document_version(params), delay=0.0
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(
    ls: STRlingLanguageServer, params: lsp.DidChangeTextDocumentParams
) -> None:
    """Invalidate older work and debounce the newest full-content version."""
    _schedule_validation(ls, params.text_document.uri, _document_version(params))


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: STRlingLanguageServer, params: lsp.DidSaveTextDocumentParams) -> None:
    """Validate the exact current saved snapshot without blocking the loop."""
    _schedule_validation(
        ls, params.text_document.uri, _document_version(params), delay=0.0
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(
    ls: STRlingLanguageServer, params: lsp.DidCloseTextDocumentParams
) -> None:
    """Cancel work, remove snapshot state, and clear editor diagnostics."""
    uri = params.text_document.uri
    with _STATE_LOCK:
        _cancel_uri_locked(uri)
        _GENERATIONS[uri] = _GENERATIONS.get(uri, 0) + 1
        _SNAPSHOTS_BY_URI.pop(uri, None)
        _CANONICAL_RESULTS_BY_URI.pop(uri, None)
        _ISLANDS_BY_URI.pop(uri, None)
        _LAST_DIAGNOSTICS.pop(uri, None)
    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=[])
    )


def _set_session_options(
    *,
    position_encoding: Optional[str] = None,
    target_profile: Optional[str] = None,
) -> None:
    """Invalidate document projections after an explicit session option change."""
    global _POSITION_ENCODING, _TARGET_PROFILE
    if position_encoding is not None and position_encoding not in {
        "utf-8",
        "utf-16",
        "utf-32",
    }:
        raise ValueError(f"unsupported position encoding {position_encoding!r}")
    with _STATE_LOCK:
        new_encoding = position_encoding or _POSITION_ENCODING
        if new_encoding == _POSITION_ENCODING and target_profile == _TARGET_PROFILE:
            return
        for uri in list(_SNAPSHOTS_BY_URI):
            _cancel_uri_locked(uri)
        _POSITION_ENCODING = new_encoding
        _TARGET_PROFILE = target_profile
        _SNAPSHOTS_BY_URI.clear()
        _CANONICAL_RESULTS_BY_URI.clear()
        _ISLANDS_BY_URI.clear()
        _LAST_DIAGNOSTICS.clear()
        _EDITOR_CACHE.clear()
        _EDITOR_CACHE_ORDER.clear()


def _snapshot_result_for_hover(
    ls: STRlingLanguageServer, uri: str
) -> Optional[_SnapshotResult]:
    try:
        source = ls.workspace.get_text_document(uri).source
    except Exception:
        return None
    with _STATE_LOCK:
        compiled = _CANONICAL_RESULTS_BY_URI.get(uri)
        if compiled is None:
            return None
        snapshot = compiled.snapshot
        if (
            snapshot.source != source
            or snapshot.position_encoding != _POSITION_ENCODING
            or snapshot.target_profile != _TARGET_PROFILE
        ):
            return None
        return compiled


def _hover_range(
    evidence: HoverEvidence,
    unit: _CompiledUnit,
    host_source: str,
) -> lsp.Range:
    start, end = project_span(unit.source, evidence.start, evidence.end, "utf-32")
    if unit.island is not None:
        host_start = unit.island.to_host(start.line, start.character)
        host_end = unit.island.to_host(end.line, end.character)
        return lsp.Range(
            start=_host_position(host_start, host_source),
            end=_host_position(host_end, host_source),
        )
    projected_start, projected_end = project_span(
        unit.source, evidence.start, evidence.end, _POSITION_ENCODING
    )
    return lsp.Range(
        start=lsp.Position(
            line=projected_start.line, character=projected_start.character
        ),
        end=lsp.Position(line=projected_end.line, character=projected_end.character),
    )


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls: STRlingLanguageServer, params: lsp.HoverParams) -> Optional[lsp.Hover]:
    """Render deterministic hover from the exact current canonical result."""
    uri = params.text_document.uri
    compiled = _snapshot_result_for_hover(ls, uri)
    if compiled is None:
        return None
    try:
        host_byte = position_to_byte_offset(
            compiled.snapshot.source,
            params.position.line,
            params.position.character,
            _POSITION_ENCODING,
        )
        host_utf32 = byte_offset_to_position(
            compiled.snapshot.source, host_byte, "utf-32"
        )
    except ValueError:
        return None

    for unit in compiled.units:
        if unit.island is None:
            cursor_byte = host_byte
        else:
            mapped = unit.island.from_host(host_utf32.line, host_utf32.character)
            if mapped is None:
                continue
            try:
                cursor_byte = position_to_byte_offset(
                    unit.source, mapped[0], mapped[1], "utf-32"
                )
            except ValueError:
                return None
        evidence = render_hover(unit.result, unit.source, cursor_byte)
        if evidence is None:
            return None
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.Markdown, value=evidence.markdown
            ),
            range=_hover_range(evidence, unit, compiled.snapshot.source),
        )
    return None


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
    token_types=list(TOKEN_TYPES),
    token_modifiers=list(TOKEN_MODIFIERS),
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


def _editor_span_range(
    span: Dict[str, Any], unit: _CompiledUnit, host_source: str
) -> lsp.Range:
    start, end = project_span(
        unit.source, int(span["start"]), int(span["end"]), "utf-32"
    )
    if unit.island is not None:
        host_start = unit.island.to_host(start.line, start.character)
        host_end = unit.island.to_host(end.line, end.character)
        return lsp.Range(
            start=_host_position(host_start, host_source),
            end=_host_position(host_end, host_source),
        )
    projected_start, projected_end = project_span(
        unit.source,
        int(span["start"]),
        int(span["end"]),
        _POSITION_ENCODING,
    )
    return lsp.Range(
        start=lsp.Position(
            line=projected_start.line, character=projected_start.character
        ),
        end=lsp.Position(line=projected_end.line, character=projected_end.character),
    )


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
    compiled = _snapshot_result_for_hover(ls, uri)
    if compiled is None:
        return lsp.SemanticTokens(data=[])
    deadline = time.monotonic() + _EDITOR.timeout_seconds
    absolute: List[tuple] = []
    for unit in compiled.units:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return lsp.SemanticTokens(data=[])
        evidence = _project_editor_unit(
            compiled, unit, None, timeout_seconds=remaining
        )
        if evidence is None:
            continue
        for token in evidence["tokens"]:
            token_range = _editor_span_range(
                token["span"], unit, compiled.snapshot.source
            )
            if token_range.start.line != token_range.end.line:
                return lsp.SemanticTokens(data=[])
            length = token_range.end.character - token_range.start.character
            if length <= 0:
                continue
            absolute.append(
                (
                    token_range.start.line,
                    token_range.start.character,
                    length,
                    TOKEN_TYPES.index(token["type"]),
                    0,
                )
            )
            if len(absolute) > MAX_TOKENS:
                return lsp.SemanticTokens(data=[])
    return lsp.SemanticTokens(data=_delta_encode_tokens(absolute))


# --------------------------------------------------------------------------- #
# Completion                                                                  #
# --------------------------------------------------------------------------- #
#
# Canonical frontends return parser-expected terminals and already-declared
# capture identities. The compatibility adapter exposes governed Simply and
# stdlib metadata only at the retained exact ``s.`` member boundary.

_COMPLETION_OPTIONS = lsp.CompletionOptions(
    trigger_characters=["."],
    resolve_provider=False,
)


def _completion_item_from_dict(
    item: Dict[str, Any], replacement: lsp.Range, order: int
) -> lsp.CompletionItem:
    kind = (
        lsp.CompletionItemKind.Variable
        if item.get("tier") == "canonical_capture_identity"
        else lsp.CompletionItemKind.Function
    )
    label = str(item.get("label", ""))
    return lsp.CompletionItem(
        label=label,
        kind=kind,
        detail=item.get("detail"),
        insert_text=label,
        insert_text_format=lsp.InsertTextFormat.PlainText,
        filter_text=label,
        sort_text=f"{order:04d}:{item.get('identity', label)}",
        text_edit=lsp.TextEdit(range=replacement, new_text=label),
        data={"canonical_id": item.get("identity"), "tier": item.get("tier")},
    )


def _position_for_host_byte(source: str, byte_offset: int) -> lsp.Position:
    position = byte_offset_to_position(source, byte_offset, _POSITION_ENCODING)
    return lsp.Position(line=position.line, character=position.character)


@server.feature(lsp.TEXT_DOCUMENT_COMPLETION, _COMPLETION_OPTIONS)
def completion(
    ls: STRlingLanguageServer, params: lsp.CompletionParams
) -> lsp.CompletionList:
    """Return context-valid canonical completions for the current snapshot."""
    uri = params.text_document.uri
    compiled = _snapshot_result_for_hover(ls, uri)
    if compiled is None:
        return lsp.CompletionList(is_incomplete=False, items=[])
    try:
        host_byte = position_to_byte_offset(
            compiled.snapshot.source,
            params.position.line,
            params.position.character,
            _POSITION_ENCODING,
        )
        host_utf32 = byte_offset_to_position(
            compiled.snapshot.source, host_byte, "utf-32"
        )
    except ValueError:
        return lsp.CompletionList(is_incomplete=False, items=[])

    candidates: Optional[Dict[str, Any]] = None
    replacement: Optional[lsp.Range] = None
    for unit in compiled.units:
        if unit.island is None:
            cursor_byte = host_byte
        else:
            mapped = unit.island.from_host(host_utf32.line, host_utf32.character)
            if mapped is None:
                continue
            try:
                cursor_byte = position_to_byte_offset(
                    unit.source, mapped[0], mapped[1], "utf-32"
                )
            except ValueError:
                return lsp.CompletionList(is_incomplete=False, items=[])
        candidates = _project_editor_unit(compiled, unit, cursor_byte)
        if candidates is not None and candidates.get("replacement_span") is not None:
            replacement = _editor_span_range(
                candidates["replacement_span"], unit, compiled.snapshot.source
            )
        break

    if candidates is None and _is_host_uri(uri):
        binding_id = language_for_uri(uri)
        if binding_id is not None:
            candidates = host_completion(
                compiled.snapshot.source, host_byte, binding_id=binding_id
            )
            if candidates is not None:
                span = candidates["replacement_span"]
                replacement = lsp.Range(
                    start=_position_for_host_byte(
                        compiled.snapshot.source, int(span["start"])
                    ),
                    end=_position_for_host_byte(
                        compiled.snapshot.source, int(span["end"])
                    ),
                )

    if candidates is None or replacement is None:
        return lsp.CompletionList(is_incomplete=False, items=[])
    items = [
        _completion_item_from_dict(item, replacement, order)
        for order, item in enumerate(candidates["completions"])
    ]
    return lsp.CompletionList(is_incomplete=False, items=items)


# --------------------------------------------------------------------------- #
# Code actions: certified canonical Semantic rewrites                          #
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
    code_action_kinds=[lsp.CodeActionKind.RefactorRewrite],
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


def _ranges_equal(a: lsp.Range, b: lsp.Range) -> bool:
    return (
        a.start.line == b.start.line
        and a.start.character == b.start.character
        and a.end.line == b.end.line
        and a.end.character == b.end.character
    )


def _canonical_diagnostic_source_id(diag: lsp.Diagnostic) -> Optional[str]:
    data = diag.data if isinstance(diag.data, dict) else {}
    canonical = data.get("canonical")
    if not isinstance(canonical, dict):
        return None
    location = canonical.get("primary_location")
    if not isinstance(location, dict):
        return None
    source_id = location.get("source_id")
    return source_id if isinstance(source_id, str) else None


@server.feature(lsp.TEXT_DOCUMENT_CODE_ACTION, _CODE_ACTION_OPTIONS)
def code_action(
    ls: STRlingLanguageServer, params: lsp.CodeActionParams
) -> List[lsp.CodeAction]:
    """Materialize certified rewrites for exact current Semantic evidence."""
    uri = params.text_document.uri
    context = params.context
    diagnostics = list(context.diagnostics) if context else []
    if not diagnostics:
        return []
    compiled = _snapshot_result_for_hover(ls, uri)
    if compiled is None or len(compiled.units) != 1:
        return []
    unit = compiled.units[0]
    if unit.frontend != "semantic" or unit.island is not None:
        return []
    evidence = _project_editor_unit(compiled, unit, None)
    if evidence is None:
        return []

    actions: List[lsp.CodeAction] = []
    for rewrite in evidence["rewrite_actions"]:
        action_range = _editor_span_range(
            rewrite["wrapper_span"], unit, compiled.snapshot.source
        )
        if not _ranges_overlap(action_range, params.range):
            continue
        matching = next(
            (
                diagnostic
                for diagnostic in diagnostics
                if str(diagnostic.code) == rewrite["diagnostic_code"]
                and _canonical_diagnostic_source_id(diagnostic)
                == rewrite["source_id"]
                and _ranges_equal(diagnostic.range, action_range)
                and _ranges_overlap(diagnostic.range, params.range)
            ),
            None,
        )
        if matching is None:
            continue
        actions.append(
            lsp.CodeAction(
                title=rewrite["explanation"],
                kind=lsp.CodeActionKind.RefactorRewrite,
                diagnostics=[matching],
                edit=lsp.WorkspaceEdit(
                    changes={
                        uri: [
                            lsp.TextEdit(
                                range=action_range,
                                new_text=rewrite["replacement_text"],
                            )
                        ]
                    }
                ),
                is_preferred=False,
            )
        )
    return actions


# --------------------------------------------------------------------------- #
# Document symbols                                                            #
# --------------------------------------------------------------------------- #
#
_SYMBOL_KINDS = {
    "empty": lsp.SymbolKind.Null,
    "sequence": lsp.SymbolKind.Array,
    "alternation": lsp.SymbolKind.Enum,
    "literal": lsp.SymbolKind.String,
    "wildcard": lsp.SymbolKind.String,
    "character_set": lsp.SymbolKind.Array,
    "repeat": lsp.SymbolKind.Operator,
    "position": lsp.SymbolKind.Constant,
    "capture": lsp.SymbolKind.Function,
    "backreference": lsp.SymbolKind.Variable,
    "lookaround": lsp.SymbolKind.Function,
    "atomic": lsp.SymbolKind.Function,
}


def _editor_symbol_to_lsp(
    symbol: Dict[str, Any], unit: _CompiledUnit, host_source: str
) -> lsp.DocumentSymbol:
    symbol_range = _editor_span_range(symbol["span"], unit, host_source)
    selection_range = _editor_span_range(
        symbol["selection_span"], unit, host_source
    )
    identity = symbol["node_id"]
    if symbol.get("capture_id"):
        identity += f" · {symbol['capture_id']}"
    return lsp.DocumentSymbol(
        name=symbol["name"],
        detail=f"{symbol['kind']} · {identity}",
        kind=_SYMBOL_KINDS.get(symbol["kind"], lsp.SymbolKind.Object),
        range=symbol_range,
        selection_range=selection_range,
        children=[
            _editor_symbol_to_lsp(child, unit, host_source)
            for child in symbol.get("children", [])
        ],
    )


def _editor_symbol_count(symbols: List[Dict[str, Any]]) -> int:
    return sum(
        1 + _editor_symbol_count(symbol.get("children", [])) for symbol in symbols
    )


@server.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(
    ls: STRlingLanguageServer, params: lsp.DocumentSymbolParams
) -> List[lsp.DocumentSymbol]:
    """Return only canonical node/capture identities from the current snapshot."""
    uri = params.text_document.uri
    compiled = _snapshot_result_for_hover(ls, uri)
    if compiled is None:
        return []
    deadline = time.monotonic() + _EDITOR.timeout_seconds
    symbols: List[lsp.DocumentSymbol] = []
    symbol_count = 0
    for unit in compiled.units:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return []
        evidence = _project_editor_unit(
            compiled, unit, None, timeout_seconds=remaining
        )
        if evidence is None:
            continue
        unit_symbol_count = _editor_symbol_count(evidence["symbols"])
        if symbol_count + unit_symbol_count > MAX_SYMBOLS:
            return []
        symbol_count += unit_symbol_count
        symbols.extend(
            _editor_symbol_to_lsp(symbol, unit, compiled.snapshot.source)
            for symbol in evidence["symbols"]
        )
    return symbols


# --------------------------------------------------------------------------- #
# Go-to-definition: registry navigation                                       #
# --------------------------------------------------------------------------- #
#
# Capture navigation resolves only current canonical capture identities.
# Host member navigation resolves exact Simply operations and binding names to
# their authored protocol/registry declarations; trigger-keyword guessing is
# intentionally absent.


def _cursor_unit(
    compiled: _SnapshotResult, position: lsp.Position
) -> Tuple[Optional[_CompiledUnit], Optional[int], Optional[int]]:
    try:
        host_byte = position_to_byte_offset(
            compiled.snapshot.source,
            position.line,
            position.character,
            _POSITION_ENCODING,
        )
        host_utf32 = byte_offset_to_position(
            compiled.snapshot.source, host_byte, "utf-32"
        )
    except ValueError:
        return None, None, None
    for unit in compiled.units:
        if unit.island is None:
            return unit, host_byte, host_byte
        mapped = unit.island.from_host(host_utf32.line, host_utf32.character)
        if mapped is None:
            continue
        try:
            unit_byte = position_to_byte_offset(
                unit.source, mapped[0], mapped[1], "utf-32"
            )
        except ValueError:
            return None, None, host_byte
        return unit, unit_byte, host_byte
    return None, None, host_byte


def _capture_at(evidence: Dict[str, Any], cursor_byte: int) -> Optional[Dict[str, Any]]:
    for capture in evidence["captures"]:
        locations = [capture["declaration"], *capture["references"]]
        if any(
            int(location["start"]) <= cursor_byte < int(location["end"])
            for location in locations
        ):
            return capture
    return None


def _catalog_word(source: str, cursor_byte: int) -> Optional[str]:
    encoded = source.encode("utf-8")
    if not 0 <= cursor_byte <= len(encoded):
        return None
    start = cursor_byte
    while start > 0 and (
        chr(encoded[start - 1]).isalnum() or encoded[start - 1] == ord("_")
    ):
        start -= 1
    end = cursor_byte
    while end < len(encoded) and (
        chr(encoded[end]).isalnum() or encoded[end] == ord("_")
    ):
        end += 1
    if encoded[:start][-2:] != b"s." or start == end:
        return None
    try:
        return encoded[start:end].decode("ascii")
    except UnicodeDecodeError:
        return None


def _catalog_location(definition) -> lsp.Location:
    source = definition.path.read_text(encoding="utf-8")
    start, end = project_span(
        source, definition.start, definition.end, _POSITION_ENCODING
    )
    return lsp.Location(
        uri=definition.path.as_uri(),
        range=lsp.Range(
            start=lsp.Position(line=start.line, character=start.character),
            end=lsp.Position(line=end.line, character=end.character),
        ),
    )


@server.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(
    ls: STRlingLanguageServer, params: lsp.DefinitionParams
) -> Optional[lsp.Location]:
    """Resolve a canonical capture or governed host catalog identity."""
    uri = params.text_document.uri
    compiled = _snapshot_result_for_hover(ls, uri)
    if compiled is None:
        return None
    unit, cursor_byte, host_byte = _cursor_unit(compiled, params.position)
    if unit is not None and cursor_byte is not None:
        evidence = _project_editor_unit(compiled, unit, None)
        if evidence is None:
            return None
        capture = _capture_at(evidence, cursor_byte)
        if capture is None:
            return None
        return lsp.Location(
            uri=uri,
            range=_editor_span_range(
                capture["declaration"], unit, compiled.snapshot.source
            ),
        )
    if not _is_host_uri(uri) or host_byte is None:
        return None
    word = _catalog_word(compiled.snapshot.source, host_byte)
    binding_id = language_for_uri(uri)
    if word is None or binding_id is None:
        return None
    try:
        target = catalog_definition(word, binding_id=binding_id)
    except EditorServiceError:
        return None
    return None if target is None else _catalog_location(target)


@server.feature(lsp.TEXT_DOCUMENT_REFERENCES)
def references(
    ls: STRlingLanguageServer, params: lsp.ReferenceParams
) -> List[lsp.Location]:
    """Return current-source locations sharing one canonical capture identity."""
    uri = params.text_document.uri
    compiled = _snapshot_result_for_hover(ls, uri)
    if compiled is None:
        return []
    unit, cursor_byte, _ = _cursor_unit(compiled, params.position)
    if unit is None or cursor_byte is None:
        return []
    evidence = _project_editor_unit(compiled, unit, None)
    if evidence is None:
        return []
    capture = _capture_at(evidence, cursor_byte)
    if capture is None:
        return []
    spans = list(capture["references"])
    if params.context.include_declaration:
        spans.insert(0, capture["declaration"])
    return [
        lsp.Location(
            uri=uri,
            range=_editor_span_range(span, unit, compiled.snapshot.source),
        )
        for span in spans
    ]


# --------------------------------------------------------------------------- #
# Document formatting                                                         #
# --------------------------------------------------------------------------- #
#
# Only complete, native ``*.semantic.strling`` snapshots have a canonical
# formatter projection. Regex-compatible sources and host islands are
# intentionally non-formatting surfaces.


@server.feature(lsp.TEXT_DOCUMENT_FORMATTING)
def formatting(
    ls: STRlingLanguageServer, params: lsp.DocumentFormattingParams
) -> List[lsp.TextEdit]:
    """Return one canonical full-document Semantic formatting edit."""
    uri = params.text_document.uri
    compiled = _snapshot_result_for_hover(ls, uri)
    if compiled is None or len(compiled.units) != 1:
        return []
    unit = compiled.units[0]
    if unit.frontend != "semantic" or unit.island is not None:
        return []
    evidence = _project_editor_unit(compiled, unit, None)
    if evidence is None:
        return []
    formatted = evidence.get("formatted_source")
    if not isinstance(formatted, str) or formatted == compiled.snapshot.source:
        return []
    return [
        lsp.TextEdit(
            range=_editor_span_range(
                {"start": 0, "end": len(compiled.snapshot.source.encode("utf-8"))},
                unit,
                compiled.snapshot.source,
            ),
            new_text=formatted,
        )
    ]


@server.feature(lsp.INITIALIZE)
def initialize(ls: STRlingLanguageServer, params: lsp.InitializeParams) -> None:
    """Negotiate position encoding and explicit target-profile identity."""
    capabilities = getattr(params, "capabilities", None) or {}
    if isinstance(capabilities, dict):
        general = capabilities.get("general") or {}
        offered = (
            general.get("positionEncodings") or general.get("position_encodings") or []
        )
    else:
        general = getattr(capabilities, "general", None)
        offered = getattr(general, "position_encodings", []) if general else []
    encoding = next(
        (
            str(candidate)
            for candidate in offered
            if str(candidate) in {"utf-8", "utf-16", "utf-32"}
        ),
        "utf-16",
    )

    initialization_options = getattr(params, "initialization_options", None) or {}
    target_profile = None
    if isinstance(initialization_options, dict):
        candidate = initialization_options.get(
            "targetProfile"
        ) or initialization_options.get("target_profile")
        if isinstance(candidate, str) and candidate:
            target_profile = candidate
    _set_session_options(
        position_encoding=encoding,
        target_profile=target_profile,
    )
    setattr(ls, "position_encoding", encoding)
    protocol = getattr(ls, "protocol", None)
    server_capabilities = getattr(protocol, "server_capabilities", None)
    if server_capabilities is not None and hasattr(
        server_capabilities, "position_encoding"
    ):
        server_capabilities.position_encoding = encoding
    _log_message(
        ls,
        f"STRling Language Server initialized (position encoding {encoding})",
    )


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
