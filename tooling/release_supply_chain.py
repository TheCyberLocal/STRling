"""Validate governed STRling release supply-chain certification evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

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


class ReleaseSupplyChainError(RuntimeError):
    """A stable fail-closed release supply-chain validation error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def load_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseSupplyChainError(
            "malformed-json", f"cannot load {path.relative_to(ROOT)}: {error}"
        ) from error
    if not isinstance(loaded, dict):
        raise ReleaseSupplyChainError(
            "malformed-json", f"{path.relative_to(ROOT)} must contain an object"
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
    evidence: Mapping[str, object], manifest: Mapping[str, object]
) -> dict[str, Any]:
    validate_schema(evidence, label="release supply-chain evidence")
    validate_manifest(manifest)
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

    artifacts = cast(list[dict[str, Any]], evidence["artifacts"])
    if _exact_ids(artifacts, label="release evidence") != ARTIFACT_IDS:
        raise ReleaseSupplyChainError(
            "artifact-denominator", "evidence does not cover all 17 release surfaces"
        )
    contracts = {item["id"]: item for item in _artifact_rows(manifest)}
    source = cast(dict[str, Any], evidence["source"])
    aggregate_statuses: list[str] = []
    artifact_statuses: list[str] = []
    toolchains = cast(list[dict[str, Any]], evidence["toolchains"])
    if _exact_ids(toolchains, label="toolchain evidence") != _toolchain_ids(manifest):
        raise ReleaseSupplyChainError(
            "toolchain-denominator", "evidence toolchain denominator changed"
        )
    toolchain_policy_sha256 = document_fingerprint(
        load_json(ROOT / cast(str, manifest["toolchain_authority"]))
    )
    for toolchain in toolchains:
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
            if reproducibility["normalized_sha256"] is None:
                raise ReleaseSupplyChainError(
                    "reproducibility", f"{artifact_id} lacks normalized identity"
                )
        elif (
            reproducibility["first_sha256"] != subject["sha256"]
            or reproducibility["second_sha256"] != subject["sha256"]
            or reproducibility["normalized_sha256"] is not None
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
    for toolchain_id in _toolchain_ids(manifest):
        toolchains.append(
            {
                "id": toolchain_id,
                "status": "passed",
                "version": "fixture",
                "executable": f"fixture/{toolchain_id}",
                "executable_sha256": hashlib.sha256(
                    f"{toolchain_id}:executable".encode()
                ).hexdigest(),
                "policy_sha256": toolchain_policy_sha256,
                "findings": [],
            }
        )
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
        description="Validate STRling release supply-chain contracts."
    )
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_contract_check()
    except ReleaseSupplyChainError as error:
        result = {
            "schema_version": "certification-result-v1",
            "operation_id": "certification.release-supply-chain-contract",
            "profile": "contract",
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
        print("release supply-chain contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
