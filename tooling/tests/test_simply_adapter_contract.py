from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tooling.simply_adapter_contract import (
    AdapterContractError,
    ROOT,
    certify,
)


class SimplyAdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        for relative in (
            "bindings/python/src/STRling/simply",
            "bindings/typescript/src/STRling/simply",
            "spec/frontends/simply/1.0",
            "spec/frontends/simply/1.1",
        ):
            source = ROOT / relative
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination)
        for relative in (
            "bindings/typescript/src/STRling/compiler.ts",
            "governance/baselines/simply-preview-adapter-compatibility.json",
            "tests/adapters/2.0/legacy-baseline.json",
        ):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_current_adapter_contract_passes(self) -> None:
        report = certify(self.root)
        self.assertEqual("1.1.0", report["protocol_version"])
        self.assertEqual("1.0.0", report["legacy_protocol_version"])
        self.assertEqual(16, report["operation_count"])
        self.assertEqual(15, report["legacy_operation_count"])
        self.assertEqual(1, report["additive_operation_count"])
        self.assertEqual(12, report["error_count"])
        self.assertTrue(report["source_fingerprint"].startswith("sha256:"))

    def test_missing_operation_fails_closed(self) -> None:
        path = self.root / "bindings/typescript/src/STRling/simply/preview.ts"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                'this.append(stepId, "empty", {})',
                'this.append(stepId, "literal", {})',
                1,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            AdapterContractError, "TypeScript Preview operation"
        ):
            certify(self.root)

    def test_host_compiler_dependency_fails_closed(self) -> None:
        path = self.root / "bindings/python/src/STRling/simply/preview.py"
        path.write_text(
            path.read_text(encoding="utf-8") + "\nimport STRling.core\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            AdapterContractError, "forbidden Preview authority"
        ):
            certify(self.root)

    def test_historical_inventory_drift_fails_closed(self) -> None:
        path = (
            self.root / "governance/baselines/simply-preview-adapter-compatibility.json"
        )
        document = json.loads(path.read_text(encoding="utf-8"))
        document["surfaces"][0]["groups"][1]["operations"].clear()
        path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(
            AdapterContractError,
            "historical public-operation inventory",
        ):
            certify(self.root)

    def test_unresolved_disposition_fails_closed(self) -> None:
        path = (
            self.root / "governance/baselines/simply-preview-adapter-compatibility.json"
        )
        document = json.loads(path.read_text(encoding="utf-8"))
        document["unresolved"] = ["surprise"]
        path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(AdapterContractError, "unresolved"):
            certify(self.root)

    def test_response_error_inventory_fails_closed(self) -> None:
        path = self.root / "spec/frontends/simply/1.1/adapter-response.schema.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["$defs"]["Error"]["properties"]["code"]["enum"].pop()
        path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(AdapterContractError, "error inventory"):
            certify(self.root)

    def test_non_additive_protocol_change_fails_closed(self) -> None:
        path = self.root / "spec/frontends/simply/1.1/protocol.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["operations"].append(
            {
                "id": "surprise",
                "destination": "host",
                "materializes_node": False,
                "arguments": [],
                "invariants": [],
            }
        )
        path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(AdapterContractError, "add exactly stdlib_helper"):
            certify(self.root)


if __name__ == "__main__":
    unittest.main()
