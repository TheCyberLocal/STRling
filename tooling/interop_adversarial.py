"""Execute the governed STRling interop fuzz and sanitizer certification."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from tooling.interop_contract import InteropContractSuite, certify_runtime


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "bindings" / "interop" / "Cargo.toml"
FUZZ_DIRECTORY = ROOT / "bindings" / "interop" / "fuzz"
NIGHTLY_TOOLCHAIN = "nightly-2026-08-01"
STABLE_TOOLCHAIN = "1.75.0"
CARGO_FUZZ_VERSION = "0.13.2"
LINUX_TARGET = "x86_64-unknown-linux-gnu"
WASM_TARGET = "wasm32-unknown-unknown"
DEFAULT_FUZZ_RUNS = 10_000
OPERATION_ID = "certification.interop-adversarial"
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2, "incomplete": 3}
FUZZ_TARGETS = (
    "fuzz-arbitrary-bytes",
    "fuzz-structured-envelope",
    "fuzz-length-boundaries",
    "fuzz-simply-graphs",
    "fuzz-target-profiles",
    "fuzz-ownership-sequences",
)


class InteropAdversarialError(RuntimeError):
    """Raised when executable interop adversarial certification fails."""


def executable(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(name)


def supported_host(system: str | None = None, machine: str | None = None) -> bool:
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    return system == "Linux" and machine in {"amd64", "x86_64"}


def fuzz_command(target: str, runs: int) -> list[str]:
    if target not in FUZZ_TARGETS:
        raise ValueError(f"unknown interop fuzz target: {target}")
    if runs < 1:
        raise ValueError("fuzz runs must be positive")
    return [
        executable("cargo"),
        f"+{NIGHTLY_TOOLCHAIN}",
        "fuzz",
        "run",
        "--fuzz-dir",
        str(FUZZ_DIRECTORY),
        target,
        "--",
        f"-runs={runs}",
        "-seed=1471701",
        "-max_len=16384",
        "-timeout=10",
        "-rss_limit_mb=4096",
    ]


def sanitizer_command(kind: str) -> list[str]:
    if kind not in {"address", "leak"}:
        raise ValueError(f"unsupported sanitizer: {kind}")
    return [
        executable("cargo"),
        f"+{NIGHTLY_TOOLCHAIN}",
        "test",
        "--manifest-path",
        str(MANIFEST),
        "-p",
        "strling-interop",
        "--tests",
        "--locked",
        "--offline",
        "--target",
        LINUX_TARGET,
        "-Zbuild-std",
    ]


def sanitizer_environment(kind: str) -> dict[str, str]:
    if kind not in {"address", "leak"}:
        raise ValueError(f"unsupported sanitizer: {kind}")
    flag = f"-Zsanitizer={kind} -Cdebuginfo=1"
    environment = {
        "RUSTFLAGS": flag,
        "RUSTDOCFLAGS": flag,
        "CARGO_TARGET_DIR": str(
            ROOT / "bindings" / "interop" / "target" / "sanitizer" / kind
        ),
    }
    if kind == "address":
        environment["ASAN_OPTIONS"] = "detect_leaks=1:halt_on_error=1:abort_on_error=1"
    else:
        environment["LSAN_OPTIONS"] = "exitcode=23:report_objects=1"
    return environment


def wasm_build_command() -> list[str]:
    return [
        executable("cargo"),
        f"+{STABLE_TOOLCHAIN}",
        "build",
        "--manifest-path",
        str(MANIFEST),
        "-p",
        "strling-interop",
        "--target",
        WASM_TARGET,
        "--release",
        "--locked",
        "--offline",
    ]


def run(
    arguments: Sequence[str], *, environment: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    process_environment = dict(os.environ)
    process_environment["CARGO_NET_OFFLINE"] = "true"
    if environment is not None:
        process_environment.update(environment)
    completed = subprocess.run(
        list(arguments),
        cwd=ROOT,
        env=process_environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-4000:]
        raise InteropAdversarialError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed


def tool_identities() -> dict[str, str]:
    rust = run([executable("rustc"), f"+{NIGHTLY_TOOLCHAIN}", "-vV"]).stdout
    rows = dict(line.split(": ", 1) for line in rust.splitlines() if ": " in line)
    if not rows.get("release", "").endswith("-nightly"):
        raise InteropAdversarialError("selected compiler is not a nightly release")
    if not rows.get("commit-hash") or not rows.get("commit-date"):
        raise InteropAdversarialError("nightly compiler identity is incomplete")
    if rows.get("host") != LINUX_TARGET:
        raise InteropAdversarialError("nightly compiler host differs from policy")
    cargo_fuzz = run(
        [executable("cargo"), f"+{NIGHTLY_TOOLCHAIN}", "fuzz", "--version"]
    ).stdout.strip()
    if re.search(rf"\b{re.escape(CARGO_FUZZ_VERSION)}\b", cargo_fuzz) is None:
        raise InteropAdversarialError("cargo-fuzz version differs from policy")
    return {
        "cargo_fuzz": cargo_fuzz,
        "rust_channel": NIGHTLY_TOOLCHAIN,
        "rust_commit": rows.get("commit-hash", ""),
        "rust_commit_date": rows.get("commit-date", ""),
        "rust_release": rows.get("release", ""),
        "rust_target": rows.get("host", ""),
    }


def check(check_id: str, status: str, details: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": check_id, "status": status, "details": dict(details)}


def payload(
    status: str, started: float, checks: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": list(checks),
    }


def certify(*, fuzz_runs: int = DEFAULT_FUZZ_RUNS) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    checks: list[dict[str, Any]] = []
    if not supported_host():
        checks.append(
            check(
                f"{OPERATION_ID}.environment",
                "unavailable",
                {
                    "host_platform": platform.platform(),
                    "required_target": LINUX_TARGET,
                    "reason": "cargo-fuzz and governed sanitizers require x86_64 Linux",
                },
            )
        )
        return payload("unavailable", started, checks), EXIT_CODES["unavailable"]
    try:
        contract = InteropContractSuite().certify()
        identities = tool_identities()
        for target in FUZZ_TARGETS:
            target_started = time.monotonic()
            run(fuzz_command(target, fuzz_runs))
            checks.append(
                check(
                    f"{OPERATION_ID}.{target}",
                    "passed",
                    {
                        "contract_fingerprint": contract.contract_fingerprint,
                        "evidence_fingerprint": contract.evidence_fingerprint,
                        "runner": "cargo-fuzz",
                        "runs": fuzz_runs,
                        "target": target,
                        "duration_ms": max(
                            0, int((time.monotonic() - target_started) * 1000)
                        ),
                        **identities,
                    },
                )
            )
        sanitizer_details: dict[str, int] = {}
        for kind in ("address", "leak"):
            sanitizer_started = time.monotonic()
            run(sanitizer_command(kind), environment=sanitizer_environment(kind))
            sanitizer_details[f"{kind}_duration_ms"] = max(
                0, int((time.monotonic() - sanitizer_started) * 1000)
            )
        checks.append(
            check(
                f"{OPERATION_ID}.sanitizer-native-address-leak",
                "passed",
                {
                    "runner": "sanitizer-ci",
                    "sanitizers": ["address", "leak"],
                    "target": LINUX_TARGET,
                    **sanitizer_details,
                    **identities,
                },
            )
        )
        run(wasm_build_command())
        wasm = certify_runtime()
        checks.append(
            check(
                f"{OPERATION_ID}.sanitizer-wasm-host-memory",
                "passed",
                {"runner": "sanitizer-ci", "target": WASM_TARGET, **wasm},
            )
        )
        return payload("passed", started, checks), EXIT_CODES["passed"]
    except FileNotFoundError as error:
        checks.append(
            check(
                f"{OPERATION_ID}.environment",
                "unavailable",
                {"host_platform": platform.platform(), "reason": str(error)},
            )
        )
        return payload("unavailable", started, checks), EXIT_CODES["unavailable"]
    except Exception as error:
        checks.append(
            check(
                f"{OPERATION_ID}.execution",
                "failed",
                {
                    "error_type": type(error).__name__,
                    "host_platform": platform.platform(),
                    "reason": str(error),
                },
            )
        )
        return payload("failed", started, checks), EXIT_CODES["failed"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fuzz-runs", type=int, default=DEFAULT_FUZZ_RUNS)
    args = parser.parse_args(argv)
    if args.fuzz_runs < 1:
        parser.error("--fuzz-runs must be positive")
    result, exit_code = certify(fuzz_runs=args.fuzz_runs)
    serialized = json.dumps(result, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    if args.json_output:
        print(serialized)
    else:
        print(
            f"INTEROP_ADVERSARIAL status={result['status']} "
            f"checks={len(result['checks'])}"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
