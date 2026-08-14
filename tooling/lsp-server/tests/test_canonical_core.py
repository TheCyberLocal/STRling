"""Executable contract design for canonical LSP compiler and range parity."""

from __future__ import annotations

import pytest

from canonical_evidence import kernel_command, load_manifest, run_case


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


def test_diagnostic_denominator_covers_frontends_profiles_and_evidence_classes() -> None:
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
    assert any(any(ord(character) > 127 for character in case["source"]) for case in cases)
    assert any("\n" in case["source"] for case in cases)


@pytest.mark.skipif(kernel_command() is None, reason="built canonical kernel unavailable")
@pytest.mark.parametrize("case", load_manifest()["diagnostic_cases"], ids=lambda case: case["id"])
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
    assert {"bmp-scalar", "astral-scalar", "multiline-astral", "crlf-line-boundary"} <= {
        case["id"] for case in cases
    }
    for case in cases:
        assert case["start"] <= case["end"] <= len(case["source"].encode("utf-8"))
        assert set(case["expected"]) == encodings
        for projected_range in case["expected"].values():
            assert len(projected_range) == 2
            assert all(len(position) == 2 for position in projected_range)
