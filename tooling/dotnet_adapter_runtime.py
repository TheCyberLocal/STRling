"""Execute deterministic C# and F# parity through the shared native bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
OPERATION_ID = "certification.dotnet-adapter-runtime"
CHECK_ID = f"{OPERATION_ID}.shared-bridge-parity"
OPERATIONS = ("describe", "compile", "simply")
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2}


class DotNetAdapterRuntimeError(RuntimeError):
    """The live .NET adapter proof failed."""


@dataclass(frozen=True)
class RuntimeReport:
    operation_count: int
    repeat_runs: int
    result_fingerprint: str
    native_library: str
    sdk_version: str
    semantic_copy_count: int
    certified_rids: tuple[str, ...]


def _native_default() -> Path:
    names = {
        "win32": "strling_interop.dll",
        "darwin": "libstrling_interop.dylib",
    }
    return (
        ROOT
        / "bindings"
        / "interop"
        / "target"
        / "release"
        / names.get(sys.platform, "libstrling_interop.so")
    )


def _run(arguments: Sequence[str], *, environment: Mapping[str, str]) -> str:
    completed = subprocess.run(
        list(arguments),
        cwd=ROOT,
        env=dict(environment),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-8000:]
        raise DotNetAdapterRuntimeError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed.stdout + completed.stderr


def _semantic_copy_count() -> int:
    baseline = json.loads(
        (ROOT / "tests/adapters/dotnet-3.0/legacy-baseline.json").read_text(
            encoding="utf-8"
        )
    )
    paths = [str(item["path"]) for item in baseline["semantic_copy_files"]]
    remaining = [path for path in paths if (ROOT / path).exists()]
    if remaining:
        raise DotNetAdapterRuntimeError(
            f"historical .NET semantic copies remain: {remaining!r}"
        )
    return len(paths)


def _assert_dependency_direction() -> None:
    csharp = (ROOT / "bindings/csharp/src/STRling/STRling.csproj").read_text(
        encoding="utf-8"
    )
    fsharp = (ROOT / "bindings/fsharp/src/STRling.FSharp/STRling.FSharp.fsproj").read_text(
        encoding="utf-8"
    )
    fsharp_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "bindings/fsharp/src/STRling.FSharp").glob("*.fs"))
    )
    if "<PackageId>STRling</PackageId>" not in csharp:
        raise DotNetAdapterRuntimeError("C# package identity changed")
    if "<PackageId>STRling.FSharp</PackageId>" not in fsharp:
        raise DotNetAdapterRuntimeError("F# package identity changed")
    if fsharp.count("csharp/src/STRling/STRling.csproj") != 1:
        raise DotNetAdapterRuntimeError("F# does not depend on exactly one C# substrate")
    forbidden = ("NativeLibrary", "DllImport", "LibraryImport", "Process.Start", "Socket")
    if any(marker in fsharp_sources for marker in forbidden):
        raise DotNetAdapterRuntimeError("F# contains an alternate native route")


def _read_observation(root: Path, binding: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for operation in OPERATIONS:
        path = root / binding / f"{operation}.json"
        try:
            result[operation] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DotNetAdapterRuntimeError(f"cannot read {path}: {error}") from error
    return result


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def execute(native_library: Path, repeat_runs: int) -> RuntimeReport:
    if repeat_runs < 2:
        raise DotNetAdapterRuntimeError("repeat_runs must be at least 2")
    native = native_library.resolve()
    if not native.is_file():
        raise FileNotFoundError(str(native))
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        raise FileNotFoundError("dotnet")
    _assert_dependency_direction()
    semantic_count = _semantic_copy_count()
    environment = os.environ.copy()
    environment["STRLING_NATIVE_LIBRARY"] = str(native)
    target = ROOT / "target"
    target.mkdir(exist_ok=True)
    observations: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="dotnet-adapter-", dir=target) as directory:
        evidence_root = Path(directory)
        for index in range(repeat_runs):
            run_root = evidence_root / f"run-{index + 1}"
            environment["STRLING_DOTNET_EVIDENCE_DIR"] = str(run_root)
            _run(
                [
                    dotnet,
                    "test",
                    "bindings/csharp/tests/STRling.Tests/STRling.Tests.csproj",
                    "-c",
                    "Release",
                    "-p:NuGetAudit=false",
                    "-m:1",
                    "--no-restore",
                ],
                environment=environment,
            )
            _run(
                [
                    dotnet,
                    "test",
                    "bindings/fsharp/test/STRling.FSharp.Tests/STRling.FSharp.Tests.fsproj",
                    "-c",
                    "Release",
                    "-p:NuGetAudit=false",
                    "-m:1",
                    "--no-restore",
                ],
                environment=environment,
            )
            csharp = _read_observation(run_root, "csharp")
            fsharp = _read_observation(run_root, "fsharp")
            if csharp != fsharp:
                raise DotNetAdapterRuntimeError(
                    f"run {index + 1}: C# and F# canonical results differ"
                )
            observations.append(csharp)
    if any(item != observations[0] for item in observations[1:]):
        raise DotNetAdapterRuntimeError(".NET adapter results are nondeterministic")
    sdk_version = _run([dotnet, "--version"], environment=environment).strip()
    certified_rids = ("win-x64",) if sys.platform == "win32" else ()
    return RuntimeReport(
        operation_count=len(OPERATIONS),
        repeat_runs=repeat_runs,
        result_fingerprint=_fingerprint(observations[0]),
        native_library=str(native),
        sdk_version=sdk_version,
        semantic_copy_count=semantic_count,
        certified_rids=certified_rids,
    )


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": dict(details)}],
    }


def certify(native_library: Path, repeat_runs: int) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    try:
        report = execute(native_library, repeat_runs)
        return _result("passed", started, asdict(report)), EXIT_CODES["passed"]
    except FileNotFoundError as error:
        return _result("unavailable", started, {"reason": str(error)}), EXIT_CODES[
            "unavailable"
        ]
    except Exception as error:
        return (
            _result(
                "failed",
                started,
                {
                    "error_type": type(error).__name__,
                    "host_platform": platform.platform(),
                    "reason": str(error),
                },
            ),
            EXIT_CODES["failed"],
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--native-library", type=Path, default=_native_default())
    parser.add_argument("--repeat-runs", type=int, default=3)
    arguments = parser.parse_args(argv)
    payload, exit_code = certify(arguments.native_library, arguments.repeat_runs)
    print(json.dumps(payload, sort_keys=True) if arguments.json_output else payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
