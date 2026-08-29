#!/usr/bin/env python3
"""Validate deterministic documentation and executable-example integrity."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Sequence
from urllib.parse import unquote, urlsplit


SCHEMA_VERSION = "1.0.0"
OPERATION_ID = "documentation.integrity"
STATUSES = ("passed", "failed", "waived", "unavailable", "incomplete")
EXIT_CODES = {"passed": 0, "failed": 1, "waived": 0, "unavailable": 2, "incomplete": 3}

INLINE_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
REFERENCE_USE_RE = re.compile(r"(?<!!)\[[^\]]+\]\[([^\]]+)\]")
REFERENCE_DEF_RE = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)")
HTML_LINK_RE = re.compile(
    r"<(?:a|img)\b[^>]*(?:href|src)=[\"']([^\"']+)[\"']", re.IGNORECASE
)
FENCE_RE = re.compile(r"^\s*(```|~~~)")

EXCLUDED_MARKDOWN = ("docs/templates/**",)
EXCLUDED_REASON = (
    "Documentation templates contain destination-relative placeholder links and are "
    "not repository documents."
)

LIMITATIONS = (
    {
        "capability": "external-link-reachability",
        "reason": "External network link checks are intentionally excluded from this offline operation.",
    },
    {
        "capability": "markdown-anchor-validation",
        "reason": "No governed GitHub-Flavored Markdown anchor implementation is currently pinned.",
    },
)

DELEGATED_OPERATIONS = (
    {
        "capability": "canonical-contract-examples",
        "operation": "canonical_contracts_check",
    },
    {
        "capability": "generated-documentation-consistency",
        "operation": "generate_check",
    },
)


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    path: str
    line: int | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }
        if self.line is not None:
            result["line"] = self.line
        return result


@dataclass(frozen=True)
class Check:
    check_id: str
    status: str
    summary: str
    findings: tuple[Finding, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "summary": self.summary,
            "findings": [finding.as_dict() for finding in self.findings],
        }


def _tracked_markdown(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [root / item for item in sorted(completed.stdout.splitlines()) if item]


def _excluded(relative: str) -> bool:
    path = PurePosixPath(relative)
    return any(path.match(pattern) for pattern in EXCLUDED_MARKDOWN)


def _target_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")]
    return value.split(maxsplit=1)[0]


def _is_local_target(target: str) -> bool:
    parsed = urlsplit(target)
    return not parsed.scheme and not parsed.netloc and bool(parsed.path)


def _validate_target(
    root: Path, source: Path, target: str, line: int
) -> Finding | None:
    value = _target_value(target)
    if not _is_local_target(value):
        return None
    parsed = urlsplit(value)
    decoded = unquote(parsed.path).replace("\\", "/")
    if decoded.startswith("/"):
        candidate = root / decoded.lstrip("/")
    else:
        candidate = source.parent / decoded
    if candidate.exists():
        return None
    return Finding(
        code="DOC-LINK-MISSING",
        message=f"Local documentation target does not exist: {value}",
        path=source.relative_to(root).as_posix(),
        line=line,
    )


def _visible_lines(text: str) -> Iterable[tuple[int, str]]:
    in_fence = False
    marker = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        fence = FENCE_RE.match(line)
        if fence:
            current = fence.group(1)
            if not in_fence:
                in_fence = True
                marker = current[:3]
            elif current.startswith(marker):
                in_fence = False
                marker = ""
            continue
        if not in_fence:
            yield line_number, re.sub(r"`[^`]*`", "", line)


def scan_markdown_links(
    root: Path, markdown_files: Sequence[Path] | None = None
) -> Check:
    files = (
        list(markdown_files) if markdown_files is not None else _tracked_markdown(root)
    )
    findings: list[Finding] = []
    scanned = 0
    for source in sorted(files):
        # A contained task may intentionally delete a tracked document before
        # its checkpoint commit. Git still reports that path through
        # ``ls-files``; only present documents can contain live link authority.
        if not source.is_file():
            continue
        relative = source.relative_to(root).as_posix()
        if _excluded(relative):
            continue
        scanned += 1
        lines = tuple(_visible_lines(source.read_text(encoding="utf-8")))
        definitions: dict[str, tuple[str, int]] = {}
        for line_number, line in lines:
            definition = REFERENCE_DEF_RE.match(line)
            if definition:
                definitions[definition.group(1).casefold()] = (
                    definition.group(2),
                    line_number,
                )

        for line_number, line in lines:
            definition = REFERENCE_DEF_RE.match(line)
            if definition:
                finding = _validate_target(
                    root, source, definition.group(2), line_number
                )
                if finding:
                    findings.append(finding)
                continue
            for match in INLINE_LINK_RE.finditer(line):
                finding = _validate_target(root, source, match.group(1), line_number)
                if finding:
                    findings.append(finding)
            for match in HTML_LINK_RE.finditer(line):
                finding = _validate_target(root, source, match.group(1), line_number)
                if finding:
                    findings.append(finding)
            for match in REFERENCE_USE_RE.finditer(line):
                reference = match.group(1).casefold()
                if reference not in definitions:
                    findings.append(
                        Finding(
                            code="DOC-REFERENCE-UNDEFINED",
                            message=f"Markdown reference is not defined: {match.group(1)}",
                            path=relative,
                            line=line_number,
                        )
                    )

    if findings:
        return Check(
            check_id="documentation.links",
            status="failed",
            summary=f"Found {len(findings)} broken local documentation reference(s) across {scanned} file(s).",
            findings=tuple(findings),
        )
    return Check(
        check_id="documentation.links",
        status="passed",
        summary=f"Validated local documentation references across {scanned} file(s).",
    )


def _execute_example(
    root: Path,
    relative: str,
    expected_exit: int,
    execute: Callable[..., subprocess.CompletedProcess[str]],
) -> Finding | None:
    conventional_cargo = (
        Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    )
    cargo = (
        os.environ.get("CARGO")
        or shutil.which("cargo")
        or (str(conventional_cargo) if conventional_cargo.is_file() else "cargo")
    )
    completed = execute(
        [
            cargo,
            "run",
            "--quiet",
            "--manifest-path",
            "core/internal/Cargo.toml",
            "--bin",
            "strling-kernel",
            "--",
            "import",
            "--format",
            "json",
            "--input",
            relative,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == expected_exit:
        return None
    return Finding(
        code="DOC-EXAMPLE-EXIT",
        message=(
            f"Expected canonical import exit {expected_exit}, "
            f"observed {completed.returncode}."
        ),
        path=relative,
    )


def check_executable_examples(
    root: Path,
    execute: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Check:
    examples_root = root / "tooling/lsp-server/examples"
    expected: list[tuple[str, int]] = [
        ("tooling/lsp-server/examples/valid_patterns.strl", 0),
        ("tooling/lsp-server/examples/invalid_patterns.strl", 2),
    ]
    expected.extend(
        (path.relative_to(root).as_posix(), 2)
        for path in sorted((examples_root / "errors").glob("*.strl"))
    )
    findings: list[Finding] = []
    for relative, expected_exit in expected:
        path = root / relative
        if not path.is_file():
            findings.append(
                Finding(
                    code="DOC-EXAMPLE-MISSING",
                    message="Governed executable example is missing.",
                    path=relative,
                )
            )
            continue
        finding = _execute_example(root, relative, expected_exit, execute)
        if finding:
            findings.append(finding)

    readme = examples_root / "README.md"
    required_commands = (
        "python3 tooling/parse_strl.py tooling/lsp-server/examples/valid_patterns.strl",
        "python3 tooling/parse_strl.py - < tooling/lsp-server/examples/valid_patterns.strl",
    )
    if not readme.is_file():
        findings.append(
            Finding(
                code="DOC-EXAMPLE-README-MISSING",
                message="Executable-example instructions are missing.",
                path=readme.relative_to(root).as_posix(),
            )
        )
    else:
        content = readme.read_text(encoding="utf-8")
        for command in required_commands:
            if command not in content:
                findings.append(
                    Finding(
                        code="DOC-EXAMPLE-COMMAND-STALE",
                        message=f"Canonical executable-example command is absent: {command}",
                        path=readme.relative_to(root).as_posix(),
                    )
                )

    if findings:
        return Check(
            check_id="documentation.executable-examples",
            status="failed",
            summary=f"Found {len(findings)} executable-example integrity failure(s).",
            findings=tuple(findings),
        )
    return Check(
        check_id="documentation.executable-examples",
        status="passed",
        summary=(
            f"Validated {len(expected)} executable canonical CLI example(s) "
            "and their documented commands."
        ),
    )


def aggregate_status(checks: Sequence[Check]) -> str:
    precedence = ("failed", "incomplete", "unavailable", "waived", "passed")
    statuses = {check.status for check in checks}
    return next(status for status in precedence if status in statuses)


def build_result(checks: Sequence[Check]) -> dict[str, object]:
    ordered = sorted(checks, key=lambda item: item.check_id)
    status = aggregate_status(ordered)
    counts = {
        candidate: sum(check.status == candidate for check in ordered)
        for candidate in STATUSES
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "operation_id": OPERATION_ID,
        "status": status,
        "engine": {
            "name": "strling-documentation-integrity",
            "version": SCHEMA_VERSION,
            "network_policy": "offline",
        },
        "checks": [check.as_dict() for check in ordered],
        "summary": {"total": len(ordered), **counts},
        "coverage": {
            "excluded_paths": [
                {"pattern": pattern, "reason": EXCLUDED_REASON}
                for pattern in EXCLUDED_MARKDOWN
            ],
            "delegated_operations": list(DELEGATED_OPERATIONS),
            "limitations": list(LIMITATIONS),
        },
    }


def validate_result(result: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if result.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if result.get("operation_id") != OPERATION_ID:
        errors.append(f"operation_id must be {OPERATION_ID}")
    checks = result.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("checks must be a non-empty list")
        return errors
    check_ids: list[str] = []
    statuses: list[str] = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"checks[{index}] must be an object")
            continue
        check_id = check.get("check_id")
        status = check.get("status")
        if not isinstance(check_id, str) or not check_id:
            errors.append(f"checks[{index}].check_id must be a non-empty string")
        else:
            check_ids.append(check_id)
        if status not in STATUSES:
            errors.append(f"checks[{index}].status is invalid")
        else:
            statuses.append(str(status))
        if not isinstance(check.get("summary"), str):
            errors.append(f"checks[{index}].summary must be a string")
        if not isinstance(check.get("findings"), list):
            errors.append(f"checks[{index}].findings must be a list")
    if check_ids != sorted(check_ids) or len(check_ids) != len(set(check_ids)):
        errors.append("checks must have unique check_ids in deterministic order")
    if statuses:
        expected = next(
            candidate
            for candidate in ("failed", "incomplete", "unavailable", "waived", "passed")
            if candidate in statuses
        )
        if result.get("status") != expected:
            errors.append(f"status must aggregate to {expected}")
        summary = result.get("summary")
        if not isinstance(summary, dict):
            errors.append("summary must be an object")
        else:
            if summary.get("total") != len(statuses):
                errors.append("summary.total must match checks")
            for candidate in STATUSES:
                if summary.get(candidate) != statuses.count(candidate):
                    errors.append(f"summary.{candidate} must match checks")
    return errors


def run(root: Path) -> dict[str, object]:
    return build_result((check_executable_examples(root), scan_markdown_links(root)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Emit the structured operation result."
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    result = run(root)
    errors = validate_result(result)
    if errors:
        result = build_result(
            (
                Check(
                    check_id="documentation.result-contract",
                    status="incomplete",
                    summary="Documentation result failed its internal contract.",
                    findings=tuple(
                        Finding(
                            code="DOC-RESULT-CONTRACT",
                            message=error,
                            path="tooling/documentation_integrity.py",
                        )
                        for error in errors
                    ),
                ),
            )
        )
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"documentation integrity: {str(result['status']).upper()}")
        for check in result["checks"]:
            assert isinstance(check, dict)
            print(
                f"- {str(check['status']).upper():11} {check['check_id']}: {check['summary']}"
            )
    return EXIT_CODES[str(result["status"])]


if __name__ == "__main__":
    raise SystemExit(main())
