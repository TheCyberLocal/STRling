from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tooling.performance_resource_certification import (
    FIXTURE_IDS,
    OPERATION_IDS,
    PERFORMANCE_OPERATION_IDS,
    RESOURCE_OPERATION_IDS,
    PerformanceResourceError,
    compare_hard_metric,
    derived_relative_budget_basis_points,
    document_fingerprint,
    environment_fingerprint,
    environments_compatible,
    load_json,
    sample_statistics,
    validate_baseline,
    validate_evidence,
    validate_fixture_manifest,
    validate_manifest,
    validate_repository_contract,
    validate_resource_inventory,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    ROOT / "governance/schemas/performance-resource-certification.schema.json"
)
MANIFEST_PATH = ROOT / "tests/certification/performance-resource/1.0/manifest.json"
FIXTURE_PATH = (
    ROOT
    / "tests/certification/performance-resource/1.0/fixtures/fixture-manifest.json"
)
INVENTORY_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/fixtures/resource-limits.json"
)
EVIDENCE_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/valid-evidence.json"
)


class PerformanceResourceCertificationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.manifest = load_json(MANIFEST_PATH)
        cls.fixtures = load_json(FIXTURE_PATH)
        cls.inventory = load_json(INVENTORY_PATH)
        cls.evidence = load_json(EVIDENCE_PATH)

    def test_schema_and_repository_contract_validate(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        validate_fixture_manifest(self.fixtures)
        validate_resource_inventory(self.inventory)
        validate_manifest(
            self.manifest,
            fixtures=self.fixtures,
            inventory=self.inventory,
        )
        validate_evidence(self.evidence, manifest=self.manifest)
        result = validate_repository_contract()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["operation_count"], 22)
        self.assertEqual(result["fixture_count"], 12)
        self.assertEqual(result["resource_declaration_count"], 56)

    def test_denominators_and_profile_partition_are_exact(self) -> None:
        self.assertEqual(
            [row["id"] for row in self.manifest["operations"]], OPERATION_IDS
        )
        self.assertEqual(
            [row["id"] for row in self.fixtures["fixtures"]], FIXTURE_IDS
        )
        partitions = {
            row["id"]: row for row in self.manifest["profile_partitions"]
        }
        self.assertEqual(partitions["local"]["operation_ids"], [])
        self.assertEqual(
            partitions["pull-request"]["operation_ids"], RESOURCE_OPERATION_IDS
        )
        self.assertEqual(partitions["full"]["operation_ids"], OPERATION_IDS)
        self.assertTrue(
            all(
                row["state"] == "planned"
                for row in self.manifest["operations"]
                if row["id"] in PERFORMANCE_OPERATION_IDS
            )
        )
        self.assertTrue(
            all(
                row["state"] == "active"
                for row in self.manifest["operations"]
                if row["id"] in RESOURCE_OPERATION_IDS
            )
        )

    def test_fixture_classes_and_resource_sources_are_complete(self) -> None:
        self.assertEqual(
            {row["class"] for row in self.fixtures["fixtures"]},
            {"tiny", "common", "large", "pathological"},
        )
        self.assertEqual(len(self.inventory["families"]), 9)
        self.assertEqual(
            sum(
                len(source["declarations"])
                for family in self.inventory["families"]
                for source in family["sources"]
            ),
            56,
        )
        test_paths = {
            source["path"]
            for family in self.inventory["families"]
            for source in family["test_sources"]
        }
        self.assertEqual(len(test_paths), 19)

    def test_robust_statistics_use_locked_nearest_rank_method(self) -> None:
        samples = list(range(1, 65))
        self.assertEqual(
            sample_statistics(samples),
            {
                "sample_count": 64,
                "median": 32,
                "p95": 61,
                "mad": 16,
                "minimum": 1,
                "maximum": 64,
            },
        )

    def test_budget_derivation_rejects_unstable_baselines(self) -> None:
        self.assertEqual(
            derived_relative_budget_basis_points(median=1000, mad=10), 1000
        )
        self.assertEqual(
            derived_relative_budget_basis_points(median=1000, mad=40), 2400
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            derived_relative_budget_basis_points(median=1000, mad=100)
        self.assertEqual(raised.exception.code, "unstable-baseline")

    def test_controlled_regression_boundaries_fail_closed(self) -> None:
        inside = compare_hard_metric(
            baseline_median=1000,
            observed_median=1099,
            relative_regression_basis_points=1000,
            absolute_ceiling=1500,
        )
        exact = compare_hard_metric(
            baseline_median=1000,
            observed_median=1100,
            relative_regression_basis_points=1000,
            absolute_ceiling=1500,
        )
        relative_over = compare_hard_metric(
            baseline_median=1000,
            observed_median=1101,
            relative_regression_basis_points=1000,
            absolute_ceiling=1500,
        )
        absolute_over = compare_hard_metric(
            baseline_median=1000,
            observed_median=1501,
            relative_regression_basis_points=10000,
            absolute_ceiling=1500,
        )
        self.assertEqual(inside["status"], "passed")
        self.assertEqual(exact["status"], "passed")
        self.assertEqual(relative_over["status"], "failed")
        self.assertFalse(relative_over["relative_passed"])
        self.assertEqual(absolute_over["status"], "failed")
        self.assertFalse(absolute_over["absolute_passed"])

    def test_environment_compatibility_is_exact_and_fail_closed(self) -> None:
        environment = self._environment()
        self.assertTrue(environments_compatible(environment, copy.deepcopy(environment)))
        for field, changed in (
            ("os_version", "different"),
            ("cpu_model", "different"),
            ("logical_cpu_count", 99),
            ("rustc_version", "rustc 9.9.9"),
            ("feature_set", ["different"]),
        ):
            observed = copy.deepcopy(environment)
            observed[field] = changed
            self.assertFalse(environments_compatible(environment, observed), field)

    def test_active_baseline_authenticates_samples_stats_budget_and_update(self) -> None:
        baseline = self._baseline()
        Draft202012Validator(self.schema).validate(baseline)
        validate_baseline(baseline, manifest=self.manifest, synthetic=True)

        mutations: list[tuple[str, Any]] = [
            ("environment_fingerprint", "0" * 64),
            ("update_command", "silent update is forbidden"),
        ]
        for field, value in mutations:
            changed = copy.deepcopy(baseline)
            changed[field] = value
            changed["baseline_fingerprint"] = document_fingerprint(
                changed, "baseline_fingerprint"
            )
            with self.assertRaises(PerformanceResourceError):
                validate_baseline(changed, manifest=self.manifest, synthetic=True)

        stale_samples = copy.deepcopy(baseline)
        stale_samples["measurements"][0]["samples"][-1] += 100
        stale_samples["baseline_fingerprint"] = document_fingerprint(
            stale_samples, "baseline_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_baseline(stale_samples, manifest=self.manifest, synthetic=True)
        self.assertEqual(raised.exception.code, "stale-statistics")

        weakened_budget = copy.deepcopy(baseline)
        weakened_budget["measurements"][0]["budget"][
            "relative_regression_basis_points"
        ] = 4000
        weakened_budget["baseline_fingerprint"] = document_fingerprint(
            weakened_budget, "baseline_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_baseline(weakened_budget, manifest=self.manifest, synthetic=True)
        self.assertEqual(raised.exception.code, "budget-derivation")

    def test_controlled_manifest_mutations_fail_closed(self) -> None:
        removed = copy.deepcopy(self.manifest)
        removed["operations"].pop()
        removed["manifest_fingerprint"] = document_fingerprint(
            removed, "manifest_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_manifest(removed, fixtures=self.fixtures, inventory=self.inventory)
        self.assertEqual(raised.exception.code, "operation-denominator")

        activated = copy.deepcopy(self.manifest)
        activated["operations"][0]["state"] = "active"
        activated["manifest_fingerprint"] = document_fingerprint(
            activated, "manifest_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_manifest(
                activated, fixtures=self.fixtures, inventory=self.inventory
            )
        self.assertEqual(raised.exception.code, "premature-activation")

        shrunk = copy.deepcopy(self.manifest)
        shrunk["profile_partitions"][1]["operation_ids"].pop()
        shrunk["manifest_fingerprint"] = document_fingerprint(
            shrunk, "manifest_fingerprint"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_manifest(shrunk, fixtures=self.fixtures, inventory=self.inventory)
        self.assertEqual(raised.exception.code, "profile-partition")

        stale = copy.deepcopy(self.manifest)
        stale["measurement_policy"]["sample_iterations"] = 63
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_manifest(stale, fixtures=self.fixtures, inventory=self.inventory)
        self.assertEqual(raised.exception.code, "manifest-fingerprint")

    def test_positive_fixture_cannot_claim_live_measurement_or_baseline(self) -> None:
        self.assertEqual(
            self.evidence["evidence_kind"], "synthetic-contract-fixture"
        )
        details = self.evidence["deterministic_evidence"]["checks"][0]["details"]
        self.assertFalse(details["live_measurement"])
        self.assertFalse(details["baseline_authority"])
        changed = copy.deepcopy(self.evidence)
        changed["deterministic_evidence"]["checks"][0]["details"][
            "live_measurement"
        ] = True
        changed["evidence_fingerprint"] = document_fingerprint(
            changed["deterministic_evidence"], "not-present"
        )
        with self.assertRaises(PerformanceResourceError) as raised:
            validate_evidence(changed, manifest=self.manifest)
        self.assertEqual(raised.exception.code, "fixture-check")

    @staticmethod
    def _environment() -> dict[str, Any]:
        return {
            "os": "linux",
            "os_version": "synthetic-contract-fixture",
            "architecture": "x86_64",
            "cpu_model": "synthetic-cpu",
            "logical_cpu_count": 8,
            "memory_bytes": 17179869184,
            "rustc_version": "rustc 1.75.0",
            "cargo_version": "cargo 1.75.0",
            "target_triple": "x86_64-unknown-linux-gnu",
            "build_profile": "release",
            "feature_set": [],
        }

    def _baseline(self) -> dict[str, Any]:
        samples = [1000 + ((index % 5) - 2) * 10 for index in range(64)]
        statistics = sample_statistics(samples)
        environment = self._environment()
        environment_hash = environment_fingerprint(environment)
        baseline: dict[str, Any] = {
            "schema_version": "1.0.0",
            "baseline_kind": "strling-performance-baseline",
            "baseline_state": "active",
            "manifest_fingerprint": self.manifest["manifest_fingerprint"],
            "fixture_manifest_fingerprint": self.fixtures[
                "fixture_manifest_fingerprint"
            ],
            "source_commit": "0" * 40,
            "environment": environment,
            "environment_fingerprint": environment_hash,
            "measurements": [
                {
                    "operation_id": "latency:semantic-parse",
                    "fixture_id": "fixture:semantic-tiny",
                    "unit": "microseconds",
                    "samples": samples,
                    "statistics": statistics,
                    "budget": {
                        "state": "active",
                        "relative_regression_basis_points": 1000,
                        "absolute_ceiling": 2000,
                        "rationale": "Synthetic controlled boundary for schema and comparison validation only."
                    },
                    "environment_fingerprint": environment_hash,
                }
            ],
            "update_command": self.manifest["measurement_policy"][
                "baseline_update_command"
            ],
            "update_rationale": "Synthetic contract fixture proving an explicit attributable baseline update.",
            "baseline_fingerprint": "0" * 64,
        }
        baseline["baseline_fingerprint"] = document_fingerprint(
            baseline, "baseline_fingerprint"
        )
        return baseline


if __name__ == "__main__":
    unittest.main()
