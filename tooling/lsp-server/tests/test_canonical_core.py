"""Executable contract design for canonical LSP compiler and range parity."""

from __future__ import annotations

import subprocess
import sys
from importlib import import_module

import pytest

from canonical_evidence import LSP_ROOT, kernel_command, load_manifest, run_case

if str(LSP_ROOT) not in sys.path:
    sys.path.insert(0, str(LSP_ROOT))

_canonical_core = import_module("server.canonical_core")
CanonicalCompiler = _canonical_core.CanonicalCompiler
CompilerServiceError = _canonical_core.CompilerServiceError
byte_offset_to_position = _canonical_core.byte_offset_to_position
diagnostic_payload = _canonical_core.diagnostic_payload
position_to_byte_offset = _canonical_core.position_to_byte_offset
project_span = _canonical_core.project_span


def test_manifest_has_closed_versions_limits_and_position_encodings() -> None:
    manifest = load_manifest()
    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["compiler_contract_version"] == "1.0.0"
    assert manifest["position_encodings"] == ["utf-8", "utf-16", "utf-32"]
    assert manifest["resource_limits"] == {
        "max_source_bytes": 1_048_576,
        "max_diagnostics": 256,
        "max_islands": 256,
        "compile_timeout_seconds": 5.0,
        "debounce_seconds": 0.05,
    }


def test_diagnostic_denominator_covers_frontends_profiles_and_evidence_classes() -> (
    None
):
    cases = load_manifest()["diagnostic_cases"]
    assert len(cases) == 12
    assert {case["frontend"] for case in cases} == {"regex", "semantic"}
    assert {case.get("target") for case in cases if case.get("target")} == {
        "pcre2-10.42",
        "python-re-3.11",
    }
    assert {case["expected_outcome"] for case in cases} == {"succeeded", "failed"}
    severities = {
        diagnostic["severity"]
        for case in cases
        for diagnostic in case["expected_diagnostics"]
    }
    assert severities == {"error", "warning"}
    assert any(
        any(ord(character) > 127 for character in case["source"]) for case in cases
    )
    assert any("\n" in case["source"] for case in cases)


@pytest.mark.skipif(
    kernel_command() is None, reason="built canonical kernel unavailable"
)
@pytest.mark.parametrize(
    "case", load_manifest()["diagnostic_cases"], ids=lambda case: case["id"]
)
def test_live_kernel_matches_authored_diagnostic_evidence(case: dict) -> None:
    exit_code, result = run_case(case)
    assert exit_code == (0 if case["expected_outcome"] == "succeeded" else 2)
    assert result["outcome"] == case["expected_outcome"]
    actual = []
    for diagnostic in result["diagnostics"]:
        location = diagnostic.get("primary_location")
        actual.append(
            {
                "code": diagnostic["code"],
                "severity": diagnostic["severity"],
                "message": diagnostic["message"],
                "start": None if location is None else location["start"],
                "end": None if location is None else location["end"],
            }
        )
        if location is not None:
            assert location["coordinate_system"] == "utf8-bytes"
    assert actual == case["expected_diagnostics"]


def test_position_evidence_is_complete_and_half_open() -> None:
    manifest = load_manifest()
    encodings = set(manifest["position_encodings"])
    cases = manifest["position_cases"]
    assert len(cases) == 6
    assert {
        "bmp-scalar",
        "astral-scalar",
        "multiline-astral",
        "crlf-line-boundary",
    } <= {case["id"] for case in cases}
    for case in cases:
        assert case["start"] <= case["end"] <= len(case["source"].encode("utf-8"))
        assert set(case["expected"]) == encodings
        for projected_range in case["expected"].values():
            assert len(projected_range) == 2
            assert all(len(position) == 2 for position in projected_range)


@pytest.mark.parametrize(
    "case", load_manifest()["position_cases"], ids=lambda case: case["id"]
)
@pytest.mark.parametrize("encoding", load_manifest()["position_encodings"])
def test_position_projection_matches_authored_evidence(
    case: dict, encoding: str
) -> None:
    start, end = project_span(case["source"], case["start"], case["end"], encoding)
    expected_start, expected_end = case["expected"][encoding]
    assert [start.line, start.character] == expected_start
    assert [end.line, end.character] == expected_end
    assert (
        position_to_byte_offset(case["source"], *expected_start, encoding)
        == case["start"]
    )
    assert (
        position_to_byte_offset(case["source"], *expected_end, encoding) == case["end"]
    )


def test_position_projection_rejects_mid_scalar_and_mid_surrogate_offsets() -> None:
    with pytest.raises(ValueError, match="splits a scalar"):
        byte_offset_to_position("é", 1, "utf-16")
    with pytest.raises(ValueError, match="splits an encoded scalar"):
        position_to_byte_offset("😀", 0, 1, "utf-16")


@pytest.mark.skipif(
    kernel_command() is None, reason="built canonical kernel unavailable"
)
@pytest.mark.parametrize(
    "case", load_manifest()["diagnostic_cases"], ids=lambda case: case["id"]
)
def test_canonical_bridge_result_is_cli_identical(case: dict) -> None:
    _, direct = run_case(case)
    bridged = CanonicalCompiler().compile(
        case["source"], frontend=case["frontend"], target=case.get("target")
    )
    assert bridged == direct


def test_diagnostic_projection_preserves_identity_and_unicode_range() -> None:
    case = next(
        case
        for case in load_manifest()["diagnostic_cases"]
        if case["id"] == "regex-unicode-orphan-close"
    )
    _, result = run_case(case)
    payload = diagnostic_payload(result["diagnostics"][0], case["source"], "utf-16")
    assert payload["code"] == "STRL-FRONTEND-2011"
    assert payload["severity"] == 1
    assert payload["message"] == "closing parenthesis has no opener"
    assert payload["range"] == {
        "start": {"line": 0, "character": 1},
        "end": {"line": 0, "character": 2},
    }
    assert payload["data"]["canonical"] == result["diagnostics"][0]


def test_bridge_reports_service_limits_without_fabricating_diagnostics() -> None:
    compiler = CanonicalCompiler(command=["missing-kernel"], max_source_bytes=1)
    with pytest.raises(CompilerServiceError) as exceeded:
        compiler.compile("é", frontend="regex")
    assert exceeded.value.code == "input_limit"

    compiler = CanonicalCompiler(command=["definitely-missing-strling-kernel"])
    with pytest.raises(CompilerServiceError) as unavailable:
        compiler.compile("a", frontend="regex")
    assert unavailable.value.code == "unavailable"


def test_bridge_rejects_malformed_compile_result_contract() -> None:
    compiler = CanonicalCompiler(command=["unused"])
    with pytest.raises(CompilerServiceError) as malformed:
        compiler._validate_result({}, "a", 0)
    assert malformed.value.code == "malformed_result"


def test_bridge_timeout_terminates_request_and_releases_observer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server import canonical_core

    class _Process:
        returncode = 0

        def __init__(self) -> None:
            self.calls = 0
            self.killed = False

        def communicate(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("kernel", 0.01)
            return b"", b""

        def kill(self) -> None:
            self.killed = True

    process = _Process()
    monkeypatch.setattr(canonical_core.subprocess, "Popen", lambda *_a, **_k: process)
    observed = []
    compiler = CanonicalCompiler(command=["kernel"], timeout_seconds=0.01)
    with pytest.raises(CompilerServiceError) as timeout:
        compiler.compile("a", frontend="regex", process_observer=observed.append)
    assert timeout.value.code == "timeout"
    assert process.killed is True
    assert observed == [process, None]
