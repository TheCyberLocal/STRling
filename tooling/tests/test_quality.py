from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLING_DIR))

from quality import (  # noqa: E402
    ConfigurationError,
    Execution,
    QualityRunner,
    Toolchain,
    _overall_exit,
    _parse_cli,
)


OPERATIONS = (
    "format",
    "format_check",
    "lint",
    "typecheck",
    "build",
    "test",
)


def target_config(
    statuses: dict[str, str] | None = None,
    commands: dict[str, list[str]] | None = None,
    aliases: dict[str, str] | None = None,
) -> dict[str, object]:
    capabilities = {operation: "not_yet_configured" for operation in OPERATIONS}
    capabilities.update(statuses or {})
    result: dict[str, object] = {
        "path": ".",
        "language": "Fixture",
        "runtime": "python3",
        "required_bins": ["python3"],
        "dependency_resolution": {
            "model": "deferred",
            "reason": "test fixture",
        },
        "files": {"manifests": [], "locks": [], "configs": []},
        "capabilities": capabilities,
    }
    result.update(commands or {})
    if aliases:
        result["command_aliases"] = aliases
    return result


def policy(
    alpha: dict[str, object] | None = None,
    beta: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "policy": {
            "aggregates": {
                "check": {
                    "operations": ["lint", "typecheck"],
                    "default_targets": ["alpha"],
                },
                "certify": {
                    "operations": ["build", "test"],
                    "default_targets": ["alpha"],
                },
            }
        },
        "orchestration": {"shell": "bash", "runtime": "python3"},
        "tools": {
            "python3": {
                "resolution": {"model": "constrained", "version": ">=3.8,<4.0"},
                "version_command": ["python3", "--version"],
                "version_pattern": "Python ([0-9.]+)",
            }
        },
        "components": {},
        "bindings": {
            "alpha": alpha or target_config(),
            "beta": beta or target_config(),
        },
    }


class QualityRoutingTests(unittest.TestCase):
    def test_valid_and_all_selection(self) -> None:
        toolchain = Toolchain(policy(), Path.cwd())
        self.assertEqual(["alpha"], [target.name for target in toolchain.select("alpha")])
        self.assertEqual(
            ["alpha", "beta"],
            [target.name for target in toolchain.select("all")],
        )

    def test_invalid_selection_is_an_error(self) -> None:
        toolchain = Toolchain(policy(), Path.cwd())
        with self.assertRaisesRegex(ConfigurationError, "unknown component 'missing'"):
            toolchain.select("missing")

    def test_configured_command_executes_once(self) -> None:
        calls: list[tuple[str, str, list[str]]] = []
        alpha = target_config(
            {"lint": "configured"},
            {"lint": ["fixture-lint", "--check"]},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())

        def execute(target, operation, command):
            calls.append((target.name, operation, command))
            return Execution(0, stdout="tool output\n")

        result = QualityRunner(toolchain, execute).run_operation("lint", "alpha")[0]
        self.assertEqual("passed", result.status)
        self.assertEqual(0, result.exit_code)
        self.assertEqual(
            [("alpha", "lint", ["fixture-lint", "--check"])],
            calls,
        )

    def test_command_alias_uses_authoritative_command(self) -> None:
        alpha = target_config(
            {"build": "configured", "typecheck": "configured"},
            {"build": ["fixture-compiler", "--build"]},
            {"typecheck": "build"},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        calls: list[str] = []

        def execute(_target, operation, _command):
            calls.append(operation)
            return Execution(0)

        result = QualityRunner(toolchain, execute).run_operation(
            "typecheck", "alpha"
        )[0]
        self.assertEqual("passed", result.status)
        self.assertEqual(["fixture-compiler", "--build"], result.command)
        self.assertEqual(["build"], calls)

    def test_not_applicable_is_explicit_and_does_not_execute(self) -> None:
        alpha = target_config({"build": "not_applicable"})
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())

        def unexpected(*_args):
            raise AssertionError("executor should not be called")

        result = QualityRunner(toolchain, unexpected).run_operation(
            "build", "alpha"
        )[0]
        self.assertEqual("not_applicable", result.status)
        self.assertIsNone(result.command)
        self.assertIsNone(result.exit_code)

    def test_not_yet_configured_is_explicit_and_non_failing(self) -> None:
        toolchain = Toolchain(policy(), Path.cwd())
        result = QualityRunner(toolchain).run_operation("format", "alpha")[0]
        self.assertEqual("not_yet_configured", result.status)
        self.assertEqual(0, _overall_exit([result], True))

    def test_command_failure_propagates(self) -> None:
        alpha = target_config(
            {"test": "configured"},
            {"test": ["fixture-test"]},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        result = QualityRunner(
            toolchain,
            lambda *_args: Execution(17, stderr="failed\n"),
        ).run_operation("test", "alpha")[0]
        self.assertEqual("failed", result.status)
        self.assertEqual(17, result.exit_code)
        self.assertEqual(17, _overall_exit([result], True))

    def test_aggregate_uses_declared_order_and_default_target(self) -> None:
        alpha = target_config(
            {"lint": "configured", "typecheck": "not_applicable"},
            {"lint": ["fixture-lint"]},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        results = QualityRunner(
            toolchain,
            lambda *_args: Execution(0),
        ).run_aggregate("check", None)
        self.assertEqual(
            [("alpha", "lint", "passed"), ("alpha", "typecheck", "not_applicable")],
            [
                (result.component, result.operation, result.status)
                for result in results
            ],
        )
        self.assertEqual(0, _overall_exit(results, False))

    def test_malformed_configured_capability_is_rejected(self) -> None:
        alpha = target_config({"lint": "configured"})
        with self.assertRaisesRegex(
            ConfigurationError, "configured without a command"
        ):
            Toolchain(policy(alpha=alpha), Path.cwd())

    def test_format_check_and_json_options_parse_in_any_order(self) -> None:
        self.assertEqual(
            ("format_check", "alpha", True),
            _parse_cli(["format", "alpha", "--check", "--json"]),
        )
        self.assertEqual(
            ("format_check", "alpha", True),
            _parse_cli(["format", "--json", "--check", "alpha"]),
        )


if __name__ == "__main__":
    unittest.main()
