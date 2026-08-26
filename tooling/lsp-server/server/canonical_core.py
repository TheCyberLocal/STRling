"""Canonical compiler transport and evidence projection for the STRling LSP.

This module is deliberately free of LSP and Python-binding imports. It owns
only bounded process transport, validation of the returned compiler envelope,
UTF-8 byte/LSP coordinate conversion, and deterministic presentation of
evidence already present in a canonical ``CompileResult``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


SUPPORTED_POSITION_ENCODINGS = ("utf-8", "utf-16", "utf-32")
DEFAULT_POSITION_ENCODING = "utf-16"
DEFAULT_MAX_SOURCE_BYTES = 1_048_576
DEFAULT_MAX_DIAGNOSTICS = 256
DEFAULT_TIMEOUT_SECONDS = 5.0


class CompilerServiceError(RuntimeError):
    """A process/transport failure distinct from compiler diagnostics."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ProjectedPosition:
    line: int
    character: int


@dataclass(frozen=True)
class HoverEvidence:
    markdown: str
    start: int
    end: int
    node_id: str
    node_kind: str


ProcessObserver = Callable[[subprocess.Popen[bytes] | None], None]


def canonical_source_id(source: str) -> str:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return f"src:cli.{digest}"


def discover_kernel_command() -> tuple[str, ...] | None:
    configured = os.environ.get("STRLING_KERNEL")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return (str(candidate.resolve()),)
        return None

    executable = "strling-kernel.exe" if os.name == "nt" else "strling-kernel"
    repository_root = Path(__file__).resolve().parents[3]
    for profile in ("debug", "release"):
        candidate = (
            repository_root / "core" / "internal" / "target" / profile / executable
        )
        if candidate.is_file():
            return (str(candidate),)

    installed = shutil.which("strling-kernel")
    if installed:
        return (installed,)
    return None


class CanonicalCompiler:
    """Invoke one canonical kernel process for one immutable source unit."""

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
        max_diagnostics: int = DEFAULT_MAX_DIAGNOSTICS,
    ) -> None:
        self.command = (
            tuple(command) if command is not None else discover_kernel_command()
        )
        self.timeout_seconds = timeout_seconds
        self.max_source_bytes = max_source_bytes
        self.max_diagnostics = max_diagnostics

    def compile(
        self,
        source: str,
        *,
        frontend: str,
        target: str | None = None,
        timeout_seconds: float | None = None,
        process_observer: ProcessObserver | None = None,
    ) -> dict[str, Any]:
        encoded = source.encode("utf-8")
        if len(encoded) > self.max_source_bytes:
            raise CompilerServiceError(
                "input_limit",
                f"source exceeds the {self.max_source_bytes}-byte LSP transport limit",
            )
        if frontend not in {"regex", "semantic"}:
            raise CompilerServiceError(
                "frontend", f"unsupported LSP frontend {frontend!r}"
            )
        if not self.command:
            self.command = discover_kernel_command()
        if not self.command:
            raise CompilerServiceError(
                "unavailable",
                "strling-kernel is unavailable; configure STRLING_KERNEL or build the kernel",
            )

        product_command = "import" if frontend == "regex" else "compile"
        arguments = [
            *self.command,
            product_command,
            "--input",
            "-",
            "--output",
            "semantic",
            "--output",
            "analysis",
            "--partial-semantics",
            "allow_for_diagnostics",
            "--max-diagnostics",
            str(self.max_diagnostics),
            "--format",
            "json",
        ]
        if frontend == "semantic":
            arguments.extend(["--frontend", "semantic"])
        if target is not None:
            arguments.extend(["--target", target])

        try:
            process = subprocess.Popen(
                arguments,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            raise CompilerServiceError("unavailable", str(error)) from error

        if process_observer is not None:
            process_observer(process)
        try:
            stdout, stderr = process.communicate(
                encoded,
                timeout=self.timeout_seconds
                if timeout_seconds is None
                else timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.communicate()
            raise CompilerServiceError(
                "timeout", "canonical compiler request timed out"
            ) from error
        finally:
            if process_observer is not None:
                process_observer(None)

        if process.returncode not in {0, 2}:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise CompilerServiceError(
                "transport",
                f"canonical compiler exited {process.returncode}"
                + (f": {detail}" if detail else ""),
            )
        if stderr:
            raise CompilerServiceError(
                "transport",
                "canonical JSON compiler wrote unexpected standard-error output",
            )
        try:
            result = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CompilerServiceError(
                "malformed_result", "canonical compiler returned malformed JSON"
            ) from error
        self._validate_result(result, source, process.returncode)
        return result

    def _validate_result(self, result: Any, source: str, exit_code: int) -> None:
        if not isinstance(result, dict):
            raise CompilerServiceError(
                "malformed_result", "CompileResult must be an object"
            )
        if result.get("contract_version") != "1.0.0":
            raise CompilerServiceError(
                "malformed_result", "unsupported CompileResult contract version"
            )
        outcome = result.get("outcome")
        if outcome not in {"succeeded", "failed"}:
            raise CompilerServiceError(
                "malformed_result", "CompileResult has invalid outcome"
            )
        if exit_code != (0 if outcome == "succeeded" else 2):
            raise CompilerServiceError(
                "malformed_result",
                "compiler exit status contradicts CompileResult outcome",
            )
        diagnostics = result.get("diagnostics")
        if not isinstance(diagnostics, list) or len(diagnostics) > self.max_diagnostics:
            raise CompilerServiceError(
                "malformed_result",
                "CompileResult diagnostic collection is invalid or unbounded",
            )
        expected_source_id = canonical_source_id(source)
        source_size = len(source.encode("utf-8"))
        for diagnostic in diagnostics:
            if not isinstance(diagnostic, dict):
                raise CompilerServiceError(
                    "malformed_result", "diagnostic must be an object"
                )
            if not isinstance(diagnostic.get("code"), str):
                raise CompilerServiceError(
                    "malformed_result", "diagnostic code is missing"
                )
            if diagnostic.get("severity") not in {"error", "warning", "info", "hint"}:
                raise CompilerServiceError(
                    "malformed_result", "diagnostic severity is invalid"
                )
            if not isinstance(diagnostic.get("message"), str):
                raise CompilerServiceError(
                    "malformed_result", "diagnostic message is missing"
                )
            for location in _diagnostic_locations(diagnostic):
                _validate_source_span(location, expected_source_id, source_size)


def _diagnostic_locations(diagnostic: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    primary = diagnostic.get("primary_location")
    if isinstance(primary, Mapping):
        yield primary
    related = diagnostic.get("related_locations")
    if isinstance(related, list):
        for item in related:
            if isinstance(item, Mapping) and isinstance(item.get("location"), Mapping):
                yield item["location"]
    fixes = diagnostic.get("fixes")
    if isinstance(fixes, list):
        for fix in fixes:
            if not isinstance(fix, Mapping):
                continue
            edits = fix.get("edits")
            if isinstance(edits, list):
                for edit in edits:
                    if isinstance(edit, Mapping) and isinstance(
                        edit.get("span"), Mapping
                    ):
                        yield edit["span"]


def _validate_source_span(
    span: Mapping[str, Any], expected_source_id: str, source_size: int
) -> None:
    if span.get("source_id") != expected_source_id:
        raise CompilerServiceError("malformed_result", "source span identity is stale")
    if span.get("coordinate_system") != "utf8-bytes":
        raise CompilerServiceError("malformed_result", "source span is not UTF-8 bytes")
    start = span.get("start")
    end = span.get("end")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or not 0 <= start <= end <= source_size
    ):
        raise CompilerServiceError("malformed_result", "source span bounds are invalid")


def _validate_encoding(encoding: str) -> None:
    if encoding not in SUPPORTED_POSITION_ENCODINGS:
        raise ValueError(f"unsupported LSP position encoding {encoding!r}")


def byte_offset_to_position(
    source: str, offset: int, encoding: str
) -> ProjectedPosition:
    """Convert a canonical UTF-8 byte offset into an LSP position."""

    _validate_encoding(encoding)
    encoded = source.encode("utf-8")
    if not 0 <= offset <= len(encoded):
        raise ValueError("UTF-8 byte offset is outside the source")
    try:
        prefix = encoded[:offset].decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("UTF-8 byte offset splits a scalar value") from error
    line = prefix.count("\n")
    tail = prefix.rsplit("\n", 1)[-1]
    if tail.endswith("\r"):
        tail = tail[:-1]
    if encoding == "utf-8":
        character = len(tail.encode("utf-8"))
    elif encoding == "utf-16":
        character = len(tail.encode("utf-16-le")) // 2
    else:
        character = len(tail)
    return ProjectedPosition(line=line, character=character)


def position_to_byte_offset(
    source: str, line: int, character: int, encoding: str
) -> int:
    """Convert an LSP position into a canonical UTF-8 byte offset."""

    _validate_encoding(encoding)
    if line < 0 or character < 0:
        raise ValueError("LSP position cannot be negative")
    lines = source.split("\n")
    if line >= len(lines):
        raise ValueError("LSP line is outside the source")
    content = lines[line]
    if content.endswith("\r"):
        content = content[:-1]
    units = 0
    scalar_index = 0
    for scalar_index, scalar in enumerate(content):
        scalar_units = (
            len(scalar.encode("utf-8"))
            if encoding == "utf-8"
            else len(scalar.encode("utf-16-le")) // 2
            if encoding == "utf-16"
            else 1
        )
        if units == character:
            break
        if units + scalar_units > character:
            raise ValueError("LSP position splits an encoded scalar value")
        units += scalar_units
    else:
        scalar_index = len(content)
    if units != character:
        if scalar_index < len(content):
            scalar = content[scalar_index]
            scalar_units = (
                len(scalar.encode("utf-8"))
                if encoding == "utf-8"
                else len(scalar.encode("utf-16-le")) // 2
                if encoding == "utf-16"
                else 1
            )
            if units + scalar_units == character:
                scalar_index += 1
                units = character
        if units != character:
            raise ValueError("LSP character is outside the line")
    line_prefix = "\n".join(lines[:line])
    byte_start = len(line_prefix.encode("utf-8")) + (1 if line else 0)
    return byte_start + len(content[:scalar_index].encode("utf-8"))


def project_span(
    source: str, start: int, end: int, encoding: str
) -> tuple[ProjectedPosition, ProjectedPosition]:
    if start > end:
        raise ValueError("source span start exceeds end")
    return (
        byte_offset_to_position(source, start, encoding),
        byte_offset_to_position(source, end, encoding),
    )


def diagnostic_payload(
    diagnostic: Mapping[str, Any], source: str, encoding: str
) -> dict[str, Any]:
    severity = {"error": 1, "warning": 2, "info": 3, "hint": 4}[
        str(diagnostic["severity"])
    ]
    location = diagnostic.get("primary_location")
    if isinstance(location, Mapping):
        _validate_source_span(
            location, canonical_source_id(source), len(source.encode("utf-8"))
        )
        start, end = project_span(
            source, int(location["start"]), int(location["end"]), encoding
        )
    else:
        start = end = ProjectedPosition(0, 0)
    return {
        "range": {
            "start": {"line": start.line, "character": start.character},
            "end": {"line": end.line, "character": end.character},
        },
        "message": str(diagnostic["message"]),
        "severity": severity,
        "source": "STRling",
        "code": str(diagnostic["code"]),
        "data": {"canonical": dict(diagnostic)},
    }


def _iter_nodes(
    node: Mapping[str, Any], depth: int = 0
) -> Iterable[tuple[int, Mapping[str, Any]]]:
    yield depth, node
    for key in ("items", "branches"):
        children = node.get(key)
        if isinstance(children, list):
            for child in children:
                if isinstance(child, Mapping) and isinstance(child.get("kind"), str):
                    yield from _iter_nodes(child, depth + 1)
    body = node.get("body")
    if isinstance(body, Mapping) and isinstance(body.get("kind"), str):
        yield from _iter_nodes(body, depth + 1)


def _node_spans(node: Mapping[str, Any], source_id: str) -> Iterable[tuple[int, int]]:
    origin = node.get("origin")
    if not isinstance(origin, Mapping):
        return
    spans = origin.get("source_spans")
    if not isinstance(spans, list):
        return
    for span in spans:
        if (
            isinstance(span, Mapping)
            and span.get("source_id") == source_id
            and span.get("coordinate_system") == "utf8-bytes"
            and isinstance(span.get("start"), int)
            and isinstance(span.get("end"), int)
        ):
            yield int(span["start"]), int(span["end"])


def select_hover_node(
    result: Mapping[str, Any], source: str, cursor_byte: int
) -> tuple[Mapping[str, Any], int, int] | None:
    semantic = result.get("semantic_result")
    if not isinstance(semantic, Mapping) or semantic.get("status") != "complete":
        return None
    program = semantic.get("program")
    if not isinstance(program, Mapping) or not isinstance(program.get("root"), Mapping):
        return None
    source_id = canonical_source_id(source)
    candidates: list[tuple[int, int, int, Mapping[str, Any], int, int]] = []
    for order, (depth, node) in enumerate(_iter_nodes(program["root"])):
        for start, end in _node_spans(node, source_id):
            contains = start == end == cursor_byte or start <= cursor_byte < end
            if contains:
                candidates.append((end - start, -depth, order, node, start, end))
    if not candidates:
        return None
    _, _, _, node, start, end = min(candidates, key=lambda candidate: candidate[:3])
    return node, start, end


def render_hover(
    result: Mapping[str, Any], source: str, cursor_byte: int
) -> HoverEvidence | None:
    selected = select_hover_node(result, source, cursor_byte)
    if selected is None:
        return None
    node, start, end = selected
    node_id = str(node["node_id"])
    kind = str(node["kind"])
    sections: list[str] = [_render_construct(node)]

    capture = _render_capture(node)
    if capture:
        sections.append(capture)

    analysis = result.get("analysis")
    if isinstance(analysis, Mapping):
        facts = analysis.get("node_facts")
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, Mapping) and fact.get("node_id") == node_id:
                    sections.append(_render_analysis(fact))
                    break

    safety = _render_safety(result, start, end)
    if safety:
        sections.append(safety)
    portability = _render_portability(result, node_id)
    if portability:
        sections.append(portability)

    return HoverEvidence(
        markdown="\n\n".join(sections),
        start=start,
        end=end,
        node_id=node_id,
        node_kind=kind,
    )


def _render_construct(node: Mapping[str, Any]) -> str:
    kind = str(node["kind"])
    lines = [f"**STRling construct: `{kind}`**", "", f"- Node: `{node['node_id']}`"]
    if kind == "sequence":
        lines.append(f"- Items: `{len(node.get('items', []))}`")
    elif kind == "alternation":
        lines.append(f"- Branches: `{len(node.get('branches', []))}`")
    elif kind == "literal":
        lines.append(f"- Text: `{_markdown_code(str(node.get('text', '')))}`")
    elif kind == "wildcard":
        lines.append(f"- Line terminators: `{node.get('line_terminators')}`")
    elif kind == "character_set":
        lines.append(f"- Negated: `{str(bool(node.get('negated'))).lower()}`")
        lines.append(f"- Members: `{len(node.get('members', []))}`")
    elif kind == "repeat":
        maximum = "unbounded" if node.get("max") is None else str(node.get("max"))
        lines.append(f"- Repetition: `{node.get('min')}..{maximum}`")
        lines.append(f"- Mode: `{node.get('mode')}`")
    elif kind == "position":
        lines.append(f"- Position: `{node.get('position')}`")
    elif kind == "lookaround":
        lines.append(f"- Direction: `{node.get('direction')}`")
        lines.append(f"- Polarity: `{node.get('polarity')}`")
    return "\n".join(lines)


def _render_capture(node: Mapping[str, Any]) -> str | None:
    if node.get("kind") not in {"capture", "backreference"}:
        return None
    lines = ["**Capture evidence**", "", f"- Capture ID: `{node.get('capture_id')}`"]
    if node.get("name") is not None:
        lines.append(f"- Name: `{_markdown_code(str(node['name']))}`")
    return "\n".join(lines)


def _render_analysis(fact: Mapping[str, Any]) -> str:
    lines = ["**Canonical analysis**", ""]
    if "nullable" in fact:
        lines.append(f"- Nullable: `{str(bool(fact['nullable'])).lower()}`")
    bounds = fact.get("length_bounds")
    if isinstance(bounds, Mapping):
        maximum = "unbounded" if bounds.get("max") is None else str(bounds.get("max"))
        lines.append(
            f"- Length: `{bounds.get('min')}..{maximum}` `{bounds.get('unit')}`"
        )
    return "\n".join(lines)


def _render_safety(result: Mapping[str, Any], start: int, end: int) -> str | None:
    entries: list[str] = []
    diagnostics = result.get("diagnostics")
    if not isinstance(diagnostics, list):
        return None
    for diagnostic in diagnostics:
        if (
            not isinstance(diagnostic, Mapping)
            or diagnostic.get("category") != "safety"
        ):
            continue
        location = diagnostic.get("primary_location")
        if not isinstance(location, Mapping):
            continue
        diagnostic_start = int(location["start"])
        diagnostic_end = int(location["end"])
        if diagnostic_end < start or end < diagnostic_start:
            continue
        entries.append(
            f"- `{diagnostic.get('code')}` `{diagnostic.get('severity')}`: "
            f"{diagnostic.get('message')}"
        )
    if not entries:
        return None
    return "\n".join(["**Safety evidence**", "", *entries])


def _render_portability(result: Mapping[str, Any], node_id: str) -> str | None:
    portability = result.get("portability")
    if not isinstance(portability, Mapping):
        return None
    decisions = portability.get("decisions")
    if not isinstance(decisions, list):
        return None
    matching = [
        decision
        for decision in decisions
        if isinstance(decision, Mapping)
        and isinstance(decision.get("node_ids"), list)
        and node_id in decision["node_ids"]
    ]
    if not matching:
        return None
    profile = portability.get("target_profile")
    if not isinstance(profile, Mapping):
        return None
    lines = [
        "**Target portability**",
        "",
        f"- Target: `{profile.get('profile_id')}@{profile.get('profile_version')}`",
    ]
    for decision in matching:
        lines.append(
            f"- `{decision.get('capability_id')}`: `{decision.get('status')}` "
            f"(`{decision.get('reason_code')}`)"
        )
    return "\n".join(lines)


def _markdown_code(value: str) -> str:
    return value.replace("`", "\\`").replace("\n", "\\n").replace("\r", "\\r")
