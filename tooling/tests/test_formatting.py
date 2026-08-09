from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLING_DIR))

from formatting import (  # noqa: E402
    FormattingConfigurationError,
    build_command,
    format_target,
    load_policy,
    select_files,
)


class FormattingPolicyTests(unittest.TestCase):
    def test_repository_policy_loads_with_enforcement_targets(self) -> None:
        policy = load_policy()
        enforcement = policy["enforcement"]
        self.assertIn("repository", enforcement["targets"])  # type: ignore[index]

    def test_file_selection_excludes_generated_paths(self) -> None:
        inventory = [
            "docs/guide.md",
            "docs/generated/reference.md",
            "package.json",
        ]
        self.assertEqual(
            ["docs/guide.md", "package.json"],
            select_files(
                inventory,
                ["*.md", "*.json"],
                ["docs/generated/*"],
            ),
        )

    def test_check_commands_are_non_mutating(self) -> None:
        prettier = build_command(
            "prettier",
            True,
            ["package.json"],
            [],
            Path("/repo"),
        )
        ruff = build_command(
            "ruff-format",
            True,
            ["tooling/quality.py"],
            [],
            Path("/repo"),
        )
        dart = build_command(
            "dart-format",
            True,
            ["bindings/dart/lib/strling.dart"],
            [],
            Path("/repo"),
        )
        dotnet = build_command(
            "dotnet-format",
            True,
            [],
            ["bindings/csharp/STRling.sln", "whitespace", "--no-restore"],
            Path("/repo"),
        )
        self.assertIn("--check", prettier)
        self.assertNotIn("--write", prettier)
        self.assertEqual(["ruff", "format", "--check", "tooling/quality.py"], ruff)
        self.assertIn("--output=none", dart)
        self.assertIn("--set-exit-if-changed", dart)
        self.assertIn("--verify-no-changes", dotnet)

    def test_all_steps_run_and_first_failure_propagates(self) -> None:
        policy = {
            "enforcement": {
                "targets": {
                    "fixture": [
                        {
                            "formatter": "prettier",
                            "include": ["*.json"],
                            "exclude": [],
                        },
                        {
                            "formatter": "ruff-format",
                            "include": ["*.py"],
                            "exclude": [],
                        },
                    ]
                }
            }
        }
        calls: list[list[str]] = []
        exit_codes = iter([9, 0])

        def runner(command, _root):
            calls.append(list(command))
            return next(exit_codes)

        result = format_target(
            "fixture",
            True,
            policy,
            ["fixture.json", "fixture.py"],
            runner,
            Path("/repo"),
        )
        self.assertEqual(9, result)
        self.assertEqual(2, len(calls))

    def test_formatter_process_failure_is_authoritative(self) -> None:
        policy = {
            "enforcement": {
                "targets": {
                    "fixture": [
                        {
                            "formatter": "prettier",
                            "include": ["*.json"],
                            "exclude": [],
                        }
                    ]
                }
            }
        }
        result = format_target(
            "fixture",
            True,
            policy,
            ["fixture.json"],
            lambda *_args: 127,
            Path("/repo"),
        )
        self.assertEqual(127, result)

    def test_empty_file_selection_is_configuration_error(self) -> None:
        policy = {
            "enforcement": {
                "targets": {
                    "fixture": [
                        {
                            "formatter": "prettier",
                            "include": ["*.json"],
                            "exclude": [],
                        }
                    ]
                }
            }
        }
        with self.assertRaisesRegex(
            FormattingConfigurationError,
            "selected no tracked files",
        ):
            format_target(
                "fixture",
                True,
                policy,
                ["fixture.py"],
                lambda *_args: 0,
                Path("/repo"),
            )


if __name__ == "__main__":
    unittest.main()
