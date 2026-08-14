"""Mutation-resistant canonical LSP lifecycle and service-failure evidence."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any

import pytest

_LSP_ROOT = str(Path(__file__).resolve().parents[1])
if _LSP_ROOT not in sys.path:
    sys.path.insert(0, _LSP_ROOT)

from canonical_evidence import load_manifest  # noqa: E402


REQUIRED_CLASSES = {
    "publication",
    "debounce",
    "close",
    "cancellation",
    "stale",
    "profile",
    "cache",
    "failure",
    "recovery",
}


class _Document:
    def __init__(self, source: str, version: int | None = None) -> None:
        self.source = source
        self.version = version


class _Workspace:
    def __init__(self, uri: str, source: str, version: int | None = None) -> None:
        self.documents = {uri: _Document(source, version)}

    def get_text_document(self, uri: str) -> _Document:
        return self.documents[uri]


class _Server:
    def __init__(self, uri: str, source: str, version: int | None = None) -> None:
        self.workspace = _Workspace(uri, source, version)
        self.published: list[Any] = []
        self.logs: list[str] = []

    def text_document_publish_diagnostics(self, params: Any) -> None:
        self.published.append(params)

    def show_message_log(self, message: str) -> None:
        self.logs.append(message)


class _Process:
    def __init__(self) -> None:
        self.terminated = False

    def poll(self) -> None:
        return None

    def terminate(self) -> None:
        self.terminated = True


class _Timer:
    created: list["_Timer"] = []

    def __init__(self, delay: float, callback: Any, args: tuple[Any, ...]) -> None:
        self.delay = delay
        self.callback = callback
        self.args = args
        self.cancelled = False
        self.started = False
        self.created.append(self)

    def cancel(self) -> None:
        self.cancelled = True

    def start(self) -> None:
        self.started = True


@pytest.fixture
def server_module():
    from server import server as module

    original_compiler = module._COMPILER
    with module._STATE_LOCK:
        for uri in list(module._DEBOUNCE_TIMERS):
            module._cancel_uri_locked(uri)
        module._ISLANDS_BY_URI.clear()
        module._LAST_DIAGNOSTICS.clear()
        module._CANONICAL_RESULTS_BY_URI.clear()
        module._SNAPSHOTS_BY_URI.clear()
        module._ACTIVE_PROCESSES.clear()
        module._GENERATIONS.clear()
        module._RESULT_CACHE.clear()
        module._RESULT_CACHE_ORDER.clear()
        module._POSITION_ENCODING = module.DEFAULT_POSITION_ENCODING
        module._TARGET_PROFILE = None
    yield module
    with module._STATE_LOCK:
        for uri in list(module._DEBOUNCE_TIMERS):
            module._cancel_uri_locked(uri)
        module._ISLANDS_BY_URI.clear()
        module._LAST_DIAGNOSTICS.clear()
        module._CANONICAL_RESULTS_BY_URI.clear()
        module._SNAPSHOTS_BY_URI.clear()
        module._ACTIVE_PROCESSES.clear()
        module._GENERATIONS.clear()
        module._RESULT_CACHE.clear()
        module._RESULT_CACHE_ORDER.clear()
        module._POSITION_ENCODING = module.DEFAULT_POSITION_ENCODING
        module._TARGET_PROFILE = None
        module._COMPILER = original_compiler


def _empty_result(module: Any, snapshot: Any) -> Any:
    return module._SnapshotResult(
        snapshot=snapshot,
        units=(),
        diagnostics=(),
        islands=(),
    )


def test_lifecycle_manifest_has_complete_unique_mutations() -> None:
    cases = load_manifest()["lifecycle_cases"]
    assert len(cases) == 16
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    counts = Counter(case["class"] for case in cases)
    assert set(counts) == REQUIRED_CLASSES
    assert counts["cancellation"] >= 2
    assert counts["cache"] >= 2
    assert counts["failure"] >= 4


def test_service_failure_and_compile_failure_are_distinct() -> None:
    by_id = {case["id"]: case["class"] for case in load_manifest()["lifecycle_cases"]}
    assert by_id["compile-failed-result-is-data"] == "failure"
    assert by_id["timeout-isolated"] == "failure"
    assert by_id["missing-kernel-isolated"] == "failure"
    assert by_id["malformed-kernel-output-isolated"] == "failure"
    assert by_id["recovery-after-service-failure"] == "recovery"


def test_cache_identity_includes_every_semantic_input() -> None:
    ids = {case["id"] for case in load_manifest()["lifecycle_cases"]}
    assert {
        "cache-hit-identical-semantic-inputs",
        "cache-miss-on-content-change",
        "profile-change-invalidates",
        "position-encoding-invalidates",
        "stale-completion-discarded",
    } <= ids


def test_open_and_save_schedule_exact_current_versions(
    server_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    uri = "file:///lifecycle/open.strl"
    calls: list[tuple[str, int | None, float]] = []
    monkeypatch.setattr(
        server_module,
        "_schedule_validation",
        lambda _ls, scheduled_uri, version, *, delay: calls.append(
            (scheduled_uri, version, delay)
        ),
    )
    ls = _Server(uri, "abc", 7)
    document = server_module.lsp.TextDocument(uri=uri, version=7)
    server_module.did_open(
        ls, server_module.lsp.DidOpenTextDocumentParams(text_document=document)
    )
    server_module.did_save(
        ls, server_module.lsp.DidSaveTextDocumentParams(text_document=document)
    )
    assert calls == [(uri, 7, 0.0), (uri, 7, 0.0)]


def test_change_debounces_latest_and_cancels_pending(
    server_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    uri = "file:///lifecycle/change.strl"
    ls = _Server(uri, "a", 1)
    _Timer.created = []
    monkeypatch.setattr(server_module.threading, "Timer", _Timer)
    server_module._schedule_validation(ls, uri, 1)
    first = _Timer.created[-1]
    ls.workspace.documents[uri] = _Document("ab", 2)
    server_module._schedule_validation(ls, uri, 2)
    second = _Timer.created[-1]
    assert first.cancelled is True
    assert second.started is True
    assert second.args[1].version == 2
    assert server_module._SNAPSHOTS_BY_URI[uri].source == "ab"


def test_new_generation_terminates_in_flight_process(server_module) -> None:
    uri = "file:///lifecycle/cancel.strl"
    ls = _Server(uri, "a", 1)
    first = server_module._capture_snapshot(ls, uri, 1)
    process = _Process()
    server_module._observe_process(first, process)
    ls.workspace.documents[uri] = _Document("b", 2)
    second = server_module._capture_snapshot(ls, uri, 2)
    assert process.terminated is True
    assert second.generation > first.generation

    stale_process = _Process()
    server_module._observe_process(first, stale_process)
    assert stale_process.terminated is True


def test_stale_completion_is_discarded(server_module) -> None:
    uri = "file:///lifecycle/stale.strl"
    ls = _Server(uri, "a", 1)
    first = server_module._capture_snapshot(ls, uri, 1)
    ls.workspace.documents[uri] = _Document("b", 2)
    server_module._capture_snapshot(ls, uri, 2)
    server_module._publish_snapshot(ls, _empty_result(server_module, first))
    assert ls.published == []
    assert uri not in server_module._CANONICAL_RESULTS_BY_URI


def test_close_cancels_clears_and_publishes_empty(server_module) -> None:
    uri = "file:///lifecycle/close.strl"
    ls = _Server(uri, "a", 4)
    snapshot = server_module._capture_snapshot(ls, uri, 4)
    process = _Process()
    timer = _Timer(10.0, lambda: None, ())
    server_module._ACTIVE_PROCESSES[uri] = (snapshot.generation, process)
    server_module._DEBOUNCE_TIMERS[uri] = timer
    server_module._CANONICAL_RESULTS_BY_URI[uri] = _empty_result(
        server_module, snapshot
    )

    params = server_module.lsp.DidCloseTextDocumentParams(
        text_document=server_module.lsp.TextDocument(uri=uri)
    )
    server_module.did_close(ls, params)

    assert process.terminated is True
    assert timer.cancelled is True
    assert uri not in server_module._SNAPSHOTS_BY_URI
    assert uri not in server_module._CANONICAL_RESULTS_BY_URI
    assert ls.published[-1].diagnostics == []


@pytest.mark.parametrize(
    "option",
    [
        {"target_profile": "target:pcre2-10.43@1.0.0"},
        {"position_encoding": "utf-8"},
    ],
)
def test_profile_and_position_changes_invalidate_state(server_module, option) -> None:
    uri = "file:///lifecycle/profile.strl"
    ls = _Server(uri, "abc", 1)
    snapshot = server_module._capture_snapshot(ls, uri, 1)
    server_module._CANONICAL_RESULTS_BY_URI[uri] = _empty_result(
        server_module, snapshot
    )
    server_module._set_session_options(**option)
    assert uri not in server_module._SNAPSHOTS_BY_URI
    assert uri not in server_module._CANONICAL_RESULTS_BY_URI


def test_initialize_negotiates_encoding_and_explicit_target(server_module) -> None:
    uri = "file:///lifecycle/initialize.strl"
    ls = _Server(uri, "abc")
    params = server_module.lsp.InitializeParams(
        capabilities={"general": {"positionEncodings": ["utf-8", "utf-16"]}},
        initialization_options={"targetProfile": "pcre2-10.42"},
    )
    server_module.initialize(ls, params)
    assert server_module._POSITION_ENCODING == "utf-8"
    assert server_module._TARGET_PROFILE == "pcre2-10.42"
    assert ls.position_encoding == "utf-8"
    assert "position encoding utf-8" in ls.logs[-1]


def test_cache_keys_every_semantic_input(server_module) -> None:
    class _Compiler:
        timeout_seconds = 1.0

        def __init__(self) -> None:
            self.calls: list[tuple[str, str, str | None]] = []

        def compile(self, source: str, *, frontend: str, target=None, **_kwargs):
            self.calls.append((source, frontend, target))
            return {"source": source, "frontend": frontend, "target": target}

    compiler = _Compiler()
    server_module._COMPILER = compiler
    first = server_module._compile_cached("a", "regex", None, "utf-16")
    assert server_module._compile_cached("a", "regex", None, "utf-16") is first
    server_module._compile_cached("b", "regex", None, "utf-16")
    server_module._compile_cached("a", "semantic", None, "utf-16")
    server_module._compile_cached("a", "regex", "target:test", "utf-16")
    server_module._compile_cached("a", "regex", None, "utf-8")
    assert len(compiler.calls) == 5


@pytest.mark.parametrize(
    "failure_code",
    ["timeout", "unavailable", "malformed_result", "input_limit"],
)
def test_service_failures_are_isolated_and_clear_diagnostics(
    server_module, monkeypatch: pytest.MonkeyPatch, failure_code: str
) -> None:
    uri = f"file:///lifecycle/{failure_code}.strl"
    ls = _Server(uri, "abc", 3)
    snapshot = server_module._capture_snapshot(ls, uri, 3)

    def fail(_snapshot):
        raise server_module.CompilerServiceError(failure_code, failure_code)

    monkeypatch.setattr(server_module, "_compile_snapshot", fail)
    server_module._execute_snapshot(ls, snapshot)
    assert ls.published[-1].diagnostics == []
    assert ls.published[-1].version == 3
    assert failure_code in ls.logs[-1]
    assert uri not in server_module._CANONICAL_RESULTS_BY_URI


def test_compile_failure_is_data_and_service_recovers(
    server_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    uri = "file:///lifecycle/recovery.strl"
    ls = _Server(uri, "(abc", 9)
    server_module.validate_document(ls, uri, 9)
    assert ls.published[-1].version == 9
    assert [item.code for item in ls.published[-1].diagnostics] == [
        "STRL-FRONTEND-2012"
    ]
    assert ls.logs == []

    snapshot = server_module._capture_snapshot(ls, uri, 10)

    def malformed(_snapshot):
        raise ValueError("bad canonical span")

    monkeypatch.setattr(server_module, "_compile_snapshot", malformed)
    server_module._execute_snapshot(ls, snapshot)
    assert ls.published[-1].diagnostics == []
    assert "projection error" in ls.logs[-1]

    monkeypatch.setattr(
        server_module,
        "_compile_snapshot",
        lambda current: _empty_result(server_module, current),
    )
    server_module._execute_snapshot(ls, snapshot)
    assert server_module._CANONICAL_RESULTS_BY_URI[uri].snapshot == snapshot
