from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tooling.generated_artifacts import (
    CommandResult,
    RegistryError,
    host_command,
    load_json,
    run_registry,
    validate_registry,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = load_json(ROOT / "governance/schemas/generated-artifact-registry.schema.json")


def fixture_registry() -> dict[str, object]:
    return {
        "registry_version": 1,
        "artifacts": [
            {
                "id": "fixture-output",
                "category": "generated-documentation",
                "description": "Test artifact",
                "authoritative_sources": ["source.txt"],
                "generator_inputs": ["source.txt"],
                "generator": {
                    "implementation_paths": ["generator.py"],
                    "command": ["fixture-generator", "--write"],
                    "working_directory": ".",
                },
                "outputs": ["output.txt"],
                "determinism": "verified",
                "checked_in": True,
                "authority": "non-normative-projection",
                "verification": {
                    "method": "command-check",
                    "command": ["fixture-generator", "--check"],
                },
                "enforcement": "enforced",
            }
        ],
    }


class GeneratedArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "source.txt").write_text("source", encoding="utf-8")
        (self.root / "generator.py").write_text("# generator\n", encoding="utf-8")
        (self.root / "output.txt").write_text("output", encoding="utf-8")
        self.registry = validate_registry(fixture_registry(), SCHEMA)

    def snapshot(self, _root: Path) -> dict[str, str]:
        return {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted(self.root.iterdir())
            if path.is_file()
        }

    def test_positive_check_reports_artifact_and_command(self) -> None:
        results = run_registry(
            self.registry,
            self.root,
            check=True,
            executor=lambda *_args: CommandResult(0),
            snapshotter=self.snapshot,
        )
        self.assertEqual(["passed"], [result.status for result in results])
        self.assertEqual("fixture-output", results[0].artifact)
        self.assertEqual(["fixture-generator", "--check"], results[0].command)

    def test_stale_generated_content_fails(self) -> None:
        results = run_registry(
            self.registry,
            self.root,
            check=True,
            executor=lambda *_args: CommandResult(1, stderr="stale output"),
            snapshotter=self.snapshot,
        )
        self.assertEqual("failed", results[0].status)
        self.assertEqual(1, results[0].exit_code)

    def test_generator_process_failure_propagates(self) -> None:
        results = run_registry(
            self.registry,
            self.root,
            check=False,
            executor=lambda *_args: CommandResult(9, stderr="generator failed"),
        )
        self.assertEqual("failed", results[0].status)
        self.assertEqual(9, results[0].exit_code)

    def test_missing_authoritative_source_fails_before_execution(self) -> None:
        (self.root / "source.txt").unlink()
        calls = []
        results = run_registry(
            self.registry,
            self.root,
            check=False,
            executor=lambda *_args: calls.append(True) or CommandResult(0),
        )
        self.assertEqual([], calls)
        self.assertIn("missing authoritative source", results[0].reason or "")

    def test_missing_expected_output_fails_before_execution(self) -> None:
        (self.root / "output.txt").unlink()
        results = run_registry(
            self.registry,
            self.root,
            check=True,
            executor=lambda *_args: CommandResult(0),
            snapshotter=self.snapshot,
        )
        self.assertIn("missing expected output", results[0].reason or "")

    def test_malformed_registry_entry_is_rejected(self) -> None:
        invalid = copy.deepcopy(fixture_registry())
        del invalid["artifacts"][0]["outputs"]
        with self.assertRaises(RegistryError):
            validate_registry(invalid, SCHEMA)

    def test_check_mode_rejects_repository_modification(self) -> None:
        def mutate(_command, _cwd):
            (self.root / "output.txt").write_text("changed", encoding="utf-8")
            return CommandResult(0)

        results = run_registry(
            self.registry,
            self.root,
            check=True,
            executor=mutate,
            snapshotter=self.snapshot,
        )
        self.assertEqual("repository-state", results[-1].artifact)
        self.assertEqual("failed", results[-1].status)
        self.assertIn("output.txt", results[-1].reason or "")

    def test_generated_output_cannot_be_its_own_input(self) -> None:
        invalid = copy.deepcopy(self.registry)
        invalid["artifacts"][0]["generator_inputs"] = ["output.txt"]
        with self.assertRaisesRegex(RegistryError, "own input"):
            run_registry(
                invalid,
                self.root,
                check=False,
                executor=lambda *_args: CommandResult(0),
            )

    def test_result_is_json_serializable(self) -> None:
        result = run_registry(
            self.registry,
            self.root,
            check=False,
            executor=lambda *_args: CommandResult(0),
        )[0]
        json.dumps(result.as_dict())

    def test_windows_host_commands_use_native_python_entrypoints(self) -> None:
        with mock.patch("tooling.generated_artifacts.os.name", "nt"):
            self.assertEqual(
                [sys.executable, "tooling/check.py", "--check"],
                host_command(["python3", "tooling/check.py", "--check"], self.root),
            )
            self.assertEqual(
                [
                    sys.executable,
                    str(self.root / "tooling/public_contracts.py"),
                    "--check",
                ],
                host_command(["./strling", "contracts", "--check"], self.root),
            )


if __name__ == "__main__":
    unittest.main()
