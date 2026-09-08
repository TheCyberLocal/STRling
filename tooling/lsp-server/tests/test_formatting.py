"""Canonical Semantic formatting coverage for the STRling LSP."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest


LSP_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    LSP_ROOT / "tests" / "fixtures" / "canonical-actions-islands" / "manifest.json"
)
if str(LSP_ROOT) not in sys.path:
    sys.path.insert(0, str(LSP_ROOT))


def _cases() -> list[dict[str, Any]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["formatting_cases"]


class _Document:
    def __init__(self, source: str, version: int = 1) -> None:
        self.source = source
        self.version = version


class _Workspace:
    def __init__(self, uri: str, source: str) -> None:
        self.documents = {uri: _Document(source)}

    def get_text_document(self, uri: str) -> _Document:
        return self.documents[uri]


@pytest.fixture
def server_module():
    from server import server as module

    with module._STATE_LOCK:
        module._ISLANDS_BY_URI.clear()
        module._LAST_DIAGNOSTICS.clear()
        module._CANONICAL_RESULTS_BY_URI.clear()
        module._SNAPSHOTS_BY_URI.clear()
        module._RESULT_CACHE.clear()
        module._RESULT_CACHE_ORDER.clear()
        module._EDITOR_CACHE.clear()
        module._EDITOR_CACHE_ORDER.clear()
    return module


@pytest.fixture
def lsp_module():
    from lsprotocol import types as lsp

    return lsp


def _uri(case: dict[str, Any]) -> str:
    suffix = {
        "semantic": ".strling",
        "regex": ".strl",
        "host_regex_island": ".py",
    }[case["frontend"]]
    return f"file:///formatting/{case['id']}{suffix}"


def test_native_extension_routes_follow_current_frontend_policy(
    server_module: Any,
) -> None:
    assert server_module._frontend_for_uri("file:///pattern.strling") == "semantic"
    assert (
        server_module._frontend_for_uri("file:///pattern.semantic.strling")
        == "semantic"
    )
    assert server_module._frontend_for_uri("file:///legacy.strl") == "regex"


def _compile_current(module: Any, uri: str, source: str) -> Any:
    module.server.workspace = _Workspace(uri, source)
    snapshot = module._capture_snapshot(module.server, uri, 1)
    compiled = module._compile_snapshot(snapshot)
    with module._STATE_LOCK:
        module._CANONICAL_RESULTS_BY_URI[uri] = compiled
    return compiled


def _params(lsp: Any, uri: str) -> Any:
    return lsp.DocumentFormattingParams(
        text_document=lsp.TextDocument(uri=uri),
        options=lsp.FormattingOptions(tab_size=8, insert_spaces=False),
    )


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
def test_formatting_matches_closed_canonical_disposition(
    server_module: Any, lsp_module: Any, case: dict[str, Any]
) -> None:
    uri = _uri(case)
    compiled = _compile_current(server_module, uri, case["source"])
    edits = server_module.formatting(server_module.server, _params(lsp_module, uri))

    if case["disposition"] == "one_full_document_edit":
        assert len(edits) == 1
        edit = edits[0]
        assert edit.new_text == case["expected"]
        assert edit.range.start == lsp_module.Position(line=0, character=0)
        expected_end = server_module.byte_offset_to_position(
            case["source"],
            len(case["source"].encode("utf-8")),
            compiled.snapshot.position_encoding,
        )
        assert edit.range.end == lsp_module.Position(
            line=expected_end.line, character=expected_end.character
        )
    else:
        assert edits == []


def test_stale_semantic_snapshot_returns_no_formatting_edit(
    server_module: Any, lsp_module: Any
) -> None:
    case = next(
        case for case in _cases() if case["id"] == "format.semantic.canonicalize"
    )
    uri = _uri(case)
    _compile_current(server_module, uri, case["source"])
    server_module.server.workspace.documents[uri].source = case["source"] + "\n"

    assert (
        server_module.formatting(server_module.server, _params(lsp_module, uri)) == []
    )
