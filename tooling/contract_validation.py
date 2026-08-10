#!/usr/bin/env python3
"""Validate canonical STRling contracts and their cross-object invariants."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "spec" / "contracts" / "1.0"


class ContractValidationError(ValueError):
    """A schema or cross-contract invariant was violated."""


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object from *path*."""
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ContractValidationError(f"{path}: root value must be an object")
    return value


def canonical_json(value: Any) -> bytes:
    """Return the deterministic JSON encoding governed by the contract suite."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _json_path(parts: Iterable[Any]) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


class ContractSuite:
    """Loaded schemas plus semantic validation not expressible in JSON Schema."""

    def __init__(self, contract_root: Path = CONTRACT_ROOT) -> None:
        self.contract_root = contract_root
        self.schemas = {
            path.name: load_json(path)
            for path in sorted(contract_root.glob("*.schema.json"))
        }
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)
        schema_store = {schema["$id"]: schema for schema in self.schemas.values()}
        self.validators = {
            name: Draft202012Validator(
                schema,
                resolver=RefResolver.from_schema(schema, store=schema_store),
                format_checker=FormatChecker(),
            )
            for name, schema in self.schemas.items()
        }

    def validate(self, schema_name: str, value: Mapping[str, Any]) -> None:
        """Validate *value* against one schema and its cross-contract rules."""
        validator = self.validators[schema_name]
        errors = sorted(
            validator.iter_errors(value), key=lambda error: list(error.path)
        )
        if errors:
            error = errors[0]
            raise ContractValidationError(
                f"{schema_name} {_json_path(error.path)}: {error.message}"
            )
        if schema_name == "source.schema.json":
            self._validate_source(value)
        elif schema_name == "semantic-ir.schema.json":
            self._validate_semantic(value)

    def validate_positive_examples(self) -> int:
        """Validate every authored positive source and Semantic IR example."""
        count = 0
        for family, schema_name in (
            ("source", "source.schema.json"),
            ("semantic-ir", "semantic-ir.schema.json"),
        ):
            for path in sorted(
                (self.contract_root / "examples" / family).glob("*.json")
            ):
                self.validate(schema_name, load_json(path))
                count += 1
        return count

    def validate_negative_examples(self) -> int:
        """Prove every controlled malformed example is rejected."""
        count = 0
        for family, schema_name in (
            ("source", "source.schema.json"),
            ("semantic-ir", "semantic-ir.schema.json"),
        ):
            for path in sorted(
                (self.contract_root / "invalid" / family).glob("*.json")
            ):
                try:
                    self.validate(schema_name, load_json(path))
                except ContractValidationError:
                    count += 1
                    continue
                raise ContractValidationError(
                    f"controlled invalid example unexpectedly passed: {path}"
                )
        return count

    def _validate_source(self, source: Mapping[str, Any]) -> None:
        content = source["content"]
        if content["kind"] == "inline":
            self._utf8_boundaries(content["text"])
        provenance = source["provenance"]
        for parent in provenance.get("parent_sources", []):
            span = parent.get("span")
            if span is not None:
                if span["source_id"] != parent["source_id"]:
                    raise ContractValidationError(
                        "parent provenance span must identify its parent source"
                    )
                self._validate_span(span, None)

    def _validate_semantic(self, program: Mapping[str, Any]) -> None:
        sources: dict[str, Mapping[str, Any]] = {}
        for source in program.get("sources", []):
            self._validate_source(source)
            source_id = source["source_id"]
            if source_id in sources:
                raise ContractValidationError(f"duplicate source_id {source_id}")
            if source["specification_version"] != program["specification_version"]:
                raise ContractValidationError(
                    f"source {source_id} uses a different specification version"
                )
            sources[source_id] = source

        nodes = list(iter_nodes(program["root"]))
        node_ids: set[str] = set()
        captures: set[str] = set()
        capture_names: set[str] = set()
        references: list[str] = []

        for node in nodes:
            node_id = node["node_id"]
            if node_id in node_ids:
                raise ContractValidationError(f"duplicate node_id {node_id}")
            node_ids.add(node_id)

            origin = node.get("origin")
            if origin is not None:
                self._validate_origin(origin, sources)

            kind = node["kind"]
            if kind == "sequence":
                items = node["items"]
                if any(item["kind"] == "sequence" for item in items):
                    raise ContractValidationError("canonical sequence cannot be nested")
                if any(
                    left["kind"] == right["kind"] == "literal"
                    for left, right in zip(items, items[1:])
                ):
                    raise ContractValidationError(
                        "adjacent canonical literals must be coalesced"
                    )
            elif kind == "alternation" and any(
                branch["kind"] == "alternation" for branch in node["branches"]
            ):
                raise ContractValidationError("canonical alternation cannot be nested")
            elif kind == "repeat":
                maximum = node["max"]
                if maximum is not None and maximum < node["min"]:
                    raise ContractValidationError(
                        "finite repetition maximum cannot be less than minimum"
                    )
            elif kind == "character_set":
                self._validate_character_set(node["members"])
            elif kind == "capture":
                capture_id = node["capture_id"]
                if capture_id in captures:
                    raise ContractValidationError(f"duplicate capture_id {capture_id}")
                captures.add(capture_id)
                name = node.get("name")
                if name is not None:
                    if name in capture_names:
                        raise ContractValidationError(f"duplicate capture name {name}")
                    capture_names.add(name)
            elif kind == "backreference":
                references.append(node["capture_id"])

        for capture_id in references:
            if capture_id not in captures:
                raise ContractValidationError(
                    f"backreference resolves to missing capture_id {capture_id}"
                )

    def _validate_origin(
        self,
        origin: Mapping[str, Any],
        sources: Mapping[str, Mapping[str, Any]],
    ) -> None:
        spans = origin.get("source_spans", [])
        span_keys = [(span["source_id"], span["start"], span["end"]) for span in spans]
        if span_keys != sorted(set(span_keys)):
            raise ContractValidationError(
                "origin source_spans must be unique and canonically sorted"
            )
        for span in spans:
            source_id = span["source_id"]
            if source_id not in sources:
                raise ContractValidationError(
                    f"origin refers to undeclared source_id {source_id}"
                )
            self._validate_span(span, sources[source_id])

        derived = origin.get("derived_from_node_ids", [])
        if derived != sorted(set(derived)):
            raise ContractValidationError(
                "derived_from_node_ids must be unique and canonically sorted"
            )

    def _validate_span(
        self,
        span: Mapping[str, Any],
        source: Mapping[str, Any] | None,
    ) -> None:
        start = span["start"]
        end = span["end"]
        if start > end:
            raise ContractValidationError("source span start must not exceed end")
        if source is None or source["content"]["kind"] != "inline":
            return
        boundaries = self._utf8_boundaries(source["content"]["text"])
        if start not in boundaries or end not in boundaries:
            raise ContractValidationError(
                "source span endpoints must be UTF-8 code-point boundaries"
            )

    @staticmethod
    def _utf8_boundaries(text: str) -> set[int]:
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ContractValidationError(
                "source text must contain valid Unicode"
            ) from error
        boundaries = {0}
        offset = 0
        for character in text:
            offset += len(character.encode("utf-8"))
            boundaries.add(offset)
        if offset != len(encoded):
            raise ContractValidationError("UTF-8 boundary calculation was inconsistent")
        return boundaries

    @staticmethod
    def _validate_character_set(members: list[Mapping[str, Any]]) -> None:
        keys = [_character_member_key(member) for member in members]
        if keys != sorted(set(keys)):
            raise ContractValidationError(
                "character-set members must be unique and canonically sorted"
            )
        for member in members:
            if member["kind"] == "range" and ord(member["start"]) > ord(member["end"]):
                raise ContractValidationError(
                    "character-set range start cannot exceed its end"
                )


def _character_member_key(member: Mapping[str, Any]) -> tuple[Any, ...]:
    kind = member["kind"]
    if kind == "literal":
        return (0, member["value"])
    if kind == "range":
        return (1, member["start"], member["end"])
    if kind == "builtin":
        return (2, member["name"], member["domain"], member["negated"])
    return (
        3,
        member["property"],
        member.get("value", ""),
        member["negated"],
    )


def iter_nodes(root: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Yield Semantic IR nodes in deterministic preorder."""
    yield root
    kind = root["kind"]
    if kind == "sequence":
        for child in root["items"]:
            yield from iter_nodes(child)
    elif kind == "alternation":
        for child in root["branches"]:
            yield from iter_nodes(child)
    elif kind in {"repeat", "capture", "lookaround", "atomic"}:
        yield from iter_nodes(root["body"])


def main() -> int:
    suite = ContractSuite()
    positive_count = suite.validate_positive_examples()
    negative_count = suite.validate_negative_examples()
    print(
        "CANONICAL_CONTRACTS status=passed "
        f"schemas={len(suite.schemas)} positive={positive_count} negative={negative_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
