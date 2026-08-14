"""Tests for the joined migration and explanation certification hardgate."""

from __future__ import annotations

import copy
import unittest

from tooling import migration_explanation_certification as certification
from tooling.contract_validation import load_json
from tooling.migration_explanation_certification import (
    MANIFEST_PATH,
    MUTATION_CATEGORIES,
    MigrationExplanationCertificationError,
    certify,
    manifest_fingerprint,
    sign_manifest,
)


class MigrationExplanationCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_json(MANIFEST_PATH)
        cls.details = certify()

    def test_complete_denominator_is_certified(self) -> None:
        self.assertEqual(7, self.details["denominators"])
        self.assertEqual(9, self.details["round_trip_cases"])
        self.assertEqual(18, self.details["destination_proofs"])
        self.assertEqual(4, self.details["conversion_cases"])
        self.assertEqual(4, self.details["semantic_explanation_cases"])
        self.assertEqual(24, self.details["no_match_cases"])
        self.assertEqual(20, self.details["target_cases"])
        self.assertEqual(100, self.details["target_observations"])
        self.assertEqual(9, self.details["pathological_cases"])
        self.assertEqual(8, self.details["mutations_detected"])

    def test_manifest_fingerprint_is_canonical_and_repeatable(self) -> None:
        claimed = self.manifest["anti_shrinkage"]["manifest_sha256"]
        self.assertEqual(claimed, manifest_fingerprint(self.manifest))
        self.assertEqual(self.manifest, sign_manifest(self.manifest))

    def test_schema_rejects_unknown_product_claims(self) -> None:
        altered = copy.deepcopy(self.manifest)
        altered["product_semantics"] = "certification cannot own this"
        altered = sign_manifest(altered)
        with self.assertRaisesRegex(
            MigrationExplanationCertificationError, "Additional properties"
        ):
            certify(manifest=altered)

    def test_resigned_denominator_shrinkage_is_rejected(self) -> None:
        altered = copy.deepcopy(self.manifest)
        altered["denominators"][0]["expected"]["cases"] = 10
        altered = sign_manifest(altered)
        with self.assertRaisesRegex(
            MigrationExplanationCertificationError, "owning validator"
        ):
            certify(manifest=altered)

    def test_resigned_round_trip_shrinkage_is_rejected(self) -> None:
        altered = copy.deepcopy(self.manifest)
        altered["corpora"]["round_trip_cases"].pop()
        altered["anti_shrinkage"]["round_trip_cases"] = 8
        altered["anti_shrinkage"]["round_trip_destination_proofs"] = 16
        altered = sign_manifest(altered)
        with self.assertRaisesRegex(
            MigrationExplanationCertificationError, "too short|9 was expected"
        ):
            certify(manifest=altered)

    def test_unregistered_target_evidence_is_rejected(self) -> None:
        altered = copy.deepcopy(self.manifest)
        altered["corpora"]["round_trip_cases"][0]["target_evidence_case_ids"].append(
            "case:target/unregistered"
        )
        altered = sign_manifest(altered)
        with self.assertRaisesRegex(
            MigrationExplanationCertificationError, "unregistered target evidence"
        ):
            certify(manifest=altered)

    def test_mutation_category_coverage_cannot_be_duplicated(self) -> None:
        altered = copy.deepcopy(self.manifest)
        altered["mutations"][1]["category"] = altered["mutations"][0]["category"]
        altered = sign_manifest(altered)
        with self.assertRaisesRegex(
            MigrationExplanationCertificationError,
            "mutation category identity|anti-shrinkage count",
        ):
            certify(manifest=altered)
        self.assertEqual(
            MUTATION_CATEGORIES,
            tuple(entry["category"] for entry in self.manifest["mutations"]),
        )

    def test_missing_pathological_proof_hook_is_rejected(self) -> None:
        altered = copy.deepcopy(self.manifest)
        altered["pathological_cases"][-1]["source_case"] = (
            "core/tests/no_match_explanation.rs#missing_proof_hook"
        )
        altered = sign_manifest(altered)
        with self.assertRaisesRegex(
            MigrationExplanationCertificationError, "proof hook is missing"
        ):
            certify(manifest=altered)

    def test_unsigned_mutation_is_rejected_before_owner_checks(self) -> None:
        altered = copy.deepcopy(self.manifest)
        altered["target_evidence"]["observation_count"] = 99
        with self.assertRaisesRegex(
            MigrationExplanationCertificationError,
            "100 was expected|manifest canonical fingerprint differs",
        ):
            certify(manifest=altered)

    def test_cli_result_is_structured_and_fail_closed(self) -> None:
        result, code = certification.run()
        self.assertEqual(0, code)
        self.assertEqual("certification-result-v1", result["schema_version"])
        self.assertEqual(certification.OPERATION_ID, result["operation_id"])
        self.assertEqual("passed", result["status"])
        self.assertEqual(certification.CHECK_ID, result["checks"][0]["id"])
        self.assertEqual("passed", result["checks"][0]["status"])


if __name__ == "__main__":
    unittest.main()
