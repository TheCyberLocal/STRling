#!/usr/bin/env python3
"""Language-aware dependency and placement checks for architecture fitness."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Mapping, Sequence


Match = Callable[[str, Sequence[str]], bool]
Finding = tuple[str, str | None]


def relative_files(
    root: Path,
    patterns: Sequence[str],
    matches_any: Match,
    suffixes: tuple[str, ...] | None = None,
) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        parts = set(relative.split("/"))
        if parts.intersection({".git", "node_modules", "dist", "vendor"}):
            continue
        if suffixes is not None and path.suffix not in suffixes:
            continue
        if matches_any(relative, patterns):
            files.append((path, relative))
    return sorted(files, key=lambda item: item[1])


def rust_crate_boundary_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Reject Rust path dependencies and source inclusions into forbidden roots."""

    manifest_relative = configuration["manifest"]
    sources = configuration["sources"]
    forbidden_roots = configuration["forbidden_repository_roots"]
    assert isinstance(manifest_relative, str)
    assert isinstance(sources, list)
    assert isinstance(forbidden_roots, list)
    root_resolved = root.resolve()
    findings: list[Finding] = []

    def inspect_reference(owner: Path, owner_relative: str, reference: str) -> None:
        resolved = (owner.parent / reference).resolve()
        try:
            repository_relative = resolved.relative_to(root_resolved).as_posix()
        except ValueError:
            findings.append(
                (
                    f"{owner_relative}: path dependency escapes repository: {reference}",
                    owner_relative,
                )
            )
            return
        if any(
            repository_relative == forbidden
            or repository_relative.startswith(str(forbidden) + "/")
            for forbidden in forbidden_roots
        ):
            findings.append(
                (
                    f"{owner_relative}: forbidden repository dependency "
                    f"{repository_relative}",
                    owner_relative,
                )
            )

    manifest = root / manifest_relative
    try:
        manifest_text = manifest.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            (
                f"{manifest_relative}: cannot inspect Rust manifest: {exc}",
                manifest_relative,
            )
        ]
    for reference in re.findall(r"\bpath\s*=\s*[\"']([^\"']+)[\"']", manifest_text):
        inspect_reference(manifest, manifest_relative, reference)

    source_reference = re.compile(
        r"(?:#\s*\[\s*path\s*=|include(?:_str|_bytes)?!\s*\()"
        r"\s*[\"']([^\"']+)[\"']"
    )
    for source, relative in relative_files(root, sources, matches_any, (".rs",)):
        try:
            source_text = source.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                (f"{relative}: cannot inspect Rust source: {exc}", relative)
            )
            continue
        for reference in source_reference.findall(source_text):
            inspect_reference(source, relative, reference)
    return findings


def python_import_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    sources = configuration["sources"]
    forbidden = configuration["forbidden_modules"]
    assert isinstance(sources, list)
    assert isinstance(forbidden, list)
    findings: list[Finding] = []
    for path, relative in relative_files(root, sources, matches_any, (".py",)):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            findings.append(
                (f"{relative}: cannot inspect Python imports: {exc}", relative)
            )
            continue
        dependencies: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                dependencies.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                dependencies.add(node.module)
        for dependency in sorted(dependencies):
            if any(
                dependency == prefix or dependency.startswith(prefix + ".")
                for prefix in forbidden
            ):
                findings.append(
                    (f"{relative}: forbidden import {dependency}", relative)
                )
    return findings


def schema_references(value: object, path: str = "$") -> list[tuple[str, object]]:
    references: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if key == "$ref":
                references.append((child_path, child))
            references.extend(schema_references(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            references.extend(schema_references(child, f"{path}/{index}"))
    return references


def schema_reference_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    sources = configuration["sources"]
    allowed_roots = configuration["allowed_reference_roots"]
    assert isinstance(sources, list)
    assert isinstance(allowed_roots, list)
    findings: list[Finding] = []
    root_resolved = root.resolve()
    for source, relative in relative_files(root, sources, matches_any, (".json",)):
        try:
            document = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append((f"{relative}: malformed JSON schema: {exc}", relative))
            continue
        for location, reference in schema_references(document):
            if not isinstance(reference, str):
                findings.append(
                    (f"{relative}:{location}: $ref must be a string", relative)
                )
                continue
            target_text = reference.split("#", 1)[0]
            if not target_text:
                continue
            if (
                target_text.startswith("/")
                or "\\" in target_text
                or "://" in target_text
            ):
                findings.append(
                    (
                        f"{relative}:{location}: forbidden schema reference {reference}",
                        relative,
                    )
                )
                continue
            resolved = (source.parent / target_text).resolve()
            try:
                target_relative = resolved.relative_to(root_resolved).as_posix()
            except ValueError:
                findings.append(
                    (
                        f"{relative}:{location}: schema reference escapes repository",
                        relative,
                    )
                )
                continue
            if not any(
                target_relative == allowed
                or target_relative.startswith(str(allowed) + "/")
                for allowed in allowed_roots
            ):
                findings.append(
                    (
                        f"{relative}:{location}: reference target {target_relative} "
                        "is outside allowed roots",
                        relative,
                    )
                )
            elif not resolved.is_file():
                findings.append(
                    (
                        f"{relative}:{location}: reference target does not exist: "
                        f"{target_relative}",
                        relative,
                    )
                )
    return findings


def semantic_declarations(path: Path) -> tuple[set[str], str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return set(), str(exc)
    if path.suffix == ".py":
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            return set(), str(exc)
        return {
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }, None
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", " ", text)
    names = set(
        re.findall(
            r"\b(?:class|function|interface|type)\s+([A-Za-z_$][A-Za-z0-9_$]*)",
            text,
        )
    )
    return names, None


def semantic_island_findings(
    root: Path,
    configuration: Mapping[str, object],
    changes: Sequence[object],
    matches_any: Match,
    architecture_declared: bool,
) -> list[Finding]:
    guarded = configuration["guarded_roots"]
    semantic_names = configuration["semantic_names"]
    assert isinstance(guarded, list)
    assert isinstance(semantic_names, list)
    ignored = {
        "__tests__",
        "dist",
        "fixtures",
        "generated",
        "node_modules",
        "out",
        "test",
        "tests",
        "vendor",
    }
    findings: list[Finding] = []
    for change in changes:
        status = str(getattr(change, "status"))
        relative = getattr(change, "new_path")
        if (
            not status.startswith(("A", "R", "C"))
            or not isinstance(relative, str)
            or not any(
                relative == guarded_root or relative.startswith(str(guarded_root) + "/")
                for guarded_root in guarded
            )
        ):
            continue
        path = root / relative
        parts = {part.lower() for part in Path(relative).parts}
        if (
            not path.is_file()
            or parts.intersection(ignored)
            or path.name.lower().startswith("test_")
            or path.suffix not in {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx"}
        ):
            continue
        declarations, error = semantic_declarations(path)
        if error is not None:
            findings.append(
                (f"{relative}: cannot inspect semantic declarations: {error}", relative)
            )
            continue
        haystacks = {path.stem.lower(), *(name.lower() for name in declarations)}
        matched = sorted(
            semantic_name
            for semantic_name in semantic_names
            if any(str(semantic_name).lower() in value for value in haystacks)
        )
        if matched and not architecture_declared:
            findings.append(
                (
                    f"{relative}: new semantic implementation island "
                    f"({', '.join(matched)}) requires architecture_change",
                    relative,
                )
            )
    return findings


def tracked_paths(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        return sorted(
            item.decode("utf-8") for item in completed.stdout.split(b"\0") if item
        )
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )


def tracked_transition_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    patterns = configuration["tracked_paths"]
    assert isinstance(patterns, list)
    matched = [path for path in tracked_paths(root) if matches_any(path, patterns)]
    if not matched:
        return []
    preview = ", ".join(matched[:5])
    suffix = "" if len(matched) <= 5 else f", plus {len(matched) - 5} more"
    return [
        (
            f"{len(matched)} tracked transition paths remain: {preview}{suffix}",
            None,
        )
    ]


def artifact_authority_findings(
    configuration: Mapping[str, object],
    artifact_registry: Mapping[str, object],
) -> list[Finding]:
    identifiers = configuration["artifact_ids"]
    allowed = configuration["allowed_authorities"]
    assert isinstance(identifiers, list)
    assert isinstance(allowed, list)
    artifacts = artifact_registry.get("artifacts")
    assert isinstance(artifacts, list)
    by_id = {
        str(artifact["id"]): artifact
        for artifact in artifacts
        if isinstance(artifact, dict)
    }
    findings: list[Finding] = []
    for identifier in identifiers:
        artifact = by_id.get(str(identifier))
        if artifact is None:
            findings.append((f"registered artifact is missing: {identifier}", None))
            continue
        authority = str(artifact.get("authority"))
        if authority not in allowed:
            findings.append(
                (
                    f"{identifier}: authority {authority} is not allowed "
                    "for implementation-derived test generation",
                    None,
                )
            )
    return findings


def evaluate_extended_rule(
    kind: str,
    *,
    root: Path,
    configuration: Mapping[str, object],
    changes: Sequence[object],
    artifact_registry: Mapping[str, object],
    matches_any: Match,
    architecture_declared: bool,
) -> list[Finding] | None:
    if kind == "rust-crate-boundary":
        return rust_crate_boundary_findings(root, configuration, matches_any)
    if kind == "forbidden-import":
        return python_import_findings(root, configuration, matches_any)
    if kind == "schema-reference-boundary":
        return schema_reference_findings(root, configuration, matches_any)
    if kind == "semantic-island-placement":
        return semantic_island_findings(
            root,
            configuration,
            changes,
            matches_any,
            architecture_declared,
        )
    if kind == "tracked-transition":
        return tracked_transition_findings(root, configuration, matches_any)
    if kind == "artifact-authority-boundary":
        return artifact_authority_findings(configuration, artifact_registry)
    return None
