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
    - Deferred Intelligence (``server.deferred_intelligence``) ← isolates
      completion/navigation/token/formatting compatibility until P16-T03/T04.

Usage:
    python server/server.py [--tcp]
    python server/server.py --stdio (default)
"""

import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
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


def _find_python_binding_src() -> Optional[str]:
    """Return the in-repo Python binding source directory when available."""
    candidates = [
        os.path.realpath(os.path.join(_SERVER_DIR, "..", "..")),
        os.path.realpath(os.path.join(_SERVER_DIR, "..", "..", "..")),
    ]
    for repo_root in candidates:
        python_src = os.path.join(repo_root, "bindings", "python", "src")
        if os.path.isdir(python_src):
            return python_src
    return None


_PYTHON_SRC = _find_python_binding_src()
if _PYTHON_SRC is not None and _PYTHON_SRC not in sys.path:
    sys.path.insert(0, _PYTHON_SRC)


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
        f"Resolved STRling Python source: {_PYTHON_SRC or '<not found>'}\n"
        f"Current working directory: {os.getcwd()}\n"
        f"Python executable: {sys.executable}\n"
        f"PYTHONPATH env: {os.environ.get('PYTHONPATH', '<unset>')}\n"
        "sys.path matrix:\n"
        f"{_format_sys_path_matrix()}\n"
        "Next step: rebuild the extension dist folder so dist/server/libs contains "
        "pygls, lsprotocol, and the STRling Python binding before relaunching the server.\n"
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

# Make the in-tree Python binding importable when running the LSP server
# directly out of the repository (the common development path). Production
# installs that already have ``STRling`` on ``sys.path`` are unaffected
# because :func:`Path.insert` is idempotent for duplicate entries here.
_PYTHON_SRC_PATH = Path(_PYTHON_SRC) if _PYTHON_SRC is not None else None
if (
    _PYTHON_SRC_PATH is not None
    and _PYTHON_SRC_PATH.is_dir()
    and str(_PYTHON_SRC_PATH) not in sys.path
):
    sys.path.insert(0, str(_PYTHON_SRC_PATH))

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
        from .deferred_intelligence import (
            SEMANTIC_TOKEN_MODIFIERS,
            SEMANTIC_TOKEN_TYPES,
            extract_document_symbols,
            find_registry_definition,
            format_pattern,
            get_completion_items,
            tokenize_pattern,
        )
        from .island_extractor import (
            Island,
            extract_islands_for_uri,
            language_for_uri,
        )
    except ImportError:
        from canonical_core import (  # type: ignore[no-redef]
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
        from deferred_intelligence import (  # type: ignore[no-redef]
            SEMANTIC_TOKEN_MODIFIERS,
            SEMANTIC_TOKEN_TYPES,
            extract_document_symbols,
            find_registry_definition,
            format_pattern,
            get_completion_items,
            tokenize_pattern,
        )
        from island_extractor import (  # type: ignore[no-redef]
            Island,
            extract_islands_for_uri,
            language_for_uri,
        )
except ImportError as import_error:
    _exit_with_import_context("its canonical/deferred editor adapters", import_error)


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


def _word_at(text: str, character: int) -> Optional[str]:
    """Return the host identifier under a cursor for deferred navigation."""
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
