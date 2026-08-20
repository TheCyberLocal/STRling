from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from STRling.interop import (
    INTEROP_PROTOCOL_VERSION,
    MAX_INTEROP_REQUEST_BYTES,
    InteropProtocolError,
    NativeAdapterError,
    NativeClient,
    NativeLoadError,
    load_native,
)


def test_explicit_native_library_describes_exact_abi(native_library: Path) -> None:
    client = load_native(native_library)
    description = client.describe()
    assert description["protocol_version"] == INTEROP_PROTOCOL_VERSION
    assert description["native_abi"]["id"] == "strling.c-abi"
    assert description["native_abi"]["major"] == 1


def test_stable_protocol_errors_remain_values(native_library: Path) -> None:
    client = NativeClient(native_library)
    response = client.execute(
        {
            "interop_protocol_version": INTEROP_PROTOCOL_VERSION,
            "operation": "not-supported",
            "payload": {},
        }
    )
    assert response["status"] == "error"
    assert response["error"] == {
        "code": "STRL-INTEROP-0005",
        "path": "$.operation",
    }


def test_invalid_utf8_and_host_bounds_are_distinct(native_library: Path) -> None:
    client = NativeClient(native_library)
    response = client.execute_bytes(b"\xff")
    assert response["error"] == {"code": "STRL-INTEROP-0001", "path": "$"}
    with pytest.raises(NativeAdapterError):
        client.execute_bytes(b"0" * (MAX_INTEROP_REQUEST_BYTES + 1))


def test_non_finite_request_values_fail_before_native_execution(
    native_library: Path,
) -> None:
    with pytest.raises(NativeAdapterError, match="not strict JSON"):
        NativeClient(native_library).execute({"value": float("nan")})


def test_high_level_invalid_payload_raises_typed_interop_error(
    native_library: Path,
) -> None:
    client = NativeClient(native_library)
    with pytest.raises(InteropProtocolError) as captured:
        client.compile({})
    assert captured.value.code == "STRL-INTEROP-0007"
    assert captured.value.path == "$.payload.compile_request"


def test_repeated_owned_response_cycles(native_library: Path) -> None:
    client = NativeClient(native_library)
    for _ in range(128):
        assert client.describe()["protocol_version"] == INTEROP_PROTOCOL_VERSION


def test_native_calls_are_reentrant_and_deterministic(native_library: Path) -> None:
    client = NativeClient(native_library)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: client.describe(), range(64)))
    assert all(result == results[0] for result in results)


def test_missing_library_has_no_implicit_fallback(tmp_path: Path) -> None:
    with pytest.raises(NativeLoadError):
        load_native(tmp_path / "missing-native-library")
