"""Shared readers for the authored P16-T02 verification evidence."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterator


LSP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = LSP_ROOT.parents[1]
MANIFEST_PATH = Path(__file__).parent / "fixtures" / "canonical-lsp" / "manifest.json"


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def kernel_command() -> list[str] | None:
    configured = os.environ.get("STRLING_KERNEL")
    if configured:
        return [configured]
    executable = "strling-kernel.exe" if os.name == "nt" else "strling-kernel"
    for profile in ("debug", "release"):
        candidate = (
            REPOSITORY_ROOT / "core" / "internal" / "target" / profile / executable
        )
        if candidate.is_file():
            return [str(candidate)]
    return None


def run_case(case: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    command = kernel_command()
    if command is None:
        raise FileNotFoundError("a built strling-kernel executable is unavailable")
    arguments = [
        *command,
        str(case["command"]),
        "--input",
        "-",
        "--output",
        "semantic",
        "--output",
        "analysis",
        "--format",
        "json",
    ]
    if case["command"] != "import":
        arguments.extend(["--frontend", str(case["frontend"])])
    target = case.get("target")
    if target is not None:
        arguments.extend(["--target", str(target)])
    completed = subprocess.run(
        arguments,
        input=str(case["source"]).encode("utf-8"),
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert completed.stderr == b"", completed.stderr.decode("utf-8", errors="replace")
    return completed.returncode, json.loads(completed.stdout.decode("utf-8"))


def iter_nodes(
    node: dict[str, Any], depth: int = 0
) -> Iterator[tuple[int, dict[str, Any]]]:
    yield depth, node
    for key in ("items", "branches"):
        children = node.get(key)
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict) and "kind" in child:
                    yield from iter_nodes(child, depth + 1)
    body = node.get("body")
    if isinstance(body, dict) and "kind" in body:
        yield from iter_nodes(body, depth + 1)


def node_span(node: dict[str, Any]) -> tuple[int, int] | None:
    origin = node.get("origin")
    if not isinstance(origin, dict):
        return None
    spans = origin.get("source_spans")
    if not isinstance(spans, list) or len(spans) != 1:
        return None
    span = spans[0]
    return int(span["start"]), int(span["end"])


def select_narrowest_node(
    root: dict[str, Any], cursor_byte: int
) -> dict[str, Any] | None:
    candidates: list[tuple[int, int, int, dict[str, Any]]] = []
    for order, (depth, node) in enumerate(iter_nodes(root)):
        span = node_span(node)
        if span is None:
            continue
        start, end = span
        contains = start == end == cursor_byte or start <= cursor_byte < end
        if contains:
            candidates.append((end - start, -depth, order, node))
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: candidate[:3])[3]
