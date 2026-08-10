"""Focused certification tests for canonical STRling data contracts."""

from __future__ import annotations

import copy
import json
import unittest

from tooling.contract_validation import (
    CONTRACT_ROOT,
    ContractValidationError,
    ContractSuite,
    canonical_json,
    iter_nodes,
    load_json,
)


class CanonicalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = ContractSuite()

    def test_all_schemas_are_valid_draft_2020_12(self) -> None:
        self.assertEqual(
            {
                "analysis.schema.json",
                "compile-request.schema.json",
                "compile-result.schema.json",
                "diagnostic.schema.json",
                "portability.schema.json",
                "semantic-ir.schema.json",
                "source.schema.json",
            },
            set(self.suite.schemas),
        )

    def test_positive_examples_validate(self) -> None:
        self.assertEqual(14, self.suite.validate_positive_examples())

    def test_controlled_negative_examples_are_rejected(self) -> None:
        self.assertEqual(17, self.suite.validate_negative_examples())

    def test_all_semantic_node_categories_are_exercised(self) -> None:
        example = load_json(
            CONTRACT_ROOT / "examples" / "semantic-ir" / "semantic-all-nodes.json"
        )
        kinds = {node["kind"] for node in iter_nodes(example["root"])}
        self.assertEqual(
            {
                "alternation",
                "atomic",
                "backreference",
                "capture",
                "character_set",
                "empty",
                "literal",
                "lookaround",
                "position",
                "repeat",
                "sequence",
                "wildcard",
            },
            kinds,
        )

    def test_constructed_semantics_need_no_source_or_span(self) -> None:
        example = load_json(
            CONTRACT_ROOT / "examples" / "semantic-ir" / "semantic-constructed.json"
        )
        self.suite.validate("semantic-ir.schema.json", example)
        self.assertNotIn("sources", example)
        self.assertTrue(
            all("origin" not in node for node in iter_nodes(example["root"]))
        )

    def test_unicode_example_uses_utf8_byte_boundaries(self) -> None:
        example = load_json(
            CONTRACT_ROOT / "examples" / "semantic-ir" / "semantic-all-nodes.json"
        )
        self.suite.validate("semantic-ir.schema.json", example)
        wildcard = next(
            node for node in iter_nodes(example["root"]) if node["kind"] == "wildcard"
        )
        span = wildcard["origin"]["source_spans"][0]
        self.assertEqual((2, 6), (span["start"], span["end"]))
        self.assertEqual(4, len("😀".encode("utf-8")))

    def test_serialization_is_deterministic_and_unicode_preserving(self) -> None:
        example = load_json(
            CONTRACT_ROOT / "examples" / "semantic-ir" / "semantic-all-nodes.json"
        )
        first = canonical_json(example)
        second = canonical_json(json.loads(first.decode("utf-8")))
        self.assertEqual(first, second)
        self.assertIn("α".encode(), first)
        self.assertNotIn(b": ", first)
        self.assertNotIn(b", ", first)

    def test_successful_source_compile_exchange(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "source-success.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "success.json"
        )
        self.suite.validate_exchange(request, result)

    def test_unsupported_frontend_is_a_structured_failure(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "unsupported-frontend.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "unsupported-frontend.json"
        )
        self.suite.validate_exchange(request, result)
        self.assertEqual("STRL-PROTOCOL-0002", result["diagnostics"][0]["code"])

    def test_partial_semantics_require_explicit_request(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "partial-failure.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "partial-failure.json"
        )
        self.suite.validate_exchange(request, result)
        self.assertEqual("partial", result["semantic_result"]["status"])

    def test_all_protocol_examples_round_trip(self) -> None:
        for family in (
            "diagnostic",
            "analysis",
            "compile-request",
            "compile-result",
        ):
            for path in sorted((CONTRACT_ROOT / "examples" / family).glob("*.json")):
                value = load_json(path)
                first = canonical_json(value)
                self.assertEqual(
                    first,
                    canonical_json(json.loads(first.decode("utf-8"))),
                    path,
                )

    def test_diagnostic_attribution_must_resolve_to_exchange_source(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "partial-failure.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "partial-failure.json"
        )
        malformed = copy.deepcopy(result)
        malformed["diagnostics"][0]["primary_location"]["source_id"] = "src:undeclared"
        with self.assertRaises(ContractValidationError):
            self.suite.validate_exchange(request, malformed)

    def test_analysis_node_ids_must_resolve_to_semantic_result(self) -> None:
        request = load_json(
            CONTRACT_ROOT / "examples" / "compile-request" / "source-success.json"
        )
        result = load_json(
            CONTRACT_ROOT / "examples" / "compile-result" / "success.json"
        )
        malformed = copy.deepcopy(result)
        malformed["analysis"]["node_facts"][0]["node_id"] = "node:undeclared"
        with self.assertRaises(ContractValidationError):
            self.suite.validate_exchange(request, malformed)


if __name__ == "__main__":
    unittest.main()
