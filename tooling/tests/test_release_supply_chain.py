from __future__ import annotations

import copy
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tooling.release_supply_chain import (
    ARTIFACT_IDS,
    MANIFEST_PATH,
    OIDC_ARTIFACT_IDS,
    SCHEMA_PATH,
    VALID_FIXTURE_PATH,
    ReleaseSupplyChainError,
    document_fingerprint,
    load_json,
    run_contract_check,
    synthetic_evidence,
    validate_contract_fixture,
    validate_evidence,
    validate_manifest,
    validate_schema,
)


class ReleaseSupplyChainContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_json(MANIFEST_PATH)
        self.fixture = load_json(VALID_FIXTURE_PATH)

    def assert_rejected(
        self,
        callable_: Any,
        code: str,
    ) -> ReleaseSupplyChainError:
        with self.assertRaises(ReleaseSupplyChainError) as raised:
            callable_()
        self.assertEqual(code, raised.exception.code)
        return raised.exception

    @staticmethod
    def resign_evidence(evidence: dict[str, Any]) -> None:
        evidence["evidence_fingerprint"] = document_fingerprint(
            evidence, "evidence_fingerprint"
        )

    @staticmethod
    def resign_fixture(fixture: dict[str, Any]) -> None:
        fixture["evidence_fingerprint"] = document_fingerprint(
            fixture, "evidence_fingerprint"
        )

    def test_schema_manifest_fixture_and_contract_check_pass(self) -> None:
        schema = load_json(SCHEMA_PATH)
        Draft202012Validator.check_schema(schema)
        validate_schema(self.manifest, label="manifest")
        validate_manifest(self.manifest)
        validate_contract_fixture(self.fixture, self.manifest)
        result = run_contract_check()
        self.assertEqual("passed", result["status"])
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(17, result["artifact_count"])

    def test_manifest_is_structurally_deterministic(self) -> None:
        first = document_fingerprint(self.manifest)
        second = document_fingerprint(load_json(MANIFEST_PATH))
        self.assertEqual(first, second)
        self.assertEqual(
            "7f957aa6a5b08d283aa610924d06b7e347874eea7ede2f8604035b2a03b0b5af",
            first,
        )

    def test_exact_artifact_denominator_is_required(self) -> None:
        missing = copy.deepcopy(self.manifest)
        missing["artifacts"].pop()
        self.assert_rejected(lambda: validate_manifest(missing), "schema")

        duplicate = copy.deepcopy(self.manifest)
        duplicate["artifacts"][-1]["id"] = duplicate["artifacts"][-2]["id"]
        self.assert_rejected(lambda: validate_manifest(duplicate), "denominator")

        reordered = copy.deepcopy(self.manifest)
        reordered["artifacts"][0], reordered["artifacts"][1] = (
            reordered["artifacts"][1],
            reordered["artifacts"][0],
        )
        self.assert_rejected(lambda: validate_manifest(reordered), "denominator")

    def test_dependency_workflow_and_package_references_fail_closed(self) -> None:
        unknown_dependency = copy.deepcopy(self.manifest)
        unknown_dependency["artifacts"][0]["dependency_roots"] = ["unknown-root"]
        self.assert_rejected(
            lambda: validate_manifest(unknown_dependency), "dependency-root"
        )

        absent_job = copy.deepcopy(self.manifest)
        absent_job["artifacts"][0]["compile_job"] = "compile-absent"
        self.assert_rejected(lambda: validate_manifest(absent_job), "workflow-job")

        absent_path = copy.deepcopy(self.manifest)
        absent_path["artifacts"][0]["package_root"] = "bindings/absent"
        self.assert_rejected(lambda: validate_manifest(absent_path), "artifact-path")

    def test_source_tag_and_package_checksum_contracts_are_exact(self) -> None:
        source_tag = copy.deepcopy(self.manifest)
        source_tag["artifacts"][0]["artifact_policy"]["checksum_required"] = True
        self.assert_rejected(lambda: validate_manifest(source_tag), "artifact-policy")

        package = copy.deepcopy(self.manifest)
        package["artifacts"][1]["artifact_policy"]["checksum_required"] = False
        self.assert_rejected(lambda: validate_manifest(package), "artifact-policy")

    def test_reproducibility_normalization_is_bounded(self) -> None:
        missing = copy.deepcopy(self.manifest)
        missing["artifacts"][1]["reproducibility"]["allowed_normalizations"] = []
        self.assert_rejected(lambda: validate_manifest(missing), "reproducibility")

        excess = copy.deepcopy(self.manifest)
        excess["artifacts"][0]["reproducibility"]["allowed_normalizations"] = [
            "archive-entry-timestamp"
        ]
        self.assert_rejected(lambda: validate_manifest(excess), "reproducibility")

    def test_oidc_and_long_lived_credential_scopes_are_exact(self) -> None:
        oidc = copy.deepcopy(self.manifest)
        row = next(item for item in oidc["artifacts"] if item["id"] == "release:dart")
        row["credential_policy"]["secret_names"] = ["DART_TOKEN"]
        self.assert_rejected(lambda: validate_manifest(oidc), "credential-policy")

        long_lived = copy.deepcopy(self.manifest)
        row = next(
            item for item in long_lived["artifacts"] if item["id"] == "release:cpp"
        )
        row["credential_policy"]["secret_names"] = []
        self.assert_rejected(lambda: validate_manifest(long_lived), "credential-policy")

        observed_oidc = {
            item["id"]
            for item in self.manifest["artifacts"]
            if item["credential_policy"]["mode"] == "oidc"
        }
        self.assertEqual(OIDC_ARTIFACT_IDS, observed_oidc)

    def test_profile_and_attestation_permissions_cannot_be_weakened(self) -> None:
        network = copy.deepcopy(self.manifest)
        network["profile_policy"]["pull-request"]["network"] = "allowed"
        self.assert_rejected(lambda: validate_manifest(network), "profile-policy")

        permission = copy.deepcopy(self.manifest)
        permission["workflow_policy"]["attestation_permissions"].remove(
            "attestations: write"
        )
        self.assert_rejected(lambda: validate_manifest(permission), "workflow-policy")

        publication = copy.deepcopy(self.manifest)
        publication["profile_policy"]["release"]["publication"] = True
        self.assert_rejected(lambda: validate_manifest(publication), "schema")

    def test_contract_fixture_has_no_live_or_publication_authority(self) -> None:
        self.assertFalse(self.fixture["publication_authorized"])
        details = self.fixture["checks"][0]["details"]
        self.assertTrue(details["synthetic"])
        self.assertFalse(details["live_artifact"])
        self.assertFalse(details["publication_authority"])
        validate_contract_fixture(self.fixture, self.manifest)

    def test_contract_fixture_rejects_stale_or_tampered_identity(self) -> None:
        stale = copy.deepcopy(self.fixture)
        stale["manifest_fingerprint"] = "f" * 64
        self.resign_fixture(stale)
        self.assert_rejected(
            lambda: validate_contract_fixture(stale, self.manifest), "stale-manifest"
        )

        tampered = copy.deepcopy(self.fixture)
        tampered["disclaimer"] += " changed"
        self.assert_rejected(
            lambda: validate_contract_fixture(tampered, self.manifest),
            "fixture-fingerprint",
        )

        authority = copy.deepcopy(self.fixture)
        authority["disclaimer"] = "Synthetic only."
        self.resign_fixture(authority)
        self.assert_rejected(
            lambda: validate_contract_fixture(authority, self.manifest),
            "fixture-authority",
        )

    def test_complete_synthetic_evidence_passes_without_authority(self) -> None:
        evidence = synthetic_evidence(self.manifest)
        validated = validate_evidence(evidence, self.manifest)
        self.assertEqual(ARTIFACT_IDS, [row["id"] for row in validated["artifacts"]])
        self.assertEqual("synthetic-contract", validated["evidence_authority"])
        self.assertFalse(validated["publication_authorized"])

    def test_evidence_denominator_and_manifest_identity_fail_closed(self) -> None:
        evidence = synthetic_evidence(self.manifest)
        evidence["artifacts"].pop()
        evidence["summary"]["passed"] -= 1
        evidence["summary"]["total"] -= 1
        self.resign_evidence(evidence)
        self.assert_rejected(
            lambda: validate_evidence(evidence, self.manifest), "schema"
        )

        evidence = synthetic_evidence(self.manifest)
        evidence["manifest_fingerprint"] = "e" * 64
        self.resign_evidence(evidence)
        self.assert_rejected(
            lambda: validate_evidence(evidence, self.manifest), "stale-manifest"
        )

    def test_checksum_and_provenance_subjects_are_bound(self) -> None:
        checksum = synthetic_evidence(self.manifest)
        checksum["artifacts"][0]["checksum"]["digest"] = "f" * 64
        self.resign_evidence(checksum)
        self.assert_rejected(
            lambda: validate_evidence(checksum, self.manifest), "checksum-subject"
        )

        subject = synthetic_evidence(self.manifest)
        subject["artifacts"][0]["provenance"]["subject_name"] = "other"
        self.resign_evidence(subject)
        self.assert_rejected(
            lambda: validate_evidence(subject, self.manifest), "provenance-subject"
        )

        command = synthetic_evidence(self.manifest)
        command["artifacts"][0]["provenance"]["build_command_sha256"] = "f" * 64
        self.resign_evidence(command)
        self.assert_rejected(
            lambda: validate_evidence(command, self.manifest), "provenance-command"
        )

    def test_toolchain_denominator_policy_and_complete_pass_are_bound(self) -> None:
        denominator = synthetic_evidence(self.manifest)
        denominator["toolchains"].pop()
        self.resign_evidence(denominator)
        self.assert_rejected(
            lambda: validate_evidence(denominator, self.manifest),
            "toolchain-denominator",
        )

        policy = synthetic_evidence(self.manifest)
        policy["toolchains"][0]["policy_sha256"] = "f" * 64
        self.resign_evidence(policy)
        self.assert_rejected(
            lambda: validate_evidence(policy, self.manifest), "toolchain-policy"
        )

        incomplete = synthetic_evidence(self.manifest)
        incomplete["toolchains"][0]["version"] = None
        self.resign_evidence(incomplete)
        self.assert_rejected(
            lambda: validate_evidence(incomplete, self.manifest), "false-pass"
        )

    def test_reproducibility_scope_and_exact_rebuilds_are_bound(self) -> None:
        normalized = synthetic_evidence(self.manifest)
        cpp = next(
            item for item in normalized["artifacts"] if item["id"] == "release:cpp"
        )
        cpp["reproducibility"]["normalized_fields"] = ["signature"]
        self.resign_evidence(normalized)
        self.assert_rejected(
            lambda: validate_evidence(normalized, self.manifest), "reproducibility"
        )

        exact = synthetic_evidence(self.manifest)
        rust = next(item for item in exact["artifacts"] if item["id"] == "release:rust")
        rust["reproducibility"]["second_sha256"] = "f" * 64
        self.resign_evidence(exact)
        self.assert_rejected(
            lambda: validate_evidence(exact, self.manifest), "reproducibility"
        )

    def test_credential_mode_secret_names_and_oidc_issuer_are_bound(self) -> None:
        secret = synthetic_evidence(self.manifest)
        cpp = next(item for item in secret["artifacts"] if item["id"] == "release:cpp")
        cpp["credential"]["secret_names"] = ["CONAN_PASSWORD"]
        self.resign_evidence(secret)
        self.assert_rejected(
            lambda: validate_evidence(secret, self.manifest), "credential-policy"
        )

        issuer = synthetic_evidence(self.manifest)
        dart = next(
            item for item in issuer["artifacts"] if item["id"] == "release:dart"
        )
        dart["credential"]["oidc_issuer"] = "https://example.invalid"
        self.resign_evidence(issuer)
        self.assert_rejected(
            lambda: validate_evidence(issuer, self.manifest), "credential-policy"
        )

    def test_false_pass_and_missing_finding_are_rejected(self) -> None:
        unresolved = synthetic_evidence(self.manifest)
        unresolved["artifacts"][0]["sbom"]["unresolved_components"] = 1
        self.resign_evidence(unresolved)
        self.assert_rejected(
            lambda: validate_evidence(unresolved, self.manifest), "false-pass"
        )

        nonpass = synthetic_evidence(self.manifest)
        nonpass["artifacts"][0]["status"] = "unavailable"
        nonpass["summary"] = {
            "passed": 16,
            "failed": 0,
            "unavailable": 1,
            "incomplete": 0,
            "total": 17,
        }
        nonpass["status"] = "unavailable"
        self.resign_evidence(nonpass)
        self.assert_rejected(
            lambda: validate_evidence(nonpass, self.manifest), "missing-finding"
        )

    def test_summary_status_and_fingerprint_are_exact(self) -> None:
        summary = synthetic_evidence(self.manifest)
        summary["summary"]["passed"] = 16
        self.resign_evidence(summary)
        self.assert_rejected(
            lambda: validate_evidence(summary, self.manifest), "summary"
        )

        status = synthetic_evidence(self.manifest)
        status["status"] = "unavailable"
        self.resign_evidence(status)
        self.assert_rejected(lambda: validate_evidence(status, self.manifest), "status")

        fingerprint = synthetic_evidence(self.manifest)
        fingerprint["source"]["tree_sha256"] = "f" * 64
        self.assert_rejected(
            lambda: validate_evidence(fingerprint, self.manifest),
            "evidence-fingerprint",
        )

    def test_synthetic_evidence_cannot_claim_live_profile(self) -> None:
        evidence = synthetic_evidence(self.manifest)
        evidence["profile"] = "full"
        self.resign_evidence(evidence)
        self.assert_rejected(
            lambda: validate_evidence(evidence, self.manifest), "evidence-authority"
        )

    def test_fixture_inputs_are_not_modified(self) -> None:
        manifest_bytes = Path(MANIFEST_PATH).read_bytes()
        fixture_bytes = Path(VALID_FIXTURE_PATH).read_bytes()
        run_contract_check()
        self.assertEqual(manifest_bytes, Path(MANIFEST_PATH).read_bytes())
        self.assertEqual(fixture_bytes, Path(VALID_FIXTURE_PATH).read_bytes())


if __name__ == "__main__":
    unittest.main()
