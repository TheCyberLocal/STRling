"""Python facade over the canonical STRling native interop boundary."""

from . import simply
from STRling.compiler import Compiler, parse, parse_to_artifact, source_compile_request
from STRling.interop import (
    INTEROP_PROTOCOL_VERSION,
    InteropProtocolError,
    NativeAbiError,
    NativeAdapterError,
    NativeClient,
    NativeLoadError,
    bundled_library_path,
    load_native,
)

__all__ = [
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
