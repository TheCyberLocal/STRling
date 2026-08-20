from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tooling import typescript_python_adapter_certification as certification


class TypeScriptPythonAdapterCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = certification.ROOT
        cls.suite = certification.TypeScriptPythonAdapterCertificationSuite(cls.root)
        cls.schema = cls._read(certification.SCHEMA_PATH)
        cls.manifest = cls._read(certification.MANIFEST_PATH)
        cls.baseline = cls._read(certification.BASELINE_PATH)
        cls.contract_fingerprint = certification._files_fingerprint(
            cls.root, certification.CONTRACT_FILES
        )
        cls.expected_baseline = certification._build_baseline(cls.root, cls.manifest)
        cls.temporary_root = cls.root / "target" / "codex-tools"
        cls.temporary_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read(path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def certify(
        self,
        manifest: dict[str, object] | None = None,
        baseline: dict[str, object] | None = None,
    ) -> certification.AdapterCertificationReport:
        return self.suite.certify_documents(
            self.schema,
            manifest or self.manifest,
            baseline or self.baseline,
            contract_fingerprint=self.contract_fingerprint,
            expected_baseline=self.expected_baseline,
        )

    def test_pristine_suite_passes(self) -> None:
        report = self.certify()
        self.assertEqual(report.case_count, 72)
        self.assertEqual(report.semantic_copy_count, 31)
        self.assertEqual(report.historical_source_count, 45)
        self.assertEqual(report.historical_case_count, 44)

    def test_contract_fingerprint_drift_fails(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["contract"]["fingerprint"] = "sha256:" + "0" * 64
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_contract_reorder_fails_even_with_recomputed_fingerprints(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["contract"]["files"][0:2] = reversed(
            manifest["contract"]["files"][0:2]
        )
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_case_removal_fails_after_count_edit(self) -> None:
        manifest = deepcopy(self.manifest)
        removed = manifest["cases"].pop()
        manifest["counts"]["total"] -= 1
        manifest["counts"]["families"][removed["family"]] -= 1
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_duplicate_case_id_fails(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"][1]["id"] = manifest["cases"][0]["id"]
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_runner_substitution_fails(self) -> None:
        manifest = deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case["runner"] == "browser-runtime":
                case["runner"] = "node-runtime"
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_family_binding_shrinkage_fails(self) -> None:
        manifest = deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case["family"] == "historical_preservation":
                case["bindings"] = ["typescript"]
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_operation_substitution_fails(self) -> None:
        manifest = deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case.get("operation") == "describe":
                case["operation"] = "compile"
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_runtime_substitution_fails(self) -> None:
        manifest = deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case.get("runtime") == "browser-wasm":
                case["runtime"] = "node-22"
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_historical_corpus_fingerprint_drift_fails(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["historical"]["corpora"]["typescript"]["fingerprint"] = (
            "sha256:" + "0" * 64
        )
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_semantic_copy_path_substitution_fails(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["legacy"]["semantic_copy_paths"][0] = (
            "bindings/typescript/src/index.ts"
        )
        manifest["fingerprint"] = certification._fingerprint_json(
            manifest, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(manifest)

    def test_source_blob_mutation_fails_after_editable_hashes_change(self) -> None:
        baseline = deepcopy(self.baseline)
        entry = baseline["historical_source_files"][0]
        content = base64.b64decode(entry["content_base64"])
        changed = content + b"\n"
        entry["content_base64"] = base64.b64encode(changed).decode("ascii")
        entry["sha256"] = "sha256:" + hashlib.sha256(changed).hexdigest()
        baseline["fingerprint"] = certification._fingerprint_json(
            baseline, {"fingerprint"}
        )
        with self.assertRaises(certification.AdapterCertificationError):
            self.certify(baseline=baseline)

    def test_historical_bundle_materializes_exact_sources(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="adapter-history-", dir=self.temporary_root
        ) as directory:
            destination = Path(directory)
            certification.materialize_historical_sources(destination, self.root)
            for entry in self.baseline["historical_source_files"]:
                content = (destination / entry["path"]).read_bytes()
                actual = "sha256:" + hashlib.sha256(content).hexdigest()
                self.assertEqual(actual, entry["sha256"])


if __name__ == "__main__":
    unittest.main()
