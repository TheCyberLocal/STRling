from __future__ import annotations

import unittest

from tooling import go_dart_swift_adapter_package


class GoDartSwiftAdapterPackageTests(unittest.TestCase):
    def test_certification_identity_is_stable(self) -> None:
        self.assertEqual(
            go_dart_swift_adapter_package.OPERATION_ID,
            "certification.go-dart-swift-adapter-package",
        )

    def test_missing_tool_is_explicitly_unavailable(self) -> None:
        with self.assertRaises(FileNotFoundError):
            go_dart_swift_adapter_package._tool("strling-tool-that-does-not-exist")

    def test_consumer_directories_cannot_alias_dependency_identities(self) -> None:
        self.assertEqual(
            set(go_dart_swift_adapter_package.CONSUMER_DIRECTORIES),
            {"go", "dart", "swift"},
        )
        for binding, directory in (
            go_dart_swift_adapter_package.CONSUMER_DIRECTORIES.items()
        ):
            with self.subTest(binding=binding):
                self.assertNotEqual(directory, binding)

    def test_governed_tool_versions_accept_only_declared_ranges(self) -> None:
        valid = {
            "go": "go version go1.22.12 linux/amd64",
            "dart": "Dart SDK version: 3.8.1 (stable)",
            "swift": "Swift version 5.10.1 (swift-5.10.1-RELEASE)",
        }
        go_dart_swift_adapter_package._assert_tool_versions(valid)
        for tool, value in (
            ("go", "go version go1.21.13 linux/amd64"),
            ("dart", "Dart SDK version: 2.19.6 (stable)"),
            ("swift", "Swift version 7.0.0 (swift-7.0.0-RELEASE)"),
        ):
            with self.subTest(tool=tool):
                invalid = dict(valid)
                invalid[tool] = value
                with self.assertRaises(
                    go_dart_swift_adapter_package.GoDartSwiftAdapterPackageError
                ):
                    go_dart_swift_adapter_package._assert_tool_versions(invalid)


if __name__ == "__main__":
    unittest.main()
