#!/usr/bin/env python3
"""Validate contained-task scope, change intent, and architecture fitness."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

try:
    from architecture_fitness import evaluate_extended_rule
except ModuleNotFoundError:  # pragma: no cover - import path differs under tests
    from tooling.architecture_fitness import evaluate_extended_rule

try:
    from generated_artifacts import (
        RegistryError,
        load_registry,
        validate_artifact_relationships,
    )
except ModuleNotFoundError:  # pragma: no cover - import path differs under tests
    from tooling.generated_artifacts import (
        RegistryError,
        load_registry,
        validate_artifact_relationships,
    )


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTROL = ROOT / "governance/change-control.json"


class GovernanceError(ValueError):
    """Raised when governance inputs or Git state cannot be trusted."""


@dataclass(frozen=True)
class Change:
    status: str
    old_path: str | None = None
    new_path: str | None = None

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(
            path for path in (self.old_path, self.new_path) if path is not None
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "old_path": self.old_path,
            "new_path": self.new_path,
        }


@dataclass
class CheckResult:
    check: str
    status: str
    findings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "check": self.check,
            "status": self.status,
            "findings": self.findings,
        }


@dataclass
class RuleResult:
    rule: str
    status: str
    findings: list[str] = field(default_factory=list)
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "status": self.status,
            "findings": self.findings,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class Exemption:
    identifier: str
    rule: str
    paths: tuple[str, ...]


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceError(f"cannot read {path}: {exc}") from exc


def load_yaml(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise GovernanceError(f"cannot read {path}: {exc}") from exc


def validate_instance(instance: object, schema: object, label: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
    except (SchemaError, ValidationError) as exc:
        raise GovernanceError(f"malformed {label}: {exc.message}") from exc


def normalize_repository_path(path: str, *, pattern: bool = False) -> str:
    if not path or path.startswith("/") or "\\" in path:
        raise GovernanceError(f"invalid repository path: {path!r}")
    pieces = path.split("/")
    if any(piece in ("", ".", "..") for piece in pieces):
        raise GovernanceError(f"invalid repository path: {path!r}")
    if not pattern and any(character in path for character in "*?[]"):
        raise GovernanceError(f"concrete path contains glob syntax: {path!r}")
    return path


def compile_path_pattern(pattern: str) -> re.Pattern[str]:
    pattern = normalize_repository_path(pattern, pattern=True)
    expression = ["^"]
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                index += 2
                if index < len(pattern) and pattern[index] == "/":
                    expression.append("(?:.*/)?")
                    index += 1
                else:
                    expression.append(".*")
                continue
            expression.append("[^/]*")
        elif character == "?":
            expression.append("[^/]")
        elif character == "[":
            closing = pattern.find("]", index + 1)
            if closing == -1:
                raise GovernanceError(f"unclosed character class in {pattern!r}")
            content = pattern[index + 1 : closing]
            if not content or not re.fullmatch(r"[!A-Za-z0-9_-]+", content):
                raise GovernanceError(f"unsupported character class in {pattern!r}")
            if content.startswith("!"):
                content = "^" + content[1:]
            expression.append("[" + content + "]")
            index = closing
        else:
            expression.append(re.escape(character))
        index += 1
    expression.append("$")
    return re.compile("".join(expression))


def path_matches(path: str, pattern: str) -> bool:
    normalized = normalize_repository_path(path)
    return compile_path_pattern(pattern).fullmatch(normalized) is not None


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(path_matches(path, pattern) for pattern in patterns)


def parse_name_status(data: bytes) -> list[Change]:
    fields = data.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    changes: list[Change] = []
    index = 0
    while index < len(fields):
        status = fields[index].decode("ascii")
        index += 1
        if status.startswith(("R", "C")):
            if index + 1 >= len(fields):
                raise GovernanceError("truncated Git rename/copy record")
            old_path = fields[index].decode("utf-8", errors="surrogateescape")
            new_path = fields[index + 1].decode("utf-8", errors="surrogateescape")
            index += 2
            changes.append(Change(status, old_path, new_path))
        else:
            if index >= len(fields):
                raise GovernanceError("truncated Git change record")
            path = fields[index].decode("utf-8", errors="surrogateescape")
            index += 1
            if status.startswith("D"):
                changes.append(Change(status, path, None))
            else:
                changes.append(Change(status, None, path))
    for change in changes:
        for path in change.paths:
            normalize_repository_path(path)
    return changes


def git_output(root: Path, arguments: Sequence[str]) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise GovernanceError(
            f"git {' '.join(arguments)} failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout


def collect_changes(root: Path, base: str, head: str) -> list[Change]:
    git_output(root, ["cat-file", "-e", f"{base}^{{commit}}"])
    comparison_head = "HEAD" if head == "working-tree" else head
    git_output(root, ["cat-file", "-e", f"{comparison_head}^{{commit}}"])
    git_output(root, ["merge-base", "--is-ancestor", base, comparison_head])

    arguments = ["diff", "--name-status", "-z", "--find-renames", base]
    if head != "working-tree":
        arguments.append(head)
    data = git_output(root, arguments)
    changes = parse_name_status(data)
    if head == "working-tree":
        untracked = git_output(
            root, ["ls-files", "--others", "--exclude-standard", "-z"]
        )
        known = {path for change in changes for path in change.paths}
        for raw_path in untracked.split(b"\0"):
            if not raw_path:
                continue
            path = raw_path.decode("utf-8", errors="surrogateescape")
            normalize_repository_path(path)
            if path not in known:
                changes.append(Change("A", None, path))
    return changes


def load_exemptions(root: Path, identifiers: Sequence[str]) -> list[Exemption]:
    if not identifiers:
        return []
    schema = load_json(root / "governance/schemas/waiver.schema.json")
    records: dict[str, Mapping[str, object]] = {}
    for path in (root / "governance/waivers").glob("*.yaml"):
        record = load_yaml(path)
        validate_instance(record, schema, f"waiver {path}")
        assert isinstance(record, dict)
        records[str(record["waiver_id"])] = record

    exemptions: list[Exemption] = []
    for identifier in identifiers:
        record = records.get(identifier)
        if record is None:
            raise GovernanceError(f"bounded exemption {identifier} was not found")
        if record["status"] != "accepted":
            raise GovernanceError(f"bounded exemption {identifier} is not accepted")
        retirement = record["retirement"]
        assert isinstance(retirement, dict)
        expires = retirement.get("expires_on")
        if isinstance(expires, str) and date.fromisoformat(expires) < date.today():
            raise GovernanceError(f"bounded exemption {identifier} has expired")
        scope = record["scope"]
        assert isinstance(scope, dict)
        paths = scope["paths"]
        assert isinstance(paths, list)
        exemptions.append(
            Exemption(
                identifier,
                str(record["rule"]),
                tuple(str(path) for path in paths),
            )
        )
    return exemptions


def is_exempt(exemptions: Sequence[Exemption], rule: str, path: str | None) -> bool:
    return any(
        exemption.rule == rule
        and path is not None
        and matches_any(path, exemption.paths)
        for exemption in exemptions
    )


def validate_scope(
    task: Mapping[str, object],
    changes: Sequence[Change],
    exemptions: Sequence[Exemption] = (),
) -> CheckResult:
    scope = task["scope"]
    assert isinstance(scope, dict)
    allowed = scope["allowed_paths"]
    forbidden = scope["forbidden_paths"]
    expected = scope["expected_files"]
    assert isinstance(allowed, list)
    assert isinstance(forbidden, list)
    assert isinstance(expected, list)
    findings: list[str] = []
    changed_paths = [path for change in changes for path in change.paths]

    for change in changes:
        for path in change.paths:
            if matches_any(path, forbidden) and not is_exempt(
                exemptions, "scope-forbidden-path", path
            ):
                findings.append(f"{change.status} {path}: forbidden by the task scope")
            elif not matches_any(path, allowed) and not is_exempt(
                exemptions, "scope-undeclared-path", path
            ):
                findings.append(f"{change.status} {path}: outside every allowed path")
    for expected_pattern in expected:
        if not any(path_matches(path, expected_pattern) for path in changed_paths):
            findings.append(
                f"expected file or pattern is absent from the diff: {expected_pattern}"
            )
    return CheckResult("scope", "failed" if findings else "passed", findings)


def declaration_level(task: Mapping[str, object], name: str) -> str:
    declarations = task["change_classification"]
    assert isinstance(declarations, dict)
    declaration = declarations[name]
    assert isinstance(declaration, dict)
    return str(declaration["level"])


def artifact_ids_for_path(registry: Mapping[str, object], path: str) -> list[str]:
    artifacts = registry["artifacts"]
    assert isinstance(artifacts, list)
    identifiers = []
    for artifact in artifacts:
        assert isinstance(artifact, dict)
        outputs = artifact["outputs"]
        assert isinstance(outputs, list)
        if matches_any(path, outputs):
            identifiers.append(str(artifact["id"]))
    return identifiers


def hygiene_generated_patterns(root: Path) -> list[str]:
    policy = load_json(root / "governance/repository-hygiene.json")
    assert isinstance(policy, dict)
    groups = policy.get("generated_paths", [])
    assert isinstance(groups, list)
    patterns: list[str] = []
    for group in groups:
        assert isinstance(group, dict)
        values = group.get("paths", [])
        assert isinstance(values, list)
        patterns.extend(str(value) for value in values)
    return patterns


def validate_declarations(
    task: Mapping[str, object],
    changes: Sequence[Change],
    control: Mapping[str, object],
    artifact_registry: Mapping[str, object],
    generated_patterns: Sequence[str],
) -> CheckResult:
    findings: list[str] = []
    changed_paths = [path for change in changes for path in change.paths]
    evidence_rules = control["path_evidence"]
    assert isinstance(evidence_rules, list)
    for evidence in evidence_rules:
        assert isinstance(evidence, dict)
        classification = str(evidence["classification"])
        paths = evidence["paths"]
        assert isinstance(paths, list)
        matched = sorted(path for path in changed_paths if matches_any(path, paths))
        if matched and declaration_level(task, classification) == "none":
            findings.append(
                f"{classification} is undeclared for: " + ", ".join(matched)
            )

    generated: dict[str, list[str]] = {}
    for path in changed_paths:
        identifiers = artifact_ids_for_path(artifact_registry, path)
        if identifiers:
            generated[path] = identifiers
        elif matches_any(path, generated_patterns):
            findings.append(f"unregistered generated output changed: {path}")

    scope = task["scope"]
    assert isinstance(scope, dict)
    permitted = scope["permitted_generated_changes"]
    expected_generated = scope["expected_generated_outputs"]
    assert isinstance(permitted, list)
    assert isinstance(expected_generated, list)
    changed_generated_ids = {
        identifier for identifiers in generated.values() for identifier in identifiers
    }
    for identifier in expected_generated:
        if identifier not in permitted:
            findings.append(
                f"expected generated artifact {identifier} is not permitted"
            )
        if identifier not in changed_generated_ids:
            findings.append(f"expected generated artifact did not change: {identifier}")
    if generated:
        if declaration_level(task, "generated_output_change") == "none":
            findings.append(
                "generated_output_change is undeclared for: "
                + ", ".join(sorted(generated))
            )
        for path, identifiers in sorted(generated.items()):
            for identifier in identifiers:
                if identifier not in permitted:
                    findings.append(
                        f"{path}: generated artifact {identifier} is not permitted"
                    )
    elif declaration_level(task, "generated_output_change") != "none":
        findings.append(
            "generated_output_change is declared but no registered output changed"
        )

    classifications = task["change_classification"]
    assert isinstance(classifications, dict)
    documentation_only = classifications["documentation_only"]
    internal_implementation = classifications["internal_implementation"]
    assert isinstance(documentation_only, bool)
    assert isinstance(internal_implementation, bool)
    documentation_paths = control["documentation_paths"]
    internal_paths = control["internal_implementation_paths"]
    assert isinstance(documentation_paths, list)
    assert isinstance(internal_paths, list)
    non_documentation = [
        path for path in changed_paths if not matches_any(path, documentation_paths)
    ]
    if documentation_only and non_documentation:
        findings.append(
            "documentation_only conflicts with non-documentation paths: "
            + ", ".join(sorted(non_documentation))
        )
    if documentation_only and internal_implementation:
        findings.append(
            "documentation_only and internal_implementation cannot both be true"
        )
    internal_changes = [
        path for path in changed_paths if matches_any(path, internal_paths)
    ]
    if internal_changes and not internal_implementation:
        findings.append(
            "internal_implementation is undeclared for: "
            + ", ".join(sorted(internal_changes))
        )
    return CheckResult(
        "change-declarations", "failed" if findings else "passed", findings
    )


def python_dependencies(path: Path) -> tuple[set[str], list[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return set(), [f"{path}: cannot inspect Python imports: {exc}"]
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dependencies.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            dependencies.add(node.module)
    return dependencies, []


def under_root(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def rule_result(
    rule: Mapping[str, object],
    *,
    root: Path,
    task: Mapping[str, object],
    changes: Sequence[Change],
    control: Mapping[str, object],
    artifact_registry: Mapping[str, object],
    exemptions: Sequence[Exemption],
) -> RuleResult:
    identifier = str(rule["id"])
    status = str(rule["status"])
    if status == "future":
        return RuleResult(
            identifier,
            status,
            reason=str(rule.get("rationale", "")),
        )

    kind = str(rule["kind"])
    configuration = rule["configuration"]
    assert isinstance(configuration, dict)
    findings: list[tuple[str, str | None]] = []
    if kind == "forbidden-dependency":
        source_patterns = configuration["sources"]
        forbidden = configuration["forbidden_dependencies"]
        assert isinstance(source_patterns, list)
        assert isinstance(forbidden, list)
        source_paths = [
            path
            for path in root.rglob("*.py")
            if matches_any(str(path.relative_to(root)), source_patterns)
        ]
        for source_path in source_paths:
            relative = str(source_path.relative_to(root))
            dependencies, errors = python_dependencies(source_path)
            findings.extend((error, relative) for error in errors)
            for dependency in sorted(dependencies):
                if any(
                    dependency == prefix
                    or dependency.startswith(prefix.replace("/", ".") + ".")
                    for prefix in forbidden
                ):
                    findings.append(
                        (
                            f"{relative}: forbidden dependency {dependency}",
                            relative,
                        )
                    )
    elif kind == "generated-input-cycle":
        try:
            validate_artifact_relationships(artifact_registry, root)
        except RegistryError as exc:
            findings.append((str(exc), None))
    elif kind == "task-record-placement":
        allowed_roots = configuration["allowed_record_roots"]
        assert isinstance(allowed_roots, list)
        candidates = {str(control["active_task"])}
        for change in changes:
            for path in change.paths:
                if path.endswith((".yaml", ".yml")) and (root / path).is_file():
                    data = load_yaml(root / path)
                    if isinstance(data, dict) and {
                        "objective",
                        "scope",
                        "change_classification",
                    }.issubset(data):
                        candidates.add(path)
        for candidate in sorted(candidates):
            if not any(under_root(candidate, allowed) for allowed in allowed_roots):
                findings.append(
                    (
                        f"{candidate}: task record is outside designated roots",
                        candidate,
                    )
                )
    elif kind == "new-top-level-directory":
        allowed = configuration["allowed_top_level_directories"]
        assert isinstance(allowed, list)
        architecture_declared = declaration_level(task, "architecture_change") != "none"
        for change in changes:
            if not change.status.startswith(("A", "R", "C")):
                continue
            path = change.new_path
            if path is None or "/" not in path:
                continue
            top_level = path.split("/", 1)[0]
            if top_level not in allowed and not architecture_declared:
                findings.append(
                    (
                        f"{path}: new top-level directory {top_level} "
                        "requires architecture_change",
                        path,
                    )
                )
    else:
        extended = evaluate_extended_rule(
            kind,
            root=root,
            configuration=configuration,
            changes=changes,
            artifact_registry=artifact_registry,
            matches_any=matches_any,
            architecture_declared=(
                declaration_level(task, "architecture_change") != "none"
            ),
        )
        if extended is None:
            findings.append((f"unsupported enforced rule kind: {kind}", None))
        else:
            findings.extend(extended)

    active_findings = [
        message
        for message, path in findings
        if not is_exempt(exemptions, identifier, path)
    ]
    if status == "transitional":
        return RuleResult(
            identifier,
            "transitional",
            active_findings,
            reason=str(rule.get("rationale", "")),
        )
    return RuleResult(
        identifier,
        "failed" if active_findings else "passed",
        active_findings,
    )


def evaluate_architecture(
    rules: Mapping[str, object],
    *,
    root: Path,
    task: Mapping[str, object],
    changes: Sequence[Change],
    control: Mapping[str, object],
    artifact_registry: Mapping[str, object],
    exemptions: Sequence[Exemption] = (),
) -> list[RuleResult]:
    configured_rules = rules["rules"]
    assert isinstance(configured_rules, list)
    return [
        rule_result(
            rule,
            root=root,
            task=task,
            changes=changes,
            control=control,
            artifact_registry=artifact_registry,
            exemptions=exemptions,
        )
        for rule in configured_rules
        if isinstance(rule, dict)
    ]


def load_governance(
    root: Path, control_path: Path
) -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    control = load_json(control_path)
    change_schema = load_json(root / "governance/schemas/change-control.schema.json")
    validate_instance(control, change_schema, "change-control configuration")
    assert isinstance(control, dict)

    task_path = root / str(control["active_task"])
    task = load_yaml(task_path)
    task_schema = load_json(root / "governance/schemas/task-record.schema.json")
    validate_instance(task, task_schema, f"task record {task_path}")
    assert isinstance(task, dict)
    if task["record_version"] != "2.0.0":
        raise GovernanceError("the active task must use record_version 2.0.0")

    artifact_path = root / str(control["generated_artifact_registry"])
    artifact_registry = load_registry(
        artifact_path,
        root / "governance/schemas/generated-artifact-registry.schema.json",
    )

    architecture_path = root / str(control["architecture_rule_registry"])
    architecture_rules = load_json(architecture_path)
    architecture_schema = load_json(
        root / "governance/schemas/architecture-rules.schema.json"
    )
    validate_instance(
        architecture_rules,
        architecture_schema,
        "architecture rule registry",
    )
    assert isinstance(architecture_rules, dict)
    return control, task, artifact_registry, architecture_rules


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate task scope and architecture fitness."
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--control", type=Path, default=DEFAULT_CONTROL)
    return parser.parse_args(argv)


def render_human(
    task_path: str,
    base: str,
    head: str,
    changes: Sequence[Change],
    checks: Sequence[CheckResult],
    rules: Sequence[RuleResult],
) -> None:
    print(f"Task: {task_path}")
    print(f"Diff: {base}..{head} ({len(changes)} entries)")
    for check in checks:
        print(f"[{check.status}] {check.check}")
        for finding in check.findings:
            print(f"  - {finding}")
    for rule in rules:
        suffix = f" ({rule.reason})" if rule.reason else ""
        print(f"[{rule.status}] architecture {rule.rule}{suffix}")
        for finding in rule.findings:
            print(f"  - {finding}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        control, task, artifact_registry, architecture_rules = load_governance(
            ROOT, args.control.resolve()
        )
        scope = task["scope"]
        assert isinstance(scope, dict)
        diff = scope["diff"]
        assert isinstance(diff, dict)
        base = str(diff["base"])
        head = str(diff["head"])
        changes = collect_changes(ROOT, base, head)
        exemptions_raw = scope["bounded_exemptions"]
        assert isinstance(exemptions_raw, list)
        exemptions = load_exemptions(
            ROOT, [str(identifier) for identifier in exemptions_raw]
        )
        checks = [
            CheckResult("contracts", "passed"),
            validate_scope(task, changes, exemptions),
            validate_declarations(
                task,
                changes,
                control,
                artifact_registry,
                hygiene_generated_patterns(ROOT),
            ),
        ]
        rule_results = evaluate_architecture(
            architecture_rules,
            root=ROOT,
            task=task,
            changes=changes,
            control=control,
            artifact_registry=artifact_registry,
            exemptions=exemptions,
        )
    except (GovernanceError, RegistryError) as exc:
        if args.json_output:
            print(
                json.dumps(
                    {
                        "operation": "governance",
                        "status": "failed",
                        "exit_code": 2,
                        "error": str(exc),
                    },
                    sort_keys=True,
                )
            )
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    failed = any(check.status == "failed" for check in checks) or any(
        rule.status == "failed" for rule in rule_results
    )
    exit_code = 1 if failed else 0
    if args.json_output:
        print(
            json.dumps(
                {
                    "operation": "governance",
                    "status": "failed" if failed else "passed",
                    "exit_code": exit_code,
                    "task_record": control["active_task"],
                    "diff": {
                        "base": base,
                        "head": head,
                        "changes": [change.as_dict() for change in changes],
                    },
                    "checks": [check.as_dict() for check in checks],
                    "architecture_rules": [result.as_dict() for result in rule_results],
                },
                sort_keys=True,
            )
        )
    else:
        render_human(
            str(control["active_task"]),
            base,
            head,
            changes,
            checks,
            rule_results,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
