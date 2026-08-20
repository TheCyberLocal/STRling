#!/usr/bin/env python3
"""Certify the TypeScript/Python Simply Preview adapter boundary."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = Path("spec/frontends/simply/1.1/protocol.json")
LEGACY_PROTOCOL = Path("spec/frontends/simply/1.0/protocol.json")
RESPONSE_SCHEMA = Path("spec/frontends/simply/1.1/adapter-response.schema.json")
LEGACY_RESPONSE_SCHEMA = Path("spec/frontends/simply/1.0/adapter-response.schema.json")
COMPATIBILITY = Path("governance/baselines/simply-preview-adapter-compatibility.json")
HISTORICAL_BASELINE = Path("tests/adapters/2.0/legacy-baseline.json")
TYPESCRIPT_PREVIEW = Path("bindings/typescript/src/STRling/simply/preview.ts")
PYTHON_PREVIEW = Path("bindings/python/src/STRling/simply/preview.py")
FINGERPRINT_INPUTS = (
    PROTOCOL,
    LEGACY_PROTOCOL,
    RESPONSE_SCHEMA,
    LEGACY_RESPONSE_SCHEMA,
    TYPESCRIPT_PREVIEW,
    PYTHON_PREVIEW,
)


class AdapterContractError(RuntimeError):
    """A deterministic adapter contract failure."""


def load_json(root: Path, path: Path) -> Any:
    try:
        return json.loads((root / path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdapterContractError(f"{path}: {error}") from error


def source_fingerprint(root: Path, sources: dict[str, str] | None = None) -> str:
    digest = hashlib.sha256()
    for path in FINGERPRINT_INPUTS:
        relative = path.as_posix()
        if sources is not None and relative in sources:
            data = sources[relative].encode("utf-8")
        else:
            data = (root / path).read_bytes()
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def protocol_operations(protocol: dict[str, Any], location: str) -> set[str]:
    operations = protocol.get("operations")
    if not isinstance(operations, list):
        raise AdapterContractError(f"{location} operations must be an array")
    found = {entry.get("id") for entry in operations if isinstance(entry, dict)}
    if None in found or len(found) != len(operations):
        raise AdapterContractError(f"{location} operations must have unique IDs")
    return {str(operation) for operation in found}


def protocol_errors(protocol: dict[str, Any]) -> set[str]:
    errors = protocol.get("errors")
    if not isinstance(errors, list):
        raise AdapterContractError("protocol errors must be an array")
    return {
        str(entry["code"])
        for entry in errors
        if isinstance(entry, dict) and "code" in entry
    }


def typescript_recorded_operations(source: str) -> set[str]:
    return set(
        re.findall(
            r'this\.append\(\s*stepId\s*,\s*"([a-z_]+)"',
            source,
            flags=re.DOTALL,
        )
    )


def python_recorded_operations(source: str) -> set[str]:
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "_append":
            continue
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
            operation = node.args[1].value
            if isinstance(operation, str):
                found.add(operation)
    return found


def flatten_inventory(compatibility: dict[str, Any], host: str) -> set[str]:
    surfaces = compatibility.get("surfaces")
    if not isinstance(surfaces, list):
        raise AdapterContractError("compatibility surfaces must be an array")
    matching = [
        surface
        for surface in surfaces
        if isinstance(surface, dict) and surface.get("host") == host
    ]
    if len(matching) != 1:
        raise AdapterContractError(f"{host}: expected exactly one inventory")
    groups = matching[0].get("groups")
    if not isinstance(groups, list):
        raise AdapterContractError(f"{host}: groups must be an array")
    allowed = set(compatibility.get("dispositions", []))
    operations: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            raise AdapterContractError(f"{host}: group must be an object")
        disposition = group.get("disposition")
        if disposition not in allowed:
            raise AdapterContractError(f"{host}: invalid disposition {disposition!r}")
        listed = group.get("operations")
        if not isinstance(listed, list) or not all(
            isinstance(operation, str) for operation in listed
        ):
            raise AdapterContractError(f"{host}: operations must be a string array")
        operations.extend(listed)
    if len(operations) != len(set(operations)):
        raise AdapterContractError(f"{host}: duplicate operation disposition")
    return set(operations)


def historical_sources(root: Path) -> dict[str, str]:
    """Read and authenticate the immutable P17-T03 task-start sources."""

    baseline = load_json(root, HISTORICAL_BASELINE)
    files = baseline.get("historical_source_files")
    if not isinstance(files, list):
        raise AdapterContractError("historical source bundle is missing")
    sources: dict[str, str] = {}
    for entry in files:
        if not isinstance(entry, dict):
            raise AdapterContractError("historical source entry must be an object")
        relative = entry.get("path")
        encoded = entry.get("content_base64")
        expected = entry.get("sha256")
        if not all(isinstance(value, str) for value in (relative, encoded, expected)):
            raise AdapterContractError("historical source entry is incomplete")
        assert isinstance(relative, str)
        assert isinstance(encoded, str)
        assert isinstance(expected, str)
        if relative in sources:
            raise AdapterContractError(f"duplicate historical source: {relative}")
        try:
            content = base64.b64decode(encoded, validate=True)
            source = content.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as error:
            raise AdapterContractError(
                f"historical source is not valid encoded UTF-8: {relative}"
            ) from error
        actual = f"sha256:{hashlib.sha256(content).hexdigest()}"
        if actual != expected:
            raise AdapterContractError(
                f"historical source content fingerprint mismatch: {relative}"
            )
        sources[relative] = source
    return sources


def source_text(root: Path, relative: str, sources: dict[str, str] | None) -> str:
    if sources is None:
        return (root / relative).read_text(encoding="utf-8")
    try:
        return sources[relative]
    except KeyError as error:
        raise AdapterContractError(
            f"historical source bundle is missing {relative}"
        ) from error


def exported_typescript_legacy_operations(
    root: Path, sources: dict[str, str] | None = None
) -> set[str]:
    base = "bindings/typescript/src/STRling"
    functions: set[str] = {"lit"}
    for relative in (
        "simply/constructors.ts",
        "simply/lookarounds.ts",
        "simply/sets.ts",
        "simply/static.ts",
        "compiler.ts",
    ):
        source = source_text(root, f"{base}/{relative}", sources)
        functions.update(
            re.findall(
                r"^export\s+(?:async\s+)?function\s+([A-Za-z][A-Za-z0-9]*)\s*\(",
                source,
                flags=re.MULTILINE,
            )
        )
    pattern = source_text(root, f"{base}/simply/pattern.ts", sources)
    error_block = pattern[
        pattern.index("export class STRlingError") : pattern.index("export const lit")
    ]
    pattern_block = pattern[pattern.index("export class Pattern") :]
    error_methods = re.findall(
        r"^\s{4}(?:public\s+|static\s+)?([A-Za-z][A-Za-z0-9]*)\s*\(",
        error_block,
        flags=re.MULTILINE,
    )
    pattern_methods = re.findall(
        r"^\s{4}(?:public\s+|static\s+)?([A-Za-z][A-Za-z0-9]*)\s*\(",
        pattern_block,
        flags=re.MULTILINE,
    )
    functions.update(f"STRlingError.{name}" for name in error_methods)
    functions.update(f"Pattern.{name}" for name in pattern_methods)
    return functions


def literal_all(module: ast.Module) -> list[str]:
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return value
    raise AdapterContractError("Python Simply __all__ must be a literal list")


def exported_python_legacy_operations(
    root: Path, sources: dict[str, str] | None = None
) -> set[str]:
    init_source = source_text(
        root, "bindings/python/src/STRling/simply/__init__.py", sources
    )
    preview_source = source_text(root, PYTHON_PREVIEW.as_posix(), sources)
    exported = set(literal_all(ast.parse(init_source)))
    preview_exports = set(literal_all(ast.parse(preview_source)))
    init_tree = ast.parse(init_source)
    canonical_exports: set[str] = set()
    for node in init_tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "STRling.simply.stdlib_generated":
            continue
        canonical_exports.update(alias.asname or alias.name for alias in node.names)
    functions = (
        exported - preview_exports - canonical_exports - {"Pattern", "STRlingError"}
    )

    pattern_tree = ast.parse(
        source_text(root, "bindings/python/src/STRling/simply/pattern.py", sources)
    )
    for node in pattern_tree.body:
        if not isinstance(node, ast.ClassDef) or node.name not in {
            "Pattern",
            "STRlingError",
        }:
            continue
        for member in node.body:
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if member.name.startswith("__") and member.name not in {
                    "__init__",
                    "__call__",
                    "__str__",
                }:
                    continue
                functions.add(f"{node.name}.{member.name}")
    return functions


def validate_response_schema(
    schema: dict[str, Any],
    expected_errors: set[str],
    expected_protocol_version: str,
) -> None:
    try:
        from jsonschema import Draft202012Validator

        Draft202012Validator.check_schema(schema)
    except ImportError as error:
        raise AdapterContractError("jsonschema is required") from error
    except Exception as error:
        raise AdapterContractError(f"invalid response schema: {error}") from error
    definitions = schema.get("$defs", {})
    try:
        actual_errors = set(definitions["Error"]["properties"]["code"]["enum"])
        request_ref = definitions["Success"]["properties"]["compile_request"]["$ref"]
        result_ref = definitions["Success"]["properties"]["compile_result"]["$ref"]
        success_version = definitions["Success"]["properties"]["protocol_version"][
            "const"
        ]
        failure_version = definitions["Failure"]["properties"]["protocol_version"][
            "const"
        ]
    except (KeyError, TypeError) as error:
        raise AdapterContractError(
            "response schema is missing canonical bindings"
        ) from error
    if actual_errors != expected_errors:
        raise AdapterContractError("response error inventory drifted")
    if {success_version, failure_version} != {expected_protocol_version}:
        raise AdapterContractError("response protocol version drifted")
    if not request_ref.endswith("/compile-request.schema.json"):
        raise AdapterContractError("response must bind canonical CompileRequest")
    if not result_ref.endswith("/compile-result.schema.json"):
        raise AdapterContractError("response must bind canonical CompileResult")


def validate_architecture(typescript_source: str, python_source: str) -> None:
    forbidden = {
        "typescript": (
            "../core/",
            "../emitters/",
            "../compiler",
            "process.env",
            "new RegExp",
        ),
        "python": (
            "STRling.core",
            "STRling.emitters",
            "os.environ",
            "features.json",
            "import re",
        ),
    }
    for label, source in (
        ("typescript", typescript_source),
        ("python", python_source),
    ):
        found = [token for token in forbidden[label] if token in source]
        if found:
            raise AdapterContractError(f"{label}: forbidden Preview authority {found}")


def validate_protocol_versions(
    typescript_source: str,
    python_source: str,
    current_version: str,
    legacy_version: str,
) -> None:
    expected = {
        "typescript": (
            f'SIMPLY_PREVIEW_PROTOCOL_VERSION = "{current_version}"',
            f'SIMPLY_PREVIEW_LEGACY_PROTOCOL_VERSION = "{legacy_version}"',
        ),
        "python": (
            f'SIMPLY_PREVIEW_PROTOCOL_VERSION = "{current_version}"',
            f'SIMPLY_PREVIEW_LEGACY_PROTOCOL_VERSION = "{legacy_version}"',
        ),
    }
    for label, source in (
        ("typescript", typescript_source),
        ("python", python_source),
    ):
        missing = [token for token in expected[label] if token not in source]
        if missing:
            raise AdapterContractError(f"{label}: protocol version constants drifted")


def certify(root: Path = ROOT) -> dict[str, Any]:
    protocol = load_json(root, PROTOCOL)
    legacy_protocol = load_json(root, LEGACY_PROTOCOL)
    compatibility = load_json(root, COMPATIBILITY)
    response_schema = load_json(root, RESPONSE_SCHEMA)
    legacy_response_schema = load_json(root, LEGACY_RESPONSE_SCHEMA)
    typescript_source = (root / TYPESCRIPT_PREVIEW).read_text(encoding="utf-8")
    python_source = (root / PYTHON_PREVIEW).read_text(encoding="utf-8")
    frozen_sources = historical_sources(root)
    operations = protocol_operations(protocol, "current protocol")
    legacy_operations = protocol_operations(legacy_protocol, "legacy protocol")
    protocol_version = str(protocol.get("protocol_version"))
    legacy_protocol_version = str(legacy_protocol.get("protocol_version"))

    if legacy_operations - operations or operations - legacy_operations != {
        "stdlib_helper"
    }:
        raise AdapterContractError(
            "Simply 1.1 must add exactly stdlib_helper to immutable Simply 1.0"
        )
    if compatibility.get("protocol_version") != protocol_version:
        raise AdapterContractError("compatibility evidence protocol version is stale")

    if typescript_recorded_operations(typescript_source) != operations:
        raise AdapterContractError("TypeScript Preview operation inventory drifted")
    if python_recorded_operations(python_source) != operations:
        raise AdapterContractError("Python Preview operation inventory drifted")
    if flatten_inventory(
        compatibility, "typescript"
    ) != exported_typescript_legacy_operations(root, frozen_sources):
        raise AdapterContractError(
            "TypeScript historical public-operation inventory drifted"
        )
    if flatten_inventory(compatibility, "python") != exported_python_legacy_operations(
        root, frozen_sources
    ):
        raise AdapterContractError(
            "Python historical public-operation inventory drifted"
        )
    unresolved = compatibility.get("unresolved")
    if unresolved != []:
        raise AdapterContractError(
            "compatibility inventory contains unresolved operations"
        )
    validate_response_schema(
        response_schema, protocol_errors(protocol), protocol_version
    )
    validate_response_schema(
        legacy_response_schema,
        protocol_errors(legacy_protocol),
        legacy_protocol_version,
    )
    validate_protocol_versions(
        typescript_source,
        python_source,
        protocol_version,
        legacy_protocol_version,
    )
    validate_architecture(typescript_source, python_source)
    report = {
        "protocol_version": protocol_version,
        "legacy_protocol_version": legacy_protocol_version,
        "operation_count": len(operations),
        "legacy_operation_count": len(legacy_operations),
        "additive_operation_count": len(operations - legacy_operations),
        "error_count": len(protocol_errors(protocol)),
        "typescript_legacy_operation_count": len(
            exported_typescript_legacy_operations(root, frozen_sources)
        ),
        "python_legacy_operation_count": len(
            exported_python_legacy_operations(root, frozen_sources)
        ),
        "source_fingerprint": source_fingerprint(root, frozen_sources),
    }
    expected_evidence = compatibility.get("evidence")
    actual_evidence = {
        "protocol_operation_count": report["operation_count"],
        "stable_error_count": report["error_count"],
        "typescript_legacy_operation_count": report[
            "typescript_legacy_operation_count"
        ],
        "python_legacy_operation_count": report["python_legacy_operation_count"],
        "source_fingerprint": report["source_fingerprint"],
    }
    if expected_evidence != actual_evidence:
        raise AdapterContractError("adapter evidence fingerprint or counts are stale")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        report = certify()
    except (AdapterContractError, OSError) as error:
        print(f"Simply adapter contract: FAILED: {error}", file=sys.stderr)
        return 1
    if arguments.json:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    else:
        print("Simply adapter contract: PASSED")
        for key, value in report.items():
            print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
