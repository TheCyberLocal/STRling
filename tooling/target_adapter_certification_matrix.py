"""Derive target and adapter certification matrices from governed evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, cast

from jsonschema import Draft202012Validator

from tooling.certification import (
    profile_definition_fingerprint,
    validate_certification_artifact,
)
from tooling.product_certification import (
    _certification_profile,
    expected_profile_result_ids,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "governance/schemas/target-adapter-certification-matrix.schema.json"
)
MANIFEST_PATH = ROOT / "tests/certification/target-adapter/1.0/manifest.json"
SOURCE_EVIDENCE_PATH = (
    ROOT / "tests/certification/target-adapter/1.0/source-profile-evidence.json"
)
MATRIX_PATH = ROOT / "tests/certification/target-adapter/1.0/evidence.json"
SUMMARY_PATH = ROOT / "tests/certification/target-adapter/1.0/evidence.md"
TOOLCHAIN_PATH = ROOT / "toolchain.json"
TARGET_ROOT = ROOT / "spec/targets/profiles"
SHARED_CORPUS_PATH = ROOT / "spec/conformance/shared-corpus-v1.json"
STDLIB_REGISTRY_PATH = ROOT / "spec/stdlib/registry/1.0/registry.json"
BINDING_SUPPORT_PATH = ROOT / "tests/adapters/binding-support-4.0/evidence.json"
PUBLIC_SURFACES_PATH = ROOT / "governance/public-surfaces.json"

TARGET_OBLIGATIONS = [
    "compile_acceptance",
    "match_nonmatch",
    "captures",
    "diagnostics",
    "options_unicode",
    "profile_constraints",
    "stdlib_helpers",
]
ADAPTER_OBLIGATIONS = {
    "supported_candidate": [
        "canonical_request_result",
        "package_install",
        "public_contract",
        "declared_runtime_platform",
        "quality_profile",
    ],
    "preview_candidate": [
        "canonical_request_result",
        "package_metadata",
        "public_contract",
        "executed_runtime_platform",
    ],
    "legacy_candidate": [
        "canonical_route_static",
        "public_contract",
        "retained_compatibility_fixture",
    ],
}
STATUS_NAMES = [
    "passed",
    "failed",
    "unavailable",
    "not_applicable",
    "waived",
    "unsupported",
]
UNAVAILABLE_SOURCE_STATUSES = {
    "unavailable",
    "not_yet_configured",
    "not_yet_enforceable",
}
FAILED_SOURCE_STATUSES = {"failed", "incomplete"}


class MatrixError(ValueError):
    """A deterministic matrix contract or evidence failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MatrixError("invalid-json", f"{path} must contain an object")
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


def pretty_json(value: object) -> str:
    return json.dumps(value, indent=4, sort_keys=True, ensure_ascii=False) + "\n"


def _validate_schema(value: Mapping[str, object], *, label: str) -> None:
    schema = load_json(SCHEMA_PATH)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        raise MatrixError("schema", f"{label}: {errors[0].message}")


def _full_profile(toolchain: Mapping[str, object]) -> dict[str, Any]:
    return _certification_profile(toolchain, "full")


def manifest_result_ids(manifest: Mapping[str, object]) -> list[str]:
    result_ids: set[str] = set()
    for source in cast(list[dict[str, Any]], manifest["target_sources"]):
        result_ids.update(
            {
                source["runtime_result_id"],
                source["shared_result_id"],
                source["stdlib_result_id"],
            }
        )
    for source in cast(list[dict[str, Any]], manifest["adapter_sources"]):
        for field in (
            "runtime_result_ids",
            "package_result_ids",
            "public_contract_result_ids",
            "environment_result_ids",
            "quality_result_ids",
        ):
            result_ids.update(cast(list[str], source[field]))
    return sorted(result_ids)


def validate_manifest(
    manifest: Mapping[str, object],
    *,
    toolchain: Mapping[str, object] | None = None,
    binding_support: Mapping[str, object] | None = None,
) -> None:
    _validate_schema(manifest, label="matrix manifest")
    toolchain = toolchain or load_json(TOOLCHAIN_PATH)
    binding_support = binding_support or load_json(BINDING_SUPPORT_PATH)

    full = _full_profile(toolchain)
    declared_full = cast(dict[str, Any], manifest["full_profile"])
    if declared_full["definition_version"] != full[
        "definition_version"
    ] or declared_full["definition_fingerprint"] != profile_definition_fingerprint(
        full
    ):
        raise MatrixError("stale-profile", "manifest Full-profile identity is stale")

    profiles = [load_json(path) for path in sorted(TARGET_ROOT.glob("*.json"))]
    expected_profile_ids = sorted(profile["profile_id"] for profile in profiles)
    target_sources = cast(list[dict[str, Any]], manifest["target_sources"])
    observed_profile_ids = [source["profile_id"] for source in target_sources]
    if observed_profile_ids != expected_profile_ids:
        raise MatrixError("stale-target", "target source denominator is stale")
    if len(observed_profile_ids) != len(set(observed_profile_ids)):
        raise MatrixError("duplicate-target", "target source IDs must be unique")
    target_policy = cast(dict[str, Any], manifest["target_policy"])
    if target_policy["obligations"] != TARGET_OBLIGATIONS:
        raise MatrixError("stale-policy", "target obligations are stale")

    expected_adapters = {
        binding["id"]: binding["certification_tier"]
        for binding in cast(list[dict[str, Any]], binding_support["bindings"])
    }
    adapter_sources = cast(list[dict[str, Any]], manifest["adapter_sources"])
    observed_adapters = {
        source["adapter_id"]: source["certification_tier"] for source in adapter_sources
    }
    if observed_adapters != expected_adapters or len(adapter_sources) != len(
        observed_adapters
    ):
        raise MatrixError("stale-adapter", "adapter source denominator is stale")

    policies = {
        policy["tier"]: policy
        for policy in cast(list[dict[str, Any]], manifest["adapter_tier_policies"])
    }
    if set(policies) != set(ADAPTER_OBLIGATIONS):
        raise MatrixError("stale-policy", "adapter tier policy denominator is stale")
    for tier, obligations in ADAPTER_OBLIGATIONS.items():
        if policies[tier]["obligations"] != obligations:
            raise MatrixError("stale-policy", f"{tier} obligations are stale")
    if not policies["supported_candidate"]["readiness_blocking"] or any(
        policies[tier]["readiness_blocking"]
        for tier in ("preview_candidate", "legacy_candidate")
    ):
        raise MatrixError("stale-policy", "adapter readiness policy is stale")

    known_results = set(expected_profile_result_ids(toolchain, "full"))
    unknown_results = sorted(set(manifest_result_ids(manifest)) - known_results)
    if unknown_results:
        raise MatrixError(
            "unknown-result",
            f"manifest references unknown Full result {unknown_results[0]!r}",
        )
    serialized = json.dumps(manifest, sort_keys=True).lower()
    if "regex-conformance" in serialized:
        raise MatrixError(
            "authority-boundary",
            "external regex-conformance cannot be a matrix authority",
        )


def _source_bundle_fingerprint(bundle: Mapping[str, object]) -> str:
    return fingerprint(
        {
            "source_profile": bundle["source_profile"],
            "results": bundle["results"],
        }
    )


def capture_source_bundle(
    profile_artifact: Mapping[str, object],
    *,
    manifest: Mapping[str, object] | None = None,
) -> dict[str, object]:
    manifest = manifest or load_json(MANIFEST_PATH)
    validate_manifest(manifest)
    validate_certification_artifact(ROOT, profile_artifact)
    deterministic = cast(dict[str, Any], profile_artifact["deterministic_evidence"])
    repository = cast(dict[str, Any], deterministic["repository"])
    profile = cast(dict[str, Any], deterministic["profile"])
    if profile["id"] != "full" or deterministic["component_scope"] != {
        "mode": "profile-default"
    }:
        raise MatrixError("stale-profile", "source evidence must be a full profile")
    if repository["dirty"] is not False:
        raise MatrixError("dirty-source", "source profile must certify a clean tree")
    declared = cast(dict[str, Any], manifest["full_profile"])
    if (
        profile["definition_version"] != declared["definition_version"]
        or profile["definition_fingerprint"] != declared["definition_fingerprint"]
    ):
        raise MatrixError("stale-profile", "source Full-profile identity is stale")

    operations = {
        operation["result_id"]: operation
        for operation in cast(list[dict[str, Any]], deterministic["operations"])
    }
    expected_ids = manifest_result_ids(manifest)
    missing = sorted(set(expected_ids) - set(operations))
    if missing:
        raise MatrixError("missing-result", f"source profile misses {missing[0]!r}")
    results = []
    for result_id in expected_ids:
        operation = operations[result_id]
        results.append(
            {
                "result_id": result_id,
                "status": operation["status"],
                "reason": operation.get("reason"),
                "waiver_references": list(operation.get("waiver_references", [])),
                "structured_evidence": copy.deepcopy(
                    operation.get("structured_evidence")
                ),
            }
        )
    bundle: dict[str, object] = {
        "$schema": "https://strling.dev/governance/target-adapter-certification-matrix.schema.json#/$defs/sourceBundle",
        "schema_version": "1.0.0",
        "bundle_kind": "strling-target-adapter-source-profile-evidence",
        "source_profile": {
            "repository_commit": repository["commit"],
            "repository_dirty": repository["dirty"],
            "profile_id": profile["id"],
            "definition_version": profile["definition_version"],
            "definition_fingerprint": profile["definition_fingerprint"],
            "evidence_fingerprint": profile_artifact["evidence_fingerprint"],
        },
        "results": results,
    }
    bundle["bundle_fingerprint"] = _source_bundle_fingerprint(bundle)
    validate_source_bundle(bundle, manifest=manifest)
    return bundle


def validate_source_bundle(
    bundle: Mapping[str, object],
    *,
    manifest: Mapping[str, object] | None = None,
) -> None:
    _validate_schema(bundle, label="source-profile evidence bundle")
    manifest = manifest or load_json(MANIFEST_PATH)
    validate_manifest(manifest)
    if bundle["bundle_fingerprint"] != _source_bundle_fingerprint(bundle):
        raise MatrixError("fingerprint", "source evidence fingerprint differs")
    source_profile = cast(dict[str, Any], bundle["source_profile"])
    declared = cast(dict[str, Any], manifest["full_profile"])
    if (
        source_profile["definition_version"] != declared["definition_version"]
        or source_profile["definition_fingerprint"]
        != declared["definition_fingerprint"]
    ):
        raise MatrixError("stale-profile", "source evidence Full identity is stale")
    results = cast(list[dict[str, Any]], bundle["results"])
    result_ids = [result["result_id"] for result in results]
    expected_ids = manifest_result_ids(manifest)
    if result_ids != expected_ids:
        missing = sorted(set(expected_ids) - set(result_ids))
        unknown = sorted(set(result_ids) - set(expected_ids))
        if missing:
            raise MatrixError(
                "missing-result", f"source evidence misses {missing[0]!r}"
            )
        if unknown:
            raise MatrixError("unknown-result", f"source evidence adds {unknown[0]!r}")
        raise MatrixError("nondeterministic-order", "source result order differs")
    for result in results:
        status = cast(str, result["status"])
        reason = result["reason"]
        waivers = cast(list[str], result["waiver_references"])
        if (
            status in FAILED_SOURCE_STATUSES | UNAVAILABLE_SOURCE_STATUSES
            and not isinstance(reason, str)
        ):
            raise MatrixError(
                "missing-reason",
                f"source evidence has no reason for {result['result_id']!r}",
            )
        if status == "waived" and not waivers:
            raise MatrixError(
                "missing-waiver",
                f"waived source evidence has no reference for {result['result_id']!r}",
            )
        structured = result["structured_evidence"]
        if structured is None:
            continue
        if not isinstance(structured, dict):
            raise MatrixError(
                "structured-evidence", "structured evidence is not an object"
            )
        if structured.get("status") != result["status"]:
            raise MatrixError(
                "conflicting-result",
                f"structured evidence conflicts for {result['result_id']!r}",
            )
        if not isinstance(structured.get("operation_id"), str):
            raise MatrixError(
                "structured-evidence",
                f"structured operation identity is absent for {result['result_id']!r}",
            )


def _bundle_result_map(bundle: Mapping[str, object]) -> dict[str, dict[str, Any]]:
    return {
        result["result_id"]: result
        for result in cast(list[dict[str, Any]], bundle["results"])
    }


def _check_map(structured: Mapping[str, object]) -> dict[str, dict[str, Any]]:
    checks = structured.get("checks")
    if not isinstance(checks, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict):
            raise MatrixError(
                "structured-evidence", "structured check is not an object"
            )
        check_id = check.get("check_id", check.get("id"))
        if not isinstance(check_id, str) or check_id in mapped:
            raise MatrixError(
                "structured-evidence", "structured check identity is invalid"
            )
        mapped[check_id] = check
    return mapped


def _source_result(
    source: Mapping[str, object],
    *,
    check_ids: Sequence[str] = (),
) -> dict[str, object]:
    structured = source.get("structured_evidence")
    status = cast(str, source["status"])
    structured_operation_id: str | None = None
    structured_fingerprint: str | None = None
    if isinstance(structured, dict):
        structured_operation_id = cast(str, structured["operation_id"])
        structured_fingerprint = fingerprint(structured)
        checks = _check_map(structured)
        if check_ids:
            missing = sorted(set(check_ids) - set(checks))
            if missing:
                raise MatrixError(
                    "missing-check",
                    f"structured evidence misses {missing[0]!r}",
                )
            status = aggregate_status(
                cast(str, checks[item]["status"]) for item in check_ids
            )
    elif check_ids:
        raise MatrixError(
            "missing-check",
            f"{source['result_id']!r} has no structured checks",
        )
    return {
        "result_id": source["result_id"],
        "status": status,
        "structured_operation_id": structured_operation_id,
        "structured_fingerprint": structured_fingerprint,
        "check_ids": list(check_ids),
    }


def aggregate_status(statuses: Iterable[str]) -> str:
    values = list(statuses)
    if not values:
        raise MatrixError("missing-result", "a matrix cell has no source results")
    if any(value in FAILED_SOURCE_STATUSES for value in values):
        return "failed"
    if any(value in UNAVAILABLE_SOURCE_STATUSES for value in values):
        return "unavailable"
    if any(value == "waived" for value in values):
        return "waived"
    if all(value == "not_applicable" for value in values):
        return "not_applicable"
    if all(value in {"passed", "not_applicable"} for value in values):
        return "passed"
    raise MatrixError("unknown-status", f"cannot aggregate source statuses {values!r}")


def _source_results(
    result_map: Mapping[str, Mapping[str, object]],
    result_ids: Sequence[str],
    *,
    check_ids_by_result: Mapping[str, Sequence[str]] | None = None,
) -> list[dict[str, object]]:
    check_ids_by_result = check_ids_by_result or {}
    return [
        _source_result(
            result_map[result_id],
            check_ids=check_ids_by_result.get(result_id, ()),
        )
        for result_id in result_ids
    ]


def _matrix_status(source_results: Sequence[Mapping[str, object]]) -> str:
    return aggregate_status(cast(str, source["status"]) for source in source_results)


def _waivers(
    result_map: Mapping[str, Mapping[str, object]], result_ids: Sequence[str]
) -> list[str]:
    return sorted(
        {
            waiver
            for result_id in result_ids
            for waiver in cast(list[str], result_map[result_id]["waiver_references"])
        }
    )


def _file_identity(path: Path, value: object | None = None) -> dict[str, str]:
    value = load_json(path) if value is None else value
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "fingerprint": fingerprint(value),
    }


def _target_profiles() -> list[tuple[Path, dict[str, Any]]]:
    return [(path, load_json(path)) for path in sorted(TARGET_ROOT.glob("*.json"))]


def _target_registry_identity(
    profiles: Sequence[tuple[Path, Mapping[str, object]]],
) -> dict[str, str]:
    return {
        "path": TARGET_ROOT.relative_to(ROOT).as_posix(),
        "fingerprint": fingerprint([profile for _, profile in profiles]),
    }


def _target_coordinate(path: Path, profile: Mapping[str, object]) -> dict[str, str]:
    engine = cast(dict[str, Any], profile["engine"])
    engine_version = cast(dict[str, Any], engine["version"])
    coordinate = {
        "profile_id": cast(str, profile["profile_id"]),
        "profile_version": cast(str, profile["profile_version"]),
        "engine_id": cast(str, engine["id"]),
        "engine_version": cast(str, engine_version["value"]),
        "profile_path": path.relative_to(ROOT).as_posix(),
        "profile_fingerprint": fingerprint(profile),
    }
    runtime = profile.get("runtime")
    if isinstance(runtime, dict):
        coordinate["runtime_id"] = cast(str, runtime["id"])
        coordinate["runtime_version"] = cast(
            str, cast(dict[str, Any], runtime["version"])["value"]
        )
    return coordinate


def _adapter_coordinate(binding: Mapping[str, object]) -> dict[str, object]:
    package = cast(dict[str, Any], binding["package"])
    return {
        "adapter_id": binding["id"],
        "language": binding["language"],
        "certification_tier": binding["certification_tier"],
        "canonical_route": binding["canonical_route"],
        "package_path": package["path"],
        "runtime_platforms": list(cast(list[str], binding["executed_platforms"])),
    }


def _target_cells(
    manifest: Mapping[str, object],
    bundle: Mapping[str, object],
    profiles: Sequence[tuple[Path, dict[str, Any]]],
) -> list[dict[str, object]]:
    result_map = _bundle_result_map(bundle)
    source_by_profile = {
        source["profile_id"]: source
        for source in cast(list[dict[str, Any]], manifest["target_sources"])
    }
    source_evidence = cast(dict[str, Any], bundle["source_profile"])
    bundle_link = {
        "path": SOURCE_EVIDENCE_PATH.relative_to(ROOT).as_posix(),
        "fingerprint": bundle["bundle_fingerprint"],
    }
    cells: list[dict[str, object]] = []
    for path, profile in profiles:
        profile_id = cast(str, profile["profile_id"])
        source = source_by_profile[profile_id]
        runtime_result_id = cast(str, source["runtime_result_id"])
        runtime_check_id = cast(str, source["runtime_check_id"])
        for obligation in TARGET_OBLIGATIONS:
            if obligation == "stdlib_helpers":
                result_ids = [runtime_result_id, cast(str, source["stdlib_result_id"])]
                contract_link = _file_identity(STDLIB_REGISTRY_PATH)
            else:
                result_ids = [runtime_result_id, cast(str, source["shared_result_id"])]
                contract_link = _file_identity(SHARED_CORPUS_PATH)
            source_results = _source_results(
                result_map,
                result_ids,
                check_ids_by_result={runtime_result_id: [runtime_check_id]},
            )
            status = _matrix_status(source_results)
            cells.append(
                {
                    "cell_id": f"target:{profile_id}:{obligation}",
                    "dimension": "target",
                    "coordinate": _target_coordinate(path, profile),
                    "obligation_id": obligation,
                    "status": status,
                    "claim_status": "certified"
                    if status == "passed"
                    else "not_certified",
                    "source_results": source_results,
                    "evidence_links": [
                        _file_identity(path, profile),
                        contract_link,
                        bundle_link,
                    ],
                    "waiver_references": _waivers(result_map, result_ids),
                    "disposition": (
                        f"{profile_id} {obligation} is {status} at clean source "
                        f"commit {source_evidence['repository_commit']}."
                    ),
                }
            )
    return cells


def _adapter_result_ids(source: Mapping[str, object], obligation: str) -> list[str]:
    mapping = {
        "canonical_request_result": "runtime_result_ids",
        "package_install": "package_result_ids",
        "package_metadata": "package_result_ids",
        "public_contract": "public_contract_result_ids",
        "declared_runtime_platform": "environment_result_ids",
        "executed_runtime_platform": "environment_result_ids",
        "quality_profile": "quality_result_ids",
        "canonical_route_static": "runtime_result_ids",
        "retained_compatibility_fixture": "package_result_ids",
    }
    return list(cast(list[str], source[mapping[obligation]]))


def _adapter_cells(
    manifest: Mapping[str, object],
    bundle: Mapping[str, object],
    binding_support: Mapping[str, object],
) -> list[dict[str, object]]:
    result_map = _bundle_result_map(bundle)
    source_by_adapter = {
        source["adapter_id"]: source
        for source in cast(list[dict[str, Any]], manifest["adapter_sources"])
    }
    binding_link = _file_identity(BINDING_SUPPORT_PATH, binding_support)
    bundle_link = {
        "path": SOURCE_EVIDENCE_PATH.relative_to(ROOT).as_posix(),
        "fingerprint": bundle["bundle_fingerprint"],
    }
    source_evidence = cast(dict[str, Any], bundle["source_profile"])
    cells: list[dict[str, object]] = []
    for binding in cast(list[dict[str, Any]], binding_support["bindings"]):
        adapter_id = cast(str, binding["id"])
        tier = cast(str, binding["certification_tier"])
        source = source_by_adapter[adapter_id]
        runtime_check_ids = cast(list[str], source["runtime_check_ids"])
        runtime_result_ids = cast(list[str], source["runtime_result_ids"])
        check_ids_by_result = (
            {runtime_result_ids[0]: runtime_check_ids} if runtime_check_ids else {}
        )
        for obligation in ADAPTER_OBLIGATIONS[tier]:
            result_ids = _adapter_result_ids(source, obligation)
            source_results = _source_results(
                result_map,
                result_ids,
                check_ids_by_result=(
                    check_ids_by_result
                    if obligation == "canonical_request_result"
                    else {}
                ),
            )
            status = _matrix_status(source_results)
            cells.append(
                {
                    "cell_id": f"adapter:{adapter_id}:{obligation}",
                    "dimension": "adapter",
                    "coordinate": _adapter_coordinate(binding),
                    "obligation_id": obligation,
                    "status": status,
                    "claim_status": "certified"
                    if status == "passed"
                    else "not_certified",
                    "source_results": source_results,
                    "evidence_links": [binding_link, bundle_link],
                    "waiver_references": _waivers(result_map, result_ids),
                    "disposition": (
                        f"{adapter_id} {obligation} is {status} for {tier} at clean "
                        f"source commit {source_evidence['repository_commit']}."
                    ),
                }
            )
    return cells


def _aggregate_status(cells: Sequence[Mapping[str, object]]) -> str:
    statuses = [cast(str, cell["status"]) for cell in cells]
    if "failed" in statuses:
        return "failed"
    if "unavailable" in statuses:
        return "unavailable"
    if "waived" in statuses:
        return "waived"
    return "passed"


def _expected_cell_ids(
    profiles: Sequence[tuple[Path, Mapping[str, object]]],
    binding_support: Mapping[str, object],
) -> tuple[list[str], list[str]]:
    target_ids = [
        f"target:{profile['profile_id']}:{obligation}"
        for _, profile in profiles
        for obligation in TARGET_OBLIGATIONS
    ]
    adapter_ids = [
        f"adapter:{binding['id']}:{obligation}"
        for binding in cast(list[dict[str, Any]], binding_support["bindings"])
        for obligation in ADAPTER_OBLIGATIONS[cast(str, binding["certification_tier"])]
    ]
    return target_ids, adapter_ids


def _assemble_artifact(
    bundle: Mapping[str, object],
    *,
    manifest: Mapping[str, object] | None = None,
) -> dict[str, object]:
    manifest = manifest or load_json(MANIFEST_PATH)
    validate_manifest(manifest)
    validate_source_bundle(bundle, manifest=manifest)
    profiles = _target_profiles()
    binding_support = load_json(BINDING_SUPPORT_PATH)
    target_cells = _target_cells(manifest, bundle, profiles)
    adapter_cells = _adapter_cells(manifest, bundle, binding_support)
    cells = target_cells + adapter_cells
    cell_ids = [cast(str, cell["cell_id"]) for cell in cells]
    expected_target_ids, expected_adapter_ids = _expected_cell_ids(
        profiles, binding_support
    )
    expected_ids = expected_target_ids + expected_adapter_ids
    if len(cell_ids) != len(set(cell_ids)):
        raise MatrixError("duplicate-cell", "matrix cell IDs must be unique")
    counts = Counter(cast(str, cell["status"]) for cell in cells)
    blocking_cell_ids = sorted(
        cast(str, cell["cell_id"])
        for cell in target_cells
        if cell["status"] != "passed"
    ) + sorted(
        cast(str, cell["cell_id"])
        for cell in adapter_cells
        if cast(dict[str, Any], cell["coordinate"])["certification_tier"]
        == "supported_candidate"
        and cell["status"] != "passed"
    )
    source_profile = cast(dict[str, Any], bundle["source_profile"])
    deterministic: dict[str, object] = {
        "repository": {
            "last_certified_commit": source_profile["repository_commit"],
            "dirty": source_profile["repository_dirty"],
        },
        "authority": {
            "manifest": _file_identity(MANIFEST_PATH, manifest),
            "source_profile": {
                "profile_id": source_profile["profile_id"],
                "definition_version": source_profile["definition_version"],
                "definition_fingerprint": source_profile["definition_fingerprint"],
                "evidence_fingerprint": source_profile["evidence_fingerprint"],
            },
            "target_registry": _target_registry_identity(profiles),
            "shared_corpus": _file_identity(SHARED_CORPUS_PATH),
            "stdlib_registry": _file_identity(STDLIB_REGISTRY_PATH),
            "binding_support": _file_identity(BINDING_SUPPORT_PATH, binding_support),
            "public_surfaces": _file_identity(PUBLIC_SURFACES_PATH),
        },
        "target_cells": target_cells,
        "adapter_cells": adapter_cells,
        "coverage": {
            "expected_target_coordinates": len(profiles),
            "observed_target_coordinates": len(
                {
                    cast(dict[str, Any], cell["coordinate"])["profile_id"]
                    for cell in target_cells
                }
            ),
            "expected_adapter_coordinates": len(binding_support["bindings"]),
            "observed_adapter_coordinates": len(
                {
                    cast(dict[str, Any], cell["coordinate"])["adapter_id"]
                    for cell in adapter_cells
                }
            ),
            "expected_cell_count": 115,
            "observed_cell_count": len(cells),
            "expected_cell_ids_fingerprint": fingerprint(sorted(expected_ids)),
            "observed_cell_ids_fingerprint": fingerprint(sorted(cell_ids)),
            "missing_cell_ids": sorted(set(expected_ids) - set(cell_ids)),
            "unknown_cell_ids": sorted(set(cell_ids) - set(expected_ids)),
        },
        "aggregate": {
            "status": _aggregate_status(cells),
            "cell_count": len(cells),
            "target_cell_count": len(target_cells),
            "adapter_cell_count": len(adapter_cells),
            "counts": {status: counts[status] for status in STATUS_NAMES},
            "blocking_cell_ids": blocking_cell_ids,
        },
    }
    artifact: dict[str, object] = {
        "$schema": "https://strling.dev/governance/target-adapter-certification-matrix.schema.json#/$defs/artifact",
        "schema_version": "1.0.0",
        "artifact_kind": "strling-target-adapter-certification-matrices",
        "deterministic_evidence": deterministic,
        "evidence_fingerprint": fingerprint(deterministic),
    }
    return artifact


def build_artifact(
    bundle: Mapping[str, object],
    *,
    manifest: Mapping[str, object] | None = None,
) -> dict[str, object]:
    artifact = _assemble_artifact(bundle, manifest=manifest)
    validate_artifact(artifact)
    return artifact


def validate_artifact(
    artifact: Mapping[str, object],
    *,
    bundle: Mapping[str, object] | None = None,
    manifest: Mapping[str, object] | None = None,
) -> None:
    _validate_schema(artifact, label="matrix artifact")
    manifest = manifest or load_json(MANIFEST_PATH)
    validate_manifest(manifest)
    profiles = _target_profiles()
    binding_support = load_json(BINDING_SUPPORT_PATH)
    expected_target_ids, expected_adapter_ids = _expected_cell_ids(
        profiles, binding_support
    )
    expected_ids = expected_target_ids + expected_adapter_ids
    deterministic = cast(dict[str, Any], artifact["deterministic_evidence"])
    if artifact["evidence_fingerprint"] != fingerprint(deterministic):
        raise MatrixError("fingerprint", "matrix evidence fingerprint differs")
    target_cells = cast(list[dict[str, Any]], deterministic["target_cells"])
    adapter_cells = cast(list[dict[str, Any]], deterministic["adapter_cells"])
    cells = target_cells + adapter_cells
    cell_ids = [cell["cell_id"] for cell in cells]
    if [cell["cell_id"] for cell in target_cells] != expected_target_ids or [
        cell["cell_id"] for cell in adapter_cells
    ] != expected_adapter_ids:
        raise MatrixError(
            "missing-cell", "matrix cell denominator or ordering is stale"
        )
    expected_target_coordinates = {
        cast(str, profile["profile_id"]): _target_coordinate(path, profile)
        for path, profile in profiles
    }
    expected_adapter_coordinates = {
        cast(str, binding["id"]): _adapter_coordinate(binding)
        for binding in cast(list[dict[str, Any]], binding_support["bindings"])
    }
    for cell in target_cells:
        coordinate = cast(dict[str, Any], cell["coordinate"])
        expected_coordinate = expected_target_coordinates.get(coordinate["profile_id"])
        if coordinate != expected_coordinate:
            raise MatrixError("stale-target", "target coordinate identity is stale")
    for cell in adapter_cells:
        coordinate = cast(dict[str, Any], cell["coordinate"])
        expected_coordinate = expected_adapter_coordinates.get(coordinate["adapter_id"])
        if coordinate != expected_coordinate:
            raise MatrixError("stale-adapter", "adapter coordinate identity is stale")
    for cell in cells:
        if (cell["status"] == "passed") != (cell["claim_status"] == "certified"):
            raise MatrixError("false-claim", "only passed cells may be certified")
    coverage = cast(dict[str, Any], deterministic["coverage"])
    if (
        coverage["expected_cell_count"] != 115
        or coverage["observed_cell_count"] != len(cells)
        or coverage["expected_target_coordinates"] != len(profiles)
        or coverage["observed_target_coordinates"] != len(profiles)
        or coverage["expected_adapter_coordinates"] != len(binding_support["bindings"])
        or coverage["observed_adapter_coordinates"] != len(binding_support["bindings"])
        or coverage["expected_cell_ids_fingerprint"]
        != fingerprint(sorted(expected_ids))
        or coverage["observed_cell_ids_fingerprint"] != fingerprint(sorted(cell_ids))
        or coverage["missing_cell_ids"]
        or coverage["unknown_cell_ids"]
    ):
        raise MatrixError("missing-cell", "matrix coverage is incomplete")
    counts = Counter(cell["status"] for cell in cells)
    aggregate = cast(dict[str, Any], deterministic["aggregate"])
    if (
        aggregate["cell_count"] != len(cells)
        or aggregate["target_cell_count"] != len(target_cells)
        or aggregate["adapter_cell_count"] != len(adapter_cells)
        or aggregate["counts"] != {status: counts[status] for status in STATUS_NAMES}
        or aggregate["status"] != _aggregate_status(cells)
    ):
        raise MatrixError("aggregate", "matrix aggregate is inconsistent")
    authority = cast(dict[str, Any], deterministic["authority"])
    static_authority = {
        "manifest": _file_identity(MANIFEST_PATH, manifest),
        "target_registry": _target_registry_identity(profiles),
        "shared_corpus": _file_identity(SHARED_CORPUS_PATH),
        "stdlib_registry": _file_identity(STDLIB_REGISTRY_PATH),
        "binding_support": _file_identity(BINDING_SUPPORT_PATH, binding_support),
        "public_surfaces": _file_identity(PUBLIC_SURFACES_PATH),
    }
    if any(authority[key] != value for key, value in static_authority.items()):
        raise MatrixError("stale-authority", "matrix authority identity is stale")
    source_profile = cast(dict[str, Any], authority["source_profile"])
    declared_full = cast(dict[str, Any], manifest["full_profile"])
    if (
        source_profile["profile_id"] != "full"
        or source_profile["definition_version"] != declared_full["definition_version"]
        or source_profile["definition_fingerprint"]
        != declared_full["definition_fingerprint"]
    ):
        raise MatrixError("stale-profile", "matrix Full-profile identity is stale")
    if bundle is not None:
        expected = _assemble_artifact(bundle, manifest=manifest)
        if artifact != expected:
            raise MatrixError("stale-evidence", "matrix differs from current evidence")


def render_markdown(artifact: Mapping[str, object]) -> str:
    deterministic = cast(dict[str, Any], artifact["deterministic_evidence"])
    repository = cast(dict[str, Any], deterministic["repository"])
    aggregate = cast(dict[str, Any], deterministic["aggregate"])
    counts = cast(dict[str, Any], aggregate["counts"])
    lines = [
        "# STRling target and adapter certification matrices",
        "",
        "This generated view is certification evidence, not semantic authority or permanent consumer-facing support policy.",
        "",
        f"- Last certified commit: `{repository['last_certified_commit']}`",
        f"- Evidence fingerprint: `{artifact['evidence_fingerprint']}`",
        f"- Matrix status: `{aggregate['status']}`",
        f"- Cells: {aggregate['cell_count']} total; {aggregate['target_cell_count']} target; {aggregate['adapter_cell_count']} adapter",
        "- Status counts: "
        + ", ".join(f"{status}={counts[status]}" for status in STATUS_NAMES),
        "",
        "## Target matrix",
        "",
        "| Profile | Profile version | Engine | Engine version | Obligation | Status | Claim | Source results |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cell in cast(list[dict[str, Any]], deterministic["target_cells"]):
        coordinate = cast(dict[str, Any], cell["coordinate"])
        sources = ", ".join(
            f"`{source['result_id']}`" for source in cell["source_results"]
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{coordinate['profile_id']}`",
                    f"`{coordinate['profile_version']}`",
                    f"`{coordinate['engine_id']}`",
                    f"`{coordinate['engine_version']}`",
                    f"`{cell['obligation_id']}`",
                    f"`{cell['status']}`",
                    f"`{cell['claim_status']}`",
                    sources,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Adapter matrix",
            "",
            "| Adapter | Language | Tier | Runtime/platform evidence | Obligation | Status | Claim | Source results |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for cell in cast(list[dict[str, Any]], deterministic["adapter_cells"]):
        coordinate = cast(dict[str, Any], cell["coordinate"])
        sources = ", ".join(
            f"`{source['result_id']}`" for source in cell["source_results"]
        )
        platforms = ", ".join(
            f"`{platform}`" for platform in coordinate["runtime_platforms"]
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{coordinate['adapter_id']}`",
                    coordinate["language"],
                    f"`{coordinate['certification_tier']}`",
                    platforms,
                    f"`{cell['obligation_id']}`",
                    f"`{cell['status']}`",
                    f"`{cell['claim_status']}`",
                    sources,
                ]
            )
            + " |"
        )
    blockers = cast(list[str], aggregate["blocking_cell_ids"])
    lines.extend(["", "## Readiness", ""])
    if blockers:
        lines.append(f"{len(blockers)} required Supported cell(s) are not certified:")
        lines.append("")
        lines.extend(f"- `{cell_id}`" for cell_id in blockers)
    else:
        lines.append("All required Supported target and adapter cells are certified.")
    lines.extend(
        [
            "",
            "Preview and Legacy rows use their explicit reduced obligations. Unexecuted, unavailable, waived, unsupported, and not-applicable cells are never labeled certified.",
            "",
        ]
    )
    return "\n".join(lines)


def check_outputs(source_path: Path = SOURCE_EVIDENCE_PATH) -> dict[str, object]:
    bundle = load_json(source_path)
    artifact = build_artifact(bundle)
    expected_json = pretty_json(artifact)
    expected_markdown = render_markdown(artifact)
    if (
        not MATRIX_PATH.is_file()
        or MATRIX_PATH.read_text(encoding="utf-8") != expected_json
    ):
        raise MatrixError("stale-output", f"{MATRIX_PATH.relative_to(ROOT)} is stale")
    if (
        not SUMMARY_PATH.is_file()
        or SUMMARY_PATH.read_text(encoding="utf-8") != expected_markdown
    ):
        raise MatrixError("stale-output", f"{SUMMARY_PATH.relative_to(ROOT)} is stale")
    return artifact


def write_outputs(source_path: Path = SOURCE_EVIDENCE_PATH) -> dict[str, object]:
    bundle = load_json(source_path)
    artifact = build_artifact(bundle)
    MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    MATRIX_PATH.write_text(pretty_json(artifact), encoding="utf-8", newline="\n")
    SUMMARY_PATH.write_text(render_markdown(artifact), encoding="utf-8", newline="\n")
    return artifact


def _result_payload(status: str, **details: object) -> dict[str, object]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": "certification.target-adapter-matrices",
        "status": status,
        "duration_ms": None,
        "checks": [
            {
                "id": "certification.target-adapter-matrices.evidence",
                "status": status,
                "details": details,
            }
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture-profile", type=Path)
    mode.add_argument("--source-evidence", type=Path)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--validate", type=Path)
    parser.add_argument("--source-output", type=Path, default=SOURCE_EVIDENCE_PATH)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        artifact: Mapping[str, object] | None = None
        if arguments.capture_profile is not None:
            bundle = capture_source_bundle(load_json(arguments.capture_profile))
            arguments.source_output.parent.mkdir(parents=True, exist_ok=True)
            arguments.source_output.write_text(
                pretty_json(bundle), encoding="utf-8", newline="\n"
            )
            details = {
                "source_output": arguments.source_output.relative_to(ROOT).as_posix(),
                "source_fingerprint": bundle["bundle_fingerprint"],
                "source_result_count": len(cast(list[object], bundle["results"])),
            }
        elif arguments.source_evidence is not None:
            artifact = (
                write_outputs(arguments.source_evidence)
                if arguments.write
                else build_artifact(load_json(arguments.source_evidence))
            )
            deterministic = cast(dict[str, Any], artifact["deterministic_evidence"])
            details = {
                "evidence_fingerprint": artifact["evidence_fingerprint"],
                "aggregate": deterministic["aggregate"],
            }
        elif arguments.check:
            artifact = check_outputs()
            deterministic = cast(dict[str, Any], artifact["deterministic_evidence"])
            details = {
                "evidence_fingerprint": artifact["evidence_fingerprint"],
                "aggregate": deterministic["aggregate"],
            }
        else:
            value = load_json(arguments.validate)
            if value.get("bundle_kind") is not None:
                validate_source_bundle(value)
                details = {"bundle_fingerprint": value["bundle_fingerprint"]}
            else:
                validate_artifact(value)
                details = {"evidence_fingerprint": value["evidence_fingerprint"]}
        payload = _result_payload("passed", **details)
        exit_code = 0
    except (MatrixError, OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        code = error.code if isinstance(error, MatrixError) else "execution"
        payload = _result_payload("failed", code=code, error=str(error))
        exit_code = 1
    if arguments.json:
        print(json.dumps(payload, sort_keys=True))
    elif exit_code == 0:
        print("Target and adapter matrix evidence passed.")
    else:
        print(f"Target and adapter matrix evidence failed: {payload}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
