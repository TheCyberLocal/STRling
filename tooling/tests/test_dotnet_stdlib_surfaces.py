from __future__ import annotations

import unittest

from tooling.dotnet_stdlib_surfaces import build_outputs


class DotNetStdlibSurfaceTests(unittest.TestCase):
    def test_outputs_cover_all_helpers_and_are_lf_stable(self) -> None:
        outputs = build_outputs()
        self.assertEqual(2, len(outputs))
        for content in outputs.values():
            for helper_id in (
                "stdlib.date_time",
                "stdlib.email",
                "stdlib.ip",
                "stdlib.url",
                "stdlib.uuid",
            ):
                self.assertIn(helper_id.encode(), content)
            self.assertNotIn(b"\r\n", content)
            self.assertTrue(content.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
