from __future__ import annotations

import json
from pathlib import Path

import pytest

from STRling import simply
from STRling.interop import NativeClient

ROOT = Path(__file__).resolve().parents[3]
PROFILE_REFERENCE = {
    "profile_id": "profile:pcre2/10.43",
    "profile_version": "1.3.0",
    "sha256": "56762a1d289d41d0811b007695464916fda0ca5c48c2f5569b4ec26983a24bff",
}
COMPILE = {
    "target_profile": PROFILE_REFERENCE,
    "requested_outputs": ["semantic", "portability", "target_artifact"],
    "compiler_options": {
        "partial_semantics": "forbid",
        "diagnostic_policy": {"minimum_severity": "hint"},
    },
}


def _profile():
    return json.loads(
        (ROOT / "spec/targets/profiles/pcre2-10.43.json").read_text(encoding="utf-8")
    )


def test_sequence_and_callable_repetition_use_simply_11(
    native_library: Path,
) -> None:
    pattern = simply.merge(simply.lit("A"), simply.digit(1, 3))
    response = pattern.compile(NativeClient(native_library), COMPILE, _profile())
    assert response["status"] == "success"
    assert response["protocol_version"] == "1.1.0"
    assert response["compile_result"]["outcome"] == "succeeded"


def test_every_generated_helper_identity_is_exposed() -> None:
    assert simply.STDLIB_HELPER_IDS == (
        "stdlib.date_time",
        "stdlib.email",
        "stdlib.ip",
        "stdlib.url",
        "stdlib.uuid",
    )
    request = simply.email().build_request(COMPILE)
    assert request["steps"][0] == {
        "step_id": "stdlib-helper-1",
        "operation": "stdlib_helper",
        "arguments": {"helper_id": "stdlib.email", "parameters": {}},
    }


def test_lexical_helper_is_not_strengthened_in_python() -> None:
    serialized = json.dumps(simply.ip(4).build_request(COMPILE))
    assert '"helper_id": "stdlib.ip"' in serialized
    assert "semantic_validator" not in serialized


def test_runtime_regex_simulation_and_rendering_are_retired() -> None:
    pattern = simply.lit("abc")
    with pytest.raises(simply.STRlingError, match="retired"):
        pattern.exec("abc")
    with pytest.raises(simply.STRlingError, match="retired"):
        str(pattern)


def test_builder_owned_values_cannot_cross_instances() -> None:
    left = simply.SimplyPreviewBuilder("left")
    right = simply.SimplyPreviewBuilder("right")
    value = left.literal("literal", "x")
    with pytest.raises(simply.SimplyPreviewTransportError):
        right.build_request(value, COMPILE)
