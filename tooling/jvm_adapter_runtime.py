"""Execute deterministic Java and Kotlin parity through the shared native bridge."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
OPERATION_ID = "certification.jvm-adapter-runtime"
CHECK_ID = f"{OPERATION_ID}.shared-bridge-parity"
OPERATIONS = ("describe", "compile", "simply")
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2}


class JvmAdapterRuntimeError(RuntimeError):
    """The live JVM adapter proof failed."""


@dataclass(frozen=True)
class RuntimeReport:
    operation_count: int
    repeat_runs: int
    result_fingerprint: str
    native_library: str
    jdk_version: str
    semantic_copy_count: int


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _tool(environment_name: str, candidates: Sequence[str]) -> str:
    configured = os.environ.get(environment_name)
    if configured:
        path = Path(configured)
        if path.is_file():
            return str(path)
        raise FileNotFoundError(f"{environment_name}={configured}")
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(" or ".join(candidates))


def _run(arguments: Sequence[str], *, cwd: Path, environment: Mapping[str, str]) -> str:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        env=dict(environment),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-6000:]
        raise JvmAdapterRuntimeError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed.stdout + completed.stderr


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
        / "debug"
        / names.get(sys.platform, "libstrling_interop.so")
    )


def _semantic_copy_count() -> int:
    baseline = json.loads(
        (ROOT / "tests/adapters/3.0/legacy-baseline.json").read_text(encoding="utf-8")
    )
    paths = [item["path"] for item in baseline["semantic_copy_files"]]
    remaining = [path for path in paths if (ROOT / path).exists()]
    if remaining:
        raise JvmAdapterRuntimeError(
            f"historical JVM semantic copies remain: {remaining!r}"
        )
    return len(paths)


def _assert_dependency_direction() -> None:
    java = (ROOT / "bindings/java/pom.xml").read_text(encoding="utf-8")
    kotlin = (ROOT / "bindings/kotlin/build.gradle.kts").read_text(encoding="utf-8")
    bridge = (ROOT / "bindings/jvm/pom.xml").read_text(encoding="utf-8")
    coordinate = "strling-jvm"
    if java.count(f"<artifactId>{coordinate}</artifactId>") != 1:
        raise JvmAdapterRuntimeError(
            "Java does not depend on exactly one shared bridge"
        )
    if kotlin.count(f"com.strling:{coordinate}:3.0.0") != 1:
        raise JvmAdapterRuntimeError(
            "Kotlin does not depend on exactly one shared bridge"
        )
    if "net.java.dev.jna" in java or "net.java.dev.jna" in kotlin:
        raise JvmAdapterRuntimeError(
            "a language facade declares an alternate JNA route"
        )
    if bridge.count("<artifactId>jna</artifactId>") != 1 or "5.19.1" not in bridge:
        raise JvmAdapterRuntimeError("shared bridge JNA pin differs from 5.19.1")


def _read_observation(root: Path, binding: str) -> dict[str, Any]:
    result = {}
    for operation in OPERATIONS:
        path = root / binding / f"{operation}.json"
        try:
            result[operation] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise JvmAdapterRuntimeError(f"cannot read {path}: {error}") from error
    return result


def execute(native_library: Path, repeat_runs: int) -> RuntimeReport:
    if repeat_runs < 2:
        raise JvmAdapterRuntimeError("repeat_runs must be at least 2")
    native = native_library.resolve()
    if not native.is_file():
        raise FileNotFoundError(str(native))

    _assert_dependency_direction()
    semantic_count = _semantic_copy_count()
    maven = _tool("STRLING_MAVEN", ("mvn", "mvn.cmd"))
    gradle = _tool("STRLING_GRADLE", ("gradle", "gradle.bat"))
    java = _tool("STRLING_JAVA", ("java", "java.exe"))
    repository = os.environ.get("STRLING_MAVEN_REPOSITORY")
    if not repository or not Path(repository).is_dir():
        raise FileNotFoundError("STRLING_MAVEN_REPOSITORY")

    environment = os.environ.copy()
    environment["STRLING_NATIVE_LIBRARY"] = str(native)
    evidence_root = ROOT / "target" / "jvm-adapter-runtime"
    if evidence_root.exists():
        shutil.rmtree(evidence_root)
    evidence_root.mkdir(parents=True)

    _run(
        [maven, "-o", "-B", "-q", "install"],
        cwd=ROOT / "bindings/jvm",
        environment=environment,
    )

    observations = []
    for index in range(repeat_runs):
        run_root = evidence_root / f"run-{index + 1}"
        environment["STRLING_JVM_EVIDENCE_DIR"] = str(run_root)
        _run(
            [maven, "-o", "-B", "-q", "test"],
            cwd=ROOT / "bindings/jvm",
            environment=environment,
        )
        _run(
            [maven, "-o", "-B", "-q", "test"],
            cwd=ROOT / "bindings/java",
            environment=environment,
        )
        _run(
            [gradle, "--offline", "--no-daemon", "clean", "test"],
            cwd=ROOT / "bindings/kotlin",
            environment=environment,
        )
        java_result = _read_observation(run_root, "java")
        kotlin_result = _read_observation(run_root, "kotlin")
        if java_result != kotlin_result:
            raise JvmAdapterRuntimeError(
                f"run {index + 1}: Java and Kotlin canonical results differ"
            )
        observations.append(java_result)
    if any(result != observations[0] for result in observations[1:]):
        raise JvmAdapterRuntimeError("JVM adapter results are nondeterministic")

    jdk_version = _run([java, "-version"], cwd=ROOT, environment=environment).strip()
    return RuntimeReport(
        operation_count=len(OPERATIONS),
        repeat_runs=repeat_runs,
        result_fingerprint=_fingerprint(observations[0]),
        native_library=str(native),
        jdk_version=jdk_version.splitlines()[0] if jdk_version else "unknown",
        semantic_copy_count=semantic_count,
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
        return _result("passed", started, report.__dict__), EXIT_CODES["passed"]
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
    if arguments.json_output:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"JVM_ADAPTER_RUNTIME status={payload['status']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
