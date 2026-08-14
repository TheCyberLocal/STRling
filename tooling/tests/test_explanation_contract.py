from __future__ import annotations

import copy
import json
import unittest

from tooling.explanation_contract import (
    CONTRACT_ROOT,
    ExplanationContractError,
    ExplanationContractSuite,
)


class ExplanationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = ExplanationContractSuite()
        path = CONTRACT_ROOT / "examples" / "source-less-literal.json"
        self.example = json.loads(path.read_text(encoding="utf-8"))

    def test_versioned_schema_and_authored_examples_certify(self) -> None:
        result = self.suite.certify()
        self.assertEqual(1, result["schemas"])
        self.assertGreaterEqual(result["positive"], 1)
        self.assertGreaterEqual(result["negative"], 1)
        self.assertRegex(result["fingerprint"], r"^sha256:[0-9a-f]{64}$")

    def test_unknown_fields_and_wrong_model_versions_fail(self) -> None:
        for mutate in (
            lambda value: value.update({"model_version": "1.1.0"}),
            lambda value: value.update({"ui_layout": "tree"}),
        ):
            candidate = copy.deepcopy(self.example)
            mutate(candidate)
            with self.assertRaises(ExplanationContractError):
                self.suite.validate(candidate)

    def test_counts_roots_and_source_modes_are_correspondence_checked(self) -> None:
        mutations = (
            ("stale count", lambda value: value["concise"].update({"node_count": 2})),
            (
                "missing root",
                lambda value: value["program"].update({"root_node_id": "node:missing"}),
            ),
            (
                "false provenance",
                lambda value: value["program"].update(
                    {"source_mode": "provenance_available"}
                ),
            ),
        )
        for label, mutate in mutations:
            candidate = copy.deepcopy(self.example)
            mutate(candidate)
            with self.subTest(label=label), self.assertRaises(ExplanationContractError):
                self.suite.validate(candidate)

    def test_node_order_references_and_root_fact_projection_are_checked(self) -> None:
        duplicate = copy.deepcopy(self.example)
        duplicate["nodes"].append(copy.deepcopy(duplicate["nodes"][0]))
        duplicate["concise"]["node_count"] = 2
        with self.assertRaisesRegex(ExplanationContractError, "node IDs"):
            self.suite.validate(duplicate)

        stale = copy.deepcopy(self.example)
        stale["concise"]["root_facts"]["minimum_consumption"] = 0
        with self.assertRaisesRegex(ExplanationContractError, "root facts"):
            self.suite.validate(stale)


if __name__ == "__main__":
    unittest.main()
