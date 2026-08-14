"""Canonical hover selection and evidence-denominator design."""

from __future__ import annotations

import pytest

from canonical_evidence import (
    iter_nodes,
    kernel_command,
    load_manifest,
    node_span,
    run_case,
    select_narrowest_node,
)


ALL_NODE_KINDS = {
    "empty",
    "sequence",
    "alternation",
    "literal",
    "wildcard",
    "character_set",
    "repeat",
    "position",
    "capture",
    "backreference",
    "lookaround",
    "atomic",
}


def test_hover_manifest_covers_every_semantic_ir_node_kind_once() -> None:
    manifest = load_manifest()
    cases = manifest["hover_cases"]
    assert len(cases) == 12
    assert {case["expected_kind"] for case in cases} == ALL_NODE_KINDS
    assert manifest["hover_section_order"] == [
        "construct",
        "capture",
        "analysis",
        "safety",
        "portability",
        "documentation",
    ]


@pytest.mark.skipif(kernel_command() is None, reason="built canonical kernel unavailable")
@pytest.mark.parametrize("case", load_manifest()["hover_cases"], ids=lambda case: case["id"])
def test_live_kernel_supports_locked_narrowest_node_hover(case: dict) -> None:
    exit_code, result = run_case(case)
    assert exit_code == 0
    root = result["semantic_result"]["program"]["root"]
    selected = select_narrowest_node(root, case["cursor_byte"])
    assert selected is not None
    assert selected["node_id"] == case["expected_node_id"]
    assert selected["kind"] == case["expected_kind"]
    assert list(node_span(selected) or ()) == case["expected_span"]

    facts = {fact["node_id"]: fact for fact in result["analysis"]["node_facts"]}
    fact = facts[selected["node_id"]]
    expected = case["expected_fact"]
    assert fact["nullable"] is expected["nullable"]
    assert fact["length_bounds"]["min"] == expected["min"]
    assert fact["length_bounds"]["max"] == expected["max"]
    assert fact["length_bounds"]["unit"] == "unicode-scalar-values"

    node_ids = [node["node_id"] for _, node in iter_nodes(root)]
    assert len(node_ids) == len(set(node_ids))


def test_hover_gap_and_stale_dispositions_are_explicit() -> None:
    lifecycle_ids = {case["id"] for case in load_manifest()["lifecycle_cases"]}
    assert "stale-completion-discarded" in lifecycle_ids
    assert "profile-change-invalidates" in lifecycle_ids
    assert "position-encoding-invalidates" in lifecycle_ids
