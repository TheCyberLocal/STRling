from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch


TOOLING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLING_DIR))

from formatting import (  # noqa: E402
    FormattingConfigurationError,
    MAXIMUM_BATCH_ARGUMENT_CHARACTERS,
    build_command,
    file_batches,
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

    def test_typescript_target_excludes_generator_owned_stdlib_projection(self) -> None:
        policy = load_policy()
        enforcement = cast(dict[str, object], policy["enforcement"])
        targets = cast(dict[str, list[dict[str, object]]], enforcement["targets"])
        step = targets["typescript"][0]
        generated = "bindings/typescript/src/STRling/simply/stdlib.generated.ts"
        authored = "bindings/typescript/src/STRling/compiler.ts"
        selected = select_files(
            [authored, generated],
            cast(list[str], step["include"]),
            cast(list[str], step["exclude"]),
        )
        self.assertEqual([authored], selected)

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
        self.assertEqual(["ruff", "format", "--check", "tooling/quality.py"], ruff[-4:])
        self.assertIn("--output=none", dart)
        self.assertIn("--set-exit-if-changed", dart)
        self.assertIn("--verify-no-changes", dotnet)

    def test_prettier_uses_utf8_safe_windows_node_entrypoint(self) -> None:
        root = Path("C:/repo")
        entrypoint = root / "node_modules" / "prettier" / "bin" / "prettier.cjs"
        with patch("formatting.os.name", "nt"):
            command = build_command("prettier", True, ["package.json"], [], root)
        self.assertEqual(["node", str(entrypoint)], command[:2])

    def test_ruff_uses_the_active_python_on_windows(self) -> None:
        with patch("formatting.os.name", "nt"):
            command = build_command(
                "ruff-format", True, ["tooling/quality.py"], [], Path("C:/repo")
            )
        self.assertEqual([sys.executable, "-m", "ruff"], command[:3])

    def test_long_formatter_file_lists_are_split_deterministically(self) -> None:
        files = [
            f"tooling/generated_{index:04d}_{'x' * 120}.py" for index in range(200)
        ]
        batches = file_batches(files)
        self.assertGreater(len(batches), 1)
        self.assertEqual(files, [path for batch in batches for path in batch])
        self.assertTrue(
            all(
                sum(len(path) + 1 for path in batch)
                <= MAXIMUM_BATCH_ARGUMENT_CHARACTERS
                for batch in batches
            )
        )

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
