from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tooling/performance_resource_certification.py"
RUNNER_MANIFEST = (
    ROOT / "tests/certification/performance-resource/1.0/runner/Cargo.toml"
)
RUNNER_SOURCE = ROOT / "tests/certification/performance-resource/1.0/runner/src/main.rs"
BARE_METAL_ENVIRONMENT = (
    ROOT
    / "tests/certification/performance-resource/1.0/environment/bare_metal_linux.py"
)
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
            "http://",
            "https://",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("import subprocess", source)
        self.assertIn('"--offline"', source)
        self.assertIn("governed_root", source)
        self.assertIn("STRLING_PERFORMANCE_HOST_ATTESTATION", source)
        self.assertIn("cgroup_cpuset_effective", source)
        self.assertIn("unsupported-host-attestation", source)
        self.assertIn("embedded reservation evidence changed", source)
        self.assertIn("authenticated-identical-before-each-repetition", source)
        self.assertNotIn("write_text(", source)
        self.assertNotIn("write_bytes(", source)

    def test_runner_is_publish_false_and_resists_optimization(self) -> None:
        manifest = RUNNER_MANIFEST.read_text(encoding="utf-8")
        source = RUNNER_SOURCE.read_text(encoding="utf-8")
        self.assertIn("publish = false", manifest)
        self.assertIn("std::hint::black_box", source)
        self.assertIn('"memory:kernel-peak-rss"', source)
        self.assertIn('"unit": "nanoseconds"', source)
        self.assertIn('"batch_iterations"', source)
        self.assertIn("minimum_sample_nanoseconds", source)
        self.assertIn('"/proc/self/cgroup"', source)
        self.assertIn('resource_root.join("cpu.max")', source)
        self.assertIn("current_clocksource", source)

    def test_bare_metal_qualification_is_offline_and_fail_closed(self) -> None:
        source = BARE_METAL_ENVIRONMENT.read_text(encoding="utf-8")
        for required in (
            "/sys/devices/system/cpu/isolated",
            "nohz_full",
            "rcu_nocbs",
            "irqaffinity",
            "unrelated_schedulable_tasks",
            "thermal_throttle_counts",
            '"reservation_evidence": evidence',
            'governor != "performance"',
            'preference != "performance"',
            'evidence["clocksource"] != "tsc"',
        ):
            self.assertIn(required, source)
        for forbidden in ("requests", "urllib", "socket", "http://", "https://"):
            self.assertNotIn(forbidden, source)

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
