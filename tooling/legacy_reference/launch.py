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
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = ROOT / "tooling" / "legacy_reference"
TYPESCRIPT_ROOT = ROOT / "bindings" / "typescript"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tooling import typescript_python_adapter_certification as adapter_evidence  # noqa: E402


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
    modes.add_argument("--comparison-certify", action="store_true")
    return parser.parse_args(argv)


def selected_runner(args: argparse.Namespace) -> str:
    if args.runner is not None:
        return args.runner
    if args.check or args.cross_certify or args.comparison_certify:
        return "all"
    return "typescript"


def build_legacy_typescript(snapshot_root: Path, output: Path) -> int:
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
            str(snapshot_root / "bindings" / "typescript" / "tsconfig.json"),
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


def frozen_environment(snapshot_root: Path, output: Path) -> dict[str, str]:
    environment = typescript_environment(output)
    environment["STRLING_LEGACY_REFERENCE_SOURCE_ROOT"] = str(snapshot_root)
    environment["STRLING_LEGACY_REFERENCE_PYTHON_SOURCE"] = str(
        snapshot_root / "bindings" / "python" / "src"
    )
    return environment


def run_node(
    output: Path,
    arguments: Sequence[str],
    environment: Mapping[str, str] | None = None,
) -> int:
    completed = subprocess.run(
        ["node", *arguments],
        cwd=ROOT,
        env=dict(environment)
        if environment is not None
        else typescript_environment(output),
        check=False,
    )
    return completed.returncode


def run_python(arguments: Sequence[str], environment: Mapping[str, str]) -> int:
    completed = subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        env=environment,
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


def run_typescript_check(
    output: Path, environment: Mapping[str, str] | None = None
) -> int:
    tests = sorted(
        str(path.relative_to(ROOT)) for path in (TOOL_ROOT / "tests").glob("*.test.mjs")
    )
    test_exit = run_node(output, ["--test", *tests], environment)
    if test_exit != 0:
        return test_exit
    return run_node(
        output, [str(TOOL_ROOT / "corpus_cli.mjs"), "--certify"], environment
    )


def run_python_check(environment: Mapping[str, str]) -> int:
    tests = sorted(
        "tooling.legacy_reference.tests." + path.stem
        for path in (TOOL_ROOT / "tests").glob("test_*.py")
    )
    test_exit = run_python(["-m", "unittest", *tests], environment)
    if test_exit != 0:
        return test_exit
    return run_python(
        [str(TOOL_ROOT / "python_reference.py"), "--certify"], environment
    )


def run_cross_certification(output: Path, environment: Mapping[str, str]) -> int:
    if __package__:
        from . import cross_reference
        from . import python_reference as python_runner
    else:
        import cross_reference
        import python_reference as python_runner

    typescript = capture_certification(
        ["node", str(TOOL_ROOT / "corpus_cli.mjs"), "--certify"],
        env=environment,
    )
    if typescript is None:
        return emit_protocol_failure(
            "CROSS_CERTIFICATION_FAILURE",
            "the TypeScript runner did not produce a valid certification",
        )
    python = capture_certification(
        [sys.executable, str(TOOL_ROOT / "python_reference.py"), "--certify"],
        env=environment,
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


def run_comparison_certification(
    output: Path, environment: Mapping[str, str], repeat_runs: int = 3
) -> int:
    from tooling import migration_comparison_certification as comparison

    if __package__:
        from . import python_reference as python_runner
    else:
        import python_reference as python_runner

    batches: dict[str, list[dict[str, object]]] = {
        "python": [],
        "typescript": [],
    }
    for _ in range(repeat_runs):
        typescript = capture_certification(
            ["node", str(TOOL_ROOT / "corpus_cli.mjs"), "--observations"],
            env=environment,
        )
        if typescript is None:
            return emit_protocol_failure(
                "COMPARISON_CERTIFICATION_FAILURE",
                "the TypeScript runner did not produce a valid observation batch",
            )
        python = capture_certification(
            [sys.executable, str(TOOL_ROOT / "python_reference.py"), "--corpus"],
            env=environment,
        )
        if python is None:
            return emit_protocol_failure(
                "COMPARISON_CERTIFICATION_FAILURE",
                "the Python runner did not produce a valid observation batch",
            )
        batches["typescript"].append(typescript)
        batches["python"].append(python)
    try:
        certification = comparison.certify_historical_batches(
            batches,
            repeat_runs=repeat_runs,
        )
    except comparison.CertificationError:
        return emit_protocol_failure(
            "COMPARISON_CERTIFICATION_FAILURE",
            "selected runner observations could not be compared deterministically",
        )
    sys.stdout.write(python_runner.canonical_line(certification))
    return 0


def run_python_mode(args: argparse.Namespace, environment: Mapping[str, str]) -> int:
    if args.cross_certify or args.comparison_certify:
        return emit_protocol_failure(
            "INVALID_INVOCATION",
            "cross-runner certification modes require --runner all",
        )
    if args.check:
        return run_python_check(environment)
    command = [str(TOOL_ROOT / "python_reference.py")]
    if args.request is not None:
        command.extend(["--request", str(args.request)])
    elif args.corpus:
        command.append("--corpus")
    elif args.certify:
        command.append("--certify")
    return run_python(command, environment)


def run_typescript_mode(
    args: argparse.Namespace,
    output: Path,
    environment: Mapping[str, str] | None = None,
) -> int:
    if args.cross_certify or args.comparison_certify:
        return emit_protocol_failure(
            "INVALID_INVOCATION",
            "cross-runner certification modes require --runner all",
        )
    if args.check:
        return run_typescript_check(output, environment)
    if args.corpus or args.certify:
        mode = "--observations" if args.corpus else "--certify"
        return run_node(output, [str(TOOL_ROOT / "corpus_cli.mjs"), mode], environment)
    command = [str(TOOL_ROOT / "cli.mjs")]
    if args.request is not None:
        command.extend(["--request", str(args.request)])
    return run_node(output, command, environment)


def run_all_mode(
    args: argparse.Namespace, output: Path, environment: Mapping[str, str]
) -> int:
    if (
        args.request is not None
        or args.corpus
        or not (
            args.check or args.certify or args.cross_certify or args.comparison_certify
        )
    ):
        return emit_protocol_failure(
            "INVALID_INVOCATION",
            "--runner all supports only aggregate check and certification modes",
        )
    if args.check:
        typescript_exit = run_typescript_check(output, environment)
        if typescript_exit != 0:
            return typescript_exit
        python_exit = run_python_check(environment)
        if python_exit != 0:
            return python_exit
    if args.comparison_certify:
        return run_comparison_certification(output, environment)
    return run_cross_certification(output, environment)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    runner = selected_runner(args)
    temporary_parent = TYPESCRIPT_ROOT / "target"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="strling-legacy-reference-", dir=temporary_parent
    ) as temporary:
        snapshot_root = Path(temporary) / "snapshot"
        adapter_evidence.materialize_historical_sources(snapshot_root)
        output = Path(temporary) / "dist"
        environment = frozen_environment(snapshot_root, output)
        if runner == "python":
            return run_python_mode(args, environment)

        build_exit = build_legacy_typescript(snapshot_root, output)
        if build_exit != 0:
            return build_exit
        if runner == "typescript":
            return run_typescript_mode(args, output, environment)
        return run_all_mode(args, output, environment)


if __name__ == "__main__":
    raise SystemExit(main())
