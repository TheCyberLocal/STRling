from __future__ import annotations

import copy
import json
import unittest

from tooling.semantic_conversion_contract import (
    CONTRACT_ROOT,
    SemanticConversionContractError,
    SemanticConversionContractSuite,
)


class SemanticConversionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = SemanticConversionContractSuite()
        self.exact_dsl = self.read_example("exact-semantic-dsl.json")
        self.exact_simply = self.read_example("exact-simply.json")
        self.partial = self.read_example("partial-capture-name.json")
        self.unsupported = self.read_example("unsupported-forward-reference.json")

    def read_example(self, name: str) -> dict:
        return json.loads(
            (CONTRACT_ROOT / "examples" / name).read_text(encoding="utf-8")
        )

    def test_closed_contract_and_authored_corpus_certify(self) -> None:
        result = self.suite.certify()
        self.assertEqual(1, result["schemas"])
        self.assertEqual(4, result["positive"])
        self.assertEqual(3, result["negative"])
        self.assertEqual(
            (2, 1, 1), (result["exact"], result["partial"], result["unsupported"])
        )
        self.assertEqual(12, result["node_kinds"])
        self.assertEqual(4, result["member_kinds"])
        self.assertRegex(result["fingerprint"], r"^sha256:[0-9a-f]{64}$")

    def test_exact_requires_a_corresponding_reconstruction_proof(self) -> None:
        mutations = (
            lambda value: value["equivalence"].update({"status": "not_proven"}),
            lambda value: value["equivalence"].update(
                {"reconstructed_fingerprint": "f" * 64}
            ),
            lambda value: value["equivalence"].pop("reconstructed_fingerprint"),
        )
        for mutate in mutations:
            candidate = copy.deepcopy(self.exact_dsl)
            mutate(candidate)
            with self.assertRaises(SemanticConversionContractError):
                self.suite.validate(candidate)

    def test_semantic_output_digest_and_spans_are_correspondence_checked(self) -> None:
        wrong_digest = copy.deepcopy(self.exact_dsl)
        wrong_digest["output"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(SemanticConversionContractError, "digest"):
            self.suite.validate(wrong_digest)

        wrong_span = copy.deepcopy(self.exact_dsl)
        wrong_span["node_mappings"][0]["byte_span"]["end"] = 1000
        with self.assertRaisesRegex(SemanticConversionContractError, "byte span"):
            self.suite.validate(wrong_span)

    def test_simply_output_is_target_neutral_and_direct_operation_only(self) -> None:
        targeted = copy.deepcopy(self.exact_simply)
        targeted["output"]["request"]["compile"]["target_profile"] = {
            "target_id": "pcre2",
            "profile_version": "1.0.0",
        }
        with self.assertRaises(SemanticConversionContractError):
            self.suite.validate(targeted)

        imported = copy.deepcopy(self.exact_simply)
        imported["output"]["request"]["steps"][0] = {
            "step_id": "n000001",
            "operation": "import_node",
            "arguments": {
                "node": {
                    "node_id": "node:imported",
                    "kind": "empty",
                }
            },
        }
        with self.assertRaisesRegex(SemanticConversionContractError, "direct"):
            self.suite.validate(imported)

    def test_partial_capture_substitution_requires_manual_decision(self) -> None:
        candidate = copy.deepcopy(self.partial)
        candidate["issues"] = candidate["issues"][:1]
        with self.assertRaisesRegex(SemanticConversionContractError, "manual"):
            self.suite.validate(candidate)

    def test_unsupported_has_no_output_or_projection_mappings(self) -> None:
        candidate = copy.deepcopy(self.unsupported)
        candidate["output"] = copy.deepcopy(self.exact_dsl["output"])
        with self.assertRaisesRegex(SemanticConversionContractError, "output"):
            self.suite.validate(candidate)

    def test_destination_explanation_and_mapping_correspondence_is_closed(self) -> None:
        wrong_contract = copy.deepcopy(self.exact_dsl)
        wrong_contract["destination_contract"]["id"] = "strling.simply-builder"
        with self.assertRaisesRegex(SemanticConversionContractError, "destination"):
            self.suite.validate(wrong_contract)

        wrong_program = copy.deepcopy(self.exact_dsl)
        wrong_program["explanation_links"] = [
            {
                "model_version": "1.0.0",
                "semantic_program": "9" * 64,
                "node_id": "node:source/literal",
                "evidence_class": "semantic_fact",
            }
        ]
        with self.assertRaisesRegex(SemanticConversionContractError, "program"):
            self.suite.validate(wrong_program)

        duplicate = copy.deepcopy(self.partial)
        duplicate["node_mappings"].append(copy.deepcopy(duplicate["node_mappings"][0]))
        with self.assertRaisesRegex(SemanticConversionContractError, "node mappings"):
            self.suite.validate(duplicate)


if __name__ == "__main__":
    unittest.main()
