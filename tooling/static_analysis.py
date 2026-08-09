#!/usr/bin/env python3
"""Deterministic helpers for native static-analysis commands."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.operation == "ruff":
        return run_ruff(args.component)
    return run_native(args.component)


if __name__ == "__main__":
    raise SystemExit(main())
