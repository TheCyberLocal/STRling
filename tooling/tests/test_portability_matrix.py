"""Completeness, classification, and mutation tests for the initial matrix."""

from __future__ import annotations

import copy
import unittest

from tooling import portability_matrix as matrix
from tooling import shared_cross_engine_corpus as shared


class PortabilityMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validation = shared.validate_corpus()
        self.evidence = matrix.load_json(shared.EVIDENCE_PATH)
        self.matrix = matrix.build_matrix(
            validation=self.validation, evidence=self.evidence
        )

    @staticmethod
    def resign(evidence) -> None:
        unsigned = dict(evidence)
        unsigned.pop("result_sha256", None)
        evidence["result_sha256"] = shared.canonical_digest(unsigned)

    def test_exact_matrix_denominator_and_dispositions(self) -> None:
        self.assertEqual(100, self.matrix["counts"]["entries"])
        self.assertEqual(
            {
                "native": 87,
                "planner_certified_equivalent_rewrite": 1,
                "target_unsupported_or_constraint": 5,
                "not_applicable": 7,
                "target_profile_or_documentation_discrepancy": 0,
                "harness_defect": 0,
                "canonical_expectation_defect": 0,
                "implementation_or_runtime_discrepancy": 0,
                "unresolved": 0,
            },
            self.matrix["counts"]["dispositions"],
        )
        self.assertEqual(
            6, self.matrix["counts"]["representation_or_support_divergences"]
        )
        self.assertEqual("ready", self.matrix["readiness"]["status"])

    def test_schema_and_result_fingerprint_validate(self) -> None:
        matrix.validate_matrix(self.matrix)
        unsigned = dict(self.matrix)
        claimed = unsigned.pop("result_sha256")
        self.assertEqual(claimed, shared.canonical_digest(unsigned))

    def test_every_profile_retains_exact_runtime_and_options(self) -> None:
        self.assertEqual(
            list(shared.EXPECTED_PROFILE_IDS),
            [item["target_profile"]["profile_id"] for item in self.matrix["profiles"]],
        )
        for profile in self.matrix["profiles"]:
            self.assertEqual(
                shared.canonical_digest(profile["options"]),
                profile["options_sha256"],
            )
            self.assertEqual(
                shared.canonical_digest(profile["runtime"]["identity"]),
                profile["runtime"]["sha256"],
            )

    def test_cross_profile_semantic_classes_are_consistent(self) -> None:
        statuses = [item["status"] for item in self.matrix["semantic_comparisons"]]
        self.assertEqual(19, statuses.count("consistent"))
        self.assertEqual(1, statuses.count("not_compared"))
        self.assertNotIn("divergent", statuses)

    def test_six_divergences_have_explicit_nonblocking_dispositions(self) -> None:
        divergences = self.matrix["divergences"]
        self.assertEqual(6, len(divergences))
        self.assertEqual(
            {
                "planner_certified_equivalent_rewrite": 1,
                "target_unsupported_or_constraint": 5,
            },
            {
                category: sum(item["category"] == category for item in divergences)
                for category in {
                    "planner_certified_equivalent_rewrite",
                    "target_unsupported_or_constraint",
                }
            },
        )
        self.assertFalse(any(item["blocking"] for item in divergences))

    def test_feature_and_requirement_rows_cover_every_exact_profile(self) -> None:
        self.assertEqual(21 * 5, len(self.matrix["feature_matrix"]))
        self.assertEqual(16 * 5, len(self.matrix["requirement_matrix"]))
        for rows in (
            self.matrix["feature_matrix"],
            self.matrix["requirement_matrix"],
        ):
            keys = sorted({row["key"] for row in rows})
            for key in keys:
                self.assertEqual(
                    list(shared.EXPECTED_PROFILE_IDS),
                    [
                        row["target_profile"]["profile_id"]
                        for row in rows
                        if row["key"] == key
                    ],
                )

    def test_missing_observation_pair_fails_closed(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["observations"].pop()
        self.resign(evidence)
        with self.assertRaisesRegex(
            matrix.PortabilityMatrixError, "exact ordered denominator"
        ):
            matrix.build_matrix(validation=self.validation, evidence=evidence)

    def test_stale_application_state_fails_closed(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["observations"][0]["state"] = "execute"
        self.resign(evidence)
        with self.assertRaisesRegex(
            matrix.PortabilityMatrixError, "disposition differs"
        ):
            matrix.build_matrix(validation=self.validation, evidence=evidence)

    def test_runtime_fingerprint_drift_fails_closed(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["runtimes"]["node"]["executable_sha256"] = "0" * 64
        self.resign(evidence)
        with self.assertRaisesRegex(matrix.PortabilityMatrixError, "Node/V8"):
            matrix.build_matrix(validation=self.validation, evidence=evidence)

    def test_semantic_difference_is_unresolved_and_blocking(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        observation = next(
            item
            for item in evidence["observations"]
            if item["state"] == "execute" and item["normalized"][0]["span"]
        )
        observation["normalized"][0]["span"] = [1, 2]
        self.resign(evidence)
        mutated = matrix.build_matrix(validation=self.validation, evidence=evidence)
        matrix.validate_matrix(mutated, require_ready=False)
        self.assertEqual("blocked", mutated["readiness"]["status"])
        self.assertGreater(mutated["counts"]["unresolved"], 0)
        with self.assertRaisesRegex(matrix.PortabilityMatrixError, "unresolved"):
            matrix.validate_matrix(mutated)

    def test_cross_profile_split_is_unresolved_when_expectation_is_less_specific(
        self,
    ) -> None:
        evidence = copy.deepcopy(self.evidence)
        observation = next(
            item
            for item in evidence["observations"]
            if item["case_id"] == "case:matching/fixed-lookbehind"
            and item["profile_id"] == "profile:ecmascript/2024"
        )
        observation["normalized"][0]["span"] = [0, 2]
        self.resign(evidence)
        mutated = matrix.build_matrix(validation=self.validation, evidence=evidence)
        comparison = next(
            item
            for item in mutated["semantic_comparisons"]
            if item["case_id"] == "case:matching/fixed-lookbehind"
        )
        self.assertEqual("divergent", comparison["status"])
        affected = [
            item
            for item in mutated["entries"]
            if item["case"]["case_id"] == "case:matching/fixed-lookbehind"
        ]
        self.assertEqual(
            {"unresolved"},
            {item["disposition"]["category"] for item in affected},
        )
        self.assertTrue(all(item["disposition"]["blocking"] for item in affected))
        self.assertEqual("blocked", mutated["readiness"]["status"])

    def test_generation_and_summary_are_deterministic(self) -> None:
        repeated = matrix.build_matrix(
            validation=self.validation, evidence=self.evidence
        )
        self.assertEqual(self.matrix, repeated)
        summary = matrix.render_markdown(self.matrix)
        self.assertIn("machine-authoritative matrix JSON", summary)
        self.assertIn(self.matrix["result_sha256"], summary)
        for profile_id in shared.EXPECTED_PROFILE_IDS:
            self.assertIn(profile_id, summary)

    def test_checked_machine_and_human_outputs_are_current(self) -> None:
        result = matrix.verify_evidence()
        self.assertEqual(100, result["entries"])
        self.assertEqual(self.matrix["result_sha256"], result["result_sha256"])


if __name__ == "__main__":
    unittest.main()
