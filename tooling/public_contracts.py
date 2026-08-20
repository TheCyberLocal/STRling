#!/usr/bin/env python3
"""Extract, compare, and verify STRling public compatibility snapshots."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

try:
    from contract_declarations import (
        DeclarationError,
        detect_base_changes,
        load_active_task,
        validate_change_declarations,
    )
except ModuleNotFoundError:  # pragma: no cover - import path differs under tests
    from tooling.contract_declarations import (
        DeclarationError,
        detect_base_changes,
        load_active_task,
        validate_change_declarations,
    )


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "governance/public-surfaces.json"
DEFAULT_CONTROL = ROOT / "governance/change-control.json"
REGISTRY_SCHEMA = ROOT / "governance/schemas/public-surface-registry.schema.json"
CLASSIFICATION_ORDER = {
    "unchanged": 0,
    "compatible": 1,
    "additive": 2,
    "breaking": 3,
}
METADATA_KEYS = {"$comment", "description", "examples", "title"}
TIGHTENING_MINIMUMS = {"minItems", "minLength", "minProperties", "minimum"}
TIGHTENING_MAXIMUMS = {"maxItems", "maxLength", "maxProperties", "maximum"}


class ContractError(ValueError):
    """Raised when a public contract cannot be extracted or trusted."""


@dataclass
class Comparison:
    classification: str
    findings: list[str] = field(default_factory=list)


@dataclass
class SurfaceResult:
    surface: str
    component: str
    status: str
    classification: str = "unchanged"
    snapshot_path: str | None = None
    findings: list[str] = field(default_factory=list)
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "component": self.component,
            "status": self.status,
            "classification": self.classification,
            "snapshot_path": self.snapshot_path,
            "findings": self.findings,
            "reason": self.reason,
        }


Runner = Callable[..., subprocess.CompletedProcess[str]]


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read {path}: {exc}") from exc


def load_registry(path: Path, schema_path: Path = REGISTRY_SCHEMA) -> dict[str, object]:
    registry = load_json(path)
    schema = load_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(registry)
    except (SchemaError, ValidationError) as exc:
        raise ContractError(
            f"malformed public-surface registry: {exc.message}"
        ) from exc
    assert isinstance(registry, dict)
    surfaces = registry["surfaces"]
    assert isinstance(surfaces, list)
    identifiers = [
        str(surface["id"]) for surface in surfaces if isinstance(surface, dict)
    ]
    if len(identifiers) != len(set(identifiers)):
        raise ContractError("public-surface identifiers must be unique")
    snapshots = [
        str(surface["snapshot_path"])
        for surface in surfaces
        if isinstance(surface, dict)
    ]
    if len(snapshots) != len(set(snapshots)):
        raise ContractError("public-surface snapshot paths must be unique")
    return registry


def canonical_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_c_comments(value: str) -> str:
    value = re.sub(r"/\*.*?\*/", " ", value, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", " ", value)


def extract_c_header(surface: Mapping[str, object], root: Path) -> dict[str, object]:
    locations = surface["source_locations"]
    assert isinstance(locations, list) and locations
    defines: list[str] = []
    declarations: list[str] = []
    for location in locations:
        path = root / str(location)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ContractError(f"cannot read C public header {path}: {exc}") from exc
        for line in text.splitlines():
            match = re.match(
                r"\s*#\s*define\s+([A-Za-z_]\w*)(?:\([^)]*\))?\s+(.*)", line
            )
            if match and not match.group(1).endswith("_H"):
                defines.append(
                    canonical_space(f"#define {match.group(1)} {match.group(2)}")
                )
        text = strip_c_comments(text)
        text = re.sub(r"^\s*#.*$", " ", text, flags=re.MULTILINE)
        text = re.sub(r'extern\s+"C"\s*\{', " ", text)
        buffer: list[str] = []
        braces = 0
        parentheses = 0
        for character in text:
            buffer.append(character)
            if character == "{":
                braces += 1
            elif character == "}":
                braces = max(0, braces - 1)
            elif character == "(":
                parentheses += 1
            elif character == ")":
                parentheses = max(0, parentheses - 1)
            elif character == ";" and braces == 0 and parentheses == 0:
                declaration = canonical_space("".join(buffer))
                buffer.clear()
                if declaration and declaration != ";":
                    declarations.append(declaration)
    symbols = {item: item for item in sorted(set(defines + declarations))}
    if not symbols:
        raise ContractError("no C declarations were extracted from installed headers")
    return snapshot(str(surface["id"]), "declarations", symbols)


def cpp_declaration_units(text: str, label: str) -> dict[str, str]:
    """Normalize public C++ namespace, type, function, and member declarations."""

    text = strip_c_comments(text)
    text = re.sub(r"^\s*#.*$", " ", text, flags=re.MULTILINE)
    contexts: list[dict[str, object]] = []
    buffer: list[str] = []
    parentheses = 0
    brackets = 0
    quote: str | None = None
    escaped = False
    symbols: dict[str, str] = {}

    def visible() -> bool:
        return all(bool(context["public"]) for context in contexts)

    def add(value: str) -> None:
        declaration = canonical_space(value)
        if not declaration or not visible():
            return
        names = [
            str(context["header"])
            for context in contexts
            if context["kind"] in {"namespace", "class", "struct"}
        ]
        key = " :: ".join([label, *names, declaration])
        symbols[key] = declaration

    for character in text:
        if quote is not None:
            buffer.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
            buffer.append(character)
            continue
        if character == "(":
            parentheses += 1
        elif character == ")":
            parentheses = max(0, parentheses - 1)
        elif character == "[":
            brackets += 1
        elif character == "]":
            brackets = max(0, brackets - 1)
        if character == ":" and parentheses == 0 and brackets == 0:
            access = canonical_space("".join(buffer))
            if access in {"public", "private", "protected"}:
                buffer.clear()
                for context in reversed(contexts):
                    if context["kind"] in {"class", "struct"}:
                        context["public"] = access == "public"
                        break
                continue
        if character == "{" and parentheses == 0 and brackets == 0:
            header = canonical_space("".join(buffer))
            buffer.clear()
            if header.startswith("namespace "):
                add(header)
                contexts.append(
                    {"header": header, "kind": "namespace", "public": visible()}
                )
            elif re.search(r"(?:^|\s)class\s+[A-Za-z_]", header):
                add(header)
                contexts.append({"header": header, "kind": "class", "public": False})
            elif re.search(r"(?:^|\s)struct\s+[A-Za-z_]", header):
                add(header)
                contexts.append(
                    {"header": header, "kind": "struct", "public": visible()}
                )
            else:
                add(header)
                contexts.append({"header": header, "kind": "body", "public": False})
            continue
        if character == "}" and parentheses == 0 and brackets == 0:
            if visible():
                add("".join(buffer))
            buffer.clear()
            if contexts:
                contexts.pop()
            continue
        if character == ";" and parentheses == 0 and brackets == 0:
            add("".join(buffer))
            buffer.clear()
            continue
        buffer.append(character)
    add("".join(buffer))
    return symbols


def extract_cpp_headers(surface: Mapping[str, object], root: Path) -> dict[str, object]:
    locations = surface["source_locations"]
    assert isinstance(locations, list) and locations
    location_set = {str(location) for location in locations}
    symbols: dict[str, str] = {}
    combined: list[str] = []
    for location in locations:
        relative = str(location)
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ContractError(f"cannot read C++ public header {path}: {exc}") from exc
        combined.append(text)
        for include in re.findall(
            r'^\s*#\s*include\s+"(strling/[^\"]+)"', text, re.MULTILINE
        ):
            included = f"bindings/cpp/include/{include}"
            if included not in location_set:
                raise ContractError(
                    f"C++ installed header closure omits included header {included}"
                )
        symbols.update(cpp_declaration_units(text, Path(relative).name))
    declaration_text = "\n".join(combined)
    required = [
        "class response final",
        "response(const response &) = delete",
        "response(response &&other) noexcept",
        "class client final",
        "class pattern final",
        "pattern(const pattern &) = delete",
        "pattern(pattern &&other) noexcept",
        "pattern merge(std::vector<pattern> values)",
        "simply::pattern email()",
        "simply::pattern date_time()",
    ]
    missing = [item for item in required if item not in declaration_text]
    if missing:
        raise ContractError(f"C++ public adapter closure is missing {missing}")
    retired = [
        "strling/ast.hpp",
        "strling/compiler.hpp",
        "strling/core/",
        "strling/ir.hpp",
    ]
    present = [item for item in retired if item in declaration_text]
    if present:
        raise ContractError(f"C++ public adapter closure retains {present}")
    if not symbols:
        raise ContractError("no C++ declarations were extracted from installed headers")
    return snapshot(str(surface["id"]), "cpp-declarations", symbols)


def _balanced_rust_block(text: str, opening: int, description: str) -> int:
    depth = 0
    for index in range(opening, len(text)):
        character = text[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ContractError(f"unbalanced Rust {description}")


def _rust_public_structs(text: str) -> dict[str, str]:
    symbols: dict[str, str] = {}
    for match in re.finditer(r"(?m)^pub struct ([A-Za-z_][A-Za-z0-9_]*)\s*", text):
        name = match.group(1)
        opening = text.find("{", match.end())
        semicolon = text.find(";", match.end())
        if semicolon >= 0 and (opening < 0 or semicolon < opening):
            declaration = canonical_space(text[match.start() : semicolon + 1])
        elif opening >= 0:
            end = _balanced_rust_block(text, opening, f"struct {name}")
            body = text[opening + 1 : end - 1]
            fields = [
                canonical_space(field.group(0))
                for field in re.finditer(
                    r"(?m)^\s*pub [a-z_][A-Za-z0-9_]*:\s*[^,\n]+,\s*$",
                    body,
                )
            ]
            declaration = canonical_space(
                f"pub struct {name} {{ {' '.join(fields)} }}"
                if fields
                else f"pub struct {name};"
            )
        else:
            raise ContractError(f"Rust public struct {name} has no body")
        symbols[f"struct:{name}"] = declaration
    return symbols


def _rust_public_methods(text: str) -> dict[str, str]:
    symbols: dict[str, str] = {}
    for implementation in re.finditer(r"(?m)^impl ([A-Za-z_][A-Za-z0-9_]*)\s*\{", text):
        type_name = implementation.group(1)
        opening = text.find("{", implementation.start())
        end = _balanced_rust_block(text, opening, f"impl {type_name}")
        body_start = opening + 1
        body = text[body_start : end - 1]
        for method in re.finditer(
            r"(?m)^\s*pub (?:const )?fn ([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            body,
        ):
            absolute_start = body_start + method.start()
            absolute_end = text.find("{", body_start + method.end())
            if absolute_end < 0 or absolute_end >= end:
                raise ContractError(
                    f"Rust public method {type_name}::{method.group(1)} has no body"
                )
            symbols[f"method:{type_name}::{method.group(1)}"] = canonical_space(
                text[absolute_start:absolute_end]
            )
    return symbols


def extract_rust_source_boundary(
    surface: Mapping[str, object], root: Path
) -> dict[str, object]:
    locations = surface["source_locations"]
    assert isinstance(locations, list) and len(locations) == 6
    try:
        lib = (root / str(locations[0])).read_text(encoding="utf-8")
        kernel = (root / str(locations[1])).read_text(encoding="utf-8")
        simply = (root / str(locations[2])).read_text(encoding="utf-8")
        explanation = (root / str(locations[3])).read_text(encoding="utf-8")
        no_match_explanation = (root / str(locations[4])).read_text(encoding="utf-8")
        semantic_conversion = (root / str(locations[5])).read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot read Rust kernel boundary source: {exc}") from exc

    symbols: dict[str, str] = {}
    if re.search(r"(?m)^pub mod kernel;\s*$", lib):
        symbols["module:kernel"] = "pub mod kernel;"
    if re.search(r"(?m)^pub mod simply;\s*$", lib):
        symbols["module:simply"] = "pub mod simply;"
    if re.search(r"(?m)^pub mod explanation;\s*$", lib):
        symbols["module:explanation"] = "pub mod explanation;"
    if re.search(r"(?m)^pub mod no_match_explanation;\s*$", lib):
        symbols["module:no_match_explanation"] = "pub mod no_match_explanation;"
    if re.search(r"(?m)^pub mod semantic_conversion;\s*$", lib):
        symbols["module:semantic_conversion"] = "pub mod semantic_conversion;"
    reexport = re.search(r"pub use kernel::\{([^}]+)\};", lib, re.DOTALL)
    if reexport is not None:
        symbols["reexport:kernel"] = canonical_space(reexport.group(0))
    reexport = re.search(r"pub use simply::\{([^}]+)\};", lib, re.DOTALL)
    if reexport is not None:
        symbols["reexport:simply"] = canonical_space(reexport.group(0))

    for source in (
        kernel,
        simply,
        explanation,
        no_match_explanation,
        semantic_conversion,
    ):
        for match in re.finditer(
            r"(?m)^pub const ([A-Z][A-Z0-9_]*):\s*([^;]+);\s*$", source
        ):
            symbols[f"const:{match.group(1)}"] = canonical_space(match.group(0))

    for source in (
        kernel,
        simply,
        explanation,
        no_match_explanation,
        semantic_conversion,
    ):
        for match in re.finditer(
            r"(?m)^pub enum ([A-Za-z_][A-Za-z0-9_]*)\s*\{", source
        ):
            opening = source.find("{", match.start())
            end = _balanced_rust_block(source, opening, f"enum {match.group(1)}")
            symbols[f"enum:{match.group(1)}"] = canonical_space(
                source[match.start() : end]
            )

    symbols.update(_rust_public_structs(simply))
    symbols.update(_rust_public_structs(explanation))
    symbols.update(_rust_public_structs(no_match_explanation))
    symbols.update(_rust_public_structs(semantic_conversion))
    symbols.update(_rust_public_methods(simply))

    for source in (kernel, explanation, no_match_explanation, semantic_conversion):
        for match in re.finditer(r"(?m)^pub fn ([A-Za-z_][A-Za-z0-9_]*)\s*\(", source):
            opening = source.find("{", match.end())
            if opening < 0:
                raise ContractError(
                    f"Rust public function {match.group(1)} has no body"
                )
            symbols[f"fn:{match.group(1)}"] = canonical_space(
                source[match.start() : opening]
            )

    required = {
        "module:kernel",
        "module:simply",
        "module:explanation",
        "module:no_match_explanation",
        "module:semantic_conversion",
        "reexport:kernel",
        "reexport:simply",
        "enum:KernelCompileError",
        "enum:KernelStage",
        "enum:SimplyCharacterSetMember",
        "enum:SimplyErrorCode",
        "enum:SemanticConversionDestination",
        "enum:SemanticConversionStatus",
        "struct:SimplyBuilder",
        "struct:SimplyCompileProjection",
        "struct:SimplyError",
        "struct:SimplyErrors",
        "struct:SimplyOptions",
        "struct:SimplyValue",
        "struct:SemanticConversionErrors",
        "struct:SemanticConversionResult",
        "fn:compile",
        "fn:convert_semantic_program",
        "fn:explain_semantics",
        "fn:explain_target",
        "fn:explain_no_match",
        "method:SimplyBuilder::new",
        "method:SimplyBuilder::empty",
        "method:SimplyBuilder::literal",
        "method:SimplyBuilder::wildcard",
        "method:SimplyBuilder::character_set",
        "method:SimplyBuilder::sequence",
        "method:SimplyBuilder::alternation",
        "method:SimplyBuilder::group",
        "method:SimplyBuilder::capture",
        "method:SimplyBuilder::backreference",
        "method:SimplyBuilder::position",
        "method:SimplyBuilder::lookaround",
        "method:SimplyBuilder::atomic",
        "method:SimplyBuilder::repeat",
        "method:SimplyBuilder::import_node",
        "method:SimplyBuilder::import_program",
        "method:SimplyBuilder::finish_program",
        "method:SimplyBuilder::finish_request",
        "method:SimplyErrorCode::as_str",
        "method:SimplyValue::step_id",
        "const:SEMANTIC_ALPHA_EQUIVALENCE_METHOD",
        "const:SEMANTIC_CONVERSION_VERSION",
    }
    missing = sorted(required - set(symbols))
    if missing:
        raise ContractError(f"Rust kernel boundary is missing {missing}")
    return snapshot(str(surface["id"]), "rust-source-boundary", symbols)


def shell_function(text: str, name: str) -> str:
    match = re.search(rf"(?m)^{re.escape(name)}\(\)\s*\{{\s*$", text)
    if not match:
        raise ContractError(f"shell function {name} was not found")
    lines = text[match.end() :].splitlines()
    body: list[str] = []
    depth = 1
    for line in lines:
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            break
        body.append(line)
    if depth != 0:
        raise ContractError(f"shell function {name} is not balanced")
    return "\n".join(body)


def powershell_function(text: str, name: str) -> str:
    match = re.search(rf"(?m)^function\s+{re.escape(name)}\s*\{{\s*$", text)
    if not match:
        raise ContractError(f"PowerShell function {name} was not found")
    lines = text[match.end() :].splitlines()
    body: list[str] = []
    depth = 1
    for line in lines:
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            break
        body.append(line)
    if depth != 0:
        raise ContractError(f"PowerShell function {name} is not balanced")
    return "\n".join(body)


def cli_command_rows(body: str, pattern: str) -> dict[str, str]:
    rows: dict[str, set[str]] = {}
    for match in re.finditer(pattern, body, re.MULTILINE):
        row = canonical_space(match.group(1))
        if row.startswith(("./", "-")):
            continue
        command = row.split(maxsplit=1)[0]
        if command == "_run-configured":
            continue
        rows.setdefault(command, set()).add(row)
    return {
        command: " | ".join(sorted(overloads))
        for command, overloads in sorted(rows.items())
    }


def extract_cli(surface: Mapping[str, object], root: Path) -> dict[str, object]:
    locations = surface["source_locations"]
    assert isinstance(locations, list) and len(locations) == 2
    posix_path = root / str(locations[0])
    powershell_path = root / str(locations[1])
    try:
        posix_body = shell_function(
            posix_path.read_text(encoding="utf-8"), "print_help"
        )
        powershell_body = powershell_function(
            powershell_path.read_text(encoding="utf-8"), "Show-Help"
        )
    except OSError as exc:
        raise ContractError(f"cannot read CLI wrapper source: {exc}") from exc
    posix_rows = cli_command_rows(posix_body, r'^\s*echo\s+"  ([a-z][^"\n]+)"\s*$')
    powershell_rows = cli_command_rows(
        powershell_body, r'^\s*Write-Host\s+"  ([a-z][^"\n]+)"\s*$'
    )
    if posix_rows != powershell_rows:
        raise ContractError("POSIX and PowerShell CLI help command rows diverge")
    if not posix_rows or "help" not in posix_rows:
        raise ContractError("CLI help command rows could not be extracted")
    return snapshot(str(surface["id"]), "cli-commands", posix_rows)


def extract_json_schema(surface: Mapping[str, object], root: Path) -> dict[str, object]:
    locations = surface["source_locations"]
    assert isinstance(locations, list) and len(locations) == 1
    contract = load_json(root / str(locations[0]))
    if not isinstance(contract, dict) or "$schema" not in contract:
        raise ContractError(f"{locations[0]} is not a JSON Schema contract")
    return {
        "snapshot_version": 1,
        "surface": str(surface["id"]),
        "format": "json-schema",
        "contract": contract,
    }


def extract_package_entrypoints(
    surface: Mapping[str, object], root: Path
) -> dict[str, object]:
    locations = surface["source_locations"]
    assert isinstance(locations, list) and len(locations) == 1
    manifest = load_json(root / str(locations[0]))
    if not isinstance(manifest, dict):
        raise ContractError("TypeScript package manifest must be an object")
    selected: dict[str, object] = {}
    for key in ("exports", "files", "main", "types"):
        if key not in manifest:
            raise ContractError(f"TypeScript package manifest is missing {key}")
        selected[key] = manifest[key]
    flattened = flatten_json(selected)
    return snapshot(str(surface["id"]), "package-entrypoints", flattened)


def literal_all(tree: ast.Module, path: Path) -> list[str]:
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            value = node.value
            if isinstance(target, ast.Name) and target.id == "__all__":
                try:
                    result = ast.literal_eval(value)
                except (ValueError, TypeError) as exc:
                    raise ContractError(f"{path}: __all__ must be literal") from exc
                if not isinstance(result, (list, tuple)) or not all(
                    isinstance(item, str) for item in result
                ):
                    raise ContractError(f"{path}: __all__ must contain only names")
                return list(result)
    raise ContractError(f"{path}: public package must define literal __all__")


def python_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    arguments = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix}({arguments}){returns}"


def python_definition_symbols(
    path: Path, module: str, names: Iterable[str]
) -> dict[str, str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise ContractError(f"cannot parse public Python module {path}: {exc}") from exc
    definitions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assignments: dict[str, ast.expr | None] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assignments[node.target.id] = node.value
    symbols: dict[str, str] = {}
    for name in names:
        qualified = f"{module}.{name}"
        definition = definitions.get(name)
        if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols[qualified] = python_signature(definition)
        elif isinstance(definition, ast.ClassDef):
            bases = ", ".join(ast.unparse(base) for base in definition.bases)
            symbols[qualified] = f"class({bases})"
            for member in definition.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    not member.name.startswith("_")
                    or member.name in {"__init__", "__str__"}
                ):
                    symbols[f"{qualified}.{member.name}"] = python_signature(member)
        elif name in assignments:
            value = assignments[name]
            symbols[qualified] = (
                f"constant={ast.unparse(value)}" if value is not None else "constant"
            )
        else:
            raise ContractError(f"{path}: exported name {name} has no definition")
    return symbols


def module_path(source_root: Path, module: str) -> Path:
    relative = Path(*module.split("."))
    package = source_root / relative / "__init__.py"
    if package.is_file():
        return package
    file_path = source_root / relative.with_suffix(".py")
    if file_path.is_file():
        return file_path
    raise ContractError(f"cannot resolve exported Python module {module}")


def extract_python(surface: Mapping[str, object], root: Path) -> dict[str, object]:
    source_root = root / "bindings/python/src"
    root_module = "STRling"
    root_path = module_path(source_root, root_module)
    try:
        root_tree = ast.parse(
            root_path.read_text(encoding="utf-8"), filename=str(root_path)
        )
    except (OSError, SyntaxError) as exc:
        raise ContractError(f"cannot parse Python package root: {exc}") from exc
    exported = literal_all(root_tree, root_path)
    symbols: dict[str, str] = {}
    imports: dict[str, tuple[str, str | None]] = {}
    for node in root_tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports[alias.asname or alias.name] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split(".")[-1]] = (alias.name, None)
    for name in exported:
        imported = imports.get(name)
        if imported is None and name == "simply":
            imported = ("STRling.simply", None)
        if imported is None:
            symbols.update(python_definition_symbols(root_path, root_module, [name]))
            continue
        module, imported_name = imported
        candidate_module = f"{module}.{imported_name}" if imported_name else module
        try:
            candidate_path = module_path(source_root, candidate_module)
        except ContractError:
            if imported_name is None:
                raise
            candidate_path = module_path(source_root, module)
            symbols.update(
                python_definition_symbols(candidate_path, module, [imported_name])
            )
            continue
        symbols[candidate_module] = "module"
        try:
            candidate_tree = ast.parse(
                candidate_path.read_text(encoding="utf-8"), filename=str(candidate_path)
            )
        except (OSError, SyntaxError) as exc:
            raise ContractError(f"cannot parse exported Python module: {exc}") from exc
        names = literal_all(candidate_tree, candidate_path)
        target_imports: dict[str, tuple[str, str]] = {}
        for node in candidate_tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    target_imports[alias.asname or alias.name] = (
                        node.module,
                        alias.name,
                    )
        for public_name in names:
            target = target_imports.get(public_name)
            if target is None:
                symbols.update(
                    python_definition_symbols(
                        candidate_path, candidate_module, [public_name]
                    )
                )
            else:
                target_module, target_name = target
                symbols.update(
                    python_definition_symbols(
                        module_path(source_root, target_module),
                        target_module,
                        [target_name],
                    )
                )
    return snapshot(str(surface["id"]), "python-symbols", symbols)


def run_command(
    arguments: Sequence[str], *, cwd: Path, runner: Runner = subprocess.run
) -> str:
    try:
        completed = runner(
            list(arguments),
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ContractError(f"cannot execute {' '.join(arguments)}: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "no output").strip()
        raise ContractError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed.stdout


def declaration_units(text: str, label: str) -> dict[str, str]:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", " ", text)
    units: dict[str, str] = {}
    context: list[str] = []
    buffer: list[str] = []
    parentheses = 0
    brackets = 0

    def add(value: str) -> None:
        normalized = canonical_space(value)
        if not normalized or normalized.startswith("private "):
            return
        key = " :: ".join([label, *context, normalized])
        units[key] = normalized

    for character in text:
        if character == "(" or character == "<":
            parentheses += 1
        elif character == ")" or character == ">":
            parentheses = max(0, parentheses - 1)
        elif character == "[":
            brackets += 1
        elif character == "]":
            brackets = max(0, brackets - 1)
        if character == "{" and parentheses == 0 and brackets == 0:
            header = canonical_space("".join(buffer))
            buffer.clear()
            if header:
                add(header)
                context.append(header)
            continue
        if character == "}" and parentheses == 0 and brackets == 0:
            add("".join(buffer))
            buffer.clear()
            if context:
                context.pop()
            continue
        if character == ";" and parentheses == 0 and brackets == 0:
            add("".join(buffer))
            buffer.clear()
            continue
        buffer.append(character)
    add("".join(buffer))
    return units


def resolve_declaration_reference(base: Path, specifier: str) -> Path | None:
    if not specifier.startswith("."):
        return None
    candidate = (base.parent / specifier).resolve()
    if candidate.suffix == ".js":
        candidate = candidate.with_suffix(".d.ts")
    elif not candidate.suffix:
        candidate = candidate.with_suffix(".d.ts")
    if candidate.is_file():
        return candidate
    index = candidate.with_suffix("") / "index.d.ts"
    return index if index.is_file() else None


def extract_typescript(
    surface: Mapping[str, object], root: Path, runner: Runner = subprocess.run
) -> dict[str, object]:
    binding = root / "bindings/typescript"
    compiler = binding / "node_modules/typescript/bin/tsc"
    if not compiler.is_file():
        raise ContractError(f"TypeScript compiler is unavailable at {compiler}")
    with tempfile.TemporaryDirectory(prefix="strling-contract-ts-") as directory:
        output = Path(directory)
        run_command(
            [
                "node",
                str(compiler),
                "-p",
                "tsconfig.json",
                "--declaration",
                "--emitDeclarationOnly",
                "--outDir",
                str(output),
            ],
            cwd=binding,
            runner=runner,
        )
        entry = output / "index.d.ts"
        if not entry.is_file():
            raise ContractError(
                "TypeScript declaration emission did not create index.d.ts"
            )
        pending = [entry]
        visited: set[Path] = set()
        symbols: dict[str, str] = {}
        while pending:
            path = pending.pop()
            if path in visited:
                continue
            visited.add(path)
            text = path.read_text(encoding="utf-8")
            label = path.relative_to(output).as_posix()
            symbols.update(declaration_units(text, label))
            references = set(
                re.findall(
                    r'(?:from\s+|import\s*\(\s*)["\']([^"\']+)["\']',
                    text,
                )
            )
            for reference in sorted(references):
                resolved = resolve_declaration_reference(path, reference)
                if resolved is not None and output in resolved.parents:
                    pending.append(resolved)
        if not symbols:
            raise ContractError("TypeScript declaration closure is empty")
        return snapshot(str(surface["id"]), "declarations", symbols)


def parse_go_doc(text: str, package: str) -> dict[str, str]:
    sections = {"CONSTANTS", "FUNCTIONS", "TYPES", "VARIABLES"}
    active = False
    lines = text.splitlines()
    symbols: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if line in sections:
            active = True
            index += 1
            continue
        if active and re.match(r"^(?:const|func|type|var)\b", line):
            block = [line]
            braces = line.count("{") - line.count("}")
            index += 1
            while index < len(lines) and braces > 0:
                block.append(lines[index])
                braces += lines[index].count("{") - lines[index].count("}")
                index += 1
            declaration = canonical_space(re.sub(r"//[^\n]*", " ", "\n".join(block)))
            key = f"{package}::{declaration}"
            symbols[key] = declaration
            continue
        index += 1
    return symbols


def extract_go(
    surface: Mapping[str, object], root: Path, runner: Runner = subprocess.run
) -> dict[str, object]:
    binding = root / "bindings/go"
    packages = [".", "./core", "./emitters", "./simply"]
    symbols: dict[str, str] = {}
    for package in packages:
        output = run_command(["go", "doc", "-all", package], cwd=binding, runner=runner)
        symbols.update(parse_go_doc(output, package))
    if not symbols:
        raise ContractError("Go documentation extractor returned no declarations")
    return snapshot(str(surface["id"]), "declarations", symbols)


def balanced_parentheses(text: str, start: int) -> str:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        character = text[index]
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ContractError("unbalanced function formals")


def extract_r(surface: Mapping[str, object], root: Path) -> dict[str, object]:
    binding = root / "bindings/r"
    try:
        namespace = (binding / "NAMESPACE").read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"cannot read R NAMESPACE: {exc}") from exc
    exports = re.findall(r"(?m)^export\(([^)]+)\)\s*$", namespace)
    methods = re.findall(r"(?m)^S3method\(([^,]+),\s*([^)]+)\)\s*$", namespace)
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((binding / "R").glob("*.R"))
    )
    symbols: dict[str, str] = {}
    for name in exports:
        match = re.search(rf"(?m)^{re.escape(name)}\s*<-\s*function\s*(\()", source)
        if not match:
            raise ContractError(f"R export {name} has no top-level function definition")
        formals = canonical_space(balanced_parentheses(source, match.start(1)))
        symbols[f"export::{name}"] = formals
    for generic, class_name in methods:
        function_name = f"{generic}.{class_name}"
        match = re.search(
            rf"(?m)^{re.escape(function_name)}\s*<-\s*function\s*(\()", source
        )
        if not match:
            raise ContractError(f"R S3 method {function_name} has no definition")
        formals = canonical_space(balanced_parentheses(source, match.start(1)))
        symbols[f"S3method::{generic},{class_name}"] = formals
    if not symbols:
        raise ContractError("R NAMESPACE has no governed exports")
    return snapshot(str(surface["id"]), "r-symbols", symbols)


def snapshot(
    surface: str, format_name: str, symbols: Mapping[str, object]
) -> dict[str, object]:
    return {
        "snapshot_version": 1,
        "surface": surface,
        "format": format_name,
        "symbols": dict(sorted(symbols.items())),
    }


def _required_tool(environment: str, candidates: Sequence[str]) -> str:
    configured = os.environ.get(environment)
    if configured:
        path = Path(configured)
        if path.is_file():
            return str(path)
        raise ContractError(f"{environment} does not name a file: {configured}")
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise ContractError(
        f"required tool is unavailable; set {environment} or install one of {list(candidates)}"
    )


def _jdk_tool(name: str) -> str:
    home = os.environ.get("JAVA_HOME")
    suffix = f"{name}.exe" if os.name == "nt" else name
    if home:
        candidate = Path(home) / "bin" / suffix
        if candidate.is_file():
            return str(candidate)
        raise ContractError(f"JAVA_HOME does not contain bin/{suffix}: {home}")
    return _required_tool(f"STRLING_{name.upper()}", (name, suffix))


def _javap_declarations(text: str, class_name: str) -> dict[str, str]:
    symbols: dict[str, str] = {}
    declaration: str | None = None
    member_index = 0
    for raw in text.splitlines():
        line = canonical_space(raw)
        if not line or line.startswith("Compiled from") or line in {"{", "}"}:
            continue
        if line.startswith("descriptor:"):
            if declaration is None:
                raise ContractError(
                    f"javap descriptor has no declaration for {class_name}"
                )
            value = f"{declaration} | {line}"
            symbols[f"binary:{class_name}:{member_index:04d}"] = value
            member_index += 1
            declaration = None
            continue
        if line.startswith(("public ", "protected ")):
            if declaration is not None:
                symbols[f"binary:{class_name}:{member_index:04d}"] = declaration
                member_index += 1
            declaration = line.rstrip(" {")
    if declaration is not None:
        symbols[f"binary:{class_name}:{member_index:04d}"] = declaration
    return symbols


def _class_names(directory: Path) -> list[str]:
    if not directory.is_dir():
        raise ContractError(f"compiled class directory is unavailable: {directory}")
    names = [
        path.relative_to(directory).with_suffix("").as_posix().replace("/", ".")
        for path in directory.rglob("*.class")
        if path.name not in {"module-info.class", "package-info.class"}
    ]
    names = sorted(name for name in names if "$WhenMappings" not in name)
    if not names:
        raise ContractError(f"compiled class directory is empty: {directory}")
    return names


def _binary_api_symbols(
    directory: Path,
    *,
    javap: str,
    runner: Runner,
    require_kotlin_metadata: bool,
) -> dict[str, str]:
    symbols: dict[str, str] = {}
    metadata_seen = False
    class_names = _class_names(directory)
    for start in range(0, len(class_names), 32):
        batch = class_names[start : start + 32]
        output = run_command(
            [javap, "-public", "-s", "-classpath", str(directory), *batch],
            cwd=directory,
            runner=runner,
        )
        for chunk in re.split(r"(?=Compiled from )", output):
            header = re.search(
                r"(?m)^(?:public|protected)\s+.*?\b(?:class|interface|enum|record)\s+([A-Za-z0-9_.$]+)",
                chunk,
            )
            if header is None:
                continue
            class_name = header.group(1)
            symbols.update(_javap_declarations(chunk, class_name))
        if require_kotlin_metadata and not metadata_seen:
            verbose = run_command(
                [javap, "-v", "-public", "-classpath", str(directory), *batch],
                cwd=directory,
                runner=runner,
            )
            metadata_seen = "kotlin.Metadata" in verbose
    if require_kotlin_metadata:
        symbols = {
            key: value
            for key, value in symbols.items()
            if "$default(" not in value
            and " access$" not in value
            and "$DefaultImpls" not in key
        }
    if not symbols:
        raise ContractError(f"javap returned no public declarations under {directory}")
    if require_kotlin_metadata and not metadata_seen:
        raise ContractError(
            "compiled Kotlin API contains no kotlin.Metadata annotation"
        )
    return symbols


def extract_java_class_api(
    surface: Mapping[str, object], root: Path, runner: Runner = subprocess.run
) -> dict[str, object]:
    component = str(surface["component"])
    if component == "jvm":
        binding = root / "bindings/jvm"
    elif component == "java":
        binding = root / "bindings/java"
    else:
        raise ContractError(f"java-class-api does not support component {component}")
    maven = _required_tool("STRLING_MAVEN", ("mvn", "mvn.cmd"))
    javap = _jdk_tool("javap")
    if component == "java":
        run_command(
            [maven, "-o", "-B", "-q", "-DskipTests", "install"],
            cwd=root / "bindings/jvm",
            runner=runner,
        )
    run_command(
        [maven, "-o", "-B", "-q", "-DskipTests", "compile"],
        cwd=binding,
        runner=runner,
    )
    symbols = _binary_api_symbols(
        binding / "target/classes",
        javap=javap,
        runner=runner,
        require_kotlin_metadata=False,
    )
    return snapshot(str(surface["id"]), "javap-public-signatures", symbols)


_KOTLIN_DECLARATION = re.compile(
    r"^(?:(?:public|protected|private|internal|expect|actual|final|open|abstract|"
    r"sealed|data|enum|annotation|value|inline|tailrec|operator|infix|external|"
    r"suspend|override|lateinit|const)\s+)*(?:class|interface|object|typealias|"
    r"fun|val|var)\b"
)


def _kotlin_signature_head(text: str) -> str:
    parentheses = 0
    brackets = 0
    angle = 0
    quote: str | None = None
    escaped = False
    result: list[str] = []
    for character in text:
        if quote:
            result.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
            result.append(character)
            continue
        if character == "(":
            parentheses += 1
        elif character == ")":
            parentheses = max(0, parentheses - 1)
        elif character == "[":
            brackets += 1
        elif character == "]":
            brackets = max(0, brackets - 1)
        elif character == "<":
            angle += 1
        elif character == ">":
            angle = max(0, angle - 1)
        if parentheses == brackets == angle == 0 and character in {"{", "="}:
            break
        result.append(character)
    return canonical_space("".join(result))


def _kotlin_brace_delta(text: str) -> int:
    quote: str | None = None
    escaped = False
    delta = 0
    for character in text:
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
        elif character == "{":
            delta += 1
        elif character == "}":
            delta -= 1
    return delta


def _kotlin_source_symbols(binding: Path) -> dict[str, str]:
    symbols: dict[str, str] = {}
    source_root = binding / "src/main/kotlin"
    for path in sorted(source_root.rglob("*.kt")):
        relative = path.relative_to(source_root).as_posix()
        text = re.sub(
            r"/\*.*?\*/", " ", path.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        lines = text.splitlines()
        depth = 0
        index = 0
        while index < len(lines):
            raw = re.sub(r"//.*$", "", lines[index]).strip()
            if depth <= 1 and _KOTLIN_DECLARATION.match(raw):
                visibility = re.match(r"^(public|protected|private|internal)\b", raw)
                if visibility is None or visibility.group(1) in {"public", "protected"}:
                    candidate = raw
                    cursor = index + 1
                    while not _kotlin_signature_head(candidate) or (
                        candidate.count("(") > candidate.count(")")
                    ):
                        if cursor >= len(lines):
                            raise ContractError(
                                f"unterminated Kotlin declaration in {relative}:{index + 1}"
                            )
                        candidate += " " + re.sub(r"//.*$", "", lines[cursor]).strip()
                        cursor += 1
                    signature = _kotlin_signature_head(candidate)
                    if signature:
                        symbols[f"source:{relative}:{signature}"] = signature
            depth += _kotlin_brace_delta(raw)
            depth = max(0, depth)
            index += 1
    if not symbols:
        raise ContractError("Kotlin source extractor returned no public declarations")
    return symbols


def extract_kotlin_binary_api(
    surface: Mapping[str, object], root: Path, runner: Runner = subprocess.run
) -> dict[str, object]:
    binding = root / "bindings/kotlin"
    wrapper = binding / ("gradlew.bat" if os.name == "nt" else "gradlew")
    gradle = (
        str(wrapper)
        if wrapper.is_file()
        else _required_tool("STRLING_GRADLE", ("gradle", "gradle.bat"))
    )
    javap = _jdk_tool("javap")
    maven = _required_tool("STRLING_MAVEN", ("mvn", "mvn.cmd"))
    run_command(
        [maven, "-o", "-B", "-q", "-DskipTests", "install"],
        cwd=root / "bindings/jvm",
        runner=runner,
    )
    run_command(
        [gradle, "--offline", "--no-daemon", "classes"],
        cwd=binding,
        runner=runner,
    )
    symbols = _kotlin_source_symbols(binding)
    symbols.update(
        _binary_api_symbols(
            binding / "build/classes/kotlin/main",
            javap=javap,
            runner=runner,
            require_kotlin_metadata=True,
        )
    )
    return snapshot(str(surface["id"]), "kotlin-source-and-binary-signatures", symbols)


def _dotnet_projects(component: str) -> tuple[str, ...]:
    if component == "csharp":
        return ("bindings/csharp/src/STRling/STRling.csproj",)
    if component == "fsharp":
        return ("bindings/fsharp/src/STRling.FSharp/STRling.FSharp.fsproj",)
    raise ContractError(f"dotnet-assembly-api does not support component {component}")


def _dotnet_output_name(project: Path) -> str:
    return f"{project.stem}.dll"


def extract_dotnet_assembly_api(
    surface: Mapping[str, object], root: Path, runner: Runner = subprocess.run
) -> dict[str, object]:
    dotnet = _required_tool("STRLING_DOTNET", ("dotnet", "dotnet.exe"))
    extractor = root / "tooling/dotnet_public_api/STRling.DotNetPublicApi.csproj"
    if not extractor.is_file():
        raise ContractError(f".NET public API extractor is unavailable: {extractor}")
    scratch_root = root / "target"
    scratch_root.mkdir(parents=True, exist_ok=True)
    symbols: dict[str, str] = {}
    with tempfile.TemporaryDirectory(
        prefix="strling-dotnet-public-", dir=scratch_root
    ) as directory:
        scratch = Path(directory)
        extractor_output = scratch / "extractor"
        run_command(
            [
                dotnet,
                "restore",
                str(extractor),
                "--ignore-failed-sources",
                "--property:NuGetAudit=false",
            ],
            cwd=root,
            runner=runner,
        )
        run_command(
            [
                dotnet,
                "build",
                str(extractor),
                "--no-restore",
                "--nologo",
                "--configuration",
                "Release",
                "--output",
                str(extractor_output),
            ],
            cwd=root,
            runner=runner,
        )
        extractor_assembly = extractor_output / "STRling.DotNetPublicApi.dll"
        if not extractor_assembly.is_file():
            raise ContractError(
                f".NET public API extractor build produced no assembly: {extractor_assembly}"
            )
        for index, relative in enumerate(_dotnet_projects(str(surface["component"]))):
            project = root / relative
            if not project.is_file():
                raise ContractError(f".NET public project is unavailable: {project}")
            output = scratch / f"product-{index}"
            run_command(
                [
                    dotnet,
                    "build",
                    str(project),
                    "--no-restore",
                    "--nologo",
                    "--configuration",
                    "Release",
                    "--property:NuGetAudit=false",
                    "--output",
                    str(output),
                ],
                cwd=root,
                runner=runner,
            )
            assembly = output / _dotnet_output_name(project)
            if not assembly.is_file():
                raise ContractError(f".NET build produced no assembly: {assembly}")
            payload = run_command(
                [
                    dotnet,
                    str(extractor_assembly),
                    "--assembly",
                    str(assembly),
                    "--prefix",
                    relative,
                ],
                cwd=root,
                runner=runner,
            )
            try:
                extracted = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ContractError(
                    f".NET public API extractor returned invalid JSON for {relative}: {exc}"
                ) from exc
            if not isinstance(extracted, dict) or not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in extracted.items()
            ):
                raise ContractError(
                    f".NET public API extractor returned invalid symbols for {relative}"
                )
            duplicate = set(symbols).intersection(extracted)
            if duplicate:
                raise ContractError(
                    f".NET public API extractor returned duplicate symbols: {sorted(duplicate)[:3]}"
                )
            symbols.update(extracted)
    if not symbols:
        raise ContractError(".NET public API extractor returned no symbols")
    return snapshot(str(surface["id"]), "dotnet-reflection-public-signatures", symbols)


def extract_surface(
    surface: Mapping[str, object], root: Path = ROOT, runner: Runner = subprocess.run
) -> dict[str, object]:
    extraction = surface["extraction"]
    assert isinstance(extraction, dict)
    mechanism = str(extraction["mechanism"])
    if mechanism == "c-header-declarations":
        return extract_c_header(surface, root)
    if mechanism == "cpp-header-declarations":
        return extract_cpp_headers(surface, root)
    if mechanism == "rust-source-boundary":
        return extract_rust_source_boundary(surface, root)
    if mechanism == "cli-help-parser":
        return extract_cli(surface, root)
    if mechanism == "go-doc-declarations":
        return extract_go(surface, root, runner)
    if mechanism == "java-class-api":
        return extract_java_class_api(surface, root, runner)
    if mechanism == "json-schema":
        return extract_json_schema(surface, root)
    if mechanism == "kotlin-binary-api":
        return extract_kotlin_binary_api(surface, root, runner)
    if mechanism == "dotnet-assembly-api":
        return extract_dotnet_assembly_api(surface, root, runner)
    if mechanism == "python-ast-exports":
        return extract_python(surface, root)
    if mechanism == "r-namespace-exports":
        return extract_r(surface, root)
    if mechanism == "typescript-declarations":
        return extract_typescript(surface, root, runner)
    if mechanism == "typescript-package-entrypoints":
        return extract_package_entrypoints(surface, root)
    raise ContractError(f"unsupported enforced extraction mechanism: {mechanism}")


def flatten_json(value: object, prefix: str = "$") -> dict[str, object]:
    if isinstance(value, dict):
        flattened: dict[str, object] = {}
        for key in sorted(value):
            flattened.update(flatten_json(value[key], f"{prefix}/{key}"))
        return flattened
    if isinstance(value, list):
        flattened = {}
        for index, item in enumerate(value):
            flattened.update(flatten_json(item, f"{prefix}/{index}"))
        return flattened
    return {prefix: value}


def strongest(comparisons: Iterable[Comparison]) -> Comparison:
    findings: list[str] = []
    classification = "unchanged"
    for comparison in comparisons:
        findings.extend(comparison.findings)
        if (
            CLASSIFICATION_ORDER[comparison.classification]
            > CLASSIFICATION_ORDER[classification]
        ):
            classification = comparison.classification
    return Comparison(classification, findings)


def compare_symbol_snapshots(
    old: Mapping[str, object], new: Mapping[str, object]
) -> Comparison:
    old_symbols = old.get("symbols")
    new_symbols = new.get("symbols")
    if not isinstance(old_symbols, dict) or not isinstance(new_symbols, dict):
        raise ContractError("symbol snapshots must contain symbol objects")
    findings: list[str] = []
    removed = sorted(set(old_symbols) - set(new_symbols))
    added = sorted(set(new_symbols) - set(old_symbols))
    changed = sorted(
        key
        for key in set(old_symbols) & set(new_symbols)
        if old_symbols[key] != new_symbols[key]
    )
    findings.extend(f"removed {key}" for key in removed)
    findings.extend(f"changed {key}" for key in changed)
    findings.extend(f"added {key}" for key in added)
    if removed or changed:
        return Comparison("breaking", findings)
    if added:
        return Comparison("additive", findings)
    return Comparison("unchanged", findings)


def sequence_set_comparison(
    old: list[object], new: list[object], path: str
) -> Comparison:
    old_values = {json.dumps(item, sort_keys=True) for item in old}
    new_values = {json.dumps(item, sort_keys=True) for item in new}
    removed = old_values - new_values
    added = new_values - old_values
    findings = [f"{path}: removed accepted value {item}" for item in sorted(removed)]
    findings.extend(f"{path}: added accepted value {item}" for item in sorted(added))
    if removed:
        return Comparison("breaking", findings)
    if added:
        return Comparison("additive", findings)
    return Comparison("unchanged")


def compare_schema_value(old: object, new: object, path: str = "$") -> Comparison:
    if old == new:
        return Comparison("unchanged")
    if path.rsplit("/", 1)[-1] in METADATA_KEYS:
        return Comparison("compatible", [f"{path}: descriptive metadata changed"])
    if isinstance(old, dict) and isinstance(new, dict):
        results: list[Comparison] = []
        old_keys = set(old)
        new_keys = set(new)
        for key in sorted(old_keys - new_keys):
            if key in METADATA_KEYS:
                results.append(
                    Comparison("compatible", [f"{path}/{key}: metadata removed"])
                )
            elif key in TIGHTENING_MINIMUMS | TIGHTENING_MAXIMUMS | {
                "pattern",
                "format",
            }:
                results.append(
                    Comparison("additive", [f"{path}/{key}: constraint removed"])
                )
            else:
                results.append(
                    Comparison("breaking", [f"{path}/{key}: contract member removed"])
                )
        for key in sorted(new_keys - old_keys):
            if key in METADATA_KEYS:
                results.append(
                    Comparison("compatible", [f"{path}/{key}: metadata added"])
                )
            elif key in TIGHTENING_MINIMUMS | TIGHTENING_MAXIMUMS | {
                "const",
                "format",
                "pattern",
                "required",
            }:
                results.append(
                    Comparison("breaking", [f"{path}/{key}: constraint added"])
                )
            elif key in {"$defs", "definitions", "properties"}:
                results.append(
                    Comparison("additive", [f"{path}/{key}: definitions added"])
                )
            else:
                results.append(
                    Comparison("additive", [f"{path}/{key}: contract member added"])
                )
        for key in sorted(old_keys & new_keys):
            child_path = f"{path}/{key}"
            old_value = old[key]
            new_value = new[key]
            if (
                key == "properties"
                and isinstance(old_value, dict)
                and isinstance(new_value, dict)
            ):
                required = (
                    set(new.get("required", []))
                    if isinstance(new.get("required", []), list)
                    else set()
                )
                for property_name in sorted(set(old_value) - set(new_value)):
                    results.append(
                        Comparison(
                            "breaking",
                            [f"{child_path}/{property_name}: property removed"],
                        )
                    )
                for property_name in sorted(set(new_value) - set(old_value)):
                    classification = (
                        "breaking" if property_name in required else "additive"
                    )
                    results.append(
                        Comparison(
                            classification,
                            [f"{child_path}/{property_name}: property added"],
                        )
                    )
                for property_name in sorted(set(old_value) & set(new_value)):
                    results.append(
                        compare_schema_value(
                            old_value[property_name],
                            new_value[property_name],
                            f"{child_path}/{property_name}",
                        )
                    )
            elif (
                key == "required"
                and isinstance(old_value, list)
                and isinstance(new_value, list)
            ):
                old_required = set(old_value)
                new_required = set(new_value)
                added = new_required - old_required
                removed = old_required - new_required
                if added:
                    results.append(
                        Comparison(
                            "breaking",
                            [f"{child_path}: required added {sorted(added)}"],
                        )
                    )
                if removed:
                    results.append(
                        Comparison(
                            "additive",
                            [f"{child_path}: required removed {sorted(removed)}"],
                        )
                    )
            elif (
                key in {"enum", "oneOf", "anyOf"}
                and isinstance(old_value, list)
                and isinstance(new_value, list)
            ):
                results.append(
                    sequence_set_comparison(old_value, new_value, child_path)
                )
            elif (
                key == "allOf"
                and isinstance(old_value, list)
                and isinstance(new_value, list)
            ):
                comparison = sequence_set_comparison(new_value, old_value, child_path)
                inverted = {
                    "additive": "breaking",
                    "breaking": "additive",
                    "unchanged": "unchanged",
                }[comparison.classification]
                results.append(Comparison(inverted, comparison.findings))
            elif (
                key in TIGHTENING_MINIMUMS
                and isinstance(old_value, (int, float))
                and isinstance(new_value, (int, float))
            ):
                classification = "breaking" if new_value > old_value else "additive"
                results.append(
                    Comparison(
                        classification, [f"{child_path}: {old_value} -> {new_value}"]
                    )
                )
            elif (
                key in TIGHTENING_MAXIMUMS
                and isinstance(old_value, (int, float))
                and isinstance(new_value, (int, float))
            ):
                classification = "breaking" if new_value < old_value else "additive"
                results.append(
                    Comparison(
                        classification, [f"{child_path}: {old_value} -> {new_value}"]
                    )
                )
            elif (
                key == "additionalProperties"
                and isinstance(old_value, bool)
                and isinstance(new_value, bool)
            ):
                classification = (
                    "breaking" if old_value and not new_value else "additive"
                )
                results.append(
                    Comparison(
                        classification, [f"{child_path}: {old_value} -> {new_value}"]
                    )
                )
            else:
                results.append(compare_schema_value(old_value, new_value, child_path))
        return strongest(results)
    if isinstance(old, list) and isinstance(new, list):
        return sequence_set_comparison(old, new, path)
    return Comparison("breaking", [f"{path}: value changed from {old!r} to {new!r}"])


def compare_snapshots(
    old: Mapping[str, object], new: Mapping[str, object], strategy: str
) -> Comparison:
    if old == new:
        return Comparison("unchanged")
    if strategy == "json-schema-structure":
        old_contract = old.get("contract")
        new_contract = new.get("contract")
        if not isinstance(old_contract, dict) or not isinstance(new_contract, dict):
            raise ContractError("schema snapshots must contain contract objects")
        return compare_schema_value(old_contract, new_contract)
    return compare_symbol_snapshots(old, new)


def serialized(value: Mapping[str, object]) -> str:
    return json.dumps(value, indent=4, sort_keys=True, ensure_ascii=False) + "\n"


def process_surface(
    surface: Mapping[str, object],
    *,
    root: Path,
    check: bool,
    runner: Runner = subprocess.run,
) -> SurfaceResult:
    identifier = str(surface["id"])
    component = str(surface["component"])
    snapshot_path = str(surface["snapshot_path"])
    enforcement = str(surface["enforcement"])
    if enforcement == "transitional":
        return SurfaceResult(
            identifier,
            component,
            "transitional",
            snapshot_path=snapshot_path,
            reason=str(surface["rationale"]),
        )
    if enforcement == "planned":
        return SurfaceResult(
            identifier,
            component,
            "planned",
            snapshot_path=snapshot_path,
            reason=str(surface["activation_condition"]),
        )
    try:
        current = extract_surface(surface, root, runner)
        destination = root / snapshot_path
        if check:
            committed = load_json(destination)
            if committed != current:
                comparison = compare_snapshots(
                    committed if isinstance(committed, dict) else {},
                    current,
                    str(surface["comparison"]),
                )
                return SurfaceResult(
                    identifier,
                    component,
                    "failed",
                    comparison.classification,
                    snapshot_path,
                    ["snapshot is stale", *comparison.findings],
                )
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized(current))
    except ContractError as exc:
        return SurfaceResult(
            identifier,
            component,
            "failed",
            snapshot_path=snapshot_path,
            findings=[str(exc)],
        )
    return SurfaceResult(identifier, component, "passed", snapshot_path=snapshot_path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or verify public contract snapshots."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--control", type=Path, default=DEFAULT_CONTROL)
    parser.add_argument("--surface", action="append", default=[])
    return parser.parse_args(argv)


def render_human(
    results: Sequence[SurfaceResult], declaration_findings: Sequence[str]
) -> None:
    for result in results:
        suffix = f" ({result.reason})" if result.reason else ""
        print(f"[{result.status}] {result.surface} [{result.classification}]{suffix}")
        for finding in result.findings:
            print(f"  - {finding}")
    status = "failed" if declaration_findings else "passed"
    print(f"[{status}] change-declarations")
    for finding in declaration_findings:
        print(f"  - {finding}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    declaration_findings: list[str] = []
    try:
        registry_path = args.registry.resolve()
        registry = load_registry(registry_path)
        surfaces = registry["surfaces"]
        assert isinstance(surfaces, list)
        selected = set(args.surface)
        if selected:
            known = {
                str(surface["id"]) for surface in surfaces if isinstance(surface, dict)
            }
            unknown = sorted(selected - known)
            if unknown:
                raise ContractError("unknown public surface: " + ", ".join(unknown))
        results = [
            process_surface(surface, root=ROOT, check=args.check)
            for surface in surfaces
            if isinstance(surface, dict)
            and (not selected or str(surface["id"]) in selected)
        ]
        if (
            args.check
            and not selected
            and registry_path == DEFAULT_REGISTRY.resolve()
            and not any(result.status == "failed" for result in results)
        ):
            task, base = load_active_task(ROOT, args.control.resolve())
            detected = detect_base_changes(
                root=ROOT,
                registry_path=registry_path,
                registry=registry,
                base=base,
                compare=compare_snapshots,
            )
            result_by_surface = {result.surface: result for result in results}
            for change in detected:
                result = result_by_surface.get(change.surface)
                if result is None:
                    result = SurfaceResult(
                        change.surface,
                        change.component,
                        "passed",
                        snapshot_path=change.snapshot_path,
                    )
                    results.append(result)
                    result_by_surface[change.surface] = result
                result.classification = change.classification
                result.findings.extend(change.findings)
            declaration_findings = validate_change_declarations(task, detected)
    except (ContractError, DeclarationError) as exc:
        if args.json_output:
            print(
                json.dumps(
                    {
                        "operation": "contracts_check"
                        if args.check
                        else "contracts_write",
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
    failed = bool(declaration_findings) or any(
        result.status == "failed" for result in results
    )
    exit_code = 1 if failed else 0
    if args.json_output:
        print(
            json.dumps(
                {
                    "operation": "contracts_check" if args.check else "contracts_write",
                    "status": "failed" if failed else "passed",
                    "exit_code": exit_code,
                    "results": [result.as_dict() for result in results],
                    "change_declarations": {
                        "status": "failed" if declaration_findings else "passed",
                        "findings": declaration_findings,
                    },
                },
                sort_keys=True,
            )
        )
    else:
        render_human(results, declaration_findings)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
