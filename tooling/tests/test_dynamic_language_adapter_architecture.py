from __future__ import annotations

import json
import unittest

from tooling import dynamic_language_adapter_certification as certification


ROOT = certification.ROOT


class DynamicLanguageAdapterArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(
            (
                ROOT / "tests/adapters/dynamic-languages-3.0/legacy-baseline.json"
            ).read_text(encoding="utf-8")
        )

    def test_all_frozen_semantic_copy_paths_are_absent(self) -> None:
        remaining = [
            str(item["path"])
            for item in self.baseline["semantic_copy_files"]
            if (ROOT / str(item["path"])).exists()
        ]
        self.assertEqual(remaining, [])
        self.assertEqual(len(self.baseline["semantic_copy_files"]), 83)

    def test_each_bridge_resolves_only_the_governed_symbols(self) -> None:
        required = {
            "strling_interop_abi_version_v1",
            "strling_interop_execute_v1",
            "strling_interop_owned_bytes_free_v1",
        }
        paths = (
            "bindings/ruby/lib/strling/native_client.rb",
            "bindings/php/src/NativeClient.php",
            "bindings/perl/lib/STRling/NativeClient.pm",
            "bindings/lua/src/strling_native.c",
            "bindings/r/src/strling_r_native.c",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8").replace("'", '"')
            with self.subTest(path=relative):
                for symbol in required:
                    self.assertIn(symbol, text)
                self.assertNotIn("interop_v2", text)

    def test_absolute_path_abi_bounds_and_release_are_per_binding(self) -> None:
        expectations = {
            "bindings/ruby/lib/strling/native_client.rb": (
                "absolute?",
                "NATIVE_ABI_VERSION",
                "MAX_INTEROP_REQUEST_BYTES",
                "MAX_INTEROP_RESPONSE_BYTES",
                "@free.call(output)",
            ),
            "bindings/php/src/NativeClient.php": (
                "isAbsolute",
                "NATIVE_ABI_VERSION",
                "MAX_INTEROP_REQUEST_BYTES",
                "MAX_INTEROP_RESPONSE_BYTES",
                "strling_interop_owned_bytes_free_v1",
            ),
            "bindings/perl/lib/STRling/NativeClient.pm": (
                "file_name_is_absolute",
                "NATIVE_ABI_VERSION",
                "MAX_INTEROP_REQUEST_BYTES",
                "MAX_INTEROP_RESPONSE_BYTES",
                "free_fn",
            ),
            "bindings/lua/src/strling_native.c": (
                "strling_is_absolute",
                "STRLING_ABI_VERSION",
                "STRLING_MAX_REQUEST_BYTES",
                "STRLING_MAX_RESPONSE_BYTES",
                "client->release(&output)",
            ),
            "bindings/r/src/strling_r_native.c": (
                "strling_is_absolute",
                "STRLING_ABI_VERSION",
                "STRLING_MAX_REQUEST_BYTES",
                "STRLING_MAX_RESPONSE_BYTES",
                "client->release(&output)",
            ),
        }
        for relative, markers in expectations.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                for marker in markers:
                    self.assertIn(marker, text)

    def test_all_canonical_operations_are_routed_by_each_facade(self) -> None:
        operations = (
            "describe",
            "compile",
            "target_profile.inspect",
            "simply.compile",
        )
        paths = (
            "bindings/ruby/lib/strling/native_client.rb",
            "bindings/php/src/NativeClient.php",
            "bindings/perl/lib/STRling/NativeClient.pm",
            "bindings/lua/src/adapter.lua",
            "bindings/r/R/native_client.R",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                for operation in operations:
                    self.assertIn(operation, text)

    def test_no_product_runtime_contains_alternate_execution(self) -> None:
        forbidden = (
            "subprocess",
            "open3",
            "Net::HTTP",
            "curl_exec",
            "fsockopen",
            "io.popen",
            "os.execute",
            "download.file",
            "system(",
            "RegExp(",
            "PCRE2",
        )
        roots = {
            ROOT / "bindings/ruby/lib": {".rb"},
            ROOT / "bindings/php/src": {".php"},
            ROOT / "bindings/perl/lib": {".pm"},
            ROOT / "bindings/lua/src": {".lua", ".c"},
            ROOT / "bindings/r/R": {".R"},
            ROOT / "bindings/r/src": {".c"},
        }
        for root, suffixes in roots.items():
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in suffixes:
                    continue
                text = path.read_text(encoding="utf-8")
                with self.subTest(path=path.relative_to(ROOT).as_posix()):
                    for marker in forbidden:
                        self.assertNotIn(marker, text)

    def test_package_graphs_declare_transport_only_dependencies(self) -> None:
        ruby = (ROOT / "bindings/ruby/strling.gemspec").read_text(encoding="utf-8")
        php = json.loads(
            (ROOT / "bindings/php/composer.json").read_text(encoding="utf-8")
        )
        perl = (ROOT / "bindings/perl/Makefile.PL").read_text(encoding="utf-8")
        lua = (ROOT / "bindings/lua/strling-template.rockspec").read_text(
            encoding="utf-8"
        )
        r = (ROOT / "bindings/r/DESCRIPTION").read_text(encoding="utf-8")
        self.assertIn("'< 4.0'", ruby)
        self.assertEqual(set(php["require"]), {"php", "ext-ffi", "ext-json"})
        self.assertIn("'FFI::Platypus' => '2.10'", perl)
        self.assertNotIn("'Moo'", perl)
        self.assertIn('"lua >= 5.1, < 5.5"', lua)
        self.assertIn('"lua-cjson >= 2.1.0, < 3.0.0"', lua)
        self.assertIn("R (>= 4.3.0), R (< 5.0.0)", r)
        self.assertIn("Apache License (== 2.0)", r)

    def test_response_decoders_reject_duplicate_keys(self) -> None:
        markers = {
            "bindings/ruby/lib/strling/native_client.rb": "duplicate property",
            "bindings/php/src/StrictJson.php": "duplicate property",
            "bindings/perl/lib/STRling/StrictJSON.pm": "duplicate property",
            "bindings/lua/src/adapter.lua": "duplicate property",
            "bindings/r/R/strict_json.R": "duplicate property",
        }
        for relative, marker in markers.items():
            with self.subTest(path=relative):
                self.assertIn(marker, (ROOT / relative).read_text(encoding="utf-8"))

    def test_host_owned_transport_buffers_and_protocol_strings_fail_closed(
        self,
    ) -> None:
        ruby = (ROOT / "bindings/ruby/lib/strling/native_client.rb").read_text(
            encoding="utf-8"
        )
        perl = (ROOT / "bindings/perl/lib/STRling/NativeClient.pm").read_text(
            encoding="utf-8"
        )
        self.assertEqual(ruby.count("Fiddle::RUBY_FREE"), 2)
        self.assertIn("_is_json_string($error->{code})", perl)
        self.assertIn("_is_json_string($error->{path})", perl)

    def test_generated_lexical_surfaces_have_one_canonical_fingerprint(self) -> None:
        registry = json.loads(
            (ROOT / "spec/stdlib/registry/1.0/registry.json").read_text(
                encoding="utf-8"
            )
        )
        fingerprint = str(registry["fingerprint"]["value"]).removeprefix("sha256:")
        paths = (
            "bindings/ruby/lib/strling/stdlib_generated.rb",
            "bindings/php/src/Stdlib.php",
            "bindings/perl/lib/STRling/StdlibGenerated.pm",
            "bindings/lua/src/stdlib_generated.lua",
            "bindings/r/R/stdlib_generated.R",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertIn(fingerprint, text)
                for helper in (
                    "stdlib.date_time",
                    "stdlib.email",
                    "stdlib.ip",
                    "stdlib.url",
                    "stdlib.uuid",
                ):
                    self.assertIn(helper, text)
                self.assertIn("do not validate semantics", text)

    def test_transport_probes_are_wired_into_each_adapter_suite(self) -> None:
        markers = (
            "STRLING_DYNAMIC_PROBE",
            "STRLING_DYNAMIC_ABI_PROBE",
            "STRLING_DYNAMIC_OVERSIZE_PROBE",
            "STRLING_DYNAMIC_DUPLICATE_PROBE",
            "STRLING_DYNAMIC_INVALID_UTF8_PROBE",
            "STRLING_DYNAMIC_RELEASE_FAILURE_PROBE",
        )
        paths = (
            "bindings/ruby/test/adapter_test.rb",
            "bindings/php/tests/AdapterTest.php",
            "bindings/perl/t/adapter.t",
            "bindings/lua/spec/adapter_spec.lua",
            "bindings/r/tests/testthat/test-adapter.R",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                for marker in markers:
                    self.assertIn(marker, text)

    def test_live_suites_project_the_same_multibyte_request_and_result(self) -> None:
        paths = (
            "bindings/ruby/test/adapter_test.rb",
            "bindings/php/tests/AdapterTest.php",
            "bindings/perl/t/adapter.t",
            "bindings/lua/spec/adapter_spec.lua",
            "bindings/r/tests/testthat/test-adapter.R",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertIn('literal "雪"', text)
                self.assertIn("unicode", text)
                self.assertIn("雪", text)
                self.assertIn("STRLING_DYNAMIC_EVIDENCE_DIR", text)

    def test_ruby_live_suite_exercises_shared_client_reentrancy(self) -> None:
        text = (ROOT / "bindings/ruby/test/adapter_test.rb").read_text(encoding="utf-8")
        self.assertIn("Array.new(4)", text)
        self.assertIn("Thread.new", text)
        self.assertIn("STRLING_DYNAMIC_CONCURRENCY_PROBE", text)
        self.assertIn("concurrent.describe == expected", text)


if __name__ == "__main__":
    unittest.main()
