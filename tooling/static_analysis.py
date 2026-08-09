#!/usr/bin/env python3
"""Deterministic helpers for native static-analysis commands."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tokenize
from collections import Counter
from dataclasses import dataclass
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent
RUFF_SCOPES = {
    "repository": [
        "tooling",
        "--exclude",
        "tooling/lsp-server/pygls",
        "--exclude",
        "tooling/lsp-server/lsprotocol",
    ],
    "lsp": [
        "tooling/lsp-server",
        "--exclude",
        "tooling/lsp-server/pygls",
        "--exclude",
        "tooling/lsp-server/lsprotocol",
    ],
    "python": ["bindings/python/src", "bindings/python/tests"],
}
NATIVE_SCOPES = {
    "perl": ("bindings/perl", ("lib/**/*.pm",)),
    "php": ("bindings/php", ("src/**/*.php", "tests/**/*.php")),
    "ruby": ("bindings/ruby", ("lib/**/*.rb", "test/**/*.rb", "spec/**/*.rb")),
}
POLICY_PATH = ROOT / "governance" / "static-analysis.json"


@dataclass(frozen=True)
class Suppression:
    path: str
    line: int
    kind: str
    directive: str


def _detectors(path: Path) -> list[tuple[str, re.Pattern[str]]]:
    suffix = path.suffix.lower()
    name = path.name
    if suffix == ".py":
        return [
            (
                "python",
                re.compile(
                    r"#\s*(?:noqa\b|type:\s*ignore\b|pyright:\s*ignore\b|"
                    r"mypy:\s*ignore\b|pylint:\s*disable\b)",
                    re.IGNORECASE,
                ),
            )
        ]
    if suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        return [
            (
                "typescript",
                re.compile(
                    r"@ts-(?:ignore|expect-error|nocheck)\b|eslint-disable\b|"
                    r"\bignoreCodes\s*:",
                    re.IGNORECASE,
                ),
            )
        ]
    if suffix == ".rs":
        return [("rust", re.compile(r"#(?:!)?\[allow\s*\(", re.IGNORECASE))]
    if suffix == ".cs":
        return [
            (
                "csharp",
                re.compile(r"#pragma\s+warning\s+disable\b", re.IGNORECASE),
            )
        ]
    if suffix == ".java":
        return [("java", re.compile(r"@SuppressWarnings\b|noinspection\b"))]
    if suffix in (".kt", ".kts"):
        return [("kotlin", re.compile(r"@Suppress\s*\(|noinspection\b"))]
    if suffix == ".go":
        return [("go", re.compile(r"//\s*nolint\b", re.IGNORECASE))]
    if suffix == ".rb":
        return [
            (
                "ruby",
                re.compile(r"rubocop:(?:disable|todo)\b", re.IGNORECASE),
            )
        ]
    if suffix == ".php":
        return [
            (
                "php",
                re.compile(r"(?:phpstan-ignore|psalm-suppress)\b", re.IGNORECASE),
            )
        ]
    if suffix == ".lua":
        return [("lua", re.compile(r"luacheck:\s*ignore\b", re.IGNORECASE))]
    if suffix in (".pl", ".pm", ".t"):
        return [("perl", re.compile(r"perlcritic\b", re.IGNORECASE))]
    if suffix == ".swift":
        return [("swift", re.compile(r"swiftlint:disable\b", re.IGNORECASE))]
    if suffix in (".c", ".h", ".cc", ".cpp", ".cxx", ".hh", ".hpp", ".hxx"):
        return [
            (
                "native-pragma",
                re.compile(r"#pragma\s+warning\s+disable\b", re.IGNORECASE),
            )
        ]
    if suffix == ".sh" or name == "gradlew" or path.as_posix() == "strling":
        return [
            (
                "shell",
                re.compile(r"shellcheck\s+disable=", re.IGNORECASE),
            )
        ]
    return []


def detect_line(path: Path, line_number: int, content: str) -> list[Suppression]:
    relative = path.as_posix()
    return [
        Suppression(relative, line_number, kind, match.group(0))
        for kind, detector in _detectors(path)
        for match in detector.finditer(content)
    ]


def tracked_suppressions(
    root: Path, governed_paths: Sequence[str]
) -> list[Suppression]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--", *governed_paths],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"git ls-files failed: {message.strip()}")
    findings: list[Suppression] = []
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative = Path(raw_path.decode("utf-8"))
        if relative.as_posix() == "tooling/static_analysis.py":
            continue
        path = root / relative
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if relative.suffix.lower() == ".py":
            try:
                tokens = tokenize.generate_tokens(StringIO(content).readline)
                for token in tokens:
                    if token.type == tokenize.COMMENT:
                        findings.extend(
                            detect_line(relative, token.start[0], token.string)
                        )
            except (IndentationError, tokenize.TokenError):
                pass
            continue
        lines = content.splitlines()
        for line_number, content in enumerate(lines, start=1):
            findings.extend(detect_line(relative, line_number, content))
    return findings


def validate_suppressions(
    suppression_policy: Mapping[str, object],
    findings: Sequence[Suppression],
    today: date,
) -> list[str]:
    errors: list[str] = []
    classifications = suppression_policy.get("classifications")
    waivers = suppression_policy.get("waivers")
    baseline_total = suppression_policy.get("baseline_total")
    if not isinstance(classifications, list) or not all(
        isinstance(item, str) for item in classifications
    ):
        return ["suppression classifications must be a list of strings"]
    if not isinstance(waivers, list):
        return ["suppression waivers must be a list"]
    if not isinstance(baseline_total, int) or baseline_total < 0:
        return ["suppression baseline_total must be a non-negative integer"]

    expected: dict[str, tuple[str, int]] = {}
    seen_ids: set[str] = set()
    expiring = {
        "bounded_transition",
        "obsolete_removable",
        "suspected_product_defect",
    }
    for raw in waivers:
        if not isinstance(raw, dict):
            errors.append("each suppression waiver must be an object")
            continue
        waiver_id = raw.get("id")
        classification = raw.get("classification")
        reason = raw.get("reason")
        retirement = raw.get("retirement_condition")
        path_counts = raw.get("path_counts")
        if not isinstance(waiver_id, str) or not waiver_id:
            errors.append("suppression waiver requires a non-empty id")
            continue
        if waiver_id in seen_ids:
            errors.append(f"duplicate suppression waiver id: {waiver_id}")
        seen_ids.add(waiver_id)
        if classification not in classifications:
            errors.append(f"{waiver_id}: invalid classification")
        if not isinstance(reason, str) or not reason:
            errors.append(f"{waiver_id}: missing reason")
        if not isinstance(retirement, str) or not retirement:
            errors.append(f"{waiver_id}: missing retirement condition")
        if not isinstance(path_counts, dict) or not path_counts:
            errors.append(f"{waiver_id}: path_counts must be a non-empty object")
            continue
        if classification in expiring:
            expires_on = raw.get("expires_on")
            try:
                expiry = date.fromisoformat(str(expires_on))
            except ValueError:
                errors.append(f"{waiver_id}: invalid or missing expires_on")
            else:
                if expiry < today:
                    errors.append(f"{waiver_id}: expired on {expiry.isoformat()}")
        for path, count in path_counts.items():
            if not isinstance(path, str) or not path:
                errors.append(f"{waiver_id}: waiver path must be non-empty")
                continue
            if not isinstance(count, int) or count <= 0:
                errors.append(f"{waiver_id}: {path} count must be positive")
                continue
            if path in expected:
                errors.append(f"{waiver_id}: duplicate governed path {path}")
                continue
            expected[path] = (waiver_id, count)

    if sum(count for _waiver, count in expected.values()) != baseline_total:
        errors.append("waiver counts do not equal suppression baseline_total")

    actual = Counter(finding.path for finding in findings)
    for path, count in sorted(actual.items()):
        if path not in expected:
            lines = ",".join(
                str(finding.line) for finding in findings if finding.path == path
            )
            errors.append(f"unmanaged suppression: {path}:{lines}")
            continue
        waiver_id, expected_count = expected[path]
        if count != expected_count:
            errors.append(
                f"{waiver_id}: {path} expected {expected_count} suppressions, found {count}"
            )
    for path, (waiver_id, expected_count) in sorted(expected.items()):
        if path not in actual:
            errors.append(
                f"{waiver_id}: {path} expected {expected_count} suppressions, found 0"
            )
    if len(findings) != baseline_total:
        errors.append(
            f"suppression baseline expected {baseline_total}, found {len(findings)}"
        )
    return errors


def run_suppression_audit(
    policy_path: Path = POLICY_PATH, today: date | None = None
) -> int:
    try:
        data = json.loads(policy_path.read_text(encoding="utf-8"))
        suppression_policy = data["suppression_policy"]
        if not isinstance(suppression_policy, dict):
            raise TypeError("suppression_policy must be an object")
        governed_paths = suppression_policy["governed_paths"]
        if not isinstance(governed_paths, list) or not all(
            isinstance(path, str) for path in governed_paths
        ):
            raise TypeError("governed_paths must be a list of strings")
        findings = tracked_suppressions(ROOT, governed_paths)
        errors = validate_suppressions(
            suppression_policy,
            findings,
            today or date.today(),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, RuntimeError) as exc:
        print(f"SUPPRESSION_RESULT status=failed reason={exc}", file=sys.stderr)
        return 2
    for error in errors:
        print(f"SUPPRESSION_FINDING {error}", file=sys.stderr)
    status = "passed" if not errors else "failed"
    print(
        f"SUPPRESSION_RESULT status={status} managed={len(findings)} "
        f"waivers={len(suppression_policy['waivers'])} findings={len(errors)}"
    )
    return 0 if not errors else 1


def _files(base: Path, globs: Iterable[str]) -> list[Path]:
    return sorted({path for pattern in globs for path in base.glob(pattern)})


def _run(command: Sequence[str], cwd: Path, warnings_are_errors: bool = False) -> int:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if completed.stderr:
        print(
            completed.stderr,
            end="" if completed.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )
    if completed.returncode != 0:
        return completed.returncode
    if warnings_are_errors and "warning:" in completed.stderr.lower():
        return 1
    return 0


def run_ruff(component: str) -> int:
    scope = RUFF_SCOPES.get(component)
    if scope is None:
        print(f"unknown Ruff component: {component}", file=sys.stderr)
        return 2
    return _run(["ruff", "check", *scope], ROOT)


def run_native(component: str) -> int:
    scope = NATIVE_SCOPES.get(component)
    if scope is None:
        print(f"unknown native lint component: {component}", file=sys.stderr)
        return 2
    relative_base, globs = scope
    base = ROOT / relative_base
    files = _files(base, globs)
    if not files:
        print(f"no governed source files found for {component}", file=sys.stderr)
        return 2

    failed = 0
    for path in files:
        relative = path.relative_to(base)
        if component == "perl":
            command = ["perl", "-Mwarnings=FATAL", "-Ilib", "-c", str(relative)]
        elif component == "php":
            command = ["php", "-l", str(relative)]
        else:
            command = ["ruby", "-wc", str(relative)]
        result = _run(
            command,
            base,
            warnings_are_errors=component in ("perl", "ruby"),
        )
        if result != 0 and failed == 0:
            failed = result
    return failed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    ruff = subparsers.add_parser("ruff")
    ruff.add_argument("component", choices=sorted(RUFF_SCOPES))

    native = subparsers.add_parser("native")
    native.add_argument("component", choices=sorted(NATIVE_SCOPES))
    subparsers.add_parser("suppressions")
    subparsers.add_parser("repository")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.operation == "ruff":
        return run_ruff(args.component)
    if args.operation == "native":
        return run_native(args.component)
    if args.operation == "suppressions":
        return run_suppression_audit()
    ruff_result = run_ruff("repository")
    suppression_result = run_suppression_audit()
    return ruff_result or suppression_result


if __name__ == "__main__":
    raise SystemExit(main())
