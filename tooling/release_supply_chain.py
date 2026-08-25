"""Validate governed STRling release supply-chain certification evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import best_match


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "governance/schemas/release-supply-chain-certification.schema.json"
MANIFEST_PATH = ROOT / "tests/certification/release-supply-chain/1.0/manifest.json"
VALID_FIXTURE_PATH = (
    ROOT / "tests/certification/release-supply-chain/1.0/fixtures/valid-evidence.json"
)
SECURITY_POLICY_PATH = ROOT / "governance/security-policy.json"
TOOLCHAIN_PATH = ROOT / "toolchain.json"

ARTIFACT_IDS = [
    "release:c",
    "release:cpp",
    "release:csharp",
    "release:dart",
    "release:fsharp",
    "release:go",
    "release:java",
    "release:kotlin",
    "release:lua",
    "release:perl",
    "release:php",
    "release:python",
    "release:r",
    "release:ruby",
    "release:rust",
    "release:swift",
    "release:typescript",
]
OIDC_ARTIFACT_IDS = {
    "release:dart",
    "release:python",
    "release:ruby",
    "release:rust",
    "release:typescript",
}
SOURCE_TAG_ARTIFACT_IDS = {
    "release:c",
    "release:go",
    "release:php",
    "release:r",
    "release:swift",
}
PROFILE_EXPECTATIONS = {
    "local": ("offline", False),
    "pull-request": ("offline", False),
    "full": ("allowed", True),
    "release": ("allowed", True),
}
STATUS_PRECEDENCE = ("failed", "incomplete", "unavailable", "passed")
TOOLCHAIN_PROBES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "R": (("R",), ("--version",)),
    "bundler": (("bundle", "bundler"), ("--version",)),
    "cargo": (("cargo",), ("--version",)),
    "cc": (("cc", "clang", "gcc", "cl"), ("--version",)),
    "cmake": (("cmake",), ("--version",)),
    "composer": (("composer",), ("--version",)),
    "conan": (("conan",), ("--version",)),
    "cxx": (("c++", "clang++", "g++", "cl"), ("--version",)),
    "dart": (("dart",), ("--version",)),
    "dotnet": (("dotnet",), ("--version",)),
    "go": (("go",), ("version",)),
    "gradle": (("gradle",), ("--version",)),
    "java": (("java",), ("-version",)),
    "lua": (("lua",), ("-v",)),
    "luarocks": (("luarocks",), ("--version",)),
    "make": (("make", "gmake"), ("--version",)),
    "maven": (("mvn",), ("--version",)),
    "node": (("node",), ("--version",)),
    "npm": (("npm",), ("--version",)),
    "perl": (("perl",), ("-v",)),
    "php": (("php",), ("--version",)),
    "python": (("python", "python3"), ("--version",)),
    "ruby": (("ruby",), ("--version",)),
    "rustc": (("rustc",), ("--version",)),
    "swift": (("swift",), ("--version",)),
}


class ReleaseSupplyChainError(RuntimeError):
    """A stable fail-closed release supply-chain validation error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def load_json(path: Path) -> dict[str, Any]:
    try:
        display_path = path.relative_to(ROOT)
    except ValueError:
        display_path = path
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseSupplyChainError(
            "malformed-json", f"cannot load {display_path}: {error}"
        ) from error
    if not isinstance(loaded, dict):
        raise ReleaseSupplyChainError(
            "malformed-json", f"{display_path} must contain an object"
        )
    return cast(dict[str, Any], loaded)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def document_fingerprint(
    document: Mapping[str, object], field: str | None = None
) -> str:
    projected = copy.deepcopy(dict(document))
    if field is not None:
        projected.pop(field, None)
    return hashlib.sha256(canonical_json(projected)).hexdigest()


def _schema_validator() -> Draft202012Validator:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_schema(document: Mapping[str, object], *, label: str) -> None:
    error = best_match(_schema_validator().iter_errors(document))
    if error is not None:
        location = ".".join(str(item) for item in error.absolute_path) or "<root>"
        raise ReleaseSupplyChainError(
            "schema", f"{label} schema violation at {location}: {error.message}"
        )


def _exact_ids(rows: Sequence[Mapping[str, object]], *, label: str) -> list[str]:
    ids = [row.get("id") for row in rows]
    if any(not isinstance(item, str) for item in ids):
        raise ReleaseSupplyChainError("denominator", f"{label} has a missing id")
    typed = cast(list[str], ids)
    if len(set(typed)) != len(typed):
        raise ReleaseSupplyChainError("denominator", f"{label} ids are duplicated")
    if typed != sorted(typed):
        raise ReleaseSupplyChainError("denominator", f"{label} ids must be sorted")
    return typed


def _artifact_rows(manifest: Mapping[str, object]) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], manifest["artifacts"])


def _toolchain_ids(manifest: Mapping[str, object]) -> list[str]:
    return sorted(
        {
            toolchain
            for artifact in _artifact_rows(manifest)
            for toolchain in cast(list[str], artifact["toolchain_refs"])
        }
    )


def _toolchain_evidence_ids(manifest: Mapping[str, object]) -> list[str]:
    return sorted(
        f"{artifact['id']}:{toolchain}"
        for artifact in _artifact_rows(manifest)
        for toolchain in cast(list[str], artifact["toolchain_refs"])
    )


def validate_manifest(
    manifest: Mapping[str, object], *, root: Path = ROOT
) -> dict[str, Any]:
    validate_schema(manifest, label="release supply-chain manifest")
    artifacts = _artifact_rows(manifest)
    if _exact_ids(artifacts, label="release artifact") != ARTIFACT_IDS:
        raise ReleaseSupplyChainError(
            "artifact-denominator", "the exact 17-surface release denominator changed"
        )

    surfaces = [cast(str, artifact["surface"]) for artifact in artifacts]
    compile_jobs = [cast(str, artifact["compile_job"]) for artifact in artifacts]
    publish_jobs = [cast(str, artifact["publish_job"]) for artifact in artifacts]
    for values, label in (
        (surfaces, "surface"),
        (compile_jobs, "compile job"),
        (publish_jobs, "publish job"),
    ):
        if len(set(values)) != len(values):
            raise ReleaseSupplyChainError("artifact-denominator", f"duplicate {label}")

    security_policy = load_json(root / cast(str, manifest["security_policy"]))
    load_json(root / cast(str, manifest["toolchain_authority"]))
    dependency_ids = {
        item["id"]
        for item in cast(list[dict[str, Any]], security_policy["dependency_roots"])
    }
    workflow_path = root / cast(dict[str, Any], manifest["workflow_policy"])["path"]
    try:
        workflow = workflow_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReleaseSupplyChainError(
            "workflow", f"cannot read governed workflow: {error}"
        ) from error

    for artifact in artifacts:
        artifact_id = cast(str, artifact["id"])
        package_root = root / cast(str, artifact["package_root"])
        working_directory = root / cast(str, artifact["working_directory"])
        if not package_root.is_dir() or not working_directory.is_dir():
            raise ReleaseSupplyChainError(
                "artifact-path", f"{artifact_id} package or working directory is absent"
            )
        referenced_roots = set(cast(list[str], artifact["dependency_roots"]))
        unknown_roots = sorted(referenced_roots - dependency_ids)
        if unknown_roots:
            raise ReleaseSupplyChainError(
                "dependency-root",
                f"{artifact_id} references unknown dependency roots: {unknown_roots}",
            )
        for job_field in ("compile_job", "publish_job"):
            job = cast(str, artifact[job_field])
            if (
                re.search(rf"^    {re.escape(job)}:\s*$", workflow, re.MULTILINE)
                is None
            ):
                raise ReleaseSupplyChainError(
                    "workflow-job",
                    f"{artifact_id} references absent workflow job {job}",
                )

        delivery_kind = artifact["delivery_kind"]
        artifact_policy = cast(dict[str, Any], artifact["artifact_policy"])
        reproducibility = cast(dict[str, Any], artifact["reproducibility"])
        credential = cast(dict[str, Any], artifact["credential_policy"])
        if artifact_id in SOURCE_TAG_ARTIFACT_IDS:
            expected = ("source-tag", "source-tree", False, "source-identity")
        else:
            expected = (
                "package-archive",
                artifact_policy["subject_kind"],
                True,
                reproducibility["mode"],
            )
        observed = (
            delivery_kind,
            artifact_policy["subject_kind"],
            artifact_policy["checksum_required"],
            reproducibility["mode"],
        )
        if observed != expected:
            raise ReleaseSupplyChainError(
                "artifact-policy", f"{artifact_id} delivery policy is inconsistent"
            )
        if reproducibility["mode"] == "normalized":
            if not reproducibility["allowed_normalizations"]:
                raise ReleaseSupplyChainError(
                    "reproducibility", f"{artifact_id} has an unbounded normalization"
                )
        elif reproducibility["allowed_normalizations"]:
            raise ReleaseSupplyChainError(
                "reproducibility", f"{artifact_id} normalizes an exact identity mode"
            )

        if artifact_id in OIDC_ARTIFACT_IDS:
            if (
                credential["mode"] != "oidc"
                or credential["secret_names"]
                or not credential["trusted_publishing"]
            ):
                raise ReleaseSupplyChainError(
                    "credential-policy", f"{artifact_id} must use secretless OIDC"
                )
        elif credential["mode"] == "long-lived-secret":
            if not credential["secret_names"] or credential["trusted_publishing"]:
                raise ReleaseSupplyChainError(
                    "credential-policy",
                    f"{artifact_id} long-lived credential scope is malformed",
                )
        elif credential["mode"] == "github-token":
            if credential["secret_names"] or credential["trusted_publishing"]:
                raise ReleaseSupplyChainError(
                    "credential-policy",
                    f"{artifact_id} GitHub token scope is malformed",
                )

    profiles = cast(dict[str, dict[str, Any]], manifest["profile_policy"])
    for profile, (network, builds) in PROFILE_EXPECTATIONS.items():
        rule = profiles[profile]
        if (rule["network"], rule["build_artifacts"], rule["publication"]) != (
            network,
            builds,
            False,
        ):
            raise ReleaseSupplyChainError(
                "profile-policy", f"{profile} release supply-chain policy changed"
            )

    workflow_policy = cast(dict[str, Any], manifest["workflow_policy"])
    if sorted(workflow_policy["attestation_permissions"]) != [
        "artifact-metadata: write",
        "attestations: write",
        "id-token: write",
    ]:
        raise ReleaseSupplyChainError(
            "workflow-policy", "the exact attestation permission set changed"
        )
    unknown_probes = sorted(set(_toolchain_ids(manifest)) - set(TOOLCHAIN_PROBES))
    if unknown_probes:
        raise ReleaseSupplyChainError(
            "toolchain-policy", f"toolchain probes are undefined: {unknown_probes}"
        )
    return cast(dict[str, Any], manifest)


def validate_contract_fixture(
    fixture: Mapping[str, object], manifest: Mapping[str, object]
) -> dict[str, Any]:
    validate_schema(fixture, label="release supply-chain contract fixture")
    if fixture["manifest_fingerprint"] != document_fingerprint(manifest):
        raise ReleaseSupplyChainError(
            "stale-manifest", "contract fixture manifest fingerprint changed"
        )
    if fixture["evidence_fingerprint"] != document_fingerprint(
        fixture, "evidence_fingerprint"
    ):
        raise ReleaseSupplyChainError(
            "fixture-fingerprint", "contract fixture fingerprint changed"
        )
    disclaimer = cast(str, fixture["disclaimer"])
    for required in (
        "synthetic",
        "not live artifact evidence",
        "cannot authorize publication",
    ):
        if required not in disclaimer.lower():
            raise ReleaseSupplyChainError(
                "fixture-authority",
                f"contract fixture disclaimer must contain {required!r}",
            )
    return cast(dict[str, Any], fixture)


def _aggregate_status(statuses: Sequence[str]) -> str:
    for status in STATUS_PRECEDENCE:
        if status in statuses:
            return status
    raise ReleaseSupplyChainError("status", "evidence has no artifact statuses")


def validate_evidence(
    evidence: Mapping[str, object],
    manifest: Mapping[str, object],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    validate_schema(evidence, label="release supply-chain evidence")
    validate_manifest(manifest, root=root)
    if evidence["manifest_fingerprint"] != document_fingerprint(manifest):
        raise ReleaseSupplyChainError("stale-manifest", "evidence manifest changed")
    if evidence["evidence_fingerprint"] != document_fingerprint(
        evidence, "evidence_fingerprint"
    ):
        raise ReleaseSupplyChainError("evidence-fingerprint", "evidence changed")

    authority = evidence["evidence_authority"]
    profile = evidence["profile"]
    if (authority, profile) not in {
        ("synthetic-contract", "contract"),
        ("live-dry-run", "full"),
        ("live-dry-run", "release"),
    }:
        raise ReleaseSupplyChainError(
            "evidence-authority",
            "synthetic evidence cannot claim live profile authority",
        )
    workflow = cast(dict[str, Any], evidence["workflow"])
    expected_permissions = sorted(
        cast(dict[str, Any], manifest["workflow_policy"])["attestation_permissions"]
    )
    if workflow["attestation_permissions"] != expected_permissions:
        raise ReleaseSupplyChainError(
            "workflow-permissions", "evidence attestation permissions changed"
        )
    if authority == "live-dry-run":
        workflow_path = root / cast(
            str, cast(dict[str, Any], manifest["workflow_policy"])["path"]
        )
        if workflow["workflow_sha256"] != _sha256_file(workflow_path):
            raise ReleaseSupplyChainError(
                "workflow-fingerprint", "evidence workflow fingerprint changed"
            )

    artifacts = cast(list[dict[str, Any]], evidence["artifacts"])
    if _exact_ids(artifacts, label="release evidence") != ARTIFACT_IDS:
        raise ReleaseSupplyChainError(
            "artifact-denominator", "evidence does not cover all 17 release surfaces"
        )
    contracts = {item["id"]: item for item in _artifact_rows(manifest)}
    source = cast(dict[str, Any], evidence["source"])
    rebuild_source = cast(dict[str, Any], evidence["rebuild_source"])
    if rebuild_source != source:
        raise ReleaseSupplyChainError(
            "source-rebuild", "rebuild source identity differs from primary source"
        )
    aggregate_statuses: list[str] = []
    artifact_statuses: list[str] = []
    toolchains = cast(list[dict[str, Any]], evidence["toolchains"])
    if _exact_ids(toolchains, label="toolchain evidence") != _toolchain_evidence_ids(
        manifest
    ):
        raise ReleaseSupplyChainError(
            "toolchain-denominator", "evidence toolchain denominator changed"
        )
    toolchain_policy_sha256 = document_fingerprint(
        load_json(root / cast(str, manifest["toolchain_authority"]))
    )
    for toolchain in toolchains:
        expected_id = f"{toolchain['artifact_id']}:{toolchain['toolchain_id']}"
        if toolchain["id"] != expected_id:
            raise ReleaseSupplyChainError(
                "toolchain-denominator",
                f"{toolchain['id']} toolchain coordinate is inconsistent",
            )
        aggregate_statuses.append(cast(str, toolchain["status"]))
        if toolchain["policy_sha256"] != toolchain_policy_sha256:
            raise ReleaseSupplyChainError(
                "toolchain-policy", f"{toolchain['id']} toolchain policy changed"
            )
        if toolchain["status"] == "passed":
            if (
                toolchain["version"] is None
                or toolchain["executable"] is None
                or toolchain["executable_sha256"] is None
                or toolchain["findings"]
            ):
                raise ReleaseSupplyChainError(
                    "false-pass", f"{toolchain['id']} toolchain passed incompletely"
                )
        elif not toolchain["findings"]:
            raise ReleaseSupplyChainError(
                "missing-finding",
                f"{toolchain['id']} toolchain nonpass lacks a finding",
            )
    for row in artifacts:
        artifact_id = cast(str, row["id"])
        contract = contracts[artifact_id]
        artifact_statuses.append(cast(str, row["status"]))
        aggregate_statuses.append(cast(str, row["status"]))
        subject = cast(dict[str, Any], row["subject"])
        checksum = cast(dict[str, Any], row["checksum"])
        provenance = cast(dict[str, Any], row["provenance"])
        reproducibility = cast(dict[str, Any], row["reproducibility"])
        credential = cast(dict[str, Any], row["credential"])
        contract_artifact = cast(dict[str, Any], contract["artifact_policy"])
        contract_reproducibility = cast(dict[str, Any], contract["reproducibility"])
        contract_credential = cast(dict[str, Any], contract["credential_policy"])

        if subject["kind"] != contract_artifact["subject_kind"]:
            raise ReleaseSupplyChainError(
                "subject-kind", f"{artifact_id} subject kind changed"
            )
        if checksum["digest"] != subject["sha256"]:
            raise ReleaseSupplyChainError(
                "checksum-subject", f"{artifact_id} checksum does not name its subject"
            )
        if (
            provenance["subject_name"] != subject["name"]
            or provenance["subject_sha256"] != subject["sha256"]
            or provenance["source_commit"] != source["commit"]
        ):
            raise ReleaseSupplyChainError(
                "provenance-subject", f"{artifact_id} provenance subject changed"
            )
        if (
            provenance["build_command_sha256"]
            != hashlib.sha256(canonical_json(contract["build_command"])).hexdigest()
        ):
            raise ReleaseSupplyChainError(
                "provenance-command", f"{artifact_id} build command changed"
            )
        if reproducibility["mode"] != contract_reproducibility["mode"]:
            raise ReleaseSupplyChainError(
                "reproducibility", f"{artifact_id} reproducibility mode changed"
            )
        if (
            reproducibility["normalized_fields"]
            != contract_reproducibility["allowed_normalizations"]
        ):
            raise ReleaseSupplyChainError(
                "reproducibility", f"{artifact_id} normalization scope changed"
            )
        if reproducibility["mode"] == "normalized":
            if (
                reproducibility["status"] == "passed"
                and reproducibility["normalized_sha256"] is None
            ):
                raise ReleaseSupplyChainError(
                    "reproducibility", f"{artifact_id} lacks normalized identity"
                )
        elif reproducibility["normalized_sha256"] is not None:
            raise ReleaseSupplyChainError(
                "reproducibility", f"{artifact_id} exact identity was normalized"
            )
        if reproducibility["status"] == "passed" and (
            reproducibility["mode"] != "normalized"
            and (
                reproducibility["first_sha256"] != subject["sha256"]
                or reproducibility["second_sha256"] != subject["sha256"]
            )
        ):
            raise ReleaseSupplyChainError(
                "reproducibility", f"{artifact_id} exact rebuild differs"
            )
        if (
            credential["mode"] != contract_credential["mode"]
            or credential["secret_names"] != contract_credential["secret_names"]
        ):
            raise ReleaseSupplyChainError(
                "credential-policy", f"{artifact_id} credential scope changed"
            )
        expected_issuer = (
            "https://token.actions.githubusercontent.com"
            if credential["mode"] == "oidc"
            else None
        )
        if credential["oidc_issuer"] != expected_issuer:
            raise ReleaseSupplyChainError(
                "credential-policy", f"{artifact_id} OIDC issuer changed"
            )
        if row["status"] == "passed":
            if (
                row["findings"]
                or cast(dict[str, Any], row["sbom"])["unresolved_components"]
                or reproducibility["status"] != "passed"
            ):
                raise ReleaseSupplyChainError(
                    "false-pass", f"{artifact_id} passed with unresolved evidence"
                )
        elif not row["findings"]:
            raise ReleaseSupplyChainError(
                "missing-finding", f"{artifact_id} nonpass lacks a finding"
            )

    summary = cast(dict[str, int], evidence["summary"])
    observed_summary = {
        status: artifact_statuses.count(status) for status in STATUS_PRECEDENCE
    }
    observed_summary["total"] = len(artifact_statuses)
    if summary != observed_summary:
        raise ReleaseSupplyChainError("summary", "artifact summary changed")
    if evidence["status"] != _aggregate_status(aggregate_statuses):
        raise ReleaseSupplyChainError("status", "aggregate status is inconsistent")
    return cast(dict[str, Any], evidence)


def synthetic_evidence(manifest: Mapping[str, object]) -> dict[str, Any]:
    """Build an in-memory no-authority fixture for controlled contract tests."""

    commit = "0" * 40
    toolchain_policy_sha256 = document_fingerprint(
        load_json(ROOT / cast(str, manifest["toolchain_authority"]))
    )
    toolchains = []
    for contract in _artifact_rows(manifest):
        artifact_id = cast(str, contract["id"])
        for toolchain_id in cast(list[str], contract["toolchain_refs"]):
            coordinate = f"{artifact_id}:{toolchain_id}"
            toolchains.append(
                {
                    "id": coordinate,
                    "artifact_id": artifact_id,
                    "toolchain_id": toolchain_id,
                    "status": "passed",
                    "version": "fixture",
                    "executable": f"fixture/{coordinate}",
                    "executable_sha256": hashlib.sha256(
                        f"{coordinate}:executable".encode()
                    ).hexdigest(),
                    "runner_os": "fixture-os",
                    "runner_arch": "fixture-arch",
                    "policy_sha256": toolchain_policy_sha256,
                    "findings": [],
                }
            )
    toolchains.sort(key=lambda row: cast(str, row["id"]))
    rows: list[dict[str, Any]] = []
    for contract in _artifact_rows(manifest):
        artifact_id = cast(str, contract["id"])
        digest = hashlib.sha256(artifact_id.encode("utf-8")).hexdigest()
        sbom_digest = hashlib.sha256(f"{artifact_id}:sbom".encode()).hexdigest()
        predicate_digest = hashlib.sha256(
            f"{artifact_id}:provenance".encode()
        ).hexdigest()
        artifact_policy = cast(dict[str, Any], contract["artifact_policy"])
        reproducibility = cast(dict[str, Any], contract["reproducibility"])
        credential = cast(dict[str, Any], contract["credential_policy"])
        subject_name = f"fixture/{artifact_id.removeprefix('release:')}.artifact"
        rows.append(
            {
                "id": artifact_id,
                "status": "passed",
                "subject": {
                    "name": subject_name,
                    "kind": artifact_policy["subject_kind"],
                    "sha256": digest,
                    "bytes": None
                    if artifact_policy["subject_kind"] == "source-tree"
                    else 1,
                },
                "checksum": {"algorithm": "sha256", "digest": digest},
                "sbom": {
                    "spdx_version": "SPDX-2.3",
                    "document_namespace": (
                        "https://strling.dev/sbom/fixture/"
                        + artifact_id.removeprefix("release:")
                    ),
                    "sha256": sbom_digest,
                    "component_count": 1,
                    "relationship_count": 0,
                    "unresolved_components": 0,
                },
                "provenance": {
                    "statement_type": "https://in-toto.io/Statement/v1",
                    "predicate_type": "https://slsa.dev/provenance/v1",
                    "subject_name": subject_name,
                    "subject_sha256": digest,
                    "source_commit": commit,
                    "builder_id": "https://strling.dev/builders/release-supply-chain-fixture",
                    "build_command_sha256": hashlib.sha256(
                        canonical_json(contract["build_command"])
                    ).hexdigest(),
                    "predicate_sha256": predicate_digest,
                },
                "reproducibility": {
                    "mode": reproducibility["mode"],
                    "status": "passed",
                    "first_sha256": digest,
                    "second_sha256": digest,
                    "normalized_sha256": digest
                    if reproducibility["mode"] == "normalized"
                    else None,
                    "normalized_fields": reproducibility["allowed_normalizations"],
                },
                "credential": {
                    "mode": credential["mode"],
                    "secret_names": credential["secret_names"],
                    "oidc_issuer": "https://token.actions.githubusercontent.com"
                    if credential["mode"] == "oidc"
                    else None,
                    "environment": "release",
                    "untrusted_context_forbidden": True,
                },
                "findings": [],
            }
        )
    evidence: dict[str, Any] = {
        "schema_version": "1.0.0",
        "document_kind": "release-supply-chain-evidence",
        "operation_id": "certification.release-supply-chain",
        "profile": "contract",
        "status": "passed",
        "evidence_authority": "synthetic-contract",
        "publication_authorized": False,
        "manifest_fingerprint": document_fingerprint(manifest),
        "source": {
            "commit": commit,
            "dirty": False,
            "tree_sha256": hashlib.sha256(b"fixture-tree").hexdigest(),
        },
        "rebuild_source": {
            "commit": commit,
            "dirty": False,
            "tree_sha256": hashlib.sha256(b"fixture-tree").hexdigest(),
        },
        "workflow": {
            "workflow_sha256": hashlib.sha256(b"fixture-workflow").hexdigest(),
            "default_read_only": True,
            "protected_environment": "release",
            "untrusted_context_isolated": True,
            "exact_artifact_handoff": True,
            "attestation_permissions": [
                "artifact-metadata: write",
                "attestations: write",
                "id-token: write",
            ],
        },
        "toolchains": toolchains,
        "artifacts": rows,
        "summary": {
            "passed": 17,
            "failed": 0,
            "unavailable": 0,
            "incomplete": 0,
            "total": 17,
        },
        "evidence_fingerprint": "0" * 64,
    }
    evidence["evidence_fingerprint"] = document_fingerprint(
        evidence, "evidence_fingerprint"
    )
    return evidence


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=4) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _relative_path(root: Path, path: Path) -> str:
    try:
        return (
            path.resolve(strict=True).relative_to(root.resolve(strict=True)).as_posix()
        )
    except (OSError, ValueError) as error:
        raise ReleaseSupplyChainError(
            "artifact-path", f"artifact path escapes the authenticated root: {path}"
        ) from error


def _tree_members(root: Path, directory: Path) -> list[dict[str, object]]:
    members: list[dict[str, object]] = []
    for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ReleaseSupplyChainError(
                "artifact-symlink", f"artifact tree contains a symlink: {path}"
            )
        if path.is_file():
            members.append(
                {
                    "name": _relative_path(root, path),
                    "sha256": _sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    if not members:
        raise ReleaseSupplyChainError(
            "artifact-empty", f"artifact tree contains no files: {directory}"
        )
    return members


def _source_tree_members(root: Path, directory: Path) -> list[dict[str, object]]:
    """Describe a source delivery from authenticated Git inputs only."""

    if not (root / ".git").exists():
        return _tree_members(root, directory)
    relative_directory = _relative_path(root, directory)
    tracked = _git_output(root, ["ls-files", "-z", "--", relative_directory]).split(
        b"\0"
    )
    members: list[dict[str, object]] = []
    for raw_relative in tracked:
        if not raw_relative:
            continue
        try:
            relative = raw_relative.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ReleaseSupplyChainError(
                "artifact-path", "tracked source path is not valid UTF-8"
            ) from error
        path = root / relative
        if _relative_path(root, path) != relative:
            raise ReleaseSupplyChainError(
                "artifact-path", f"tracked source path is not canonical: {relative}"
            )
        if path.is_symlink():
            raise ReleaseSupplyChainError(
                "artifact-symlink", f"source tree contains a symlink: {relative}"
            )
        if not path.is_file():
            raise ReleaseSupplyChainError(
                "artifact-missing", f"tracked source file is absent: {relative}"
            )
        members.append(
            {
                "name": relative,
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    if not members:
        raise ReleaseSupplyChainError(
            "artifact-empty", f"source tree contains no tracked files: {directory}"
        )
    return members


def _surface_members(
    root: Path, artifact: Mapping[str, object], version: str
) -> list[dict[str, object]]:
    policy = cast(dict[str, Any], artifact["artifact_policy"])
    paths: dict[str, Path] = {}
    for raw_pattern in cast(list[str], policy["patterns"]):
        pattern = raw_pattern.replace("VERSION", version)
        for path in root.glob(pattern):
            relative = _relative_path(root, path)
            paths[relative] = path
    if not paths:
        raise ReleaseSupplyChainError(
            "artifact-missing", f"{artifact['id']} did not match an artifact"
        )
    if len(paths) > cast(int, policy["maximum_subjects"]):
        raise ReleaseSupplyChainError(
            "artifact-count", f"{artifact['id']} exceeded its maximum subject count"
        )

    members: list[dict[str, object]] = []
    for relative, path in sorted(paths.items()):
        if path.is_symlink():
            raise ReleaseSupplyChainError(
                "artifact-symlink", f"artifact subject is a symlink: {relative}"
            )
        if path.is_dir():
            nested = (
                _source_tree_members(root, path)
                if policy["subject_kind"] == "source-tree"
                else _tree_members(root, path)
            )
            members.append(
                {
                    "name": relative,
                    "sha256": hashlib.sha256(canonical_json(nested)).hexdigest(),
                    "bytes": sum(cast(int, row["bytes"]) for row in nested),
                    "files": nested,
                }
            )
        elif path.is_file():
            members.append(
                {
                    "name": relative,
                    "sha256": _sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
        else:
            raise ReleaseSupplyChainError(
                "artifact-path", f"artifact subject has an unsupported type: {relative}"
            )
    return members


def _member_from_path(
    root: Path, relative: str, *, source_tree: bool = False
) -> dict[str, object]:
    path = root / relative
    authenticated = _relative_path(root, path)
    if authenticated != relative:
        raise ReleaseSupplyChainError(
            "artifact-path", f"artifact path is not canonical: {relative}"
        )
    if path.is_symlink():
        raise ReleaseSupplyChainError(
            "artifact-symlink", f"artifact subject is a symlink: {relative}"
        )
    if path.is_dir():
        nested = (
            _source_tree_members(root, path)
            if source_tree
            else _tree_members(root, path)
        )
        return {
            "name": relative,
            "sha256": hashlib.sha256(canonical_json(nested)).hexdigest(),
            "bytes": sum(cast(int, row["bytes"]) for row in nested),
            "files": nested,
        }
    if path.is_file():
        return {
            "name": relative,
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        }
    raise ReleaseSupplyChainError(
        "artifact-missing", f"artifact subject is absent: {relative}"
    )


def _surface_identity(members: Sequence[Mapping[str, object]]) -> tuple[str, str, int]:
    projected = [
        {"name": row["name"], "sha256": row["sha256"], "bytes": row["bytes"]}
        for row in members
    ]
    if len(projected) == 1:
        name = cast(str, projected[0]["name"])
        digest = cast(str, projected[0]["sha256"])
    else:
        name = (
            "strling-release-set:"
            + hashlib.sha256(
                canonical_json([row["name"] for row in projected])
            ).hexdigest()[:16]
        )
        digest = hashlib.sha256(canonical_json(projected)).hexdigest()
    return name, digest, sum(cast(int, row["bytes"]) for row in projected)


def _git_output(root: Path, arguments: Sequence[str]) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ReleaseSupplyChainError(
            "source-authentication", f"cannot authenticate Git source: {error}"
        ) from error
    return completed.stdout


def authenticate_source(root: Path) -> dict[str, object]:
    commit = _git_output(root, ["rev-parse", "HEAD"]).decode().strip()
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ReleaseSupplyChainError("source-authentication", "Git HEAD is not exact")
    dirty = _git_output(root, ["status", "--porcelain", "--untracked-files=all"])
    if dirty:
        raise ReleaseSupplyChainError(
            "source-dirty", "release evidence requires a clean source tree"
        )
    submodules = _git_output(root, ["submodule", "status", "--recursive"])
    if submodules:
        raise ReleaseSupplyChainError(
            "source-submodule", "release evidence forbids unauthenticated submodules"
        )
    tracked = _git_output(root, ["ls-files", "-s", "-z"])
    return {
        "commit": commit,
        "dirty": False,
        "tree_sha256": hashlib.sha256(tracked).hexdigest(),
    }


def _permission_set(value: object) -> set[str]:
    if not isinstance(value, dict):
        return set()
    return {
        f"{key}: {permission}"
        for key, permission in value.items()
        if isinstance(key, str) and isinstance(permission, str)
    }


def _workflow_artifact_name(artifact: Mapping[str, object]) -> str:
    slug = re.sub(
        r"[^a-z0-9]+", "-", cast(str, artifact["id"]).removeprefix("release:")
    ).strip("-")
    return f"release-{slug}-${{{{ needs.verify-release.outputs.release_ref }}}}"


def _workflow_rebuild_name(artifact: Mapping[str, object]) -> str:
    slug = re.sub(
        r"[^a-z0-9]+", "-", cast(str, artifact["id"]).removeprefix("release:")
    ).strip("-")
    return f"rebuild-{slug}-${{{{ needs.verify-release.outputs.release_ref }}}}"


def _workflow_receipt_name(artifact: Mapping[str, object]) -> str:
    slug = re.sub(
        r"[^a-z0-9]+", "-", cast(str, artifact["id"]).removeprefix("release:")
    ).strip("-")
    return (
        f"release-build-receipt-{slug}-"
        "${{ needs.verify-release.outputs.release_ref }}"
    )


def qualify_workflow(root: Path, manifest: Mapping[str, object]) -> dict[str, object]:
    policy = cast(dict[str, Any], manifest["workflow_policy"])
    path = root / cast(str, policy["path"])
    try:
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ReleaseSupplyChainError(
            "workflow", f"cannot parse the governed release workflow: {error}"
        ) from error
    if not isinstance(workflow, dict) or not isinstance(workflow.get("jobs"), dict):
        raise ReleaseSupplyChainError("workflow", "release workflow has no job map")
    jobs = cast(dict[str, dict[str, Any]], workflow["jobs"])
    triggers = workflow.get("on", workflow.get(True))
    if not isinstance(triggers, dict) or any(
        event in triggers for event in ("pull_request", "pull_request_target")
    ):
        raise ReleaseSupplyChainError(
            "workflow-trigger", "release workflow is callable from untrusted code"
        )
    if workflow.get("permissions") != {"contents": "read"}:
        raise ReleaseSupplyChainError(
            "workflow-permissions",
            "release workflow default permissions are not read-only",
        )

    certify = jobs.get("certify-release-supply-chain")
    required_permissions = set(cast(list[str], policy["attestation_permissions"]))
    if not isinstance(certify, dict):
        raise ReleaseSupplyChainError(
            "workflow-certification",
            "release workflow lacks the common certification job",
        )
    certify_environment = certify.get("environment")
    certify_environment_name = (
        certify_environment.get("name")
        if isinstance(certify_environment, dict)
        else certify_environment
    )
    if certify_environment_name != policy["protected_environment"]:
        raise ReleaseSupplyChainError(
            "workflow-environment",
            "certification job is outside the release environment",
        )
    certify_permissions = _permission_set(certify.get("permissions"))
    if not required_permissions.issubset(certify_permissions):
        raise ReleaseSupplyChainError(
            "workflow-permissions", "certification job lacks attestation permissions"
        )
    certify_needs = certify.get("needs", [])
    if isinstance(certify_needs, str):
        certify_needs = [certify_needs]
    required_needs = {
        "verify-release",
        *[cast(str, artifact["compile_job"]) for artifact in _artifact_rows(manifest)],
    }
    if not isinstance(certify_needs, list) or set(certify_needs) != required_needs:
        raise ReleaseSupplyChainError(
            "workflow-certification",
            "certification job does not consume the exact compile denominator",
        )
    certify_steps = cast(list[dict[str, Any]], certify.get("steps", []))
    if not any(
        "actions/attest@" in str(step.get("uses", "")) for step in certify_steps
    ):
        raise ReleaseSupplyChainError(
            "workflow-certification", "certification job lacks artifact attestation"
        )
    certify_commands = "\n".join(
        str(step.get("run", "")) for step in certify_steps if "run" in step
    )
    for required_command in (
        "release_supply_chain security",
        "release_supply_chain produce",
        "release_supply_chain verify",
    ):
        if required_command not in certify_commands:
            raise ReleaseSupplyChainError(
                "workflow-certification",
                f"certification job lacks {required_command}",
            )
    release_certification = jobs.get("release-certification")
    if not isinstance(release_certification, dict):
        raise ReleaseSupplyChainError(
            "workflow-certification", "release profile certification job is absent"
        )
    if release_certification.get("needs") not in (None, []):
        raise ReleaseSupplyChainError(
            "workflow-certification",
            "canonical release certification must precede release preflight",
        )
    release_commands = "\n".join(
        str(step.get("run", ""))
        for step in cast(list[dict[str, Any]], release_certification.get("steps", []))
        if "run" in step
    )
    if "strling profile release" not in release_commands:
        raise ReleaseSupplyChainError(
            "workflow-certification", "release job does not run the canonical profile"
        )
    verify_release = jobs.get("verify-release")
    if not isinstance(verify_release, dict) or verify_release.get("needs") != (
        "release-certification"
    ):
        raise ReleaseSupplyChainError(
            "workflow-certification",
            "release preflight does not depend on canonical release certification",
        )

    for artifact in _artifact_rows(manifest):
        compile_job = cast(str, artifact["compile_job"])
        publish_job = cast(str, artifact["publish_job"])
        compile_config = jobs.get(compile_job)
        publish_config = jobs.get(publish_job)
        if not isinstance(compile_config, dict) or not isinstance(publish_config, dict):
            raise ReleaseSupplyChainError(
                "workflow-job", f"release workflow lacks {compile_job} or {publish_job}"
            )
        environment = publish_config.get("environment")
        environment_name = (
            environment.get("name") if isinstance(environment, dict) else environment
        )
        if environment_name != policy["protected_environment"]:
            raise ReleaseSupplyChainError(
                "workflow-environment",
                f"{publish_job} is outside the release environment",
            )
        condition = str(publish_config.get("if", ""))
        if "is_dry_run == 'false'" not in condition:
            raise ReleaseSupplyChainError(
                "workflow-credentials",
                f"{publish_job} can receive publication authority during dry-run",
            )
        needs = publish_config.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        if (
            compile_job not in needs
            or "certify-release-supply-chain" not in needs
            or "release-certification" not in needs
        ):
            raise ReleaseSupplyChainError(
                "workflow-handoff",
                f"{publish_job} does not consume certified build identity",
            )
        compile_steps = cast(list[dict[str, Any]], compile_config.get("steps", []))
        publish_steps = cast(list[dict[str, Any]], publish_config.get("steps", []))
        uploads = [
            step
            for step in compile_steps
            if "actions/upload-artifact@" in str(step.get("uses", ""))
        ]
        downloads = [
            step
            for step in publish_steps
            if "actions/download-artifact@" in str(step.get("uses", ""))
        ]
        if len(uploads) != 3:
            raise ReleaseSupplyChainError(
                "workflow-handoff",
                f"{compile_job} does not upload its artifact, rebuild, and receipts",
            )
        if len(downloads) != 1:
            raise ReleaseSupplyChainError(
                "workflow-handoff",
                f"{publish_job} does not download its exact artifact",
            )
        download_with = downloads[0].get("with")
        expected_name = _workflow_artifact_name(artifact)
        expected_rebuild_name = _workflow_rebuild_name(artifact)
        expected_receipt_name = _workflow_receipt_name(artifact)
        expected_paths = [
            str(path).replace("VERSION", "${{ needs.verify-release.outputs.version }}")
            for path in cast(dict[str, Any], artifact["artifact_policy"])["patterns"]
        ]
        expected_rebuild_paths = [f".rebuild/{path}" for path in expected_paths]
        slug = cast(str, artifact["id"]).removeprefix("release:")
        expected_receipt_paths = [
            f"artifacts/build-receipts/{slug}-first.json",
            f"artifacts/build-receipts/{slug}-second.json",
        ]
        uploads_by_name = {
            cast(str, step["with"]["name"]): cast(dict[str, Any], step["with"])
            for step in uploads
            if isinstance(step.get("with"), dict)
            and isinstance(step["with"].get("name"), str)
        }
        if set(uploads_by_name) != {
            expected_name,
            expected_rebuild_name,
            expected_receipt_name,
        }:
            raise ReleaseSupplyChainError(
                "workflow-handoff", f"{artifact['id']} upload names changed"
            )
        for name, paths in (
            (expected_name, expected_paths),
            (expected_rebuild_name, expected_rebuild_paths),
            (expected_receipt_name, expected_receipt_paths),
        ):
            upload_with = uploads_by_name[name]
            observed_paths = [
                line.strip() for line in str(upload_with.get("path", "")).splitlines()
            ]
            if (
                observed_paths != paths
                or upload_with.get("if-no-files-found") != "error"
            ):
                raise ReleaseSupplyChainError(
                    "workflow-handoff",
                    f"{artifact['id']} {name} upload paths changed",
                )
        if (
            not isinstance(download_with, dict)
            or download_with.get("name") != expected_name
            or download_with.get("path") != artifact["package_root"]
        ):
            raise ReleaseSupplyChainError(
                "workflow-handoff",
                f"{artifact['id']} artifact name or path handoff changed",
            )

    workflow_text = path.read_text(encoding="utf-8")
    for action in re.findall(r"\buses:\s*([^\s#]+)", workflow_text):
        if "@" in action and re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) is None:
            raise ReleaseSupplyChainError(
                "workflow-action", f"workflow action is not immutable: {action}"
            )
    return {
        "workflow_sha256": _sha256_file(path),
        "default_read_only": True,
        "protected_environment": "release",
        "untrusted_context_isolated": True,
        "exact_artifact_handoff": True,
        "attestation_permissions": sorted(required_permissions),
    }


def probe_toolchains(
    root: Path, manifest: Mapping[str, object]
) -> list[dict[str, object]]:
    policy_sha256 = document_fingerprint(
        load_json(root / cast(str, manifest["toolchain_authority"]))
    )
    rows: list[dict[str, object]] = []
    for artifact in _artifact_rows(manifest):
        artifact_id = cast(str, artifact["id"])
        for toolchain_id in cast(list[str], artifact["toolchain_refs"]):
            rows.append(
                _probe_toolchain(
                    root,
                    artifact_id=artifact_id,
                    toolchain_id=toolchain_id,
                    policy_sha256=policy_sha256,
                )
            )
    return sorted(rows, key=lambda row: cast(str, row["id"]))


def _probe_toolchain(
    root: Path,
    *,
    artifact_id: str,
    toolchain_id: str,
    policy_sha256: str,
) -> dict[str, object]:
    candidates, version_args = TOOLCHAIN_PROBES[toolchain_id]
    coordinate = f"{artifact_id}:{toolchain_id}"
    runner = {"runner_os": platform.system(), "runner_arch": platform.machine()}
    repository_candidates: list[Path] = []
    if artifact_id == "release:kotlin" and toolchain_id == "gradle":
        repository_candidates.extend(
            [root / "bindings/kotlin/gradlew", root / "bindings/kotlin/gradlew.bat"]
        )
    executable = next(
        (str(path) for path in repository_candidates if path.is_file()),
        None,
    ) or next((shutil.which(name) for name in candidates if shutil.which(name)), None)
    if executable is None:
        return {
            "id": coordinate,
            "artifact_id": artifact_id,
            "toolchain_id": toolchain_id,
            "status": "unavailable",
            "version": None,
            "executable": None,
            "executable_sha256": None,
            **runner,
            "policy_sha256": policy_sha256,
            "findings": [
                {
                    "code": "SUPPLY-TOOLCHAIN-UNAVAILABLE",
                    "message": f"{coordinate} executable is unavailable",
                }
            ],
        }
    try:
        completed = subprocess.run(
            [executable, *version_args],
            cwd=root,
            env=_canonical_subprocess_environment(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        version = " ".join(completed.stdout.split())
        if not version:
            raise ValueError("empty version output")
        return {
            "id": coordinate,
            "artifact_id": artifact_id,
            "toolchain_id": toolchain_id,
            "status": "passed",
            "version": version,
            "executable": Path(executable).resolve().as_posix(),
            "executable_sha256": _sha256_file(Path(executable)),
            **runner,
            "policy_sha256": policy_sha256,
            "findings": [],
        }
    except (
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        ValueError,
    ) as error:
        return {
            "id": coordinate,
            "artifact_id": artifact_id,
            "toolchain_id": toolchain_id,
            "status": "incomplete",
            "version": None,
            "executable": Path(executable).resolve().as_posix(),
            "executable_sha256": _sha256_file(Path(executable)),
            **runner,
            "policy_sha256": policy_sha256,
            "findings": [
                {
                    "code": "SUPPLY-TOOLCHAIN-VERSION",
                    "message": f"{coordinate} version probe failed: {error}",
                }
            ],
        }


def _canonical_subprocess_environment() -> dict[str, str] | None:
    """Remove case-duplicate PATH keys that native Windows tools reject."""

    if os.name != "nt":
        return None
    environment = {
        key: value for key, value in os.environ.items() if key.casefold() != "path"
    }
    path_values = [
        value for key, value in os.environ.items() if key.casefold() == "path"
    ]
    environment["Path"] = os.pathsep.join(dict.fromkeys(path_values))
    return environment


def capture_build_receipt(
    *,
    root: Path,
    artifact_id: str,
    version: str,
    output_path: Path,
    manifest: Mapping[str, object],
) -> dict[str, Any]:
    """Capture the exact output and environment of one completed dry-run build."""

    if output_path.exists():
        raise ReleaseSupplyChainError(
            "output-exists", "build receipt output must not already exist"
        )
    validate_manifest(manifest, root=root)
    contracts = {cast(str, row["id"]): row for row in _artifact_rows(manifest)}
    if artifact_id not in contracts:
        raise ReleaseSupplyChainError(
            "artifact-denominator", f"unknown release artifact: {artifact_id}"
        )
    artifact = contracts[artifact_id]
    source = authenticate_source(root)
    members = _surface_members(root, artifact, version)
    subject_name, subject_sha256, subject_bytes = _surface_identity(members)
    policy_sha256 = document_fingerprint(
        load_json(root / cast(str, manifest["toolchain_authority"]))
    )
    toolchains = [
        _probe_toolchain(
            root,
            artifact_id=artifact_id,
            toolchain_id=toolchain_id,
            policy_sha256=policy_sha256,
        )
        for toolchain_id in cast(list[str], artifact["toolchain_refs"])
    ]
    toolchains.sort(key=lambda row: cast(str, row["id"]))
    reproducibility = cast(dict[str, Any], artifact["reproducibility"])
    normalized_sha256 = (
        _normalized_surface_sha256(
            root,
            members,
            cast(list[str], reproducibility["allowed_normalizations"]),
        )
        if reproducibility["mode"] == "normalized"
        else None
    )
    receipt: dict[str, Any] = {
        "schema_version": "1.0.0",
        "document_kind": "release-build-receipt",
        "operation_id": "certification.release-build-capture",
        "artifact_id": artifact_id,
        "source": source,
        "build_command_sha256": hashlib.sha256(
            canonical_json(artifact["build_command"])
        ).hexdigest(),
        "subject": {
            "name": subject_name,
            "sha256": subject_sha256,
            "bytes": subject_bytes,
            "members": members,
            "normalized_sha256": normalized_sha256,
        },
        "toolchains": toolchains,
        "publication_authorized": False,
        "receipt_fingerprint": "0" * 64,
    }
    receipt["receipt_fingerprint"] = document_fingerprint(
        receipt, "receipt_fingerprint"
    )
    _validate_build_receipt(
        receipt,
        root=root,
        artifact=artifact,
        version=version,
        require_passed_toolchains=False,
    )
    _write_json(output_path, receipt)
    return receipt


def _validate_build_receipt(
    receipt: Mapping[str, object],
    *,
    root: Path,
    artifact: Mapping[str, object],
    version: str,
    require_passed_toolchains: bool,
) -> dict[str, Any]:
    required = {
        "schema_version",
        "document_kind",
        "operation_id",
        "artifact_id",
        "source",
        "build_command_sha256",
        "subject",
        "toolchains",
        "publication_authorized",
        "receipt_fingerprint",
    }
    artifact_id = cast(str, artifact["id"])
    if set(receipt) != required:
        raise ReleaseSupplyChainError(
            "build-receipt", f"{artifact_id} build receipt fields changed"
        )
    if (
        receipt["schema_version"] != "1.0.0"
        or receipt["document_kind"] != "release-build-receipt"
        or receipt["operation_id"] != "certification.release-build-capture"
        or receipt["artifact_id"] != artifact_id
        or receipt["publication_authorized"] is not False
    ):
        raise ReleaseSupplyChainError(
            "build-receipt", f"{artifact_id} build receipt authority changed"
        )
    if receipt["receipt_fingerprint"] != document_fingerprint(
        receipt, "receipt_fingerprint"
    ):
        raise ReleaseSupplyChainError(
            "build-receipt", f"{artifact_id} build receipt changed"
        )
    if receipt["source"] != authenticate_source(root):
        raise ReleaseSupplyChainError(
            "source-rebuild", f"{artifact_id} build receipt source changed"
        )
    if (
        receipt["build_command_sha256"]
        != hashlib.sha256(canonical_json(artifact["build_command"])).hexdigest()
    ):
        raise ReleaseSupplyChainError(
            "provenance-command", f"{artifact_id} build receipt command changed"
        )
    observed_members = _surface_members(root, artifact, version)
    observed_name, observed_sha256, observed_bytes = _surface_identity(observed_members)
    reproducibility = cast(dict[str, Any], artifact["reproducibility"])
    subject = receipt["subject"]
    if not isinstance(subject, dict) or subject != {
        "name": observed_name,
        "sha256": observed_sha256,
        "bytes": observed_bytes,
        "members": observed_members,
        "normalized_sha256": (
            _normalized_surface_sha256(
                root,
                observed_members,
                cast(list[str], reproducibility["allowed_normalizations"]),
            )
            if reproducibility["mode"] == "normalized"
            else None
        ),
    }:
        raise ReleaseSupplyChainError(
            "build-receipt", f"{artifact_id} build receipt subject changed"
        )
    toolchains = receipt["toolchains"]
    if not isinstance(toolchains, list) or _exact_ids(
        cast(list[Mapping[str, object]], toolchains), label="build receipt toolchain"
    ) != sorted(
        f"{artifact_id}:{toolchain}"
        for toolchain in cast(list[str], artifact["toolchain_refs"])
    ):
        raise ReleaseSupplyChainError(
            "toolchain-denominator", f"{artifact_id} build receipt toolchains changed"
        )
    if require_passed_toolchains and any(
        row.get("status") != "passed"
        for row in cast(list[Mapping[str, object]], toolchains)
    ):
        raise ReleaseSupplyChainError(
            "toolchain-unavailable", f"{artifact_id} build toolchain is not qualified"
        )
    return cast(dict[str, Any], receipt)


def load_build_receipts(
    *,
    receipt_dir: Path,
    root: Path,
    second_root: Path,
    manifest: Mapping[str, object],
    version: str,
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    toolchains: list[dict[str, object]] = []
    first_source: dict[str, object] | None = None
    second_source: dict[str, object] | None = None
    for artifact in _artifact_rows(manifest):
        artifact_id = cast(str, artifact["id"])
        slug = artifact_id.removeprefix("release:")
        first = _validate_build_receipt(
            load_json(receipt_dir / f"{slug}-first.json"),
            root=root,
            artifact=artifact,
            version=version,
            require_passed_toolchains=True,
        )
        second = _validate_build_receipt(
            load_json(receipt_dir / f"{slug}-second.json"),
            root=second_root,
            artifact=artifact,
            version=version,
            require_passed_toolchains=True,
        )
        if first["toolchains"] != second["toolchains"]:
            raise ReleaseSupplyChainError(
                "toolchain-rebuild",
                f"{artifact_id} rebuild toolchain fingerprint changed",
            )
        if first_source is None:
            first_source = cast(dict[str, object], first["source"])
            second_source = cast(dict[str, object], second["source"])
        elif first["source"] != first_source or second["source"] != second_source:
            raise ReleaseSupplyChainError(
                "source-rebuild", "build receipts do not share one source identity"
            )
        toolchains.extend(cast(list[dict[str, object]], first["toolchains"]))
    if first_source is None or second_source is None:
        raise ReleaseSupplyChainError("build-receipt", "build receipt set is empty")
    return (
        sorted(toolchains, key=lambda row: cast(str, row["id"])),
        first_source,
        second_source,
    )


def stage_downloaded_artifacts(
    *,
    download_root: Path,
    receipt_dir: Path,
    first_root: Path,
    second_root: Path,
    release_ref: str,
    manifest: Mapping[str, object],
) -> dict[str, object]:
    """Restore immutable workflow uploads at their governed repository paths."""

    staged = 0
    for artifact in _artifact_rows(manifest):
        artifact_id = cast(str, artifact["id"])
        slug = artifact_id.removeprefix("release:")
        for label, target_root, artifact_name in (
            ("first", first_root, f"release-{slug}-{release_ref}"),
            ("second", second_root, f"rebuild-{slug}-{release_ref}"),
        ):
            receipt = load_json(receipt_dir / f"{slug}-{label}.json")
            subject = receipt.get("subject")
            if not isinstance(subject, dict) or not isinstance(
                subject.get("members"), list
            ):
                raise ReleaseSupplyChainError(
                    "build-receipt", f"{artifact_id} {label} receipt has no members"
                )
            members = cast(list[dict[str, Any]], subject["members"])
            concrete = [
                cast(dict[str, Any], nested)
                for member in members
                for nested in (
                    cast(list[dict[str, Any]], member["files"])
                    if "files" in member
                    else [member]
                )
            ]
            member_paths = [Path(cast(str, member["name"])) for member in concrete]
            if len(members) == 1 and "files" in members[0]:
                upload_root = Path(cast(str, members[0]["name"]))
            else:
                upload_root = Path(
                    os.path.commonpath([str(path.parent) for path in member_paths])
                )
            artifact_root = download_root / artifact_name
            for member, member_path in zip(concrete, member_paths, strict=True):
                try:
                    download_relative = member_path.relative_to(upload_root)
                except ValueError as error:
                    raise ReleaseSupplyChainError(
                        "artifact-path",
                        f"{artifact_id} upload root does not contain {member_path}",
                    ) from error
                source = artifact_root / download_relative
                destination = target_root / member_path
                if not source.is_file() or _sha256_file(source) != member["sha256"]:
                    raise ReleaseSupplyChainError(
                        "workflow-handoff",
                        f"{artifact_id} downloaded {label} subject changed: {member_path}",
                    )
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                staged += 1
    return {
        "schema_version": "certification-result-v1",
        "operation_id": "certification.release-artifact-stage",
        "profile": "release",
        "status": "passed",
        "publication_authorized": False,
        "staged_files": staged,
    }


def _normalized_file_sha256(path: Path, fields: Sequence[str]) -> str:
    lowered = path.name.lower()
    if "archive-entry-timestamp" in fields and (
        lowered.endswith((".tar.gz", ".tgz", ".crate", ".gem"))
    ):
        try:
            with tarfile.open(path, "r:*") as archive:
                rows: list[dict[str, object]] = []
                for member in sorted(archive.getmembers(), key=lambda item: item.name):
                    row: dict[str, object] = {
                        "name": member.name,
                        "type": member.type.hex(),
                        "mode": member.mode,
                        "size": member.size,
                        "linkname": member.linkname,
                    }
                    if member.isfile():
                        extracted = archive.extractfile(member)
                        if extracted is None:
                            raise ReleaseSupplyChainError(
                                "reproducibility",
                                f"cannot read archive entry {member.name}",
                            )
                        row["sha256"] = hashlib.sha256(extracted.read()).hexdigest()
                    rows.append(row)
            return hashlib.sha256(canonical_json(rows)).hexdigest()
        except (OSError, tarfile.TarError) as error:
            raise ReleaseSupplyChainError(
                "reproducibility", f"cannot normalize tar artifact {path}: {error}"
            ) from error

    if any(item in fields for item in ("archive-entry-timestamp", "signature")) and (
        lowered.endswith((".zip", ".jar", ".nupkg", ".whl"))
    ):
        try:
            with zipfile.ZipFile(path) as archive:
                rows = []
                for name in sorted(archive.namelist()):
                    upper = name.upper()
                    if "signature" in fields and (
                        upper.startswith("META-INF/")
                        and upper.endswith((".SF", ".RSA", ".DSA", ".EC"))
                    ):
                        continue
                    rows.append(
                        {
                            "name": name,
                            "sha256": hashlib.sha256(archive.read(name)).hexdigest(),
                        }
                    )
            return hashlib.sha256(canonical_json(rows)).hexdigest()
        except (OSError, zipfile.BadZipFile) as error:
            raise ReleaseSupplyChainError(
                "reproducibility", f"cannot normalize ZIP artifact {path}: {error}"
            ) from error
    return _sha256_file(path)


def _normalized_surface_sha256(
    root: Path, members: Sequence[Mapping[str, object]], fields: Sequence[str]
) -> str:
    normalized: list[dict[str, str]] = []
    for member in members:
        path = root / cast(str, member["name"])
        if path.is_dir():
            nested = []
            for row in _tree_members(root, path):
                nested_path = root / cast(str, row["name"])
                nested.append(
                    {
                        "name": row["name"],
                        "sha256": _normalized_file_sha256(nested_path, fields),
                    }
                )
            digest = hashlib.sha256(canonical_json(nested)).hexdigest()
        else:
            digest = _normalized_file_sha256(path, fields)
        normalized.append({"name": cast(str, member["name"]), "sha256": digest})
    return hashlib.sha256(canonical_json(normalized)).hexdigest()


def _dependency_resolution(
    root: Path,
    manifest: Mapping[str, object],
    artifact: Mapping[str, object],
    risk_evidence: Mapping[str, object] | None = None,
) -> tuple[list[dict[str, object]], int]:
    security = load_json(root / cast(str, manifest["security_policy"]))
    policies = {
        row["id"]: row
        for row in cast(list[dict[str, Any]], security["dependency_roots"])
    }
    components: list[dict[str, object]] = []
    unresolved = 0
    risk_checks: dict[str, Mapping[str, object]] = {}
    if risk_evidence is not None:
        summary = risk_evidence.get("summary")
        raw_checks = risk_evidence.get("checks")
        if (
            risk_evidence.get("operation_id") != "security.dependency-risk"
            or risk_evidence.get("status") not in ("passed", "waived")
            or not isinstance(summary, dict)
            or any(
                summary.get(status, 0) != 0
                for status in ("failed", "incomplete", "unavailable")
            )
            or not isinstance(raw_checks, list)
        ):
            raise ReleaseSupplyChainError(
                "dependency-risk", "live dependency-risk evidence is not release-usable"
            )
        for check in raw_checks:
            if not isinstance(check, dict) or not isinstance(
                check.get("check_id"), str
            ):
                raise ReleaseSupplyChainError(
                    "dependency-risk", "live dependency-risk evidence is malformed"
                )
            risk_checks[cast(str, check["check_id"])] = check
    for dependency_id in cast(list[str], artifact["dependency_roots"]):
        policy = policies[dependency_id]
        manifest_hashes = []
        for relative in [*policy.get("manifests", []), *policy.get("locks", [])]:
            path = root / relative
            if path.is_file():
                manifest_hashes.append({"path": relative, "sha256": _sha256_file(path)})
            else:
                unresolved += 1
        resolved_without_external = policy.get(
            "risk_mode"
        ) == "no_dependencies" and policy.get("integrity_mode") in (
            "no_external_dependencies",
            "inventory_only",
        )
        resolved_components: list[dict[str, object]] = []
        evidence_hash: str | None = None
        if risk_evidence is not None:
            vulnerability = risk_checks.get(f"security.vulnerability.{dependency_id}")
            license_check = risk_checks.get(f"security.license.{dependency_id}")
            if (
                vulnerability is None
                or license_check is None
                or vulnerability.get("status") != "passed"
                or license_check.get("status") != "passed"
            ):
                unresolved += 1
            else:
                scanner = license_check.get("scanner")
                raw_components = (
                    scanner.get("components") if isinstance(scanner, dict) else None
                )
                if raw_components is None and resolved_without_external:
                    raw_components = []
                if not isinstance(raw_components, list):
                    unresolved += 1
                else:
                    for component in raw_components:
                        if (
                            not isinstance(component, dict)
                            or not all(
                                isinstance(component.get(field), str)
                                for field in (
                                    "name",
                                    "version",
                                    "reported_license",
                                    "classification",
                                    "distribution_scope",
                                )
                            )
                            or component.get("classification")
                            not in ("permitted", "scoped_permitted")
                        ):
                            unresolved += 1
                            continue
                        resolved_components.append(dict(component))
                    evidence_hash = hashlib.sha256(
                        canonical_json(
                            {"vulnerability": vulnerability, "license": license_check}
                        )
                    ).hexdigest()
        elif not resolved_without_external:
            unresolved += 1
        components.append(
            {
                "id": dependency_id,
                "policy": {
                    "ecosystem": policy.get("ecosystem"),
                    "risk_mode": policy.get("risk_mode"),
                    "integrity_mode": policy.get("integrity_mode"),
                },
                "inputs": manifest_hashes,
                "resolved_without_external": resolved_without_external,
                "resolved_components": resolved_components,
                "risk_evidence_sha256": evidence_hash,
            }
        )
    return components, unresolved


def _spdx_document(
    artifact: Mapping[str, object],
    members: Sequence[Mapping[str, object]],
    subject_digest: str,
    dependencies: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    artifact_id = cast(str, artifact["id"])
    surface = cast(str, artifact["surface"])
    namespace = f"https://strling.dev/sbom/{surface}/{subject_digest}"
    files: list[dict[str, object]] = []
    relationships: list[dict[str, str]] = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": "SPDXRef-Package",
        }
    ]
    flattened: list[Mapping[str, object]] = []
    for member in members:
        nested = member.get("files")
        if isinstance(nested, list):
            flattened.extend(cast(list[Mapping[str, object]], nested))
        else:
            flattened.append(member)
    for index, member in enumerate(flattened, start=1):
        spdx_id = f"SPDXRef-File-{index}"
        files.append(
            {
                "SPDXID": spdx_id,
                "fileName": member["name"],
                "checksums": [
                    {"algorithm": "SHA256", "checksumValue": member["sha256"]}
                ],
                "licenseConcluded": "Apache-2.0",
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-Package",
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": spdx_id,
            }
        )
    annotations = [
        {
            "annotationType": "OTHER",
            "annotator": "Tool: strling-release-supply-chain",
            "annotationDate": "1970-01-01T00:00:00Z",
            "comment": json.dumps(dependency, sort_keys=True, separators=(",", ":")),
        }
        for dependency in dependencies
    ]
    packages: list[dict[str, object]] = [
        {
            "name": cast(str, artifact["package_name"]),
            "SPDXID": "SPDXRef-Package",
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": True,
            "licenseConcluded": "Apache-2.0",
            "licenseDeclared": "Apache-2.0",
            "copyrightText": "NOASSERTION",
            "checksums": [{"algorithm": "SHA256", "checksumValue": subject_digest}],
            "externalRefs": [
                {
                    "referenceCategory": "OTHER",
                    "referenceType": "strling-release-surface",
                    "referenceLocator": artifact_id,
                }
            ],
        }
    ]
    dependency_index = 0
    for dependency in dependencies:
        root_id = cast(str, dependency["id"])
        for component in cast(
            list[Mapping[str, object]], dependency.get("resolved_components", [])
        ):
            dependency_index += 1
            name = cast(str, component["name"])
            version = cast(str, component["version"])
            reported_license = cast(str, component["reported_license"])
            selected_license = component.get("selected_license")
            identity = hashlib.sha256(
                canonical_json(
                    {
                        "root": root_id,
                        "name": name,
                        "version": version,
                    }
                )
            ).hexdigest()[:12]
            spdx_id = f"SPDXRef-Dependency-{dependency_index}-{identity}"
            coordinate = json.dumps(
                {
                    "dependency_root": root_id,
                    "ecosystem": dependency["policy"]["ecosystem"],
                    "name": name,
                    "version": version,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            packages.append(
                {
                    "name": name,
                    "versionInfo": version,
                    "SPDXID": spdx_id,
                    "downloadLocation": "NOASSERTION",
                    "filesAnalyzed": False,
                    "licenseDeclared": reported_license,
                    "licenseConcluded": (
                        selected_license
                        if isinstance(selected_license, str)
                        else reported_license
                    ),
                    "copyrightText": "NOASSERTION",
                    "externalRefs": [
                        {
                            "referenceCategory": "OTHER",
                            "referenceType": "strling-dependency-coordinate",
                            "referenceLocator": coordinate,
                        }
                    ],
                    "annotations": [
                        {
                            "annotationType": "OTHER",
                            "annotator": "Tool: strling-release-supply-chain",
                            "annotationDate": "1970-01-01T00:00:00Z",
                            "comment": json.dumps(
                                {
                                    "dependency_root": root_id,
                                    "classification": component["classification"],
                                    "disposition_id": component.get("disposition_id"),
                                    "distribution_scope": component[
                                        "distribution_scope"
                                    ],
                                },
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        }
                    ],
                }
            )
            if str(component["distribution_scope"]).startswith("non-distributed"):
                relationships.append(
                    {
                        "spdxElementId": spdx_id,
                        "relationshipType": "BUILD_DEPENDENCY_OF",
                        "relatedSpdxElement": "SPDXRef-Package",
                    }
                )
            else:
                relationships.append(
                    {
                        "spdxElementId": "SPDXRef-Package",
                        "relationshipType": "DEPENDS_ON",
                        "relatedSpdxElement": spdx_id,
                    }
                )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"STRling {surface} release artifact",
        "documentNamespace": namespace,
        "creationInfo": {
            "created": "1970-01-01T00:00:00Z",
            "creators": ["Tool: strling-release-supply-chain"],
            "licenseListVersion": "3.23",
        },
        "documentDescribes": ["SPDXRef-Package"],
        "packages": packages,
        "files": files,
        "relationships": relationships,
        "annotations": annotations,
    }


def _provenance_statement(
    artifact: Mapping[str, object],
    members: Sequence[Mapping[str, object]],
    source: Mapping[str, object],
    manifest_fingerprint: str,
    toolchains: Sequence[Mapping[str, object]],
    dependencies: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    artifact_id = cast(str, artifact["id"])
    required_toolchains = set(cast(list[str], artifact["toolchain_refs"]))
    toolchain_inputs = [
        {
            "id": row["id"],
            "executable_sha256": row["executable_sha256"],
            "version": row["version"],
        }
        for row in toolchains
        if row["artifact_id"] == artifact_id
        and row["toolchain_id"] in required_toolchains
    ]
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {"name": member["name"], "digest": {"sha256": member["sha256"]}}
            for member in members
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://strling.dev/build-types/release-supply-chain/v1",
                "externalParameters": {
                    "artifactId": artifact_id,
                    "buildCommand": artifact["build_command"],
                },
                "internalParameters": {
                    "manifestSha256": manifest_fingerprint,
                    "toolchains": toolchain_inputs,
                },
                "resolvedDependencies": [
                    {
                        "uri": f"git+https://github.com/strling-lang/strling@{source['commit']}",
                        "digest": {"gitCommit": source["commit"]},
                    },
                    *[
                        {
                            "uri": f"strling:dependency-root:{row['id']}",
                            "digest": {
                                "sha256": hashlib.sha256(
                                    canonical_json(row)
                                ).hexdigest()
                            },
                        }
                        for row in dependencies
                    ],
                ],
            },
            "runDetails": {
                "builder": {
                    "id": "https://strling.dev/builders/release-supply-chain/v1"
                },
                "metadata": {
                    "invocationId": f"{source['commit']}:{artifact_id}",
                    "startedOn": "1970-01-01T00:00:00Z",
                    "finishedOn": "1970-01-01T00:00:00Z",
                },
            },
        },
    }


def _missing_artifact_row(
    artifact: Mapping[str, object], source: Mapping[str, object], message: str
) -> dict[str, object]:
    artifact_id = cast(str, artifact["id"])
    policy = cast(dict[str, Any], artifact["artifact_policy"])
    reproducibility = cast(dict[str, Any], artifact["reproducibility"])
    credential = cast(dict[str, Any], artifact["credential_policy"])
    digest = hashlib.sha256(
        canonical_json({"id": artifact_id, "missing": True})
    ).hexdigest()
    subject_name = f"missing:{artifact_id}"
    return {
        "id": artifact_id,
        "status": "unavailable",
        "subject": {
            "name": subject_name,
            "kind": policy["subject_kind"],
            "sha256": digest,
            "bytes": None,
        },
        "checksum": {"algorithm": "sha256", "digest": digest},
        "sbom": {
            "spdx_version": "SPDX-2.3",
            "document_namespace": f"https://strling.dev/sbom/missing/{artifact_id.removeprefix('release:')}",
            "sha256": hashlib.sha256(
                f"{artifact_id}:missing-sbom".encode()
            ).hexdigest(),
            "component_count": 1,
            "relationship_count": 0,
            "unresolved_components": 1,
        },
        "provenance": {
            "statement_type": "https://in-toto.io/Statement/v1",
            "predicate_type": "https://slsa.dev/provenance/v1",
            "subject_name": subject_name,
            "subject_sha256": digest,
            "source_commit": source["commit"],
            "builder_id": "https://strling.dev/builders/release-supply-chain/v1",
            "build_command_sha256": hashlib.sha256(
                canonical_json(artifact["build_command"])
            ).hexdigest(),
            "predicate_sha256": hashlib.sha256(
                f"{artifact_id}:missing-provenance".encode()
            ).hexdigest(),
        },
        "reproducibility": {
            "mode": reproducibility["mode"],
            "status": "unavailable",
            "first_sha256": digest,
            "second_sha256": digest,
            "normalized_sha256": None,
            "normalized_fields": reproducibility["allowed_normalizations"],
        },
        "credential": {
            "mode": credential["mode"],
            "secret_names": credential["secret_names"],
            "oidc_issuer": "https://token.actions.githubusercontent.com"
            if credential["mode"] == "oidc"
            else None,
            "environment": "release",
            "untrusted_context_forbidden": True,
        },
        "findings": [{"code": "SUPPLY-ARTIFACT-UNAVAILABLE", "message": message}],
    }


def produce_bundle(
    *,
    root: Path,
    second_root: Path,
    output_dir: Path,
    version: str,
    profile: str,
    manifest: Mapping[str, object],
    source: Mapping[str, object],
    workflow: Mapping[str, object],
    toolchains: Sequence[Mapping[str, object]],
    evidence_authority: str,
    risk_evidence: Mapping[str, object] | None = None,
    rebuild_source: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """Produce deterministic evidence over two already-prepared artifact trees."""

    if output_dir.exists():
        raise ReleaseSupplyChainError(
            "output-exists", "evidence output directory must not already exist"
        )
    if evidence_authority == "live-dry-run" and rebuild_source is None:
        raise ReleaseSupplyChainError(
            "source-rebuild", "live evidence requires an authenticated rebuild source"
        )
    authenticated_rebuild = dict(rebuild_source or source)
    if authenticated_rebuild != dict(source):
        raise ReleaseSupplyChainError(
            "source-rebuild", "rebuild source identity differs from primary source"
        )
    validate_manifest(manifest, root=root)
    expected_toolchains = _toolchain_evidence_ids(manifest)
    if _exact_ids(toolchains, label="producer toolchain") != expected_toolchains:
        raise ReleaseSupplyChainError(
            "toolchain-denominator", "producer toolchain denominator changed"
        )
    manifest_fingerprint = document_fingerprint(manifest)
    toolchain_by_id = {
        (cast(str, row["artifact_id"]), cast(str, row["toolchain_id"])): row
        for row in toolchains
    }
    rows: list[dict[str, object]] = []
    companion_documents: list[tuple[Path, Mapping[str, object] | str]] = []

    for artifact in _artifact_rows(manifest):
        artifact_id = cast(str, artifact["id"])
        surface = cast(str, artifact["surface"])
        try:
            first_members = _surface_members(root, artifact, version)
            second_members = _surface_members(second_root, artifact, version)
        except ReleaseSupplyChainError as error:
            rows.append(_missing_artifact_row(artifact, source, str(error)))
            continue

        subject_name, subject_digest, subject_bytes = _surface_identity(first_members)
        _, second_digest, _ = _surface_identity(second_members)
        reproducibility_policy = cast(dict[str, Any], artifact["reproducibility"])
        mode = cast(str, reproducibility_policy["mode"])
        normalized_fields = cast(
            list[str], reproducibility_policy["allowed_normalizations"]
        )
        normalized_sha256: str | None = None
        reproducibility_status = "passed"
        findings: list[dict[str, str]] = []
        if mode == "normalized":
            first_normalized = _normalized_surface_sha256(
                root, first_members, normalized_fields
            )
            second_normalized = _normalized_surface_sha256(
                second_root, second_members, normalized_fields
            )
            normalized_sha256 = first_normalized
            if first_normalized != second_normalized:
                reproducibility_status = "failed"
                findings.append(
                    {
                        "code": "SUPPLY-REPRODUCIBILITY-MISMATCH",
                        "message": f"{artifact_id} normalized rebuild differs",
                    }
                )
        elif subject_digest != second_digest:
            reproducibility_status = "failed"
            findings.append(
                {
                    "code": "SUPPLY-REPRODUCIBILITY-MISMATCH",
                    "message": f"{artifact_id} exact rebuild differs",
                }
            )

        dependencies, unresolved = _dependency_resolution(
            root, manifest, artifact, risk_evidence
        )
        if unresolved:
            findings.append(
                {
                    "code": "SUPPLY-SBOM-UNRESOLVED",
                    "message": f"{artifact_id} has {unresolved} unresolved dependency inputs",
                }
            )
        required_toolchains = cast(list[str], artifact["toolchain_refs"])
        unavailable_toolchains = [
            item
            for item in required_toolchains
            if toolchain_by_id[(artifact_id, item)]["status"] != "passed"
        ]
        if unavailable_toolchains:
            findings.append(
                {
                    "code": "SUPPLY-TOOLCHAIN-UNAVAILABLE",
                    "message": f"{artifact_id} lacks toolchains: {', '.join(unavailable_toolchains)}",
                }
            )

        spdx = _spdx_document(artifact, first_members, subject_digest, dependencies)
        provenance = _provenance_statement(
            artifact,
            first_members,
            source,
            manifest_fingerprint,
            toolchains,
            dependencies,
        )
        spdx_sha256 = hashlib.sha256(canonical_json(spdx)).hexdigest()
        provenance_sha256 = hashlib.sha256(canonical_json(provenance)).hexdigest()
        checksum_lines = [f"# surface-sha256 {subject_digest}"]
        checksum_lines.extend(
            f"{member['sha256']}  {member['name']}" for member in first_members
        )
        checksum_text = "\n".join(checksum_lines) + "\n"
        companion_documents.extend(
            [
                (Path("checksums") / f"{surface}.sha256", checksum_text),
                (Path("sbom") / f"{surface}.spdx.json", spdx),
                (Path("provenance") / f"{surface}.intoto.json", provenance),
            ]
        )
        artifact_status = "passed"
        if reproducibility_status == "failed":
            artifact_status = "failed"
        elif unresolved or unavailable_toolchains:
            artifact_status = "incomplete"
        policy = cast(dict[str, Any], artifact["artifact_policy"])
        credential = cast(dict[str, Any], artifact["credential_policy"])
        rows.append(
            {
                "id": artifact_id,
                "status": artifact_status,
                "subject": {
                    "name": subject_name,
                    "kind": policy["subject_kind"],
                    "sha256": subject_digest,
                    "bytes": subject_bytes,
                },
                "checksum": {"algorithm": "sha256", "digest": subject_digest},
                "sbom": {
                    "spdx_version": "SPDX-2.3",
                    "document_namespace": spdx["documentNamespace"],
                    "sha256": spdx_sha256,
                    "component_count": len(cast(list[object], spdx["packages"])),
                    "relationship_count": len(
                        cast(list[object], spdx["relationships"])
                    ),
                    "unresolved_components": unresolved,
                },
                "provenance": {
                    "statement_type": "https://in-toto.io/Statement/v1",
                    "predicate_type": "https://slsa.dev/provenance/v1",
                    "subject_name": subject_name,
                    "subject_sha256": subject_digest,
                    "source_commit": source["commit"],
                    "builder_id": "https://strling.dev/builders/release-supply-chain/v1",
                    "build_command_sha256": hashlib.sha256(
                        canonical_json(artifact["build_command"])
                    ).hexdigest(),
                    "predicate_sha256": provenance_sha256,
                },
                "reproducibility": {
                    "mode": mode,
                    "status": reproducibility_status,
                    "first_sha256": subject_digest,
                    "second_sha256": second_digest,
                    "normalized_sha256": normalized_sha256,
                    "normalized_fields": normalized_fields,
                },
                "credential": {
                    "mode": credential["mode"],
                    "secret_names": credential["secret_names"],
                    "oidc_issuer": "https://token.actions.githubusercontent.com"
                    if credential["mode"] == "oidc"
                    else None,
                    "environment": "release",
                    "untrusted_context_forbidden": True,
                },
                "findings": findings,
            }
        )

    artifact_statuses = [cast(str, row["status"]) for row in rows]
    overall_status = _aggregate_status(
        [*artifact_statuses, *[cast(str, row["status"]) for row in toolchains]]
    )
    evidence: dict[str, Any] = {
        "schema_version": "1.0.0",
        "document_kind": "release-supply-chain-evidence",
        "operation_id": "certification.release-supply-chain",
        "profile": profile,
        "status": overall_status,
        "evidence_authority": evidence_authority,
        "publication_authorized": False,
        "manifest_fingerprint": manifest_fingerprint,
        "source": dict(source),
        "rebuild_source": authenticated_rebuild,
        "workflow": dict(workflow),
        "toolchains": [dict(row) for row in toolchains],
        "artifacts": rows,
        "summary": {
            status: artifact_statuses.count(status) for status in STATUS_PRECEDENCE
        },
        "evidence_fingerprint": "0" * 64,
    }
    evidence["summary"]["total"] = len(rows)
    evidence["evidence_fingerprint"] = document_fingerprint(
        evidence, "evidence_fingerprint"
    )
    validate_evidence(evidence, manifest, root=root)

    output_dir.mkdir(parents=True)
    for relative, document in companion_documents:
        path = output_dir / relative
        if isinstance(document, str):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(document, encoding="utf-8", newline="\n")
        else:
            _write_json(path, document)
    _write_json(output_dir / "release-supply-chain-evidence.json", evidence)
    return evidence


def verify_bundle(
    *,
    root: Path,
    evidence_path: Path,
    manifest: Mapping[str, object],
    verify_subjects: bool = True,
) -> dict[str, Any]:
    evidence = validate_evidence(load_json(evidence_path), manifest, root=root)
    bundle_root = evidence_path.parent
    contracts = {row["id"]: row for row in _artifact_rows(manifest)}
    for row in cast(list[dict[str, Any]], evidence["artifacts"]):
        if row["status"] != "passed":
            continue
        surface = cast(str, contracts[row["id"]]["surface"])
        checksum_path = bundle_root / "checksums" / f"{surface}.sha256"
        sbom_path = bundle_root / "sbom" / f"{surface}.spdx.json"
        provenance_path = bundle_root / "provenance" / f"{surface}.intoto.json"
        try:
            checksum = checksum_path.read_text(encoding="utf-8")
            sbom = load_json(sbom_path)
            provenance = load_json(provenance_path)
        except OSError as error:
            raise ReleaseSupplyChainError(
                "bundle-document", f"cannot read {surface} companion evidence: {error}"
            ) from error
        expected_header = f"# surface-sha256 {row['subject']['sha256']}\n"
        if not checksum.startswith(expected_header):
            raise ReleaseSupplyChainError(
                "checksum-document", f"{surface} checksum header changed"
            )
        members: list[dict[str, object]] = []
        checksum_subjects: list[dict[str, object]] = []
        for line in checksum.splitlines()[1:]:
            matched = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if matched is None:
                raise ReleaseSupplyChainError(
                    "checksum-document", f"{surface} checksum entry is malformed"
                )
            expected_digest, relative = matched.groups()
            if verify_subjects:
                policy = cast(dict[str, Any], contracts[row["id"]]["artifact_policy"])
                member = _member_from_path(
                    root,
                    relative,
                    source_tree=policy["subject_kind"] == "source-tree",
                )
                if member["sha256"] != expected_digest:
                    raise ReleaseSupplyChainError(
                        "checksum-document",
                        f"{surface} artifact bytes changed: {relative}",
                    )
                members.append(member)
            checksum_subjects.append(
                {"name": relative, "digest": {"sha256": expected_digest}}
            )
        if not checksum_subjects:
            raise ReleaseSupplyChainError(
                "checksum-document", f"{surface} checksum document is empty"
            )
        if verify_subjects:
            observed_name, observed_digest, observed_bytes = _surface_identity(members)
            if (
                observed_name != row["subject"]["name"]
                or observed_digest != row["subject"]["sha256"]
                or observed_bytes != row["subject"]["bytes"]
            ):
                raise ReleaseSupplyChainError(
                    "checksum-document", f"{surface} aggregate subject changed"
                )
        if hashlib.sha256(canonical_json(sbom)).hexdigest() != row["sbom"]["sha256"]:
            raise ReleaseSupplyChainError(
                "sbom-document", f"{surface} SPDX document changed"
            )
        packages = sbom.get("packages")
        if not isinstance(packages, list) or not packages:
            raise ReleaseSupplyChainError(
                "sbom-document", f"{surface} SPDX package is absent"
            )
        package_checksums = packages[0].get("checksums")
        if package_checksums != [
            {"algorithm": "SHA256", "checksumValue": row["subject"]["sha256"]}
        ]:
            raise ReleaseSupplyChainError(
                "sbom-document", f"{surface} SPDX subject changed"
            )
        if (
            hashlib.sha256(canonical_json(provenance)).hexdigest()
            != row["provenance"]["predicate_sha256"]
        ):
            raise ReleaseSupplyChainError(
                "provenance-document", f"{surface} provenance statement changed"
            )
        if (
            provenance.get("_type") != "https://in-toto.io/Statement/v1"
            or provenance.get("predicateType") != "https://slsa.dev/provenance/v1"
        ):
            raise ReleaseSupplyChainError(
                "provenance-document", f"{surface} provenance type changed"
            )
        if provenance.get("subject") != checksum_subjects:
            raise ReleaseSupplyChainError(
                "provenance-document", f"{surface} provenance subjects changed"
            )
    return evidence


def run_profile_certification(
    *, profile: str, evidence_path: Path | None, root: Path = ROOT
) -> dict[str, Any]:
    if evidence_path is None:
        contract = run_contract_check()
        status = cast(str, contract["status"])
        fingerprint = cast(str, contract["manifest_fingerprint"])
        evidence_authority = "contract"
    else:
        manifest = load_json(root / MANIFEST_PATH.relative_to(ROOT))
        evidence = verify_bundle(
            root=root,
            evidence_path=evidence_path,
            manifest=manifest,
            verify_subjects=False,
        )
        if evidence["profile"] != profile:
            raise ReleaseSupplyChainError(
                "profile", f"{profile} evidence profile changed"
            )
        status = cast(str, evidence["status"])
        fingerprint = cast(str, evidence["evidence_fingerprint"])
        evidence_authority = "live-dry-run"
    return {
        "schema_version": "certification-result-v1",
        "operation_id": "certification.release-supply-chain-profile",
        "profile": profile,
        "status": status,
        "publication_authorized": False,
        "evidence_authority": evidence_authority,
        "evidence_fingerprint": fingerprint,
    }


def run_governed_security_evidence(*, root: Path, risk_output: Path) -> dict[str, Any]:
    from tooling import security

    try:
        policy = security.load_policy(
            root / SECURITY_POLICY_PATH.relative_to(ROOT),
            root / "governance/schemas/security-policy.schema.json",
        )
        engine = security.SecurityEngine(root, policy)
        operations = {
            "integrity": engine.run_integrity(),
            "content": engine.run_content(),
            "risk": engine.run_risk(),
        }
    except security.SecurityConfigurationError as error:
        raise ReleaseSupplyChainError("security-evidence", str(error)) from error
    documents = {name: operation.as_dict() for name, operation in operations.items()}
    _write_json(risk_output, documents["risk"])
    statuses = {name: operation.status for name, operation in operations.items()}
    blocking = {
        name: status
        for name, status in statuses.items()
        if status in security.BLOCKING_STATUSES
    }
    return {
        "schema_version": "certification-result-v1",
        "operation_id": "certification.release-supply-chain-security-evidence",
        "profile": "release",
        "status": "failed" if blocking else "passed",
        "publication_authorized": False,
        "security_statuses": statuses,
        "risk_evidence": risk_output.as_posix(),
        "risk_evidence_sha256": hashlib.sha256(risk_output.read_bytes()).hexdigest(),
    }


def run_live_producer(
    *,
    root: Path = ROOT,
    profile: str,
    version: str,
    second_root: Path,
    output_dir: Path,
    risk_evidence_path: Path,
    build_receipt_dir: Path | None = None,
) -> dict[str, Any]:
    manifest_path = root / MANIFEST_PATH.relative_to(ROOT)
    manifest = validate_manifest(load_json(manifest_path), root=root)
    if build_receipt_dir is None:
        toolchains = probe_toolchains(root, manifest)
        source = authenticate_source(root)
        rebuild_source = authenticate_source(second_root)
    else:
        toolchains, source, rebuild_source = load_build_receipts(
            receipt_dir=build_receipt_dir,
            root=root,
            second_root=second_root,
            manifest=manifest,
            version=version,
        )
    return produce_bundle(
        root=root,
        second_root=second_root,
        output_dir=output_dir,
        version=version,
        profile=profile,
        manifest=manifest,
        source=source,
        workflow=qualify_workflow(root, manifest),
        toolchains=toolchains,
        evidence_authority="live-dry-run",
        risk_evidence=load_json(risk_evidence_path),
        rebuild_source=rebuild_source,
    )


def run_contract_check() -> dict[str, Any]:
    manifest = validate_manifest(load_json(MANIFEST_PATH))
    fixture = validate_contract_fixture(load_json(VALID_FIXTURE_PATH), manifest)
    validate_evidence(synthetic_evidence(manifest), manifest)
    return {
        "schema_version": "certification-result-v1",
        "operation_id": "certification.release-supply-chain-contract",
        "profile": "contract",
        "status": "passed",
        "publication_authorized": False,
        "manifest_fingerprint": document_fingerprint(manifest),
        "fixture_fingerprint": fixture["evidence_fingerprint"],
        "artifact_count": len(ARTIFACT_IDS),
        "standards": manifest["standards"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Produce and validate STRling release supply-chain evidence."
    )
    parser.add_argument(
        "command",
        choices=[
            "capture",
            "check",
            "produce",
            "profile",
            "security",
            "stage",
            "verify",
        ],
    )
    parser.add_argument(
        "--profile", choices=["local", "pull-request", "full", "release"]
    )
    parser.add_argument("--version")
    parser.add_argument("--second-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--risk-evidence", type=Path)
    parser.add_argument("--artifact-id")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--build-receipt-dir", type=Path)
    parser.add_argument("--download-root", type=Path)
    parser.add_argument("--first-root", type=Path)
    parser.add_argument("--release-ref")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "capture":
            if not all((args.artifact_id, args.version, args.output_dir)):
                raise ReleaseSupplyChainError(
                    "arguments",
                    "capture requires --artifact-id, --version, and --output-dir",
                )
            source_root = (args.source_root or ROOT).resolve()
            receipt = capture_build_receipt(
                root=source_root,
                artifact_id=args.artifact_id,
                version=args.version,
                output_path=args.output_dir.resolve(),
                manifest=load_json(source_root / MANIFEST_PATH.relative_to(ROOT)),
            )
            result = {
                "schema_version": "certification-result-v1",
                "operation_id": "certification.release-build-capture",
                "profile": "full",
                "status": (
                    "passed"
                    if all(row["status"] == "passed" for row in receipt["toolchains"])
                    else "incomplete"
                ),
                "publication_authorized": False,
                "receipt_fingerprint": receipt["receipt_fingerprint"],
            }
        elif args.command == "check":
            result = run_contract_check()
        elif args.command == "profile":
            if args.profile is None:
                raise ReleaseSupplyChainError("arguments", "profile requires --profile")
            environment_evidence = os.environ.get(
                "STRLING_RELEASE_SUPPLY_CHAIN_EVIDENCE"
            )
            evidence_path = args.evidence or (
                Path(environment_evidence) if environment_evidence else None
            )
            result = run_profile_certification(
                profile=args.profile,
                evidence_path=(evidence_path.resolve() if evidence_path else None),
                root=(args.source_root or ROOT).resolve(),
            )
        elif args.command == "security":
            if args.risk_evidence is None:
                raise ReleaseSupplyChainError(
                    "arguments", "security requires --risk-evidence"
                )
            result = run_governed_security_evidence(
                root=(args.source_root or ROOT).resolve(),
                risk_output=args.risk_evidence.resolve(),
            )
        elif args.command == "stage":
            if not all(
                (
                    args.download_root,
                    args.build_receipt_dir,
                    args.first_root,
                    args.second_root,
                    args.release_ref,
                )
            ):
                raise ReleaseSupplyChainError(
                    "arguments",
                    "stage requires --download-root, --build-receipt-dir, --first-root, --second-root, and --release-ref",
                )
            source_root = (args.source_root or ROOT).resolve()
            result = stage_downloaded_artifacts(
                download_root=args.download_root.resolve(),
                receipt_dir=args.build_receipt_dir.resolve(),
                first_root=args.first_root.resolve(),
                second_root=args.second_root.resolve(),
                release_ref=args.release_ref,
                manifest=load_json(source_root / MANIFEST_PATH.relative_to(ROOT)),
            )
        elif args.command == "produce":
            if not all(
                (
                    args.profile,
                    args.version,
                    args.second_root,
                    args.output_dir,
                    args.risk_evidence,
                )
            ):
                raise ReleaseSupplyChainError(
                    "arguments",
                    "produce requires --profile, --version, --second-root, --output-dir, and --risk-evidence",
                )
            evidence = run_live_producer(
                root=(args.source_root or ROOT).resolve(),
                profile=args.profile,
                version=args.version,
                second_root=args.second_root.resolve(),
                output_dir=args.output_dir.resolve(),
                risk_evidence_path=args.risk_evidence.resolve(),
                build_receipt_dir=(
                    args.build_receipt_dir.resolve()
                    if args.build_receipt_dir is not None
                    else None
                ),
            )
            result = {
                "schema_version": "certification-result-v1",
                "operation_id": "certification.release-supply-chain",
                "profile": args.profile,
                "status": evidence["status"],
                "publication_authorized": False,
                "evidence_fingerprint": evidence["evidence_fingerprint"],
                "summary": evidence["summary"],
            }
        else:
            if args.evidence is None:
                raise ReleaseSupplyChainError("arguments", "verify requires --evidence")
            evidence = verify_bundle(
                root=(args.source_root or ROOT).resolve(),
                evidence_path=args.evidence.resolve(),
                manifest=load_json(MANIFEST_PATH),
            )
            result = {
                "schema_version": "certification-result-v1",
                "operation_id": "certification.release-supply-chain",
                "profile": evidence["profile"],
                "status": evidence["status"],
                "publication_authorized": False,
                "evidence_fingerprint": evidence["evidence_fingerprint"],
                "summary": evidence["summary"],
            }
    except ReleaseSupplyChainError as error:
        operation_id = (
            "certification.release-supply-chain-profile"
            if args.command == "profile"
            else "certification.release-supply-chain"
        )
        result = {
            "schema_version": "certification-result-v1",
            "operation_id": operation_id,
            "profile": getattr(args, "profile", None) or "contract",
            "status": "failed",
            "publication_authorized": False,
            "error": {"code": error.code, "message": str(error)},
        }
        if args.json:
            print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        else:
            print(f"release supply-chain contract failed: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"release supply-chain {args.command}: {result['status']}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
