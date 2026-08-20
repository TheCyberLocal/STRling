from __future__ import annotations

import json
from pathlib import Path

import pytest

from STRling.compiler import Compiler, parse, parse_to_artifact
from STRling.interop import NativeClient

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_exact_profile_artifact_is_canonical(native_library: Path) -> None:
    client = NativeClient(native_library)
    request = _json("spec/contracts/1.0/examples/compile-request/target-artifact.json")
    profile = _json("spec/targets/profiles/pcre2-10.43.json")
    result = Compiler(client).compile(request, profile)
    assert result["outcome"] == "succeeded"
    assert result["artifact"]["target_profile"] == request["target_profile"]


def test_canonical_failed_compile_remains_a_value(native_library: Path) -> None:
    result = parse(NativeClient(native_library), "(")
    assert result["outcome"] == "failed"
    assert result["diagnostics"]


def test_artifact_projection_requires_exact_target(native_library: Path) -> None:
    with pytest.raises(TypeError):
        parse_to_artifact(NativeClient(native_library), "abc", {})


def test_target_profile_inspection_preserves_canonical_data(
    native_library: Path,
) -> None:
    profile = _json("spec/targets/profiles/pcre2-10.43.json")
    result = NativeClient(native_library).inspect_target_profile(profile)
    assert result["target_profile"] == profile
    assert result["profile_reference"]["profile_id"] == "profile:pcre2/10.43"
