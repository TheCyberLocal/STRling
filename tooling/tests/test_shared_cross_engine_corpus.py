"""Completeness and anti-shrinkage tests for the shared engine corpus."""

from __future__ import annotations

import copy
import unittest
from unittest import mock

from tooling import shared_cross_engine_corpus as shared


class SharedCrossEngineCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validation = shared.validate_corpus()

    def validate_mutation(self, mutate) -> None:
        corpus = copy.deepcopy(self.validation["corpus"])
        mutate(corpus)
        original = shared.load_json

        def load(path):
            if path == shared.CORPUS_PATH:
                return copy.deepcopy(corpus)
            return original(path)

        with mock.patch.object(shared, "load_json", side_effect=load):
            with self.assertRaises(shared.SharedCorpusError):
                shared.validate_corpus()

    def test_exact_five_profile_denominator_is_complete(self) -> None:
        corpus = self.validation["corpus"]
        self.assertEqual(20, self.validation["case_count"])
        self.assertEqual(
            {"execute": 84, "not_applicable": 7, "unsupported": 9},
            self.validation["application_counts"],
        )
        for vector in corpus["vectors"]:
            self.assertEqual(
                list(shared.EXPECTED_PROFILE_IDS),
                [
                    item["target_profile"]["profile_id"]
                    for item in vector["applications"]
                ],
            )

    def test_case_removal_fails_closed(self) -> None:
        self.validate_mutation(lambda corpus: corpus["vectors"].pop())

    def test_profile_application_removal_fails_closed(self) -> None:
        self.validate_mutation(
            lambda corpus: corpus["vectors"][0]["applications"].pop()
        )

    def test_case_fingerprint_mutation_fails_closed(self) -> None:
        self.validate_mutation(
            lambda corpus: corpus["vectors"][0].update({"sha256": "0" * 64})
        )

    def test_vector_coverage_fingerprint_mutation_fails_closed(self) -> None:
        self.validate_mutation(
            lambda corpus: corpus["vectors"][0]["features"].append("unexpected")
        )

    def test_target_output_cannot_become_expectation_authority(self) -> None:
        self.validate_mutation(
            lambda corpus: corpus["vectors"][0].update({"target_pattern": "derived"})
        )

    def test_every_mandatory_rewrite_has_positive_negative_execution_evidence(
        self,
    ) -> None:
        corpus = self.validation["corpus"]
        rewrite_vectors = [
            vector for vector in corpus["vectors"] if vector["rewrite_strategies"]
        ]
        self.assertEqual(1, len(rewrite_vectors))
        vector = rewrite_vectors[0]
        case = shared.load_json(shared.ROOT / vector["path"])
        self.assertTrue(case["expectations"]["matches"]["positive"])
        self.assertTrue(case["expectations"]["matches"]["negative"])
        self.assertIn(
            "equivalent_rewrite",
            [item.get("portability_status") for item in vector["applications"]],
        )
        registry = shared.load_json(shared.EQUIVALENCE_REGISTRY)
        mandatory = sorted(
            item["strategy_id"]
            for item in registry["strategies"]
            if item["application_kind"] == "mandatory_portability"
        )
        optional = {
            item["strategy_id"]
            for item in registry["strategies"]
            if item["application_kind"] == "optional_optimization"
        }
        self.assertEqual(mandatory, corpus["coverage"]["required_rewrite_strategies"])
        self.assertTrue(optional)
        self.assertTrue(
            optional.isdisjoint(
                strategy
                for item in rewrite_vectors
                for strategy in item["rewrite_strategies"]
            )
        )

    def test_checked_observation_evidence_is_structurally_current(self) -> None:
        evidence = shared.verify_evidence()
        self.assertEqual(20, evidence["case_count"])

    def test_projection_environment_preserves_windows_linker_discovery(self) -> None:
        values = {
            "INCLUDE": "include-path",
            "LIB": "library-path",
            "LIBPATH": "managed-library-path",
            "PATH": "executable-path",
            "SYSTEMROOT": "windows-root",
            "TEMP": "temporary-path",
            "TMP": "temporary-path",
        }
        with mock.patch.object(shared.os, "name", "nt"):
            with mock.patch.dict(shared.os.environ, values, clear=True):
                environment = shared._projection_environment()
        self.assertEqual(values, {key: environment[key] for key in values})
        self.assertEqual("C.UTF-8", environment["LANG"])
        self.assertEqual("C.UTF-8", environment["LC_ALL"])
        self.assertEqual("UTC", environment["TZ"])


if __name__ == "__main__":
    unittest.main()
