from __future__ import annotations

import unittest

from tooling.jvm_stdlib_surfaces import build_outputs


class JvmStdlibSurfaceTests(unittest.TestCase):
    def test_outputs_are_generated_from_all_registry_helpers(self) -> None:
        outputs = build_outputs()
        self.assertEqual(2, len(outputs))
        java = next(value for path, value in outputs.items() if path.suffix == ".java")
        kotlin = next(value for path, value in outputs.items() if path.suffix == ".kt")
        for helper_id in (
            "stdlib.date_time",
            "stdlib.email",
            "stdlib.ip",
            "stdlib.url",
            "stdlib.uuid",
        ):
            self.assertIn(helper_id.encode(), java)
            self.assertIn(helper_id.encode(), kotlin)

    def test_outputs_are_lf_stable(self) -> None:
        for content in build_outputs().values():
            self.assertNotIn(b"\r\n", content)
            self.assertTrue(content.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
