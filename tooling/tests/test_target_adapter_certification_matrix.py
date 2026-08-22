from __future__ import annotations

import copy
import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tooling.certification import profile_definition_fingerprint
from tooling.product_certification import (
    _certification_profile,
    expected_profile_result_ids,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    ROOT / "governance/schemas/target-adapter-certification-matrix.schema.json"
)
MANIFEST_PATH = ROOT / "tests/certification/target-adapter/1.0/manifest.json"
FIXTURE_PATH = (
    ROOT
    / "tests/certification/target-adapter/1.0/fixtures/valid-evidence.json"
)
MUTATIONS_PATH = (
    ROOT / "tests/certification/target-adapter/1.0/fixtures/mutations.json"
)
TARGET_ROOT = ROOT / "spec/targets/profiles"
BINDING_SUPPORT_PATH = ROOT / "tests/adapters/binding-support-4.0/evidence.json"
TOOLCHAIN_PATH = ROOT / "toolchain.json"

TARGET_OBLIGATIONS = [
    "compile_acceptance",
    "match_nonmatch",
    "captures",
    "diagnostics",
    "options_unicode",
    "profile_constraints",
    "stdlib_helpers",
]
ADAPTER_OBLIGATIONS = {
    "supported_candidate": [
        "canonical_request_result",
        "package_install",
        "public_contract",
        "declared_runtime_platform",
        "quality_profile",
    ],
    "preview_candidate": [
        "canonical_request_result",
        "package_metadata",
        "public_contract",
        "executed_runtime_platform",
    ],
    "legacy_candidate": [
        "canonical_route_static",
        "public_contract",
        "retained_compatibility_fixture",
    ],
}
STATUS_NAMES = [
    "passed",
    "failed",
    "unavailable",
    "not_applicable",
    "waived",
    "unsupported",
]


class EvidenceError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


def canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def schema_validator() -> Draft202012Validator:
    return Draft202012Validator(load_json(SCHEMA_PATH))


def pointer_parent(document: object, pointer: str) -> tuple[object, str]:
    parts = pointer.lstrip("/").split("/")
    current = document
    for part in parts[:-1]:
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise TypeError(f"cannot traverse mutation pointer {pointer!r}")
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
        value = copy.deepcopy(mutation["value"])
        if isinstance(parent, list):
            parent[int(key)] = value
        else:
            parent[key] = value
    elif operation == "duplicate":
        if not isinstance(parent, list):
            raise TypeError("duplicate mutation must address a list item")
        parent.append(copy.deepcopy(parent[int(key)]))
    else:
        raise ValueError(f"unsupported mutation operation {operation!r}")


def validate_fixture(
    artifact: dict[str, Any], *, expected: dict[str, Any] | None = None
) -> None:
    errors = sorted(schema_validator().iter_errors(artifact), key=lambda item: list(item.path))
    if errors:
        raise EvidenceError(f"schema: {errors[0].message}")

    deterministic = artifact["deterministic_evidence"]
    if artifact["evidence_fingerprint"] != canonical_digest(deterministic):
        raise EvidenceError("fingerprint: deterministic evidence fingerprint differs")

    target_cells = deterministic["target_cells"]
    adapter_cells = deterministic["adapter_cells"]
    cells = target_cells + adapter_cells
    cell_ids = [cell["cell_id"] for cell in cells]
    if len(cell_ids) != len(set(cell_ids)):
        raise EvidenceError("duplicate-cell: cell IDs must be unique")

    coverage = deterministic["coverage"]
    cell_ids_fingerprint = canonical_digest(sorted(cell_ids))
    if (
        coverage["observed_cell_count"] != len(cells)
        or coverage["expected_cell_count"] != len(cells)
        or coverage["observed_cell_ids_fingerprint"] != cell_ids_fingerprint
        or coverage["expected_cell_ids_fingerprint"] != cell_ids_fingerprint
        or coverage["observed_target_coordinates"]
        != len({cell["coordinate"]["profile_id"] for cell in target_cells})
        or coverage["observed_adapter_coordinates"]
        != len({cell["coordinate"]["adapter_id"] for cell in adapter_cells})
    ):
        raise EvidenceError("missing-cell: coverage does not match observed cells")

    aggregate = deterministic["aggregate"]
    counts = Counter(cell["status"] for cell in cells)
    if (
        aggregate["cell_count"] != len(cells)
        or aggregate["target_cell_count"] != len(target_cells)
        or aggregate["adapter_cell_count"] != len(adapter_cells)
        or aggregate["counts"] != {status: counts[status] for status in STATUS_NAMES}
    ):
        raise EvidenceError("aggregate: cell counts do not match the matrix")

    for cell in cells:
        if (cell["status"] == "passed") != (cell["claim_status"] == "certified"):
            raise EvidenceError("false-claim: only passed cells may be certified")

    if expected is None:
        return
    expected_cells = {
        cell["cell_id"]: cell
        for cell in expected["deterministic_evidence"]["target_cells"]
        + expected["deterministic_evidence"]["adapter_cells"]
    }
    if set(cell_ids) != set(expected_cells):
        raise EvidenceError("missing-cell: evidence denominator changed")
    known_results = {
        source["result_id"]
        for cell in expected_cells.values()
        for source in cell["source_results"]
    }
    for cell in cells:
        baseline = expected_cells[cell["cell_id"]]
        coordinate = cell["coordinate"]
        baseline_coordinate = baseline["coordinate"]
        if cell["dimension"] == "target" and coordinate != baseline_coordinate:
            raise EvidenceError("stale-target: target coordinate changed")
        if cell["dimension"] == "adapter" and coordinate != baseline_coordinate:
            raise EvidenceError("stale-adapter: adapter coordinate changed")
        if any(
            source["result_id"] not in known_results
            for source in cell["source_results"]
        ):
            raise EvidenceError("unknown-result: source result is not declared")


class TargetAdapterEvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.manifest = load_json(MANIFEST_PATH)
        cls.fixture = load_json(FIXTURE_PATH)
        cls.mutations = load_json(MUTATIONS_PATH)["mutations"]
        cls.toolchain = load_json(TOOLCHAIN_PATH)
        cls.binding_support = load_json(BINDING_SUPPORT_PATH)

    def test_schema_accepts_manifest_and_positive_artifact(self) -> None:
        validator = Draft202012Validator(self.schema)
        validator.validate(self.manifest)
        validator.validate(self.fixture)
        validate_fixture(self.fixture)

    def test_manifest_matches_full_profile_identity_and_result_membership(self) -> None:
        full = _certification_profile(self.toolchain, "full")
        declared = self.manifest["full_profile"]
        self.assertEqual(declared["definition_version"], full["definition_version"])
        self.assertEqual(
            declared["definition_fingerprint"],
            profile_definition_fingerprint(full),
        )
        known_results = set(expected_profile_result_ids(self.toolchain, "full"))
        referenced_results = {
            source[key]
            for source in self.manifest["target_sources"]
            for key in (
                "runtime_result_id",
                "shared_result_id",
                "stdlib_result_id",
            )
        }
        for source in self.manifest["adapter_sources"]:
            for key in (
                "runtime_result_ids",
                "package_result_ids",
                "public_contract_result_ids",
                "environment_result_ids",
                "quality_result_ids",
            ):
                referenced_results.update(source[key])
        self.assertEqual(set(), referenced_results.difference(known_results))

    def test_manifest_matches_target_profile_registry(self) -> None:
        profiles = [load_json(path) for path in sorted(TARGET_ROOT.glob("*.json"))]
        expected = sorted(profile["profile_id"] for profile in profiles)
        observed = [source["profile_id"] for source in self.manifest["target_sources"]]
        self.assertEqual(expected, observed)
        self.assertEqual(TARGET_OBLIGATIONS, self.manifest["target_policy"]["obligations"])
        pcre = {
            source["profile_id"]: source["runtime_check_id"]
            for source in self.manifest["target_sources"]
            if source["profile_id"].startswith("profile:pcre2/")
        }
        self.assertEqual(
            {
                "profile:pcre2/10.42": "certification.pcre2-runtime.10.42",
                "profile:pcre2/10.43": "certification.pcre2-runtime.10.43",
            },
            pcre,
        )

    def test_manifest_matches_binding_support_registry_and_tiers(self) -> None:
        expected = {
            binding["id"]: binding["certification_tier"]
            for binding in self.binding_support["bindings"]
        }
        observed = {
            source["adapter_id"]: source["certification_tier"]
            for source in self.manifest["adapter_sources"]
        }
        self.assertEqual(expected, observed)
        policies = {
            policy["tier"]: policy
            for policy in self.manifest["adapter_tier_policies"]
        }
        self.assertEqual(set(ADAPTER_OBLIGATIONS), set(policies))
        for tier, obligations in ADAPTER_OBLIGATIONS.items():
            self.assertEqual(obligations, policies[tier]["obligations"])
        self.assertTrue(policies["supported_candidate"]["readiness_blocking"])
        self.assertFalse(policies["preview_candidate"]["readiness_blocking"])
        self.assertFalse(policies["legacy_candidate"]["readiness_blocking"])

    def test_closed_matrix_denominator_is_115_cells(self) -> None:
        target_cells = len(self.manifest["target_sources"]) * len(TARGET_OBLIGATIONS)
        adapter_cells = sum(
            len(ADAPTER_OBLIGATIONS[source["certification_tier"]])
            for source in self.manifest["adapter_sources"]
        )
        self.assertEqual(35, target_cells)
        self.assertEqual(80, adapter_cells)
        self.assertEqual(115, target_cells + adapter_cells)

    def test_every_adapter_has_explicit_runtime_package_public_and_environment_sources(
        self,
    ) -> None:
        for source in self.manifest["adapter_sources"]:
            with self.subTest(adapter=source["adapter_id"]):
                self.assertTrue(source["runtime_result_ids"])
                self.assertTrue(source["package_result_ids"])
                self.assertEqual(
                    ["contracts_check@repository"],
                    source["public_contract_result_ids"],
                )
                self.assertTrue(source["environment_result_ids"])
                self.assertTrue(source["quality_result_ids"])

    def test_contract_has_no_external_regex_conformance_authority(self) -> None:
        paths = [
            item
            for source in self.manifest["adapter_sources"]
            for key, value in source.items()
            for item in (value if isinstance(value, list) else [value])
            if key.endswith("result_ids")
        ]
        self.assertFalse(any("regex-conformance" in str(item) for item in paths))

    def test_all_declared_single_delta_mutations_fail_closed(self) -> None:
        self.assertEqual(11, len(self.mutations))
        self.assertEqual(
            len(self.mutations), len({mutation["id"] for mutation in self.mutations})
        )
        for mutation in self.mutations:
            with self.subTest(mutation=mutation["id"]):
                candidate = copy.deepcopy(self.fixture)
                apply_mutation(candidate, mutation)
                if mutation["refresh_fingerprint"]:
                    candidate["evidence_fingerprint"] = canonical_digest(
                        candidate["deterministic_evidence"]
                    )
                with self.assertRaises(EvidenceError):
                    validate_fixture(candidate, expected=self.fixture)


if __name__ == "__main__":
    unittest.main()
