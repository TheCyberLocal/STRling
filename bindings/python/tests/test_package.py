from __future__ import annotations

import ast
from pathlib import Path

import STRling

ROOT = Path(__file__).resolve().parents[3]
BINDING = ROOT / "bindings" / "python"


def test_root_exports_canonical_native_facade() -> None:
    assert STRling.__all__ == [
        "Compiler",
        "INTEROP_PROTOCOL_VERSION",
        "InteropProtocolError",
        "NativeAbiError",
        "NativeAdapterError",
        "NativeClient",
        "NativeLoadError",
        "bundled_library_path",
        "load_native",
        "parse",
        "parse_to_artifact",
        "simply",
        "source_compile_request",
    ]


def test_retired_semantic_modules_are_absent() -> None:
    package = BINDING / "src" / "STRling"
    assert not any((package / "core").glob("*.py"))
    assert not any((package / "emitters").glob("*.py"))


def test_product_sources_have_no_cli_or_regex_fallback() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((BINDING / "src" / "STRling").rglob("*.py"))
    )
    assert "subprocess.run" not in sources
    assert "import re" not in sources
    assert "NATIVE_EXEC" not in sources
    assert "WASM_EXEC" not in sources


def test_python_38_can_parse_every_product_source() -> None:
    for path in sorted((BINDING / "src" / "STRling").rglob("*.py")):
        ast.parse(
            path.read_text(encoding="utf-8"), filename=str(path), feature_version=8
        )
