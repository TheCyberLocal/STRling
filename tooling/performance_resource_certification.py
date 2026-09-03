"""Validate governed STRling performance and resource certification evidence."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import os
import platform
import random
import re
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence, cast

from jsonschema import Draft202012Validator

from tooling import performance_windows
from tooling.structured_operation_execution import (
    StructuredExecutionError,
    atomic_write_artifact,
    authenticated_sample_count,
    execution_context,
    extract_environment_identity,
    zero_sample_consumption,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "governance/schemas/performance-resource-certification.schema.json"
MANIFEST_PATH = ROOT / "tests/certification/performance-resource/1.0/manifest.json"
FIXTURE_MANIFEST_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/fixtures/fixture-manifest.json"
)
RESOURCE_INVENTORY_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/fixtures/resource-limits.json"
)
VALID_EVIDENCE_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/valid-evidence.json"
)
BASELINE_PATH = ROOT / "tests/certification/performance-resource/1.0/baseline.json"
PERFORMANCE_HISTORY_PATH = ROOT / "tests/certification/performance-resource/1.0/history"
RUNNER_MANIFEST_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/runner/Cargo.toml"
)

LINUX_TARGET = "x86_64-unknown-linux-gnu"
WINDOWS_TARGET = "x86_64-pc-windows-msvc"
WINDOWS_CANONICAL_BUILD_DRIVE = "P:"
MEASUREMENT_CONDITIONING_MAX_ATTEMPTS = 3
MEASUREMENT_CONDITIONING_RETRY_DELAY_SECONDS = 15
HOST_ATTESTATION_ENV = "STRLING_PERFORMANCE_HOST_ATTESTATION"
ALLOWED_CLOCKSOURCES = {"tsc", "hyperv_clocksource_tsc_page"}
WINDOWS_ENVIRONMENT_PATH = ROOT / "tooling/performance_windows.py"
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2, "incomplete": 3}
WINDOWS_EXTERNAL_WORKLOAD_PROCESS_NAMES = {
    "behavioral_realization",
    "cargo",
    "fortress",
    "rustc",
}

_KERNEL_ARTIFACT_SOURCE_PATHS = (
    "core/internal/Cargo.toml",
    "core/src",
    "spec/portability/equivalence/1.0",
    "spec/stdlib/registry/1.0",
    "spec/targets/profiles",
    "tests/conformance",
)
ARTIFACT_SOURCE_PATHS = {
    "kernel": (
        *_KERNEL_ARTIFACT_SOURCE_PATHS,
        "core/internal/Cargo.lock",
    ),
    "interop": (
        *_KERNEL_ARTIFACT_SOURCE_PATHS,
        "bindings/interop/Cargo.lock",
        "bindings/interop/Cargo.toml",
        "bindings/interop/src",
        "spec/interop/1.0",
    ),
    "runner": (
        *_KERNEL_ARTIFACT_SOURCE_PATHS,
        "Cargo.toml",
        "bindings/interop/Cargo.toml",
        "bindings/interop/src",
        "spec/interop/1.0",
        "tests/certification/performance-resource/1.0/runner/Cargo.lock",
        "tests/certification/performance-resource/1.0/runner/Cargo.toml",
        "tests/certification/performance-resource/1.0/runner/src",
    ),
}

PROFILE_IDS = ["local", "pull-request", "full"]
PROFILE_OPERATION_IDS = {
    "local": "certification.performance-resource-local",
    "pull-request": "certification.performance-resource-pull-request",
    "full": "certification.performance-resource-full",
}
FIXTURE_IDS = [
    "fixture:semantic-tiny",
    "fixture:semantic-common",
    "fixture:semantic-large",
    "fixture:semantic-pathological",
    "fixture:legacy-tiny",
    "fixture:legacy-common",
    "fixture:legacy-large",
    "fixture:simply-tiny",
    "fixture:simply-common",
    "fixture:simply-large",
    "fixture:protocol-common",
    "fixture:protocol-pathological",
]
PERFORMANCE_OPERATION_IDS = [
    "latency:semantic-parse",
    "latency:legacy-import",
    "latency:kernel-request",
    "latency:normalization",
    "latency:semantic-analysis",
    "latency:structural-safety",
    "latency:capability-portability",
    "latency:pcre2-lower-serialize",
    "latency:ecmascript-lower-serialize",
    "latency:python-re-lower-serialize",
    "latency:end-to-end",
    "latency:cli-startup",
    "latency:editor-interaction",
    "latency:interop-roundtrip",
    "latency:supported-host-overhead",
    "memory:kernel-peak-rss",
    "size:kernel-artifacts",
]
RESOURCE_OPERATION_IDS = [
    "resource:frontend-limits",
    "resource:kernel-limits",
    "resource:target-limits",
    "resource:editor-interop-limits",
    "resource:no-match-limits",
]
OPERATION_IDS = PERFORMANCE_OPERATION_IDS + RESOURCE_OPERATION_IDS
RESOURCE_TARGET_DIRECTORY = "target/rust-1.75-resource-certification"

RESOURCE_COMMANDS: dict[str, list[list[str]]] = {
    "resource:frontend-limits": [
        [
            "cargo",
            "+1.75.0",
            "test",
            "--manifest-path",
            "core/internal/Cargo.toml",
            "--locked",
            "--offline",
            "--test",
            "semantic_frontend",
            "--test",
            "semantic_frontend_properties",
            "--test",
            "regex_frontend",
        ]
    ],
    "resource:kernel-limits": [
        [
            "cargo",
            "+1.75.0",
            "test",
            "--manifest-path",
            "core/internal/Cargo.toml",
            "--locked",
            "--offline",
            "--test",
            "compiler_boundary_resources",
            "--test",
            "semantic_analysis",
            "--test",
            "structural_analysis",
            "--test",
            "safety_analysis",
            "--test",
            "capability_evaluation",
            "--test",
            "portability_planning",
        ]
    ],
    "resource:target-limits": [
        [
            "cargo",
            "+1.75.0",
            "test",
            "--manifest-path",
            "core/internal/Cargo.toml",
            "--locked",
            "--offline",
            "--test",
            "pcre2_lowering",
            "--test",
            "ecmascript_lowering",
            "--test",
            "python_re_lowering",
            "--test",
            "pcre2_serialization",
            "--test",
            "ecmascript_serialization",
            "--test",
            "python_re_serialization",
        ]
    ],
    "resource:editor-interop-limits": [
        [
            "cargo",
            "+1.75.0",
            "test",
            "--manifest-path",
            "core/internal/Cargo.toml",
            "--locked",
            "--offline",
            "--test",
            "editor_intelligence",
        ],
        [
            "cargo",
            "+1.75.0",
            "test",
            "--manifest-path",
            "bindings/interop/Cargo.toml",
            "--locked",
            "--offline",
            "--test",
            "protocol",
        ],
    ],
    "resource:no-match-limits": [
        [
            "cargo",
            "+1.75.0",
            "test",
            "--manifest-path",
            "core/internal/Cargo.toml",
            "--locked",
            "--offline",
            "--test",
            "no_match_explanation",
            "--test",
            "no_match_explanation_properties",
        ]
    ],
}


class PerformanceResourceError(ValueError):
    """A deterministic performance/resource contract failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _coordinate_id(key: tuple[str, str | None]) -> str:
    fixture = key[1] if key[1] is not None else "fixture-free"
    return f"{key[0]}/{fixture}"


class PerformanceExecutionLedger:
    """Persist monotonic sample-consumption state for one exact invocation."""

    def __init__(
        self,
        directory: Path,
        *,
        producer_id: str,
        operation_id: str,
        source_sha: str,
        invocation_id: str,
        certification_profile: str,
        producer_profile: str,
    ) -> None:
        if not directory.is_dir():
            raise PerformanceResourceError(
                "execution-artifact-directory",
                f"structured execution directory does not exist: {directory}",
            )
        try:
            entries = list(directory.iterdir())
        except OSError as error:
            raise PerformanceResourceError(
                "execution-artifact-directory", str(error)
            ) from error
        if entries:
            raise PerformanceResourceError(
                "stale-execution-artifact",
                "structured execution directory must be empty before producer start",
            )
        self.directory = directory
        self.context = execution_context(
            producer_id=producer_id,
            operation_id=operation_id,
            source_sha=source_sha,
            invocation_id=invocation_id,
            certification_profile=certification_profile,
            producer_profile=producer_profile,
        )
        self.sample_consumption = zero_sample_consumption()
        self._write_progress()

    def _write_progress(self) -> None:
        atomic_write_artifact(
            self.directory / "progress.json",
            {
                **self.context,
                "artifact_kind": "structured-operation-progress",
                "sample_consumption": copy.deepcopy(self.sample_consumption),
            },
        )

    def start_coordinate(self, key: tuple[str, str | None]) -> None:
        if self.sample_consumption["current_coordinate_id"] is not None:
            raise PerformanceResourceError(
                "sample-ledger-state", "a performance coordinate is already active"
            )
        coordinate = _coordinate_id(key)
        self.sample_consumption["state"] = "indeterminate"
        self.sample_consumption["authenticated_sample_count"] = None
        self.sample_consumption["coordinates_started"] = (
            cast(int, self.sample_consumption["coordinates_started"]) + 1
        )
        self.sample_consumption["current_coordinate_id"] = coordinate
        self._write_progress()

    def complete_coordinate(
        self, key: tuple[str, str | None], samples: Sequence[int]
    ) -> None:
        coordinate = _coordinate_id(key)
        if self.sample_consumption["current_coordinate_id"] != coordinate:
            raise PerformanceResourceError(
                "sample-ledger-state", "completed performance coordinate is not active"
            )
        if not samples:
            raise PerformanceResourceError(
                "sample-ledger-state", "completed performance coordinate has no samples"
            )
        completed_count = cast(
            int, self.sample_consumption["completed_sample_count"]
        ) + len(samples)
        completed = cast(list[str], self.sample_consumption["completed_coordinate_ids"])
        completed.append(coordinate)
        self.sample_consumption["state"] = "consumed"
        self.sample_consumption["authenticated_sample_count"] = completed_count
        self.sample_consumption["completed_sample_count"] = completed_count
        self.sample_consumption["coordinates_completed"] = (
            cast(int, self.sample_consumption["coordinates_completed"]) + 1
        )
        self.sample_consumption["current_coordinate_id"] = None
        self._write_progress()

    def write_result(
        self, result: Mapping[str, object], *, process_exit_code: int
    ) -> int:
        status = result.get("status")
        if not isinstance(status, str) or EXIT_CODES.get(status) != process_exit_code:
            return self.write_incomplete(
                code="producer-terminal-status",
                message="producer status and selected process exit code disagree",
            )
        observed_samples = authenticated_sample_count(result)
        recorded_samples = self.sample_consumption.get("authenticated_sample_count")
        if (
            self.sample_consumption.get("state") == "indeterminate"
            or observed_samples != recorded_samples
        ):
            return self.write_incomplete(
                code="sample-ledger-mismatch",
                message=(
                    "structured performance evidence does not authenticate the "
                    "sample-consumption ledger"
                ),
            )
        try:
            atomic_write_artifact(
                self.directory / "result.json",
                {
                    **self.context,
                    "artifact_kind": "structured-operation-result",
                    "result_contract": "certification-result-v1",
                    "process_exit_code": process_exit_code,
                    "terminal_status": status,
                    "environment_identity": extract_environment_identity(result),
                    "performance_evidence_identity": result.get("evidence_fingerprint"),
                    "sample_consumption": copy.deepcopy(self.sample_consumption),
                    "structured_result": dict(result),
                    "integrity_error": None,
                },
            )
        except StructuredExecutionError as error:
            raise PerformanceResourceError(
                "execution-artifact-write", str(error)
            ) from error
        return process_exit_code

    def write_incomplete(self, *, code: str, message: str) -> int:
        try:
            atomic_write_artifact(
                self.directory / "result.json",
                {
                    **self.context,
                    "artifact_kind": "structured-operation-result",
                    "result_contract": "certification-result-v1",
                    "process_exit_code": EXIT_CODES["incomplete"],
                    "terminal_status": "incomplete",
                    "environment_identity": None,
                    "performance_evidence_identity": None,
                    "sample_consumption": copy.deepcopy(self.sample_consumption),
                    "structured_result": None,
                    "integrity_error": {"code": code, "message": message},
                },
            )
        except StructuredExecutionError as error:
            raise PerformanceResourceError(
                "execution-artifact-write", str(error)
            ) from error
        return EXIT_CODES["incomplete"]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PerformanceResourceError("invalid-json", f"{path} must be an object")
    return value


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def document_fingerprint(document: Mapping[str, object], field: str) -> str:
    payload = dict(document)
    payload.pop(field, None)
    return fingerprint(payload)


def serialized_json(document: Mapping[str, object]) -> str:
    return json.dumps(document, indent=4, ensure_ascii=False) + "\n"


def serialized_fingerprint(document: Mapping[str, object]) -> str:
    return hashlib.sha256(serialized_json(document).encode("utf-8")).hexdigest()


def _schema() -> dict[str, Any]:
    return load_json(SCHEMA_PATH)


def validate_schema(value: Mapping[str, object], *, label: str) -> None:
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        raise PerformanceResourceError("schema", f"{label}: {errors[0].message}")


def validate_definition(
    value: Mapping[str, object], *, definition: str, label: str
) -> None:
    schema = _schema()
    focused = {
        "$schema": schema["$schema"],
        "$ref": f"#/$defs/{definition}",
        "$defs": schema["$defs"],
    }
    errors = sorted(
        Draft202012Validator(focused).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        raise PerformanceResourceError("schema", f"{label}: {errors[0].message}")


def _unique_ids(rows: Sequence[Mapping[str, object]], *, label: str) -> list[str]:
    ids = [cast(str, row["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise PerformanceResourceError("duplicate-id", f"{label} IDs must be unique")
    return ids


def _normalized_expression(value: str) -> str:
    return re.sub(r"[\s_]", "", value)


def validate_resource_inventory(
    inventory: Mapping[str, object], *, root: Path = ROOT
) -> None:
    validate_schema(inventory, label="resource inventory")
    if inventory["inventory_fingerprint"] != document_fingerprint(
        inventory, "inventory_fingerprint"
    ):
        raise PerformanceResourceError(
            "inventory-fingerprint", "resource inventory fingerprint changed"
        )
    rows = cast(list[dict[str, Any]], inventory["families"])
    if _unique_ids(rows, label="resource family") != [
        "resource-family:semantic-frontend",
        "resource-family:legacy-frontend",
        "resource-family:kernel-contract",
        "resource-family:analysis",
        "resource-family:target-lowering",
        "resource-family:target-serialization",
        "resource-family:editor",
        "resource-family:interop",
        "resource-family:no-match-explanation",
    ]:
        raise PerformanceResourceError(
            "resource-denominator", "resource family denominator changed"
        )
    declaration_count = 0
    for row in rows:
        for source_row in row["sources"]:
            source_path = root / source_row["path"]
            if not source_path.is_file():
                raise PerformanceResourceError(
                    "missing-source", f"missing resource source {source_row['path']}"
                )
            source = source_path.read_text(encoding="utf-8")
            for declaration in source_row["declarations"]:
                declaration_count += 1
                name = declaration["name"]
                match = re.search(
                    rf"(?:pub\s+)?const\s+{re.escape(name)}\s*:[^=]+=(.*?);",
                    source,
                    re.DOTALL,
                )
                if match is None or _normalized_expression(match.group(1)) != (
                    _normalized_expression(declaration["expression"])
                ):
                    raise PerformanceResourceError(
                        "stale-resource",
                        f"resource declaration changed for {source_row['path']}::{name}",
                    )
        for test_source in row["test_sources"]:
            test_path = root / test_source["path"]
            if not test_path.is_file():
                raise PerformanceResourceError(
                    "missing-test", f"missing resource test {test_source['path']}"
                )
            if file_fingerprint(test_path) != test_source["sha256"]:
                raise PerformanceResourceError(
                    "stale-test", f"resource test changed for {test_source['path']}"
                )
    if declaration_count != inventory["declaration_count"]:
        raise PerformanceResourceError(
            "resource-denominator", "resource declaration count changed"
        )


def validate_fixture_manifest(fixtures: Mapping[str, object]) -> None:
    validate_schema(fixtures, label="fixture manifest")
    if fixtures["fixture_manifest_fingerprint"] != document_fingerprint(
        fixtures, "fixture_manifest_fingerprint"
    ):
        raise PerformanceResourceError(
            "fixture-fingerprint", "fixture manifest fingerprint changed"
        )
    rows = cast(list[dict[str, Any]], fixtures["fixtures"])
    if _unique_ids(rows, label="fixture") != FIXTURE_IDS:
        raise PerformanceResourceError("fixture-denominator", "fixture set changed")
    classes = {row["class"] for row in rows}
    if classes != {"tiny", "common", "large", "pathological"}:
        raise PerformanceResourceError(
            "fixture-classes", "all four fixture classes are required"
        )
    for row in rows:
        if row["payload_fingerprint"] != fingerprint(row["payload"]):
            raise PerformanceResourceError(
                "fixture-payload", f"fixture payload changed for {row['id']}"
            )


def validate_manifest(
    manifest: Mapping[str, object],
    *,
    root: Path = ROOT,
    fixtures: Mapping[str, object] | None = None,
    inventory: Mapping[str, object] | None = None,
    verify_source_files: bool = True,
) -> None:
    validate_schema(manifest, label="manifest")
    fixtures = fixtures or load_json(root / manifest["fixture_manifest"]["path"])
    inventory = inventory or load_json(root / manifest["resource_inventory"]["path"])
    validate_fixture_manifest(fixtures)
    validate_resource_inventory(inventory, root=root)
    if verify_source_files and (
        file_fingerprint(root / manifest["fixture_manifest"]["path"])
        != manifest["fixture_manifest"]["sha256"]
    ):
        raise PerformanceResourceError(
            "stale-fixture-manifest", "fixture manifest source changed"
        )
    if verify_source_files and (
        file_fingerprint(root / manifest["resource_inventory"]["path"])
        != manifest["resource_inventory"]["sha256"]
    ):
        raise PerformanceResourceError(
            "stale-resource-inventory", "resource inventory source changed"
        )
    if manifest["manifest_fingerprint"] != document_fingerprint(
        manifest, "manifest_fingerprint"
    ):
        raise PerformanceResourceError(
            "manifest-fingerprint", "manifest fingerprint changed"
        )
    operations = cast(list[dict[str, Any]], manifest["operations"])
    if _unique_ids(operations, label="operation") != OPERATION_IDS:
        raise PerformanceResourceError(
            "operation-denominator", "operation denominator changed"
        )
    fixture_ids = set(FIXTURE_IDS)
    performance_states: set[str] = set()
    for operation in operations:
        if not set(operation["fixture_ids"]).issubset(fixture_ids):
            raise PerformanceResourceError(
                "fixture-reference", f"unknown fixture for {operation['id']}"
            )
        is_resource = operation["id"] in RESOURCE_OPERATION_IDS
        if is_resource:
            expected_state = "active"
            expected_budget_state = "not-applicable"
        else:
            expected_state = operation["state"]
            performance_states.add(expected_state)
            expected_budget_state = expected_state
        if expected_state not in {"planned", "active"}:
            raise PerformanceResourceError(
                "operation-state", f"unexpected state for {operation['id']}"
            )
        if is_resource and operation["state"] != expected_state:
            raise PerformanceResourceError(
                "operation-state", f"unexpected state for {operation['id']}"
            )
        if operation["budget"]["state"] != expected_budget_state:
            raise PerformanceResourceError(
                "budget-state", f"unexpected budget state for {operation['id']}"
            )
        if not is_resource and expected_state == "active":
            if (
                operation["budget"]["relative_regression_basis_points"] is None
                or operation["budget"]["absolute_ceiling"] is None
            ):
                raise PerformanceResourceError(
                    "active-budget",
                    f"active budget is incomplete for {operation['id']}",
                )
    if len(performance_states) != 1:
        raise PerformanceResourceError(
            "partial-activation", "performance operations must activate atomically"
        )
    partitions = cast(list[dict[str, Any]], manifest["profile_partitions"])
    if [row["id"] for row in partitions] != PROFILE_IDS:
        raise PerformanceResourceError(
            "profile-partition", "profile partition order changed"
        )
    by_profile = {row["id"]: row for row in partitions}
    if by_profile["local"]["operation_ids"]:
        raise PerformanceResourceError(
            "profile-partition", "Local must be contract-only"
        )
    if by_profile["pull-request"]["operation_ids"] != RESOURCE_OPERATION_IDS:
        raise PerformanceResourceError(
            "profile-partition", "Pull Request resource denominator changed"
        )
    if by_profile["full"]["operation_ids"] != OPERATION_IDS:
        raise PerformanceResourceError(
            "profile-partition", "Full operation denominator changed"
        )
    policy = manifest["measurement_policy"]
    if (
        policy["warmup_iterations"] != 16
        or policy["sample_iterations"] != 64
        or policy["baseline_repetitions"] != 5
        or policy["minimum_sample_duration_nanoseconds"] != 1_000_000
        or policy["batch_duration_safety_factor"] != 2
        or policy["maximum_batch_iterations"] != 4096
        or policy["order_seed"] != 1804
        or not policy["single_worker"]
        or policy["cpu_affinity_policy"] != "single-fixed-logical-cpu"
        or policy["selected_logical_cpu"] != 20
        or policy["host_reservation_policy"]
        != "authenticated-native-placement-or-host-pinned-reservation"
        or policy["execution_resource_policy"] != "platform-native-single-cpu-effective"
        or policy["cpu_quota_policy"] != "unlimited"
        or policy["conditioning_policy"]
        != "authenticated-identical-before-each-repetition"
        or not policy["randomize_operation_order"]
        or policy["statistics"] != ["median", "p95", "mad"]
    ):
        raise PerformanceResourceError(
            "measurement-policy", "measurement and noise policy changed"
        )


def percentile_nearest_rank(samples: Sequence[int], percentile: int) -> int:
    if not samples:
        raise PerformanceResourceError("empty-samples", "samples cannot be empty")
    ordered = sorted(samples)
    rank = max(1, math.ceil(percentile * len(ordered) / 100))
    return ordered[rank - 1]


def sample_statistics(samples: Sequence[int]) -> dict[str, int]:
    if not samples:
        raise PerformanceResourceError("empty-samples", "samples cannot be empty")
    median = int(statistics.median(samples))
    deviations = [abs(sample - median) for sample in samples]
    return {
        "sample_count": len(samples),
        "median": median,
        "p95": percentile_nearest_rank(samples, 95),
        "mad": int(statistics.median(deviations)),
        "minimum": min(samples),
        "maximum": max(samples),
    }


def derived_relative_budget_basis_points(
    *, median: int, mad: int, floor: int = 1000, maximum: int = 4000
) -> int:
    if median <= 0 or mad < 0:
        raise PerformanceResourceError("invalid-statistic", "median/MAD is invalid")
    derived = max(floor, math.ceil((6 * mad * 10_000) / median))
    if derived > maximum:
        raise PerformanceResourceError(
            "unstable-baseline", "variance exceeds the hard-metric budget ceiling"
        )
    return derived


def environments_compatible(
    baseline: Mapping[str, object], observed: Mapping[str, object]
) -> bool:
    return environment_identity(baseline) == environment_identity(observed)


def environment_identity(environment: Mapping[str, object]) -> dict[str, object]:
    """Project diagnostic wrapper ancestry out of governed Windows controls."""

    identity = copy.deepcopy(dict(environment))
    if identity.get("os") != "windows":
        return identity
    execution = cast(dict[str, Any], identity["execution_resource"])
    quota = cast(dict[str, Any], execution["cpu_quota"])
    quota.pop("in_job", None)
    attestation = cast(dict[str, Any], identity["host_attestation"])
    evidence = cast(dict[str, Any], attestation["reservation_evidence"])
    evidence_quota = cast(dict[str, Any], evidence["cpu_quota"])
    evidence_quota.pop("in_job", None)
    reservation = cast(dict[str, Any], attestation["reservation"])
    reservation["evidence_sha256"] = fingerprint(evidence)
    attestation["attestation_fingerprint"] = document_fingerprint(
        attestation, "attestation_fingerprint"
    )
    identity["host_attestation_fingerprint"] = attestation["attestation_fingerprint"]
    return identity


def environment_identity_fingerprint(environment: Mapping[str, object]) -> str:
    return fingerprint(environment_identity(environment))


def environment_mismatches(
    baseline: Mapping[str, object], observed: Mapping[str, object]
) -> list[dict[str, object]]:
    """Return deterministic leaf coordinates for an exact environment mismatch."""

    mismatches: list[dict[str, object]] = []

    def compare(expected: object, actual: object, path: str) -> None:
        if isinstance(expected, Mapping) and isinstance(actual, Mapping):
            keys = sorted(set(expected) | set(actual))
            for key in keys:
                coordinate = f"{path}.{key}" if path else str(key)
                if key not in expected:
                    mismatches.append(
                        {
                            "coordinate": coordinate,
                            "baseline": None,
                            "observed": actual[key],
                        }
                    )
                elif key not in actual:
                    mismatches.append(
                        {
                            "coordinate": coordinate,
                            "baseline": expected[key],
                            "observed": None,
                        }
                    )
                else:
                    compare(expected[key], actual[key], coordinate)
            return
        if isinstance(expected, list) and isinstance(actual, list):
            if expected != actual:
                mismatches.append(
                    {"coordinate": path, "baseline": expected, "observed": actual}
                )
            return
        if expected != actual:
            mismatches.append(
                {"coordinate": path, "baseline": expected, "observed": actual}
            )

    compare(baseline, observed, "")
    return mismatches


def conditioning_identity_fingerprint(snapshot: Mapping[str, object]) -> str:
    """Return the stable conditioning identity, excluding raw noise observations."""

    value = snapshot.get("conditioning_identity_fingerprint")
    if isinstance(value, str):
        return value
    return cast(str, snapshot["snapshot_fingerprint"])


def conditioning_identities_match(
    snapshots: Sequence[Mapping[str, object]],
) -> bool:
    return bool(snapshots) and all(
        conditioning_identity_fingerprint(snapshot)
        == conditioning_identity_fingerprint(snapshots[0])
        for snapshot in snapshots[1:]
    )


def conditioning_snapshots_compatible(
    baseline: Mapping[str, object], observed: Mapping[str, object]
) -> bool:
    if baseline.get("platform") != "windows" or observed.get("platform") != "windows":
        return conditioning_identity_fingerprint(
            baseline
        ) == conditioning_identity_fingerprint(observed)
    excluded = {
        "conditioning_identity_fingerprint",
        "host_attestation_fingerprint",
        "quiescence_observation",
        "snapshot_fingerprint",
    }
    baseline_controls = {
        key: copy.deepcopy(value)
        for key, value in baseline.items()
        if key not in excluded
    }
    observed_controls = {
        key: copy.deepcopy(value)
        for key, value in observed.items()
        if key not in excluded
    }
    return baseline_controls == observed_controls


def compare_hard_metric(
    *,
    baseline_median: int,
    observed_median: int,
    relative_regression_basis_points: int,
    absolute_ceiling: int | None,
) -> dict[str, object]:
    relative_ceiling = math.floor(
        baseline_median * (10_000 + relative_regression_basis_points) / 10_000
    )
    relative_passed = observed_median <= relative_ceiling
    absolute_passed = absolute_ceiling is None or observed_median <= absolute_ceiling
    return {
        "status": "passed" if relative_passed and absolute_passed else "failed",
        "baseline_median": baseline_median,
        "observed_median": observed_median,
        "relative_ceiling": relative_ceiling,
        "absolute_ceiling": absolute_ceiling,
        "relative_passed": relative_passed,
        "absolute_passed": absolute_passed,
    }


def certification_measurement_status(
    *, enforcement: str, comparison_status: str
) -> str:
    if enforcement == "hard":
        return comparison_status
    if enforcement == "informational":
        return "passed"
    raise PerformanceResourceError(
        "measurement-enforcement", f"unknown enforcement {enforcement}"
    )


def environment_fingerprint(environment: Mapping[str, object]) -> str:
    return fingerprint(environment)


def performance_measurement_keys(
    manifest: Mapping[str, object],
) -> list[tuple[str, str | None]]:
    keys: list[tuple[str, str | None]] = []
    for operation in cast(list[dict[str, Any]], manifest["operations"]):
        if operation["id"] not in PERFORMANCE_OPERATION_IDS:
            continue
        fixtures = cast(list[str], operation["fixture_ids"])
        if fixtures:
            keys.extend((operation["id"], fixture) for fixture in fixtures)
        else:
            keys.append((operation["id"], None))
    return keys


def _expected_repetition_sample_count(
    operation: Mapping[str, object], manifest: Mapping[str, object]
) -> int:
    if operation["measurement_kind"] == "latency":
        return cast(int, manifest["measurement_policy"]["sample_iterations"])
    return 1


def validate_baseline(
    baseline: Mapping[str, object],
    *,
    manifest: Mapping[str, object],
    synthetic: bool = False,
) -> None:
    validate_schema(baseline, label="baseline")
    if baseline["manifest_fingerprint"] != manifest["manifest_fingerprint"]:
        raise PerformanceResourceError(
            "stale-manifest", "baseline manifest fingerprint changed"
        )
    fixtures = load_json(ROOT / manifest["fixture_manifest"]["path"])
    if (
        baseline["fixture_manifest_fingerprint"]
        != fixtures["fixture_manifest_fingerprint"]
    ):
        raise PerformanceResourceError(
            "stale-fixtures", "baseline fixture fingerprint changed"
        )
    if baseline["environment_fingerprint"] != environment_fingerprint(
        baseline["environment"]
    ):
        raise PerformanceResourceError(
            "environment-fingerprint", "baseline environment fingerprint changed"
        )
    if baseline["baseline_fingerprint"] != document_fingerprint(
        baseline, "baseline_fingerprint"
    ):
        raise PerformanceResourceError(
            "baseline-fingerprint", "baseline fingerprint changed"
        )
    if (
        baseline["update_command"]
        != manifest["measurement_policy"]["baseline_update_command"]
    ):
        raise PerformanceResourceError(
            "baseline-update", "baseline update command changed"
        )
    if baseline["baseline_state"] == "planned":
        if (
            baseline["measurements"]
            or baseline["artifact_fingerprints"]
            or baseline["conditioning_repetitions"]
        ):
            raise PerformanceResourceError(
                "planned-baseline",
                "planned baseline cannot contain measurement, artifact, or conditioning evidence",
            )
        return
    if baseline["source_commit"] == "0" * 40 and not synthetic:
        raise PerformanceResourceError(
            "baseline-source", "live baseline requires a real source commit"
        )
    if set(baseline["artifact_fingerprints"]) != {"runner", "kernel", "interop"}:
        raise PerformanceResourceError(
            "artifact-fingerprints", "active baseline artifact denominator changed"
        )
    conditioning_repetitions = baseline["conditioning_repetitions"]
    expected_repetitions = manifest["measurement_policy"]["baseline_repetitions"]
    if len(conditioning_repetitions) != expected_repetitions:
        raise PerformanceResourceError(
            "conditioning-repetitions", "conditioning repetition count changed"
        )
    for snapshot in conditioning_repetitions:
        if snapshot["snapshot_fingerprint"] != document_fingerprint(
            snapshot, "snapshot_fingerprint"
        ):
            raise PerformanceResourceError(
                "conditioning-fingerprint", "conditioning snapshot changed"
            )
        if (
            snapshot["host_attestation_fingerprint"]
            != baseline["environment"]["host_attestation_fingerprint"]
            or snapshot["conditioner_sha256"]
            != baseline["environment"]["host_attestation"]["conditioning"][
                "executable_sha256"
            ]
            or snapshot["selected_logical_cpu"]
            != baseline["environment"]["selected_logical_cpu"]
        ):
            raise PerformanceResourceError(
                "conditioning-environment",
                "conditioning snapshot does not match the baseline environment",
            )
    if not conditioning_identities_match(conditioning_repetitions):
        raise PerformanceResourceError(
            "conditioning-drift",
            "all five baseline repetitions require identical conditioning identity",
        )
    operations = {
        row["id"]: row for row in cast(list[dict[str, Any]], manifest["operations"])
    }
    seen: set[tuple[str, str | None]] = set()
    for measurement in baseline["measurements"]:
        key = (measurement["operation_id"], measurement["fixture_id"])
        if key in seen:
            raise PerformanceResourceError(
                "duplicate-measurement", f"duplicate baseline measurement {key}"
            )
        seen.add(key)
        operation = operations.get(measurement["operation_id"])
        if (
            operation is None
            or measurement["operation_id"] not in PERFORMANCE_OPERATION_IDS
        ):
            raise PerformanceResourceError(
                "baseline-operation", f"unknown performance operation {key[0]}"
            )
        expected_fixtures = operation["fixture_ids"]
        if expected_fixtures and measurement["fixture_id"] not in expected_fixtures:
            raise PerformanceResourceError(
                "baseline-fixture", f"fixture is not governed for {key[0]}"
            )
        if not expected_fixtures and measurement["fixture_id"] is not None:
            raise PerformanceResourceError(
                "baseline-fixture", f"fixture-free metric has a fixture for {key[0]}"
            )
        if (
            measurement["environment_fingerprint"]
            != baseline["environment_fingerprint"]
        ):
            raise PerformanceResourceError(
                "measurement-environment", f"measurement environment changed for {key}"
            )
        repetitions = measurement["repetitions"]
        expected_repetitions = manifest["measurement_policy"]["baseline_repetitions"]
        if len(repetitions) != expected_repetitions:
            raise PerformanceResourceError(
                "repetition-count", f"baseline repetition count changed for {key}"
            )
        expected_count = _expected_repetition_sample_count(operation, manifest)
        if any(len(repetition) != expected_count for repetition in repetitions):
            raise PerformanceResourceError(
                "sample-count", f"repetition sample count changed for {key}"
            )
        batch_iterations = measurement["batch_iterations"]
        maximum_batch_iterations = manifest["measurement_policy"][
            "maximum_batch_iterations"
        ]
        if not 1 <= batch_iterations <= maximum_batch_iterations:
            raise PerformanceResourceError(
                "batch-iterations", f"batch count is outside policy for {key}"
            )
        batch_duration_repetitions = measurement["batch_duration_repetitions"]
        if operation["measurement_kind"] == "latency":
            if (
                batch_duration_repetitions is None
                or len(batch_duration_repetitions) != expected_repetitions
                or any(
                    len(repetition) != expected_count
                    for repetition in batch_duration_repetitions
                )
            ):
                raise PerformanceResourceError(
                    "batch-duration-evidence",
                    f"batch duration evidence changed for {key}",
                )
            for normalized, elapsed in zip(repetitions, batch_duration_repetitions):
                expected_normalized = [
                    max(1, (value + (batch_iterations // 2)) // batch_iterations)
                    for value in elapsed
                ]
                if normalized != expected_normalized:
                    raise PerformanceResourceError(
                        "batch-normalization",
                        f"normalized batch evidence changed for {key}",
                    )
            minimum_duration = manifest["measurement_policy"][
                "minimum_sample_duration_nanoseconds"
            ]
            duration_medians = [
                sample_statistics(repetition)["median"]
                for repetition in batch_duration_repetitions
            ]
            if any(median < minimum_duration for median in duration_medians):
                raise PerformanceResourceError(
                    "batch-duration-minimum",
                    f"batch median is below the governed minimum for {key}; "
                    f"batch_iterations={batch_iterations}; "
                    f"repetition_medians={duration_medians}",
                )
        elif batch_iterations != 1 or batch_duration_repetitions is not None:
            raise PerformanceResourceError(
                "batch-nonlatency",
                f"non-latency measurement cannot claim batching for {key}",
            )
        samples = [
            sample_statistics(repetition)["median"] for repetition in repetitions
        ]
        if measurement["samples"] != samples:
            raise PerformanceResourceError(
                "representative-samples", f"representative samples changed for {key}"
            )
        if measurement["statistics"] != sample_statistics(samples):
            raise PerformanceResourceError(
                "stale-statistics", f"statistics changed for {key}"
            )
        statistics_row = measurement["statistics"]
        if statistics_row["median"] <= 0:
            raise PerformanceResourceError(
                "invalid-statistic", f"median must be positive for {key}"
            )
        relative_mad_basis_points = math.ceil(
            statistics_row["mad"] * 10_000 / statistics_row["median"]
        )
        if (
            relative_mad_basis_points
            > manifest["measurement_policy"]["maximum_relative_mad_basis_points"]
        ):
            raise PerformanceResourceError(
                "unstable-baseline", f"relative MAD is unstable for {key}"
            )
        budget = measurement["budget"]
        if budget["state"] != "active":
            raise PerformanceResourceError(
                "inactive-budget", f"active baseline requires a budget for {key}"
            )
        expected_budget = derived_relative_budget_basis_points(
            median=statistics_row["median"],
            mad=statistics_row["mad"],
            floor=manifest["measurement_policy"][
                "minimum_relative_budget_basis_points"
            ],
            maximum=manifest["measurement_policy"][
                "maximum_relative_budget_basis_points"
            ],
        )
        if budget["relative_regression_basis_points"] != expected_budget:
            raise PerformanceResourceError(
                "budget-derivation", f"relative budget changed for {key}"
            )
        if operation["enforcement"] == "hard" and budget["absolute_ceiling"] is None:
            raise PerformanceResourceError(
                "absolute-ceiling", f"hard metric lacks an absolute ceiling for {key}"
            )
    expected_keys = performance_measurement_keys(manifest)
    if seen != set(expected_keys):
        missing = sorted(set(expected_keys) - seen, key=str)
        extra = sorted(seen - set(expected_keys), key=str)
        raise PerformanceResourceError(
            "baseline-denominator",
            f"baseline measurement denominator changed; missing={missing}, extra={extra}",
        )
    for operation_id in PERFORMANCE_OPERATION_IDS:
        operation = operations[operation_id]
        if operation["state"] != "active":
            raise PerformanceResourceError(
                "inactive-operation", f"active baseline requires {operation_id}"
            )
        rows = [
            row
            for row in baseline["measurements"]
            if row["operation_id"] == operation_id
        ]
        summary_budget = operation["budget"]
        if summary_budget["relative_regression_basis_points"] != max(
            row["budget"]["relative_regression_basis_points"] for row in rows
        ) or summary_budget["absolute_ceiling"] != max(
            row["budget"]["absolute_ceiling"] for row in rows
        ):
            raise PerformanceResourceError(
                "manifest-budget",
                f"manifest budget summary changed for {operation_id}",
            )


def host_environment_stub() -> dict[str, object]:
    """Return non-authoritative host facts for diagnostics, never a baseline."""

    return {
        "os": platform.system().lower(),
        "os_version": platform.version(),
        "architecture": platform.machine().lower(),
        "cpu_model": platform.processor() or "unknown",
        "logical_cpu_count": 0,
        "memory_bytes": 0,
        "rustc_version": "unmeasured",
        "cargo_version": "unmeasured",
        "target_triple": "unmeasured",
        "build_profile": "unmeasured",
        "feature_set": [],
        "cpu_affinity_policy": "unmeasured",
        "selected_logical_cpu": -1,
        "effective_cpu_affinity": [],
        "effective_cpuset": "unmeasured",
    }


def aggregate_status(statuses: Sequence[str]) -> str:
    if "failed" in statuses:
        return "failed"
    if "unavailable" in statuses:
        return "unavailable"
    return "passed"


def _resolved_command(command: Sequence[str]) -> list[str]:
    values = list(command)
    overrides = {
        "cargo": os.environ.get("STRLING_PERFORMANCE_CARGO"),
        "rustc": os.environ.get("STRLING_PERFORMANCE_RUSTC"),
    }
    if values and overrides.get(values[0]):
        values[0] = cast(str, overrides[values[0]])
        if len(values) > 1 and values[1] == "+1.75.0":
            values.pop(1)
    return values


def _resolved_environment(
    command: Sequence[str], *, root: Path = ROOT
) -> dict[str, str]:
    environment = os.environ.copy()
    rustc = os.environ.get("STRLING_PERFORMANCE_RUSTC")
    if command and command[0] == "cargo":
        if rustc:
            environment["RUSTC"] = rustc
        environment.pop("RUSTFLAGS", None)
        flags = [f"--remap-path-prefix={root.absolute()}=C:/strling-source"]
        if platform.system().lower() == "windows":
            flags.extend(
                [
                    "-C",
                    "link-arg=/Brepro",
                    "-C",
                    "link-arg=/PDBALTPATH:%_PDB%",
                ]
            )
        environment["CARGO_ENCODED_RUSTFLAGS"] = "\x1f".join(flags)
        environment["CARGO_INCREMENTAL"] = "0"
    return environment


def _run_command(
    command: Sequence[str], *, root: Path = ROOT, timeout_seconds: int = 900
) -> tuple[str, dict[str, object]]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            _resolved_command(command),
            cwd=root,
            env=_resolved_environment(command, root=root),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as error:
        return "unavailable", {
            "command": _resolved_command(command),
            "reason": str(error),
            "return_code": None,
        }
    except subprocess.TimeoutExpired as error:
        return "failed", {
            "command": _resolved_command(command),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "reason": f"timed out after {error.timeout} seconds",
            "return_code": None,
        }
    output = completed.stdout + completed.stderr
    details: dict[str, object] = {
        "command": _resolved_command(command),
        "duration_ms": int((time.monotonic() - started) * 1000),
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "return_code": completed.returncode,
    }
    if completed.returncode != 0:
        details["output_tail"] = output[-4000:]
    return ("passed" if completed.returncode == 0 else "failed"), details


def _git_invocation(root: Path, *arguments: str) -> list[str]:
    command = ["git"]
    pointer = root / ".git"
    if platform.system().lower() == "windows" and pointer.is_file():
        match = re.fullmatch(
            r"gitdir:\s*/mnt/([A-Za-z])/(.+)",
            pointer.read_text(encoding="utf-8").strip(),
        )
        if match is not None:
            drive, tail = match.groups()
            command.extend(
                [
                    "--git-dir",
                    f"{drive.upper()}:/{tail}",
                    "--work-tree",
                    str(root),
                ]
            )
    return [*command, *arguments]


def _git_identity(root: Path = ROOT) -> tuple[str, bool]:
    commit = subprocess.run(
        _git_invocation(root, "rev-parse", "HEAD"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        _git_invocation(root, "status", "--porcelain", "--untracked-files=normal"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return commit, bool(status.strip())


def _release_artifacts(root: Path = ROOT) -> dict[str, object]:
    suffix = ".exe" if os.name == "nt" else ""
    runner = (
        root
        / "tests/certification/performance-resource/1.0/runner/target/release"
        / f"strling-performance-runner{suffix}"
    )
    kernel = root / "core/internal/target/release" / f"strling-kernel{suffix}"
    interop_root = root / "bindings/interop/target/release"
    library_names = (
        ["strling_interop.dll"]
        if os.name == "nt"
        else ["libstrling_interop.so", "libstrling_interop.dylib"]
    )
    interop = next(
        (
            interop_root / name
            for name in library_names
            if (interop_root / name).is_file()
        ),
        interop_root / library_names[0],
    )
    return {"runner": runner, "kernel": kernel, "interop": interop}


@contextmanager
def _canonical_build_root(root: Path) -> Iterator[Path]:
    if platform.system().lower() != "windows":
        yield root
        return
    canonical_root = Path(f"{WINDOWS_CANONICAL_BUILD_DRIVE}/")
    if root.drive.upper() == WINDOWS_CANONICAL_BUILD_DRIVE:
        yield root
        return
    if canonical_root.exists():
        raise PerformanceResourceError(
            "canonical-build-drive",
            f"{WINDOWS_CANONICAL_BUILD_DRIVE} is already in use",
        )
    try:
        mapped = subprocess.run(
            ["subst", WINDOWS_CANONICAL_BUILD_DRIVE, str(root.resolve())],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise PerformanceResourceError("canonical-build-drive", str(error)) from error
    if mapped.returncode != 0:
        reason = (mapped.stdout + mapped.stderr).strip() or "subst failed"
        raise PerformanceResourceError("canonical-build-drive", reason)
    try:
        yield canonical_root
    finally:
        try:
            removed = subprocess.run(
                ["subst", WINDOWS_CANONICAL_BUILD_DRIVE, "/D"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            raise PerformanceResourceError(
                "canonical-build-drive-cleanup", str(error)
            ) from error
        if removed.returncode != 0:
            reason = (removed.stdout + removed.stderr).strip() or "subst cleanup failed"
            raise PerformanceResourceError("canonical-build-drive-cleanup", reason)


def _build_release_artifacts(root: Path = ROOT) -> tuple[str, dict[str, object]]:
    commands = [
        [
            "cargo",
            "+1.75.0",
            "build",
            "--release",
            "--manifest-path",
            str(RUNNER_MANIFEST_PATH.relative_to(ROOT)),
            "--locked",
            "--offline",
        ],
        [
            "cargo",
            "+1.75.0",
            "build",
            "--release",
            "--manifest-path",
            "core/internal/Cargo.toml",
            "--locked",
            "--offline",
            "--bin",
            "strling-kernel",
        ],
        [
            "cargo",
            "+1.75.0",
            "build",
            "--release",
            "--manifest-path",
            "bindings/interop/Cargo.toml",
            "--locked",
            "--offline",
            "--lib",
        ],
    ]
    steps: list[dict[str, object]] = []
    statuses: list[str] = []
    try:
        with _canonical_build_root(root) as build_root:
            for command in commands:
                status, details = _run_command(
                    command, root=build_root, timeout_seconds=1800
                )
                statuses.append(status)
                steps.append({"status": status, **details})
                if status != "passed":
                    break
    except PerformanceResourceError as error:
        return "unavailable", {
            "steps": steps,
            "code": error.code,
            "reason": str(error),
        }
    artifacts = _release_artifacts(root)
    missing = [
        str(path) for path in artifacts.values() if not cast(Path, path).is_file()
    ]
    if not missing and aggregate_status(statuses) == "passed":
        artifact_details = {
            name: {
                "path": str(cast(Path, path).relative_to(root)).replace("\\", "/"),
                "sha256": file_fingerprint(cast(Path, path)),
                "bytes": cast(Path, path).stat().st_size,
            }
            for name, path in artifacts.items()
        }
        return "passed", {
            "steps": steps,
            "artifacts": artifact_details,
            "canonical_build_root": (
                f"{WINDOWS_CANONICAL_BUILD_DRIVE}/"
                if platform.system().lower() == "windows"
                else None
            ),
        }
    return aggregate_status(statuses or ["unavailable"]), {
        "steps": steps,
        "missing_artifacts": missing,
    }


def _capture(command: Sequence[str], *, root: Path = ROOT) -> str:
    try:
        return subprocess.run(
            _resolved_command(command),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise PerformanceResourceError("tool-unavailable", str(error)) from error


def _required_text(path: Path, *, code: str) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise PerformanceResourceError(code, f"{path}: {error}") from error
    if not value:
        raise PerformanceResourceError(code, f"{path} is empty")
    return value


def _optional_text(path: Path, *, default: str = "unknown") -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return default
    return value or default


def _parse_cpu_set(value: str, *, code: str) -> list[int]:
    cpus: list[int] = []
    for part in value.split(","):
        bounds = part.split("-")
        if len(bounds) not in {1, 2}:
            raise PerformanceResourceError(code, f"invalid CPU set {value}")
        try:
            start = int(bounds[0])
            end = int(bounds[-1])
        except ValueError as error:
            raise PerformanceResourceError(code, f"invalid CPU set {value}") from error
        if start < 0 or end < start:
            raise PerformanceResourceError(code, f"invalid CPU set {value}")
        cpus.extend(range(start, end + 1))
    return sorted(set(cpus))


def _cpuinfo_fields(selected_logical_cpu: int) -> dict[str, str]:
    cpuinfo = _required_text(Path("/proc/cpuinfo"), code="processor-identity")
    blocks = [block for block in cpuinfo.split("\n\n") if block.strip()]
    selected: dict[str, str] | None = None
    for block in blocks:
        fields = {
            key.strip(): value.strip()
            for line in block.splitlines()
            if ":" in line
            for key, value in [line.split(":", 1)]
        }
        if fields.get("processor") == str(selected_logical_cpu):
            selected = fields
            break
    if selected is None:
        raise PerformanceResourceError(
            "processor-identity",
            f"logical CPU {selected_logical_cpu} is absent from /proc/cpuinfo",
        )
    required = {
        "vendor_id": "vendor_id",
        "family": "cpu family",
        "model": "model",
        "stepping": "stepping",
        "microcode": "microcode",
        "model_name": "model name",
    }
    result = {
        name: selected.get(source, "unknown") for name, source in required.items()
    }
    if any(value == "unknown" for value in result.values()):
        raise PerformanceResourceError(
            "processor-identity", "selected processor identity is incomplete"
        )
    return result


def _selected_cpu_topology(selected_logical_cpu: int) -> dict[str, object]:
    cpu_root = Path(f"/sys/devices/system/cpu/cpu{selected_logical_cpu}")
    topology_root = cpu_root / "topology"
    online_value = _optional_text(cpu_root / "online", default="1")
    topology = {
        "logical_cpu": selected_logical_cpu,
        "online": online_value == "1",
        "package_id": _required_text(
            topology_root / "physical_package_id", code="processor-topology"
        ),
        "die_id": _optional_text(topology_root / "die_id"),
        "core_id": _required_text(topology_root / "core_id", code="processor-topology"),
        "core_type": _optional_text(topology_root / "core_type"),
        "thread_siblings": _required_text(
            topology_root / "thread_siblings_list", code="processor-topology"
        ),
    }
    if not topology["online"]:
        raise PerformanceResourceError(
            "processor-topology", f"logical CPU {selected_logical_cpu} is offline"
        )
    validate_definition(
        topology, definition="processorTopology", label="selected processor topology"
    )
    return topology


def _linux_execution_resource_identity(selected_logical_cpu: int) -> dict[str, object]:
    cgroup_path = None
    for line in _required_text(
        Path("/proc/self/cgroup"), code="cgroup-v2"
    ).splitlines():
        if line.startswith("0::"):
            cgroup_path = line[3:] or "/"
            break
    if cgroup_path is None or not Path("/sys/fs/cgroup/cgroup.controllers").is_file():
        raise PerformanceResourceError(
            "cgroup-v2", "governed certification requires a unified cgroup v2"
        )
    cgroup_root = Path("/sys/fs/cgroup").resolve()
    resource_root = (cgroup_root / cgroup_path.lstrip("/")).resolve()
    if resource_root != cgroup_root and cgroup_root not in resource_root.parents:
        raise PerformanceResourceError("cgroup-v2", "cgroup path escaped its mount")
    cpuset = _required_text(
        resource_root / "cpuset.cpus.effective", code="cgroup-cpuset"
    )
    if _parse_cpu_set(cpuset, code="cgroup-cpuset") != [selected_logical_cpu]:
        raise PerformanceResourceError(
            "cgroup-cpuset",
            f"effective cgroup cpuset {cpuset} is not logical CPU {selected_logical_cpu}",
        )
    cpu_max = " ".join(
        _required_text(resource_root / "cpu.max", code="cgroup-quota").split()
    )
    if not cpu_max.startswith("max "):
        raise PerformanceResourceError(
            "cgroup-quota", f"governed CPU quota must be unlimited, observed {cpu_max}"
        )
    clocksource = _required_text(
        Path("/sys/devices/system/clocksource/clocksource0/current_clocksource"),
        code="clocksource",
    )
    if clocksource not in ALLOWED_CLOCKSOURCES:
        raise PerformanceResourceError(
            "clocksource", f"unsupported governed clocksource {clocksource}"
        )
    execution = {
        "cgroup_version": 2,
        "cgroup_path": cgroup_path,
        "cgroup_cpuset_effective": cpuset,
        "cgroup_cpu_max": cpu_max,
        "clocksource": clocksource,
        "processor_topology": _selected_cpu_topology(selected_logical_cpu),
    }
    validate_definition(
        execution, definition="executionResource", label="execution resource"
    )
    return execution


def _execution_resource_identity(selected_logical_cpu: int) -> dict[str, object]:
    system = platform.system().lower()
    if system == "linux":
        return _linux_execution_resource_identity(selected_logical_cpu)
    if system == "windows":
        try:
            execution = performance_windows.execution_resource(selected_logical_cpu)
        except performance_windows.WindowsQualificationError as error:
            raise PerformanceResourceError(
                "windows-execution-resource", str(error)
            ) from error
        validate_definition(
            execution, definition="executionResource", label="execution resource"
        )
        return execution
    raise PerformanceResourceError(
        "environment-unavailable", f"unsupported native performance host {system}"
    )


def _verify_external_file(
    path: Path,
    *,
    label: str,
    expected_sha256: str | None = None,
    executable: bool = False,
    require_root_owned: bool = True,
) -> Path:
    if not path.is_absolute():
        raise PerformanceResourceError(label, f"{path} must be absolute")
    try:
        resolved = path.resolve(strict=True)
        details = resolved.stat()
    except OSError as error:
        raise PerformanceResourceError(label, f"{path}: {error}") from error
    if resolved != path:
        raise PerformanceResourceError(label, f"{path} must not be a symlink")
    if not stat.S_ISREG(details.st_mode):
        raise PerformanceResourceError(label, f"{path} must be a regular file")
    if require_root_owned and (
        details.st_uid != 0 or details.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        raise PerformanceResourceError(
            label, f"{path} must be root-owned and not group/other writable"
        )
    if executable and not details.st_mode & stat.S_IXUSR:
        raise PerformanceResourceError(label, f"{path} must be executable")
    if expected_sha256 is not None and file_fingerprint(path) != expected_sha256:
        raise PerformanceResourceError(label, f"{path} fingerprint changed")
    return resolved


def _windows_host_attestation(
    probe: Mapping[str, Any],
    *,
    selected_logical_cpu: int,
    root: Path = ROOT,
) -> dict[str, Any]:
    processor = cast(Mapping[str, Any], probe["processor_registry"])
    identifier = cast(str, processor["identifier"])
    signature = re.search(
        r"Family\s+(\d+)\s+Model\s+(\d+)\s+Stepping\s+(\d+)", identifier
    )
    if signature is None:
        raise PerformanceResourceError(
            "processor-identity",
            f"unrecognized Windows processor identifier {identifier}",
        )
    execution = cast(Mapping[str, Any], probe["execution_resource"])
    selected = cast(Mapping[str, Any], probe["selected_cpu_set"])
    implementation = root / WINDOWS_ENVIRONMENT_PATH.relative_to(ROOT)
    if not implementation.is_file():
        raise PerformanceResourceError(
            "windows-conditioner", f"missing governed conditioner {implementation}"
        )
    evidence: dict[str, Any] = {
        "selected_cpu_topology": dict(selected),
        "cpu_set_allocation_state": copy.deepcopy(
            execution["cpu_set_allocation_state"]
        ),
        "host_topology": copy.deepcopy(probe["host_cpu_sets"]),
        "processor_group_counts": list(probe["processor_group_counts"]),
        "process_affinity_mask": execution["process_affinity_mask"],
        "system_affinity_mask": execution["system_affinity_mask"],
        "process_default_cpu_set_ids": list(execution["process_default_cpu_set_ids"]),
        "process_power_policy": copy.deepcopy(execution["process_power_policy"]),
        "cpu_quota": copy.deepcopy(execution["cpu_quota"]),
        "timer": copy.deepcopy(execution["timer"]),
        "power": copy.deepcopy(probe["power"]),
        "firmware": copy.deepcopy(probe["firmware"]),
        "guest_indicators": list(probe["guest_indicators"]),
    }
    placement_identity = {
        "mechanism": "native-windows-supported-controls",
        "selected_logical_cpu": selected_logical_cpu,
        "selected_cpu_set_id": execution["selected_cpu_set_id"],
        "physical_core_identity": selected["physical_core_identity"],
        "cpu_set_allocation_state": execution["cpu_set_allocation_state"],
        "host_topology_sha256": fingerprint(probe["host_cpu_sets"]),
    }
    host_identity = {
        "firmware": probe["firmware"],
        "processor": processor,
        "host_topology": probe["host_cpu_sets"],
    }
    allocation_state = cast(Mapping[str, object], execution["cpu_set_allocation_state"])
    exclusive = bool(
        allocation_state["allocated"]
        and allocation_state["allocated_to_target_process"]
    )
    attestation: dict[str, Any] = {
        "schema_version": "1.0.0",
        "attestation_kind": "strling-performance-host-reservation",
        "environment_kind": "native-windows-bare-metal",
        "host_id_sha256": fingerprint(host_identity),
        "host_os": (
            f"{probe['os']['product_name']} {probe['os']['display_version']} "
            f"build {probe['os']['current_build']}.{probe['os']['ubr']}"
        ),
        "host_kernel_or_hypervisor": (
            f"Windows NT {probe['os']['native_version']} native host; "
            "firmware guest indicators absent"
        ),
        "host_processor": {
            "vendor_id": str(processor["vendor_id"]),
            "family": signature.group(1),
            "model": signature.group(2),
            "stepping": signature.group(3),
            "microcode": str(processor["microcode_update_revision"]),
            "model_name": str(processor["model_name"]).strip(),
            "processor_identifier": identifier,
            "guest_environment_detected": False,
            "logical_cpu_count": probe["logical_processor_count"],
            "physical_core_count": probe["physical_core_count"],
            "topology_sha256": fingerprint(probe["host_cpu_sets"]),
        },
        "reservation": {
            "mechanism": "native-windows-supported-controls",
            "reservation_id": f"windows-{fingerprint(placement_identity)[:24]}",
            "host_logical_processors": [selected_logical_cpu],
            "host_physical_core_identity": selected["physical_core_identity"],
            "cpu_quota": "unlimited",
            "process_affinity_enforced": True,
            "cpu_set_enforced": True,
            "exclusive": exclusive,
            "housekeeping_excluded": False,
            "unrelated_workloads_excluded": exclusive,
            "quiescence_required": True,
            "evidence_sha256": fingerprint(evidence),
        },
        "reservation_evidence": evidence,
        "conditioning": {
            "policy_id": performance_windows.POLICY_ID,
            "implementation_path": implementation.relative_to(root).as_posix(),
            "executable_sha256": file_fingerprint(implementation),
            "observation_milliseconds": performance_windows.OBSERVATION_MILLISECONDS,
            "maximum_selected_busy_basis_points": (
                performance_windows.MAXIMUM_SELECTED_BUSY_BASIS_POINTS
            ),
            "maximum_selected_interrupt_basis_points": (
                performance_windows.MAXIMUM_SELECTED_INTERRUPT_BASIS_POINTS
            ),
            "maximum_system_busy_basis_points": (
                performance_windows.MAXIMUM_SYSTEM_BUSY_BASIS_POINTS
            ),
        },
        "attestation_fingerprint": "0" * 64,
    }
    attestation["attestation_fingerprint"] = document_fingerprint(
        attestation, "attestation_fingerprint"
    )
    validate_schema(attestation, label="Windows host attestation")
    return attestation


def _load_host_attestation(
    *,
    require_root_owned: bool = True,
    selected_logical_cpu: int | None = None,
    root: Path = ROOT,
    windows_probe: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if platform.system().lower() == "windows":
        if selected_logical_cpu is None:
            raise PerformanceResourceError(
                "host-attestation", "Windows host attestation requires a selected CPU"
            )
        try:
            probe = (
                dict(windows_probe)
                if windows_probe is not None
                else performance_windows.stable_platform_probe(selected_logical_cpu)
            )
        except performance_windows.WindowsQualificationError as error:
            raise PerformanceResourceError("host-attestation", str(error)) from error
        return _windows_host_attestation(
            probe, selected_logical_cpu=selected_logical_cpu, root=root
        )
    raw_path = os.environ.get(HOST_ATTESTATION_ENV)
    if not raw_path:
        raise PerformanceResourceError(
            "host-attestation",
            f"{HOST_ATTESTATION_ENV} must name the privileged host attestation",
        )
    path = _verify_external_file(
        Path(raw_path), label="host-attestation", require_root_owned=require_root_owned
    )
    attestation = load_json(path)
    validate_schema(attestation, label="host attestation")
    if attestation["attestation_fingerprint"] != document_fingerprint(
        attestation, "attestation_fingerprint"
    ):
        raise PerformanceResourceError(
            "host-attestation-fingerprint", "host attestation fingerprint changed"
        )
    expected_mechanism = {
        "dedicated-bare-metal": "bare-metal-cpuset-isolation",
        "hypervisor-host-pinned": "hypervisor-host-pinned",
    }[attestation["environment_kind"]]
    if attestation["reservation"]["mechanism"] != expected_mechanism:
        raise PerformanceResourceError(
            "host-reservation", "host reservation mechanism is inconsistent"
        )
    if attestation["environment_kind"] != "dedicated-bare-metal":
        raise PerformanceResourceError(
            "unsupported-host-attestation",
            "hypervisor host binding requires an implemented host-side trust path",
        )
    reservation_evidence = attestation["reservation_evidence"]
    if attestation["reservation"]["evidence_sha256"] != fingerprint(
        reservation_evidence
    ):
        raise PerformanceResourceError(
            "host-reservation-evidence", "embedded reservation evidence changed"
        )
    conditioning = attestation["conditioning"]
    _verify_external_file(
        Path(conditioning["executable_path"]),
        label="conditioner",
        expected_sha256=conditioning["executable_sha256"],
        executable=True,
        require_root_owned=require_root_owned,
    )
    return attestation


def _toolchain_fingerprints(*, root: Path = ROOT) -> dict[str, str]:
    def governed_path(tool: str) -> Path:
        override = os.environ.get(f"STRLING_PERFORMANCE_{tool.upper()}")
        if override:
            resolved = shutil.which(override) or override
        else:
            resolved = _capture(
                ["rustup", "which", "--toolchain", "1.75.0", tool], root=root
            )
        path = Path(resolved).resolve()
        if not path.is_file():
            raise PerformanceResourceError(
                "toolchain-fingerprint", f"resolved {tool} is not a file: {path}"
            )
        return path

    fingerprints = {
        "python": file_fingerprint(Path(sys.executable).resolve()),
        "rustc": file_fingerprint(governed_path("rustc")),
        "cargo": file_fingerprint(governed_path("cargo")),
    }
    validate_definition(
        fingerprints,
        definition="toolchainFingerprints",
        label="toolchain fingerprints",
    )
    return fingerprints


def _execution_resource_cpuset(execution: Mapping[str, object]) -> str:
    if execution.get("platform") == "windows":
        topology = cast(Mapping[str, object], execution["processor_topology"])
        return (
            f"group-{execution['processor_group']}:logical-"
            f"{execution['selected_logical_processor']}:cpu-set-"
            f"{execution['selected_cpu_set_id']}:core-{topology['core_index']}:"
            f"efficiency-{topology['efficiency_class']}"
        )
    return cast(str, execution["cgroup_cpuset_effective"])


def _windows_conditioning_snapshot(
    environment: Mapping[str, object], *, root: Path = ROOT
) -> dict[str, Any]:
    attestation = cast(Mapping[str, Any], environment["host_attestation"])
    conditioning = cast(Mapping[str, Any], attestation["conditioning"])
    implementation = root / cast(str, conditioning["implementation_path"])
    if (
        not implementation.is_file()
        or file_fingerprint(implementation) != conditioning["executable_sha256"]
    ):
        raise PerformanceResourceError(
            "conditioning-fingerprint", "governed Windows conditioner changed"
        )
    command = [
        sys.executable,
        str(implementation),
        "condition",
        "--selected-logical-cpu",
        str(environment["selected_logical_cpu"]),
        "--expected-host-attestation",
        cast(str, environment["host_attestation_fingerprint"]),
        "--json",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=900,
        )
        report = json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        raise PerformanceResourceError("conditioning", str(error)) from error
    expected_keys = {
        "conditioning_version",
        "status",
        "policy_id",
        "host_attestation_fingerprint",
        "selected_logical_cpu",
        "conditioning_identity",
        "conditioning_identity_fingerprint",
        "observation",
        "report_fingerprint",
    }
    if not isinstance(report, dict) or set(report) != expected_keys:
        raise PerformanceResourceError(
            "conditioning", "Windows conditioner report changed"
        )
    if report["report_fingerprint"] != document_fingerprint(
        report, "report_fingerprint"
    ):
        raise PerformanceResourceError(
            "conditioning-fingerprint", "Windows conditioner report fingerprint changed"
        )
    identity = cast(Mapping[str, Any], report["conditioning_identity"])
    observation = cast(Mapping[str, Any], report["observation"])
    execution = cast(Mapping[str, Any], environment["execution_resource"])
    evidence = cast(Mapping[str, Any], attestation["reservation_evidence"])
    expected_limits = {
        "observation_milliseconds": conditioning["observation_milliseconds"],
        "maximum_selected_busy_basis_points": conditioning[
            "maximum_selected_busy_basis_points"
        ],
        "maximum_selected_interrupt_basis_points": conditioning[
            "maximum_selected_interrupt_basis_points"
        ],
        "maximum_system_busy_basis_points": conditioning[
            "maximum_system_busy_basis_points"
        ],
    }
    if (
        completed.returncode != 0
        or report["conditioning_version"] != performance_windows.CONDITIONING_VERSION
        or report["status"] != "passed"
        or report["policy_id"] != conditioning["policy_id"]
        or report["host_attestation_fingerprint"]
        != environment["host_attestation_fingerprint"]
        or report["selected_logical_cpu"] != environment["selected_logical_cpu"]
        or report["conditioning_identity_fingerprint"] != fingerprint(identity)
        or identity.get("policy_id") != conditioning["policy_id"]
        or identity.get("selected_logical_cpu") != environment["selected_logical_cpu"]
        or identity.get("execution_resource") != execution
        or identity.get("power") != evidence["power"]
        or identity.get("limits") != expected_limits
        or observation.get("failures") != []
    ):
        raise PerformanceResourceError(
            "conditioning",
            "native Windows host was not quiet under the governed conditioning policy",
        )
    live_execution = _execution_resource_identity(
        cast(int, environment["selected_logical_cpu"])
    )
    if live_execution != execution:
        raise PerformanceResourceError(
            "conditioning-drift",
            "Windows execution resource changed during conditioning",
        )
    snapshot: dict[str, Any] = {
        "status": "passed",
        "platform": "windows",
        "policy_id": conditioning["policy_id"],
        "host_attestation_fingerprint": environment["host_attestation_fingerprint"],
        "conditioner_sha256": conditioning["executable_sha256"],
        "selected_logical_cpu": environment["selected_logical_cpu"],
        "effective_cpu_affinity": list(execution["effective_cpu_affinity"]),
        "effective_cpuset": _execution_resource_cpuset(execution),
        "cpu_quota": execution["cpu_quota"]["effective_cpu_quota"],
        "timer_source": (
            f"{execution['timer']['source']}:{execution['timer']['frequency_hz']}"
        ),
        "process_power_policy": copy.deepcopy(execution["process_power_policy"]),
        "power_state": "ac-governed",
        "conditioning_identity_fingerprint": report[
            "conditioning_identity_fingerprint"
        ],
        "quiescence_observation": dict(observation),
        "snapshot_fingerprint": "0" * 64,
    }
    snapshot["snapshot_fingerprint"] = document_fingerprint(
        snapshot, "snapshot_fingerprint"
    )
    validate_definition(
        snapshot, definition="conditioningSnapshot", label="conditioning snapshot"
    )
    return snapshot


def _conditioning_snapshot(
    environment: Mapping[str, object], *, root: Path = ROOT
) -> dict[str, Any]:
    if environment["os"] == "windows":
        return _windows_conditioning_snapshot(environment, root=root)
    attestation = cast(Mapping[str, Any], environment["host_attestation"])
    conditioning = cast(Mapping[str, str], attestation["conditioning"])
    executable = _verify_external_file(
        Path(conditioning["executable_path"]),
        label="conditioner",
        expected_sha256=conditioning["executable_sha256"],
        executable=True,
    )
    try:
        conditioner_environment = os.environ.copy()
        conditioner_environment["STRLING_PERFORMANCE_SELECTED_LOGICAL_CPU"] = str(
            environment["selected_logical_cpu"]
        )
        conditioner_environment["STRLING_PERFORMANCE_EXPECTED_HOST_ATTESTATION"] = cast(
            str, environment["host_attestation_fingerprint"]
        )
        completed = subprocess.run(
            [str(executable), "--json"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
            env=conditioner_environment,
        )
        report = json.loads(completed.stdout)
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
    ) as error:
        raise PerformanceResourceError("conditioning", str(error)) from error
    expected_keys = {
        "conditioning_version",
        "status",
        "policy_id",
        "host_attestation_fingerprint",
        "selected_logical_cpu",
        "thermal_state",
        "power_state",
        "unrelated_workloads_excluded",
        "report_fingerprint",
    }
    if not isinstance(report, dict) or set(report) != expected_keys:
        raise PerformanceResourceError("conditioning", "conditioner report changed")
    if report["report_fingerprint"] != document_fingerprint(
        report, "report_fingerprint"
    ):
        raise PerformanceResourceError(
            "conditioning-fingerprint", "conditioner report fingerprint changed"
        )
    selected = cast(int, environment["selected_logical_cpu"])
    if (
        report["conditioning_version"] != "1.0.0"
        or report["status"] != "passed"
        or report["policy_id"] != conditioning["policy_id"]
        or report["host_attestation_fingerprint"]
        != environment["host_attestation_fingerprint"]
        or report["selected_logical_cpu"] != selected
        or report["thermal_state"] != "nominal"
        or report["power_state"] != "governed"
        or report["unrelated_workloads_excluded"] is not True
    ):
        raise PerformanceResourceError(
            "conditioning", "conditioner did not attest the governed state"
        )
    affinity = _effective_cpu_affinity()
    execution = _execution_resource_identity(selected)
    if (
        affinity != environment["effective_cpu_affinity"]
        or execution != environment["execution_resource"]
    ):
        raise PerformanceResourceError(
            "conditioning-drift", "execution resource changed during conditioning"
        )
    snapshot: dict[str, Any] = {
        "status": "passed",
        "policy_id": conditioning["policy_id"],
        "host_attestation_fingerprint": environment["host_attestation_fingerprint"],
        "conditioner_sha256": conditioning["executable_sha256"],
        "selected_logical_cpu": selected,
        "effective_cpu_affinity": affinity,
        "effective_cpuset": execution["cgroup_cpuset_effective"],
        "cgroup_cpu_max": execution["cgroup_cpu_max"],
        "clocksource": execution["clocksource"],
        "thermal_state": report["thermal_state"],
        "power_state": report["power_state"],
        "unrelated_workloads_excluded": report["unrelated_workloads_excluded"],
        "snapshot_fingerprint": "0" * 64,
    }
    snapshot["snapshot_fingerprint"] = document_fingerprint(
        snapshot, "snapshot_fingerprint"
    )
    validate_definition(
        snapshot, definition="conditioningSnapshot", label="conditioning snapshot"
    )
    return snapshot


def _format_cpu_set(cpus: Sequence[int]) -> str:
    ordered = sorted(set(cpus))
    if not ordered:
        raise PerformanceResourceError("cpu-affinity", "CPU affinity is empty")
    ranges: list[str] = []
    start = previous = ordered[0]
    for cpu in ordered[1:]:
        if cpu == previous + 1:
            previous = cpu
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = cpu
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(ranges)


def _effective_cpu_affinity() -> list[int]:
    system = platform.system().lower()
    if system == "windows":
        try:
            return cast(
                list[int],
                performance_windows.process_affinity()["effective_logical_processors"],
            )
        except performance_windows.WindowsQualificationError as error:
            raise PerformanceResourceError(
                "affinity-unavailable", str(error)
            ) from error
    if system != "linux" or not hasattr(os, "sched_getaffinity"):
        raise PerformanceResourceError(
            "affinity-unavailable",
            "governed CPU affinity requires native Linux or Windows controls",
        )
    try:
        return sorted(os.sched_getaffinity(0))
    except OSError as error:
        raise PerformanceResourceError("affinity-unavailable", str(error)) from error


def _enforce_governed_cpu_affinity(manifest: Mapping[str, object]) -> list[int]:
    policy = cast(Mapping[str, object], manifest["measurement_policy"])
    if policy.get("cpu_affinity_policy") != "single-fixed-logical-cpu":
        raise PerformanceResourceError(
            "affinity-policy", "single fixed logical CPU affinity is required"
        )
    selected = policy.get("selected_logical_cpu")
    if not isinstance(selected, int) or selected < 0:
        raise PerformanceResourceError(
            "affinity-policy", "selected logical CPU is invalid"
        )
    if platform.system().lower() == "windows":
        try:
            placement = performance_windows.enforce_current_process_placement(selected)
        except performance_windows.WindowsQualificationError as error:
            raise PerformanceResourceError("affinity-control", str(error)) from error
        effective = cast(list[int], placement["effective_logical_processors"])
        if effective != [selected]:
            raise PerformanceResourceError(
                "affinity-control", "Windows placement did not select exactly one CPU"
            )
        return effective
    available = _effective_cpu_affinity()
    if selected not in available:
        raise PerformanceResourceError(
            "affinity-unavailable",
            f"selected logical CPU {selected} is absent from effective affinity {_format_cpu_set(available)}",
        )
    try:
        os.sched_setaffinity(0, {selected})
    except (AttributeError, OSError) as error:
        raise PerformanceResourceError("affinity-control", str(error)) from error
    effective = _effective_cpu_affinity()
    if effective != [selected]:
        raise PerformanceResourceError(
            "affinity-control",
            f"effective affinity {_format_cpu_set(effective)} does not equal selected logical CPU {selected}",
        )
    return effective


def _windows_live_environment(
    *, selected_logical_cpu: int, root: Path = ROOT
) -> dict[str, object]:
    try:
        probe = performance_windows.stable_platform_probe(selected_logical_cpu)
    except performance_windows.WindowsQualificationError as error:
        raise PerformanceResourceError("environment-unavailable", str(error)) from error
    execution_resource = cast(dict[str, Any], probe["execution_resource"])
    effective_cpu_affinity = cast(
        list[int], execution_resource["effective_cpu_affinity"]
    )
    if effective_cpu_affinity != [selected_logical_cpu]:
        raise PerformanceResourceError(
            "affinity-control",
            "Windows environment was not constrained to the selected logical processor",
        )
    host_attestation = _load_host_attestation(
        selected_logical_cpu=selected_logical_cpu,
        root=root,
        windows_probe=probe,
    )
    rust_verbose = _capture(["rustc", "+1.75.0", "-vV"], root=root)
    host_match = re.search(r"^host:\s*(\S+)$", rust_verbose, re.MULTILINE)
    target = host_match.group(1) if host_match else "unknown"
    os_identity = cast(Mapping[str, Any], probe["os"])
    processor = cast(Mapping[str, Any], probe["processor_registry"])
    environment: dict[str, object] = {
        "os": "windows",
        "os_version": (
            f"{os_identity['product_name']} {os_identity['display_version']} | "
            f"build {os_identity['current_build']}.{os_identity['ubr']} | "
            f"{os_identity['build_lab_ex']}"
        ),
        "architecture": "x86_64",
        "cpu_model": str(processor["model_name"]).strip(),
        "logical_cpu_count": probe["logical_processor_count"],
        "memory_bytes": probe["memory_bytes"],
        "python_version": platform.python_version(),
        "runtime_abi": "windows-msvc",
        "rustc_version": rust_verbose.splitlines()[0],
        "cargo_version": _capture(["cargo", "+1.75.0", "-V"], root=root),
        "toolchain_sha256": _toolchain_fingerprints(root=root),
        "target_triple": target,
        "build_profile": "release",
        "feature_set": [],
        "cpu_affinity_policy": "single-fixed-logical-cpu",
        "selected_logical_cpu": selected_logical_cpu,
        "effective_cpu_affinity": effective_cpu_affinity,
        "effective_cpuset": _execution_resource_cpuset(execution_resource),
        "execution_resource": execution_resource,
        "host_attestation": host_attestation,
        "host_attestation_fingerprint": host_attestation["attestation_fingerprint"],
    }
    validate_schema(
        {
            "schema_version": "1.0.0",
            "baseline_kind": "strling-performance-baseline",
            "baseline_state": "planned",
            "manifest_fingerprint": "0" * 64,
            "fixture_manifest_fingerprint": "0" * 64,
            "source_commit": "0" * 40,
            "environment": environment,
            "environment_fingerprint": environment_fingerprint(environment),
            "artifact_fingerprints": {},
            "conditioning_repetitions": [],
            "measurements": [],
            "update_command": "synthetic environment schema validation only",
            "update_rationale": "synthetic environment schema validation only",
            "baseline_fingerprint": "0" * 64,
        },
        label="Windows environment probe",
    )
    if target != WINDOWS_TARGET:
        raise PerformanceResourceError(
            "environment-unavailable",
            f"governed Windows target must be {WINDOWS_TARGET}, observed {target}",
        )
    return environment


def live_environment(
    *, selected_logical_cpu: int, root: Path = ROOT
) -> dict[str, object]:
    architecture = platform.machine().lower()
    system = platform.system().lower()
    if architecture not in {"x86_64", "amd64"}:
        raise PerformanceResourceError(
            "environment-unavailable",
            "live performance authority requires native x86_64",
        )
    if system == "windows":
        return _windows_live_environment(
            selected_logical_cpu=selected_logical_cpu, root=root
        )
    if system != "linux":
        raise PerformanceResourceError(
            "environment-unavailable",
            "live performance authority requires native Linux or Windows",
        )
    os_release = "unknown-linux"
    os_release_path = Path("/etc/os-release")
    if os_release_path.is_file():
        values = {}
        for line in os_release_path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"')
        os_release = values.get("PRETTY_NAME", os_release)
    cpu_fields = _cpuinfo_fields(selected_logical_cpu)
    memory_bytes = 0
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        match = re.search(
            r"^MemTotal:\s*(\d+)\s+kB$", meminfo.read_text(), re.MULTILINE
        )
        if match:
            memory_bytes = int(match.group(1)) * 1024
    rust_verbose = _capture(["rustc", "+1.75.0", "-vV"], root=root)
    host_match = re.search(r"^host:\s*(\S+)$", rust_verbose, re.MULTILINE)
    effective_cpu_affinity = _effective_cpu_affinity()
    if effective_cpu_affinity != [selected_logical_cpu]:
        raise PerformanceResourceError(
            "affinity-control",
            "live environment was not measured with the selected single logical CPU",
        )
    execution_resource = _execution_resource_identity(selected_logical_cpu)
    host_attestation = _load_host_attestation(
        selected_logical_cpu=selected_logical_cpu, root=root
    )
    if host_attestation["environment_kind"] == "dedicated-bare-metal":
        host_processor = host_attestation["host_processor"]
        reservation = host_attestation["reservation"]
        reservation_evidence = host_attestation["reservation_evidence"]
        if (
            host_processor["model_name"] != cpu_fields["model_name"]
            or host_processor["vendor_id"] != cpu_fields["vendor_id"]
            or host_processor["family"] != cpu_fields["family"]
            or host_processor["model"] != cpu_fields["model"]
            or host_processor["stepping"] != cpu_fields["stepping"]
            or host_processor["microcode"] != cpu_fields["microcode"]
            or host_processor["logical_cpu_count"] != (os.cpu_count() or 0)
            or host_processor["topology_sha256"]
            != fingerprint(reservation_evidence["host_topology"])
            or reservation["host_logical_processors"] != [selected_logical_cpu]
            or reservation_evidence["selected_cpu_topology"]
            != execution_resource["processor_topology"]
            or reservation_evidence["cgroup_path"] != execution_resource["cgroup_path"]
            or reservation_evidence["cgroup_cpuset_effective"]
            != execution_resource["cgroup_cpuset_effective"]
            or reservation_evidence["cgroup_cpu_max"]
            != execution_resource["cgroup_cpu_max"]
            or reservation_evidence["clocksource"] != execution_resource["clocksource"]
        ):
            raise PerformanceResourceError(
                "host-attestation",
                "bare-metal host attestation does not match the live processor",
            )
    libc_name, libc_version = platform.libc_ver()
    glibc_version = f"{libc_name} {libc_version}".strip()
    if not glibc_version:
        raise PerformanceResourceError(
            "environment-unavailable", "glibc identity is unavailable"
        )
    environment = {
        "os": "linux",
        "os_version": f"{os_release} | kernel {platform.release()}",
        "architecture": "x86_64",
        "cpu_model": cpu_fields["model_name"],
        "logical_cpu_count": os.cpu_count() or 0,
        "memory_bytes": memory_bytes,
        "python_version": platform.python_version(),
        "runtime_abi": glibc_version,
        "rustc_version": rust_verbose.splitlines()[0],
        "cargo_version": _capture(["cargo", "+1.75.0", "-V"], root=root),
        "toolchain_sha256": _toolchain_fingerprints(root=root),
        "target_triple": host_match.group(1) if host_match else "unknown",
        "build_profile": "release",
        "feature_set": [],
        "cpu_affinity_policy": "single-fixed-logical-cpu",
        "selected_logical_cpu": selected_logical_cpu,
        "effective_cpu_affinity": effective_cpu_affinity,
        "effective_cpuset": execution_resource["cgroup_cpuset_effective"],
        "execution_resource": execution_resource,
        "host_attestation": host_attestation,
        "host_attestation_fingerprint": host_attestation["attestation_fingerprint"],
    }
    validate_schema(
        {
            "schema_version": "1.0.0",
            "baseline_kind": "strling-performance-baseline",
            "baseline_state": "planned",
            "manifest_fingerprint": "0" * 64,
            "fixture_manifest_fingerprint": "0" * 64,
            "source_commit": "0" * 40,
            "environment": environment,
            "environment_fingerprint": environment_fingerprint(environment),
            "artifact_fingerprints": {},
            "conditioning_repetitions": [],
            "measurements": [],
            "update_command": "synthetic environment schema validation only",
            "update_rationale": "synthetic environment schema validation only",
            "baseline_fingerprint": "0" * 64,
        },
        label="environment probe",
    )
    if (
        environment["logical_cpu_count"] == 0
        or environment["memory_bytes"] == 0
        or environment["target_triple"] != LINUX_TARGET
    ):
        raise PerformanceResourceError(
            "environment-unavailable", "Linux environment identity is incomplete"
        )
    return environment


def _runner_resource_matches(
    result: Mapping[str, object],
    *,
    selected_logical_cpu: int,
    execution_resource: Mapping[str, object],
) -> bool:
    if (
        result.get("selected_logical_cpu") != selected_logical_cpu
        or result.get("effective_cpu_affinity") != [selected_logical_cpu]
        or result.get("effective_cpuset")
        != _execution_resource_cpuset(execution_resource)
    ):
        return False
    if execution_resource.get("platform") == "windows":
        timer = cast(Mapping[str, object], execution_resource["timer"])
        return (
            result.get("platform") == "windows"
            and result.get("placement_mechanism")
            == execution_resource["placement_mechanism"]
            and result.get("processor_group") == execution_resource["processor_group"]
            and result.get("selected_cpu_set_id")
            == execution_resource["selected_cpu_set_id"]
            and result.get("cpu_set_allocation_state")
            == execution_resource["cpu_set_allocation_state"]
            and result.get("cpu_quota") == "unlimited"
            and result.get("timer_source")
            == f"{timer['source']}:{timer['frequency_hz']}"
            and result.get("process_power_policy")
            == execution_resource["process_power_policy"]
            and result.get("observed_processor_groups")
            == [execution_resource["processor_group"]]
            and result.get("observed_logical_processors") == [selected_logical_cpu]
        )
    return (
        result.get("cgroup_path") == execution_resource["cgroup_path"]
        and result.get("cpu_quota") == execution_resource["cgroup_cpu_max"]
        and result.get("clocksource") == execution_resource["clocksource"]
    )


def _runner_samples(
    operation_id: str,
    fixture_id: str,
    *,
    artifacts: Mapping[str, object],
    warmups: int,
    samples: int,
    batch_iterations: int | None,
    minimum_sample_nanoseconds: int | None,
    maximum_batch_iterations: int,
    selected_logical_cpu: int,
    execution_resource: Mapping[str, object],
    root: Path = ROOT,
) -> dict[str, Any]:
    command = [
        str(artifacts["runner"]),
        "--operation",
        operation_id,
        "--fixture",
        fixture_id,
        "--warmups",
        str(warmups),
        "--samples",
        str(samples),
        "--maximum-batch-iterations",
        str(maximum_batch_iterations),
        "--expected-logical-cpu",
        str(selected_logical_cpu),
    ]
    if batch_iterations is not None:
        command.extend(["--batch-iterations", str(batch_iterations)])
    elif minimum_sample_nanoseconds is not None:
        command.extend(
            ["--minimum-sample-nanoseconds", str(minimum_sample_nanoseconds)]
        )
    if operation_id == "latency:cli-startup":
        command.extend(["--kernel-bin", str(artifacts["kernel"])])
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        raise PerformanceResourceError("runner-failed", str(error)) from error
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise PerformanceResourceError("runner-json", str(error)) from error
    observed_batch_iterations = result.get("batch_iterations")
    batch_elapsed_samples = result.get("batch_elapsed_samples", [])
    normalized_samples = result.get("samples", [])
    if (
        result.get("operation_id") != operation_id
        or result.get("fixture_id") != fixture_id
        or result.get("unit") != "nanoseconds"
        or result.get("sample_iterations") != samples
        or not isinstance(observed_batch_iterations, int)
        or not 1 <= observed_batch_iterations <= maximum_batch_iterations
        or batch_iterations is not None
        and observed_batch_iterations != batch_iterations
        or len(normalized_samples) != samples
        or len(batch_elapsed_samples) != samples
        or not _runner_resource_matches(
            result,
            selected_logical_cpu=selected_logical_cpu,
            execution_resource=execution_resource,
        )
    ):
        raise PerformanceResourceError(
            "runner-contract", f"runner result changed for {operation_id}/{fixture_id}"
        )
    normalized = [int(value) for value in normalized_samples]
    elapsed = [int(value) for value in batch_elapsed_samples]
    expected = [
        max(
            1,
            (value + (observed_batch_iterations // 2)) // observed_batch_iterations,
        )
        for value in elapsed
    ]
    if normalized != expected:
        raise PerformanceResourceError(
            "runner-batch-normalization",
            f"runner batch normalization changed for {operation_id}/{fixture_id}",
        )
    return {
        "samples": normalized,
        "batch_iterations": observed_batch_iterations,
        "batch_duration_samples": elapsed,
    }


def _memory_sample(
    fixture_id: str,
    *,
    artifacts: Mapping[str, object],
    selected_logical_cpu: int,
    execution_resource: Mapping[str, object],
    root: Path = ROOT,
) -> int:
    if execution_resource.get("platform") == "windows":
        command = [
            str(artifacts["runner"]),
            "--operation",
            "memory:kernel-peak-rss",
            "--fixture",
            fixture_id,
            "--warmups",
            "1",
            "--samples",
            "1",
            "--expected-logical-cpu",
            str(selected_logical_cpu),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
                timeout=1800,
            )
            result = json.loads(completed.stdout)
        except (
            OSError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
        ) as error:
            raise PerformanceResourceError(
                "memory-runner-failed", str(error)
            ) from error
        peak = result.get("peak_working_set_bytes")
        if (
            not isinstance(peak, int)
            or peak <= 0
            or not _runner_resource_matches(
                result,
                selected_logical_cpu=selected_logical_cpu,
                execution_resource=execution_resource,
            )
        ):
            raise PerformanceResourceError(
                "memory-affinity", "native Windows peak RSS evidence is not governed"
            )
        return peak
    time_binary = Path("/usr/bin/time")
    if not time_binary.is_file():
        raise PerformanceResourceError(
            "memory-tool-unavailable", "/usr/bin/time is required for peak RSS"
        )
    command = [
        str(time_binary),
        "-f",
        "__STRLING_MAX_RSS_KIB__:%M",
        str(artifacts["runner"]),
        "--operation",
        "memory:kernel-peak-rss",
        "--fixture",
        fixture_id,
        "--warmups",
        "1",
        "--samples",
        "1",
        "--expected-logical-cpu",
        str(selected_logical_cpu),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        raise PerformanceResourceError("memory-runner-failed", str(error)) from error
    match = re.search(r"__STRLING_MAX_RSS_KIB__:(\d+)", completed.stderr)
    if match is None:
        raise PerformanceResourceError("memory-result", "peak RSS marker is absent")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise PerformanceResourceError("memory-result", str(error)) from error
    if not _runner_resource_matches(
        result,
        selected_logical_cpu=selected_logical_cpu,
        execution_resource=execution_resource,
    ):
        raise PerformanceResourceError(
            "memory-affinity", "peak RSS runner affinity is not governed"
        )
    return int(match.group(1)) * 1024


def _artifact_size(artifacts: Mapping[str, object]) -> int:
    return (
        cast(Path, artifacts["kernel"]).stat().st_size
        + cast(Path, artifacts["interop"]).stat().st_size
    )


def _measure_key(
    key: tuple[str, str | None],
    *,
    manifest: Mapping[str, object],
    artifacts: Mapping[str, object],
    environment: Mapping[str, object],
    batch_iterations: int | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    operation_id, fixture_id = key
    operation = next(
        row
        for row in cast(list[dict[str, Any]], manifest["operations"])
        if row["id"] == operation_id
    )
    if operation["measurement_kind"] == "latency":
        if fixture_id is None:
            raise PerformanceResourceError("fixture-required", operation_id)
        policy = manifest["measurement_policy"]
        selected_logical_cpu = policy["selected_logical_cpu"]
        minimum_duration = policy["minimum_sample_duration_nanoseconds"]
        return _runner_samples(
            operation_id,
            fixture_id,
            artifacts=artifacts,
            warmups=policy["warmup_iterations"],
            samples=policy["sample_iterations"],
            batch_iterations=batch_iterations,
            minimum_sample_nanoseconds=(
                None
                if batch_iterations is not None
                else minimum_duration * policy["batch_duration_safety_factor"]
            ),
            maximum_batch_iterations=policy["maximum_batch_iterations"],
            selected_logical_cpu=selected_logical_cpu,
            execution_resource=cast(
                Mapping[str, object], environment["execution_resource"]
            ),
            root=root,
        )
    if operation["measurement_kind"] == "peak-rss":
        if fixture_id is None:
            raise PerformanceResourceError("fixture-required", operation_id)
        return {
            "samples": [
                _memory_sample(
                    fixture_id,
                    artifacts=artifacts,
                    selected_logical_cpu=manifest["measurement_policy"][
                        "selected_logical_cpu"
                    ],
                    execution_resource=cast(
                        Mapping[str, object], environment["execution_resource"]
                    ),
                    root=root,
                )
            ],
            "batch_iterations": 1,
            "batch_duration_samples": None,
        }
    if operation["measurement_kind"] == "artifact-bytes":
        return {
            "samples": [_artifact_size(artifacts)],
            "batch_iterations": 1,
            "batch_duration_samples": None,
        }
    raise PerformanceResourceError("measurement-kind", operation_id)


def _measurement_conditioning_check(
    key: tuple[str, str | None],
    *,
    environment: Mapping[str, object],
    root: Path = ROOT,
) -> dict[str, object]:
    fixture_label = key[1] if key[1] is not None else "fixture-free"
    check_id = f"environment:measurement-conditioning/{key[0]}/{fixture_label}"
    rejected_attempts: list[dict[str, object]] = []
    for attempt in range(1, MEASUREMENT_CONDITIONING_MAX_ATTEMPTS + 1):
        try:
            snapshot = _conditioning_snapshot(environment, root=root)
        except PerformanceResourceError as error:
            retrying = attempt < MEASUREMENT_CONDITIONING_MAX_ATTEMPTS
            rejected_attempts.append(
                {
                    "attempt": attempt,
                    "code": error.code,
                    "reason": str(error),
                    "settling_delay_seconds": (
                        MEASUREMENT_CONDITIONING_RETRY_DELAY_SECONDS if retrying else 0
                    ),
                }
            )
            if retrying:
                time.sleep(MEASUREMENT_CONDITIONING_RETRY_DELAY_SECONDS)
            continue
        return {
            "id": check_id,
            "status": "passed",
            "details": {
                "attempt": attempt,
                "maximum_attempts": MEASUREMENT_CONDITIONING_MAX_ATTEMPTS,
                "retry_delay_seconds": MEASUREMENT_CONDITIONING_RETRY_DELAY_SECONDS,
                "rejected_attempts": rejected_attempts,
                "conditioning_identity_fingerprint": snapshot[
                    "conditioning_identity_fingerprint"
                ],
                "snapshot_fingerprint": snapshot["snapshot_fingerprint"],
                "quiescence_observation": snapshot["quiescence_observation"],
            },
        }
    return {
        "id": check_id,
        "status": "unavailable",
        "details": {
            "maximum_attempts": MEASUREMENT_CONDITIONING_MAX_ATTEMPTS,
            "retry_delay_seconds": MEASUREMENT_CONDITIONING_RETRY_DELAY_SECONDS,
            "rejected_attempts": rejected_attempts,
            "reason": "native Windows host did not satisfy governed quiescence",
        },
    }


def _windows_external_workloads() -> list[dict[str, object]]:
    """Return heavyweight evaluator/build processes visible on the Windows host."""

    if platform.system().lower() != "windows":
        return []
    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        (
            "Get-Process | Where-Object { "
            "$_.ProcessName -match "
            "'^(?:fortress|cargo|rustc|behavioral_realization)(?:-|$)' "
            "} | ForEach-Object { "
            "[pscustomobject]@{ ProcessId = $_.Id; Name = $_.ProcessName } "
            "} | ConvertTo-Csv -NoTypeInformation"
        ),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PerformanceResourceError(
            "external-workload-scan", f"Windows process scan failed: {error}"
        ) from error
    if completed.returncode != 0:
        reason = completed.stderr.strip() or "process scan returned no diagnostic"
        raise PerformanceResourceError(
            "external-workload-scan",
            f"Windows process scan exited {completed.returncode}: {reason}",
        )
    workloads: list[dict[str, object]] = []
    for row in csv.DictReader(io.StringIO(completed.stdout)):
        raw_name = str(row.get("Name", "")).strip()
        normalized_name = raw_name.lower().removesuffix(".exe")
        if not any(
            normalized_name == candidate or normalized_name.startswith(f"{candidate}-")
            for candidate in WINDOWS_EXTERNAL_WORKLOAD_PROCESS_NAMES
        ):
            continue
        try:
            process_id = int(str(row.get("ProcessId", "")).strip())
        except ValueError:
            raise PerformanceResourceError(
                "external-workload-scan",
                "Windows process scan returned a malformed process identifier",
            ) from None
        workloads.append({"name": normalized_name, "process_id": process_id})
    return sorted(workloads, key=lambda row: (str(row["name"]), int(row["process_id"])))


def _external_workload_isolation_check(
    key: tuple[str, str | None], *, phase: str
) -> dict[str, object]:
    fixture_label = key[1] if key[1] is not None else "fixture-free"
    check_id = (
        f"environment:external-workload-isolation/{phase}/{key[0]}/{fixture_label}"
    )
    try:
        workloads = _windows_external_workloads()
    except PerformanceResourceError as error:
        return {
            "id": check_id,
            "status": "unavailable",
            "details": {"code": error.code, "reason": str(error), "phase": phase},
        }
    return {
        "id": check_id,
        "status": "passed" if not workloads else "unavailable",
        "details": {
            "phase": phase,
            "observed_workloads": workloads,
            "unrelated_heavyweight_workloads_absent": not workloads,
        },
    }


def _absolute_ceiling(median: int, relative_budget_basis_points: int) -> int:
    return math.ceil(median * (10_000 + (2 * relative_budget_basis_points)) / 10_000)


def create_active_contract(
    manifest: Mapping[str, object],
    fixtures: Mapping[str, object],
    *,
    environment: Mapping[str, object],
    artifact_fingerprints: Mapping[str, object],
    conditioning_repetitions: Sequence[Mapping[str, object]],
    source_commit: str,
    repetitions: Mapping[tuple[str, str | None], list[list[int]]],
    batch_iterations: Mapping[tuple[str, str | None], int],
    batch_duration_repetitions: Mapping[tuple[str, str | None], list[list[int]] | None],
    rationale: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(rationale.strip()) < 20:
        raise PerformanceResourceError(
            "baseline-rationale", "baseline rationale must be reviewable"
        )
    environment_hash = environment_fingerprint(environment)
    validate_definition(
        artifact_fingerprints,
        definition="artifactFingerprints",
        label="release artifact fingerprints",
    )
    if len(conditioning_repetitions) != manifest["measurement_policy"][
        "baseline_repetitions"
    ] or not conditioning_identities_match(conditioning_repetitions):
        raise PerformanceResourceError(
            "conditioning-drift",
            "all five baseline repetitions require identical conditioning identity",
        )
    operations = {
        row["id"]: row for row in cast(list[dict[str, Any]], manifest["operations"])
    }
    rows: list[dict[str, Any]] = []
    for key in performance_measurement_keys(manifest):
        operation_id, fixture_id = key
        operation = operations[operation_id]
        repeated = repetitions.get(key)
        if repeated is None:
            raise PerformanceResourceError(
                "baseline-denominator", f"missing calibration for {key}"
            )
        governed_batch_iterations = batch_iterations.get(key)
        if governed_batch_iterations is None:
            raise PerformanceResourceError(
                "baseline-batch", f"missing batch count for {key}"
            )
        elapsed_repetitions = batch_duration_repetitions.get(key)
        representative = [sample_statistics(values)["median"] for values in repeated]
        statistics_row = sample_statistics(representative)
        relative_mad_basis_points = math.ceil(
            statistics_row["mad"] * 10_000 / statistics_row["median"]
        )
        maximum_relative_mad_basis_points = manifest["measurement_policy"][
            "maximum_relative_mad_basis_points"
        ]
        if relative_mad_basis_points > maximum_relative_mad_basis_points:
            raise PerformanceResourceError(
                "unstable-baseline",
                (
                    f"relative MAD is unstable for {key}: "
                    f"{relative_mad_basis_points} bp exceeds "
                    f"{maximum_relative_mad_basis_points} bp; "
                    f"repetition medians={representative}"
                ),
            )
        relative_budget = derived_relative_budget_basis_points(
            median=statistics_row["median"],
            mad=statistics_row["mad"],
            floor=manifest["measurement_policy"][
                "minimum_relative_budget_basis_points"
            ],
            maximum=manifest["measurement_policy"][
                "maximum_relative_budget_basis_points"
            ],
        )
        ceiling = max(
            max(representative),
            _absolute_ceiling(statistics_row["median"], relative_budget),
        )
        rows.append(
            {
                "operation_id": operation_id,
                "fixture_id": fixture_id,
                "unit": operation["unit"],
                "repetitions": repeated,
                "batch_iterations": governed_batch_iterations,
                "batch_duration_repetitions": elapsed_repetitions,
                "samples": representative,
                "statistics": statistics_row,
                "budget": {
                    "state": "active",
                    "relative_regression_basis_points": relative_budget,
                    "absolute_ceiling": ceiling,
                    "rationale": (
                        "Five governed repetition medians determine variance; the "
                        "absolute ceiling is two derived relative budgets above the median."
                    ),
                },
                "environment_fingerprint": environment_hash,
            }
        )
    expected_keys = set(performance_measurement_keys(manifest))
    if (
        set(repetitions) != expected_keys
        or set(batch_iterations) != expected_keys
        or set(batch_duration_repetitions) != expected_keys
    ):
        raise PerformanceResourceError(
            "baseline-denominator", "unexpected calibration measurement key"
        )
    activated = copy.deepcopy(manifest)
    activated_operations = {row["id"]: row for row in activated["operations"]}
    for operation_id in PERFORMANCE_OPERATION_IDS:
        operation_rows = [row for row in rows if row["operation_id"] == operation_id]
        relative = max(
            row["budget"]["relative_regression_basis_points"] for row in operation_rows
        )
        absolute = max(row["budget"]["absolute_ceiling"] for row in operation_rows)
        activated_operations[operation_id]["state"] = "active"
        activated_operations[operation_id]["budget"] = {
            "state": "active",
            "relative_regression_basis_points": relative,
            "absolute_ceiling": absolute,
            "rationale": (
                "Maximum measured fixture budget and ceiling; fixture-specific "
                "comparison authority remains in the authenticated baseline."
            ),
        }
    activated["manifest_fingerprint"] = document_fingerprint(
        activated, "manifest_fingerprint"
    )
    baseline: dict[str, Any] = {
        "schema_version": "1.0.0",
        "baseline_kind": "strling-performance-baseline",
        "baseline_state": "active",
        "manifest_fingerprint": activated["manifest_fingerprint"],
        "fixture_manifest_fingerprint": fixtures["fixture_manifest_fingerprint"],
        "source_commit": source_commit,
        "environment": dict(environment),
        "environment_fingerprint": environment_hash,
        "artifact_fingerprints": copy.deepcopy(artifact_fingerprints),
        "conditioning_repetitions": copy.deepcopy(conditioning_repetitions),
        "measurements": rows,
        "update_command": activated["measurement_policy"]["baseline_update_command"],
        "update_rationale": rationale,
        "baseline_fingerprint": "0" * 64,
    }
    baseline["baseline_fingerprint"] = document_fingerprint(
        baseline, "baseline_fingerprint"
    )
    validate_manifest(activated, fixtures=fixtures)
    validate_baseline(baseline, manifest=activated)
    return activated, baseline


def planned_environment_rollover_manifest(
    manifest: Mapping[str, object],
) -> dict[str, Any]:
    """Return the reviewed transient state required before one calibration."""

    planned = copy.deepcopy(dict(manifest))
    operations = {
        row["id"]: row for row in cast(list[dict[str, Any]], planned["operations"])
    }
    for operation_id in PERFORMANCE_OPERATION_IDS:
        operations[operation_id]["state"] = "planned"
        operations[operation_id]["budget"] = {
            "state": "planned",
            "relative_regression_basis_points": None,
            "absolute_ceiling": None,
            "rationale": (
                "A reviewed environment-version rollover requires one governed "
                "calibration before reactivation."
            ),
        }
    planned["manifest_fingerprint"] = document_fingerprint(
        planned, "manifest_fingerprint"
    )
    return planned


def _rollover_contract_projection(manifest: Mapping[str, object]) -> dict[str, Any]:
    projected = copy.deepcopy(dict(manifest))
    projected.pop("manifest_fingerprint", None)
    for operation in cast(list[dict[str, Any]], projected["operations"]):
        if operation["id"] in PERFORMANCE_OPERATION_IDS:
            operation["state"] = "environment-versioned-active"
            operation["budget"] = "environment-derived-under-unchanged-policy"
    return projected


def validate_environment_rollover(
    prior_manifest: Mapping[str, object],
    prior_baseline: Mapping[str, object],
    candidate_manifest: Mapping[str, object],
    candidate_baseline: Mapping[str, object],
    *,
    expected_os_build: str,
) -> dict[str, Any]:
    """Prove an OS-only rollover against the immediately prior active contract."""

    if not re.fullmatch(r"\d+\.\d+", expected_os_build):
        raise PerformanceResourceError(
            "rollover-os-build", "expected Windows build must be <build>.<ubr>"
        )
    if _rollover_contract_projection(prior_manifest) != _rollover_contract_projection(
        candidate_manifest
    ):
        raise PerformanceResourceError(
            "rollover-contract-drift",
            "benchmark coordinates or performance policy changed during environment rollover",
        )
    if (
        prior_baseline["artifact_fingerprints"]
        != candidate_baseline["artifact_fingerprints"]
    ):
        raise PerformanceResourceError(
            "rollover-product-identity",
            "release artifact identities changed during environment rollover",
        )

    prior_environment = cast(Mapping[str, object], prior_baseline["environment"])
    candidate_environment = cast(
        Mapping[str, object], candidate_baseline["environment"]
    )
    if (
        prior_environment.get("os") != "windows"
        or candidate_environment.get("os") != "windows"
    ):
        raise PerformanceResourceError(
            "rollover-platform", "environment rollover is authorized only for Windows"
        )
    observed_version = cast(str, candidate_environment["os_version"])
    if f"build {expected_os_build}" not in observed_version:
        raise PerformanceResourceError(
            "rollover-os-build",
            f"qualified environment is not Windows build {expected_os_build}",
        )
    prior_version = cast(str, prior_environment["os_version"])
    if prior_version == observed_version:
        raise PerformanceResourceError(
            "rollover-no-change", "environment rollover requires a changed OS identity"
        )

    permitted_environment_coordinates = {
        "os_version",
        "host_attestation.host_os",
        "host_attestation.host_kernel_or_hypervisor",
        "host_attestation.attestation_fingerprint",
        "host_attestation_fingerprint",
    }
    mismatches = environment_mismatches(prior_environment, candidate_environment)
    unexpected = [
        row
        for row in mismatches
        if row["coordinate"] not in permitted_environment_coordinates
    ]
    if unexpected:
        raise PerformanceResourceError(
            "rollover-environment-drift",
            "non-OS environment identity changed: "
            + json.dumps(unexpected, sort_keys=True),
        )

    prior_rows = {
        (row["operation_id"], row["fixture_id"]): row
        for row in cast(list[dict[str, Any]], prior_baseline["measurements"])
    }
    candidate_rows = {
        (row["operation_id"], row["fixture_id"]): row
        for row in cast(list[dict[str, Any]], candidate_baseline["measurements"])
    }
    if set(prior_rows) != set(candidate_rows):
        raise PerformanceResourceError(
            "rollover-denominator", "performance measurement coordinates changed"
        )
    comparisons: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for key in performance_measurement_keys(prior_manifest):
        prior = prior_rows[key]
        candidate = candidate_rows[key]
        comparison = compare_hard_metric(
            baseline_median=prior["statistics"]["median"],
            observed_median=candidate["statistics"]["median"],
            relative_regression_basis_points=prior["budget"][
                "relative_regression_basis_points"
            ],
            absolute_ceiling=prior["budget"]["absolute_ceiling"],
        )
        row = {
            "operation_id": key[0],
            "fixture_id": key[1],
            "comparison": comparison,
        }
        comparisons.append(row)
        if comparison["status"] != "passed":
            failed.append(row)
    if failed:
        raise PerformanceResourceError(
            "rollover-regression",
            "new environment calibration does not pass the prior active contract: "
            + json.dumps(failed, sort_keys=True),
        )
    return {
        "status": "passed",
        "expected_os_build": expected_os_build,
        "prior_environment_fingerprint": prior_baseline["environment_fingerprint"],
        "candidate_environment_fingerprint": candidate_baseline[
            "environment_fingerprint"
        ],
        "environment_mismatches": mismatches,
        "comparison_count": len(comparisons),
        "failed_comparisons": 0,
        "artifact_fingerprints_preserved": True,
        "contract_projection_preserved": True,
    }


def _write_json(path: Path, value: Mapping[str, object], *, root: Path = ROOT) -> None:
    governed_root = (root / "tests/certification/performance-resource/1.0").resolve()
    resolved = path.resolve()
    if resolved.suffix != ".json" or governed_root not in resolved.parents:
        raise PerformanceResourceError(
            "write-boundary", f"refusing non-governed output {path}"
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=resolved.parent,
        prefix=f".{resolved.name}.",
        suffix=".tmp",
        delete=False,
    ) as output:
        output.write(serialized_json(value))
        temporary = Path(output.name)
    os.replace(temporary, resolved)


def refresh_resource_identities(
    manifest: Mapping[str, object],
    inventory: Mapping[str, object],
    baseline: Mapping[str, object],
    evidence: Mapping[str, object],
    *,
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Renew source-bound identities without recalibrating performance data."""

    refreshed_inventory = copy.deepcopy(dict(inventory))
    for family in cast(list[dict[str, Any]], refreshed_inventory["families"]):
        for test_source in cast(list[dict[str, Any]], family["test_sources"]):
            relative = cast(str, test_source["path"])
            path = root / relative
            if not path.is_file():
                raise PerformanceResourceError(
                    "missing-test", f"missing resource test {relative}"
                )
            test_source["sha256"] = file_fingerprint(path)
    refreshed_inventory["inventory_fingerprint"] = document_fingerprint(
        refreshed_inventory, "inventory_fingerprint"
    )

    refreshed_manifest = copy.deepcopy(dict(manifest))
    refreshed_manifest["resource_inventory"]["sha256"] = serialized_fingerprint(
        refreshed_inventory
    )
    refreshed_manifest["manifest_fingerprint"] = document_fingerprint(
        refreshed_manifest, "manifest_fingerprint"
    )

    refreshed_baseline = copy.deepcopy(dict(baseline))
    refreshed_baseline["manifest_fingerprint"] = refreshed_manifest[
        "manifest_fingerprint"
    ]
    refreshed_baseline["baseline_fingerprint"] = document_fingerprint(
        refreshed_baseline, "baseline_fingerprint"
    )

    refreshed_evidence = copy.deepcopy(dict(evidence))
    refreshed_evidence["manifest_fingerprint"] = refreshed_manifest[
        "manifest_fingerprint"
    ]

    fixtures = load_json(root / FIXTURE_MANIFEST_PATH.relative_to(ROOT))
    validate_resource_inventory(refreshed_inventory, root=root)
    validate_manifest(
        refreshed_manifest,
        root=root,
        fixtures=fixtures,
        inventory=refreshed_inventory,
        verify_source_files=False,
    )
    validate_baseline(refreshed_baseline, manifest=refreshed_manifest)
    validate_evidence(refreshed_evidence, manifest=refreshed_manifest)
    return (
        refreshed_manifest,
        refreshed_inventory,
        refreshed_baseline,
        refreshed_evidence,
    )


def _refresh_identity_command(*, root: Path = ROOT) -> dict[str, Any]:
    manifest, inventory, baseline, evidence = refresh_resource_identities(
        load_json(root / MANIFEST_PATH.relative_to(ROOT)),
        load_json(root / RESOURCE_INVENTORY_PATH.relative_to(ROOT)),
        load_json(root / BASELINE_PATH.relative_to(ROOT)),
        load_json(root / VALID_EVIDENCE_PATH.relative_to(ROOT)),
        root=root,
    )
    _write_json(root / RESOURCE_INVENTORY_PATH.relative_to(ROOT), inventory, root=root)
    _write_json(root / MANIFEST_PATH.relative_to(ROOT), manifest, root=root)
    _write_json(root / BASELINE_PATH.relative_to(ROOT), baseline, root=root)
    _write_json(root / VALID_EVIDENCE_PATH.relative_to(ROOT), evidence, root=root)
    validated = validate_repository_contract(root)
    return {
        "status": "passed",
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "baseline_fingerprint": baseline["baseline_fingerprint"],
        "resource_inventory_fingerprint": validated["resource_inventory_fingerprint"],
        "measurements_recalibrated": False,
    }


def calibrate_baseline(
    manifest: Mapping[str, object],
    fixtures: Mapping[str, object],
    *,
    artifacts: Mapping[str, object],
    artifact_fingerprints: Mapping[str, object],
    environment: Mapping[str, object],
    source_commit: str,
    rationale: str,
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    keys = performance_measurement_keys(manifest)
    repetitions: dict[tuple[str, str | None], list[list[int]]] = {
        key: [] for key in keys
    }
    batch_iterations: dict[tuple[str, str | None], int] = {}
    batch_duration_repetitions: dict[tuple[str, str | None], list[list[int]] | None] = {
        key: [] for key in keys
    }
    conditioning_repetitions: list[dict[str, Any]] = []
    policy = manifest["measurement_policy"]
    for repetition_index in range(policy["baseline_repetitions"]):
        conditioning_repetitions.append(_conditioning_snapshot(environment, root=root))
        if not conditioning_identities_match(conditioning_repetitions):
            raise PerformanceResourceError(
                "conditioning-drift",
                "conditioning identity changed between baseline repetitions",
            )
        ordered = list(keys)
        random.Random(policy["order_seed"] + repetition_index).shuffle(ordered)
        for key in ordered:
            observation = _measure_key(
                key,
                manifest=manifest,
                artifacts=artifacts,
                environment=environment,
                batch_iterations=batch_iterations.get(key),
                root=root,
            )
            observed_batch_iterations = observation["batch_iterations"]
            if (
                key in batch_iterations
                and batch_iterations[key] != observed_batch_iterations
            ):
                raise PerformanceResourceError(
                    "batch-reuse", f"batch count changed during calibration for {key}"
                )
            batch_iterations[key] = observed_batch_iterations
            repetitions[key].append(observation["samples"])
            elapsed = observation["batch_duration_samples"]
            if elapsed is None:
                batch_duration_repetitions[key] = None
            else:
                duration_rows = batch_duration_repetitions[key]
                if duration_rows is None:
                    raise PerformanceResourceError(
                        "batch-duration-evidence",
                        f"batch duration evidence changed during calibration for {key}",
                    )
                duration_rows.append(elapsed)
    return create_active_contract(
        manifest,
        fixtures,
        environment=environment,
        artifact_fingerprints=artifact_fingerprints,
        conditioning_repetitions=conditioning_repetitions,
        source_commit=source_commit,
        repetitions=repetitions,
        batch_iterations=batch_iterations,
        batch_duration_repetitions=batch_duration_repetitions,
        rationale=rationale,
    )


def _resource_checks(root: Path = ROOT) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for operation_id in RESOURCE_OPERATION_IDS:
        steps = []
        statuses = []
        for command in RESOURCE_COMMANDS[operation_id]:
            isolated_command = [
                *command,
                "--target-dir",
                str(root / RESOURCE_TARGET_DIRECTORY),
            ]
            status, details = _run_command(
                isolated_command, root=root, timeout_seconds=900
            )
            statuses.append(status)
            steps.append({"status": status, **details})
            if status != "passed":
                break
        checks.append(
            {
                "id": operation_id,
                "status": aggregate_status(statuses or ["unavailable"]),
                "details": {"steps": steps},
            }
        )
    return checks


def _artifact_fingerprints_match(
    baseline: Mapping[str, object], observed: Mapping[str, object]
) -> bool:
    return set(baseline) == {"runner", "kernel", "interop"} and baseline == observed


def _artifact_source_git(
    root: Path, *arguments: str
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            _git_invocation(root, *arguments),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PerformanceResourceError("artifact-source-git", str(error)) from error


def _artifact_source_changes(
    *,
    baseline_source_commit: str,
    candidate_source_commit: str,
    root: Path = ROOT,
) -> dict[str, list[str]]:
    commit_pattern = re.compile(r"[0-9a-f]{40}")
    if not commit_pattern.fullmatch(
        baseline_source_commit
    ) or not commit_pattern.fullmatch(candidate_source_commit):
        raise PerformanceResourceError(
            "artifact-source-identity", "artifact source commits must be exact SHA-1s"
        )
    if baseline_source_commit == candidate_source_commit:
        return {name: [] for name in ARTIFACT_SOURCE_PATHS}

    ancestry = _artifact_source_git(
        root,
        "merge-base",
        "--is-ancestor",
        baseline_source_commit,
        candidate_source_commit,
    )
    if ancestry.returncode != 0:
        reason = ancestry.stderr.strip() or (
            "the active baseline source is not an ancestor of the candidate"
            if ancestry.returncode == 1
            else f"git merge-base exited {ancestry.returncode}"
        )
        raise PerformanceResourceError("artifact-source-ancestry", reason)

    changes: dict[str, list[str]] = {}
    for artifact_name, source_paths in ARTIFACT_SOURCE_PATHS.items():
        completed = _artifact_source_git(
            root,
            "diff",
            "--name-only",
            "--no-renames",
            baseline_source_commit,
            candidate_source_commit,
            "--",
            *source_paths,
        )
        if completed.returncode != 0:
            reason = completed.stderr.strip() or (
                f"git diff exited {completed.returncode} for {artifact_name}"
            )
            raise PerformanceResourceError("artifact-source-diff", reason)
        changes[artifact_name] = sorted(
            {
                line.strip().replace("\\", "/")
                for line in completed.stdout.splitlines()
                if line.strip()
            }
        )
    return changes


def _artifact_identity_check(
    baseline: Mapping[str, object],
    observed: Mapping[str, object],
    *,
    baseline_source_commit: str,
    candidate_source_commit: str,
    source_changes: Mapping[str, Sequence[str]] | None,
) -> tuple[bool, dict[str, object]]:
    artifact_names = {"runner", "kernel", "interop"}
    complete = set(baseline) == artifact_names and set(observed) == artifact_names
    rows: dict[str, object] = {}
    for artifact_name in sorted(artifact_names):
        exact_match = (
            artifact_name in baseline
            and artifact_name in observed
            and baseline[artifact_name] == observed[artifact_name]
        )
        changed_paths = (
            sorted(set(source_changes.get(artifact_name, ())))
            if source_changes is not None
            else []
        )
        source_closure_changed = bool(changed_paths)
        rows[artifact_name] = {
            "status": (
                "baseline-exact"
                if exact_match
                else (
                    "candidate-source-bound"
                    if source_closure_changed
                    else "unexplained-artifact-drift"
                )
            ),
            "exact_match": exact_match,
            "source_closure_changed": source_closure_changed,
            "changed_paths": changed_paths,
            "source_paths": list(ARTIFACT_SOURCE_PATHS[artifact_name]),
        }
    accepted = complete and all(
        cast(Mapping[str, object], row)["exact_match"]
        or cast(Mapping[str, object], row)["source_closure_changed"]
        for row in rows.values()
    )
    return accepted, {
        "policy": "baseline-exact-or-candidate-source-closure-changed",
        "baseline_source_commit": baseline_source_commit,
        "candidate_source_commit": candidate_source_commit,
        "complete_artifact_set": complete,
        "artifacts": rows,
    }


def _controlled_regression_check(
    baseline: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    if baseline is None:
        baseline_median = 1000
        relative_budget = 1000
        absolute_ceiling = 2000
        source = "synthetic-boundary"
    else:
        measurement = baseline["measurements"][0]
        baseline_median = measurement["statistics"]["median"]
        relative_budget = measurement["budget"]["relative_regression_basis_points"]
        absolute_ceiling = measurement["budget"]["absolute_ceiling"]
        source = f"{measurement['operation_id']}/{measurement['fixture_id']}"
    relative_ceiling = math.floor(baseline_median * (10_000 + relative_budget) / 10_000)
    result = compare_hard_metric(
        baseline_median=baseline_median,
        observed_median=relative_ceiling + 1,
        relative_regression_basis_points=relative_budget,
        absolute_ceiling=absolute_ceiling,
    )
    return {
        "id": "controlled:one-unit-relative-regression",
        "status": "passed" if result["status"] == "failed" else "failed",
        "details": {
            "injected_observation": relative_ceiling + 1,
            "comparison": result,
            "source": source,
        },
    }


def _certification_evidence(
    *,
    profile: str,
    commit: str,
    checks: list[dict[str, Any]],
    manifest: Mapping[str, object],
) -> dict[str, Any]:
    deterministic = {
        "profile": profile,
        "status": aggregate_status([row["status"] for row in checks]),
        "checks": checks,
    }
    evidence = {
        "schema_version": "certification-result-v1",
        "evidence_kind": "live-certification",
        "operation_id": PROFILE_OPERATION_IDS[profile],
        "profile": profile,
        "status": deterministic["status"],
        "duration_ms": None,
        "checks": checks,
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "commit": commit,
        "deterministic_evidence": deterministic,
        "evidence_fingerprint": fingerprint(deterministic),
        "disclaimer": (
            "Live engineering certification only; it does not update a baseline, "
            "define language semantics, or claim target-regex runtime performance."
        ),
    }
    validate_evidence(evidence, manifest=manifest)
    return evidence


def certify(
    profile: str,
    *,
    root: Path = ROOT,
    allow_artifact_rebind: bool = False,
    execution_ledger: PerformanceExecutionLedger | None = None,
) -> dict[str, Any]:
    repository = validate_repository_contract(root)
    manifest = load_json(root / MANIFEST_PATH.relative_to(ROOT))
    commit, dirty = _git_identity(root)
    checks: list[dict[str, Any]] = []
    if profile == "local":
        checks.append(
            {
                "id": "contract:performance-resource-manifest",
                "status": "passed",
                "details": {**repository, "dirty_worktree": dirty},
            }
        )
    elif profile == "pull-request":
        checks.extend(_resource_checks(root))
        baseline_path = root / BASELINE_PATH.relative_to(ROOT)
        baseline = load_json(baseline_path) if baseline_path.is_file() else None
        checks.append(_controlled_regression_check(baseline))
    elif profile == "full":
        baseline_path = root / BASELINE_PATH.relative_to(ROOT)
        if not baseline_path.is_file():
            checks.append(
                {
                    "id": "baseline:active",
                    "status": "unavailable",
                    "details": {"reason": "no active governed baseline"},
                }
            )
            return _certification_evidence(
                profile=profile, commit=commit, checks=checks, manifest=manifest
            )
        baseline = load_json(baseline_path)
        try:
            effective_cpu_affinity = _enforce_governed_cpu_affinity(manifest)
        except PerformanceResourceError as error:
            checks.append(
                {
                    "id": "environment:single-fixed-logical-cpu",
                    "status": "unavailable",
                    "details": {"code": error.code, "reason": str(error)},
                }
            )
            return _certification_evidence(
                profile=profile, commit=commit, checks=checks, manifest=manifest
            )
        checks.append(
            {
                "id": "environment:single-fixed-logical-cpu",
                "status": "passed",
                "details": {
                    "selected_logical_cpu": manifest["measurement_policy"][
                        "selected_logical_cpu"
                    ],
                    "effective_cpu_affinity": effective_cpu_affinity,
                    "effective_cpuset": _format_cpu_set(effective_cpu_affinity),
                },
            }
        )
        build_status, build_details = _build_release_artifacts(root)
        checks.append(
            {
                "id": "build:release-performance-artifacts",
                "status": build_status,
                "details": build_details,
            }
        )
        if build_status != "passed":
            return _certification_evidence(
                profile=profile, commit=commit, checks=checks, manifest=manifest
            )
        observed_artifacts = cast(
            Mapping[str, object], build_details.get("artifacts", {})
        )
        artifact_fingerprints_match = _artifact_fingerprints_match(
            cast(Mapping[str, object], baseline["artifact_fingerprints"]),
            observed_artifacts,
        )
        source_changes: Mapping[str, Sequence[str]] | None = None
        artifact_identity_error: PerformanceResourceError | None = None
        if not artifact_fingerprints_match and not allow_artifact_rebind:
            try:
                source_changes = _artifact_source_changes(
                    baseline_source_commit=cast(str, baseline["source_commit"]),
                    candidate_source_commit=commit,
                    root=root,
                )
            except PerformanceResourceError as error:
                artifact_identity_error = error
        artifact_identity_accepted, artifact_identity_details = (
            _artifact_identity_check(
                cast(Mapping[str, object], baseline["artifact_fingerprints"]),
                observed_artifacts,
                baseline_source_commit=cast(str, baseline["source_commit"]),
                candidate_source_commit=commit,
                source_changes=source_changes,
            )
        )
        if artifact_identity_error is not None:
            artifact_identity_details["code"] = artifact_identity_error.code
            artifact_identity_details["reason"] = str(artifact_identity_error)
        checks.append(
            {
                "id": "build:baseline-artifact-identity",
                "status": (
                    "passed"
                    if artifact_identity_accepted or allow_artifact_rebind
                    else "unavailable"
                ),
                "details": {
                    "baseline_artifacts": baseline["artifact_fingerprints"],
                    "observed_artifacts": observed_artifacts,
                    "exact_match": artifact_fingerprints_match,
                    "candidate_rebind": (
                        allow_artifact_rebind and not artifact_fingerprints_match
                    ),
                    "candidate_identity": artifact_identity_details,
                },
            }
        )
        if not artifact_identity_accepted and not allow_artifact_rebind:
            return _certification_evidence(
                profile=profile, commit=commit, checks=checks, manifest=manifest
            )
        try:
            environment = live_environment(
                selected_logical_cpu=manifest["measurement_policy"][
                    "selected_logical_cpu"
                ],
                root=root,
            )
        except PerformanceResourceError as error:
            checks.append(
                {
                    "id": "environment:fingerprinted-native-x86_64",
                    "status": "unavailable",
                    "details": {"code": error.code, "reason": str(error)},
                }
            )
            return _certification_evidence(
                profile=profile, commit=commit, checks=checks, manifest=manifest
            )
        compatible = environments_compatible(baseline["environment"], environment)
        baseline_identity_fingerprint = environment_identity_fingerprint(
            cast(Mapping[str, object], baseline["environment"])
        )
        observed_identity_fingerprint = environment_identity_fingerprint(environment)
        checks.append(
            {
                "id": "environment:fingerprinted-native-x86_64",
                "status": "passed" if compatible else "unavailable",
                "details": {
                    "baseline_fingerprint": baseline["environment_fingerprint"],
                    "observed_fingerprint": environment_fingerprint(environment),
                    "exact_match": compatible,
                    "baseline_identity_fingerprint": baseline_identity_fingerprint,
                    "observed_identity_fingerprint": observed_identity_fingerprint,
                    "raw_mismatches": environment_mismatches(
                        cast(Mapping[str, object], baseline["environment"]),
                        environment,
                    ),
                    "governed_mismatches": environment_mismatches(
                        environment_identity(
                            cast(Mapping[str, object], baseline["environment"])
                        ),
                        environment_identity(environment),
                    ),
                },
            }
        )
        if not compatible:
            return _certification_evidence(
                profile=profile, commit=commit, checks=checks, manifest=manifest
            )
        try:
            conditioning = _conditioning_snapshot(environment, root=root)
        except PerformanceResourceError as error:
            checks.append(
                {
                    "id": "environment:identical-conditioning",
                    "status": "unavailable",
                    "details": {"code": error.code, "reason": str(error)},
                }
            )
            return _certification_evidence(
                profile=profile, commit=commit, checks=checks, manifest=manifest
            )
        baseline_conditioning = cast(
            Mapping[str, object], baseline["conditioning_repetitions"][0]
        )
        conditioning_matches = conditioning_snapshots_compatible(
            baseline_conditioning, conditioning
        )
        checks.append(
            {
                "id": "environment:identical-conditioning",
                "status": "passed" if conditioning_matches else "unavailable",
                "details": {
                    "conditioning_identity_fingerprint": (
                        conditioning_identity_fingerprint(conditioning)
                    ),
                    "baseline_conditioning_identity_fingerprint": (
                        conditioning_identity_fingerprint(baseline_conditioning)
                    ),
                    "identical_conditioning_identity": conditioning_matches,
                },
            }
        )
        if not conditioning_matches:
            return _certification_evidence(
                profile=profile, commit=commit, checks=checks, manifest=manifest
            )
        artifacts = _release_artifacts(root)
        baseline_rows = {
            (row["operation_id"], row["fixture_id"]): row
            for row in baseline["measurements"]
        }
        ordered = performance_measurement_keys(manifest)
        random.Random(manifest["measurement_policy"]["order_seed"]).shuffle(ordered)
        for key in ordered:
            pre_measurement_isolation = _external_workload_isolation_check(
                key, phase="pre-measurement"
            )
            checks.append(pre_measurement_isolation)
            if pre_measurement_isolation["status"] != "passed":
                return _certification_evidence(
                    profile=profile, commit=commit, checks=checks, manifest=manifest
                )
            measurement_conditioning = _measurement_conditioning_check(
                key, environment=environment, root=root
            )
            checks.append(measurement_conditioning)
            if measurement_conditioning["status"] != "passed":
                return _certification_evidence(
                    profile=profile, commit=commit, checks=checks, manifest=manifest
                )
            baseline_row = baseline_rows[key]
            if execution_ledger is not None:
                execution_ledger.start_coordinate(key)
            observation = _measure_key(
                key,
                manifest=manifest,
                artifacts=artifacts,
                environment=environment,
                batch_iterations=baseline_row["batch_iterations"],
                root=root,
            )
            samples = observation["samples"]
            if execution_ledger is not None:
                execution_ledger.complete_coordinate(key, samples)
            observed = sample_statistics(samples)
            comparison = compare_hard_metric(
                baseline_median=baseline_row["statistics"]["median"],
                observed_median=observed["median"],
                relative_regression_basis_points=baseline_row["budget"][
                    "relative_regression_basis_points"
                ],
                absolute_ceiling=baseline_row["budget"]["absolute_ceiling"],
            )
            operation = next(
                row
                for row in cast(list[dict[str, Any]], manifest["operations"])
                if row["id"] == key[0]
            )
            status = certification_measurement_status(
                enforcement=operation["enforcement"],
                comparison_status=cast(str, comparison["status"]),
            )
            fixture_label = key[1] if key[1] is not None else "fixture-free"
            checks.append(
                {
                    "id": f"measurement:{key[0]}/{fixture_label}",
                    "status": status,
                    "details": {
                        "samples": samples,
                        "statistics": observed,
                        "comparison": comparison,
                        "enforcement": operation["enforcement"],
                        "disposition": (
                            "release-blocking"
                            if operation["enforcement"] == "hard"
                            else "informational-trend"
                        ),
                        "would_exceed_budget": comparison["status"] == "failed",
                        "batch_iterations": observation["batch_iterations"],
                        "batch_duration_samples": observation["batch_duration_samples"],
                        "unit": baseline_row["unit"],
                    },
                }
            )
            post_measurement_isolation = _external_workload_isolation_check(
                key, phase="post-measurement"
            )
            checks.append(post_measurement_isolation)
            if post_measurement_isolation["status"] != "passed" or status == "failed":
                return _certification_evidence(
                    profile=profile, commit=commit, checks=checks, manifest=manifest
                )
        checks.extend(_resource_checks(root))
        checks.append(_controlled_regression_check(baseline))
    else:
        raise PerformanceResourceError("profile", f"unknown profile {profile}")
    return _certification_evidence(
        profile=profile, commit=commit, checks=checks, manifest=manifest
    )


def _rebind_artifact_command(
    *, confirm_preserve_measurements: bool, root: Path = ROOT
) -> dict[str, Any]:
    if not confirm_preserve_measurements:
        raise PerformanceResourceError(
            "artifact-rebind-confirmation",
            "artifact rebind requires --confirm-preserve-measurements",
        )
    if platform.system().lower() != "windows":
        raise PerformanceResourceError(
            "artifact-rebind-platform",
            "the active baseline requires native Windows artifact revalidation",
        )
    commit, dirty = _git_identity(root)
    if dirty:
        raise PerformanceResourceError(
            "dirty-artifact-rebind",
            "artifact revalidation requires a clean source checkpoint",
        )
    baseline_path = root / BASELINE_PATH.relative_to(ROOT)
    baseline = load_json(baseline_path)
    prior_measurements = copy.deepcopy(baseline["measurements"])
    prior_artifacts = copy.deepcopy(baseline["artifact_fingerprints"])
    prior_fingerprint = baseline["baseline_fingerprint"]
    evidence = certify("full", root=root, allow_artifact_rebind=True)
    deterministic = cast(dict[str, Any], evidence["deterministic_evidence"])
    if deterministic["status"] != "passed":
        blockers = [
            row["id"]
            for row in cast(list[dict[str, Any]], deterministic["checks"])
            if row["status"] != "passed"
        ]
        raise PerformanceResourceError(
            "artifact-rebind-validation",
            f"current artifacts did not pass the existing baseline: {blockers}",
        )
    identity_check = next(
        row
        for row in cast(list[dict[str, Any]], deterministic["checks"])
        if row["id"] == "build:baseline-artifact-identity"
    )
    observed_artifacts = copy.deepcopy(identity_check["details"]["observed_artifacts"])
    if identity_check["details"]["exact_match"]:
        raise PerformanceResourceError(
            "artifact-rebind-redundant",
            "current artifacts already match the active baseline",
        )
    baseline["artifact_fingerprints"] = observed_artifacts
    baseline["source_commit"] = commit
    baseline["update_rationale"] = (
        "P18-T06 current-artifact revalidation after the P18-T05 same-source Rust "
        "packaging transition; all calibrated measurements and budgets are preserved"
    )
    baseline["baseline_fingerprint"] = document_fingerprint(
        baseline, "baseline_fingerprint"
    )
    if baseline["measurements"] != prior_measurements:
        raise PerformanceResourceError(
            "artifact-rebind-measurements",
            "artifact revalidation must not alter calibrated measurements",
        )
    _write_json(baseline_path, baseline, root=root)
    validate_repository_contract(root)
    return {
        "status": "passed",
        "source_commit": commit,
        "prior_baseline_fingerprint": prior_fingerprint,
        "baseline_fingerprint": baseline["baseline_fingerprint"],
        "prior_artifacts": prior_artifacts,
        "artifact_fingerprints": observed_artifacts,
        "measurement_count": len(prior_measurements),
        "measurements_preserved": True,
        "validation_evidence_fingerprint": evidence["evidence_fingerprint"],
    }


def _should_delegate_windows_full(values: Sequence[str]) -> bool:
    arguments = list(values)
    try:
        profile = arguments[arguments.index("--profile") + 1]
    except (ValueError, IndexError):
        return False
    if profile != "full" or "--json" not in arguments:
        return False
    if os.environ.get("STRLING_PERFORMANCE_NATIVE_CHILD") == "1":
        return False
    if (
        platform.system().lower() != "linux"
        or "microsoft" not in platform.release().lower()
    ):
        return False
    baseline = load_json(BASELINE_PATH)
    return baseline.get("environment", {}).get("os") == "windows"


def _windows_native_worktree(root: Path = ROOT) -> Path:
    source_commit, source_dirty = _git_identity(root)
    if source_dirty:
        raise PerformanceResourceError(
            "windows-native-worktree",
            "Windows delegation requires a clean source worktree",
        )
    try:
        completed = subprocess.run(
            _git_invocation(root, "worktree", "list", "--porcelain"),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise PerformanceResourceError("windows-native-worktree", str(error)) from error

    candidates: list[Path] = []
    for block in completed.stdout.split("\n\n"):
        fields = {
            key: value
            for line in block.splitlines()
            if " " in line
            for key, value in [line.split(" ", 1)]
        }
        worktree = fields.get("worktree")
        if worktree is None or re.fullmatch(r"/mnt/[A-Za-z]/.+", worktree) is None:
            continue
        candidate = Path(worktree)
        try:
            candidate_commit, candidate_dirty = _git_identity(candidate)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        if candidate_commit == source_commit and not candidate_dirty:
            candidates.append(candidate)

    resolved_root = root.resolve()
    current_candidates = [
        candidate for candidate in candidates if candidate.resolve() == resolved_root
    ]
    if len(current_candidates) == 1:
        return current_candidates[0]
    if len(candidates) != 1:
        raise PerformanceResourceError(
            "windows-native-worktree",
            "Windows delegation requires exactly one clean native worktree at "
            f"source commit {source_commit}; found {len(candidates)}",
        )
    return candidates[0]


def _delegate_windows_full(values: Sequence[str], root: Path = ROOT) -> int:
    powershell = Path(
        os.environ.get(
            "STRLING_PERFORMANCE_WINDOWS_POWERSHELL",
            "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
        )
    )
    if not powershell.is_file():
        raise PerformanceResourceError(
            "windows-bridge",
            f"native Windows PowerShell is unavailable: {powershell}",
        )
    native_root = _windows_native_worktree(root)
    try:
        windows_root = subprocess.run(
            ["wslpath", "-w", str(native_root)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise PerformanceResourceError("windows-bridge", str(error)) from error
    forwarded = list(values)
    if "--execution-directory" in forwarded:
        try:
            directory_index = forwarded.index("--execution-directory") + 1
            directory = forwarded[directory_index]
        except IndexError as error:
            raise PerformanceResourceError(
                "windows-bridge", "execution directory argument is missing its value"
            ) from error
        try:
            forwarded[directory_index] = subprocess.run(
                ["wslpath", "-w", directory],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError) as error:
            raise PerformanceResourceError("windows-bridge", str(error)) from error
    escaped_root = windows_root.replace("'", "''")
    escaped_arguments = [argument.replace("'", "''") for argument in forwarded]
    powershell_arguments = ", ".join(f"'{argument}'" for argument in escaped_arguments)
    script = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "$toolchain = Join-Path $env:USERPROFILE '.rustup\\toolchains\\1.75.0-x86_64-pc-windows-msvc\\bin'",
            "$cargo = Join-Path $toolchain 'cargo.exe'",
            "$rustc = Join-Path $toolchain 'rustc.exe'",
            "$env:PATH = (Split-Path $cargo) + ';' + $env:PATH",
            "$env:STRLING_PERFORMANCE_CARGO = $cargo",
            "$env:STRLING_PERFORMANCE_RUSTC = $rustc",
            "$env:STRLING_PERFORMANCE_NATIVE_CHILD = '1'",
            "$env:PYTHONDONTWRITEBYTECODE = '1'",
            f"Set-Location -LiteralPath '{escaped_root}'",
            "$python = (Get-Command python -ErrorAction Stop).Source",
            f"$arguments = @({powershell_arguments})",
            "& $python -m tooling.performance_resource_certification @arguments",
            "exit $LASTEXITCODE",
        ]
    )
    completed = subprocess.run(
        [
            str(powershell),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        cwd=native_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return completed.returncode


def _baseline_command(
    *,
    replace: bool,
    rationale: str,
    rollover_from: str | None = None,
    expected_os_build: str | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    if not replace:
        raise PerformanceResourceError(
            "baseline-replace", "baseline updates require explicit --replace"
        )
    commit, dirty = _git_identity(root)
    if dirty:
        raise PerformanceResourceError(
            "dirty-baseline", "baseline calibration requires a clean worktree"
        )
    manifest = load_json(root / MANIFEST_PATH.relative_to(ROOT))
    fixtures = load_json(root / FIXTURE_MANIFEST_PATH.relative_to(ROOT))
    validate_manifest(manifest, root=root, fixtures=fixtures)
    if any(
        row["state"] == "active"
        for row in cast(list[dict[str, Any]], manifest["operations"])
        if row["id"] in PERFORMANCE_OPERATION_IDS
    ):
        raise PerformanceResourceError(
            "active-baseline",
            "replace requires a reviewed manifest reset or new version",
        )
    _enforce_governed_cpu_affinity(manifest)
    build_status, build_details = _build_release_artifacts(root)
    if build_status != "passed":
        raise PerformanceResourceError(
            "release-build", json.dumps(build_details, sort_keys=True)
        )
    environment = live_environment(
        selected_logical_cpu=manifest["measurement_policy"]["selected_logical_cpu"],
        root=root,
    )
    activated, baseline = calibrate_baseline(
        manifest,
        fixtures,
        artifacts=_release_artifacts(root),
        artifact_fingerprints=cast(Mapping[str, object], build_details["artifacts"]),
        environment=environment,
        source_commit=commit,
        rationale=rationale,
        root=root,
    )
    rollover = None
    if rollover_from is not None:
        if expected_os_build is None:
            raise PerformanceResourceError(
                "rollover-os-build",
                "environment rollover calibration requires --expected-os-build",
            )
        history = root / PERFORMANCE_HISTORY_PATH.relative_to(ROOT) / rollover_from
        prior_manifest_path = history / "manifest.json"
        prior_baseline_path = history / "baseline.json"
        if not prior_manifest_path.is_file() or not prior_baseline_path.is_file():
            raise PerformanceResourceError(
                "rollover-history",
                f"missing immutable prior authority {history.relative_to(root)}",
            )
        prior_manifest = load_json(prior_manifest_path)
        prior_baseline = load_json(prior_baseline_path)
        prior_fixtures = load_json(root / FIXTURE_MANIFEST_PATH.relative_to(ROOT))
        validate_manifest(prior_manifest, root=root, fixtures=prior_fixtures)
        validate_baseline(prior_baseline, manifest=prior_manifest)
        if prior_baseline["baseline_fingerprint"] != rollover_from:
            raise PerformanceResourceError(
                "rollover-history", "prior authority directory identity changed"
            )
        rollover = validate_environment_rollover(
            prior_manifest,
            prior_baseline,
            activated,
            baseline,
            expected_os_build=expected_os_build,
        )
    elif expected_os_build is not None:
        raise PerformanceResourceError(
            "rollover-history",
            "--expected-os-build requires --rollover-from",
        )
    evidence = load_json(root / VALID_EVIDENCE_PATH.relative_to(ROOT))
    evidence["manifest_fingerprint"] = activated["manifest_fingerprint"]
    _write_json(root / MANIFEST_PATH.relative_to(ROOT), activated, root=root)
    _write_json(root / VALID_EVIDENCE_PATH.relative_to(ROOT), evidence, root=root)
    _write_json(root / BASELINE_PATH.relative_to(ROOT), baseline, root=root)
    return {
        "status": "passed",
        "source_commit": commit,
        "manifest_fingerprint": activated["manifest_fingerprint"],
        "baseline_fingerprint": baseline["baseline_fingerprint"],
        "environment_fingerprint": baseline["environment_fingerprint"],
        "measurement_count": len(baseline["measurements"]),
        "repetitions": manifest["measurement_policy"]["baseline_repetitions"],
        "build": build_details,
        "environment_rollover": rollover,
    }


def _reset_environment_command(
    *,
    confirm_environment_rollover: bool,
    rationale: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    if not confirm_environment_rollover:
        raise PerformanceResourceError(
            "rollover-confirmation",
            "environment rollover requires --confirm-environment-rollover",
        )
    if len(rationale.strip()) < 20:
        raise PerformanceResourceError(
            "baseline-rationale", "rollover rationale must be reviewable"
        )
    commit, dirty = _git_identity(root)
    if dirty:
        raise PerformanceResourceError(
            "dirty-rollover", "environment rollover reset requires a clean worktree"
        )
    manifest_path = root / MANIFEST_PATH.relative_to(ROOT)
    baseline_path = root / BASELINE_PATH.relative_to(ROOT)
    evidence_path = root / VALID_EVIDENCE_PATH.relative_to(ROOT)
    fixtures = load_json(root / FIXTURE_MANIFEST_PATH.relative_to(ROOT))
    manifest = load_json(manifest_path)
    baseline = load_json(baseline_path)
    evidence = load_json(evidence_path)
    validate_manifest(manifest, root=root, fixtures=fixtures)
    validate_baseline(baseline, manifest=manifest)
    validate_evidence(evidence, manifest=manifest)
    if any(
        row["state"] != "active"
        for row in cast(list[dict[str, Any]], manifest["operations"])
        if row["id"] in PERFORMANCE_OPERATION_IDS
    ):
        raise PerformanceResourceError(
            "rollover-active-baseline",
            "environment rollover requires one completely active baseline",
        )

    prior_fingerprint = cast(str, baseline["baseline_fingerprint"])
    history = root / PERFORMANCE_HISTORY_PATH.relative_to(ROOT) / prior_fingerprint
    if history.exists():
        raise PerformanceResourceError(
            "rollover-history-exists",
            f"refusing to overwrite immutable prior authority {history.relative_to(root)}",
        )
    _write_json(history / "manifest.json", manifest, root=root)
    _write_json(history / "baseline.json", baseline, root=root)
    _write_json(history / "valid-evidence.json", evidence, root=root)

    planned = planned_environment_rollover_manifest(manifest)
    validate_manifest(planned, root=root, fixtures=fixtures)
    refreshed_evidence = copy.deepcopy(evidence)
    refreshed_evidence["manifest_fingerprint"] = planned["manifest_fingerprint"]
    _write_json(manifest_path, planned, root=root)
    _write_json(evidence_path, refreshed_evidence, root=root)
    return {
        "status": "passed",
        "source_commit": commit,
        "rationale": rationale,
        "prior_manifest_fingerprint": manifest["manifest_fingerprint"],
        "prior_baseline_fingerprint": prior_fingerprint,
        "history_path": history.relative_to(root).as_posix(),
        "planned_manifest_fingerprint": planned["manifest_fingerprint"],
        "performance_operation_count": len(PERFORMANCE_OPERATION_IDS),
        "resource_operations_preserved": True,
    }


def _qualification_command(*, root: Path = ROOT) -> dict[str, Any]:
    commit, dirty = _git_identity(root)
    if dirty:
        raise PerformanceResourceError(
            "dirty-qualification",
            "environment qualification requires a clean worktree",
        )
    manifest = load_json(root / MANIFEST_PATH.relative_to(ROOT))
    fixtures = load_json(root / FIXTURE_MANIFEST_PATH.relative_to(ROOT))
    validate_manifest(manifest, root=root, fixtures=fixtures)
    affinity = _enforce_governed_cpu_affinity(manifest)
    build_status, build_details = _build_release_artifacts(root)
    if build_status != "passed":
        raise PerformanceResourceError(
            "release-build", json.dumps(build_details, sort_keys=True)
        )
    environment = live_environment(
        selected_logical_cpu=manifest["measurement_policy"]["selected_logical_cpu"],
        root=root,
    )
    conditioning = _conditioning_snapshot(environment, root=root)
    return {
        "status": "passed",
        "source_commit": commit,
        "effective_cpu_affinity": affinity,
        "environment": environment,
        "environment_fingerprint": environment_fingerprint(environment),
        "artifact_fingerprints": build_details["artifacts"],
        "conditioning": conditioning,
    }


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    execution_ledger: PerformanceExecutionLedger | None = None
    try:
        if _should_delegate_windows_full(values):
            return _delegate_windows_full(values)
        if values and values[0] == "rebind-artifacts":
            parser = argparse.ArgumentParser(
                description="Revalidate current artifacts against the active baseline"
            )
            parser.add_argument("rebind-artifacts")
            parser.add_argument("--confirm-preserve-measurements", action="store_true")
            parser.add_argument("--json", action="store_true")
            arguments = parser.parse_args(values)
            result = _rebind_artifact_command(
                confirm_preserve_measurements=(arguments.confirm_preserve_measurements)
            )
            status = cast(str, result["status"])
        elif values and values[0] == "refresh-identities":
            parser = argparse.ArgumentParser(
                description="Renew governed performance source identities"
            )
            parser.add_argument("refresh-identities")
            parser.add_argument("--json", action="store_true")
            arguments = parser.parse_args(values)
            result = _refresh_identity_command()
            status = cast(str, result["status"])
        elif values and values[0] == "qualify":
            parser = argparse.ArgumentParser(
                description="Qualify the governed performance environment"
            )
            parser.add_argument("qualify")
            parser.add_argument("--json", action="store_true")
            arguments = parser.parse_args(values)
            result = _qualification_command()
            status = cast(str, result["status"])
        elif values and values[0] == "reset-environment":
            parser = argparse.ArgumentParser(
                description="Archive and reset an active environment baseline"
            )
            parser.add_argument("reset-environment")
            parser.add_argument("--confirm-environment-rollover", action="store_true")
            parser.add_argument("--rationale", required=True)
            parser.add_argument("--json", action="store_true")
            arguments = parser.parse_args(values)
            result = _reset_environment_command(
                confirm_environment_rollover=(arguments.confirm_environment_rollover),
                rationale=arguments.rationale,
            )
            status = cast(str, result["status"])
        elif values and values[0] == "baseline":
            parser = argparse.ArgumentParser(
                description="Update governed performance baseline"
            )
            parser.add_argument("baseline")
            parser.add_argument("--replace", action="store_true")
            parser.add_argument("--rationale", required=True)
            parser.add_argument("--rollover-from")
            parser.add_argument("--expected-os-build")
            parser.add_argument("--json", action="store_true")
            arguments = parser.parse_args(values)
            result = _baseline_command(
                replace=arguments.replace,
                rationale=arguments.rationale,
                rollover_from=arguments.rollover_from,
                expected_os_build=arguments.expected_os_build,
            )
            status = cast(str, result["status"])
        else:
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument("--profile", choices=PROFILE_IDS, required=True)
            parser.add_argument("--json", action="store_true")
            parser.add_argument("--execution-directory")
            parser.add_argument("--certification-invocation-id")
            parser.add_argument(
                "--certification-profile",
                choices=("local", "pull-request", "full", "release"),
            )
            parser.add_argument("--expected-source-sha")
            parser.add_argument("--producer-id")
            arguments = parser.parse_args(values)
            execution_values = (
                arguments.execution_directory,
                arguments.certification_invocation_id,
                arguments.certification_profile,
                arguments.expected_source_sha,
                arguments.producer_id,
            )
            provided_execution_values = sum(
                value is not None for value in execution_values
            )
            if provided_execution_values not in (0, len(execution_values)):
                raise PerformanceResourceError(
                    "execution-context",
                    "invocation-bound execution arguments must be supplied together",
                )
            if provided_execution_values:
                commit, dirty = _git_identity(ROOT)
                if dirty or commit != arguments.expected_source_sha:
                    raise PerformanceResourceError(
                        "execution-source-identity",
                        "producer source SHA or clean-tree identity does not match invocation",
                    )
                execution_ledger = PerformanceExecutionLedger(
                    Path(arguments.execution_directory).resolve(),
                    producer_id=arguments.producer_id,
                    operation_id=PROFILE_OPERATION_IDS[arguments.profile],
                    source_sha=arguments.expected_source_sha,
                    invocation_id=arguments.certification_invocation_id,
                    certification_profile=arguments.certification_profile,
                    producer_profile=arguments.profile,
                )
            result = certify(arguments.profile, execution_ledger=execution_ledger)
            status = result["deterministic_evidence"]["status"]
        selected_exit = EXIT_CODES[status]
        if execution_ledger is not None:
            selected_exit = execution_ledger.write_result(
                result, process_exit_code=selected_exit
            )
        print(
            json.dumps(result, sort_keys=True)
            if arguments.json
            else json.dumps(result, indent=2, sort_keys=True)
        )
        return selected_exit
    except PerformanceResourceError as error:
        if execution_ledger is not None:
            selected_exit = execution_ledger.write_incomplete(
                code=error.code, message=str(error)
            )
            result = {
                "status": "incomplete",
                "code": error.code,
                "message": str(error),
            }
        else:
            selected_exit = EXIT_CODES["failed"]
            result = {"status": "failed", "code": error.code, "message": str(error)}
        print(json.dumps(result, sort_keys=True))
        return selected_exit


def validate_evidence(
    evidence: Mapping[str, object], *, manifest: Mapping[str, object]
) -> None:
    validate_schema(evidence, label="evidence")
    if evidence["manifest_fingerprint"] != manifest["manifest_fingerprint"]:
        raise PerformanceResourceError(
            "stale-manifest", "evidence manifest fingerprint changed"
        )
    deterministic = evidence["deterministic_evidence"]
    profile = deterministic["profile"]
    if (
        evidence["operation_id"] != PROFILE_OPERATION_IDS[profile]
        or evidence["profile"] != profile
        or evidence["status"] != deterministic["status"]
        or evidence["checks"] != deterministic["checks"]
    ):
        raise PerformanceResourceError(
            "profile-result-envelope",
            "profile result identity, status, or checks differ from deterministic evidence",
        )
    if evidence["evidence_fingerprint"] != fingerprint(deterministic):
        raise PerformanceResourceError(
            "evidence-fingerprint", "evidence fingerprint changed"
        )
    if evidence["evidence_kind"] == "live-certification":
        if evidence["commit"] == "0" * 40:
            raise PerformanceResourceError(
                "live-commit", "live certification requires a real commit"
            )
        statuses = [row["status"] for row in deterministic["checks"]]
        if deterministic["status"] != aggregate_status(statuses):
            raise PerformanceResourceError(
                "live-status", "live certification status does not aggregate"
            )
        return
    if evidence["evidence_kind"] != "synthetic-contract-fixture":
        raise PerformanceResourceError("evidence-kind", "unknown evidence kind")
    if deterministic["status"] != "passed" or deterministic["profile"] != "local":
        raise PerformanceResourceError(
            "fixture-status", "synthetic Local contract fixture must pass"
        )
    checks = deterministic["checks"]
    if checks != [
        {
            "id": "contract:performance-resource-manifest",
            "status": "passed",
            "details": {
                "fixture": True,
                "live_measurement": False,
                "baseline_authority": False,
            },
        }
    ]:
        raise PerformanceResourceError(
            "fixture-check", "synthetic contract fixture changed"
        )


def validate_repository_contract(root: Path = ROOT) -> dict[str, Any]:
    manifest = load_json(root / MANIFEST_PATH.relative_to(ROOT))
    fixtures = load_json(root / FIXTURE_MANIFEST_PATH.relative_to(ROOT))
    inventory = load_json(root / RESOURCE_INVENTORY_PATH.relative_to(ROOT))
    evidence = load_json(root / VALID_EVIDENCE_PATH.relative_to(ROOT))
    validate_manifest(manifest, root=root, fixtures=fixtures, inventory=inventory)
    validate_evidence(evidence, manifest=manifest)
    performance_state = cast(list[dict[str, Any]], manifest["operations"])[0]["state"]
    baseline_path = root / BASELINE_PATH.relative_to(ROOT)
    if performance_state == "active":
        if not baseline_path.is_file():
            raise PerformanceResourceError(
                "missing-baseline", "active performance contract lacks a baseline"
            )
        validate_baseline(load_json(baseline_path), manifest=manifest)
    elif baseline_path.is_file():
        raise PerformanceResourceError(
            "premature-baseline", "planned performance contract has a baseline"
        )
    return {
        "status": "passed",
        "baseline_state": performance_state,
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "fixture_manifest_fingerprint": fixtures["fixture_manifest_fingerprint"],
        "resource_inventory_fingerprint": inventory["inventory_fingerprint"],
        "operation_count": len(manifest["operations"]),
        "fixture_count": len(fixtures["fixtures"]),
        "resource_declaration_count": inventory["declaration_count"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
