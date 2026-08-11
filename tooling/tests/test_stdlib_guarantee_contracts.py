"""Certification tests for standard-library validation guarantee contracts."""

from __future__ import annotations

import ast
import copy
import unittest

from tooling.stdlib_guarantee_contracts import (
    ROOT,
    STDLIB_EXAMPLE_ROOT,
    STDLIB_INVALID_ROOT,
    STDLIB_TRANSITION_INVENTORY,
    StandardLibraryContractError,
    StandardLibraryGuaranteeSuite,
    canonical_json,
    load_json,
)


class StandardLibraryGuaranteeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = StandardLibraryGuaranteeSuite()

    def test_schema_family_is_closed_and_versioned(self) -> None:
        self.assertEqual(3, self.suite.validate_suite_structure())

    def test_all_levels_and_transition_inventory_validate(self) -> None:
        self.assertEqual(4, self.suite.validate_positive_examples())
        levels = {
            load_json(path)["guarantee_level"]
            for path in STDLIB_EXAMPLE_ROOT.glob("*.json")
        }
        self.assertEqual({"lexical_shape", "normalized_structure", "semantic"}, levels)

    def test_every_controlled_overclaim_is_rejected_for_declared_rule(self) -> None:
        self.assertEqual(7, self.suite.validate_negative_examples())

    def test_identical_definitions_validate_identically_without_mutation(self) -> None:
        definition = load_json(STDLIB_EXAMPLE_ROOT / "semantic.json")
        before = canonical_json(definition)
        self.suite.validate_guarantee(definition)
        first = canonical_json(definition)
        self.suite.validate_guarantee(definition)
        second = canonical_json(definition)
        self.assertEqual(before, first)
        self.assertEqual(first, second)

    def test_controlled_invalid_materialization_is_deterministic(self) -> None:
        for path in sorted(STDLIB_INVALID_ROOT.glob("*.json")):
            case = load_json(path)
            first = self.suite.materialize_invalid_case(case)
            second = self.suite.materialize_invalid_case(case)
            self.assertEqual(canonical_json(first), canonical_json(second), path)

    def test_lexical_claim_cannot_embed_a_semantic_check(self) -> None:
        definition = load_json(STDLIB_EXAMPLE_ROOT / "lexical-shape.json")
        definition["validation_definition"]["conditions"][0]["category"] = "semantic"
        definition["checks"]["performed"][0]["category"] = "semantic"
        with self.assertRaisesRegex(
            StandardLibraryContractError, "guarantee.level.ceiling"
        ):
            self.suite.validate_guarantee(definition)

    def test_duplicate_evidence_cannot_inflate_support(self) -> None:
        definition = load_json(STDLIB_EXAMPLE_ROOT / "lexical-shape.json")
        definition["evidence"]["references"].append(
            copy.deepcopy(definition["evidence"]["references"][0])
        )
        with self.assertRaisesRegex(StandardLibraryContractError, "evidence.unique"):
            self.suite.validate_guarantee(definition)

    def test_safety_and_portability_remain_independent(self) -> None:
        cases = {
            path.name: load_json(path) for path in STDLIB_INVALID_ROOT.glob("*.json")
        }
        for name, rule in (
            ("unsupported-safety-claim.json", "validation.safety_claim_forbidden"),
            ("portability-as-validation.json", "validation.portability_forbidden"),
        ):
            invalid = self.suite.materialize_invalid_case(cases[name])
            with self.assertRaisesRegex(StandardLibraryContractError, rule):
                self.suite.validate_guarantee(invalid)

    def test_subset_cannot_be_reclassified_as_complete(self) -> None:
        case = load_json(STDLIB_INVALID_ROOT / "complete-with-subset-exclusions.json")
        invalid = self.suite.materialize_invalid_case(case)
        with self.assertRaisesRegex(
            StandardLibraryContractError,
            "standard.complete.exclusions_forbidden",
        ):
            self.suite.validate_guarantee(invalid)

    def test_historical_helpers_are_explicitly_unratified(self) -> None:
        inventory = load_json(STDLIB_TRANSITION_INVENTORY)
        self.suite.validate_transition_inventory(inventory)
        self.assertEqual(5, len(inventory["entries"]))
        self.assertEqual(
            {"not_ratified"},
            {entry["guarantee_status"] for entry in inventory["entries"]},
        )
        self.assertEqual(
            {"no_validation_guarantee"},
            {entry["strongest_permitted_claim"] for entry in inventory["entries"]},
        )

    def test_authored_evidence_fingerprint_is_stable_within_a_run(self) -> None:
        self.assertEqual(
            self.suite.evidence_fingerprint(), self.suite.evidence_fingerprint()
        )

    def test_canonical_quality_operation_owns_all_guarantee_checks(self) -> None:
        toolchain = load_json(ROOT / "toolchain.json")
        policy = toolchain["policy"]
        operation = policy["operation_registry"]["canonical_contracts_check"]
        self.assertEqual(
            ["python3", "tooling/contract_validation.py"], operation["command"]
        )
        for profile_name in ("local", "pull-request", "full", "release"):
            operations = {
                member["operation"]
                for member in policy["profiles"][profile_name]["operations"]
            }
            self.assertIn("canonical_contracts_check", operations)

        tree = ast.parse(
            (ROOT / "tooling" / "contract_validation.py").read_text(encoding="utf-8")
        )
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "stdlib_suite"
        }
        self.assertEqual(
            {
                "validate_negative_examples",
                "validate_positive_examples",
                "validate_suite_structure",
            },
            calls,
        )


if __name__ == "__main__":
    unittest.main()
