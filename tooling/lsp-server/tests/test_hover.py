"""Canonical hover selection and evidence-denominator design."""

from __future__ import annotations

import sys
from importlib import import_module

import pytest

from canonical_evidence import (
    LSP_ROOT,
    iter_nodes,
    kernel_command,
    load_manifest,
    node_span,
    run_case,
    select_narrowest_node,
)

if str(LSP_ROOT) not in sys.path:
    sys.path.insert(0, str(LSP_ROOT))

_canonical_core = import_module("server.canonical_core")
CanonicalCompiler = _canonical_core.CanonicalCompiler
render_hover = _canonical_core.render_hover


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


@pytest.mark.skipif(
    kernel_command() is None, reason="built canonical kernel unavailable"
)
@pytest.mark.parametrize(
    "case", load_manifest()["hover_cases"], ids=lambda case: case["id"]
)
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

    evidence = render_hover(result, case["source"], case["cursor_byte"])
    assert evidence is not None
    assert evidence.node_id == case["expected_node_id"]
    assert evidence.node_kind == case["expected_kind"]
    assert [evidence.start, evidence.end] == case["expected_span"]
    assert (
        evidence.markdown
        == render_hover(result, case["source"], case["cursor_byte"]).markdown
    )


def test_literal_hover_markdown_is_an_exact_canonical_golden() -> None:
    case = next(
        case for case in load_manifest()["hover_cases"] if case["id"] == "hover-literal"
    )
    _, result = run_case(case)
    evidence = render_hover(result, case["source"], case["cursor_byte"])
    assert evidence is not None
    assert evidence.markdown == (
        "**STRling construct: `literal`**\n\n"
        "- Node: `node:regex-compat/00000001`\n"
        "- Text: `abc`\n\n"
        "**Canonical analysis**\n\n"
        "- Nullable: `false`\n"
        "- Length: `3..3` `unicode-scalar-values`"
    )


def test_capture_safety_and_portability_sections_require_canonical_evidence() -> None:
    compiler = CanonicalCompiler()
    capture = compiler.compile("(?<word>a)", frontend="regex")
    capture_hover = render_hover(capture, "(?<word>a)", 1)
    assert capture_hover is not None
    assert "**Capture evidence**" in capture_hover.markdown
    assert "- Capture ID: `capture:regex-compat/00001`" in capture_hover.markdown
    assert "- Name: `word`" in capture_hover.markdown

    safety = compiler.compile("(a+)+", frontend="regex")
    safety_hover = render_hover(safety, "(a+)+", 4)
    assert safety_hover is not None
    assert "**Safety evidence**" in safety_hover.markdown
    assert "`STRL-SAFETY-0003` `warning`" in safety_hover.markdown

    portability = compiler.compile("(?>a)", frontend="regex", target="python-re-3.11")
    portability_hover = render_hover(portability, "(?>a)", 1)
    assert portability_hover is not None
    assert "**Target portability**" in portability_hover.markdown
    assert "`profile:python-re/3.11@1.2.0`" in portability_hover.markdown
    assert "`groups.atomic`: `native`" in portability_hover.markdown

    no_target = compiler.compile("(?>a)", frontend="regex")
    no_target_hover = render_hover(no_target, "(?>a)", 1)
    assert no_target_hover is not None
    assert "**Target portability**" not in no_target_hover.markdown


def test_hover_gap_and_stale_dispositions_are_explicit() -> None:
    lifecycle_ids = {case["id"] for case in load_manifest()["lifecycle_cases"]}
    assert "stale-completion-discarded" in lifecycle_ids
    assert "profile-change-invalidates" in lifecycle_ids
    assert "position-encoding-invalidates" in lifecycle_ids
