#!/usr/bin/env python3
"""Build the governed TypeScript sources in isolation and run reference tooling."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = ROOT / "tooling" / "legacy_reference"
TYPESCRIPT_ROOT = ROOT / "bindings" / "typescript"
TSC = TYPESCRIPT_ROOT / "node_modules" / "typescript" / "bin" / "tsc"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the controlled legacy TypeScript reference harness."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--request", type=Path)
    return parser.parse_args(argv)


def build_legacy_typescript(output: Path) -> int:
    if not TSC.is_file():
        print(
            "legacy reference setup failure: governed TypeScript dependencies "
            "are not installed; run ./strling setup typescript",
            file=sys.stderr,
        )
        return 3
    completed = subprocess.run(
        [
            "node",
            str(TSC),
            "-p",
            str(TYPESCRIPT_ROOT / "tsconfig.json"),
            "--outDir",
            str(output),
        ],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        return completed.returncode
    (output / "package.json").write_text(
        json.dumps({"private": True, "type": "module"}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


def run_node(output: Path, arguments: Sequence[str]) -> int:
    environment = os.environ.copy()
    environment["STRLING_LEGACY_REFERENCE_DIST"] = str(output)
    completed = subprocess.run(
        ["node", *arguments],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    return completed.returncode


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check and args.request is not None:
        print("--check and --request are mutually exclusive", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="strling-legacy-reference-") as temporary:
        output = Path(temporary) / "dist"
        build_exit = build_legacy_typescript(output)
        if build_exit != 0:
            return build_exit

        if args.check:
            tests = sorted(
                str(path.relative_to(ROOT))
                for path in (TOOL_ROOT / "tests").glob("*.test.mjs")
            )
            return run_node(output, ["--test", *tests])

        command = [str(TOOL_ROOT / "cli.mjs")]
        if args.request is not None:
            command.extend(["--request", str(args.request)])
        return run_node(output, command)


if __name__ == "__main__":
    raise SystemExit(main())
