"""Minimal stub for pygls used in tests.

This is a tiny, local shim to allow the repo tests to import
`pygls.server` and `pygls.protocol` without requiring the real
pygls package to be installed in the system Python environment.
"""

from .server import JsonRPCServer
from .protocol import LanguageServerProtocol, default_converter

__all__ = ["JsonRPCServer", "LanguageServerProtocol", "default_converter"]
