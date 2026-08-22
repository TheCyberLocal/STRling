#!/usr/bin/env python3
"""Deterministic product certification assembled from structured profile evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

_certification = importlib.import_module(
    "tooling.certification" if __package__ else "certification"
)
CertificationError = _certification.CertificationError
profile_definition_fingerprint = _certification.profile_definition_fingerprint
repository_state = _certification.repository_state
validate_certification_artifact = _certification.validate_certification_artifact


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "strling-product-certification"
MANIFEST_KIND = "strling-product-certification-producers"
CHECK_OPERATION_ID = "certification.product-authority"
ARTIFACT_SCHEMA_PATH = Path(
    "governance/schemas/product-certification-artifact.schema.json"
)
MANIFEST_SCHEMA_PATH = Path(
    "governance/schemas/product-certification-producer-manifest.schema.json"
)
MANIFEST_PATH = Path("tests/certification/product/1.0/producer-manifest.json")
FIXTURE_PATH = Path("tests/certification/product/1.0/fixtures/valid-product.json")
MUTATIONS_PATH = Path("tests/certification/product/1.0/fixtures/mutations.json")
TOOLCHAIN_PATH = Path("toolchain.json")
RESULT_STATUSES = (
    "passed",
    "failed",
    "waived",
    "skipped",
    "unavailable",
    "incomplete",
    "not_applicable",
    "not_yet_configured",
    "not_yet_enforceable",
)
CLAIM_STATUSES = ("passed", "failed", "waived", "unavailable", "incomplete")
INCOMPLETE_STATUSES = {
    "incomplete",
    "not_yet_configured",
    "not_yet_enforceable",
    "skipped",
}
BLOCKING_STATUSES = {"failed", "unavailable", *INCOMPLETE_STATUSES}
CERTIFICATION_PROFILE_IDS = ("full", "release")


class ProductCertificationError(ValueError):
    """A stable fail-closed product-certification rejection."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path, *, code: str = "invalid-input") -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductCertificationError(code, f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProductCertificationError(code, f"{path} must contain a JSON object")
    return value


def _validate_schema(
    instance: Mapping[str, object], schema_path: Path, *, label: str
) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
    except (OSError, json.JSONDecodeError, SchemaError, ValidationError) as exc:
        raise ProductCertificationError(
            "schema-invalid", f"invalid {label}: {exc}"
        ) from exc


def aggregate_product_status(statuses: Iterable[str]) -> str:
    """Apply the versioned product aggregate policy."""

    observed = set(statuses)
    unknown = observed.difference(RESULT_STATUSES).difference(CLAIM_STATUSES)
    if unknown:
        raise ProductCertificationError(
            "aggregate-mismatch", f"unknown status {sorted(unknown)[0]!r}"
        )
    if "failed" in observed:
        return "failed"
    if observed.intersection(INCOMPLETE_STATUSES):
        return "incomplete"
    if "unavailable" in observed:
        return "unavailable"
    if "waived" in observed:
        return "waived"
    return "passed"


def aggregate_exit_code(statuses: Iterable[str]) -> int:
    observed = tuple(statuses)
    aggregate_product_status(observed)
    return 1 if any(status in BLOCKING_STATUSES for status in observed) else 0


def _governed_waiver_ids(root: Path) -> set[str]:
    return {path.stem for path in (root / "governance/waivers").glob("*.yaml")}


def _preflight_waivers(results: Sequence[Mapping[str, object]], root: Path) -> None:
    governed = _governed_waiver_ids(root)
    for result in results:
        status = result.get("status")
        references = result.get("waiver_references", [])
        if not isinstance(references, list) or not all(
            isinstance(item, str) for item in references
        ):
            raise ProductCertificationError(
                "invalid-waiver", "waiver references must be a string array"
            )
        if status == "waived" and not references:
            raise ProductCertificationError(
                "invalid-waiver", "waived evidence requires a governed waiver ID"
            )
        unknown = sorted(set(references).difference(governed))
        if unknown:
            raise ProductCertificationError(
                "invalid-waiver", f"unknown governed waiver ID {unknown[0]!r}"
            )


def _certification_profile(
    toolchain: Mapping[str, object], profile_id: str
) -> dict[str, Any]:
    if profile_id not in CERTIFICATION_PROFILE_IDS:
        raise ProductCertificationError(
            "stale-profile", f"unsupported certification profile {profile_id!r}"
        )
    try:
        policy = cast(dict[str, Any], toolchain["policy"])
        profiles = cast(dict[str, Any], policy["profiles"])
        profile = cast(dict[str, Any], profiles[profile_id])
    except (KeyError, TypeError) as exc:
        raise ProductCertificationError(
            "stale-profile",
            f"toolchain.json does not define the {profile_id!r} profile",
        ) from exc
    return profile


def _operation_registry(toolchain: Mapping[str, object]) -> dict[str, dict[str, Any]]:
    try:
        policy = cast(dict[str, Any], toolchain["policy"])
        return cast(dict[str, dict[str, Any]], policy["operation_registry"])
    except (KeyError, TypeError) as exc:
        raise ProductCertificationError(
            "stale-toolchain", "toolchain.json has no operation registry"
        ) from exc


def expected_profile_result_ids(
    toolchain: Mapping[str, object], profile_id: str = "full"
) -> list[str]:
    profile = _certification_profile(toolchain, profile_id)
    registry = _operation_registry(toolchain)
    members = profile.get("operations")
    if not isinstance(members, list):
        raise ProductCertificationError(
            "stale-profile", f"{profile_id!r} profile operations must be an array"
        )
    result_ids: list[str] = []
    for member in members:
        if not isinstance(member, dict) or not isinstance(member.get("operation"), str):
            raise ProductCertificationError(
                "stale-profile",
                f"{profile_id!r} profile member has no operation identity",
            )
        operation_id = cast(str, member["operation"])
        definition = registry.get(operation_id)
        if not isinstance(definition, dict):
            raise ProductCertificationError(
                "stale-profile",
                f"unknown {profile_id!r}-profile operation {operation_id!r}",
            )
        if definition.get("kind") == "repository":
            component = definition.get("component")
            if not isinstance(component, str):
                raise ProductCertificationError(
                    "stale-toolchain",
                    f"repository operation {operation_id!r} has no component",
                )
            result_ids.append(f"{operation_id}@{component}")
            continue
        targets = member.get("targets")
        if not isinstance(targets, list) or not all(
            isinstance(target, str) for target in targets
        ):
            raise ProductCertificationError(
                "stale-profile",
                f"component operation {operation_id!r} has no {profile_id!r} target list",
            )
        result_ids.extend(f"{operation_id}@{target}" for target in targets)
    return result_ids


def validate_producer_manifest(
    root: Path,
    manifest: Mapping[str, object],
    toolchain: Mapping[str, object],
) -> None:
    _validate_schema(
        manifest,
        root / MANIFEST_SCHEMA_PATH,
        label="product certification producer manifest",
    )
    if manifest.get("manifest_kind") != MANIFEST_KIND:
        raise ProductCertificationError(
            "stale-manifest", "producer manifest kind is unsupported"
        )

    profiles: dict[str, dict[str, Any]] = {}
    for profile_id, manifest_key in (
        ("full", "source_profile"),
        ("release", "release_profile"),
    ):
        profile = _certification_profile(toolchain, profile_id)
        declared = cast(dict[str, Any], manifest[manifest_key])
        if declared.get("id") != profile_id or declared.get(
            "definition_fingerprint"
        ) != profile_definition_fingerprint(profile):
            raise ProductCertificationError(
                "stale-profile",
                f"producer manifest {profile_id!r}-profile fingerprint is stale",
            )
        profiles[profile_id] = profile

    full_members = cast(list[dict[str, Any]], profiles["full"]["operations"])
    release_members = cast(list[dict[str, Any]], profiles["release"]["operations"])
    if full_members != release_members:
        raise ProductCertificationError(
            "stale-profile",
            "Full and release profile memberships differ for product certification",
        )

    members = full_members
    expected_operations = [cast(str, member["operation"]) for member in members]
    producers = cast(list[dict[str, Any]], manifest["producers"])
    actual_operations = [cast(str, producer["operation_id"]) for producer in producers]
    if len(actual_operations) != len(set(actual_operations)):
        raise ProductCertificationError(
            "duplicate-result", "producer manifest contains a duplicate operation"
        )
    if actual_operations != expected_operations:
        missing = sorted(set(expected_operations).difference(actual_operations))
        unknown = sorted(set(actual_operations).difference(expected_operations))
        if missing:
            raise ProductCertificationError(
                "missing-result", f"producer manifest misses {missing[0]!r}"
            )
        if unknown:
            raise ProductCertificationError(
                "unknown-result", f"producer manifest adds {unknown[0]!r}"
            )
        raise ProductCertificationError(
            "conflicting-result",
            "producer manifest order differs from certification profiles",
        )

    registry = _operation_registry(toolchain)
    used_areas: set[str] = set()
    for producer in producers:
        operation_id = cast(str, producer["operation_id"])
        definition = registry[operation_id]
        used_areas.add(cast(str, producer["evidence_area"]))
        if producer.get("result_contract") != definition.get("result_contract"):
            raise ProductCertificationError(
                "conflicting-result",
                f"result contract differs for {operation_id!r}",
            )
        if producer.get("structured_operation_id") != definition.get(
            "result_operation_id"
        ):
            raise ProductCertificationError(
                "conflicting-result",
                f"structured operation identity differs for {operation_id!r}",
            )
    if used_areas != set(cast(list[str], manifest["evidence_areas"])):
        raise ProductCertificationError(
            "stale-manifest", "declared evidence areas do not match producer usage"
        )

    claims = cast(list[dict[str, Any]], manifest["claims"])
    claim_ids = [cast(str, claim["claim_id"]) for claim in claims]
    required_claims = {
        "product.full-profile-coverage",
        "omega.duplicate-name-contract",
        "omega.range-contract",
        "omega.essential-five-contract",
    }
    if len(claim_ids) != len(set(claim_ids)) or set(claim_ids) != required_claims:
        raise ProductCertificationError(
            "stale-manifest", "producer manifest claim coverage is incomplete"
        )
    known = set(actual_operations)
    for claim in claims:
        source = cast(dict[str, Any], claim["source"])
        operations = source.get("operations")
        if isinstance(operations, list):
            unknown = sorted(set(cast(list[str], operations)).difference(known))
            if unknown:
                raise ProductCertificationError(
                    "unknown-result",
                    f"claim {claim['claim_id']!r} references {unknown[0]!r}",
                )


def _producer_map(manifest: Mapping[str, object]) -> dict[str, dict[str, Any]]:
    return {
        cast(str, producer["operation_id"]): producer
        for producer in cast(list[dict[str, Any]], manifest["producers"])
    }


def _result_id_fingerprint(result_ids: Sequence[str]) -> str:
    return fingerprint(sorted(result_ids))


def _identity(
    kind: str,
    identity: str,
    *,
    version: str | None = None,
    identity_fingerprint: str | None = None,
    path: str | None = None,
) -> dict[str, object]:
    return {
        "kind": kind,
        "id": identity,
        "version": version,
        "fingerprint": identity_fingerprint,
        "path": path,
    }


def _product_result(
    source: Mapping[str, object],
    producer: Mapping[str, object],
    contract_versions: Mapping[str, object],
    source_index: int,
) -> dict[str, object]:
    operation_id = cast(str, source["operation_id"])
    component = cast(str, source["component"])
    result_contract = producer.get("result_contract")
    structured = source.get("structured_evidence")
    producer_evidence: dict[str, object] | None = None
    identities = [
        _identity("operation", operation_id, path="toolchain.json"),
        _identity("component", component),
    ]
    if result_contract is not None:
        if not isinstance(structured, dict):
            raise ProductCertificationError(
                "missing-result", f"structured evidence is absent for {operation_id!r}"
            )
        expected_operation = producer.get("structured_operation_id")
        version_identity = producer.get("payload_version_override")
        if not isinstance(version_identity, dict):
            version_identity = cast(dict[str, Any], contract_versions[result_contract])
        version_field = cast(str, version_identity["field"])
        version_value = cast(str, version_identity["value"])
        if (
            structured.get(version_field) != version_value
            or structured.get("operation_id") != expected_operation
            or structured.get("status") != source.get("status")
        ):
            raise ProductCertificationError(
                "conflicting-result",
                f"structured evidence conflicts for {operation_id!r}",
            )
        payload_fingerprint = fingerprint(structured)
        producer_evidence = {
            "contract": result_contract,
            "schema_version": version_value,
            "operation_id": structured["operation_id"],
            "status": structured["status"],
            "duration_ms": None,
            "fingerprint": payload_fingerprint,
            "payload": copy.deepcopy(structured),
        }
        identities.append(
            _identity(
                "producer",
                cast(str, structured["operation_id"]),
                version=version_value,
                identity_fingerprint=payload_fingerprint,
            )
        )
    elif structured is not None:
        raise ProductCertificationError(
            "unknown-result",
            f"unregistered structured evidence exists for {operation_id!r}",
        )

    return {
        "result_id": f"{operation_id}@{component}",
        "operation_id": operation_id,
        "component": component,
        "evidence_area": producer["evidence_area"],
        "status": source["status"],
        "reason": source.get("reason"),
        "source_profile_index": source_index,
        "result_contract": result_contract,
        "producer_evidence": producer_evidence,
        "identities": identities,
        "evidence_links": [],
        "waiver_references": list(cast(list[str], source.get("waiver_references", []))),
    }


def _claims(
    manifest: Mapping[str, object], results: Sequence[Mapping[str, object]]
) -> list[dict[str, object]]:
    claims: list[dict[str, object]] = []
    for declaration in cast(list[dict[str, Any]], manifest["claims"]):
        source = cast(dict[str, Any], declaration["source"])
        selected: list[Mapping[str, object]]
        if source.get("all_profile_results") is True:
            selected = list(results)
        else:
            operations = set(cast(list[str], source["operations"]))
            selected = [
                result for result in results if result["operation_id"] in operations
            ]
        if not selected:
            raise ProductCertificationError(
                "missing-result", f"claim {declaration['claim_id']!r} has no evidence"
            )
        source_result_ids = sorted(cast(str, item["result_id"]) for item in selected)
        status = aggregate_product_status(
            cast(str, item["status"]) for item in selected
        )
        claims.append(
            {
                "claim_id": declaration["claim_id"],
                "description": declaration["description"],
                "evidence_area": declaration["evidence_area"],
                "status": status,
                "source_result_ids": source_result_ids,
            }
        )
    return claims


def _aggregate(
    results: Sequence[Mapping[str, object]], claims: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    result_statuses = [cast(str, result["status"]) for result in results]
    claim_statuses = [cast(str, claim["status"]) for claim in claims]
    result_counts = Counter(result_statuses)
    claim_counts = Counter(claim_statuses)
    combined = [*result_statuses, *claim_statuses]
    return {
        "status": aggregate_product_status(combined),
        "exit_code": aggregate_exit_code(combined),
        "result_count": len(results),
        "counts": {status: result_counts.get(status, 0) for status in RESULT_STATUSES},
        "claim_count": len(claims),
        "claim_counts": {
            status: claim_counts.get(status, 0) for status in CLAIM_STATUSES
        },
    }


def _profile_artifact_from_embedded(
    deterministic: Mapping[str, object], source: Mapping[str, object]
) -> dict[str, object]:
    return {
        "schema_version": source["artifact_schema_version"],
        "artifact_kind": source["artifact_kind"],
        "deterministic_evidence": deterministic["source_profile_evidence"],
        "evidence_fingerprint": source["evidence_fingerprint"],
        "execution_metadata": {"generated_at": "1970-01-01T00:00:00Z"},
    }


def build_product_artifact(
    *,
    root: Path,
    profile_artifact: Mapping[str, object],
    manifest: Mapping[str, object] | None = None,
    toolchain: Mapping[str, object] | None = None,
    resolved_repository_state: Mapping[str, object] | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    """Build one product artifact from one validated certification profile."""

    resolved_manifest = dict(manifest or load_json(root / MANIFEST_PATH))
    resolved_toolchain = dict(toolchain or load_json(root / TOOLCHAIN_PATH))
    validate_producer_manifest(root, resolved_manifest, resolved_toolchain)
    try:
        validate_certification_artifact(root, profile_artifact)
    except CertificationError as exc:
        raise ProductCertificationError("source-profile-fingerprint", str(exc)) from exc

    source_deterministic = profile_artifact.get("deterministic_evidence")
    if not isinstance(source_deterministic, dict):
        raise ProductCertificationError(
            "schema-invalid", "profile artifact has no deterministic evidence"
        )
    source_repository = cast(dict[str, Any], source_deterministic["repository"])
    current_repository = dict(resolved_repository_state or repository_state(root))
    if source_repository != current_repository:
        raise ProductCertificationError(
            "stale-repository",
            "profile artifact repository identity differs from the current repository",
        )
    profile = cast(dict[str, Any], source_deterministic["profile"])
    profile_id = profile.get("id")
    if not isinstance(profile_id, str) or profile_id not in CERTIFICATION_PROFILE_IDS:
        raise ProductCertificationError(
            "stale-profile", "source artifact is not a governed certification profile"
        )
    current_profile = _certification_profile(resolved_toolchain, profile_id)
    manifest_key = "source_profile" if profile_id == "full" else "release_profile"
    manifest_source = cast(dict[str, Any], resolved_manifest[manifest_key])
    if profile.get("definition_fingerprint") != manifest_source[
        "definition_fingerprint"
    ] or profile.get("definition_fingerprint") != profile_definition_fingerprint(
        current_profile
    ):
        raise ProductCertificationError(
            "stale-profile",
            "source artifact does not identify a governed certification profile",
        )
    scope = cast(dict[str, Any], source_deterministic["component_scope"])
    if scope != {"mode": "profile-default"}:
        raise ProductCertificationError(
            "missing-result",
            "product certification requires the complete certification profile",
        )

    source_operations = cast(list[dict[str, Any]], source_deterministic["operations"])
    expected_ids = expected_profile_result_ids(resolved_toolchain, profile_id)
    source_ids = [cast(str, operation["result_id"]) for operation in source_operations]
    _reject_result_set(source_ids, expected_ids)
    producers = _producer_map(resolved_manifest)
    contract_versions = cast(
        dict[str, object], resolved_manifest["result_contract_versions"]
    )
    results = [
        _product_result(
            operation,
            producers[cast(str, operation["operation_id"])],
            contract_versions,
            index,
        )
        for index, operation in enumerate(source_operations)
    ]
    _preflight_waivers(results, root)
    claims = _claims(resolved_manifest, results)
    structured_count = sum(
        1 for producer in producers.values() if producer["result_contract"] is not None
    )
    deterministic_evidence: dict[str, object] = {
        "repository": dict(source_repository),
        "authority": {
            "specification": dict(
                cast(dict[str, Any], resolved_manifest["specification"])
            ),
            "toolchain": {
                "path": str(TOOLCHAIN_PATH).replace("\\", "/"),
                "schema_version": resolved_toolchain["schema_version"],
                "fingerprint": fingerprint(resolved_toolchain),
            },
            "source_profile": {
                "artifact_schema_version": profile_artifact["schema_version"],
                "artifact_kind": profile_artifact["artifact_kind"],
                "profile_id": profile["id"],
                "definition_fingerprint": profile["definition_fingerprint"],
                "evidence_fingerprint": profile_artifact["evidence_fingerprint"],
            },
            "producer_manifest": {
                "schema_version": resolved_manifest["schema_version"],
                "path": str(MANIFEST_PATH).replace("\\", "/"),
                "fingerprint": fingerprint(resolved_manifest),
            },
        },
        "aggregate_policy": dict(
            cast(dict[str, Any], resolved_manifest["aggregate_policy"])
        ),
        "source_profile_evidence": source_deterministic,
        "coverage": {
            "expected_result_count": len(expected_ids),
            "observed_result_count": len(source_ids),
            "expected_result_ids_fingerprint": _result_id_fingerprint(expected_ids),
            "observed_result_ids_fingerprint": _result_id_fingerprint(source_ids),
            "expected_structured_producer_count": structured_count,
            "observed_structured_producer_count": sum(
                result["producer_evidence"] is not None for result in results
            ),
            "missing_result_ids": [],
            "unknown_result_ids": [],
        },
        "results": results,
        "claims": claims,
        "aggregate": _aggregate(results, claims),
    }
    artifact: dict[str, object] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "deterministic_evidence": deterministic_evidence,
        "evidence_fingerprint": fingerprint(deterministic_evidence),
        "presentation": {
            "generated_at": generated_at
            or datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        },
    }
    validate_product_artifact(
        root,
        artifact,
        manifest=resolved_manifest,
        toolchain=resolved_toolchain,
        resolved_repository_state=current_repository,
    )
    return artifact


def _reject_result_set(observed: Sequence[str], expected: Sequence[str]) -> None:
    duplicates = sorted(
        result_id for result_id, count in Counter(observed).items() if count > 1
    )
    if duplicates:
        raise ProductCertificationError(
            "duplicate-result", f"duplicate result identity {duplicates[0]!r}"
        )
    unknown = sorted(set(observed).difference(expected))
    if unknown:
        raise ProductCertificationError(
            "unknown-result", f"unknown result identity {unknown[0]!r}"
        )
    missing = sorted(set(expected).difference(observed))
    if missing:
        raise ProductCertificationError(
            "missing-result", f"missing required result {missing[0]!r}"
        )
    if list(observed) != list(expected):
        raise ProductCertificationError(
            "conflicting-result", "result order differs from the Full profile"
        )


def validate_product_artifact(
    root: Path,
    artifact: Mapping[str, object],
    *,
    manifest: Mapping[str, object] | None = None,
    toolchain: Mapping[str, object] | None = None,
    resolved_repository_state: Mapping[str, object] | None = None,
    enforce_current_repository: bool = True,
) -> None:
    """Validate schema, source integrity, coverage, aggregation, and fingerprints."""

    deterministic_preflight = artifact.get("deterministic_evidence")
    if isinstance(deterministic_preflight, dict):
        preflight_results = deterministic_preflight.get("results", [])
        if isinstance(preflight_results, list) and all(
            isinstance(item, dict) for item in preflight_results
        ):
            _preflight_waivers(cast(list[dict[str, Any]], preflight_results), root)
    _validate_schema(
        artifact, root / ARTIFACT_SCHEMA_PATH, label="product certification artifact"
    )

    deterministic = cast(dict[str, Any], artifact["deterministic_evidence"])
    authority = cast(dict[str, Any], deterministic["authority"])
    source_authority = cast(dict[str, Any], authority["source_profile"])
    embedded_profile = _profile_artifact_from_embedded(deterministic, source_authority)
    try:
        validate_certification_artifact(root, embedded_profile)
    except CertificationError as exc:
        raise ProductCertificationError("source-profile-fingerprint", str(exc)) from exc

    resolved_manifest = dict(manifest or load_json(root / MANIFEST_PATH))
    resolved_toolchain = dict(toolchain or load_json(root / TOOLCHAIN_PATH))
    validate_producer_manifest(root, resolved_manifest, resolved_toolchain)
    if authority["producer_manifest"]["fingerprint"] != fingerprint(resolved_manifest):
        raise ProductCertificationError(
            "stale-manifest", "product artifact producer manifest fingerprint is stale"
        )
    if authority["toolchain"]["fingerprint"] != fingerprint(resolved_toolchain):
        raise ProductCertificationError(
            "stale-toolchain", "product artifact toolchain fingerprint is stale"
        )
    profile_id = source_authority["profile_id"]
    manifest_key = "source_profile" if profile_id == "full" else "release_profile"
    manifest_source = cast(dict[str, Any], resolved_manifest[manifest_key])
    if source_authority["definition_fingerprint"] != manifest_source[
        "definition_fingerprint"
    ] or source_authority["definition_fingerprint"] != profile_definition_fingerprint(
        _certification_profile(resolved_toolchain, cast(str, profile_id))
    ):
        raise ProductCertificationError(
            "stale-profile",
            "product artifact certification-profile fingerprint is stale",
        )

    repository = cast(dict[str, Any], deterministic["repository"])
    source_evidence = cast(dict[str, Any], deterministic["source_profile_evidence"])
    if repository != source_evidence["repository"]:
        raise ProductCertificationError(
            "stale-repository",
            "product and source-profile repository identities differ",
        )
    if enforce_current_repository:
        current = dict(resolved_repository_state or repository_state(root))
        if repository != current:
            raise ProductCertificationError(
                "stale-repository",
                "product artifact repository identity differs from the current repository",
            )

    expected_ids = expected_profile_result_ids(
        resolved_toolchain, cast(str, profile_id)
    )
    source_operations = cast(list[dict[str, Any]], source_evidence["operations"])
    source_ids = [cast(str, operation["result_id"]) for operation in source_operations]
    _reject_result_set(source_ids, expected_ids)
    results = cast(list[dict[str, Any]], deterministic["results"])
    observed_ids = [cast(str, result["result_id"]) for result in results]
    _reject_result_set(observed_ids, expected_ids)
    producers = _producer_map(resolved_manifest)
    contract_versions = cast(
        dict[str, object], resolved_manifest["result_contract_versions"]
    )
    for index, (source, actual) in enumerate(
        zip(source_operations, results, strict=True)
    ):
        operation_id = cast(str, source["operation_id"])
        expected = _product_result(
            source, producers[operation_id], contract_versions, index
        )
        if actual.get("status") != source.get("status"):
            raise ProductCertificationError(
                "conflicting-result", f"status conflicts for {actual['result_id']!r}"
            )
        producer_evidence = actual.get("producer_evidence")
        if isinstance(producer_evidence, dict):
            payload = producer_evidence.get("payload")
            if not isinstance(payload, dict) or producer_evidence.get(
                "fingerprint"
            ) != fingerprint(payload):
                raise ProductCertificationError(
                    "producer-fingerprint",
                    f"producer payload fingerprint differs for {actual['result_id']!r}",
                )
        if actual != expected:
            code = (
                "producer-fingerprint"
                if actual.get("producer_evidence") != expected["producer_evidence"]
                else "conflicting-result"
            )
            raise ProductCertificationError(
                code, f"derived result differs for {actual['result_id']!r}"
            )

    coverage = cast(dict[str, Any], deterministic["coverage"])
    structured_count = sum(
        producer["result_contract"] is not None for producer in producers.values()
    )
    expected_coverage = {
        "expected_result_count": len(expected_ids),
        "observed_result_count": len(observed_ids),
        "expected_result_ids_fingerprint": _result_id_fingerprint(expected_ids),
        "observed_result_ids_fingerprint": _result_id_fingerprint(observed_ids),
        "expected_structured_producer_count": structured_count,
        "observed_structured_producer_count": sum(
            result["producer_evidence"] is not None for result in results
        ),
        "missing_result_ids": [],
        "unknown_result_ids": [],
    }
    if coverage != expected_coverage:
        raise ProductCertificationError(
            "aggregate-mismatch", "coverage summary differs from result evidence"
        )

    expected_claims = _claims(resolved_manifest, results)
    if deterministic["claims"] != expected_claims:
        raise ProductCertificationError(
            "artifact-fingerprint", "derived claims differ from producer manifest"
        )
    expected_aggregate = _aggregate(results, expected_claims)
    if deterministic["aggregate"] != expected_aggregate:
        raise ProductCertificationError(
            "aggregate-mismatch", "aggregate summary differs from result evidence"
        )
    if deterministic["aggregate_policy"] != resolved_manifest["aggregate_policy"]:
        raise ProductCertificationError(
            "aggregate-mismatch", "aggregate policy differs from producer manifest"
        )
    if artifact["evidence_fingerprint"] != fingerprint(deterministic):
        raise ProductCertificationError(
            "artifact-fingerprint", "deterministic evidence fingerprint differs"
        )


def render_product_report(artifact: Mapping[str, object]) -> str:
    """Render the human view only from validated deterministic evidence."""

    deterministic = cast(dict[str, Any], artifact["deterministic_evidence"])
    repository = cast(dict[str, Any], deterministic["repository"])
    authority = cast(dict[str, Any], deterministic["authority"])
    coverage = cast(dict[str, Any], deterministic["coverage"])
    aggregate = cast(dict[str, Any], deterministic["aggregate"])
    results = cast(list[dict[str, Any]], deterministic["results"])
    claims = cast(list[dict[str, Any]], deterministic["claims"])
    counts = cast(dict[str, int], aggregate["counts"])
    count_text = ", ".join(
        f"{status}={counts[status]}" for status in RESULT_STATUSES if counts[status]
    )
    repository_state_text = "dirty" if repository["dirty"] else "clean"
    source = cast(dict[str, Any], authority["source_profile"])
    manifest = cast(dict[str, Any], authority["producer_manifest"])

    area_counts = Counter(cast(str, result["evidence_area"]) for result in results)
    nonpassing = [
        result
        for result in results
        if result["status"] not in ("passed", "not_applicable")
    ]
    lines = [
        "# STRling Product Certification",
        "",
        f"- Repository: `{repository['commit']}` ({repository_state_text})",
        (
            f"- Source profile: `{source['profile_id']}` "
            f"(`{source['evidence_fingerprint']}`)"
        ),
        f"- Producer manifest: `{manifest['fingerprint']}`",
        f"- Product evidence: `{artifact['evidence_fingerprint']}`",
        (
            f"- Aggregate: **{str(aggregate['status']).upper()}** "
            f"(exit {aggregate['exit_code']}; {count_text})"
        ),
        (
            f"- Coverage: {coverage['observed_result_count']}/"
            f"{coverage['expected_result_count']} results; "
            f"{coverage['observed_structured_producer_count']}/"
            f"{coverage['expected_structured_producer_count']} structured producers"
        ),
        "",
        "## Evidence areas",
        "",
        "| Area | Results |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {area} | {area_counts[area]} |" for area in sorted(area_counts))
    lines.extend(
        [
            "",
            "## Claims",
            "",
            "| Claim | Status | Source results |",
            "| --- | --- | ---: |",
        ]
    )
    lines.extend(
        f"| `{claim['claim_id']}` | {claim['status']} | {len(claim['source_result_ids'])} |"
        for claim in claims
    )
    lines.extend(["", "## Non-passing evidence", ""])
    if nonpassing:
        lines.extend(
            f"- `{result['result_id']}`: {result['status']}"
            + (f" — {result['reason']}" if result.get("reason") else "")
            for result in nonpassing
        )
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def write_json(path: Path, value: Mapping[str, object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        raise ProductCertificationError(
            "write-failed", f"cannot write product artifact {path}: {exc}"
        ) from exc


def write_report(path: Path, report: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
    except OSError as exc:
        raise ProductCertificationError(
            "write-failed", f"cannot write product report {path}: {exc}"
        ) from exc


def static_check(root: Path) -> dict[str, object]:
    started = time.monotonic()
    toolchain = load_json(root / TOOLCHAIN_PATH)
    manifest = load_json(root / MANIFEST_PATH)
    validate_producer_manifest(root, manifest, toolchain)
    fixture = load_json(root / FIXTURE_PATH)
    _preflight_waivers(
        cast(
            list[dict[str, Any]],
            cast(dict[str, Any], fixture["deterministic_evidence"])["results"],
        ),
        root,
    )
    _validate_schema(
        fixture, root / ARTIFACT_SCHEMA_PATH, label="product certification fixture"
    )
    deterministic = cast(dict[str, Any], fixture["deterministic_evidence"])
    if fixture["evidence_fingerprint"] != fingerprint(deterministic):
        raise ProductCertificationError(
            "artifact-fingerprint", "positive fixture fingerprint differs"
        )
    source = cast(
        dict[str, Any],
        cast(dict[str, Any], deterministic["authority"])["source_profile"],
    )
    try:
        validate_certification_artifact(
            root, _profile_artifact_from_embedded(deterministic, source)
        )
    except CertificationError as exc:
        raise ProductCertificationError("source-profile-fingerprint", str(exc)) from exc
    mutations = load_json(root / MUTATIONS_PATH)
    cases = cast(list[dict[str, Any]], mutations.get("cases", []))
    expected_result_ids = expected_profile_result_ids(toolchain)
    producers = cast(list[dict[str, Any]], manifest["producers"])
    structured = sum(producer["result_contract"] is not None for producer in producers)
    return {
        "schema_version": "certification-result-v1",
        "operation_id": CHECK_OPERATION_ID,
        "status": "passed",
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "details": {
            "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
            "manifest_schema_version": manifest["schema_version"],
            "profile_id": "full",
            "profile_definition_fingerprint": cast(
                dict[str, Any], manifest["source_profile"]
            )["definition_fingerprint"],
            "release_profile_definition_fingerprint": cast(
                dict[str, Any], manifest["release_profile"]
            )["definition_fingerprint"],
            "profile_result_count": len(expected_result_ids),
            "profile_declaration_count": len(producers),
            "structured_producer_count": structured,
            "evidence_area_count": len(cast(list[str], manifest["evidence_areas"])),
            "claim_count": len(cast(list[object], manifest["claims"])),
            "mutation_case_count": len(cases),
            "manifest_fingerprint": fingerprint(manifest),
            "prose_authority_inputs": 0,
        },
    }


def _run_profile(root: Path, artifact_path: Path) -> int:
    if os.name == "nt":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell is None:
            raise ProductCertificationError(
                "profile-unavailable", "PowerShell is required to run the Full profile"
            )
        command = [
            shell,
            "-NoProfile",
            "-File",
            str(root / "strling.ps1"),
            "profile",
            "full",
            "--artifact",
            str(artifact_path),
        ]
    else:
        command = [
            str(root / "strling"),
            "profile",
            "full",
            "--artifact",
            str(artifact_path),
        ]
    completed = subprocess.run(command, cwd=root, check=False)
    if not artifact_path.is_file():
        raise ProductCertificationError(
            "profile-unavailable",
            f"Full profile exited {completed.returncode} without an artifact",
        )
    return completed.returncode


def run_full_product_certification(
    root: Path,
    *,
    artifact_output: Path | None = None,
    report_output: Path | None = None,
) -> tuple[dict[str, object], str]:
    scratch_root = root / "target"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="strling-product-certification-", dir=scratch_root
    ) as directory:
        profile_path = Path(directory) / "profile.json"
        _run_profile(root, profile_path)
        artifact = build_product_artifact(
            root=root, profile_artifact=load_json(profile_path)
        )
    report = render_product_report(artifact)
    if artifact_output is not None:
        write_json(artifact_output, artifact)
    if report_output is not None:
        write_report(report_output, report)
    return artifact, report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--profile-artifact", type=Path)
    mode.add_argument("--validate", type=Path)
    mode.add_argument("--run-profile", action="store_true")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.check:
            result = static_check(ROOT)
            if args.json:
                print(json.dumps(result, sort_keys=True))
            else:
                details = cast(dict[str, Any], result["details"])
                print(
                    "PRODUCT_CERTIFICATION_CHECK "
                    f"status=passed results={details['profile_result_count']} "
                    f"structured={details['structured_producer_count']} "
                    f"claims={details['claim_count']} "
                    f"mutations={details['mutation_case_count']}"
                )
            return 0

        if args.run_profile:
            artifact, report = run_full_product_certification(
                ROOT, artifact_output=args.artifact, report_output=args.report
            )
        elif args.profile_artifact is not None:
            artifact = build_product_artifact(
                root=ROOT, profile_artifact=load_json(args.profile_artifact)
            )
            report = render_product_report(artifact)
            if args.artifact is not None:
                write_json(args.artifact, artifact)
            if args.report is not None:
                write_report(args.report, report)
        else:
            assert args.validate is not None
            artifact = load_json(args.validate)
            validate_product_artifact(ROOT, artifact)
            report = render_product_report(artifact)
            if args.artifact is not None:
                write_json(args.artifact, artifact)
            if args.report is not None:
                write_report(args.report, report)

        if args.json:
            print(json.dumps(artifact, sort_keys=True))
        elif args.report is None:
            print(report, end="")
        aggregate = cast(
            dict[str, Any],
            cast(dict[str, Any], artifact["deterministic_evidence"])["aggregate"],
        )
        return cast(int, aggregate["exit_code"])
    except ProductCertificationError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "schema_version": "certification-result-v1",
                        "operation_id": CHECK_OPERATION_ID,
                        "status": "failed",
                        "duration_ms": 0,
                        "details": {"error_code": exc.code, "message": exc.detail},
                    },
                    sort_keys=True,
                )
            )
        else:
            print(f"PRODUCT_CERTIFICATION_ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
