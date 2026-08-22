from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from tooling.certification import profile_definition_fingerprint


ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOT = ROOT / "tests/certification/product/1.0"
ARTIFACT_SCHEMA_PATH = (
    ROOT / "governance/schemas/product-certification-artifact.schema.json"
)
MANIFEST_SCHEMA_PATH = (
    ROOT / "governance/schemas/product-certification-producer-manifest.schema.json"
)
MANIFEST_PATH = PRODUCT_ROOT / "producer-manifest.json"
VALID_FIXTURE_PATH = PRODUCT_ROOT / "fixtures/valid-product.json"
MUTATIONS_PATH = PRODUCT_ROOT / "fixtures/mutations.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def apply_mutation(base: dict[str, Any], mutation: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(base)
    path = cast(str, mutation["path"])
    parts = [part.replace("~1", "/").replace("~0", "~") for part in path.split("/")[1:]]
    parent: Any = value
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    leaf = parts[-1]
    operation = mutation["mutation"]
    if operation == "append-copy":
        assert isinstance(parent, list)
        parent.append(copy.deepcopy(parent[int(leaf)]))
    elif operation == "remove":
        if isinstance(parent, list):
            parent.pop(int(leaf))
        else:
            del parent[leaf]
    elif operation == "replace":
        replacement = copy.deepcopy(mutation["value"])
        if isinstance(parent, list):
            parent[int(leaf)] = replacement
        else:
            parent[leaf] = replacement
    else:
        raise AssertionError(f"unknown fixture mutation {operation!r}")
    return value


class ProductCertificationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact_schema = cast(dict[str, Any], load_json(ARTIFACT_SCHEMA_PATH))
        cls.manifest_schema = cast(dict[str, Any], load_json(MANIFEST_SCHEMA_PATH))
        cls.manifest = cast(dict[str, Any], load_json(MANIFEST_PATH))
        cls.fixture = cast(dict[str, Any], load_json(VALID_FIXTURE_PATH))
        cls.mutations = cast(dict[str, Any], load_json(MUTATIONS_PATH))

    def test_schemas_are_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(self.artifact_schema)
        Draft202012Validator.check_schema(self.manifest_schema)

    def test_checked_in_manifest_and_positive_fixture_validate(self) -> None:
        Draft202012Validator(self.manifest_schema).validate(self.manifest)
        Draft202012Validator(self.artifact_schema).validate(self.fixture)

    def test_manifest_exactly_covers_the_governed_full_profile(self) -> None:
        toolchain = cast(dict[str, Any], load_json(ROOT / "toolchain.json"))
        policy = cast(dict[str, Any], toolchain["policy"])
        full = cast(dict[str, Any], cast(dict[str, Any], policy["profiles"])["full"])
        registry = cast(dict[str, dict[str, Any]], policy["operation_registry"])
        members = cast(list[dict[str, Any]], full["operations"])
        producers = cast(list[dict[str, Any]], self.manifest["producers"])

        expected_operations = [cast(str, member["operation"]) for member in members]
        actual_operations = [
            cast(str, producer["operation_id"]) for producer in producers
        ]
        self.assertEqual(expected_operations, actual_operations)
        self.assertEqual(len(actual_operations), len(set(actual_operations)))
        self.assertEqual(
            profile_definition_fingerprint(full),
            cast(dict[str, Any], self.manifest["source_profile"])[
                "definition_fingerprint"
            ],
        )

        for producer in producers:
            operation_id = cast(str, producer["operation_id"])
            definition = registry[operation_id]
            self.assertEqual(
                definition.get("result_contract"), producer["result_contract"]
            )
            self.assertEqual(
                definition.get("result_operation_id"),
                producer["structured_operation_id"],
            )

    def test_manifest_claims_are_closed_over_known_producers(self) -> None:
        producer_ids = {
            cast(str, producer["operation_id"])
            for producer in cast(list[dict[str, Any]], self.manifest["producers"])
        }
        claims = cast(list[dict[str, Any]], self.manifest["claims"])
        claim_ids = [cast(str, claim["claim_id"]) for claim in claims]
        self.assertEqual(
            [
                "product.full-profile-coverage",
                "omega.duplicate-name-contract",
                "omega.range-contract",
                "omega.essential-five-contract",
            ],
            claim_ids,
        )
        self.assertEqual(len(claim_ids), len(set(claim_ids)))
        for claim in claims:
            source = cast(dict[str, Any], claim["source"])
            if "operations" in source:
                self.assertTrue(
                    set(cast(list[str], source["operations"])) <= producer_ids
                )

    def test_aggregate_policy_is_explicit_and_artifacted(self) -> None:
        expected = {
            "version": "1.0.0",
            "precedence": [
                "failed",
                "incomplete",
                "unavailable",
                "waived",
                "passed",
            ],
            "incomplete_result_statuses": [
                "incomplete",
                "not_yet_configured",
                "not_yet_enforceable",
                "skipped",
            ],
            "neutral_result_statuses": ["not_applicable", "passed"],
            "blocking_result_statuses": [
                "failed",
                "incomplete",
                "not_yet_configured",
                "not_yet_enforceable",
                "skipped",
                "unavailable",
            ],
        }
        self.assertEqual(expected, self.manifest["aggregate_policy"])
        self.assertEqual(
            expected,
            cast(dict[str, Any], self.fixture["deterministic_evidence"])[
                "aggregate_policy"
            ],
        )

    def test_positive_fixture_fingerprints_are_self_consistent(self) -> None:
        deterministic = cast(dict[str, Any], self.fixture["deterministic_evidence"])
        results = cast(list[dict[str, Any]], deterministic["results"])
        result_ids = sorted(cast(str, result["result_id"]) for result in results)
        coverage = cast(dict[str, Any], deterministic["coverage"])
        self.assertEqual(
            fingerprint(result_ids), coverage["expected_result_ids_fingerprint"]
        )
        self.assertEqual(
            fingerprint(result_ids), coverage["observed_result_ids_fingerprint"]
        )

        producer = cast(dict[str, Any], results[1]["producer_evidence"])
        self.assertEqual(fingerprint(producer["payload"]), producer["fingerprint"])
        self.assertEqual(
            fingerprint(deterministic), self.fixture["evidence_fingerprint"]
        )

    def test_mutation_catalog_covers_required_fail_closed_cases(self) -> None:
        cases = cast(list[dict[str, Any]], self.mutations["cases"])
        expected = {
            "duplicate-result",
            "missing-result",
            "unknown-result",
            "stale-repository",
            "stale-profile",
            "conflicting-result",
            "invalid-waiver",
            "producer-fingerprint",
            "aggregate-mismatch",
            "artifact-fingerprint",
        }
        observed = {cast(str, case["expected_error"]) for case in cases}
        self.assertEqual(expected, observed)
        self.assertEqual(
            len(cases), len({cast(str, case["case_id"]) for case in cases})
        )

        schema = Draft202012Validator(self.artifact_schema)
        for case in cases:
            with self.subTest(case=case["case_id"]):
                mutated = apply_mutation(self.fixture, case)
                deterministic = cast(dict[str, Any], mutated["deterministic_evidence"])
                schema_errors = list(schema.iter_errors(mutated))
                self.assertTrue(
                    schema_errors
                    or fingerprint(deterministic) != mutated["evidence_fingerprint"]
                )

    def test_presentation_metadata_is_outside_deterministic_identity(self) -> None:
        updated = copy.deepcopy(self.fixture)
        updated["presentation"]["generated_at"] = "2026-08-22T00:00:00Z"
        self.assertEqual(
            self.fixture["evidence_fingerprint"], updated["evidence_fingerprint"]
        )
        self.assertEqual(
            self.fixture["deterministic_evidence"], updated["deterministic_evidence"]
        )


if __name__ == "__main__":
    unittest.main()
