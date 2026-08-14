from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tooling.simply_contract import (
    PROTOCOL_1_1_ROOT,
    PROTOCOL_ROOT,
    Simply11ContractSuite,
    SimplyContractError,
    SimplyContractSuite,
)


class SimplyContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.protocol_root = Path(self.temporary.name) / "1.0"
        shutil.copytree(PROTOCOL_ROOT, self.protocol_root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def read_json(self, relative: str) -> dict[str, object]:
        return json.loads((self.protocol_root / relative).read_text(encoding="utf-8"))

    def write_json(self, relative: str, value: object) -> None:
        (self.protocol_root / relative).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_current_protocol_certifies_deterministically(self) -> None:
        first = SimplyContractSuite(self.protocol_root).certify()
        second = SimplyContractSuite(self.protocol_root).certify()
        self.assertEqual(first, second)
        self.assertEqual(
            {
                "schemas": 3,
                "operations": 15,
                "errors": 12,
                "compatibility": 8,
                "positive": 9,
                "negative": 13,
            },
            {key: value for key, value in first.items() if key != "fingerprint"},
        )
        self.assertRegex(first["fingerprint"], r"^sha256:[0-9a-f]{64}$")

    def test_operation_inventory_is_closed(self) -> None:
        protocol = self.read_json("protocol.json")
        operations = protocol["operations"]
        assert isinstance(operations, list)
        operations.pop()
        self.write_json("protocol.json", protocol)
        with self.assertRaises(SimplyContractError):
            SimplyContractSuite(self.protocol_root).certify()

    def test_manifest_detects_any_governed_input_change(self) -> None:
        readme = self.protocol_root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SimplyContractError, "fingerprint is stale"):
            SimplyContractSuite(self.protocol_root).certify()

    def test_schema_widening_cannot_admit_raw_or_target_fields(self) -> None:
        schema = self.read_json("builder-request.schema.json")
        properties = schema["properties"]
        assert isinstance(properties, dict)
        properties["raw_regex"] = {"type": "string"}
        properties["target_pattern"] = {"type": "string"}
        self.write_json("builder-request.schema.json", schema)
        suite = SimplyContractSuite(self.protocol_root)
        base = copy.deepcopy(suite.positive["cases"][0]["request"])
        for marker in ("raw_regex", "target_pattern"):
            request = copy.deepcopy(base)
            request[marker] = "authority escape"
            with (
                self.subTest(marker=marker),
                self.assertRaises(SimplyContractError) as raised,
            ):
                suite.project_request(request)
            self.assertEqual(
                [{"code": "STRL-SIMPLY-0010", "path": f"$.{marker}"}],
                raised.exception.errors,
            )

    def test_compatibility_evidence_must_resolve(self) -> None:
        protocol = self.read_json("protocol.json")
        dispositions = protocol["compatibility_dispositions"]
        assert isinstance(dispositions, list)
        dispositions[0]["evidence"] = ["missing/simply-evidence"]
        self.write_json("protocol.json", protocol)
        with self.assertRaisesRegex(SimplyContractError, "does not resolve"):
            SimplyContractSuite(self.protocol_root).validate_protocol()

    def test_negative_error_identity_is_executable(self) -> None:
        negative = self.read_json("fixtures/negative.json")
        cases = negative["cases"]
        assert isinstance(cases, list)
        case = next(
            item
            for item in cases
            if item["expected"]["errors"][0]["code"] == "STRL-SIMPLY-0010"
        )
        case["expected"]["errors"][0]["code"] = "STRL-SIMPLY-0001"
        self.write_json("fixtures/negative.json", negative)
        with self.assertRaisesRegex(SimplyContractError, "failure identity changed"):
            SimplyContractSuite(self.protocol_root).certify()


class Simply11ContractTests(unittest.TestCase):
    def test_additive_protocol_certifies_deterministically(self) -> None:
        first = Simply11ContractSuite(PROTOCOL_1_1_ROOT).certify()
        second = Simply11ContractSuite(PROTOCOL_1_1_ROOT).certify()
        self.assertEqual(first, second)
        self.assertEqual(
            {
                "schemas": 4,
                "operations": 16,
                "inherited_operations": 15,
                "positive": 8,
                "negative": 2,
            },
            {key: value for key, value in first.items() if key != "fingerprint"},
        )
        self.assertRegex(first["fingerprint"], r"^sha256:[0-9a-f]{64}$")

    def test_every_registry_variant_is_covered(self) -> None:
        suite = Simply11ContractSuite(PROTOCOL_1_1_ROOT)
        self.assertEqual((8, 2), suite.validate_cases())


if __name__ == "__main__":
    unittest.main()
