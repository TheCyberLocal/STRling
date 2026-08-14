from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr
from datetime import date
from io import StringIO
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch


TOOLING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLING_DIR))

static_analysis = __import__("static_analysis")
Suppression = static_analysis.Suppression
detect_line = static_analysis.detect_line
run_suppression_audit = static_analysis.run_suppression_audit
run_ruff = static_analysis.run_ruff
validate_suppressions = static_analysis.validate_suppressions
run_command = static_analysis._run


def policy(
    *,
    count: int = 1,
    expires_on: str = "2099-01-01",
) -> dict[str, object]:
    return {
        "classifications": [
            "permanent_interoperability",
            "bounded_transition",
            "obsolete_removable",
            "suspected_product_defect",
        ],
        "baseline_total": count,
        "waivers": [
            {
                "id": "WVR-TEST-001",
                "classification": "bounded_transition",
                "expires_on": expires_on,
                "reason": "fixture reason",
                "retirement_condition": "remove fixture",
                "path_counts": {"fixture.py": count},
            }
        ],
    }


class SuppressionGovernanceTests(unittest.TestCase):
    def test_recognizes_governed_waiver(self) -> None:
        findings = [Suppression("fixture.py", 1, "python", "# noqa")]
        self.assertEqual(
            [],
            validate_suppressions(policy(), findings, date(2026, 8, 9)),
        )

    def test_unmanaged_suppression_fails(self) -> None:
        findings = [
            Suppression("fixture.py", 1, "python", "# noqa"),
            Suppression("new.py", 2, "python", "# type: ignore"),
        ]
        errors = validate_suppressions(policy(), findings, date(2026, 8, 9))
        self.assertTrue(
            any("unmanaged suppression: new.py:2" in item for item in errors)
        )

    def test_expired_waiver_fails(self) -> None:
        findings = [Suppression("fixture.py", 1, "python", "# noqa")]
        errors = validate_suppressions(
            policy(expires_on="2026-08-08"),
            findings,
            date(2026, 8, 9),
        )
        self.assertTrue(any("expired on 2026-08-08" in item for item in errors))

    def test_invalid_waiver_fails(self) -> None:
        findings = [Suppression("fixture.py", 1, "python", "# noqa")]
        errors = validate_suppressions(
            policy(expires_on="not-a-date"),
            findings,
            date(2026, 8, 9),
        )
        self.assertTrue(any("invalid or missing expires_on" in item for item in errors))

    def test_detects_file_wide_and_line_suppressions(self) -> None:
        typescript = detect_line(Path("fixture.ts"), 1, "// @ts-nocheck")
        python = detect_line(Path("fixture.py"), 2, "# mypy: ignore-errors")
        self.assertEqual("typescript", typescript[0].kind)
        self.assertEqual("python", python[0].kind)

    def test_detects_ts_jest_diagnostic_suppression(self) -> None:
        typescript = detect_line(
            Path("jest.config.mjs"),
            1,
            "diagnostics: { ignoreCodes: [151002] },",
        )
        self.assertEqual("typescript", typescript[0].kind)
        self.assertEqual("ignoreCodes:", typescript[0].directive)

    def test_repository_suppression_baseline_is_governed(self) -> None:
        self.assertEqual(0, run_suppression_audit(today=date(2026, 8, 9)))

    def test_native_warning_text_causes_failure(self) -> None:
        completed = CompletedProcess(
            ["fixture"],
            0,
            stdout="Syntax OK\n",
            stderr="fixture.rb:1: warning: unused variable\n",
        )
        with (
            patch.object(static_analysis.subprocess, "run", return_value=completed),
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(
                1,
                run_command(["fixture"], Path.cwd(), warnings_are_errors=True),
            )

    def test_ruff_uses_the_active_python_on_windows(self) -> None:
        completed = CompletedProcess(["fixture"], 0, stdout="", stderr="")
        with (
            patch.object(static_analysis.sys, "platform", "win32"),
            patch.object(
                static_analysis.subprocess, "run", return_value=completed
            ) as run,
        ):
            self.assertEqual(0, run_ruff("repository"))
        self.assertEqual(
            [sys.executable, "-m", "ruff", "check"],
            run.call_args.args[0][:4],
        )


if __name__ == "__main__":
    unittest.main()
