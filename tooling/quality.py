#!/usr/bin/env python3
"""Language-agnostic orchestration for STRling repository quality commands."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence


QUALITY_OPERATIONS = (
    "format",
    "hygiene",
    "format_check",
    "lint",
    "typecheck",
    "build",
    "test",
)
AGGREGATE_OPERATIONS = ("check", "certify")
ENVIRONMENT_OPERATION = "environment"
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
class ToolResult:
    tool: str
    status: str
    expected: str | None
    actual: str | None
    command: list[str] | None
    exit_code: int | None
    reason: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "tool": self.tool,
            "status": self.status,
            "expected": self.expected,
            "actual": self.actual,
            "command": self.command,
            "exit_code": self.exit_code,
            "reason": self.reason,
        }


@dataclass
class OperationResult:
    operation: str
    component: str
    status: str
    command: list[str] | None
    exit_code: int | None
    reason: str | None
    formatters: list[str] = field(default_factory=list)
    environment: list[ToolResult] = field(default_factory=list)
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
            "formatters": self.formatters,
            "environment": [result.as_dict() for result in self.environment],
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

    def select(
        self, requested: str | None, defaults: Sequence[str] | None = None
    ) -> list[Target]:
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

    def operation_tools(self, target: Target, operation: str | None) -> list[str]:
        configured = target.config.get("operation_tools", {})
        assert isinstance(configured, dict)
        if operation is None:
            tools: list[str] = []
            for values in configured.values():
                assert isinstance(values, list)
                tools.extend(values)
            return list(dict.fromkeys(tools))
        values = configured.get(operation, [])
        assert isinstance(values, list)
        return list(values)

    def formatter_names(self, target: Target, operation: str) -> list[str]:
        if operation not in ("format", "format_check"):
            return []
        formatters = target.config.get("formatters", [])
        assert isinstance(formatters, list)
        return list(formatters)

    def resolve_command(self, target: Target, operation: str) -> tuple[str, list[str]]:
        aliases = target.config.get("command_aliases", {})
        if not isinstance(aliases, dict):
            raise ConfigurationError(f"{target.name}.command_aliases must be an object")
        resolved = operation
        seen: set[str] = set()
        while resolved in aliases:
            if resolved in seen:
                raise ConfigurationError(
                    f"{target.name} contains a command alias cycle"
                )
            seen.add(resolved)
            alias = aliases[resolved]
            if not isinstance(alias, str):
                raise ConfigurationError(
                    f"{target.name}.{resolved} alias must be a string"
                )
            resolved = alias
        command = target.config.get(resolved)
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(item, str) and item for item in command)
        ):
            raise ConfigurationError(
                f"{target.name}.{operation} is configured without a command"
            )
        return resolved, list(command)

    def aggregate(self, name: str) -> Mapping[str, object]:
        aggregates = self.policy["aggregates"]
        assert isinstance(aggregates, dict)
        return aggregates[name]  # type: ignore[return-value]

    def operation_defaults(self, operation: str) -> list[str] | None:
        defaults = self.policy.get("operation_defaults", {})
        assert isinstance(defaults, dict)
        selected = defaults.get(operation)
        if selected is None:
            return None
        assert isinstance(selected, list)
        return list(selected)

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
        declared_models = policy.get("resolution_models")
        if not isinstance(declared_models, list):
            raise ConfigurationError("policy.resolution_models must be a list")
        for name, raw_tool in tools.items():
            if not isinstance(raw_tool, dict):
                raise ConfigurationError(f"tool {name} must be an object")
            resolution = raw_tool.get("resolution")
            command = raw_tool.get("version_command")
            pattern = raw_tool.get("version_pattern")
            if not isinstance(resolution, dict):
                raise ConfigurationError(f"tool {name} must declare resolution")
            model = resolution.get("model")
            if model not in declared_models:
                raise ConfigurationError(
                    f"tool {name} has unknown resolution model '{model}'"
                )
            if (
                not isinstance(command, list)
                or not command
                or not all(isinstance(item, str) and item for item in command)
            ):
                raise ConfigurationError(f"tool {name} must declare version_command")
            if not isinstance(pattern, str):
                raise ConfigurationError(f"tool {name} must declare version_pattern")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ConfigurationError(
                    f"tool {name} has invalid version_pattern: {exc}"
                ) from exc
            if model in ("exact", "constrained"):
                version = resolution.get("version")
                if not isinstance(version, str):
                    raise ConfigurationError(
                        f"tool {name} must declare a version constraint"
                    )
                if model == "exact" and not re.fullmatch(
                    r"[0-9]+(?:\.[0-9]+){0,3}", version
                ):
                    raise ConfigurationError(
                        f"exact tool {name} must declare one numeric version"
                    )
                version_satisfies("0", version)
                transitional = resolution.get("transitional_version")
                if transitional is not None:
                    if not isinstance(transitional, str) or not isinstance(
                        resolution.get("reason"), str
                    ):
                        raise ConfigurationError(
                            f"tool {name} transitional version requires a constraint and reason"
                        )
                    version_satisfies("0", transitional)
            elif model == "repository_managed":
                if not isinstance(resolution.get("file"), str):
                    raise ConfigurationError(
                        f"repository-managed tool {name} must declare its authority file"
                    )
            elif not isinstance(resolution.get("reason"), str):
                raise ConfigurationError(f"deferred tool {name} must declare a reason")
        orchestration = self.data["orchestration"]
        assert isinstance(orchestration, dict)
        for field_name in ("shell", "runtime"):
            tool_name = orchestration.get(field_name)
            if tool_name not in tools:
                raise ConfigurationError(
                    f"orchestration.{field_name} references unknown tool '{tool_name}'"
                )
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
                    raise ConfigurationError(
                        f"{name}.runtime references unknown tool '{runtime}'"
                    )
                required = raw.get("required_bins")
                if not isinstance(required, list) or not required:
                    raise ConfigurationError(
                        f"{name}.required_bins must be a non-empty list"
                    )
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
                operation_tools = raw.get("operation_tools", {})
                if not isinstance(operation_tools, dict):
                    raise ConfigurationError(
                        f"{name}.operation_tools must be an object"
                    )
                for operation, operation_required in operation_tools.items():
                    if operation not in QUALITY_OPERATIONS:
                        raise ConfigurationError(
                            f"{name}.operation_tools contains unknown operation '{operation}'"
                        )
                    if not isinstance(operation_required, list) or not all(
                        isinstance(tool, str) and tool for tool in operation_required
                    ):
                        raise ConfigurationError(
                            f"{name}.{operation} operation tools must be a list of tool names"
                        )
                    unknown_operation_tools = [
                        tool for tool in operation_required if tool not in tools
                    ]
                    if unknown_operation_tools:
                        raise ConfigurationError(
                            f"{name}.{operation} references unknown tool "
                            f"'{unknown_operation_tools[0]}'"
                        )
                formatters = raw.get("formatters", [])
                if not isinstance(formatters, list) or not all(
                    isinstance(formatter, str) and formatter for formatter in formatters
                ):
                    raise ConfigurationError(
                        f"{name}.formatters must be a list of names"
                    )
                if (
                    any(
                        capabilities[operation] == "configured"
                        for operation in ("format", "format_check")
                    )
                    and not formatters
                ):
                    raise ConfigurationError(
                        f"{name} configures formatting without formatter metadata"
                    )
                target = Target(name, section_name[:-1], raw)
                for operation, status in capabilities.items():
                    if status not in CAPABILITY_STATUSES:
                        raise ConfigurationError(
                            f"{name}.{operation} has invalid capability status '{status}'"
                        )
                    if status == "configured":
                        self.resolve_command(target, operation)
        operation_defaults = policy.get("operation_defaults", {})
        if not isinstance(operation_defaults, dict):
            raise ConfigurationError("policy.operation_defaults must be an object")
        for operation, default_targets in operation_defaults.items():
            if operation not in QUALITY_OPERATIONS:
                raise ConfigurationError(
                    f"policy.operation_defaults contains unknown operation '{operation}'"
                )
            if not isinstance(default_targets, list) or not default_targets:
                raise ConfigurationError(
                    f"policy.operation_defaults.{operation} must be a non-empty list"
                )
            if any(target not in target_names for target in default_targets):
                raise ConfigurationError(
                    f"policy.operation_defaults.{operation} contains an unknown target"
                )
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
                raise ConfigurationError(
                    f"{name}.default_targets must be a non-empty list"
                )
            if any(target not in target_names for target in defaults):
                raise ConfigurationError(f"{name} contains an unknown default target")


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = version.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ConfigurationError(f"invalid numeric version '{version}'")
    values = tuple(int(part) for part in parts)
    return values + (0,) * (4 - len(values))


def version_satisfies(actual: str, constraint: str) -> bool:
    """Evaluate comma-separated comparisons with optional || alternatives."""

    actual_version = _version_tuple(actual)
    for alternative in constraint.split("||"):
        matches = True
        clauses = [
            clause.strip() for clause in alternative.split(",") if clause.strip()
        ]
        if not clauses:
            raise ConfigurationError(f"empty version constraint '{constraint}'")
        for clause in clauses:
            match = re.fullmatch(r"(>=|<=|==|>|<)?\s*([0-9]+(?:\.[0-9]+){0,3})", clause)
            if not match:
                raise ConfigurationError(f"invalid version constraint '{constraint}'")
            operator = match.group(1) or "=="
            expected = _version_tuple(match.group(2))
            comparisons = {
                "==": actual_version == expected,
                ">=": actual_version >= expected,
                "<=": actual_version <= expected,
                ">": actual_version > expected,
                "<": actual_version < expected,
            }
            if not comparisons[operator]:
                matches = False
                break
        if matches:
            return True
    return False


Probe = Callable[[Sequence[str]], Execution]
Which = Callable[[str], str | None]


class EnvironmentInspector:
    """Resolve executable availability and declared version compatibility."""

    def __init__(
        self,
        toolchain: Toolchain,
        probe: Probe | None = None,
        which: Which | None = None,
    ) -> None:
        self.toolchain = toolchain
        self.probe = probe or self._probe
        self.which = which or shutil.which
        self._cache: dict[str, ToolResult] = {}

    def check_target(
        self, target: Target, operation: str | None = None
    ) -> list[ToolResult]:
        required = target.config["required_bins"]
        assert isinstance(required, list)
        operation_required = self.toolchain.operation_tools(target, operation)
        orchestration = self.toolchain.data["orchestration"]
        assert isinstance(orchestration, dict)
        tools = [
            orchestration["shell"],
            orchestration["runtime"],
            *required,
            *operation_required,
        ]
        unique = list(dict.fromkeys(tools))
        return [self.check_tool(tool) for tool in unique]

    def check_tool(self, name: str) -> ToolResult:
        if name in self._cache:
            return self._cache[name]
        raw = self.toolchain.tools[name]
        assert isinstance(raw, dict)
        command = raw["version_command"]
        pattern = raw["version_pattern"]
        resolution = raw["resolution"]
        assert isinstance(command, list)
        assert isinstance(pattern, str)
        assert isinstance(resolution, dict)
        executable = command[0]
        assert isinstance(executable, str)
        model = resolution["model"]
        expected = resolution.get("version")
        if not self.which(executable):
            result = ToolResult(
                name,
                "unavailable",
                str(expected) if expected else None,
                None,
                None,
                None,
                f"required executable '{executable}' was not found",
            )
            self._cache[name] = result
            return result
        execution = self.probe(command)
        if execution.returncode != 0:
            result = ToolResult(
                name,
                "unknown",
                str(expected) if expected else None,
                None,
                list(command),
                execution.returncode,
                "version probe failed",
            )
            self._cache[name] = result
            return result
        output = execution.stdout + "\n" + execution.stderr
        match = re.search(pattern, output, re.IGNORECASE)
        if not match:
            result = ToolResult(
                name,
                "unknown",
                str(expected) if expected else None,
                None,
                list(command),
                execution.returncode,
                "version probe output did not match the declared pattern",
            )
            self._cache[name] = result
            return result
        actual = match.group(1)
        if model == "deferred":
            result = ToolResult(
                name,
                "deferred",
                None,
                actual,
                list(command),
                execution.returncode,
                str(resolution["reason"]),
            )
        elif model == "repository_managed":
            expected_version = self._repository_version(resolution)
            if expected_version is None or version_satisfies(actual, expected_version):
                result = ToolResult(
                    name,
                    "compatible",
                    expected_version,
                    actual,
                    list(command),
                    execution.returncode,
                    None,
                )
            else:
                result = ToolResult(
                    name,
                    "incompatible",
                    expected_version,
                    actual,
                    list(command),
                    execution.returncode,
                    "installed version differs from the repository-managed version",
                )
        else:
            assert isinstance(expected, str)
            if version_satisfies(actual, expected):
                result = ToolResult(
                    name,
                    "compatible",
                    expected,
                    actual,
                    list(command),
                    execution.returncode,
                    None,
                )
            else:
                transitional = resolution.get("transitional_version")
                if isinstance(transitional, str) and version_satisfies(
                    actual, transitional
                ):
                    result = ToolResult(
                        name,
                        "transitional",
                        expected,
                        actual,
                        list(command),
                        execution.returncode,
                        str(resolution["reason"]),
                    )
                else:
                    result = ToolResult(
                        name,
                        "incompatible",
                        expected,
                        actual,
                        list(command),
                        execution.returncode,
                        f"version {actual} does not satisfy {expected}",
                    )
        self._cache[name] = result
        return result

    def _repository_version(self, resolution: Mapping[str, object]) -> str | None:
        file_name = resolution.get("file")
        pattern = resolution.get("file_pattern")
        if not isinstance(file_name, str) or not isinstance(pattern, str):
            return None
        path = self.toolchain.root / file_name
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(
                f"cannot read repository version file {path}: {exc}"
            ) from exc
        match = re.search(pattern, content)
        if not match:
            raise ConfigurationError(
                f"repository version file {file_name} does not match its declared pattern"
            )
        return match.group(1)

    @staticmethod
    def _probe(command: Sequence[str]) -> Execution:
        try:
            completed = subprocess.run(
                list(command),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            return Execution(127, stderr=str(exc))
        return Execution(completed.returncode, completed.stdout, completed.stderr)


Executor = Callable[[Target, str, list[str]], Execution]


class QualityRunner:
    """Dispatch configured commands and preserve their exact status."""

    def __init__(
        self,
        toolchain: Toolchain,
        executor: Executor | None = None,
        inspector: EnvironmentInspector | None = None,
    ) -> None:
        self.toolchain = toolchain
        self.executor = executor or self._execute
        self.inspector = inspector or EnvironmentInspector(toolchain)

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
        formatters = self.toolchain.formatter_names(target, operation)
        environment = self.inspector.check_target(target, operation)
        blockers = [
            result
            for result in environment
            if result.status in ("unavailable", "unknown", "incompatible")
        ]
        if blockers:
            details = "; ".join(
                f"{result.tool}: {result.reason}" for result in blockers
            )
            return OperationResult(
                operation=operation,
                component=target.name,
                status="unavailable",
                command=None,
                exit_code=None,
                reason=details,
                formatters=formatters,
                environment=environment,
            )
        execution = self.executor(target, resolved, command)
        status = "passed" if execution.returncode == 0 else "failed"
        notices = [
            f"{result.tool} is {result.status}: {result.reason}"
            for result in environment
            if result.status in ("transitional", "deferred")
        ]
        reason = "; ".join(notices) if notices else None
        if execution.returncode != 0:
            failure = f"command exited with status {execution.returncode}"
            reason = f"{failure}; {reason}" if reason else failure
        return OperationResult(
            operation=operation,
            component=target.name,
            status=status,
            command=command,
            exit_code=execution.returncode,
            reason=reason,
            formatters=formatters,
            environment=environment,
            stdout=execution.stdout,
            stderr=execution.stderr,
        )

    def run_operation(
        self, operation: str, requested: str | None
    ) -> list[OperationResult]:
        defaults = self.toolchain.operation_defaults(operation)
        return [
            self.run_leaf(operation, target)
            for target in self.toolchain.select(requested, defaults)
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

    def run_environment(self, requested: str | None) -> list[OperationResult]:
        results: list[OperationResult] = []
        for target in self.toolchain.select(requested):
            environment = self.inspector.check_target(target)
            blockers = [
                result
                for result in environment
                if result.status in ("unavailable", "unknown", "incompatible")
            ]
            notices = [
                f"{result.tool} is {result.status}: {result.reason}"
                for result in environment
                if result.status in ("transitional", "deferred")
            ]
            if blockers:
                notices.extend(f"{result.tool}: {result.reason}" for result in blockers)
            results.append(
                OperationResult(
                    operation=ENVIRONMENT_OPERATION,
                    component=target.name,
                    status="unavailable" if blockers else "passed",
                    command=None,
                    exit_code=1 if blockers else 0,
                    reason="; ".join(notices) if notices else None,
                    environment=environment,
                )
            )
        return results

    def _execute(self, target: Target, resolved: str, command: list[str]) -> Execution:
        if target.kind == "binding" and resolved not in ("format", "format_check"):
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
    if operation not in QUALITY_OPERATIONS + AGGREGATE_OPERATIONS + (
        ENVIRONMENT_OPERATION,
    ):
        raise ConfigurationError(f"unknown quality operation '{operation}'")
    if any(argument.startswith("-") for argument in args):
        option = next(argument for argument in args if argument.startswith("-"))
        raise ConfigurationError(f"unknown option '{option}'")
    if len(args) > 1:
        raise ConfigurationError("at most one component may be selected")
    return operation, args[0] if args else None, json_output


def _overall_exit(results: Iterable[OperationResult], single: bool) -> int:
    failures = [
        result for result in results if result.status in ("failed", "unavailable")
    ]
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
            print(
                result.stderr,
                end="" if result.stderr.endswith("\n") else "\n",
                file=sys.stderr,
            )
        command = shlex.join(result.command) if result.command else "-"
        suffix = f" ({result.reason})" if result.reason else ""
        formatters = ", ".join(result.formatters)
        formatter_suffix = f" [formatters: {formatters}]" if formatters else ""
        print(
            f"[{result.status}] {result.component} {result.operation}: "
            f"{command}{formatter_suffix}{suffix}"
        )
        if operation == ENVIRONMENT_OPERATION:
            for tool in result.environment:
                expected = f", expected {tool.expected}" if tool.expected else ""
                actual = tool.actual or "unavailable"
                print(f"  {tool.tool}: {tool.status} ({actual}{expected})")
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
    print(
        "Quality commands: format, hygiene, lint, typecheck, build, test, check, certify, environment"
    )


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
        elif operation == ENVIRONMENT_OPERATION:
            results = runner.run_environment(requested)
            incomplete = []
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
