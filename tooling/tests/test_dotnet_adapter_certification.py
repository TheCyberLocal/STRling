from __future__ import annotations

import base64
import copy
import unittest

from tooling import dotnet_adapter_certification as certification


class DotNetAdapterCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = certification._read_json(
            certification.EVIDENCE_ROOT / "evidence.schema.json"
        )
        cls.manifest = certification._read_json(
            certification.EVIDENCE_ROOT / "manifest.json"
        )
        cls.baseline = certification._build_baseline(certification.ROOT)
        cls.contract_fingerprint = certification._files_fingerprint(
            certification.ROOT, certification.CONTRACT_FILES
        )

    def certify(
        self,
        manifest: dict[str, object] | None = None,
        baseline: dict[str, object] | None = None,
    ) -> certification.DotNetAdapterCertificationReport:
        return certification.DotNetAdapterCertificationSuite().certify_documents(
            self.schema,
            manifest or self.manifest,
            baseline or self.baseline,
            expected_baseline=self.baseline,
            contract_fingerprint=self.contract_fingerprint,
        )

    def test_repository_documents_certify(self) -> None:
        report = certification.DotNetAdapterCertificationSuite().certify()
        self.assertEqual(report.case_count, 72)
        self.assertEqual(report.semantic_copy_count, 18)
        self.assertEqual(report.historical_source_count, 50)

    def test_case_removal_fails_after_editing_declared_total(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["cases"].pop()
        manifest["counts"]["total"] = 71
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.DotNetAdapterCertificationError):
            self.certify(manifest)

    def test_case_identity_substitution_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["cases"][0]["id"] = "public-substituted-case"
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaisesRegex(
            certification.DotNetAdapterCertificationError,
            "required .NET evidence",
        ):
            self.certify(manifest)

    def test_runner_substitution_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case["runner"] == "manifest":
                case["runner"] = "public-contract"
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaisesRegex(
            certification.DotNetAdapterCertificationError,
            "runner denominator",
        ):
            self.certify(manifest)

    def test_observation_reclassification_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["task_start_observations"][1]["status"] = "passed"
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.DotNetAdapterCertificationError):
            self.certify(manifest)

    def test_semantic_path_substitution_fails_after_fingerprint_edit(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        baseline["semantic_copy_files"][0]["path"] = certification.PRODUCT_PROJECTS[0]
        baseline["fingerprint"] = certification._fingerprint_json(
            baseline, {"fingerprint"}
        )
        with self.assertRaisesRegex(
            certification.DotNetAdapterCertificationError,
            "does not reproduce",
        ):
            self.certify(baseline=baseline)

    def test_source_mutation_fails_after_blob_and_document_hash_edits(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        entry = baseline["historical_source_files"][0]
        content = base64.b64decode(entry["content_base64"]) + b"mutation"
        entry["content_base64"] = base64.b64encode(content).decode("ascii")
        entry["sha256"] = "sha256:" + certification.hashlib.sha256(content).hexdigest()
        baseline["fingerprint"] = certification._fingerprint_json(
            baseline, {"fingerprint"}
        )
        with self.assertRaisesRegex(
            certification.DotNetAdapterCertificationError,
            "does not reproduce",
        ):
            self.certify(baseline=baseline)

    def test_embedded_source_materializes_exactly(self) -> None:
        for entry in self.baseline["historical_source_files"]:
            content = base64.b64decode(entry["content_base64"])
            expected = certification._git_blob(certification.ROOT, entry["path"])
            self.assertEqual(content, expected)

    def test_manifest_fingerprint_is_canonical(self) -> None:
        expected = certification._fingerprint_json(self.manifest, {"fingerprint"})
        self.assertEqual(self.manifest["fingerprint"], expected)


if __name__ == "__main__":
    unittest.main()
