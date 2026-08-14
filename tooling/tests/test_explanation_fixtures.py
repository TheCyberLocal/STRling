from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tooling import explanation_fixtures
from tooling.explanation_fixtures import ExplanationFixtureError


class ExplanationFixtureTests(unittest.TestCase):
    def test_checked_outputs_are_current_and_deterministic(self) -> None:
        first = explanation_fixtures.check_outputs()
        second = explanation_fixtures.check_outputs()
        self.assertEqual(first, second)
        self.assertEqual(2, first["outputs"])
        self.assertRegex(first["fingerprint"], r"^[0-9a-f]{64}$")

    def test_missing_and_stale_outputs_fail(self) -> None:
        missing = explanation_fixtures.ROOT / "missing.txt"
        with patch.object(explanation_fixtures, "OUTPUTS", {missing: "concise"}):
            with patch.object(Path, "is_file", return_value=False):
                with self.assertRaisesRegex(ExplanationFixtureError, "missing"):
                    explanation_fixtures.check_outputs()
            with (
                patch.object(Path, "is_file", return_value=True),
                patch.object(Path, "read_text", return_value="stale\n"),
            ):
                with self.assertRaisesRegex(ExplanationFixtureError, "stale"):
                    explanation_fixtures.check_outputs()


if __name__ == "__main__":
    unittest.main()
