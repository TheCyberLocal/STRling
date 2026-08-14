"""Mutation-resistant lifecycle and service-failure evidence design."""

from __future__ import annotations

from collections import Counter

from canonical_evidence import load_manifest


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
