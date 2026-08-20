"""Build the governed host-native interop library for Python packaging/tests."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "bindings" / "interop" / "Cargo.toml"


def cargo() -> str:
    resolved = shutil.which("cargo")
    if resolved is not None:
        return resolved
    candidate = Path.home() / ".cargo" / "bin" / "cargo.exe"
    if sys.platform == "win32" and candidate.is_file():
        return str(candidate)
    raise RuntimeError("Cargo is required to assemble the STRling native library")


def library_name() -> str:
    if sys.platform == "win32":
        return "strling_interop.dll"
    if sys.platform == "darwin":
        return "libstrling_interop.dylib"
    return "libstrling_interop.so"


def assemble(output_directory: Path) -> Path:
    completed = subprocess.run(
        [
            cargo(),
            "+1.75.0",
            "build",
            "--manifest-path",
            str(MANIFEST),
            "-p",
            "strling-interop",
            "--release",
            "--locked",
            "--offline",
        ],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    source = ROOT / "bindings" / "interop" / "target" / "release" / library_name()
    if not source.is_file():
        raise RuntimeError("Cargo did not produce the expected native library")
    output_directory.mkdir(parents=True, exist_ok=True)
    output = output_directory / library_name()
    shutil.copyfile(source, output)
    print("assembled {}".format(output.resolve()))
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assemble(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
