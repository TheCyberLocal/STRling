from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tooling/performance_resource_certification.py"
TASK = ROOT / "docs/migration/records/performance-resource-certification.yaml"
CHANGE_CONTROL = ROOT / "governance/change-control.json"


class PerformanceResourceCertificationArchitectureTests(unittest.TestCase):
    def test_controller_is_verification_only_and_offline(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        for forbidden in (
            "from core",
            "import core",
            "from bindings",
            "import bindings",
            "requests",
            "urllib",
            "socket",
            "subprocess",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("write_text(", source)
        self.assertNotIn("write_bytes(", source)

    def test_task_scope_forbids_product_and_public_authority(self) -> None:
        source = TASK.read_text(encoding="utf-8")
        for required in (
            "- core/src/**",
            "- bindings/*/src/**",
            "- packages/**",
            "- spec/contracts/**",
            "runtime performance claims remain unchanged",
            "publication, release, upload, push",
        ):
            self.assertIn(required, source)

    def test_active_change_control_points_to_performance_record(self) -> None:
        change_control = json.loads(CHANGE_CONTROL.read_text(encoding="utf-8"))
        self.assertEqual(
            change_control["active_task"],
            "docs/migration/records/performance-resource-certification.yaml",
        )

    def test_schema_is_engineering_only(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "governance/schemas/performance-resource-certification.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            schema["$id"],
            "https://strling.dev/governance/performance-resource-certification.schema.json",
        )
        serialized = json.dumps(schema)
        self.assertNotIn("CompileRequest schema", serialized)
        self.assertNotIn("target profile schema", serialized)


if __name__ == "__main__":
    unittest.main()
