"""Governed discrepancy-classification contract tests."""

from __future__ import annotations

import copy
import unittest

from tooling import migration_classification as classification
from tooling import migration_comparison as projection_contract
from tooling import migration_comparison_engine as engine
from tooling.legacy_reference import python_reference as reference
from tooling.tests.test_migration_comparison import make_context
from tooling.tests.test_migration_comparison_engine import (
    make_pair,
    make_typescript_observation,
)


def make_rationale(
    comparison: dict[str, object],
    *,
    authority: list[dict[str, str]] | None = None,
    explanation: str = "Controlled classification rationale.",
    limitations: list[str] | None = None,
    unresolved_questions: list[str] | None = None,
) -> dict[str, object]:
    evidence_identity = "sha256:" + "8" * 64
    return {
        "affected_operation": comparison["operation"],
        "affected_surfaces": sorted(
            surface
            for surface in comparison["surfaces"].values()
            if surface is not None
        ),
        "authority": authority or [],
        "comparison_identity": comparison["comparison_identity"],
        "difference_paths": [
            difference["path"] for difference in comparison["differences"]
        ],
        "evidence_identities": [comparison["comparison_identity"], evidence_identity],
        "explanation": explanation,
        "limitations": limitations or [],
        "unresolved_questions": unresolved_questions or [],
    }


def authority(kind: str, reference_value: str) -> dict[str, str]:
    return {
        "evidence_identity": "sha256:" + "9" * 64,
        "kind": kind,
        "reference": reference_value,
    }


def differing_comparison() -> dict[str, object]:
    left, _ = make_pair()
    right_observation = make_typescript_observation()
    right_observation["outcome"]["evidence"]["flags"]["unicode"] = False
    right = projection_contract.project_observation(
        right_observation, make_context(right_observation)
    )
    return engine.compare_projections(left, right)


class ClassificationTests(unittest.TestCase):
    def test_historical_peer_comparison_is_structurally_not_applicable(self) -> None:
        comparison = differing_comparison()
        result = classification.classify_comparison(
            comparison,
            evidence_scope="historical_evidence_only",
            roles={"left": "historical", "right": "historical"},
            rationale=make_rationale(
                comparison,
                explanation="Historical divergence is evidence only.",
                limitations=["No replacement observation exists."],
            ),
        )
        self.assertEqual(result["applicability"], "not_applicable")
        self.assertIsNone(result["disposition"])

    def test_historical_difference_opened_for_migration_defaults_unresolved(
        self,
    ) -> None:
        comparison = differing_comparison()
        result = classification.classify_comparison(
            comparison,
            evidence_scope="migration_review",
            roles={"left": "historical", "right": "historical"},
            rationale=make_rationale(
                comparison,
                explanation="Replacement behavior has not been established.",
                unresolved_questions=["Which behavior follows governing semantics?"],
            ),
        )
        self.assertEqual(result["disposition"], "unresolved_discrepancy")

    def test_preserved_behavior_requires_replacement_evidence_and_scope(self) -> None:
        left, right = make_pair()
        comparison = engine.compare_projections(left, right)
        rationale = make_rationale(
            comparison,
            authority=[
                authority("replacement_evidence", "fixture:replacement-equivalence")
            ],
        )
        result = classification.classify_comparison(
            comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=rationale,
            requested_disposition="preserved_behavior",
            preservation_scope="literal parser outcome fixture",
        )
        self.assertEqual(result["disposition"], "preserved_behavior")
        self.assertEqual(result["preservation_scope"], "literal parser outcome fixture")

        with self.assertRaisesRegex(
            classification.ClassificationError, "replacement evidence"
        ):
            classification.classify_comparison(
                comparison,
                evidence_scope="certification_fixture",
                roles={"left": "historical", "right": "replacement"},
                rationale=make_rationale(comparison),
                requested_disposition="preserved_behavior",
                preservation_scope="literal parser outcome fixture",
            )

    def test_intentional_correction_requires_difference_rule_and_authority(
        self,
    ) -> None:
        comparison = differing_comparison()
        rationale = make_rationale(
            comparison,
            authority=[
                authority(
                    "canonical_contract",
                    "spec/contracts/1.0/semantic-ir.schema.json#fixture-rule",
                )
            ],
        )
        result = classification.classify_comparison(
            comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=rationale,
            requested_disposition="intentional_specification_correction",
            corrected_rule="fixture semantic rule",
        )
        self.assertEqual(result["disposition"], "intentional_specification_correction")

        with self.assertRaisesRegex(classification.ClassificationError, "authority"):
            classification.classify_comparison(
                comparison,
                evidence_scope="certification_fixture",
                roles={"left": "historical", "right": "replacement"},
                rationale=make_rationale(comparison),
                requested_disposition="intentional_specification_correction",
                corrected_rule="fixture semantic rule",
            )

    def test_equivalent_correction_requires_exceptional_justification(self) -> None:
        left, right = make_pair()
        comparison = engine.compare_projections(left, right)
        rationale = make_rationale(
            comparison,
            authority=[authority("normative_specification", "fixture:normative-rule")],
        )
        with self.assertRaisesRegex(classification.ClassificationError, "exceptional"):
            classification.classify_comparison(
                comparison,
                evidence_scope="certification_fixture",
                roles={"left": "historical", "right": "replacement"},
                rationale=rationale,
                requested_disposition="intentional_specification_correction",
                corrected_rule="fixture semantic rule",
            )
        accepted = classification.classify_comparison(
            comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=rationale,
            requested_disposition="intentional_specification_correction",
            corrected_rule="fixture semantic rule",
            exceptional_justification="The fixture certifies the exceptional contract path.",
        )
        self.assertEqual(
            accepted["disposition"], "intentional_specification_correction"
        )

    def test_unsupported_legacy_requires_scope_boundary_and_authority(self) -> None:
        unsupported = {"reason": "outside fixture scope", "status": "unsupported"}
        left, right = make_pair(right_outcome=unsupported)
        comparison = engine.compare_projections(left, right)
        rationale = make_rationale(
            comparison,
            authority=[
                authority("supported_scope_contract", "fixture:supported-scope")
            ],
        )
        result = classification.classify_comparison(
            comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=rationale,
            requested_disposition="unsupported_legacy_behavior",
            scope_boundary="fixture replacement excludes the legacy extension",
        )
        self.assertEqual(result["disposition"], "unsupported_legacy_behavior")

        with self.assertRaisesRegex(
            classification.ClassificationError, "scope_boundary"
        ):
            classification.classify_comparison(
                comparison,
                evidence_scope="certification_fixture",
                roles={"left": "historical", "right": "replacement"},
                rationale=rationale,
                requested_disposition="unsupported_legacy_behavior",
            )

    def test_unresolved_cannot_be_used_for_equivalent_observations(self) -> None:
        left, right = make_pair()
        comparison = engine.compare_projections(left, right)
        with self.assertRaisesRegex(classification.ClassificationError, "equivalent"):
            classification.classify_comparison(
                comparison,
                evidence_scope="certification_fixture",
                roles={"left": "historical", "right": "replacement"},
                rationale=make_rationale(comparison),
                requested_disposition="unresolved_discrepancy",
            )

    def test_migration_review_rejects_legacy_runner_as_replacement(self) -> None:
        comparison = differing_comparison()
        with self.assertRaisesRegex(classification.ClassificationError, "adapter"):
            classification.classify_comparison(
                comparison,
                evidence_scope="migration_review",
                roles={"left": "historical", "right": "replacement"},
                rationale=make_rationale(comparison),
                requested_disposition="unresolved_discrepancy",
            )

    def test_invalid_disposition_and_altered_difference_path_are_rejected(self) -> None:
        comparison = differing_comparison()
        with self.assertRaisesRegex(
            classification.ClassificationError, "invalid disposition"
        ):
            classification.classify_comparison(
                comparison,
                evidence_scope="certification_fixture",
                roles={"left": "historical", "right": "replacement"},
                rationale=make_rationale(comparison),
                requested_disposition="accepted_difference",
            )

        altered = copy.deepcopy(comparison)
        altered["differences"][0]["path"] = "/invented/path"
        with self.assertRaisesRegex(classification.ClassificationError, "identity"):
            classification.classify_comparison(
                altered,
                evidence_scope="historical_evidence_only",
                roles={"left": "historical", "right": "historical"},
                rationale=make_rationale(altered),
            )

    def test_classification_is_immutable_deterministic_and_traceably_superseded(
        self,
    ) -> None:
        comparison = differing_comparison()
        before = copy.deepcopy(comparison)
        rationale = make_rationale(comparison)
        first = classification.classify_comparison(
            comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=rationale,
            requested_disposition="unresolved_discrepancy",
        )
        repeated = classification.classify_comparison(
            comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=rationale,
            requested_disposition="unresolved_discrepancy",
        )
        self.assertEqual(
            reference.canonical_line(first), reference.canonical_line(repeated)
        )
        self.assertEqual(comparison, before)

        corrected = classification.classify_comparison(
            comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=make_rationale(
                comparison,
                authority=[authority("canonical_contract", "fixture:governing-rule")],
            ),
            requested_disposition="intentional_specification_correction",
            corrected_rule="fixture semantic rule",
            supersedes=[first["classification_identity"]],
        )
        self.assertNotEqual(
            first["classification_identity"], corrected["classification_identity"]
        )
        self.assertEqual(corrected["supersedes"], [first["classification_identity"]])


if __name__ == "__main__":
    unittest.main()
