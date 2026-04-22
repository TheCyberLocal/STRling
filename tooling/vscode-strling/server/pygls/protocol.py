"""Minimal protocol surface consumed by the bundled STRling server.

The real ``pygls`` package exposes a richer protocol object. The extension only
needs the placeholders below so the server can construct its transport layer
without importing external dependencies at startup.
"""


def default_converter():
    return None


class LanguageServerProtocol:
    """Lightweight placeholder for the server's protocol class."""

    pass
