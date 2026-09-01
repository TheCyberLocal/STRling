from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tooling.certification import (
    CertificationError,
    build_certification_artifact,
    profile_definition_fingerprint,
    render_certification_summary,
    validate_certification_artifact,
    write_certification_artifact,
)


ROOT = Path(__file__).resolve().parents[2]


FIXTURES = ROOT / "tooling/tests/fixtures/certification"
PROFILE = {
    "definition_version": "1.0.0",
    "purpose": "Fixture certification profile.",
    "network_policy": "offline",
    "operations": [{"operation": "lint", "targets": ["repository"]}],
}
REPOSITORY_STATE = {"commit": "1" * 40, "dirty": False}


def result(
    status: str = "passed",
    operation: str = "lint",
    component: str = "repository",
    reason: str | None = None,
    structured_result: dict[str, object] | None = None,
    execution_integrity: dict[str, object] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "operation": operation,
        "component": component,
        "status": status,
        "command": ["fixture", "--check"] if status == "passed" else None,
        "exit_code": 0 if status == "passed" else None,
        "reason": reason,
        "capability": "enforced",
        "formatters": [],
        "environment": [],
    }
    if structured_result is not None:
        value["structured_result"] = structured_result
    if execution_integrity is not None:
        value["execution_integrity"] = execution_integrity
    return value


def build(
    results: list[dict[str, object]],
    status: str,
    exit_code: int,
    generated_at: str = "2026-08-11T12:00:00Z",
) -> dict[str, object]:
    return build_certification_artifact(
        root=ROOT,
        profile_id="local",
        profile_definition=PROFILE,
        requested_component=None,
        results=results,
        aggregate_status=status,
        exit_code=exit_code,
        resolved_repository_state=REPOSITORY_STATE,
        generated_at=generated_at,
    )


class CertificationArtifactTests(unittest.TestCase):
    def test_schema_and_positive_fixture_validate(self) -> None:
        schema = json.loads(
            (
                ROOT / "governance/schemas/profile-certification-artifact.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        fixture = json.loads((FIXTURES / "valid.json").read_text(encoding="utf-8"))
        validate_certification_artifact(ROOT, fixture)

    def test_invalid_fixture_is_rejected_mechanically(self) -> None:
        fixture = json.loads((FIXTURES / "invalid.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(
            CertificationError, "invalid certification artifact"
        ):
            validate_certification_artifact(ROOT, fixture)

    def test_artifact_preserves_exact_ordered_results_and_identity(self) -> None:
        results = [
            result(),
            result(
                status="unavailable",
                operation="test",
                component="swift",
                reason="required executable 'swift' was not found",
            ),
        ]
        artifact = build(results, "unavailable", 1)
        deterministic = artifact["deterministic_evidence"]
        assert isinstance(deterministic, dict)
        operations = deterministic["operations"]
        assert isinstance(operations, list)
        self.assertEqual(
            ["lint@repository", "test@swift"],
            [operation["result_id"] for operation in operations],
        )
        self.assertEqual(
            ["passed", "unavailable"],
            [operation["status"] for operation in operations],
        )
        aggregate = deterministic["aggregate"]
        assert isinstance(aggregate, dict)
        self.assertEqual(2, aggregate["operation_count"])
        self.assertEqual(1, aggregate["counts"]["passed"])
        self.assertEqual(1, aggregate["counts"]["unavailable"])
        profile = deterministic["profile"]
        assert isinstance(profile, dict)
        self.assertEqual(
            profile_definition_fingerprint(PROFILE),
            profile["definition_fingerprint"],
        )

    def test_aggregate_mismatch_cannot_be_artifacted(self) -> None:
        with self.assertRaisesRegex(
            CertificationError, "does not match the operation result set"
        ):
            build([result(status="failed", reason="fixture failed")], "passed", 0)

    def test_execution_metadata_does_not_change_evidence_identity(self) -> None:
        first = build([result()], "passed", 0, "2026-08-11T12:00:00Z")
        second = build([result()], "passed", 0, "2026-08-11T13:00:00Z")
        self.assertNotEqual(first["execution_metadata"], second["execution_metadata"])
        self.assertEqual(
            first["deterministic_evidence"], second["deterministic_evidence"]
        )
        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])

    def test_invocation_integrity_is_preserved_in_profile_evidence(self) -> None:
        execution_integrity = {
            "schema_version": "structured-operation-execution-v1",
            "invocation_id": "2" * 32,
            "source_sha": "1" * 40,
            "terminal_status": "passed",
            "process_exit_code": 0,
        }
        artifact = build([result(execution_integrity=execution_integrity)], "passed", 0)
        validate_certification_artifact(ROOT, artifact)
        operation = artifact["deterministic_evidence"]["operations"][0]
        self.assertEqual(execution_integrity, operation["execution_integrity"])

    def test_tampered_deterministic_evidence_is_rejected(self) -> None:
        artifact = build([result()], "passed", 0)
        tampered = copy.deepcopy(artifact)
        tampered["deterministic_evidence"]["repository"]["dirty"] = True
        with self.assertRaisesRegex(CertificationError, "fingerprint mismatch"):
            validate_certification_artifact(ROOT, tampered)

    def test_rehashed_inconsistent_aggregate_is_rejected(self) -> None:
        artifact = build([result()], "passed", 0)
        tampered = copy.deepcopy(artifact)
        deterministic = tampered["deterministic_evidence"]
        deterministic["aggregate"]["counts"]["passed"] = 0
        tampered["evidence_fingerprint"] = hashlib.sha256(
            json.dumps(
                deterministic,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        with self.assertRaisesRegex(CertificationError, "aggregate evidence mismatch"):
            validate_certification_artifact(ROOT, tampered)

    def test_summary_is_derived_from_all_result_categories(self) -> None:
        waived_evidence = {
            "checks": [
                {
                    "status": "waived",
                    "findings": [
                        {
                            "code": "FIXTURE-WAIVED",
                            "waiver_id": "WVR-SEC-TEST-001",
                        }
                    ],
                }
            ]
        }
        results = [
            result(),
            result(
                status="failed",
                operation="build",
                component="core",
                reason="command exited with status 1",
            ),
            result(
                status="waived",
                operation="security_dependency_risk",
                reason="governed finding is waived",
                structured_result=waived_evidence,
            ),
            result(
                status="unavailable",
                operation="test",
                component="swift",
                reason="Swift is unavailable",
            ),
        ]
        artifact = build(results, "failed", 1)
        summary = render_certification_summary(artifact)
        self.assertIn("STRling certification profile: local", summary)
        self.assertIn("Aggregate: FAILED", summary)
        self.assertIn("Passed operations: lint@repository", summary)
        self.assertIn("Failed operations: build@core", summary)
        self.assertIn("WVR-SEC-TEST-001", summary)
        self.assertIn("FIXTURE-WAIVED", summary)
        self.assertIn("test@swift", summary)
        self.assertIn("Resolve the failed operations", summary)

    def test_validated_artifact_round_trips_to_requested_path(self) -> None:
        artifact = build([result()], "passed", 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested/certification.json"
            write_certification_artifact(path, artifact)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(artifact, loaded)
            validate_certification_artifact(ROOT, loaded)


if __name__ == "__main__":
    unittest.main()
