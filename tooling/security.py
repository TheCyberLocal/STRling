#!/usr/bin/env python3
"""Deterministic repository-security operations for STRling."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "governance/security-policy.json"
POLICY_SCHEMA_PATH = ROOT / "governance/schemas/security-policy.schema.json"
ENGINE_NAME = "strling-repository-security"
ENGINE_VERSION = "1.2.0"
STATUSES = ("passed", "failed", "waived", "unavailable", "incomplete")
BLOCKING_STATUSES = ("failed", "unavailable", "incomplete")
EXIT_CODES = {
    "passed": 0,
    "waived": 0,
    "failed": 1,
    "unavailable": 2,
    "incomplete": 3,
}
STATUS_PRECEDENCE = {
    "passed": 0,
    "waived": 1,
    "incomplete": 2,
    "unavailable": 3,
    "failed": 4,
}
SECRET_PATTERNS = (
    (
        "SEC-SECRET-PRIVATE-KEY",
        "private key material is tracked",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ),
    (
        "SEC-SECRET-GITHUB-TOKEN",
        "GitHub access token is tracked",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    ),
    (
        "SEC-SECRET-CLOUD-ACCESS-KEY",
        "cloud access-key identifier is tracked",
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ),
    (
        "SEC-SECRET-NPM-TOKEN",
        "npm access token is tracked",
        re.compile(r"\bnpm_[A-Za-z0-9]{36,}\b"),
    ),
    (
        "SEC-SECRET-API-TOKEN",
        "high-confidence API token is tracked",
        re.compile(
            r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{32,}|xox[baprs]-[A-Za-z0-9-]{24,})\b"
        ),
    ),
    (
        "SEC-SECRET-REPOSITORY-CREDENTIAL",
        "repository URL contains embedded credentials",
        re.compile(r"https?://[^\s/:@]+:[^\s/@]+@[^\s]+"),
    ),
)
GENERIC_CREDENTIAL_PATTERN = re.compile(
    r"""(?ix)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)\b
    \s*[:=]\s*["']([A-Za-z0-9+/_.=-]{16,})["']"""
)


class SecurityConfigurationError(ValueError):
    """Raised when normative security inputs cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    path: str | None = None
    line: int | None = None
    package: str | None = None
    version: str | None = None
    advisory: str | None = None
    severity: str | None = None
    license: str | None = None
    waiver_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "code": self.code,
            "message": self.message,
        }
        for name in (
            "path",
            "line",
            "package",
            "version",
            "advisory",
            "severity",
            "license",
            "waiver_id",
        ):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        return result


@dataclass
class SecurityCheck:
    check_id: str
    category: str
    status: str
    inputs: list[str]
    ecosystem: str | None = None
    findings: list[Finding] = field(default_factory=list)
    unavailable_reason: str | None = None
    scanner: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "check_id": self.check_id,
            "category": self.category,
            "status": self.status,
            "inputs": sorted(self.inputs),
            "finding_codes": sorted({finding.code for finding in self.findings}),
            "findings": [
                finding.as_dict()
                for finding in sorted(
                    self.findings,
                    key=lambda item: (
                        item.code,
                        item.path or "",
                        item.line or 0,
                        item.package or "",
                        item.advisory or "",
                        item.message,
                    ),
                )
            ],
        }
        if self.ecosystem is not None:
            result["ecosystem"] = self.ecosystem
        if self.unavailable_reason is not None:
            result["unavailable_reason"] = self.unavailable_reason
        if self.scanner is not None:
            result["scanner"] = self.scanner
        return result


@dataclass
class SecurityOperation:
    operation_id: str
    network_mode: str
    checks: list[SecurityCheck]
    advisory_metadata: dict[str, object] | None = None

    @property
    def status(self) -> str:
        if not self.checks:
            return "incomplete"
        return max(
            (check.status for check in self.checks),
            key=lambda status: STATUS_PRECEDENCE[status],
        )

    def as_dict(self) -> dict[str, object]:
        summary = {
            status: sum(check.status == status for check in self.checks)
            for status in STATUSES
        }
        result: dict[str, object] = {
            "schema_version": "1.0.0",
            "operation_id": self.operation_id,
            "status": self.status,
            "engine": {"name": ENGINE_NAME, "version": ENGINE_VERSION},
            "network_mode": self.network_mode,
            "checks": [check.as_dict() for check in self.checks],
            "summary": summary,
        }
        if self.advisory_metadata is not None:
            result["advisory_metadata"] = self.advisory_metadata
        return result


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SecurityConfigurationError(f"cannot read {path}: {exc}") from exc


def load_policy(
    policy_path: Path = POLICY_PATH,
    schema_path: Path = POLICY_SCHEMA_PATH,
) -> dict[str, object]:
    policy = load_json(policy_path)
    schema = load_json(schema_path)
    if not isinstance(policy, dict):
        raise SecurityConfigurationError("security policy root must be an object")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(policy)
    except (SchemaError, ValidationError) as exc:
        raise SecurityConfigurationError(
            f"malformed security policy: {exc.message}"
        ) from exc
    return policy


TrackedFileProbe = Callable[[Path], list[str]]
CommandRunner = Callable[
    [Sequence[str], Path],
    subprocess.CompletedProcess[str],
]


def run_security_command(
    args: Sequence[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    command = list(args)
    if sys.platform == "win32" and command:
        declared = Path(command[0])
        if declared.is_absolute():
            candidate = declared
        elif declared.parent != Path("."):
            candidate = (cwd / declared).resolve()
        else:
            resolved = shutil.which(command[0])
            candidate = Path(resolved).resolve() if resolved is not None else declared
        candidates = [candidate]
        if candidate.suffix == "":
            candidates = [
                candidate.with_suffix(suffix) for suffix in (".cmd", ".exe", ".bat")
            ]
            candidates.append(candidate)
        for resolved in candidates:
            if resolved.is_file():
                command[0] = str(resolved)
                break
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def git_tracked_files(root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise SecurityConfigurationError(
            f"cannot enumerate tracked files: {exc}"
        ) from exc
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SecurityConfigurationError(
            f"cannot enumerate tracked files: {message or 'git ls-files failed'}"
        )
    return sorted(
        value.decode("utf-8", errors="strict")
        for value in completed.stdout.split(b"\0")
        if value
    )


class SecurityEngine:
    """Evaluate security policy without importing or executing product code."""

    def __init__(
        self,
        root: Path,
        policy: Mapping[str, object],
        *,
        tracked_files: Sequence[str] | None = None,
        tracked_file_probe: TrackedFileProbe = git_tracked_files,
        engine_version: str = ENGINE_VERSION,
        command_runner: CommandRunner = run_security_command,
        today: date | None = None,
    ) -> None:
        self.root = root
        self.policy = policy
        self._tracked_files = (
            sorted(tracked_files)
            if tracked_files is not None
            else tracked_file_probe(root)
        )
        self.engine_version = engine_version
        self._command_runner = command_runner
        self.today = today or date.today()

    def run_integrity(self) -> SecurityOperation:
        checks = [self._check_engine_pin(), self._check_dependency_inventory()]
        roots = self.policy.get("dependency_roots")
        if not isinstance(roots, list):
            return self._apply_security_waivers(
                SecurityOperation(
                    "security.dependency-integrity",
                    "local",
                    [
                        SecurityCheck(
                            "security.dependency-policy",
                            "dependency_integrity",
                            "incomplete",
                            [],
                            findings=[
                                Finding(
                                    "SEC-DEP-POLICY-MALFORMED",
                                    "dependency_roots is not a list",
                                )
                            ],
                        )
                    ],
                )
            )
        checks.extend(
            self._check_dependency_root(root)
            for root in roots
            if isinstance(root, dict)
        )
        if len(checks) != len(roots) + 2:
            checks.append(
                SecurityCheck(
                    "security.dependency-policy",
                    "dependency_integrity",
                    "incomplete",
                    [],
                    findings=[
                        Finding(
                            "SEC-DEP-POLICY-MALFORMED",
                            "one or more dependency roots is not an object",
                        )
                    ],
                )
            )
        return self._apply_security_waivers(
            SecurityOperation("security.dependency-integrity", "local", checks)
        )

    def run_content(self) -> SecurityOperation:
        workflows = sorted(
            path
            for path in self._tracked_files
            if path.startswith(".github/workflows/")
            and Path(path).suffix in (".yml", ".yaml")
        )
        checks = [self._check_tracked_secrets()]
        if workflows:
            checks.extend(self._check_workflow(path) for path in workflows)
        else:
            checks.append(
                SecurityCheck(
                    "security.workflows",
                    "workflow",
                    "passed",
                    [],
                    scanner={"name": ENGINE_NAME, "version": self.engine_version},
                )
            )
        return self._apply_security_waivers(
            SecurityOperation("security.content-and-workflows", "local", checks)
        )

    def run_risk(self) -> SecurityOperation:
        roots = self.policy.get("dependency_roots")
        if not isinstance(roots, list):
            return self._apply_security_waivers(
                SecurityOperation(
                    "security.dependency-risk",
                    "network",
                    [
                        SecurityCheck(
                            "security.dependency-risk.policy",
                            "vulnerability",
                            "incomplete",
                            [],
                            findings=[
                                Finding(
                                    "SEC-RISK-POLICY-MALFORMED",
                                    "dependency_roots is not a list",
                                )
                            ],
                        )
                    ],
                )
            )

        checks: list[SecurityCheck] = []
        coverage_gaps: list[dict[str, object]] = []
        for raw in roots:
            if not isinstance(raw, dict):
                checks.append(
                    SecurityCheck(
                        "security.dependency-risk.policy",
                        "vulnerability",
                        "incomplete",
                        [],
                        findings=[
                            Finding(
                                "SEC-RISK-POLICY-MALFORMED",
                                "dependency root is not an object",
                            )
                        ],
                    )
                )
                continue
            root_id = str(raw.get("id", "unknown"))
            mode = raw.get("risk_mode")
            inputs = [
                *self._string_list(raw.get("manifests")),
                *self._string_list(raw.get("locks")),
            ]
            if mode == "npm_audit":
                checks.append(self._audit_npm(root_id, raw))
                checks.append(self._license_npm(root_id, raw))
            elif mode == "cargo_audit":
                checks.append(self._audit_cargo(root_id, raw))
                checks.append(self._license_cargo(root_id, raw))
            elif mode == "osv_scan":
                vulnerability, license_check = self._audit_osv(root_id, raw)
                checks.extend([vulnerability, license_check])
            elif mode == "luarocks_evidence":
                vulnerability, license_check = self._audit_luarocks(root_id, raw)
                checks.extend([vulnerability, license_check])
            elif mode == "cpansa_evidence":
                vulnerability, license_check = self._audit_cpansa(root_id, raw)
                checks.extend([vulnerability, license_check])
            elif mode == "no_dependencies":
                scanner = {"name": ENGINE_NAME, "version": self.engine_version}
                checks.extend(
                    [
                        SecurityCheck(
                            f"security.vulnerability.{root_id}",
                            "vulnerability",
                            "passed",
                            inputs,
                            ecosystem=str(raw.get("ecosystem", "unknown")),
                            scanner=scanner,
                        ),
                        SecurityCheck(
                            f"security.license.{root_id}",
                            "license",
                            "passed",
                            inputs,
                            ecosystem=str(raw.get("ecosystem", "unknown")),
                            scanner=scanner,
                        ),
                    ]
                )
            elif mode == "unavailable":
                reason = "no authoritative repository scanner is configured for this ecosystem"
                coverage_gaps.append(
                    {
                        "root_id": root_id,
                        "ecosystem": str(raw.get("ecosystem", "unknown")),
                        "reason": reason,
                    }
                )
                scanner = {"name": ENGINE_NAME, "version": self.engine_version}
                checks.extend(
                    [
                        self._risk_unavailable(
                            root_id,
                            "vulnerability",
                            str(raw.get("ecosystem", "unknown")),
                            inputs,
                            reason,
                            scanner,
                        ),
                        self._risk_unavailable(
                            root_id,
                            "license",
                            str(raw.get("ecosystem", "unknown")),
                            inputs,
                            reason,
                            scanner,
                        ),
                    ]
                )
            else:
                checks.append(
                    SecurityCheck(
                        f"security.vulnerability.{root_id}",
                        "vulnerability",
                        "incomplete",
                        inputs,
                        ecosystem=str(raw.get("ecosystem", "unknown")),
                        findings=[
                            Finding(
                                "SEC-RISK-MODE-UNKNOWN",
                                f"unsupported risk mode: {mode!r}",
                            )
                        ],
                    )
                )

        vulnerability_policy = self.policy.get("vulnerability_policy")
        sources = (
            vulnerability_policy.get("advisory_sources", {})
            if isinstance(vulnerability_policy, dict)
            else {}
        )
        metadata = {
            "sources": sources,
            "retrieval_status": {
                check.check_id: check.status
                for check in checks
                if check.category == "vulnerability"
            },
            "coverage_gaps": sorted(
                coverage_gaps, key=lambda item: str(item["root_id"])
            ),
        }
        return self._apply_security_waivers(
            SecurityOperation(
                "security.dependency-risk",
                "network",
                checks,
                advisory_metadata=metadata,
            )
        )

    def _apply_security_waivers(
        self, operation: SecurityOperation
    ) -> SecurityOperation:
        configured = self.policy.get("security_waivers", [])
        if not configured:
            return operation
        waiver_inputs: list[str] = []
        errors: list[Finding] = []
        if not isinstance(configured, list) or any(
            not isinstance(item, str) for item in configured
        ):
            errors.append(
                Finding(
                    "SEC-WAIVER-POLICY-MALFORMED",
                    "security_waivers must be a list of stable waiver IDs",
                    path="governance/security-policy.json",
                )
            )
            configured = []
        elif len(configured) != len(set(configured)):
            errors.append(
                Finding(
                    "SEC-WAIVER-POLICY-MALFORMED",
                    "security_waivers contains a duplicate waiver ID",
                    path="governance/security-policy.json",
                )
            )

        schema_path = self.policy.get("waiver_schema")
        schema: object | None = None
        if isinstance(schema_path, str):
            try:
                schema = load_json(self.root / schema_path)
                Draft202012Validator.check_schema(schema)
            except (SecurityConfigurationError, SchemaError) as exc:
                errors.append(
                    Finding(
                        "SEC-WAIVER-SCHEMA-MALFORMED",
                        f"security waiver schema is unavailable: {exc}",
                        path=schema_path,
                    )
                )
        else:
            errors.append(
                Finding(
                    "SEC-WAIVER-POLICY-MALFORMED",
                    "waiver_schema must be a repository path",
                    path="governance/security-policy.json",
                )
            )

        records: dict[str, Mapping[str, object]] = {}
        waiver_directory = self.root / "governance" / "waivers"
        if schema is not None:
            for waiver_path in sorted(waiver_directory.glob("*.yaml")):
                relative_path = waiver_path.relative_to(self.root).as_posix()
                try:
                    loaded = yaml.safe_load(waiver_path.read_text(encoding="utf-8"))
                    Draft202012Validator(schema).validate(loaded)
                except (OSError, yaml.YAMLError, ValidationError) as exc:
                    errors.append(
                        Finding(
                            "SEC-WAIVER-RECORD-MALFORMED",
                            f"waiver record is malformed: {exc}",
                            path=relative_path,
                        )
                    )
                    continue
                if not isinstance(loaded, dict):
                    continue
                waiver_id = str(loaded.get("waiver_id", ""))
                if waiver_id in records:
                    errors.append(
                        Finding(
                            "SEC-WAIVER-ID-DUPLICATE",
                            f"waiver ID {waiver_id} is declared more than once",
                            path=relative_path,
                        )
                    )
                    continue
                records[waiver_id] = loaded

        relevant: list[tuple[str, Mapping[str, object], str]] = []
        for waiver_id in configured:
            if not isinstance(waiver_id, str):
                continue
            record_path = f"governance/waivers/{waiver_id}.yaml"
            waiver_inputs.append(record_path)
            record = records.get(waiver_id)
            if record is None:
                errors.append(
                    Finding(
                        "SEC-WAIVER-UNKNOWN",
                        f"configured security waiver {waiver_id} was not found",
                        path=record_path,
                    )
                )
                continue
            security = record.get("security")
            if not isinstance(security, dict):
                errors.append(
                    Finding(
                        "SEC-WAIVER-RECORD-MALFORMED",
                        f"configured waiver {waiver_id} has no security scope",
                        path=record_path,
                    )
                )
                continue
            retirement = record.get("retirement")
            expires_on = (
                retirement.get("expires_on") if isinstance(retirement, dict) else None
            )
            created_on = security.get("created_on")
            try:
                expiry = date.fromisoformat(str(expires_on))
                created = date.fromisoformat(str(created_on))
            except ValueError:
                errors.append(
                    Finding(
                        "SEC-WAIVER-RECORD-MALFORMED",
                        f"security waiver {waiver_id} has no valid creation date or expiry",
                        path=record_path,
                    )
                )
                continue
            if record.get("status") != "accepted":
                errors.append(
                    Finding(
                        "SEC-WAIVER-NOT-ACCEPTED",
                        f"security waiver {waiver_id} is not accepted",
                        path=record_path,
                    )
                )
                continue
            if created > self.today or expiry < created:
                errors.append(
                    Finding(
                        "SEC-WAIVER-DATE-INVALID",
                        f"security waiver {waiver_id} has an invalid creation/expiry interval",
                        path=record_path,
                    )
                )
                continue
            if expiry < self.today:
                errors.append(
                    Finding(
                        "SEC-WAIVER-EXPIRED",
                        f"security waiver {waiver_id} expired on {expiry.isoformat()}",
                        path=record_path,
                    )
                )
                continue
            if security.get("operation_id") == operation.operation_id:
                relevant.append((waiver_id, record, record_path))

        assignments: dict[tuple[str, int], str] = {}
        for waiver_id, record, record_path in relevant:
            security = record["security"]
            assert isinstance(security, dict)
            finding_code = str(security["finding_code"])
            matches = security["matches"]
            scope = record["scope"]
            assert isinstance(matches, list) and isinstance(scope, dict)
            declared_paths = set(self._string_list(scope.get("paths")))
            covered_inputs: set[str] = set()
            for raw_match in matches:
                assert isinstance(raw_match, dict)
                check_id = str(raw_match["check_id"])
                candidates: list[tuple[SecurityCheck, int]] = []
                for check in operation.checks:
                    if check.check_id != check_id:
                        continue
                    for index, finding in enumerate(check.findings):
                        if finding.code != finding_code:
                            continue
                        if self._waiver_match_finding(raw_match, finding):
                            candidates.append((check, index))
                expected = 1
                for value in raw_match.values():
                    if isinstance(value, list):
                        expected *= len(value)
                if len(candidates) != expected:
                    errors.append(
                        Finding(
                            "SEC-WAIVER-SCOPE-STALE",
                            f"waiver {waiver_id} match resolved to {len(candidates)} findings, expected {expected}",
                            path=record_path,
                        )
                    )
                    continue
                for check, index in candidates:
                    key = (check.check_id, index)
                    if key in assignments:
                        errors.append(
                            Finding(
                                "SEC-WAIVER-SCOPE-OVERLAP",
                                f"finding is covered by both {assignments[key]} and {waiver_id}",
                                path=record_path,
                            )
                        )
                        continue
                    assignments[key] = waiver_id
                    covered_inputs.update(check.inputs)
            if covered_inputs != declared_paths:
                errors.append(
                    Finding(
                        "SEC-WAIVER-PATH-SCOPE-MISMATCH",
                        f"waiver {waiver_id} paths do not exactly equal matched check inputs",
                        path=record_path,
                    )
                )

        if errors:
            operation.checks.append(
                SecurityCheck(
                    "security.waivers",
                    "waiver",
                    "failed",
                    sorted(set(waiver_inputs)),
                    findings=errors,
                    scanner={"name": ENGINE_NAME, "version": self.engine_version},
                )
            )
            return operation

        for check in operation.checks:
            check.findings = [
                replace(
                    finding,
                    waiver_id=assignments.get((check.check_id, index)),
                )
                if (check.check_id, index) in assignments
                else finding
                for index, finding in enumerate(check.findings)
            ]
            blocking = [
                finding
                for finding in check.findings
                if finding.code != "SEC-VULN-NONBLOCKING"
            ]
            if (
                check.status == "failed"
                and blocking
                and all(finding.waiver_id for finding in blocking)
            ):
                check.status = "waived"
        operation.checks.append(
            SecurityCheck(
                "security.waivers",
                "waiver",
                "passed",
                sorted(set(waiver_inputs)),
                scanner={"name": ENGINE_NAME, "version": self.engine_version},
            )
        )
        return operation

    @staticmethod
    def _waiver_match_finding(
        raw_match: Mapping[str, object], finding: Finding
    ) -> bool:
        fields = {
            "paths": "path",
            "packages": "package",
            "versions": "version",
            "advisories": "advisory",
            "severities": "severity",
            "licenses": "license",
        }
        for match_name, finding_name in fields.items():
            values = raw_match.get(match_name)
            if (
                isinstance(values, list)
                and getattr(finding, finding_name) not in values
            ):
                return False
        return True

    def _secret_marker_exclusions(
        self,
    ) -> tuple[dict[str, set[str]], list[Finding]]:
        secret_policy = self.policy.get("secret_policy")
        if secret_policy is None:
            return {}, []
        if not isinstance(secret_policy, dict):
            return {}, [
                Finding(
                    "SEC-SECRET-POLICY-MALFORMED",
                    "secret_policy must be a mapping",
                    path="governance/security-policy.json",
                )
            ]
        policy_path = secret_policy.get("credential_marker_policy")
        if not isinstance(policy_path, str):
            return {}, [
                Finding(
                    "SEC-SECRET-POLICY-MALFORMED",
                    "credential_marker_policy must be a repository path",
                    path="governance/security-policy.json",
                )
            ]
        try:
            marker_policy = load_json(self.root / policy_path)
        except SecurityConfigurationError as exc:
            return {}, [
                Finding(
                    "SEC-SECRET-POLICY-MALFORMED",
                    str(exc),
                    path=policy_path,
                )
            ]
        if not isinstance(marker_policy, dict):
            return {}, [
                Finding(
                    "SEC-SECRET-POLICY-MALFORMED",
                    "credential marker policy must be a mapping",
                    path=policy_path,
                )
            ]
        markers = marker_policy.get("private_key_markers")
        entries = marker_policy.get("credential_marker_exclusions")
        if not isinstance(markers, list) or not isinstance(entries, list):
            return {}, [
                Finding(
                    "SEC-SECRET-POLICY-MALFORMED",
                    "credential marker policy requires marker and exclusion lists",
                    path=policy_path,
                )
            ]
        exclusions: dict[str, set[str]] = {}
        errors: list[Finding] = []
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("path"), str)
                or not isinstance(entry.get("rationale"), str)
                or not entry["rationale"].strip()
            ):
                errors.append(
                    Finding(
                        "SEC-SECRET-POLICY-MALFORMED",
                        "credential marker exclusions require exact path and rationale",
                        path=policy_path,
                    )
                )
                continue
            exclusions[entry["path"]] = {
                marker for marker in markers if isinstance(marker, str)
            }
        return exclusions, errors

    def _check_tracked_secrets(self) -> SecurityCheck:
        marker_exclusions, policy_errors = self._secret_marker_exclusions()
        findings: list[Finding] = []
        incomplete: list[Finding] = []
        for relative_path in self._tracked_files:
            path = self.root / relative_path
            if not path.is_file():
                incomplete.append(
                    Finding(
                        "SEC-SECRET-SCAN-INCOMPLETE",
                        "tracked path could not be read as a regular file",
                        path=relative_path,
                    )
                )
                continue
            try:
                content = path.read_bytes().decode("utf-8", errors="replace")
            except OSError as exc:
                incomplete.append(
                    Finding(
                        "SEC-SECRET-SCAN-INCOMPLETE",
                        f"tracked path could not be read: {exc}",
                        path=relative_path,
                    )
                )
                continue
            for code, message, pattern in SECRET_PATTERNS:
                for match in pattern.finditer(content):
                    if code == "SEC-SECRET-PRIVATE-KEY" and match.group(
                        0
                    ) in marker_exclusions.get(relative_path, set()):
                        continue
                    findings.append(
                        Finding(
                            code,
                            message,
                            path=relative_path,
                            line=content.count("\n", 0, match.start()) + 1,
                        )
                    )
            findings.extend(
                Finding(
                    "SEC-SECRET-OBVIOUS-CREDENTIAL",
                    "obvious credential assignment is tracked",
                    path=relative_path,
                    line=content.count("\n", 0, match.start()) + 1,
                )
                for match in GENERIC_CREDENTIAL_PATTERN.finditer(content)
            )
        if incomplete or policy_errors:
            return SecurityCheck(
                "security.tracked-secrets",
                "secret",
                "incomplete",
                list(self._tracked_files),
                findings=[*findings, *incomplete, *policy_errors],
                scanner={"name": ENGINE_NAME, "version": self.engine_version},
            )
        return self._finding_check(
            "security.tracked-secrets",
            "secret",
            list(self._tracked_files),
            findings,
            scanner={"name": ENGINE_NAME, "version": self.engine_version},
        )

    def _check_workflow(self, relative_path: str) -> SecurityCheck:
        try:
            content = (self.root / relative_path).read_text(encoding="utf-8")
            loaded = yaml.safe_load(content)
        except (OSError, yaml.YAMLError) as exc:
            return SecurityCheck(
                f"security.workflow.{Path(relative_path).stem}",
                "workflow",
                "incomplete",
                [relative_path],
                findings=[
                    Finding(
                        "SEC-WORKFLOW-MALFORMED",
                        f"workflow could not be parsed: {exc}",
                        path=relative_path,
                    )
                ],
                scanner={"name": ENGINE_NAME, "version": self.engine_version},
            )
        if not isinstance(loaded, dict):
            return SecurityCheck(
                f"security.workflow.{Path(relative_path).stem}",
                "workflow",
                "incomplete",
                [relative_path],
                findings=[
                    Finding(
                        "SEC-WORKFLOW-MALFORMED",
                        "workflow root must be a mapping",
                        path=relative_path,
                    )
                ],
                scanner={"name": ENGINE_NAME, "version": self.engine_version},
            )

        findings: list[Finding] = []
        workflow_policy = self.policy.get("workflow_policy")
        if not isinstance(workflow_policy, dict):
            return SecurityCheck(
                f"security.workflow.{Path(relative_path).stem}",
                "workflow",
                "incomplete",
                [relative_path],
                findings=[
                    Finding(
                        "SEC-WORKFLOW-POLICY-MALFORMED",
                        "workflow_policy must be a mapping",
                        path="governance/security-policy.json",
                    )
                ],
                scanner={"name": ENGINE_NAME, "version": self.engine_version},
            )

        expected_permissions = workflow_policy.get("default_permissions")
        if loaded.get("permissions") != expected_permissions:
            findings.append(
                Finding(
                    "SEC-WORKFLOW-DEFAULT-PERMISSIONS",
                    "workflow must declare the exact read-only default permissions",
                    path=relative_path,
                    line=self._line_for(content, "permissions:"),
                )
            )

        jobs = loaded.get("jobs")
        if not isinstance(jobs, dict):
            findings.append(
                Finding(
                    "SEC-WORKFLOW-MALFORMED",
                    "workflow jobs must be a mapping",
                    path=relative_path,
                )
            )
            jobs = {}

        privileged_jobs = self._workflow_job_policy(
            workflow_policy, "privileged_jobs", relative_path
        )
        persistence_jobs = set(
            self._workflow_path_list(
                workflow_policy, "credential_persistence_jobs", relative_path
            )
        )
        for job_id, raw_job in sorted(jobs.items()):
            if not isinstance(raw_job, dict):
                findings.append(
                    Finding(
                        "SEC-WORKFLOW-MALFORMED",
                        f"job {job_id} must be a mapping",
                        path=relative_path,
                    )
                )
                continue
            permissions = raw_job.get("permissions", {})
            if not isinstance(permissions, dict):
                findings.append(
                    Finding(
                        "SEC-WORKFLOW-JOB-PERMISSIONS",
                        f"job {job_id} permissions must be a mapping",
                        path=relative_path,
                    )
                )
                permissions = {}
            allowed_write_scopes = set(privileged_jobs.get(str(job_id), []))
            for scope, access in permissions.items():
                if access == "write" and scope not in allowed_write_scopes:
                    findings.append(
                        Finding(
                            "SEC-WORKFLOW-JOB-PERMISSIONS",
                            f"job {job_id} has ungoverned {scope}: write permission",
                            path=relative_path,
                            line=self._line_for(content, f"{scope}: write"),
                        )
                    )

            if (
                workflow_policy.get("validation_secrets_prohibited")
                and relative_path.endswith("/ci.yml")
                and "${{ secrets." in json.dumps(raw_job)
            ):
                findings.append(
                    Finding(
                        "SEC-WORKFLOW-VALIDATION-SECRET",
                        f"validation job {job_id} references a repository secret",
                        path=relative_path,
                    )
                )

            steps = raw_job.get("steps", [])
            if not isinstance(steps, list):
                findings.append(
                    Finding(
                        "SEC-WORKFLOW-MALFORMED",
                        f"job {job_id} steps must be a list",
                        path=relative_path,
                    )
                )
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                if isinstance(uses, str):
                    findings.extend(
                        self._action_reference_findings(
                            relative_path, content, str(job_id), uses
                        )
                    )
                    if uses.startswith("actions/checkout@"):
                        settings = step.get("with", {})
                        if not isinstance(settings, dict):
                            settings = {}
                        actual = settings.get("persist-credentials")
                        expected = str(job_id) in persistence_jobs
                        if actual is not expected:
                            findings.append(
                                Finding(
                                    "SEC-WORKFLOW-CREDENTIAL-PERSISTENCE",
                                    f"checkout in job {job_id} must set persist-credentials to {str(expected).lower()}",
                                    path=relative_path,
                                    line=self._line_for(content, uses),
                                )
                            )
                run = step.get("run")
                if (
                    workflow_policy.get("shell_secret_interpolation_prohibited")
                    and isinstance(run, str)
                    and "${{ secrets." in run
                ):
                    findings.append(
                        Finding(
                            "SEC-WORKFLOW-SHELL-SECRET",
                            f"job {job_id} interpolates a secret directly into shell command text",
                            path=relative_path,
                            line=self._line_for(content, "${{ secrets."),
                        )
                    )

        return self._finding_check(
            f"security.workflow.{Path(relative_path).stem}",
            "workflow",
            [relative_path],
            findings,
            scanner={"name": ENGINE_NAME, "version": self.engine_version},
        )

    def _action_reference_findings(
        self, path: str, content: str, job_id: str, uses: str
    ) -> list[Finding]:
        if uses.startswith(("./", "docker://")):
            return []
        if "@" not in uses:
            return [
                Finding(
                    "SEC-WORKFLOW-ACTION-UNPINNED",
                    f"job {job_id} action reference has no revision",
                    path=path,
                    line=self._line_for(content, uses),
                )
            ]
        revision = uses.rsplit("@", 1)[1]
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            return [
                Finding(
                    "SEC-WORKFLOW-ACTION-UNPINNED",
                    f"job {job_id} action reference must use a full immutable commit",
                    path=path,
                    line=self._line_for(content, uses),
                )
            ]
        return []

    @staticmethod
    def _workflow_job_policy(
        policy: Mapping[str, object], field_name: str, path: str
    ) -> dict[str, list[str]]:
        configured = policy.get(field_name, {})
        if not isinstance(configured, dict):
            return {}
        selected = configured.get(path, {})
        if not isinstance(selected, dict):
            return {}
        return {
            str(job): [str(scope) for scope in scopes]
            for job, scopes in selected.items()
            if isinstance(scopes, list)
        }

    @staticmethod
    def _workflow_path_list(
        policy: Mapping[str, object], field_name: str, path: str
    ) -> list[str]:
        configured = policy.get(field_name, {})
        if not isinstance(configured, dict):
            return []
        selected = configured.get(path, [])
        if not isinstance(selected, list):
            return []
        return [str(item) for item in selected]

    @staticmethod
    def _line_for(content: str, needle: str) -> int | None:
        for line_number, line in enumerate(content.splitlines(), start=1):
            if needle in line:
                return line_number
        return None

    def _invoke(
        self, args: Sequence[str], cwd: Path
    ) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
        try:
            return self._command_runner(args, cwd), None
        except OSError as exc:
            return None, str(exc)

    def _audit_npm(self, root_id: str, raw: Mapping[str, object]) -> SecurityCheck:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        inputs = [*manifests, *locks]
        ecosystem = str(raw.get("ecosystem", "npm"))
        if len(manifests) != 1 or len(locks) != 1:
            return SecurityCheck(
                f"security.vulnerability.{root_id}",
                "vulnerability",
                "incomplete",
                inputs,
                ecosystem=ecosystem,
                findings=[
                    Finding(
                        "SEC-VULN-INVENTORY-INCOMPLETE",
                        "npm audit requires exactly one manifest and lockfile",
                    )
                ],
            )
        lock, lock_findings = self._read_json_object(
            locks[0], "SEC-VULN-INVENTORY-INCOMPLETE"
        )
        if lock is None:
            return SecurityCheck(
                f"security.vulnerability.{root_id}",
                "vulnerability",
                "incomplete",
                inputs,
                ecosystem=ecosystem,
                findings=lock_findings,
            )
        cwd = (self.root / manifests[0]).parent
        version_result, version_error = self._invoke(["npm", "--version"], cwd)
        if version_result is None or version_result.returncode != 0:
            reason = version_error or version_result.stderr.strip() or "npm unavailable"
            return self._risk_unavailable(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                reason,
                {"name": "npm audit", "source": "npm-registry"},
            )
        npm_version = version_result.stdout.strip()
        scanner = {
            "name": "npm audit",
            "version": npm_version,
            "source": "npm-registry",
        }
        audit_result, audit_error = self._invoke(
            ["npm", "audit", "--json", "--package-lock-only"], cwd
        )
        if audit_result is None:
            return self._risk_unavailable(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                audit_error or "npm audit unavailable",
                scanner,
            )
        try:
            payload = json.loads(audit_result.stdout)
        except json.JSONDecodeError as exc:
            reason = audit_result.stderr.strip()
            if audit_result.returncode != 0 and reason:
                return self._risk_unavailable(
                    root_id,
                    "vulnerability",
                    ecosystem,
                    inputs,
                    reason,
                    scanner,
                )
            return SecurityCheck(
                f"security.vulnerability.{root_id}",
                "vulnerability",
                "incomplete",
                inputs,
                ecosystem=ecosystem,
                findings=[
                    Finding(
                        "SEC-VULN-EVIDENCE-INCOMPLETE",
                        f"npm audit did not return JSON: {exc}",
                    )
                ],
                scanner=scanner,
            )
        if not isinstance(payload, dict):
            return self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "npm audit result must be an object",
                scanner,
            )
        error = payload.get("error")
        if error:
            reason = json.dumps(error, sort_keys=True)
            return self._risk_unavailable(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                reason,
                scanner,
            )
        vulnerabilities = payload.get("vulnerabilities")
        if not isinstance(vulnerabilities, dict):
            return self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "npm audit result omitted vulnerability inventory",
                scanner,
            )
        packages = lock.get("packages")
        if not isinstance(packages, dict):
            return self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "npm lockfile omitted package inventory",
                scanner,
            )
        findings: list[Finding] = []
        incomplete = False
        seen: set[tuple[str, str, str, str]] = set()
        blocking_severities = self._blocking_severities()
        for package_name, raw_vulnerability in sorted(vulnerabilities.items()):
            if not isinstance(raw_vulnerability, dict):
                incomplete = True
                continue
            nodes = raw_vulnerability.get("nodes", [])
            versions = sorted(
                {
                    str(packages[node].get("version"))
                    for node in nodes
                    if isinstance(node, str)
                    and isinstance(packages.get(node), dict)
                    and packages[node].get("version")
                }
            )
            if not versions:
                incomplete = True
                continue
            vias = raw_vulnerability.get("via", [])
            direct_advisories = [via for via in vias if isinstance(via, dict)]
            for advisory in direct_advisories:
                identifier = advisory.get("url") or advisory.get("source")
                if identifier is None:
                    incomplete = True
                    continue
                severity = str(
                    advisory.get("severity")
                    or raw_vulnerability.get("severity")
                    or "unknown"
                ).lower()
                title = str(advisory.get("title") or advisory.get("name") or "")
                for version in versions:
                    advisory_range = advisory.get("range")
                    applies = (
                        self._npm_range_contains(version, advisory_range)
                        if isinstance(advisory_range, str)
                        else True
                    )
                    if applies is None:
                        incomplete = True
                        continue
                    if not applies:
                        continue
                    key = (str(package_name), version, str(identifier), severity)
                    if key in seen:
                        continue
                    seen.add(key)
                    blocking = severity in blocking_severities or severity == "unknown"
                    findings.append(
                        Finding(
                            "SEC-VULN-BLOCKING" if blocking else "SEC-VULN-NONBLOCKING",
                            title or "npm advisory affects locked dependency",
                            package=str(package_name),
                            version=version,
                            advisory=str(identifier),
                            severity=severity,
                        )
                    )
        if incomplete:
            findings.append(
                Finding(
                    "SEC-VULN-EVIDENCE-INCOMPLETE",
                    "npm audit evidence could not be bound to every package/version/advisory",
                )
            )
            return SecurityCheck(
                f"security.vulnerability.{root_id}",
                "vulnerability",
                "incomplete",
                inputs,
                ecosystem=ecosystem,
                findings=findings,
                scanner=scanner,
            )
        status = (
            "failed"
            if any(finding.code == "SEC-VULN-BLOCKING" for finding in findings)
            else "passed"
        )
        return SecurityCheck(
            f"security.vulnerability.{root_id}",
            "vulnerability",
            status,
            inputs,
            ecosystem=ecosystem,
            findings=findings,
            scanner={**scanner, "retrieval": "completed"},
        )

    def _audit_osv(
        self, root_id: str, raw: Mapping[str, object]
    ) -> tuple[SecurityCheck, SecurityCheck]:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        inputs = [*manifests, *locks]
        ecosystem = str(raw.get("ecosystem", "unknown"))
        scan_inputs = [
            relative
            for relative in (locks or manifests)
            if self._osv_supported_input(relative)
        ]
        expected_version = self._security_tool_version("osv-scanner")
        executable = self._security_tool_executable("osv-scanner")
        scanner: dict[str, object] = {
            "name": "OSV-Scanner",
            "expected_version": expected_version,
            "source": "osv.dev/deps.dev",
        }
        if not scan_inputs or expected_version is None or executable is None:
            reason = (
                "OSV scanning requires governed inputs, a pinned scanner, and "
                "an authenticated scanner executable"
            )
            return (
                self._risk_unavailable(
                    root_id, "vulnerability", ecosystem, inputs, reason, scanner
                ),
                self._risk_unavailable(
                    root_id, "license", ecosystem, inputs, reason, scanner
                ),
            )

        version_result, version_error = self._invoke(
            [executable, "--version"], self.root
        )
        if version_result is None or version_result.returncode != 0:
            reason = (
                version_error
                or version_result.stderr.strip()
                or "OSV-Scanner is unavailable"
            )
            return (
                self._risk_unavailable(
                    root_id, "vulnerability", ecosystem, inputs, reason, scanner
                ),
                self._risk_unavailable(
                    root_id, "license", ecosystem, inputs, reason, scanner
                ),
            )
        match = re.search(
            r"osv-scanner version:\s*(\d+\.\d+\.\d+)", version_result.stdout
        )
        actual_version = match.group(1) if match else "unknown"
        executable_path = Path(executable).resolve()
        expected_sha256 = self._security_tool_sha256("osv-scanner")
        actual_sha256 = (
            hashlib.sha256(executable_path.read_bytes()).hexdigest()
            if executable_path.is_file()
            else None
        )
        scanner.update(
            {
                "version": actual_version,
                "executable": executable_path.as_posix(),
                "executable_sha256": actual_sha256,
                "expected_sha256": expected_sha256,
            }
        )
        identity_findings: list[Finding] = []
        if actual_version != expected_version:
            identity_findings.append(
                Finding(
                    "SEC-TOOL-VERSION-DRIFT",
                    f"OSV-Scanner {actual_version} does not match {expected_version}",
                )
            )
        if expected_sha256 is None or actual_sha256 != expected_sha256:
            identity_findings.append(
                Finding(
                    "SEC-TOOL-HASH-DRIFT",
                    "OSV-Scanner executable hash does not match the governed platform hash",
                )
            )
        if identity_findings:

            def failed(category: str) -> SecurityCheck:
                return SecurityCheck(
                    f"security.{category}.{root_id}",
                    category,
                    "failed",
                    inputs,
                    ecosystem=ecosystem,
                    findings=list(identity_findings),
                    scanner=scanner,
                )

            return failed("vulnerability"), failed("license")

        license_allowlist = self._security_tool_string_list(
            "osv-scanner", "license_allowlist"
        )
        command = [
            executable,
            "scan",
            "source",
            "--format",
            "json",
            "--all-packages",
            "--no-resolve",
        ]
        if license_allowlist:
            command.append(f"--licenses={','.join(license_allowlist)}")
        for relative in scan_inputs:
            command.extend(["--lockfile", relative])
        scan_result, scan_error = self._invoke(command, self.root)
        if scan_result is None:
            reason = scan_error or "OSV-Scanner execution failed"
            return (
                self._risk_unavailable(
                    root_id, "vulnerability", ecosystem, inputs, reason, scanner
                ),
                self._risk_unavailable(
                    root_id, "license", ecosystem, inputs, reason, scanner
                ),
            )
        try:
            payload = json.loads(scan_result.stdout)
        except json.JSONDecodeError as exc:
            reason = scan_result.stderr.strip()
            if scan_result.returncode not in (0, 1) and reason:
                return (
                    self._risk_unavailable(
                        root_id, "vulnerability", ecosystem, inputs, reason, scanner
                    ),
                    self._risk_unavailable(
                        root_id, "license", ecosystem, inputs, reason, scanner
                    ),
                )
            error_message = f"OSV-Scanner did not return JSON: {exc}"

            def incomplete(category: str) -> SecurityCheck:
                return self._risk_incomplete(
                    root_id,
                    category,
                    ecosystem,
                    inputs,
                    error_message,
                    scanner,
                )

            return incomplete("vulnerability"), incomplete("license")
        if not isinstance(payload, dict) or not isinstance(
            payload.get("results"), list
        ):

            def incomplete(category: str) -> SecurityCheck:
                return self._risk_incomplete(
                    root_id,
                    category,
                    ecosystem,
                    inputs,
                    "OSV-Scanner result omitted its result inventory",
                    scanner,
                )

            return incomplete("vulnerability"), incomplete("license")

        packages: list[Mapping[str, object]] = []
        malformed = False
        for result in payload["results"]:
            if not isinstance(result, dict) or not isinstance(
                result.get("packages"), list
            ):
                malformed = True
                continue
            for package in result["packages"]:
                if not isinstance(package, dict):
                    malformed = True
                    continue
                packages.append(package)
        if malformed:

            def incomplete(category: str) -> SecurityCheck:
                return self._risk_incomplete(
                    root_id,
                    category,
                    ecosystem,
                    inputs,
                    "OSV-Scanner returned a malformed package inventory",
                    scanner,
                )

            return incomplete("vulnerability"), incomplete("license")

        vulnerability_findings: list[Finding] = []
        license_findings: list[Finding] = []
        native_licenses, native_license_error = self._native_lock_licenses(raw)
        malformed = malformed or native_license_error is not None
        license_counts = {
            "permitted": 0,
            "scoped_permitted": 0,
            "scope_violation": 0,
            "prohibited": 0,
            "unknown": 0,
            "overridden": 0,
        }
        scoped_dispositions: set[str] = set()
        components: list[dict[str, object]] = []
        blocking_severities = self._blocking_severities()
        seen_packages: set[tuple[str, str]] = set()
        for row in packages:
            package = row.get("package")
            if not isinstance(package, dict):
                malformed = True
                continue
            name = package.get("name")
            version = package.get("version")
            if not isinstance(name, str) or not isinstance(version, str):
                malformed = True
                continue
            identity = (name, version)
            if identity in seen_packages:
                continue
            seen_packages.add(identity)
            vulnerabilities = row.get("vulnerabilities", [])
            if not isinstance(vulnerabilities, list):
                malformed = True
                continue
            for vulnerability in vulnerabilities:
                if not isinstance(vulnerability, dict) or not isinstance(
                    vulnerability.get("id"), str
                ):
                    malformed = True
                    continue
                severity = self._osv_severity(vulnerability)
                blocking = severity in blocking_severities or severity == "unknown"
                vulnerability_findings.append(
                    Finding(
                        "SEC-VULN-BLOCKING" if blocking else "SEC-VULN-NONBLOCKING",
                        str(
                            vulnerability.get("summary")
                            or "OSV advisory affects dependency"
                        ),
                        package=name,
                        version=version,
                        advisory=str(vulnerability["id"]),
                        severity=severity,
                    )
                )

            raw_licenses = row.get("licenses", [])
            licenses = native_licenses.get(identity)
            if licenses is None:
                licenses = (
                    [str(value) for value in raw_licenses if isinstance(value, str)]
                    if isinstance(raw_licenses, list)
                    else []
                )
            override = self._license_override(ecosystem, name, version)
            if override is not None:
                licenses = [override]
                license_counts["overridden"] += 1
            expression = " OR ".join(sorted(set(licenses))) if licenses else "unknown"
            classification, disposition_id = self._dependency_license_classification(
                root_id=root_id,
                dependency_root=raw,
                ecosystem=ecosystem,
                package=name,
                version=version,
                expression=expression,
            )
            classifications = [(classification, disposition_id, expression)]
            if disposition_id is not None:
                scoped_dispositions.add(disposition_id)
            package_classification = "permitted"
            if any(item[0] == "scope_violation" for item in classifications):
                package_classification = "scope_violation"
            elif any(item[0] == "prohibited" for item in classifications):
                package_classification = "prohibited"
            elif any(item[0] == "unknown" for item in classifications):
                package_classification = "unknown"
            elif any(item[0] == "scoped_permitted" for item in classifications):
                package_classification = "scoped_permitted"
            license_counts[package_classification] += 1
            components.append(
                self._license_component_evidence(
                    root_id=root_id,
                    dependency_root=raw,
                    ecosystem=ecosystem,
                    package=name,
                    version=version,
                    expression=expression,
                    classification=package_classification,
                    disposition_id=disposition_id,
                )
            )
            if package_classification not in ("permitted", "scoped_permitted"):
                expression = " OR ".join(sorted({item[2] for item in classifications}))
                code = {
                    "scope_violation": "SEC-LICENSE-SCOPE-VIOLATION",
                    "prohibited": "SEC-LICENSE-PROHIBITED",
                    "unknown": "SEC-LICENSE-UNKNOWN",
                }[package_classification]
                license_findings.append(
                    Finding(
                        code,
                        "OSV/deps.dev license metadata is not permitted by repository policy",
                        package=name,
                        version=version,
                        license=expression,
                    )
                )

        scanner = {
            **scanner,
            "retrieval": "completed",
            "packages_evaluated": len(seen_packages),
        }
        if malformed:
            vulnerability_findings.append(
                Finding(
                    "SEC-VULN-EVIDENCE-INCOMPLETE",
                    "OSV-Scanner package or advisory identity was incomplete",
                )
            )
            license_findings.append(
                Finding(
                    "SEC-LICENSE-INVENTORY-INCOMPLETE",
                    "OSV-Scanner package or license identity was incomplete",
                )
            )
        vulnerability_status = (
            "incomplete"
            if malformed
            else "failed"
            if any(
                finding.code == "SEC-VULN-BLOCKING"
                for finding in vulnerability_findings
            )
            else "passed"
        )
        license_status = (
            "incomplete" if malformed else "failed" if license_findings else "passed"
        )
        return (
            SecurityCheck(
                f"security.vulnerability.{root_id}",
                "vulnerability",
                vulnerability_status,
                inputs,
                ecosystem=ecosystem,
                findings=vulnerability_findings,
                scanner=scanner,
            ),
            SecurityCheck(
                f"security.license.{root_id}",
                "license",
                license_status,
                inputs,
                ecosystem=ecosystem,
                findings=license_findings,
                scanner={
                    **scanner,
                    "classifications": license_counts,
                    "scoped_dispositions": sorted(scoped_dispositions),
                    "components": components,
                },
            ),
        )

    @staticmethod
    def _network_bytes(
        url: str, *, payload: Mapping[str, object] | None = None
    ) -> tuple[bytes | None, str | None]:
        body = (
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if payload is not None
            else None
        )
        headers = {"User-Agent": "strling-security-evidence/1"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read(), None
        except (OSError, urllib.error.URLError) as exc:
            return None, str(exc)

    @staticmethod
    def _json_bytes(payload: bytes) -> tuple[Mapping[str, object] | None, str | None]:
        try:
            value = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return None, str(exc)
        if not isinstance(value, dict):
            return None, "response is not a JSON object"
        return value, None

    def _license_evidence_check(
        self,
        root_id: str,
        raw: Mapping[str, object],
        expected: set[tuple[str, str]],
        scanner: Mapping[str, object],
    ) -> SecurityCheck:
        ecosystem = str(raw.get("ecosystem", "unknown"))
        inputs = [
            *self._string_list(raw.get("manifests")),
            *self._string_list(raw.get("locks")),
        ]
        records, evidence_error = self._license_evidence_records(ecosystem)
        if evidence_error is not None:
            return self._risk_incomplete(
                root_id,
                "license",
                ecosystem,
                inputs,
                evidence_error,
                scanner,
            )
        if set(records) != expected:
            return self._risk_incomplete(
                root_id,
                "license",
                ecosystem,
                inputs,
                "hash-bound license evidence differs from the exact locked inventory",
                scanner,
            )
        findings: list[Finding] = []
        counts = {
            "permitted": 0,
            "scoped_permitted": 0,
            "scope_violation": 0,
            "prohibited": 0,
            "unknown": 0,
        }
        dispositions: set[str] = set()
        components: list[dict[str, object]] = []
        for package, version in sorted(expected):
            expression = records[(package, version)].get("license")
            classification, disposition = self._dependency_license_classification(
                root_id=root_id,
                dependency_root=raw,
                ecosystem=ecosystem,
                package=package,
                version=version,
                expression=expression,
            )
            counts[classification] += 1
            if disposition is not None:
                dispositions.add(disposition)
            components.append(
                self._license_component_evidence(
                    root_id=root_id,
                    dependency_root=raw,
                    ecosystem=ecosystem,
                    package=package,
                    version=version,
                    expression=expression,
                    classification=classification,
                    disposition_id=disposition,
                )
            )
            if classification not in ("permitted", "scoped_permitted"):
                code = {
                    "scope_violation": "SEC-LICENSE-SCOPE-VIOLATION",
                    "prohibited": "SEC-LICENSE-PROHIBITED",
                    "unknown": "SEC-LICENSE-UNKNOWN",
                }[classification]
                findings.append(
                    Finding(
                        code,
                        "primary package license evidence is not permitted by repository policy",
                        package=package,
                        version=version,
                        license=str(expression or "unknown"),
                    )
                )
        return SecurityCheck(
            f"security.license.{root_id}",
            "license",
            "failed" if findings else "passed",
            inputs,
            ecosystem=ecosystem,
            findings=findings,
            scanner={
                **scanner,
                "retrieval": "completed",
                "packages_evaluated": len(expected),
                "classifications": counts,
                "scoped_dispositions": sorted(dispositions),
                "components": components,
            },
        )

    def _audit_luarocks(
        self, root_id: str, raw: Mapping[str, object]
    ) -> tuple[SecurityCheck, SecurityCheck]:
        ecosystem = str(raw.get("ecosystem", "luarocks"))
        inputs = [
            *self._string_list(raw.get("manifests")),
            *self._string_list(raw.get("locks")),
        ]
        tools = self.policy.get("security_tools")
        configured = tools.get("luarocks-evidence") if isinstance(tools, dict) else None
        scanner: dict[str, object] = {
            "name": "LuaRocks primary-source and OSV commit evidence",
            "source": "luarocks.org, github.com/openresty/lua-cjson, api.osv.dev",
        }
        if not isinstance(configured, dict):
            unavailable = self._risk_unavailable(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "LuaRocks evidence policy is not configured",
                scanner,
            )
            return unavailable, self._risk_unavailable(
                root_id,
                "license",
                ecosystem,
                inputs,
                "LuaRocks evidence policy is not configured",
                scanner,
            )
        records, evidence_error = self._license_evidence_records(ecosystem)
        expected = {("lua-cjson", "2.1.0.10-1")}
        if evidence_error is not None or set(records) != expected:
            reason = evidence_error or "LuaRocks license evidence differs from the lock"
            incomplete = self._risk_incomplete(
                root_id, "vulnerability", ecosystem, inputs, reason, scanner
            )
            return incomplete, self._risk_incomplete(
                root_id, "license", ecosystem, inputs, reason, scanner
            )
        record = records[("lua-cjson", "2.1.0.10-1")]
        source_commit = configured.get("source_commit")
        rockspec_sha256 = configured.get("rockspec_sha256")
        if (
            record.get("source_commit") != source_commit
            or record.get("rockspec_sha256") != rockspec_sha256
            or record.get("registry_metadata_url") != configured.get("rockspec_url")
            or not isinstance(source_commit, str)
            or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
        ):
            reason = "LuaRocks lock, rockspec, source commit, and generated evidence disagree"
            incomplete = self._risk_incomplete(
                root_id, "vulnerability", ecosystem, inputs, reason, scanner
            )
            return incomplete, self._risk_incomplete(
                root_id, "license", ecosystem, inputs, reason, scanner
            )
        scanner.update(
            {
                "source_commit": source_commit,
                "rockspec_sha256": rockspec_sha256,
                "packages_evaluated": 1,
            }
        )
        query_url = configured.get("osv_query_url")
        if not isinstance(query_url, str):
            vulnerability = self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "LuaRocks OSV query endpoint is not pinned",
                scanner,
            )
        else:
            response, network_error = self._network_bytes(
                query_url, payload={"commit": source_commit}
            )
            if response is None:
                vulnerability = self._risk_unavailable(
                    root_id,
                    "vulnerability",
                    ecosystem,
                    inputs,
                    network_error or "OSV commit query failed",
                    scanner,
                )
            else:
                payload, payload_error = self._json_bytes(response)
                vulnerabilities = (
                    payload.get("vulns", []) if isinstance(payload, dict) else None
                )
                if payload_error is not None or not isinstance(vulnerabilities, list):
                    vulnerability = self._risk_incomplete(
                        root_id,
                        "vulnerability",
                        ecosystem,
                        inputs,
                        payload_error or "OSV commit result omitted vulnerabilities",
                        scanner,
                    )
                else:
                    findings: list[Finding] = []
                    malformed = False
                    for advisory in vulnerabilities:
                        if not isinstance(advisory, dict) or not isinstance(
                            advisory.get("id"), str
                        ):
                            malformed = True
                            continue
                        severity = self._osv_severity(advisory)
                        blocking = (
                            severity in self._blocking_severities()
                            or severity == "unknown"
                        )
                        findings.append(
                            Finding(
                                "SEC-VULN-BLOCKING"
                                if blocking
                                else "SEC-VULN-NONBLOCKING",
                                str(
                                    advisory.get("summary")
                                    or "OSV advisory affects source commit"
                                ),
                                package="lua-cjson",
                                version="2.1.0.10-1",
                                advisory=str(advisory["id"]),
                                severity=severity,
                            )
                        )
                    vulnerability = SecurityCheck(
                        f"security.vulnerability.{root_id}",
                        "vulnerability",
                        "incomplete"
                        if malformed
                        else "failed"
                        if any(item.code == "SEC-VULN-BLOCKING" for item in findings)
                        else "passed",
                        inputs,
                        ecosystem=ecosystem,
                        findings=findings,
                        scanner={**scanner, "retrieval": "completed"},
                    )
        license_check = self._license_evidence_check(root_id, raw, expected, scanner)
        return vulnerability, license_check

    def _audit_cpansa(
        self, root_id: str, raw: Mapping[str, object]
    ) -> tuple[SecurityCheck, SecurityCheck]:
        ecosystem = str(raw.get("ecosystem", "cpan"))
        inputs = [
            *self._string_list(raw.get("manifests")),
            *self._string_list(raw.get("locks")),
        ]
        tools = self.policy.get("security_tools")
        configured = tools.get("cpansa") if isinstance(tools, dict) else None
        scanner: dict[str, object] = {
            "name": "CPANSA exact locked-graph evaluator",
            "source": "cpan-security-advisory",
        }
        if not isinstance(configured, dict):
            reason = "CPANSA evidence policy is not configured"
            return (
                self._risk_unavailable(
                    root_id, "vulnerability", ecosystem, inputs, reason, scanner
                ),
                self._risk_unavailable(
                    root_id, "license", ecosystem, inputs, reason, scanner
                ),
            )
        locks = self._string_list(raw.get("locks"))
        if len(locks) != 1:
            reason = "CPANSA evaluation requires one exact Carton snapshot"
            return (
                self._risk_incomplete(
                    root_id, "vulnerability", ecosystem, inputs, reason, scanner
                ),
                self._risk_incomplete(
                    root_id, "license", ecosystem, inputs, reason, scanner
                ),
            )
        try:
            snapshot_text = (self.root / locks[0]).read_text(encoding="utf-8")
        except OSError as exc:
            reason = f"cannot read Carton snapshot: {exc}"
            return (
                self._risk_incomplete(
                    root_id, "vulnerability", ecosystem, inputs, reason, scanner
                ),
                self._risk_incomplete(
                    root_id, "license", ecosystem, inputs, reason, scanner
                ),
            )
        records, snapshot_error = self._parse_carton_snapshot(snapshot_text)
        core_modules, core_error = self._cpan_runtime_modules()
        if snapshot_error is not None or core_error is not None:
            reason = snapshot_error or core_error or "CPAN inventory is malformed"
            return (
                self._risk_incomplete(
                    root_id, "vulnerability", ecosystem, inputs, reason, scanner
                ),
                self._risk_incomplete(
                    root_id, "license", ecosystem, inputs, reason, scanner
                ),
            )
        external = {
            (str(record["package"]), str(record["version"]))
            for record in records.values()
        }
        license_check = self._license_evidence_check(root_id, raw, external, scanner)
        runtime = configured.get("certification_runtime")
        if not isinstance(runtime, dict):
            vulnerability = self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "CPANSA certification runtime is malformed",
                scanner,
            )
            return vulnerability, license_check
        inventory = {package: version for package, version in external}
        for module in core_modules.values():
            distribution = module["distribution"]
            version = (
                str(runtime.get("perl_version"))
                if distribution == "perl"
                else module["version"]
            )
            current = inventory.get(distribution)
            if current is not None and current != version:
                vulnerability = self._risk_incomplete(
                    root_id,
                    "vulnerability",
                    ecosystem,
                    inputs,
                    f"CPAN distribution {distribution} has conflicting selected versions",
                    scanner,
                )
                return vulnerability, license_check
            inventory[distribution] = version
        database_url = configured.get("database_url")
        database_sha256 = configured.get("database_sha256")
        if not isinstance(database_url, str) or not isinstance(database_sha256, str):
            vulnerability = self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "CPANSA database identity is not pinned",
                scanner,
            )
            return vulnerability, license_check
        database_bytes, database_error = self._network_bytes(database_url)
        if database_bytes is None:
            vulnerability = self._risk_unavailable(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                database_error or "CPANSA database retrieval failed",
                scanner,
            )
            return vulnerability, license_check
        actual_database_sha256 = hashlib.sha256(database_bytes).hexdigest()
        database, parse_error = self._json_bytes(database_bytes)
        metadata = database.get("meta") if isinstance(database, dict) else None
        distributions = database.get("dists") if isinstance(database, dict) else None
        if (
            actual_database_sha256 != database_sha256
            or parse_error is not None
            or not isinstance(metadata, dict)
            or metadata.get("commit") != configured.get("database_content_commit")
            or not isinstance(distributions, dict)
        ):
            vulnerability = self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                parse_error
                or "CPANSA database hash, content commit, or structure drifted",
                {**scanner, "database_sha256": actual_database_sha256},
            )
            return vulnerability, license_check
        corrections = configured.get("severity_corrections")
        correction_map: dict[str, Mapping[str, object]] = {}
        if not isinstance(corrections, list):
            corrections = []
        for correction in corrections:
            if not isinstance(correction, dict) or not isinstance(
                correction.get("advisory"), str
            ):
                vulnerability = self._risk_incomplete(
                    root_id,
                    "vulnerability",
                    ecosystem,
                    inputs,
                    "CPANSA severity correction is malformed",
                    scanner,
                )
                return vulnerability, license_check
            correction_map[str(correction["advisory"])] = correction
        validated_corrections: set[str] = set()
        findings: list[Finding] = []
        incomplete = False
        absent_distributions = 0
        for package, version in sorted(inventory.items()):
            distribution = distributions.get(package)
            if distribution is None:
                absent_distributions += 1
                continue
            advisories = (
                distribution.get("advisories")
                if isinstance(distribution, dict)
                else None
            )
            if not isinstance(advisories, list):
                incomplete = True
                continue
            for advisory in advisories:
                if not isinstance(advisory, dict) or not isinstance(
                    advisory.get("id"), str
                ):
                    incomplete = True
                    continue
                ranges = advisory.get("affected_versions")
                if not isinstance(ranges, list) or not all(
                    isinstance(item, str) for item in ranges
                ):
                    incomplete = True
                    continue
                applicability = [
                    self._cpan_range_contains(version, str(item)) for item in ranges
                ]
                if any(item is None for item in applicability):
                    incomplete = True
                    continue
                if not any(applicability):
                    continue
                advisory_id = str(advisory["id"])
                raw_severity = advisory.get("severity")
                severity = (
                    str(raw_severity).lower()
                    if isinstance(raw_severity, str) and raw_severity
                    else "unknown"
                )
                correction = correction_map.get(advisory_id)
                if correction is not None:
                    api_url = correction.get("source_api")
                    if not isinstance(api_url, str):
                        incomplete = True
                        continue
                    advisory_bytes, advisory_error = self._network_bytes(api_url)
                    if advisory_bytes is None:
                        vulnerability = self._risk_unavailable(
                            root_id,
                            "vulnerability",
                            ecosystem,
                            inputs,
                            advisory_error or "independent advisory retrieval failed",
                            scanner,
                        )
                        return vulnerability, license_check
                    independent, independent_error = self._json_bytes(advisory_bytes)
                    cvss = (
                        independent.get("cvss")
                        if isinstance(independent, dict)
                        else None
                    )
                    expected_ghsa = str(correction.get("source", "")).rsplit("/", 1)[-1]
                    cves = advisory.get("cves")
                    if (
                        independent_error is not None
                        or independent.get("ghsa_id") != expected_ghsa
                        or independent.get("cve_id") != correction.get("cve")
                        or not isinstance(cves, list)
                        or correction.get("cve") not in cves
                        or independent.get("severity") != correction.get("severity")
                        or not isinstance(cvss, dict)
                        or cvss.get("score") != correction.get("cvss_score")
                        or cvss.get("vector_string") != correction.get("cvss_vector")
                    ):
                        incomplete = True
                        continue
                    severity = str(correction["severity"])
                    validated_corrections.add(advisory_id)
                blocking = (
                    severity in self._blocking_severities() or severity == "unknown"
                )
                findings.append(
                    Finding(
                        "SEC-VULN-BLOCKING" if blocking else "SEC-VULN-NONBLOCKING",
                        str(
                            advisory.get("description")
                            or "CPANSA advisory affects dependency"
                        ),
                        package=package,
                        version=version,
                        advisory=advisory_id,
                        severity=severity,
                    )
                )
        scanner.update(
            {
                "retrieval": "completed",
                "database_commit": configured.get("database_commit"),
                "database_content_commit": configured.get("database_content_commit"),
                "database_sha256": actual_database_sha256,
                "certification_image": runtime.get("image"),
                "certification_image_digest": runtime.get("image_digest"),
                "distributions_evaluated": len(inventory),
                "distributions_without_advisory_records": absent_distributions,
                "severity_corrections": sorted(validated_corrections),
            }
        )
        if incomplete:
            findings.append(
                Finding(
                    "SEC-VULN-EVIDENCE-INCOMPLETE",
                    "CPANSA package, range, or independent severity evidence is incomplete",
                )
            )
        vulnerability = SecurityCheck(
            f"security.vulnerability.{root_id}",
            "vulnerability",
            "incomplete"
            if incomplete
            else "failed"
            if any(item.code == "SEC-VULN-BLOCKING" for item in findings)
            else "passed",
            inputs,
            ecosystem=ecosystem,
            findings=findings,
            scanner=scanner,
        )
        return vulnerability, license_check

    def _native_lock_licenses(
        self, raw: Mapping[str, object]
    ) -> tuple[dict[tuple[str, str], list[str]], str | None]:
        ecosystem = raw.get("ecosystem")
        if ecosystem not in ("composer", "dart-pub", "python", "r"):
            return {}, None
        if ecosystem == "python":
            license_policy = self.policy.get("license_policy")
            if not isinstance(license_policy, dict) or not isinstance(
                license_policy.get("evidence_manifest"), str
            ):
                return {}, None
        locks = self._string_list(raw.get("locks"))
        if ecosystem == "python" and (
            len(locks) != 1 or Path(locks[0]).name != "requirements.lock.txt"
        ):
            return {}, None
        if len(locks) != 1:
            return {}, f"{ecosystem} license evidence requires exactly one lockfile"
        if ecosystem == "dart-pub":
            try:
                lock = yaml.safe_load(
                    (self.root / locks[0]).read_text(encoding="utf-8")
                )
            except (OSError, yaml.YAMLError) as exc:
                return {}, f"cannot parse Dart lock for license evidence: {exc}"
            packages = lock.get("packages") if isinstance(lock, dict) else None
            if not isinstance(packages, dict) or not packages:
                return {}, "Dart lock omitted its package inventory"
            evidence, evidence_error = self._license_evidence_records("dart-pub")
            if evidence_error is not None:
                return {}, evidence_error
            result: dict[tuple[str, str], list[str]] = {}
            expected_identities: set[tuple[str, str]] = set()
            for package_name, package in packages.items():
                if not isinstance(package_name, str) or not isinstance(package, dict):
                    return {}, "Dart lock contains a malformed package record"
                version = package.get("version")
                description = package.get("description")
                if (
                    package.get("source") != "hosted"
                    or not isinstance(version, str)
                    or not isinstance(description, dict)
                    or not isinstance(description.get("sha256"), str)
                ):
                    return {}, "Dart lock package integrity identity is incomplete"
                identity = (package_name, version)
                expected_identities.add(identity)
                record = evidence.get(identity)
                if (
                    record is None
                    or record.get("archive_sha256") != description["sha256"]
                    or not isinstance(record.get("license"), str)
                ):
                    return (
                        {},
                        f"Dart license evidence does not match {package_name}@{version}",
                    )
                result[identity] = [str(record["license"])]
            if set(evidence) != expected_identities:
                return {}, "Dart license evidence inventory differs from pubspec.lock"
            return result, None

        if ecosystem == "python":
            try:
                content = (self.root / locks[0]).read_text(encoding="utf-8")
            except OSError as exc:
                return {}, f"cannot read Python lock for license evidence: {exc}"
            package_rows = list(
                re.finditer(
                    r"(?m)^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\;]+)\s*\\?\s*$",
                    content,
                )
            )
            locked: dict[tuple[str, str], set[str]] = {}
            for index, matched in enumerate(package_rows):
                identity = (
                    matched.group(1).lower().replace("_", "-"),
                    matched.group(2),
                )
                end = (
                    package_rows[index + 1].start()
                    if index + 1 < len(package_rows)
                    else len(content)
                )
                locked[identity] = set(
                    re.findall(
                        r"--hash=sha256:([0-9a-f]{64})", content[matched.end() : end]
                    )
                )
            evidence, evidence_error = self._license_evidence_records("python")
            if evidence_error is not None:
                return {}, evidence_error
            result: dict[tuple[str, str], list[str]] = {}
            for identity, record in evidence.items():
                archive_sha256 = record.get("archive_sha256")
                license_expression = record.get("license")
                if (
                    identity not in locked
                    or archive_sha256 not in locked[identity]
                    or not isinstance(license_expression, str)
                ):
                    return (
                        {},
                        f"Python license evidence does not match {identity[0]}@{identity[1]}",
                    )
                result[identity] = [license_expression]
            return result, None

        lock, findings = self._read_json_object(
            locks[0], "SEC-LICENSE-INVENTORY-INCOMPLETE"
        )
        if lock is None:
            return {}, findings[
                0
            ].message if findings else f"cannot read {ecosystem} lock"
        if ecosystem == "r":
            packages = lock.get("Packages")
            if not isinstance(packages, dict) or not packages:
                return {}, "renv lock omitted its package inventory"
            result: dict[tuple[str, str], list[str]] = {}
            for package_key, package in packages.items():
                if not isinstance(package, dict):
                    return {}, "renv lock contains a malformed package record"
                name = package.get("Package")
                version = package.get("Version")
                license_expression = package.get("License")
                if (
                    not isinstance(package_key, str)
                    or not isinstance(name, str)
                    or package_key != name
                    or not isinstance(version, str)
                    or not isinstance(license_expression, str)
                    or not license_expression.strip()
                ):
                    return {}, "renv lock package license identity is incomplete"
                normalized = {
                    "MIT + file LICENSE": "MIT",
                    "GPL-2 | GPL-3": "GPL-2.0-only OR GPL-3.0-only",
                }.get(license_expression, license_expression)
                result[(name, version)] = [normalized]
            return result, None

        result: dict[tuple[str, str], list[str]] = {}
        for section in ("packages", "packages-dev"):
            packages = lock.get(section)
            if not isinstance(packages, list):
                return {}, f"Composer lock omitted {section}"
            for package in packages:
                if not isinstance(package, dict):
                    return {}, f"Composer lock contains a malformed {section} package"
                name = package.get("name")
                version = package.get("version")
                licenses = package.get("license")
                if (
                    not isinstance(name, str)
                    or not isinstance(version, str)
                    or not isinstance(licenses, list)
                    or not licenses
                    or any(not isinstance(value, str) for value in licenses)
                ):
                    return {}, "Composer lock package license identity is incomplete"
                result[(name, version)] = [str(value) for value in licenses]
        return result, None

    def _license_evidence_records(
        self, ecosystem: str
    ) -> tuple[dict[tuple[str, str], Mapping[str, object]], str | None]:
        policy = self.policy.get("license_policy")
        evidence_path = (
            policy.get("evidence_manifest") if isinstance(policy, dict) else None
        )
        if not isinstance(evidence_path, str):
            return {}, "license evidence manifest is not configured"
        evidence, findings = self._read_json_object(
            evidence_path, "SEC-LICENSE-INVENTORY-INCOMPLETE"
        )
        if evidence is None:
            return {}, findings[
                0
            ].message if findings else "cannot read license evidence"
        fingerprint = evidence.get("fingerprint")
        normalized = {
            key: value for key, value in evidence.items() if key != "fingerprint"
        }
        actual_fingerprint = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(
                    normalized,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
        )
        entries = evidence.get("entries")
        if (
            evidence.get("document_kind") != "dependency-license-evidence"
            or evidence.get("schema_version") != "1.0.0"
            or fingerprint != actual_fingerprint
            or not isinstance(entries, list)
        ):
            return {}, "license evidence manifest is malformed or has fingerprint drift"
        records: dict[tuple[str, str], Mapping[str, object]] = {}
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("ecosystem") != ecosystem:
                continue
            package = entry.get("package")
            version = entry.get("version")
            archive_sha256 = entry.get("archive_sha256")
            license_expression = entry.get("license")
            license_sha256 = entry.get("license_sha256")
            identity = (str(package), str(version))
            if (
                not isinstance(package, str)
                or not isinstance(version, str)
                or not isinstance(archive_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", archive_sha256) is None
                or not isinstance(license_expression, str)
                or not license_expression
                or not isinstance(license_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", license_sha256) is None
                or identity in records
            ):
                return {}, "license evidence entry identity or hashes are malformed"
            records[identity] = entry
        if not records:
            return {}, f"license evidence has no records for {ecosystem}"
        return records, None

    def _audit_cargo(self, root_id: str, raw: Mapping[str, object]) -> SecurityCheck:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        inputs = [*manifests, *locks]
        ecosystem = str(raw.get("ecosystem", "cargo"))
        expected_version = self._security_tool_version("cargo-audit")
        if len(manifests) != 1 or len(locks) != 1 or expected_version is None:
            return self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "cargo audit requires one manifest, one lockfile, and a pinned scanner",
                {"name": "cargo-audit"},
            )
        cwd = (self.root / manifests[0]).parent
        version_result, version_error = self._invoke(
            ["cargo", "audit", "--version"], cwd
        )
        if version_result is None or version_result.returncode != 0:
            reason = (
                version_error
                or version_result.stderr.strip()
                or "cargo-audit unavailable"
            )
            return self._risk_unavailable(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                reason,
                {"name": "cargo-audit", "version": expected_version},
            )
        match = re.search(r"(\d+\.\d+\.\d+)", version_result.stdout)
        actual_version = match.group(1) if match else "unknown"
        scanner = {
            "name": "cargo-audit",
            "version": actual_version,
            "expected_version": expected_version,
            "source": "rustsec",
        }
        if actual_version != expected_version:
            return SecurityCheck(
                f"security.vulnerability.{root_id}",
                "vulnerability",
                "failed",
                inputs,
                ecosystem=ecosystem,
                findings=[
                    Finding(
                        "SEC-TOOL-VERSION-DRIFT",
                        f"cargo-audit {actual_version} does not match {expected_version}",
                    )
                ],
                scanner=scanner,
            )
        audit_result, audit_error = self._invoke(
            ["cargo", "audit", "--json", "--file", locks[0]], self.root
        )
        if audit_result is None:
            return self._risk_unavailable(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                audit_error or "cargo-audit unavailable",
                scanner,
            )
        try:
            payload = json.loads(audit_result.stdout)
        except json.JSONDecodeError as exc:
            reason = audit_result.stderr.strip()
            unavailable_markers = ("network", "fetch", "resolve host", "database")
            if audit_result.returncode != 0 and any(
                marker in reason.lower() for marker in unavailable_markers
            ):
                return self._risk_unavailable(
                    root_id,
                    "vulnerability",
                    ecosystem,
                    inputs,
                    reason,
                    scanner,
                )
            return self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                f"cargo-audit did not return JSON: {exc}",
                scanner,
            )
        if not isinstance(payload, dict):
            return self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "cargo-audit result must be an object",
                scanner,
            )
        vulnerability_data = payload.get("vulnerabilities")
        if not isinstance(vulnerability_data, dict) or not isinstance(
            vulnerability_data.get("list"), list
        ):
            return self._risk_incomplete(
                root_id,
                "vulnerability",
                ecosystem,
                inputs,
                "cargo-audit result omitted vulnerability inventory",
                scanner,
            )
        findings: list[Finding] = []
        incomplete = False
        blocking_severities = self._blocking_severities()
        for entry in vulnerability_data["list"]:
            if not isinstance(entry, dict):
                incomplete = True
                continue
            package = entry.get("package")
            advisory = entry.get("advisory")
            if not isinstance(package, dict) or not isinstance(advisory, dict):
                incomplete = True
                continue
            name = package.get("name")
            version = package.get("version")
            identifier = advisory.get("id")
            if not all(
                isinstance(value, str) and value
                for value in (name, version, identifier)
            ):
                incomplete = True
                continue
            severity = str(advisory.get("severity") or "unknown").lower()
            blocking = severity in blocking_severities or severity == "unknown"
            findings.append(
                Finding(
                    "SEC-VULN-BLOCKING" if blocking else "SEC-VULN-NONBLOCKING",
                    str(
                        advisory.get("title")
                        or "RustSec advisory affects locked dependency"
                    ),
                    package=name,
                    version=version,
                    advisory=identifier,
                    severity=severity,
                )
            )
        if incomplete:
            findings.append(
                Finding(
                    "SEC-VULN-EVIDENCE-INCOMPLETE",
                    "cargo-audit evidence omitted required package/version/advisory fields",
                )
            )
            return SecurityCheck(
                f"security.vulnerability.{root_id}",
                "vulnerability",
                "incomplete",
                inputs,
                ecosystem=ecosystem,
                findings=findings,
                scanner=scanner,
            )
        status = (
            "failed"
            if any(finding.code == "SEC-VULN-BLOCKING" for finding in findings)
            else "passed"
        )
        return SecurityCheck(
            f"security.vulnerability.{root_id}",
            "vulnerability",
            status,
            inputs,
            ecosystem=ecosystem,
            findings=findings,
            scanner={**scanner, "retrieval": "completed"},
        )

    def _license_npm(self, root_id: str, raw: Mapping[str, object]) -> SecurityCheck:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        inputs = [*manifests, *locks]
        ecosystem = str(raw.get("ecosystem", "npm"))
        if len(locks) != 1:
            return self._risk_incomplete(
                root_id,
                "license",
                ecosystem,
                inputs,
                "npm license check requires exactly one lockfile",
                {"name": ENGINE_NAME, "version": self.engine_version},
            )
        lock, lock_findings = self._read_json_object(
            locks[0], "SEC-LICENSE-INVENTORY-INCOMPLETE"
        )
        packages = lock.get("packages") if lock else None
        if not isinstance(packages, dict):
            return SecurityCheck(
                f"security.license.{root_id}",
                "license",
                "incomplete",
                inputs,
                ecosystem=ecosystem,
                findings=lock_findings
                or [
                    Finding(
                        "SEC-LICENSE-INVENTORY-INCOMPLETE",
                        "npm lockfile omitted package inventory",
                    )
                ],
            )
        findings: list[Finding] = []
        counts = {
            "permitted": 0,
            "scoped_permitted": 0,
            "scope_violation": 0,
            "prohibited": 0,
            "unknown": 0,
            "overridden": 0,
        }
        scoped_dispositions: set[str] = set()
        components: list[dict[str, object]] = []
        evaluated = 0
        incomplete = False
        for package_path, package_data in sorted(packages.items()):
            if not package_path or not isinstance(package_data, dict):
                continue
            if package_data.get("link") is True:
                continue
            package_name = self._npm_package_name(str(package_path))
            version = package_data.get("version")
            if package_name is None:
                continue
            if not isinstance(version, str):
                incomplete = True
                continue
            evaluated += 1
            expression = package_data.get("license")
            override = self._license_override(ecosystem, package_name, version)
            if not isinstance(expression, str) and override is not None:
                expression = override
                counts["overridden"] += 1
            classification, disposition_id = self._dependency_license_classification(
                root_id=root_id,
                dependency_root=raw,
                ecosystem=ecosystem,
                package=package_name,
                version=version,
                expression=expression,
            )
            counts[classification] += 1
            if disposition_id is not None:
                scoped_dispositions.add(disposition_id)
            components.append(
                self._license_component_evidence(
                    root_id=root_id,
                    dependency_root=raw,
                    ecosystem=ecosystem,
                    package=package_name,
                    version=version,
                    expression=expression,
                    classification=classification,
                    disposition_id=disposition_id,
                )
            )
            if classification == "prohibited":
                findings.append(
                    Finding(
                        "SEC-LICENSE-PROHIBITED",
                        "dependency license is prohibited by repository policy",
                        package=package_name,
                        version=version,
                        license=str(expression),
                    )
                )
            elif classification == "unknown":
                findings.append(
                    Finding(
                        "SEC-LICENSE-UNKNOWN",
                        "dependency license is unknown or unclassified",
                        package=package_name,
                        version=version,
                        license=str(expression or "unknown"),
                    )
                )
            elif classification == "scope_violation":
                findings.append(
                    Finding(
                        "SEC-LICENSE-SCOPE-VIOLATION",
                        "dependency matches an exact scoped license disposition but is reachable from an unauthorized dependency root or usage",
                        package=package_name,
                        version=version,
                        license=str(expression),
                    )
                )
        scanner = {
            "name": ENGINE_NAME,
            "version": self.engine_version,
            "packages_evaluated": evaluated,
            "classifications": counts,
            "scoped_dispositions": sorted(scoped_dispositions),
            "components": components,
        }
        if incomplete:
            findings.append(
                Finding(
                    "SEC-LICENSE-INVENTORY-INCOMPLETE",
                    "npm package identity or version was incomplete",
                )
            )
            status = "incomplete"
        else:
            status = "failed" if findings else "passed"
        return SecurityCheck(
            f"security.license.{root_id}",
            "license",
            status,
            inputs,
            ecosystem=ecosystem,
            findings=findings,
            scanner=scanner,
        )

    def _license_cargo(self, root_id: str, raw: Mapping[str, object]) -> SecurityCheck:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        inputs = [*manifests, *locks]
        ecosystem = str(raw.get("ecosystem", "cargo"))
        if len(manifests) != 1 or len(locks) != 1:
            return self._risk_incomplete(
                root_id,
                "license",
                ecosystem,
                inputs,
                "Cargo license check requires one manifest and one lockfile",
                {"name": "cargo metadata"},
            )
        result, error = self._invoke(
            [
                "cargo",
                "metadata",
                "--locked",
                "--offline",
                "--format-version=1",
                "--manifest-path",
                manifests[0],
            ],
            self.root,
        )
        scanner = {"name": "cargo metadata", "network": "offline"}
        if result is None or result.returncode != 0:
            reason = error or result.stderr.strip() or "cargo metadata unavailable"
            return self._risk_unavailable(
                root_id, "license", ecosystem, inputs, reason, scanner
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return self._risk_incomplete(
                root_id,
                "license",
                ecosystem,
                inputs,
                f"cargo metadata did not return JSON: {exc}",
                scanner,
            )
        packages = payload.get("packages") if isinstance(payload, dict) else None
        if not isinstance(packages, list):
            return self._risk_incomplete(
                root_id,
                "license",
                ecosystem,
                inputs,
                "cargo metadata omitted package inventory",
                scanner,
            )
        reachable_ids, resolve_root, reachability_error = (
            self._cargo_reachable_package_ids(payload)
        )
        if reachability_error is not None or reachable_ids is None:
            return self._risk_incomplete(
                root_id,
                "license",
                ecosystem,
                inputs,
                reachability_error
                or "cargo metadata omitted the selected-root dependency graph",
                scanner,
            )
        package_by_id = {
            str(package["id"]): package
            for package in packages
            if isinstance(package, dict) and isinstance(package.get("id"), str)
        }
        missing_ids = sorted(reachable_ids - package_by_id.keys())
        if missing_ids:
            return self._risk_incomplete(
                root_id,
                "license",
                ecosystem,
                inputs,
                "cargo metadata dependency graph references packages absent from its inventory",
                scanner,
            )
        findings: list[Finding] = []
        counts = {
            "permitted": 0,
            "scoped_permitted": 0,
            "scope_violation": 0,
            "prohibited": 0,
            "unknown": 0,
            "overridden": 0,
        }
        scoped_dispositions: set[str] = set()
        components: list[dict[str, object]] = []
        evaluated = 0
        incomplete = False
        for package_id in sorted(reachable_ids):
            package = package_by_id[package_id]
            if package.get("source") is None:
                continue
            name = package.get("name")
            version = package.get("version")
            if not isinstance(name, str) or not isinstance(version, str):
                incomplete = True
                continue
            evaluated += 1
            expression = package.get("license")
            override = self._license_override(ecosystem, name, version)
            if not isinstance(expression, str) and override is not None:
                expression = override
                counts["overridden"] += 1
            classification, disposition_id = self._dependency_license_classification(
                root_id=root_id,
                dependency_root=raw,
                ecosystem=ecosystem,
                package=name,
                version=version,
                expression=expression,
            )
            counts[classification] += 1
            if disposition_id is not None:
                scoped_dispositions.add(disposition_id)
            components.append(
                self._license_component_evidence(
                    root_id=root_id,
                    dependency_root=raw,
                    ecosystem=ecosystem,
                    package=name,
                    version=version,
                    expression=expression,
                    classification=classification,
                    disposition_id=disposition_id,
                )
            )
            if classification == "prohibited":
                findings.append(
                    Finding(
                        "SEC-LICENSE-PROHIBITED",
                        "dependency license is prohibited by repository policy",
                        package=name,
                        version=version,
                        license=str(expression),
                    )
                )
            elif classification == "unknown":
                findings.append(
                    Finding(
                        "SEC-LICENSE-UNKNOWN",
                        "dependency license is unknown or unclassified",
                        package=name,
                        version=version,
                        license=str(expression or "unknown"),
                    )
                )
            elif classification == "scope_violation":
                findings.append(
                    Finding(
                        "SEC-LICENSE-SCOPE-VIOLATION",
                        "dependency matches an exact scoped license disposition but is reachable from an unauthorized dependency root or usage",
                        package=name,
                        version=version,
                        license=str(expression),
                    )
                )
        scanner = {
            **scanner,
            "package_scope": "selected-root-reachable",
            "resolve_root": resolve_root,
            "workspace_packages_total": len(packages),
            "reachable_packages_total": len(reachable_ids),
            "workspace_packages_excluded": len(packages) - len(reachable_ids),
            "packages_evaluated": evaluated,
            "classifications": counts,
            "scoped_dispositions": sorted(scoped_dispositions),
            "components": components,
        }
        if incomplete:
            findings.append(
                Finding(
                    "SEC-LICENSE-INVENTORY-INCOMPLETE",
                    "Cargo package identity or version was incomplete",
                )
            )
            status = "incomplete"
        else:
            status = "failed" if findings else "passed"
        return SecurityCheck(
            f"security.license.{root_id}",
            "license",
            status,
            inputs,
            ecosystem=ecosystem,
            findings=findings,
            scanner=scanner,
        )

    def _risk_unavailable(
        self,
        root_id: str,
        category: str,
        ecosystem: str,
        inputs: list[str],
        reason: str,
        scanner: dict[str, object],
    ) -> SecurityCheck:
        return SecurityCheck(
            f"security.{category}.{root_id}",
            category,
            "unavailable",
            inputs,
            ecosystem=ecosystem,
            unavailable_reason=reason,
            scanner=scanner,
        )

    def _risk_incomplete(
        self,
        root_id: str,
        category: str,
        ecosystem: str,
        inputs: list[str],
        message: str,
        scanner: dict[str, object],
    ) -> SecurityCheck:
        code = (
            "SEC-VULN-EVIDENCE-INCOMPLETE"
            if category == "vulnerability"
            else "SEC-LICENSE-INVENTORY-INCOMPLETE"
        )
        return SecurityCheck(
            f"security.{category}.{root_id}",
            category,
            "incomplete",
            inputs,
            ecosystem=ecosystem,
            findings=[Finding(code, message)],
            scanner=scanner,
        )

    def _blocking_severities(self) -> set[str]:
        policy = self.policy.get("vulnerability_policy")
        if not isinstance(policy, dict):
            return set()
        return {
            str(value).lower()
            for value in self._string_list(policy.get("blocking_severities"))
        }

    def _security_tool_version(self, name: str) -> str | None:
        tools = self.policy.get("security_tools")
        if not isinstance(tools, dict):
            return None
        tool = tools.get(name)
        if not isinstance(tool, dict):
            return None
        version = tool.get("version")
        return version if isinstance(version, str) else None

    def _security_tool_executable(self, name: str) -> str | None:
        tools = self.policy.get("security_tools")
        if not isinstance(tools, dict):
            return None
        tool = tools.get(name)
        if not isinstance(tool, dict):
            return None
        variable = tool.get("executable_environment_variable")
        declared = os.environ.get(variable) if isinstance(variable, str) else None
        candidate = declared or shutil.which(name)
        if candidate is None:
            return None
        resolved = Path(candidate).resolve()
        return str(resolved) if resolved.is_file() else None

    def _security_tool_sha256(self, name: str) -> str | None:
        tools = self.policy.get("security_tools")
        if not isinstance(tools, dict):
            return None
        tool = tools.get(name)
        if not isinstance(tool, dict):
            return None
        hashes = tool.get("sha256")
        if not isinstance(hashes, dict):
            return None
        machine = platform.machine().lower()
        architecture = "amd64" if machine in ("amd64", "x86_64") else machine
        operating_system = "windows" if sys.platform == "win32" else "linux"
        expected = hashes.get(f"{operating_system}_{architecture}")
        return str(expected) if isinstance(expected, str) else None

    def _security_tool_string_list(self, name: str, field: str) -> list[str]:
        tools = self.policy.get("security_tools")
        if not isinstance(tools, dict):
            return []
        tool = tools.get(name)
        if not isinstance(tool, dict):
            return []
        return self._string_list(tool.get(field))

    @staticmethod
    def _osv_severity(vulnerability: Mapping[str, object]) -> str:
        database_specific = vulnerability.get("database_specific")
        if isinstance(database_specific, dict):
            severity = database_specific.get("severity")
            if isinstance(severity, str) and severity:
                return severity.lower()
        severity = vulnerability.get("severity")
        if isinstance(severity, str) and severity:
            return severity.lower()
        return "unknown"

    @staticmethod
    def _osv_supported_input(relative: str) -> bool:
        name = Path(relative).name.lower()
        return (
            name
            in {
                "cargo.lock",
                "composer.lock",
                "gemfile.lock",
                "go.mod",
                "gradle.lockfile",
                "packages.lock.json",
                "pom.xml",
                "pubspec.lock",
                "renv.lock",
                "requirements.lock.txt",
            }
            or name.startswith("requirements")
            and name.endswith(".txt")
            or Path(name).suffix in (".csproj", ".fsproj")
        )

    def _license_classification(self, expression: object) -> str:
        if not isinstance(expression, str) or not expression.strip():
            return "unknown"
        policy = self.policy.get("license_policy")
        if not isinstance(policy, dict):
            return "unknown"
        if expression in self._string_list(policy.get("prohibited")):
            return "prohibited"
        if expression in self._string_list(policy.get("permitted")):
            return "permitted"
        branches = self._top_level_or_branches(expression)
        if len(branches) > 1:
            classifications = [
                self._license_classification(branch) for branch in branches
            ]
            if "permitted" in classifications:
                return "permitted"
            if all(
                classification == "prohibited" for classification in classifications
            ):
                return "prohibited"
        return "unknown"

    @staticmethod
    def _top_level_or_branches(expression: str) -> list[str]:
        stripped = expression.strip()
        if stripped.startswith("(") and stripped.endswith(")"):
            depth = 0
            encloses_all = True
            for index, character in enumerate(stripped):
                if character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
                    if depth == 0 and index != len(stripped) - 1:
                        encloses_all = False
                        break
            if encloses_all and depth == 0:
                stripped = stripped[1:-1].strip()
        branches: list[str] = []
        depth = 0
        start = 0
        for matched in re.finditer(r"\(|\)|\s+OR\s+", stripped):
            token = matched.group(0)
            if token == "(":
                depth += 1
            elif token == ")":
                depth -= 1
            elif depth == 0:
                branches.append(stripped[start : matched.start()].strip())
                start = matched.end()
        if branches:
            branches.append(stripped[start:].strip())
        return [branch for branch in branches if branch]

    def _dependency_license_classification(
        self,
        *,
        root_id: str,
        dependency_root: Mapping[str, object],
        ecosystem: str,
        package: str,
        version: str,
        expression: object,
    ) -> tuple[str, str | None]:
        disposition = self._scoped_license_disposition(
            root_id, ecosystem, package, version, expression
        )
        if disposition is None:
            return self._license_classification(expression), None
        disposition_id = str(disposition["id"])
        allowed_roots = self._string_list(disposition.get("dependency_roots"))
        usage = str(dependency_root.get("usage", "unknown"))
        reachability = disposition.get("reachability_evidence")
        if (
            root_id in allowed_roots
            and usage == disposition.get("required_usage")
            and (
                reachability is None
                or self._license_reachability_matches(
                    dependency_root, disposition, reachability
                )
            )
            and self._license_material_matches(disposition)
        ):
            return "scoped_permitted", disposition_id
        return "scope_violation", disposition_id

    def _license_component_evidence(
        self,
        *,
        root_id: str,
        dependency_root: Mapping[str, object],
        ecosystem: str,
        package: str,
        version: str,
        expression: object,
        classification: str,
        disposition_id: str | None,
    ) -> dict[str, object]:
        disposition = self._scoped_license_disposition(
            root_id, ecosystem, package, version, expression
        )
        selected = (
            disposition.get("selected_license") if disposition is not None else None
        )
        reachability = (
            disposition.get("reachability_evidence")
            if disposition is not None
            else None
        )
        reachability_kind = (
            reachability.get("kind") if isinstance(reachability, dict) else None
        )
        non_distributed = reachability_kind in {
            "maven-direct-scope",
            "gradle-lock-configurations",
            "renv-development-path",
        }
        return {
            "name": package,
            "version": version,
            "reported_license": str(expression or "unknown"),
            "selected_license": str(selected) if isinstance(selected, str) else None,
            "classification": classification,
            "disposition_id": disposition_id,
            "distribution_scope": (
                "non-distributed-build-test"
                if non_distributed
                else "distributed-runtime"
                if dependency_root.get("usage") == "runtime"
                else "non-distributed-tooling"
            ),
        }

    def _scoped_license_disposition(
        self,
        root_id: str,
        ecosystem: str,
        package: str,
        version: str,
        expression: object,
    ) -> Mapping[str, object] | None:
        if not isinstance(expression, str):
            return None
        policy = self.policy.get("license_policy")
        if not isinstance(policy, dict):
            return None
        dispositions = policy.get("scoped_permitted", [])
        if not isinstance(dispositions, list):
            return None
        candidates: list[Mapping[str, object]] = []
        for disposition in dispositions:
            if not isinstance(disposition, dict):
                continue
            if (
                disposition.get("ecosystem") == ecosystem
                and disposition.get("package") == package
                and disposition.get("version") == version
                and disposition.get("license") == expression
                and isinstance(disposition.get("id"), str)
            ):
                candidates.append(disposition)
        for disposition in candidates:
            if root_id in self._string_list(disposition.get("dependency_roots")):
                return disposition
        return candidates[0] if candidates else None

    def _license_reachability_matches(
        self,
        dependency_root: Mapping[str, object],
        disposition: Mapping[str, object],
        raw_evidence: object,
    ) -> bool:
        if not isinstance(raw_evidence, dict):
            return False
        kind = raw_evidence.get("kind")
        if kind == "maven-direct-scope":
            return self._maven_disposition_reachability(
                dependency_root, disposition, raw_evidence
            )
        if kind == "gradle-lock-configurations":
            return self._gradle_disposition_reachability(
                dependency_root, disposition, raw_evidence
            )
        if kind == "renv-development-path":
            return self._renv_disposition_reachability(
                dependency_root, disposition, raw_evidence
            )
        if kind == "cpan-runtime-closure":
            return self._cpan_disposition_reachability(
                dependency_root, disposition, raw_evidence
            )
        return False

    def _license_material_matches(self, disposition: Mapping[str, object]) -> bool:
        selected = disposition.get("selected_license")
        material = disposition.get("license_material")
        if selected is None and material is None:
            return True
        expression = disposition.get("license")
        if (
            not isinstance(selected, str)
            or not isinstance(expression, str)
            or selected not in self._top_level_or_branches(expression)
            or not isinstance(material, dict)
        ):
            return False
        manifest = material.get("manifest")
        if not isinstance(manifest, str):
            return False
        try:
            payload = json.loads((self.root / manifest).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return False
        matches = [
            row
            for row in entries
            if isinstance(row, dict)
            and row.get("ecosystem") == disposition.get("ecosystem")
            and row.get("package") == disposition.get("package")
            and row.get("version") == disposition.get("version")
            and row.get("license") == expression
        ]
        if len(matches) != 1:
            return False
        row = matches[0]
        return all(
            row.get(field) == material.get(field)
            for field in (
                "archive_url",
                "archive_sha256",
                "license_path",
                "license_sha256",
            )
        )

    def _cpan_disposition_reachability(
        self,
        dependency_root: Mapping[str, object],
        disposition: Mapping[str, object],
        evidence: Mapping[str, object],
    ) -> bool:
        manifests = self._string_list(dependency_root.get("manifests"))
        locks = self._string_list(dependency_root.get("locks"))
        manifest = evidence.get("manifest")
        lock = evidence.get("lock")
        release_manifest = evidence.get("release_manifest")
        release_surface = evidence.get("release_surface")
        path = evidence.get("path")
        if (
            dependency_root.get("ecosystem") != "cpan"
            or dependency_root.get("id") != "perl-cpan"
            or not isinstance(manifest, str)
            or manifest not in manifests
            or not isinstance(lock, str)
            or locks != [lock]
            or not isinstance(release_manifest, str)
            or not isinstance(release_surface, str)
            or not isinstance(path, list)
            or not path
            or not all(isinstance(item, dict) for item in path)
        ):
            return False
        try:
            cpanfile = (self.root / manifest).read_text(encoding="utf-8")
            snapshot = (self.root / lock).read_text(encoding="utf-8")
            release = json.loads(
                (self.root / release_manifest).read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return False
        records, error = self._parse_carton_snapshot(snapshot)
        if error is not None:
            return False
        identities: list[tuple[str, str]] = []
        selected_records: list[Mapping[str, object]] = []
        for item in path:
            package = item.get("package")
            version = item.get("version")
            if not isinstance(package, str) or not isinstance(version, str):
                return False
            record = next(
                (
                    row
                    for row in records.values()
                    if row.get("package") == package and row.get("version") == version
                ),
                None,
            )
            if record is None:
                return False
            identities.append((package, version))
            selected_records.append(record)
        if identities[-1] != (
            disposition.get("package"),
            disposition.get("version"),
        ):
            return False
        first_provides = selected_records[0].get("provides")
        if not isinstance(first_provides, dict) or not any(
            re.search(
                rf"(?m)^\s*requires\s+['\"]{re.escape(module)}['\"]\s*,",
                cpanfile,
            )
            for module in first_provides
        ):
            return False
        for source, target in zip(selected_records, selected_records[1:]):
            requirements = source.get("requirements")
            provides = target.get("provides")
            if (
                not isinstance(requirements, dict)
                or not isinstance(provides, dict)
                or not set(requirements).intersection(provides)
            ):
                return False
        artifacts = release.get("artifacts") if isinstance(release, dict) else None
        if not isinstance(artifacts, list):
            return False
        reachable_surfaces = [
            row.get("id")
            for row in artifacts
            if isinstance(row, dict)
            and dependency_root.get("id")
            in self._string_list(row.get("dependency_roots"))
        ]
        return reachable_surfaces == [release_surface]

    def _maven_disposition_reachability(
        self,
        dependency_root: Mapping[str, object],
        disposition: Mapping[str, object],
        evidence: Mapping[str, object],
    ) -> bool:
        manifests = self._string_list(dependency_root.get("manifests"))
        manifest = evidence.get("manifest")
        if (
            dependency_root.get("ecosystem") != "maven"
            or not isinstance(manifest, str)
            or manifests != [manifest]
            or evidence.get("scope") != "test"
        ):
            return False
        try:
            project = ET.parse(self.root / manifest).getroot()
        except (OSError, ET.ParseError):
            return False
        namespace = ""
        if project.tag.startswith("{"):
            namespace = project.tag.split("}", 1)[0] + "}"
        properties: dict[str, str] = {}
        raw_properties = project.find(f"{namespace}properties")
        if raw_properties is not None:
            for child in raw_properties:
                name = child.tag.rsplit("}", 1)[-1]
                if child.text is not None:
                    properties[name] = child.text.strip()

        def resolve(value: str) -> str:
            matched = re.fullmatch(r"\$\{([^}]+)\}", value)
            return properties.get(matched.group(1), value) if matched else value

        expected_package = disposition.get("package")
        expected_version = disposition.get("version")
        dependencies = project.find(f"{namespace}dependencies")
        if dependencies is None:
            return False
        for dependency in dependencies.findall(f"{namespace}dependency"):
            group = dependency.findtext(f"{namespace}groupId")
            artifact = dependency.findtext(f"{namespace}artifactId")
            version = dependency.findtext(f"{namespace}version")
            scope = dependency.findtext(f"{namespace}scope", default="compile")
            if not all(isinstance(item, str) for item in (group, artifact, version)):
                continue
            if (
                f"{group.strip()}:{artifact.strip()}" == expected_package
                and resolve(version.strip()) == expected_version
                and scope.strip() == "test"
            ):
                return True
        return False

    def _gradle_disposition_reachability(
        self,
        dependency_root: Mapping[str, object],
        disposition: Mapping[str, object],
        evidence: Mapping[str, object],
    ) -> bool:
        lock = evidence.get("lock")
        expected_configurations = evidence.get("configurations")
        if (
            dependency_root.get("ecosystem") != "gradle"
            or not isinstance(lock, str)
            or lock not in self._string_list(dependency_root.get("locks"))
            or not isinstance(expected_configurations, list)
            or not expected_configurations
            or not all(isinstance(item, str) for item in expected_configurations)
        ):
            return False
        coordinate = f"{disposition.get('package')}:{disposition.get('version')}="
        try:
            lines = (self.root / lock).read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        matches = [line for line in lines if line.startswith(coordinate)]
        if len(matches) != 1:
            return False
        actual = matches[0].split("=", 1)[1].split(",")
        return actual == expected_configurations

    def _renv_disposition_reachability(
        self,
        dependency_root: Mapping[str, object],
        disposition: Mapping[str, object],
        evidence: Mapping[str, object],
    ) -> bool:
        manifests = self._string_list(dependency_root.get("manifests"))
        locks = self._string_list(dependency_root.get("locks"))
        manifest = evidence.get("manifest")
        lock = evidence.get("lock")
        path = evidence.get("path")
        if (
            dependency_root.get("ecosystem") != "r"
            or not isinstance(manifest, str)
            or not isinstance(lock, str)
            or manifests != [manifest]
            or locks != [lock]
            or not isinstance(path, list)
            or len(path) < 2
            or not all(isinstance(item, dict) for item in path)
        ):
            return False
        try:
            description = (self.root / manifest).read_text(encoding="utf-8")
            lock_payload = json.loads((self.root / lock).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        packages = (
            lock_payload.get("Packages") if isinstance(lock_payload, dict) else None
        )
        if not isinstance(packages, dict):
            return False
        suggests_match = re.search(
            r"(?ms)^Suggests:\s*(.+?)(?=^[A-Za-z][A-Za-z0-9/]*:|\Z)",
            description,
        )
        suggests = (
            {
                item
                for item in re.findall(
                    r"(?:^|,)\s*([A-Za-z][A-Za-z0-9.]*)",
                    suggests_match.group(1),
                )
            }
            if suggests_match is not None
            else set()
        )
        identities: list[tuple[str, str]] = []
        for item in path:
            package = item.get("package")
            version = item.get("version")
            if not isinstance(package, str) or not isinstance(version, str):
                return False
            record = packages.get(package)
            if (
                not isinstance(record, dict)
                or record.get("Package") != package
                or record.get("Version") != version
            ):
                return False
            identities.append((package, version))
        if identities[0][0] not in suggests:
            return False
        if identities[-1] != (
            disposition.get("package"),
            disposition.get("version"),
        ):
            return False
        for (source, _), (target, _) in zip(identities, identities[1:]):
            record = packages[source]
            imports = record.get("Imports") if isinstance(record, dict) else None
            if not isinstance(imports, list):
                return False
            imported = {
                matched.group(1)
                for item in imports
                if isinstance(item, str)
                and (matched := re.match(r"^([A-Za-z][A-Za-z0-9.]*)", item))
            }
            if target not in imported:
                return False
        return True

    @staticmethod
    def _cargo_reachable_package_ids(
        payload: Mapping[str, object],
    ) -> tuple[set[str] | None, str | None, str | None]:
        resolve = payload.get("resolve")
        if not isinstance(resolve, dict):
            return None, None, "cargo metadata omitted its resolved dependency graph"
        root = resolve.get("root")
        nodes = resolve.get("nodes")
        if not isinstance(root, str) or not isinstance(nodes, list):
            return (
                None,
                None,
                "cargo metadata omitted the selected package root or resolve nodes",
            )
        node_by_id: dict[str, Mapping[str, object]] = {}
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get("id"), str):
                return None, root, "cargo metadata contains a malformed resolve node"
            node_by_id[str(node["id"])] = node
        if root not in node_by_id:
            return (
                None,
                root,
                "cargo metadata selected root is absent from resolve nodes",
            )
        reachable: set[str] = set()
        pending = [root]
        while pending:
            package_id = pending.pop()
            if package_id in reachable:
                continue
            node = node_by_id.get(package_id)
            if node is None:
                return (
                    None,
                    root,
                    "cargo metadata dependency is absent from resolve nodes",
                )
            reachable.add(package_id)
            dependencies = node.get("deps")
            if not isinstance(dependencies, list):
                return None, root, "cargo metadata resolve node omitted dependencies"
            for dependency in dependencies:
                if not isinstance(dependency, dict) or not isinstance(
                    dependency.get("pkg"), str
                ):
                    return (
                        None,
                        root,
                        "cargo metadata contains a malformed dependency edge",
                    )
                pending.append(str(dependency["pkg"]))
        return reachable, root, None

    def _license_override(
        self, ecosystem: str, package: str, version: str
    ) -> str | None:
        policy = self.policy.get("license_policy")
        if not isinstance(policy, dict):
            return None
        overrides = policy.get("metadata_overrides", [])
        if not isinstance(overrides, list):
            return None
        for override in overrides:
            if not isinstance(override, dict):
                continue
            if (
                override.get("ecosystem") == ecosystem
                and override.get("package") == package
                and override.get("version") == version
                and isinstance(override.get("license"), str)
            ):
                return str(override["license"])
        return None

    @staticmethod
    def _npm_range_contains(version: str, expression: str) -> bool | None:
        parsed_version = SecurityEngine._npm_semver(version)
        if parsed_version is None:
            return None
        for alternative in expression.split("||"):
            candidate = alternative.strip()
            if candidate in ("", "*"):
                return True
            hyphen = re.fullmatch(r"(\S+)\s+-\s+(\S+)", candidate)
            if hyphen:
                lower = SecurityEngine._npm_semver(hyphen.group(1))
                upper = SecurityEngine._npm_semver(hyphen.group(2))
                if lower is None or upper is None:
                    return None
                if lower <= parsed_version <= upper:
                    return True
                continue
            tokens = candidate.split()
            if not tokens:
                return None
            matched = True
            for token in tokens:
                match = re.fullmatch(r"(<=|>=|<|>|=)?(.+)", token)
                if not match:
                    return None
                operator = match.group(1) or "="
                boundary = SecurityEngine._npm_semver(match.group(2))
                if boundary is None:
                    return None
                comparisons = {
                    "<": parsed_version < boundary,
                    "<=": parsed_version <= boundary,
                    ">": parsed_version > boundary,
                    ">=": parsed_version >= boundary,
                    "=": parsed_version == boundary,
                }
                matched = matched and comparisons[operator]
            if matched:
                return True
        return False

    @staticmethod
    def _npm_semver(value: str) -> tuple[int, int, int, int, str] | None:
        match = re.fullmatch(
            r"v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?",
            value.strip(),
        )
        if not match:
            return None
        prerelease = match.group(4)
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            1 if prerelease is None else 0,
            prerelease or "",
        )

    @staticmethod
    def _npm_package_name(package_path: str) -> str | None:
        marker = "node_modules/"
        if marker not in package_path:
            return None
        return package_path.rsplit(marker, 1)[1]

    def _check_engine_pin(self) -> SecurityCheck:
        configured = self.policy.get("engine")
        expected = configured.get("version") if isinstance(configured, dict) else None
        findings: list[Finding] = []
        if expected != self.engine_version:
            findings.append(
                Finding(
                    "SEC-TOOL-VERSION-DRIFT",
                    f"security engine {self.engine_version} does not match policy pin {expected!r}",
                    path="governance/security-policy.json",
                )
            )
        return self._finding_check(
            "security.tool-version",
            "dependency_integrity",
            ["governance/security-policy.json", "tooling/security.py"],
            findings,
            scanner={"name": ENGINE_NAME, "version": self.engine_version},
        )

    def _check_dependency_inventory(self) -> SecurityCheck:
        known = {
            path
            for raw in self.policy.get("dependency_roots", [])
            if isinstance(raw, dict)
            for field_name in ("manifests", "locks")
            for path in raw.get(field_name, [])
            if isinstance(path, str)
        }
        candidates = {
            path for path in self._tracked_files if self._is_dependency_file(path)
        }
        unmanaged = sorted(candidates - known)
        findings = [
            Finding(
                "SEC-DEP-UNMANAGED-MANIFEST",
                "tracked dependency manifest or lockfile is outside the governed inventory",
                path=path,
            )
            for path in unmanaged
        ]
        return self._finding_check(
            "security.dependency-inventory",
            "dependency_integrity",
            sorted(candidates),
            findings,
        )

    def _is_dependency_file(self, path: str) -> bool:
        name = Path(path).name
        names = self.policy.get("manifest_names", [])
        suffixes = self.policy.get("manifest_suffixes", [])
        known_lock_names = {
            "package-lock.json",
            "Cargo.lock",
            "pubspec.lock",
            "composer.lock",
            "Gemfile.lock",
            "go.sum",
            "Package.resolved",
            "packages.lock.json",
            "requirements.lock.txt",
            "gradle.lockfile",
            "verification-metadata.xml",
            "renv.lock",
            "luarocks.lock",
            "cpanfile.snapshot",
        }
        return (
            name in names
            or name in known_lock_names
            or (name.startswith("requirements") and name.endswith(".txt"))
            or any(name.endswith(suffix) for suffix in suffixes)
        )

    def _check_dependency_root(self, raw: Mapping[str, object]) -> SecurityCheck:
        identifier = str(raw.get("id", "invalid"))
        ecosystem = str(raw.get("ecosystem", "unknown"))
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        inputs = manifests + locks
        findings: list[Finding] = []

        for path in manifests:
            if not (self.root / path).is_file():
                findings.append(
                    Finding(
                        "SEC-DEP-MANIFEST-MISSING",
                        "governed dependency manifest is missing",
                        path=path,
                    )
                )
        if raw.get("lock_policy") == "required":
            if not locks:
                findings.append(
                    Finding(
                        "SEC-DEP-LOCK-POLICY",
                        "required-lock policy declares no lock path",
                    )
                )
            for path in locks:
                if not (self.root / path).is_file():
                    findings.append(
                        Finding(
                            "SEC-DEP-LOCK-MISSING",
                            "required dependency lockfile is missing",
                            path=path,
                        )
                    )

        if not findings:
            mode = raw.get("integrity_mode")
            validators = {
                "npm_lock_v3": self._validate_npm,
                "cargo_lock": self._validate_cargo,
                "presence_and_parse": self._validate_presence_and_parse,
                "composer_lock": self._validate_composer,
                "no_external_dependencies": self._validate_no_external_dependencies,
                "direct_pins": self._validate_direct_pins,
                "exact_requirements": self._validate_exact_requirements,
                "hash_pinned_requirements": self._validate_hash_pinned_requirements,
                "gradle_lock": self._validate_gradle_lock,
                "renv_lock": self._validate_renv_lock,
                "luarocks_lock": self._validate_luarocks_lock,
                "carton_snapshot": self._validate_carton_snapshot,
                "inventory_only": lambda _raw: [],
            }
            validator = validators.get(mode)
            if validator is None:
                findings.append(
                    Finding(
                        "SEC-DEP-INTEGRITY-MODE",
                        f"unknown dependency integrity mode {mode!r}",
                    )
                )
            else:
                findings.extend(validator(raw))

        return self._finding_check(
            f"security.dependency.{identifier}",
            "dependency_integrity",
            inputs,
            findings,
            ecosystem=ecosystem,
        )

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]

    def _validate_npm(self, raw: Mapping[str, object]) -> list[Finding]:
        manifest_path = self._string_list(raw.get("manifests"))[0]
        lock_path = self._string_list(raw.get("locks"))[0]
        manifest = self._read_json_object(manifest_path, "SEC-DEP-MANIFEST-MALFORMED")
        lock = self._read_json_object(lock_path, "SEC-DEP-LOCK-MALFORMED")
        findings = [*manifest[1], *lock[1]]
        if findings:
            return findings
        manifest_data = manifest[0]
        lock_data = lock[0]
        assert manifest_data is not None and lock_data is not None
        if lock_data.get("lockfileVersion") != 3:
            findings.append(
                Finding(
                    "SEC-DEP-LOCK-VERSION",
                    "npm lockfileVersion must be 3",
                    path=lock_path,
                )
            )
        packages = lock_data.get("packages")
        if not isinstance(packages, dict) or not isinstance(packages.get(""), dict):
            return findings + [
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    "npm lockfile must contain packages['']",
                    path=lock_path,
                )
            ]
        root_package = packages[""]
        for section in (
            "dependencies",
            "devDependencies",
            "optionalDependencies",
            "peerDependencies",
        ):
            manifest_dependencies = manifest_data.get(section, {})
            lock_dependencies = root_package.get(section, {})
            if manifest_dependencies != lock_dependencies:
                findings.append(
                    Finding(
                        "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                        f"npm {section} differs between manifest and lock root",
                        path=lock_path,
                    )
                )
            if isinstance(manifest_dependencies, dict):
                findings.extend(
                    self._floating_specifier_findings(
                        manifest_dependencies, manifest_path
                    )
                )
        require_integrity = self._dependency_rule("require_npm_integrity")
        for package_path, package in sorted(packages.items()):
            if not package_path or not isinstance(package, dict) or package.get("link"):
                continue
            resolved = package.get("resolved")
            if isinstance(resolved, str) and resolved.startswith("http://"):
                findings.append(
                    Finding(
                        "SEC-DEP-INSECURE-SOURCE",
                        "npm resolved source must use HTTPS",
                        path=lock_path,
                        package=package_path.removeprefix("node_modules/"),
                        version=str(package.get("version", "")),
                    )
                )
            if (
                require_integrity
                and isinstance(resolved, str)
                and resolved.startswith(("http://", "https://"))
                and not isinstance(package.get("integrity"), str)
            ):
                findings.append(
                    Finding(
                        "SEC-DEP-INTEGRITY-MISSING",
                        "resolved npm package lacks integrity metadata",
                        path=lock_path,
                        package=package_path.removeprefix("node_modules/"),
                        version=str(package.get("version", "")),
                    )
                )
        return findings

    def _validate_cargo(self, raw: Mapping[str, object]) -> list[Finding]:
        manifest_path = self._string_list(raw.get("manifests"))[0]
        lock_path = self._string_list(raw.get("locks"))[0]
        manifest = self._read_toml_object(manifest_path, "SEC-DEP-MANIFEST-MALFORMED")
        lock = self._read_toml_object(lock_path, "SEC-DEP-LOCK-MALFORMED")
        findings = [*manifest[1], *lock[1]]
        if findings:
            return findings
        manifest_data = manifest[0]
        lock_data = lock[0]
        assert manifest_data is not None and lock_data is not None
        if lock_data.get("version") not in (3, 4):
            findings.append(
                Finding(
                    "SEC-DEP-LOCK-VERSION",
                    "Cargo lockfile version must be 3 or 4",
                    path=lock_path,
                )
            )
        packages = lock_data.get("package")
        if not isinstance(packages, list):
            return findings + [
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    "Cargo lockfile package inventory is missing",
                    path=lock_path,
                )
            ]
        locked_names = {
            package.get("name") for package in packages if isinstance(package, dict)
        }
        for section in ("dependencies", "dev-dependencies", "build-dependencies"):
            dependencies = manifest_data.get(section, {})
            if isinstance(dependencies, dict):
                for name in dependencies:
                    if name not in locked_names:
                        findings.append(
                            Finding(
                                "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                                "Cargo dependency is absent from Cargo.lock",
                                path=lock_path,
                                package=name,
                            )
                        )
        if self._dependency_rule("require_cargo_checksums"):
            for package in packages:
                if not isinstance(package, dict):
                    continue
                source = package.get("source")
                if (
                    isinstance(source, str)
                    and source.startswith("registry+")
                    and not isinstance(package.get("checksum"), str)
                ):
                    findings.append(
                        Finding(
                            "SEC-DEP-INTEGRITY-MISSING",
                            "registry Cargo package lacks a checksum",
                            path=lock_path,
                            package=str(package.get("name", "")),
                            version=str(package.get("version", "")),
                        )
                    )
        return findings

    def _validate_presence_and_parse(self, raw: Mapping[str, object]) -> list[Finding]:
        ecosystem = raw.get("ecosystem")
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        findings: list[Finding] = []
        if ecosystem == "dart-pub":
            for path in manifests + locks:
                try:
                    value = yaml.safe_load(
                        (self.root / path).read_text(encoding="utf-8")
                    )
                except (OSError, yaml.YAMLError) as exc:
                    findings.append(
                        Finding(
                            "SEC-DEP-LOCK-MALFORMED"
                            if path in locks
                            else "SEC-DEP-MANIFEST-MALFORMED",
                            f"cannot parse YAML dependency file: {exc}",
                            path=path,
                        )
                    )
                else:
                    if not isinstance(value, dict):
                        findings.append(
                            Finding(
                                "SEC-DEP-LOCK-MALFORMED"
                                if path in locks
                                else "SEC-DEP-MANIFEST-MALFORMED",
                                "YAML dependency file must contain a mapping",
                                path=path,
                            )
                        )
        elif ecosystem == "bundler":
            lock_path = locks[0]
            try:
                content = (self.root / lock_path).read_text(encoding="utf-8")
            except OSError as exc:
                findings.append(
                    Finding(
                        "SEC-DEP-LOCK-MALFORMED",
                        f"cannot read Bundler lockfile: {exc}",
                        path=lock_path,
                    )
                )
            else:
                if "GEM\n" not in content or "BUNDLED WITH\n" not in content:
                    findings.append(
                        Finding(
                            "SEC-DEP-LOCK-MALFORMED",
                            "Bundler lockfile lacks required sections",
                            path=lock_path,
                        )
                    )
        else:
            findings.append(
                Finding(
                    "SEC-DEP-INTEGRITY-MODE",
                    f"presence-and-parse has no validator for {ecosystem!r}",
                )
            )
        return findings

    def _validate_composer(self, raw: Mapping[str, object]) -> list[Finding]:
        manifest_path = self._string_list(raw.get("manifests"))[0]
        lock_path = self._string_list(raw.get("locks"))[0]
        manifest = self._read_json_object(manifest_path, "SEC-DEP-MANIFEST-MALFORMED")
        lock = self._read_json_object(lock_path, "SEC-DEP-LOCK-MALFORMED")
        findings = [*manifest[1], *lock[1]]
        if findings:
            return findings
        lock_data = lock[0]
        assert lock_data is not None
        if not isinstance(lock_data.get("content-hash"), str):
            findings.append(
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    "Composer lockfile lacks content-hash",
                    path=lock_path,
                )
            )
        for section in ("packages", "packages-dev"):
            if not isinstance(lock_data.get(section), list):
                findings.append(
                    Finding(
                        "SEC-DEP-LOCK-MALFORMED",
                        f"Composer lockfile lacks {section}",
                        path=lock_path,
                    )
                )
        return findings

    def _validate_no_external_dependencies(
        self, raw: Mapping[str, object]
    ) -> list[Finding]:
        manifest_path = self._string_list(raw.get("manifests"))[0]
        try:
            content = (self.root / manifest_path).read_text(encoding="utf-8")
        except OSError as exc:
            return [
                Finding(
                    "SEC-DEP-MANIFEST-MALFORMED",
                    f"cannot read dependency manifest: {exc}",
                    path=manifest_path,
                )
            ]
        ecosystem = raw.get("ecosystem")
        if ecosystem == "go":
            has_external = bool(re.search(r"(?m)^\s*require\s*(?:\(|\S)", content))
        elif ecosystem == "swiftpm":
            has_external = ".package(" in content
        elif ecosystem == "nuget":
            try:
                root = ET.fromstring(content)
            except ET.ParseError as exc:
                return [
                    Finding(
                        "SEC-DEP-MANIFEST-MALFORMED",
                        f"cannot parse NuGet project manifest: {exc}",
                        path=manifest_path,
                    )
                ]
            has_external = any(
                element.tag.rsplit("}", 1)[-1] == "PackageReference"
                for element in root.iter()
            )
        else:
            return [
                Finding(
                    "SEC-DEP-INTEGRITY-MODE",
                    f"no-external-dependencies has no validator for {ecosystem!r}",
                )
            ]
        if has_external:
            return [
                Finding(
                    "SEC-DEP-UNLOCKED-EXTERNAL",
                    "manifest declares external dependencies while policy declares none",
                    path=manifest_path,
                )
            ]
        return []

    def _validate_direct_pins(self, raw: Mapping[str, object]) -> list[Finding]:
        manifest_path = self._string_list(raw.get("manifests"))[0]
        try:
            content = (self.root / manifest_path).read_text(encoding="utf-8")
        except OSError as exc:
            return [
                Finding(
                    "SEC-DEP-MANIFEST-MALFORMED",
                    f"cannot read dependency manifest: {exc}",
                    path=manifest_path,
                )
            ]
        ecosystem = raw.get("ecosystem")
        if ecosystem == "maven":
            return self._validate_maven_pins(manifest_path, content)
        if ecosystem == "gradle":
            return self._validate_gradle_pins(manifest_path, content)
        return [
            Finding(
                "SEC-DEP-INTEGRITY-MODE",
                f"direct-pins has no validator for {ecosystem!r}",
            )
        ]

    def _validate_maven_pins(self, path: str, content: str) -> list[Finding]:
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            return [
                Finding(
                    "SEC-DEP-MANIFEST-MALFORMED",
                    f"cannot parse Maven manifest: {exc}",
                    path=path,
                )
            ]
        properties = {
            child.tag.rsplit("}", 1)[-1]: (child.text or "").strip()
            for properties_node in root.findall(".//{*}properties")
            for child in properties_node
        }
        findings: list[Finding] = []
        for dependency in root.findall(".//{*}dependency"):
            artifact = dependency.findtext("{*}artifactId") or "unknown"
            version = (dependency.findtext("{*}version") or "").strip()
            if version.startswith("${") and version.endswith("}"):
                version = properties.get(version[2:-1], "")
            if not version or self._is_floating(version):
                findings.append(
                    Finding(
                        "SEC-DEP-FLOATING",
                        "Maven dependency must declare a fixed direct version",
                        path=path,
                        package=artifact,
                        version=version,
                    )
                )
        return findings

    def _validate_gradle_pins(self, path: str, content: str) -> list[Finding]:
        findings: list[Finding] = []
        coordinates = re.findall(
            r"(?:implementation|api|testImplementation|compileOnly|runtimeOnly)\(\s*[\"']([^\"']+)[\"']",
            content,
        )
        for coordinate in coordinates:
            parts = coordinate.split(":")
            version = parts[2] if len(parts) >= 3 else ""
            if not version or self._is_floating(version):
                findings.append(
                    Finding(
                        "SEC-DEP-FLOATING",
                        "Gradle dependency must declare a fixed direct version",
                        path=path,
                        package=":".join(parts[:2]),
                        version=version,
                    )
                )
        for plugin, version in re.findall(
            r"id\(\s*[\"']([^\"']+)[\"']\s*\)\s*version\s*[\"']([^\"']+)[\"']",
            content,
        ):
            if self._is_floating(version):
                findings.append(
                    Finding(
                        "SEC-DEP-FLOATING",
                        "Gradle plugin must declare a fixed version",
                        path=path,
                        package=plugin,
                        version=version,
                    )
                )
        return findings

    def _validate_exact_requirements(self, raw: Mapping[str, object]) -> list[Finding]:
        findings: list[Finding] = []
        for path in self._string_list(raw.get("manifests")):
            try:
                lines = (self.root / path).read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                findings.append(
                    Finding(
                        "SEC-DEP-MANIFEST-MALFORMED",
                        f"cannot read requirements file: {exc}",
                        path=path,
                    )
                )
                continue
            for line_number, line in enumerate(lines, start=1):
                value = line.strip()
                if not value or value.startswith("#"):
                    continue
                if not re.fullmatch(
                    r"[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9_,.-]+\])?==[^\s;]+",
                    value,
                ):
                    findings.append(
                        Finding(
                            "SEC-DEP-FLOATING",
                            "governed quality requirement must use one exact == pin",
                            path=path,
                            line=line_number,
                        )
                    )
        return findings

    def _validate_hash_pinned_requirements(
        self, raw: Mapping[str, object]
    ) -> list[Finding]:
        locks = self._string_list(raw.get("locks"))
        if len(locks) != 1:
            return [
                Finding(
                    "SEC-DEP-LOCK-POLICY",
                    "hash-pinned Python requirements require exactly one lockfile",
                )
            ]
        lock_path = locks[0]
        try:
            content = (self.root / lock_path).read_text(encoding="utf-8")
        except OSError as exc:
            return [
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    f"cannot read hash-pinned requirements lock: {exc}",
                    path=lock_path,
                )
            ]
        package_rows = list(
            re.finditer(
                r"(?m)^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\;]+)\s*\\?\s*$",
                content,
            )
        )
        findings: list[Finding] = []
        if not package_rows:
            findings.append(
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    "hash-pinned requirements lock has no exact package rows",
                    path=lock_path,
                )
            )
            return findings
        locked_names: set[str] = set()
        for index, matched in enumerate(package_rows):
            package = matched.group(1)
            locked_names.add(package.lower().replace("_", "-"))
            end = (
                package_rows[index + 1].start()
                if index + 1 < len(package_rows)
                else len(content)
            )
            block = content[matched.end() : end]
            if not re.search(r"--hash=sha256:[0-9a-f]{64}", block):
                findings.append(
                    Finding(
                        "SEC-DEP-INTEGRITY-MISSING",
                        "locked Python package lacks a SHA-256 distribution hash",
                        path=lock_path,
                        package=package,
                        version=matched.group(2),
                    )
                )
        for manifest_path in self._string_list(raw.get("manifests")):
            if Path(manifest_path).name == "pyproject.toml":
                continue
            try:
                manifest = (self.root / manifest_path).read_text(encoding="utf-8")
            except OSError:
                continue
            for matched in re.finditer(
                r"(?m)^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:[<>=!~].*)?$", manifest
            ):
                package = matched.group(1)
                if package.lower().replace("_", "-") not in locked_names:
                    findings.append(
                        Finding(
                            "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                            "declared Python dependency is absent from the governed lock",
                            path=manifest_path,
                            package=package,
                        )
                    )
        return findings

    @staticmethod
    def _cpan_version(value: str) -> tuple[int, ...] | None:
        normalized = value.strip().removeprefix("v")
        if re.fullmatch(r"\d+(?:[._]\d+)*", normalized) is None:
            return None
        if normalized.startswith("5.") and normalized.count(".") == 1:
            major, fractional = normalized.split(".", 1)
            if len(fractional) >= 3 and len(fractional) % 3 == 0:
                return (int(major),) + tuple(
                    int(fractional[index : index + 3])
                    for index in range(0, len(fractional), 3)
                )
        return tuple(int(part) for part in re.split(r"[._]", normalized))

    @classmethod
    def _cpan_version_compare(cls, left: str, right: str) -> int | None:
        left_value = cls._cpan_version(left)
        right_value = cls._cpan_version(right)
        if left_value is None or right_value is None:
            return None
        width = max(len(left_value), len(right_value))
        padded_left = left_value + (0,) * (width - len(left_value))
        padded_right = right_value + (0,) * (width - len(right_value))
        return (padded_left > padded_right) - (padded_left < padded_right)

    @classmethod
    def _cpan_range_contains(cls, version: str, expression: str) -> bool | None:
        predicates = [item.strip() for item in expression.split(",") if item.strip()]
        if not predicates:
            return None
        for predicate in predicates:
            matched = re.fullmatch(
                r"(>=|<=|==|!=|>|<)?\s*(v?\d+(?:[._]\d+)*)", predicate
            )
            if matched is None:
                return None
            operator = matched.group(1) or ">="
            comparison = cls._cpan_version_compare(version, matched.group(2))
            if comparison is None:
                return None
            accepted = {
                ">=": comparison >= 0,
                "<=": comparison <= 0,
                "==": comparison == 0,
                "!=": comparison != 0,
                ">": comparison > 0,
                "<": comparison < 0,
            }[operator]
            if not accepted:
                return False
        return True

    @staticmethod
    def _parse_carton_snapshot(
        content: str,
    ) -> tuple[dict[str, dict[str, object]], str | None]:
        if not content.startswith(
            "# carton snapshot format: version 1.0\nDISTRIBUTIONS\n"
        ):
            return {}, "Carton snapshot format is not version 1.0"
        blocks = list(
            re.finditer(
                r"(?ms)^  ([A-Za-z0-9._-]+)\n(.*?)(?=^  [A-Za-z0-9._-]+\n|\Z)",
                content,
            )
        )
        if not blocks:
            return {}, "Carton snapshot has no distributions"
        records: dict[str, dict[str, object]] = {}
        for block in blocks:
            identity = block.group(1)
            matched_identity = re.fullmatch(r"(.+)-([0-9][A-Za-z0-9._]*)", identity)
            if matched_identity is None or identity in records:
                return {}, f"Carton distribution identity is malformed: {identity}"
            package, version = matched_identity.groups()
            pathname_match = re.search(
                r"(?m)^    pathname: ([A-Z0-9]/[A-Z0-9]{2}/[A-Z0-9._-]+/([A-Za-z0-9._-]+)\.tar\.gz)$",
                block.group(2),
            )
            if pathname_match is None or pathname_match.group(2) != identity:
                return {}, f"Carton pathname does not match {identity}"
            provides: dict[str, str] = {}
            requirements: dict[str, str] = {}
            section: dict[str, str] | None = None
            for line in block.group(2).splitlines():
                if line == "    provides:":
                    section = provides
                    continue
                if line == "    requirements:":
                    section = requirements
                    continue
                if line.startswith("    ") and not line.startswith("      "):
                    section = None
                    continue
                if line.startswith("      "):
                    if section is None or " " not in line.strip():
                        return {}, f"Carton module record is malformed in {identity}"
                    module, module_version = line.strip().rsplit(" ", 1)
                    if module in section:
                        return (
                            {},
                            f"Carton module is duplicated in {identity}: {module}",
                        )
                    section[module] = module_version
            if not provides:
                return {}, f"Carton distribution has no provided modules: {identity}"
            records[identity] = {
                "package": package,
                "version": version,
                "pathname": pathname_match.group(1),
                "provides": provides,
                "requirements": requirements,
            }
        return records, None

    def _cpan_runtime_modules(
        self,
    ) -> tuple[dict[str, dict[str, str]], str | None]:
        tools = self.policy.get("security_tools")
        cpansa = tools.get("cpansa") if isinstance(tools, dict) else None
        runtime = (
            cpansa.get("certification_runtime") if isinstance(cpansa, dict) else None
        )
        modules = runtime.get("core_modules") if isinstance(runtime, dict) else None
        if not isinstance(modules, list) or not modules:
            return {}, "CPANSA certification runtime has no core-module inventory"
        result: dict[str, dict[str, str]] = {}
        for row in modules:
            if not isinstance(row, dict):
                return {}, "CPANSA core-module record is malformed"
            module = row.get("module")
            version = row.get("version")
            distribution = row.get("distribution")
            if (
                not isinstance(module, str)
                or not isinstance(version, str)
                or self._cpan_version(version) is None
                or not isinstance(distribution, str)
                or not distribution
                or module in result
            ):
                return {}, "CPANSA core-module identity is malformed or duplicated"
            result[module] = {"version": version, "distribution": distribution}
        perl_version = (
            runtime.get("perl_version") if isinstance(runtime, dict) else None
        )
        if (
            not isinstance(perl_version, str)
            or result.get("perl", {}).get("version") != perl_version
        ):
            return {}, "CPANSA Perl runtime and module inventory disagree"
        return result, None

    def _validate_luarocks_lock(self, raw: Mapping[str, object]) -> list[Finding]:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        if len(manifests) != 1 or len(locks) != 1:
            return [
                Finding(
                    "SEC-DEP-LOCK-POLICY",
                    "LuaRocks integrity requires one rockspec and one lockfile",
                )
            ]
        try:
            rockspec = (self.root / manifests[0]).read_text(encoding="utf-8")
            lock = (self.root / locks[0]).read_text(encoding="utf-8")
        except OSError as exc:
            return [
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    f"cannot read LuaRocks dependency evidence: {exc}",
                    path=locks[0],
                )
            ]
        locked = re.findall(
            r'^\s*\["([A-Za-z0-9._-]+)"\]\s*=\s*"([0-9][A-Za-z0-9._-]*)"\s*,?\s*$',
            lock,
            re.MULTILINE,
        )
        declared = re.findall(
            r'^\s*"([A-Za-z0-9._-]+)\s+([^"\n]+)",?\s*$',
            rockspec,
            re.MULTILINE,
        )
        external = [
            (name, expression) for name, expression in declared if name != "lua"
        ]
        findings: list[Finding] = []
        if len(locked) != 1 or len(external) != 1 or locked[0][0] != external[0][0]:
            findings.append(
                Finding(
                    "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                    "LuaRocks lock does not exactly resolve the external rockspec graph",
                    path=locks[0],
                )
            )
            return findings
        base_version = locked[0][1].rsplit("-", 1)[0]
        contains = self._cpan_range_contains(base_version, external[0][1])
        if contains is not True:
            findings.append(
                Finding(
                    "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                    "locked Lua rock does not satisfy the declared version range",
                    path=locks[0],
                    package=locked[0][0],
                    version=locked[0][1],
                )
            )
        return findings

    def _validate_carton_snapshot(self, raw: Mapping[str, object]) -> list[Finding]:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        if len(manifests) != 3 or len(locks) != 1:
            return [
                Finding(
                    "SEC-DEP-LOCK-POLICY",
                    "CPAN integrity requires Makefile.PL, dist.ini, cpanfile, and one Carton snapshot",
                )
            ]
        paths = {Path(path).name: path for path in manifests}
        if set(paths) != {"Makefile.PL", "dist.ini", "cpanfile"}:
            return [
                Finding(
                    "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                    "CPAN manifest denominator is incomplete",
                )
            ]
        try:
            cpanfile = (self.root / paths["cpanfile"]).read_text(encoding="utf-8")
            makefile = (self.root / paths["Makefile.PL"]).read_text(encoding="utf-8")
            dist_ini = (self.root / paths["dist.ini"]).read_text(encoding="utf-8")
            snapshot_text = (self.root / locks[0]).read_text(encoding="utf-8")
        except OSError as exc:
            return [
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    f"cannot read CPAN dependency evidence: {exc}",
                    path=locks[0],
                )
            ]
        records, snapshot_error = self._parse_carton_snapshot(snapshot_text)
        if snapshot_error is not None:
            return [
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    snapshot_error,
                    path=locks[0],
                )
            ]
        roots: dict[str, str] = {}
        for module, version in re.findall(
            r"(?m)^\s*requires\s+'([^']+)'\s*,\s*'([^']+)'\s*;",
            cpanfile,
        ):
            current = roots.get(module)
            comparison = (
                self._cpan_version_compare(version, current)
                if current is not None
                else 1
            )
            if comparison is None:
                findings = [
                    Finding(
                        "SEC-DEP-MANIFEST-MALFORMED",
                        "cpanfile contains an unsupported version expression",
                        path=paths["cpanfile"],
                        package=module,
                        version=version,
                    )
                ]
                return findings
            if comparison > 0:
                roots[module] = version
        expected_roots = {
            "perl": "5.010",
            "FFI::Platypus": "2.10",
            "JSON::PP": "4.00",
            "ExtUtils::MakeMaker": "0",
            "Test::More": "0",
        }
        findings: list[Finding] = []
        if roots != expected_roots:
            findings.append(
                Finding(
                    "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                    "cpanfile dependency roots differ from the governed manifest graph",
                    path=paths["cpanfile"],
                )
            )
        for module, version in (("FFI::Platypus", "2.10"), ("JSON::PP", "4.00")):
            if (
                re.search(
                    rf"['\"]?{re.escape(module)}['\"]?\s*(?:=>|=)\s*['\"]?{re.escape(version)}",
                    makefile,
                )
                is None
                or re.search(
                    rf"(?m)^{re.escape(module)}\s*=\s*{re.escape(version)}$",
                    dist_ini,
                )
                is None
            ):
                findings.append(
                    Finding(
                        "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                        "Perl authored manifests disagree on a runtime dependency",
                        package=module,
                        version=version,
                    )
                )
        core_modules, core_error = self._cpan_runtime_modules()
        if core_error is not None:
            findings.append(
                Finding("SEC-DEP-LOCK-MALFORMED", core_error, path=locks[0])
            )
            return findings
        provided: dict[str, tuple[str, str, str]] = {}
        for identity, record in records.items():
            provides = record["provides"]
            assert isinstance(provides, dict)
            for module, module_version in provides.items():
                provided[str(module)] = (
                    str(module_version),
                    identity,
                    str(record["version"]),
                )
        reachable: set[str] = set()
        pending = list(roots.items())
        seen_modules: set[str] = set()
        while pending:
            module, required_version = pending.pop()
            if module in seen_modules:
                continue
            seen_modules.add(module)
            external = provided.get(module)
            if external is not None:
                actual_version, identity, _ = external
                if actual_version == "undef":
                    actual_version = "0"
                comparison = self._cpan_version_compare(
                    actual_version, required_version
                )
                if comparison is None or comparison < 0:
                    findings.append(
                        Finding(
                            "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                            "Carton snapshot does not satisfy a dependency requirement",
                            package=module,
                            version=actual_version,
                        )
                    )
                    continue
                if identity not in reachable:
                    reachable.add(identity)
                    requirements = records[identity]["requirements"]
                    assert isinstance(requirements, dict)
                    pending.extend(
                        (str(name), str(value)) for name, value in requirements.items()
                    )
                continue
            core = core_modules.get(module)
            comparison = (
                self._cpan_version_compare(core["version"], required_version)
                if core is not None
                else None
            )
            if comparison is None or comparison < 0:
                findings.append(
                    Finding(
                        "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                        "CPAN dependency is absent from the snapshot and pinned Perl runtime",
                        package=module,
                        version=required_version,
                    )
                )
        if reachable != set(records):
            findings.append(
                Finding(
                    "SEC-DEP-LOCK-EXTRANEOUS",
                    "Carton snapshot contains an unreachable distribution",
                    path=locks[0],
                )
            )
        return findings

    def _validate_gradle_lock(self, raw: Mapping[str, object]) -> list[Finding]:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        lock_path = next(
            (path for path in locks if Path(path).name == "gradle.lockfile"), None
        )
        verification_path = next(
            (path for path in locks if Path(path).name == "verification-metadata.xml"),
            None,
        )
        if len(manifests) != 1 or lock_path is None or verification_path is None:
            return [
                Finding(
                    "SEC-DEP-LOCK-POLICY",
                    "Gradle integrity requires one manifest, dependency lock, and verification metadata",
                )
            ]
        try:
            lock_lines = (
                (self.root / lock_path).read_text(encoding="utf-8").splitlines()
            )
            verification = ET.parse(self.root / verification_path).getroot()
        except (OSError, ET.ParseError) as exc:
            return [
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    f"cannot parse Gradle lock evidence: {exc}",
                    path=lock_path,
                )
            ]
        findings = self._validate_direct_pins(raw)
        coordinates: set[str] = set()
        for line_number, line in enumerate(lock_lines, start=1):
            value = line.strip()
            if not value or value.startswith("#") or value.startswith("empty="):
                continue
            matched = re.fullmatch(r"([^:=]+:[^:=]+:[^=]+)=.+", value)
            if matched is None:
                findings.append(
                    Finding(
                        "SEC-DEP-LOCK-MALFORMED",
                        "Gradle lock entry is malformed",
                        path=lock_path,
                        line=line_number,
                    )
                )
            else:
                coordinates.add(matched.group(1))
        if not coordinates:
            findings.append(
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    "Gradle lock contains no dependency coordinates",
                    path=lock_path,
                )
            )
        sha256_values = [
            element.get("value")
            for element in verification.iter()
            if element.tag.rsplit("}", 1)[-1] == "sha256"
        ]
        if not sha256_values or any(
            not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in sha256_values
        ):
            findings.append(
                Finding(
                    "SEC-DEP-INTEGRITY-MISSING",
                    "Gradle verification metadata lacks complete SHA-256 artifact identities",
                    path=verification_path,
                )
            )
        return findings

    def _validate_renv_lock(self, raw: Mapping[str, object]) -> list[Finding]:
        manifests = self._string_list(raw.get("manifests"))
        locks = self._string_list(raw.get("locks"))
        if len(manifests) != 1 or len(locks) != 1:
            return [
                Finding(
                    "SEC-DEP-LOCK-POLICY",
                    "renv integrity requires one DESCRIPTION manifest and one lockfile",
                )
            ]
        manifest_path = manifests[0]
        lock_path = locks[0]
        try:
            manifest = (self.root / manifest_path).read_text(encoding="utf-8")
        except OSError as exc:
            return [
                Finding(
                    "SEC-DEP-MANIFEST-MALFORMED",
                    f"cannot read R DESCRIPTION manifest: {exc}",
                    path=manifest_path,
                )
            ]
        lock, lock_findings = self._read_json_object(
            lock_path, "SEC-DEP-LOCK-MALFORMED"
        )
        if lock is None:
            return lock_findings
        r_record = lock.get("R")
        packages = lock.get("Packages")
        findings: list[Finding] = []
        if (
            not isinstance(r_record, dict)
            or not isinstance(r_record.get("Version"), str)
            or re.fullmatch(r"\d+\.\d+\.\d+", str(r_record.get("Version"))) is None
        ):
            findings.append(
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    "renv lock lacks an exact R runtime version",
                    path=lock_path,
                )
            )
        if not isinstance(packages, dict) or not packages:
            return findings + [
                Finding(
                    "SEC-DEP-LOCK-MALFORMED",
                    "renv lock lacks a package inventory",
                    path=lock_path,
                )
            ]
        for package_key, package in packages.items():
            if not isinstance(package, dict):
                findings.append(
                    Finding(
                        "SEC-DEP-LOCK-MALFORMED",
                        "renv package record must be an object",
                        path=lock_path,
                        package=str(package_key),
                    )
                )
                continue
            name = package.get("Package")
            version = package.get("Version")
            source = package.get("Source")
            license_expression = package.get("License")
            if (
                name != package_key
                or not isinstance(version, str)
                or re.fullmatch(r"\d+(?:\.\d+)+(?:[-+][A-Za-z0-9.]+)?", version) is None
                or source != "Repository"
                or not isinstance(license_expression, str)
                or not license_expression.strip()
            ):
                findings.append(
                    Finding(
                        "SEC-DEP-LOCK-MALFORMED",
                        "renv package identity, source, version, or license is incomplete",
                        path=lock_path,
                        package=str(package_key),
                        version=str(version or ""),
                    )
                )
        declared_packages: set[str] = set()
        for description_field in ("Imports", "Suggests"):
            matched = re.search(
                rf"(?ms)^{description_field}:\s*(.+?)(?=^[A-Za-z][A-Za-z0-9/]*:|\Z)",
                manifest,
            )
            if matched is None:
                continue
            declared_packages.update(
                package
                for package in re.findall(
                    r"(?:^|,)\s*([A-Za-z][A-Za-z0-9.]*)", matched.group(1)
                )
                if package != "R"
            )
        for package in sorted(declared_packages - set(packages)):
            findings.append(
                Finding(
                    "SEC-DEP-MANIFEST-LOCK-MISMATCH",
                    "declared R dependency is absent from renv.lock",
                    path=lock_path,
                    package=package,
                )
            )
        return findings

    def _floating_specifier_findings(
        self, dependencies: Mapping[str, object], path: str
    ) -> list[Finding]:
        findings: list[Finding] = []
        for package, raw_specifier in sorted(dependencies.items()):
            specifier = str(raw_specifier).strip()
            if self._is_floating(specifier):
                findings.append(
                    Finding(
                        "SEC-DEP-FLOATING",
                        "dependency uses a prohibited floating declaration",
                        path=path,
                        package=package,
                        version=specifier,
                    )
                )
            if specifier.startswith(
                ("git+", "github:", "http://", "https://")
            ) and not re.search(r"(?:#|@)[0-9a-f]{40}$", specifier):
                findings.append(
                    Finding(
                        "SEC-DEP-UNPINNED-SOURCE",
                        "source dependency must end in an immutable full commit",
                        path=path,
                        package=package,
                        version=specifier,
                    )
                )
        return findings

    def _is_floating(self, value: str) -> bool:
        prohibited = self.policy.get("dependency_rules", {}).get(
            "prohibited_specifiers", []
        )
        normalized = value.strip().lower()
        return (
            normalized in {str(item).lower() for item in prohibited}
            or "latest" in normalized
            or normalized.endswith("+")
        )

    def _dependency_rule(self, name: str) -> bool:
        rules = self.policy.get("dependency_rules")
        return bool(rules.get(name)) if isinstance(rules, dict) else False

    def _read_json_object(
        self, path: str, code: str
    ) -> tuple[dict[str, object] | None, list[Finding]]:
        try:
            value = json.loads((self.root / path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return None, [
                Finding(code, f"cannot parse JSON dependency file: {exc}", path)
            ]
        if not isinstance(value, dict):
            return None, [Finding(code, "JSON dependency file must be an object", path)]
        return value, []

    def _read_toml_object(
        self, path: str, code: str
    ) -> tuple[dict[str, object] | None, list[Finding]]:
        try:
            value = tomllib.loads((self.root / path).read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            return None, [
                Finding(code, f"cannot parse TOML dependency file: {exc}", path)
            ]
        if not isinstance(value, dict):
            return None, [Finding(code, "TOML dependency file must be an object", path)]
        return value, []

    @staticmethod
    def _finding_check(
        check_id: str,
        category: str,
        inputs: list[str],
        findings: Iterable[Finding],
        *,
        ecosystem: str | None = None,
        scanner: dict[str, object] | None = None,
    ) -> SecurityCheck:
        collected = list(findings)
        return SecurityCheck(
            check_id,
            category,
            "failed" if collected else "passed",
            inputs,
            ecosystem=ecosystem,
            findings=collected,
            scanner=scanner,
        )


def incomplete_operation(
    operation_id: str,
    message: str,
    *,
    network_mode: str = "local",
    category: str = "dependency_integrity",
) -> SecurityOperation:
    return SecurityOperation(
        operation_id,
        network_mode,
        [
            SecurityCheck(
                f"{operation_id}.configuration",
                category,
                "incomplete",
                [],
                findings=[Finding("SEC-CONFIG-INCOMPLETE", message)],
            )
        ],
    )


def render_human(operation: SecurityOperation) -> None:
    for check in operation.checks:
        print(f"[{check.status}] {check.check_id}")
        for finding in check.findings:
            location = f" ({finding.path})" if finding.path else ""
            print(f"  {finding.code}{location}: {finding.message}")
        if check.unavailable_reason:
            print(f"  unavailable: {check.unavailable_reason}")
    print(f"security operation: {operation.status}")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("integrity", "content", "risk"))
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--policy-schema", type=Path, default=POLICY_SCHEMA_PATH)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        policy = load_policy(args.policy, args.policy_schema)
        engine = SecurityEngine(args.root, policy)
        if args.operation == "integrity":
            operation = engine.run_integrity()
        elif args.operation == "content":
            operation = engine.run_content()
        else:
            operation = engine.run_risk()
    except SecurityConfigurationError as exc:
        operation_ids = {
            "integrity": "security.dependency-integrity",
            "content": "security.content-and-workflows",
            "risk": "security.dependency-risk",
        }
        operation = incomplete_operation(
            operation_ids[args.operation],
            str(exc),
            network_mode="network" if args.operation == "risk" else "local",
            category="vulnerability"
            if args.operation == "risk"
            else "dependency_integrity",
        )
    serialized = json.dumps(operation.as_dict(), sort_keys=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8", newline="\n")
    if args.json_output:
        print(serialized)
    else:
        render_human(operation)
    return EXIT_CODES[operation.status]


if __name__ == "__main__":
    sys.exit(main())
