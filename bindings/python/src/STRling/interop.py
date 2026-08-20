"""Thin ctypes adapter for the governed ``strling.c-abi`` version 1 boundary."""

from __future__ import annotations

import ctypes
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Union

INTEROP_PROTOCOL_VERSION = "1.0.0"
NATIVE_ABI_VERSION = 1
MAX_INTEROP_REQUEST_BYTES = 10_485_760
MAX_INTEROP_RESPONSE_BYTES = 33_554_432

_STATUS_RESPONSE_WRITTEN = 0


class NativeAdapterError(RuntimeError):
    """Base class for host loading, ABI, memory, and response failures."""


class NativeLoadError(NativeAdapterError):
    """The explicitly selected or bundled native library could not be loaded."""


class NativeAbiError(NativeAdapterError):
    """The native ABI returned a non-success status."""

    def __init__(self, message: str, status: int) -> None:
        self.status = status
        super().__init__("{} (status {})".format(message, status))


class InteropProtocolError(NativeAdapterError):
    """A versioned interop failure retaining its stable code and path."""

    def __init__(self, response: Mapping[str, Any]) -> None:
        error = response["error"]
        self.code = str(error["code"])
        self.path = str(error["path"])
        operation = response.get("operation")
        self.operation = str(operation) if operation is not None else None
        super().__init__("{} at {}".format(self.code, self.path))


class _OwnedBytes(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_uint8)),
        ("len", ctypes.c_size_t),
    ]


PathLike = Union[str, "Path"]


class NativeClient:
    """A reentrant native client with descriptor-scoped response ownership."""

    def __init__(self, library_path: PathLike) -> None:
        path = Path(library_path).resolve()
        if not path.is_file():
            raise NativeLoadError("native STRling library not found: {}".format(path))
        try:
            library = ctypes.CDLL(str(path))
        except OSError as error:
            raise NativeLoadError(str(error)) from error

        self.library_path = path
        self._library = library
        try:
            self._abi_version = library.strling_interop_abi_version_v1
            self._execute = library.strling_interop_execute_v1
            self._free = library.strling_interop_owned_bytes_free_v1
        except AttributeError as error:
            raise NativeLoadError(
                "native library does not export the complete strling.c-abi v1"
            ) from error

        self._abi_version.argtypes = []
        self._abi_version.restype = ctypes.c_uint32
        self._execute.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
            ctypes.POINTER(_OwnedBytes),
        ]
        self._execute.restype = ctypes.c_uint32
        self._free.argtypes = [ctypes.POINTER(_OwnedBytes)]
        self._free.restype = ctypes.c_uint32
        if self._abi_version() != NATIVE_ABI_VERSION:
            raise NativeLoadError("unsupported strling.c-abi version")

    def execute(self, request: Mapping[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(
                dict(request),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise NativeAdapterError(
                "interop request is not strict JSON: {}".format(error)
            ) from error
        return self.execute_bytes(encoded)

    def execute_bytes(self, request: bytes) -> dict[str, Any]:
        if len(request) > MAX_INTEROP_REQUEST_BYTES:
            raise NativeAdapterError(
                "interop request exceeds {} bytes".format(MAX_INTEROP_REQUEST_BYTES)
            )

        request_buffer = None
        request_pointer = ctypes.POINTER(ctypes.c_uint8)()
        if request:
            request_buffer = (ctypes.c_uint8 * len(request)).from_buffer_copy(request)
            request_pointer = ctypes.cast(
                request_buffer, ctypes.POINTER(ctypes.c_uint8)
            )
        output = _OwnedBytes()
        primary_error = None
        try:
            status = int(
                self._execute(request_pointer, len(request), ctypes.byref(output))
            )
            if status != _STATUS_RESPONSE_WRITTEN:
                raise NativeAbiError("native STRling execution failed", status)
            if (
                not bool(output.data)
                or output.len == 0
                or output.len > MAX_INTEROP_RESPONSE_BYTES
            ):
                raise NativeAdapterError(
                    "native STRling returned an invalid or oversized response"
                )
            raw = ctypes.string_at(output.data, output.len)
            try:
                text = raw.decode("utf-8", errors="strict")
                decoded = json.loads(text, parse_constant=_reject_json_constant)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                raise NativeAdapterError(
                    "native STRling response is not strict UTF-8 JSON: {}".format(error)
                ) from error
            return _decode_interop_response(decoded)
        except BaseException as error:
            primary_error = error
            raise
        finally:
            free_status = int(self._free(ctypes.byref(output)))
            if primary_error is None and free_status != _STATUS_RESPONSE_WRITTEN:
                raise NativeAbiError(
                    "native STRling response release failed", free_status
                )

    def describe(self) -> Any:
        return self._completed_result(
            {
                "interop_protocol_version": INTEROP_PROTOCOL_VERSION,
                "operation": "describe",
                "payload": {},
            }
        )

    def compile(
        self,
        compile_request: Mapping[str, Any],
        target_profile: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        payload = {"compile_request": dict(compile_request)}
        if target_profile is not None:
            payload["target_profile"] = dict(target_profile)
        return self._completed_result(
            {
                "interop_protocol_version": INTEROP_PROTOCOL_VERSION,
                "operation": "compile",
                "payload": payload,
            }
        )

    def inspect_target_profile(self, target_profile: Mapping[str, Any]) -> Any:
        return self._completed_result(
            {
                "interop_protocol_version": INTEROP_PROTOCOL_VERSION,
                "operation": "target_profile.inspect",
                "payload": {"target_profile": dict(target_profile)},
            }
        )

    def simply_compile(
        self,
        builder_request: Mapping[str, Any],
        target_profile: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        payload = {"builder_request": dict(builder_request)}
        if target_profile is not None:
            payload["target_profile"] = dict(target_profile)
        return self._completed_result(
            {
                "interop_protocol_version": INTEROP_PROTOCOL_VERSION,
                "operation": "simply.compile",
                "payload": payload,
            }
        )

    def _completed_result(self, request: Mapping[str, Any]) -> Any:
        response = self.execute(request)
        if response["status"] == "error":
            raise InteropProtocolError(response)
        return response["result"]


def load_native(library_path: Optional[PathLike] = None) -> NativeClient:
    """Load one explicit path or the exact library bundled in this wheel."""

    selected = (
        Path(library_path) if library_path is not None else bundled_library_path()
    )
    return NativeClient(selected)


def bundled_library_path() -> Path:
    return Path(__file__).with_name("_native") / _platform_library_name()


def _platform_library_name() -> str:
    if sys.platform == "win32":
        return "strling_interop.dll"
    if sys.platform == "darwin":
        return "libstrling_interop.dylib"
    return "libstrling_interop.so"


def _reject_json_constant(value: str) -> None:
    raise ValueError("non-standard JSON constant {}".format(value))


def _decode_interop_response(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NativeAdapterError("interop response must be an object")
    if value.get("interop_protocol_version") != INTEROP_PROTOCOL_VERSION or value.get(
        "status"
    ) not in ("completed", "error"):
        raise NativeAdapterError(
            "interop response has an unsupported version or status"
        )
    if value["status"] == "completed" and "result" not in value:
        raise NativeAdapterError("completed interop response has no result")
    if value["status"] == "error":
        error = value.get("error")
        if (
            not isinstance(error, dict)
            or not isinstance(error.get("code"), str)
            or not isinstance(error.get("path"), str)
        ):
            raise NativeAdapterError(
                "failed interop response has no stable code and path"
            )
    return value


__all__ = [
    "INTEROP_PROTOCOL_VERSION",
    "MAX_INTEROP_REQUEST_BYTES",
    "MAX_INTEROP_RESPONSE_BYTES",
    "NATIVE_ABI_VERSION",
    "InteropProtocolError",
    "NativeAbiError",
    "NativeAdapterError",
    "NativeClient",
    "NativeLoadError",
    "bundled_library_path",
    "load_native",
]
