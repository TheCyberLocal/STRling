"""Deterministic pairing and field-comparison certification tests."""

from __future__ import annotations

import copy
import unittest

from tooling import migration_comparison as projection_contract
from tooling import migration_comparison_engine as engine
from tooling.legacy_reference import python_reference as reference
from tooling.tests.test_migration_comparison import make_context, make_observation


def make_typescript_observation(
    *,
    outcome: dict[str, object] | None = None,
    source: str = "literal",
) -> dict[str, object]:
    observation = make_observation(outcome=outcome)
    request = observation["request"]["value"]
    request["expected_legacy_surface"] = "typescript.core.parser.parse"
    request["input"]["source"] = source
    observation["request"]["fingerprint"] = projection_contract.canonical_fingerprint(
        request
    )
    observation["runner"] = {
        "id": "typescript",
        "kind": "strling.legacy-reference-runner",
        "language": "typescript",
        "version": "1.0.0",
    }
    observation["implementation"] = {
        "algorithm": "sha256",
        "fingerprint": "sha256:" + "6" * 64,
        "inputs": [],
        "kind": "strling.legacy-typescript-implementation",
        "manifest_encoding": "canonical-json-v1",
        "runtime": {"name": "node", "version": "24.4.1"},
    }
    observation["surface"] = "typescript.core.parser.parse"
    return observation


def make_pair(
    *,
    left_outcome: dict[str, object] | None = None,
    right_outcome: dict[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    left_observation = make_observation(outcome=left_outcome)
    right_observation = make_typescript_observation(outcome=right_outcome)
    return (
        projection_contract.project_observation(
            left_observation, make_context(left_observation)
        ),
        projection_contract.project_observation(
            right_observation, make_context(right_observation)
        ),
    )


class PairingAndComparisonTests(unittest.TestCase):
    def test_normalized_exact_equality_is_equivalent(self) -> None:
        left, right = make_pair()
        result = engine.compare_projections(left, right)
        self.assertEqual(
            result["comparability"], {"reason": None, "state": "comparable"}
        )
        self.assertEqual(result["relationship"], "equivalent_observation")
        self.assertEqual(result["differences"], [])
        self.assertNotEqual(
            result["left"]["source"]["observation_identity"],
            result["right"]["source"]["observation_identity"],
        )

    def test_single_nested_field_difference_has_exact_path(self) -> None:
        left, right = make_pair()
        right_observation = make_typescript_observation()
        right_observation["outcome"]["evidence"]["flags"]["unicode"] = False
        right = projection_contract.project_observation(
            right_observation, make_context(right_observation)
        )
        result = engine.compare_projections(left, right)
        self.assertEqual(result["relationship"], "differing_observation")
        self.assertEqual(
            result["differences"],
            [
                {
                    "kind": "value_mismatch",
                    "left": {"present": True, "value": True},
                    "path": "/outcome/evidence/flags/unicode",
                    "right": {"present": True, "value": False},
                }
            ],
        )

    def test_multiple_object_and_array_differences_are_stably_ordered(self) -> None:
        left_outcome = {
            "evidence": {"items": [{"a": 1}, {"b": 2}], "left_only": "yes"},
            "status": "success",
        }
        right_outcome = {
            "evidence": {
                "items": [{"a": 3}, {"b": 2}, {"c": 4}],
                "right_only": "yes",
            },
            "status": "success",
        }
        left, right = make_pair(
            left_outcome=left_outcome,
            right_outcome=right_outcome,
        )
        result = engine.compare_projections(left, right)
        self.assertEqual(
            [difference["path"] for difference in result["differences"]],
            [
                "/outcome/evidence/items/0/a",
                "/outcome/evidence/items/2",
                "/outcome/evidence/left_only",
                "/outcome/evidence/right_only",
            ],
        )
        self.assertEqual(
            [difference["kind"] for difference in result["differences"]],
            [
                "value_mismatch",
                "left_missing",
                "right_missing",
                "left_missing",
            ],
        )

    def test_success_and_failure_are_different_without_collapsing_fields(self) -> None:
        failure = {
            "failure": {
                "class": "STRlingParseError",
                "message": "bad group",
                "stage": "parser",
            },
            "status": "legacy_failure",
        }
        left, right = make_pair(right_outcome=failure)
        result = engine.compare_projections(left, right)
        self.assertEqual(result["relationship"], "differing_observation")
        self.assertEqual(
            [difference["path"] for difference in result["differences"]],
            ["/outcome/evidence", "/outcome/failure", "/outcome/status"],
        )

    def test_equal_failures_are_equivalent(self) -> None:
        failure = {
            "failure": {
                "class": "STRlingParseError",
                "message": "bad group",
                "position": 4,
                "stage": "parser",
            },
            "status": "legacy_failure",
        }
        left, right = make_pair(left_outcome=failure, right_outcome=failure)
        result = engine.compare_projections(left, right)
        self.assertEqual(result["relationship"], "equivalent_observation")

    def test_any_unsupported_outcome_is_not_comparable(self) -> None:
        unsupported = {
            "reason": "not implemented by this fixture",
            "status": "unsupported",
        }
        left, right = make_pair(right_outcome=unsupported)
        result = engine.compare_projections(left, right)
        self.assertEqual(result["relationship"], "not_comparable")
        self.assertEqual(
            result["comparability"],
            {"reason": "unsupported_operation", "state": "not_comparable"},
        )
        self.assertEqual(result["differences"], [])

    def test_unsupported_vs_unsupported_remains_not_comparable(self) -> None:
        unsupported = {
            "reason": "not exposed by either fixture",
            "status": "unsupported",
        }
        left, right = make_pair(left_outcome=unsupported, right_outcome=unsupported)
        result = engine.compare_projections(left, right)
        self.assertEqual(result["relationship"], "not_comparable")
        self.assertEqual(result["comparability"]["reason"], "unsupported_operation")

    def test_missing_counterpart_is_not_comparable(self) -> None:
        left, _ = make_pair()
        result = engine.compare_projections(left, None)
        self.assertEqual(result["relationship"], "not_comparable")
        self.assertEqual(result["comparability"]["reason"], "missing_counterpart")
        self.assertIsNone(result["right"])

    def test_incompatible_same_runner_surfaces_are_not_comparable(self) -> None:
        observation = make_observation()
        context = make_context(observation)
        left = projection_contract.project_observation(observation, context)
        right = projection_contract.project_observation(observation, context)
        result = engine.compare_projections(left, right)
        self.assertEqual(result["relationship"], "not_comparable")
        self.assertEqual(result["comparability"]["reason"], "incompatible_surface")

    def test_pairing_rejects_mismatched_case_and_normalization_identity(self) -> None:
        left, _ = make_pair()
        different_observation = make_typescript_observation(source="different")
        different = projection_contract.project_observation(
            different_observation, make_context(different_observation)
        )
        with self.assertRaisesRegex(engine.PairingError, "case identities"):
            engine.compare_projections(left, different)

        zero_rule_observation = make_typescript_observation()
        zero_rule = projection_contract.project_observation(
            zero_rule_observation,
            make_context(zero_rule_observation),
            normalization_rule_ids=(),
        )
        with self.assertRaisesRegex(
            engine.PairingError, "normalization rule identities"
        ):
            engine.compare_projections(left, zero_rule)

    def test_projection_fingerprint_and_semantic_mutations_are_rejected(self) -> None:
        left, right = make_pair()
        fingerprint_mutation = copy.deepcopy(right)
        fingerprint_mutation["projection_fingerprint"] = "sha256:" + "7" * 64
        with self.assertRaisesRegex(
            projection_contract.ComparisonContractError, "fingerprint"
        ):
            engine.compare_projections(left, fingerprint_mutation)

        semantic_mutation = copy.deepcopy(right)
        semantic_mutation["semantic_observation"]["outcome"]["status"] = "unsupported"
        with self.assertRaises(projection_contract.ComparisonContractError):
            engine.compare_projections(left, semantic_mutation)

    def test_repeated_comparison_is_stable_and_does_not_mutate_projections(
        self,
    ) -> None:
        left, right = make_pair()
        before_left = copy.deepcopy(left)
        before_right = copy.deepcopy(right)
        first = engine.compare_projections(left, right)
        second = engine.compare_projections(left, right)
        self.assertEqual(
            reference.canonical_line(first), reference.canonical_line(second)
        )
        self.assertEqual(left, before_left)
        self.assertEqual(right, before_right)

    def test_both_missing_is_rejected(self) -> None:
        with self.assertRaisesRegex(engine.PairingError, "at least one"):
            engine.compare_projections(None, None)


if __name__ == "__main__":
    unittest.main()
