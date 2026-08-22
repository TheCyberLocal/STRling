"""Validate governed STRling performance and resource certification evidence."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "governance/schemas/performance-resource-certification.schema.json"
)
MANIFEST_PATH = ROOT / "tests/certification/performance-resource/1.0/manifest.json"
FIXTURE_MANIFEST_PATH = (
    ROOT
    / "tests/certification/performance-resource/1.0/fixtures/fixture-manifest.json"
)
RESOURCE_INVENTORY_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/fixtures/resource-limits.json"
)
VALID_EVIDENCE_PATH = (
    ROOT / "tests/certification/performance-resource/1.0/valid-evidence.json"
)

PROFILE_IDS = ["local", "pull-request", "full"]
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

ENVIRONMENT_COMPATIBILITY_FIELDS = [
    "os",
    "os_version",
    "architecture",
    "cpu_model",
    "logical_cpu_count",
    "memory_bytes",
    "rustc_version",
    "cargo_version",
    "target_triple",
    "build_profile",
    "feature_set",
]


class PerformanceResourceError(ValueError):
    """A deterministic performance/resource contract failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


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


def _schema() -> dict[str, Any]:
    return load_json(SCHEMA_PATH)


def validate_schema(value: Mapping[str, object], *, label: str) -> None:
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(value),
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
) -> None:
    validate_schema(manifest, label="manifest")
    fixtures = fixtures or load_json(root / manifest["fixture_manifest"]["path"])
    inventory = inventory or load_json(root / manifest["resource_inventory"]["path"])
    validate_fixture_manifest(fixtures)
    validate_resource_inventory(inventory, root=root)
    if file_fingerprint(root / manifest["fixture_manifest"]["path"]) != (
        manifest["fixture_manifest"]["sha256"]
    ):
        raise PerformanceResourceError(
            "stale-fixture-manifest", "fixture manifest source changed"
        )
    if file_fingerprint(root / manifest["resource_inventory"]["path"]) != (
        manifest["resource_inventory"]["sha256"]
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
    for operation in operations:
        if not set(operation["fixture_ids"]).issubset(fixture_ids):
            raise PerformanceResourceError(
                "fixture-reference", f"unknown fixture for {operation['id']}"
            )
        is_resource = operation["id"] in RESOURCE_OPERATION_IDS
        expected_state = "active" if is_resource else "planned"
        expected_budget_state = "not-applicable" if is_resource else "planned"
        if operation["state"] != expected_state:
            raise PerformanceResourceError(
                "premature-activation", f"unexpected state for {operation['id']}"
            )
        if operation["budget"]["state"] != expected_budget_state:
            raise PerformanceResourceError(
                "budget-state", f"unexpected budget state for {operation['id']}"
            )
    partitions = cast(list[dict[str, Any]], manifest["profile_partitions"])
    if [row["id"] for row in partitions] != PROFILE_IDS:
        raise PerformanceResourceError(
            "profile-partition", "profile partition order changed"
        )
    by_profile = {row["id"]: row for row in partitions}
    if by_profile["local"]["operation_ids"]:
        raise PerformanceResourceError("profile-partition", "Local must be contract-only")
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
        or policy["order_seed"] != 1804
        or not policy["single_worker"]
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
    return all(baseline.get(field) == observed.get(field) for field in ENVIRONMENT_COMPATIBILITY_FIELDS)


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


def environment_fingerprint(environment: Mapping[str, object]) -> str:
    return fingerprint(environment)


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
    if baseline["fixture_manifest_fingerprint"] != fixtures[
        "fixture_manifest_fingerprint"
    ]:
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
    if baseline["update_command"] != manifest["measurement_policy"][
        "baseline_update_command"
    ]:
        raise PerformanceResourceError(
            "baseline-update", "baseline update command changed"
        )
    if baseline["baseline_state"] == "planned":
        if baseline["measurements"]:
            raise PerformanceResourceError(
                "planned-baseline", "planned baseline cannot contain measurements"
            )
        return
    if baseline["source_commit"] == "0" * 40 and not synthetic:
        raise PerformanceResourceError(
            "baseline-source", "live baseline requires a real source commit"
        )
    operations = {row["id"]: row for row in manifest["operations"]}
    seen: set[tuple[str, str]] = set()
    for measurement in baseline["measurements"]:
        key = (measurement["operation_id"], measurement["fixture_id"])
        if key in seen:
            raise PerformanceResourceError(
                "duplicate-measurement", f"duplicate baseline measurement {key}"
            )
        seen.add(key)
        operation = operations.get(measurement["operation_id"])
        if operation is None or measurement["operation_id"] not in PERFORMANCE_OPERATION_IDS:
            raise PerformanceResourceError(
                "baseline-operation", f"unknown performance operation {key[0]}"
            )
        if measurement["fixture_id"] not in operation["fixture_ids"]:
            raise PerformanceResourceError(
                "baseline-fixture", f"fixture is not governed for {key[0]}"
            )
        if measurement["environment_fingerprint"] != baseline[
            "environment_fingerprint"
        ]:
            raise PerformanceResourceError(
                "measurement-environment", f"measurement environment changed for {key}"
            )
        samples = measurement["samples"]
        expected_count = manifest["measurement_policy"]["sample_iterations"]
        if len(samples) != expected_count:
            raise PerformanceResourceError(
                "sample-count", f"sample count changed for {key}"
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
        if relative_mad_basis_points > manifest["measurement_policy"][
            "maximum_relative_mad_basis_points"
        ]:
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
    }


def validate_evidence(
    evidence: Mapping[str, object], *, manifest: Mapping[str, object]
) -> None:
    validate_schema(evidence, label="evidence")
    if evidence["manifest_fingerprint"] != manifest["manifest_fingerprint"]:
        raise PerformanceResourceError(
            "stale-manifest", "evidence manifest fingerprint changed"
        )
    if evidence["evidence_kind"] != "synthetic-contract-fixture":
        raise PerformanceResourceError(
            "fixture-kind", "CP2 evidence must be explicitly synthetic"
        )
    deterministic = evidence["deterministic_evidence"]
    if evidence["evidence_fingerprint"] != fingerprint(deterministic):
        raise PerformanceResourceError(
            "evidence-fingerprint", "evidence fingerprint changed"
        )
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
    return {
        "status": "passed",
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "fixture_manifest_fingerprint": fixtures["fixture_manifest_fingerprint"],
        "resource_inventory_fingerprint": inventory["inventory_fingerprint"],
        "operation_count": len(manifest["operations"]),
        "fixture_count": len(fixtures["fixtures"]),
        "resource_declaration_count": inventory["declaration_count"],
    }
