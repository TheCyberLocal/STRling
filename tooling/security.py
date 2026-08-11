#!/usr/bin/env python3
"""Deterministic repository-security operations for STRling."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "governance/security-policy.json"
POLICY_SCHEMA_PATH = ROOT / "governance/schemas/security-policy.schema.json"
ENGINE_NAME = "strling-repository-security"
ENGINE_VERSION = "1.0.0"
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
    return subprocess.run(
        list(args),
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

    def run_integrity(self) -> SecurityOperation:
        checks = [self._check_engine_pin(), self._check_dependency_inventory()]
        roots = self.policy.get("dependency_roots")
        if not isinstance(roots, list):
            return SecurityOperation(
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
        return SecurityOperation("security.dependency-integrity", "local", checks)

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
        return SecurityOperation("security.content-and-workflows", "local", checks)

    def run_risk(self) -> SecurityOperation:
        roots = self.policy.get("dependency_roots")
        if not isinstance(roots, list):
            return SecurityOperation(
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
        return SecurityOperation(
            "security.dependency-risk",
            "network",
            checks,
            advisory_metadata=metadata,
        )

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
        counts = {"permitted": 0, "prohibited": 0, "unknown": 0, "overridden": 0}
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
            classification = self._license_classification(expression)
            counts[classification] += 1
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
        scanner = {
            "name": ENGINE_NAME,
            "version": self.engine_version,
            "packages_evaluated": evaluated,
            "classifications": counts,
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
        findings: list[Finding] = []
        counts = {"permitted": 0, "prohibited": 0, "unknown": 0, "overridden": 0}
        evaluated = 0
        incomplete = False
        for package in packages:
            if not isinstance(package, dict) or package.get("source") is None:
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
            classification = self._license_classification(expression)
            counts[classification] += 1
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
        scanner = {
            **scanner,
            "packages_evaluated": evaluated,
            "classifications": counts,
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
        return "unknown"

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
    if args.json_output:
        print(json.dumps(operation.as_dict(), sort_keys=True))
    else:
        render_human(operation)
    return EXIT_CODES[operation.status]


if __name__ == "__main__":
    sys.exit(main())
