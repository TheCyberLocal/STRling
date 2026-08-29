from __future__ import annotations

import copy
import subprocess
import unittest
from unittest.mock import patch

from tooling import legacy_removal_inventory as inventory
from tooling.architecture_fitness import binding_semantic_path_candidate
from tooling.governance import matches_any


class LegacyRemovalInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = inventory._read_json(inventory.MANIFEST_PATH)

    def build(self, manifest: dict[str, object]) -> dict[str, object]:
        return inventory._build_evidence(manifest=manifest)

    def test_repository_inventory_certifies(self) -> None:
        report = inventory._certify()
        self.assertEqual(52, report.finding_count)
        self.assertEqual(1094, report.fixture_count)
        self.assertEqual(17, report.binding_count)
        self.assertEqual(9, report.remove_now_count)
        self.assertEqual(2, report.temporary_count)

    def test_fixture_baseline_and_current_population_reconcile(self) -> None:
        evidence = self.build(copy.deepcopy(self.manifest))
        reconciliation = evidence["fixture_reconciliation"]
        self.assertEqual(1094, reconciliation["classified"])
        self.assertEqual(596, reconciliation["current_classified"])
        self.assertEqual(498, reconciliation["removed"])

    def test_detached_worktree_at_authorized_branch_tip_certifies(self) -> None:
        real_git = inventory._git

        def detached_git(*args: str, check: bool = True):
            if args == ("branch", "--show-current"):
                return subprocess.CompletedProcess(args, 0, "\n", "")
            if args == ("rev-parse", "HEAD"):
                return subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", "")
            if args == (
                "rev-parse",
                "--verify",
                "refs/heads/architecture/v4",
            ):
                return subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", "")
            return real_git(*args, check=check)

        manifest = copy.deepcopy(self.manifest)
        with patch.object(inventory, "_git", side_effect=detached_git):
            evidence = self.build(manifest)
        self.assertEqual("architecture/v4", evidence["source"]["branch"])

    def test_detached_worktree_away_from_authorized_branch_tip_fails(self) -> None:
        real_git = inventory._git

        def detached_git(*args: str, check: bool = True):
            if args == ("branch", "--show-current"):
                return subprocess.CompletedProcess(args, 0, "\n", "")
            if args == ("rev-parse", "HEAD"):
                return subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", "")
            if args == (
                "rev-parse",
                "--verify",
                "refs/heads/architecture/v4",
            ):
                return subprocess.CompletedProcess(args, 0, "b" * 40 + "\n", "")
            return real_git(*args, check=check)

        with patch.object(inventory, "_git", side_effect=detached_git):
            with self.assertRaisesRegex(
                inventory.LegacyRemovalInventoryError,
                "detached HEAD does not equal the authorized branch tip",
            ):
                self.build(copy.deepcopy(self.manifest))

    def test_fixture_denominator_mutation_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["fixture_population"]["expected_total"] += 1
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError,
            "schema validation|fixture denominator changed",
        ):
            self.build(manifest)

    def test_fixture_family_count_mutation_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["fixture_population"]["families"][0]["expected_count"] += 1
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError, "fixture family"
        ):
            self.build(manifest)

    def test_current_fixture_family_count_mutation_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["fixture_population"]["families"][1]["current_expected_count"] += 1
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError, "current fixture family"
        ):
            self.build(manifest)

    def test_fixture_families_must_partition_without_overlap(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        family = manifest["fixture_population"]["families"][2]
        family["selectors"] = ["tooling/js_to_json_ast/**/*.pattern"]
        family["expected_count"] = 491
        family["current_expected_count"] = 0
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError, "does not partition exactly"
        ):
            self.build(manifest)

    def test_binding_route_mutation_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        finding = next(
            finding for finding in manifest["findings"] if finding["id"] == "ADAPTER-C"
        )
        finding["canonical_replacement"]["route"] = "binding-local compiler"
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError, "does not reproduce evidence"
        ):
            self.build(manifest)

    def test_binding_finding_removal_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["findings"] = [
            finding
            for finding in manifest["findings"]
            if finding["id"] != "ADAPTER-SWIFT"
        ]
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError, "has no stable adapter finding"
        ):
            self.build(manifest)

    def test_generated_artifact_coverage_mutation_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["coverage"]["generated_artifact_ids"].pop()
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError,
            "generated transitional/projection coverage changed",
        ):
            self.build(manifest)

    def test_architecture_rule_coverage_mutation_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["coverage"]["architecture_rule_ids"].pop()
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError,
            "architecture exception coverage changed",
        ):
            self.build(manifest)

    def test_waiver_coverage_mutation_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["coverage"]["waiver_ids"].pop()
        with self.assertRaisesRegex(
            inventory.LegacyRemovalInventoryError, "accepted waiver coverage changed"
        ):
            self.build(manifest)

    def test_remove_now_requires_deletion_proof(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        finding = next(
            finding
            for finding in manifest["findings"]
            if finding["disposition"] == "REMOVE_NOW"
        )
        finding.pop("deletion")
        with self.assertRaises(inventory.LegacyRemovalInventoryError):
            self.build(manifest)

    def test_temporary_retention_requires_expiry_proof(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        finding = next(
            finding
            for finding in manifest["findings"]
            if finding["disposition"] == "RETAIN_TEMPORARILY"
        )
        finding["temporary_retention"].pop("expiry_condition")
        with self.assertRaises(inventory.LegacyRemovalInventoryError):
            self.build(manifest)

    def test_new_binding_semantic_module_is_detected(self) -> None:
        architecture = inventory._read_json(inventory.ARCHITECTURE_PATH)
        rule = inventory._rule_map(architecture)["duplicated-binding-compilers"]
        self.assertTrue(
            binding_semantic_path_candidate(
                "bindings/go/parser.go", rule["configuration"], matches_any
            )
        )


if __name__ == "__main__":
    unittest.main()
