"""Tests for registry-derived standard-library public surfaces."""

from __future__ import annotations

import unittest

from tooling.stdlib_surfaces import build_outputs, synchronize


class StandardLibrarySurfaceTests(unittest.TestCase):
    def test_closed_denominator_and_output_set(self) -> None:
        outputs, counts = build_outputs()
        self.assertEqual(14, len(outputs))
        self.assertEqual(5, counts["helpers"])
        self.assertEqual(8, counts["variants"])
        self.assertEqual(17, counts["bindings"])
        self.assertEqual(2, counts["adapters"])
        self.assertEqual(5, counts["profiles"])
        self.assertEqual(40, counts["portability_rows"])
        self.assertEqual(580, counts["execute_applications"])
        self.assertEqual(5, counts["not_applicable_applications"])
        self.assertEqual(
            8,
            sum(
                path.startswith("spec/stdlib/generated/semantic-dsl/")
                for path in outputs
            ),
        )

    def test_checked_outputs_reproduce_exactly(self) -> None:
        result = synchronize(write=False)
        self.assertEqual(0, result["changed"])
        self.assertEqual(0, result["removed"])


if __name__ == "__main__":
    unittest.main()
