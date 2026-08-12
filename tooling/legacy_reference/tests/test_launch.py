from __future__ import annotations

import io
import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

launch = importlib.import_module("tooling.legacy_reference.launch")


class MultiRunnerLaunchTests(unittest.TestCase):
    def test_selection_defaults_preserve_typescript_except_aggregate_modes(
        self,
    ) -> None:
        self.assertEqual(launch.selected_runner(launch.parse_args([])), "typescript")
        self.assertEqual(
            launch.selected_runner(launch.parse_args(["--certify"])),
            "typescript",
        )
        self.assertEqual(
            launch.selected_runner(launch.parse_args(["--check"])),
            "all",
        )
        self.assertEqual(
            launch.selected_runner(launch.parse_args(["--cross-certify"])),
            "all",
        )
        self.assertEqual(
            launch.selected_runner(launch.parse_args(["--comparison-certify"])),
            "all",
        )
        self.assertEqual(
            launch.selected_runner(
                launch.parse_args(["--runner", "python", "--certify"])
            ),
            "python",
        )

    @patch("tooling.legacy_reference.launch.run_python")
    @patch("tooling.legacy_reference.launch.build_legacy_typescript")
    def test_python_certification_skips_typescript_build(
        self,
        build_typescript,
        run_python,
    ) -> None:
        run_python.return_value = 0
        self.assertEqual(
            launch.main(["--runner", "python", "--certify"]),
            0,
        )
        build_typescript.assert_not_called()
        run_python.assert_called_once()
        self.assertEqual(run_python.call_args.args[0][-1], "--certify")

    @patch("tooling.legacy_reference.launch.run_node")
    @patch("tooling.legacy_reference.launch.build_legacy_typescript")
    def test_default_certification_preserves_typescript_behavior(
        self,
        build_typescript,
        run_node,
    ) -> None:
        build_typescript.return_value = 0
        run_node.return_value = 0
        self.assertEqual(launch.main(["--certify"]), 0)
        build_typescript.assert_called_once()
        self.assertEqual(run_node.call_args.args[1][-1], "--certify")

    @patch("tooling.legacy_reference.launch.run_cross_certification")
    @patch("tooling.legacy_reference.launch.run_python_check")
    @patch("tooling.legacy_reference.launch.run_typescript_check")
    @patch("tooling.legacy_reference.launch.build_legacy_typescript")
    def test_default_check_runs_both_runners_then_cross_certification(
        self,
        build_typescript,
        run_typescript_check,
        run_python_check,
        run_cross_certification,
    ) -> None:
        build_typescript.return_value = 0
        run_typescript_check.return_value = 0
        run_python_check.return_value = 0
        run_cross_certification.return_value = 0
        self.assertEqual(launch.main(["--check"]), 0)
        build_typescript.assert_called_once()
        run_typescript_check.assert_called_once()
        run_python_check.assert_called_once_with()
        run_cross_certification.assert_called_once()

    @patch("tooling.legacy_reference.launch.run_cross_certification")
    @patch("tooling.legacy_reference.launch.build_legacy_typescript")
    def test_runner_all_certification_emits_cross_certification(
        self,
        build_typescript,
        run_cross_certification,
    ) -> None:
        build_typescript.return_value = 0
        run_cross_certification.return_value = 0
        self.assertEqual(
            launch.main(["--runner", "all", "--certify"]),
            0,
        )
        run_cross_certification.assert_called_once()

    @patch("tooling.legacy_reference.launch.run_comparison_certification")
    @patch("tooling.legacy_reference.launch.build_legacy_typescript")
    def test_comparison_certification_uses_aggregate_runner_mode(
        self,
        build_typescript,
        run_comparison_certification,
    ) -> None:
        build_typescript.return_value = 0
        run_comparison_certification.return_value = 0
        self.assertEqual(launch.main(["--comparison-certify"]), 0)
        run_comparison_certification.assert_called_once()

    @patch("tooling.legacy_reference.launch.build_legacy_typescript")
    def test_runner_all_rejects_single_request_and_corpus_modes(
        self,
        build_typescript,
    ) -> None:
        build_typescript.return_value = 0
        for arguments in (
            ["--runner", "all"],
            ["--runner", "all", "--corpus"],
        ):
            with (
                self.subTest(arguments=arguments),
                patch(
                    "sys.stderr",
                    new_callable=io.StringIO,
                ) as stderr,
            ):
                self.assertEqual(
                    launch.main(arguments),
                    2,
                )
                self.assertIn("INVALID_INVOCATION", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
