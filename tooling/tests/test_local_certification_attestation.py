from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tooling.certification import (
    build_certification_artifact,
    write_certification_artifact,
)
from tooling.local_certification_attestation import (
    AttestationError,
    _public_key_fingerprint,
    _sign,
    canonical_bytes,
    create_attestation,
    file_sha256,
    object_sha256,
    verify_attestation,
)


ROOT = Path(__file__).resolve().parents[2]
CERTIFIER_ID = "test-local-certifier"
INVOCATION_ID = "a" * 32


class LocalCertificationAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_root = None
        if os.name == "nt":
            (ROOT / "target").mkdir(exist_ok=True)
            temporary_root = ROOT / "target"
        self.temporary = tempfile.TemporaryDirectory(
            dir=temporary_root, prefix="local-attestation-test-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repository = self.base / "repository"
        self.inputs = self.base / "inputs"
        self.bundle = self.base / "bundle"
        self.repository.mkdir()
        self.inputs.mkdir()
        (self.repository / "governance/schemas").mkdir(parents=True)
        (self.repository / "spec/targets/profiles").mkdir(parents=True)
        (self.repository / "core").mkdir()
        (self.repository / "bindings/interop").mkdir(parents=True)
        for name in (
            "profile-certification-artifact.schema.json",
            "local-certification-attestation.schema.json",
            "local-certification-trust.schema.json",
        ):
            shutil.copyfile(
                ROOT / "governance/schemas" / name,
                self.repository / "governance/schemas" / name,
            )
        self.private_key = self.base / "certifier"
        subprocess.run(
            [
                "ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-f",
                str(self.private_key),
            ],
            check=True,
        )
        public_key = subprocess.run(
            ["ssh-keygen", "-y", "-f", str(self.private_key)],
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout.strip()
        self.trust = {
            "$schema": "https://strling.dev/governance/local-certification-trust.schema.json",
            "schema_version": "1.0.0",
            "policy_kind": "strling-local-certification-trust",
            "signature_namespace": "strling-local-certification-v1",
            "bundle_path": "tests/certification/hardened-core/1.0/current",
            "required_profiles": ["full", "release"],
            "allowed_waivers": ["WVR-SEC-VSCE-LICENSE-001"],
            "closure_paths": ["docs/certification/**"],
            "authorized_certifiers": [
                {
                    "certifier_id": CERTIFIER_ID,
                    "public_key": public_key,
                    "ssh_key_fingerprint": _public_key_fingerprint(public_key),
                    "authorized_profiles": ["full", "release"],
                    "status": "active",
                }
            ],
        }
        (self.repository / "governance/local-certification-trust.json").write_text(
            json.dumps(self.trust, indent=2) + "\n", encoding="utf-8"
        )
        self.profiles = {
            name: {
                "definition_version": "1.0.0",
                "purpose": f"test {name}",
                "network_policy": "allowed",
                "operations": [
                    {"operation": "performance_resource_full_certification"},
                    {"operation": "adversarial_real_engine_equivalence"},
                ],
            }
            for name in ("full", "release")
        }
        toolchain = {
            "policy": {
                "profiles": self.profiles,
                "operation_registry": {
                    "performance_resource_full_certification": {"kind": "repository"},
                    "adversarial_real_engine_equivalence": {"kind": "repository"},
                },
            }
        }
        (self.repository / "toolchain.json").write_text(
            json.dumps(toolchain, indent=2) + "\n", encoding="utf-8"
        )
        target_profile = {
            "contract_version": "1.0.0",
            "profile_id": "profile:test/1",
            "profile_version": "1.0.0",
        }
        (self.repository / "spec/targets/profiles/test.json").write_text(
            json.dumps(target_profile) + "\n", encoding="utf-8"
        )
        (self.repository / "core/kernel.rs").write_text("kernel\n", encoding="utf-8")
        (self.repository / "bindings/interop/lib.rs").write_text(
            "interop\n", encoding="utf-8"
        )
        self._git("init")
        self._git("config", "user.email", "tests@strling.dev")
        self._git("config", "user.name", "STRling tests")
        self._git("add", ".")
        self._git("commit", "-m", "fixture")
        self.source_sha = self._git("rev-parse", "HEAD")
        for profile in ("full", "release"):
            artifact = build_certification_artifact(
                root=self.repository,
                profile_id=profile,
                profile_definition=self.profiles[profile],
                requested_component=None,
                results=self._results(profile),
                aggregate_status="passed",
                exit_code=0,
                resolved_repository_state={"commit": self.source_sha, "dirty": False},
            )
            write_certification_artifact(self.inputs / f"{profile}.json", artifact)
        create_attestation(
            repository_root=self.repository,
            trust_root=self.repository,
            output_dir=self.bundle,
            full_artifact=self.inputs / "full.json",
            release_artifact=self.inputs / "release.json",
            extra_evidence=[],
            private_key=self.private_key,
            certifier_id=CERTIFIER_ID,
            invocation_id=INVOCATION_ID,
        )

    def _git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.repository,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.strip()

    @staticmethod
    def _results(profile: str) -> list[dict[str, object]]:
        real_engine = {
            "schema_version": "1.0.0",
            "operation_id": "certification.adversarial-real-engine-equivalence",
            "status": "passed",
            "checks": [
                {
                    "check_id": "certification.adversarial-real-engine-equivalence.matrix",
                    "status": "passed",
                    "evidence": {
                        "counts": {
                            "semantic_cases": 41,
                            "subjects": 95,
                            "target_profile_compiles": 205,
                            "runtime_executions": 1531,
                            "governed_refusals": 48,
                            "cross_profile_comparisons": 1129,
                        },
                        "runtime_identities": {"node": {"version": "v22.23.2"}},
                        "findings": [],
                        "unaccounted_observations": 0,
                        "run_id": ("1" if profile == "full" else "2") * 64,
                    },
                }
            ],
            "summary": {
                "passed": 1,
                "failed": 0,
                "waived": 0,
                "unavailable": 0,
                "incomplete": 0,
            },
        }
        performance = {
            "schema_version": "1.0.0",
            "operation_id": "certification.performance-resource-full",
            "status": "passed",
        }
        return [
            {
                "operation": "performance_resource_full_certification",
                "component": "repository",
                "status": "passed",
                "command": ["performance"],
                "exit_code": 0,
                "reason": None,
                "capability": None,
                "formatters": [],
                "environment": [],
                "structured_result": performance,
                "execution_integrity": {
                    "invocation_id": ("3" if profile == "full" else "4") * 32,
                    "sample_consumption": {"authenticated_sample_count": 3204},
                },
            },
            {
                "operation": "adversarial_real_engine_equivalence",
                "component": "repository",
                "status": "passed",
                "command": ["audit"],
                "exit_code": 0,
                "reason": None,
                "capability": None,
                "formatters": [],
                "environment": [],
                "structured_result": real_engine,
            },
        ]

    def _attestation(self) -> dict:
        return json.loads(
            (self.bundle / "attestation.json").read_text(encoding="utf-8")
        )

    def _write_resigned(self, attestation: dict) -> None:
        payload = attestation["signed_payload"]
        projection = copy.deepcopy(payload)
        projection.pop("evidence_root_sha256", None)
        payload["evidence_root_sha256"] = object_sha256(projection)
        signed = canonical_bytes(payload)
        signature = _sign(signed, self.private_key, "strling-local-certification-v1")
        attestation["signature"].update(
            {
                "signature_base64": base64.b64encode(signature).decode("ascii"),
                "signature_sha256": hashlib.sha256(signature).hexdigest(),
                "signed_payload_sha256": hashlib.sha256(signed).hexdigest(),
            }
        )
        (self.bundle / "attestation.json").write_text(
            json.dumps(attestation, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _resign_payload_mutation(self, mutator) -> None:
        attestation = self._attestation()
        mutator(attestation["signed_payload"])
        self._write_resigned(attestation)

    def test_valid_attestation_passes(self) -> None:
        result = verify_attestation(
            repository_root=self.repository,
            trust_root=self.repository,
            bundle_dir=self.bundle,
        )
        self.assertEqual("CLOUD_VERIFIED", result["certification_state"])

    def test_source_changed_after_certification_is_rejected(self) -> None:
        (self.repository / "core/kernel.rs").write_text("changed\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "change source")
        with self.assertRaisesRegex(AttestationError, "outside closure paths"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_one_evidence_byte_changed_is_rejected(self) -> None:
        path = self.bundle / "evidence/profile-full/full.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(AttestationError, "size mismatch"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_missing_evidence_file_is_rejected(self) -> None:
        (self.bundle / "evidence/profile-release/release.json").unlink()
        with self.assertRaisesRegex(AttestationError, "presence mismatch"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_wrong_profile_fingerprint_is_rejected(self) -> None:
        self._resign_payload_mutation(
            lambda payload: payload["profile_results"][0].update(
                definition_fingerprint="0" * 64
            )
        )
        with self.assertRaisesRegex(AttestationError, "profile result aggregate"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_stale_attestation_replay_is_rejected(self) -> None:
        (self.repository / "outside.txt").write_text("new source\n", encoding="utf-8")
        self._git("add", ".")
        self._git("commit", "-m", "advance")
        with self.assertRaisesRegex(AttestationError, "outside closure paths"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_untrusted_certifier_is_rejected(self) -> None:
        trust = copy.deepcopy(self.trust)
        trust["authorized_certifiers"][0]["certifier_id"] = "other-certifier"
        (self.repository / "governance/local-certification-trust.json").write_text(
            json.dumps(trust), encoding="utf-8"
        )
        with self.assertRaisesRegex(AttestationError, "not uniquely authorized"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_malformed_signature_is_rejected(self) -> None:
        attestation = self._attestation()
        attestation["signature"]["signature_base64"] = "not-base64"
        (self.bundle / "attestation.json").write_text(
            json.dumps(attestation), encoding="utf-8"
        )
        with self.assertRaises(AttestationError):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_passing_aggregate_with_failed_producer_is_rejected(self) -> None:
        path = self.bundle / "evidence/profile-full/full.json"
        artifact = json.loads(path.read_text(encoding="utf-8"))
        artifact["deterministic_evidence"]["operations"][0]["structured_evidence"][
            "status"
        ] = "failed"
        artifact["evidence_fingerprint"] = object_sha256(
            artifact["deterministic_evidence"]
        )
        path.write_text(
            json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        attestation = self._attestation()
        entry = next(
            item
            for item in attestation["signed_payload"]["evidence_files"]
            if item["path"] == "evidence/profile-full/full.json"
        )
        entry["bytes"] = path.stat().st_size
        entry["sha256"] = file_sha256(path)
        attestation["signed_payload"]["profile_results"][0]["evidence_fingerprint"] = (
            artifact["evidence_fingerprint"]
        )
        self._write_resigned(attestation)
        with self.assertRaisesRegex(AttestationError, "outer status contradicts"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_performance_sample_count_altered_is_rejected(self) -> None:
        self._resign_payload_mutation(
            lambda payload: payload["authenticated_sample_counts"].update(
                {next(iter(payload["authenticated_sample_counts"])): 1}
            )
        )
        with self.assertRaisesRegex(AttestationError, "sample count mismatch"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_real_engine_evidence_altered_is_rejected(self) -> None:
        self._resign_payload_mutation(
            lambda payload: payload["real_engine_evidence"].update(
                runtime_executions=1530
            )
        )
        with self.assertRaisesRegex(AttestationError, "real-engine evidence aggregate"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_waiver_added_after_certification_is_rejected(self) -> None:
        self._resign_payload_mutation(
            lambda payload: payload["waiver_inventory"].append("WVR-FAKE-001")
        )
        with self.assertRaisesRegex(AttestationError, "waiver inventory"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_wrong_invocation_id_is_rejected(self) -> None:
        self._resign_payload_mutation(
            lambda payload: payload["producer_invocation_ids"].append("f" * 32)
        )
        with self.assertRaisesRegex(AttestationError, "producer invocation"):
            verify_attestation(
                repository_root=self.repository,
                trust_root=self.repository,
                bundle_dir=self.bundle,
            )

    def test_evidence_root_is_deterministically_reproducible(self) -> None:
        payload = self._attestation()["signed_payload"]
        root = payload.pop("evidence_root_sha256")
        self.assertEqual(root, object_sha256(payload))


if __name__ == "__main__":
    unittest.main()
