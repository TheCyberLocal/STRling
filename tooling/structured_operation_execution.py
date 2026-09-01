"""Atomic, invocation-bound transport for structured repository operations."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Mapping, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "governance/schemas/structured-operation-execution.schema.json"
SCHEMA_VERSION = "structured-operation-execution-v1"
STATUS_EXIT_CODES = {
    "passed": 0,
    "waived": 0,
    "failed": 1,
    "unavailable": 2,
    "incomplete": 3,
}


class StructuredExecutionError(ValueError):
    """Raised when an execution artifact is absent, stale, or contradictory."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def document_fingerprint(value: Mapping[str, object]) -> str:
    payload = dict(value)
    payload.pop("artifact_fingerprint", None)
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _load_schema() -> dict[str, object]:
    try:
        value = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StructuredExecutionError(
            f"cannot load structured execution schema: {error}"
        ) from error
    if not isinstance(value, dict):
        raise StructuredExecutionError("structured execution schema must be an object")
    return cast(dict[str, object], value)


def validate_schema(value: Mapping[str, object]) -> None:
    schema = _load_schema()
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)
    except (SchemaError, ValidationError) as error:
        raise StructuredExecutionError(
            f"invalid structured execution artifact: {error.message}"
        ) from error
    if value.get("artifact_fingerprint") != document_fingerprint(value):
        raise StructuredExecutionError(
            "structured execution artifact fingerprint mismatch"
        )
    if value.get("artifact_kind") == "structured-operation-result":
        status = value.get("terminal_status")
        if value.get("process_exit_code") != STATUS_EXIT_CODES.get(str(status)):
            raise StructuredExecutionError(
                "structured terminal status and process exit code disagree"
            )
    consumption = value.get("sample_consumption")
    if isinstance(consumption, dict):
        completed_coordinates = consumption.get("completed_coordinate_ids")
        if isinstance(completed_coordinates, list) and consumption.get(
            "coordinates_completed"
        ) != len(completed_coordinates):
            raise StructuredExecutionError(
                "sample ledger coordinate count is not monotonic"
            )
        if consumption.get("state") == "consumed" and consumption.get(
            "authenticated_sample_count"
        ) != consumption.get("completed_sample_count"):
            raise StructuredExecutionError(
                "authenticated and completed sample counts disagree"
            )


def load_artifact(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StructuredExecutionError(
            f"cannot read structured execution artifact {path.name}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise StructuredExecutionError(
            f"structured execution artifact {path.name} must be an object"
        )
    artifact = cast(dict[str, object], value)
    validate_schema(artifact)
    return artifact


def atomic_write_artifact(path: Path, value: Mapping[str, object]) -> dict[str, object]:
    artifact = dict(value)
    artifact["artifact_fingerprint"] = document_fingerprint(artifact)
    validate_schema(artifact)
    if path.name == "result.json" and path.exists():
        raise StructuredExecutionError(
            "terminal structured execution artifact already exists"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(artifact, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        load_artifact(temporary)
        os.replace(temporary, path)
    except OSError as error:
        raise StructuredExecutionError(
            f"cannot atomically write structured execution artifact: {error}"
        ) from error
    return artifact


def atomic_write_stream(path: Path, value: str) -> dict[str, object]:
    if path.exists():
        raise StructuredExecutionError(
            f"structured execution stream already exists: {path.name}"
        )
    encoded = value.encode("utf-8")
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise StructuredExecutionError(
            f"cannot atomically preserve structured execution stream: {error}"
        ) from error
    return {
        "path": path.name,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "bytes": len(encoded),
    }


def execution_context(
    *,
    producer_id: str,
    operation_id: str,
    source_sha: str,
    invocation_id: str,
    certification_profile: str,
    producer_profile: str,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "producer_id": producer_id,
        "operation_id": operation_id,
        "source_sha": source_sha,
        "invocation_id": invocation_id,
        "certification_profile": certification_profile,
        "producer_profile": producer_profile,
    }


def zero_sample_consumption() -> dict[str, object]:
    return {
        "state": "zero",
        "authenticated_sample_count": 0,
        "completed_sample_count": 0,
        "coordinates_started": 0,
        "coordinates_completed": 0,
        "completed_coordinate_ids": [],
        "current_coordinate_id": None,
    }


def extract_environment_identity(
    structured_result: Mapping[str, object],
) -> dict[str, object] | None:
    identity: dict[str, object] = {}
    manifest = structured_result.get("manifest_fingerprint")
    if isinstance(manifest, str):
        identity["manifest_fingerprint"] = manifest
    checks = structured_result.get("checks")
    if isinstance(checks, list):
        for item in checks:
            if not isinstance(item, dict) or not isinstance(item.get("details"), dict):
                continue
            details = cast(dict[str, object], item["details"])
            if item.get("id") == "environment:fingerprinted-native-x86_64":
                for key in (
                    "baseline_fingerprint",
                    "observed_fingerprint",
                    "baseline_identity_fingerprint",
                    "observed_identity_fingerprint",
                ):
                    if isinstance(details.get(key), str):
                        identity[key] = details[key]
            elif item.get("id") == "environment:identical-conditioning":
                for key in (
                    "conditioning_identity_fingerprint",
                    "baseline_conditioning_identity_fingerprint",
                ):
                    if isinstance(details.get(key), str):
                        identity[key] = details[key]
            elif item.get("id") == "build:baseline-artifact-identity":
                observed = details.get("observed_artifacts")
                if isinstance(observed, dict):
                    identity["artifact_fingerprints"] = observed
    return identity or None


def authenticated_sample_count(structured_result: Mapping[str, object]) -> int:
    total = 0
    checks = structured_result.get("checks")
    if not isinstance(checks, list):
        return total
    for item in checks:
        if (
            not isinstance(item, dict)
            or not str(item.get("id", "")).startswith("measurement:")
            or not isinstance(item.get("details"), dict)
        ):
            continue
        samples = cast(dict[str, object], item["details"]).get("samples")
        if not isinstance(samples, list) or not all(
            isinstance(sample, int) and sample >= 0 for sample in samples
        ):
            raise StructuredExecutionError(
                "measurement evidence is missing an authenticated sample array"
            )
        total += len(samples)
    return total


def _validate_context(
    artifact: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    for key, value in expected.items():
        if artifact.get(key) != value:
            raise StructuredExecutionError(
                f"structured execution {key} mismatch: expected {value!r}, "
                f"observed {artifact.get(key)!r}"
            )


def _directory_entries(directory: Path) -> set[str]:
    try:
        return {entry.name for entry in directory.iterdir()}
    except OSError as error:
        raise StructuredExecutionError(
            f"cannot inspect structured execution directory: {error}"
        ) from error


def validate_result_directory(
    directory: Path,
    *,
    expected_context: Mapping[str, object],
    result_contract: str,
    actual_exit_code: int,
) -> dict[str, object]:
    entries = _directory_entries(directory)
    unexpected = entries.difference(
        {"progress.json", "result.json", "stdout.txt", "stderr.txt"}
    )
    if unexpected:
        raise StructuredExecutionError(
            "structured execution directory contains partial or conflicting "
            f"artifacts: {sorted(unexpected)}"
        )
    if "result.json" not in entries:
        raise StructuredExecutionError(
            "terminal structured execution artifact is missing"
        )
    artifact = load_artifact(directory / "result.json")
    if artifact.get("artifact_kind") != "structured-operation-result":
        raise StructuredExecutionError("terminal artifact has the wrong artifact kind")
    _validate_context(artifact, expected_context)
    if artifact.get("result_contract") != result_contract:
        raise StructuredExecutionError("structured result contract mismatch")
    terminal_status = artifact.get("terminal_status")
    expected_exit = STATUS_EXIT_CODES.get(str(terminal_status))
    if (
        actual_exit_code != expected_exit
        or artifact.get("process_exit_code") != actual_exit_code
    ):
        raise StructuredExecutionError(
            "actual process exit, structured process exit, and terminal status disagree"
        )
    structured = artifact.get("structured_result")
    if terminal_status == "incomplete":
        if structured is not None:
            raise StructuredExecutionError(
                "incomplete execution cannot expose a completed structured result"
            )
        return artifact
    if not isinstance(structured, dict):
        raise StructuredExecutionError(
            "terminal execution is missing structured evidence"
        )
    if structured.get("schema_version") != result_contract:
        raise StructuredExecutionError("embedded structured result schema mismatch")
    if structured.get("operation_id") != expected_context.get("operation_id"):
        raise StructuredExecutionError("embedded structured result operation mismatch")
    if structured.get("status") != terminal_status:
        raise StructuredExecutionError("embedded structured result status mismatch")
    if structured.get("commit") != expected_context.get("source_sha"):
        raise StructuredExecutionError("embedded structured result source SHA mismatch")
    if structured.get("profile") != expected_context.get("producer_profile"):
        raise StructuredExecutionError("embedded structured result profile mismatch")
    evidence_identity = structured.get("evidence_fingerprint")
    if artifact.get("performance_evidence_identity") != evidence_identity:
        raise StructuredExecutionError("performance evidence identity mismatch")
    if artifact.get("environment_identity") != extract_environment_identity(structured):
        raise StructuredExecutionError("performance environment identity mismatch")
    sample_count = authenticated_sample_count(structured)
    sample_consumption = artifact.get("sample_consumption")
    assert isinstance(sample_consumption, dict)
    if sample_count == 0:
        if (
            sample_consumption.get("state") != "zero"
            or sample_consumption.get("authenticated_sample_count") != 0
        ):
            raise StructuredExecutionError(
                "structured result omits authenticated samples consumed by the execution"
            )
    elif (
        sample_consumption.get("state") != "consumed"
        or sample_consumption.get("authenticated_sample_count") != sample_count
        or sample_consumption.get("completed_sample_count") != sample_count
    ):
        raise StructuredExecutionError(
            "structured sample count does not match authenticated measurement evidence"
        )
    return artifact


def recover_progress(
    directory: Path, *, expected_context: Mapping[str, object]
) -> dict[str, object] | None:
    path = directory / "progress.json"
    if not path.is_file():
        return None
    progress = load_artifact(path)
    if progress.get("artifact_kind") != "structured-operation-progress":
        raise StructuredExecutionError("progress artifact has the wrong artifact kind")
    _validate_context(progress, expected_context)
    return progress
