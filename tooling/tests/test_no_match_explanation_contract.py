from __future__ import annotations

import copy
import json
import unittest

from tooling.no_match_explanation_contract import (
    CONTRACT_ROOT,
    NoMatchExplanationContractError,
    NoMatchExplanationContractSuite,
)


class NoMatchExplanationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = NoMatchExplanationContractSuite()
        self.matched = self.read_example("matched-literal.json")
        self.proven = self.read_example("proven-literal-mismatch.json")
        self.likely = self.read_example("likely-multiple-blockers.json")
        self.unknown = self.read_example("unknown-step-limit.json")
        self.unavailable = self.read_example("unavailable-target.json")

    @staticmethod
    def read_example(name: str) -> dict:
        return json.loads(
            (CONTRACT_ROOT / "examples" / name).read_text(encoding="utf-8")
        )

    def test_closed_contract_taxonomy_and_corpus_certify(self) -> None:
        result = self.suite.certify()
        self.assertEqual(1, result["schemas"])
        self.assertEqual(5, result["positive"])
        self.assertEqual(5, result["negative"])
        self.assertEqual(27, result["reasons"])
        self.assertEqual(17, result["programs"])
        self.assertEqual(24, result["cases"])
        self.assertEqual(1, result["matched"])
        self.assertGreaterEqual(result["proven"], 1)
        self.assertGreaterEqual(result["likely"], 1)
        self.assertGreaterEqual(result["unknown"], 7)
        self.assertEqual(1, result["unavailable"])
        self.assertRegex(result["fingerprint"], r"^sha256:[0-9a-f]{64}$")

    def test_outcome_and_explanation_disposition_are_independent_but_closed(
        self,
    ) -> None:
        matched_with_cause = copy.deepcopy(self.matched)
        matched_with_cause["explanation_disposition"] = "proven"
        matched_with_cause["findings"] = copy.deepcopy(self.proven["findings"])
        with self.assertRaises(NoMatchExplanationContractError):
            self.suite.validate(matched_with_cause)

        false_proof = copy.deepcopy(self.proven)
        false_proof["findings"][0]["confidence"] = "likely"
        with self.assertRaisesRegex(NoMatchExplanationContractError, "proven/likely"):
            self.suite.validate(false_proof)

        unknown_proof = copy.deepcopy(self.unknown)
        unknown_proof["findings"][0]["confidence"] = "proven"
        with self.assertRaisesRegex(NoMatchExplanationContractError, "uncertainty"):
            self.suite.validate(unknown_proof)

    def test_resource_reason_and_reached_limit_must_correspond(self) -> None:
        candidate = copy.deepcopy(self.unknown)
        candidate["work"]["reached_limits"] = []
        with self.assertRaisesRegex(NoMatchExplanationContractError, "correspond"):
            self.suite.validate(candidate)

        wrong_kind = copy.deepcopy(self.unknown)
        wrong_kind["work"]["reached_limits"] = ["branches"]
        with self.assertRaisesRegex(NoMatchExplanationContractError, "correspond"):
            self.suite.validate(wrong_kind)

    def test_target_status_and_unavailable_reason_must_correspond(self) -> None:
        candidate = copy.deepcopy(self.unavailable)
        candidate["target"]["status"] = "unresolved"
        with self.assertRaisesRegex(NoMatchExplanationContractError, "correspond"):
            self.suite.validate(candidate)

        portable = copy.deepcopy(self.unavailable)
        portable["target"]["status"] = "native"
        with self.assertRaises(NoMatchExplanationContractError):
            self.suite.validate(portable)

    def test_program_subject_and_utf8_correspondence_are_checked(self) -> None:
        wrong_program = copy.deepcopy(self.matched)
        wrong_program["semantic_explanation"]["semantic_program"] = "0" * 64
        with self.assertRaisesRegex(NoMatchExplanationContractError, "program"):
            self.suite.validate(wrong_program)

        wrong_location = copy.deepcopy(self.proven)
        wrong_location["findings"][0]["subject_location"]["end"] = 4
        with self.assertRaisesRegex(NoMatchExplanationContractError, "subject span"):
            self.suite.validate(wrong_location)

        unicode_boundary = copy.deepcopy(self.proven)
        unicode_boundary["subject"]["utf8_bytes"] = 2
        unicode_boundary["findings"][0]["subject_location"] = {
            "kind": "span",
            "start": 0,
            "end": 2,
        }
        self.suite.validate(unicode_boundary)

    def test_finding_order_taxonomy_and_context_are_closed(self) -> None:
        noncanonical = copy.deepcopy(self.likely)
        noncanonical["findings"][0]["ordinal"] = 1
        with self.assertRaisesRegex(NoMatchExplanationContractError, "ordinals"):
            self.suite.validate(noncanonical)

        wrong_evidence = copy.deepcopy(self.proven)
        wrong_evidence["findings"][0]["evidence_class"] = "uncertainty"
        with self.assertRaisesRegex(NoMatchExplanationContractError, "taxonomy"):
            self.suite.validate(wrong_evidence)

        missing_context = copy.deepcopy(self.proven)
        missing_context["findings"][0].pop("context")
        with self.assertRaisesRegex(NoMatchExplanationContractError, "context"):
            self.suite.validate(missing_context)


if __name__ == "__main__":
    unittest.main()
