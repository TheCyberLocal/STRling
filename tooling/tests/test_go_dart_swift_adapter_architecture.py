from __future__ import annotations

import unittest

from tooling import go_dart_swift_adapter_certification as certification


ROOT = certification.ROOT


class GoDartSwiftAdapterArchitectureTests(unittest.TestCase):
    def test_all_frozen_semantic_copy_paths_are_absent(self) -> None:
        remaining = [
            path for path in certification.SEMANTIC_PATHS if (ROOT / path).exists()
        ]
        self.assertEqual(remaining, [])

    def test_each_bridge_resolves_only_the_governed_symbols(self) -> None:
        paths = (
            "bindings/go/native_cgo.go",
            "bindings/dart/lib/src/native_client.dart",
            "bindings/swift/Sources/CSTRlingNative/strling_swift_native.c",
        )
        required = {
            "strling_interop_abi_version_v1",
            "strling_interop_execute_v1",
            "strling_interop_owned_bytes_free_v1",
        }
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8").replace("'", '"')
            with self.subTest(path=relative):
                self.assertTrue(required.issubset(set(text.split('"'))))
                self.assertNotIn("interop_v2", text)

    def test_absolute_path_and_bounds_are_present_per_binding(self) -> None:
        expectations = {
            "bindings/go/client.go": (
                "filepath.IsAbs",
                "MaxInteropRequestBytes",
                "MaxInteropResponseBytes",
            ),
            "bindings/dart/lib/src/native_client.dart": (
                "path.isAbsolute",
                "maxInteropRequestBytes",
                "maxInteropResponseBytes",
            ),
            "bindings/swift/Sources/STRling/NativeClient.swift": (
                "URL(fileURLWithPath:",
                "maxInteropRequestBytes",
                "maxInteropResponseBytes",
            ),
        }
        for relative, markers in expectations.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                for marker in markers:
                    self.assertIn(marker, text)

    def test_all_canonical_operations_are_routed_by_each_facade(self) -> None:
        operations = {
            '"describe"',
            '"compile"',
            '"target_profile.inspect"',
            '"simply.compile"',
        }
        for relative in (
            "bindings/go/client.go",
            "bindings/dart/lib/src/native_client.dart",
            "bindings/swift/Sources/STRling/NativeClient.swift",
        ):
            normalized = (ROOT / relative).read_text(encoding="utf-8").replace("'", '"')
            with self.subTest(path=relative):
                for operation in operations:
                    self.assertIn(operation, normalized)

    def test_no_product_facade_contains_alternate_execution_markers(self) -> None:
        forbidden = (
            "os/exec",
            "net/http",
            "Process.start",
            "Socket.connect",
            "HttpClient(",
            "RegExp(",
            "NSRegularExpression",
            "URLSession",
        )
        roots = (
            ROOT / "bindings/go",
            ROOT / "bindings/dart/lib",
            ROOT / "bindings/swift/Sources",
        )
        suffixes = {".go", ".dart", ".swift", ".c", ".h"}
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in suffixes:
                    continue
                text = path.read_text(encoding="utf-8")
                with self.subTest(path=path.relative_to(ROOT).as_posix()):
                    for marker in forbidden:
                        self.assertNotIn(marker, text)

    def test_package_graphs_declare_only_transport_dependencies(self) -> None:
        go_mod = (ROOT / "bindings/go/go.mod").read_text(encoding="utf-8")
        dart = (ROOT / "bindings/dart/pubspec.yaml").read_text(encoding="utf-8")
        swift = (ROOT / "bindings/swift/Package.swift").read_text(encoding="utf-8")
        self.assertNotIn("require (", go_mod)
        self.assertIn("ffi: ^2.1.2", dart)
        self.assertIn("path: ^1.8.0", dart)
        self.assertIn('name: "CSTRlingNative"', swift)
        self.assertNotIn(".package(", swift)

    def test_no_cgo_route_fails_closed(self) -> None:
        text = (ROOT / "bindings/go/native_nocgo.go").read_text(encoding="utf-8")
        self.assertIn("ErrCgoUnavailable", text)
        self.assertNotIn("SourceCompileRequest", text)

    def test_each_response_decoder_enforces_strict_utf8_and_duplicate_keys(
        self,
    ) -> None:
        expectations = {
            "bindings/go/client.go": ("utf8.Valid(raw)", "duplicate property"),
            "bindings/dart/lib/src/native_client.dart": (
                "allowMalformed: false",
                "_DuplicateKeyScanner",
            ),
            "bindings/swift/Sources/STRling/NativeClient.swift": (
                "String(data: data, encoding: .utf8)",
                "JSONDuplicateKeyValidator",
            ),
        }
        for relative, markers in expectations.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                for marker in markers:
                    self.assertIn(marker, text)

    def test_transport_probes_are_wired_into_every_adapter_suite(self) -> None:
        markers = (
            "STRLING_GDS_RELEASE_PROBE",
            "STRLING_GDS_ABI_PROBE",
            "STRLING_GDS_OVERSIZE_PROBE",
            "STRLING_GDS_DUPLICATE_PROBE",
            "STRLING_GDS_INVALID_UTF8_PROBE",
        )
        for relative in (
            "bindings/go/client_test.go",
            "bindings/dart/test/adapter_test.dart",
            "bindings/swift/Tests/STRlingAdapterTests/AdapterTests.swift",
            "tooling/go_dart_swift_adapter_runtime.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                for marker in markers:
                    self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
