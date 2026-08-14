#!/usr/bin/env python3
"""Run the canonical STRling formatters over policy-selected tracked files."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "governance" / "formatting.json"
Runner = Callable[[Sequence[str], Path], int]
MAXIMUM_BATCH_ARGUMENT_CHARACTERS = 4_000


class FormattingConfigurationError(ValueError):
    """Raised when the formatting policy cannot produce a deterministic run."""


def load_policy(path: Path = POLICY_PATH) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise FormattingConfigurationError(
            f"cannot read formatting policy: {exc}"
        ) from exc
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise FormattingConfigurationError("unsupported formatting policy schema")
    enforcement = policy.get("enforcement")
    if not isinstance(enforcement, dict) or not isinstance(
        enforcement.get("targets"), dict
    ):
        raise FormattingConfigurationError(
            "formatting policy must define enforcement targets"
        )
    return policy


def tracked_files(root: Path = ROOT) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise FormattingConfigurationError(
            f"cannot inventory tracked files: {exc}"
        ) from exc
    if completed.returncode != 0:
        details = completed.stderr.decode("utf-8", errors="replace").strip()
        raise FormattingConfigurationError(
            f"git tracked-file inventory failed: {details}"
        )
    return sorted(
        item.decode("utf-8", errors="strict").replace("\\", "/")
        for item in completed.stdout.split(b"\0")
        if item
    )


def matches(path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def select_files(
    inventory: Sequence[str],
    include: Sequence[str],
    exclude: Sequence[str],
) -> list[str]:
    return [
        path
        for path in inventory
        if matches(path, include) and not matches(path, exclude)
    ]


def file_batches(files: Sequence[str]) -> list[list[str]]:
    """Bound formatter arguments below conservative cross-platform limits."""

    batches: list[list[str]] = []
    current: list[str] = []
    current_size = 0
    for path in files:
        path_size = len(path) + 1
        if current and current_size + path_size > MAXIMUM_BATCH_ARGUMENT_CHARACTERS:
            batches.append(current)
            current = []
            current_size = 0
        current.append(path)
        current_size += path_size
    if current:
        batches.append(current)
    return batches


def build_command(
    formatter: str,
    check: bool,
    files: Sequence[str],
    arguments: Sequence[str],
    root: Path = ROOT,
) -> list[str]:
    if formatter == "prettier":
        executable = root / "node_modules" / ".bin" / "prettier"
        prefix = [str(executable)]
        if os.name == "nt":
            prefix = [
                "node",
                str(root / "node_modules" / "prettier" / "bin" / "prettier.cjs"),
            ]
        mode = "--check" if check else "--write"
        return [
            *prefix,
            mode,
            "--config",
            str(root / ".prettierrc"),
            *files,
        ]
    if formatter == "ruff-format":
        mode = ["--check"] if check else []
        prefix = ["ruff"]
        if os.name == "nt":
            prefix = [sys.executable, "-m", "ruff"]
        return [*prefix, "format", *mode, *files]
    if formatter == "dart-format":
        mode = ["--output=none", "--set-exit-if-changed"] if check else []
        return ["dart", "format", *mode, *files]
    if formatter == "dotnet-format":
        mode = ["--verify-no-changes"] if check else []
        return ["dotnet", "format", *arguments, *mode]
    raise FormattingConfigurationError(f"unknown formatter adapter '{formatter}'")


def run_process(command: Sequence[str], root: Path) -> int:
    try:
        completed = subprocess.run(list(command), cwd=root, check=False)
    except OSError as exc:
        print(f"formatter process failed to start: {exc}", file=sys.stderr)
        return 127
    return completed.returncode


def format_target(
    target: str,
    check: bool,
    policy: Mapping[str, object],
    inventory: Sequence[str],
    runner: Runner = run_process,
    root: Path = ROOT,
) -> int:
    enforcement = policy["enforcement"]
    assert isinstance(enforcement, dict)
    targets = enforcement["targets"]
    assert isinstance(targets, dict)
    raw_steps = targets.get(target)
    if not isinstance(raw_steps, list) or not raw_steps:
        raise FormattingConfigurationError(
            f"component '{target}' has no formatter enforcement definition"
        )

    overall = 0
    for raw_step in raw_steps:
        if not isinstance(raw_step, dict):
            raise FormattingConfigurationError(
                f"component '{target}' contains an invalid formatter step"
            )
        formatter = raw_step.get("formatter")
        include = raw_step.get("include", [])
        exclude = raw_step.get("exclude", [])
        arguments = raw_step.get("arguments", [])
        if not isinstance(formatter, str):
            raise FormattingConfigurationError(
                f"component '{target}' formatter must be a string"
            )
        if not all(
            isinstance(value, list) and all(isinstance(item, str) for item in value)
            for value in (include, exclude, arguments)
        ):
            raise FormattingConfigurationError(
                f"component '{target}' formatter lists must contain strings"
            )

        files = select_files(inventory, include, exclude)
        if not arguments and not files:
            raise FormattingConfigurationError(
                f"component '{target}' formatter '{formatter}' selected no tracked files"
            )
        exit_code = 0
        batches = file_batches(files) if files else [[]]
        for batch in batches:
            result = runner(
                build_command(formatter, check, batch, arguments, root), root
            )
            if result != 0 and exit_code == 0:
                exit_code = result
        status = "passed" if exit_code == 0 else "failed"
        print(
            "FORMATTER_RESULT "
            f"formatter={formatter} component={target} "
            f"status={status} exit_code={exit_code}"
        )
        if exit_code != 0 and overall == 0:
            overall = exit_code
    return overall


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="toolchain component to format")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify canonical formatting without writing files",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        policy = load_policy()
        return format_target(
            args.target,
            args.check,
            policy,
            tracked_files(),
        )
    except FormattingConfigurationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
