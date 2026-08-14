#!/usr/bin/env python3
"""Validate the canonical Semantic IR conversion-result contract."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "spec" / "conversions" / "semantic" / "1.0"
SCHEMA_PATH = CONTRACT_ROOT / "conversion-result.schema.json"
DOMAIN_PATH = CONTRACT_ROOT / "destination-domain.json"
POSITIVE_FIXTURES = (
    "exact-semantic-dsl.json",
    "exact-simply.json",
    "partial-capture-name.json",
    "unsupported-forward-reference.json",
)
INVALID_FIXTURES = (
    "false-exact-proof.json",
    "missing-manual-decision.json",
    "output-on-unsupported.json",
)
DESTINATION_CONTRACTS = {
    "semantic_strling": ("strling.semantic", "1.0.0"),
    "simply_builder": ("strling.simply-builder", "1.0.0"),
}
DIRECT_SIMPLY_OPERATIONS = {
    "empty",
    "literal",
    "wildcard",
    "character_set",
    "sequence",
    "alternation",
    "group",
    "capture",
    "backreference",
    "position",
    "lookaround",
    "atomic",
    "repeat",
}
CANONICAL_NODE_KINDS = (
    "alternation",
    "atomic",
    "backreference",
    "capture",
    "character_set",
    "empty",
    "literal",
    "lookaround",
    "position",
    "repeat",
    "sequence",
    "wildcard",
)
CANONICAL_MEMBER_KINDS = ("builtin", "literal", "range", "unicode_property")


class SemanticConversionContractError(ValueError):
    """The conversion schema or a cross-object invariant failed."""


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise SemanticConversionContractError(f"{path}: root must be an object")
    return value


def _canonical_json(value: Any) -> bytes:
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


def _sorted_unique(values: list[Any], label: str) -> None:
    keys = [_canonical_json(value) for value in values]
    if keys != sorted(set(keys)):
        raise SemanticConversionContractError(
            f"{label} must be unique and canonically ordered"
        )


class SemanticConversionContractSuite:
    """Certify schema shape, authored evidence, and proof/status correspondence."""

    def __init__(self, contract_root: Path = CONTRACT_ROOT) -> None:
        if __package__:
            from tooling.simply_contract import (
                SimplyContractError,
                SimplyContractSuite,
            )
        else:
            from simply_contract import SimplyContractError, SimplyContractSuite

        self.contract_root = contract_root
        self.schema = _load_json(contract_root / "conversion-result.schema.json")
        self.domain = _load_json(contract_root / "destination-domain.json")
        Draft202012Validator.check_schema(self.schema)
        self.validator = Draft202012Validator(
            self.schema,
            resolver=RefResolver.from_schema(self.schema),
            format_checker=FormatChecker(),
        )
        self.simply = SimplyContractSuite()
        self.simply_error = SimplyContractError

    def validate_suite_structure(self) -> int:
        if self.schema["$id"] != (
            "https://strling.dev/conversions/semantic/1.0/conversion-result.schema.json"
        ):
            raise SemanticConversionContractError(
                "conversion result schema ID is not canonical"
            )
        if self.schema.get("additionalProperties") is not False:
            raise SemanticConversionContractError(
                "conversion result root must reject unknown fields"
            )
        if self.schema["properties"]["conversion_version"] != {"const": "1.0.0"}:
            raise SemanticConversionContractError(
                "conversion version must be independently pinned"
            )
        positive = tuple(
            path.name
            for path in sorted((self.contract_root / "examples").glob("*.json"))
        )
        invalid = tuple(
            path.name
            for path in sorted((self.contract_root / "invalid").glob("*.json"))
        )
        if positive != tuple(sorted(POSITIVE_FIXTURES)):
            raise SemanticConversionContractError(
                "positive fixture inventory must equal the closed 1.0 corpus"
            )
        if invalid != tuple(sorted(INVALID_FIXTURES)):
            raise SemanticConversionContractError(
                "invalid fixture inventory must equal the closed 1.0 corpus"
            )
        self._validate_destination_domain()
        schema_text = json.dumps(self.schema, sort_keys=True).lower()
        for forbidden in (
            "raw_regex",
            "emitted_pattern",
            "match_trace",
            "why_no_match",
            "whynomatch",
            "binding_source",
            "runtime_subject",
        ):
            if forbidden in schema_text:
                raise SemanticConversionContractError(
                    f"conversion schema crosses a forbidden boundary: {forbidden}"
                )
        return 1

    def validate(self, value: Mapping[str, Any]) -> None:
        errors = sorted(
            self.validator.iter_errors(value), key=lambda error: list(error.path)
        )
        if errors:
            error = errors[0]
            raise SemanticConversionContractError(
                f"conversion {_json_path(error.path)}: {error.message}"
            )
        self._validate_correspondence(value)

    def validate_positive_examples(self) -> int:
        paths = [self.contract_root / "examples" / name for name in POSITIVE_FIXTURES]
        for path in paths:
            self.validate(_load_json(path))
        return len(paths)

    def validate_negative_examples(self) -> int:
        count = 0
        for name in INVALID_FIXTURES:
            path = self.contract_root / "invalid" / name
            try:
                self.validate(_load_json(path))
            except SemanticConversionContractError:
                count += 1
                continue
            raise SemanticConversionContractError(
                f"controlled invalid conversion unexpectedly passed: {path}"
            )
        return count

    def certify(self) -> dict[str, Any]:
        schema_count = self.validate_suite_structure()
        positive_count = self.validate_positive_examples()
        negative_count = self.validate_negative_examples()
        inputs = [
            SCHEMA_PATH,
            DOMAIN_PATH,
            *[self.contract_root / "examples" / name for name in POSITIVE_FIXTURES],
            *[self.contract_root / "invalid" / name for name in INVALID_FIXTURES],
        ]
        fingerprint = hashlib.sha256()
        for path in inputs:
            fingerprint.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
            fingerprint.update(b"\0")
            fingerprint.update(path.read_bytes())
            fingerprint.update(b"\0")
        return {
            "schemas": schema_count,
            "positive": positive_count,
            "negative": negative_count,
            "exact": 2,
            "partial": 1,
            "unsupported": 1,
            "node_kinds": len(CANONICAL_NODE_KINDS),
            "member_kinds": len(CANONICAL_MEMBER_KINDS),
            "fingerprint": f"sha256:{fingerprint.hexdigest()}",
        }

    def _validate_destination_domain(self) -> None:
        if self.domain.get("conversion_version") != "1.0.0":
            raise SemanticConversionContractError(
                "destination domain must pin conversion version 1.0.0"
            )
        if self.domain.get("source_contract") != (
            "https://strling.dev/contracts/1.0/semantic-ir.schema.json"
        ):
            raise SemanticConversionContractError(
                "destination domain must name canonical Semantic IR authority"
            )
        if self.domain.get("comment_policy") != "semantic_ir_only":
            raise SemanticConversionContractError(
                "destination domain must retain the source-less comment policy"
            )
        destinations = self.domain.get("destinations")
        if not isinstance(destinations, list):
            raise SemanticConversionContractError("destinations must be an array")
        if [entry.get("id") for entry in destinations] != [
            "semantic_strling",
            "simply_builder",
        ]:
            raise SemanticConversionContractError(
                "destination domain must list the two canonical destinations in order"
            )
        for destination in destinations:
            nodes = destination.get("node_kinds")
            members = destination.get("member_kinds")
            if not isinstance(nodes, list) or not isinstance(members, list):
                raise SemanticConversionContractError(
                    "destination node/member inventories must be arrays"
                )
            if tuple(entry.get("kind") for entry in nodes) != CANONICAL_NODE_KINDS:
                raise SemanticConversionContractError(
                    f"{destination['id']} must cover all twelve canonical node kinds"
                )
            if tuple(entry.get("kind") for entry in members) != CANONICAL_MEMBER_KINDS:
                raise SemanticConversionContractError(
                    f"{destination['id']} must cover all four set-member kinds"
                )
            for entry in [*nodes, *members]:
                if set(entry) != {"kind", "mapping", "disposition"}:
                    raise SemanticConversionContractError(
                        "destination taxonomy entries must be closed"
                    )
                if entry["disposition"] not in {
                    "direct",
                    "name_limited",
                    "topology_limited",
                }:
                    raise SemanticConversionContractError(
                        "destination taxonomy disposition is unknown"
                    )
        simply = destinations[1]
        if simply.get("forbidden_operations") != [
            "import_node",
            "import_program",
            "stdlib_helper",
        ]:
            raise SemanticConversionContractError(
                "Simply conversion must close the forbidden operation inventory"
            )

    def _validate_correspondence(self, document: Mapping[str, Any]) -> None:
        destination = document["destination"]
        destination_contract = document["destination_contract"]
        if (
            destination_contract["id"],
            destination_contract["version"],
        ) != DESTINATION_CONTRACTS[destination]:
            raise SemanticConversionContractError(
                "destination and destination contract do not correspond"
            )

        node_mappings = document["node_mappings"]
        capture_mappings = document["capture_mappings"]
        self._validate_mappings(node_mappings, "source_node_id", "node mappings")
        self._validate_mappings(
            capture_mappings, "source_capture_id", "capture mappings"
        )
        issue_ids = [issue["issue_id"] for issue in document["issues"]]
        if issue_ids != sorted(set(issue_ids)):
            raise SemanticConversionContractError(
                "issue IDs must be unique and canonically ordered"
            )
        _sorted_unique(document["explanation_links"], "explanation links")
        _sorted_unique(document["target_annotations"], "target annotations")
        for link in document["explanation_links"]:
            if link["semantic_program"] != document["source_program"]:
                raise SemanticConversionContractError(
                    "explanation link program must equal the conversion source"
                )

        output = document.get("output")
        if output is not None and output["kind"] != destination:
            raise SemanticConversionContractError(
                "output kind must equal the requested destination"
            )
        if output is not None:
            if len(node_mappings) != document["source_summary"]["node_count"]:
                raise SemanticConversionContractError(
                    "executable output must map every source node"
                )
            if len(capture_mappings) != document["source_summary"]["capture_count"]:
                raise SemanticConversionContractError(
                    "executable output must map every source capture"
                )
            if destination == "semantic_strling":
                self._validate_semantic_output(output, node_mappings, capture_mappings)
            else:
                self._validate_simply_output(output, node_mappings)

        self._validate_status(document, output)

    def _validate_mappings(
        self, mappings: list[Mapping[str, Any]], identity_key: str, label: str
    ) -> None:
        identities = [mapping[identity_key] for mapping in mappings]
        if identities != sorted(set(identities)):
            raise SemanticConversionContractError(
                f"{label} must have unique sorted source identities"
            )
        destination_keys = [mapping["destination_key"] for mapping in mappings]
        if len(destination_keys) != len(set(destination_keys)):
            raise SemanticConversionContractError(
                f"{label} must have unique destination keys"
            )

    def _validate_semantic_output(
        self,
        output: Mapping[str, Any],
        node_mappings: list[Mapping[str, Any]],
        capture_mappings: list[Mapping[str, Any]],
    ) -> None:
        encoded = output["text"].encode("utf-8")
        actual = hashlib.sha256(encoded).hexdigest()
        if actual != output["sha256"]:
            raise SemanticConversionContractError(
                "Semantic STRling output digest does not match its UTF-8 bytes"
            )
        for mapping in node_mappings:
            span = mapping.get("byte_span")
            if span is None:
                raise SemanticConversionContractError(
                    "Semantic STRling node mappings require byte spans"
                )
            self._validate_span(span, len(encoded), "node byte span")
        for mapping in capture_mappings:
            span = mapping.get("identifier_span")
            if span is None:
                raise SemanticConversionContractError(
                    "Semantic STRling capture mappings require identifier spans"
                )
            self._validate_span(span, len(encoded), "capture identifier span")

    def _validate_simply_output(
        self, output: Mapping[str, Any], node_mappings: list[Mapping[str, Any]]
    ) -> None:
        request = output["request"]
        try:
            self.simply._validate("builder-request.schema.json", request)
        except self.simply_error as exc:
            raise SemanticConversionContractError(
                f"Simply output violates its destination contract: {exc}"
            ) from exc
        operations = {step["operation"] for step in request["steps"]}
        disallowed = operations - DIRECT_SIMPLY_OPERATIONS
        if disallowed:
            raise SemanticConversionContractError(
                "Simply conversion output must use direct operations only: "
                + ", ".join(sorted(disallowed))
            )
        compile_projection = request["compile"]
        if "target_profile" in compile_projection:
            raise SemanticConversionContractError(
                "Simply conversion output must remain target-neutral"
            )
        if compile_projection["requested_outputs"] != ["semantic"]:
            raise SemanticConversionContractError(
                "Simply conversion output must request only canonical semantics"
            )
        step_ids = {step["step_id"] for step in request["steps"]}
        if {mapping["destination_key"] for mapping in node_mappings} != step_ids:
            raise SemanticConversionContractError(
                "Simply node mappings must correspond exactly to emitted steps"
            )
        if any("byte_span" in mapping for mapping in node_mappings):
            raise SemanticConversionContractError(
                "Simply node mappings cannot claim textual byte spans"
            )

    def _validate_status(
        self, document: Mapping[str, Any], output: Mapping[str, Any] | None
    ) -> None:
        status = document["status"]
        evidence = document["equivalence"]
        issues = document["issues"]
        categories = {issue["category"] for issue in issues}
        codes = {issue["code"] for issue in issues}
        source = evidence["source_fingerprint"]
        reconstructed = evidence.get("reconstructed_fingerprint")

        if status == "exact":
            if output is None or evidence["status"] != "proven":
                raise SemanticConversionContractError(
                    "exact status requires output and proven equivalence"
                )
            if reconstructed is None or reconstructed != source:
                raise SemanticConversionContractError(
                    "exact status requires equal source and reconstructed fingerprints"
                )
            if categories - {"nonsemantic_loss"}:
                raise SemanticConversionContractError(
                    "exact status cannot carry semantic loss, approximation, manual, or unsupported issues"
                )
        elif status == "partial":
            if output is None or evidence["status"] != "not_proven":
                raise SemanticConversionContractError(
                    "partial status requires output and non-proven equivalence"
                )
            if reconstructed is not None:
                raise SemanticConversionContractError(
                    "partial status cannot publish a reconstructed proof fingerprint"
                )
            if not categories.intersection(
                {"loss", "approximation", "manual_decision"}
            ):
                raise SemanticConversionContractError(
                    "partial status requires an explicit loss, approximation, or manual decision"
                )
        else:
            if (
                output is not None
                or document["node_mappings"]
                or document["capture_mappings"]
            ):
                raise SemanticConversionContractError(
                    "unsupported status cannot carry executable output or mappings"
                )
            if evidence["status"] != "not_applicable" or reconstructed is not None:
                raise SemanticConversionContractError(
                    "unsupported status requires non-applicable equivalence"
                )
            if "unsupported" not in categories:
                raise SemanticConversionContractError(
                    "unsupported status requires at least one blocking issue"
                )

        if "capture_name_substituted" in codes:
            if "manual_capture_name_required" not in codes:
                raise SemanticConversionContractError(
                    "capture-name substitution requires an explicit manual decision"
                )
            replacements = {
                issue.get("replacement")
                for issue in issues
                if issue["code"] == "capture_name_substituted"
            }
            decisions = {
                issue.get("replacement")
                for issue in issues
                if issue["code"] == "manual_capture_name_required"
            }
            if None in replacements or not replacements.issubset(decisions):
                raise SemanticConversionContractError(
                    "capture-name decisions must correspond to every substitution"
                )

    def _validate_span(
        self, span: Mapping[str, int], byte_length: int, label: str
    ) -> None:
        if span["start"] >= span["end"] or span["end"] > byte_length:
            raise SemanticConversionContractError(
                f"{label} must be a non-empty half-open range within output bytes"
            )


def main() -> int:
    result = SemanticConversionContractSuite().certify()
    print(
        "SEMANTIC_CONVERSION_CONTRACT status=passed "
        f"schemas={result['schemas']} positive={result['positive']} "
        f"negative={result['negative']} exact={result['exact']} "
        f"partial={result['partial']} unsupported={result['unsupported']} "
        f"node_kinds={result['node_kinds']} member_kinds={result['member_kinds']} "
        f"fingerprint={result['fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
