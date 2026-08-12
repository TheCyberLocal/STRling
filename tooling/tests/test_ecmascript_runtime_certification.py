from __future__ import annotations

import copy
import unittest

from tooling.ecmascript_runtime_certification import (
    CORPUS,
    EXPECTED_ARCHITECTURE,
    EXPECTED_EXECUTABLE_SHA256,
    EXPECTED_NODE,
    EXPECTED_PLATFORM,
    EXPECTED_V8,
    build_request,
    generated_cases,
    load_json,
    result_digest,
    run_certification,
    validate_corpus_identity,
)


def exact_runtime() -> dict[str, str]:
    return {
        "node": EXPECTED_NODE,
        "v8": EXPECTED_V8,
        "platform": EXPECTED_PLATFORM,
        "architecture": EXPECTED_ARCHITECTURE,
    }


def rewrite_observations(subjects: list[str]) -> list[dict[str, object]]:
    return [
        {
            "subject": subject,
            "matches": (
                [
                    {
                        "span": [0, 1],
                        "value": "a",
                        "captures": [{"index": 0, "span": [0, 1], "value": "a"}],
                    }
                ]
                if subject == "a"
                else []
            ),
        }
        for subject in subjects
    ]


def passing_response(request: dict[str, object]) -> dict[str, object]:
    corpus = load_json(CORPUS)
    generated = generated_cases(corpus["generated_cases"])
    observations = {
        case["id"]: case["expected"] for case in [*corpus["cases"], *generated]
    }
    for rewrite in corpus["rewrite_cases"]:
        expected = rewrite_observations(rewrite["subjects"])
        observations[f"rewrite:{rewrite['id']}:original"] = expected
        observations[f"rewrite:{rewrite['id']}:rewritten"] = expected
    compile_errors = {case["id"] for case in corpus["compile_error_cases"]}
    cases = []
    for case in request["cases"]:  # type: ignore[index]
        case_id = case["id"]
        if case_id in compile_errors:
            cases.append({"id": case_id, "compile": "syntax_error", "observations": []})
        else:
            cases.append(
                {
                    "id": case_id,
                    "compile": "ok",
                    "observations": observations[case_id],
                }
            )
    return {
        "protocol_version": "1.0.0",
        "runtime": exact_runtime(),
        "cases": cases,
    }


class EcmascriptRuntimeCertificationTests(unittest.TestCase):
    def test_corpus_and_generated_cases_are_exact_bounded_and_deterministic(
        self,
    ) -> None:
        corpus = load_json(CORPUS)
        validate_corpus_identity(corpus)
        first = generated_cases(corpus["generated_cases"])
        second = generated_cases(corpus["generated_cases"])
        self.assertEqual(first, second)
        self.assertEqual(128, len(first))
        self.assertEqual(128, len({case["id"] for case in first}))
        request, rewrite_ids = build_request(corpus, first)
        self.assertEqual(
            len(request["cases"]), len({case["id"] for case in request["cases"]})
        )
        self.assertEqual(2, len(rewrite_ids))
        self.assertTrue(any(case["flags"] == ["v"] for case in corpus["cases"]))
        self.assertIn(
            "newer-runtime-scoped-modifier-extension",
            {case["id"] for case in corpus["compile_error_cases"]},
        )

    def test_generated_case_limits_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "source exceeds"):
            generated_cases(
                {
                    "seed": 1,
                    "count": 1,
                    "maximum_source_bytes": 1,
                    "maximum_subject_utf16_units": 160,
                }
            )

    def test_missing_or_wrong_binary_is_structured_unavailable(self) -> None:
        missing = run_certification(None, 2)
        self.assertEqual("unavailable", missing["status"])
        self.assertEqual(1, missing["summary"]["unavailable"])
        wrong = run_certification(
            CORPUS,
            2,
            identity_reader=lambda _path: "0" * 64,
        )
        self.assertEqual("unavailable", wrong["status"])
        self.assertIn("SHA-256", wrong["checks"][0]["unavailable_reason"])

    def test_wrong_reported_runtime_is_structured_unavailable(self) -> None:
        def wrong_runtime(_binary, request):
            result = passing_response(request)
            result["runtime"] = {**exact_runtime(), "node": "v22.23.1"}
            return result

        result = run_certification(
            CORPUS,
            2,
            runner=wrong_runtime,
            identity_reader=lambda _path: EXPECTED_EXECUTABLE_SHA256,
        )
        self.assertEqual("unavailable", result["status"])
        self.assertIn("identity", result["checks"][0]["unavailable_reason"])

    def test_local_io_details_do_not_enter_unavailable_evidence(self) -> None:
        def unreadable(_path):
            raise OSError("host-specific path and errno")

        unreadable_result = run_certification(
            CORPUS,
            2,
            identity_reader=unreadable,
        )
        self.assertEqual("unavailable", unreadable_result["status"])
        self.assertEqual(
            "exact Node executable identity is unreadable",
            unreadable_result["checks"][0]["unavailable_reason"],
        )

        def cannot_start(_binary, _request):
            raise OSError("different host-specific path and errno")

        start_result = run_certification(
            CORPUS,
            2,
            runner=cannot_start,
            identity_reader=lambda _path: EXPECTED_EXECUTABLE_SHA256,
        )
        self.assertEqual("unavailable", start_result["status"])
        self.assertEqual(
            "exact Node executable could not be started",
            start_result["checks"][0]["unavailable_reason"],
        )

    def test_exact_repeated_evidence_passes_with_stable_digest(self) -> None:
        result = run_certification(
            CORPUS,
            2,
            runner=lambda _binary, request: passing_response(request),
            identity_reader=lambda _path: EXPECTED_EXECUTABLE_SHA256,
            clock=iter([1.0, 1.1, 2.0, 2.2]).__next__,
        )
        self.assertEqual("passed", result["status"])
        evidence = result["checks"][0]["evidence"]
        self.assertEqual(128, evidence["generated_cases"])
        self.assertEqual(2, evidence["repeat_runs"])
        self.assertEqual(EXPECTED_EXECUTABLE_SHA256, evidence["executable_sha256"])
        self.assertEqual(result["deterministic_result_sha256"], result_digest(result))

    def test_semantic_difference_fails_closed(self) -> None:
        def changed(_binary, request):
            result = passing_response(request)
            result["cases"][0]["observations"] = []
            return result

        result = run_certification(
            CORPUS,
            2,
            runner=changed,
            identity_reader=lambda _path: EXPECTED_EXECUTABLE_SHA256,
        )
        self.assertEqual("failed", result["status"])
        self.assertEqual(
            "ECMASCRIPT_RUNTIME_CERTIFICATION_FAILED",
            result["checks"][0]["findings"][0]["code"],
        )

    def test_result_digest_excludes_only_raw_timing_observations(self) -> None:
        result = {
            "operation_id": "certification.ecmascript-runtime",
            "status": "passed",
            "checks": [
                {
                    "status": "passed",
                    "evidence": {
                        "semantic_result_sha256": "a" * 64,
                        "timing_observations_microseconds": [10, 11],
                    },
                }
            ],
        }
        changed_timing = copy.deepcopy(result)
        changed_timing["checks"][0]["evidence"]["timing_observations_microseconds"] = [
            100,
            200,
        ]
        self.assertEqual(result_digest(result), result_digest(changed_timing))
        changed_semantics = copy.deepcopy(result)
        changed_semantics["checks"][0]["evidence"]["semantic_result_sha256"] = "b" * 64
        self.assertNotEqual(result_digest(result), result_digest(changed_semantics))


if __name__ == "__main__":
    unittest.main()
