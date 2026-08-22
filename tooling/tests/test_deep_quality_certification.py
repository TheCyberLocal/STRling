from __future__ import annotations

import copy
import json
import unittest
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import patch

from jsonschema import Draft202012Validator

from tooling.deep_quality_certification import (
    EXPECTED_COUNTS,
    INHERITED_FUZZ_IDS,
    INHERITED_SANITIZER_IDS,
    MUTANT_IDS,
    OWNED_FUZZ_IDS,
    OWNED_SANITIZER_IDS,
    PROPERTY_IDS,
    PULL_REQUEST_MUTANT_IDS,
    DeepQualityError,
    _replace_occurrence,
    certify,
    fingerprint,
    manifest_fingerprint,
    validate_evidence,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "governance/schemas/deep-quality-certification.schema.json"
MANIFEST_PATH = ROOT / "tests/certification/deep-quality/1.0/manifest.json"
FIXTURE_PATH = (
    ROOT / "tests/certification/deep-quality/1.0/fixtures/valid-evidence.json"
)
MUTATIONS_PATH = ROOT / "tests/certification/deep-quality/1.0/fixtures/mutations.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


def pointer_parent(document: object, pointer: str) -> tuple[object, str]:
    current = document
    parts = pointer.lstrip("/").split("/")
    for part in parts[:-1]:
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise TypeError(f"cannot traverse {pointer!r}")
    return current, parts[-1]


def apply_mutation(document: dict[str, Any], mutation: dict[str, Any]) -> None:
    parent, key = pointer_parent(document, mutation["path"])
    operation = mutation["operation"]
    if operation == "remove":
        if isinstance(parent, list):
            parent.pop(int(key))
        else:
            del parent[key]
    elif operation == "replace":
        if isinstance(parent, list):
            parent[int(key)] = copy.deepcopy(mutation["value"])
        else:
            parent[key] = copy.deepcopy(mutation["value"])
    elif operation == "duplicate":
        if not isinstance(parent, list):
            raise TypeError("duplicate mutation must target a list item")
        parent.append(copy.deepcopy(parent[int(key)]))
    else:
        raise ValueError(f"unsupported mutation operation {operation!r}")


class DeepQualityCertificationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.manifest = load_json(MANIFEST_PATH)
        cls.fixture = load_json(FIXTURE_PATH)
        cls.mutations = load_json(MUTATIONS_PATH)["mutations"]

    def test_schema_and_positive_contract_fixture_validate(self) -> None:
        validator = Draft202012Validator(self.schema)
        validator.validate(self.manifest)
        validator.validate(self.fixture)
        validate_manifest(self.manifest)
        validate_evidence(self.fixture, manifest=self.manifest)

    def test_denominators_and_profile_partitions_are_exact(self) -> None:
        self.assertEqual(self.manifest["expected_counts"], EXPECTED_COUNTS)
        self.assertEqual(
            [row["id"] for row in self.manifest["property_suites"]], PROPERTY_IDS
        )
        self.assertEqual(
            [row["id"] for row in self.manifest["fuzz_targets"]],
            INHERITED_FUZZ_IDS + OWNED_FUZZ_IDS,
        )
        self.assertEqual(
            [row["id"] for row in self.manifest["sanitizer_cases"]],
            INHERITED_SANITIZER_IDS + OWNED_SANITIZER_IDS,
        )
        self.assertEqual([row["id"] for row in self.manifest["mutants"]], MUTANT_IDS)
        partitions = {row["id"]: row for row in self.manifest["profile_partitions"]}
        self.assertEqual(
            partitions["pull-request"]["mutant_ids"], PULL_REQUEST_MUTANT_IDS
        )
        self.assertEqual(partitions["full"]["mutant_ids"], MUTANT_IDS)
        self.assertEqual(partitions["full"]["fuzz_target_ids"], OWNED_FUZZ_IDS)
        self.assertEqual(partitions["full"]["sanitizer_case_ids"], OWNED_SANITIZER_IDS)

    def test_source_and_fuzz_license_boundaries_are_exact(self) -> None:
        source_paths = {
            source["path"]
            for suite in self.manifest["property_suites"]
            for source in suite["sources"]
        }
        self.assertEqual(len(source_paths), 16)
        self.assertEqual(
            {row["ownership"] for row in self.manifest["fuzz_targets"]},
            {"p17-inherited", "p18-t03"},
        )
        self.assertEqual(self.manifest["toolchain"]["libfuzzer_sys"], "0.4.13")
        self.assertEqual(
            self.manifest["toolchain"]["fuzz_dependency_root"],
            "interop-fuzz-cargo",
        )
        owned = [
            row
            for row in self.manifest["fuzz_targets"]
            if row["ownership"] == "p18-t03"
        ]
        self.assertTrue(all(row["state"] == "active" for row in owned))
        self.assertTrue(all(len(row["source_sha256"]) == 64 for row in owned))
        self.assertTrue(
            all(
                row["corpus_seed_path"].startswith("bindings/interop/fuzz/corpus/deep-")
                for row in owned
            )
        )
        self.assertTrue(all(len(row["corpus_seed_sha256"]) == 64 for row in owned))

    def test_local_execution_is_contract_only_and_machine_readable(self) -> None:
        evidence, exit_code = certify("local", manifest=self.manifest)
        self.assertEqual(exit_code, 0)
        self.assertEqual(evidence["status"], "passed")
        self.assertEqual(
            [check["id"] for check in evidence["checks"]], ["contract:manifest"]
        )
        self.assertEqual(evidence["operation_id"], "certification.deep-quality-local")

    def test_source_mutation_replaces_only_the_selected_occurrence(self) -> None:
        self.assertEqual(
            _replace_occurrence("before before", "before", "after", 2),
            "before after",
        )
        with self.assertRaises(DeepQualityError) as raised:
            _replace_occurrence("before", "before", "after", 2)
        self.assertEqual(raised.exception.code, "stale-mutation")

    def test_full_non_linux_disposition_is_explicit(self) -> None:
        properties = [
            {"id": item, "status": "passed", "details": {}} for item in PROPERTY_IDS
        ]
        mutants = [
            {"id": item, "status": "passed", "details": {}} for item in MUTANT_IDS
        ]
        with (
            patch(
                "tooling.deep_quality_certification._run_properties",
                return_value=properties,
            ),
            patch(
                "tooling.deep_quality_certification._run_mutants",
                return_value=mutants,
            ),
            patch(
                "tooling.deep_quality_certification.supported_host", return_value=False
            ),
        ):
            evidence, exit_code = certify("full", manifest=self.manifest)
        self.assertEqual(exit_code, 2)
        self.assertEqual(evidence["status"], "unavailable")
        checks = {check["id"]: check for check in evidence["checks"]}
        for case_id in OWNED_FUZZ_IDS + OWNED_SANITIZER_IDS:
            self.assertEqual(checks[case_id]["status"], "unavailable")
            self.assertEqual(
                checks[case_id]["details"]["required_target"],
                "x86_64-unknown-linux-gnu",
            )

    def test_mutation_policy_is_criticality_specific_and_zero_survivor(self) -> None:
        policies = {
            row["criticality"]: row for row in self.manifest["mutation_policies"]
        }
        self.assertEqual(set(policies), {"critical", "high"})
        self.assertTrue(
            all(
                row["minimum_kill_basis_points"] == 10000
                and row["maximum_survivors"] == 0
                for row in policies.values()
            )
        )
        self.assertEqual(
            Counter(row["criticality"] for row in self.manifest["mutants"]),
            {"critical": 8, "high": 6},
        )
        self.assertEqual(
            {row["category"] for row in self.manifest["mutants"]},
            {
                "normalization",
                "capability-evaluation",
                "portability-aggregation",
                "safety-diagnostics",
                "target-lowering",
                "equivalence-rewrite",
                "certification-aggregation",
            },
        )

    def test_fingerprint_is_canonical_and_fixture_is_explicitly_synthetic(self) -> None:
        self.assertEqual(
            self.manifest["manifest_fingerprint"],
            manifest_fingerprint(self.manifest),
        )
        self.assertEqual(self.fixture["evidence_kind"], "synthetic-contract-fixture")
        self.assertTrue(self.fixture["checks"][0]["details"]["fixture"])
        self.assertEqual(
            self.fixture["evidence_fingerprint"],
            fingerprint(self.fixture["deterministic_evidence"]),
        )

    def test_every_controlled_mutation_fails_closed(self) -> None:
        self.assertEqual(len(self.mutations), 12)
        self.assertEqual(
            len({mutation["id"] for mutation in self.mutations}), len(self.mutations)
        )
        for mutation in self.mutations:
            document = copy.deepcopy(
                self.manifest if mutation["document"] == "manifest" else self.fixture
            )
            apply_mutation(document, mutation)
            if mutation["document"] == "manifest":
                if mutation["id"] != "mutation.manifest-fingerprint":
                    document["manifest_fingerprint"] = manifest_fingerprint(document)
            else:
                if mutation["id"] == "mutation.evidence-summary":
                    document["evidence_fingerprint"] = fingerprint(
                        document["deterministic_evidence"]
                    )
            with self.subTest(mutation=mutation["id"]):
                with self.assertRaises(DeepQualityError) as raised:
                    if mutation["document"] == "manifest":
                        validate_manifest(document)
                    else:
                        validate_evidence(document, manifest=self.manifest)
                self.assertEqual(raised.exception.code, mutation["expected_code"])


if __name__ == "__main__":
    unittest.main()
