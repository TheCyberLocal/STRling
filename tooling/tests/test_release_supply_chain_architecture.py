from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tooling/release_supply_chain.py"
SCHEMA = ROOT / "governance/schemas/release-supply-chain-certification.schema.json"
MANIFEST = ROOT / "tests/certification/release-supply-chain/1.0/manifest.json"
FIXTURE = (
    ROOT / "tests/certification/release-supply-chain/1.0/fixtures/valid-evidence.json"
)
TASK = ROOT / "docs/migration/records/release-supply-chain-certification.yaml"
CHANGE_CONTROL = ROOT / "governance/change-control.json"


class ReleaseSupplyChainArchitectureTests(unittest.TestCase):
    def test_controller_is_verification_only_and_offline_at_cp3(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        for forbidden in (
            "from core",
            "import core",
            "from bindings",
            "import bindings",
            "requests",
            "urllib",
            "socket",
            "shell=True",
            "git push",
            "npm publish",
            "cargo publish",
            "dotnet nuget push",
            "twine upload",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("publication_authorized", source)
        self.assertIn("synthetic evidence cannot claim live profile authority", source)
        self.assertIn("release evidence requires a clean source tree", source)
        self.assertIn("evidence output directory must not already exist", source)
        self.assertIn("actions/upload-artifact@", source)
        self.assertIn("actions/download-artifact@", source)
        self.assertIn("checksum-subject", source)
        self.assertIn("provenance-subject", source)
        self.assertIn("false-pass", source)

    def test_schema_is_engineering_only_and_uses_locked_standards(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            "https://strling.dev/governance/release-supply-chain-certification.schema.json",
            schema["$id"],
        )
        serialized = json.dumps(schema)
        for required in (
            "SPDX-2.3-json",
            "https://in-toto.io/Statement/v1",
            "https://slsa.dev/provenance/v1",
            "publication_authorized",
            "synthetic-contract-fixture",
        ):
            self.assertIn(required, serialized)
        for forbidden in ("CompileRequest", "TargetArtifact", "language semantics"):
            self.assertNotIn(forbidden, serialized)

    def test_manifest_matches_exact_workflow_release_denominator(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        workflow = (ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8")
        artifacts = manifest["artifacts"]
        self.assertEqual(17, len(artifacts))
        self.assertEqual(
            [
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
            ],
            [item["id"] for item in artifacts],
        )
        for item in artifacts:
            self.assertIn(f"    {item['compile_job']}:", workflow)
            self.assertIn(f"    {item['publish_job']}:", workflow)
            self.assertTrue(item["sbom_policy"]["required"])
            self.assertTrue(item["provenance_policy"]["required"])
            self.assertFalse(manifest["profile_policy"]["release"]["publication"])

        python_artifact = next(
            item for item in artifacts if item["id"] == "release:python"
        )
        self.assertEqual(
            ["interop-cargo", "python-binding"], python_artifact["dependency_roots"]
        )
        self.assertEqual(
            ["cargo", "python", "rustc"], python_artifact["toolchain_refs"]
        )

    def test_native_package_builds_prefetch_locked_cargo_graphs(self) -> None:
        workflow = (ROOT / ".github/workflows/cd.yml").read_text(encoding="utf-8")
        for command in (
            "cargo +1.75.0 fetch --manifest-path bindings/interop/Cargo.toml --locked",
            "cargo +1.75.0 fetch --manifest-path .rebuild/bindings/interop/Cargo.toml --locked",
            "cargo +1.75.0 fetch --manifest-path bindings/interop/Cargo.toml --locked --target wasm32-unknown-unknown",
            "cargo +1.75.0 fetch --manifest-path .rebuild/bindings/interop/Cargo.toml --locked --target wasm32-unknown-unknown",
        ):
            self.assertEqual(1, workflow.count(f"- run: {command}\n"))

    def test_fixture_explicitly_denies_live_and_publication_authority(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual("synthetic-contract-fixture", fixture["evidence_kind"])
        self.assertFalse(fixture["publication_authorized"])
        details = fixture["checks"][0]["details"]
        self.assertTrue(details["synthetic"])
        self.assertFalse(details["live_artifact"])
        self.assertFalse(details["publication_authority"])

    def test_active_change_control_and_task_scope_are_exact(self) -> None:
        change_control = json.loads(CHANGE_CONTROL.read_text(encoding="utf-8"))
        self.assertEqual(
            "docs/migration/records/release-supply-chain-certification.yaml",
            change_control["active_task"],
        )
        task = TASK.read_text(encoding="utf-8")
        for required in (
            "- core/src/lib_public.rs",
            "- spec/frontends/simply/1.0/README.md",
            "one publishable strling crate",
            "publication, release creation, upload, tag push, and branch push",
            "package versions, support tiers, performance contracts",
            "SPDX 2.3 JSON",
            "SLSA Provenance v1",
        ):
            self.assertIn(required, task)


if __name__ == "__main__":
    unittest.main()
