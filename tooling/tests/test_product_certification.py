from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any, cast
from unittest import mock

from jsonschema import Draft202012Validator

from tooling.certification import (
    build_certification_artifact,
    profile_definition_fingerprint,
)
from tooling import audit_omega
from tooling.product_certification import (
    ProductCertificationError,
    aggregate_product_status,
    build_product_artifact,
    render_product_report,
    static_check,
    validate_product_artifact,
)


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
FIXTURE_REPOSITORY = {
    "commit": "1111111111111111111111111111111111111111",
    "dirty": False,
}


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
        contract_versions = cast(
            dict[str, dict[str, str]], self.manifest["result_contract_versions"]
        )

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
        release = cast(
            dict[str, Any], cast(dict[str, Any], policy["profiles"])["release"]
        )
        self.assertEqual(members, release["operations"])
        self.assertEqual(
            profile_definition_fingerprint(release),
            cast(dict[str, Any], self.manifest["release_profile"])[
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
            contract = producer["result_contract"]
            if isinstance(contract, str):
                version = cast(
                    dict[str, str],
                    producer.get("payload_version_override")
                    or contract_versions[contract],
                )
                self.assertIn(
                    version["field"], {"schema_version", "certification_version"}
                )
                self.assertTrue(version["value"])

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
        authority = cast(dict[str, Any], deterministic["authority"])
        source = cast(dict[str, Any], authority["source_profile"])
        self.assertEqual(
            fingerprint(deterministic["source_profile_evidence"]),
            source["evidence_fingerprint"],
        )
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


class ProductCertificationImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.toolchain = cast(dict[str, Any], load_json(ROOT / "toolchain.json"))
        cls.manifest = cast(dict[str, Any], load_json(MANIFEST_PATH))
        policy = cast(dict[str, Any], cls.toolchain["policy"])
        cls.profile = cast(
            dict[str, Any], cast(dict[str, Any], policy["profiles"])["full"]
        )
        cls.registry = cast(dict[str, dict[str, Any]], policy["operation_registry"])
        cls.profile_artifact = cls._build_profile_artifact("full")
        cls.product_artifact = build_product_artifact(
            root=ROOT,
            profile_artifact=cls.profile_artifact,
            manifest=cls.manifest,
            toolchain=cls.toolchain,
            resolved_repository_state=FIXTURE_REPOSITORY,
            generated_at="2026-08-21T00:00:00Z",
        )

    @classmethod
    def _build_profile_artifact(cls, profile_id: str) -> dict[str, object]:
        profile = cast(
            dict[str, Any],
            cast(
                dict[str, Any],
                cast(dict[str, Any], cls.toolchain["policy"])["profiles"],
            )[profile_id],
        )
        results: list[dict[str, object]] = []
        producers = {
            cast(str, producer["operation_id"]): producer
            for producer in cast(list[dict[str, Any]], cls.manifest["producers"])
        }
        contract_versions = cast(
            dict[str, dict[str, str]], cls.manifest["result_contract_versions"]
        )
        for member in cast(list[dict[str, Any]], profile["operations"]):
            operation_id = cast(str, member["operation"])
            definition = cls.registry[operation_id]
            components = (
                [cast(str, definition["component"])]
                if definition["kind"] == "repository"
                else cast(list[str], member["targets"])
            )
            for component in components:
                structured: dict[str, object] | None = None
                contract = definition.get("result_contract")
                if isinstance(contract, str):
                    producer = producers[operation_id]
                    version = cast(
                        dict[str, str],
                        producer.get("payload_version_override")
                        or contract_versions[contract],
                    )
                    structured = {
                        version["field"]: version["value"],
                        "operation_id": definition["result_operation_id"],
                        "status": "passed",
                        "duration_ms": 1,
                        "details": {"fixture": "product-certification"},
                    }
                results.append(
                    {
                        "operation": operation_id,
                        "component": component,
                        "status": "passed",
                        "command": ["fixture-command"],
                        "exit_code": 0,
                        "reason": None,
                        "capability": None,
                        "formatters": [],
                        "environment": [],
                        "structured_result": structured,
                    }
                )
        return build_certification_artifact(
            root=ROOT,
            profile_id=profile_id,
            profile_definition=profile,
            requested_component=None,
            results=results,
            aggregate_status="passed",
            exit_code=0,
            resolved_repository_state=FIXTURE_REPOSITORY,
            generated_at="2026-08-21T00:00:00Z",
        )

    def assert_rejected(self, artifact: dict[str, Any], code: str) -> None:
        with self.assertRaises(ProductCertificationError) as raised:
            validate_product_artifact(
                ROOT,
                artifact,
                manifest=self.manifest,
                toolchain=self.toolchain,
                resolved_repository_state=FIXTURE_REPOSITORY,
                enforce_current_repository=False,
            )
        self.assertEqual(code, raised.exception.code)

    def test_full_profile_merge_is_exact_and_repeatable(self) -> None:
        deterministic = cast(
            dict[str, Any], self.product_artifact["deterministic_evidence"]
        )
        coverage = cast(dict[str, Any], deterministic["coverage"])
        self.assertEqual(116, coverage["expected_result_count"])
        self.assertEqual(116, coverage["observed_result_count"])
        self.assertEqual(23, coverage["expected_structured_producer_count"])
        self.assertEqual(23, coverage["observed_structured_producer_count"])
        self.assertEqual(4, len(cast(list[object], deterministic["claims"])))
        self.assertEqual("passed", deterministic["aggregate"]["status"])

        evidence = {
            cast(str, result["operation_id"]): cast(
                dict[str, Any], result["producer_evidence"]
            )
            for result in cast(list[dict[str, Any]], deterministic["results"])
            if result["producer_evidence"] is not None
        }
        self.assertEqual(
            "1.0.0", evidence["security_dependency_integrity"]["schema_version"]
        )
        self.assertEqual("1.0.0", evidence["documentation_integrity"]["schema_version"])
        self.assertEqual(
            "1.0.0", evidence["pcre2_runtime_certification"]["schema_version"]
        )
        self.assertEqual(
            "certification-result-v1",
            evidence["product_certification_authority"]["schema_version"],
        )

        repeated = build_product_artifact(
            root=ROOT,
            profile_artifact=self.profile_artifact,
            manifest=self.manifest,
            toolchain=self.toolchain,
            resolved_repository_state=FIXTURE_REPOSITORY,
            generated_at="2026-08-21T00:00:00Z",
        )
        self.assertEqual(self.product_artifact, repeated)

    def test_release_profile_uses_the_same_closed_product_evidence(self) -> None:
        release = build_product_artifact(
            root=ROOT,
            profile_artifact=self._build_profile_artifact("release"),
            manifest=self.manifest,
            toolchain=self.toolchain,
            resolved_repository_state=FIXTURE_REPOSITORY,
            generated_at="2026-08-21T00:00:00Z",
        )
        deterministic = cast(dict[str, Any], release["deterministic_evidence"])
        authority = cast(dict[str, Any], deterministic["authority"])
        source = cast(dict[str, Any], authority["source_profile"])
        self.assertEqual("release", source["profile_id"])
        self.assertEqual(116, deterministic["coverage"]["observed_result_count"])
        self.assertEqual("passed", deterministic["aggregate"]["status"])

    def test_human_report_is_derived_only_from_the_machine_artifact(self) -> None:
        report = render_product_report(self.product_artifact)
        self.assertIn("# STRling Product Certification", report)
        self.assertIn("116/116 results", report)
        self.assertIn("23/23 structured producers", report)
        self.assertIn("`omega.essential-five-contract`", report)
        self.assertNotIn("stdout", report.casefold())
        self.assertNotIn("test name", report.casefold())

    def test_aggregate_precedence_is_fail_closed(self) -> None:
        self.assertEqual(
            "passed", aggregate_product_status(["passed", "not_applicable"])
        )
        self.assertEqual("waived", aggregate_product_status(["passed", "waived"]))
        self.assertEqual(
            "unavailable", aggregate_product_status(["waived", "unavailable"])
        )
        self.assertEqual(
            "incomplete", aggregate_product_status(["unavailable", "skipped"])
        )
        self.assertEqual("failed", aggregate_product_status(["incomplete", "failed"]))

    def test_static_authority_check_is_structured(self) -> None:
        result = static_check(ROOT)
        self.assertEqual("certification-result-v1", result["schema_version"])
        self.assertEqual("certification.product-authority", result["operation_id"])
        self.assertEqual("passed", result["status"])
        details = cast(dict[str, Any], result["details"])
        self.assertEqual(116, details["profile_result_count"])
        self.assertEqual(23, details["structured_producer_count"])
        self.assertEqual(0, details["prose_authority_inputs"])
        self.assertEqual(
            profile_definition_fingerprint(
                cast(
                    dict[str, Any],
                    cast(dict[str, Any], self.toolchain["policy"])["profiles"][
                        "release"
                    ],
                )
            ),
            details["release_profile_definition_fingerprint"],
        )

    def test_historical_omega_entrypoint_only_delegates(self) -> None:
        with mock.patch.object(
            audit_omega, "product_certification_main", return_value=0
        ) as delegated:
            self.assertEqual(0, audit_omega.main())
        delegated.assert_called_once_with(audit_omega.delegated_arguments())

        source = (ROOT / "tooling/audit_omega.py").read_text(encoding="utf-8")
        for forbidden in ("shell=True", "re.compile", "subprocess", "SKIP_PATTERNS"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_release_and_generated_report_authority_are_retired(self) -> None:
        registry = cast(
            dict[str, Any], load_json(ROOT / "governance/generated-artifacts.json")
        )
        historical = next(
            artifact
            for artifact in cast(list[dict[str, Any]], registry["artifacts"])
            if artifact["id"] == "final-audit-report"
        )
        self.assertEqual("transitional-compatibility-evidence", historical["authority"])
        self.assertIsNone(historical["generator"]["command"])
        self.assertEqual("not-enforced", historical["verification"]["method"])

        releasing = (ROOT / "docs/releasing.md").read_text(encoding="utf-8")
        self.assertIn("tooling/product_certification.py --run-profile", releasing)
        self.assertNotIn("Omega Audit", releasing)

    def test_duplicate_missing_and_unknown_results_are_rejected(self) -> None:
        duplicate = copy.deepcopy(self.product_artifact)
        duplicate["deterministic_evidence"]["results"].append(
            copy.deepcopy(duplicate["deterministic_evidence"]["results"][0])
        )
        self.assert_rejected(duplicate, "duplicate-result")

        missing = copy.deepcopy(self.product_artifact)
        missing["deterministic_evidence"]["results"].pop()
        self.assert_rejected(missing, "missing-result")

        unknown = copy.deepcopy(self.product_artifact)
        unknown["deterministic_evidence"]["results"][-1]["result_id"] = (
            "unknown_check@repository"
        )
        self.assert_rejected(unknown, "unknown-result")

    def test_stale_repository_and_profile_are_rejected(self) -> None:
        stale_repository = copy.deepcopy(self.product_artifact)
        stale_repository["deterministic_evidence"]["repository"]["commit"] = "9" * 40
        self.assert_rejected(stale_repository, "stale-repository")

        stale_profile = copy.deepcopy(self.product_artifact)
        stale_profile["deterministic_evidence"]["authority"]["source_profile"][
            "definition_fingerprint"
        ] = "9" * 64
        self.assert_rejected(stale_profile, "stale-profile")

    def test_conflicts_waivers_and_producer_tampering_are_rejected(self) -> None:
        conflicting = copy.deepcopy(self.product_artifact)
        conflicting["deterministic_evidence"]["results"][0]["status"] = "failed"
        self.assert_rejected(conflicting, "conflicting-result")

        invalid_waiver = copy.deepcopy(self.product_artifact)
        invalid_waiver["deterministic_evidence"]["results"][0]["status"] = "waived"
        invalid_waiver["deterministic_evidence"]["results"][0]["waiver_references"] = [
            "WVR-NOT-GOVERNED"
        ]
        self.assert_rejected(invalid_waiver, "invalid-waiver")

        producer_tamper = copy.deepcopy(self.product_artifact)
        structured = next(
            result
            for result in producer_tamper["deterministic_evidence"]["results"]
            if result["producer_evidence"] is not None
        )
        structured["producer_evidence"]["payload"]["details"]["fixture"] = "tampered"
        self.assert_rejected(producer_tamper, "producer-fingerprint")

    def test_aggregate_source_and_artifact_tampering_are_rejected(self) -> None:
        aggregate = copy.deepcopy(self.product_artifact)
        aggregate["deterministic_evidence"]["aggregate"]["counts"]["passed"] -= 1
        self.assert_rejected(aggregate, "aggregate-mismatch")

        source = copy.deepcopy(self.product_artifact)
        source["deterministic_evidence"]["source_profile_evidence"]["operations"][0][
            "reason"
        ] = "tampered"
        self.assert_rejected(source, "source-profile-fingerprint")

        artifact = copy.deepcopy(self.product_artifact)
        artifact["evidence_fingerprint"] = "0" * 64
        self.assert_rejected(artifact, "artifact-fingerprint")


if __name__ == "__main__":
    unittest.main()
