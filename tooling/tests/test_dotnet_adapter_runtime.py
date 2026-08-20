from __future__ import annotations

import unittest

from tooling import dotnet_adapter_runtime


class DotNetAdapterRuntimeTests(unittest.TestCase):
    def test_default_native_path_is_absolute_and_platform_named(self) -> None:
        path = dotnet_adapter_runtime._native_default()
        self.assertTrue(path.is_absolute())
        self.assertIn("strling_interop", path.name)

    def test_fingerprint_is_key_order_independent(self) -> None:
        self.assertEqual(
            dotnet_adapter_runtime._fingerprint({"a": 1, "b": 2}),
            dotnet_adapter_runtime._fingerprint({"b": 2, "a": 1}),
        )


if __name__ == "__main__":
    unittest.main()
