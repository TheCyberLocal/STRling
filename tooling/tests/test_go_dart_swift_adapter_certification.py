from __future__ import annotations

import base64
import copy
import hashlib
import unittest

from tooling import go_dart_swift_adapter_certification as certification


class GoDartSwiftAdapterCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = certification._schema()
        cls.manifest = certification._build_manifest(certification.ROOT)
        cls.baseline = certification._build_baseline(certification.ROOT)

    def certify(
        self,
        schema: dict[str, object] | None = None,
        manifest: dict[str, object] | None = None,
        baseline: dict[str, object] | None = None,
    ) -> certification.GoDartSwiftAdapterCertificationReport:
        return certification.GoDartSwiftAdapterCertificationSuite().certify_documents(
            schema or self.schema,
            manifest or self.manifest,
            baseline or self.baseline,
            expected_schema=self.schema,
            expected_manifest=self.manifest,
            expected_baseline=self.baseline,
        )

    def test_repository_documents_certify(self) -> None:
        report = certification.GoDartSwiftAdapterCertificationSuite().certify()
        self.assertEqual(report.case_count, 78)
        self.assertEqual(report.public_input_count, 36)
        self.assertEqual(report.semantic_copy_count, 30)
        self.assertEqual(report.historical_source_count, 204)

    def test_case_removal_fails_after_editing_declared_total(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["cases"].pop()
        manifest["counts"]["total"] = 77
        manifest["fingerprint"] = certification._fingerprint_json(manifest)
        with self.assertRaises(certification.GoDartSwiftAdapterCertificationError):
            self.certify(manifest=manifest)

    def test_case_identity_substitution_fails(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["cases"][0]["id"] = "public-api-go-substituted"
        manifest["fingerprint"] = certification._fingerprint_json(manifest)
        with self.assertRaisesRegex(
            certification.GoDartSwiftAdapterCertificationError,
            "does not reproduce",
        ):
            self.certify(manifest=manifest)

    def test_unavailable_observation_cannot_be_promoted(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["task_start_observations"][0]["status"] = "passed"
        manifest["task_start_observations"][0]["tests"] = 1
        manifest["fingerprint"] = certification._fingerprint_json(manifest)
        with self.assertRaises(certification.GoDartSwiftAdapterCertificationError):
            self.certify(manifest=manifest)

    def test_semantic_path_substitution_fails(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        baseline["semantic_copy_files"][0] = baseline["public_files"][-1]
        baseline["fingerprint"] = certification._fingerprint_json(baseline)
        with self.assertRaisesRegex(
            certification.GoDartSwiftAdapterCertificationError,
            "does not reproduce",
        ):
            self.certify(baseline=baseline)

    def test_source_mutation_fails_after_hash_edits(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        entry = baseline["historical_source_files"][0]
        content = base64.b64decode(entry["content_base64"]) + b"mutation"
        entry["content_base64"] = base64.b64encode(content).decode("ascii")
        entry["sha256"] = f"sha256:{hashlib.sha256(content).hexdigest()}"
        baseline["fingerprint"] = certification._fingerprint_json(baseline)
        with self.assertRaisesRegex(
            certification.GoDartSwiftAdapterCertificationError,
            "does not reproduce",
        ):
            self.certify(baseline=baseline)

    def test_embedded_source_materializes_exactly(self) -> None:
        entry = self.baseline["historical_source_files"][0]
        content = base64.b64decode(entry["content_base64"])
        expected = certification._git_blob(certification.ROOT, entry["path"])
        self.assertEqual(content, expected)

    def test_schema_shrinkage_fails(self) -> None:
        schema = copy.deepcopy(self.schema)
        schema["properties"]["cases"]["minItems"] = 77
        with self.assertRaisesRegex(
            certification.GoDartSwiftAdapterCertificationError,
            "schema does not reproduce",
        ):
            self.certify(schema=schema)

    def test_fingerprints_are_canonical(self) -> None:
        self.assertEqual(
            self.manifest["fingerprint"],
            certification._fingerprint_json(self.manifest, {"fingerprint"}),
        )
        self.assertEqual(
            self.baseline["fingerprint"],
            certification._fingerprint_json(self.baseline, {"fingerprint"}),
        )


if __name__ == "__main__":
    unittest.main()
