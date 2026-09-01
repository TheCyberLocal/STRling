from __future__ import annotations

import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch
from uuid import uuid4

from tooling.production_certification import (
    build_certification_environment,
    capture,
    fingerprint,
    load_capacity_contract,
    materialize_governed_production_inputs,
    parse_args,
    profile_summary,
    product_summary,
    release_profile_command,
    require_runtime_capacity_reserve,
    render_report,
    storage_capacity_evidence,
)


class ProductionCertificationTests(unittest.TestCase):
    @contextmanager
    def temporary_directory(self) -> Iterator[Path]:
        root = (
            Path(__file__).resolve().parents[2]
            / "target"
            / "codex-tools"
            / "production-certification-tests"
        )
        root.mkdir(parents=True, exist_ok=True)
        directory = root / uuid4().hex
        directory.mkdir()
        try:
            yield directory
        finally:
            rmtree(directory, ignore_errors=True)

    @patch(
        "tooling.production_certification.subprocess.run",
        side_effect=FileNotFoundError("missing-tool"),
    )
    def test_fingerprint_probe_records_missing_executable(self, _run) -> None:
        result = capture(["missing-tool"])
        self.assertEqual(127, result.returncode)
        self.assertIn("missing-tool", result.stderr)

    def test_canonical_alias_requires_every_no_reuse_release_flag(self) -> None:
        args = parse_args(["--profile", "release", "--all", "--no-reuse", "--plain"])
        self.assertEqual("release", args.profile)
        self.assertTrue(args.all)
        self.assertTrue(args.no_reuse)
        self.assertTrue(args.plain)

    def test_all_production_stages_preserve_release_profile_membership(self) -> None:
        command = release_profile_command(Path("/tmp/profile-release.json"))
        self.assertEqual("release", command[2])
        self.assertNotIn("all", command)
        self.assertEqual("--artifact", command[3])

    def test_report_is_derived_from_structured_evidence(self) -> None:
        artifact = {
            "deterministic_evidence": {
                "status": "passed",
                "source": {"sha": "a" * 40},
                "command": "canonical command",
                "no_reuse": {"honored": True},
                "aggregate": {
                    "status": "passed",
                    "passed": 122,
                    "failed": 0,
                    "unavailable": 0,
                    "incomplete": 0,
                },
                "artifacts": {"profile": "/tmp/profile.json"},
            }
        }
        report = render_report(artifact)
        self.assertIn("Passed operations: `122`", report)
        self.assertIn("Failed operations: `0`", report)
        self.assertIn("No reuse: `true`", report)

    def test_fingerprint_is_order_independent(self) -> None:
        self.assertEqual(fingerprint({"a": 1, "b": 2}), fingerprint({"b": 2, "a": 1}))

    def test_capacity_contract_is_derived_from_observed_release_outputs(self) -> None:
        contract = load_capacity_contract()
        measurement = contract["measurement_basis"]
        self.assertEqual(
            measurement["observed_transient_bytes"],
            sum(family["bytes"] for family in measurement["families"]),
        )
        self.assertLessEqual(
            measurement["observed_transient_bytes"],
            contract["rounded_workspace_envelope_bytes"],
        )
        self.assertEqual(
            contract["maximum_expected_transient_bytes"],
            contract["rounded_workspace_envelope_bytes"]
            * contract["simultaneous_workspace_envelopes"],
        )
        self.assertEqual(
            contract["required_free_bytes"],
            contract["maximum_expected_transient_bytes"]
            + contract["safety_margin_bytes"],
        )

    def test_capacity_preflight_fails_closed_below_required_bytes(self) -> None:
        contract = load_capacity_contract()
        evidence = storage_capacity_evidence(
            free_bytes=contract["required_free_bytes"] - 1,
            contract=contract,
        )
        self.assertEqual("failed", evidence["status"])

    def test_capacity_preflight_accepts_current_host_scale(self) -> None:
        contract = load_capacity_contract()
        evidence = storage_capacity_evidence(
            free_bytes=int(135.28 * 1024**3),
            contract=contract,
        )
        self.assertEqual("passed", evidence["status"])
        self.assertEqual(112 * 1024**3, evidence["required_free_bytes"])

    def test_stage_boundary_reserve_fails_closed(self) -> None:
        contract = load_capacity_contract()
        with patch("tooling.production_certification.shutil.disk_usage") as disk_usage:
            disk_usage.return_value.free = contract["safety_margin_bytes"] - 1
            with self.assertRaisesRegex(RuntimeError, "exhausted its capacity reserve"):
                require_runtime_capacity_reserve(
                    contract=contract, root=Path("repository")
                )

    def test_hash_bound_historical_input_materializes_into_clean_worktree(self) -> None:
        with self.temporary_directory() as directory:
            root = Path(directory)
            authority = root / "authority"
            worktree = root / "worktree"
            relative = Path(
                "artifacts/production-certification/baseline/run/production-candidate-certification.json"
            )
            payload = b'{"status":"passed"}\n'
            (authority / relative).parent.mkdir(parents=True)
            (authority / relative).write_bytes(payload)
            inventory = worktree / "governance/legacy-removal-inventory.json"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                "{\n"
                '  "source": {\n'
                f'    "production_certification_path": "{relative.as_posix()}",\n'
                f'    "production_certification_sha256": "{sha256(payload).hexdigest()}"\n'
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            evidence = materialize_governed_production_inputs(
                authority_root=authority, worktree=worktree
            )
            self.assertEqual(payload, (worktree / relative).read_bytes())
            self.assertEqual(sha256(payload).hexdigest(), evidence[0]["sha256"])

    def test_governed_input_materialization_rejects_path_escape(self) -> None:
        with self.temporary_directory() as directory:
            root = Path(directory)
            worktree = root / "worktree"
            inventory = worktree / "governance/legacy-removal-inventory.json"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                '{"source":{"production_certification_path":"../outside.json",'
                '"production_certification_sha256":"' + "0" * 64 + '"}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "unsafe path"):
                materialize_governed_production_inputs(
                    authority_root=root / "authority", worktree=worktree
                )

    def test_governed_input_materialization_rejects_missing_input(self) -> None:
        with self.temporary_directory() as directory:
            root = Path(directory)
            worktree = root / "worktree"
            inventory = worktree / "governance/legacy-removal-inventory.json"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                '{"source":{"production_certification_path":'
                '"artifacts/production-certification/missing/run/evidence.json",'
                '"production_certification_sha256":"' + "0" * 64 + '"}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "is unavailable"):
                materialize_governed_production_inputs(
                    authority_root=root / "authority", worktree=worktree
                )

    def test_governed_input_materialization_rejects_hash_drift(self) -> None:
        with self.temporary_directory() as directory:
            root = Path(directory)
            authority = root / "authority"
            worktree = root / "worktree"
            relative = Path(
                "artifacts/production-certification/baseline/run/production-candidate-certification.json"
            )
            (authority / relative).parent.mkdir(parents=True)
            (authority / relative).write_text("changed", encoding="utf-8")
            inventory = worktree / "governance/legacy-removal-inventory.json"
            inventory.parent.mkdir(parents=True)
            inventory.write_text(
                "{\n"
                '  "source": {\n'
                f'    "production_certification_path": "{relative.as_posix()}",\n'
                f'    "production_certification_sha256": "{"0" * 64}"\n'
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "hash changed"):
                materialize_governed_production_inputs(
                    authority_root=authority, worktree=worktree
                )

    @patch.dict("os.environ", {}, clear=True)
    def test_release_environment_pins_exact_certification_runtimes(self) -> None:
        environment = build_certification_environment()
        self.assertEqual("/opt/temurin-11.0.32+9", environment["JAVA_HOME"])
        self.assertEqual(
            "/root/.m2/repository", environment["STRLING_MAVEN_REPOSITORY"]
        )
        self.assertIn("cpython-3.11.15", environment["STRLING_CPYTHON_311_BINARY"])
        self.assertEqual("1", environment["COMPOSER_ALLOW_SUPERUSER"])
        self.assertEqual("1", environment["COMPOSER_NO_INTERACTION"])
        self.assertEqual("1", environment["STRLING_CERTIFICATION_NO_REUSE"])

    def test_profile_summary_is_derived_from_wrapped_profile_evidence(self) -> None:
        summary = profile_summary(
            {
                "deterministic_evidence": {
                    "aggregate": {
                        "status": "failed",
                        "operation_count": 9,
                        "counts": {
                            "passed": 6,
                            "failed": 1,
                            "unavailable": 1,
                            "incomplete": 1,
                            "waived": 0,
                        },
                    }
                }
            }
        )
        self.assertEqual(9, summary["total"])
        self.assertEqual(1, summary["failed"])
        self.assertEqual(1, summary["unavailable"])
        self.assertEqual(1, summary["incomplete"])

    def test_product_summary_is_derived_from_product_evidence(self) -> None:
        summary = product_summary(
            {
                "schema_version": "1.0.0",
                "evidence_fingerprint": "product-fingerprint",
                "deterministic_evidence": {
                    "authority": {
                        "source_profile": {
                            "artifact_schema_version": "2.0.0",
                            "definition_fingerprint": "profile-fingerprint",
                        }
                    },
                    "source_profile_evidence": {
                        "profile": {"definition_version": "4.0.0"}
                    },
                    "results": [
                        {
                            "evidence_area": "security",
                            "status": "passed",
                            "waiver_references": ["WVR-001"],
                        },
                        {"evidence_area": "security", "status": "passed"},
                    ],
                    "aggregate": {"status": "passed"},
                },
            }
        )
        self.assertEqual({"passed": 2}, summary["evidence_areas"]["security"])
        self.assertEqual(["WVR-001"], summary["waiver_references"])
        self.assertEqual("4.0.0", summary["profile_definition_version"])


if __name__ == "__main__":
    unittest.main()
