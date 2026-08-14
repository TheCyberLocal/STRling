#!/usr/bin/env python3
"""Validate base-relative public contract drift against exact task declarations."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


CLASSIFICATION_ORDER = {
    "unchanged": 0,
    "compatible": 1,
    "additive": 2,
    "breaking": 3,
}


class DeclarationError(ValueError):
    """Raised when declaration approval inputs cannot be trusted."""


@dataclass(frozen=True)
class DetectedChange:
    surface: str
    component: str
    declaration: str
    classification: str
    snapshot_path: str | None
    findings: tuple[str, ...] = field(default_factory=tuple)


Comparator = Callable[
    [Mapping[str, object], Mapping[str, object], str],
    object,
]


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeclarationError(f"cannot read {path}: {exc}") from exc


def validate_instance(instance: object, schema: object, label: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(instance)
    except (SchemaError, ValidationError) as exc:
        raise DeclarationError(f"malformed {label}: {exc.message}") from exc


def load_active_task(root: Path, control_path: Path) -> tuple[dict[str, object], str]:
    control = load_json(control_path)
    validate_instance(
        control,
        load_json(root / "governance/schemas/change-control.schema.json"),
        "change-control configuration",
    )
    assert isinstance(control, dict)
    task_path = root / str(control["active_task"])
    try:
        task = yaml.safe_load(task_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DeclarationError(f"cannot read active task {task_path}: {exc}") from exc
    validate_instance(
        task,
        load_json(root / "governance/schemas/task-record.schema.json"),
        f"task record {task_path}",
    )
    assert isinstance(task, dict)
    scope = task["scope"]
    assert isinstance(scope, dict)
    diff = scope["diff"]
    assert isinstance(diff, dict)
    return task, str(diff["base"])


def git_json_optional(root: Path, revision: str, path: str) -> object | None:
    commit = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if commit.returncode != 0:
        raise DeclarationError(f"task base is not a commit: {revision}")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}:{path}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if exists.returncode != 0:
        return None
    completed = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    if completed.returncode != 0:
        raise DeclarationError(
            f"cannot read {path} at {revision}: {completed.stderr.strip()}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DeclarationError(f"malformed JSON at {revision}:{path}: {exc}") from exc


def surface_map(registry: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    surfaces = registry.get("surfaces")
    if not isinstance(surfaces, list):
        raise DeclarationError("base public-surface registry has no surfaces array")
    result: dict[str, Mapping[str, object]] = {}
    for surface in surfaces:
        if not isinstance(surface, dict) or not isinstance(surface.get("id"), str):
            raise DeclarationError("base public-surface registry has a malformed entry")
        identifier = str(surface["id"])
        if identifier in result:
            raise DeclarationError(
                f"base public-surface registry repeats identifier {identifier}"
            )
        result[identifier] = surface
    return result


def declaration_for_surface(surface: Mapping[str, object]) -> str:
    return (
        "schema_change"
        if surface.get("kind") == "structured-schema"
        else "public_api_change"
    )


def detect_base_changes(
    *,
    root: Path,
    registry_path: Path,
    registry: Mapping[str, object],
    base: str,
    compare: Comparator,
) -> list[DetectedChange]:
    try:
        relative_registry = (
            registry_path.resolve().relative_to(root.resolve()).as_posix()
        )
    except ValueError as exc:
        raise DeclarationError(
            "public-surface registry must be inside the repository"
        ) from exc
    base_registry_raw = git_json_optional(root, base, relative_registry)
    if base_registry_raw is None:
        # This is the one-time bootstrap that establishes the first compatibility
        # baseline. Existing product structure is not misclassified as newly added API.
        return []
    if not isinstance(base_registry_raw, dict):
        raise DeclarationError("base public-surface registry must be an object")
    base_surfaces = surface_map(base_registry_raw)
    current_surfaces = surface_map(registry)
    detected: list[DetectedChange] = []

    for identifier, current in current_surfaces.items():
        if current.get("enforcement") != "enforced":
            continue
        previous = base_surfaces.get(identifier)
        if previous is None:
            detected.append(
                DetectedChange(
                    identifier,
                    str(current["component"]),
                    declaration_for_surface(current),
                    "additive",
                    str(current["snapshot_path"]),
                    ("new enforced public surface added to the registry",),
                )
            )
            continue
        if previous.get("enforcement") != "enforced":
            # Activating a recorded baseline improves coverage but does not assert
            # that the already-existing product surface itself was newly added.
            continue
        old_path = str(previous["snapshot_path"])
        old_snapshot = git_json_optional(root, base, old_path)
        if old_snapshot is None or not isinstance(old_snapshot, dict):
            raise DeclarationError(
                f"enforced base snapshot is missing or malformed: {old_path}"
            )
        current_path = root / str(current["snapshot_path"])
        current_snapshot = load_json(current_path)
        if not isinstance(current_snapshot, dict):
            raise DeclarationError(
                f"current snapshot must be an object: {current['snapshot_path']}"
            )
        comparison = compare(
            old_snapshot,
            current_snapshot,
            str(current["comparison"]),
        )
        classification = str(getattr(comparison, "classification"))
        if classification == "unchanged":
            continue
        raw_findings = getattr(comparison, "findings")
        findings = tuple(str(finding) for finding in raw_findings)
        detected.append(
            DetectedChange(
                identifier,
                str(current["component"]),
                declaration_for_surface(current),
                classification,
                str(current["snapshot_path"]),
                findings,
            )
        )

    for identifier, previous in base_surfaces.items():
        if previous.get("enforcement") != "enforced":
            continue
        current = current_surfaces.get(identifier)
        if current is not None and current.get("enforcement") == "enforced":
            continue
        disposition = "removed" if current is None else "downgraded from enforced"
        detected.append(
            DetectedChange(
                identifier,
                str(previous["component"]),
                "architecture_change",
                "breaking",
                str(previous["snapshot_path"]),
                (f"enforced public surface was {disposition}",),
            )
        )
    return detected


def declaration_value(task: Mapping[str, object], name: str) -> tuple[str, set[str]]:
    classifications = task.get("change_classification")
    if not isinstance(classifications, dict):
        raise DeclarationError("task has no change_classification object")
    declaration = classifications.get(name)
    if isinstance(declaration, str):
        return declaration, set()
    if not isinstance(declaration, dict):
        raise DeclarationError(f"{name} declaration must be an object")
    level = declaration.get("level")
    evidence = declaration.get("evidence")
    affected = declaration.get("affected_surfaces", [])
    if (
        level
        not in {
            "none",
            "compatible",
            "additive",
            "breaking",
            "intentional-correction",
        }
        or not isinstance(evidence, list)
        or not all(isinstance(item, str) and item for item in evidence)
        or not isinstance(affected, list)
        or not all(isinstance(item, str) for item in affected)
    ):
        raise DeclarationError(f"malformed {name} declaration")
    return str(level), set(affected)


def validate_change_declarations(
    task: Mapping[str, object], detected: list[DetectedChange]
) -> list[str]:
    findings: list[str] = []
    for declaration_name in (
        "public_api_change",
        "schema_change",
        "architecture_change",
    ):
        relevant = [
            change for change in detected if change.declaration == declaration_name
        ]
        level, affected = declaration_value(task, declaration_name)
        detected_ids = {change.surface for change in relevant}
        if not relevant:
            if affected:
                findings.append(
                    f"{declaration_name} names surfaces without detected drift: "
                    + ", ".join(sorted(affected))
                )
            continue
        missing = detected_ids - affected
        extra = affected - detected_ids
        if missing:
            findings.append(
                f"{declaration_name} does not name changed surfaces: "
                + ", ".join(sorted(missing))
            )
        if extra:
            findings.append(
                f"{declaration_name} names unrelated surfaces: "
                + ", ".join(sorted(extra))
            )
        strongest = max(
            relevant,
            key=lambda change: CLASSIFICATION_ORDER[change.classification],
        ).classification
        if level == "none":
            findings.append(
                f"{declaration_name} is none but detected {strongest} drift"
            )
        elif level != strongest and level != "intentional-correction":
            findings.append(
                f"{declaration_name} level {level} does not match detected "
                f"{strongest} drift"
            )
    return findings
