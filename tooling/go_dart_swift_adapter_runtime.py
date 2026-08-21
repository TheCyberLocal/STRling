"""Execute deterministic Go, Dart, and Swift parity through strling.c-abi v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
OPERATION_ID = "certification.go-dart-swift-adapter-runtime"
CHECK_ID = f"{OPERATION_ID}.cross-language-parity"
OPERATIONS = ("describe", "compile", "target_profile", "simply")
BINDINGS = ("go", "dart", "swift")
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2}

PROBE_SOURCE = r"""
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <windows.h>
#endif

#if !defined(STRLING_PROBE_ABI)
#define STRLING_PROBE_ABI 1
#endif

#if defined(_WIN32)
#define STRLING_EXPORT __declspec(dllexport)
#else
#define STRLING_EXPORT __attribute__((visibility("default")))
#endif

typedef struct {
    uint8_t *data;
    size_t len;
} strling_owned_bytes;

static volatile int outstanding = 0;
#if defined(STRLING_PROBE_DUPLICATE)
static const uint8_t response[] =
    "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
    "\"status\":\"completed\",\"result\":{},\"result\":{}}";
#elif defined(STRLING_PROBE_INVALID_UTF8)
static const uint8_t response[] =
    "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
    "\"status\":\"completed\",\"result\":\"\xff\"}";
#else
static const uint8_t response[] =
    "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
    "\"status\":\"completed\",\"result\":{}}";
#endif

STRLING_EXPORT uint32_t strling_interop_abi_version_v1(void) {
    return STRLING_PROBE_ABI;
}

STRLING_EXPORT uint32_t strling_interop_execute_v1(
    const uint8_t *input,
    size_t input_len,
    strling_owned_bytes *output
) {
    (void)input;
    (void)input_len;
#if defined(_WIN32)
    if (InterlockedExchange((volatile LONG *)&outstanding, 1) != 0) return 91;
#else
    if (__sync_lock_test_and_set(&outstanding, 1) != 0) return 91;
#endif
#if defined(STRLING_PROBE_OVERSIZE)
    output->data = (uint8_t *)(uintptr_t)response;
    output->len = 33554433u;
    return 0;
#else
    output->len = sizeof(response) - 1u;
    output->data = (uint8_t *)malloc(output->len);
    if (output->data == NULL) return 92;
    memcpy(output->data, response, output->len);
    return 0;
#endif
}

STRLING_EXPORT uint32_t strling_interop_owned_bytes_free_v1(
    strling_owned_bytes *output
) {
#if !defined(STRLING_PROBE_OVERSIZE)
    free(output->data);
#endif
    output->data = NULL;
    output->len = 0;
#if defined(_WIN32)
    InterlockedExchange((volatile LONG *)&outstanding, 0);
#else
    __sync_lock_release(&outstanding);
#endif
    return 0;
}
"""


class GoDartSwiftAdapterRuntimeError(RuntimeError):
    """The live Go/Dart/Swift adapter proof failed."""


@dataclass(frozen=True)
class RuntimeReport:
    operation_count: int
    repeat_runs: int
    result_fingerprint: str
    native_library: str
    platform: str
    tool_versions: Mapping[str, str]
    semantic_copy_count: int
    executed_bindings: tuple[str, ...]
    probe_count: int


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


def _tool(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise FileNotFoundError(name)
    return resolved


def _run(
    arguments: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int = 900,
) -> str:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        env=dict(environment),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-8000:]
        raise GoDartSwiftAdapterRuntimeError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed.stdout + completed.stderr


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _version_tuple(text: str, pattern: str, label: str) -> tuple[int, ...]:
    match = re.search(pattern, text)
    if match is None:
        raise GoDartSwiftAdapterRuntimeError(
            f"cannot parse governed {label} version from {text!r}"
        )
    return tuple(int(part) for part in match.group(1).split("."))


def _assert_tool_versions(versions: Mapping[str, str]) -> None:
    go = _version_tuple(versions["go"], r"\bgo(\d+\.\d+(?:\.\d+)?)\b", "Go")
    dart = _version_tuple(
        versions["dart"], r"Dart SDK version:\s*(\d+\.\d+(?:\.\d+)?)", "Dart"
    )
    swift = _version_tuple(
        versions["swift"], r"Swift version\s+(\d+\.\d+(?:\.\d+)?)", "Swift"
    )
    if go[:2] != (1, 22):
        raise GoDartSwiftAdapterRuntimeError(
            f"Go {'.'.join(map(str, go))} is outside >=1.22,<1.23"
        )
    if dart[0] != 3:
        raise GoDartSwiftAdapterRuntimeError(
            f"Dart {'.'.join(map(str, dart))} is outside >=3.0,<4.0"
        )
    if swift < (5, 9) or swift >= (7, 0):
        raise GoDartSwiftAdapterRuntimeError(
            f"Swift {'.'.join(map(str, swift))} is outside >=5.9,<7.0"
        )


def _semantic_copy_count() -> int:
    baseline = json.loads(
        (ROOT / "tests/adapters/go-dart-swift-3.0/legacy-baseline.json").read_text(
            encoding="utf-8"
        )
    )
    paths = tuple(str(item["path"]) for item in baseline["semantic_copy_files"])
    remaining = tuple(path for path in paths if (ROOT / path).exists())
    if remaining:
        raise GoDartSwiftAdapterRuntimeError(
            f"historical Go/Dart/Swift semantic copies remain: {remaining!r}"
        )
    return len(paths)


def _read_observation(root: Path, binding: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for operation in OPERATIONS:
        path = root / binding / f"{operation}.json"
        try:
            result[operation] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise GoDartSwiftAdapterRuntimeError(
                f"cannot read {path}: {error}"
            ) from error
    return result


def _build_probe(
    compiler: str, root: Path, name: str, definitions: Sequence[str]
) -> Path:
    source = root / f"{name}.c"
    source.write_text(PROBE_SOURCE, encoding="utf-8", newline="\n")
    if sys.platform == "win32":
        output = root / f"{name}.dll"
        command = [
            compiler,
            "-shared",
            "-O2",
            *definitions,
            str(source),
            "-o",
            str(output),
        ]
    elif sys.platform == "darwin":
        output = root / f"lib{name}.dylib"
        command = [
            compiler,
            "-dynamiclib",
            "-O2",
            *definitions,
            str(source),
            "-o",
            str(output),
        ]
    else:
        output = root / f"lib{name}.so"
        command = [
            compiler,
            "-shared",
            "-fPIC",
            "-O2",
            *definitions,
            str(source),
            "-o",
            str(output),
        ]
    _run(command, cwd=root, environment=os.environ)
    if not output.is_file():
        raise GoDartSwiftAdapterRuntimeError(f"C ABI probe was not created: {output}")
    return output


def _assert_package_identities() -> None:
    go_module = (ROOT / "bindings/go/go.mod").read_text(encoding="utf-8")
    dart_package = (ROOT / "bindings/dart/pubspec.yaml").read_text(encoding="utf-8")
    swift_package = (ROOT / "bindings/swift/Package.swift").read_text(encoding="utf-8")
    if "module github.com/strling-lang/strling/bindings/go" not in go_module:
        raise GoDartSwiftAdapterRuntimeError("Go module identity changed")
    if "name: strling" not in dart_package:
        raise GoDartSwiftAdapterRuntimeError("Dart package identity changed")
    if 'name: "STRling"' not in swift_package:
        raise GoDartSwiftAdapterRuntimeError("Swift package identity changed")


def execute(native_library: Path, repeat_runs: int) -> RuntimeReport:
    if repeat_runs < 2:
        raise GoDartSwiftAdapterRuntimeError("repeat_runs must be at least 2")
    native = native_library.resolve()
    if not native.is_file():
        raise FileNotFoundError(str(native))
    tools = {name: _tool(name) for name in (*BINDINGS, "cc")}
    _assert_package_identities()
    semantic_count = _semantic_copy_count()

    base_environment = os.environ.copy()
    base_environment["STRLING_NATIVE_LIBRARY"] = str(native)
    base_environment["NO_COLOR"] = "1"
    base_environment["CI"] = "true"
    tool_versions = {
        "go": _run(
            [tools["go"], "version"], cwd=ROOT, environment=base_environment
        ).strip(),
        "dart": _run(
            [tools["dart"], "--version"], cwd=ROOT, environment=base_environment
        ).strip(),
        "swift": _run(
            [tools["swift"], "--version"], cwd=ROOT, environment=base_environment
        ).strip(),
    }
    _assert_tool_versions(tool_versions)

    go_no_cgo = dict(base_environment)
    go_no_cgo.pop("STRLING_NATIVE_LIBRARY", None)
    go_no_cgo["CGO_ENABLED"] = "0"
    _run(
        [tools["go"], "test", "./..."],
        cwd=ROOT / "bindings/go",
        environment=go_no_cgo,
    )
    _run(
        [tools["dart"], "pub", "get", "--offline", "--enforce-lockfile"],
        cwd=ROOT / "bindings/dart",
        environment=base_environment,
    )
    _run(
        [tools["dart"], "analyze", "--fatal-infos", "--fatal-warnings"],
        cwd=ROOT / "bindings/dart",
        environment=base_environment,
    )

    observations: list[dict[str, Any]] = []
    target = ROOT / "target"
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gds-adapter-", dir=target) as directory:
        evidence_root = Path(directory)
        release_probe = _build_probe(
            tools["cc"], evidence_root, "strling_release_probe", ()
        )
        abi_probe = _build_probe(
            tools["cc"], evidence_root, "strling_abi_probe", ("-DSTRLING_PROBE_ABI=2",)
        )
        oversize_probe = _build_probe(
            tools["cc"],
            evidence_root,
            "strling_oversize_probe",
            ("-DSTRLING_PROBE_OVERSIZE=1",),
        )
        duplicate_probe = _build_probe(
            tools["cc"],
            evidence_root,
            "strling_duplicate_probe",
            ("-DSTRLING_PROBE_DUPLICATE=1",),
        )
        invalid_utf8_probe = _build_probe(
            tools["cc"],
            evidence_root,
            "strling_invalid_utf8_probe",
            ("-DSTRLING_PROBE_INVALID_UTF8=1",),
        )
        for index in range(repeat_runs):
            run_root = evidence_root / f"run-{index + 1}"
            environment = dict(base_environment)
            environment["STRLING_GDS_EVIDENCE_DIR"] = str(run_root)
            environment["STRLING_GDS_RELEASE_PROBE"] = str(release_probe)
            environment["STRLING_GDS_ABI_PROBE"] = str(abi_probe)
            environment["STRLING_GDS_OVERSIZE_PROBE"] = str(oversize_probe)
            environment["STRLING_GDS_DUPLICATE_PROBE"] = str(duplicate_probe)
            environment["STRLING_GDS_INVALID_UTF8_PROBE"] = str(invalid_utf8_probe)
            environment["CGO_ENABLED"] = "1"
            _run(
                [tools["go"], "test", "./...", "-count=1"],
                cwd=ROOT / "bindings/go",
                environment=environment,
            )
            _run(
                [tools["dart"], "test", "--concurrency=1"],
                cwd=ROOT / "bindings/dart",
                environment=environment,
            )
            _run(
                [
                    tools["swift"],
                    "test",
                    "-c",
                    "release",
                    "--jobs",
                    "1",
                    "-Xswiftc",
                    "-warnings-as-errors",
                ],
                cwd=ROOT / "bindings/swift",
                environment=environment,
            )
            per_binding = {
                binding: _read_observation(run_root, binding) for binding in BINDINGS
            }
            first = per_binding[BINDINGS[0]]
            differing = tuple(
                binding for binding in BINDINGS[1:] if per_binding[binding] != first
            )
            if differing:
                raise GoDartSwiftAdapterRuntimeError(
                    f"run {index + 1}: canonical results differ for {differing!r}"
                )
            observations.append(first)

    if any(item != observations[0] for item in observations[1:]):
        raise GoDartSwiftAdapterRuntimeError(
            "Go/Dart/Swift adapter results are nondeterministic"
        )
    return RuntimeReport(
        operation_count=len(OPERATIONS),
        repeat_runs=repeat_runs,
        result_fingerprint=_fingerprint(observations[0]),
        native_library=str(native),
        platform=platform.platform(),
        tool_versions=tool_versions,
        semantic_copy_count=semantic_count,
        executed_bindings=BINDINGS,
        probe_count=5,
    )


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": dict(details)}],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-library", type=Path, default=_native_default())
    parser.add_argument("--repeat-runs", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    started = time.monotonic()
    try:
        report = execute(arguments.native_library, arguments.repeat_runs)
    except FileNotFoundError as error:
        payload = _result("unavailable", started, {"missing": str(error)})
    except (
        GoDartSwiftAdapterRuntimeError,
        OSError,
        subprocess.SubprocessError,
    ) as error:
        payload = _result("failed", started, {"error": str(error)})
    else:
        payload = _result("passed", started, asdict(report))
    print(json.dumps(payload, sort_keys=True) if arguments.json else payload)
    return EXIT_CODES[str(payload["status"])]


if __name__ == "__main__":
    raise SystemExit(main())
