from __future__ import annotations

import copy
import unittest

from tooling.canonical_cli_contract import (
    CanonicalCliContractError,
    CanonicalCliContractSuite,
    EXPECTED_COMMANDS,
)


class CanonicalCliContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = CanonicalCliContractSuite()

    def test_certification_locks_complete_denominator(self) -> None:
        result = self.suite.certify()
        self.assertEqual(result["commands"], 8)
        self.assertEqual(result["cases"], 42)
        self.assertEqual(result["coverage_requirements"], 19)
        self.assertEqual(result["profiles"], 5)
        self.assertEqual(result["positive_responses"], 6)
        self.assertEqual(result["negative_mutations"], 6)
        self.assertRegex(result["fingerprint"], r"^sha256:[a-f0-9]{64}$")

    def test_command_tree_is_exact(self) -> None:
        observed = {entry["id"] for entry in self.suite.manifest["commands"]}
        self.assertEqual(observed, EXPECTED_COMMANDS)

    def test_case_shrinkage_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.suite.manifest)
        manifest["cases"] = manifest["cases"][:-1]
        with self.assertRaises(CanonicalCliContractError):
            self.suite.validate_manifest(manifest)

    def test_duplicate_case_identity_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.suite.manifest)
        manifest["cases"][1]["id"] = manifest["cases"][0]["id"]
        with self.assertRaises(CanonicalCliContractError):
            self.suite.validate_manifest(manifest)

    def test_missing_coverage_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.suite.manifest)
        manifest["coverage_requirements"].append("uncovered_requirement")
        manifest["coverage_requirements"].sort()
        with self.assertRaises(CanonicalCliContractError):
            self.suite.validate_manifest(manifest)

    def test_profile_fingerprint_mutation_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.suite.manifest)
        manifest["profiles"][0]["sha256"] = "0" * 64
        with self.assertRaises(CanonicalCliContractError):
            self.suite.validate_manifest(manifest)

    def test_every_positive_response_validates(self) -> None:
        self.assertEqual(self.suite.validate_positive_responses(), 6)

    def test_every_controlled_mutation_is_rejected(self) -> None:
        self.assertEqual(self.suite.validate_negative_mutations(), 6)

    def test_unknown_response_field_is_rejected(self) -> None:
        response = copy.deepcopy(self.suite.positive_responses()["target_list"])
        response["semantic_guess"] = True
        with self.assertRaises(CanonicalCliContractError):
            self.suite.validate_response(response)

    def test_raw_subject_has_no_cli_schema_field(self) -> None:
        schema_text = str(self.suite.response_schema).lower()
        self.assertNotIn("subject_text", schema_text)
        self.assertNotIn("raw_subject", schema_text)


if __name__ == "__main__":
    unittest.main()
