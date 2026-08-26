from __future__ import annotations

import unittest
from unittest.mock import patch

from tooling.production_certification import (
    capture,
    fingerprint,
    parse_args,
    render_report,
)


class ProductionCertificationTests(unittest.TestCase):
    @patch(
        "tooling.production_certification.subprocess.run",
        side_effect=FileNotFoundError("missing-tool"),
    )
    def test_fingerprint_probe_records_missing_executable(self, _run) -> None:
        result = capture(["missing-tool"])
        self.assertEqual(127, result.returncode)
        self.assertIn("missing-tool", result.stderr)

    def test_canonical_alias_requires_every_no_reuse_release_flag(self) -> None:
        args = parse_args(["--profile", "release", "--all", "--no-reuse", "--plain"])
        self.assertEqual("release", args.profile)
        self.assertTrue(args.all)
        self.assertTrue(args.no_reuse)
        self.assertTrue(args.plain)

    def test_report_is_derived_from_structured_evidence(self) -> None:
        artifact = {
            "deterministic_evidence": {
                "status": "passed",
                "source": {"sha": "a" * 40},
                "command": "canonical command",
                "no_reuse": {"honored": True},
                "aggregate": {
                    "status": "passed",
                    "passed": 122,
                    "failed": 0,
                    "unavailable": 0,
                    "incomplete": 0,
                },
                "artifacts": {"profile": "/tmp/profile.json"},
            }
        }
        report = render_report(artifact)
        self.assertIn("Passed operations: `122`", report)
        self.assertIn("Failed operations: `0`", report)
        self.assertIn("No reuse: `true`", report)

    def test_fingerprint_is_order_independent(self) -> None:
        self.assertEqual(fingerprint({"a": 1, "b": 2}), fingerprint({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
