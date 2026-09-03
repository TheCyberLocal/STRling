from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from tooling import semantic_authority


class SemanticAuthorityTests(unittest.TestCase):
    def test_repository_authority_is_current_and_structured(self) -> None:
        evidence = semantic_authority.build_evidence()
        self.assertEqual("passed", evidence["summary"]["status"])
        self.assertEqual(4, evidence["summary"]["profile_count"])
        self.assertEqual(0, evidence["summary"]["active_generated_oracle_count"])
        self.assertEqual(0, evidence["summary"]["semantic_scraping_count"])

    def test_retired_profile_operation_fails_closed(self) -> None:
        real_load = semantic_authority._load

        def mutated(path):
            value = real_load(path)
            if path == semantic_authority.TOOLCHAIN_PATH:
                value = copy.deepcopy(value)
                value["policy"]["profiles"]["local"]["operations"].append(
                    {"operation": "legacy_reference_check"}
                )
            return value

        with patch.object(semantic_authority, "_load", side_effect=mutated):
            with self.assertRaisesRegex(
                semantic_authority.SemanticAuthorityError, "retired operation"
            ):
                semantic_authority.build_evidence()

    def test_generated_oracle_lineage_fails_closed(self) -> None:
        real_load = semantic_authority._load

        def mutated(path):
            value = real_load(path)
            if path == semantic_authority.REGISTRY_PATH:
                value = copy.deepcopy(value)
                artifact = next(
                    entry
                    for entry in value["artifacts"]
                    if entry["enforcement"] == "enforced"
                )
                artifact["generator_inputs"].append("tests/spec/*.json")
            return value

        with patch.object(semantic_authority, "_load", side_effect=mutated):
            with self.assertRaisesRegex(
                semantic_authority.SemanticAuthorityError,
                "consumes retired authority",
            ):
                semantic_authority.build_evidence()

    def test_semantic_stdout_scraping_syntax_is_detected(self) -> None:
        findings = semantic_authority._semantic_scraping_findings(
            "tooling/rogue.py",
            "expected_semantics = completed.stdout.splitlines()",
            semantic_authority._load(semantic_authority.POLICY_PATH)[
                "forbidden_semantic_scraping_patterns"
            ],
        )
        self.assertTrue(findings)

    def test_semantic_test_name_scraping_syntax_is_detected(self) -> None:
        findings = semantic_authority._semantic_scraping_findings(
            "tooling/rogue.py",
            "semantic_oracle = test_name",
            semantic_authority._load(semantic_authority.POLICY_PATH)[
                "forbidden_semantic_scraping_patterns"
            ],
        )
        self.assertTrue(findings)

    def test_omega_claim_identity_fails_closed(self) -> None:
        real_load = semantic_authority._load

        def mutated(path):
            value = real_load(path)
            if path == semantic_authority.PRODUCT_MANIFEST_PATH:
                value = copy.deepcopy(value)
                value["claims"][0]["claim_id"] = "omega.reintroduced"
            return value

        with patch.object(semantic_authority, "_load", side_effect=mutated):
            with self.assertRaisesRegex(
                semantic_authority.SemanticAuthorityError, "Omega claim"
            ):
                semantic_authority.build_evidence()


if __name__ == "__main__":
    unittest.main()
