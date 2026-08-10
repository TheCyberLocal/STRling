#!/usr/bin/env python3
"""Certify the Rust kernel mapping against authoritative contract bytes."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "core" / "contract-mapping.json"
CONTRACT_ROOT = ROOT / "spec" / "contracts" / "1.0"

EXPECTED_SCHEMAS = tuple(
    f"spec/contracts/1.0/{name}.schema.json"
    for name in (
        "analysis",
        "compile-request",
        "compile-result",
        "conformance-case",
        "conformance-manifest",
        "diagnostic",
        "portability",
        "semantic-ir",
        "source",
        "target-artifact",
        "target-profile",
    )
)
EXPECTED_FIXTURE_ROOTS = (
    "spec/contracts/1.0/examples",
    "spec/contracts/1.0/invalid",
    "spec/conformance",
    "spec/targets/profiles",
)
ALLOWED_RUNTIME_DEPENDENCIES = {"serde", "serde_json", "sha2"}
MODULE_PATHS = {
    "conformance": "core/src/conformance/mod.rs",
    "diagnostic": "core/src/diagnostic/mod.rs",
    "normalization": "core/src/normalization.rs",
    "protocol::analysis": "core/src/protocol/analysis.rs",
    "protocol::exchange": "core/src/protocol/exchange.rs",
    "protocol::request": "core/src/protocol/request.rs",
    "protocol::result": "core/src/protocol/result.rs",
    "semantic": "core/src/semantic/mod.rs",
    "source": "core/src/source/mod.rs",
    "target": "core/src/target/mod.rs",
    "target::profile": "core/src/target/profile.rs",
}


class CoreContractError(ValueError):
    """The kernel mapping or its architectural boundary is stale."""


def load_mapping(path: Path = MAPPING_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise CoreContractError("core mapping root must be an object")
    return value


def validate_mapping_document(
    mapping: Mapping[str, Any],
    root: Path = ROOT,
    content_overrides: Mapping[str, bytes] | None = None,
) -> int:
    expected_root_keys = {
        "mapping_version",
        "contract_suite",
        "schemas",
        "fixture_roots",
    }
    if set(mapping) != expected_root_keys:
        raise CoreContractError("core mapping has unknown or missing root fields")
    if mapping["mapping_version"] != "1.0.0":
        raise CoreContractError("unsupported core mapping version")
    if mapping["contract_suite"] != "1.0.0":
        raise CoreContractError("kernel must map certified contract suite 1.0.0")

    schemas = mapping["schemas"]
    if not isinstance(schemas, list):
        raise CoreContractError("schemas must be an array")
    paths = [entry.get("schema") for entry in schemas if isinstance(entry, dict)]
    if paths != list(EXPECTED_SCHEMAS):
        raise CoreContractError(
            "schema mappings must contain every canonical family exactly once in order"
        )
    overrides = content_overrides or {}
    for index, entry in enumerate(schemas):
        if not isinstance(entry, dict) or set(entry) != {
            "schema",
            "sha256",
            "rust_modules",
        }:
            raise CoreContractError(
                f"schema mapping {index} has unknown or missing fields"
            )
        relative = entry["schema"]
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise CoreContractError(f"mapped schema does not resolve: {relative}")
        content = overrides.get(relative, path.read_bytes())
        actual = hashlib.sha256(content).hexdigest()
        if entry["sha256"] != actual:
            raise CoreContractError(f"Rust mapping fingerprint is stale for {relative}")
        modules = entry["rust_modules"]
        if (
            not isinstance(modules, list)
            or not modules
            or modules != sorted(set(modules))
        ):
            raise CoreContractError(
                f"{relative}: Rust modules must be a nonempty unique sorted array"
            )
        for module in modules:
            module_path = MODULE_PATHS.get(module)
            if module_path is None or not (root / module_path).is_file():
                raise CoreContractError(
                    f"{relative}: mapped Rust module does not resolve: {module}"
                )
        if relative == "spec/contracts/1.0/semantic-ir.schema.json" and modules != [
            "normalization",
            "semantic",
        ]:
            raise CoreContractError(
                "Semantic IR mapping must include the canonical normalization stage"
            )

    fixture_roots = mapping["fixture_roots"]
    if fixture_roots != list(EXPECTED_FIXTURE_ROOTS):
        raise CoreContractError(
            "canonical fixture roots changed without mapping review"
        )
    for relative in fixture_roots:
        if not (root / relative).is_dir():
            raise CoreContractError(f"fixture root does not resolve: {relative}")
    return len(schemas)


def runtime_dependencies(cargo_manifest: str) -> set[str]:
    dependencies: set[str] = set()
    in_dependencies = False
    for raw_line in cargo_manifest.splitlines():
        line = raw_line.strip()
        if line == "[dependencies]":
            in_dependencies = True
            continue
        if line.startswith("[") and line.endswith("]"):
            in_dependencies = False
            continue
        if in_dependencies and line and not line.startswith("#"):
            match = re.match(r"([A-Za-z0-9_-]+)\s*=", line)
            if match:
                dependencies.add(match.group(1))
    return dependencies


def validate_source_boundaries(
    source_texts: Mapping[str, str], dependencies: set[str]
) -> None:
    if dependencies != ALLOWED_RUNTIME_DEPENDENCIES:
        raise CoreContractError(
            "kernel runtime dependencies must remain exactly serde, serde_json, and sha2"
        )
    joined = "\n".join(source_texts.values())
    for forbidden in (
        "std::fs",
        "std::net",
        "std::path",
        "tokio::",
        "reqwest::",
        "bindings/",
        "bindings::",
        "tooling/",
    ):
        if forbidden in joined:
            raise CoreContractError(
                f"kernel source violates deterministic dependency boundary: {forbidden}"
            )

    semantic = source_texts.get("core/src/semantic/mod.rs", "").lower()
    for forbidden in (
        "pcre2",
        "ecmascript",
        "python_re",
        "engine_options",
        "emitted_pattern",
        "target_profile",
    ):
        if forbidden in semantic:
            raise CoreContractError(
                f"Semantic IR contains target-specific marker: {forbidden}"
            )
    node_start = semantic.find("pub enum node")
    node_end = semantic.find("impl node", node_start)
    if node_start < 0 or node_end < 0:
        raise CoreContractError("Semantic IR Node union cannot be located")
    node_union = semantic[node_start:node_end]
    for derived in (
        "nullable",
        "length_bounds",
        "feature_requirements",
        "overlap",
        "safety_analysis",
    ):
        if derived in node_union:
            raise CoreContractError(
                f"Semantic IR node embeds derived analysis: {derived}"
            )

    normalization = source_texts.get("core/src/normalization.rs", "").lower()
    if "pub fn normalize(" not in normalization:
        raise CoreContractError(
            "canonical normalization stage boundary cannot be located"
        )
    for forbidden in (
        "crate::target",
        "crate::protocol",
        "crate::diagnostic",
        "crate::conformance",
        "std::env",
        "std::time",
        "systemtime",
        "thread_rng",
        "target_profile",
        "engine_options",
        "emitted_pattern",
        "pcre2",
        "ecmascript",
        "python_re",
    ):
        if forbidden in normalization:
            raise CoreContractError(
                "normalization violates pure target-neutral stage boundary: "
                f"{forbidden}"
            )
    for derived in (
        "nullable",
        "length_bounds",
        "feature_requirements",
        "overlap",
        "safety_analysis",
    ):
        if derived in normalization:
            raise CoreContractError(f"normalization embeds derived analysis: {derived}")


def canonical_fixture_paths(root: Path = ROOT) -> set[Path]:
    paths = {
        *sorted((CONTRACT_ROOT / "examples").glob("**/*.json")),
        *sorted((CONTRACT_ROOT / "invalid").glob("**/*.json")),
        *sorted((root / "spec" / "targets" / "profiles").glob("*.json")),
        *sorted((root / "spec" / "conformance" / "cases").glob("*.json")),
        root / "spec" / "conformance" / "manifest.json",
    }
    return {path.resolve() for path in paths}


def referenced_fixture_paths(root: Path = ROOT) -> set[Path]:
    references: set[Path] = set()
    pattern = re.compile(r'include_str!\s*\(\s*"([^"]+)"\s*\)')
    for test in sorted((root / "core" / "tests").glob("*.rs")):
        for relative in pattern.findall(test.read_text(encoding="utf-8")):
            resolved = (test.parent / relative).resolve()
            if "/tests/spec/" in resolved.as_posix():
                raise CoreContractError(
                    f"kernel test treats legacy fixture as authority: {test}"
                )
            if resolved.suffix == ".json":
                references.add(resolved)
    return references


def validate_fixture_coverage(root: Path = ROOT) -> int:
    expected = canonical_fixture_paths(root)
    actual = referenced_fixture_paths(root)
    if expected != actual:
        missing = sorted(
            path.relative_to(root).as_posix() for path in expected - actual
        )
        extra = sorted(path.relative_to(root).as_posix() for path in actual - expected)
        raise CoreContractError(
            f"kernel fixture coverage drifted; missing={missing}, extra={extra}"
        )
    return len(expected)


def validate_repository(root: Path = ROOT) -> tuple[int, int]:
    mapping = load_mapping(root / "core" / "contract-mapping.json")
    schema_count = validate_mapping_document(mapping, root)
    sources = {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((root / "core" / "src").glob("**/*.rs"))
    }
    dependencies = runtime_dependencies(
        (root / "core" / "Cargo.toml").read_text(encoding="utf-8")
    )
    validate_source_boundaries(sources, dependencies)
    fixture_count = validate_fixture_coverage(root)
    return schema_count, fixture_count


def main() -> int:
    try:
        schemas, fixtures = validate_repository()
    except (CoreContractError, OSError, json.JSONDecodeError) as error:
        print(f"CORE_CONTRACTS status=failed error={error}")
        return 1
    print(f"CORE_CONTRACTS status=passed schema_mappings={schemas} fixtures={fixtures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
