"""Certification tests for the canonical standard-library registry."""

from __future__ import annotations

import copy
import unittest

from tooling.stdlib_registry import (
    INVALID_ROOT,
    REGISTRY_PATH,
    StandardLibraryRegistryError,
    StandardLibraryRegistrySuite,
    canonical_json,
    load_json,
    registry_fingerprint,
)


class StandardLibraryRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = StandardLibraryRegistrySuite()
        cls.registry = load_json(REGISTRY_PATH)

    def test_schema_family_is_closed_and_versioned(self) -> None:
        self.assertEqual(2, self.suite.validate_suite_structure())

    def test_registry_reconciles_complete_audited_denominator(self) -> None:
        self.assertEqual((5, 8, 17, 40), self.suite.validate_canonical_file())
        self.assertEqual(
            {"lexical_shape"},
            {helper["guarantee"]["level"] for helper in self.registry["helpers"]},
        )
        self.assertEqual(
            {"compatibility"},
            {helper["support_tier"] for helper in self.registry["helpers"]},
        )

    def test_helper_identity_is_separate_from_host_language_spelling(self) -> None:
        helper_ids = {helper["id"] for helper in self.registry["helpers"]}
        self.assertEqual(5, len(helper_ids))
        for binding in self.registry["host_bindings"]:
            self.assertEqual(
                helper_ids,
                {exposure["helper_id"] for exposure in binding["exposures"]},
            )
        c_binding = next(
            item for item in self.registry["host_bindings"] if item["binding_id"] == "c"
        )
        c_names = {
            exposure["helper_id"]: exposure["public_names"]
            for exposure in c_binding["exposures"]
        }
        self.assertEqual(["sl_email"], c_names["stdlib.email"])
        self.assertEqual(["sl_ip_any", "sl_ip_v4", "sl_ip_v6"], c_names["stdlib.ip"])

    def test_fingerprint_and_serialization_are_stable(self) -> None:
        expected = self.registry["fingerprint"]["value"]
        self.assertEqual(expected, registry_fingerprint(self.registry))
        self.assertEqual(expected, registry_fingerprint(copy.deepcopy(self.registry)))

    def test_compatibility_projections_are_exact_and_non_normative(self) -> None:
        self.assertEqual(
            "non-normative", self.registry["authority"]["generated_outputs"]
        )
        self.assertEqual((5, 8, 17, 40), self.suite.check_projections())

    def test_controlled_invalid_fixtures_fail_for_declared_rules(self) -> None:
        self.assertEqual(9, self.suite.validate_negative_fixtures())

    def test_controlled_invalid_materialization_is_deterministic(self) -> None:
        for path in sorted(INVALID_ROOT.glob("*.json")):
            case = load_json(path)
            first = self.suite.materialize_invalid_case(case)
            second = self.suite.materialize_invalid_case(case)
            self.assertEqual(canonical_json(first), canonical_json(second), path)

    def test_missing_examples_and_evidence_fail_before_schema_fallback(self) -> None:
        for filename, rule in (
            ("missing-examples.json", "helper.examples.required"),
            ("missing-evidence.json", "helper.evidence.required"),
        ):
            case = load_json(INVALID_ROOT / filename)
            with self.assertRaisesRegex(StandardLibraryRegistryError, rule):
                self.suite.validate_registry(self.suite.materialize_invalid_case(case))

    def test_derivation_graph_rejects_cycles_and_ambiguous_outputs(self) -> None:
        for filename, rule in (
            ("cyclic-derivation.json", "derivation.cycle"),
            ("ambiguous-derivation-output.json", "derivation.output.ambiguous"),
        ):
            case = load_json(INVALID_ROOT / filename)
            with self.assertRaisesRegex(StandardLibraryRegistryError, rule):
                self.suite.validate_registry(self.suite.materialize_invalid_case(case))

    def test_audit_reconciliation_rejects_semantic_strengthening(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["helpers"][0]["guarantee"]["level"] = "semantic"
        registry["fingerprint"]["value"] = registry_fingerprint(registry)
        with self.assertRaisesRegex(
            StandardLibraryRegistryError, "audit.guarantee.correspondence"
        ):
            self.suite.validate_registry(registry)


if __name__ == "__main__":
    unittest.main()
