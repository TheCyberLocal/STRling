from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLING_DIR))

from quality import (  # noqa: E402
    ConfigurationError,
    EnvironmentInspector,
    Execution,
    QualityRunner,
    Toolchain,
    _overall_exit,
    _parse_cli,
    version_satisfies,
)


OPERATIONS = (
    "format",
    "format_check",
    "lint",
    "hygiene",
    "typecheck",
    "build",
    "test",
)


def target_config(
    statuses: dict[str, str] | None = None,
    commands: dict[str, list[str]] | None = None,
    aliases: dict[str, str] | None = None,
    formatters: list[str] | None = None,
    operation_tools: dict[str, list[str]] | None = None,
    capability_details: dict[str, dict[str, str]] | None = None,
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
    if formatters:
        result["formatters"] = formatters
    if operation_tools:
        result["operation_tools"] = operation_tools
    if capability_details:
        result["capability_details"] = capability_details
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
            "resolution_models": [
                "exact",
                "constrained",
                "repository_managed",
                "deferred",
            ],
            "aggregates": {
                "check": {
                    "operations": ["lint", "typecheck"],
                    "default_targets": ["alpha"],
                },
                "certify": {
                    "operations": ["build", "test"],
                    "default_targets": ["alpha"],
                },
            },
            "operation_defaults": {
                "hygiene": ["alpha"],
            },
        },
        "orchestration": {"shell": "python3", "runtime": "python3"},
        "tools": {
            "python3": {
                "resolution": {"model": "constrained", "version": ">=3.8,<4.0"},
                "version_command": ["python3", "--version"],
                "version_pattern": "Python ([0-9.]+)",
            },
            "fixture-format": {
                "resolution": {"model": "exact", "version": "1.2.3"},
                "version_command": ["fixture-format", "--version"],
                "version_pattern": "fixture-format ([0-9.]+)",
            },
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
        self.assertEqual(
            ["alpha"], [target.name for target in toolchain.select("alpha")]
        )
        self.assertEqual(
            ["alpha", "beta"],
            [target.name for target in toolchain.select("all")],
        )

    def test_invalid_selection_is_an_error(self) -> None:
        toolchain = Toolchain(policy(), Path.cwd())
        with self.assertRaisesRegex(ConfigurationError, "unknown component 'missing'"):
            toolchain.select("missing")

    def test_operation_uses_declared_default_target(self) -> None:
        alpha = target_config(
            {"hygiene": "configured"},
            {"hygiene": ["fixture-hygiene"]},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        calls: list[str] = []
        results = QualityRunner(
            toolchain,
            lambda target, *_args: calls.append(target.name) or Execution(0),
        ).run_operation("hygiene", None)
        self.assertEqual(["alpha"], calls)
        self.assertEqual(["alpha"], [result.component for result in results])

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
        self.assertEqual("configured", result.capability)
        self.assertEqual("configured", result.as_dict()["capability"])

    def test_enforced_lint_command_executes(self) -> None:
        alpha = target_config(
            {"lint": "enforced"},
            {"lint": ["fixture-lint", "--strict"]},
        )
        result = QualityRunner(
            Toolchain(policy(alpha=alpha), Path.cwd()),
            lambda *_args: Execution(0),
        ).run_operation("lint", "alpha")[0]
        self.assertEqual("passed", result.status)
        self.assertEqual("enforced", result.capability)

    def test_lint_violation_preserves_command_and_exit(self) -> None:
        alpha = target_config(
            {"lint": "configured"},
            {"lint": ["fixture-lint", "--check"]},
        )
        result = QualityRunner(
            Toolchain(policy(alpha=alpha), Path.cwd()),
            lambda *_args: Execution(9, stderr="fixture violation\n"),
        ).run_operation("lint", "alpha")[0]
        self.assertEqual("failed", result.status)
        self.assertEqual(["fixture-lint", "--check"], result.command)
        self.assertEqual(9, result.exit_code)
        self.assertIn("status 9", result.reason or "")
        self.assertEqual(9, _overall_exit([result], True))

    def test_typecheck_success_and_failure_propagate(self) -> None:
        alpha = target_config(
            {"typecheck": "configured"},
            {"typecheck": ["fixture-types", "--check"]},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        passed = QualityRunner(
            toolchain,
            lambda *_args: Execution(0),
        ).run_operation("typecheck", "alpha")[0]
        failed = QualityRunner(
            toolchain,
            lambda *_args: Execution(4, stderr="type failure\n"),
        ).run_operation("typecheck", "alpha")[0]
        self.assertEqual("passed", passed.status)
        self.assertEqual("failed", failed.status)
        self.assertEqual(4, failed.exit_code)

    def test_configured_formatter_success_reports_formatter(self) -> None:
        alpha = target_config(
            {"format": "configured"},
            {"format": ["fixture-format", "--write"]},
            formatters=["Fixture Format 1.2.3"],
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        result = QualityRunner(
            toolchain,
            lambda *_args: Execution(0),
        ).run_operation("format", "alpha")[0]
        self.assertEqual("passed", result.status)
        self.assertEqual(["Fixture Format 1.2.3"], result.formatters)
        self.assertEqual(["Fixture Format 1.2.3"], result.as_dict()["formatters"])

    def test_formatter_mismatch_propagates_exact_exit(self) -> None:
        alpha = target_config(
            {"format_check": "configured"},
            {"format_check": ["fixture-format", "--check"]},
            formatters=["Fixture Format 1.2.3"],
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        result = QualityRunner(
            toolchain,
            lambda *_args: Execution(3, stderr="would reformat fixture"),
        ).run_operation("format_check", "alpha")[0]
        self.assertEqual("failed", result.status)
        self.assertEqual(3, result.exit_code)
        self.assertEqual(3, _overall_exit([result], True))

    def test_unavailable_formatter_prevents_execution(self) -> None:
        alpha = target_config(
            {"format_check": "configured"},
            {"format_check": ["fixture-format", "--check"]},
            formatters=["Fixture Format 1.2.3"],
            operation_tools={"format_check": ["fixture-format"]},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        inspector = EnvironmentInspector(
            toolchain,
            probe=lambda command: Execution(
                0,
                stdout=(
                    "Python 3.12.4"
                    if command[0] == "python3"
                    else "fixture-format 1.2.3"
                ),
            ),
            which=lambda command: (
                None if command == "fixture-format" else "/fixture/tool"
            ),
        )

        def unexpected(*_args):
            raise AssertionError("executor should not be called")

        result = QualityRunner(toolchain, unexpected, inspector).run_operation(
            "format_check", "alpha"
        )[0]
        self.assertEqual("unavailable", result.status)
        self.assertIn("fixture-format", result.reason or "")

    def test_unavailable_lint_analyzer_prevents_execution(self) -> None:
        alpha = target_config(
            {"lint": "configured"},
            {"lint": ["fixture-format", "--lint"]},
            operation_tools={"lint": ["fixture-format"]},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        inspector = EnvironmentInspector(
            toolchain,
            probe=lambda _command: Execution(0, stdout="Python 3.12.4"),
            which=lambda command: (
                None if command == "fixture-format" else "/fixture/tool"
            ),
        )

        def unexpected(*_args):
            raise AssertionError("executor should not be called")

        result = QualityRunner(toolchain, unexpected, inspector).run_operation(
            "lint", "alpha"
        )[0]
        self.assertEqual("unavailable", result.status)
        self.assertEqual("configured", result.capability)
        self.assertIn("fixture-format", result.reason or "")

    def test_format_non_applicable_is_explicit(self) -> None:
        alpha = target_config({"format": "not_applicable"})
        result = QualityRunner(
            Toolchain(policy(alpha=alpha), Path.cwd())
        ).run_operation("format", "alpha")[0]
        self.assertEqual("not_applicable", result.status)

    def test_formatter_execution_is_scoped_to_selected_component(self) -> None:
        def configured(name: str) -> dict[str, object]:
            return target_config(
                {"format": "configured"},
                {"format": ["fixture-format", name]},
                formatters=["Fixture Format 1.2.3"],
            )

        toolchain = Toolchain(
            policy(alpha=configured("alpha"), beta=configured("beta")),
            Path.cwd(),
        )
        calls: list[str] = []
        QualityRunner(
            toolchain,
            lambda target, *_args: calls.append(target.name) or Execution(0),
        ).run_operation("format", "beta")
        self.assertEqual(["beta"], calls)

    def test_lint_execution_is_scoped_to_selected_component(self) -> None:
        def configured(name: str) -> dict[str, object]:
            return target_config(
                {"lint": "configured"},
                {"lint": ["fixture-lint", name]},
            )

        toolchain = Toolchain(
            policy(alpha=configured("alpha"), beta=configured("beta")),
            Path.cwd(),
        )
        calls: list[str] = []
        QualityRunner(
            toolchain,
            lambda target, *_args: calls.append(target.name) or Execution(0),
        ).run_operation("lint", "beta")
        self.assertEqual(["beta"], calls)

    def test_aggregate_formatter_failure_propagates(self) -> None:
        alpha = target_config(
            {"format_check": "configured"},
            {"format_check": ["fixture-format", "--check"]},
            formatters=["Fixture Format 1.2.3"],
        )
        data = policy(alpha=alpha)
        aggregates = data["policy"]["aggregates"]  # type: ignore[index]
        aggregates["check"]["operations"] = ["format_check"]  # type: ignore[index]
        toolchain = Toolchain(data, Path.cwd())
        results = QualityRunner(
            toolchain,
            lambda *_args: Execution(23),
        ).run_aggregate("check", None)
        self.assertEqual("failed", results[0].status)
        self.assertEqual(1, _overall_exit(results, False))

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

        result = QualityRunner(toolchain, execute).run_operation("typecheck", "alpha")[
            0
        ]
        self.assertEqual("passed", result.status)
        self.assertEqual(["fixture-compiler", "--build"], result.command)
        self.assertEqual(["build"], calls)

    def test_not_applicable_is_explicit_and_does_not_execute(self) -> None:
        alpha = target_config({"build": "not_applicable"})
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())

        def unexpected(*_args):
            raise AssertionError("executor should not be called")

        result = QualityRunner(toolchain, unexpected).run_operation("build", "alpha")[0]
        self.assertEqual("not_applicable", result.status)
        self.assertIsNone(result.command)
        self.assertIsNone(result.exit_code)

    def test_not_yet_configured_is_explicit_and_non_failing(self) -> None:
        toolchain = Toolchain(policy(), Path.cwd())
        result = QualityRunner(toolchain).run_operation("format", "alpha")[0]
        self.assertEqual("not_yet_configured", result.status)
        self.assertEqual(0, _overall_exit([result], True))

    def test_not_yet_enforceable_is_explicit_and_non_failing(self) -> None:
        alpha = target_config(
            {"lint": "not_yet_enforceable"},
            capability_details={
                "lint": {
                    "reason": "fixture debt",
                    "retirement_condition": "remove fixture debt",
                }
            },
        )
        result = QualityRunner(
            Toolchain(policy(alpha=alpha), Path.cwd())
        ).run_operation("lint", "alpha")[0]
        self.assertEqual("not_yet_enforceable", result.status)
        self.assertEqual("fixture debt", result.reason)
        self.assertEqual(0, _overall_exit([result], True))

    def test_unavailable_capability_is_explicit_and_failing(self) -> None:
        alpha = target_config(
            {"lint": "unavailable"},
            capability_details={"lint": {"reason": "fixture analyzer missing"}},
        )
        result = QualityRunner(
            Toolchain(policy(alpha=alpha), Path.cwd())
        ).run_operation("lint", "alpha")[0]
        self.assertEqual("unavailable", result.status)
        self.assertEqual("fixture analyzer missing", result.reason)
        self.assertEqual(1, _overall_exit([result], True))

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
            [(result.component, result.operation, result.status) for result in results],
        )
        self.assertEqual(0, _overall_exit(results, False))

    def test_aggregate_static_failure_propagates(self) -> None:
        alpha = target_config(
            {"lint": "configured", "typecheck": "configured"},
            {
                "lint": ["fixture-lint"],
                "typecheck": ["fixture-types"],
            },
        )
        results = QualityRunner(
            Toolchain(policy(alpha=alpha), Path.cwd()),
            lambda _target, operation, _command: Execution(
                5 if operation == "typecheck" else 0
            ),
        ).run_aggregate("check", None)
        self.assertEqual(["passed", "failed"], [result.status for result in results])
        self.assertEqual(1, _overall_exit(results, False))

    def test_aggregate_uses_operation_specific_default_targets(self) -> None:
        alpha = target_config(
            {"lint": "configured"},
            {"lint": ["fixture-lint"]},
        )
        beta = target_config(
            {"hygiene": "configured"},
            {"hygiene": ["fixture-hygiene"]},
        )
        data = policy(alpha=alpha, beta=beta)
        check = data["policy"]["aggregates"]["check"]  # type: ignore[index]
        check["operations"] = ["lint", "hygiene"]
        check["operation_targets"] = {  # type: ignore[index]
            "lint": ["alpha"],
            "hygiene": ["beta"],
        }
        calls: list[tuple[str, str]] = []
        results = QualityRunner(
            Toolchain(data, Path.cwd()),
            lambda target, operation, _command: (
                calls.append((target.name, operation)) or Execution(0)
            ),
        ).run_aggregate("check", None)
        self.assertEqual([("alpha", "lint"), ("beta", "hygiene")], calls)
        self.assertEqual(
            [("alpha", "lint"), ("beta", "hygiene")],
            [(result.component, result.operation) for result in results],
        )

    def test_aggregate_rejects_operation_target_outside_membership(self) -> None:
        data = policy()
        check = data["policy"]["aggregates"]["check"]  # type: ignore[index]
        check["operation_targets"] = {"test": ["alpha"]}  # type: ignore[index]
        with self.assertRaisesRegex(
            ConfigurationError, "operation outside the aggregate"
        ):
            Toolchain(data, Path.cwd())

    def test_malformed_configured_capability_is_rejected(self) -> None:
        alpha = target_config({"lint": "configured"})
        with self.assertRaisesRegex(ConfigurationError, "configured without a command"):
            Toolchain(policy(alpha=alpha), Path.cwd())

    def test_transitional_capability_requires_retirement_condition(self) -> None:
        alpha = target_config(
            {"lint": "not_yet_enforceable"},
            capability_details={"lint": {"reason": "fixture debt"}},
        )
        with self.assertRaisesRegex(ConfigurationError, "retirement condition"):
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


class EnvironmentValidationTests(unittest.TestCase):
    def inspector(
        self,
        output: str = "Python 3.12.4",
        available: bool = True,
        data: dict[str, object] | None = None,
    ) -> EnvironmentInspector:
        toolchain = Toolchain(data or policy(), Path.cwd())
        return EnvironmentInspector(
            toolchain,
            probe=lambda _command: Execution(0, stdout=output),
            which=lambda _command: "/fixture/tool" if available else None,
        )

    def test_matching_constrained_version(self) -> None:
        result = self.inspector().check_tool("python3")
        self.assertEqual("compatible", result.status)
        self.assertEqual("3.12.4", result.actual)

    def test_supported_constraint_boundaries(self) -> None:
        self.assertTrue(version_satisfies("3.8.0", ">=3.8,<4.0"))
        self.assertTrue(version_satisfies("3.13.2", ">=3.8,<4.0"))
        self.assertFalse(version_satisfies("4.0.0", ">=3.8,<4.0"))

    def test_mismatched_version_is_incompatible(self) -> None:
        result = self.inspector(output="Python 4.0.0").check_tool("python3")
        self.assertEqual("incompatible", result.status)
        self.assertIn("does not satisfy", result.reason or "")

    def test_unavailable_tool_is_explicit(self) -> None:
        result = self.inspector(available=False).check_tool("python3")
        self.assertEqual("unavailable", result.status)
        self.assertIsNone(result.actual)

    def test_malformed_version_policy_is_rejected(self) -> None:
        data = policy()
        tool = data["tools"]["python3"]  # type: ignore[index]
        tool["resolution"]["version"] = "latest"  # type: ignore[index]
        with self.assertRaisesRegex(ConfigurationError, "invalid version constraint"):
            Toolchain(data, Path.cwd())

    def test_bounded_transitional_version_is_distinct(self) -> None:
        data = policy()
        tool = data["tools"]["python3"]  # type: ignore[index]
        tool["resolution"]["transitional_version"] = ">=3.7,<3.8"  # type: ignore[index]
        tool["resolution"]["reason"] = "fixture transition"  # type: ignore[index]
        result = self.inspector(output="Python 3.7.9", data=data).check_tool("python3")
        self.assertEqual("transitional", result.status)
        self.assertEqual("fixture transition", result.reason)

    def test_incompatible_environment_prevents_execution(self) -> None:
        alpha = target_config(
            {"test": "configured"},
            {"test": ["fixture-test"]},
        )
        toolchain = Toolchain(policy(alpha=alpha), Path.cwd())
        inspector = EnvironmentInspector(
            toolchain,
            probe=lambda _command: Execution(0, stdout="Python 4.0.0"),
            which=lambda _command: "/fixture/tool",
        )

        def unexpected(*_args):
            raise AssertionError("executor should not be called")

        result = QualityRunner(toolchain, unexpected, inspector).run_operation(
            "test", "alpha"
        )[0]
        self.assertEqual("unavailable", result.status)
        self.assertIsNone(result.command)


if __name__ == "__main__":
    unittest.main()
