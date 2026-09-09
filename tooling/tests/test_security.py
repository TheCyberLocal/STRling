from __future__ import annotations

import json
import hashlib
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
    def test_dotnet_public_api_tooling_has_no_external_dependencies(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        extractor = next(
            root
            for root in configured["dependency_roots"]
            if root["id"] == "dotnet-public-api-tooling"
        )
        self.assertEqual("nuget", extractor["ecosystem"])
        self.assertEqual("no_external_dependencies", extractor["integrity_mode"])
        engine = SecurityEngine(REPOSITORY_ROOT, configured, tracked_files=[])
        self.assertEqual([], engine._validate_no_external_dependencies(extractor))

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

    def test_runtime_license_dispositions_match_exact_reachability(
        self,
    ) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        roots = {item["id"]: item for item in configured["dependency_roots"]}
        dispositions = [
            item
            for item in configured["license_policy"]["scoped_permitted"]
            if item["required_usage"] == "runtime"
        ]
        self.assertEqual(15, len(dispositions))
        engine = SecurityEngine(REPOSITORY_ROOT, configured, tracked_files=[])
        for disposition in dispositions:
            root_id = disposition["dependency_roots"][0]
            classification, disposition_id = engine._dependency_license_classification(
                root_id=root_id,
                dependency_root=roots[root_id],
                ecosystem=disposition["ecosystem"],
                package=disposition["package"],
                version=disposition["version"],
                expression=disposition["license"],
            )
            with self.subTest(disposition=disposition["id"]):
                self.assertEqual("scoped_permitted", classification)
                self.assertEqual(disposition["id"], disposition_id)

    def test_gradle_junit_bom_metadata_override_is_exact(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        override = next(
            item
            for item in configured["license_policy"]["metadata_overrides"]
            if item["ecosystem"] == "gradle"
            and item["package"] == "org.junit:junit-bom"
        )
        self.assertEqual(
            {
                "ecosystem": "gradle",
                "package": "org.junit:junit-bom",
                "version": "5.10.1",
                "license": "EPL-2.0",
                "evidence": override["evidence"],
            },
            override,
        )
        self.assertEqual(
            "EPL-2.0",
            SecurityEngine(
                REPOSITORY_ROOT, configured, tracked_files=[]
            )._license_override("gradle", "org.junit:junit-bom", "5.10.1"),
        )
        disposition = next(
            item
            for item in configured["license_policy"]["scoped_permitted"]
            if item["id"] == "LIC-GRADLE-JUNIT-BOM-5.10.1"
        )
        self.assertEqual(["kotlin-gradle"], disposition["dependency_roots"])
        self.assertEqual(
            ["testCompileClasspath", "testRuntimeClasspath"],
            disposition["reachability_evidence"]["configurations"],
        )

    def test_cpan_runtime_dispositions_select_exact_artistic_material(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        dispositions = {
            item["id"]: item
            for item in configured["license_policy"]["scoped_permitted"]
            if item["ecosystem"] == "cpan"
        }
        self.assertEqual(
            {
                "LIC-CPAN-FFI-CHECKLIB-0.31",
                "LIC-CPAN-FFI-PLATYPUS-2.11",
                "LIC-CPAN-FILE-WHICH-1.27",
            },
            set(dispositions),
        )
        for disposition in dispositions.values():
            with self.subTest(disposition=disposition["id"]):
                self.assertEqual("Artistic-1.0-Perl", disposition["selected_license"])
                self.assertEqual(["perl-cpan"], disposition["dependency_roots"])
                self.assertEqual("runtime", disposition["required_usage"])
                self.assertEqual(
                    "cpan-runtime-closure",
                    disposition["reachability_evidence"]["kind"],
                )
                self.assertEqual(
                    "governance/dependency-license-evidence.json",
                    disposition["license_material"]["manifest"],
                )
                component = SecurityEngine(
                    REPOSITORY_ROOT, configured, tracked_files=[]
                )._license_component_evidence(
                    root_id="perl-cpan",
                    dependency_root=next(
                        item
                        for item in configured["dependency_roots"]
                        if item["id"] == "perl-cpan"
                    ),
                    ecosystem="cpan",
                    package=disposition["package"],
                    version=disposition["version"],
                    expression=disposition["license"],
                    classification="scoped_permitted",
                    disposition_id=disposition["id"],
                )
                self.assertEqual("Artistic-1.0-Perl", component["selected_license"])
                self.assertEqual("distributed-runtime", component["distribution_scope"])

    def test_cpan_runtime_disposition_fails_on_closure_surface_or_material_drift(
        self,
    ) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        disposition = next(
            item
            for item in configured["license_policy"]["scoped_permitted"]
            if item["id"] == "LIC-CPAN-FFI-PLATYPUS-2.11"
        )
        dependency = next(
            item for item in configured["dependency_roots"] if item["id"] == "perl-cpan"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_disposition = json.loads(json.dumps(disposition))
            fixture_dependency = json.loads(json.dumps(dependency))
            mappings = {
                "bindings/perl/cpanfile": "cpanfile",
                "bindings/perl/cpanfile.snapshot": "cpanfile.snapshot",
                "tests/certification/release-supply-chain/1.0/manifest.json": "release.json",
                "governance/dependency-license-evidence.json": "licenses.json",
            }
            for source, target in mappings.items():
                (root / target).write_text(
                    (REPOSITORY_ROOT / source).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            fixture_dependency["manifests"] = [
                Path(item).name for item in dependency["manifests"]
            ]
            for source in dependency["manifests"]:
                name = Path(source).name
                if not (root / name).exists():
                    (root / name).write_text(
                        (REPOSITORY_ROOT / source).read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
            fixture_dependency["locks"] = ["cpanfile.snapshot"]
            fixture_disposition["reachability_evidence"].update(
                {
                    "manifest": "cpanfile",
                    "lock": "cpanfile.snapshot",
                    "release_manifest": "release.json",
                }
            )
            fixture_disposition["license_material"]["manifest"] = "licenses.json"
            configured["license_policy"]["scoped_permitted"] = [fixture_disposition]
            engine = SecurityEngine(root, configured, tracked_files=[])
            arguments = {
                "root_id": "perl-cpan",
                "dependency_root": fixture_dependency,
                "ecosystem": disposition["ecosystem"],
                "package": disposition["package"],
                "version": disposition["version"],
                "expression": disposition["license"],
            }
            self.assertEqual(
                "scoped_permitted",
                engine._dependency_license_classification(**arguments)[0],
            )

            original_snapshot = (root / "cpanfile.snapshot").read_text(encoding="utf-8")
            (root / "cpanfile.snapshot").write_text(
                original_snapshot.replace("FFI-Platypus-2.11", "FFI-Platypus-2.12"),
                encoding="utf-8",
            )
            self.assertEqual(
                "scope_violation",
                engine._dependency_license_classification(**arguments)[0],
            )
            (root / "cpanfile.snapshot").write_text(original_snapshot, encoding="utf-8")

            release = json.loads((root / "release.json").read_text(encoding="utf-8"))
            release["artifacts"][0]["dependency_roots"].append("perl-cpan")
            (root / "release.json").write_text(json.dumps(release), encoding="utf-8")
            self.assertEqual(
                "scope_violation",
                engine._dependency_license_classification(**arguments)[0],
            )
            (root / "release.json").write_text(
                (
                    REPOSITORY_ROOT
                    / "tests/certification/release-supply-chain/1.0/manifest.json"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            licenses = json.loads((root / "licenses.json").read_text(encoding="utf-8"))
            row = next(
                item
                for item in licenses["entries"]
                if item["ecosystem"] == "cpan"
                and item["package"] == "FFI-Platypus"
                and item["version"] == "2.11"
            )
            row["license_sha256"] = "0" * 64
            (root / "licenses.json").write_text(json.dumps(licenses), encoding="utf-8")
            self.assertEqual(
                "scope_violation",
                engine._dependency_license_classification(**arguments)[0],
            )

    def test_maven_disposition_fails_if_test_dependency_becomes_runtime(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        disposition = next(
            item
            for item in configured["license_policy"]["scoped_permitted"]
            if item["id"] == "LIC-MAVEN-JAVA-JUNIT-API-5.10.1"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = (REPOSITORY_ROOT / "bindings/java/pom.xml").read_text(
                encoding="utf-8"
            )
            (root / "pom.xml").write_text(manifest, encoding="utf-8")
            fixture_disposition = json.loads(json.dumps(disposition))
            fixture_disposition["reachability_evidence"]["manifest"] = "pom.xml"
            configured["license_policy"]["scoped_permitted"] = [fixture_disposition]
            dependency_root = {
                "id": "java-maven",
                "ecosystem": "maven",
                "usage": "runtime",
                "manifests": ["pom.xml"],
                "locks": [],
            }
            engine = SecurityEngine(root, configured, tracked_files=[])
            arguments = {
                "root_id": "java-maven",
                "dependency_root": dependency_root,
                "ecosystem": disposition["ecosystem"],
                "package": disposition["package"],
                "version": disposition["version"],
                "expression": disposition["license"],
            }
            self.assertEqual(
                "scoped_permitted",
                engine._dependency_license_classification(**arguments)[0],
            )
            (root / "pom.xml").write_text(
                manifest.replace("<scope>test</scope>", "<scope>runtime</scope>"),
                encoding="utf-8",
            )
            self.assertEqual(
                "scope_violation",
                engine._dependency_license_classification(**arguments)[0],
            )

    def test_gradle_disposition_fails_if_configuration_scope_expands(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        disposition = next(
            item
            for item in configured["license_policy"]["scoped_permitted"]
            if item["id"] == "LIC-GRADLE-TROVE4J-1.0.20200330"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = (REPOSITORY_ROOT / "bindings/kotlin/gradle.lockfile").read_text(
                encoding="utf-8"
            )
            (root / "gradle.lockfile").write_text(lock, encoding="utf-8")
            fixture_disposition = json.loads(json.dumps(disposition))
            fixture_disposition["reachability_evidence"]["lock"] = "gradle.lockfile"
            configured["license_policy"]["scoped_permitted"] = [fixture_disposition]
            dependency_root = {
                "id": "kotlin-gradle",
                "ecosystem": "gradle",
                "usage": "runtime",
                "manifests": ["build.gradle.kts"],
                "locks": ["gradle.lockfile"],
            }
            engine = SecurityEngine(root, configured, tracked_files=[])
            arguments = {
                "root_id": "kotlin-gradle",
                "dependency_root": dependency_root,
                "ecosystem": disposition["ecosystem"],
                "package": disposition["package"],
                "version": disposition["version"],
                "expression": disposition["license"],
            }
            self.assertEqual(
                "scoped_permitted",
                engine._dependency_license_classification(**arguments)[0],
            )
            (root / "gradle.lockfile").write_text(
                lock.replace(
                    "kotlinKlibCommonizerClasspath\n",
                    "kotlinKlibCommonizerClasspath,runtimeClasspath\n",
                    1,
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                "scope_violation",
                engine._dependency_license_classification(**arguments)[0],
            )

    def test_renv_disposition_fails_if_test_root_becomes_runtime_import(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        disposition = next(
            item
            for item in configured["license_policy"]["scoped_permitted"]
            if item["id"] == "LIC-R-DIFFOBJ-0.3.8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            description = (REPOSITORY_ROOT / "bindings/r/DESCRIPTION").read_text(
                encoding="utf-8"
            )
            renv = (REPOSITORY_ROOT / "bindings/r/renv.lock").read_text(
                encoding="utf-8"
            )
            (root / "DESCRIPTION").write_text(description, encoding="utf-8")
            (root / "renv.lock").write_text(renv, encoding="utf-8")
            fixture_disposition = json.loads(json.dumps(disposition))
            fixture_disposition["reachability_evidence"].update(
                {"manifest": "DESCRIPTION", "lock": "renv.lock"}
            )
            configured["license_policy"]["scoped_permitted"] = [fixture_disposition]
            dependency_root = {
                "id": "r-package",
                "ecosystem": "r",
                "usage": "runtime",
                "manifests": ["DESCRIPTION"],
                "locks": ["renv.lock"],
            }
            engine = SecurityEngine(root, configured, tracked_files=[])
            arguments = {
                "root_id": "r-package",
                "dependency_root": dependency_root,
                "ecosystem": disposition["ecosystem"],
                "package": disposition["package"],
                "version": disposition["version"],
                "expression": disposition["license"],
            }
            self.assertEqual(
                "scoped_permitted",
                engine._dependency_license_classification(**arguments)[0],
            )
            (root / "DESCRIPTION").write_text(
                description.replace("Suggests: testthat", "Imports: testthat"),
                encoding="utf-8",
            )
            self.assertEqual(
                "scope_violation",
                engine._dependency_license_classification(**arguments)[0],
            )

    def test_luarocks_lock_is_exact_and_fails_on_version_drift(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        dependency = next(
            item
            for item in configured["dependency_roots"]
            if item["id"] == "lua-luarocks"
        )
        engine = SecurityEngine(REPOSITORY_ROOT, configured, tracked_files=[])
        self.assertEqual([], engine._validate_luarocks_lock(dependency))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "strling.rockspec").write_text(
                (REPOSITORY_ROOT / dependency["manifests"][0]).read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            lock = (REPOSITORY_ROOT / dependency["locks"][0]).read_text(
                encoding="utf-8"
            )
            (root / "luarocks.lock").write_text(
                lock.replace("2.1.0.10-1", "3.0.0-1"), encoding="utf-8"
            )
            fixture = {
                **dependency,
                "manifests": ["strling.rockspec"],
                "locks": ["luarocks.lock"],
            }
            findings = SecurityEngine(
                root, configured, tracked_files=[]
            )._validate_luarocks_lock(fixture)
            self.assertEqual(
                ["SEC-DEP-MANIFEST-LOCK-MISMATCH"],
                sorted({item.code for item in findings}),
            )

    def test_carton_snapshot_is_exact_and_fails_on_closure_drift(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        dependency = next(
            item for item in configured["dependency_roots"] if item["id"] == "perl-cpan"
        )
        engine = SecurityEngine(REPOSITORY_ROOT, configured, tracked_files=[])
        self.assertEqual([], engine._validate_carton_snapshot(dependency))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_manifests: list[str] = []
            for relative in dependency["manifests"]:
                name = Path(relative).name
                fixture_manifests.append(name)
                (root / name).write_text(
                    (REPOSITORY_ROOT / relative).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            snapshot = (REPOSITORY_ROOT / dependency["locks"][0]).read_text(
                encoding="utf-8"
            )
            (root / "cpanfile.snapshot").write_text(
                snapshot.replace("      File::Which 1.27", "      File::WhichX 1.27"),
                encoding="utf-8",
            )
            fixture = {
                **dependency,
                "manifests": fixture_manifests,
                "locks": ["cpanfile.snapshot"],
            }
            findings = SecurityEngine(
                root, configured, tracked_files=[]
            )._validate_carton_snapshot(fixture)
            self.assertIn(
                "SEC-DEP-MANIFEST-LOCK-MISMATCH", {item.code for item in findings}
            )

    def test_cpan_version_ranges_use_selected_versions(self) -> None:
        self.assertTrue(SecurityEngine._cpan_range_contains("5.44.0", ">0"))
        self.assertTrue(SecurityEngine._cpan_range_contains("5.44.0", ">=5.43.11"))
        self.assertFalse(
            SecurityEngine._cpan_range_contains("5.44.0", ">=5.41.0,<5.43.11")
        )
        self.assertTrue(SecurityEngine._cpan_range_contains("5.44.0", ">=5.008004"))
        self.assertIsNone(SecurityEngine._cpan_range_contains("5.44.0", "~=5.44"))

    def test_luarocks_source_identity_drift_is_incomplete(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        dependency = next(
            item
            for item in configured["dependency_roots"]
            if item["id"] == "lua-luarocks"
        )
        configured["security_tools"]["luarocks-evidence"]["source_commit"] = "0" * 40
        engine = SecurityEngine(REPOSITORY_ROOT, configured, tracked_files=[])
        vulnerability, license_check = engine._audit_luarocks(
            "lua-luarocks", dependency
        )
        self.assertEqual("incomplete", vulnerability.status)
        self.assertEqual("incomplete", license_check.status)

    def test_cpansa_unknown_affected_severity_blocks(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        dependency = next(
            item for item in configured["dependency_roots"] if item["id"] == "perl-cpan"
        )
        database = {
            "meta": {"commit": "fixture-content"},
            "dists": {
                "perl": {
                    "advisories": [
                        {
                            "id": "CPANSA-fixture-unknown",
                            "affected_versions": [">0"],
                            "severity": None,
                            "description": "fixture affected advisory",
                        }
                    ]
                }
            },
        }
        database_bytes = json.dumps(database, sort_keys=True).encode("utf-8")
        cpansa = configured["security_tools"]["cpansa"]
        cpansa["database_sha256"] = hashlib.sha256(database_bytes).hexdigest()
        cpansa["database_content_commit"] = "fixture-content"
        cpansa["severity_corrections"] = []
        engine = SecurityEngine(REPOSITORY_ROOT, configured, tracked_files=[])
        with patch.object(
            SecurityEngine, "_network_bytes", return_value=(database_bytes, None)
        ):
            vulnerability, license_check = engine._audit_cpansa("perl-cpan", dependency)
        self.assertEqual("failed", vulnerability.status)
        self.assertIn(
            "SEC-VULN-BLOCKING", {item.code for item in vulnerability.findings}
        )
        self.assertEqual("passed", license_check.status)

    def test_cpansa_severity_correction_fails_on_independent_drift(self) -> None:
        configured = json.loads(
            (REPOSITORY_ROOT / "governance/security-policy.json").read_text(
                encoding="utf-8"
            )
        )
        dependency = next(
            item for item in configured["dependency_roots"] if item["id"] == "perl-cpan"
        )
        database = {
            "meta": {"commit": "fixture-content"},
            "dists": {
                "File-Temp": {
                    "advisories": [
                        {
                            "id": "CPANSA-File-Temp-2011-4116",
                            "affected_versions": [">0"],
                            "severity": "high",
                            "cves": ["CVE-2011-4116"],
                            "description": "fixture File::Temp advisory",
                        }
                    ]
                }
            },
        }
        database_bytes = json.dumps(database, sort_keys=True).encode("utf-8")
        cpansa = configured["security_tools"]["cpansa"]
        cpansa["database_sha256"] = hashlib.sha256(database_bytes).hexdigest()
        cpansa["database_content_commit"] = "fixture-content"
        independent = {
            "ghsa_id": "GHSA-grqm-6jmc-2h46",
            "cve_id": "CVE-2011-4116",
            "severity": "medium",
            "cvss": {"score": 9.9, "vector_string": "drifted"},
        }
        responses = [
            (database_bytes, None),
            (json.dumps(independent).encode("utf-8"), None),
        ]
        engine = SecurityEngine(REPOSITORY_ROOT, configured, tracked_files=[])
        with patch.object(SecurityEngine, "_network_bytes", side_effect=responses):
            vulnerability, _ = engine._audit_cpansa("perl-cpan", dependency)
        self.assertEqual("incomplete", vulnerability.status)
        self.assertIn(
            "SEC-VULN-EVIDENCE-INCOMPLETE",
            {item.code for item in vulnerability.findings},
        )


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

    @staticmethod
    def _osv_root() -> dict[str, object]:
        return {
            "id": "fixture-python",
            "ecosystem": "python",
            "classification": "actively_governed",
            "usage": "tooling_only",
            "manifests": ["requirements.txt"],
            "locks": [],
            "lock_policy": "exact_requirements",
            "integrity_mode": "exact_requirements",
            "risk_mode": "osv_scan",
        }

    @staticmethod
    def _osv_runner(payload: dict[str, object]):
        def runner(args: object, cwd: Path) -> CompletedProcess[str]:
            command = list(cast(list[str], args))
            if command[-1] == "--version":
                return CompletedProcess(command, 0, "osv-scanner version: 2.4.0\n", "")
            return CompletedProcess(command, 0, json.dumps(payload), "")

        return runner

    def _osv_policy(
        self, root: dict[str, object], executable: Path
    ) -> dict[str, object]:
        configured = policy(root)
        configured["engine"] = {
            "name": "strling-repository-security",
            "version": ENGINE_VERSION,
        }
        configured["security_tools"]["osv-scanner"] = {
            "version": "2.4.0",
            "executable_environment_variable": "STRLING_OSV_SCANNER",
            "sha256": {
                "windows_amd64": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "linux_amd64": hashlib.sha256(executable.read_bytes()).hexdigest(),
            },
            "license_allowlist": ["MIT", "Apache-2.0"],
        }
        return configured

    def test_osv_scan_authenticates_tool_and_passes_complete_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "osv-scanner"
            executable.write_bytes(b"governed scanner")
            (root / "requirements.txt").write_text(
                "fixture-package==1.2.3\n", encoding="utf-8"
            )
            payload = {
                "results": [
                    {
                        "packages": [
                            {
                                "package": {
                                    "name": "fixture-package",
                                    "version": "1.2.3",
                                    "ecosystem": "PyPI",
                                },
                                "licenses": ["MIT"],
                            }
                        ]
                    }
                ]
            }
            with patch.dict(
                "os.environ", {"STRLING_OSV_SCANNER": str(executable)}, clear=False
            ):
                result = SecurityEngine(
                    root,
                    self._osv_policy(self._osv_root(), executable),
                    tracked_files=["requirements.txt"],
                    command_runner=self._osv_runner(payload),
                ).run_risk()

            self.assertEqual("passed", result.status)
            self.assertEqual(2, result.as_dict()["summary"]["passed"])
            self.assertEqual(
                hashlib.sha256(executable.read_bytes()).hexdigest(),
                result.checks[0].scanner["executable_sha256"],
            )

    def test_osv_unknown_severity_and_license_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "osv-scanner"
            executable.write_bytes(b"governed scanner")
            (root / "requirements.txt").write_text(
                "fixture-package==1.2.3\n", encoding="utf-8"
            )
            payload = {
                "results": [
                    {
                        "packages": [
                            {
                                "package": {
                                    "name": "fixture-package",
                                    "version": "1.2.3",
                                    "ecosystem": "PyPI",
                                },
                                "licenses": ["UNKNOWN"],
                                "vulnerabilities": [
                                    {"id": "OSV-FIXTURE-1", "summary": "fixture"}
                                ],
                            }
                        ]
                    }
                ]
            }
            with patch.dict(
                "os.environ", {"STRLING_OSV_SCANNER": str(executable)}, clear=False
            ):
                result = SecurityEngine(
                    root,
                    self._osv_policy(self._osv_root(), executable),
                    tracked_files=["requirements.txt"],
                    command_runner=self._osv_runner(payload),
                ).run_risk()

            self.assertEqual("failed", result.status)
            self.assertEqual("SEC-VULN-BLOCKING", result.checks[0].findings[0].code)
            self.assertEqual("SEC-LICENSE-UNKNOWN", result.checks[1].findings[0].code)

    def test_osv_metadata_override_replaces_reported_license(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "osv-scanner"
            executable.write_bytes(b"governed scanner")
            (root / "requirements.txt").write_text(
                "fixture-package==1.2.3\n", encoding="utf-8"
            )
            configured = self._osv_policy(self._osv_root(), executable)
            configured["license_policy"]["metadata_overrides"] = [
                {
                    "ecosystem": "python",
                    "package": "fixture-package",
                    "version": "1.2.3",
                    "license": "MIT",
                    "evidence": "fixture metadata correction",
                }
            ]
            payload = {
                "results": [
                    {
                        "packages": [
                            {
                                "package": {
                                    "name": "fixture-package",
                                    "version": "1.2.3",
                                    "ecosystem": "PyPI",
                                },
                                "licenses": ["non-standard"],
                            }
                        ]
                    }
                ]
            }
            with patch.dict(
                "os.environ", {"STRLING_OSV_SCANNER": str(executable)}, clear=False
            ):
                result = SecurityEngine(
                    root,
                    configured,
                    tracked_files=["requirements.txt"],
                    command_runner=self._osv_runner(payload),
                ).run_risk()

            self.assertEqual("passed", result.status)
            license_check = next(
                check for check in result.checks if check.category == "license"
            )
            self.assertEqual(1, license_check.scanner["classifications"]["overridden"])
            self.assertEqual(
                "MIT", license_check.scanner["components"][0]["reported_license"]
            )

    def test_osv_scanner_hash_drift_fails_before_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "osv-scanner"
            executable.write_bytes(b"governed scanner")
            (root / "requirements.txt").write_text("", encoding="utf-8")
            configured = self._osv_policy(self._osv_root(), executable)
            configured["security_tools"]["osv-scanner"]["sha256"] = {
                "windows_amd64": "0" * 64,
                "linux_amd64": "0" * 64,
            }
            with patch.dict(
                "os.environ", {"STRLING_OSV_SCANNER": str(executable)}, clear=False
            ):
                result = SecurityEngine(
                    root,
                    configured,
                    tracked_files=["requirements.txt"],
                    command_runner=self._osv_runner({"results": []}),
                ).run_risk()

            self.assertEqual("failed", result.status)
            self.assertEqual("SEC-TOOL-HASH-DRIFT", result.checks[0].findings[0].code)

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

    def test_hash_pinned_requirements_accepts_hashes_and_rejects_omission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("fixture>=1\n", encoding="utf-8")
            lock = root / "requirements.lock.txt"
            lock.write_text(
                f"fixture==1.2.3 \\\n    --hash=sha256:{'a' * 64}\n",
                encoding="utf-8",
            )
            dependency = {
                "manifests": ["requirements.txt"],
                "locks": ["requirements.lock.txt"],
            }
            engine = SecurityEngine(root, policy(npm_root()), tracked_files=[])
            self.assertEqual([], engine._validate_hash_pinned_requirements(dependency))

            lock.write_text("fixture==1.2.3\n", encoding="utf-8")
            findings = engine._validate_hash_pinned_requirements(dependency)
            self.assertEqual("SEC-DEP-INTEGRITY-MISSING", findings[0].code)

    def test_gradle_lock_requires_sha256_verification_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build.gradle.kts").write_text(
                'dependencies { implementation("fixture:core:1.2.3") }\n',
                encoding="utf-8",
            )
            (root / "gradle.lockfile").write_text(
                "fixture:core:1.2.3=runtimeClasspath\n", encoding="utf-8"
            )
            verification = root / "verification-metadata.xml"
            verification.write_text(
                f'<verification-metadata><sha256 value="{"b" * 64}"/></verification-metadata>',
                encoding="utf-8",
            )
            dependency = {
                "ecosystem": "gradle",
                "manifests": ["build.gradle.kts"],
                "locks": ["gradle.lockfile", "verification-metadata.xml"],
            }
            engine = SecurityEngine(root, policy(npm_root()), tracked_files=[])
            self.assertEqual([], engine._validate_gradle_lock(dependency))

            verification.write_text(
                '<verification-metadata><sha256 value="invalid"/></verification-metadata>',
                encoding="utf-8",
            )
            findings = engine._validate_gradle_lock(dependency)
            self.assertEqual("SEC-DEP-INTEGRITY-MISSING", findings[0].code)

    def test_native_composer_and_renv_license_evidence_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "composer.lock").write_text(
                json.dumps(
                    {
                        "packages": [
                            {
                                "name": "fixture/runtime",
                                "version": "1.2.3",
                                "license": ["MIT"],
                            }
                        ],
                        "packages-dev": [],
                    }
                ),
                encoding="utf-8",
            )
            (root / "renv.lock").write_text(
                json.dumps(
                    {
                        "R": {"Version": "4.3.3"},
                        "Packages": {
                            "fixtureR": {
                                "Package": "fixtureR",
                                "Version": "1.2.3",
                                "Source": "Repository",
                                "License": "MIT + file LICENSE",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            engine = SecurityEngine(root, policy(npm_root()), tracked_files=[])
            composer, composer_error = engine._native_lock_licenses(
                {"ecosystem": "composer", "locks": ["composer.lock"]}
            )
            renv, renv_error = engine._native_lock_licenses(
                {"ecosystem": "r", "locks": ["renv.lock"]}
            )
            self.assertIsNone(composer_error)
            self.assertEqual(["MIT"], composer[("fixture/runtime", "1.2.3")])
            self.assertIsNone(renv_error)
            self.assertEqual(["MIT"], renv[("fixtureR", "1.2.3")])

            malformed = json.loads((root / "renv.lock").read_text(encoding="utf-8"))
            del malformed["Packages"]["fixtureR"]["License"]
            (root / "renv.lock").write_text(json.dumps(malformed), encoding="utf-8")
            _, renv_error = engine._native_lock_licenses(
                {"ecosystem": "r", "locks": ["renv.lock"]}
            )
            self.assertEqual(
                "renv lock package license identity is incomplete", renv_error
            )

    def test_hash_bound_dart_license_evidence_accepts_match_and_rejects_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_sha256 = "a" * 64
            license_sha256 = "b" * 64
            (root / "pubspec.lock").write_text(
                """packages:
  fixture:
    dependency: direct main
    description:
      name: fixture
      sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
      url: https://pub.dev
    source: hosted
    version: 1.2.3
""",
                encoding="utf-8",
            )
            evidence = {
                "document_kind": "dependency-license-evidence",
                "schema_version": "1.0.0",
                "sources": ["pubspec.lock"],
                "entries": [
                    {
                        "archive_sha256": archive_sha256,
                        "archive_url": "https://pub.dev/api/archives/fixture-1.2.3.tar.gz",
                        "ecosystem": "dart-pub",
                        "license": "BSD-3-Clause",
                        "license_path": "LICENSE",
                        "license_sha256": license_sha256,
                        "package": "fixture",
                        "registry_metadata_url": "https://pub.dev/api/packages/fixture/versions/1.2.3",
                        "version": "1.2.3",
                    }
                ],
            }
            evidence["fingerprint"] = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(
                        evidence,
                        allow_nan=False,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                ).hexdigest()
            )
            (root / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
            configured = policy(npm_root())
            configured["license_policy"]["evidence_manifest"] = "evidence.json"
            engine = SecurityEngine(root, configured, tracked_files=[])
            licenses, error = engine._native_lock_licenses(
                {"ecosystem": "dart-pub", "locks": ["pubspec.lock"]}
            )
            self.assertIsNone(error)
            self.assertEqual(["BSD-3-Clause"], licenses[("fixture", "1.2.3")])

            evidence["entries"][0]["archive_sha256"] = "c" * 64
            (root / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
            _, error = engine._native_lock_licenses(
                {"ecosystem": "dart-pub", "locks": ["pubspec.lock"]}
            )
            self.assertEqual(
                "license evidence manifest is malformed or has fingerprint drift", error
            )

    def test_disjunctive_license_is_permitted_only_with_a_permitted_branch(
        self,
    ) -> None:
        engine = SecurityEngine(Path("."), policy(npm_root()), tracked_files=[])
        self.assertEqual(
            "permitted",
            engine._license_classification("LGPL-2.1-or-later OR Apache-2.0"),
        )
        self.assertEqual(
            "unknown",
            engine._license_classification("GPL-2.0-only OR GPL-3.0-only"),
        )

    def test_renv_lock_qualifies_exact_repository_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "DESCRIPTION").write_text(
                "Package: fixture\nImports: jsonlite (>= 1.8.8)\nSuggests: testthat\n",
                encoding="utf-8",
            )
            lock = {
                "R": {"Version": "4.3.3"},
                "Packages": {
                    name: {
                        "Package": name,
                        "Version": "1.2.3",
                        "Source": "Repository",
                        "License": "MIT + file LICENSE",
                    }
                    for name in ("jsonlite", "testthat")
                },
            }
            (root / "renv.lock").write_text(json.dumps(lock), encoding="utf-8")
            dependency = {
                "manifests": ["DESCRIPTION"],
                "locks": ["renv.lock"],
            }
            engine = SecurityEngine(root, policy(npm_root()), tracked_files=[])
            self.assertEqual([], engine._validate_renv_lock(dependency))

            del lock["Packages"]["testthat"]
            (root / "renv.lock").write_text(json.dumps(lock), encoding="utf-8")
            findings = engine._validate_renv_lock(dependency)
            self.assertEqual("SEC-DEP-MANIFEST-LOCK-MISMATCH", findings[0].code)

    def test_test_source_contains_no_functional_credential_fixture(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        for _, _, pattern in SECRET_PATTERNS:
            self.assertIsNone(pattern.search(source))
        self.assertIsNone(GENERIC_CREDENTIAL_PATTERN.search(source))


if __name__ == "__main__":
    unittest.main()
