from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import cast

from tooling.security import ENGINE_VERSION, SecurityEngine


def policy(root: dict[str, object]) -> dict[str, object]:
    return {
        "engine": {
            "name": "strling-repository-security",
            "version": ENGINE_VERSION,
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


if __name__ == "__main__":
    unittest.main()
