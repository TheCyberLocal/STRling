from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from tooling import binding_support_certification as certification
from tooling.architecture_fitness import (
    binding_semantic_path_candidate,
    required_rule_status_findings,
)
from tooling.governance import matches_any


class BindingSupportCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = certification._read_json(certification.SCHEMA_PATH)
        cls.manifest = certification._read_json(certification.MANIFEST_PATH)
        cls.evidence = certification._build_evidence(certification.ROOT, cls.manifest)

    def certify(
        self,
        *,
        schema: dict[str, object] | None = None,
        manifest: dict[str, object] | None = None,
        evidence: dict[str, object] | None = None,
        expected: dict[str, object] | None = None,
        require_ready: bool = False,
    ) -> certification.BindingSupportCertificationReport:
        return certification.BindingSupportCertificationSuite().certify_documents(
            schema or self.schema,
            manifest or self.manifest,
            evidence or self.evidence,
            expected_evidence=expected or self.evidence,
            require_ready=require_ready,
        )

    def test_repository_evidence_certifies(self) -> None:
        report = certification.BindingSupportCertificationSuite().certify()
        bindings = self.manifest["bindings"]
        self.assertEqual(report.binding_count, len(bindings))
        self.assertEqual(
            report.supported_candidate_count,
            sum(row["certification_tier"] == "supported_candidate" for row in bindings),
        )
        self.assertEqual(
            report.preview_candidate_count,
            sum(row["certification_tier"] == "preview_candidate" for row in bindings),
        )
        self.assertEqual(
            report.public_surface_count,
            sum(len(row["public_surfaces"]) for row in bindings),
        )

    def test_binding_removal_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["bindings"].pop()
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError,
            "every unique manifest route",
        ):
            self.certify(manifest=manifest)

    def test_binding_order_substitution_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["bindings"][0], manifest["bindings"][1] = (
            manifest["bindings"][1],
            manifest["bindings"][0],
        )
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError,
            "every unique manifest route",
        ):
            self.certify(manifest=manifest)

    def test_tier_mutation_fails_exact_reproduction(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["bindings"][0]["certification_tier"] = "preview_candidate"
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError, "does not reproduce"
        ):
            self.certify(evidence=evidence)

    def test_route_mutation_fails_exact_reproduction(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["bindings"][0]["canonical_route"] = "binding-local compiler"
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError, "does not reproduce"
        ):
            self.certify(evidence=evidence)

    def test_noncanonical_route_classification_blocks_readiness(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["bindings"][0]["adapter_contract"] = "semantic"
        evidence = certification._build_evidence(certification.ROOT, manifest)
        self.assertIn(
            "all-binding-routes-thin-and-canonical",
            evidence["readiness"]["blocking_requirements"],
        )

    def test_unregistered_product_route_blocks_readiness(self) -> None:
        real_read = certification._read_json

        def mutated(path):
            value = real_read(path)
            if path == certification.ROOT / "toolchain.json":
                value = copy.deepcopy(value)
                value["bindings"]["newlang"] = copy.deepcopy(value["bindings"]["c"])
            return value

        with patch.object(certification, "_read_json", side_effect=mutated):
            evidence = certification._build_evidence(certification.ROOT, self.manifest)
        self.assertIn(
            "all-registered-binding-routes-classified",
            evidence["readiness"]["blocking_requirements"],
        )

    def test_public_enforcement_mutation_fails_exact_reproduction(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["bindings"][0]["public_contracts"][0]["enforcement"] = "transitional"
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError, "does not reproduce"
        ):
            self.certify(evidence=evidence)

    def test_semantic_path_mutation_fails_exact_reproduction(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["semantic_ownership"]["forbidden_product_paths"].append(
            "bindings/go/parser.go"
        )
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError, "does not reproduce"
        ):
            self.certify(evidence=evidence)

    def test_not_ready_evidence_fails_the_final_gate(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["readiness"] = {
            "status": "not_ready",
            "blocking_requirements": ["controlled-test-blocker"],
        }
        evidence["fingerprint"] = certification._fingerprint_json(
            evidence, {"fingerprint"}
        )
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError, "is not ready"
        ):
            self.certify(
                evidence=evidence,
                expected=evidence,
                require_ready=True,
            )

    def test_repository_evidence_passes_the_final_gate(self) -> None:
        report = certification.BindingSupportCertificationSuite().certify(
            require_ready=True
        )
        self.assertEqual(0, report.blocking_requirement_count)

    def test_fingerprint_is_canonical(self) -> None:
        self.assertEqual(
            self.evidence["fingerprint"],
            certification._fingerprint_json(self.evidence, {"fingerprint"}),
        )

    def test_global_semantic_rule_rejects_new_parser_path(self) -> None:
        configuration = {
            "sources": ["bindings/**"],
            "semantic_names": ["compiler", "parser", "emitters"],
            "permitted_paths": ["bindings/python/compiler.py"],
            "permitted_declarations": [],
            "excluded_path_parts": ["tests"],
        }
        self.assertTrue(
            binding_semantic_path_candidate(
                "bindings/go/parser.go", configuration, matches_any
            )
        )
        self.assertFalse(
            binding_semantic_path_candidate(
                "bindings/python/compiler.py", configuration, matches_any
            )
        )
        self.assertFalse(
            binding_semantic_path_candidate(
                "bindings/go/tests/parser.go", configuration, matches_any
            )
        )

    def test_route_coverage_requires_enforced_rules(self) -> None:
        rules = [
            {"id": "rust-route", "status": "enforced"},
            {"id": "jvm-route", "status": "transitional"},
        ]
        findings = required_rule_status_findings(
            rules, ["rust-route", "jvm-route", "missing-route"]
        )
        self.assertEqual(2, len(findings))
        self.assertIn("not enforced", findings[0][0])
        self.assertIn("missing", findings[1][0])


if __name__ == "__main__":
    unittest.main()
