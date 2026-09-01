from __future__ import annotations

import copy
import json
import shutil
import unittest
import uuid
from pathlib import Path

from tooling.structured_operation_execution import (
    StructuredExecutionError,
    atomic_write_artifact,
    execution_context,
    validate_result_directory,
    zero_sample_consumption,
)


ROOT = Path(__file__).resolve().parents[2]


class StructuredOperationExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = (
            ROOT / "target/codex-tools/structured-operation-tests" / uuid.uuid4().hex
        )
        self.directory.mkdir(parents=True)
        self.context = execution_context(
            producer_id="performance_resource_full_certification@repository",
            operation_id="certification.performance-resource-full",
            source_sha="1" * 40,
            invocation_id="2" * 32,
            certification_profile="release",
            producer_profile="full",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)

    def _structured_result(
        self, *, status: str = "passed", samples: list[int] | None = None
    ) -> dict[str, object]:
        checks: list[dict[str, object]] = []
        if samples is not None:
            checks.append(
                {
                    "id": "measurement:latency:fixture/fixture:tiny",
                    "status": status,
                    "details": {"samples": samples},
                }
            )
        return {
            "schema_version": "certification-result-v1",
            "operation_id": self.context["operation_id"],
            "profile": "full",
            "status": status,
            "commit": self.context["source_sha"],
            "checks": checks,
            "manifest_fingerprint": "3" * 64,
            "evidence_fingerprint": "4" * 64,
        }

    def _sample_consumption(self, samples: list[int] | None) -> dict[str, object]:
        if not samples:
            return zero_sample_consumption()
        return {
            "state": "consumed",
            "authenticated_sample_count": len(samples),
            "completed_sample_count": len(samples),
            "coordinates_started": 1,
            "coordinates_completed": 1,
            "completed_coordinate_ids": ["latency:fixture/fixture:tiny"],
            "current_coordinate_id": None,
        }

    def _write_result(
        self,
        *,
        status: str = "passed",
        process_exit_code: int = 0,
        samples: list[int] | None = None,
        context_updates: dict[str, object] | None = None,
        result_updates: dict[str, object] | None = None,
        sample_consumption: dict[str, object] | None = None,
        artifact_updates: dict[str, object] | None = None,
    ) -> None:
        context = {**self.context, **(context_updates or {})}
        result = self._structured_result(status=status, samples=samples)
        result.update(result_updates or {})
        artifact = {
            **context,
            "artifact_kind": "structured-operation-result",
            "result_contract": "certification-result-v1",
            "process_exit_code": process_exit_code,
            "terminal_status": status,
            "environment_identity": {
                "manifest_fingerprint": result["manifest_fingerprint"]
            },
            "performance_evidence_identity": result["evidence_fingerprint"],
            "sample_consumption": sample_consumption
            or self._sample_consumption(samples),
            "structured_result": result,
            "integrity_error": None,
        }
        artifact.update(artifact_updates or {})
        atomic_write_artifact(
            self.directory / "result.json",
            artifact,
        )

    def _validate(self, *, actual_exit_code: int = 0) -> dict[str, object]:
        return validate_result_directory(
            self.directory,
            expected_context=self.context,
            result_contract="certification-result-v1",
            actual_exit_code=actual_exit_code,
        )

    def test_normal_success_and_failure_aggregate_with_exact_identity(self) -> None:
        self._write_result(samples=[10, 11, 12])
        self.assertEqual("passed", self._validate()["terminal_status"])

        failure_directory = self.directory / "failure"
        failure_directory.mkdir()
        original = self.directory
        self.directory = failure_directory
        try:
            self._write_result(status="failed", process_exit_code=1, samples=[20])
            self.assertEqual(
                "failed", self._validate(actual_exit_code=1)["terminal_status"]
            )
        finally:
            self.directory = original

    def test_identity_and_profile_mismatches_are_rejected(self) -> None:
        cases = {
            "wrong producer": {
                "context_updates": {"producer_id": "other_producer@repository"}
            },
            "wrong operation": {
                "context_updates": {"operation_id": "certification.other"}
            },
            "wrong source SHA": {"context_updates": {"source_sha": "5" * 40}},
            "wrong invocation": {"context_updates": {"invocation_id": "6" * 32}},
            "previous run": {"context_updates": {"invocation_id": "7" * 32}},
            "wrong profile": {"context_updates": {"certification_profile": "full"}},
            "wrong producer profile": {
                "context_updates": {"producer_profile": "pull-request"}
            },
        }
        for label, arguments in cases.items():
            with self.subTest(label=label):
                case_directory = self.directory / label.replace(" ", "-")
                case_directory.mkdir()
                original = self.directory
                self.directory = case_directory
                try:
                    self._write_result(**arguments)
                    with self.assertRaises(StructuredExecutionError):
                        self._validate()
                finally:
                    self.directory = original

    def test_process_status_and_structured_exit_disagreements_are_rejected(
        self,
    ) -> None:
        cases = (
            ("stale success after failed process", "passed", 0, 1),
            ("structured exit differs", "passed", 1, 1),
            ("success with nonzero exit", "passed", 0, 2),
            ("failure with zero exit", "failed", 1, 0),
        )
        for label, status, structured_exit, actual_exit in cases:
            with self.subTest(label=label):
                case_directory = self.directory / label.replace(" ", "-")
                case_directory.mkdir()
                original = self.directory
                self.directory = case_directory
                try:
                    if label == "structured exit differs":
                        payload = self._structured_result(status=status)
                        artifact = {
                            **self.context,
                            "artifact_kind": "structured-operation-result",
                            "result_contract": "certification-result-v1",
                            "process_exit_code": structured_exit,
                            "terminal_status": status,
                            "environment_identity": {
                                "manifest_fingerprint": payload["manifest_fingerprint"]
                            },
                            "performance_evidence_identity": payload[
                                "evidence_fingerprint"
                            ],
                            "sample_consumption": zero_sample_consumption(),
                            "structured_result": payload,
                            "integrity_error": None,
                        }
                        # The schema must reject the contradiction before aggregation.
                        with self.assertRaises(StructuredExecutionError):
                            atomic_write_artifact(
                                self.directory / "result.json", artifact
                            )
                        continue
                    self._write_result(status=status, process_exit_code=structured_exit)
                    with self.assertRaises(StructuredExecutionError):
                        self._validate(actual_exit_code=actual_exit)
                finally:
                    self.directory = original

    def test_truncated_partial_and_duplicate_artifacts_are_rejected(self) -> None:
        (self.directory / "result.json").write_text(
            '{"schema_version":', encoding="utf-8"
        )
        with self.assertRaisesRegex(StructuredExecutionError, "cannot read"):
            self._validate()

        partial_directory = self.directory / "partial"
        partial_directory.mkdir()
        original = self.directory
        self.directory = partial_directory
        try:
            self._write_result()
            (self.directory / "result.json.deadbeef.tmp").write_text(
                "partial", encoding="utf-8"
            )
            with self.assertRaisesRegex(StructuredExecutionError, "partial"):
                self._validate()
        finally:
            self.directory = original

        duplicate_directory = self.directory / "duplicate"
        duplicate_directory.mkdir()
        original = self.directory
        self.directory = duplicate_directory
        try:
            self._write_result()
            duplicate = copy.deepcopy(
                json.loads((self.directory / "result.json").read_text("utf-8"))
            )
            duplicate["terminal_status"] = "failed"
            (self.directory / "conflicting-result.json").write_text(
                json.dumps(duplicate), encoding="utf-8"
            )
            with self.assertRaisesRegex(StructuredExecutionError, "conflicting"):
                self._validate()
        finally:
            self.directory = original

    def test_sampled_result_without_authenticated_count_is_rejected(self) -> None:
        self._write_result(
            samples=[10, 11, 12], sample_consumption=zero_sample_consumption()
        )
        with self.assertRaisesRegex(StructuredExecutionError, "sample"):
            self._validate()

    def test_embedded_result_identity_status_and_evidence_are_rejected(self) -> None:
        cases = {
            "source": {"commit": "8" * 40},
            "operation": {"operation_id": "certification.other"},
            "profile": {"profile": "pull-request"},
            "status": {"status": "failed"},
            "evidence": {},
            "environment": {},
        }
        for label, updates in cases.items():
            with self.subTest(label=label):
                case_directory = self.directory / f"embedded-{label}"
                case_directory.mkdir()
                original = self.directory
                self.directory = case_directory
                try:
                    self._write_result(
                        result_updates=updates,
                        artifact_updates=(
                            {"performance_evidence_identity": "9" * 64}
                            if label == "evidence"
                            else (
                                {"environment_identity": None}
                                if label == "environment"
                                else None
                            )
                        ),
                    )
                    with self.assertRaises(StructuredExecutionError):
                        self._validate()
                finally:
                    self.directory = original


if __name__ == "__main__":
    unittest.main()
