#!/usr/bin/env python3
"""Certify the specification-owned Simply builder protocol and evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

if __package__:
    from tooling.contract_validation import (
        ContractSuite,
        ContractValidationError,
        canonical_json,
        iter_nodes,
    )
else:
    from contract_validation import (
        ContractSuite,
        ContractValidationError,
        canonical_json,
        iter_nodes,
    )

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = ROOT / "spec" / "frontends" / "simply" / "1.0"
PROTOCOL_1_1_ROOT = ROOT / "spec" / "frontends" / "simply" / "1.1"

EXPECTED_FILES = (
    "README.md",
    "builder-request.schema.json",
    "case.schema.json",
    "fixtures/negative.json",
    "fixtures/positive.json",
    "protocol.json",
    "protocol.schema.json",
)
EXPECTED_OPERATIONS = (
    "alternation",
    "atomic",
    "backreference",
    "capture",
    "character_set",
    "empty",
    "group",
    "import_node",
    "import_program",
    "literal",
    "lookaround",
    "position",
    "repeat",
    "sequence",
    "wildcard",
)
EXPECTED_1_1_OPERATIONS = tuple(sorted((*EXPECTED_OPERATIONS, "stdlib_helper")))
EXPECTED_1_1_FILES = (
    "README.md",
    "adapter-response.schema.json",
    "builder-request.schema.json",
    "case.schema.json",
    "fixtures/negative.json",
    "fixtures/positive.json",
    "protocol.json",
    "protocol.schema.json",
)
EXPECTED_OPTIONS = (
    "builtin_character_domain",
    "case_matching",
    "text_model",
    "wildcard_line_terminators",
)
EXPECTED_ERRORS = tuple(
    (f"STRL-SIMPLY-{index:04d}", identifier)
    for index, identifier in enumerate(
        (
            "invalid_argument",
            "invalid_bounds",
            "duplicate_identity",
            "duplicate_capture_name",
            "unresolved_value",
            "unresolved_capture",
            "reused_value",
            "incompatible_import",
            "invalid_provenance",
            "unsupported_construct",
            "invalid_compile_request",
            "resource_limit",
        ),
        start=1,
    )
)
EXPECTED_COMPATIBILITY = {
    "historical.simply.capture_repeat_guards": "excluded_host_quirk",
    "historical.simply.direct_target_conveniences": "adapter_obligation",
    "historical.simply.empty_literal": "adapter_obligation",
    "historical.simply.formatted_exceptions": "excluded_host_quirk",
    "historical.simply.immutable_composition": "adapter_obligation",
    "historical.simply.literal": "adapter_obligation",
    "historical.simply.max_zero_unbounded": "protocol_correction",
    "historical.simply.numbered_capture_duplication": "excluded_host_quirk",
}
FORBIDDEN_REQUEST_KEYS = {
    "emitted_pattern",
    "engine_options",
    "raw_regex",
    "runtime",
    "runtime_options",
    "target_pattern",
}


class SimplyContractError(ValueError):
    """The builder protocol, a request, or its evidence is invalid."""

    def __init__(
        self,
        message: str,
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.errors = errors or []


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SimplyContractError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise SimplyContractError(f"{path}: root must be an object")
    return value


def _json_path(parts: Iterable[Any]) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def _failure(code: str, path: str, message: str) -> SimplyContractError:
    return SimplyContractError(message, [{"code": code, "path": path}])


def _node_id(request: Mapping[str, Any], step_id: str) -> str:
    return f"node:simply/{request['identity_namespace']}/{step_id}"


def _capture_id(request: Mapping[str, Any], capture_key: str) -> str:
    return f"capture:simply/{request['identity_namespace']}/{capture_key}"


def _member_key(member: Mapping[str, Any]) -> tuple[Any, ...]:
    kind = member["kind"]
    if kind == "literal":
        return (0, member["value"], "", False)
    if kind == "range":
        return (1, member["start"], member["end"], False)
    if kind == "builtin":
        return (2, member["name"], member["domain"], member["negated"])
    return (
        3,
        member["property"],
        member.get("value", ""),
        member["negated"],
    )


def _walk_forbidden(value: Any, path: str = "$") -> tuple[str, str] | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_REQUEST_KEYS:
                return key, child_path
            violation = _walk_forbidden(child, child_path)
            if violation is not None:
                return violation
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violation = _walk_forbidden(child, f"{path}[{index}]")
            if violation is not None:
                return violation
    return None


def _node_children(node: Mapping[str, Any]) -> Iterable[tuple[str, Mapping[str, Any]]]:
    kind = node["kind"]
    if kind == "sequence":
        for index, child in enumerate(node["items"]):
            yield f"items[{index}]", child
    elif kind == "alternation":
        for index, child in enumerate(node["branches"]):
            yield f"branches[{index}]", child
    elif kind in {"repeat", "capture", "lookaround", "atomic"}:
        yield "body", node["body"]


def _validate_origins(
    node: Mapping[str, Any], sources: set[str], path: str = "$.root"
) -> None:
    origin = node.get("origin")
    if isinstance(origin, Mapping):
        for index, span in enumerate(origin.get("source_spans", [])):
            if span["source_id"] not in sources:
                raise _failure(
                    "STRL-SIMPLY-0009",
                    f"{path}.origin.source_spans[{index}].source_id",
                    "imported origin refers to an undeclared source",
                )
    for suffix, child in _node_children(node):
        _validate_origins(child, sources, f"{path}.{suffix}")


class SimplyContractSuite:
    """Validate and project the closed Simply builder contract."""

    def __init__(self, protocol_root: Path = PROTOCOL_ROOT) -> None:
        self.protocol_root = protocol_root
        self.canonical = ContractSuite()
        self.schemas = {
            name: load_json(protocol_root / name)
            for name in (
                "protocol.schema.json",
                "builder-request.schema.json",
                "case.schema.json",
            )
        }
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)
        canonical_store = {
            schema["$id"]: schema for schema in self.canonical.schemas.values()
        }
        store = {
            **canonical_store,
            **{schema["$id"]: schema for schema in self.schemas.values()},
        }
        self.validators = {
            name: Draft202012Validator(
                schema,
                resolver=RefResolver.from_schema(schema, store=store),
                format_checker=FormatChecker(),
            )
            for name, schema in self.schemas.items()
        }
        self.protocol = load_json(protocol_root / "protocol.json")
        self.positive = load_json(protocol_root / "fixtures" / "positive.json")
        self.negative = load_json(protocol_root / "fixtures" / "negative.json")
        self.manifest = load_json(protocol_root / "fixtures" / "manifest.json")

    def _validate(self, schema_name: str, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validators[schema_name].iter_errors(value),
            key=lambda error: tuple(str(item) for item in error.absolute_path),
        )
        if errors:
            error = errors[0]
            raise SimplyContractError(
                f"{schema_name} {_json_path(error.absolute_path)}: {error.message}"
            )

    def validate_protocol(self) -> None:
        self._validate("protocol.schema.json", self.protocol)
        operations = tuple(entry["id"] for entry in self.protocol["operations"])
        if operations != EXPECTED_OPERATIONS:
            raise SimplyContractError(
                "Simply operations must equal the closed canonical inventory in order"
            )
        options = tuple(entry["id"] for entry in self.protocol["semantic_options"])
        if options != EXPECTED_OPTIONS:
            raise SimplyContractError(
                "Simply semantic options must equal the closed inventory in order"
            )
        errors = tuple(
            (entry["code"], entry["id"]) for entry in self.protocol["errors"]
        )
        if errors != EXPECTED_ERRORS:
            raise SimplyContractError(
                "Simply errors must remain complete and ordered by stable code"
            )
        dispositions = {
            entry["id"]: entry["disposition"]
            for entry in self.protocol["compatibility_dispositions"]
        }
        if dispositions != EXPECTED_COMPATIBILITY:
            raise SimplyContractError(
                "historical Simply compatibility dispositions drifted"
            )
        identifiers = [
            entry["id"] for entry in self.protocol["compatibility_dispositions"]
        ]
        if identifiers != sorted(identifiers):
            raise SimplyContractError(
                "historical compatibility identities must be canonically ordered"
            )
        for entry in self.protocol["compatibility_dispositions"]:
            for relative in entry["evidence"]:
                if not (ROOT / relative).is_file():
                    raise SimplyContractError(
                        f"{entry['id']}: evidence path does not resolve: {relative}"
                    )

    def _builder_schema_error(self, request: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validators["builder-request.schema.json"].iter_errors(request),
            key=lambda error: tuple(str(item) for item in error.absolute_path),
        )
        if not errors:
            return
        error = errors[0]
        raise _failure(
            "STRL-SIMPLY-0001",
            _json_path(error.absolute_path),
            f"builder request schema violation: {error.message}",
        )

    def project_request(
        self, request: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Project one valid request into canonical contract values."""

        forbidden = _walk_forbidden(request)
        if forbidden is not None:
            marker, path = forbidden
            raise _failure(
                "STRL-SIMPLY-0010",
                path,
                f"unsupported target/runtime/raw construct: {marker}",
            )
        for index, step in enumerate(request.get("steps", [])):
            operation = step.get("operation") if isinstance(step, Mapping) else None
            if operation not in EXPECTED_OPERATIONS:
                raise _failure(
                    "STRL-SIMPLY-0010",
                    f"$.steps[{index}].operation",
                    f"unsupported builder operation: {operation}",
                )
        self._builder_schema_error(request)

        values: dict[str, dict[str, Any]] = {}
        consumed: dict[str, int] = {}
        capture_keys: dict[str, str] = {}
        capture_names: set[str] = set()
        pending_references: list[tuple[str, str]] = []
        sources: dict[str, dict[str, Any]] = {}

        def add_source(source: Mapping[str, Any], path: str) -> None:
            source_id = source["source_id"]
            current = sources.get(source_id)
            if current is not None and current != source:
                raise _failure(
                    "STRL-SIMPLY-0008",
                    path,
                    "imported source identity has conflicting bytes",
                )
            sources[source_id] = copy.deepcopy(dict(source))

        def take(step_id: str, path: str) -> dict[str, Any]:
            if step_id not in values:
                raise _failure(
                    "STRL-SIMPLY-0005", path, "builder value is not yet defined"
                )
            if consumed.get(step_id, 0) != 0:
                raise _failure(
                    "STRL-SIMPLY-0007",
                    path,
                    "immutable builder value already has a parent",
                )
            consumed[step_id] = 1
            return copy.deepcopy(values[step_id])

        for index, step in enumerate(request["steps"]):
            step_id = step["step_id"]
            step_path = f"$.steps[{index}]"
            if step_id in values:
                raise _failure(
                    "STRL-SIMPLY-0003",
                    f"{step_path}.step_id",
                    "builder step identity must be unique",
                )
            operation = step["operation"]
            arguments = step["arguments"]
            node_id = _node_id(request, step_id)

            if operation == "empty":
                node = {"node_id": node_id, "kind": "empty"}
            elif operation == "literal":
                text = arguments["text"]
                node = (
                    {"node_id": node_id, "kind": "empty"}
                    if text == ""
                    else {"node_id": node_id, "kind": "literal", "text": text}
                )
            elif operation == "wildcard":
                node = {
                    "node_id": node_id,
                    "kind": "wildcard",
                    "line_terminators": arguments.get(
                        "line_terminators",
                        request["semantic_options"]["wildcard_line_terminators"],
                    ),
                }
            elif operation == "character_set":
                members = copy.deepcopy(arguments["members"])
                default_domain = request["semantic_options"]["builtin_character_domain"]
                for member in members:
                    if member["kind"] == "builtin":
                        member.setdefault("domain", default_domain)
                    if member["kind"] == "range" and member["start"] > member["end"]:
                        raise _failure(
                            "STRL-SIMPLY-0001",
                            f"{step_path}.arguments.members",
                            "character-set range is reversed",
                        )
                members.sort(key=_member_key)
                if len({json.dumps(item, sort_keys=True) for item in members}) != len(
                    members
                ):
                    raise _failure(
                        "STRL-SIMPLY-0001",
                        f"{step_path}.arguments.members",
                        "character-set members must be unique",
                    )
                node = {
                    "node_id": node_id,
                    "kind": "character_set",
                    "negated": arguments["negated"],
                    "members": members,
                }
            elif operation in {"sequence", "alternation"}:
                children = [
                    take(value, f"{step_path}.arguments.values[{child_index}]")
                    for child_index, value in enumerate(arguments["values"])
                ]
                node = {
                    "node_id": node_id,
                    "kind": operation,
                    ("items" if operation == "sequence" else "branches"): children,
                }
            elif operation == "group":
                node = take(arguments["value"], f"{step_path}.arguments.value")
                origin = node.setdefault("origin", {})
                derived = origin.setdefault("derived_from_node_ids", [])
                derived.append(node_id)
                origin["derived_from_node_ids"] = sorted(set(derived))
            elif operation == "capture":
                capture_key = arguments["capture_key"]
                if capture_key in capture_keys:
                    raise _failure(
                        "STRL-SIMPLY-0003",
                        f"{step_path}.arguments.capture_key",
                        "logical capture key must be unique",
                    )
                name = arguments.get("name")
                if name is not None and name in capture_names:
                    raise _failure(
                        "STRL-SIMPLY-0004",
                        f"{step_path}.arguments.name",
                        "capture name must be unique",
                    )
                capture_id = _capture_id(request, capture_key)
                capture_keys[capture_key] = capture_id
                if name is not None:
                    capture_names.add(name)
                node = {
                    "node_id": node_id,
                    "kind": "capture",
                    "capture_id": capture_id,
                    "body": take(arguments["value"], f"{step_path}.arguments.value"),
                }
                if name is not None:
                    node["name"] = name
            elif operation == "backreference":
                capture_key = arguments["capture_key"]
                pending_references.append(
                    (capture_key, f"{step_path}.arguments.capture_key")
                )
                node = {
                    "node_id": node_id,
                    "kind": "backreference",
                    "capture_id": _capture_id(request, capture_key),
                }
            elif operation == "position":
                node = {
                    "node_id": node_id,
                    "kind": "position",
                    "position": arguments["position"],
                }
            elif operation == "lookaround":
                node = {
                    "node_id": node_id,
                    "kind": "lookaround",
                    "direction": arguments["direction"],
                    "polarity": arguments["polarity"],
                    "body": take(arguments["value"], f"{step_path}.arguments.value"),
                }
            elif operation == "atomic":
                node = {
                    "node_id": node_id,
                    "kind": "atomic",
                    "body": take(arguments["value"], f"{step_path}.arguments.value"),
                }
            elif operation == "repeat":
                maximum = arguments["max"]
                if maximum is not None and maximum < arguments["min"]:
                    raise _failure(
                        "STRL-SIMPLY-0002",
                        f"{step_path}.arguments.max",
                        "finite repetition maximum is below minimum",
                    )
                node = {
                    "node_id": node_id,
                    "kind": "repeat",
                    "body": take(arguments["value"], f"{step_path}.arguments.value"),
                    "min": arguments["min"],
                    "max": maximum,
                    "mode": arguments["mode"],
                }
            elif operation == "import_node":
                node = copy.deepcopy(arguments["node"])
                for source_index, source in enumerate(arguments.get("sources", [])):
                    add_source(source, f"{step_path}.arguments.sources[{source_index}]")
            else:
                program = arguments["program"]
                if program["contract_version"] != request["contract_version"]:
                    raise _failure(
                        "STRL-SIMPLY-0008",
                        f"{step_path}.arguments.program.contract_version",
                        "imported program uses another contract version",
                    )
                if program["specification_version"] != request["specification_version"]:
                    raise _failure(
                        "STRL-SIMPLY-0008",
                        f"{step_path}.arguments.program.specification_version",
                        "imported program uses another specification version",
                    )
                if (
                    program["case_matching"]
                    != request["semantic_options"]["case_matching"]
                ):
                    raise _failure(
                        "STRL-SIMPLY-0008",
                        f"{step_path}.arguments.program.case_matching",
                        "imported program uses incompatible semantic options",
                    )
                try:
                    self.canonical.validate("semantic-ir.schema.json", program)
                except ContractValidationError as error:
                    raise _failure(
                        "STRL-SIMPLY-0008",
                        f"{step_path}.arguments.program",
                        f"imported program is not canonical: {error}",
                    ) from error
                for source_index, source in enumerate(program.get("sources", [])):
                    add_source(
                        source,
                        f"{step_path}.arguments.program.sources[{source_index}]",
                    )
                node = copy.deepcopy(program["root"])
            values[step_id] = node
            consumed.setdefault(step_id, 0)

        for capture_key, path in pending_references:
            if capture_key not in capture_keys:
                raise _failure(
                    "STRL-SIMPLY-0006",
                    path,
                    "backreference does not resolve to a builder capture",
                )

        root_step = request["root_step_id"]
        if root_step not in values:
            raise _failure(
                "STRL-SIMPLY-0005",
                "$.root_step_id",
                "root builder value is not defined",
            )
        if consumed[root_step] != 0:
            raise _failure(
                "STRL-SIMPLY-0007",
                "$.root_step_id",
                "root builder value is already nested under another value",
            )
        for step_id in values:
            expected = 0 if step_id == root_step else 1
            if consumed[step_id] != expected:
                raise _failure(
                    "STRL-SIMPLY-0001",
                    "$.steps",
                    f"builder step {step_id} is not part of the root value",
                )

        program: dict[str, Any] = {
            "contract_version": request["contract_version"],
            "specification_version": request["specification_version"],
            "normalization": "canonical-v1",
            "case_matching": request["semantic_options"]["case_matching"],
            "root": copy.deepcopy(values[root_step]),
        }
        if sources:
            program["sources"] = [sources[key] for key in sorted(sources)]
        _validate_origins(program["root"], set(sources))
        try:
            self.canonical.validate("semantic-ir.schema.json", program)
        except ContractValidationError as error:
            raise _failure(
                "STRL-SIMPLY-0001", "$.root", f"invalid semantic projection: {error}"
            ) from error

        compile_projection = request["compile"]
        needs_profile = any(
            output in {"portability", "target_artifact"}
            for output in compile_projection["requested_outputs"]
        )
        if needs_profile and "target_profile" not in compile_projection:
            raise _failure(
                "STRL-SIMPLY-0011",
                "$.compile.target_profile",
                "requested target work requires an exact target profile",
            )
        limits = compile_projection["compiler_options"].get("resource_limits", {})
        maximum_nodes = limits.get("max_semantic_nodes")
        node_count = sum(1 for _ in iter_nodes(program["root"]))
        if maximum_nodes is not None and node_count > maximum_nodes:
            raise _failure(
                "STRL-SIMPLY-0012",
                "$.compile.compiler_options.resource_limits.max_semantic_nodes",
                "projected semantic node count exceeds the declared limit",
            )

        compile_request: dict[str, Any] = {
            "contract_version": request["contract_version"],
            "specification_version": request["specification_version"],
            "input": {"kind": "semantic", "program": copy.deepcopy(program)},
            "requested_outputs": copy.deepcopy(compile_projection["requested_outputs"]),
            "compiler_options": copy.deepcopy(compile_projection["compiler_options"]),
        }
        if "target_profile" in compile_projection:
            compile_request["target_profile"] = copy.deepcopy(
                compile_projection["target_profile"]
            )
        try:
            self.canonical.validate("compile-request.schema.json", compile_request)
        except ContractValidationError as error:
            raise _failure(
                "STRL-SIMPLY-0011",
                "$.compile",
                f"invalid CompileRequest projection: {error}",
            ) from error
        return program, compile_request

    def validate_cases(self) -> tuple[int, int]:
        self._validate("case.schema.json", self.positive)
        self._validate("case.schema.json", self.negative)
        if self.positive["kind"] != "positive" or self.negative["kind"] != "negative":
            raise SimplyContractError("Simply case documents have swapped kinds")

        case_ids: list[str] = []
        positive_features: set[str] = set()
        operation_coverage: set[str] = set()
        for case in self.positive["cases"]:
            case_ids.append(case["case_id"])
            if case["feature_ids"] != sorted(case["feature_ids"]):
                raise SimplyContractError(
                    f"{case['case_id']}: feature identities are not sorted"
                )
            positive_features.update(case["feature_ids"])
            operation_coverage.update(
                step["operation"] for step in case["request"]["steps"]
            )
            program, compile_request = self.project_request(case["request"])
            if program != case["expected"]["semantic_program"]:
                raise SimplyContractError(
                    f"{case['case_id']}: semantic projection differs from authored expectation"
                )
            if compile_request != case["expected"]["compile_request"]:
                raise SimplyContractError(
                    f"{case['case_id']}: CompileRequest projection differs from authored expectation"
                )
        if operation_coverage != set(EXPECTED_OPERATIONS):
            raise SimplyContractError(
                "positive cases do not cover every closed builder operation"
            )
        required_features = {
            *EXPECTED_OPERATIONS,
            "compile_request",
            "identity",
            "options",
            "provenance",
        }
        if positive_features != required_features:
            raise SimplyContractError(
                "positive feature coverage is incomplete or contains unknown scope"
            )

        negative_codes: set[str] = set()
        for case in self.negative["cases"]:
            case_ids.append(case["case_id"])
            if case["feature_ids"] != sorted(case["feature_ids"]):
                raise SimplyContractError(
                    f"{case['case_id']}: feature identities are not sorted"
                )
            try:
                self.project_request(case["request"])
            except SimplyContractError as error:
                if error.errors != case["expected"]["errors"]:
                    raise SimplyContractError(
                        f"{case['case_id']}: failure identity changed; "
                        f"expected={case['expected']['errors']} actual={error.errors}"
                    ) from error
                negative_codes.update(item["code"] for item in error.errors)
            else:
                raise SimplyContractError(
                    f"{case['case_id']}: controlled invalid request unexpectedly passed"
                )
        if negative_codes != {code for code, _ in EXPECTED_ERRORS}:
            raise SimplyContractError(
                "negative cases do not cover every stable builder error code"
            )
        if len(case_ids) != len(set(case_ids)):
            raise SimplyContractError("Simply case identities must be globally unique")
        return len(self.positive["cases"]), len(self.negative["cases"])

    def validate_manifest(self, positive: int, negative: int) -> str:
        expected_keys = {
            "manifest_kind",
            "manifest_version",
            "protocol_version",
            "contract_version",
            "authorship",
            "files",
            "case_counts",
        }
        if set(self.manifest) != expected_keys:
            raise SimplyContractError("Simply fixture manifest keys are invalid")
        if self.manifest["manifest_kind"] != "strling.simply-builder-fixtures":
            raise SimplyContractError("Simply fixture manifest kind is invalid")
        for key in ("manifest_version", "protocol_version", "contract_version"):
            if self.manifest[key] != "1.0.0":
                raise SimplyContractError(f"Simply fixture manifest {key} is invalid")
        if self.manifest["authorship"] != "specification-authored":
            raise SimplyContractError("Simply fixtures must be specification-authored")
        if self.manifest["case_counts"] != {
            "negative": negative,
            "positive": positive,
        }:
            raise SimplyContractError("Simply fixture manifest counts are stale")
        entries = self.manifest["files"]
        paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
        if paths != list(EXPECTED_FILES):
            raise SimplyContractError(
                "Simply fixture manifest must exactly cover governed inputs"
            )
        for entry in entries:
            if set(entry) != {"path", "sha256"}:
                raise SimplyContractError(
                    f"Simply manifest entry has invalid keys: {entry.get('path')}"
                )
            path = self.protocol_root / entry["path"]
            actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            if entry["sha256"] != actual:
                raise SimplyContractError(
                    f"Simply fixture fingerprint is stale for {entry['path']}"
                )
        certification = {
            "protocol": self.protocol,
            "manifest": self.manifest,
        }
        return "sha256:" + hashlib.sha256(canonical_json(certification)).hexdigest()

    def certify(self) -> dict[str, Any]:
        self.validate_protocol()
        positive, negative = self.validate_cases()
        fingerprint = self.validate_manifest(positive, negative)
        return {
            "schemas": len(self.schemas),
            "operations": len(EXPECTED_OPERATIONS),
            "errors": len(EXPECTED_ERRORS),
            "compatibility": len(EXPECTED_COMPATIBILITY),
            "positive": positive,
            "negative": negative,
            "fingerprint": fingerprint,
        }


class Simply11ContractSuite:
    """Validate the backward-compatible Simply 1.1 standard-library extension."""

    def __init__(self, protocol_root: Path = PROTOCOL_1_1_ROOT) -> None:
        self.protocol_root = protocol_root
        self.canonical = ContractSuite()
        self.schemas = {
            name: load_json(protocol_root / name)
            for name in (
                "protocol.schema.json",
                "builder-request.schema.json",
                "adapter-response.schema.json",
                "case.schema.json",
            )
        }
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)
        store = {
            **{schema["$id"]: schema for schema in self.canonical.schemas.values()},
            **{schema["$id"]: schema for schema in self.schemas.values()},
        }
        self.validators = {
            name: Draft202012Validator(
                schema,
                resolver=RefResolver.from_schema(schema, store=store),
                format_checker=FormatChecker(),
            )
            for name, schema in self.schemas.items()
        }
        self.protocol = load_json(protocol_root / "protocol.json")
        self.positive = load_json(protocol_root / "fixtures" / "positive.json")
        self.negative = load_json(protocol_root / "fixtures" / "negative.json")
        self.manifest = load_json(protocol_root / "fixtures" / "manifest.json")
        self.registry = load_json(
            ROOT / "spec" / "stdlib" / "registry" / "1.0" / "registry.json"
        )

    def _validate(self, schema_name: str, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validators[schema_name].iter_errors(value),
            key=lambda error: tuple(str(item) for item in error.absolute_path),
        )
        if errors:
            error = errors[0]
            raise SimplyContractError(
                f"{schema_name} {_json_path(error.absolute_path)}: {error.message}"
            )

    def validate_protocol(self) -> None:
        self._validate("protocol.schema.json", self.protocol)
        operations = tuple(entry["id"] for entry in self.protocol["operations"])
        if operations != EXPECTED_1_1_OPERATIONS:
            raise SimplyContractError(
                "Simply 1.1 operations must equal the closed canonical inventory"
            )
        previous = load_json(PROTOCOL_ROOT / "protocol.json")
        previous_operations = {entry["id"]: entry for entry in previous["operations"]}
        current_operations = {
            entry["id"]: entry for entry in self.protocol["operations"]
        }
        for operation_id, definition in previous_operations.items():
            if current_operations.get(operation_id) != definition:
                raise SimplyContractError(
                    f"Simply 1.1 changed inherited operation {operation_id}"
                )
        for field, value in previous.items():
            if field in {"protocol_version", "operations"}:
                continue
            if self.protocol.get(field) != value:
                raise SimplyContractError(
                    f"Simply 1.1 changed inherited protocol field {field}"
                )
        stdlib = current_operations["stdlib_helper"]
        if stdlib != {
            "id": "stdlib_helper",
            "destination": "canonical-stdlib-registry",
            "materializes_node": True,
            "arguments": ["helper_id", "parameters"],
            "invariants": [
                "registry-helper-identity",
                "registry-declared-parameters",
                "canonical-core-delegation",
                "no-host-semantic-implementation",
            ],
        }:
            raise SimplyContractError("stdlib_helper protocol definition drifted")

    def _helper_selection(
        self, request: Mapping[str, Any]
    ) -> tuple[str, str] | list[dict[str, str]]:
        steps = request.get("steps")
        if not isinstance(steps, list) or len(steps) != 1:
            return [
                {
                    "code": "STRL-SIMPLY-0001",
                    "path": "$.steps",
                }
            ]
        step = steps[0]
        if not isinstance(step, Mapping) or step.get("operation") != "stdlib_helper":
            return [
                {
                    "code": "STRL-SIMPLY-0010",
                    "path": "$.steps[0].operation",
                }
            ]
        arguments = step.get("arguments")
        if not isinstance(arguments, Mapping):
            return [
                {
                    "code": "STRL-SIMPLY-0001",
                    "path": "$.steps[0].arguments",
                }
            ]
        helper_id = arguments.get("helper_id")
        helper = next(
            (
                candidate
                for candidate in self.registry["helpers"]
                if candidate["id"] == helper_id
            ),
            None,
        )
        if helper is None:
            return [
                {
                    "code": "STRL-SIMPLY-0010",
                    "path": "$.steps[0].arguments.helper_id",
                }
            ]
        parameters = arguments.get("parameters")
        if not isinstance(parameters, Mapping):
            return [
                {
                    "code": "STRL-SIMPLY-0001",
                    "path": "$.steps[0].arguments.parameters",
                }
            ]
        definitions = {
            parameter["name"]: parameter
            for parameter in helper["signature"]["parameters"]
        }
        for name, value in parameters.items():
            definition = definitions.get(name)
            if definition is None:
                return [
                    {
                        "code": "STRL-SIMPLY-0001",
                        "path": f"$.steps[0].arguments.parameters.{name}",
                    }
                ]
            accepted = definition["accepted_types"]
            valid = (
                value is None
                and "null" in accepted
                or isinstance(value, int)
                and not isinstance(value, bool)
                and "integer" in accepted
            )
            if not valid:
                return [
                    {
                        "code": "STRL-SIMPLY-0001",
                        "path": f"$.steps[0].arguments.parameters.{name}",
                    }
                ]
        normalized = {
            name: parameters.get(name, definition["default"])
            for name, definition in definitions.items()
        }
        variant = next(
            (
                candidate
                for candidate in helper["semantic_definition"]["variants"]
                if candidate["parameter_values"] == normalized
            ),
            None,
        )
        if variant is None:
            variant = next(
                (
                    candidate
                    for candidate in helper["semantic_definition"]["variants"]
                    if all(
                        value == "default_or_other"
                        for value in candidate["parameter_values"].values()
                    )
                    and set(candidate["parameter_values"]) == set(normalized)
                ),
                None,
            )
        if variant is None:
            return [
                {
                    "code": "STRL-SIMPLY-0001",
                    "path": "$.steps[0].arguments.parameters",
                }
            ]
        return str(helper_id), str(variant["variant_id"])

    def validate_cases(self) -> tuple[int, int]:
        self._validate("case.schema.json", self.positive)
        self._validate("case.schema.json", self.negative)
        expected_variants = {
            (
                helper["id"],
                variant["variant_id"],
            )
            for helper in self.registry["helpers"]
            for variant in helper["semantic_definition"]["variants"]
        }
        actual_variants: set[tuple[str, str]] = set()
        case_ids: list[str] = []
        for case in self.positive["cases"]:
            case_ids.append(case["case_id"])
            self._validate("builder-request.schema.json", case["request"])
            selection = self._helper_selection(case["request"])
            if isinstance(selection, list):
                raise SimplyContractError(
                    f"{case['case_id']}: accepted helper selection failed"
                )
            expected = (
                case["expected"]["helper_id"],
                case["expected"]["variant_id"],
            )
            if selection != expected:
                raise SimplyContractError(
                    f"{case['case_id']}: helper selection drifted"
                )
            actual_variants.add(selection)
        if actual_variants != expected_variants:
            raise SimplyContractError(
                "Simply 1.1 positive cases must cover every registry variant"
            )
        for case in self.negative["cases"]:
            case_ids.append(case["case_id"])
            selection = self._helper_selection(case["request"])
            if not isinstance(selection, list):
                raise SimplyContractError(
                    f"{case['case_id']}: controlled invalid helper passed"
                )
            if selection != case["expected"]["errors"]:
                raise SimplyContractError(
                    f"{case['case_id']}: failure identity changed"
                )
        if len(case_ids) != len(set(case_ids)):
            raise SimplyContractError("Simply 1.1 case identities must be unique")
        return len(self.positive["cases"]), len(self.negative["cases"])

    def validate_manifest(self, positive: int, negative: int) -> str:
        if set(self.manifest) != {
            "manifest_kind",
            "manifest_version",
            "protocol_version",
            "contract_version",
            "authorship",
            "inherits",
            "files",
            "case_counts",
        }:
            raise SimplyContractError("Simply 1.1 fixture manifest keys are invalid")
        if (
            self.manifest["manifest_kind"] != "strling.simply-builder-fixtures"
            or self.manifest["manifest_version"] != "1.1.0"
            or self.manifest["protocol_version"] != "1.1.0"
            or self.manifest["contract_version"] != "1.0.0"
            or self.manifest["authorship"] != "specification-authored"
        ):
            raise SimplyContractError("Simply 1.1 fixture manifest identity is invalid")
        if self.manifest["inherits"] != {
            "protocol_version": "1.0.0",
            "reference": "spec/frontends/simply/1.0/fixtures/manifest.json",
        }:
            raise SimplyContractError("Simply 1.1 inheritance declaration is invalid")
        if self.manifest["case_counts"] != {
            "negative": negative,
            "positive": positive,
        }:
            raise SimplyContractError("Simply 1.1 fixture counts are stale")
        entries = self.manifest["files"]
        if [entry.get("path") for entry in entries] != list(EXPECTED_1_1_FILES):
            raise SimplyContractError(
                "Simply 1.1 manifest must exactly cover governed inputs"
            )
        for entry in entries:
            if set(entry) != {"path", "sha256"}:
                raise SimplyContractError("Simply 1.1 manifest entry is invalid")
            actual = (
                "sha256:"
                + hashlib.sha256(
                    (self.protocol_root / entry["path"]).read_bytes()
                ).hexdigest()
            )
            if entry["sha256"] != actual:
                raise SimplyContractError(
                    f"Simply 1.1 manifest fingerprint is stale for {entry['path']}"
                )
        certification = {
            "protocol": self.protocol,
            "manifest": self.manifest,
        }
        return "sha256:" + hashlib.sha256(canonical_json(certification)).hexdigest()

    def certify(self) -> dict[str, Any]:
        self.validate_protocol()
        positive, negative = self.validate_cases()
        fingerprint = self.validate_manifest(positive, negative)
        return {
            "schemas": len(self.schemas),
            "operations": len(EXPECTED_1_1_OPERATIONS),
            "inherited_operations": len(EXPECTED_OPERATIONS),
            "positive": positive,
            "negative": negative,
            "fingerprint": fingerprint,
        }


def main() -> int:
    try:
        result = SimplyContractSuite().certify()
        result_1_1 = Simply11ContractSuite().certify()
    except (SimplyContractError, OSError, json.JSONDecodeError) as error:
        print(f"SIMPLY_CONTRACT status=failed error={error}")
        return 1
    print(
        "SIMPLY_CONTRACT status=passed "
        f"schemas={result['schemas']} operations={result['operations']} "
        f"errors={result['errors']} compatibility={result['compatibility']} "
        f"positive={result['positive']} negative={result['negative']} "
        f"fingerprint={result['fingerprint']} "
        f"v1_1_schemas={result_1_1['schemas']} "
        f"v1_1_operations={result_1_1['operations']} "
        f"v1_1_inherited={result_1_1['inherited_operations']} "
        f"v1_1_positive={result_1_1['positive']} "
        f"v1_1_negative={result_1_1['negative']} "
        f"v1_1_fingerprint={result_1_1['fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
