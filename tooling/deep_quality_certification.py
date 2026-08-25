"""Validate and execute governed STRling deep-quality certification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PINNED_RUST_TARGET_DIRECTORY = Path("target/rust-1.75-deep-quality-certification")
SCHEMA_PATH = ROOT / "governance/schemas/deep-quality-certification.schema.json"
MANIFEST_PATH = ROOT / "tests/certification/deep-quality/1.0/manifest.json"
FIXTURE_PATH = (
    ROOT / "tests/certification/deep-quality/1.0/fixtures/valid-evidence.json"
)

PROPERTY_IDS = [
    "property:semantic-dsl-roundtrip",
    "property:legacy-regex-import",
    "property:normalization-idempotence",
    "property:semantic-analysis-determinism",
    "property:structural-analysis-determinism",
    "property:source-span-validity",
    "property:compiler-determinism",
    "property:pcre2-serialization",
    "property:ecmascript-serialization",
    "property:python-re-serialization",
    "property:portability-completeness",
    "property:explanation-migration-conservatism",
    "property:simply-host-roundtrip",
    "property:interop-serialization-roundtrip",
]
INHERITED_FUZZ_IDS = [
    "fuzz:arbitrary-host-bytes",
    "fuzz:structured-envelope",
    "fuzz:length-boundaries",
    "fuzz:simply-graphs",
    "fuzz:target-profiles",
    "fuzz:ownership-sequences",
]
OWNED_FUZZ_IDS = [
    "fuzz:semantic-dsl",
    "fuzz:legacy-regex",
    "fuzz:compiler-protocol",
    "fuzz:normalization-analysis",
    "fuzz:target-serialization",
]
INHERITED_SANITIZER_IDS = [
    "sanitizer:interop-address-leak",
    "sanitizer:wasm-host-memory",
]
OWNED_SANITIZER_IDS = [
    "sanitizer:c-adapter-address-undefined",
    "sanitizer:cpp-adapter-address-undefined",
]
MUTANT_IDS = [
    "mutant:normalization-preflight",
    "mutant:normalization-set-dedup",
    "mutant:capability-unavailable",
    "mutant:capability-unknown",
    "mutant:portability-status",
    "mutant:portability-unresolved",
    "mutant:safety-finding-dedup",
    "mutant:safety-uncertainty-dedup",
    "mutant:pcre2-case-mapping",
    "mutant:ecmascript-case-mapping",
    "mutant:python-re-case-mapping",
    "mutant:rewrite-exact-bound",
    "mutant:product-failed-precedence",
    "mutant:product-unavailable-precedence",
]
PULL_REQUEST_MUTANT_IDS = [
    "mutant:normalization-preflight",
    "mutant:capability-unavailable",
    "mutant:portability-status",
    "mutant:safety-finding-dedup",
    "mutant:pcre2-case-mapping",
    "mutant:rewrite-exact-bound",
    "mutant:product-failed-precedence",
]
PROFILE_OPERATION_IDS = {
    "local": "certification.deep-quality-local",
    "pull-request": "certification.deep-quality-pull-request",
    "full": "certification.deep-quality-full",
}
EXPECTED_COUNTS = {
    "property_suites": 14,
    "property_source_files": 16,
    "fuzz_targets": 11,
    "owned_fuzz_targets": 5,
    "inherited_fuzz_targets": 6,
    "sanitizer_cases": 4,
    "owned_sanitizer_cases": 2,
    "inherited_sanitizer_cases": 2,
    "mutants": 14,
    "mutation_test_source_files": 16,
    "critical_mutants": 8,
    "high_mutants": 6,
    "pull_request_mutants": 7,
    "full_mutants": 14,
}
LINUX_TARGET = "x86_64-unknown-linux-gnu"
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2}


class DeepQualityError(ValueError):
    """A deterministic deep-quality contract or evidence failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DeepQualityError("invalid-json", f"{path} must contain an object")
    return value


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_fingerprint(manifest: Mapping[str, object]) -> str:
    payload = dict(manifest)
    payload.pop("manifest_fingerprint", None)
    return fingerprint(payload)


def _schema() -> dict[str, Any]:
    return load_json(SCHEMA_PATH)


def _validate_schema(value: Mapping[str, object], *, label: str) -> None:
    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        raise DeepQualityError("schema", f"{label}: {errors[0].message}")


def _unique_ids(rows: Sequence[Mapping[str, object]], *, label: str) -> list[str]:
    ids = [cast(str, row["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise DeepQualityError("duplicate-id", f"{label} IDs must be unique")
    return ids


def _validate_source(source: Mapping[str, object], *, root: Path) -> None:
    relative = cast(str, source["path"])
    path = root / relative
    if not path.is_file():
        raise DeepQualityError("missing-source", f"missing governed source {relative}")
    observed = file_fingerprint(path)
    if observed != source["sha256"]:
        raise DeepQualityError(
            "stale-source", f"source fingerprint changed for {relative}"
        )


def _profile_partitions(manifest: Mapping[str, object]) -> dict[str, dict[str, Any]]:
    rows = cast(list[dict[str, Any]], manifest["profile_partitions"])
    ids = [row["id"] for row in rows]
    if ids != ["local", "pull-request", "full"]:
        raise DeepQualityError("profile-partition", "profile partition order changed")
    return {row["id"]: row for row in rows}


def _validate_properties(manifest: Mapping[str, object], *, root: Path) -> None:
    rows = cast(list[dict[str, Any]], manifest["property_suites"])
    if _unique_ids(rows, label="property suite") != PROPERTY_IDS:
        raise DeepQualityError(
            "property-denominator", "property suite denominator changed"
        )
    source_paths: list[str] = []
    for row in rows:
        if row["profiles"] != ["pull-request", "full"]:
            raise DeepQualityError(
                "profile-partition", f"property profile changed for {row['id']}"
            )
        for source in row["sources"]:
            _validate_source(source, root=root)
            source_paths.append(source["path"])
    if len(source_paths) != 16 or len(source_paths) != len(set(source_paths)):
        raise DeepQualityError(
            "property-denominator",
            "property source denominator must be 16 unique files",
        )


def _validate_fuzz(manifest: Mapping[str, object], *, root: Path) -> None:
    rows = cast(list[dict[str, Any]], manifest["fuzz_targets"])
    expected = INHERITED_FUZZ_IDS + OWNED_FUZZ_IDS
    if _unique_ids(rows, label="fuzz target") != expected:
        raise DeepQualityError("fuzz-denominator", "fuzz target denominator changed")
    for row in rows:
        if row["profiles"] != ["full"]:
            raise DeepQualityError(
                "profile-partition", f"fuzz profile changed for {row['id']}"
            )
        inherited = row["id"] in INHERITED_FUZZ_IDS
        expected_owner = "p17-inherited" if inherited else "p18-t03"
        expected_state = "active"
        expected_operation = (
            "certification.interop-adversarial"
            if inherited
            else "certification.deep-quality-full"
        )
        expected_seed = 1471701 if inherited else 1471803
        if (
            row["ownership"] != expected_owner
            or row["state"] != expected_state
            or row["runner_operation"] != expected_operation
            or row["budget"]
            != {
                "runs": 10000,
                "seed": expected_seed,
                "max_len_bytes": 16384,
                "timeout_seconds": 10,
                "rss_limit_mb": 4096,
            }
        ):
            raise DeepQualityError(
                "fuzz-policy", f"fuzz policy changed for {row['id']}"
            )
        _validate_source(
            {"path": row["source_path"], "sha256": row["source_sha256"]},
            root=root,
        )
        if not inherited:
            if "corpus_seed_path" not in row or "corpus_seed_sha256" not in row:
                raise DeepQualityError(
                    "fuzz-corpus", f"owned fuzz target {row['id']} lacks a seed"
                )
            _validate_source(
                {
                    "path": row["corpus_seed_path"],
                    "sha256": row["corpus_seed_sha256"],
                },
                root=root,
            )
    cargo_manifest = (root / "bindings/interop/fuzz/Cargo.toml").read_text(
        encoding="utf-8"
    )
    if (
        "publish = false" not in cargo_manifest
        or 'libfuzzer-sys = "=0.4.13"' not in cargo_manifest
    ):
        raise DeepQualityError(
            "fuzz-license-boundary",
            "the governed publish-false libfuzzer dependency root changed",
        )


def _validate_sanitizers(manifest: Mapping[str, object]) -> None:
    rows = cast(list[dict[str, Any]], manifest["sanitizer_cases"])
    expected = INHERITED_SANITIZER_IDS + OWNED_SANITIZER_IDS
    if _unique_ids(rows, label="sanitizer case") != expected:
        raise DeepQualityError(
            "sanitizer-denominator", "sanitizer case denominator changed"
        )
    for row in rows:
        inherited = row["id"] in INHERITED_SANITIZER_IDS
        if (
            row["ownership"] != ("p17-inherited" if inherited else "p18-t03")
            or row["state"] != "active"
            or row["runner_operation"]
            != (
                "certification.interop-adversarial"
                if inherited
                else "certification.deep-quality-full"
            )
            or row["profiles"] != ["full"]
        ):
            raise DeepQualityError(
                "sanitizer-policy", f"sanitizer policy changed for {row['id']}"
            )


def _validate_mutants(manifest: Mapping[str, object], *, root: Path) -> None:
    policies = cast(list[dict[str, Any]], manifest["mutation_policies"])
    if [policy["criticality"] for policy in policies] != ["critical", "high"]:
        raise DeepQualityError("mutation-policy", "mutation criticality order changed")
    if any(
        policy["minimum_kill_basis_points"] != 10000
        or policy["maximum_survivors"] != 0
        or policy["survivor_disposition"]
        != "blocking-until-killed-or-separately-authorized"
        for policy in policies
    ):
        raise DeepQualityError(
            "mutation-policy", "critical and high mutations must have zero survivors"
        )

    rows = cast(list[dict[str, Any]], manifest["mutants"])
    if _unique_ids(rows, label="mutant") != MUTANT_IDS:
        raise DeepQualityError("mutation-denominator", "mutant denominator changed")
    criticalities = Counter(row["criticality"] for row in rows)
    if criticalities != {"critical": 8, "high": 6}:
        raise DeepQualityError("mutation-policy", "mutation criticality counts changed")
    for row in rows:
        for source in cast(list[dict[str, Any]], row["test_sources"]):
            _validate_source(source, root=root)
        relative = cast(str, row["source_path"])
        if not (
            relative.startswith("core/src/")
            or relative == "tooling/product_certification.py"
        ):
            raise DeepQualityError(
                "mutation-boundary",
                f"mutant source is outside critical logic: {relative}",
            )
        source = {"path": relative, "sha256": row["source_sha256"]}
        _validate_source(source, root=root)
        text = (root / relative).read_text(encoding="utf-8")
        before = cast(str, row["before"])
        if text.count(before) < row["occurrence"]:
            raise DeepQualityError(
                "stale-mutation", f"mutant source token changed for {row['id']}"
            )
        if before == row["after"]:
            raise DeepQualityError("stale-mutation", f"mutant {row['id']} is a no-op")
        expected_profiles = (
            ["pull-request", "full"]
            if row["id"] in PULL_REQUEST_MUTANT_IDS
            else ["full"]
        )
        if row["profiles"] != expected_profiles:
            raise DeepQualityError(
                "profile-partition", f"mutant profile changed for {row['id']}"
            )
    test_source_paths = {
        source["path"]
        for row in rows
        for source in cast(list[dict[str, Any]], row["test_sources"])
    }
    if len(test_source_paths) != EXPECTED_COUNTS["mutation_test_source_files"]:
        raise DeepQualityError(
            "mutation-denominator", "mutation test-source denominator changed"
        )


def _validate_partitions(manifest: Mapping[str, object]) -> None:
    partitions = _profile_partitions(manifest)
    local = partitions["local"]
    pull_request = partitions["pull-request"]
    full = partitions["full"]
    for profile, partition in partitions.items():
        if partition["operation_id"] != PROFILE_OPERATION_IDS[profile]:
            raise DeepQualityError(
                "profile-partition", f"operation ID changed for {profile}"
            )
    if any(
        local[field]
        for field in (
            "property_suite_ids",
            "fuzz_target_ids",
            "sanitizer_case_ids",
            "mutant_ids",
            "required_companion_operations",
        )
    ):
        raise DeepQualityError("profile-partition", "Local must remain contract-only")
    if (
        pull_request["property_suite_ids"] != PROPERTY_IDS
        or pull_request["fuzz_target_ids"]
        or pull_request["sanitizer_case_ids"]
        or pull_request["mutant_ids"] != PULL_REQUEST_MUTANT_IDS
        or pull_request["required_companion_operations"]
    ):
        raise DeepQualityError("profile-partition", "Pull Request partition changed")
    if (
        full["property_suite_ids"] != PROPERTY_IDS
        or full["fuzz_target_ids"] != OWNED_FUZZ_IDS
        or full["sanitizer_case_ids"] != OWNED_SANITIZER_IDS
        or full["mutant_ids"] != MUTANT_IDS
        or full["required_companion_operations"]
        != ["certification.interop", "certification.interop-adversarial"]
    ):
        raise DeepQualityError("profile-partition", "Full partition changed")
    if [partitions[key]["maximum_duration_seconds"] for key in partitions] != [
        30,
        900,
        3600,
    ]:
        raise DeepQualityError("runtime-budget", "profile runtime budgets changed")


def validate_manifest(manifest: Mapping[str, object], *, root: Path = ROOT) -> None:
    _validate_schema(manifest, label="deep-quality manifest")
    if manifest["manifest_fingerprint"] != manifest_fingerprint(manifest):
        raise DeepQualityError("fingerprint", "manifest fingerprint differs")
    _validate_properties(manifest, root=root)
    _validate_fuzz(manifest, root=root)
    _validate_sanitizers(manifest)
    _validate_mutants(manifest, root=root)
    _validate_partitions(manifest)
    if manifest["expected_counts"] != EXPECTED_COUNTS:
        raise DeepQualityError("count-mismatch", "expected counts changed")


def expected_check_ids(manifest: Mapping[str, object], profile: str) -> list[str]:
    partition = _profile_partitions(manifest)[profile]
    return (
        ["contract:manifest"]
        + list(partition["property_suite_ids"])
        + list(partition["fuzz_target_ids"])
        + list(partition["sanitizer_case_ids"])
        + list(partition["mutant_ids"])
    )


def aggregate_status(statuses: Sequence[str]) -> str:
    if "failed" in statuses:
        return "failed"
    if "unavailable" in statuses:
        return "unavailable"
    return "passed"


def validate_evidence(
    evidence: Mapping[str, object],
    *,
    manifest: Mapping[str, object] | None = None,
    root: Path = ROOT,
) -> None:
    _validate_schema(evidence, label="deep-quality evidence")
    resolved = manifest or load_json(MANIFEST_PATH)
    validate_manifest(resolved, root=root)
    profile = cast(str, evidence["profile"])
    if evidence["operation_id"] != PROFILE_OPERATION_IDS[profile]:
        raise DeepQualityError("profile-mismatch", "evidence operation ID differs")
    deterministic = cast(dict[str, Any], evidence["deterministic_evidence"])
    if deterministic["manifest_fingerprint"] != resolved["manifest_fingerprint"]:
        raise DeepQualityError("stale-manifest", "evidence manifest identity is stale")
    if evidence["evidence_fingerprint"] != fingerprint(deterministic):
        raise DeepQualityError("fingerprint", "evidence fingerprint differs")
    checks = cast(list[dict[str, Any]], evidence["checks"])
    check_ids = [check["id"] for check in checks]
    if check_ids != expected_check_ids(resolved, profile):
        raise DeepQualityError(
            "check-denominator", "evidence check denominator changed"
        )
    if len(check_ids) != len(set(check_ids)):
        raise DeepQualityError("duplicate-id", "evidence check IDs must be unique")
    statuses = [check["status"] for check in checks]
    status_projection = [
        {"id": check["id"], "status": check["status"]} for check in checks
    ]
    if deterministic["check_status_fingerprint"] != fingerprint(status_projection):
        raise DeepQualityError(
            "fingerprint", "evidence check status fingerprint differs"
        )
    expected_status = aggregate_status(statuses)
    if evidence["status"] != expected_status:
        raise DeepQualityError(
            "aggregate-mismatch", "evidence status differs from checks"
        )
    counts = Counter(statuses)
    summary = deterministic["summary"]
    if summary != {
        "total": len(checks),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "unavailable": counts["unavailable"],
    }:
        raise DeepQualityError("aggregate-mismatch", "evidence summary differs")
    repository = deterministic["repository"]
    if evidence["evidence_kind"] == "live" and repository["dirty"] is not False:
        raise DeepQualityError(
            "dirty-evidence", "live evidence requires a clean commit"
        )


def supported_host(system: str | None = None, machine: str | None = None) -> bool:
    resolved_system = system or platform.system()
    resolved_machine = (machine or platform.machine()).lower()
    return resolved_system == "Linux" and resolved_machine in {"amd64", "x86_64"}


def _host_command(command: Sequence[str]) -> list[str]:
    resolved = list(command)
    if sys.platform == "win32" and resolved and resolved[0] == "python3":
        resolved[0] = sys.executable
    return resolved


def _run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    environment: Mapping[str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    started = time.monotonic()
    resolved_environment = dict(os.environ)
    resolved_environment["CARGO_NET_OFFLINE"] = "true"
    resolved_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if environment:
        resolved_environment.update(environment)
    try:
        completed = subprocess.run(
            _host_command(command),
            cwd=cwd,
            env=resolved_environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(1, timeout_seconds),
        )
    except FileNotFoundError as error:
        return "unavailable", {
            "command": list(command),
            "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
            "reason": str(error),
        }
    except subprocess.TimeoutExpired as error:
        combined = (error.stdout or "") + (error.stderr or "")
        return "failed", {
            "command": list(command),
            "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
            "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
            "reason": "command exceeded governed runtime budget",
            "timeout_seconds": timeout_seconds,
        }
    output = completed.stdout + completed.stderr
    details: dict[str, Any] = {
        "command": list(command),
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "return_code": completed.returncode,
    }
    if completed.returncode != 0:
        details["output_tail"] = output[-4000:]
    return ("passed" if completed.returncode == 0 else "failed"), details


def _remaining_seconds(started: float, maximum_seconds: int) -> int:
    elapsed = int(time.monotonic() - started)
    return max(1, maximum_seconds - elapsed)


def _repository_identity(root: Path) -> dict[str, object]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {"commit": commit, "dirty": bool(status.strip())}


def _copy_tracked_repository(root: Path, destination: Path) -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    for encoded in tracked:
        if not encoded:
            continue
        relative = Path(os.fsdecode(encoded))
        source = root / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _replace_occurrence(text: str, before: str, after: str, occurrence: int) -> str:
    start = 0
    index = -1
    for _ in range(occurrence):
        index = text.find(before, start)
        if index < 0:
            raise DeepQualityError(
                "stale-mutation", "mutation token occurrence is absent"
            )
        start = index + len(before)
    return text[:index] + after + text[index + len(before) :]


def _run_properties(
    manifest: Mapping[str, object],
    *,
    profile: str,
    root: Path,
    started: float,
    maximum_seconds: int,
) -> list[dict[str, Any]]:
    selected = set(_profile_partitions(manifest)[profile]["property_suite_ids"])
    checks: list[dict[str, Any]] = []
    for row in cast(list[dict[str, Any]], manifest["property_suites"]):
        if row["id"] not in selected:
            continue
        command = list(cast(list[str], row["command"]))
        if command[:2] == ["cargo", "+1.75.0"]:
            command.extend(
                ["--target-dir", str((root / PINNED_RUST_TARGET_DIRECTORY).resolve())]
            )
        status, details = _run_command(
            command,
            cwd=root,
            timeout_seconds=_remaining_seconds(started, maximum_seconds),
        )
        details["invariant"] = row["invariant"]
        checks.append({"id": row["id"], "status": status, "details": details})
    return checks


def _run_mutants(
    manifest: Mapping[str, object],
    *,
    profile: str,
    root: Path,
    started: float,
    maximum_seconds: int,
) -> list[dict[str, Any]]:
    selected = set(_profile_partitions(manifest)[profile]["mutant_ids"])
    rows = [
        row
        for row in cast(list[dict[str, Any]], manifest["mutants"])
        if row["id"] in selected
    ]
    if not rows:
        return []
    checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(
        prefix="strling-deep-quality-mutation-"
    ) as temporary:
        isolated_root = Path(temporary) / "repository"
        isolated_root.mkdir()
        _copy_tracked_repository(root, isolated_root)
        target_dir = Path(temporary) / "cargo-target"
        environment = {"CARGO_TARGET_DIR": str(target_dir)}
        baseline_cache: dict[tuple[str, ...], tuple[str, dict[str, Any]]] = {}
        for row in rows:
            command = tuple(cast(list[str], row["command"]))
            if command not in baseline_cache:
                baseline_cache[command] = _run_command(
                    command,
                    cwd=isolated_root,
                    timeout_seconds=_remaining_seconds(started, maximum_seconds),
                    environment=environment,
                )
            baseline_status, baseline_details = baseline_cache[command]
            source = isolated_root / row["source_path"]
            original = source.read_text(encoding="utf-8")
            mutated = _replace_occurrence(
                original,
                cast(str, row["before"]),
                cast(str, row["after"]),
                cast(int, row["occurrence"]),
            )
            try:
                source.write_text(mutated, encoding="utf-8")
                mutation_status, mutation_details = _run_command(
                    command,
                    cwd=isolated_root,
                    timeout_seconds=_remaining_seconds(started, maximum_seconds),
                    environment=environment,
                )
            finally:
                source.write_text(original, encoding="utf-8")
            killed = (
                mutation_status == "failed"
                and mutation_details.get("return_code") is not None
            )
            status = "passed" if baseline_status == "passed" and killed else "failed"
            if baseline_status == "unavailable" or mutation_status == "unavailable":
                status = "unavailable"
            checks.append(
                {
                    "id": row["id"],
                    "status": status,
                    "details": {
                        "baseline": baseline_details,
                        "category": row["category"],
                        "criticality": row["criticality"],
                        "isolated_temporary_copy": True,
                        "killed": killed,
                        "mutation": mutation_details,
                        "source_path": row["source_path"],
                    },
                }
            )
    return checks


def _fuzz_tool_identity(root: Path, timeout_seconds: int) -> tuple[str, dict[str, Any]]:
    rust_status, rust = _run_command(
        ["rustc", "+nightly-2026-08-01", "-vV"],
        cwd=root,
        timeout_seconds=timeout_seconds,
    )
    fuzz_status, cargo_fuzz = _run_command(
        ["cargo", "+nightly-2026-08-01", "fuzz", "--version"],
        cwd=root,
        timeout_seconds=timeout_seconds,
    )
    status = aggregate_status([rust_status, fuzz_status])
    details = {"cargo_fuzz": cargo_fuzz, "rust": rust}
    if status == "passed":
        rust_output = subprocess.run(
            ["rustc", "+nightly-2026-08-01", "-vV"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        fuzz_output = subprocess.run(
            ["cargo", "+nightly-2026-08-01", "fuzz", "--version"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if (
            "release: " not in rust_output
            or "-nightly" not in rust_output
            or f"host: {LINUX_TARGET}" not in rust_output
            or "cargo-fuzz 0.13.2" not in fuzz_output
        ):
            status = "failed"
            details["reason"] = "governed fuzz tool identity differs"
    return status, details


def _run_fuzz_targets(
    manifest: Mapping[str, object],
    *,
    root: Path,
    started: float,
    maximum_seconds: int,
) -> list[dict[str, Any]]:
    selected = set(_profile_partitions(manifest)["full"]["fuzz_target_ids"])
    rows = [
        row
        for row in cast(list[dict[str, Any]], manifest["fuzz_targets"])
        if row["id"] in selected
    ]
    identity_status, identity = _fuzz_tool_identity(
        root, _remaining_seconds(started, maximum_seconds)
    )
    checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="strling-deep-quality-fuzz-") as temporary:
        corpus_root = Path(temporary)
        for row in rows:
            budget = row["budget"]
            if identity_status != "passed":
                checks.append(
                    {"id": row["id"], "status": identity_status, "details": identity}
                )
                continue
            corpus = corpus_root / row["cargo_target"]
            corpus.mkdir()
            shutil.copy2(root / row["corpus_seed_path"], corpus / "canonical-seed")
            command = [
                "cargo",
                "+nightly-2026-08-01",
                "fuzz",
                "run",
                "--fuzz-dir",
                str(root / "bindings/interop/fuzz"),
                row["cargo_target"],
                str(corpus),
                "--",
                f"-runs={budget['runs']}",
                f"-seed={budget['seed']}",
                f"-max_len={budget['max_len_bytes']}",
                f"-timeout={budget['timeout_seconds']}",
                f"-rss_limit_mb={budget['rss_limit_mb']}",
            ]
            status, details = _run_command(
                command,
                cwd=root,
                timeout_seconds=_remaining_seconds(started, maximum_seconds),
            )
            details["budget"] = budget
            details["isolated_temporary_corpus"] = True
            details["seed_sha256"] = row["corpus_seed_sha256"]
            details["tool_identity"] = identity
            checks.append({"id": row["id"], "status": status, "details": details})
    return checks


def _run_sanitizer_case(
    case_id: str,
    *,
    root: Path,
    started: float,
    maximum_seconds: int,
) -> dict[str, Any]:
    binding = "c" if case_id == OWNED_SANITIZER_IDS[0] else "cpp"
    with tempfile.TemporaryDirectory(
        prefix=f"strling-deep-quality-{binding}-"
    ) as temporary:
        build = Path(temporary) / "build"
        common_flags = "-fsanitize=address,undefined -fno-omit-frame-pointer"
        configure = [
            "cmake",
            "-S",
            str(root / "bindings" / binding),
            "-B",
            str(build),
            "-DBUILD_TESTING=ON",
            "-DCMAKE_BUILD_TYPE=Debug",
            f"-DCMAKE_EXE_LINKER_FLAGS={common_flags}",
        ]
        if binding == "c":
            configure.append(f"-DCMAKE_C_FLAGS={common_flags}")
        else:
            configure.extend(
                [
                    "-DSTRLING_CPP_ENABLE_SANITIZERS=ON",
                    f"-DCMAKE_C_FLAGS={common_flags}",
                    f"-DCMAKE_CXX_FLAGS={common_flags}",
                ]
            )
        environment = {
            "ASAN_OPTIONS": "detect_leaks=1:halt_on_error=1:abort_on_error=1",
            "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1",
        }
        steps: list[dict[str, Any]] = []
        status = "passed"
        for command in (
            configure,
            ["cmake", "--build", str(build), "--parallel", "2"],
            ["ctest", "--test-dir", str(build), "--output-on-failure"],
        ):
            step_status, details = _run_command(
                command,
                cwd=root,
                timeout_seconds=_remaining_seconds(started, maximum_seconds),
                environment=environment,
            )
            steps.append({"status": step_status, **details})
            if step_status != "passed":
                status = step_status
                break
        return {
            "id": case_id,
            "status": status,
            "details": {
                "host": LINUX_TARGET,
                "isolated_temporary_build": True,
                "sanitizers": ["address", "undefined"],
                "steps": steps,
                "surface": binding,
            },
        }


def _build_evidence(
    manifest: Mapping[str, object],
    *,
    profile: str,
    started: float,
    checks: Sequence[Mapping[str, object]],
    root: Path,
) -> dict[str, Any]:
    statuses = [cast(str, check["status"]) for check in checks]
    counts = Counter(statuses)
    deterministic = {
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "check_status_fingerprint": fingerprint(
            [{"id": check["id"], "status": check["status"]} for check in checks]
        ),
        "repository": _repository_identity(root),
        "summary": {
            "total": len(checks),
            "passed": counts["passed"],
            "failed": counts["failed"],
            "unavailable": counts["unavailable"],
        },
    }
    return {
        "schema_version": "certification-result-v1",
        "evidence_kind": "live",
        "operation_id": PROFILE_OPERATION_IDS[profile],
        "profile": profile,
        "status": aggregate_status(statuses),
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": list(checks),
        "deterministic_evidence": deterministic,
        "evidence_fingerprint": fingerprint(deterministic),
    }


def certify(
    profile: str,
    *,
    root: Path = ROOT,
    manifest: Mapping[str, object] | None = None,
) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    resolved = manifest or load_json(MANIFEST_PATH)
    validate_manifest(resolved, root=root)
    maximum_seconds = cast(
        int, _profile_partitions(resolved)[profile]["maximum_duration_seconds"]
    )
    checks: list[dict[str, Any]] = [
        {
            "id": "contract:manifest",
            "status": "passed",
            "details": {"manifest_fingerprint": resolved["manifest_fingerprint"]},
        }
    ]
    checks.extend(
        _run_properties(
            resolved,
            profile=profile,
            root=root,
            started=started,
            maximum_seconds=maximum_seconds,
        )
    )
    if profile == "full":
        if supported_host():
            checks.extend(
                _run_fuzz_targets(
                    resolved,
                    root=root,
                    started=started,
                    maximum_seconds=maximum_seconds,
                )
            )
            for case_id in OWNED_SANITIZER_IDS:
                checks.append(
                    _run_sanitizer_case(
                        case_id,
                        root=root,
                        started=started,
                        maximum_seconds=maximum_seconds,
                    )
                )
        else:
            for case_id in OWNED_FUZZ_IDS + OWNED_SANITIZER_IDS:
                checks.append(
                    {
                        "id": case_id,
                        "status": "unavailable",
                        "details": {
                            "host_platform": platform.platform(),
                            "reason": "governed fuzz and sanitizers require x86_64 Linux",
                            "required_target": LINUX_TARGET,
                        },
                    }
                )
    checks.extend(
        _run_mutants(
            resolved,
            profile=profile,
            root=root,
            started=started,
            maximum_seconds=maximum_seconds,
        )
    )
    evidence = _build_evidence(
        resolved, profile=profile, started=started, checks=checks, root=root
    )
    if evidence["deterministic_evidence"]["repository"]["dirty"] is False:
        validate_evidence(evidence, manifest=resolved, root=root)
    status = cast(str, evidence["status"])
    return evidence, EXIT_CODES[status]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--profile", choices=tuple(PROFILE_OPERATION_IDS))
    args = parser.parse_args(argv)
    manifest = load_json(MANIFEST_PATH)
    if args.profile is not None:
        result, exit_code = certify(args.profile, manifest=manifest)
        serialized = json.dumps(result, sort_keys=True)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized + "\n", encoding="utf-8")
        if args.json_output:
            print(serialized)
        else:
            print(
                f"DEEP_QUALITY_CERTIFICATION profile={args.profile} "
                f"status={result['status']} checks={len(result['checks'])}"
            )
        return exit_code
    validate_manifest(manifest)
    fixture_count = 0
    if FIXTURE_PATH.exists():
        validate_evidence(load_json(FIXTURE_PATH), manifest=manifest)
        fixture_count = 1
    result = {
        "status": "passed",
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "property_suites": len(manifest["property_suites"]),
        "fuzz_targets": len(manifest["fuzz_targets"]),
        "sanitizer_cases": len(manifest["sanitizer_cases"]),
        "mutants": len(manifest["mutants"]),
        "fixtures": fixture_count,
    }
    if args.json_output:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            "DEEP_QUALITY_CONTRACT "
            + " ".join(f"{key}={value}" for key, value in result.items())
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
