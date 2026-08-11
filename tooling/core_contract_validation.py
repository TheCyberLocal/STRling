#!/usr/bin/env python3
"""Certify the Rust kernel mapping against authoritative contract bytes."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    from core_stage_boundaries import (
        capability_evaluation_boundary_violation,
        compiler_pipeline_boundary_violation,
        diagnostic_generation_boundary_violation,
        kernel_boundary_violation,
        portability_pipeline_boundary_violation,
        portability_planning_boundary_violation,
        target_neutral_reverse_dependency_violation,
    )
except ModuleNotFoundError:  # pragma: no cover - import path differs under tests
    from tooling.core_stage_boundaries import (
        capability_evaluation_boundary_violation,
        compiler_pipeline_boundary_violation,
        diagnostic_generation_boundary_violation,
        kernel_boundary_violation,
        portability_pipeline_boundary_violation,
        portability_planning_boundary_violation,
        target_neutral_reverse_dependency_violation,
    )


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
    "capability_evaluation": "core/src/capability_evaluation.rs",
    "capability_pipeline": "core/src/capability_pipeline.rs",
    "compiler_pipeline": "core/src/compiler_pipeline.rs",
    "kernel": "core/src/kernel.rs",
    "conformance": "core/src/conformance/mod.rs",
    "diagnostic": "core/src/diagnostic/mod.rs",
    "diagnostic_generation": "core/src/diagnostic_generation.rs",
    "normalization": "core/src/normalization.rs",
    "portability_planning": "core/src/portability_planning.rs",
    "protocol::analysis": "core/src/protocol/analysis.rs",
    "protocol::exchange": "core/src/protocol/exchange.rs",
    "protocol::request": "core/src/protocol/request.rs",
    "protocol::result": "core/src/protocol/result.rs",
    "semantic": "core/src/semantic/mod.rs",
    "semantic_analysis": "core/src/semantic_analysis.rs",
    "safety_analysis": "core/src/safety_analysis.rs",
    "structural_analysis": "core/src/structural_analysis.rs",
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
            or len(modules) != len(set(modules))
        ):
            raise CoreContractError(
                f"{relative}: Rust modules must be a nonempty unique array"
            )
        for module in modules:
            module_path = MODULE_PATHS.get(module)
            if module_path is None or not (root / module_path).is_file():
                raise CoreContractError(
                    f"{relative}: mapped Rust module does not resolve: {module}"
                )
        if relative == "spec/contracts/1.0/compile-request.schema.json" and modules != [
            "kernel",
            "protocol::request",
        ]:
            raise CoreContractError(
                "compile request mapping must register the public kernel facade"
            )
        if relative == "spec/contracts/1.0/analysis.schema.json" and modules != [
            "protocol::analysis",
            "semantic_analysis",
            "structural_analysis",
            "safety_analysis",
            "diagnostic_generation",
        ]:
            raise CoreContractError(
                "analysis mapping must register semantic analysis, structural analysis, semantic safety analysis, and diagnostic generation in dependency order"
            )
        if relative == "spec/contracts/1.0/compile-result.schema.json" and modules != [
            "protocol::exchange",
            "protocol::result",
            "compiler_pipeline",
            "kernel",
        ]:
            raise CoreContractError(
                "compile result mapping must register the compiler pipeline and public facade"
            )
        if relative == "spec/contracts/1.0/diagnostic.schema.json" and modules != [
            "diagnostic",
            "diagnostic_generation",
        ]:
            raise CoreContractError(
                "diagnostic mapping must register canonical diagnostic generation"
            )
        if relative == "spec/contracts/1.0/portability.schema.json" and modules != [
            "protocol::analysis",
            "target",
            "portability_planning",
        ]:
            raise CoreContractError(
                "portability mapping must register canonical portability planning"
            )
        if relative == "spec/contracts/1.0/semantic-ir.schema.json" and modules != [
            "normalization",
            "semantic",
            "semantic_analysis",
            "structural_analysis",
            "safety_analysis",
            "diagnostic_generation",
            "capability_evaluation",
            "portability_planning",
        ]:
            raise CoreContractError(
                "Semantic IR mapping must register target-neutral stages, capability requirement extraction, and portability planning in dependency order"
            )
        if relative == "spec/contracts/1.0/target-profile.schema.json" and modules != [
            "target::profile",
            "capability_evaluation",
            "portability_planning",
        ]:
            raise CoreContractError(
                "target profile mapping must register factual capability evaluation and portability planning"
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
        "crate::semantic_analysis",
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

    analysis = "\n".join(
        text.lower()
        for path, text in source_texts.items()
        if path == "core/src/semantic_analysis.rs"
        or path.startswith("core/src/semantic_analysis/")
    )
    if "pub fn analyze(" not in analysis:
        raise CoreContractError(
            "canonical semantic analysis stage boundary cannot be located"
        )
    for forbidden in (
        "crate::normalization",
        "crate::target",
        "crate::protocol",
        "crate::diagnostic",
        "crate::conformance",
        "crate::emitter",
        "crate::emitters",
        "crate::bindings",
        "crate::frontend",
        "crate::lsp",
        "crate::editor",
        "bindings::",
        "frontend::",
        "emitters::",
        "std::env",
        "std::time",
        "systemtime",
        "thread_rng",
        "target_profile",
        "engine_options",
        "emitted_pattern",
        "portability_plan",
        "pcre2",
        "ecmascript",
        "python_re",
    ):
        if forbidden in analysis:
            raise CoreContractError(
                "semantic analysis violates pure target-neutral stage boundary: "
                f"{forbidden}"
            )

    structural = "\n".join(
        text.lower()
        for path, text in source_texts.items()
        if path == "core/src/structural_analysis.rs"
        or path.startswith("core/src/structural_analysis/")
    )
    if "pub fn analyze_structure(" not in structural:
        raise CoreContractError(
            "canonical structural analysis stage boundary cannot be located"
        )
    if "crate::semantic_analysis" not in structural:
        raise CoreContractError(
            "structural analysis must consume certified foundational semantic facts"
        )
    for forbidden in (
        "crate::normalization",
        "crate::target",
        "crate::protocol",
        "crate::diagnostic",
        "crate::conformance",
        "crate::emitter",
        "crate::emitters",
        "crate::bindings",
        "crate::frontend",
        "crate::lsp",
        "crate::editor",
        "crate::planner",
        "crate::portability",
        "crate::safety",
        "bindings::",
        "frontend::",
        "emitters::",
        "std::env",
        "std::time",
        "std::process",
        "std::thread",
        "systemtime",
        "thread_rng",
        "rand::",
        "target_profile",
        "engine_options",
        "emitted_pattern",
        "portability_plan",
        "portability_decision",
        "risk_severity",
        "redos",
        "pcre2",
        "ecmascript",
        "python_re",
    ):
        if forbidden in structural:
            raise CoreContractError(
                "structural analysis violates pure target-neutral stage boundary: "
                f"{forbidden}"
            )

    safety_entry = source_texts.get("core/src/safety_analysis.rs", "").lower()
    safety = "\n".join(
        text.lower()
        for path, text in source_texts.items()
        if path == "core/src/safety_analysis.rs"
        or path.startswith("core/src/safety_analysis/")
    )
    if "pub fn analyze_safety(" not in safety_entry:
        raise CoreContractError(
            "canonical semantic safety analysis stage boundary cannot be located"
        )
    if "crate::semantic_analysis" not in safety_entry:
        raise CoreContractError(
            "semantic safety analysis must consume certified foundational semantic facts"
        )
    if "crate::structural_analysis" not in safety_entry:
        raise CoreContractError(
            "semantic safety analysis must consume certified structural analysis facts"
        )
    for forbidden in (
        "crate::normalization",
        "crate::target",
        "crate::protocol",
        "crate::diagnostic",
        "crate::conformance",
        "crate::emitter",
        "crate::emitters",
        "crate::bindings",
        "crate::frontend",
        "crate::lsp",
        "crate::editor",
        "crate::planner",
        "crate::portability",
        "crate::parser",
        "bindings::",
        "frontend::",
        "emitters::",
        "std::env",
        "std::time",
        "std::process",
        "std::thread",
        "systemtime",
        "thread_rng",
        "rand::",
        "target_profile",
        "engine_options",
        "emitted_pattern",
        "portability_plan",
        "portability_decision",
        "risk_severity",
        "raw_source",
        "source_text",
        "regex_source",
        "parse_regex",
        "scan_regex",
        "redos",
        "pcre2",
        "ecmascript",
        "python_re",
    ):
        if forbidden in safety:
            raise CoreContractError(
                "semantic safety analysis violates pure target-neutral stage boundary: "
                f"{forbidden}"
            )

    for boundary_check in (
        target_neutral_reverse_dependency_violation,
        diagnostic_generation_boundary_violation,
        compiler_pipeline_boundary_violation,
        kernel_boundary_violation,
        capability_evaluation_boundary_violation,
        portability_planning_boundary_violation,
        portability_pipeline_boundary_violation,
    ):
        violation = boundary_check(source_texts)
        if violation is not None:
            raise CoreContractError(violation)


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
