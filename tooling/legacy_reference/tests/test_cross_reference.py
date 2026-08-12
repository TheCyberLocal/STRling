from __future__ import annotations

import copy
import importlib
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

cross = importlib.import_module("tooling.legacy_reference.cross_reference")
reference = importlib.import_module("tooling.legacy_reference.python_reference")


def fake_certification(
    runner_id: str,
    corpus: dict[str, object],
    fingerprint_character: str,
) -> dict[str, object]:
    cases = corpus["cases"]
    assert isinstance(cases, list)
    operations = Counter(entry["request"]["operation"] for entry in cases)
    language = "typescript" if runner_id == "typescript" else "python"
    return {
        "case_summaries": [
            {
                "case_id": entry["id"],
                "operation": entry["request"]["operation"],
            }
            for entry in cases
        ],
        "certification_kind": reference.CERTIFICATION_KIND,
        "certification_schema_version": reference.CERTIFICATION_SCHEMA_VERSION,
        "corpus": {
            "algorithm": "sha256",
            "fingerprint": reference.canonical_fingerprint(corpus),
            "version": corpus["corpus_version"],
        },
        "fixture_immutability": {
            "corpus_unchanged": True,
            "governed_implementation_inputs_unchanged": True,
        },
        "implementation": {
            "algorithm": "sha256",
            "fingerprint": f"sha256:{fingerprint_character * 64}",
            "kind": f"strling.legacy-{runner_id}-implementation",
        },
        "malformed_cases": sum(
            entry["behavior_family"] == "malformed-input" for entry in cases
        ),
        "observation_schema_version": reference.OBSERVATION_SCHEMA_VERSION,
        "operation_counts": dict(operations),
        "outcome_counts": {"success": len(cases)},
        "protocol_version": reference.PROTOCOL_VERSION,
        "repeatability": {
            "canonical_batches_compared": 3,
            "canonical_observations_compared": len(cases) * 3,
            "mismatches": 0,
            "repeat_runs": 3,
        },
        "runner": {
            "id": runner_id,
            "kind": reference.RUNNER["kind"],
            "language": language,
            "version": "1.0.0",
        },
        "status": "passed",
        "unexplained_failures": 0,
    }


class CrossReferenceCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpora = {
            "python": cross.load_corpus(cross.PYTHON_CORPUS_PATH),
            "typescript": cross.load_corpus(cross.TYPESCRIPT_CORPUS_PATH),
        }
        cls.certifications = {
            "python": fake_certification("python", cls.corpora["python"], "a"),
            "typescript": fake_certification(
                "typescript",
                cls.corpora["typescript"],
                "b",
            ),
        }

    def certify(self) -> dict[str, object]:
        return cross.certify_cross_runner(
            copy.deepcopy(self.certifications),
            copy.deepcopy(self.corpora),
        )

    def test_shared_cases_require_matching_identity_operation_input_and_options(
        self,
    ) -> None:
        certification = self.certify()
        shared_ids = {entry["case_id"] for entry in certification["shared_cases"]}
        self.assertEqual(
            shared_ids,
            {
                "compiler-directive-flags",
                "compiler-literal-normalization",
                "emitter-redos-warning",
                "emitter-variable-lookbehind",
                "parser-artifact-repetition",
                "parser-escape-class",
                "parser-extended-directive",
                "parser-groups-alternation-lookaround",
                "parser-literal",
                "parser-malformed-group",
                "simply-literal-empty",
                "simply-literal-escaping",
            },
        )
        self.assertNotIn("compiler-malformed-group", shared_ids)
        self.assertNotIn("compiler-feature-metadata", shared_ids)
        self.assertEqual(
            {tuple(entry["runners"]) for entry in certification["shared_cases"]},
            {("python", "typescript")},
        )

    def test_runner_specific_cases_remain_partitioned(self) -> None:
        certification = self.certify()
        partitions = {
            entry["runner_id"]: entry["cases"]
            for entry in certification["runner_specific_cases"]
        }
        self.assertEqual(len(partitions["typescript"]), 12)
        self.assertEqual(len(partitions["python"]), 8)
        self.assertRegex(
            partitions["python"][0]["case_identity"],
            r"^sha256:[0-9a-f]{64}$",
        )

    def test_quantitative_totals_do_not_compare_runner_outputs(self) -> None:
        certification = self.certify()
        self.assertEqual(
            certification["totals"],
            {
                "canonical_observations_compared": 132,
                "malformed_cases": 4,
                "repeat_mismatches": 0,
                "repeat_runs": 6,
                "runner_cases": 44,
                "runner_specific_cases": 20,
                "runners": 2,
                "shared_cases": 12,
                "shared_runner_cases": 24,
                "unexplained_failures": 0,
            },
        )
        encoded = reference.canonical_json(certification)
        for forbidden_field in (
            '"consensus"',
            '"defect"',
            '"preserved"',
            '"corrected"',
            '"equivalent"',
            '"incompatible"',
            '"normative"',
        ):
            self.assertNotIn(forbidden_field, encoded)

    def test_canonical_certification_is_repeatable_and_does_not_mutate_inputs(
        self,
    ) -> None:
        corpora_before = reference.canonical_json(self.corpora)
        certifications_before = reference.canonical_json(self.certifications)
        first = self.certify()
        second = self.certify()
        self.assertEqual(
            cross.serialize_certification(first),
            cross.serialize_certification(second),
        )
        self.assertEqual(reference.canonical_json(self.corpora), corpora_before)
        self.assertEqual(
            reference.canonical_json(self.certifications),
            certifications_before,
        )

    def test_implementation_identities_are_independently_sensitive(self) -> None:
        baseline = self.certify()
        changed_inputs = copy.deepcopy(self.certifications)
        changed_inputs["python"]["implementation"]["fingerprint"] = "sha256:" + (
            "c" * 64
        )
        changed = cross.certify_cross_runner(changed_inputs, self.corpora)
        baseline_by_runner = {
            entry["runner"]["id"]: entry for entry in baseline["runners"]
        }
        changed_by_runner = {
            entry["runner"]["id"]: entry for entry in changed["runners"]
        }
        self.assertEqual(
            baseline_by_runner["typescript"],
            changed_by_runner["typescript"],
        )
        self.assertNotEqual(
            baseline_by_runner["python"]["implementation"],
            changed_by_runner["python"]["implementation"],
        )

        typescript_changed_inputs = copy.deepcopy(self.certifications)
        typescript_changed_inputs["typescript"]["implementation"]["fingerprint"] = (
            "sha256:" + ("d" * 64)
        )
        typescript_changed = cross.certify_cross_runner(
            typescript_changed_inputs,
            self.corpora,
        )
        typescript_changed_by_runner = {
            entry["runner"]["id"]: entry for entry in typescript_changed["runners"]
        }
        self.assertEqual(
            baseline_by_runner["python"],
            typescript_changed_by_runner["python"],
        )
        self.assertNotEqual(
            baseline_by_runner["typescript"]["implementation"],
            typescript_changed_by_runner["typescript"]["implementation"],
        )

    def test_invalid_runner_identity_and_repeat_mismatch_are_rejected(self) -> None:
        wrong_runner = copy.deepcopy(self.certifications)
        wrong_runner["python"]["runner"]["id"] = "typescript"
        with self.assertRaisesRegex(
            cross.CrossCertificationError,
            "wrong runner identity",
        ):
            cross.certify_cross_runner(wrong_runner, self.corpora)

        mismatch = copy.deepcopy(self.certifications)
        mismatch["typescript"]["repeatability"]["mismatches"] = 1
        with self.assertRaisesRegex(
            cross.CrossCertificationError,
            "repeatability evidence is invalid",
        ):
            cross.certify_cross_runner(mismatch, self.corpora)

    def test_corpus_fingerprint_and_case_coverage_are_validated(self) -> None:
        wrong_fingerprint = copy.deepcopy(self.certifications)
        wrong_fingerprint["python"]["corpus"]["fingerprint"] = "sha256:" + ("e" * 64)
        with self.assertRaisesRegex(
            cross.CrossCertificationError,
            "does not match its source",
        ):
            cross.certify_cross_runner(wrong_fingerprint, self.corpora)

        missing_summary = copy.deepcopy(self.certifications)
        missing_summary["typescript"]["case_summaries"].pop()
        with self.assertRaisesRegex(
            cross.CrossCertificationError,
            "do not cover its corpus",
        ):
            cross.certify_cross_runner(missing_summary, self.corpora)


if __name__ == "__main__":
    unittest.main()
