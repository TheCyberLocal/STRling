"""Execute structured native and WebAssembly certification for STRling interop."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

from tooling.interop_contract import (
    InteropContractSuite,
    certify_runtime,
    write_or_check_header,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "bindings" / "interop" / "Cargo.toml"
TOOLCHAIN = "1.75.0"
OPERATION_ID = "certification.interop"
CHECK_ID = f"{OPERATION_ID}.native-wasm-boundary"
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2, "incomplete": 3}
NATIVE_SYMBOLS = {
    "strling_interop_abi_version_v1",
    "strling_interop_execute_v1",
    "strling_interop_owned_bytes_free_v1",
}


class InteropCertificationError(RuntimeError):
    """Raised when executable interop certification fails."""


def executable(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    suffix = ".exe" if os.name == "nt" else ""
    fallback = Path.home() / ".cargo" / "bin" / f"{name}{suffix}"
    if fallback.is_file():
        return str(fallback)
    raise FileNotFoundError(name)


def run(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["CARGO_NET_OFFLINE"] = "true"
    completed = subprocess.run(
        list(arguments),
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise InteropCertificationError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed


def cargo(*arguments: str) -> subprocess.CompletedProcess[str]:
    if not arguments:
        raise InteropCertificationError("cargo subcommand is required")
    subcommand, *rest = arguments
    return run(
        [
            executable("cargo"),
            f"+{TOOLCHAIN}",
            subcommand,
            "--manifest-path",
            str(MANIFEST),
            *rest,
        ]
    )


def rust_identity() -> dict[str, str]:
    completed = run([executable("rustc"), f"+{TOOLCHAIN}", "-vV"])
    rows = dict(
        line.split(": ", 1) for line in completed.stdout.splitlines() if ": " in line
    )
    release = rows.get("release")
    host = rows.get("host")
    if release != TOOLCHAIN or not host:
        raise InteropCertificationError("Rust release/host identity is incomplete")
    return {"host": host, "release": release}


def cargo_target_directory() -> Path:
    configured = os.environ.get("CARGO_TARGET_DIR")
    if not configured:
        return ROOT / "bindings" / "interop" / "target"
    target = Path(configured).expanduser()
    return target if target.is_absolute() else ROOT / target


def native_library(host: str) -> Path:
    root = cargo_target_directory() / "release"
    if "windows" in host:
        return root / "strling_interop.dll"
    if "apple" in host:
        return root / "libstrling_interop.dylib"
    return root / "libstrling_interop.so"


def llvm_tool(identity: dict[str, str], name: str) -> str:
    sysroot = Path(
        run(
            [
                executable("rustc"),
                f"+{TOOLCHAIN}",
                "--print",
                "sysroot",
            ]
        ).stdout.strip()
    )
    suffix = ".exe" if os.name == "nt" else ""
    candidate = (
        sysroot / "lib" / "rustlib" / identity["host"] / "bin" / f"{name}{suffix}"
    )
    if not candidate.is_file():
        raise FileNotFoundError(str(candidate))
    return str(candidate)


def native_symbol_snapshot(identity: dict[str, str]) -> list[str]:
    library = native_library(identity["host"])
    if not library.is_file():
        raise InteropCertificationError(f"native library is missing: {library}")
    if os.name == "nt":
        arguments = [
            llvm_tool(identity, "llvm-readobj"),
            "--coff-exports",
            str(library),
        ]
    else:
        arguments = [
            llvm_tool(identity, "llvm-nm"),
            "--defined-only",
            "--extern-only",
        ]
        if "apple" not in identity["host"]:
            arguments.append("--dynamic")
        arguments.append(str(library))
    completed = run(arguments)
    if os.name == "nt":
        symbols = sorted(
            line.split("Name:", 1)[1].strip()
            for line in completed.stdout.splitlines()
            if line.strip().startswith("Name:")
        )
    else:
        symbols = sorted(
            normalize_symbol(identity["host"], line.rsplit(maxsplit=1)[-1])
            for line in completed.stdout.splitlines()
            if line.strip()
        )
    interop = {symbol for symbol in symbols if symbol.startswith("strling_interop_")}
    if interop != NATIVE_SYMBOLS:
        raise InteropCertificationError(
            f"native symbol snapshot differs: {sorted(interop)!r}"
        )
    return sorted(interop)


def normalize_symbol(host: str, symbol: str) -> str:
    if "apple" in host and symbol.startswith("_"):
        return symbol[1:]
    return symbol


def execute(*, wasm: bool, expected_host: str | None = None) -> dict[str, Any]:
    contract = InteropContractSuite().certify()
    write_or_check_header(check=True)
    identity = rust_identity()
    if expected_host is not None and identity["host"] != expected_host:
        raise InteropCertificationError(
            f"native host differs: expected {expected_host}, found {identity['host']}"
        )
    cargo("fmt", "--all", "--", "--check")
    cargo("clippy", "--all-targets", "--locked", "--offline", "--", "-D", "warnings")
    cargo("test", "--all-targets", "--locked", "--offline")
    cargo("build", "--release", "--locked", "--offline")
    symbols = native_symbol_snapshot(identity)
    details: dict[str, Any] = {
        "contract_fingerprint": contract.contract_fingerprint,
        "evidence_fingerprint": contract.evidence_fingerprint,
        "evidence_cases": contract.case_count,
        "native_host": identity["host"],
        "native_symbols": symbols,
        "rust_release": identity["release"],
        "wasm_executed": wasm,
    }
    if wasm:
        cargo(
            "build",
            "--target",
            "wasm32-unknown-unknown",
            "--release",
            "--locked",
            "--offline",
        )
        details.update(certify_runtime())
    return details


def result(status: str, started: float, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": details}],
    }


def certify(
    *, wasm: bool, expected_host: str | None = None
) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    try:
        details = execute(wasm=wasm, expected_host=expected_host)
        return result("passed", started, details), 0
    except FileNotFoundError as error:
        return result(
            "unavailable",
            started,
            {
                "host_platform": platform.platform(),
                "reason": str(error),
            },
        ), EXIT_CODES["unavailable"]
    except Exception as error:
        return result(
            "failed",
            started,
            {
                "error_type": type(error).__name__,
                "host_platform": platform.platform(),
                "reason": str(error),
            },
        ), EXIT_CODES["failed"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--wasm", action="store_true")
    parser.add_argument("--expected-host")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload, exit_code = certify(wasm=args.wasm, expected_host=args.expected_host)
    serialized = json.dumps(payload, sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    if args.json_output:
        print(serialized)
    else:
        check = payload["checks"][0]
        print(
            f"INTEROP_CERTIFICATION status={payload['status']} "
            f"details={check['details']}"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
