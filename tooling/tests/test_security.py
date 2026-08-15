from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from subprocess import CompletedProcess
from typing import cast
from unittest.mock import patch

from tooling.security import (
    ENGINE_VERSION,
    GENERIC_CREDENTIAL_PATTERN,
    SECRET_PATTERNS,
    SecurityEngine,
    run_security_command,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class RepositorySecurityPolicyTests(unittest.TestCase):
    def test_interop_fuzz_has_a_distinct_root_with_the_shared_lock(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        interop = next(
            root
            for root in configured["dependency_roots"]
            if root["id"] == "interop-cargo"
        )
        self.assertEqual(
            ["bindings/interop/Cargo.toml"],
            interop["manifests"],
        )
        self.assertEqual(["bindings/interop/Cargo.lock"], interop["locks"])
        fuzz = next(
            root
            for root in configured["dependency_roots"]
            if root["id"] == "interop-fuzz-cargo"
        )
        self.assertEqual(["bindings/interop/fuzz/Cargo.toml"], fuzz["manifests"])
        self.assertEqual(["bindings/interop/Cargo.lock"], fuzz["locks"])
        self.assertEqual("tooling_only", fuzz["usage"])

    def test_libfuzzer_license_disposition_is_exact_and_tooling_only(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        disposition = next(
            item
            for item in configured["license_policy"]["scoped_permitted"]
            if item["id"] == "LIC-CARGO-LIBFUZZER-SYS-0.4.13"
        )
        self.assertEqual("cargo", disposition["ecosystem"])
        self.assertEqual("libfuzzer-sys", disposition["package"])
        self.assertEqual("0.4.13", disposition["version"])
        self.assertEqual("(MIT OR Apache-2.0) AND NCSA", disposition["license"])
        self.assertEqual(["interop-fuzz-cargo"], disposition["dependency_roots"])
        self.assertEqual("tooling_only", disposition["required_usage"])


class SecurityCommandTests(unittest.TestCase):
    def test_windows_command_resolves_cmd_shim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shim = root / "npm.cmd"
            shim.write_text("@exit /b 0\n", encoding="utf-8")
            completed = CompletedProcess([str(shim)], 0, "{}", "")
            with (
                patch("tooling.security.sys.platform", "win32"),
                patch("tooling.security.shutil.which", return_value=str(shim)),
                patch(
                    "tooling.security.subprocess.run", return_value=completed
                ) as runner,
            ):
                result = run_security_command(["npm", "audit", "--json"], root)

            self.assertIs(completed, result)
            runner.assert_called_once_with(
                [str(shim.resolve()), "audit", "--json"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )


def policy(root: dict[str, object]) -> dict[str, object]:
    return {
        "engine": {
            "name": "strling-repository-security",
            "version": ENGINE_VERSION,
        },
        "security_tools": {
            "cargo-audit": {
                "version": "0.22.2",
            }
        },
        "waiver_schema": "governance/schemas/waiver.schema.json",
        "security_waivers": [],
        "vulnerability_policy": {
            "blocking_severities": ["high", "critical"],
            "advisory_sources": {"npm": "npm-registry", "cargo": "rustsec"},
        },
        "license_policy": {
            "permitted": ["MIT", "Apache-2.0"],
            "prohibited": ["AGPL-3.0-only"],
            "scoped_permitted": [],
            "metadata_overrides": [],
            "unknown_is_blocking": True,
        },
        "dependency_roots": [root],
        "manifest_names": [
            "package.json",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle.kts",
        ],
        "manifest_suffixes": [".csproj"],
        "dependency_rules": {
            "prohibited_specifiers": ["*", "latest", "main", "master", "stable"],
            "require_npm_integrity": True,
            "require_cargo_checksums": True,
        },
        "workflow_policy": {
            "default_permissions": {"contents": "read"},
            "immutable_action_references": True,
            "validation_secrets_prohibited": True,
            "shell_secret_interpolation_prohibited": True,
            "privileged_jobs": {},
            "credential_persistence_jobs": {},
        },
    }


def npm_root() -> dict[str, object]:
    return {
        "id": "fixture-npm",
        "ecosystem": "npm",
        "classification": "actively_governed",
        "usage": "tooling_only",
        "manifests": ["package.json"],
        "locks": ["package-lock.json"],
        "lock_policy": "required",
        "integrity_mode": "npm_lock_v3",
        "risk_mode": "npm_audit",
    }


def write_npm_fixture(
    root: Path,
    *,
    manifest_specifier: str = "1.2.3",
    lock_specifier: str = "1.2.3",
) -> list[str]:
    manifest = {
        "private": True,
        "devDependencies": {"fixture-package": manifest_specifier},
    }
    lock = {
        "name": "fixture",
        "lockfileVersion": 3,
        "requires": True,
        "packages": {
            "": {"devDependencies": {"fixture-package": lock_specifier}},
            "node_modules/fixture-package": {
                "version": "1.2.3",
                "resolved": "https://registry.npmjs.org/fixture-package/-/fixture-package-1.2.3.tgz",
                "integrity": "sha512-c3ludGhldGljLW5vdC1hLXJlYWwtaW50ZWdyaXR5",
                "dev": True,
                "license": "MIT",
            },
        },
    }
    (root / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    return ["package-lock.json", "package.json"]


def npm_runner(payload: dict[str, object]):
    def runner(args: object, cwd: Path) -> CompletedProcess[str]:
        command = list(cast(list[str], args))
        if command == ["npm", "--version"]:
            return CompletedProcess(command, 0, "10.0.0\n", "")
        return CompletedProcess(command, 1, json.dumps(payload), "")

    return runner


def blocking_advisory(
    url: str = "https://advisories.invalid/GHSA-fixture",
) -> dict[str, object]:
    return {
        "vulnerabilities": {
            "fixture-package": {
                "severity": "high",
                "nodes": ["node_modules/fixture-package"],
                "via": [
                    {
                        "url": url,
                        "severity": "high",
                        "title": "synthetic advisory",
                    }
                ],
            }
        }
    }


def write_security_waiver(
    root: Path,
    configured_policy: dict[str, object],
    *,
    waiver_id: str = "WVR-SEC-TEST-001",
    expires_on: str = "2099-01-01",
    matches: list[dict[str, object]] | None = None,
) -> None:
    schema_target = root / "governance" / "schemas" / "waiver.schema.json"
    schema_target.parent.mkdir(parents=True)
    schema_target.write_text(
        (REPOSITORY_ROOT / "governance/schemas/waiver.schema.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    waiver_directory = root / "governance" / "waivers"
    waiver_directory.mkdir(parents=True)
    record = {
        "record_version": "1.0.0",
        "waiver_id": waiver_id,
        "status": "accepted",
        "rule": "SEC-VULN-BLOCKING",
        "scope": {
            "description": "exact synthetic fixture advisory",
            "paths": ["package.json", "package-lock.json"],
        },
        "rationale": "controlled nonfunctional certification fixture",
        "security": {
            "operation_id": "security.dependency-risk",
            "finding_code": "SEC-VULN-BLOCKING",
            "owner": "security test owner",
            "subsystem": "security-certification",
            "created_on": "2026-08-11",
            "review_context": "controlled waiver containment certification",
            "matches": matches
            or [
                {
                    "check_id": "security.vulnerability.fixture-npm",
                    "packages": ["fixture-package"],
                    "versions": ["1.2.3"],
                    "advisories": ["https://advisories.invalid/GHSA-fixture"],
                    "severities": ["high"],
                }
            ],
        },
        "retirement": {
            "condition": "synthetic test completes",
            "expires_on": expires_on,
            "replacement_work": ["remove the synthetic fixture waiver"],
        },
    }
    (waiver_directory / f"{waiver_id}.yaml").write_text(
        json.dumps(record), encoding="utf-8"
    )
    configured_policy["security_waivers"] = [waiver_id]


class DependencyIntegrityTests(unittest.TestCase):
    def test_valid_locked_dependency_state_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            result = SecurityEngine(
                root, policy(npm_root()), tracked_files=tracked
            ).run_integrity()
            self.assertEqual("passed", result.status)
            dependency = result.checks[-1]
            self.assertEqual("npm", dependency.ecosystem)
            self.assertEqual(
                ["package-lock.json", "package.json"],
                sorted(dependency.inputs),
            )
            self.assertEqual([], dependency.findings)

    def test_missing_required_lock_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_npm_fixture(root)
            (root / "package-lock.json").unlink()
            result = SecurityEngine(
                root, policy(npm_root()), tracked_files=["package.json"]
            ).run_integrity()
            finding_codes = {
                finding.code for check in result.checks for finding in check.findings
            }
            self.assertEqual("failed", result.status)
            self.assertIn("SEC-DEP-LOCK-MISSING", finding_codes)

    def test_manifest_lock_inconsistency_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(
                root,
                manifest_specifier="^1.2.3",
                lock_specifier="1.2.3",
            )
            result = SecurityEngine(
                root, policy(npm_root()), tracked_files=tracked
            ).run_integrity()
            finding_codes = {
                finding.code for check in result.checks for finding in check.findings
            }
            self.assertIn("SEC-DEP-MANIFEST-LOCK-MISMATCH", finding_codes)

    def test_unmanaged_dependency_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            unmanaged = root / "nested"
            unmanaged.mkdir()
            (unmanaged / "package.json").write_text("{}", encoding="utf-8")
            tracked.append("nested/package.json")
            result = SecurityEngine(
                root, policy(npm_root()), tracked_files=tracked
            ).run_integrity()
            inventory = result.checks[1]
            self.assertEqual("failed", inventory.status)
            self.assertEqual(
                ["nested/package.json"],
                [finding.path for finding in inventory.findings],
            )

    def test_security_engine_version_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            result = SecurityEngine(
                root,
                policy(npm_root()),
                tracked_files=tracked,
                engine_version="9.9.9",
            ).run_integrity()
            self.assertEqual("failed", result.checks[0].status)
            self.assertEqual(
                "SEC-TOOL-VERSION-DRIFT",
                result.checks[0].findings[0].code,
            )

    def test_malformed_lockfile_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            (root / "package-lock.json").write_text("{", encoding="utf-8")
            result = SecurityEngine(
                root, policy(npm_root()), tracked_files=tracked
            ).run_integrity()
            self.assertEqual("failed", result.status)
            self.assertIn(
                "SEC-DEP-LOCK-MALFORMED",
                {finding.code for check in result.checks for finding in check.findings},
            )

    def test_structured_result_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            engine = SecurityEngine(
                root, policy(npm_root()), tracked_files=reversed(tracked)
            )
            first = engine.run_integrity().as_dict()
            second = engine.run_integrity().as_dict()
            self.assertEqual(first, second)
            self.assertEqual("security.dependency-integrity", first["operation_id"])
            checks = cast(list[dict[str, object]], first["checks"])
            self.assertEqual("npm", checks[-1]["ecosystem"])


def write_workflow(root: Path, content: str) -> list[str]:
    path = root / ".github" / "workflows" / "ci.yml"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")
    return [".github/workflows/ci.yml"]


def workflow_text(
    *,
    permissions: bool = True,
    action_revision: str = "1111111111111111111111111111111111111111",
    persist_credentials: str | None = "false",
    job_permissions: str = "",
    run: str = "echo fixture",
) -> str:
    permission_block = "permissions:\n    contents: read\n" if permissions else ""
    persistence = (
        f"              with:\n                  persist-credentials: {persist_credentials}\n"
        if persist_credentials is not None
        else ""
    )
    job_permission_block = (
        f"        permissions:\n            {job_permissions}\n"
        if job_permissions
        else ""
    )
    return (
        "name: Fixture\n"
        "on: [pull_request]\n"
        f"{permission_block}"
        "jobs:\n"
        "    validate:\n"
        "        runs-on: ubuntu-latest\n"
        f"{job_permission_block}"
        "        steps:\n"
        f"            - uses: actions/checkout@{action_revision}\n"
        f"{persistence}"
        f"            - run: {run}\n"
    )


class ContentSecurityTests(unittest.TestCase):
    def test_safe_tracked_content_and_workflow_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("synthetic fixture", encoding="utf-8")
            tracked = ["README.md", *write_workflow(root, workflow_text())]
            result = SecurityEngine(
                root, policy(npm_root()), tracked_files=tracked
            ).run_content()
            self.assertEqual("passed", result.status)
            self.assertEqual(
                ["passed", "passed"],
                [check.status for check in result.checks],
            )

    def test_nonfunctional_secret_markers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private_key_marker = "-----BEGIN " + "RSA PRIVATE KEY-----"
            token_marker = "gh" + "p_" + ("A" * 36)
            (root / "fixture.txt").write_text(
                private_key_marker + "\n" + token_marker,
                encoding="utf-8",
            )
            result = SecurityEngine(
                root,
                policy(npm_root()),
                tracked_files=["fixture.txt"],
            ).run_content()
            codes = {
                finding.code for check in result.checks for finding in check.findings
            }
            self.assertEqual("failed", result.status)
            self.assertIn("SEC-SECRET-PRIVATE-KEY", codes)
            self.assertIn("SEC-SECRET-GITHUB-TOKEN", codes)

    def test_workflow_requires_read_only_defaults_and_immutable_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_workflow(
                root,
                workflow_text(
                    permissions=False,
                    action_revision="v5",
                    persist_credentials=None,
                ),
            )
            result = SecurityEngine(
                root, policy(npm_root()), tracked_files=tracked
            ).run_content()
            codes = {
                finding.code for check in result.checks for finding in check.findings
            }
            self.assertIn("SEC-WORKFLOW-DEFAULT-PERMISSIONS", codes)
            self.assertIn("SEC-WORKFLOW-ACTION-UNPINNED", codes)
            self.assertIn("SEC-WORKFLOW-CREDENTIAL-PERSISTENCE", codes)

    def test_validation_job_cannot_elevate_or_use_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            secret_expression = "$" + "{{ secrets.FIXTURE }}"
            tracked = write_workflow(
                root,
                workflow_text(
                    job_permissions="contents: write",
                    run=f'echo "{secret_expression}"',
                ),
            )
            result = SecurityEngine(
                root, policy(npm_root()), tracked_files=tracked
            ).run_content()
            codes = {
                finding.code for check in result.checks for finding in check.findings
            }
            self.assertIn("SEC-WORKFLOW-JOB-PERMISSIONS", codes)
            self.assertIn("SEC-WORKFLOW-VALIDATION-SECRET", codes)
            self.assertIn("SEC-WORKFLOW-SHELL-SECRET", codes)


class DependencyRiskTests(unittest.TestCase):
    @staticmethod
    def _cargo_license_payload(
        *,
        selected_root: str,
        selected_dependencies: list[str],
        libfuzzer_version: str = "0.4.13",
    ) -> dict[str, object]:
        packages = [
            {
                "id": "runtime-root",
                "name": "runtime-root",
                "version": "0.1.0",
                "source": None,
                "license": None,
            },
            {
                "id": "fuzz-root",
                "name": "fuzz-root",
                "version": "0.1.0",
                "source": None,
                "license": None,
            },
            {
                "id": "permitted-dependency",
                "name": "permitted-dependency",
                "version": "1.2.3",
                "source": "registry+https://example.invalid/index",
                "license": "MIT",
            },
            {
                "id": "libfuzzer-dependency",
                "name": "libfuzzer-sys",
                "version": libfuzzer_version,
                "source": "registry+https://example.invalid/index",
                "license": "(MIT OR Apache-2.0) AND NCSA",
            },
        ]
        return {
            "packages": packages,
            "resolve": {
                "root": selected_root,
                "nodes": [
                    {
                        "id": "runtime-root",
                        "deps": [
                            {"pkg": dependency}
                            for dependency in (
                                selected_dependencies
                                if selected_root == "runtime-root"
                                else ["permitted-dependency"]
                            )
                        ],
                    },
                    {
                        "id": "fuzz-root",
                        "deps": [
                            {"pkg": dependency}
                            for dependency in (
                                selected_dependencies
                                if selected_root == "fuzz-root"
                                else ["libfuzzer-dependency"]
                            )
                        ],
                    },
                    {"id": "permitted-dependency", "deps": []},
                    {"id": "libfuzzer-dependency", "deps": []},
                ],
            },
        }

    @staticmethod
    def _cargo_license_root(root_id: str, usage: str) -> dict[str, object]:
        return {
            "id": root_id,
            "ecosystem": "cargo",
            "classification": "actively_governed",
            "usage": usage,
            "manifests": ["Cargo.toml"],
            "locks": ["Cargo.lock"],
            "lock_policy": "required",
            "integrity_mode": "cargo_lock",
            "risk_mode": "cargo_audit",
        }

    @staticmethod
    def _cargo_metadata_runner(payload: dict[str, object]):
        def runner(args: object, cwd: Path) -> CompletedProcess[str]:
            command = list(cast(list[str], args))
            return CompletedProcess(command, 0, json.dumps(payload), "")

        return runner

    @staticmethod
    def _add_libfuzzer_disposition(configured: dict[str, object]) -> None:
        license_policy = cast(dict[str, object], configured["license_policy"])
        license_policy["scoped_permitted"] = [
            {
                "id": "LIC-CARGO-LIBFUZZER-SYS-0.4.13",
                "ecosystem": "cargo",
                "package": "libfuzzer-sys",
                "version": "0.4.13",
                "license": "(MIT OR Apache-2.0) AND NCSA",
                "dependency_roots": ["interop-fuzz-cargo"],
                "required_usage": "tooling_only",
                "evidence": "fixture disposition",
            }
        ]

    def test_cargo_license_inventory_excludes_unreachable_workspace_members(
        self,
    ) -> None:
        root = self._cargo_license_root("interop-cargo", "runtime")
        payload = self._cargo_license_payload(
            selected_root="runtime-root",
            selected_dependencies=["permitted-dependency"],
        )
        configured = policy(root)
        self._add_libfuzzer_disposition(configured)
        check = SecurityEngine(
            Path("."),
            configured,
            tracked_files=[],
            command_runner=self._cargo_metadata_runner(payload),
        )._license_cargo("interop-cargo", root)

        self.assertEqual("passed", check.status)
        self.assertEqual(1, check.scanner["packages_evaluated"])
        self.assertEqual(2, check.scanner["workspace_packages_excluded"])
        self.assertEqual([], check.scanner["scoped_dispositions"])

    def test_exact_cargo_license_disposition_passes_only_for_tooling_root(
        self,
    ) -> None:
        root = self._cargo_license_root("interop-fuzz-cargo", "tooling_only")
        payload = self._cargo_license_payload(
            selected_root="fuzz-root",
            selected_dependencies=["libfuzzer-dependency"],
        )
        configured = policy(root)
        self._add_libfuzzer_disposition(configured)
        check = SecurityEngine(
            Path("."),
            configured,
            tracked_files=[],
            command_runner=self._cargo_metadata_runner(payload),
        )._license_cargo("interop-fuzz-cargo", root)

        self.assertEqual("passed", check.status)
        self.assertEqual(1, check.scanner["classifications"]["scoped_permitted"])
        self.assertEqual(
            ["LIC-CARGO-LIBFUZZER-SYS-0.4.13"],
            check.scanner["scoped_dispositions"],
        )

    def test_scoped_cargo_license_disposition_fails_in_runtime_root(self) -> None:
        root = self._cargo_license_root("interop-cargo", "runtime")
        payload = self._cargo_license_payload(
            selected_root="runtime-root",
            selected_dependencies=["libfuzzer-dependency"],
        )
        configured = policy(root)
        self._add_libfuzzer_disposition(configured)
        check = SecurityEngine(
            Path("."),
            configured,
            tracked_files=[],
            command_runner=self._cargo_metadata_runner(payload),
        )._license_cargo("interop-cargo", root)

        self.assertEqual("failed", check.status)
        self.assertEqual("SEC-LICENSE-SCOPE-VIOLATION", check.findings[0].code)

    def test_scoped_cargo_license_disposition_does_not_cover_version_drift(
        self,
    ) -> None:
        root = self._cargo_license_root("interop-fuzz-cargo", "tooling_only")
        payload = self._cargo_license_payload(
            selected_root="fuzz-root",
            selected_dependencies=["libfuzzer-dependency"],
            libfuzzer_version="0.4.14",
        )
        configured = policy(root)
        self._add_libfuzzer_disposition(configured)
        check = SecurityEngine(
            Path("."),
            configured,
            tracked_files=[],
            command_runner=self._cargo_metadata_runner(payload),
        )._license_cargo("interop-fuzz-cargo", root)

        self.assertEqual("failed", check.status)
        self.assertEqual("SEC-LICENSE-UNKNOWN", check.findings[0].code)

    def test_blocking_npm_advisory_carries_required_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            result = SecurityEngine(
                root,
                policy(npm_root()),
                tracked_files=tracked,
                command_runner=npm_runner(blocking_advisory()),
            ).run_risk()
            vulnerability = next(
                check for check in result.checks if check.category == "vulnerability"
            )
            finding = vulnerability.findings[0]
            self.assertEqual("failed", result.status)
            self.assertEqual("SEC-VULN-BLOCKING", finding.code)
            self.assertEqual("fixture-package", finding.package)
            self.assertEqual("1.2.3", finding.version)
            self.assertEqual(
                "https://advisories.invalid/GHSA-fixture", finding.advisory
            )
            self.assertEqual("high", finding.severity)

    def test_unavailable_advisory_scanner_is_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)

            def runner(args: object, cwd: Path) -> CompletedProcess[str]:
                raise FileNotFoundError("synthetic npm absence")

            result = SecurityEngine(
                root,
                policy(npm_root()),
                tracked_files=tracked,
                command_runner=runner,
            ).run_risk()
            vulnerability = next(
                check for check in result.checks if check.category == "vulnerability"
            )
            self.assertEqual("unavailable", result.status)
            self.assertEqual("unavailable", vulnerability.status)
            self.assertIn(
                "synthetic npm absence", vulnerability.unavailable_reason or ""
            )

    def test_unknown_license_is_visible_and_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            lock_path = root / "package-lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["packages"]["node_modules/fixture-package"]["license"] = (
                "Fixture-Unknown"
            )
            lock_path.write_text(json.dumps(lock), encoding="utf-8")

            def runner(args: object, cwd: Path) -> CompletedProcess[str]:
                command = list(cast(list[str], args))
                if command == ["npm", "--version"]:
                    return CompletedProcess(command, 0, "10.0.0\n", "")
                return CompletedProcess(
                    command, 0, json.dumps({"vulnerabilities": {}}), ""
                )

            result = SecurityEngine(
                root,
                policy(npm_root()),
                tracked_files=tracked,
                command_runner=runner,
            ).run_risk()
            license_check = next(
                check for check in result.checks if check.category == "license"
            )
            self.assertEqual("failed", license_check.status)
            self.assertEqual("SEC-LICENSE-UNKNOWN", license_check.findings[0].code)
            self.assertEqual("Fixture-Unknown", license_check.findings[0].license)

    def test_cargo_audit_version_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.toml").write_text(
                '[package]\nname = "fixture"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            (root / "Cargo.lock").write_text("version = 4\n", encoding="utf-8")
            cargo_root = {
                "id": "fixture-cargo",
                "ecosystem": "cargo",
                "classification": "actively_governed",
                "usage": "runtime",
                "manifests": ["Cargo.toml"],
                "locks": ["Cargo.lock"],
                "lock_policy": "required",
                "integrity_mode": "cargo_lock",
                "risk_mode": "cargo_audit",
            }

            def runner(args: object, cwd: Path) -> CompletedProcess[str]:
                command = list(cast(list[str], args))
                if command[:3] == ["cargo", "audit", "--version"]:
                    return CompletedProcess(command, 0, "cargo-audit 0.22.1\n", "")
                metadata = {"packages": []}
                return CompletedProcess(command, 0, json.dumps(metadata), "")

            result = SecurityEngine(
                root,
                policy(cargo_root),
                tracked_files=["Cargo.lock", "Cargo.toml"],
                command_runner=runner,
            ).run_risk()
            vulnerability = next(
                check for check in result.checks if check.category == "vulnerability"
            )
            self.assertEqual("failed", vulnerability.status)
            self.assertEqual("SEC-TOOL-VERSION-DRIFT", vulnerability.findings[0].code)

    def test_malformed_risk_inventory_is_incomplete_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            (root / "package-lock.json").write_text("{", encoding="utf-8")
            result = SecurityEngine(
                root,
                policy(npm_root()),
                tracked_files=tracked,
                command_runner=npm_runner({"vulnerabilities": {}}),
            ).run_risk()
            self.assertEqual("incomplete", result.status)
            self.assertNotEqual("passed", result.checks[0].status)


class SecurityWaiverCertificationTests(unittest.TestCase):
    def test_exact_accepted_waiver_produces_waived_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            configured = policy(npm_root())
            write_security_waiver(root, configured)
            result = SecurityEngine(
                root,
                configured,
                tracked_files=tracked,
                command_runner=npm_runner(blocking_advisory()),
                today=date(2026, 8, 11),
            ).run_risk()
            vulnerability = next(
                check for check in result.checks if check.category == "vulnerability"
            )
            self.assertEqual("waived", result.status)
            self.assertEqual("waived", vulnerability.status)
            self.assertEqual("WVR-SEC-TEST-001", vulnerability.findings[0].waiver_id)

    def test_waiver_does_not_suppress_unrelated_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            configured = policy(npm_root())
            write_security_waiver(root, configured)
            payload = blocking_advisory()
            vulnerabilities = cast(dict[str, object], payload["vulnerabilities"])
            fixture = cast(dict[str, object], vulnerabilities["fixture-package"])
            vias = cast(list[object], fixture["via"])
            vias.append(
                {
                    "url": "https://advisories.invalid/GHSA-unrelated",
                    "severity": "critical",
                    "title": "second synthetic advisory",
                }
            )
            result = SecurityEngine(
                root,
                configured,
                tracked_files=tracked,
                command_runner=npm_runner(payload),
                today=date(2026, 8, 11),
            ).run_risk()
            vulnerability = next(
                check for check in result.checks if check.category == "vulnerability"
            )
            self.assertEqual("failed", result.status)
            self.assertEqual(
                [None, "WVR-SEC-TEST-001"],
                sorted(
                    (finding.waiver_id for finding in vulnerability.findings),
                    key=lambda item: item or "",
                ),
            )

    def test_expired_waiver_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            configured = policy(npm_root())
            write_security_waiver(root, configured, expires_on="2026-08-11")
            result = SecurityEngine(
                root,
                configured,
                tracked_files=tracked,
                command_runner=npm_runner(blocking_advisory()),
                today=date(2026, 8, 12),
            ).run_risk()
            waiver_check = next(
                check for check in result.checks if check.category == "waiver"
            )
            self.assertEqual("failed", result.status)
            self.assertEqual("SEC-WAIVER-EXPIRED", waiver_check.findings[0].code)

    def test_unknown_waiver_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            configured = policy(npm_root())
            configured["security_waivers"] = ["WVR-SEC-MISSING-001"]
            schema = root / "governance" / "schemas" / "waiver.schema.json"
            schema.parent.mkdir(parents=True)
            schema.write_text(
                (REPOSITORY_ROOT / "governance/schemas/waiver.schema.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            result = SecurityEngine(
                root,
                configured,
                tracked_files=tracked,
                command_runner=npm_runner(blocking_advisory()),
                today=date(2026, 8, 11),
            ).run_risk()
            waiver_check = next(
                check for check in result.checks if check.category == "waiver"
            )
            self.assertEqual("failed", result.status)
            self.assertEqual("SEC-WAIVER-UNKNOWN", waiver_check.findings[0].code)

    def test_waived_risk_result_is_structurally_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            configured = policy(npm_root())
            write_security_waiver(root, configured)
            engine = SecurityEngine(
                root,
                configured,
                tracked_files=tracked,
                command_runner=npm_runner(blocking_advisory()),
                today=date(2026, 8, 11),
            )
            self.assertEqual(engine.run_risk().as_dict(), engine.run_risk().as_dict())

    def test_security_operations_leave_inputs_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tracked = write_npm_fixture(root)
            tracked.extend(write_workflow(root, workflow_text()))
            before = {path: (root / path).read_bytes() for path in tracked}
            engine = SecurityEngine(
                root,
                policy(npm_root()),
                tracked_files=tracked,
                command_runner=npm_runner({"vulnerabilities": {}}),
            )
            engine.run_integrity()
            engine.run_content()
            engine.run_risk()
            after = {path: (root / path).read_bytes() for path in tracked}
            self.assertEqual(before, after)

    def test_test_source_contains_no_functional_credential_fixture(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        for _, _, pattern in SECRET_PATTERNS:
            self.assertIsNone(pattern.search(source))
        self.assertIsNone(GENERIC_CREDENTIAL_PATTERN.search(source))


if __name__ == "__main__":
    unittest.main()
