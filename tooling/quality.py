#!/usr/bin/env python3
"""Language-agnostic orchestration for STRling repository quality commands."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence


QUALITY_OPERATIONS = (
    "format",
    "format_check",
    "lint",
    "typecheck",
    "build",
    "test",
)
AGGREGATE_OPERATIONS = ("check", "certify")
CAPABILITY_STATUSES = (
    "configured",
    "not_applicable",
    "not_yet_configured",
)


class ConfigurationError(ValueError):
    """Raised when toolchain.json cannot support deterministic orchestration."""


@dataclass(frozen=True)
class Target:
    name: str
    kind: str
    config: Mapping[str, object]


@dataclass(frozen=True)
class Execution:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class OperationResult:
    operation: str
    component: str
    status: str
    command: list[str] | None
    exit_code: int | None
    reason: str | None
    stdout: str = field(default="", repr=False)
    stderr: str = field(default="", repr=False)

    def as_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "component": self.component,
            "status": self.status,
            "command": self.command,
            "exit_code": self.exit_code,
            "reason": self.reason,
        }


class Toolchain:
    """Validated view of the command and capability policy."""

    def __init__(self, data: Mapping[str, object], root: Path) -> None:
        self.data = data
        self.root = root
        self._validate()

    @classmethod
    def load(cls, path: Path) -> "Toolchain":
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"cannot read {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigurationError("toolchain root must be an object")
        return cls(data, path.parent)

    @property
    def policy(self) -> Mapping[str, object]:
        return self.data["policy"]  # type: ignore[return-value]

    @property
    def tools(self) -> Mapping[str, object]:
        return self.data["tools"]  # type: ignore[return-value]

    @property
    def targets(self) -> dict[str, Target]:
        targets: dict[str, Target] = {}
        for kind, section in (
            ("component", self.data["components"]),
            ("binding", self.data["bindings"]),
        ):
            assert isinstance(section, dict)
            for name, config in section.items():
                assert isinstance(config, dict)
                targets[name] = Target(name, kind, config)
        return targets

    def select(self, requested: str | None, defaults: Sequence[str] | None = None) -> list[Target]:
        targets = self.targets
        if requested is None and defaults is not None:
            names = list(defaults)
        elif requested is None or requested == "all":
            names = sorted(targets)
        else:
            names = [requested]
        unknown = [name for name in names if name not in targets]
        if unknown:
            available = ", ".join(sorted(targets))
            raise ConfigurationError(
                f"unknown component '{unknown[0]}'; available components: {available}"
            )
        return [targets[name] for name in names]

    def capability(self, target: Target, operation: str) -> str:
        capabilities = target.config["capabilities"]
        assert isinstance(capabilities, dict)
        return capabilities[operation]  # type: ignore[return-value]

    def resolve_command(self, target: Target, operation: str) -> tuple[str, list[str]]:
        aliases = target.config.get("command_aliases", {})
        if not isinstance(aliases, dict):
            raise ConfigurationError(f"{target.name}.command_aliases must be an object")
        resolved = operation
        seen: set[str] = set()
        while resolved in aliases:
            if resolved in seen:
                raise ConfigurationError(f"{target.name} contains a command alias cycle")
            seen.add(resolved)
            alias = aliases[resolved]
            if not isinstance(alias, str):
                raise ConfigurationError(f"{target.name}.{resolved} alias must be a string")
            resolved = alias
        command = target.config.get(resolved)
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) and item for item in command
        ):
            raise ConfigurationError(
                f"{target.name}.{operation} is configured without a command"
            )
        return resolved, list(command)

    def aggregate(self, name: str) -> Mapping[str, object]:
        aggregates = self.policy["aggregates"]
        assert isinstance(aggregates, dict)
        return aggregates[name]  # type: ignore[return-value]

    def incomplete_capabilities(self) -> list[dict[str, str]]:
        incomplete: list[dict[str, str]] = []
        for name, target in sorted(self.targets.items()):
            for operation in QUALITY_OPERATIONS:
                status = self.capability(target, operation)
                if status == "not_yet_configured":
                    incomplete.append(
                        {
                            "component": name,
                            "operation": operation,
                            "status": status,
                        }
                    )
        return incomplete

    def _validate(self) -> None:
        if self.data.get("schema_version") != 1:
            raise ConfigurationError("unsupported or missing toolchain schema_version")
        for key in ("policy", "orchestration", "tools", "components", "bindings"):
            if not isinstance(self.data.get(key), dict):
                raise ConfigurationError(f"{key} must be an object")
        policy = self.data["policy"]
        assert isinstance(policy, dict)
        aggregates = policy.get("aggregates")
        if not isinstance(aggregates, dict):
            raise ConfigurationError("policy.aggregates must be an object")
        tools = self.data["tools"]
        assert isinstance(tools, dict)
        target_names: set[str] = set()
        for section_name in ("components", "bindings"):
            section = self.data[section_name]
            assert isinstance(section, dict)
            for name, raw in section.items():
                if name in target_names:
                    raise ConfigurationError(f"duplicate component '{name}'")
                target_names.add(name)
                if not isinstance(raw, dict):
                    raise ConfigurationError(f"{name} must be an object")
                path = raw.get("path")
                if not isinstance(path, str) or not path:
                    raise ConfigurationError(f"{name}.path must be a non-empty string")
                runtime = raw.get("runtime")
                if runtime not in tools:
                    raise ConfigurationError(f"{name}.runtime references unknown tool '{runtime}'")
                required = raw.get("required_bins")
                if not isinstance(required, list) or not required:
                    raise ConfigurationError(f"{name}.required_bins must be a non-empty list")
                unknown_tools = [tool for tool in required if tool not in tools]
                if unknown_tools:
                    raise ConfigurationError(
                        f"{name}.required_bins references unknown tool '{unknown_tools[0]}'"
                    )
                capabilities = raw.get("capabilities")
                if not isinstance(capabilities, dict):
                    raise ConfigurationError(f"{name}.capabilities must be an object")
                if set(capabilities) != set(QUALITY_OPERATIONS):
                    raise ConfigurationError(
                        f"{name}.capabilities must declare every quality operation"
                    )
                target = Target(name, section_name[:-1], raw)
                for operation, status in capabilities.items():
                    if status not in CAPABILITY_STATUSES:
                        raise ConfigurationError(
                            f"{name}.{operation} has invalid capability status '{status}'"
                        )
                    if status == "configured":
                        self.resolve_command(target, operation)
        for name in AGGREGATE_OPERATIONS:
            aggregate = aggregates.get(name)
            if not isinstance(aggregate, dict):
                raise ConfigurationError(f"policy.aggregates.{name} must be an object")
            operations = aggregate.get("operations")
            defaults = aggregate.get("default_targets")
            if not isinstance(operations, list) or not operations:
                raise ConfigurationError(f"{name}.operations must be a non-empty list")
            if any(operation not in QUALITY_OPERATIONS for operation in operations):
                raise ConfigurationError(f"{name} contains an unknown operation")
            if not isinstance(defaults, list) or not defaults:
                raise ConfigurationError(f"{name}.default_targets must be a non-empty list")
            if any(target not in target_names for target in defaults):
                raise ConfigurationError(f"{name} contains an unknown default target")


Executor = Callable[[Target, str, list[str]], Execution]


class QualityRunner:
    """Dispatch configured commands and preserve their exact status."""

    def __init__(self, toolchain: Toolchain, executor: Executor | None = None) -> None:
        self.toolchain = toolchain
        self.executor = executor or self._execute

    def run_leaf(self, operation: str, target: Target) -> OperationResult:
        capability = self.toolchain.capability(target, operation)
        if capability != "configured":
            wording = capability.replace("_", " ")
            return OperationResult(
                operation,
                target.name,
                capability,
                None,
                None,
                f"{operation.replace('_', ' ')} is {wording} for {target.name}",
            )
        resolved, command = self.toolchain.resolve_command(target, operation)
        execution = self.executor(target, resolved, command)
        status = "passed" if execution.returncode == 0 else "failed"
        reason = None
        if execution.returncode != 0:
            reason = f"command exited with status {execution.returncode}"
        return OperationResult(
            operation,
            target.name,
            status,
            command,
            execution.returncode,
            reason,
            execution.stdout,
            execution.stderr,
        )

    def run_operation(self, operation: str, requested: str | None) -> list[OperationResult]:
        return [
            self.run_leaf(operation, target)
            for target in self.toolchain.select(requested)
        ]

    def run_aggregate(self, name: str, requested: str | None) -> list[OperationResult]:
        aggregate = self.toolchain.aggregate(name)
        operations = aggregate["operations"]
        defaults = aggregate["default_targets"]
        assert isinstance(operations, list)
        assert isinstance(defaults, list)
        targets = self.toolchain.select(requested, defaults)
        return [
            self.run_leaf(operation, target)
            for target in targets
            for operation in operations
        ]

    def _execute(self, target: Target, resolved: str, command: list[str]) -> Execution:
        if target.kind == "binding":
            invocation = [
                str(self.toolchain.root / "strling"),
                "_run-configured",
                resolved,
                target.name,
            ]
            cwd = self.toolchain.root
        else:
            invocation = command
            cwd = self.toolchain.root / str(target.config["path"])
        try:
            completed = subprocess.run(
                invocation,
                cwd=cwd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            return Execution(127, stderr=str(exc))
        return Execution(completed.returncode, completed.stdout, completed.stderr)


def _parse_cli(argv: Sequence[str]) -> tuple[str, str | None, bool]:
    args = list(argv)
    json_output = False
    if "--json" in args:
        args.remove("--json")
        json_output = True
    if not args or args[0] in ("help", "-h", "--help"):
        return "help", None, json_output
    operation = args.pop(0)
    if operation == "format" and "--check" in args:
        args.remove("--check")
        operation = "format_check"
    if operation not in QUALITY_OPERATIONS + AGGREGATE_OPERATIONS:
        raise ConfigurationError(f"unknown quality operation '{operation}'")
    if any(argument.startswith("-") for argument in args):
        raise ConfigurationError(f"unknown option '{args[0]}'")
    if len(args) > 1:
        raise ConfigurationError("at most one component may be selected")
    return operation, args[0] if args else None, json_output


def _overall_exit(results: Iterable[OperationResult], single: bool) -> int:
    failures = [result for result in results if result.status in ("failed", "unavailable")]
    if not failures:
        return 0
    if single and failures[0].exit_code:
        return failures[0].exit_code
    return 1


def _render_human(
    operation: str,
    results: Sequence[OperationResult],
    incomplete: Sequence[Mapping[str, str]],
) -> None:
    for result in results:
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
        command = shlex.join(result.command) if result.command else "-"
        suffix = f" ({result.reason})" if result.reason else ""
        print(
            f"[{result.status}] {result.component} {result.operation}: {command}{suffix}"
        )
    if operation in AGGREGATE_OPERATIONS and incomplete:
        print("Incomplete capabilities:")
        grouped: dict[str, list[str]] = {}
        for item in incomplete:
            grouped.setdefault(item["component"], []).append(item["operation"])
        for component, operations in grouped.items():
            print(f"  {component}: {', '.join(operations)} [not_yet_configured]")


def _print_help() -> None:
    print("Usage: ./strling <quality-command> [component|all] [--json]")
    print("       ./strling format [--check] [component|all] [--json]")
    print("")
    print("Quality commands: format, lint, typecheck, build, test, check, certify")


def main(argv: Sequence[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        operation, requested, json_output = _parse_cli(argv)
        if operation == "help":
            _print_help()
            return 0
        root = Path(__file__).resolve().parent.parent
        toolchain = Toolchain.load(root / "toolchain.json")
        runner = QualityRunner(toolchain)
        if operation in AGGREGATE_OPERATIONS:
            results = runner.run_aggregate(operation, requested)
            incomplete = toolchain.incomplete_capabilities()
        else:
            results = runner.run_operation(operation, requested)
            incomplete = []
        exit_code = _overall_exit(results, len(results) == 1)
        status = "passed" if exit_code == 0 else "failed"
        if json_output:
            print(
                json.dumps(
                    {
                        "operation": operation,
                        "status": status,
                        "exit_code": exit_code,
                        "results": [result.as_dict() for result in results],
                        "incomplete_capabilities": incomplete,
                    },
                    sort_keys=True,
                )
            )
        else:
            _render_human(operation, results, incomplete)
        return exit_code
    except ConfigurationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
