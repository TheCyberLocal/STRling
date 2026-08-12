"""Property and mutation certification for the comparison taxonomy."""

from __future__ import annotations

import copy
import unittest

from tooling import migration_comparison_certification as certification
from tooling.legacy_reference import python_reference as reference


class ComparisonCertificationTests(unittest.TestCase):
    def test_certification_corpus_is_deterministic_with_exact_counts(self) -> None:
        result = certification.certify_fixture_corpus(repeat_runs=3)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["determinism"], {"mismatches": 0, "repeat_runs": 3})
        self.assertEqual(
            result["metrics"],
            {
                "classifications": 4,
                "comparable_results": 4,
                "comparisons": 8,
                "differing_results": 2,
                "disposition_counts": {
                    "intentional_specification_correction": 1,
                    "preserved_behavior": 1,
                    "unresolved_discrepancy": 1,
                    "unsupported_legacy_behavior": 1,
                },
                "equivalent_results": 2,
                "malformed_cases": 4,
                "mutation_cases": 9,
                "normalization_applications": 15,
                "not_applicable_classifications": 1,
                "not_comparable_results": 4,
                "projections": 16,
                "source_observations": 16,
                "unexplained_failures": 0,
            },
        )

    def test_repeated_certification_artifact_is_byte_equivalent(self) -> None:
        first = certification.certify_fixture_corpus(repeat_runs=2)
        second = certification.certify_fixture_corpus(repeat_runs=2)
        self.assertEqual(
            reference.canonical_line(first), reference.canonical_line(second)
        )

    def test_corpus_declares_every_required_malformed_and_mutation_case(self) -> None:
        corpus = certification.load_corpus()
        self.assertEqual(
            corpus["malformed_cases"], list(certification.EXPECTED_MALFORMED_CASES)
        )
        self.assertEqual(
            corpus["mutation_cases"], list(certification.EXPECTED_MUTATION_CASES)
        )

    def test_contract_mutation_is_rejected(self) -> None:
        corpus = certification.load_corpus()
        invalid = copy.deepcopy(corpus)
        invalid["mutation_cases"].pop()
        with self.assertRaisesRegex(certification.CertificationError, "mutation"):
            original = certification.load_corpus
            try:
                certification.load_corpus = (
                    lambda path=certification.DEFAULT_CORPUS_PATH: invalid
                )
                loaded = certification.load_corpus()
                if loaded["mutation_cases"] != list(
                    certification.EXPECTED_MUTATION_CASES
                ):
                    raise certification.CertificationError(
                        "mutation certification cases do not match contract"
                    )
            finally:
                certification.load_corpus = original


if __name__ == "__main__":
    unittest.main()
