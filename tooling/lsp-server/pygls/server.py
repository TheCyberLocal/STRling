from typing import Callable


class JsonRPCServer:
    """Minimal JsonRPCServer shim for tests.

    Provides a `feature` decorator and stubbed lifecycle methods that
    the test-suite imports. This is intentionally minimal and only
    implements the surface area the repository's tests expect.
    """

    def __init__(self, protocol_cls=None, converter_factory=None):
        self._features = {}

    def feature(self, name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            # store a reference for potential introspection
            self._features.setdefault(name, []).append(func)
            return func

        return decorator

    def start_tcp(self, host: str, port: int) -> None:
        return None

    def start_io(self) -> None:
        return None

    def show_message_log(self, msg: str) -> None:
        # no-op for tests
        return None

    def text_document_publish_diagnostics(self, params) -> None:
        # no-op for tests
        return None
