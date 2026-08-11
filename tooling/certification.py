#!/usr/bin/env python3
"""Structured certification artifacts and summaries for canonical quality profiles."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


ARTIFACT_SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "strling-profile-certification"
RESULT_STATUSES = (
    "passed",
    "failed",
    "waived",
    "unavailable",
    "incomplete",
    "not_applicable",
    "not_yet_configured",
    "not_yet_enforceable",
)
BLOCKING_STATUSES = {
    "failed",
    "incomplete",
    "unavailable",
    "not_yet_configured",
    "not_yet_enforceable",
}


class CertificationError(ValueError):
    """Raised when certification evidence cannot be constructed or validated."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def profile_definition_fingerprint(definition: Mapping[str, object]) -> str:
    """Fingerprint only the governed profile definition."""

    return _sha256(definition)


def aggregate_profile_status(statuses: Iterable[str]) -> str:
    """Apply the one canonical profile status precedence."""

    observed = set(statuses)
    unknown = observed.difference(RESULT_STATUSES)
    if unknown:
        raise CertificationError(
            f"cannot aggregate unknown result status '{sorted(unknown)[0]}'"
        )
    if "failed" in observed:
        return "failed"
    if observed.intersection(
        {"incomplete", "not_yet_configured", "not_yet_enforceable"}
    ):
        return "incomplete"
    if "unavailable" in observed:
        return "unavailable"
    if "waived" in observed:
        return "waived"
    return "passed"


def aggregate_profile_exit(statuses: Iterable[str]) -> int:
    """Derive fail-closed process status from canonical result states."""

    observed = tuple(statuses)
    unknown = set(observed).difference(RESULT_STATUSES)
    if unknown:
        raise CertificationError(
            f"cannot aggregate unknown result status '{sorted(unknown)[0]}'"
        )
    return 1 if any(status in BLOCKING_STATUSES for status in observed) else 0


def repository_state(root: Path) -> dict[str, object]:
    """Read committed identity and dirty state without mutating the repository."""

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if commit.returncode != 0:
        raise CertificationError(
            f"cannot resolve repository commit: {commit.stderr.strip() or 'git failed'}"
        )
    identity = commit.stdout.strip()
    if len(identity) != 40 or any(character not in "0123456789abcdef" for character in identity):
        raise CertificationError("repository commit identity is not a lowercase SHA-1")

    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if status.returncode != 0:
        raise CertificationError(
            f"cannot resolve repository state: {status.stderr.strip() or 'git failed'}"
        )
    return {"commit": identity, "dirty": bool(status.stdout)}


def _waiver_references(value: object) -> list[str]:
    references: set[str] = set()

    def visit(item: object) -> None:
        if isinstance(item, dict):
            waiver = item.get("waiver_id")
            if isinstance(waiver, str) and waiver:
                references.add(waiver)
            for nested in item.values():
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(value)
    return sorted(references)


def _operation_evidence(result: Mapping[str, object]) -> dict[str, object]:
    operation = result.get("operation")
    component = result.get("component")
    if not isinstance(operation, str) or not isinstance(component, str):
        raise CertificationError("operation results require operation and component IDs")
    evidence: dict[str, object] = {
        "operation_id": operation,
        "result_id": f"{operation}@{component}",
        "component": component,
        "status": result.get("status"),
        "command": result.get("command"),
        "exit_code": result.get("exit_code"),
        "reason": result.get("reason"),
        "capability": result.get("capability"),
        "formatters": result.get("formatters", []),
        "environment": result.get("environment", []),
        "waiver_references": _waiver_references(result.get("structured_result")),
    }
    structured = result.get("structured_result")
    if isinstance(structured, dict):
        evidence["structured_evidence"] = structured
    return evidence


def _component_scope(requested: str | None) -> dict[str, str]:
    if requested is None:
        return {"mode": "profile-default"}
    if requested == "all":
        return {"mode": "all"}
    return {"mode": "component", "component": requested}


def build_certification_artifact(
    *,
    root: Path,
    profile_id: str,
    profile_definition: Mapping[str, object],
    requested_component: str | None,
    results: Sequence[Mapping[str, object]],
    aggregate_status: str,
    exit_code: int,
    resolved_repository_state: Mapping[str, object] | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    """Build and validate an artifact from the exact aggregated result sequence."""

    statuses: list[str] = []
    operation_evidence: list[dict[str, object]] = []
    result_ids: set[str] = set()
    for result in results:
        status = result.get("status")
        if not isinstance(status, str):
            raise CertificationError("operation result status must be a string")
        statuses.append(status)
        evidence = _operation_evidence(result)
        result_id = evidence["result_id"]
        assert isinstance(result_id, str)
        if result_id in result_ids:
            raise CertificationError(f"duplicate certification result ID '{result_id}'")
        result_ids.add(result_id)
        operation_evidence.append(evidence)

    expected_status = aggregate_profile_status(statuses)
    expected_exit = aggregate_profile_exit(statuses)
    if aggregate_status != expected_status or exit_code != expected_exit:
        raise CertificationError(
            "artifact aggregate does not match the operation result set used for exit status"
        )

    definition_version = profile_definition.get("definition_version")
    purpose = profile_definition.get("purpose")
    network_policy = profile_definition.get("network_policy")
    if not all(
        isinstance(value, str)
        for value in (definition_version, purpose, network_policy)
    ):
        raise CertificationError("profile definition is missing artifact identity fields")

    counts = Counter(statuses)
    aggregate_counts = {status: counts.get(status, 0) for status in RESULT_STATUSES}
    repository = dict(resolved_repository_state or repository_state(root))
    deterministic_evidence: dict[str, object] = {
        "repository": repository,
        "profile": {
            "id": profile_id,
            "definition_version": definition_version,
            "definition_fingerprint": profile_definition_fingerprint(
                profile_definition
            ),
            "purpose": purpose,
            "network_policy": network_policy,
        },
        "component_scope": _component_scope(requested_component),
        "operations": operation_evidence,
        "aggregate": {
            "status": aggregate_status,
            "exit_code": exit_code,
            "operation_count": len(operation_evidence),
            "counts": aggregate_counts,
        },
    }
    artifact: dict[str, object] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "deterministic_evidence": deterministic_evidence,
        "evidence_fingerprint": _sha256(deterministic_evidence),
        "execution_metadata": {
            "generated_at": generated_at
            or datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        },
    }
    validate_certification_artifact(root, artifact)
    return artifact


def validate_certification_artifact(
    root: Path, artifact: Mapping[str, object]
) -> None:
    """Validate schema and deterministic evidence integrity."""

    schema_path = root / "governance/schemas/profile-certification-artifact.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(artifact)
    except (OSError, json.JSONDecodeError, SchemaError, ValidationError) as exc:
        raise CertificationError(f"invalid certification artifact: {exc}") from exc

    deterministic = artifact.get("deterministic_evidence")
    fingerprint = artifact.get("evidence_fingerprint")
    if not isinstance(deterministic, dict) or fingerprint != _sha256(deterministic):
        raise CertificationError(
            "invalid certification artifact: deterministic evidence fingerprint mismatch"
        )

    operations = deterministic["operations"]
    aggregate = deterministic["aggregate"]
    assert isinstance(operations, list)
    assert isinstance(aggregate, dict)
    statuses: list[str] = []
    result_ids: set[str] = set()
    for operation in operations:
        assert isinstance(operation, dict)
        operation_id = operation["operation_id"]
        component = operation["component"]
        result_id = operation["result_id"]
        status = operation["status"]
        assert isinstance(operation_id, str)
        assert isinstance(component, str)
        assert isinstance(result_id, str)
        assert isinstance(status, str)
        if result_id != f"{operation_id}@{component}" or result_id in result_ids:
            raise CertificationError(
                "invalid certification artifact: result identity mismatch"
            )
        result_ids.add(result_id)
        statuses.append(status)

    expected_counts = Counter(statuses)
    counts = aggregate["counts"]
    assert isinstance(counts, dict)
    if (
        aggregate["operation_count"] != len(operations)
        or any(counts[status] != expected_counts.get(status, 0) for status in RESULT_STATUSES)
        or aggregate["status"] != aggregate_profile_status(statuses)
        or aggregate["exit_code"] != aggregate_profile_exit(statuses)
    ):
        raise CertificationError(
            "invalid certification artifact: aggregate evidence mismatch"
        )


def write_certification_artifact(path: Path, artifact: Mapping[str, object]) -> None:
    """Write a validated artifact without affecting its semantic identity."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(artifact, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise CertificationError(f"cannot write certification artifact {path}: {exc}") from exc


def render_certification_summary(artifact: Mapping[str, object]) -> str:
    """Render the human view solely from validated structured evidence."""

    deterministic = artifact["deterministic_evidence"]
    assert isinstance(deterministic, dict)
    repository = deterministic["repository"]
    profile = deterministic["profile"]
    scope = deterministic["component_scope"]
    operations = deterministic["operations"]
    aggregate = deterministic["aggregate"]
    assert isinstance(repository, dict)
    assert isinstance(profile, dict)
    assert isinstance(scope, dict)
    assert isinstance(operations, list)
    assert isinstance(aggregate, dict)

    scope_text = str(scope["mode"])
    if scope_text == "component":
        scope_text = f"component:{scope['component']}"
    repository_state_text = "dirty" if repository["dirty"] else "clean"
    counts = aggregate["counts"]
    assert isinstance(counts, dict)
    count_text = ", ".join(
        f"{status}={counts[status]}"
        for status in RESULT_STATUSES
        if counts[status]
    )

    def describe(statuses: set[str]) -> str:
        selected: list[str] = []
        for operation in operations:
            assert isinstance(operation, dict)
            if operation["status"] not in statuses:
                continue
            reason = operation.get("reason")
            suffix = ""
            if (
                operation["status"] != "passed"
                and isinstance(reason, str)
                and reason
            ):
                suffix = f" - {reason}"
            selected.append(f"{operation['result_id']}{suffix}")
        return ", ".join(selected) if selected else "none"

    waived: list[str] = []
    for operation in operations:
        assert isinstance(operation, dict)
        if operation["status"] != "waived":
            continue
        references = operation["waiver_references"]
        assert isinstance(references, list)
        structured = operation.get("structured_evidence")
        recorded_finding = False
        if isinstance(structured, dict):
            checks = structured.get("checks", [])
            if isinstance(checks, list):
                for check in checks:
                    if not isinstance(check, dict):
                        continue
                    findings = check.get("findings", [])
                    if not isinstance(findings, list):
                        continue
                    for finding in findings:
                        if not isinstance(finding, dict):
                            continue
                        waiver = finding.get("waiver_id")
                        if not isinstance(waiver, str):
                            continue
                        code = finding.get("code", "finding")
                        waived.append(
                            f"{operation['result_id']}:{code} [{waiver}]"
                        )
                        recorded_finding = True
        if not recorded_finding:
            waived.append(
                f"{operation['result_id']} "
                f"[{', '.join(str(item) for item in references)}]"
            )

    aggregate_status = str(aggregate["status"])
    next_actions = {
        "passed": "No profile action is required.",
        "waived": "Review the recorded waiver references and their expiry conditions.",
        "unavailable": "Provide the required tools or environment, then rerun the profile.",
        "incomplete": "Complete the missing governed evidence, then rerun the profile.",
        "failed": "Resolve the failed operations, then rerun the profile.",
    }
    lines = [
        f"STRling certification profile: {profile['id']}",
        (
            f"Repository: {repository['commit']} ({repository_state_text}); "
            f"scope: {scope_text}"
        ),
        (
            f"Aggregate: {aggregate_status.upper()} "
            f"(exit {aggregate['exit_code']}; {count_text or 'no results'})"
        ),
        f"Passed operations: {describe({'passed'})}",
        f"Failed operations: {describe({'failed'})}",
        f"Waived findings: {', '.join(waived) if waived else 'none'}",
        (
            "Unavailable/incomplete operations: "
            + describe(
                {
                    "unavailable",
                    "incomplete",
                    "not_yet_configured",
                    "not_yet_enforceable",
                }
            )
        ),
        f"Next action: {next_actions[aggregate_status]}",
    ]
    return "\n".join(lines)
