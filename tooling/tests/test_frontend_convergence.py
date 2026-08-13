from __future__ import annotations

import copy
import unittest

from tooling.frontend_convergence import (
    FrontendConvergenceError,
    FrontendConvergenceSuite,
)


class FrontendConvergenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid = FrontendConvergenceSuite().corpus

    def certify(self, corpus: dict) -> dict:
        return FrontendConvergenceSuite(corpus=corpus).certify()

    def test_checked_corpus_is_complete(self) -> None:
        result = self.certify(self.valid)
        self.assertEqual(result["cases"], 11)
        self.assertEqual(result["host_routes"], 3)
        self.assertEqual(result["operations"], 15)
        self.assertEqual(result["mappings"], 17)
        self.assertEqual(result["legacy_cases"], 9)
        self.assertEqual(result["legacy_features"], 38)
        self.assertEqual(result["legacy_families"], 10)
        self.assertEqual(result["rejected"], 13)
        self.assertEqual(result["profiles"], 3)

    def test_case_shrinkage_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.valid)
        mutated["cases"].pop()
        with self.assertRaisesRegex(FrontendConvergenceError, "expected 11"):
            self.certify(mutated)

    def test_host_route_shrinkage_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.valid)
        mutated["host_routes"].pop()
        with self.assertRaises(FrontendConvergenceError):
            self.certify(mutated)

    def test_simply_operation_shrinkage_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.valid)
        case = next(case for case in mutated["cases"] if case["id"].endswith("atomic-composition"))
        step = next(step for step in case["steps"] if step["operation"] == "atomic")
        step["operation"] = "group"
        with self.assertRaises(FrontendConvergenceError):
            self.certify(mutated)

    def test_semantic_mapping_shrinkage_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.valid)
        for case in mutated["cases"]:
            if "node.atomic" in case["semantic_mapping_ids"]:
                case["semantic_mapping_ids"].remove("node.atomic")
        with self.assertRaisesRegex(FrontendConvergenceError, "Semantic mapping coverage"):
            self.certify(mutated)

    def test_legacy_feature_shrinkage_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.valid)
        case = next(case for case in mutated["cases"] if case["id"].endswith("atomic-composition"))
        case["legacy"]["feature_ids"].remove("group.atomic")
        with self.assertRaisesRegex(FrontendConvergenceError, "supported-feature coverage"):
            self.certify(mutated)

    def test_unresolved_legacy_disposition_is_blocking(self) -> None:
        mutated = copy.deepcopy(self.valid)
        mutated["rejected_legacy_features"][0]["disposition"] = "unresolved_discrepancy"
        with self.assertRaises(FrontendConvergenceError):
            self.certify(mutated)

    def test_profile_identity_drift_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.valid)
        mutated["target_profiles"][0]["reference"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(FrontendConvergenceError, "profile fingerprint mismatch"):
            self.certify(mutated)

    def test_representation_exclusion_expansion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.valid)
        mutated["representation_exclusions"].append("diagnostic content")
        with self.assertRaises(FrontendConvergenceError):
            self.certify(mutated)

    def test_stale_corpus_fingerprint_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.valid)
        mutated["authority"] += " drift"
        with self.assertRaisesRegex(FrontendConvergenceError, "fingerprint is stale"):
            self.certify(mutated)


if __name__ == "__main__":
    unittest.main()
