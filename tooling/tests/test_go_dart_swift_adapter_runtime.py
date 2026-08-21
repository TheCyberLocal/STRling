from __future__ import annotations

import unittest

from tooling import go_dart_swift_adapter_runtime


class GoDartSwiftAdapterRuntimeTests(unittest.TestCase):
    def test_default_native_path_is_absolute_and_platform_named(self) -> None:
        path = go_dart_swift_adapter_runtime._native_default()
        self.assertTrue(path.is_absolute())
        self.assertIn("strling_interop", path.name)

    def test_fingerprint_is_key_order_independent(self) -> None:
        self.assertEqual(
            go_dart_swift_adapter_runtime._fingerprint({"a": 1, "b": 2}),
            go_dart_swift_adapter_runtime._fingerprint({"b": 2, "a": 1}),
        )

    def test_operation_denominator_is_closed(self) -> None:
        self.assertEqual(
            go_dart_swift_adapter_runtime.OPERATIONS,
            ("describe", "compile", "target_profile", "simply"),
        )
        self.assertEqual(
            go_dart_swift_adapter_runtime.BINDINGS,
            ("go", "dart", "swift"),
        )
        for marker in (
            "STRLING_PROBE_ABI",
            "STRLING_PROBE_OVERSIZE",
            "STRLING_PROBE_DUPLICATE",
            "STRLING_PROBE_INVALID_UTF8",
        ):
            with self.subTest(probe=marker):
                self.assertIn(marker, go_dart_swift_adapter_runtime.PROBE_SOURCE)

    def test_governed_tool_versions_accept_only_declared_ranges(self) -> None:
        valid = {
            "go": "go version go1.22.12 windows/amd64",
            "dart": "Dart SDK version: 3.8.1 (stable)",
            "swift": "Swift version 6.1.2 (swift-6.1.2-RELEASE)",
        }
        go_dart_swift_adapter_runtime._assert_tool_versions(valid)
        for tool, value in (
            ("go", "go version go1.23.0 windows/amd64"),
            ("dart", "Dart SDK version: 4.0.0 (stable)"),
            ("swift", "Swift version 7.0.0 (swift-7.0.0-RELEASE)"),
        ):
            with self.subTest(tool=tool):
                invalid = dict(valid)
                invalid[tool] = value
                with self.assertRaises(
                    go_dart_swift_adapter_runtime.GoDartSwiftAdapterRuntimeError
                ):
                    go_dart_swift_adapter_runtime._assert_tool_versions(invalid)


if __name__ == "__main__":
    unittest.main()
