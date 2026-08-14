"""Certified canonical code-action coverage for the STRling LSP."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest


LSP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = LSP_ROOT.parents[1]
MANIFEST_PATH = (
    LSP_ROOT / "tests" / "fixtures" / "canonical-actions-islands" / "manifest.json"
)
if str(LSP_ROOT) not in sys.path:
    sys.path.insert(0, str(LSP_ROOT))


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _case(identifier: str) -> dict[str, Any]:
    return next(
        case for case in _manifest()["action_cases"] if case["id"] == identifier
    )


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


def _compile_current(module: Any, uri: str, source: str) -> Any:
    module.server.workspace = _Workspace(uri, source)
    snapshot = module._capture_snapshot(module.server, uri, 1)
    compiled = module._compile_snapshot(snapshot)
    with module._STATE_LOCK:
        module._CANONICAL_RESULTS_BY_URI[uri] = compiled
    return compiled


def _request(lsp: Any, uri: str, request_range: Any, diagnostics: list[Any]) -> Any:
    return lsp.CodeActionParams(
        text_document=lsp.TextDocument(uri=uri),
        range=request_range,
        context=lsp.CodeActionContext(diagnostics=diagnostics),
    )


def test_only_certified_refactor_rewrites_are_advertised(
    server_module: Any, lsp_module: Any
) -> None:
    options = server_module.server._feature_options[
        lsp_module.TEXT_DOCUMENT_CODE_ACTION
    ]
    assert options.code_action_kinds == [lsp_module.CodeActionKind.RefactorRewrite]


def test_exact_current_semantic_diagnostic_materializes_certified_edit(
    server_module: Any, lsp_module: Any
) -> None:
    case = _case("action.semantic.greedy")
    uri = "file:///actions/positive.semantic.strling"
    compiled = _compile_current(server_module, uri, case["source"])
    diagnostic = next(
        item for item in compiled.diagnostics if item.code == case["diagnostic_code"]
    )

    actions = server_module.code_action(
        server_module.server,
        _request(lsp_module, uri, diagnostic.range, [diagnostic]),
    )

    assert len(actions) == 1
    action = actions[0]
    assert action.kind == lsp_module.CodeActionKind.RefactorRewrite
    assert action.is_preferred is False
    assert action.diagnostics == [diagnostic]
    edit = action.edit.changes[uri][0]
    assert edit.range == diagnostic.range
    assert edit.new_text == case["replacement_text"]


def test_nested_exact_once_nodes_remain_independent_single_edits(
    server_module: Any, lsp_module: Any
) -> None:
    case = _case("action.semantic.nested_outer")
    uri = "file:///actions/nested.semantic.strling"
    compiled = _compile_current(server_module, uri, case["source"])
    diagnostics = [
        item for item in compiled.diagnostics if item.code == "STRL-QUALITY-0002"
    ]
    whole_document = lsp_module.Range(
        start=lsp_module.Position(line=0, character=0),
        end=lsp_module.Position(line=20, character=0),
    )

    actions = server_module.code_action(
        server_module.server,
        _request(lsp_module, uri, whole_document, diagnostics),
    )

    assert len(actions) == 2
    edits = [action.edit.changes[uri] for action in actions]
    assert all(len(group) == 1 for group in edits)
    assert len({group[0].range.start.character for group in edits}) == 2


@pytest.mark.parametrize(
    "identifier,uri",
    [
        ("action.refuse.regex_exact", "file:///actions/refuse.strl"),
        ("action.refuse.redos", "file:///actions/redos.strl"),
        ("action.refuse.safety_code", "file:///actions/safety.semantic.strling"),
        ("action.refuse.comment_loss", "file:///actions/comment.semantic.strling"),
        ("action.refuse.malformed", "file:///actions/malformed.semantic.strling"),
    ],
)
def test_unproved_frontends_shapes_and_source_loss_return_no_action(
    server_module: Any, lsp_module: Any, identifier: str, uri: str
) -> None:
    case = _case(identifier)
    compiled = _compile_current(server_module, uri, case["source"])
    diagnostics = list(compiled.diagnostics)
    request_range = (
        diagnostics[0].range
        if diagnostics
        else lsp_module.Range(
            start=lsp_module.Position(line=0, character=0),
            end=lsp_module.Position(line=20, character=0),
        )
    )
    assert (
        server_module.code_action(
            server_module.server,
            _request(lsp_module, uri, request_range, diagnostics),
        )
        == []
    )


def test_empty_mismatched_stale_and_host_contexts_fail_closed(
    server_module: Any, lsp_module: Any
) -> None:
    case = _case("action.semantic.greedy")
    uri = "file:///actions/refusal.semantic.strling"
    compiled = _compile_current(server_module, uri, case["source"])
    diagnostic = compiled.diagnostics[0]

    assert (
        server_module.code_action(
            server_module.server,
            _request(lsp_module, uri, diagnostic.range, []),
        )
        == []
    )

    mismatched = lsp_module.Diagnostic(
        range=diagnostic.range,
        message=diagnostic.message,
        severity=diagnostic.severity,
        source=diagnostic.source,
        code="STRL-SAFETY-0003",
        data=diagnostic.data,
    )
    assert (
        server_module.code_action(
            server_module.server,
            _request(lsp_module, uri, diagnostic.range, [mismatched]),
        )
        == []
    )

    server_module.server.workspace.documents[uri].source = case["source"].replace(
        'text "a"', 'text "b"'
    )
    assert (
        server_module.code_action(
            server_module.server,
            _request(lsp_module, uri, diagnostic.range, [diagnostic]),
        )
        == []
    )

    host_uri = "file:///actions/host.py"
    host_source = 'pattern = s.parse("a{1}")\n'
    host = _compile_current(server_module, host_uri, host_source)
    assert (
        server_module.code_action(
            server_module.server,
            _request(
                lsp_module,
                host_uri,
                lsp_module.Range(
                    start=lsp_module.Position(line=0, character=0),
                    end=lsp_module.Position(line=0, character=len(host_source)),
                ),
                list(host.diagnostics),
            ),
        )
        == []
    )


def test_disjoint_request_range_returns_no_action(
    server_module: Any, lsp_module: Any
) -> None:
    case = _case("action.semantic.greedy")
    uri = "file:///actions/outside.semantic.strling"
    compiled = _compile_current(server_module, uri, case["source"])
    diagnostic = compiled.diagnostics[0]
    outside = lsp_module.Range(
        start=lsp_module.Position(line=0, character=0),
        end=lsp_module.Position(line=0, character=1),
    )
    assert (
        server_module.code_action(
            server_module.server,
            _request(lsp_module, uri, outside, [diagnostic]),
        )
        == []
    )
