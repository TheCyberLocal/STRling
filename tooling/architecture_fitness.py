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
    registered_paths = configuration["registered_paths"]
    assert isinstance(guarded, list)
    assert isinstance(semantic_names, list)
    assert isinstance(registered_paths, list)
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
        if matched and not matches_any(relative, registered_paths):
            findings.append(
                (
                    f"{relative}: unregistered semantic implementation island "
                    f"({', '.join(matched)}); expected an explicit registered path",
                    relative,
                )
            )
        elif matched and not architecture_declared:
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
    concrete_allowed = {
        str(relative)
        for relative in allowed_files
        if not any(character in str(relative) for character in "*?[")
    }
    for relative in sorted(concrete_allowed - actual):
        findings.append((f"{relative}: required historical data is missing", relative))
    for relative in sorted(
        path
        for path in actual
        if not matches_any(path, [str(item) for item in allowed_files])
    ):
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


def _identifier_words(identifier: str) -> tuple[str, ...]:
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", identifier)
    return tuple(
        word.casefold() for word in re.split(r"[^A-Za-z0-9]+", separated) if word
    )


def _identifier_word_stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return f"{word[:-3]}y"
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def _semantic_declaration_name(
    identifier: str, semantic_names: Sequence[object]
) -> str | None:
    words = _identifier_words(identifier)
    joined = "_".join(words)
    for semantic_name in semantic_names:
        semantic_words = _identifier_words(str(semantic_name))
        normalized = "_".join(semantic_words)
        word_match = all(
            any(
                word == semantic_word
                or (
                    len(semantic_word) > 2
                    and len(word) > 2
                    and (
                        _identifier_word_stem(word).startswith(
                            _identifier_word_stem(semantic_word)
                        )
                        or _identifier_word_stem(semantic_word).startswith(
                            _identifier_word_stem(word)
                        )
                    )
                )
                for word in words
            )
            for semantic_word in semantic_words
        )
        if normalized == joined or word_match:
            return str(semantic_name)
    return None


def source_declarations(path: Path) -> tuple[set[str], str | None]:
    """Extract declared source symbols without treating strings as implementation."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return set(), str(exc)
    if path.suffix.casefold() == ".py":
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            return set(), str(exc)
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }, None

    scrubbed = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    scrubbed = re.sub(r"(?m)//[^\n]*|#[^\n]*", " ", scrubbed)
    names: set[str] = set()
    patterns = (
        r"\b(?:class|interface|struct|enum|type|record|trait)\s+([A-Za-z_$][A-Za-z0-9_$]*)",
        r"\b(?:def|fn|fun|function|sub)\s+([A-Za-z_$][A-Za-z0-9_$]*)",
        r"\bfunc(?:\s+\([^)]*\))?\s+([A-Za-z_$][A-Za-z0-9_$]*)",
        r"(?m)^\s*([A-Za-z.][A-Za-z0-9._]*)\s*(?:<-|=)\s*function\s*\(",
    )
    for pattern in patterns:
        names.update(re.findall(pattern, scrubbed))
    return names, None


def _permitted_declarations(
    configuration: Mapping[str, object], relative: str
) -> set[str]:
    rows = configuration.get("permitted_declarations", [])
    assert isinstance(rows, list)
    permitted: set[str] = set()
    for row in rows:
        assert isinstance(row, dict)
        if row.get("path") != relative:
            continue
        names = row.get("names")
        assert isinstance(names, list)
        permitted.update(str(name).casefold() for name in names)
    return permitted


def binding_semantic_path_findings(
    root: Path,
    configuration: Mapping[str, object],
    matches_any: Match,
) -> list[Finding]:
    """Reject new binding-owned compiler stages while admitting exact facades."""

    sources = configuration["sources"]
    semantic_names = configuration["semantic_names"]
    excluded_path_parts = configuration["excluded_path_parts"]
    assert isinstance(sources, list)
    assert isinstance(semantic_names, list)
    assert isinstance(excluded_path_parts, list)
    source_suffixes = {
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
        ".kt",
        ".lua",
        ".mjs",
        ".php",
        ".pl",
        ".pm",
        ".py",
        ".r",
        ".rb",
        ".rs",
        ".swift",
        ".ts",
        ".tsx",
    }
    findings: list[Finding] = []
    for relative in candidate_paths(root):
        if not matches_any(relative, sources):
            continue
        path = Path(relative)
        parts = {part.casefold() for part in path.parts}
        if (
            parts.intersection(str(part).casefold() for part in excluded_path_parts)
            or path.suffix.casefold() not in source_suffixes
        ):
            continue
        if path.stem.casefold().startswith("test_") or path.stem.casefold().endswith(
            "_test"
        ):
            continue
        permitted = _permitted_declarations(configuration, relative)
        if binding_semantic_path_candidate(relative, configuration, matches_any):
            findings.append(
                (
                    f"{relative}: binding-owned semantic implementation path is "
                    "forbidden; expected a registered thin-adapter facade",
                    relative,
                )
            )
        declarations, error = source_declarations(root / relative)
        if error is not None:
            findings.append(
                (f"{relative}: cannot inspect adapter declarations: {error}", relative)
            )
            continue
        for declaration in sorted(declarations):
            semantic_name = _semantic_declaration_name(declaration, semantic_names)
            if semantic_name is None or declaration.casefold() in permitted:
                continue
            findings.append(
                (
                    f"{relative}: unregistered binding semantic declaration "
                    f"{declaration} matches {semantic_name}; expected marshalling, "
                    "transport, or result projection only",
                    relative,
                )
            )
    return findings


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
    """Require every registered product and transport to declare a canonical route."""

    manifest_relative = configuration["manifest"]
    toolchain_relative = configuration["toolchain"]
    allowed_transports = configuration["allowed_transports"]
    global_rule_ids = configuration["global_rule_ids"]
    assert isinstance(manifest_relative, str)
    assert isinstance(toolchain_relative, str)
    assert isinstance(allowed_transports, list)
    assert isinstance(global_rule_ids, list)
    try:
        registry = json.loads(
            (root / "governance/architecture-rules.json").read_text(encoding="utf-8")
        )
        manifest = json.loads((root / manifest_relative).read_text(encoding="utf-8"))
        toolchain = json.loads((root / toolchain_relative).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [(f"cannot inspect binding route rule registry: {error}", None)]
    rules = registry.get("rules") if isinstance(registry, dict) else None
    bindings = manifest.get("bindings") if isinstance(manifest, dict) else None
    transports = (
        manifest.get("supporting_transports") if isinstance(manifest, dict) else None
    )
    registered = toolchain.get("bindings") if isinstance(toolchain, dict) else None
    if (
        not isinstance(rules, list)
        or not isinstance(bindings, list)
        or not isinstance(transports, list)
        or not isinstance(registered, dict)
    ):
        return [("binding route registries are malformed", None)]

    findings: list[Finding] = []
    product_ids = [str(row.get("id")) for row in bindings if isinstance(row, dict)]
    transport_ids = [str(row.get("id")) for row in transports if isinstance(row, dict)]
    if len(product_ids) != len(bindings) or len(product_ids) != len(set(product_ids)):
        findings.append(
            ("binding route manifest has missing or duplicate product ids", None)
        )
    if len(transport_ids) != len(transports) or len(transport_ids) != len(
        set(transport_ids)
    ):
        findings.append(
            ("binding route manifest has missing or duplicate transport ids", None)
        )
    expected_products = [
        identifier for identifier in registered if identifier not in set(transport_ids)
    ]
    if product_ids != expected_products:
        findings.append(
            (
                "binding route coverage differs from toolchain registration: "
                f"expected {expected_products}, observed {product_ids}",
                None,
            )
        )
    if set(registered) - set(product_ids) - set(transport_ids):
        findings.append(
            (
                "every toolchain binding must be classified as a product route or "
                "supporting transport; observed unclassified registration set "
                f"{sorted(set(registered) - set(product_ids) - set(transport_ids))}",
                None,
            )
        )

    by_rule = {
        str(rule.get("id")): rule
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("id"), str)
    }
    route_rule_ids: list[str] = []
    for row in [*bindings, *transports]:
        if not isinstance(row, dict):
            continue
        identifier = str(row.get("id", "<missing>"))
        rule_id = str(row.get("route_rule_id", ""))
        route_rule_ids.append(rule_id)
        transport = row.get("canonical_transport")
        if transport not in allowed_transports:
            findings.append(
                (
                    f"{manifest_relative}: route {identifier} uses forbidden canonical "
                    f"transport {transport}; expected one of {allowed_transports}",
                    manifest_relative,
                )
            )
        if row.get("adapter_contract") != "thin":
            findings.append(
                (
                    f"{manifest_relative}: route {identifier} is not classified as a "
                    "thin adapter",
                    manifest_relative,
                )
            )
        rule = by_rule.get(rule_id)
        if rule is None:
            findings.append(
                (
                    f"{manifest_relative}: route {identifier} references missing "
                    f"architecture rule {rule_id}",
                    manifest_relative,
                )
            )
        elif rule.get("status") != "enforced":
            findings.append(
                (
                    f"{manifest_relative}: route {identifier} rule {rule_id} is not "
                    "enforced",
                    manifest_relative,
                )
            )

    required = manifest.get("required_architecture_rules", [])
    if not isinstance(required, list):
        findings.append(
            (f"{manifest_relative}: required rules must be an array", manifest_relative)
        )
    else:
        expected_rules = set(route_rule_ids) | {str(item) for item in global_rule_ids}
        if set(str(item) for item in required) != expected_rules:
            findings.append(
                (
                    f"{manifest_relative}: required architecture rules must derive "
                    "from every route plus global invariants; "
                    f"expected {sorted(expected_rules)}, observed {sorted(required)}",
                    manifest_relative,
                )
            )
        findings.extend(required_rule_status_findings(rules, required))
    return findings


def retired_dependency_findings(
    root: Path, configuration: Mapping[str, object]
) -> list[Finding]:
    """Keep dependencies removed with obsolete semantic machinery at zero."""

    manifests = configuration["dependency_manifests"]
    assert isinstance(manifests, list)
    findings: list[Finding] = []
    for row in manifests:
        assert isinstance(row, dict)
        relative = str(row["path"])
        forbidden = {str(item) for item in row["forbidden_dependencies"]}
        lockfiles = row.get("lockfiles", [])
        assert isinstance(lockfiles, list)
        try:
            manifest = json.loads((root / relative).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            findings.append(
                (f"{relative}: cannot inspect dependencies: {error}", relative)
            )
            continue
        declared: set[str] = set()
        for field in (
            "dependencies",
            "devDependencies",
            "optionalDependencies",
            "peerDependencies",
        ):
            values = manifest.get(field, {}) if isinstance(manifest, dict) else {}
            if isinstance(values, dict):
                declared.update(str(item) for item in values)
        for dependency in sorted(forbidden & declared):
            findings.append(
                (
                    f"{relative}: retired transitional dependency {dependency} is "
                    "declared; expected dependency population zero",
                    relative,
                )
            )
        for lock_relative in lockfiles:
            lock_path = str(lock_relative)
            try:
                lock = json.loads((root / lock_path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                findings.append(
                    (f"{lock_path}: cannot inspect dependency lock: {error}", lock_path)
                )
                continue
            packages = lock.get("packages", {}) if isinstance(lock, dict) else {}
            if not isinstance(packages, dict):
                findings.append(
                    (f"{lock_path}: package lock has no package map", lock_path)
                )
                continue
            for package_path in sorted(str(item) for item in packages):
                dependency = package_path.rsplit("node_modules/", 1)[-1]
                if dependency in forbidden:
                    findings.append(
                        (
                            f"{lock_path}: retired transitional dependency {dependency} "
                            f"remains at {package_path}; expected lock population zero",
                            lock_path,
                        )
                    )
    return findings


def retired_path_findings(
    root: Path, configuration: Mapping[str, object], matches_any: Match
) -> list[Finding]:
    patterns = configuration["forbidden_paths"]
    assert isinstance(patterns, list)
    return [
        (
            f"{relative}: retired architecture path is present; expected permanent absence",
            relative,
        )
        for relative in candidate_paths(root)
        if matches_any(relative, patterns)
    ]


def canonical_semantic_route_findings(root: Path) -> list[Finding]:
    """Reuse the canonical contract mapper to enforce stage ordering and separation."""

    try:
        try:
            from core_contract_validation import (
                ALLOWED_RUNTIME_DEPENDENCIES,
                load_mapping,
                runtime_dependencies,
                validate_mapping_document,
                validate_source_boundaries,
            )
        except ModuleNotFoundError:  # pragma: no cover - import path under tests
            from tooling.core_contract_validation import (
                ALLOWED_RUNTIME_DEPENDENCIES,
                load_mapping,
                runtime_dependencies,
                validate_mapping_document,
                validate_source_boundaries,
            )

        mapping = load_mapping(root / "core/contract-mapping.json")
        validate_mapping_document(mapping, root)
        sources = {
            path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted((root / "core/src").glob("**/*.rs"))
        }
        dependencies = runtime_dependencies(
            (root / "Cargo.toml").read_text(encoding="utf-8")
        )
        validate_source_boundaries(sources, dependencies)
        if dependencies != ALLOWED_RUNTIME_DEPENDENCIES:  # defensive clarity
            raise ValueError("canonical runtime dependency set changed")
    except Exception as error:
        return [
            (
                "canonical Semantic IR route violated: expected all frontends to "
                "converge before analysis/planning and all target serialization to "
                f"follow lowering; observed {error}",
                None,
            )
        ]
    return []


def profile_operation_coverage_findings(
    root: Path, configuration: Mapping[str, object]
) -> list[Finding]:
    toolchain_relative = str(configuration["toolchain"])
    producer_relative = str(configuration["producer_manifest"])
    required_operations = [str(item) for item in configuration["required_operations"]]
    findings: list[Finding] = []
    try:
        toolchain = json.loads((root / toolchain_relative).read_text(encoding="utf-8"))
        producer = json.loads((root / producer_relative).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [(f"cannot inspect architecture hardgate coverage: {error}", None)]
    policy = toolchain.get("policy", {}) if isinstance(toolchain, dict) else {}
    operation_registry = (
        policy.get("operation_registry", {}) if isinstance(policy, dict) else {}
    )
    profiles = policy.get("profiles", {}) if isinstance(policy, dict) else {}
    if not isinstance(operation_registry, dict) or not isinstance(profiles, dict):
        return [
            (
                f"{toolchain_relative}: operation/profile registry is malformed",
                toolchain_relative,
            )
        ]
    for operation in required_operations:
        if operation not in operation_registry:
            findings.append(
                (
                    f"{toolchain_relative}: required architecture hardgate "
                    f"{operation} is unregistered",
                    toolchain_relative,
                )
            )
    for profile_id, profile in profiles.items():
        members = (
            [
                entry.get("operation")
                for entry in profile.get("operations", [])
                if isinstance(entry, dict)
            ]
            if isinstance(profile, dict)
            else []
        )
        for operation in required_operations:
            if members.count(operation) != 1:
                findings.append(
                    (
                        f"{toolchain_relative}: profile {profile_id} must contain "
                        f"architecture hardgate {operation} exactly once; observed "
                        f"{members.count(operation)}",
                        toolchain_relative,
                    )
                )
    producers = producer.get("producers", []) if isinstance(producer, dict) else []
    producer_ids = [
        str(row.get("operation_id")) for row in producers if isinstance(row, dict)
    ]
    for operation in required_operations:
        if producer_ids.count(operation) != 1:
            findings.append(
                (
                    f"{producer_relative}: product certification must retain "
                    f"hardgate {operation} exactly once; observed "
                    f"{producer_ids.count(operation)}",
                    producer_relative,
                )
            )
    return findings


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
    """Require cloud CI to verify trusted local evidence without recomputation."""

    sources = configuration["sources"]
    assert isinstance(sources, list)
    expected_sources = {
        ".github/workflows/ci.yml",
        ".github/workflows/cd.yml",
        ".github/workflows/certification-integrity.yml",
    }
    findings: list[Finding] = []
    if set(sources) != expected_sources:
        findings.append(
            (
                "CI certification routing must govern manual profiles, delivery verification, and trusted integrity verification",
                None,
            )
        )

    upload_action = "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
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

    texts: dict[str, str] = {}
    for relative in sorted(expected_sources):
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                (f"{relative}: cannot inspect CI profile routing: {exc}", relative)
            )
            continue
        texts[relative] = text

    ci_text = texts.get(".github/workflows/ci.yml", "")
    for profile in ("local", "pull-request"):
        if profile not in ci_text:
            findings.append(
                (
                    f".github/workflows/ci.yml: missing manual {profile} profile",
                    ".github/workflows/ci.yml",
                )
            )
    for forbidden in ("schedule:", 'profile="full"', 'profile="release"'):
        if forbidden in ci_text:
            findings.append(
                (
                    f".github/workflows/ci.yml: cloud workflow retains expensive automatic routing fragment {forbidden}",
                    ".github/workflows/ci.yml",
                )
            )
    manual_invocation = './strling profile "$PROFILE" --artifact "$ARTIFACT_PATH"'
    if ci_text.count(manual_invocation) != 1:
        findings.append(
            (
                f".github/workflows/ci.yml: manual canonical profile invocation must be exactly {manual_invocation}",
                ".github/workflows/ci.yml",
            )
        )

    cd_text = texts.get(".github/workflows/cd.yml", "")
    if "./strling certification verify" not in cd_text:
        findings.append(
            (
                ".github/workflows/cd.yml: delivery must verify authoritative local certification",
                ".github/workflows/cd.yml",
            )
        )
    if "./strling profile release" in cd_text:
        findings.append(
            (
                ".github/workflows/cd.yml: delivery must not recompute the expensive Release profile",
                ".github/workflows/cd.yml",
            )
        )

    integrity_text = texts.get(".github/workflows/certification-integrity.yml", "")
    for fragment in (
        "pull_request_target:",
        "Checkout trusted verifier",
        "Checkout candidate evidence as data",
        "trusted/tooling/local_certification_attestation.py",
        "--repository-root candidate",
        "--trust-root trusted",
        "tests/certification/hardened-core/1.0/current",
    ):
        if fragment not in integrity_text:
            findings.append(
                (
                    f".github/workflows/certification-integrity.yml: missing trusted verification fragment {fragment}",
                    ".github/workflows/certification-integrity.yml",
                )
            )
    if re.search(r"candidate/(?:strling|tooling/[^ ]+\.py)\s", integrity_text):
        findings.append(
            (
                ".github/workflows/certification-integrity.yml: pull_request_target must not execute candidate code",
                ".github/workflows/certification-integrity.yml",
            )
        )
    for forbidden in (
        "profile full",
        "profile release",
        "adversarial_semantic_audit",
        "performance_resource_certification",
    ):
        if forbidden in integrity_text:
            findings.append(
                (
                    f".github/workflows/certification-integrity.yml: cheap verifier must not recompute {forbidden}",
                    ".github/workflows/certification-integrity.yml",
                )
            )

    for relative, text in texts.items():
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
    if kind == "retired-dependency-boundary":
        return retired_dependency_findings(root, configuration)
    if kind == "retired-path-boundary":
        return retired_path_findings(root, configuration, matches_any)
    if kind == "canonical-semantic-route":
        return canonical_semantic_route_findings(root)
    if kind == "profile-operation-coverage":
        return profile_operation_coverage_findings(root, configuration)
    if kind == "artifact-authority-boundary":
        return artifact_authority_findings(configuration, artifact_registry)
    if kind == "ci-profile-routing":
        return ci_profile_routing_findings(root, configuration)
    return None
