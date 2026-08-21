from __future__ import annotations

import copy
import unittest

from tooling import binding_support_certification as certification


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
        self.assertEqual(report.binding_count, 17)
        self.assertEqual(report.supported_candidate_count, 12)
        self.assertEqual(report.preview_candidate_count, 5)
        self.assertEqual(report.public_surface_count, 18)

    def test_binding_removal_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["bindings"].pop()
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError, "seventeen-language"
        ):
            self.certify(manifest=manifest)

    def test_binding_order_substitution_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["bindings"][0], manifest["bindings"][1] = (
            manifest["bindings"][1],
            manifest["bindings"][0],
        )
        with self.assertRaisesRegex(
            certification.BindingSupportCertificationError, "seventeen-language"
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
        if self.evidence["readiness"]["status"] == "not_ready":
            with self.assertRaisesRegex(
                certification.BindingSupportCertificationError, "is not ready"
            ):
                self.certify(require_ready=True)

    def test_fingerprint_is_canonical(self) -> None:
        self.assertEqual(
            self.evidence["fingerprint"],
            certification._fingerprint_json(self.evidence, {"fingerprint"}),
        )


if __name__ == "__main__":
    unittest.main()
