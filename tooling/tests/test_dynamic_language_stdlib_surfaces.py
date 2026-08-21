from __future__ import annotations

import unittest

from tooling import dynamic_language_stdlib_surfaces as surfaces


class DynamicLanguageStdlibSurfaceTests(unittest.TestCase):
    def test_generated_surfaces_reproduce(self) -> None:
        self.assertEqual(surfaces.synchronize(write=False)["mismatches"], [])

    def test_five_outputs_share_canonical_helper_set(self) -> None:
        outputs = surfaces.build_outputs()
        self.assertEqual(len(outputs), 5)
        for path, content in outputs.items():
            text = content.decode("utf-8")
            with self.subTest(path=path.name):
                for helper in (
                    "stdlib.date_time",
                    "stdlib.email",
                    "stdlib.ip",
                    "stdlib.url",
                    "stdlib.uuid",
                ):
                    self.assertIn(helper, text)
                self.assertIn("do not validate semantics", text)


if __name__ == "__main__":
    unittest.main()
