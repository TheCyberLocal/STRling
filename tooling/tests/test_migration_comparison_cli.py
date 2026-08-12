from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tooling import migration_comparison as projection_contract
from tooling import migration_comparison_certification as certification
from tooling import migration_comparison_cli as cli


class MigrationComparisonCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus = certification.load_corpus()
        self.corpus_fingerprint = projection_contract.canonical_fingerprint(self.corpus)

    def projection(self, runner_id: str) -> dict[str, object]:
        observation = certification._observation(
            runner_id,
            "parser.parse",
            "cli-case",
            self.corpus["outcomes"]["success-base"],
        )
        return cli.execute_request(
            "project",
            {
                "raw_observation": observation,
                "source_context": certification._context(
                    observation, "cli-case", self.corpus_fingerprint
                ),
            },
        )

    def test_explicit_modes_derive_projection_comparison_and_classification(
        self,
    ) -> None:
        left = self.projection("python")
        right = self.projection("typescript")
        comparison = cli.execute_request("compare", {"left": left, "right": right})
        classified = cli.execute_request(
            "classify",
            {
                "comparison": comparison,
                "evidence_scope": "historical_evidence_only",
                "rationale": certification._rationale(comparison),
                "roles": {"left": "historical", "right": "historical"},
            },
        )
        self.assertEqual("equivalent_observation", comparison["relationship"])
        self.assertEqual("not_applicable", classified["applicability"])
        self.assertIsNone(classified["disposition"])

    def test_certify_mode_is_canonical_machine_readable_output(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(0, cli.main(["certify", "--repeat-runs", "3"]))
        result = json.loads(stdout.getvalue())
        self.assertEqual("passed", result["status"])
        self.assertEqual(0, result["determinism"]["mismatches"])

    def test_malformed_request_has_machine_readable_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            request = Path(temporary) / "request.json"
            request.write_text("[]\n", encoding="utf-8")
            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                self.assertEqual(2, cli.main(["project", "--request", str(request)]))
        failure = json.loads(stderr.getvalue())
        self.assertEqual("failed", failure["status"])
        self.assertEqual(
            "INVALID_MIGRATION_COMPARISON_REQUEST", failure["error"]["code"]
        )


if __name__ == "__main__":
    unittest.main()
