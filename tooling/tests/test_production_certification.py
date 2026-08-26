from __future__ import annotations

import unittest
from unittest.mock import patch

from tooling.production_certification import (
    build_certification_environment,
    capture,
    fingerprint,
    parse_args,
    product_summary,
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

    @patch.dict("os.environ", {}, clear=True)
    def test_release_environment_pins_exact_certification_runtimes(self) -> None:
        environment = build_certification_environment()
        self.assertEqual("/opt/temurin-11.0.32+9", environment["JAVA_HOME"])
        self.assertIn("cpython-3.11.15", environment["STRLING_CPYTHON_311_BINARY"])
        self.assertEqual("1", environment["STRLING_CERTIFICATION_NO_REUSE"])

    def test_product_summary_is_derived_from_product_evidence(self) -> None:
        summary = product_summary(
            {
                "schema_version": "1.0.0",
                "evidence_fingerprint": "product-fingerprint",
                "deterministic_evidence": {
                    "authority": {
                        "source_profile": {
                            "artifact_schema_version": "2.0.0",
                            "definition_fingerprint": "profile-fingerprint",
                        }
                    },
                    "source_profile_evidence": {
                        "profile": {"definition_version": "4.0.0"}
                    },
                    "results": [
                        {
                            "evidence_area": "security",
                            "status": "passed",
                            "waiver_references": ["WVR-001"],
                        },
                        {"evidence_area": "security", "status": "passed"},
                    ],
                    "aggregate": {"status": "passed"},
                },
            }
        )
        self.assertEqual({"passed": 2}, summary["evidence_areas"]["security"])
        self.assertEqual(["WVR-001"], summary["waiver_references"])
        self.assertEqual("4.0.0", summary["profile_definition_version"])


if __name__ == "__main__":
    unittest.main()
