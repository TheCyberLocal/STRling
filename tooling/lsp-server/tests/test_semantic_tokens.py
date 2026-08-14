"""Authored semantic-token and host-projection denominator for P16-T03."""

from __future__ import annotations

from canonical_intelligence_evidence import load_manifest, materialize_tokens


def test_token_cases_cover_both_frontends_and_every_frozen_legend_type() -> None:
    manifest = load_manifest()
    cases = manifest["token_cases"]
    assert len(cases) == 8
    assert {case["frontend"] for case in cases} == {"semantic", "regex"}
    actual_types = {
        token["type"] for case in cases for token in materialize_tokens(case)
    }
    assert actual_types == set(manifest["semantic_token_legend"])


def test_authored_token_spans_are_utf8_exact_sorted_and_non_overlapping() -> None:
    for case in load_manifest()["token_cases"]:
        source_bytes = case["source"].encode("utf-8")
        previous_end = 0
        for token in materialize_tokens(case):
            assert previous_end <= token["start"] < token["end"] <= len(source_bytes)
            assert b"\n" not in source_bytes[token["start"] : token["end"]]
            assert b"\r" not in source_bytes[token["start"] : token["end"]]
            previous_end = token["end"]


def test_capture_token_identity_and_multiline_split_are_explicit() -> None:
    cases = {case["id"]: case for case in load_manifest()["token_cases"]}
    capture_types = [
        token["type"] for token in cases["regex-named-capture-reference"]["tokens"]
    ]
    assert "function" in capture_types
    assert "variable" in capture_types
    multiline = materialize_tokens(cases["regex-unicode-multiline-split"])
    assert [(token["start"], token["end"]) for token in multiline] == [
        (0, 2),
        (3, 7),
        (7, 8),
    ]


def test_host_projection_cases_freeze_bmp_astral_and_multiline_utf16_ranges() -> None:
    cases = load_manifest()["host_projection_cases"]
    assert len(cases) == 3
    assert {case["id"] for case in cases} == {
        "host-python-bmp",
        "host-python-astral",
        "host-python-multiline",
    }
    assert all(case["encoding"] == "utf-16" for case in cases)
    for case in cases:
        assert len(case["virtual_spans"]) == len(case["expected_host_ranges"])
