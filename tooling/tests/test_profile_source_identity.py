from __future__ import annotations

import copy
import json
import unittest
import uuid
from unittest import mock

from jsonschema import Draft202012Validator

from tooling.certification import canonical_evidence_fingerprint
from tooling.profile_source_identity import (
    GRAPH_SCHEMA_PATH,
    IDENTITY_SOURCE_REFERENCE,
    PROFILE_IDS,
    ROOT,
    SCHEMA_PATH,
    ProfileSourceIdentityError,
    _atomic_write_json,
    build_invocation_evidence,
    derive_definition_bundle,
    load_definition_bundle,
    load_dependency_graph,
    profile_identity,
    validate_definition_bundle,
    validate_dependency_graph,
    validate_invocation_evidence,
)


CLEAN_REPOSITORY = {"commit": "a" * 40, "dirty": False}


def refresh_definition_fingerprint(value: dict[str, object]) -> None:
    payload = dict(value)
    payload.pop("evidence_fingerprint", None)
    value["evidence_fingerprint"] = canonical_evidence_fingerprint(payload)


def refresh_invocation_fingerprints(value: dict[str, object]) -> None:
    deterministic = value["deterministic_evidence"]
    value["evidence_fingerprint"] = canonical_evidence_fingerprint(deterministic)
    payload = dict(value)
    payload.pop("artifact_fingerprint", None)
    value["artifact_fingerprint"] = canonical_evidence_fingerprint(payload)


class ProfileSourceIdentityTests(unittest.TestCase):
    def test_schemas_and_checked_in_definition_bundle_are_current(self) -> None:
        for path in (SCHEMA_PATH, GRAPH_SCHEMA_PATH):
            Draft202012Validator.check_schema(
                json.loads(path.read_text(encoding="utf-8"))
            )
        bundle = load_definition_bundle(root=ROOT)
        self.assertEqual("identity-only", bundle["evidence_role"])
        self.assertEqual(
            IDENTITY_SOURCE_REFERENCE["path"],
            "tests/certification/profile-source/1.0/definitions.json",
        )
        self.assertEqual(list(PROFILE_IDS), [item["id"] for item in bundle["profiles"]])
        self.assertEqual(derive_definition_bundle(root=ROOT), bundle)

    def test_definition_bundle_contains_no_result_or_readiness_claim(self) -> None:
        serialized = json.dumps(load_definition_bundle(root=ROOT), sort_keys=True)
        for forbidden in (
            '"status"',
            '"passed"',
            '"certified"',
            '"release_ready"',
            '"sample"',
        ):
            self.assertNotIn(forbidden, serialized.casefold())

    def test_profile_version_and_fingerprint_are_canonical(self) -> None:
        bundle = load_definition_bundle(root=ROOT)
        full = profile_identity(bundle, "full")
        release = profile_identity(bundle, "release")
        self.assertEqual("1.27.0", full["definition_version"])
        self.assertEqual("1.27.0", release["definition_version"])
        self.assertNotEqual(
            full["definition_fingerprint"], release["definition_fingerprint"]
        )

    def test_stale_profile_definition_identity_fails_closed(self) -> None:
        candidate = copy.deepcopy(load_definition_bundle(root=ROOT))
        candidate["profiles"][2]["definition_version"] = "9.9.9"
        refresh_definition_fingerprint(candidate)
        with self.assertRaisesRegex(
            ProfileSourceIdentityError, "differs from canonical source definitions"
        ):
            validate_definition_bundle(candidate, root=ROOT)

        candidate = copy.deepcopy(load_definition_bundle(root=ROOT))
        candidate["profiles"][2]["definition_fingerprint"] = "9" * 64
        refresh_definition_fingerprint(candidate)
        with self.assertRaises(ProfileSourceIdentityError):
            validate_definition_bundle(candidate, root=ROOT)

    def test_wrong_operation_registry_fingerprint_fails_closed(self) -> None:
        candidate = copy.deepcopy(load_definition_bundle(root=ROOT))
        candidate["registry"]["operation_registry_fingerprint"] = "9" * 64
        refresh_definition_fingerprint(candidate)
        with self.assertRaises(ProfileSourceIdentityError):
            validate_definition_bundle(candidate, root=ROOT)

    @mock.patch(
        "tooling.profile_source_identity.repository_state",
        return_value=CLEAN_REPOSITORY,
    )
    def test_invocation_binds_clean_source_and_is_identity_only(
        self, _repository_state: mock.Mock
    ) -> None:
        artifact = build_invocation_evidence(
            root=ROOT,
            invocation_id="b" * 32,
            generated_at="2026-09-01T00:00:00Z",
        )
        self.assertEqual("identity-only", artifact["evidence_role"])
        self.assertNotIn("status", artifact)
        validate_invocation_evidence(artifact, root=ROOT)

    @mock.patch(
        "tooling.profile_source_identity.repository_state",
        return_value=CLEAN_REPOSITORY,
    )
    def test_previous_source_invocation_fails_closed(
        self, _repository_state: mock.Mock
    ) -> None:
        artifact = build_invocation_evidence(
            root=ROOT,
            invocation_id="c" * 32,
            generated_at="2026-09-01T00:00:00Z",
        )
        artifact["deterministic_evidence"]["repository"]["commit"] = "d" * 40
        refresh_invocation_fingerprints(artifact)
        with self.assertRaisesRegex(ProfileSourceIdentityError, "previous source SHA"):
            validate_invocation_evidence(artifact, root=ROOT)

    @mock.patch(
        "tooling.profile_source_identity.repository_state",
        return_value=CLEAN_REPOSITORY,
    )
    def test_identity_only_artifact_cannot_claim_certification_success(
        self, _repository_state: mock.Mock
    ) -> None:
        artifact = build_invocation_evidence(
            root=ROOT,
            invocation_id="e" * 32,
            generated_at="2026-09-01T00:00:00Z",
        )
        artifact["status"] = "passed"
        refresh_invocation_fingerprints(artifact)
        with self.assertRaisesRegex(ProfileSourceIdentityError, "schema rejection"):
            validate_invocation_evidence(artifact, root=ROOT)

    def test_result_artifact_cannot_substitute_for_identity_evidence(self) -> None:
        result = {
            "schema_version": "1.0.0",
            "artifact_kind": "strling-profile-certification",
            "status": "passed",
        }
        with self.assertRaises(ProfileSourceIdentityError):
            validate_invocation_evidence(result, root=ROOT)

    @mock.patch(
        "tooling.profile_source_identity.repository_state",
        return_value=CLEAN_REPOSITORY,
    )
    def test_contradictory_identity_role_fails_closed(
        self, _repository_state: mock.Mock
    ) -> None:
        artifact = build_invocation_evidence(
            root=ROOT,
            invocation_id="f" * 32,
            generated_at="2026-09-01T00:00:00Z",
        )
        artifact["evidence_role"] = "certification-result"
        refresh_invocation_fingerprints(artifact)
        with self.assertRaises(ProfileSourceIdentityError):
            validate_invocation_evidence(artifact, root=ROOT)

    def test_dependency_graph_is_acyclic_and_has_exact_field_classifications(
        self,
    ) -> None:
        graph = load_dependency_graph(root=ROOT)
        validate_dependency_graph(graph, root=ROOT)
        classifications = {
            (item["artifact_path"], item["json_pointer"]): item["classification"]
            for item in graph["field_classifications"]
        }
        self.assertEqual(
            "DERIVABLE_PRE_EXECUTION",
            classifications[
                (
                    "tests/certification/product/1.0/producer-manifest.json",
                    "/source_profile",
                )
            ],
        )
        self.assertEqual(
            "RESULT_ONLY",
            classifications[
                (
                    "tests/certification/target-adapter/1.0/source-profile-evidence.json",
                    "/results",
                )
            ],
        )

    def test_result_to_preflight_dependency_fails_closed(self) -> None:
        graph = copy.deepcopy(load_dependency_graph(root=ROOT))
        graph["edges"] = [
            edge
            for edge in graph["edges"]
            if not (
                edge["from"] == "target-adapter-manifest"
                and edge["to"] == "full-execution"
            )
        ]
        graph["edges"].append(
            {
                "from": "full-result",
                "to": "target-adapter-manifest",
                "relationship": "controlled forbidden result dependency",
            }
        )
        with self.assertRaisesRegex(
            ProfileSourceIdentityError, "feeds pre-execution authority"
        ):
            validate_dependency_graph(graph, root=ROOT)

    def test_atomic_publication_leaves_no_partial_artifact(self) -> None:
        destination = (
            ROOT
            / "target/codex-tools/profile-source-identity-tests"
            / f"{uuid.uuid4().hex}.json"
        )
        with mock.patch(
            "tooling.profile_source_identity._load_json",
            side_effect=ProfileSourceIdentityError(
                "controlled partial-artifact rejection"
            ),
        ):
            with self.assertRaises(ProfileSourceIdentityError):
                _atomic_write_json(
                    destination,
                    {"identity": "only"},
                    validator=lambda value: None,
                )
        self.assertFalse(destination.exists())
        self.assertEqual([], list(destination.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
