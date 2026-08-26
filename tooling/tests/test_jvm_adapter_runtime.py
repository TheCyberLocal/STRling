from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tooling import jvm_adapter_runtime as runtime


class JvmAdapterRuntimeTests(unittest.TestCase):
    def test_fingerprint_is_order_stable(self) -> None:
        self.assertEqual(
            runtime._fingerprint({"b": 2, "a": 1}),
            runtime._fingerprint({"a": 1, "b": 2}),
        )

    def test_repository_gradle_wrapper_precedes_host_tool(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper = (
                root
                / "bindings/kotlin"
                / ("gradlew.bat" if runtime.os.name == "nt" else "gradlew")
            )
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text("governed wrapper", encoding="utf-8")
            with (
                patch.object(runtime, "ROOT", root),
                patch.object(runtime, "_tool", side_effect=AssertionError),
            ):
                self.assertEqual(str(wrapper), runtime._gradle_tool())

    def test_host_gradle_is_fallback_when_wrapper_is_absent(self) -> None:
        with TemporaryDirectory() as directory:
            with (
                patch.object(runtime, "ROOT", Path(directory)),
                patch.object(runtime, "_tool", return_value="host-gradle") as tool,
            ):
                self.assertEqual("host-gradle", runtime._gradle_tool())
                tool.assert_called_once_with("STRLING_GRADLE", ("gradle", "gradle.bat"))


if __name__ == "__main__":
    unittest.main()
