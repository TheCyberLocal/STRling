#!/usr/bin/env python3
"""Exercise every certified editor feature through a packaged LSP process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping


class EvidenceError(RuntimeError):
    pass


class JsonRpcClient:
    def __init__(self, command: list[str], *, cwd: Path, env: Mapping[str, str]):
        self.process = subprocess.Popen(
            command,
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self.backlog: list[dict[str, Any]] = []
        self.next_id = 1
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        assert self.process.stdout is not None
        try:
            while True:
                headers: dict[str, str] = {}
                while True:
                    line = self.process.stdout.readline()
                    if not line:
                        return
                    if line in {b"\r\n", b"\n"}:
                        break
                    name, value = line.decode("ascii").split(":", 1)
                    headers[name.lower()] = value.strip()
                length = int(headers["content-length"])
                body = self.process.stdout.read(length)
                message = json.loads(body.decode("utf-8"))
                if isinstance(message, dict):
                    self.messages.put(message)
        except BaseException as error:  # pragma: no cover - process forensics
            self.messages.put({"_reader_error": repr(error)})

    def _send(self, message: Mapping[str, Any]) -> None:
        assert self.process.stdin is not None
        body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.process.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode())
        self.process.stdin.write(body)
        self.process.stdin.flush()

    def _matching(
        self, predicate: Callable[[dict[str, Any]], bool], timeout: float = 15.0
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            for index, message in enumerate(self.backlog):
                if predicate(message):
                    return self.backlog.pop(index)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stderr = b""
                if self.process.poll() is not None and self.process.stderr is not None:
                    stderr = self.process.stderr.read()
                raise EvidenceError(
                    "timed out waiting for LSP evidence"
                    + (f": {stderr.decode(errors='replace')}" if stderr else "")
                )
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty as error:
                raise EvidenceError("timed out waiting for LSP evidence") from error
            if "_reader_error" in message:
                raise EvidenceError(str(message["_reader_error"]))
            if predicate(message):
                return message
            self.backlog.append(message)

    def request(self, method: str, params: Mapping[str, Any]) -> Any:
        identifier = self.next_id
        self.next_id += 1
        self._send(
            {
                "jsonrpc": "2.0",
                "id": identifier,
                "method": method,
                "params": params,
            }
        )
        message = self._matching(lambda item: item.get("id") == identifier)
        if "error" in message:
            raise EvidenceError(f"{method} failed: {message['error']}")
        return message.get("result")

    def notify(self, method: str, params: Mapping[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def wait_notification(
        self, method: str, predicate: Callable[[Any], bool] | None = None
    ) -> Any:
        message = self._matching(
            lambda item: (
                item.get("method") == method
                and (predicate is None or predicate(item.get("params")))
            )
        )
        return message.get("params")

    def close(self) -> None:
        try:
            self.request("shutdown", {})
            self.notify("exit", {})
            self.process.wait(timeout=5.0)
        except BaseException:
            self.process.terminate()
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5.0)


def _sha(value: object) -> str:
    data = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _environment(payload: Path, suffix: str) -> dict[str, str]:
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONPATH": str(payload / "server" / "libs"),
            "STRLING_KERNEL": str(
                payload / "server" / "bin" / f"strling-kernel{suffix}"
            ),
            "STRLING_EDITOR_CORE": str(
                payload / "server" / "bin" / f"strling-editor-core{suffix}"
            ),
            "STRLING_SIMPLY_PROTOCOL_PATH": str(
                payload / "server" / "resources" / "simply-protocol.json"
            ),
            "STRLING_STDLIB_REGISTRY_PATH": str(
                payload / "server" / "resources" / "stdlib-registry.json"
            ),
            "STRLING_ISLAND_BOUNDARIES_PATH": str(
                payload / "server" / "resources" / "island-boundaries.json"
            ),
        }
    )
    return environment


def _open(client: JsonRpcClient, uri: str, language: str, source: str) -> list[dict]:
    client.notify(
        "textDocument/didOpen",
        {
            "textDocument": {
                "uri": uri,
                "languageId": language,
                "version": 1,
                "text": source,
            }
        },
    )
    publication = client.wait_notification(
        "textDocument/publishDiagnostics",
        lambda params: isinstance(params, dict) and params.get("uri") == uri,
    )
    if not isinstance(publication, dict) or not isinstance(
        publication.get("diagnostics"), list
    ):
        raise EvidenceError(f"{uri} did not publish diagnostics")
    return publication["diagnostics"]


def _kernel_compile(
    payload: Path, environment: Mapping[str, str], source: str, frontend: str
) -> dict[str, Any]:
    command = [
        environment["STRLING_KERNEL"],
        "import" if frontend == "regex" else "compile",
        "--input",
        "-",
        "--output",
        "semantic",
        "--output",
        "analysis",
        "--partial-semantics",
        "allow_for_diagnostics",
        "--max-diagnostics",
        "256",
        "--format",
        "json",
    ]
    if frontend == "semantic":
        command.extend(["--frontend", "semantic"])
    completed = subprocess.run(
        command,
        cwd=payload,
        env=dict(environment),
        input=source.encode("utf-8"),
        capture_output=True,
        check=False,
        timeout=30.0,
    )
    if completed.returncode not in {0, 2} or completed.stderr:
        raise EvidenceError(
            f"packaged kernel failed: {completed.stderr.decode(errors='replace')}"
        )
    return json.loads(completed.stdout.decode("utf-8"))


def execute(payload: Path, target: str) -> dict[str, Any]:
    payload = payload.resolve()
    suffix = ".exe" if target.startswith("win32-") else ""
    environment = _environment(payload, suffix)
    client = JsonRpcClient(
        [sys.executable, str(payload / "server" / "server.py"), "--stdio"],
        cwd=payload,
        env=environment,
    )
    try:
        initialize = client.request(
            "initialize",
            {
                "processId": None,
                "rootUri": None,
                "capabilities": {"general": {"positionEncodings": ["utf-16"]}},
                "initializationOptions": {
                    "features": {
                        "hover": True,
                        "semanticTokens": True,
                        "completion": True,
                        "codeAction": True,
                        "documentSymbol": True,
                        "definition": True,
                        "references": True,
                        "formatting": True,
                    }
                },
            },
        )
        client.notify("initialized", {})
        if not isinstance(initialize, dict):
            raise EvidenceError("initialize returned no capabilities")

        regex_source = "(?<word>é+)x\\k<word>"
        regex_uri = "file:///packaged/capture.strl"
        regex_diagnostics = _open(client, regex_uri, "strling", regex_source)
        hover = client.request(
            "textDocument/hover",
            {
                "textDocument": {"uri": regex_uri},
                "position": {"line": 0, "character": 4},
            },
        )
        reference_character = regex_source.rindex("word") + 1
        definition = client.request(
            "textDocument/definition",
            {
                "textDocument": {"uri": regex_uri},
                "position": {"line": 0, "character": reference_character},
            },
        )
        references = client.request(
            "textDocument/references",
            {
                "textDocument": {"uri": regex_uri},
                "position": {"line": 0, "character": 4},
                "context": {"includeDeclaration": True},
            },
        )
        symbols = client.request(
            "textDocument/documentSymbol", {"textDocument": {"uri": regex_uri}}
        )
        tokens = client.request(
            "textDocument/semanticTokens/full",
            {"textDocument": {"uri": regex_uri}},
        )

        completion_source = "semantic strling 1.0;\ncase sensitive;\npattern se"
        completion_uri = "file:///packaged/completion.semantic.strling"
        _open(client, completion_uri, "strling", completion_source)
        completion = client.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": completion_uri},
                "position": {"line": 2, "character": len("pattern se")},
            },
        )

        semantic_source = (
            "semantic strling 1.0; case sensitive; "
            'pattern repeat from 1 to 1 using greedy { text "a"; }'
        )
        semantic_uri = "file:///packaged/action.semantic.strling"
        semantic_diagnostics = _open(client, semantic_uri, "strling", semantic_source)
        quality = next(
            (
                diagnostic
                for diagnostic in semantic_diagnostics
                if diagnostic.get("code") == "STRL-QUALITY-0002"
            ),
            None,
        )
        if quality is None:
            raise EvidenceError("packaged semantic source has no certified diagnostic")
        actions = client.request(
            "textDocument/codeAction",
            {
                "textDocument": {"uri": semantic_uri},
                "range": quality["range"],
                "context": {"diagnostics": [quality]},
            },
        )
        formatting = client.request(
            "textDocument/formatting",
            {
                "textDocument": {"uri": semantic_uri},
                "options": {"tabSize": 4, "insertSpaces": True},
            },
        )

        host_source = 'pattern = s.parse("é+")\n'
        host_uri = "file:///packaged/island.py"
        host_diagnostics = _open(client, host_uri, "python", host_source)
        host_tokens = client.request(
            "textDocument/semanticTokens/full",
            {"textDocument": {"uri": host_uri}},
        )

        canonical = _kernel_compile(payload, environment, semantic_source, "semantic")
        canonical_codes = [item["code"] for item in canonical["diagnostics"]]
        lsp_codes = [item["code"] for item in semantic_diagnostics]
        if canonical_codes != lsp_codes:
            raise EvidenceError(
                f"LSP/kernel diagnostics differ: {lsp_codes} != {canonical_codes}"
            )
        if regex_diagnostics:
            raise EvidenceError("valid packaged regex unexpectedly has diagnostics")
        if not hover or not definition or len(references or []) != 2:
            raise EvidenceError("packaged hover/navigation evidence is incomplete")
        if not symbols or not isinstance(tokens, dict) or not tokens.get("data"):
            raise EvidenceError("packaged symbol/token evidence is incomplete")
        completion_items = (
            completion.get("items", []) if isinstance(completion, dict) else completion
        )
        if not any(item.get("label") == "sequence" for item in completion_items or []):
            raise EvidenceError("packaged completion evidence is incomplete")
        if len(actions or []) != 1 or len(formatting or []) != 1:
            raise EvidenceError("packaged action/formatting evidence is incomplete")
        if (
            host_diagnostics
            or not isinstance(host_tokens, dict)
            or not host_tokens.get("data")
        ):
            raise EvidenceError("packaged island evidence is incomplete")

        features = {
            "diagnostics": len(semantic_diagnostics),
            "hover": 1,
            "completion": len(completion_items or []),
            "definition": 1,
            "references": len(references),
            "document_symbols": len(symbols),
            "semantic_tokens": len(tokens["data"]),
            "code_actions": len(actions),
            "formatting": len(formatting),
            "embedded_islands": len(host_tokens["data"]),
        }
        return {
            "status": "passed",
            "target": target,
            "features": features,
            "canonical_diagnostic_codes": canonical_codes,
            "canonical_result_fingerprint": _sha(canonical),
            "lsp_evidence_fingerprint": _sha(features),
        }
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    try:
        result = execute(args.payload, args.target)
    except (EvidenceError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"packaged runtime evidence failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
