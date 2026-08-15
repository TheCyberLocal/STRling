from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from tooling.interop_contract import (
    InteropContractError,
    InteropContractSuite,
    _fingerprint_json,
    render_c_header,
    wasm_module_paths,
    write_or_check_header,
)


ROOT = Path(__file__).resolve().parents[2]


class InteropContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = InteropContractSuite(ROOT)
        self.abi = json.loads(
            (ROOT / "spec/interop/1.0/abi.json").read_text(encoding="utf-8")
        )
        self.manifest = json.loads(
            (ROOT / "tests/interop/1.0/manifest.json").read_text(encoding="utf-8")
        )

    def certify_manifest(self, manifest: dict[str, object]) -> None:
        self.suite.certify_documents(self.abi, manifest)

    def test_certifies_exact_contract_and_evidence_denominator(self) -> None:
        report = self.suite.certify()
        self.assertEqual(77, report.case_count)
        self.assertEqual(10, len(report.family_counts))
        self.assertRegex(report.contract_fingerprint, r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(report.evidence_fingerprint, r"^sha256:[0-9a-f]{64}$")

    def test_contract_fingerprint_detects_any_governed_input_change(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["contract_fingerprint"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(InteropContractError, "contract fingerprint"):
            self.certify_manifest(manifest)

    def test_evidence_fingerprint_detects_manifest_change(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"][0]["claim"] = "mutated"
        with self.assertRaisesRegex(InteropContractError, "evidence fingerprint"):
            self.certify_manifest(manifest)

    def test_case_removal_is_rejected_even_after_declared_count_change(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"].pop()
        manifest["counts"]["total"] = 76
        manifest["fingerprint"] = _fingerprint_json(manifest, {"fingerprint"})
        with self.assertRaises(InteropContractError):
            self.certify_manifest(manifest)

    def test_duplicate_case_identity_is_rejected(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"][1]["id"] = manifest["cases"][0]["id"]
        manifest["fingerprint"] = _fingerprint_json(manifest, {"fingerprint"})
        with self.assertRaises(InteropContractError):
            self.certify_manifest(manifest)

    def test_family_substitution_is_rejected(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["cases"][0]["family"] = "protocol_failure"
        manifest["fingerprint"] = _fingerprint_json(manifest, {"fingerprint"})
        with self.assertRaises(InteropContractError):
            self.certify_manifest(manifest)

    def test_operation_coverage_is_closed(self) -> None:
        manifest = deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case.get("operation") == "describe":
                case.pop("operation")
        manifest["fingerprint"] = _fingerprint_json(manifest, {"fingerprint"})
        with self.assertRaises(InteropContractError):
            self.certify_manifest(manifest)

    def test_platform_target_coverage_is_closed(self) -> None:
        manifest = deepcopy(self.manifest)
        for case in manifest["cases"]:
            if case.get("target") == "aarch64-apple-darwin":
                case.pop("target")
        manifest["fingerprint"] = _fingerprint_json(manifest, {"fingerprint"})
        with self.assertRaises(InteropContractError):
            self.certify_manifest(manifest)

    def test_abi_error_code_mutation_is_rejected(self) -> None:
        abi = deepcopy(self.abi)
        abi["error_codes"][0]["code"] = "STRL-INTEROP-9999"
        with self.assertRaises(InteropContractError):
            self.suite.certify_documents(abi, self.manifest)

    def test_wasm_host_import_or_shared_memory_is_rejected(self) -> None:
        abi = deepcopy(self.abi)
        abi["wasm_abi"]["host_imports"] = ["wasi_snapshot_preview1"]
        with self.assertRaises(InteropContractError):
            self.suite.certify_documents(abi, self.manifest)

    def test_wasm_module_paths_honor_the_cargo_target_directory(self) -> None:
        with (
            patch("tooling.interop_contract.ROOT", Path("repository")),
            patch.dict("os.environ", {"CARGO_TARGET_DIR": "shared-target"}, clear=True),
        ):
            raw, closed = wasm_module_paths()
        self.assertEqual(
            Path(
                "repository/shared-target/wasm32-unknown-unknown/release/"
                "strling_interop.wasm"
            ),
            raw,
        )
        self.assertEqual(
            raw.with_name("strling_interop.closed.wasm"),
            closed,
        )

    def test_c_header_is_derived_from_exact_native_descriptor(self) -> None:
        header = render_c_header(self.abi)
        for symbol in self.abi["native_abi"]["symbols"]:
            self.assertEqual(1, header.count(symbol["name"]))
        for status in self.abi["native_abi"]["status_values"]:
            self.assertIn(f"{status['name']} = {status['value']}", header)
        self.assertIn("uint8_t *data;", header)
        self.assertIn("size_t len;", header)

    def test_c_header_rejects_unmapped_native_signature(self) -> None:
        abi = deepcopy(self.abi)
        abi["native_abi"]["symbols"][0]["signature"] = "opaque(void)"
        with self.assertRaisesRegex(InteropContractError, "unsupported native"):
            render_c_header(abi)

    def test_c_header_writer_uses_lf_on_every_host(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "strling_interop.h"
            with patch("tooling.interop_contract.HEADER_PATH", destination):
                write_or_check_header(check=False)
            self.assertNotIn(b"\r\n", destination.read_bytes())


if __name__ == "__main__":
    unittest.main()
