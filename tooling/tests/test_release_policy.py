from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tooling.release_policy import (
    ROOT,
    check_document,
    load_policy,
    render_document,
    validate_policy,
)


class ReleasePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = load_policy()

    def mutated(self) -> dict[str, object]:
        return copy.deepcopy(self.policy)

    def assert_finding(self, policy: dict[str, object], code: str) -> None:
        result = validate_policy(policy=policy)
        self.assertTrue(
            any(finding.startswith(code) for finding in result.findings),
            result.findings,
        )

    def test_current_policy_and_document_projection_pass(self) -> None:
        self.assertEqual((), validate_policy().findings)
        self.assertIsNone(check_document(ROOT, self.policy))

    def test_product_version_has_one_canonical_authority(self) -> None:
        product = self.policy["product"]
        self.assertEqual("4.0.0", product["version"])
        self.assertEqual(
            "governance/release-policy.json#/product/version",
            product["version_authority"],
        )
        self.assertEqual("preparation", product["repository_projection"]["status"])

    def test_duplicate_version_surface_is_rejected(self) -> None:
        policy = self.mutated()
        policy["version_surfaces"].append(copy.deepcopy(policy["version_surfaces"][0]))
        self.assert_finding(policy, "RP-ID-001 version surfaces")

    def test_manifest_version_drift_is_rejected(self) -> None:
        policy = self.mutated()
        surface = next(
            item
            for item in policy["version_surfaces"]
            if item["id"] == "rust-public-crate"
        )
        surface["current_version"] = "9.9.9"
        self.assert_finding(policy, "RP-VERSION-005 rust-public-crate")

    def test_supported_claim_without_certified_evidence_is_rejected(self) -> None:
        policy = self.mutated()
        policy["support_claims"][0]["certification_status"] = "preview-evidence"
        self.assert_finding(policy, "RP-SUPPORT-002 binding:c")

    def test_registered_binding_without_support_claim_is_rejected(self) -> None:
        policy = self.mutated()
        policy["support_claims"] = [
            claim for claim in policy["support_claims"] if claim["id"] != "binding:c"
        ]
        self.assert_finding(policy, "RP-SUPPORT-004 binding:c")

    def test_unregistered_binding_support_claim_is_rejected(self) -> None:
        policy = self.mutated()
        extra = copy.deepcopy(policy["support_claims"][0])
        extra["id"] = "binding:new-island"
        extra["subject"] = "Unregistered binding"
        policy["support_claims"].append(extra)
        self.assert_finding(policy, "RP-SUPPORT-006 bindings")

    def test_release_state_shortcut_is_rejected(self) -> None:
        policy = self.mutated()
        policy["release_lifecycle"]["transitions"].append(
            {
                "from": "certified",
                "to": "published",
                "requirements": ["none"],
            }
        )
        self.assert_finding(policy, "RP-LIFECYCLE-002 transitions")

    def test_unratified_public_channel_is_rejected(self) -> None:
        policy = self.mutated()
        policy["release_channels"] = [
            channel
            for channel in policy["release_channels"]
            if channel["id"] != "stable"
        ]
        self.assert_finding(policy, "RP-LIFECYCLE-004 release channels")

    def test_certification_cannot_authorize_publication(self) -> None:
        policy = self.mutated()
        policy["publication"]["certification_authorizes_publication"] = True
        self.assert_finding(policy, "RP-PUBLISH-001 publication")

    def test_release_candidate_cannot_be_replaceable(self) -> None:
        policy = self.mutated()
        policy["release_lifecycle"]["release_candidate"]["replaceable"] = True
        self.assert_finding(policy, "RP-PUBLISH-003 release candidate")

    def test_accepted_waiver_must_be_accounted_for_exactly(self) -> None:
        policy = self.mutated()
        policy["waivers"]["active"] = []
        self.assert_finding(policy, "RP-WAIVER-001 waivers")

    def test_document_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "docs/release-policy.md").write_text("stale\n", encoding="utf-8")
            finding = check_document(root, self.policy)
            self.assertIsNotNone(finding)
            self.assertTrue(finding.startswith("RP-DOC-002"))

    def test_document_generation_is_deterministic(self) -> None:
        first = render_document(self.policy)
        second = render_document(json.loads(json.dumps(self.policy)))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
