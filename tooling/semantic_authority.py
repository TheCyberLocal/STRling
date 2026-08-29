#!/usr/bin/env python3
"""Certify that only current structured/spec-authored semantic authority is live."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "tests" / "architecture" / "semantic-authority" / "1.0"
POLICY_PATH = EVIDENCE_ROOT / "policy.json"
POLICY_SCHEMA_PATH = EVIDENCE_ROOT / "policy.schema.json"
EVIDENCE_SCHEMA_PATH = EVIDENCE_ROOT / "evidence.schema.json"
EVIDENCE_PATH = EVIDENCE_ROOT / "evidence.json"
TOOLCHAIN_PATH = ROOT / "toolchain.json"
REGISTRY_PATH = ROOT / "governance" / "generated-artifacts.json"
PRODUCT_MANIFEST_PATH = (
    ROOT / "tests" / "certification" / "product" / "1.0" / "producer-manifest.json"
)
OPERATION_ID = "certification.semantic-authority"


class SemanticAuthorityError(RuntimeError):
    """Raised when obsolete semantic authority remains reachable."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SemanticAuthorityError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise SemanticAuthorityError(f"{path} must contain one object")
    return value


def _validate(schema: Mapping[str, Any], value: Mapping[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "/".join(str(item) for item in error.absolute_path) or "<root>"
        raise SemanticAuthorityError(
            f"schema validation at {location}: {error.message}"
        )


def _fingerprint(value: Mapping[str, Any], excluded: set[str] | None = None) -> str:
    normalized = {
        key: item for key, item in value.items() if key not in (excluded or set())
    }
    payload = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _matches(pattern: str) -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.glob(pattern)
        if path.is_file()
    )


def _decision_files(patterns: Sequence[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(files)


def build_evidence() -> dict[str, Any]:
    policy = _load(POLICY_PATH)
    _validate(_load(POLICY_SCHEMA_PATH), policy)
    toolchain = _load(TOOLCHAIN_PATH)
    registry = _load(REGISTRY_PATH)
    product = _load(PRODUCT_MANIFEST_PATH)
    operation = policy["structured_operation"]
    retired_operations = set(policy["retired_operation_ids"])
    operation_registry = toolchain["policy"]["operation_registry"]

    if retired_operations & set(operation_registry):
        raise SemanticAuthorityError("retired operation remains registered")
    definition = operation_registry.get(operation["id"])
    if not isinstance(definition, dict):
        raise SemanticAuthorityError(
            "structured semantic-authority operation is missing"
        )
    if (
        definition.get("result_contract") != operation["contract"]
        or definition.get("result_operation_id") != operation["operation_id"]
    ):
        raise SemanticAuthorityError("structured semantic-authority identity changed")

    profile_rows: list[dict[str, Any]] = []
    for profile_id in policy["profile_ids"]:
        profile = toolchain["policy"]["profiles"][profile_id]
        members = [entry["operation"] for entry in profile["operations"]]
        if members.count(operation["id"]) != 1:
            raise SemanticAuthorityError(
                f"{profile_id}: semantic-authority operation must appear exactly once"
            )
        if retired_operations & set(members):
            raise SemanticAuthorityError(
                f"{profile_id}: retired operation remains live"
            )
        profile_rows.append(
            {
                "id": profile_id,
                "definition_version": profile["definition_version"],
                "operation_count": len(members),
            }
        )

    retired_matches = {
        pattern: _matches(pattern) for pattern in policy["retired_path_patterns"]
    }
    live_retired = {
        pattern: paths for pattern, paths in retired_matches.items() if paths
    }
    if live_retired:
        pattern = sorted(live_retired)[0]
        raise SemanticAuthorityError(
            f"retired authority path remains for {pattern}: {live_retired[pattern][0]}"
        )

    history = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tooling" / "legacy_reference").rglob("*")
        if path.is_file()
    )
    if history != sorted(policy["historical_files"]):
        raise SemanticAuthorityError("historical reference directory is not data-only")

    decision_hits: list[dict[str, str]] = []
    scraping_hits: list[dict[str, str]] = []
    for path in _decision_files(policy["decision_sources"]):
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        for token in policy["forbidden_decision_tokens"]:
            if token in text:
                decision_hits.append({"path": relative, "token": token})
        for token in policy["forbidden_semantic_scraping_tokens"]:
            if token in text:
                scraping_hits.append({"path": relative, "token": token})
    if decision_hits:
        raise SemanticAuthorityError(
            f"obsolete decision token remains: {decision_hits[0]}"
        )
    if scraping_hits:
        raise SemanticAuthorityError(
            f"semantic stdout/test-name authority remains: {scraping_hits[0]}"
        )

    artifacts = registry["artifacts"]
    artifact_ids = {artifact["id"] for artifact in artifacts}
    retired_artifacts = set(policy["retired_generated_artifact_ids"])
    if retired_artifacts & artifact_ids:
        raise SemanticAuthorityError("retired oracle artifact remains registered")
    retired_input_markers = (
        "tooling/js_to_json_ast",
        "tooling/legacy_reference",
        "tooling/migration_",
        "tests/spec/",
    )
    active_oracles: list[dict[str, str]] = []
    for artifact in artifacts:
        if artifact.get("enforcement") != "enforced":
            continue
        inputs = [
            *artifact.get("authoritative_sources", []),
            *artifact.get("generator_inputs", []),
            *artifact["generator"].get("implementation_paths", []),
        ]
        for source in inputs:
            if any(marker in source for marker in retired_input_markers):
                active_oracles.append({"artifact": artifact["id"], "source": source})
    if active_oracles:
        raise SemanticAuthorityError(
            f"enforced generated artifact consumes retired authority: {active_oracles[0]}"
        )

    producer_ids = [entry["operation_id"] for entry in product["producers"]]
    if producer_ids.count(operation["id"]) != 1:
        raise SemanticAuthorityError(
            "product producer manifest must consume semantic authority exactly once"
        )
    if retired_operations & set(producer_ids):
        raise SemanticAuthorityError("product producer consumes retired authority")
    claim_ids = [claim["claim_id"] for claim in product["claims"]]
    if any(claim_id.startswith("omega.") for claim_id in claim_ids):
        raise SemanticAuthorityError("Omega claim identity remains current")

    checks = [
        {
            "id": "profiles-use-structured-authority",
            "status": "passed",
            "details": {"profiles": profile_rows, "operation": operation},
        },
        {
            "id": "retired-operations-absent",
            "status": "passed",
            "details": {"operation_ids": sorted(retired_operations)},
        },
        {
            "id": "retired-authority-paths-absent",
            "status": "passed",
            "details": {"patterns": policy["retired_path_patterns"]},
        },
        {
            "id": "historical-evidence-data-only",
            "status": "passed",
            "details": {"files": history},
        },
        {
            "id": "generated-lineage-current",
            "status": "passed",
            "details": {"active_generated_oracles": active_oracles},
        },
        {
            "id": "product-consumes-structured-authority",
            "status": "passed",
            "details": {"producer_operation": operation["id"], "claims": claim_ids},
        },
        {
            "id": "semantic-scraping-absent",
            "status": "passed",
            "details": {"stdout_or_test_name_authority": scraping_hits},
        },
    ]
    evidence: dict[str, Any] = {
        "$schema": "evidence.schema.json",
        "artifact_kind": "strling.semantic-authority-evidence",
        "schema_version": "1.0.0",
        "policy_fingerprint": _fingerprint(policy),
        "checks": checks,
        "summary": {
            "status": "passed",
            "profile_count": len(profile_rows),
            "retired_operation_count": len(retired_operations),
            "retired_path_count": len(policy["retired_path_patterns"]),
            "historical_file_count": len(history),
            "active_generated_oracle_count": len(active_oracles),
            "semantic_scraping_count": len(scraping_hits),
        },
    }
    evidence["fingerprint"] = _fingerprint(evidence)
    _validate(_load(EVIDENCE_SCHEMA_PATH), evidence)
    return evidence


def _write() -> dict[str, Any]:
    evidence = build_evidence()
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    return evidence


def _check() -> dict[str, Any]:
    expected = build_evidence()
    actual = _load(EVIDENCE_PATH)
    if actual != expected:
        raise SemanticAuthorityError("checked-in semantic-authority evidence is stale")
    if actual["fingerprint"] != _fingerprint(actual, {"fingerprint"}):
        raise SemanticAuthorityError("semantic-authority fingerprint is not canonical")
    return actual


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [
            {
                "id": "certification.semantic-authority.current-only",
                "status": status,
                "details": dict(details),
            }
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.write and not args.check:
        args.check = True
    started = time.monotonic()
    try:
        evidence = _write() if args.write else _check()
        result = _result("passed", started, evidence["summary"])
    except Exception as error:
        result = _result(
            "failed",
            started,
            {"error_type": type(error).__name__, "reason": str(error)},
        )
    print(json.dumps(result, sort_keys=True) if args.json else result)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
