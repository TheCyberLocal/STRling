"""Mutation and transport tests for empirical adversarial evidence, not semantics."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import ValidationError

from tooling import adversarial_semantic_audit as audit


class AdversarialCorpusTests(unittest.TestCase):
    def setUp(self):
        self.corpus = audit.validate_corpus()

    def reject(self, mutation):
        value = copy.deepcopy(self.corpus)
        mutation(value)
        with self.assertRaises((ValueError, ValidationError)):
            audit.validate_corpus(value)

    def test_broader_than_previous_subject_denominator(self):
        self.assertGreater(len({s["value"] for s in self.corpus["subjects"]}), 49)

    def test_every_line_form_is_required_in_each_line_context(self):
        for name in audit.LINES:
            for context in ("bare", "start", "end", "final"):
                with self.subTest(name=name, context=context):

                    def mutate(value):
                        for subject in value["subjects"]:
                            if subject["id"] == f"line-{name}-{context}":
                                subject["value"] = "agreement-only"

                    self.reject(mutate)

    def test_unicode_categories_are_values_not_just_tags(self):
        for category in ("Mn", "Pc", "Lo", "Nl", "Nd", "No"):

            def mutate(value):
                for subject in value["subjects"]:
                    if "category:" + category in subject["tags"]:
                        subject["value"] = "a"

            self.reject(mutate)

    def test_casefold_edges_are_bidirectional(self):
        for point in audit.EDGE_POINTS:

            def mutate(value):
                for subject in value["subjects"]:
                    if subject["value"] == chr(point):
                        subject["value"] = "a"

            self.reject(mutate)

    def test_missing_semantic_cases_cannot_be_renamed_away(self):
        for case_id in ("wildcard-excluding-lines", "unicode-word-class"):

            def mutate(value):
                next(c for c in value["cases"] if c["id"] == case_id)["id"] = (
                    "substitute"
                )

            self.reject(mutate)

    def test_line_matrix_obligation_cannot_be_removed(self):
        def mutate(value):
            for case in value["cases"]:
                case["tags"] = [
                    t for t in case["tags"] if not t.startswith("line-matrix:")
                ]

        self.reject(mutate)

    def test_capture_obligations_cannot_be_removed(self):
        for tag in ("capture:nonparticipating", "capture:reset-in-repetition"):

            def mutate(value):
                for case in value["cases"]:
                    case["tags"] = [t for t in case["tags"] if t != tag]

            self.reject(mutate)

    def test_bytes_inputs_cannot_be_restricted_to_ascii(self):
        def mutate(value):
            for subject in value["subjects"]:
                if subject["id"] in {"utf8-two", "utf8-three"}:
                    subject["value"] = "a"

        self.reject(mutate)

    def test_no_orphaned_subject_can_satisfy_coverage(self):
        self.reject(
            lambda value: value["subjects"].append(
                {"id": "orphan", "value": "x", "tags": ["control"]}
            )
        )

    def test_observed_expectations_are_not_corpus_authority(self):
        self.reject(lambda value: value["cases"][0].update(expected_pattern="."))


class AdversarialHarnessTests(unittest.TestCase):
    def test_multibyte_partial_match_is_preserved(self):
        raw = {
            "span": [0, 1],
            "captures": [{"index": 1, "span": [0, 1], "value": "c3"}],
        }
        result = audit.normalize_match(raw, "é", "profile:python-re/3.11-bytes")
        self.assertEqual([0, 1], result["span_utf8"])
        self.assertEqual("c3", result["captures"][0]["value_utf8_hex"])
        text = audit.normalize_match({"span": [0, 1]}, "é", "profile:python-re/3.11")
        self.assertEqual([0, 2], text["span_utf8"])

    def test_utf16_offsets_match_utf8_without_erasing_span_differences(self):
        result = audit.normalize_match(
            {"span": [0, 2]}, "😀", "profile:ecmascript/2024"
        )
        self.assertEqual([0, 4], result["span_utf8"])

    def test_first_search_does_not_become_fullmatch(self):
        result = audit.normalize_match({"span": [1, 2]}, "ba", "profile:python-re/3.11")
        self.assertTrue(result["matched"])
        self.assertEqual([1, 2], result["span_utf8"])

    def test_bytes_adapter_executes_exact_emitted_pattern_with_utf8_subject(self):
        artifact = {
            "target_profile": {"profile_id": "profile:python-re/3.11-bytes"},
            "pattern": {"text": ".", "flags": []},
        }
        response = {
            "cases": [
                {
                    "id": "adversarial",
                    "compile": {"status": "ok"},
                    "observations": [
                        {"subject": "c3a9", "matches": [{"span": [0, 1]}]}
                    ],
                }
            ]
        }
        with mock.patch.object(
            audit, "python_harness", return_value=response
        ) as harness:
            _, observations = audit.execute_artifact(
                artifact, ["é"], {"python": "governed"}
            )
        request = harness.call_args.args[1]["cases"][0]
        self.assertEqual(".", request["source"])
        self.assertEqual(["c3a9"], request["subjects"])
        self.assertEqual([0, 1], observations[0]["span_utf8"])

    def test_truncated_engine_response_cannot_look_like_agreement(self):
        artifact = {
            "target_profile": {"profile_id": "profile:python-re/3.11"},
            "pattern": {"text": "."},
        }
        response = {
            "cases": [
                {"id": "adversarial", "compile": {"status": "ok"}, "observations": []}
            ]
        }
        with mock.patch.object(audit, "python_harness", return_value=response):
            with self.assertRaisesRegex(ValueError, "denominator"):
                audit.execute_artifact(artifact, ["a"], {"python": "governed"})

    def test_target_compile_failure_is_never_no_match(self):
        artifact = {
            "target_profile": {"profile_id": "profile:python-re/3.11"},
            "pattern": {"text": "("},
        }
        response = {
            "cases": [
                {
                    "id": "adversarial",
                    "compile": {"status": "error"},
                    "observations": [],
                }
            ]
        }
        with mock.patch.object(audit, "python_harness", return_value=response):
            raw, observations = audit.execute_artifact(
                artifact, ["a"], {"python": "governed"}
            )
        self.assertEqual("error", raw["compile"]["status"])
        self.assertEqual([], observations)

    def test_capture_reset_is_compared_even_when_match_spans_agree(self):
        rows = []
        for profile, captured in [
            ("profile:ecmascript/2024", False),
            ("profile:pcre2/10.43", True),
        ]:
            rows.append(
                {
                    "case_id": "reset",
                    "profile": {"profile_id": profile},
                    "compile": {"stdout": {}},
                    "observations": [
                        {
                            "subject_id": "ab",
                            "result": {
                                "matched": True,
                                "span_utf8": [0, 2],
                                "captures": [
                                    {
                                        "slot": 1,
                                        "span_utf8": [0, 1] if captured else None,
                                    }
                                ],
                            },
                        }
                    ],
                }
            )
        self.assertEqual(1, len(audit.findings_for(rows)))

    def test_structured_failed_result_is_not_a_diagnostic_delivery_finding(self):
        rows = [
            {
                "case_id": "governed-refusal",
                "profile": {"profile_id": "profile:pcre2/10.42"},
                "compile": {
                    "stdout": {
                        "outcome": "failed",
                        "diagnostics": [
                            {
                                "code": "STRL-PCRE2_LOWERING-0014",
                                "severity": "error",
                            }
                        ],
                    }
                },
                "disposition": "EXPLICIT_PROFILE_REFUSAL",
                "target_compile": "not_emitted",
                "observations": [],
            }
        ]
        self.assertEqual([], audit.findings_for(rows))

    def test_semantic_tags_must_have_real_constructs(self):
        corpus = audit.validate_corpus()
        for case in corpus["cases"]:
            if case["id"] in {
                "wildcard-excluding-lines",
                "unicode-word-class",
                "unset-backreference",
                "repetition-capture-reset",
            }:
                with self.assertRaises(ValueError):
                    audit.validate_semantic_probe(
                        case, {"root": {"kind": "literal", "text": "a"}}
                    )


class AdversarialEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = audit.validate_corpus()
        cls.evidence = audit.load_evidence()

    def test_sharded_round_trip_and_size(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            audit.write_evidence(self.evidence, path)
            self.assertEqual(self.evidence, audit.load_evidence(path))
            for output in path.parent.rglob("*.json"):
                self.assertLessEqual(output.stat().st_size, 1048576)

    def test_observation_paths_are_portable_to_case_insensitive_hosts(self):
        paths = [
            audit.observation_path(case["id"]).casefold()
            for case in self.corpus["cases"]
        ]
        self.assertEqual(len(paths), len(set(paths)))

    def test_shard_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            audit.write_evidence(self.evidence, path)
            shard = next((path.parent / "observations").glob("*.json"))
            shard.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                audit.load_evidence(path)

    def test_unreferenced_shard_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            audit.write_evidence(self.evidence, path)
            (path.parent / "observations/orphan.json").write_text(
                "{}", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "unreferenced"):
                audit.load_evidence(path)

    def test_preserved_evidence_integrity(self):
        audit.validate_evidence(self.evidence, self.corpus)

    def test_empirical_counts_cover_the_complete_matrix(self):
        self.assertEqual(
            {
                "semantic_cases": 41,
                "subjects": 95,
                "target_profile_compiles": 205,
                "runtime_executions": 1531,
                "governed_refusals": 48,
                "cross_profile_comparisons": 1129,
            },
            audit.empirical_counts(self.evidence, self.corpus),
        )

    def test_certification_result_is_deterministic_and_runtime_bound(self):
        first = audit.certification_result(self.evidence, self.corpus, None)
        second = audit.certification_result(self.evidence, self.corpus, None)
        self.assertEqual(first, second)
        self.assertEqual("passed", first["status"])
        check = first["checks"][0]
        self.assertEqual(
            5, len({row["profile"]["profile_id"] for row in self.evidence["rows"]})
        )
        self.assertEqual(4, len(check["evidence"]["runtime_identities"]))
        self.assertEqual([], check["evidence"]["findings"])
        self.assertEqual(0, check["evidence"]["unaccounted_observations"])

    def test_missing_runtime_result_is_structured_and_fail_closed(self):
        result = audit.incomplete_result("governed runtime is missing")
        self.assertEqual("incomplete", result["status"])
        self.assertEqual(1, result["summary"]["incomplete"])
        self.assertEqual(
            "ADVERSARIAL_RUNTIME_ENVIRONMENT_INCOMPLETE",
            result["checks"][0]["findings"][0]["code"],
        )
        self.assertEqual(3, audit.EXIT_CODES[result["status"]])

    def test_artifact_tampering_rejected_even_with_new_envelope_hash(self):
        evidence = copy.deepcopy(self.evidence)
        row = next(r for r in evidence["rows"] if r.get("artifact_sha256"))
        row["artifact_sha256"] = "0" * 64
        evidence["result_sha256"] = audit.DIGEST(
            {k: v for k, v in evidence.items() if k != "result_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "artifact"):
            audit.validate_evidence(evidence, self.corpus)

    def test_missing_profile_rejected_even_with_new_envelope_hash(self):
        evidence = copy.deepcopy(self.evidence)
        evidence["rows"][-1] = evidence["rows"][0]
        evidence["result_sha256"] = audit.DIGEST(
            {k: v for k, v in evidence.items() if k != "result_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "denominator"):
            audit.validate_evidence(evidence, self.corpus)

    def test_registered_zero_finding_check_is_in_mandatory_profiles(self):
        toolchain = audit.load_json(audit.ROOT / "toolchain.json")
        generated = audit.load_json(audit.ROOT / "governance/generated-artifacts.json")
        family = next(
            item
            for item in generated["artifacts"]
            if item["id"] == "adversarial-semantic-observations"
        )
        self.assertEqual("enforced", family["enforcement"])
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.adversarial_semantic_audit",
                "--check",
            ],
            family["verification"]["command"],
        )
        for profile in ("local", "pull-request"):
            operations = {
                step["operation"]
                for step in toolchain["policy"]["profiles"][profile]["operations"]
            }
            self.assertIn("generate_check", operations)
        pull_request_operations = {
            step["operation"]
            for step in toolchain["policy"]["profiles"]["pull-request"]["operations"]
        }
        local_operations = {
            step["operation"]
            for step in toolchain["policy"]["profiles"]["local"]["operations"]
        }
        self.assertIn("adversarial_real_engine_equivalence", pull_request_operations)
        self.assertNotIn("adversarial_real_engine_equivalence", local_operations)
        for profile in ("full", "release"):
            operations = {
                step["operation"]
                for step in toolchain["policy"]["profiles"][profile]["operations"]
            }
            self.assertIn("adversarial_real_engine_equivalence", operations)
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.adversarial_semantic_audit",
                "--strict",
                "--json",
                "--output",
                "artifacts/adversarial-semantic-runtime/evidence.json",
            ],
            toolchain["policy"]["operation_registry"][
                "adversarial_real_engine_equivalence"
            ]["command"],
        )

    def test_evidence_source_identity_mutation_is_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        path = next(iter(evidence["source_files"]))
        evidence["source_files"][path] = "0" * 64
        evidence["result_sha256"] = audit.DIGEST(
            {k: v for k, v in evidence.items() if k != "result_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "source identity"):
            audit.validate_evidence(evidence, self.corpus)

    def test_zero_finding_ratchet_rejects_any_finding(self):
        evidence = {"findings": [{"id": "diagnostic/regression/profile:test"}]}
        with self.assertRaisesRegex(ValueError, "hardgate has findings"):
            audit.enforce_zero_findings(evidence)


if __name__ == "__main__":
    unittest.main()
