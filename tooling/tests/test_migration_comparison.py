"""Certification tests for canonical historical-observation comparison."""

from __future__ import annotations

import copy
import unittest

from tooling import migration_comparison as comparison
from tooling.legacy_reference import python_reference as reference


def make_observation(
    *,
    outcome: dict[str, object] | None = None,
    implementation_fingerprint: str = "sha256:" + "1" * 64,
) -> dict[str, object]:
    request_value = {
        "expected_legacy_surface": "python.core.parser.parse",
        "input": {"source": "literal"},
        "kind": reference.REQUEST_KIND,
        "operation": "parser.parse",
        "options": {},
        "protocol_version": reference.PROTOCOL_VERSION,
    }
    return {
        "implementation": {
            "algorithm": "sha256",
            "fingerprint": implementation_fingerprint,
            "inputs": [],
            "kind": "strling.legacy-python-implementation",
            "manifest_encoding": "canonical-json-v1",
            "runtime": {"name": "python", "version": "3.13.5"},
        },
        "kind": reference.OBSERVATION_KIND,
        "observation_schema_version": reference.OBSERVATION_SCHEMA_VERSION,
        "operation": "parser.parse",
        "outcome": outcome
        or {
            "evidence": {
                "ast": [{"kind": "literal", "value": "literal"}],
                "diagnostics": [],
                "flags": {"unicode": True},
                "return_shape": "list",
            },
            "status": "success",
        },
        "protocol_version": reference.PROTOCOL_VERSION,
        "request": {
            "algorithm": "sha256",
            "fingerprint": comparison.canonical_fingerprint(request_value),
            "value": request_value,
        },
        "runner": copy.deepcopy(reference.RUNNER),
        "surface": "python.core.parser.parse",
    }


def make_context(observation: dict[str, object]) -> dict[str, object]:
    corpus = {
        "algorithm": "sha256",
        "fingerprint": "sha256:" + "2" * 64,
        "version": "1.0.0",
    }
    case_id = "projection-literal"
    request = observation["request"]
    assert isinstance(request, dict)
    return {
        "case_id": case_id,
        "case_identity": comparison.canonical_fingerprint(
            {
                "case_id": case_id,
                "corpus_version": corpus["version"],
                "request": request["value"],
            }
        ),
        "comparison_corpus_version": "1.0.0",
        "corpus": corpus,
    }


class ProjectionContractTests(unittest.TestCase):
    def test_allowed_normalization_preserves_complete_outcome(self) -> None:
        observation = make_observation()
        projection = comparison.project_observation(
            observation,
            make_context(observation),
        )

        self.assertEqual(
            projection["normalization_rule_ids"],
            ["select-semantic-outcome@1.0.0"],
        )
        self.assertEqual(
            projection["semantic_observation"],
            {"outcome": observation["outcome"]},
        )
        self.assertEqual(
            projection["source"]["implementation"], observation["implementation"]
        )
        self.assertEqual(projection["source"]["runner"], observation["runner"])
        self.assertEqual(projection["source"]["request"], observation["request"])

    def test_zero_normalization_retains_entire_observation(self) -> None:
        observation = make_observation()
        projection = comparison.project_observation(
            observation,
            make_context(observation),
            normalization_rule_ids=(),
        )
        self.assertEqual(projection["normalization_rule_ids"], [])
        self.assertEqual(projection["semantic_observation"], observation)

    def test_normalization_is_idempotent_for_semantic_payload(self) -> None:
        observation = make_observation()
        first = comparison.project_observation(observation, make_context(observation))
        second = comparison.project_observation(observation, make_context(observation))
        self.assertEqual(first, second)

    def test_unknown_duplicate_and_non_array_rules_are_rejected(self) -> None:
        observation = make_observation()
        context = make_context(observation)
        with self.assertRaisesRegex(comparison.ComparisonContractError, "unknown"):
            comparison.project_observation(
                observation,
                context,
                normalization_rule_ids=("invented@1.0.0",),
            )
        with self.assertRaisesRegex(comparison.ComparisonContractError, "repeat"):
            comparison.project_observation(
                observation,
                context,
                normalization_rule_ids=(
                    "select-semantic-outcome@1.0.0",
                    "select-semantic-outcome@1.0.0",
                ),
            )
        with self.assertRaisesRegex(comparison.ComparisonContractError, "array"):
            comparison.project_observation(
                observation,
                context,
                normalization_rule_ids="select-semantic-outcome@1.0.0",
            )

    def test_projection_fingerprint_is_sensitive_to_provenance_and_semantics(
        self,
    ) -> None:
        observation = make_observation()
        context = make_context(observation)
        baseline = comparison.project_observation(observation, context)

        implementation_changed = make_observation(
            implementation_fingerprint="sha256:" + "3" * 64
        )
        implementation_projection = comparison.project_observation(
            implementation_changed,
            make_context(implementation_changed),
        )
        self.assertEqual(
            baseline["semantic_observation"],
            implementation_projection["semantic_observation"],
        )
        self.assertNotEqual(
            baseline["projection_fingerprint"],
            implementation_projection["projection_fingerprint"],
        )

        semantic_changed = make_observation()
        semantic_changed["outcome"]["evidence"]["flags"]["unicode"] = False
        semantic_projection = comparison.project_observation(
            semantic_changed,
            make_context(semantic_changed),
        )
        self.assertNotEqual(
            baseline["projection_fingerprint"],
            semantic_projection["projection_fingerprint"],
        )

    def test_malformed_schema_request_and_source_identity_are_rejected(self) -> None:
        observation = make_observation()
        context = make_context(observation)

        wrong_schema = copy.deepcopy(observation)
        wrong_schema["observation_schema_version"] = "9.9.9"
        with self.assertRaisesRegex(comparison.ComparisonContractError, "schema"):
            comparison.project_observation(wrong_schema, context)

        wrong_request = copy.deepcopy(observation)
        wrong_request["request"]["fingerprint"] = "sha256:" + "4" * 64
        with self.assertRaisesRegex(
            comparison.ComparisonContractError, "request fingerprint"
        ):
            comparison.project_observation(wrong_request, context)

        wrong_context = copy.deepcopy(context)
        wrong_context["case_identity"] = "sha256:" + "5" * 64
        with self.assertRaisesRegex(
            comparison.ComparisonContractError, "case identity"
        ):
            comparison.project_observation(observation, wrong_context)

    def test_semantic_order_positions_diagnostics_and_text_are_not_normalized(
        self,
    ) -> None:
        evidence = {
            "ast": [
                {"capture": 2, "kind": "group", "position": 7},
                {"capture": 1, "kind": "group", "position": 2},
            ],
            "diagnostics": ["second", "first"],
            "emitted": "(?<name>text)",
            "flags": "mi",
            "target_options": ["utf", "ucp"],
        }
        observation = make_observation(
            outcome={"evidence": evidence, "status": "success"}
        )
        projection = comparison.project_observation(
            observation,
            make_context(observation),
        )
        self.assertEqual(
            projection["semantic_observation"]["outcome"]["evidence"],
            evidence,
        )

    def test_failures_and_unsupported_outcomes_cannot_be_hidden(self) -> None:
        outcomes = (
            {
                "failure": {
                    "class": "STRlingParseError",
                    "message": "bad group",
                    "position": 4,
                    "stage": "parser",
                },
                "status": "legacy_failure",
            },
            {
                "reason": "the selected historical surface is not exposed",
                "status": "unsupported",
            },
        )
        for outcome in outcomes:
            with self.subTest(status=outcome["status"]):
                observation = make_observation(outcome=outcome)
                projection = comparison.project_observation(
                    observation,
                    make_context(observation),
                )
                self.assertEqual(
                    projection["semantic_observation"],
                    {"outcome": outcome},
                )

    def test_raw_observation_is_immutable(self) -> None:
        observation = make_observation()
        before = copy.deepcopy(observation)
        comparison.project_observation(observation, make_context(observation))
        self.assertEqual(observation, before)

    def test_projection_source_mismatch_is_rejected(self) -> None:
        observation = make_observation()
        context = make_context(observation)
        projection = comparison.project_observation(observation, context)
        comparison.validate_projection(projection, observation, context)

        altered = copy.deepcopy(projection)
        altered["source"]["surface"] = "python.core.parser.other"
        with self.assertRaisesRegex(
            comparison.ComparisonContractError, "does not match"
        ):
            comparison.validate_projection(altered, observation, context)


if __name__ == "__main__":
    unittest.main()
