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
from certification import (
    CertificationError,
    aggregate_profile_exit,
    aggregate_profile_status,
    build_certification_artifact,
    render_certification_summary,
    write_certification_artifact,
)

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
PROFILE_OPERATION = "profile"
PROFILE_NAMES = ("local", "pull-request", "full", "release")
CAPABILITY_STATUSES = (
    "enforced",
    "configured",
    "not_applicable",
    "not_yet_configured",
    "not_yet_enforceable",
    "unavailable",
)
EXECUTABLE_CAPABILITY_STATUSES = ("configured", "enforced")
STRUCTURED_RESULT_STATUSES = (
    "passed",
    "failed",
    "waived",
    "unavailable",
    "incomplete",
)
STRUCTURED_RESULT_EXIT_CODES = {
    "passed": 0,
    "waived": 0,
    "failed": 1,
    "unavailable": 2,
    "incomplete": 3,
}
STRUCTURED_RESULT_CONTRACT_PREFIXES = {
    "security-result-v1": "security.",
    "documentation-result-v1": "documentation.",
    "certification-result-v1": "certification.",
}


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
    capability: str | None = None
    formatters: list[str] = field(default_factory=list)
    environment: list[ToolResult] = field(default_factory=list)
    structured_result: dict[str, object] | None = None
    stdout: str = field(default="", repr=False)
    stderr: str = field(default="", repr=False)

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "operation": self.operation,
            "component": self.component,
            "status": self.status,
            "command": self.command,
            "exit_code": self.exit_code,
            "reason": self.reason,
            "capability": self.capability,
            "formatters": self.formatters,
            "environment": [result.as_dict() for result in self.environment],
        }
        if self.structured_result is not None:
            result["structured_result"] = self.structured_result
        return result


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

    def operation(self, name: str) -> Mapping[str, object]:
        registry = self.policy["operation_registry"]
        assert isinstance(registry, dict)
        operation = registry.get(name)
        if not isinstance(operation, dict):
            raise ConfigurationError(f"unknown canonical operation '{name}'")
        return operation

    def profile(self, name: str) -> Mapping[str, object]:
        profiles = self.policy["profiles"]
        assert isinstance(profiles, dict)
        profile = profiles.get(name)
        if not isinstance(profile, dict):
            available = ", ".join(PROFILE_NAMES)
            raise ConfigurationError(
                f"unknown certification profile '{name}'; available profiles: {available}"
            )
        return profile

    def aggregate_profile(self, name: str) -> str:
        aliases = self.policy["aggregate_profiles"]
        assert isinstance(aliases, dict)
        profile = aliases[name]
        assert isinstance(profile, str)
        return profile

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
                if status in (
                    "not_yet_configured",
                    "not_yet_enforceable",
                    "unavailable",
                ):
                    item = {
                        "component": name,
                        "operation": operation,
                        "status": status,
                    }
                    details = self.capability_details(target, operation)
                    reason = details.get("reason")
                    if isinstance(reason, str):
                        item["reason"] = reason
                    incomplete.append(item)
        return incomplete

    def capability_details(
        self, target: Target, operation: str
    ) -> Mapping[str, object]:
        details = target.config.get("capability_details", {})
        if not isinstance(details, dict):
            raise ConfigurationError(
                f"{target.name}.capability_details must be an object"
            )
        operation_details = details.get(operation, {})
        if not isinstance(operation_details, dict):
            raise ConfigurationError(
                f"{target.name}.capability_details.{operation} must be an object"
            )
        return operation_details

    def _validate(self) -> None:
        if self.data.get("schema_version") != 1:
            raise ConfigurationError("unsupported or missing toolchain schema_version")
        for key in ("policy", "orchestration", "tools", "components", "bindings"):
            if not isinstance(self.data.get(key), dict):
                raise ConfigurationError(f"{key} must be an object")
        policy = self.data["policy"]
        assert isinstance(policy, dict)
        registry = policy.get("operation_registry")
        profiles = policy.get("profiles")
        aggregate_profiles = policy.get("aggregate_profiles")
        if not isinstance(registry, dict) or not registry:
            raise ConfigurationError("policy.operation_registry must be an object")
        if not isinstance(profiles, dict) or set(profiles) != set(PROFILE_NAMES):
            raise ConfigurationError(
                "policy.profiles must declare local, pull-request, full, and release"
            )
        if (
            not isinstance(aggregate_profiles, dict)
            or set(aggregate_profiles) != set(AGGREGATE_OPERATIONS)
            or any(
                aggregate_profiles[name] not in PROFILE_NAMES
                for name in AGGREGATE_OPERATIONS
            )
        ):
            raise ConfigurationError(
                "policy.aggregate_profiles must map check and certify to known profiles"
            )
        if any(operation not in registry for operation in QUALITY_OPERATIONS):
            raise ConfigurationError(
                "policy.operation_registry must declare every quality operation"
            )
        repository_components: list[tuple[str, str]] = []
        for operation, definition in registry.items():
            if (
                not isinstance(operation, str)
                or re.fullmatch(r"[a-z][a-z0-9_]*", operation) is None
                or not isinstance(definition, dict)
            ):
                raise ConfigurationError(
                    "canonical operations require stable snake-case object identities"
                )
            kind = definition.get("kind")
            network = definition.get("network")
            if network not in ("offline", "network"):
                raise ConfigurationError(
                    f"canonical operation {operation} has invalid network policy"
                )
            if kind == "component":
                if (
                    definition.get("capability") != operation
                    or operation not in QUALITY_OPERATIONS
                ):
                    raise ConfigurationError(
                        f"component operation {operation} must reference its canonical capability"
                    )
                continue
            if kind != "repository":
                raise ConfigurationError(
                    f"canonical operation {operation} has unknown kind '{kind}'"
                )
            component = definition.get("component")
            command = definition.get("command")
            if not isinstance(component, str) or not component:
                raise ConfigurationError(
                    f"repository operation {operation} must declare a component"
                )
            repository_components.append((operation, component))
            if (
                not isinstance(command, list)
                or not command
                or not all(isinstance(item, str) and item for item in command)
            ):
                raise ConfigurationError(
                    f"repository operation {operation} must declare a command"
                )
            result_contract = definition.get("result_contract")
            result_operation_id = definition.get("result_operation_id")
            if result_contract is None:
                if result_operation_id is not None:
                    raise ConfigurationError(
                        f"repository operation {operation} declares a result operation without a contract"
                    )
            elif result_contract not in STRUCTURED_RESULT_CONTRACT_PREFIXES:
                raise ConfigurationError(
                    f"repository operation {operation} has unsupported result contract"
                )
            else:
                expected_prefix = STRUCTURED_RESULT_CONTRACT_PREFIXES[result_contract]
                if (
                    not isinstance(result_operation_id, str)
                    or not result_operation_id.startswith(expected_prefix)
                    or "--json" not in command
                ):
                    raise ConfigurationError(
                        f"repository operation {operation} structured result requires a matching operation ID and JSON command"
                    )
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
        enforced_capabilities: list[tuple[str, str]] = []
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
                capability_details = raw.get("capability_details", {})
                if not isinstance(capability_details, dict):
                    raise ConfigurationError(
                        f"{name}.capability_details must be an object"
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
                    if status in EXECUTABLE_CAPABILITY_STATUSES:
                        self.resolve_command(target, operation)
                    if status == "enforced":
                        enforced_capabilities.append((name, operation))
                    if status in ("not_yet_enforceable", "unavailable"):
                        details = capability_details.get(operation)
                        if not isinstance(details, dict):
                            raise ConfigurationError(
                                f"{name}.{operation} {status} requires capability_details"
                            )
                        reason = details.get("reason")
                        if not isinstance(reason, str) or not reason:
                            raise ConfigurationError(
                                f"{name}.{operation} {status} requires a reason"
                            )
                        if status == "not_yet_enforceable":
                            retirement = details.get("retirement_condition")
                            if not isinstance(retirement, str) or not retirement:
                                raise ConfigurationError(
                                    f"{name}.{operation} not_yet_enforceable requires a retirement condition"
                                )
        operation_defaults = policy.get("operation_defaults", {})
        for operation, component in repository_components:
            if component not in target_names:
                raise ConfigurationError(
                    f"repository operation {operation} references unknown component "
                    f"'{component}'"
                )
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

        profile_memberships: dict[str, list[Mapping[str, object]]] = {}
        for profile_name in PROFILE_NAMES:
            definition = profiles[profile_name]
            if not isinstance(definition, dict):
                raise ConfigurationError(
                    f"policy.profiles.{profile_name} must be an object"
                )
            version = definition.get("definition_version")
            purpose = definition.get("purpose")
            network_policy = definition.get("network_policy")
            members = definition.get("operations")
            if (
                not isinstance(version, str)
                or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None
            ):
                raise ConfigurationError(
                    f"profile {profile_name} requires a semantic definition version"
                )
            if not isinstance(purpose, str) or not purpose:
                raise ConfigurationError(f"profile {profile_name} requires a purpose")
            if network_policy not in ("offline", "allowed"):
                raise ConfigurationError(
                    f"profile {profile_name} has invalid network policy"
                )
            if not isinstance(members, list) or not members:
                raise ConfigurationError(
                    f"profile {profile_name} must declare ordered operations"
                )
            seen: set[str] = set()
            validated: list[Mapping[str, object]] = []
            for member in members:
                if not isinstance(member, dict):
                    raise ConfigurationError(
                        f"profile {profile_name} members must be objects"
                    )
                operation = member.get("operation")
                if not isinstance(operation, str) or operation not in registry:
                    raise ConfigurationError(
                        f"profile {profile_name} references an unknown operation"
                    )
                if operation in seen:
                    raise ConfigurationError(
                        f"profile {profile_name} repeats operation '{operation}'"
                    )
                seen.add(operation)
                canonical = registry[operation]
                assert isinstance(canonical, dict)
                if network_policy == "offline" and canonical["network"] == "network":
                    raise ConfigurationError(
                        f"profile {profile_name} forbids network operation '{operation}'"
                    )
                if canonical["kind"] == "repository":
                    if set(member) != {"operation"}:
                        raise ConfigurationError(
                            f"repository operation {operation} cannot declare profile targets"
                        )
                else:
                    targets = member.get("targets")
                    if (
                        set(member) != {"operation", "targets"}
                        or not isinstance(targets, list)
                        or not targets
                        or not all(isinstance(target, str) for target in targets)
                    ):
                        raise ConfigurationError(
                            f"component operation {operation} requires ordered targets"
                        )
                    if len(set(targets)) != len(targets):
                        raise ConfigurationError(
                            f"profile {profile_name} repeats a target for {operation}"
                        )
                    if any(target not in target_names for target in targets):
                        raise ConfigurationError(
                            f"profile {profile_name} {operation} contains an unknown target"
                        )
                validated.append(member)
            profile_memberships[profile_name] = validated

        def require_profile_superset(base: str, expanded: str) -> None:
            expanded_members = profile_memberships[expanded]
            positions = {
                member["operation"]: index
                for index, member in enumerate(expanded_members)
            }
            previous = -1
            for member in profile_memberships[base]:
                operation = member["operation"]
                assert isinstance(operation, str)
                position = positions.get(operation)
                if position is None or position <= previous:
                    raise ConfigurationError(
                        f"profile {expanded} must preserve ordered {base} guarantees"
                    )
                previous = position
                canonical = registry[operation]
                assert isinstance(canonical, dict)
                if canonical["kind"] == "component":
                    base_targets = member["targets"]
                    expanded_targets = expanded_members[position]["targets"]
                    assert isinstance(base_targets, list)
                    assert isinstance(expanded_targets, list)
                    if not set(base_targets).issubset(expanded_targets):
                        raise ConfigurationError(
                            f"profile {expanded} must preserve {base} targets for {operation}"
                        )

        require_profile_superset("local", "pull-request")
        require_profile_superset("pull-request", "full")
        require_profile_superset("full", "release")

        pull_request = {
            member["operation"]: member
            for member in profile_memberships["pull-request"]
        }
        for target_name, operation in enforced_capabilities:
            member = pull_request.get(operation)
            targets = member.get("targets") if member is not None else None
            if not isinstance(targets, list) or target_name not in targets:
                raise ConfigurationError(
                    f"{target_name}.{operation} is enforced but omitted from pull-request"
                )


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
        arguments = list(command)
        if arguments:
            resolved = shutil.which(arguments[0])
            if resolved is not None:
                arguments[0] = str(Path(resolved).resolve())
        try:
            completed = subprocess.run(
                arguments,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            return Execution(127, stderr=str(exc))
        return Execution(completed.returncode, completed.stdout, completed.stderr)


Executor = Callable[[Target, str, list[str]], Execution]
HardgateExecutor = Callable[[str, list[str]], Execution]


def host_command(command: Sequence[str]) -> list[str]:
    arguments = list(command)
    if sys.platform == "win32" and arguments and arguments[0] == "python3":
        arguments[0] = sys.executable
    return arguments


def windows_command(command: Sequence[str], cwd: Path) -> list[str]:
    """Resolve a declared command to an executable Windows can launch directly."""

    arguments = host_command(command)
    if sys.platform != "win32" or not arguments:
        return arguments

    declared = Path(arguments[0])
    if declared.is_absolute():
        candidate = declared
    elif declared.parent != Path("."):
        candidate = (cwd / declared).resolve()
    else:
        resolved = shutil.which(arguments[0])
        if resolved is None:
            return arguments
        candidate = Path(resolved).resolve()

    candidates = [candidate]
    if candidate.suffix == "":
        candidates = [
            candidate.with_suffix(suffix) for suffix in (".cmd", ".exe", ".bat")
        ]
        candidates.append(candidate)
    for resolved in candidates:
        if resolved.is_file():
            arguments[0] = str(resolved)
            break
    return arguments


class QualityRunner:
    """Dispatch configured commands and preserve their exact status."""

    def __init__(
        self,
        toolchain: Toolchain,
        executor: Executor | None = None,
        inspector: EnvironmentInspector | None = None,
        hardgate_executor: HardgateExecutor | None = None,
    ) -> None:
        self.toolchain = toolchain
        self.executor = executor or self._execute
        self.inspector = inspector or EnvironmentInspector(toolchain)
        self.inspect_leaf_environment = inspector is not None or executor is None
        self.hardgate_executor = hardgate_executor or self._execute_hardgate

    def run_leaf(self, operation: str, target: Target) -> OperationResult:
        capability = self.toolchain.capability(target, operation)
        if capability not in EXECUTABLE_CAPABILITY_STATUSES:
            details = self.toolchain.capability_details(target, operation)
            reason = details.get("reason")
            if not isinstance(reason, str):
                wording = capability.replace("_", " ")
                reason = f"{operation.replace('_', ' ')} is {wording} for {target.name}"
            return OperationResult(
                operation=operation,
                component=target.name,
                status=capability,
                command=None,
                exit_code=None,
                reason=reason,
                capability=capability,
            )
        resolved, command = self.toolchain.resolve_command(target, operation)
        formatters = self.toolchain.formatter_names(target, operation)
        environment = (
            self.inspector.check_target(target, operation)
            if self.inspect_leaf_environment
            else []
        )
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
                capability=capability,
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
            capability=capability,
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
        return self.run_profile(self.toolchain.aggregate_profile(name), requested)

    def run_profile(self, name: str, requested: str | None) -> list[OperationResult]:
        profile = self.toolchain.profile(name)
        members = profile["operations"]
        assert isinstance(members, list)
        results: list[OperationResult] = []
        for member in members:
            assert isinstance(member, dict)
            operation = member["operation"]
            assert isinstance(operation, str)
            canonical = self.toolchain.operation(operation)
            if canonical["kind"] == "repository":
                results.append(self.run_repository_operation(operation, canonical))
                continue
            configured_targets = member["targets"]
            assert isinstance(configured_targets, list)
            targets = self.toolchain.select(
                requested, configured_targets if requested is None else None
            )
            results.extend(self.run_leaf(operation, target) for target in targets)
        return results

    def run_repository_operation(
        self, operation: str, definition: Mapping[str, object]
    ) -> OperationResult:
        component = definition["component"]
        command = definition["command"]
        assert isinstance(component, str)
        assert isinstance(command, list)
        assert all(isinstance(item, str) for item in command)
        invocation = list(command)
        execution = self.hardgate_executor(operation, invocation)
        structured_result: dict[str, object] | None = None
        result_contract = definition.get("result_contract")
        if result_contract in STRUCTURED_RESULT_CONTRACT_PREFIXES:
            expected_operation = definition["result_operation_id"]
            assert isinstance(expected_operation, str)
            try:
                parsed = json.loads(execution.stdout)
            except json.JSONDecodeError as exc:
                status = "incomplete"
                reason = f"structured operation result is malformed: {exc}"
            else:
                if not isinstance(parsed, dict):
                    status = "incomplete"
                    reason = "structured operation result must be an object"
                else:
                    parsed_status = parsed.get("status")
                    parsed_operation = parsed.get("operation_id")
                    expected_exit = STRUCTURED_RESULT_EXIT_CODES.get(str(parsed_status))
                    if (
                        parsed_status not in STRUCTURED_RESULT_STATUSES
                        or parsed_operation != expected_operation
                        or execution.returncode != expected_exit
                    ):
                        status = "incomplete"
                        reason = (
                            "structured operation result identity, status, and exit code "
                            "must agree"
                        )
                    else:
                        status = str(parsed_status)
                        reason = (
                            None
                            if status in ("passed", "waived")
                            else f"structured operation reported {status}"
                        )
                        structured_result = parsed
        else:
            status = "passed" if execution.returncode == 0 else "failed"
            reason = (
                None
                if execution.returncode == 0
                else f"command exited with status {execution.returncode}"
            )
        return OperationResult(
            operation=operation,
            component=component,
            status=status,
            command=invocation,
            exit_code=execution.returncode,
            reason=reason,
            structured_result=structured_result,
            stdout=execution.stdout,
            stderr=execution.stderr,
        )

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
                    capability=None,
                    environment=environment,
                )
            )
        return results

    def _execute(self, target: Target, resolved: str, command: list[str]) -> Execution:
        if target.kind == "binding" and resolved not in ("format", "format_check"):
            if sys.platform == "win32":
                cwd = self.toolchain.root / str(target.config["path"])
                invocation = windows_command(command, cwd)
            else:
                invocation = [
                    str(self.toolchain.root / "strling"),
                    "_run-configured",
                    resolved,
                    target.name,
                ]
                cwd = self.toolchain.root
        else:
            cwd = self.toolchain.root / str(target.config["path"])
            invocation = (
                windows_command(command, cwd)
                if sys.platform == "win32"
                else host_command(command)
            )
        try:
            completed = subprocess.run(
                invocation,
                cwd=cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            return Execution(127, stderr=str(exc))
        return Execution(completed.returncode, completed.stdout, completed.stderr)

    def _execute_hardgate(self, _operation: str, command: list[str]) -> Execution:
        invocation = host_command(command)
        try:
            completed = subprocess.run(
                invocation,
                cwd=self.toolchain.root,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            return Execution(127, stderr=str(exc))
        return Execution(completed.returncode, completed.stdout, completed.stderr)


def _parse_cli(
    argv: Sequence[str],
) -> tuple[str, str | None, bool, str | None, str | None]:
    args = list(argv)
    json_output = False
    if "--json" in args:
        args.remove("--json")
        json_output = True

    artifact_output: str | None = None
    artifact_options = [
        index for index, argument in enumerate(args) if argument == "--artifact"
    ]
    if len(artifact_options) > 1:
        raise ConfigurationError("--artifact may be specified only once")
    if artifact_options:
        index = artifact_options[0]
        if index + 1 >= len(args) or args[index + 1].startswith("-"):
            raise ConfigurationError("--artifact requires an output path")
        artifact_output = args[index + 1]
        del args[index : index + 2]

    if not args or args[0] in ("help", "-h", "--help"):
        return "help", None, json_output, None, artifact_output
    operation = args.pop(0)
    profile_name: str | None = None
    if operation == PROFILE_OPERATION:
        if not args or args[0].startswith("-"):
            raise ConfigurationError("profile requires a profile identity")
        profile_name = args.pop(0)
    if operation == "format" and "--check" in args:
        args.remove("--check")
        operation = "format_check"
    if operation not in QUALITY_OPERATIONS + AGGREGATE_OPERATIONS + (
        ENVIRONMENT_OPERATION,
        PROFILE_OPERATION,
    ):
        raise ConfigurationError(f"unknown quality operation '{operation}'")
    if artifact_output is not None and operation not in (
        *AGGREGATE_OPERATIONS,
        PROFILE_OPERATION,
    ):
        raise ConfigurationError("--artifact is supported only for profile executions")
    if any(argument.startswith("-") for argument in args):
        option = next(argument for argument in args if argument.startswith("-"))
        raise ConfigurationError(f"unknown option '{option}'")
    if len(args) > 1:
        raise ConfigurationError("at most one component may be selected")
    return (
        operation,
        args[0] if args else None,
        json_output,
        profile_name,
        artifact_output,
    )


def _overall_exit(results: Iterable[OperationResult], single: bool) -> int:
    failures = [
        result
        for result in results
        if result.status in ("failed", "unavailable", "incomplete")
    ]
    if not failures:
        return 0
    if single and failures[0].exit_code:
        return failures[0].exit_code
    return 1


def _overall_status(results: Iterable[OperationResult]) -> str:
    statuses = {result.status for result in results}
    for status in ("failed", "unavailable", "incomplete", "waived"):
        if status in statuses:
            return status
    return "passed"


def _profile_exit(results: Iterable[OperationResult]) -> int:
    return aggregate_profile_exit(result.status for result in results)


def _profile_status(results: Iterable[OperationResult]) -> str:
    return aggregate_profile_status(result.status for result in results)


def _render_structured_result(result: OperationResult) -> None:
    assert result.structured_result is not None
    summary = result.structured_result.get("summary")
    if isinstance(summary, dict):
        details = ", ".join(
            f"{status}={summary.get(status, 0)}"
            for status in STRUCTURED_RESULT_STATUSES
        )
        print(f"  structured summary: {details}")
    checks = result.structured_result.get("checks")
    if not isinstance(checks, list):
        return
    for check in checks:
        if not isinstance(check, dict) or check.get("status") == "passed":
            continue
        print(f"  [{check.get('status')}] {check.get('check_id')}")
        unavailable_reason = check.get("unavailable_reason")
        if isinstance(unavailable_reason, str):
            print(f"    unavailable: {unavailable_reason}")
        findings = check.get("findings")
        if not isinstance(findings, list):
            continue
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            identity = ":".join(
                str(finding[field])
                for field in ("package", "version", "advisory", "license")
                if field in finding
            )
            identity_suffix = f" ({identity})" if identity else ""
            waiver = finding.get("waiver_id")
            waiver_suffix = f" [{waiver}]" if waiver else ""
            print(
                f"    {finding.get('code')}{identity_suffix}{waiver_suffix}: "
                f"{finding.get('message')}"
            )


def _render_human(
    operation: str,
    results: Sequence[OperationResult],
    incomplete: Sequence[Mapping[str, str]],
) -> None:
    for result in results:
        if result.structured_result is not None:
            _render_structured_result(result)
        elif result.stdout:
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
    if operation in (*AGGREGATE_OPERATIONS, PROFILE_OPERATION) and incomplete:
        print("Incomplete capabilities:")
        grouped: dict[str, list[str]] = {}
        for item in incomplete:
            grouped.setdefault(item["component"], []).append(
                f"{item['operation']} [{item['status']}]"
            )
        for component, operations in grouped.items():
            print(f"  {component}: {', '.join(operations)}")


def _print_help() -> None:
    print("Usage: ./strling <quality-command> [component|all] [--json]")
    print("       ./strling format [--check] [component|all] [--json]")
    print(
        "       ./strling profile <local|pull-request|full|release> "
        "[component|all] [--json] [--artifact PATH]"
    )
    print("")
    print(
        "Quality commands: format, hygiene, lint, typecheck, build, test, "
        "check, certify, profile, environment"
    )


def main(argv: Sequence[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        (
            operation,
            requested,
            json_output,
            requested_profile,
            artifact_output,
        ) = _parse_cli(argv)
        if operation == "help":
            _print_help()
            return 0
        root = Path(__file__).resolve().parent.parent
        toolchain = Toolchain.load(root / "toolchain.json")
        runner = QualityRunner(toolchain)
        selected_profile: str | None = None
        if operation in AGGREGATE_OPERATIONS:
            selected_profile = toolchain.aggregate_profile(operation)
            results = runner.run_profile(selected_profile, requested)
        elif operation == PROFILE_OPERATION:
            assert requested_profile is not None
            selected_profile = requested_profile
            results = runner.run_profile(selected_profile, requested)
        elif operation == ENVIRONMENT_OPERATION:
            results = runner.run_environment(requested)
        else:
            results = runner.run_operation(operation, requested)

        if selected_profile is not None:
            exit_code = _profile_exit(results)
            status = _profile_status(results)
            artifact = build_certification_artifact(
                root=root,
                profile_id=selected_profile,
                profile_definition=toolchain.profile(selected_profile),
                requested_component=requested,
                results=[result.as_dict() for result in results],
                aggregate_status=status,
                exit_code=exit_code,
            )
            if artifact_output is not None:
                write_certification_artifact(Path(artifact_output), artifact)
            if json_output:
                print(json.dumps(artifact, sort_keys=True))
            else:
                print(render_certification_summary(artifact))
            return exit_code

        exit_code = _overall_exit(results, len(results) == 1)
        status = _overall_status(results)
        if json_output:
            payload: dict[str, object] = {
                "operation": operation,
                "status": status,
                "exit_code": exit_code,
                "results": [result.as_dict() for result in results],
                "incomplete_capabilities": [],
            }
            print(json.dumps(payload, sort_keys=True))
        else:
            _render_human(operation, results, [])
        return exit_code
    except (CertificationError, ConfigurationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
