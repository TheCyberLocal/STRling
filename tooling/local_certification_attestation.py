#!/usr/bin/env python3
"""Create and verify trusted attestations for authoritative local certification."""

from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

try:
    from .certification import (
        operation_registry_fingerprint,
        profile_definition_fingerprint,
        profile_registry_fingerprint,
        validate_certification_artifact,
    )
except ImportError:  # pragma: no cover - direct script execution
    from certification import (  # type: ignore[no-redef]
        operation_registry_fingerprint,
        profile_definition_fingerprint,
        profile_registry_fingerprint,
        validate_certification_artifact,
    )


ATTESTATION_KIND = "strling-local-certification-attestation"
ATTESTATION_VERSION = "1.0.0"
TRUST_KIND = "strling-local-certification-trust"
TRUST_VERSION = "1.0.0"
CONTRACT_OPERATION = "certification.local-attestation-contract"
VERIFY_OPERATION = "certification.local-attestation-verification"
SUCCESS_STATUSES = {"passed", "waived"}
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ROLE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


class AttestationError(ValueError):
    """Raised when certification evidence is incomplete or untrusted."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def object_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AttestationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AttestationError(f"JSON document must be an object: {path}")
    return value


def _validate_schema(document: Mapping[str, object], schema_path: Path) -> None:
    schema = _load_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(document)
    except (SchemaError, ValidationError) as exc:
        raise AttestationError(
            f"schema validation failed for {schema_path}: {exc}"
        ) from exc


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise AttestationError(
            f"git {' '.join(arguments)} failed: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed.stdout.strip()


def _git_bytes(root: Path, source_sha: str, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{source_sha}:{relative}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise AttestationError(
            f"cannot read {relative} at {source_sha}: "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def _git_json(root: Path, source_sha: str, relative: str) -> dict[str, Any]:
    try:
        value = json.loads(_git_bytes(root, source_sha, relative))
    except json.JSONDecodeError as exc:
        raise AttestationError(
            f"invalid JSON at {source_sha}:{relative}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise AttestationError(f"expected object at {source_sha}:{relative}")
    return value


def _public_key_fingerprint(public_key: str) -> str:
    parts = public_key.strip().split()
    if len(parts) < 2 or parts[0] != "ssh-ed25519":
        raise AttestationError("authorized certifier key must be ssh-ed25519")
    try:
        wire_key = base64.b64decode(parts[1], validate=True)
    except ValueError as exc:
        raise AttestationError("authorized certifier public key is malformed") from exc
    encoded = base64.b64encode(hashlib.sha256(wire_key).digest()).decode("ascii")
    return f"SHA256:{encoded.rstrip('=')}"


def load_trust_policy(trust_root: Path) -> dict[str, Any]:
    path = trust_root / "governance/local-certification-trust.json"
    trust = _load_json(path)
    _validate_schema(
        trust,
        trust_root / "governance/schemas/local-certification-trust.schema.json",
    )
    if (
        trust.get("schema_version") != TRUST_VERSION
        or trust.get("policy_kind") != TRUST_KIND
    ):
        raise AttestationError("unsupported local certification trust policy")
    certifiers = trust["authorized_certifiers"]
    identities = [item["certifier_id"] for item in certifiers]
    fingerprints = [item["ssh_key_fingerprint"] for item in certifiers]
    if len(identities) != len(set(identities)):
        raise AttestationError("duplicate authorized certifier identity")
    if len(fingerprints) != len(set(fingerprints)):
        raise AttestationError("duplicate authorized certifier key fingerprint")
    for certifier in certifiers:
        actual = _public_key_fingerprint(certifier["public_key"])
        if actual != certifier["ssh_key_fingerprint"]:
            raise AttestationError(
                f"authorized certifier {certifier['certifier_id']} key fingerprint mismatch"
            )
    return trust


def validate_contract(repository_root: Path, trust_root: Path) -> dict[str, Any]:
    trust = load_trust_policy(trust_root)
    toolchain = _load_json(repository_root / "toolchain.json")
    profiles = toolchain.get("policy", {}).get("profiles")
    if not isinstance(profiles, dict):
        raise AttestationError("toolchain profile registry is missing")
    for profile in trust["required_profiles"]:
        if profile not in profiles:
            raise AttestationError(
                f"required certification profile is missing: {profile}"
            )
    bundle = PurePosixPath(trust["bundle_path"])
    if bundle.is_absolute() or ".." in bundle.parts:
        raise AttestationError("certification bundle path must be repository-relative")
    for pattern in trust["closure_paths"]:
        candidate = PurePosixPath(pattern)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise AttestationError(f"unsafe closure path pattern: {pattern}")
    return trust


def _result(
    operation_id: str, status: str, checks: list[dict[str, object]]
) -> dict[str, object]:
    summary = {
        name: 0 for name in ("passed", "failed", "waived", "unavailable", "incomplete")
    }
    summary[status] = 1
    return {
        "schema_version": "1.0.0",
        "operation_id": operation_id,
        "status": status,
        "checks": checks,
        "summary": summary,
    }


def contract_result(repository_root: Path, trust_root: Path) -> dict[str, object]:
    try:
        trust = validate_contract(repository_root, trust_root)
    except AttestationError as exc:
        return _result(
            CONTRACT_OPERATION,
            "failed",
            [
                {
                    "check_id": f"{CONTRACT_OPERATION}.trust-policy",
                    "status": "failed",
                    "findings": [
                        {
                            "code": "CERT-LOCAL-ATTESTATION-0001",
                            "message": str(exc),
                        }
                    ],
                }
            ],
        )
    return _result(
        CONTRACT_OPERATION,
        "passed",
        [
            {
                "check_id": f"{CONTRACT_OPERATION}.trust-policy",
                "status": "passed",
                "evidence": {
                    "required_profiles": trust["required_profiles"],
                    "certifier_ids": [
                        item["certifier_id"] for item in trust["authorized_certifiers"]
                    ],
                    "bundle_path": trust["bundle_path"],
                },
            }
        ],
    )


def _nested_status_consistency(artifact: Mapping[str, Any]) -> None:
    operations = artifact["deterministic_evidence"]["operations"]
    for operation in operations:
        structured = operation.get("structured_evidence")
        if not isinstance(structured, dict):
            continue
        nested = structured.get("status")
        if nested is not None and nested != operation["status"]:
            raise AttestationError(
                f"{operation['result_id']} outer status contradicts producer status"
            )


def _profile_claim(
    repository_root: Path,
    artifact_path: Path,
    expected_profile: str,
    source_sha: str,
    source_profiles: Mapping[str, object],
    evidence_path: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifact = _load_json(artifact_path)
    try:
        validate_certification_artifact(repository_root, artifact)
    except Exception as exc:
        raise AttestationError(
            f"invalid {expected_profile} profile artifact: {exc}"
        ) from exc
    _nested_status_consistency(artifact)
    deterministic = artifact["deterministic_evidence"]
    repository = deterministic["repository"]
    profile = deterministic["profile"]
    aggregate = deterministic["aggregate"]
    if repository != {"commit": source_sha, "dirty": False}:
        raise AttestationError(
            f"{expected_profile} profile is not bound to clean source {source_sha}"
        )
    if profile["id"] != expected_profile:
        raise AttestationError(f"expected {expected_profile} profile artifact")
    if aggregate["status"] not in SUCCESS_STATUSES or aggregate["exit_code"] != 0:
        raise AttestationError(
            f"{expected_profile} profile is not terminally successful"
        )
    definition = source_profiles.get(expected_profile)
    if not isinstance(definition, dict):
        raise AttestationError(
            f"source profile definition is missing: {expected_profile}"
        )
    if profile["definition_version"] != definition.get("definition_version"):
        raise AttestationError(f"{expected_profile} profile version mismatch")
    if profile["definition_fingerprint"] != profile_definition_fingerprint(definition):
        raise AttestationError(f"{expected_profile} profile fingerprint mismatch")
    claim = {
        "profile": expected_profile,
        "definition_version": profile["definition_version"],
        "definition_fingerprint": profile["definition_fingerprint"],
        "evidence_fingerprint": artifact["evidence_fingerprint"],
        "status": aggregate["status"],
        "exit_code": aggregate["exit_code"],
        "operation_count": aggregate["operation_count"],
        "counts": aggregate["counts"],
        "evidence_path": evidence_path,
    }
    return claim, artifact


def _walk(value: object) -> Iterable[tuple[str, object]]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key, nested
            yield from _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested)


def _waivers(artifacts: Iterable[Mapping[str, Any]]) -> list[str]:
    values: set[str] = set()
    for artifact in artifacts:
        for key, value in _walk(artifact):
            if key == "waiver_id" and isinstance(value, str):
                values.add(value)
            elif key == "waiver_references" and isinstance(value, list):
                values.update(item for item in value if isinstance(item, str))
    return sorted(values)


def _producer_invocations(artifacts: Iterable[Mapping[str, Any]]) -> list[str]:
    values: set[str] = set()
    for artifact in artifacts:
        operations = artifact["deterministic_evidence"]["operations"]
        for operation in operations:
            integrity = operation.get("execution_integrity")
            if isinstance(integrity, dict):
                identity = integrity.get("invocation_id")
                if isinstance(identity, str):
                    values.add(identity)
    return sorted(values)


def _sample_counts(artifacts: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for artifact in artifacts:
        profile = artifact["deterministic_evidence"]["profile"]["id"]
        operations = artifact["deterministic_evidence"]["operations"]
        for operation in operations:
            integrity = operation.get("execution_integrity")
            if not isinstance(integrity, dict):
                continue
            consumption = integrity.get("sample_consumption")
            if not isinstance(consumption, dict):
                continue
            count = consumption.get("authenticated_sample_count")
            if isinstance(count, int):
                counts[f"{profile}:{operation['operation_id']}"] = count
    return dict(sorted(counts.items()))


def _require_authenticated_samples(counts: Mapping[str, int]) -> None:
    for profile in ("full", "release"):
        key = f"{profile}:performance_resource_full_certification"
        if counts.get(key, 0) <= 0:
            raise AttestationError(
                f"{profile} evidence has no authenticated governed performance samples"
            )


def _real_engine_claim(
    artifacts: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    counts: dict[str, int] | None = None
    runtime_identities: dict[str, Any] | None = None
    run_ids: set[str] = set()
    for artifact in artifacts:
        operations = artifact["deterministic_evidence"]["operations"]
        operation = next(
            (
                item
                for item in operations
                if item["operation_id"] == "adversarial_real_engine_equivalence"
            ),
            None,
        )
        if operation is None:
            raise AttestationError(
                "profile is missing real-engine equivalence evidence"
            )
        structured = operation.get("structured_evidence")
        if not isinstance(structured, dict) or structured.get("status") != "passed":
            raise AttestationError("real-engine equivalence producer did not pass")
        checks = structured.get("checks")
        if not isinstance(checks, list) or len(checks) != 1:
            raise AttestationError("real-engine equivalence evidence is malformed")
        evidence = checks[0].get("evidence")
        if not isinstance(evidence, dict):
            raise AttestationError("real-engine equivalence evidence is missing")
        observed = evidence.get("counts")
        identities = evidence.get("runtime_identities")
        findings = evidence.get("findings")
        run_id = evidence.get("run_id")
        if not isinstance(observed, dict) or not isinstance(identities, dict):
            raise AttestationError(
                "real-engine counts or runtime identities are missing"
            )
        if findings != [] or evidence.get("unaccounted_observations") != 0:
            raise AttestationError(
                "real-engine evidence contains findings or unaccounted observations"
            )
        if not isinstance(run_id, str) or not SHA256.fullmatch(run_id):
            raise AttestationError("real-engine run identity is malformed")
        normalized = {key: int(value) for key, value in observed.items()}
        if counts is not None and normalized != counts:
            raise AttestationError("Full and Release real-engine counts disagree")
        if runtime_identities is not None and identities != runtime_identities:
            raise AttestationError("Full and Release runtime identities disagree")
        counts = normalized
        runtime_identities = identities
        run_ids.add(run_id)
    assert counts is not None and runtime_identities is not None
    required = {
        "semantic_cases",
        "subjects",
        "target_profile_compiles",
        "runtime_executions",
        "governed_refusals",
        "cross_profile_comparisons",
    }
    if not required.issubset(counts):
        raise AttestationError("real-engine evidence omits required counts")
    claim = {key: counts[key] for key in sorted(required)}
    claim["findings"] = 0
    claim["run_ids"] = sorted(run_ids)
    return claim, runtime_identities


def _target_profile_claims(
    repository_root: Path, source_sha: str
) -> list[dict[str, str]]:
    paths = _git(
        repository_root,
        "ls-tree",
        "-r",
        "--name-only",
        source_sha,
        "spec/targets/profiles",
    ).splitlines()
    claims: list[dict[str, str]] = []
    for relative in sorted(path for path in paths if path.endswith(".json")):
        profile = _git_json(repository_root, source_sha, relative)
        claims.append(
            {
                "profile_id": str(profile["profile_id"]),
                "profile_version": str(profile["profile_version"]),
                "fingerprint": object_sha256(profile),
            }
        )
    if not claims:
        raise AttestationError("source contains no governed target profiles")
    return claims


def _command_version(command: Sequence[str]) -> str:
    completed = subprocess.run(
        list(command),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return (completed.stdout or completed.stderr).strip().splitlines()[0]


def _runner_identity() -> dict[str, str]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "git": _command_version(["git", "--version"]),
        "ssh": _command_version(["ssh", "-V"]),
    }


def _copy_evidence(
    output_dir: Path,
    sources: Sequence[tuple[str, Path]],
) -> list[dict[str, object]]:
    evidence_root = output_dir / "evidence"
    evidence_root.mkdir(parents=True)
    destinations: set[str] = set()
    entries: list[dict[str, object]] = []
    for role, source in sources:
        if not ROLE.fullmatch(role):
            raise AttestationError(f"invalid evidence role: {role}")
        if not source.exists():
            raise AttestationError(f"evidence source does not exist: {source}")
        files = (
            [source]
            if source.is_file()
            else sorted(path for path in source.rglob("*") if path.is_file())
        )
        if not files:
            raise AttestationError(f"evidence source is empty: {source}")
        for path in files:
            suffix = Path(path.name) if source.is_file() else path.relative_to(source)
            relative = (
                PurePosixPath("evidence") / role / PurePosixPath(suffix.as_posix())
            ).as_posix()
            if relative in destinations:
                raise AttestationError(f"duplicate evidence destination: {relative}")
            destinations.add(relative)
            destination = output_dir / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            size = destination.stat().st_size
            if size == 0:
                raise AttestationError(f"evidence file is empty: {relative}")
            entries.append(
                {
                    "path": relative,
                    "role": role,
                    "bytes": size,
                    "sha256": file_sha256(destination),
                }
            )
    return sorted(entries, key=lambda item: str(item["path"]))


def _certifier(trust: Mapping[str, Any], certifier_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in trust["authorized_certifiers"]
        if item["certifier_id"] == certifier_id and item["status"] == "active"
    ]
    if len(matches) != 1:
        raise AttestationError(f"certifier is not uniquely authorized: {certifier_id}")
    return matches[0]


def _private_key_matches(private_key: Path, certifier: Mapping[str, Any]) -> None:
    completed = subprocess.run(
        ["ssh-keygen", "-y", "-f", str(private_key)],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise AttestationError(
            f"cannot read certifier private key: {completed.stderr.strip()}"
        )
    expected = " ".join(str(certifier["public_key"]).split()[:2])
    actual = " ".join(completed.stdout.strip().split()[:2])
    if actual != expected:
        raise AttestationError("private key does not match the trusted certifier")


def _sign(payload: bytes, private_key: Path, namespace: str) -> bytes:
    completed = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(private_key), "-n", namespace],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode or not completed.stdout:
        raise AttestationError(
            "certification signature failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout


def _verify_signature(
    payload: bytes,
    signature: bytes,
    certifier: Mapping[str, Any],
    namespace: str,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        allowed = temporary / "allowed_signers"
        signature_path = temporary / "attestation.sig"
        allowed.write_text(
            f"{certifier['certifier_id']} {certifier['public_key']}\n",
            encoding="utf-8",
        )
        signature_path.write_bytes(signature)
        completed = subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "verify",
                "-f",
                str(allowed),
                "-I",
                str(certifier["certifier_id"]),
                "-n",
                namespace,
                "-s",
                str(signature_path),
            ],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if completed.returncode:
        reason = (
            (completed.stderr or completed.stdout)
            .decode("utf-8", errors="replace")
            .strip()
        )
        raise AttestationError(
            f"attestation signature is untrusted or malformed: {reason}"
        )


def _parse_evidence_argument(argument: str) -> tuple[str, Path]:
    if "=" not in argument:
        raise AttestationError("--evidence requires ROLE=PATH")
    role, value = argument.split("=", 1)
    return role, Path(value).resolve()


def create_attestation(
    *,
    repository_root: Path,
    trust_root: Path,
    output_dir: Path,
    full_artifact: Path,
    release_artifact: Path,
    extra_evidence: Sequence[tuple[str, Path]],
    private_key: Path,
    certifier_id: str,
    invocation_id: str,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    trust_root = trust_root.resolve()
    trust = validate_contract(repository_root, trust_root)
    if not re.fullmatch(r"[0-9a-f]{32}", invocation_id):
        raise AttestationError(
            "certification invocation ID must be 32 lowercase hex characters"
        )
    source_sha = _git(repository_root, "rev-parse", "HEAD")
    if not SHA1.fullmatch(source_sha):
        raise AttestationError("repository HEAD is not a full lowercase Git SHA")
    dirty = _git(repository_root, "status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise AttestationError(
            "authoritative local certification requires a clean worktree"
        )
    source_tree = _git(repository_root, "rev-parse", f"{source_sha}^{{tree}}")
    toolchain_bytes = _git_bytes(repository_root, source_sha, "toolchain.json")
    toolchain = json.loads(toolchain_bytes)
    profiles = toolchain["policy"]["profiles"]
    operations = toolchain["policy"]["operation_registry"]
    certifier = _certifier(trust, certifier_id)
    if sorted(certifier["authorized_profiles"]) != sorted(trust["required_profiles"]):
        raise AttestationError("certifier profile authorization is incomplete")
    _private_key_matches(private_key.resolve(), certifier)

    if output_dir.exists():
        raise AttestationError(
            f"attestation output directory already exists: {output_dir}"
        )
    output_dir.mkdir(parents=True)
    try:
        copied = _copy_evidence(
            output_dir,
            [
                ("profile-full", full_artifact.resolve()),
                ("profile-release", release_artifact.resolve()),
                *extra_evidence,
            ],
        )
        full_path = next(
            item["path"] for item in copied if item["role"] == "profile-full"
        )
        release_path = next(
            item["path"] for item in copied if item["role"] == "profile-release"
        )
        full_claim, full = _profile_claim(
            repository_root,
            output_dir / str(full_path),
            "full",
            source_sha,
            profiles,
            str(full_path),
        )
        release_claim, release = _profile_claim(
            repository_root,
            output_dir / str(release_path),
            "release",
            source_sha,
            profiles,
            str(release_path),
        )
        real_engine, runtimes = _real_engine_claim((full, release))
        sample_counts = _sample_counts((full, release))
        _require_authenticated_samples(sample_counts)
        payload: dict[str, Any] = {
            "certification_state": "LOCALLY_CERTIFIED",
            "certified_source": {
                "commit": source_sha,
                "tree": source_tree,
                "clean": True,
            },
            "certification_contract": {
                "toolchain_sha256": hashlib.sha256(toolchain_bytes).hexdigest(),
                "profile_registry_fingerprint": profile_registry_fingerprint(profiles),
                "operation_registry_fingerprint": operation_registry_fingerprint(
                    operations
                ),
                "trust_policy_sha256": object_sha256(trust),
            },
            "certification_invocation_id": invocation_id,
            "certifier": {
                "certifier_id": certifier_id,
                "ssh_key_fingerprint": certifier["ssh_key_fingerprint"],
            },
            "runner_identity": _runner_identity(),
            "component_identities": {
                "kernel_tree": _git(repository_root, "rev-parse", f"{source_sha}:core"),
                "interop_tree": _git(
                    repository_root, "rev-parse", f"{source_sha}:bindings/interop"
                ),
            },
            "target_profiles": _target_profile_claims(repository_root, source_sha),
            "runtime_identities": runtimes,
            "profile_results": [full_claim, release_claim],
            "producer_invocation_ids": _producer_invocations((full, release)),
            "waiver_inventory": _waivers((full, release)),
            "authenticated_sample_counts": sample_counts,
            "real_engine_evidence": real_engine,
            "evidence_files": copied,
        }
        payload["evidence_root_sha256"] = object_sha256(payload)
        signed = canonical_bytes(payload)
        signature = _sign(signed, private_key.resolve(), trust["signature_namespace"])
        attestation = {
            "schema_version": ATTESTATION_VERSION,
            "artifact_kind": ATTESTATION_KIND,
            "signed_payload": payload,
            "signature": {
                "scheme": "SSHSIG_ED25519",
                "namespace": trust["signature_namespace"],
                "certifier_id": certifier_id,
                "signature_base64": base64.b64encode(signature).decode("ascii"),
                "signature_sha256": hashlib.sha256(signature).hexdigest(),
                "signed_payload_sha256": hashlib.sha256(signed).hexdigest(),
            },
        }
        _validate_schema(
            attestation,
            trust_root
            / "governance/schemas/local-certification-attestation.schema.json",
        )
        (output_dir / "attestation.json").write_text(
            json.dumps(attestation, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        verify_attestation(
            repository_root=repository_root,
            trust_root=trust_root,
            bundle_dir=output_dir,
        )
        return attestation
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def _closure_paths(
    repository_root: Path, source_sha: str, trust: Mapping[str, Any]
) -> list[str]:
    head = _git(repository_root, "rev-parse", "HEAD")
    if head == source_sha:
        return []
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_sha, head],
        cwd=repository_root,
        check=False,
    )
    if completed.returncode:
        raise AttestationError(
            "certified source is not an ancestor of the verified source"
        )
    changed = _git(
        repository_root,
        "diff",
        "--name-only",
        "--diff-filter=ACDMRTUXB",
        f"{source_sha}..{head}",
    ).splitlines()
    allowed = trust["closure_paths"]
    rejected = [
        path
        for path in changed
        if not any(fnmatch.fnmatchcase(path, pattern) for pattern in allowed)
    ]
    if rejected:
        raise AttestationError(
            "source advanced beyond the certified commit outside closure paths: "
            + ", ".join(rejected)
        )
    return changed


def _verify_evidence_files(
    bundle_dir: Path, entries: Sequence[Mapping[str, Any]]
) -> None:
    declared = [str(item["path"]) for item in entries]
    if declared != sorted(declared) or len(declared) != len(set(declared)):
        raise AttestationError(
            "evidence file manifest is unordered or contains duplicates"
        )
    actual = sorted(
        path.relative_to(bundle_dir).as_posix()
        for path in (bundle_dir / "evidence").rglob("*")
        if path.is_file()
    )
    if actual != declared:
        missing = sorted(set(declared) - set(actual))
        extra = sorted(set(actual) - set(declared))
        raise AttestationError(
            f"evidence presence mismatch; missing={missing}, extra={extra}"
        )
    for entry in entries:
        path = bundle_dir / str(entry["path"])
        if path.stat().st_size != entry["bytes"]:
            raise AttestationError(f"evidence size mismatch: {entry['path']}")
        if file_sha256(path) != entry["sha256"]:
            raise AttestationError(f"evidence hash mismatch: {entry['path']}")


def verify_attestation(
    *, repository_root: Path, trust_root: Path, bundle_dir: Path
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    trust_root = trust_root.resolve()
    bundle_dir = bundle_dir.resolve()
    trust = validate_contract(repository_root, trust_root)
    attestation = _load_json(bundle_dir / "attestation.json")
    _validate_schema(
        attestation,
        trust_root / "governance/schemas/local-certification-attestation.schema.json",
    )
    payload = attestation["signed_payload"]
    signature_record = attestation["signature"]
    if signature_record["namespace"] != trust["signature_namespace"]:
        raise AttestationError("signature namespace does not match trust policy")
    if signature_record["certifier_id"] != payload["certifier"]["certifier_id"]:
        raise AttestationError("signature and payload certifier identities disagree")
    certifier = _certifier(trust, signature_record["certifier_id"])
    if payload["certifier"]["ssh_key_fingerprint"] != certifier["ssh_key_fingerprint"]:
        raise AttestationError("payload certifier fingerprint is not trusted")
    signed = canonical_bytes(payload)
    if hashlib.sha256(signed).hexdigest() != signature_record["signed_payload_sha256"]:
        raise AttestationError("signed payload digest mismatch")
    try:
        signature = base64.b64decode(
            signature_record["signature_base64"], validate=True
        )
    except ValueError as exc:
        raise AttestationError("attestation signature encoding is malformed") from exc
    if hashlib.sha256(signature).hexdigest() != signature_record["signature_sha256"]:
        raise AttestationError("signature digest mismatch")
    _verify_signature(signed, signature, certifier, trust["signature_namespace"])
    root_projection = dict(payload)
    root_digest = root_projection.pop("evidence_root_sha256")
    if root_digest != object_sha256(root_projection):
        raise AttestationError("root evidence digest mismatch")
    if payload["certification_state"] != "LOCALLY_CERTIFIED":
        raise AttestationError("terminal certification state is not LOCALLY_CERTIFIED")
    source_sha = payload["certified_source"]["commit"]
    if not SHA1.fullmatch(source_sha):
        raise AttestationError("certified source identity is malformed")
    if _git(repository_root, "rev-parse", f"{source_sha}^{{commit}}") != source_sha:
        raise AttestationError("certified source commit is unavailable")
    if (
        _git(repository_root, "rev-parse", f"{source_sha}^{{tree}}")
        != payload["certified_source"]["tree"]
    ):
        raise AttestationError("certified Git tree identity mismatch")
    if payload["certified_source"]["clean"] is not True:
        raise AttestationError("certified source does not assert a clean worktree")
    closure = _closure_paths(repository_root, source_sha, trust)
    _verify_evidence_files(bundle_dir, payload["evidence_files"])
    evidence_roles = {
        (str(item["role"]), str(item["path"])) for item in payload["evidence_files"]
    }

    toolchain_bytes = _git_bytes(repository_root, source_sha, "toolchain.json")
    toolchain = json.loads(toolchain_bytes)
    profiles = toolchain["policy"]["profiles"]
    operations = toolchain["policy"]["operation_registry"]
    contract = payload["certification_contract"]
    expected_contract = {
        "toolchain_sha256": hashlib.sha256(toolchain_bytes).hexdigest(),
        "profile_registry_fingerprint": profile_registry_fingerprint(profiles),
        "operation_registry_fingerprint": operation_registry_fingerprint(operations),
        "trust_policy_sha256": object_sha256(trust),
    }
    if contract != expected_contract:
        raise AttestationError("certification contract or profile fingerprint mismatch")
    if payload["component_identities"] != {
        "kernel_tree": _git(repository_root, "rev-parse", f"{source_sha}:core"),
        "interop_tree": _git(
            repository_root, "rev-parse", f"{source_sha}:bindings/interop"
        ),
    }:
        raise AttestationError("kernel or interop identity mismatch")
    if payload["target_profiles"] != _target_profile_claims(
        repository_root, source_sha
    ):
        raise AttestationError("target profile identity mismatch")

    results_by_profile = {item["profile"]: item for item in payload["profile_results"]}
    if sorted(results_by_profile) != sorted(trust["required_profiles"]):
        raise AttestationError("required Full/Release profile evidence is missing")
    artifacts: list[dict[str, Any]] = []
    reconstructed: list[dict[str, Any]] = []
    for profile in trust["required_profiles"]:
        claim = results_by_profile[profile]
        required_evidence = (f"profile-{profile}", claim["evidence_path"])
        if required_evidence not in evidence_roles:
            raise AttestationError(
                f"{profile} profile artifact is not declared with its required evidence role"
            )
        rebuilt, artifact = _profile_claim(
            repository_root,
            bundle_dir / claim["evidence_path"],
            profile,
            source_sha,
            profiles,
            claim["evidence_path"],
        )
        reconstructed.append(rebuilt)
        artifacts.append(artifact)
    if payload["profile_results"] != reconstructed:
        raise AttestationError("profile result aggregate contradicts producer evidence")
    waivers = _waivers(artifacts)
    if waivers != payload["waiver_inventory"]:
        raise AttestationError("waiver inventory contradicts producer evidence")
    unapproved = sorted(set(waivers) - set(trust["allowed_waivers"]))
    if unapproved:
        raise AttestationError(
            "unapproved waiver in certification evidence: " + ", ".join(unapproved)
        )
    if payload["producer_invocation_ids"] != _producer_invocations(artifacts):
        raise AttestationError("producer invocation identity mismatch")
    reconstructed_samples = _sample_counts(artifacts)
    _require_authenticated_samples(reconstructed_samples)
    if payload["authenticated_sample_counts"] != reconstructed_samples:
        raise AttestationError("authenticated performance sample count mismatch")
    real_engine, runtimes = _real_engine_claim(artifacts)
    if payload["real_engine_evidence"] != real_engine:
        raise AttestationError("real-engine evidence aggregate mismatch")
    if payload["runtime_identities"] != runtimes:
        raise AttestationError("governed runtime identity mismatch")
    return {
        "certification_state": "CLOUD_VERIFIED",
        "certified_source_sha": source_sha,
        "verified_head_sha": _git(repository_root, "rev-parse", "HEAD"),
        "closure_paths": closure,
        "evidence_root_sha256": root_digest,
        "attestation_sha256": file_sha256(bundle_dir / "attestation.json"),
        "signature_sha256": signature_record["signature_sha256"],
        "certifier_id": certifier["certifier_id"],
        "profile_results": reconstructed,
        "real_engine_evidence": real_engine,
        "authenticated_sample_counts": payload["authenticated_sample_counts"],
        "waiver_inventory": waivers,
    }


def verification_result(
    repository_root: Path, trust_root: Path, bundle_dir: Path
) -> dict[str, object]:
    try:
        evidence = verify_attestation(
            repository_root=repository_root,
            trust_root=trust_root,
            bundle_dir=bundle_dir,
        )
    except AttestationError as exc:
        return _result(
            VERIFY_OPERATION,
            "failed",
            [
                {
                    "check_id": f"{VERIFY_OPERATION}.integrity",
                    "status": "failed",
                    "findings": [
                        {
                            "code": "CERT-LOCAL-ATTESTATION-0002",
                            "message": str(exc),
                        }
                    ],
                }
            ],
        )
    return _result(
        VERIFY_OPERATION,
        "passed",
        [
            {
                "check_id": f"{VERIFY_OPERATION}.integrity",
                "status": "passed",
                "evidence": evidence,
            }
        ],
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--trust-root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    contract = subparsers.add_parser("contract")
    contract.add_argument("--json", action="store_true")
    attest = subparsers.add_parser("attest")
    attest.add_argument("--full-artifact", type=Path, required=True)
    attest.add_argument("--release-artifact", type=Path, required=True)
    attest.add_argument("--evidence", action="append", default=[])
    attest.add_argument("--private-key", type=Path, required=True)
    attest.add_argument("--certifier-id", required=True)
    attest.add_argument("--invocation-id", default=uuid.uuid4().hex)
    attest.add_argument("--output-dir", type=Path, required=True)
    attest.add_argument("--json", action="store_true")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--bundle", type=Path)
    verify.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    repository_root = arguments.repository_root.resolve()
    trust_root = (arguments.trust_root or repository_root).resolve()
    if arguments.command == "contract":
        result = contract_result(repository_root, trust_root)
    elif arguments.command == "attest":
        try:
            attestation = create_attestation(
                repository_root=repository_root,
                trust_root=trust_root,
                output_dir=arguments.output_dir.resolve(),
                full_artifact=arguments.full_artifact,
                release_artifact=arguments.release_artifact,
                extra_evidence=[
                    _parse_evidence_argument(item) for item in arguments.evidence
                ],
                private_key=arguments.private_key,
                certifier_id=arguments.certifier_id,
                invocation_id=arguments.invocation_id,
            )
        except AttestationError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        summary = {
            "status": "passed",
            "output_dir": str(arguments.output_dir),
            "certified_source_sha": attestation["signed_payload"]["certified_source"][
                "commit"
            ],
            "evidence_root_sha256": attestation["signed_payload"][
                "evidence_root_sha256"
            ],
            "signature_sha256": attestation["signature"]["signature_sha256"],
        }
        print(
            json.dumps(summary, sort_keys=True)
            if arguments.json
            else json.dumps(summary, indent=2, sort_keys=True)
        )
        return 0
    else:
        trust = load_trust_policy(trust_root)
        bundle = arguments.bundle or repository_root / trust["bundle_path"]
        result = verification_result(repository_root, trust_root, bundle)
    print(
        json.dumps(result, sort_keys=True)
        if arguments.json
        else json.dumps(result, indent=2, sort_keys=True)
    )
    return 0 if result["status"] in SUCCESS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
