from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "tooling/deep_quality_certification.py"
MANIFEST = ROOT / "tests/certification/deep-quality/1.0/manifest.json"
TASK_RECORD = ROOT / "docs/migration/records/deep-quality-certification.yaml"


class DeepQualityCertificationArchitectureTests(unittest.TestCase):
    def test_controller_is_verification_only(self) -> None:
        source = CONTROLLER.read_text(encoding="utf-8")
        forbidden = (
            "from core",
            "import core",
            "from bindings",
            "import bindings",
            "urllib",
            "requests",
            "socket",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_manifest_keeps_product_and_external_authority_out(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        serialized = json.dumps(manifest, sort_keys=True)
        self.assertEqual(manifest["authority"]["semantic_authority"], "spec")
        self.assertEqual(
            manifest["authority"]["external_regex_conformance"],
            "excluded-not-repository-authority",
        )
        self.assertNotIn("regex-conformance/", serialized)
        self.assertTrue(
            all(
                row["source_path"].startswith("bindings/interop/fuzz/fuzz_targets/")
                for row in manifest["fuzz_targets"]
            )
        )

    def test_task_scope_forbids_product_implementation_changes(self) -> None:
        record = TASK_RECORD.read_text(encoding="utf-8")
        for path in (
            "bindings/c/src/**",
            "bindings/cpp/src/**",
            "bindings/interop/src/**",
            "core/src/**",
            "spec/contracts/**",
            "spec/targets/**",
        ):
            with self.subTest(path=path):
                self.assertIn(f"        - {path}", record)

    def test_p17_interop_denominator_remains_a_companion(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        full = next(
            row for row in manifest["profile_partitions"] if row["id"] == "full"
        )
        self.assertEqual(
            full["required_companion_operations"],
            ["certification.interop", "certification.interop-adversarial"],
        )
        inherited = [
            row for row in manifest["fuzz_targets"] if row["ownership"] == "p17-inherited"
        ]
        self.assertEqual(len(inherited), 6)
        self.assertTrue(
            all(
                row["runner_operation"] == "certification.interop-adversarial"
                for row in inherited
            )
        )


if __name__ == "__main__":
    unittest.main()
