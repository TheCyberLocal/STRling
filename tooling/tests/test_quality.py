from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch


TOOLING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLING_DIR))

from quality import (  # noqa: E402
    ConfigurationError,
    EnvironmentInspector,
    Execution,
    OperationResult,
    QualityRunner,
    Target,
    Toolchain,
    _overall_exit,
    _profile_exit,
    _profile_status,
    _parse_cli,
    host_command,
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
    operation_registry = {
        operation: {
            "kind": "component",
            "capability": operation,
            "network": "offline",
        }
        for operation in OPERATIONS
    }
    pull_request = [
        {"operation": "lint", "targets": ["alpha"]},
        {"operation": "typecheck", "targets": ["alpha"]},
    ]
    full = [
        *pull_request,
        {"operation": "build", "targets": ["alpha"]},
        {"operation": "test", "targets": ["alpha"]},
    ]

    def copy_members(
        members: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        copied = [dict(member) for member in members]
        for member in copied:
            targets = member.get("targets")
            if isinstance(targets, list):
                member["targets"] = list(targets)
        return copied

    return {
        "schema_version": 1,
        "policy": {
            "resolution_models": [
                "exact",
                "constrained",
                "repository_managed",
                "deferred",
            ],
            "operation_registry": operation_registry,
            "profiles": {
                "local": {
                    "definition_version": "1.0.0",
                    "purpose": "fixture local",
                    "network_policy": "offline",
                    "operations": copy_members(pull_request),
                },
                "pull-request": {
                    "definition_version": "1.0.0",
                    "purpose": "fixture pull request",
                    "network_policy": "offline",
                    "operations": copy_members(pull_request),
                },
                "full": {
                    "definition_version": "1.0.0",
                    "purpose": "fixture full",
                    "network_policy": "allowed",
                    "operations": copy_members(full),
                },
                "release": {
                    "definition_version": "1.0.0",
                    "purpose": "fixture release",
                    "network_policy": "allowed",
                    "operations": copy_members(full),
                },
            },
            "aggregate_profiles": {
                "check": "pull-request",
                "certify": "full",
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
    def test_repository_python_hardgates_use_the_active_windows_runtime(self) -> None:
        with patch("quality.sys.platform", "win32"):
            command = host_command(["python3", "tooling/governance.py"])
        self.assertEqual(
            [sys.executable, "tooling/governance.py"],
            command,
        )

    @patch("quality.shutil.which")
    @patch("quality.subprocess.run")
    def test_windows_binding_execution_uses_the_declared_command(
        self, run, which
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        executable = Path.cwd() / "fixture-tools" / "fixture-lint.cmd"
        which.return_value = str(executable)
        toolchain = Toolchain(policy(), Path.cwd())
        target = toolchain.select("alpha")[0]

        with (
            patch("quality.sys.platform", "win32"),
            patch("quality.Path.is_file", return_value=True),
        ):
            result = QualityRunner(toolchain)._execute(
                target,
                "lint",
                ["fixture-lint"],
            )

        self.assertEqual(result.returncode, 0)
        invocation = run.call_args.args[0]
        self.assertEqual(
            invocation,
            [str(executable.resolve())],
        )
        self.assertEqual(run.call_args.kwargs["cwd"], Path.cwd())
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")

    @patch("quality.subprocess.run")
    def test_windows_binding_execution_prefers_local_cmd_shim(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        toolchain = Toolchain(policy(), Path.cwd())
        target = toolchain.select("alpha")[0]
        executable = Path.cwd() / "node_modules" / ".bin" / "tsc.cmd"

        with (
            patch("quality.sys.platform", "win32"),
            patch("quality.Path.is_file", return_value=True),
        ):
            result = QualityRunner(toolchain)._execute(
                target,
                "typecheck",
                ["./node_modules/.bin/tsc", "--noEmit"],
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            run.call_args.args[0],
            [str(executable), "--noEmit"],
        )

    @patch("quality.subprocess.run")
    def test_windows_component_execution_prefers_local_cmd_shim(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        toolchain = Toolchain(policy(), Path.cwd())
        target = Target("component", "component", target_config())
        executable = Path.cwd() / "node_modules" / ".bin" / "tsc.cmd"

        with (
            patch("quality.sys.platform", "win32"),
            patch("quality.Path.is_file", return_value=True),
        ):
            result = QualityRunner(toolchain)._execute(
                target,
                "typecheck",
                ["./node_modules/.bin/tsc", "--noEmit"],
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            run.call_args.args[0],
            [str(executable), "--noEmit"],
        )

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

    def test_enforced_capability_must_be_in_check(self) -> None:
        beta = target_config(
            {"lint": "enforced"},
            {"lint": ["fixture-lint"]},
        )
        with self.assertRaisesRegex(
            ConfigurationError, "beta.lint is enforced but omitted from pull-request"
        ):
            Toolchain(policy(beta=beta), Path.cwd())

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
        member = {"operation": "format_check", "targets": ["alpha"]}
        policy_data = cast(dict[str, object], data["policy"])
        profiles = cast(dict[str, object], policy_data["profiles"])
        for raw_profile in profiles.values():
            profile = cast(dict[str, object], raw_profile)
            profile["operations"] = [member]
        toolchain = Toolchain(data, Path.cwd())
        results = QualityRunner(
            toolchain,
            lambda *_args: Execution(23),
        ).run_aggregate("check", None)
        self.assertEqual("failed", results[0].status)
        self.assertEqual(1, _profile_exit(results))

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

    def test_repository_operations_and_profile_membership_are_canonical(self) -> None:
        toolchain = Toolchain.load(TOOLING_DIR.parent / "toolchain.json")
        local_members = toolchain.profile("local")["operations"]
        assert isinstance(local_members, list)
        self.assertEqual(
            [
                "security_dependency_integrity",
                "security_content_workflows",
                "baseline_check",
                "canonical_contracts_check",
                "core_contracts_check",
                "contracts_check",
                "generate_check",
                "documentation_integrity",
                "governance",
                "product_certification_authority",
                "interop_contract_check",
                "legacy_reference_check",
                "migration_comparison_check",
                "migration_differential_gate",
                "migration_explanation_certification",
                "lsp_package_contract_check",
            ],
            [member["operation"] for member in local_members[:16]],
        )
        self.assertEqual(
            [
                "python3",
                "tooling/product_certification.py",
                "--check",
                "--json",
            ],
            toolchain.operation("product_certification_authority")["command"],
        )
        self.assertEqual(
            ["python3", "tooling/security.py", "integrity", "--json"],
            toolchain.operation("security_dependency_integrity")["command"],
        )
        local_test = next(
            member for member in local_members if member["operation"] == "test"
        )
        self.assertEqual(["core", "interop"], local_test["targets"])
        self.assertEqual("1.9.0", toolchain.profile("local")["definition_version"])
        self.assertEqual(
            "1.14.0", toolchain.profile("pull-request")["definition_version"]
        )
        self.assertEqual(
            ["perl"],
            toolchain.data["bindings"]["perl"]["operation_tools"]["lint"],
        )
        self.assertEqual(
            ["make", "perl-ffi-platypus"],
            toolchain.data["bindings"]["perl"]["operation_tools"]["build"],
        )
        self.assertEqual(
            ["prove", "perl-ffi-platypus"],
            toolchain.data["bindings"]["perl"]["operation_tools"]["test"],
        )
        self.assertEqual(
            ["perl", "-MFFI::Platypus", "-e", "print $FFI::Platypus::VERSION"],
            toolchain.tools["perl-ffi-platypus"]["version_command"],
        )
        self.assertEqual(
            ["python-build"],
            toolchain.data["bindings"]["python"]["operation_tools"]["build"],
        )
        self.assertEqual(
            ["python-pytest"],
            toolchain.data["bindings"]["python"]["operation_tools"]["test"],
        )
        self.assertEqual(
            ["python3", "-m", "pytest", "-v", "-W", "error"],
            toolchain.data["bindings"]["python"]["test"],
        )
        for binding in ("csharp", "fsharp"):
            self.assertIn(
                "-p:NuGetAudit=false",
                toolchain.data["bindings"][binding]["lint"],
            )
            self.assertEqual(
                [
                    "dotnet",
                    "test",
                    "--no-restore",
                    "--verbosity",
                    "normal",
                    "-p:NuGetAudit=false",
                ],
                toolchain.data["bindings"][binding]["test"],
            )

        self.assertEqual(
            ["python3", "tooling/core_contract_validation.py"],
            toolchain.operation("core_contracts_check")["command"],
        )
        self.assertEqual(
            ["python3", "tooling/governance.py"],
            toolchain.operation("governance")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "tooling/interop_contract.py",
                "--check-header",
                "--json",
            ],
            toolchain.operation("interop_contract_check")["command"],
        )
        self.assertEqual(
            "certification-result-v1",
            toolchain.operation("interop_certification")["result_contract"],
        )
        self.assertEqual(
            "certification.interop",
            toolchain.operation("interop_certification")["result_operation_id"],
        )
        self.assertEqual(
            "certification-result-v1",
            toolchain.operation("interop_adversarial_certification")["result_contract"],
        )
        self.assertEqual(
            "certification.interop-adversarial",
            toolchain.operation("interop_adversarial_certification")[
                "result_operation_id"
            ],
        )
        self.assertEqual(
            [
                "python3",
                "tooling/legacy_reference/launch.py",
                "--check",
            ],
            toolchain.operation("legacy_reference_check")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "tooling/legacy_reference/launch.py",
                "--comparison-certify",
            ],
            toolchain.operation("migration_comparison_check")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "tooling/migration_differential.py",
                "--repeat-runs",
                "3",
            ],
            toolchain.operation("migration_differential_gate")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.migration_explanation_certification",
                "--json",
                "--check",
            ],
            toolchain.operation("migration_explanation_certification")["command"],
        )
        self.assertEqual(
            "certification-result-v1",
            toolchain.operation("migration_explanation_certification")[
                "result_contract"
            ],
        )
        self.assertEqual(
            "certification.migration-explanation",
            toolchain.operation("migration_explanation_certification")[
                "result_operation_id"
            ],
        )
        self.assertEqual(
            [
                "python3",
                "tooling/lsp-server/package_extension.py",
                "certify",
                "--target",
                "auto",
            ],
            toolchain.operation("lsp_package_certification")["command"],
        )
        for profile_id in ["local", "pull-request", "full", "release"]:
            members = toolchain.profile(profile_id)["operations"]
            self.assertEqual(
                1,
                sum(
                    member["operation"] == "interop_contract_check"
                    for member in members
                ),
            )
            self.assertEqual(
                1,
                sum(
                    member["operation"] == "legacy_reference_check"
                    for member in members
                ),
            )
            self.assertEqual(
                1,
                sum(
                    member["operation"] == "lsp_package_contract_check"
                    for member in members
                ),
            )
            self.assertEqual(
                1,
                sum(
                    member["operation"] == "migration_explanation_certification"
                    for member in members
                ),
            )
            ids = [member["operation"] for member in members]
            certification_chain = ["migration_differential_gate"]
            certification_chain.extend(
                operation
                for operation in (
                    "typescript_python_adapter_runtime_certification",
                    "jvm_adapter_runtime_certification",
                    "dotnet_adapter_runtime_certification",
                    "go_dart_swift_adapter_runtime_certification",
                    "go_dart_swift_adapter_package_certification",
                    "dynamic_language_adapter_runtime_certification",
                    "dynamic_language_adapter_package_check",
                )
                if operation in ids
            )
            certification_chain.append("migration_explanation_certification")
            for predecessor, successor in zip(
                certification_chain, certification_chain[1:]
            ):
                self.assertEqual(ids.index(predecessor) + 1, ids.index(successor))
            self.assertEqual(
                1,
                sum(
                    member["operation"] == "migration_comparison_check"
                    for member in members
                ),
            )
            self.assertEqual(
                1,
                sum(
                    member["operation"] == "migration_differential_gate"
                    for member in members
                ),
            )
        full_members = toolchain.profile("full")["operations"]
        assert isinstance(full_members, list)
        full_ids = [member["operation"] for member in full_members]
        self.assertIn("security_dependency_risk", full_ids)
        self.assertIn("interop_certification", full_ids)
        self.assertIn("interop_adversarial_certification", full_ids)
        self.assertEqual(
            full_ids.index("interop_certification") + 1,
            full_ids.index("interop_adversarial_certification"),
        )
        for profile_id in ("full", "release"):
            profile_ids = [
                member["operation"]
                for member in toolchain.profile(profile_id)["operations"]
            ]
            self.assertEqual(1, profile_ids.count("interop_adversarial_certification"))
            self.assertEqual(
                profile_ids.index("interop_certification") + 1,
                profile_ids.index("interop_adversarial_certification"),
            )
        for profile_id in ("local", "pull-request"):
            profile_ids = [
                member["operation"]
                for member in toolchain.profile(profile_id)["operations"]
            ]
            self.assertNotIn("interop_adversarial_certification", profile_ids)
        self.assertIn("pcre2_runtime_certification", full_ids)
        self.assertIn("ecmascript_runtime_certification", full_ids)
        self.assertIn("python_re_runtime_certification", full_ids)
        self.assertIn("shared_cross_engine_certification", full_ids)
        self.assertIn("stdlib_runtime_certification", full_ids)
        self.assertIn("portability_matrix_certification", full_ids)
        self.assertIn("lsp_package_certification", full_ids)
        self.assertEqual(
            full_ids.index("pcre2_runtime_certification") + 1,
            full_ids.index("ecmascript_runtime_certification"),
        )
        self.assertEqual(
            full_ids.index("ecmascript_runtime_certification") + 1,
            full_ids.index("python_re_runtime_certification"),
        )
        self.assertEqual(
            full_ids.index("python_re_runtime_certification") + 1,
            full_ids.index("shared_cross_engine_certification"),
        )
        self.assertEqual(
            full_ids.index("shared_cross_engine_certification") + 1,
            full_ids.index("stdlib_runtime_certification"),
        )
        self.assertEqual(
            full_ids.index("stdlib_runtime_certification") + 1,
            full_ids.index("portability_matrix_certification"),
        )
        self.assertEqual(
            full_ids.index("portability_matrix_certification") + 1,
            full_ids.index("lsp_package_contract_check"),
        )
        self.assertEqual(
            full_ids.index("lsp_package_contract_check") + 1,
            full_ids.index("lsp_package_certification"),
        )
        self.assertNotIn(
            "pcre2_runtime_certification",
            [member["operation"] for member in local_members],
        )
        self.assertNotIn(
            "interop_certification",
            [member["operation"] for member in local_members],
        )
        self.assertNotIn(
            "ecmascript_runtime_certification",
            [member["operation"] for member in local_members],
        )
        self.assertNotIn(
            "python_re_runtime_certification",
            [member["operation"] for member in local_members],
        )
        self.assertNotIn(
            "portability_matrix_certification",
            [member["operation"] for member in local_members],
        )
        self.assertNotIn(
            "stdlib_runtime_certification",
            [member["operation"] for member in local_members],
        )
        self.assertNotIn(
            "pcre2_runtime_certification",
            [
                member["operation"]
                for member in toolchain.profile("pull-request")["operations"]
            ],
        )
        self.assertNotIn(
            "lsp_package_certification",
            [member["operation"] for member in local_members],
        )
        self.assertNotIn(
            "lsp_package_certification",
            [
                member["operation"]
                for member in toolchain.profile("pull-request")["operations"]
            ],
        )
        self.assertNotIn(
            "ecmascript_runtime_certification",
            [
                member["operation"]
                for member in toolchain.profile("pull-request")["operations"]
            ],
        )
        self.assertNotIn(
            "python_re_runtime_certification",
            [
                member["operation"]
                for member in toolchain.profile("pull-request")["operations"]
            ],
        )
        self.assertNotIn(
            "portability_matrix_certification",
            [
                member["operation"]
                for member in toolchain.profile("pull-request")["operations"]
            ],
        )
        self.assertNotIn(
            "stdlib_runtime_certification",
            [
                member["operation"]
                for member in toolchain.profile("pull-request")["operations"]
            ],
        )
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.pcre2_runtime_certification",
                "--json",
                "--repeat-runs",
                "2",
            ],
            toolchain.operation("pcre2_runtime_certification")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.ecmascript_runtime_certification",
                "--json",
                "--repeat-runs",
                "2",
            ],
            toolchain.operation("ecmascript_runtime_certification")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.python_re_runtime_certification",
                "--json",
                "--repeat-runs",
                "2",
            ],
            toolchain.operation("python_re_runtime_certification")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.shared_cross_engine_corpus",
                "--json",
                "--check",
                "--repeat-runs",
                "2",
            ],
            toolchain.operation("shared_cross_engine_certification")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.stdlib_runtime_certification",
                "--json",
                "--check",
                "--repeat-runs",
                "2",
            ],
            toolchain.operation("stdlib_runtime_certification")["command"],
        )
        self.assertEqual(
            [
                "python3",
                "-m",
                "tooling.portability_matrix",
                "--json",
                "--check",
            ],
            toolchain.operation("portability_matrix_certification")["command"],
        )
        release_ids = [
            member["operation"] for member in toolchain.profile("release")["operations"]
        ]
        self.assertEqual(
            release_ids.index("ecmascript_runtime_certification") + 1,
            release_ids.index("python_re_runtime_certification"),
        )
        self.assertEqual(
            release_ids.index("python_re_runtime_certification") + 1,
            release_ids.index("shared_cross_engine_certification"),
        )
        self.assertEqual(
            release_ids.index("shared_cross_engine_certification") + 1,
            release_ids.index("stdlib_runtime_certification"),
        )
        self.assertEqual(
            release_ids.index("stdlib_runtime_certification") + 1,
            release_ids.index("portability_matrix_certification"),
        )
        self.assertEqual("1.20.0", toolchain.profile("full")["definition_version"])
        self.assertEqual("1.20.0", toolchain.profile("release")["definition_version"])
        self.assertNotIn(
            "security_dependency_risk",
            [member["operation"] for member in local_members],
        )
        self.assertEqual("pull-request", toolchain.aggregate_profile("check"))
        self.assertEqual("full", toolchain.aggregate_profile("certify"))

    def test_structured_security_operation_preserves_non_pass_status(self) -> None:
        data = policy()
        definition = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-security", "--json"],
            "network": "offline",
            "result_contract": "security-result-v1",
            "result_operation_id": "security.fixture",
        }
        payload = {
            "operation_id": "security.fixture",
            "status": "unavailable",
            "summary": {"unavailable": 1},
            "checks": [],
        }
        result = QualityRunner(
            Toolchain(data, Path.cwd()),
            hardgate_executor=lambda *_args: Execution(2, stdout=json.dumps(payload)),
        ).run_repository_operation("security_fixture", definition)
        self.assertEqual("unavailable", result.status)
        self.assertEqual(payload, result.as_dict()["structured_result"])
        self.assertEqual(1, _profile_exit([result]))
        self.assertEqual("unavailable", _profile_status([result]))

    def test_structured_security_false_pass_is_incomplete(self) -> None:
        data = policy()
        definition = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-security", "--json"],
            "network": "offline",
            "result_contract": "security-result-v1",
            "result_operation_id": "security.fixture",
        }
        payload = {"operation_id": "security.fixture", "status": "passed"}
        result = QualityRunner(
            Toolchain(data, Path.cwd()),
            hardgate_executor=lambda *_args: Execution(2, stdout=json.dumps(payload)),
        ).run_repository_operation("security_fixture", definition)
        self.assertEqual("incomplete", result.status)
        self.assertIsNone(result.structured_result)
        self.assertEqual(1, _profile_exit([result]))

    def test_structured_documentation_operation_preserves_result(self) -> None:
        data = policy()
        definition = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-documentation", "--json"],
            "network": "offline",
            "result_contract": "documentation-result-v1",
            "result_operation_id": "documentation.integrity",
        }
        payload = {
            "operation_id": "documentation.integrity",
            "status": "passed",
            "summary": {"passed": 2},
            "checks": [],
        }
        result = QualityRunner(
            Toolchain(data, Path.cwd()),
            hardgate_executor=lambda *_args: Execution(0, stdout=json.dumps(payload)),
        ).run_repository_operation("documentation_integrity", definition)
        self.assertEqual("passed", result.status)
        self.assertEqual(payload, result.structured_result)
        self.assertEqual(0, _profile_exit([result]))

    def test_structured_certification_operation_preserves_unavailable(self) -> None:
        data = policy()
        definition = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-certification", "--json"],
            "network": "offline",
            "result_contract": "certification-result-v1",
            "result_operation_id": "certification.fixture",
        }
        payload = {
            "operation_id": "certification.fixture",
            "status": "unavailable",
            "summary": {"unavailable": 2},
            "checks": [],
        }
        result = QualityRunner(
            Toolchain(data, Path.cwd()),
            hardgate_executor=lambda *_args: Execution(2, stdout=json.dumps(payload)),
        ).run_repository_operation("certification_fixture", definition)
        self.assertEqual("unavailable", result.status)
        self.assertEqual(payload, result.structured_result)
        self.assertEqual(1, _profile_exit([result]))

    def test_repository_operation_precedes_profile_and_cannot_be_scoped_away(
        self,
    ) -> None:
        alpha = target_config(
            {"lint": "configured", "typecheck": "not_applicable"},
            {"lint": ["fixture-lint"]},
        )
        data = policy(alpha=alpha)
        policy_data = cast(dict[str, object], data["policy"])
        registry = cast(dict[str, object], policy_data["operation_registry"])
        definition = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-integrity", "--check"],
            "network": "offline",
        }
        registry["fixture_integrity"] = definition
        profiles = cast(dict[str, object], policy_data["profiles"])
        for raw_profile in profiles.values():
            profile = cast(dict[str, object], raw_profile)
            operations = cast(list[object], profile["operations"])
            operations.insert(0, {"operation": "fixture_integrity"})
        calls: list[tuple[str, list[str]]] = []
        results = QualityRunner(
            Toolchain(data, Path.cwd()),
            lambda *_args: Execution(0),
            hardgate_executor=lambda operation, command: (
                calls.append((operation, command)) or Execution(0)
            ),
        ).run_aggregate("check", "alpha")
        self.assertEqual(
            [
                ("alpha", "fixture_integrity", "passed"),
                ("alpha", "lint", "passed"),
                ("alpha", "typecheck", "not_applicable"),
            ],
            [(result.component, result.operation, result.status) for result in results],
        )
        self.assertEqual(
            [("fixture_integrity", ["fixture-integrity", "--check"])],
            calls,
        )

    def test_repository_operation_failure_propagates(self) -> None:
        data = policy()
        policy_data = cast(dict[str, object], data["policy"])
        registry = cast(dict[str, object], policy_data["operation_registry"])
        registry["fixture_integrity"] = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-integrity", "--check"],
            "network": "offline",
        }
        profiles = cast(dict[str, object], policy_data["profiles"])
        for raw_profile in profiles.values():
            operations = cast(dict[str, object], raw_profile)["operations"]
            cast(list[object], operations).insert(0, {"operation": "fixture_integrity"})
        results = QualityRunner(
            Toolchain(data, Path.cwd()),
            hardgate_executor=lambda *_args: Execution(31, stderr="stale\n"),
        ).run_aggregate("check", None)
        self.assertEqual("failed", results[0].status)
        self.assertEqual(31, results[0].exit_code)
        self.assertEqual("stale\n", results[0].stderr)
        self.assertEqual(1, _profile_exit(results))

    def test_canonical_operation_configuration_is_validated(self) -> None:
        malformed_entries = [
            (
                "fixture_integrity",
                {
                    "kind": "repository",
                    "component": "alpha",
                    "command": [],
                    "network": "offline",
                },
            ),
            (
                "fixture_integrity",
                {
                    "kind": "repository",
                    "component": "missing",
                    "command": ["fixture-integrity"],
                    "network": "offline",
                },
            ),
            (
                "fixture_integrity",
                {
                    "kind": "repository",
                    "component": "alpha",
                    "command": ["fixture-integrity"],
                    "network": "sometimes",
                },
            ),
            (
                "lint",
                {
                    "kind": "repository",
                    "component": "alpha",
                    "command": ["fixture-integrity"],
                    "network": "offline",
                },
            ),
            (
                "security_fixture",
                {
                    "kind": "repository",
                    "component": "alpha",
                    "command": ["fixture-integrity", "--json"],
                    "network": "offline",
                    "result_contract": "security-result-v1",
                },
            ),
            (
                "certification_fixture",
                {
                    "kind": "repository",
                    "component": "alpha",
                    "command": ["fixture-certification", "--json"],
                    "network": "offline",
                    "result_contract": "certification-result-v1",
                    "result_operation_id": "security.wrong-prefix",
                },
            ),
        ]
        for operation, definition in malformed_entries:
            with self.subTest(operation=operation, definition=definition):
                data = policy()
                policy_data = cast(dict[str, object], data["policy"])
                registry = cast(dict[str, object], policy_data["operation_registry"])
                registry[operation] = definition
                with self.assertRaises(ConfigurationError):
                    Toolchain(data, Path.cwd())

    def test_profile_uses_operation_specific_default_targets(self) -> None:
        alpha = target_config(
            {"lint": "configured"},
            {"lint": ["fixture-lint"]},
        )
        beta = target_config(
            {"hygiene": "configured"},
            {"hygiene": ["fixture-hygiene"]},
        )
        data = policy(alpha=alpha, beta=beta)
        members = [
            {"operation": "lint", "targets": ["alpha"]},
            {"operation": "hygiene", "targets": ["beta"]},
        ]
        policy_data = cast(dict[str, object], data["policy"])
        profiles = cast(dict[str, object], policy_data["profiles"])
        for raw_profile in profiles.values():
            profile = cast(dict[str, object], raw_profile)
            profile["operations"] = members
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

    def test_profile_rejects_unknown_operation_membership(self) -> None:
        data = policy()
        policy_data = cast(dict[str, object], data["policy"])
        profiles = cast(dict[str, object], policy_data["profiles"])
        pull_request = cast(dict[str, object], profiles["pull-request"])
        operations = cast(list[object], pull_request["operations"])
        operations.append({"operation": "unknown", "targets": ["alpha"]})
        with self.assertRaisesRegex(ConfigurationError, "unknown operation"):
            Toolchain(data, Path.cwd())

    def test_all_profile_identities_and_unknown_profile(self) -> None:
        toolchain = Toolchain(policy(), Path.cwd())
        self.assertEqual(
            ["local", "pull-request", "full", "release"],
            [
                name
                for name in ("local", "pull-request", "full", "release")
                if toolchain.profile(name)
            ],
        )
        with self.assertRaisesRegex(
            ConfigurationError, "unknown certification profile 'unknown'"
        ):
            toolchain.profile("unknown")

    def test_offline_profile_rejects_network_operation(self) -> None:
        data = policy()
        policy_data = cast(dict[str, object], data["policy"])
        registry = cast(dict[str, object], policy_data["operation_registry"])
        registry["network_fixture"] = {
            "kind": "repository",
            "component": "alpha",
            "command": ["fixture-network"],
            "network": "network",
        }
        profiles = cast(dict[str, object], policy_data["profiles"])
        local = cast(dict[str, object], profiles["local"])
        cast(list[object], local["operations"]).insert(
            0, {"operation": "network_fixture"}
        )
        with self.assertRaisesRegex(
            ConfigurationError, "local forbids network operation"
        ):
            Toolchain(data, Path.cwd())

    def test_unavailable_profile_operation_is_not_a_pass(self) -> None:
        alpha = target_config(
            {"lint": "unavailable"},
            capability_details={"lint": {"reason": "fixture analyzer missing"}},
        )
        data = policy(alpha=alpha)
        member = [{"operation": "lint", "targets": ["alpha"]}]
        policy_data = cast(dict[str, object], data["policy"])
        profiles = cast(dict[str, object], policy_data["profiles"])
        for raw_profile in profiles.values():
            profile = cast(dict[str, object], raw_profile)
            profile["operations"] = member
        results = QualityRunner(Toolchain(data, Path.cwd())).run_profile("local", None)
        self.assertEqual(["unavailable"], [result.status for result in results])
        self.assertEqual("unavailable", _profile_status(results))
        self.assertEqual(1, _profile_exit(results))

    def test_each_profile_executes_declared_order_deterministically(self) -> None:
        toolchain = Toolchain(policy(), Path.cwd())
        runner = QualityRunner(toolchain)
        expected = {
            "local": ["lint", "typecheck"],
            "pull-request": ["lint", "typecheck"],
            "full": ["lint", "typecheck", "build", "test"],
            "release": ["lint", "typecheck", "build", "test"],
        }
        for profile, operations in expected.items():
            with self.subTest(profile=profile):
                first = runner.run_profile(profile, None)
                second = runner.run_profile(profile, None)
                self.assertEqual(operations, [result.operation for result in first])
                self.assertEqual(
                    [result.as_dict() for result in first],
                    [result.as_dict() for result in second],
                )

    def test_profile_aggregate_status_precedence(self) -> None:
        def result(status: str) -> OperationResult:
            return OperationResult("fixture", "alpha", status, None, None, None)

        self.assertEqual(
            "failed",
            _profile_status(
                [
                    result("waived"),
                    result("unavailable"),
                    result("incomplete"),
                    result("failed"),
                ]
            ),
        )
        self.assertEqual(
            "incomplete",
            _profile_status([result("unavailable"), result("incomplete")]),
        )
        self.assertEqual("incomplete", _profile_status([result("not_yet_configured")]))
        self.assertEqual(
            "unavailable",
            _profile_status([result("waived"), result("unavailable")]),
        )
        self.assertEqual(
            "waived", _profile_status([result("passed"), result("waived")])
        )
        self.assertEqual(
            "passed", _profile_status([result("passed"), result("not_applicable")])
        )
        self.assertEqual(0, _profile_exit([result("waived")]))
        self.assertEqual(1, _profile_exit([result("not_yet_enforceable")]))

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
            ("format_check", "alpha", True, None, None),
            _parse_cli(["format", "alpha", "--check", "--json"]),
        )
        self.assertEqual(
            ("format_check", "alpha", True, None, None),
            _parse_cli(["format", "--json", "--check", "alpha"]),
        )
        self.assertEqual(
            (
                "profile",
                "alpha",
                True,
                "pull-request",
                "/tmp/certification.json",
            ),
            _parse_cli(
                [
                    "profile",
                    "pull-request",
                    "alpha",
                    "--artifact",
                    "/tmp/certification.json",
                    "--json",
                ]
            ),
        )
        with self.assertRaisesRegex(
            ConfigurationError, "profile requires a profile identity"
        ):
            _parse_cli(["profile"])
        with self.assertRaisesRegex(ConfigurationError, "only for profile"):
            _parse_cli(["lint", "--artifact", "certification.json"])
        with self.assertRaisesRegex(ConfigurationError, "requires an output path"):
            _parse_cli(["check", "--artifact"])


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

    @patch("quality.subprocess.run")
    @patch("quality.shutil.which")
    def test_default_probe_executes_the_resolved_command(self, which, run) -> None:
        resolved = Path.cwd() / "fixture-tools" / "python3.CMD"
        which.return_value = str(resolved)
        run.return_value = subprocess.CompletedProcess(
            [str(resolved), "--version"],
            0,
            stdout="Python 3.12.4\n",
            stderr="",
        )

        execution = EnvironmentInspector._probe(["python3", "--version"])

        self.assertEqual(execution.returncode, 0)
        self.assertEqual(
            run.call_args.args[0],
            [str(resolved.absolute()), "--version"],
        )

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
