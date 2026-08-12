from __future__ import annotations

import copy
import unittest

from tooling.pcre2_runtime_certification import (
    aggregate_status,
    generated_cases,
    result_digest,
    run_certification,
)


class Pcre2RuntimeCertificationTests(unittest.TestCase):
    def test_generated_cases_are_deterministic_bounded_and_balanced(self) -> None:
        configuration = {
            "seed": 1234,
            "count": 32,
            "maximum_pattern_bytes": 160,
            "maximum_subject_bytes": 160,
        }
        first = generated_cases(configuration)
        second = generated_cases(configuration)
        self.assertEqual(first, second)
        self.assertEqual(32, len(first))
        self.assertEqual(32, len({case["id"] for case in first}))
        self.assertTrue(all(len(case["observations"]) == 2 for case in first))
        self.assertTrue(
            all(
                ["match", "no_match"]
                == [item["outcome"] for item in case["observations"]]
                for case in first
            )
        )

    def test_generated_case_limits_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "pattern exceeds"):
            generated_cases(
                {
                    "seed": 1,
                    "count": 1,
                    "maximum_pattern_bytes": 1,
                    "maximum_subject_bytes": 160,
                }
            )

    def test_missing_exact_libraries_are_structured_unavailable(self) -> None:
        result = run_certification({"10.42": None, "10.43": None}, 2)
        self.assertEqual("certification.pcre2-runtime", result["operation_id"])
        self.assertEqual("unavailable", result["status"])
        self.assertEqual(2, result["summary"]["unavailable"])
        self.assertEqual(result["deterministic_result_sha256"], result_digest(result))
        self.assertTrue(
            all(check["status"] == "unavailable" for check in result["checks"])
        )

    def test_result_digest_excludes_only_raw_timing_observations(self) -> None:
        result = {
            "operation_id": "certification.pcre2-runtime",
            "status": "passed",
            "summary": {"passed": 1},
            "checks": [
                {
                    "check_id": "certification.pcre2-runtime.10.42",
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

    def test_aggregate_status_preserves_blocking_precedence(self) -> None:
        self.assertEqual(
            "failed",
            aggregate_status(
                [{"status": "passed"}, {"status": "unavailable"}, {"status": "failed"}]
            ),
        )
        self.assertEqual(
            "unavailable",
            aggregate_status([{"status": "passed"}, {"status": "unavailable"}]),
        )


if __name__ == "__main__":
    unittest.main()
