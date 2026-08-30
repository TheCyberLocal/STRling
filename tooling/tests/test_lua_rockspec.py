from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tooling.lua_rockspec import (
    RockspecError,
    materialize,
    render_rockspec,
    rockspec_name,
    verify_rockspec,
)


TEMPLATE = """package = "strling"
version = "VERSION-1"
source = { tag = "vVERSION" }
"""


class LuaRockspecTests(unittest.TestCase):
    def test_render_preserves_release_revision_contract(self) -> None:
        self.assertIn('version = "3.0.0-1"', render_rockspec(TEMPLATE, "3.0.0"))
        self.assertIn(
            'version = "3.0.0-rc1-2"',
            render_rockspec(TEMPLATE, "3.0.0-rc1-2"),
        )
        self.assertEqual("strling-3.0.0-rc1-2.rockspec", rockspec_name("3.0.0-rc1-2"))

    def test_materialized_output_verifies_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.rockspec"
            template.write_text(TEMPLATE, encoding="utf-8")
            output = materialize("3.0.0", root, template)
            self.assertEqual("strling-3.0.0-1.rockspec", output.name)
            verify_rockspec("3.0.0", output, template)

    def test_verification_rejects_content_or_filename_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.rockspec"
            template.write_text(TEMPLATE, encoding="utf-8")
            output = materialize("3.0.0", root, template)
            output.write_text("stale\n", encoding="utf-8")
            with self.assertRaisesRegex(RockspecError, "content"):
                verify_rockspec("3.0.0", output, template)
            with self.assertRaisesRegex(RockspecError, "filename"):
                verify_rockspec("3.0.0", root / "wrong.rockspec", template)

    def test_template_requires_both_governed_placeholders(self) -> None:
        with self.assertRaisesRegex(RockspecError, "exactly one"):
            render_rockspec('version = "VERSION-1"\n', "3.0.0")


if __name__ == "__main__":
    unittest.main()
