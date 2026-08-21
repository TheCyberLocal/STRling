from __future__ import annotations

import unittest

from tooling import go_dart_swift_stdlib_surfaces as surfaces


class GoDartSwiftStdlibSurfaceTests(unittest.TestCase):
    def test_checked_in_outputs_reproduce(self) -> None:
        self.assertEqual(
            surfaces.synchronize(write=False),
            {"status": "passed", "outputs": 3, "mismatches": []},
        )

    def test_every_output_has_five_helper_identities(self) -> None:
        expected = {
            "stdlib.date_time",
            "stdlib.email",
            "stdlib.ip",
            "stdlib.url",
            "stdlib.uuid",
        }
        for path, content in surfaces.build_outputs().items():
            text = content.decode("utf-8")
            with self.subTest(path=path.name):
                self.assertEqual({item for item in expected if item in text}, expected)

    def test_outputs_record_lexical_identity_without_semantics(self) -> None:
        forbidden = ("regex", "pattern_source", "semantic_validator", "isValid")
        for path, content in surfaces.build_outputs().items():
            text = content.decode("utf-8")
            with self.subTest(path=path.name):
                for marker in forbidden:
                    self.assertNotIn(marker, text)
                self.assertIn("stdlibhelper", text.casefold())

    def test_generator_uses_registry_fingerprint(self) -> None:
        registry = surfaces._registry()
        fingerprint = surfaces._source_fingerprint(registry)
        for content in surfaces.build_outputs().values():
            self.assertIn(fingerprint, content.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
