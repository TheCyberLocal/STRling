"""Build and seal the governed raw-WASM artifact into the local npm package."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BINDING = ROOT / "bindings" / "typescript"
MANIFEST = ROOT / "bindings" / "interop" / "Cargo.toml"
RAW_WASM = (
    ROOT
    / "bindings"
    / "interop"
    / "target"
    / "wasm32-unknown-unknown"
    / "release"
    / "strling_interop.wasm"
)
OUTPUT = BINDING / "dist" / "strling_interop.wasm"


def cargo() -> str:
    resolved = shutil.which("cargo")
    if resolved is not None:
        return resolved
    candidate = Path.home() / ".cargo" / "bin" / "cargo.exe"
    if sys.platform == "win32" and candidate.is_file():
        return str(candidate)
    raise RuntimeError("Cargo is required to assemble the STRling WASM artifact")


def main() -> int:
    completed = subprocess.run(
        [
            cargo(),
            "+1.75.0",
            "build",
            "--manifest-path",
            str(MANIFEST),
            "-p",
            "strling-interop",
            "--target",
            "wasm32-unknown-unknown",
            "--release",
            "--locked",
            "--offline",
        ],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        return completed.returncode

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tooling.interop_wasm import inspect_module, seal_module

    sealed = seal_module(RAW_WASM.read_bytes())
    exports = inspect_module(sealed)
    if len(exports) != 6:
        raise RuntimeError("sealed strling.wasm-abi artifact has unexpected exports")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(sealed)
    print(f"assembled {OUTPUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
