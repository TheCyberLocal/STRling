"""Minimal local ``pygls``-compatible transport used by the VS Code extension.

This shim mirrors the bundled test transport used elsewhere in the repo. It
provides a working stdio/TCP JSON-RPC loop, publishes diagnostics, and answers
initialize with the capabilities STRling advertises so the extension no longer
depends on an externally installed ``pygls`` package.
"""

from __future__ import annotations

import json
import socket
import sys
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any, Callable, Dict, IO, List, Optional


def _snake_to_camel(name: str) -> str:
    parts = name.split("_")
    if len(parts) == 1:
        return name
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _to_json(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return {
            _snake_to_camel(field.name): _to_json(getattr(value, field.name))
            for field in fields(value)
            if getattr(value, field.name) is not None
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _to_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json(item) for item in value]
    return value


class _WorkspaceDocument:
    def __init__(
        self, uri: str, source: str = "", language_id: Optional[str] = None
    ) -> None:
        self.uri = uri
        self.source = source
        self.language_id = language_id


class _Workspace:
    def __init__(self) -> None:
        self._documents: Dict[str, _WorkspaceDocument] = {}

    def upsert(
        self, uri: str, source: str = "", language_id: Optional[str] = None
    ) -> None:
        self._documents[uri] = _WorkspaceDocument(uri, source, language_id)

    def get_text_document(self, uri: str) -> _WorkspaceDocument:
        document = self._documents.get(uri)
        if document is not None:
            return document

        source = ""
        if uri.startswith("file://"):
            try:
                from urllib.parse import unquote
                from urllib.request import url2pathname

                path = url2pathname(unquote(uri[len("file://") :]))
                with open(path, "r", encoding="utf-8") as handle:
                    source = handle.read()
            except OSError:
                source = ""

        document = _WorkspaceDocument(uri=uri, source=source)
        self._documents[uri] = document
        return document


class JsonRPCServer:
    """Minimal JsonRPCServer shim for the extension runtime."""

    def __init__(self, protocol_cls: Any = None, converter_factory: Any = None) -> None:
        self._features: Dict[str, List[Callable[..., Any]]] = {}
        self._feature_options: Dict[str, Any] = {}
        self.workspace = _Workspace()
        self._stdin: Optional[IO[bytes]] = None
        self._stdout: Optional[IO[bytes]] = None
        self._running = False
        self._shutdown_requested = False
        self._next_id = 0

    def feature(
        self, name: str, options: Any = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._features.setdefault(name, []).append(func)
            if options is not None:
                self._feature_options[name] = options
            return func

        return decorator

    def start_tcp(self, host: str, port: int) -> None:
        with socket.create_server((host, port), reuse_port=False) as listener:
            connection, _addr = listener.accept()
            with connection:
                self._serve(connection.makefile("rb"), connection.makefile("wb"))

    def start_io(self) -> None:
        self._serve(sys.stdin.buffer, sys.stdout.buffer)

    def show_message_log(self, msg: str) -> None:
        self._notify("window/logMessage", {"type": 4, "message": msg})

    def text_document_publish_diagnostics(self, params: Any) -> None:
        self._notify("textDocument/publishDiagnostics", _to_json(params))

    def _serve(self, stdin: IO[bytes], stdout: IO[bytes]) -> None:
        self._stdin = stdin
        self._stdout = stdout
        self._running = True
        try:
            while self._running and not self._shutdown_requested:
                message = self._read_message(stdin)
                if message is None:
                    break
                self._handle_message(message)
        finally:
            try:
                stdout.flush()
            except Exception:
                pass

    def _read_message(self, stdin: IO[bytes]) -> Optional[Dict[str, Any]]:
        headers: Dict[str, str] = {}
        while True:
            line = stdin.readline()
            if not line:
                return None
            if line in (b"\r\n", b"\n"):
                break
            try:
                key, value = line.decode("utf-8", errors="replace").split(":", 1)
            except ValueError:
                continue
            headers[key.strip().lower()] = value.strip()

        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        raw = stdin.read(length)
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))

    def _handle_message(self, message: Dict[str, Any]) -> None:
        method = message.get("method")
        if method is None:
            return

        message_id = message.get("id")
        params = message.get("params") or {}

        if method == "shutdown":
            self._shutdown_requested = True
            self._respond(message_id, None)
            return

        if method == "exit":
            self._running = False
            return

        if method == "initialize":
            from lsprotocol import types as lsp

            if message_id is not None:
                self._respond(message_id, self._initialize_result())
            handlers = self._features.get(lsp.INITIALIZE, [])
            for handler in handlers:
                try:
                    handler(self, self._coerce_params(method, params))
                except Exception as exc:
                    self.show_message_log(f"initialize handler failed: {exc}")
            return

        if method in ("initialized",):
            return

        from lsprotocol import types as lsp

        if method == lsp.TEXT_DOCUMENT_DID_OPEN:
            self._handle_did_open(params)
            return
        if method == lsp.TEXT_DOCUMENT_DID_CHANGE:
            self._handle_did_change(params)
            return
        if method == lsp.TEXT_DOCUMENT_DID_SAVE:
            self._handle_did_save(params)
            return

        handlers = self._features.get(method, [])
        if not handlers:
            if message_id is not None:
                self._respond_error(message_id, -32601, f"Method not found: {method}")
            return

        handler = handlers[0]
        coerced = self._coerce_params(method, params)
        try:
            result = handler(self, coerced)
            if message_id is not None:
                self._respond(message_id, result)
        except Exception as exc:
            if message_id is not None:
                self._respond_error(message_id, -32603, str(exc))

    def _handle_did_open(self, params: Dict[str, Any]) -> None:
        from lsprotocol import types as lsp

        text_document = params.get("textDocument") or params.get("text_document") or {}
        uri = str(text_document.get("uri", ""))
        source = str(text_document.get("text") or text_document.get("source") or "")
        language_id = text_document.get("languageId") or text_document.get(
            "language_id"
        )
        self.workspace.upsert(uri, source, language_id)
        handler = self._features.get(lsp.TEXT_DOCUMENT_DID_OPEN, [])
        if handler:
            handler[0](self, self._coerce_params(lsp.TEXT_DOCUMENT_DID_OPEN, params))

    def _handle_did_change(self, params: Dict[str, Any]) -> None:
        from lsprotocol import types as lsp

        text_document = params.get("textDocument") or params.get("text_document") or {}
        uri = str(text_document.get("uri", ""))
        document = self.workspace.get_text_document(uri)
        changes = params.get("contentChanges") or params.get("content_changes") or []
        if changes:
            first_change = changes[0] or {}
            if isinstance(first_change, dict):
                document.source = str(first_change.get("text", document.source))
        elif "text" in text_document:
            document.source = str(text_document.get("text") or document.source)
        handler = self._features.get(lsp.TEXT_DOCUMENT_DID_CHANGE, [])
        if handler:
            handler[0](self, self._coerce_params(lsp.TEXT_DOCUMENT_DID_CHANGE, params))

    def _handle_did_save(self, params: Dict[str, Any]) -> None:
        from lsprotocol import types as lsp

        text_document = params.get("textDocument") or params.get("text_document") or {}
        uri = str(text_document.get("uri", ""))
        if uri:
            document = self.workspace.get_text_document(uri)
            source = text_document.get("text") or text_document.get("source")
            if source is not None:
                document.source = str(source)
        handler = self._features.get(lsp.TEXT_DOCUMENT_DID_SAVE, [])
        if handler:
            handler[0](self, self._coerce_params(lsp.TEXT_DOCUMENT_DID_SAVE, params))

    def _coerce_params(self, method: str, params: Dict[str, Any]) -> Any:
        from lsprotocol import types as lsp

        text_document_data = (
            params.get("textDocument") or params.get("text_document") or {}
        )
        text_document = lsp.TextDocument(
            uri=str(text_document_data.get("uri", "")),
            text=text_document_data.get("text") or text_document_data.get("source"),
            language_id=text_document_data.get("languageId")
            or text_document_data.get("language_id"),
        )

        if method == "initialize":
            return lsp.InitializeParams()
        if method == lsp.TEXT_DOCUMENT_DID_OPEN:
            return lsp.DidOpenTextDocumentParams(text_document=text_document)
        if method == lsp.TEXT_DOCUMENT_DID_CHANGE:
            return lsp.DidChangeTextDocumentParams(text_document=text_document)
        if method == lsp.TEXT_DOCUMENT_DID_SAVE:
            return lsp.DidSaveTextDocumentParams(text_document=text_document)
        if method == lsp.TEXT_DOCUMENT_HOVER:
            position = params.get("position") or {}
            return lsp.HoverParams(
                text_document=text_document,
                position=lsp.Position(
                    line=int(position.get("line", 0)),
                    character=int(position.get("character", 0)),
                ),
            )
        if method == lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL:
            return lsp.DocumentSymbolParams(text_document=text_document)
        if method == lsp.TEXT_DOCUMENT_DEFINITION:
            position = params.get("position") or {}
            return lsp.DefinitionParams(
                text_document=text_document,
                position=lsp.Position(
                    line=int(position.get("line", 0)),
                    character=int(position.get("character", 0)),
                ),
            )
        if method == lsp.TEXT_DOCUMENT_COMPLETION:
            position = params.get("position") or {}
            return lsp.CompletionParams(
                text_document=text_document,
                position=lsp.Position(
                    line=int(position.get("line", 0)),
                    character=int(position.get("character", 0)),
                ),
            )
        if method == lsp.TEXT_DOCUMENT_CODE_ACTION:
            range_data = params.get("range") or {}
            context_data = params.get("context") or {}
            diagnostics = [
                self._coerce_diagnostic(item)
                for item in context_data.get("diagnostics", [])
            ]
            return lsp.CodeActionParams(
                text_document=text_document,
                range=self._coerce_range(range_data),
                context=lsp.CodeActionContext(
                    diagnostics=diagnostics,
                    only=context_data.get("only"),
                    trigger_kind=context_data.get("triggerKind")
                    or context_data.get("trigger_kind"),
                ),
            )
        if method == lsp.TEXT_DOCUMENT_FORMATTING:
            options = params.get("options") or {}
            return lsp.DocumentFormattingParams(
                text_document=text_document,
                options=lsp.FormattingOptions(
                    tab_size=int(options.get("tabSize", options.get("tab_size", 4))),
                    insert_spaces=bool(
                        options.get("insertSpaces", options.get("insert_spaces", True))
                    ),
                ),
            )
        return params

    def _coerce_range(self, range_data: Dict[str, Any]) -> Any:
        from lsprotocol import types as lsp

        start = range_data.get("start") or {}
        end = range_data.get("end") or {}
        return lsp.Range(
            start=lsp.Position(
                line=int(start.get("line", 0)), character=int(start.get("character", 0))
            ),
            end=lsp.Position(
                line=int(end.get("line", 0)), character=int(end.get("character", 0))
            ),
        )

    def _coerce_diagnostic(self, item: Dict[str, Any]) -> Any:
        from lsprotocol import types as lsp

        return lsp.Diagnostic(
            range=self._coerce_range(item.get("range") or {}),
            message=str(item.get("message", "")),
            severity=item.get("severity"),
            source=item.get("source"),
            code=item.get("code"),
            data=item.get("data"),
        )

    def _initialize_result(self) -> Dict[str, Any]:
        capabilities: Dict[str, Any] = {
            "textDocumentSync": 2,
        }
        for method, handlers in self._features.items():
            if not handlers:
                continue
            options = self._feature_options.get(method)
            if method.endswith("/hover"):
                capabilities["hoverProvider"] = True
            elif method.endswith("/semanticTokens/full"):
                legend = _to_json(options) if options is not None else None
                capabilities["semanticTokensProvider"] = {
                    "legend": legend,
                    "full": True,
                }
            elif method.endswith("/completion"):
                capabilities["completionProvider"] = _to_json(options) or {}
            elif method.endswith("/codeAction"):
                capabilities["codeActionProvider"] = _to_json(options) or True
            elif method.endswith("/documentSymbol"):
                capabilities["documentSymbolProvider"] = True
            elif method.endswith("/definition"):
                capabilities["definitionProvider"] = True
            elif method.endswith("/formatting"):
                capabilities["documentFormattingProvider"] = True
        return {
            "capabilities": capabilities,
            "serverInfo": {
                "name": getattr(self, "name", "pygls-shim"),
                "version": getattr(self, "version", "0.0.0"),
            },
        }

    def _respond(self, message_id: Any, result: Any) -> None:
        self._write_message(
            {"jsonrpc": "2.0", "id": message_id, "result": _to_json(result)}
        )

    def _respond_error(self, message_id: Any, code: int, message: str) -> None:
        self._write_message(
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {"code": code, "message": message},
            }
        )

    def _notify(self, method: str, params: Any) -> None:
        self._write_message(
            {"jsonrpc": "2.0", "method": method, "params": _to_json(params)}
        )

    def _write_message(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        message = (
            b"Content-Length: " + str(len(data)).encode("ascii") + b"\r\n\r\n" + data
        )
        stdout = self._stdout or sys.stdout.buffer
        stdout.write(message)
        stdout.flush()
