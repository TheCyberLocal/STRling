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
    for relative in candidate_paths(root):
        path = root / relative
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


def native_adapter_boundary_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Reject retired semantic sources and dependencies in a native adapter."""

    sources = configuration["sources"]
    forbidden_paths = configuration["forbidden_paths"]
    forbidden_markers = configuration["forbidden_markers"]
    required_markers = configuration["required_markers"]
    assert isinstance(sources, list)
    assert isinstance(forbidden_paths, list)
    assert isinstance(forbidden_markers, list)
    assert isinstance(required_markers, list)
    findings: list[Finding] = []

    for path, relative in relative_files(root, forbidden_paths, matches_any):
        findings.append(
            (f"{relative}: retired semantic adapter path remains", relative)
        )

    for path, relative in relative_files(root, sources, matches_any):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                (f"{relative}: cannot inspect native adapter: {exc}", relative)
            )
            continue
        folded = text.casefold()
        for marker in forbidden_markers:
            if str(marker).casefold() in folded:
                findings.append(
                    (
                        f"{relative}: native adapter contains forbidden semantic "
                        f"dependency marker {marker}",
                        relative,
                    )
                )

    for requirement in required_markers:
        assert isinstance(requirement, dict)
        relative = requirement["path"]
        markers = requirement["markers"]
        assert isinstance(relative, str)
        assert isinstance(markers, list)
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                (f"{relative}: cannot inspect required route: {exc}", relative)
            )
            continue
        for marker in markers:
            if str(marker) not in text:
                findings.append(
                    (
                        f"{relative}: required canonical adapter marker is missing: "
                        f"{marker}",
                        relative,
                    )
                )
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


def frontend_authority_boundary_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Keep compatibility syntax out of semantic and target authority."""

    contract_sources = configuration["frontend_contract_sources"]
    semantic_sources = configuration["semantic_authority_sources"]
    target_sources = configuration["target_authority_sources"]
    frontend_markers = configuration["forbidden_frontend_markers"]
    contract_markers = configuration["contract_forbidden_authority_markers"]
    assert isinstance(contract_sources, list)
    assert isinstance(semantic_sources, list)
    assert isinstance(target_sources, list)
    assert isinstance(frontend_markers, list)
    assert isinstance(contract_markers, list)
    findings: list[Finding] = []

    def authority_files(patterns: list[object]) -> list[tuple[Path, str]]:
        """Enumerate only declared authority roots, not the whole repository."""

        selected = [str(pattern) for pattern in patterns]
        candidates: set[Path] = set()
        for pattern in selected:
            wildcard = min(
                (
                    index
                    for index in (pattern.find("*"), pattern.find("?"))
                    if index >= 0
                ),
                default=len(pattern),
            )
            prefix = pattern[:wildcard].rstrip("/")
            candidate = root / prefix
            if candidate.is_file():
                candidates.add(candidate)
            elif candidate.is_dir():
                candidates.update(
                    path for path in candidate.rglob("*") if path.is_file()
                )

        files = []
        for path in candidates:
            relative = path.relative_to(root).as_posix()
            if matches_any(relative, selected):
                files.append((path, relative))
        return sorted(files, key=lambda item: item[1])

    def inspect(
        patterns: list[object],
        markers: list[object],
        boundary: str,
    ) -> None:
        for path, relative in authority_files(patterns):
            try:
                folded = path.read_text(encoding="utf-8").casefold()
            except (OSError, UnicodeDecodeError) as error:
                findings.append(
                    (f"{relative}: cannot inspect {boundary}: {error}", relative)
                )
                continue
            for marker in markers:
                if str(marker).casefold() not in folded:
                    continue
                findings.append(
                    (
                        f"{relative}: {boundary} contains forbidden frontend "
                        f"authority marker {marker}",
                        relative,
                    )
                )
                break

    inspect(contract_sources, contract_markers, "frontend contract")
    inspect(semantic_sources, frontend_markers, "semantic authority")
    inspect(target_sources, frontend_markers, "target authority")
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
            relative
            for item in completed.stdout.split(b"\0")
            if item
            for relative in [item.decode("utf-8")]
            if (root / relative).is_file()
        )
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )


def candidate_paths(root: Path) -> list[str]:
    """Return tracked and visible untracked files without build/cache artifacts."""

    completed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        return sorted(
            relative
            for item in completed.stdout.split(b"\0")
            if item
            if (relative := item.decode("utf-8"))
            if (root / relative).is_file()
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


def non_normative_history_boundary_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Keep retained migration history data-only and unreachable from authority."""

    history_roots = configuration["history_roots"]
    allowed_files = configuration["allowed_files"]
    consumer_sources = configuration["consumer_sources"]
    forbidden_reference_markers = configuration["forbidden_reference_markers"]
    forbidden_extensions = configuration["forbidden_extensions"]
    assert isinstance(history_roots, list)
    assert isinstance(allowed_files, list)
    assert isinstance(consumer_sources, list)
    assert isinstance(forbidden_reference_markers, list)
    assert isinstance(forbidden_extensions, list)

    findings: list[Finding] = []
    actual = {
        relative
        for relative in tracked_paths(root)
        if matches_any(relative, history_roots)
    }
    expected = set(allowed_files)
    for relative in sorted(expected - actual):
        findings.append((f"{relative}: required historical data is missing", relative))
    for relative in sorted(actual - expected):
        findings.append(
            (f"{relative}: unregistered historical executable or data", relative)
        )
    for relative in sorted(actual):
        if Path(relative).suffix.casefold() in {
            str(extension).casefold() for extension in forbidden_extensions
        }:
            findings.append((f"{relative}: executable history is forbidden", relative))

    text_suffixes = (
        ".c",
        ".cc",
        ".cpp",
        ".cs",
        ".dart",
        ".fs",
        ".go",
        ".h",
        ".hpp",
        ".java",
        ".js",
        ".json",
        ".kt",
        ".kts",
        ".lua",
        ".mjs",
        ".php",
        ".pl",
        ".pm",
        ".ps1",
        ".py",
        ".r",
        ".rb",
        ".rs",
        ".sh",
        ".toml",
        ".ts",
        ".tsx",
        ".xml",
        ".yaml",
        ".yml",
    )
    for path, relative in relative_files(
        root, consumer_sources, matches_any, text_suffixes
    ):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            findings.append((f"{relative}: cannot inspect consumer: {error}", relative))
            continue
        for marker in forbidden_reference_markers:
            if str(marker) in text:
                findings.append(
                    (f"{relative}: imports retained historical data {marker}", relative)
                )
    return findings


def binding_semantic_path_candidate(
    relative: str, configuration: Mapping[str, object], matches_any: Match
) -> bool:
    """Return whether a tracked binding path looks like an owned compiler stage."""

    sources = configuration["sources"]
    semantic_names = configuration["semantic_names"]
    permitted_paths = configuration["permitted_paths"]
    excluded_path_parts = configuration["excluded_path_parts"]
    assert isinstance(sources, list)
    assert isinstance(semantic_names, list)
    assert isinstance(permitted_paths, list)
    assert isinstance(excluded_path_parts, list)
    if not matches_any(relative, sources) or relative in permitted_paths:
        return False
    path = Path(relative)
    parts = {part.casefold() for part in path.parts}
    if parts.intersection(str(part).casefold() for part in excluded_path_parts):
        return False
    names = {str(name).casefold() for name in semantic_names}
    return path.stem.casefold() in names or bool(
        {part.casefold() for part in path.parts[:-1]}.intersection(names)
    )


def binding_semantic_path_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Reject new binding-owned compiler stages while admitting exact facades."""

    return [
        (
            f"{relative}: binding-owned semantic implementation path is forbidden",
            relative,
        )
        for relative in tracked_paths(root)
        if binding_semantic_path_candidate(relative, configuration, matches_any)
    ]


def required_rule_status_findings(
    rules: Sequence[object], required_rule_ids: Sequence[object]
) -> list[Finding]:
    by_id = {
        str(rule.get("id")): rule
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("id"), str)
    }
    findings: list[Finding] = []
    for item in required_rule_ids:
        identifier = str(item)
        rule = by_id.get(identifier)
        if rule is None:
            findings.append(
                (f"required binding route rule is missing: {identifier}", None)
            )
        elif rule.get("status") != "enforced":
            findings.append(
                (f"required binding route rule is not enforced: {identifier}", None)
            )
    return findings


def binding_route_coverage_findings(
    root: Path,
    configuration: Mapping[str, object],
) -> list[Finding]:
    """Require one enforced canonical-route rule for every binding family."""

    required_rule_ids = configuration["required_rule_ids"]
    assert isinstance(required_rule_ids, list)
    try:
        registry = json.loads(
            (root / "governance/architecture-rules.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        return [(f"cannot inspect binding route rule registry: {error}", None)]
    rules = registry.get("rules") if isinstance(registry, dict) else None
    if not isinstance(rules, list):
        return [("binding route rule registry has no rules", None)]
    return required_rule_status_findings(rules, required_rule_ids)


def jvm_adapter_boundary_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Enforce one semantic-free JVM bridge and the retired-copy denominator."""

    sources = configuration["sources"]
    forbidden_paths = configuration["forbidden_paths"]
    forbidden_markers = configuration["forbidden_markers"]
    required_markers = configuration["required_markers"]
    assert isinstance(sources, list)
    assert isinstance(forbidden_paths, list)
    assert isinstance(forbidden_markers, list)
    assert isinstance(required_markers, list)

    candidates = candidate_paths(root)
    findings: list[Finding] = []
    for relative in candidates:
        if matches_any(relative, forbidden_paths):
            findings.append(
                (f"{relative}: retired JVM semantic copy remains", relative)
            )
        if not matches_any(relative, sources):
            continue
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            findings.append(
                (f"{relative}: cannot inspect JVM facade: {error}", relative)
            )
            continue
        for marker in forbidden_markers:
            if str(marker) in text:
                findings.append(
                    (
                        f"{relative}: JVM facade contains alternate route {marker}",
                        relative,
                    )
                )

    for requirement in required_markers:
        assert isinstance(requirement, dict)
        relative = str(requirement["path"])
        markers = requirement["markers"]
        assert isinstance(markers, list)
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except OSError as error:
            findings.append(
                (
                    f"{relative}: cannot inspect JVM dependency direction: {error}",
                    relative,
                )
            )
            continue
        for marker in markers:
            if str(marker) not in text:
                findings.append(
                    (
                        f"{relative}: missing required JVM bridge marker {marker}",
                        relative,
                    )
                )
    return findings


def dotnet_adapter_boundary_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Enforce one semantic-free C# bridge and a dependent F# facade."""

    sources = configuration["sources"]
    fsharp_sources = configuration["fsharp_sources"]
    forbidden_paths = configuration["forbidden_paths"]
    forbidden_markers = configuration["forbidden_markers"]
    fsharp_forbidden_markers = configuration["fsharp_forbidden_markers"]
    required_markers = configuration["required_markers"]
    assert isinstance(sources, list)
    assert isinstance(fsharp_sources, list)
    assert isinstance(forbidden_paths, list)
    assert isinstance(forbidden_markers, list)
    assert isinstance(fsharp_forbidden_markers, list)
    assert isinstance(required_markers, list)

    candidates = candidate_paths(root)
    findings: list[Finding] = []
    for relative in candidates:
        if matches_any(relative, forbidden_paths):
            findings.append(
                (f"{relative}: retired .NET semantic copy remains", relative)
            )
        if not matches_any(relative, sources):
            continue
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            findings.append(
                (f"{relative}: cannot inspect .NET facade: {error}", relative)
            )
            continue
        markers = list(forbidden_markers)
        if matches_any(relative, fsharp_sources):
            markers.extend(fsharp_forbidden_markers)
        for marker in markers:
            if str(marker) in text:
                findings.append(
                    (
                        f"{relative}: .NET facade contains alternate route {marker}",
                        relative,
                    )
                )

    for requirement in required_markers:
        assert isinstance(requirement, dict)
        relative = str(requirement["path"])
        markers = requirement["markers"]
        assert isinstance(markers, list)
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except OSError as error:
            findings.append(
                (
                    f"{relative}: cannot inspect .NET dependency direction: {error}",
                    relative,
                )
            )
            continue
        for marker in markers:
            if str(marker) not in text:
                findings.append(
                    (
                        f"{relative}: missing required .NET bridge marker {marker}",
                        relative,
                    )
                )
    return findings


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


def ci_profile_routing_findings(
    root: Path, configuration: Mapping[str, object]
) -> list[Finding]:
    """Require CI certification authority to remain on canonical profiles."""

    sources = configuration["sources"]
    assert isinstance(sources, list)
    expected = {
        ".github/workflows/ci.yml": {
            "profiles": ("local", "pull-request", "full", "release"),
            "invocation": './strling profile "$PROFILE" --artifact "$ARTIFACT_PATH"',
            "routing": (
                'workflow_dispatch) profile="$REQUESTED_PROFILE" ;;',
                'pull_request) profile="pull-request" ;;',
                'schedule) profile="full" ;;',
                'profile="release"',
                'profile="pull-request"',
            ),
            "product_routing": (
                "steps.certification_profile.outputs.profile == 'full'",
                "steps.certification_profile.outputs.profile == 'release'",
            ),
            "product_artifacts": (
                "steps.certification_profile.outputs.product_artifact_path",
                "steps.certification_profile.outputs.product_report_path",
            ),
        },
        ".github/workflows/cd.yml": {
            "profiles": ("release",),
            "invocation": './strling profile release --artifact "$ARTIFACT_PATH"',
            "product_routing": (),
            "product_artifacts": (
                "artifacts/product-certification-release.json",
                "artifacts/product-certification-release.md",
            ),
        },
    }
    findings: list[Finding] = []
    if set(sources) != set(expected):
        findings.append(
            (
                "CI profile routing must govern both ci.yml and cd.yml",
                None,
            )
        )

    upload_action = "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    product_invocation = (
        'python3 tooling/product_certification.py --profile-artifact "$ARTIFACT_PATH" '
        '--artifact "$PRODUCT_ARTIFACT_PATH" --report "$PRODUCT_REPORT_PATH"'
    )
    direct_authorities = (
        "architecture_fitness.py",
        "baseline.py",
        "contract_validation.py",
        "core_contract_validation.py",
        "documentation_integrity.py",
        "formatting.py",
        "generated_artifacts.py",
        "governance.py",
        "public_contracts.py",
        "quality.py",
        "security.py",
        "static_analysis.py",
    )
    direct_pattern = re.compile(
        r"\bpython3?\s+(?:\./)?tooling/(?:"
        + "|".join(re.escape(name) for name in direct_authorities)
        + r")\b"
    )

    for relative, requirements in expected.items():
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                (f"{relative}: cannot inspect CI profile routing: {exc}", relative)
            )
            continue

        profiles = requirements["profiles"]
        assert isinstance(profiles, tuple)
        for profile in profiles:
            if profile not in text:
                findings.append(
                    (
                        f"{relative}: missing canonical {profile} profile mapping",
                        relative,
                    )
                )

        invocation = requirements["invocation"]
        assert isinstance(invocation, str)
        actual_invocations = [
            line.strip() for line in text.splitlines() if "./strling profile" in line
        ]
        if actual_invocations != [invocation]:
            findings.append(
                (
                    f"{relative}: canonical profile invocation must be exactly {invocation}",
                    relative,
                )
            )
        routing = requirements.get("routing", ())
        assert isinstance(routing, tuple)
        for fragment in routing:
            if fragment not in text:
                findings.append(
                    (
                        f"{relative}: missing deterministic routing fragment {fragment}",
                        relative,
                    )
                )
        product_routing = requirements["product_routing"]
        assert isinstance(product_routing, tuple)
        for fragment in product_routing:
            if fragment not in text:
                findings.append(
                    (
                        f"{relative}: missing structured product routing fragment {fragment}",
                        relative,
                    )
                )
        if text.count(product_invocation) != 1:
            findings.append(
                (
                    f"{relative}: structured product derivation must be exactly {product_invocation}",
                    relative,
                )
            )
        product_index = text.find(product_invocation)
        product_prefix = text[max(0, product_index - 700) : product_index]
        if product_index >= 0 and not re.search(
            r"if:\s*(?:>-\s*)?(?:\$\{\{\s*)?always\(\)", product_prefix
        ):
            findings.append(
                (
                    f"{relative}: structured product derivation must preserve nonpassing profile evidence with always()",
                    relative,
                )
            )
        product_artifacts = requirements["product_artifacts"]
        assert isinstance(product_artifacts, tuple)
        for artifact in product_artifacts:
            if text.count(artifact) < 2:
                findings.append(
                    (
                        f"{relative}: structured product artifact is not derived and retained: {artifact}",
                        relative,
                    )
                )
        if re.search(r"\./strling\s+(?:check|certify)\b", text):
            findings.append(
                (
                    f"{relative}: compatibility aliases cannot be CI certification authority",
                    relative,
                )
            )
        if direct_pattern.search(text):
            findings.append(
                (
                    f"{relative}: workflow cannot invoke a quality implementation directly",
                    relative,
                )
            )
        if text.count(upload_action) != 1:
            findings.append(
                (
                    f"{relative}: certification artifact upload must use the governed immutable action",
                    relative,
                )
            )
        if (
            "if: ${{ always() }}" not in text
            or "if-no-files-found: warn" not in text
            or text.count("continue-on-error: true") != 1
        ):
            findings.append(
                (
                    f"{relative}: artifact retention must be unconditional and non-authoritative",
                    relative,
                )
            )

    cd_path = root / ".github/workflows/cd.yml"
    if cd_path.is_file() and "needs: release-certification" not in cd_path.read_text(
        encoding="utf-8"
    ):
        findings.append(
            (
                ".github/workflows/cd.yml: release preflight must depend on release certification",
                ".github/workflows/cd.yml",
            )
        )
    return findings


def legacy_reference_boundary_findings(
    root: Path,
    configuration: Mapping[str, object],
    artifact_registry: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Keep legacy observations outside product and normative authority."""

    consumer_sources = configuration["consumer_sources"]
    normative_sources = configuration["normative_sources"]
    runner_sources = configuration["runner_sources"]
    runner_isolation_boundaries = configuration["runner_isolation_boundaries"]
    comparison_sources = configuration["comparison_sources"]
    comparison_contract = configuration["comparison_contract"]
    comparison_mutation_tokens = configuration["comparison_forbidden_mutation_tokens"]
    comparison_authority_tokens = configuration["comparison_forbidden_authority_tokens"]
    evidence_markers = configuration["forbidden_evidence_markers"]
    runner_forbidden_roots = configuration["runner_forbidden_roots"]
    runner_authority_tokens = configuration["runner_forbidden_authority_tokens"]
    normative_output_roots = configuration["normative_output_roots"]
    assert isinstance(consumer_sources, list)
    assert isinstance(normative_sources, list)
    assert isinstance(runner_sources, list)
    assert isinstance(runner_isolation_boundaries, list)
    assert isinstance(evidence_markers, list)
    assert isinstance(comparison_sources, list)
    assert isinstance(comparison_contract, str)
    assert isinstance(comparison_mutation_tokens, list)
    assert isinstance(comparison_authority_tokens, list)
    assert isinstance(runner_forbidden_roots, list)
    assert isinstance(runner_authority_tokens, list)
    assert isinstance(normative_output_roots, list)

    text_suffixes = (
        ".c",
        ".cc",
        ".cpp",
        ".cs",
        ".dart",
        ".fs",
        ".go",
        ".h",
        ".hpp",
        ".java",
        ".js",
        ".json",
        ".kt",
        ".kts",
        ".lua",
        ".md",
        ".mjs",
        ".php",
        ".pl",
        ".pm",
        ".py",
        ".r",
        ".rb",
        ".rs",
        ".swift",
        ".toml",
        ".ts",
        ".tsx",
        ".xml",
        ".yaml",
        ".yml",
    )
    findings: list[Finding] = []
    completed = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        candidate_paths = sorted(
            item.decode("utf-8") for item in completed.stdout.split(b"\0") if item
        )
    else:
        candidate_paths = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        )

    def selected_files(
        patterns: Sequence[str], suffixes: tuple[str, ...]
    ) -> list[tuple[Path, str]]:
        return [
            (root / relative, relative)
            for relative in candidate_paths
            if (root / relative).is_file()
            and Path(relative).suffix.lower() in suffixes
            and matches_any(relative, patterns)
        ]

    def read_text(path: Path, relative: str) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(
                (f"{relative}: cannot inspect authority references: {exc}", relative)
            )
            return None

    protected_patterns = [*consumer_sources, *normative_sources]
    for path, relative in selected_files(protected_patterns, text_suffixes):
        text = read_text(path, relative)
        if text is None:
            continue
        folded = text.casefold()
        for marker in evidence_markers:
            if str(marker).casefold() in folded:
                findings.append(
                    (
                        f"{relative}: product or normative source references "
                        f"legacy evidence marker {marker}",
                        relative,
                    )
                )
                break

    for path, relative in selected_files(comparison_sources, text_suffixes):
        text = read_text(path, relative)
        if text is None:
            continue
        folded = text.casefold()
        for token in comparison_mutation_tokens:
            if str(token).casefold() in folded:
                findings.append(
                    (
                        f"{relative}: comparison tooling contains forbidden "
                        f"source-mutation token {token}",
                        relative,
                    )
                )
        for token in comparison_authority_tokens:
            if str(token).casefold() in folded:
                findings.append(
                    (
                        f"{relative}: comparison tooling contains forbidden "
                        f"authority or acceptance token {token}",
                        relative,
                    )
                )

    contract_path = root / comparison_contract
    if not comparison_contract.startswith("tooling/"):
        findings.append(
            (
                f"{comparison_contract}: normalization authority must remain in tooling",
                comparison_contract,
            )
        )
    try:
        comparison_definition = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(
            (
                f"{comparison_contract}: cannot inspect comparison authority: {exc}",
                comparison_contract,
            )
        )
    else:
        authority_model = comparison_definition.get("authority_model")
        if not isinstance(authority_model, dict) or (
            authority_model.get("historical_consensus_is_normative") is not False
            or authority_model.get("majority_is_authority") is not False
        ):
            findings.append(
                (
                    f"{comparison_contract}: historical evidence cannot become authority",
                    comparison_contract,
                )
            )
        dispositions = comparison_definition.get("dispositions")
        disposition_ids = (
            [entry.get("id") for entry in dispositions]
            if isinstance(dispositions, list)
            and all(isinstance(entry, dict) for entry in dispositions)
            else []
        )
        if disposition_ids != [
            "preserved_behavior",
            "intentional_specification_correction",
            "unsupported_legacy_behavior",
            "unresolved_discrepancy",
        ]:
            findings.append(
                (
                    f"{comparison_contract}: discrepancy taxonomy identities changed",
                    comparison_contract,
                )
            )
        relationships = comparison_definition.get("comparison_relationships")
        if relationships != [
            "equivalent_observation",
            "differing_observation",
            "not_comparable",
        ]:
            findings.append(
                (
                    f"{comparison_contract}: comparison relationship states changed",
                    comparison_contract,
                )
            )
        rules = comparison_definition.get("normalization_rules")
        if not isinstance(rules, list) or not rules:
            findings.append(
                (
                    f"{comparison_contract}: normalization rules require explicit identities",
                    comparison_contract,
                )
            )

    root_resolved = root.resolve()
    for boundary in runner_isolation_boundaries:
        assert isinstance(boundary, dict)
        boundary_id = boundary["id"]
        boundary_sources = boundary["sources"]
        forbidden_markers = boundary["forbidden_markers"]
        assert isinstance(boundary_id, str)
        assert isinstance(boundary_sources, list)
        assert isinstance(forbidden_markers, list)
        for path, relative in selected_files(
            boundary_sources,
            (".cjs", ".js", ".json", ".mjs", ".py"),
        ):
            text = read_text(path, relative)
            if text is None:
                continue
            folded = text.casefold()
            for marker in forbidden_markers:
                if str(marker).casefold() not in folded:
                    continue
                findings.append(
                    (
                        f"{relative}: {boundary_id} runner contains forbidden "
                        f"cross-runner expectation marker {marker}",
                        relative,
                    )
                )
                break

    string_literal = re.compile(r"""["']([^"'\\]*(?:\\.[^"'\\]*)*)["']""")
    for path, relative in selected_files(
        runner_sources, (".cjs", ".js", ".json", ".mjs", ".py")
    ):
        text = read_text(path, relative)
        if text is None:
            continue
        folded = text.casefold()
        for token in runner_authority_tokens:
            if str(token).casefold() in folded:
                findings.append(
                    (
                        f"{relative}: legacy runner contains forbidden authority "
                        f"token {token}",
                        relative,
                    )
                )
        for reference in string_literal.findall(text):
            normalized = reference.replace("\\\\", "/")
            for forbidden_root in runner_forbidden_roots:
                forbidden = str(forbidden_root)
                direct = normalized == forbidden or normalized.startswith(
                    forbidden + "/"
                )
                resolved_under_forbidden = False
                if normalized.startswith("."):
                    resolved = (path.parent / normalized).resolve()
                    try:
                        repository_relative = resolved.relative_to(
                            root_resolved
                        ).as_posix()
                    except ValueError:
                        repository_relative = ""
                    resolved_under_forbidden = (
                        repository_relative == forbidden
                        or repository_relative.startswith(forbidden + "/")
                    )
                if direct or resolved_under_forbidden:
                    findings.append(
                        (
                            f"{relative}: legacy runner references forbidden "
                            f"authority root {forbidden}",
                            relative,
                        )
                    )

    artifacts = artifact_registry.get("artifacts")
    assert isinstance(artifacts, list)
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        outputs = artifact.get("outputs", [])
        if not isinstance(outputs, list) or not any(
            isinstance(output, str)
            and any(
                output == str(output_root) or output.startswith(str(output_root) + "/")
                for output_root in normative_output_roots
            )
            for output in outputs
        ):
            continue
        relationship = json.dumps(
            {
                "authoritative_sources": artifact.get("authoritative_sources", []),
                "generator": artifact.get("generator", {}),
                "generator_inputs": artifact.get("generator_inputs", []),
            },
            sort_keys=True,
        ).casefold()
        for marker in evidence_markers:
            if str(marker).casefold() in relationship:
                identifier = artifact.get("id", "<unknown>")
                findings.append(
                    (
                        f"generated artifact {identifier}: normative output depends "
                        f"on legacy evidence marker {marker}",
                        None,
                    )
                )
                break
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
    if kind == "native-adapter-boundary":
        return native_adapter_boundary_findings(root, configuration, matches_any)
    if kind == "non-normative-history-boundary":
        return non_normative_history_boundary_findings(root, configuration, matches_any)
    if kind == "forbidden-import":
        return python_import_findings(root, configuration, matches_any)
    if kind == "schema-reference-boundary":
        return schema_reference_findings(root, configuration, matches_any)
    if kind == "frontend-authority-boundary":
        return frontend_authority_boundary_findings(root, configuration, matches_any)
    if kind == "semantic-island-placement":
        return semantic_island_findings(
            root,
            configuration,
            changes,
            matches_any,
            architecture_declared,
        )
    if kind == "jvm-adapter-boundary":
        return jvm_adapter_boundary_findings(root, configuration, matches_any)
    if kind == "dotnet-adapter-boundary":
        return dotnet_adapter_boundary_findings(root, configuration, matches_any)
    if kind == "tracked-transition":
        return tracked_transition_findings(root, configuration, matches_any)
    if kind == "binding-semantic-path-boundary":
        return binding_semantic_path_findings(root, configuration, matches_any)
    if kind == "binding-route-coverage":
        return binding_route_coverage_findings(root, configuration)
    if kind == "artifact-authority-boundary":
        return artifact_authority_findings(configuration, artifact_registry)
    if kind == "ci-profile-routing":
        return ci_profile_routing_findings(root, configuration)
    return None
