#!/usr/bin/env python3
"""Derive profile-definition identity without executing certification results."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

_certification = importlib.import_module(
    "tooling.certification" if __package__ else "certification"
)
canonical_evidence_fingerprint = _certification.canonical_evidence_fingerprint
operation_registry_fingerprint = _certification.operation_registry_fingerprint
profile_definition_fingerprint = _certification.profile_definition_fingerprint
profile_registry_fingerprint = _certification.profile_registry_fingerprint
repository_state = _certification.repository_state


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "governance/schemas/profile-source-evidence.schema.json"
GRAPH_PATH = ROOT / "governance/certification-evidence-dependency-graph.json"
GRAPH_SCHEMA_PATH = (
    ROOT / "governance/schemas/certification-evidence-dependency-graph.schema.json"
)
DEFINITIONS_PATH = (
    ROOT / "tests/certification/profile-source/1.0/definitions.json"
)
TOOLCHAIN_PATH = ROOT / "toolchain.json"
PRODUCER_PATH = ROOT / "tooling/profile_source_identity.py"
PROFILE_IDS = ("local", "pull-request", "full", "release")
CONTRACT_PATHS = (
    "governance/schemas/certification-evidence-dependency-graph.schema.json",
    "governance/schemas/product-certification-producer-manifest.schema.json",
    "governance/schemas/profile-certification-artifact.schema.json",
    "governance/schemas/profile-source-evidence.schema.json",
    "governance/schemas/structured-operation-execution.schema.json",
    "governance/schemas/target-adapter-certification-matrix.schema.json",
)
IDENTITY_SOURCE_REFERENCE = {
    "path": "tests/certification/profile-source/1.0/definitions.json"
}


class ProfileSourceIdentityError(ValueError):
    """Raised when identity-only profile evidence is stale or contradictory."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileSourceIdentityError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise ProfileSourceIdentityError(f"{path} must contain one JSON object")
    return cast(dict[str, Any], value)


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ProfileSourceIdentityError(f"cannot fingerprint {path}: {error}") from error


def _file_identity(path: Path, *, root: Path = ROOT) -> dict[str, str]:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as error:
        raise ProfileSourceIdentityError(f"identity path escapes repository: {path}") from error
    return {"path": relative, "sha256": _sha256_file(path)}


def _load_schema(path: Path) -> dict[str, Any]:
    return _load_json(path)


def _validate_schema(value: Mapping[str, object], schema_path: Path) -> None:
    schema = _load_schema(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)
    except (SchemaError, ValidationError) as error:
        raise ProfileSourceIdentityError(
            f"profile source evidence schema rejection: {error.message}"
        ) from error


def validate_dependency_graph(
    graph: Mapping[str, object], *, root: Path = ROOT
) -> None:
    _validate_schema(graph, root / GRAPH_SCHEMA_PATH.relative_to(ROOT))
    nodes = cast(list[dict[str, Any]], graph["nodes"])
    node_ids = [cast(str, node["id"]) for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ProfileSourceIdentityError("dependency graph node IDs must be unique")
    node_by_id = {cast(str, node["id"]): node for node in nodes}
    edges = cast(list[dict[str, Any]], graph["edges"])
    edge_pairs: set[tuple[str, str]] = set()
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    indegree = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        source = cast(str, edge["from"])
        target = cast(str, edge["to"])
        if source not in node_by_id or target not in node_by_id:
            raise ProfileSourceIdentityError(
                f"dependency graph edge references unknown node {source!r}->{target!r}"
            )
        if source == target or (source, target) in edge_pairs:
            raise ProfileSourceIdentityError(
                f"dependency graph has duplicate/self edge {source!r}->{target!r}"
            )
        edge_pairs.add((source, target))
        adjacency[source].add(target)
        indegree[target] += 1

    ready = sorted(node_id for node_id, count in indegree.items() if count == 0)
    visited: list[str] = []
    while ready:
        current = ready.pop(0)
        visited.append(current)
        for target in sorted(adjacency[current]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if len(visited) != len(node_ids):
        raise ProfileSourceIdentityError("certification evidence dependency graph is cyclic")

    result_nodes = {
        node_id
        for node_id, node in node_by_id.items()
        if node["evidence_role"] in {"certification-result", "historical-provenance"}
    }
    forbidden_targets = {
        node_id
        for node_id, node in node_by_id.items()
        if node["phase"] == "pre-execution"
        and node["evidence_role"] == "pre-execution-authority"
    }
    for source in sorted(result_nodes):
        pending = list(adjacency[source])
        reached: set[str] = set()
        while pending:
            target = pending.pop()
            if target in reached:
                continue
            reached.add(target)
            pending.extend(adjacency[target])
        blocked = sorted(reached & forbidden_targets)
        if blocked:
            raise ProfileSourceIdentityError(
                "post-execution evidence feeds pre-execution authority: "
                f"{source!r}->{blocked[0]!r}"
            )

    classifications = cast(list[dict[str, Any]], graph["field_classifications"])
    keys = [
        (entry["artifact_path"], entry["json_pointer"])
        for entry in classifications
    ]
    if len(keys) != len(set(keys)):
        raise ProfileSourceIdentityError(
            "dependency graph field classifications must be unique"
        )


def load_dependency_graph(*, root: Path = ROOT) -> dict[str, Any]:
    graph = _load_json(root / GRAPH_PATH.relative_to(ROOT))
    validate_dependency_graph(graph, root=root)
    return graph


def _profile_identities(profiles: Mapping[str, object]) -> list[dict[str, str]]:
    identities: list[dict[str, str]] = []
    for profile_id in PROFILE_IDS:
        value = profiles.get(profile_id)
        if not isinstance(value, dict):
            raise ProfileSourceIdentityError(
                f"toolchain is missing canonical profile {profile_id!r}"
            )
        version = value.get("definition_version")
        if not isinstance(version, str):
            raise ProfileSourceIdentityError(
                f"profile {profile_id!r} has no semantic definition version"
            )
        identities.append(
            {
                "id": profile_id,
                "definition_version": version,
                "definition_fingerprint": profile_definition_fingerprint(value),
            }
        )
    return identities


def derive_definition_bundle(*, root: Path = ROOT) -> dict[str, object]:
    toolchain = _load_json(root / TOOLCHAIN_PATH.relative_to(ROOT))
    policy = toolchain.get("policy")
    if not isinstance(policy, dict):
        raise ProfileSourceIdentityError("toolchain.json has no policy object")
    profiles = policy.get("profiles")
    operations = policy.get("operation_registry")
    if not isinstance(profiles, dict) or not isinstance(operations, dict):
        raise ProfileSourceIdentityError(
            "toolchain profile or operation registry is malformed"
        )
    schema_version = toolchain.get("schema_version")
    if not isinstance(schema_version, int):
        raise ProfileSourceIdentityError("toolchain schema version is malformed")
    load_dependency_graph(root=root)
    deterministic: dict[str, object] = {
        "$schema": "https://strling.dev/governance/profile-source-evidence.schema.json#/$defs/definitionBundle",
        "schema_version": "1.0.0",
        "artifact_kind": "strling-profile-source-definitions",
        "evidence_role": "identity-only",
        "registry": {
            "path": "toolchain.json",
            "schema_version": schema_version,
            "profile_registry_fingerprint": profile_registry_fingerprint(profiles),
            "operation_registry_fingerprint": operation_registry_fingerprint(
                operations
            ),
        },
        "profiles": _profile_identities(profiles),
        "dependency_graph": _file_identity(
            root / GRAPH_PATH.relative_to(ROOT), root=root
        ),
        "contracts": [
            _file_identity(root / path, root=root) for path in CONTRACT_PATHS
        ],
        "producer": _file_identity(
            root / PRODUCER_PATH.relative_to(ROOT), root=root
        ),
    }
    deterministic["evidence_fingerprint"] = canonical_evidence_fingerprint(
        deterministic
    )
    validate_definition_bundle(deterministic, root=root, require_current=False)
    return deterministic


def validate_definition_bundle(
    value: Mapping[str, object],
    *,
    root: Path = ROOT,
    require_current: bool = True,
) -> None:
    _validate_schema(value, root / SCHEMA_PATH.relative_to(ROOT))
    if value.get("artifact_kind") != "strling-profile-source-definitions":
        raise ProfileSourceIdentityError(
            "profile definition bundle has the wrong artifact kind"
        )
    payload = dict(value)
    observed = payload.pop("evidence_fingerprint", None)
    if observed != canonical_evidence_fingerprint(payload):
        raise ProfileSourceIdentityError(
            "profile definition bundle fingerprint mismatch"
        )
    profiles = cast(list[dict[str, Any]], value["profiles"])
    profile_ids = [cast(str, profile["id"]) for profile in profiles]
    if profile_ids != list(PROFILE_IDS):
        raise ProfileSourceIdentityError(
            "profile definition bundle ordering or denominator is stale"
        )
    if require_current and dict(value) != derive_definition_bundle(root=root):
        raise ProfileSourceIdentityError(
            "profile definition bundle differs from canonical source definitions"
        )


def load_definition_bundle(
    *, root: Path = ROOT, require_current: bool = True
) -> dict[str, Any]:
    value = _load_json(root / DEFINITIONS_PATH.relative_to(ROOT))
    validate_definition_bundle(value, root=root, require_current=require_current)
    return value


def profile_identity(
    bundle: Mapping[str, object], profile_id: str
) -> dict[str, str]:
    for identity in cast(list[dict[str, Any]], bundle["profiles"]):
        if identity["id"] == profile_id:
            return {
                "id": cast(str, identity["id"]),
                "definition_version": cast(str, identity["definition_version"]),
                "definition_fingerprint": cast(
                    str, identity["definition_fingerprint"]
                ),
            }
    raise ProfileSourceIdentityError(
        f"profile definition bundle has no identity for {profile_id!r}"
    )


def build_invocation_evidence(
    *,
    root: Path = ROOT,
    invocation_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    bundle = load_definition_bundle(root=root)
    repository = repository_state(root)
    if repository["dirty"]:
        raise ProfileSourceIdentityError(
            "profile source identity requires an exact clean repository"
        )
    deterministic: dict[str, object] = {
        "repository": dict(repository),
        "definition_bundle": {
            "path": DEFINITIONS_PATH.relative_to(ROOT).as_posix(),
            "evidence_fingerprint": bundle["evidence_fingerprint"],
        },
        "registry": bundle["registry"],
        "profiles": bundle["profiles"],
        "dependency_graph": bundle["dependency_graph"],
    }
    artifact: dict[str, object] = {
        "$schema": "https://strling.dev/governance/profile-source-evidence.schema.json#/$defs/invocationEvidence",
        "schema_version": "1.0.0",
        "artifact_kind": "strling-profile-source-evidence",
        "evidence_role": "identity-only",
        "deterministic_evidence": deterministic,
        "evidence_fingerprint": canonical_evidence_fingerprint(deterministic),
        "execution_metadata": {
            "invocation_id": invocation_id or uuid.uuid4().hex,
            "generated_at": generated_at
            or datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        },
    }
    artifact["artifact_fingerprint"] = canonical_evidence_fingerprint(artifact)
    validate_invocation_evidence(artifact, root=root)
    return artifact


def validate_invocation_evidence(
    value: Mapping[str, object],
    *,
    root: Path = ROOT,
    require_current_repository: bool = True,
) -> None:
    _validate_schema(value, root / SCHEMA_PATH.relative_to(ROOT))
    if value.get("artifact_kind") != "strling-profile-source-evidence":
        raise ProfileSourceIdentityError(
            "profile source invocation has the wrong artifact kind"
        )
    payload = dict(value)
    observed_artifact = payload.pop("artifact_fingerprint", None)
    if observed_artifact != canonical_evidence_fingerprint(payload):
        raise ProfileSourceIdentityError(
            "profile source invocation artifact fingerprint mismatch"
        )
    deterministic = cast(dict[str, Any], value["deterministic_evidence"])
    if value["evidence_fingerprint"] != canonical_evidence_fingerprint(
        deterministic
    ):
        raise ProfileSourceIdentityError(
            "profile source invocation evidence fingerprint mismatch"
        )
    bundle = load_definition_bundle(root=root)
    if deterministic["definition_bundle"] != {
        "path": DEFINITIONS_PATH.relative_to(ROOT).as_posix(),
        "evidence_fingerprint": bundle["evidence_fingerprint"],
    }:
        raise ProfileSourceIdentityError(
            "profile source invocation binds the wrong definition bundle"
        )
    for key in ("registry", "profiles", "dependency_graph"):
        if deterministic[key] != bundle[key]:
            raise ProfileSourceIdentityError(
                f"profile source invocation has stale {key.replace('_', ' ')}"
            )
    if require_current_repository:
        repository = repository_state(root)
        if repository["dirty"]:
            raise ProfileSourceIdentityError(
                "profile source identity requires an exact clean repository"
            )
        if deterministic["repository"] != repository:
            raise ProfileSourceIdentityError(
                "profile source invocation comes from a previous source SHA"
            )


def _atomic_write_json(
    path: Path, value: Mapping[str, object], *, validator: Any
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=4, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        candidate = _load_json(temporary)
        validator(candidate)
        os.replace(temporary, path)
    except OSError as error:
        raise ProfileSourceIdentityError(
            f"cannot atomically publish profile source evidence: {error}"
        ) from error
    finally:
        if temporary.exists():
            temporary.unlink()


def write_definition_bundle(*, root: Path = ROOT) -> dict[str, object]:
    value = derive_definition_bundle(root=root)
    path = root / DEFINITIONS_PATH.relative_to(ROOT)
    _atomic_write_json(
        path,
        value,
        validator=lambda candidate: validate_definition_bundle(
            candidate, root=root, require_current=True
        ),
    )
    return value


def write_invocation_evidence(
    path: Path,
    *,
    root: Path = ROOT,
    invocation_id: str | None = None,
) -> dict[str, object]:
    value = build_invocation_evidence(root=root, invocation_id=invocation_id)
    _atomic_write_json(
        path,
        value,
        validator=lambda candidate: validate_invocation_evidence(
            candidate, root=root
        ),
    )
    return value


def _default_invocation_path(root: Path, invocation_id: str) -> Path:
    repository = repository_state(root)
    source = cast(str, repository["commit"])
    return (
        root
        / "target/codex-tools/profile-source-identity"
        / source
        / invocation_id
        / "evidence.json"
    )


def _structured_result(
    status: str, *, details: Mapping[str, object]
) -> dict[str, object]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": "certification.profile-source-identity",
        "status": status,
        "duration_ms": 0,
        "checks": [
            {
                "id": "certification.profile-source-identity.pre-execution",
                "status": status,
                "details": dict(details),
            }
        ],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-definitions", action="store_true")
    mode.add_argument("--check-definitions", action="store_true")
    mode.add_argument("--check-current", action="store_true")
    mode.add_argument("--emit-evidence", type=Path)
    mode.add_argument("--validate", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.write_definitions:
            value = write_definition_bundle()
            details: dict[str, object] = {
                "artifact": DEFINITIONS_PATH.relative_to(ROOT).as_posix(),
                "evidence_role": value["evidence_role"],
                "evidence_fingerprint": value["evidence_fingerprint"],
            }
        elif args.check_definitions:
            value = load_definition_bundle()
            details = {
                "artifact": DEFINITIONS_PATH.relative_to(ROOT).as_posix(),
                "evidence_role": value["evidence_role"],
                "evidence_fingerprint": value["evidence_fingerprint"],
            }
        elif args.check_current:
            invocation_id = uuid.uuid4().hex
            path = _default_invocation_path(ROOT, invocation_id)
            value = write_invocation_evidence(
                path, root=ROOT, invocation_id=invocation_id
            )
            details = {
                "artifact": path.relative_to(ROOT).as_posix(),
                "artifact_fingerprint": value["artifact_fingerprint"],
                "evidence_role": value["evidence_role"],
                "evidence_fingerprint": value["evidence_fingerprint"],
                "source_sha": cast(
                    dict[str, Any], value["deterministic_evidence"]
                )["repository"]["commit"],
            }
            result = _structured_result("passed", details=details)
            print(json.dumps(result, sort_keys=True))
            return 0
        elif args.emit_evidence is not None:
            value = write_invocation_evidence(args.emit_evidence)
            details = {
                "artifact": args.emit_evidence.as_posix(),
                "artifact_fingerprint": value["artifact_fingerprint"],
                "evidence_role": value["evidence_role"],
                "evidence_fingerprint": value["evidence_fingerprint"],
            }
        else:
            value = _load_json(args.validate)
            if value.get("artifact_kind") == "strling-profile-source-definitions":
                validate_definition_bundle(value)
            else:
                validate_invocation_evidence(value)
            details = {
                "artifact": args.validate.as_posix(),
                "artifact_kind": value["artifact_kind"],
                "evidence_role": value["evidence_role"],
            }
        if args.json:
            print(json.dumps(details, sort_keys=True))
        else:
            print(
                "PROFILE_SOURCE_IDENTITY "
                + " ".join(f"{key}={value}" for key, value in details.items())
            )
        return 0
    except (ProfileSourceIdentityError, OSError) as error:
        details = {"error_code": "profile-source-identity", "message": str(error)}
        if args.check_current:
            print(json.dumps(_structured_result("failed", details=details), sort_keys=True))
        elif args.json:
            print(json.dumps({"status": "failed", "details": details}, sort_keys=True))
        else:
            print(f"PROFILE_SOURCE_IDENTITY_FAILED {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
