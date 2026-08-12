from __future__ import annotations

import copy
import json
import unittest

from tooling import migration_classification as classification
from tooling import migration_comparison as comparison_contract
from tooling import migration_comparison_certification as comparison_certification
from tooling import migration_comparison_engine as comparison_engine
from tooling import migration_differential as differential
from tooling.legacy_reference import python_reference as reference


class FullMigrationDifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = differential.load_contract()
        cls.baseline = differential.load_baseline()
        cls.batches = differential.capture_full_corpus(2)
        cls.candidate = differential.build_candidate(
            cls.batches,
            contract=cls.contract,
            repeat_runs=2,
        )
        cls.fixture = json.loads(
            (
                differential.ROOT
                / "tooling/tests/fixtures/migration_differential/certification.json"
            ).read_text(encoding="utf-8")
        )

    def test_contract_exactly_covers_every_corpus_operation(self) -> None:
        corpora = differential._contract_corpora(self.contract)
        operations = {
            case["request"]["operation"]
            for corpus in corpora.values()
            for case in corpus["cases"]
        }
        routes = {
            route["operation"]
            for route in self.contract["canonical_boundary"]["routes"]
        }
        self.assertEqual(routes, operations)
        self.assertTrue(
            all(
                route["state"] == "not_comparable"
                and route["authority"]
                and route["rationale"]
                for route in self.contract["canonical_boundary"]["routes"]
            )
        )

    def test_full_corpus_candidate_has_expected_quantitative_evidence(self) -> None:
        metrics = self.candidate["metrics"]
        expected = self.fixture["expected_metrics"]
        self.assertEqual(metrics["source_observations"], expected["source_observations"])
        self.assertEqual(
            metrics["canonical_not_comparable_cases"],
            expected["canonical_not_comparable_cases"],
        )
        self.assertEqual(
            metrics["canonical_comparable_cases"],
            expected["canonical_comparable_cases"],
        )
        self.assertEqual(
            metrics["historical_peer_unresolved_evidence"],
            expected["historical_peer_unresolved_evidence"],
        )
        self.assertEqual(
            metrics["blocking_unresolved_replacements"],
            expected["blocking_unresolved_replacements"],
        )
        self.assertEqual(
            self.candidate["historical_peer_comparison"]["metrics"]["comparisons"],
            expected["historical_peer_comparisons"],
        )
        self.assertEqual(self.candidate["determinism"], {"mismatches": 0, "repeat_runs": 2})

    def test_checked_baseline_certifies_the_complete_candidate(self) -> None:
        artifact = differential.certify(
            self.batches,
            contract=self.contract,
            baseline=self.baseline,
            repeat_runs=2,
        )
        self.assertEqual(artifact["status"], "passed")
        self.assertEqual(artifact["metrics"]["source_observations"], 44)
        self.assertEqual(
            artifact["metrics"]["blocking_unresolved_replacements"], 0
        )
        comparison_contract._require_fingerprint(
            artifact["result_fingerprint"], "artifact.result_fingerprint"
        )

    def test_repeated_candidate_construction_is_byte_stable(self) -> None:
        again = differential.build_candidate(
            self.batches,
            contract=self.contract,
            repeat_runs=2,
        )
        self.assertEqual(
            reference.canonical_line(self.candidate),
            reference.canonical_line(again),
        )

    def test_corpus_shrinkage_is_blocking(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["corpora"][0]["case_count"] -= 1
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "corpus shrinkage"
        ):
            differential.validate_baseline(changed, self.baseline)

    def test_source_observation_change_is_blocking(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["source_observations"][0]["observation_identity"] = (
            "sha256:" + ("a" * 64)
        )
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "source observation changed"
        ):
            differential.validate_baseline(changed, self.baseline)

    def test_stale_route_review_is_blocking(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["route_coverage_fingerprint"] = "sha256:" + ("b" * 64)
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "route approvals are stale"
        ):
            differential.validate_baseline(changed, self.baseline)

    def test_canonical_boundary_change_requires_renewed_review(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["canonical_boundary"]["fingerprint"] = "sha256:" + ("c" * 64)
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "canonical boundary changed"
        ):
            differential.validate_baseline(changed, self.baseline)

    def test_historical_peer_evidence_change_is_blocking(self) -> None:
        changed = copy.deepcopy(self.candidate)
        changed["historical_peer_comparison"]["result_fingerprint"] = (
            "sha256:" + ("d" * 64)
        )
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "peer comparison evidence changed"
        ):
            differential.validate_baseline(changed, self.baseline)

    def test_altered_baseline_fingerprint_is_blocking(self) -> None:
        changed = copy.deepcopy(self.baseline)
        changed["source_observations_fingerprint"] = "sha256:" + ("e" * 64)
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "baseline was altered"
        ):
            differential.validate_baseline(self.candidate, changed)

    def test_missing_route_review_is_rejected_before_gating(self) -> None:
        changed = copy.deepcopy(self.contract)
        changed["canonical_boundary"]["routes"].pop()
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "do not exactly cover"
        ):
            differential.build_candidate(
                self.batches,
                contract=changed,
                repeat_runs=2,
            )

    def test_approved_disposition_removal_or_alteration_is_detected(self) -> None:
        review = self._approved_preservation_review()
        validated = differential.validate_replacement_reviews(
            [review], allow_certification_fixture=True
        )
        self.assertEqual(validated[0]["disposition"], "preserved_behavior")

        removed = copy.deepcopy(review)
        del removed["classification"]
        with self.assertRaises(differential.DifferentialGateError):
            differential.validate_replacement_reviews(
                [removed], allow_certification_fixture=True
            )

        altered = copy.deepcopy(review)
        altered["classification"]["preservation_scope"] = "altered scope"
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "stale or altered"
        ):
            differential.validate_replacement_reviews(
                [altered], allow_certification_fixture=True
            )

    def test_unresolved_replacement_review_is_blocking(self) -> None:
        comparison = self._equivalent_replacement_comparison()
        changed = copy.deepcopy(comparison)
        changed["relationship"] = "differing_observation"
        changed["differences"] = [
            {
                "kind": "value_mismatch",
                "left": {"present": True, "value": "legacy"},
                "path": "/outcome/evidence/value",
                "right": {"present": True, "value": "replacement"},
            }
        ]
        changed["comparison_identity"] = reference.canonical_fingerprint(
            {key: value for key, value in changed.items() if key != "comparison_identity"}
        )
        rationale = comparison_certification._rationale(changed)
        unresolved = classification.classify_comparison(
            changed,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=rationale,
        )
        review = {
            "classification": unresolved,
            "comparison": changed,
            "review_id": "fixture-unresolved@1.0.0",
        }
        with self.assertRaisesRegex(
            differential.DifferentialGateError, "blocking unresolved"
        ):
            differential.validate_replacement_reviews(
                [review], allow_certification_fixture=True
            )

    def test_controlled_mutation_manifest_is_complete(self) -> None:
        self.assertEqual(
            self.fixture["mutation_cases"],
            [
                "approved-disposition-altered",
                "approved-disposition-removed",
                "baseline-fingerprint-altered",
                "canonical-boundary-changed",
                "corpus-shrinkage",
                "historical-peer-evidence-changed",
                "source-observation-changed",
                "stale-route-review",
            ],
        )

    @staticmethod
    def _equivalent_replacement_comparison() -> dict[str, object]:
        outcome = {
            "evidence": {"root": {"kind": "Lit", "value": "a"}},
            "status": "success",
        }
        corpus_fingerprint = reference.canonical_fingerprint(
            {"fixture": "approved-preservation"}
        )
        projections = []
        for runner_id in ("python", "typescript"):
            observation = comparison_certification._observation(
                runner_id,
                "parser.parse",
                "approved-preservation",
                outcome,
            )
            projections.append(
                comparison_contract.project_observation(
                    observation,
                    comparison_certification._context(
                        observation,
                        "approved-preservation",
                        corpus_fingerprint,
                    ),
                )
            )
        return comparison_engine.compare_projections(projections[0], projections[1])

    def _approved_preservation_review(self) -> dict[str, object]:
        comparison = self._equivalent_replacement_comparison()
        rationale = comparison_certification._rationale(
            comparison,
            [
                comparison_certification._authority(
                    "replacement_evidence", "fixture:replacement-adapter"
                )
            ],
        )
        approved = classification.classify_comparison(
            comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=rationale,
            requested_disposition="preserved_behavior",
            preservation_scope="fixture semantic outcome",
        )
        return {
            "classification": approved,
            "comparison": comparison,
            "review_id": "fixture-approved-preservation@1.0.0",
        }


if __name__ == "__main__":
    unittest.main()
