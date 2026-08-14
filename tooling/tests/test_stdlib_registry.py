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
        self.assertEqual(3, self.suite.validate_suite_structure())

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

    def test_canonical_semantics_cover_every_variant_and_zero_validators(self) -> None:
        self.suite._validate_canonical_semantics(self.registry)
        self.assertEqual(8, len(self.suite.semantics["entries"]))
        self.assertEqual(17, len(self.suite.semantics["stress_cases"]))
        self.assertEqual(0, self.suite.semantics["semantic_validator_count"])
        self.assertEqual(
            {"canonical-core-implemented"},
            {
                helper["semantic_definition"]["implementation_status"]
                for helper in self.registry["helpers"]
            },
        )
        result = self.suite.certify()
        self.assertEqual(117, result["edge_case_count"])
        self.assertEqual(585, result["runtime_application_count"])
        self.assertEqual(580, result["runtime_execute_count"])
        self.assertEqual(5, result["runtime_not_applicable_count"])

    def test_runtime_denominator_materialization_is_exact_and_deterministic(
        self,
    ) -> None:
        first = self.suite.materialize_runtime_cases()
        second = self.suite.materialize_runtime_cases()
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(117, len(first))
        self.assertEqual(117, len({case["case_id"] for case in first}))
        self.assertEqual(8, len({case["variant_id"] for case in first}))
        self.assertEqual(
            {"audited": 40, "compatibility": 60, "stress": 17},
            {
                source: sum(case["source"] == source for case in first)
                for source in ("audited", "compatibility", "stress")
            },
        )
        oversized_email = next(
            case for case in first if case["case_id"] == "email.oversized.local"
        )
        self.assertEqual(10012, len(oversized_email["input"]))

    def test_target_dependent_digits_follow_explicit_profile_models(self) -> None:
        records = {
            case["case_id"]: case for case in self.suite.materialize_runtime_cases()
        }
        target_case = next(
            case for case in records.values() if case["expected_match"] is None
        )
        applications = {
            application["profile_id"]: application
            for application in self.suite.runtime_applications([target_case])
        }
        self.assertEqual(
            ("execute", False),
            (
                applications["profile:ecmascript/2024"]["state"],
                applications["profile:ecmascript/2024"]["expected_match"],
            ),
        )
        for profile_id in (
            "profile:pcre2/10.42",
            "profile:pcre2/10.43",
            "profile:python-re/3.11",
        ):
            self.assertEqual(
                ("execute", True),
                (
                    applications[profile_id]["state"],
                    applications[profile_id]["expected_match"],
                ),
            )
        self.assertEqual(
            ("not_applicable", None),
            (
                applications["profile:python-re/3.11-bytes"]["state"],
                applications["profile:python-re/3.11-bytes"]["expected_match"],
            ),
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
