from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BINDING = ROOT / "bindings" / "python"


def _library_name() -> str:
    if sys.platform == "win32":
        return "strling_interop.dll"
    if sys.platform == "darwin":
        return "libstrling_interop.dylib"
    return "libstrling_interop.so"


@pytest.fixture(scope="session")
def native_library() -> Path:
    output_directory = BINDING / "target" / "native"
    library = output_directory / _library_name()
    if not library.is_file():
        subprocess.run(
            [
                sys.executable,
                str(BINDING / "scripts" / "assemble_native.py"),
                "--output",
                str(output_directory),
            ],
            check=True,
        )
    return library
