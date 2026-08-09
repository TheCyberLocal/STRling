"""
Emitter Edges Conformance — Python bridge.

Drives the global pathological-AST fixture
(``tests/conformance/inputs/emitter_edges/pathological.json``) through the
Python PCRE2 emitter and asserts each safety guard fires:

  1. Variable-Length Lookbehind Rejection — STRlingCompilationError
  2. AST Depth Limit Exceeded             — STRlingCompilationError
  3. ReDoS Risk Warning (nested ``(a+)+``) — non-fatal STRlingWarning

The fixture's ``ast`` field is the user-facing AST sketch (e.g.
``{type: "Lookbehind", content: ...}``), not the post-lowering IR. The
adapter ``_ast_to_ir`` below mirrors the TypeScript bridge's ``astToIR``
function so the test targets the emitter without coupling to the parser
or compiler stages. Keep it minimal — supporting only the node types
present in ``pathological.json`` — so adapter omissions cannot mask
emitter bugs by silently dropping nodes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

import pytest

from STRling.core.errors import STRlingCompilationError, STRlingWarning
from STRling.core.ir import (
    IRGroup,
    IRLit,
    IRLook,
    IROp,
    IRQuant,
)
from STRling.emitters.pcre2 import emit, emit_with_diagnostics


# Workspace-rooted fixture path: from ``bindings/python/tests/unit/this.py`` we
# climb four parent directories to reach the workspace root
# (``unit`` → ``tests`` → ``python`` → ``bindings`` → repo root) and then
# descend to the shared global fixture.
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4]
    / "tests"
    / "conformance"
    / "inputs"
    / "emitter_edges"
    / "pathological.json"
)


def _ast_to_ir(node: Dict[str, Any]) -> IROp:
    """Convert a pathological-fixture AST sketch into Python IR.

    Supports only the node types currently appearing in
    ``pathological.json``. Extend deliberately when new vectors are added
    so coverage gaps surface as ``KeyError`` rather than silent passes.
    """
    t = node["type"]

    if t == "Literal":
        return IRLit(node.get("value", ""))

    if t == "Group":
        # Pathological fixtures use non-capturing groups for nesting.
        if "content" not in node:
            raise ValueError("Group node missing 'content'")
        return IRGroup(capturing=False, body=_ast_to_ir(node["content"]))

    if t == "Quantifier":
        if "content" not in node:
            raise ValueError("Quantifier node missing 'content'")
        child = _ast_to_ir(node["content"])
        min_v = node.get("min", 0)
        # ``null`` in the user-facing AST means unbounded → IR sentinel "Inf".
        max_raw = node.get("max", None)
        max_v: Any = "Inf" if max_raw is None else max_raw
        mode = node.get("mode", "Greedy")
        return IRQuant(child=child, min=min_v, max=max_v, mode=mode)

    if t == "Lookbehind":
        if "content" not in node:
            raise ValueError("Lookbehind node missing 'content'")
        return IRLook(dir="Behind", neg=False, body=_ast_to_ir(node["content"]))

    if t == "NegativeLookbehind":
        if "content" not in node:
            raise ValueError("NegativeLookbehind node missing 'content'")
        return IRLook(dir="Behind", neg=True, body=_ast_to_ir(node["content"]))

    if t == "Lookahead":
        if "content" not in node:
            raise ValueError("Lookahead node missing 'content'")
        return IRLook(dir="Ahead", neg=False, body=_ast_to_ir(node["content"]))

    if t == "NegativeLookahead":
        if "content" not in node:
            raise ValueError("NegativeLookahead node missing 'content'")
        return IRLook(dir="Ahead", neg=True, body=_ast_to_ir(node["content"]))

    raise ValueError(
        f"_ast_to_ir: unsupported pathological AST node type {t!r}. "
        "Extend the adapter when new pathological vectors are added."
    )


def _expected_substring(expected: str) -> str:
    """Strip the ``STRlingCompilationError: ``/``STRlingWarning [CODE]: ``
    prefix from a fixture's expected string so we can substring-match
    against the actual error message / warning message."""
    m = re.match(r"^STRlingCompilationError:\s*(.*)$", expected)
    if m:
        return m.group(1)
    m = re.match(r"^STRlingWarning\s*\[[^\]]+\]:\s*(.*)$", expected)
    if m:
        return m.group(1)
    return expected


def _load_fixture() -> Dict[str, Any]:
    assert _FIXTURE_PATH.is_file(), (
        f"emitter_edges fixture not found at {_FIXTURE_PATH}; "
        "the global pathological fixture must be present for conformance."
    )
    with _FIXTURE_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


_FIXTURE = _load_fixture()


def test_fixture_is_well_formed() -> None:
    assert isinstance(_FIXTURE.get("tests"), list)
    assert len(_FIXTURE["tests"]) > 0


@pytest.mark.parametrize(
    "case",
    _FIXTURE["tests"],
    ids=[c["name"] for c in _FIXTURE["tests"]],
)
def test_pathological_case(case: Dict[str, Any]) -> None:
    ir = _ast_to_ir(case["ast"])
    max_depth = case.get("depth_override_for_test")

    if "expected_error" in case:
        needle = _expected_substring(case["expected_error"])
        with pytest.raises(STRlingCompilationError) as excinfo:
            emit(ir, flags=None, max_depth=max_depth)
        assert needle in str(excinfo.value), (
            f"expected error to contain {needle!r}; got {excinfo.value!r}"
        )
        return

    if "expected_warning" in case:
        needle = _expected_substring(case["expected_warning"])
        result = emit_with_diagnostics(ir, flags=None, max_depth=max_depth)
        # Warnings must NOT abort emission — the pattern is still produced.
        assert isinstance(result.pattern, str)
        assert len(result.pattern) > 0
        assert any(
            isinstance(w, STRlingWarning) and needle in w.message
            for w in result.warnings
        ), f"expected REDOS_RISK warning containing {needle!r}; got {result.warnings!r}"
        return

    pytest.fail(
        f"Test case {case['name']!r} declares neither expected_error nor expected_warning."
    )


# --- Negative controls --------------------------------------------------------


def test_non_pathological_pattern_emits_no_warnings() -> None:
    """A plain literal must not surface any diagnostic warnings."""
    result = emit_with_diagnostics(IRLit("abc"))
    assert result.pattern == "abc"
    assert result.warnings == []


def test_depth_cap_does_not_fire_under_limit() -> None:
    """Two nested groups under a depth cap of 5 must compile cleanly."""
    deep = IRGroup(capturing=False, body=IRGroup(capturing=False, body=IRLit("ok")))
    result = emit_with_diagnostics(deep, max_depth=5)
    assert result.warnings == []
    assert "ok" in result.pattern
