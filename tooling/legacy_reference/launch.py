#!/usr/bin/env python3
"""Build and run independently versioned historical reference implementations."""

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
RUNNER_CHOICES = ("all", "python", "typescript")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run controlled historical STRling reference harnesses."
    )
    parser.add_argument("--runner", choices=RUNNER_CHOICES)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--request", type=Path)
    modes.add_argument("--corpus", action="store_true")
    modes.add_argument("--certify", action="store_true")
    modes.add_argument("--cross-certify", action="store_true")
    return parser.parse_args(argv)


def selected_runner(args: argparse.Namespace) -> str:
    if args.runner is not None:
        return args.runner
    if args.check or args.cross_certify:
        return "all"
    return "typescript"


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


def typescript_environment(output: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["STRLING_LEGACY_REFERENCE_DIST"] = str(output)
    return environment


def run_node(output: Path, arguments: Sequence[str]) -> int:
    completed = subprocess.run(
        ["node", *arguments],
        cwd=ROOT,
        env=typescript_environment(output),
        check=False,
    )
    return completed.returncode


def run_python(arguments: Sequence[str]) -> int:
    completed = subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        check=False,
    )
    return completed.returncode


def emit_protocol_failure(code: str, message: str) -> int:
    if __package__:
        from . import python_reference as python_runner
    else:
        import python_reference as python_runner

    error = python_runner.ProtocolError(code, message)
    sys.stderr.write(
        python_runner.canonical_line(python_runner.protocol_failure(error))
    )
    return 2


def capture_certification(
    command: Sequence[str], **kwargs: object
) -> dict[str, object] | None:
    completed = subprocess.run(
        list(command),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        **kwargs,
    )
    if completed.returncode != 0:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return None
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def run_typescript_check(output: Path) -> int:
    tests = sorted(
        str(path.relative_to(ROOT)) for path in (TOOL_ROOT / "tests").glob("*.test.mjs")
    )
    test_exit = run_node(output, ["--test", *tests])
    if test_exit != 0:
        return test_exit
    return run_node(output, [str(TOOL_ROOT / "corpus_cli.mjs"), "--certify"])


def run_python_check() -> int:
    tests = sorted(
        "tooling.legacy_reference.tests." + path.stem
        for path in (TOOL_ROOT / "tests").glob("test_*.py")
    )
    test_exit = run_python(["-m", "unittest", *tests])
    if test_exit != 0:
        return test_exit
    return run_python([str(TOOL_ROOT / "python_reference.py"), "--certify"])


def run_cross_certification(output: Path) -> int:
    if __package__:
        from . import cross_reference
        from . import python_reference as python_runner
    else:
        import cross_reference
        import python_reference as python_runner

    typescript = capture_certification(
        ["node", str(TOOL_ROOT / "corpus_cli.mjs"), "--certify"],
        env=typescript_environment(output),
    )
    if typescript is None:
        return emit_protocol_failure(
            "CROSS_CERTIFICATION_FAILURE",
            "the TypeScript runner did not produce a valid certification",
        )
    python = capture_certification(
        [sys.executable, str(TOOL_ROOT / "python_reference.py"), "--certify"]
    )
    if python is None:
        return emit_protocol_failure(
            "CROSS_CERTIFICATION_FAILURE",
            "the Python runner did not produce a valid certification",
        )
    try:
        certification = cross_reference.certify_selected_runners(
            typescript,
            python,
        )
    except cross_reference.CrossCertificationError:
        return emit_protocol_failure(
            "CROSS_CERTIFICATION_FAILURE",
            "selected runner certifications could not be composed",
        )
    sys.stdout.write(python_runner.canonical_line(certification))
    return 0


def run_python_mode(args: argparse.Namespace) -> int:
    if args.cross_certify:
        return emit_protocol_failure(
            "INVALID_INVOCATION",
            "--cross-certify requires --runner all",
        )
    if args.check:
        return run_python_check()
    command = [str(TOOL_ROOT / "python_reference.py")]
    if args.request is not None:
        command.extend(["--request", str(args.request)])
    elif args.corpus:
        command.append("--corpus")
    elif args.certify:
        command.append("--certify")
    return run_python(command)


def run_typescript_mode(args: argparse.Namespace, output: Path) -> int:
    if args.cross_certify:
        return emit_protocol_failure(
            "INVALID_INVOCATION",
            "--cross-certify requires --runner all",
        )
    if args.check:
        return run_typescript_check(output)
    if args.corpus or args.certify:
        mode = "--observations" if args.corpus else "--certify"
        return run_node(output, [str(TOOL_ROOT / "corpus_cli.mjs"), mode])
    command = [str(TOOL_ROOT / "cli.mjs")]
    if args.request is not None:
        command.extend(["--request", str(args.request)])
    return run_node(output, command)


def run_all_mode(args: argparse.Namespace, output: Path) -> int:
    if (
        args.request is not None
        or args.corpus
        or not (args.check or args.certify or args.cross_certify)
    ):
        return emit_protocol_failure(
            "INVALID_INVOCATION",
            "--runner all supports only --check, --certify, or --cross-certify",
        )
    if args.check:
        typescript_exit = run_typescript_check(output)
        if typescript_exit != 0:
            return typescript_exit
        python_exit = run_python_check()
        if python_exit != 0:
            return python_exit
    return run_cross_certification(output)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    runner = selected_runner(args)
    if runner == "python":
        return run_python_mode(args)

    with tempfile.TemporaryDirectory(prefix="strling-legacy-reference-") as temporary:
        output = Path(temporary) / "dist"
        build_exit = build_legacy_typescript(output)
        if build_exit != 0:
            return build_exit
        if runner == "typescript":
            return run_typescript_mode(args, output)
        return run_all_mode(args, output)


if __name__ == "__main__":
    raise SystemExit(main())
