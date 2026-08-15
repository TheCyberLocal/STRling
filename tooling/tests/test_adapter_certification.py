from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from tooling.adapter_certification import (
    BASELINE_PATH,
    CONTRACT_FILES,
    MANIFEST_PATH,
    SCHEMA_PATH,
    AdapterCertificationError,
    AdapterCertificationSuite,
    _build_baseline,
    _files_fingerprint,
    _fingerprint_json,
)


ROOT = Path(__file__).resolve().parents[2]


class AdapterCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = AdapterCertificationSuite(ROOT)
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        cls.contract_fingerprint = _files_fingerprint(ROOT, CONTRACT_FILES)
        cls.expected_baseline = _build_baseline(ROOT, cls.manifest)

    def certify(
        self,
        manifest: dict[str, object] | None = None,
        baseline: dict[str, object] | None = None,
    ) -> None:
        self.suite.certify_documents(
            self.schema,
            manifest or self.manifest,
            baseline or self.baseline,
            contract_fingerprint=self.contract_fingerprint,
            expected_baseline=self.expected_baseline,
        )

    @staticmethod
    def refresh_manifest(manifest: dict[str, object]) -> None:
        manifest["fingerprint"] = _fingerprint_json(manifest, {"fingerprint"})

    def test_certifies_closed_denominators_and_fingerprints(self) -> None:
        report = self.suite.certify()
        self.assertEqual(58, report.case_count)
        self.assertEqual(10, len(report.family_counts))
        self.assertEqual(28, report.public_input_count)
        self.assertEqual(35, report.semantic_copy_count)
        self.assertRegex(report.contract_fingerprint, r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(report.evidence_fingerprint, r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(report.baseline_fingerprint, r"^sha256:[0-9a-f]{64}$")

    def test_contract_fingerprint_detects_authority_drift(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["contract"]["fingerprint"] = "sha256:" + "0" * 64
        self.refresh_manifest(manifest)
        with self.assertRaisesRegex(AdapterCertificationError, "contract fingerprint"):
            self.certify(manifest)

    def test_contract_file_order_is_closed(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["contract"]["files"][0:2] = reversed(
            manifest["contract"]["files"][0:2]
        )
        self.refresh_manifest(manifest)
        with self.assertRaisesRegex(AdapterCertificationError, "file set or order"):
            self.certify(manifest)

    def test_evidence_fingerprint_detects_claim_mutation(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"][0]["claim"] = "mutated"
        with self.assertRaisesRegex(AdapterCertificationError, "evidence fingerprint"):
            self.certify(manifest)

    def test_case_removal_fails_even_after_declared_count_change(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"].pop()
        manifest["counts"]["total"] = 57
        self.refresh_manifest(manifest)
        with self.assertRaises(AdapterCertificationError):
            self.certify(manifest)

    def test_duplicate_case_identity_is_rejected(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"][1]["id"] = manifest["cases"][0]["id"]
        self.refresh_manifest(manifest)
        with self.assertRaisesRegex(AdapterCertificationError, "ids must be unique"):
            self.certify(manifest)

    def test_family_substitution_is_rejected(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"][0]["family"] = "canonical_parity"
        self.refresh_manifest(manifest)
        with self.assertRaisesRegex(AdapterCertificationError, "family denominator"):
            self.certify(manifest)

    def test_runner_coverage_is_closed(self) -> None:
        manifest = deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case["runner"] == "manifest":
                case["runner"] = "public-contract"
        self.refresh_manifest(manifest)
        with self.assertRaisesRegex(AdapterCertificationError, "runner coverage"):
            self.certify(manifest)

    def test_binding_coverage_is_closed_per_family(self) -> None:
        manifest = deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case["family"] == "public_api":
                case["bindings"] = [
                    binding for binding in case["bindings"] if binding != "cpp"
                ] or ["rust"]
        self.refresh_manifest(manifest)
        with self.assertRaisesRegex(AdapterCertificationError, "binding coverage"):
            self.certify(manifest)

    def test_legacy_path_denominators_are_closed(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["legacy"]["public_inputs"][0:2] = reversed(
            manifest["legacy"]["public_inputs"][0:2]
        )
        self.refresh_manifest(manifest)
        with self.assertRaisesRegex(AdapterCertificationError, "public-input"):
            self.certify(manifest)

    def test_baseline_reproduces_exact_base_blobs(self) -> None:
        self.assertEqual(self.expected_baseline, self.baseline)
        baseline = deepcopy(self.baseline)
        baseline["public_files"][0]["sha256"] = "sha256:" + "0" * 64
        baseline["fingerprint"] = _fingerprint_json(baseline, {"fingerprint"})
        with self.assertRaisesRegex(AdapterCertificationError, "does not reproduce"):
            self.certify(baseline=baseline)


if __name__ == "__main__":
    unittest.main()
