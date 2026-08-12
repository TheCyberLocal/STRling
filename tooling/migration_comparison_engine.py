#!/usr/bin/env python3
"""Stable pairing and factual field comparison for migration projections."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from tooling import migration_comparison as projection_contract
from tooling.legacy_reference import python_reference as reference

COMPARISON_KIND = projection_contract.CONTRACT["comparison_kind"]
COMPARISON_SCHEMA_VERSION = projection_contract.COMPARISON_SCHEMA_VERSION
COMPARATOR_IMPLEMENTATION_VERSION = (
    projection_contract.COMPARATOR_IMPLEMENTATION_VERSION
)
TAXONOMY_VERSION = projection_contract.TAXONOMY_VERSION


class PairingError(projection_contract.ComparisonContractError):
    """Two present projections do not satisfy stable pairing authority."""


def _require_fingerprint(value: Any, location: str) -> str:
    return projection_contract._require_fingerprint(value, location)


def _validate_projection_source(
    source: Any, semantic_observation: Mapping[str, Any], rule_ids: tuple[str, ...]
) -> dict[str, Any]:
    value = projection_contract._require_object(source, "projection.source")
    projection_contract._exact_keys(
        value,
        (
            "case",
            "corpus",
            "implementation",
            "observation_identity",
            "observation_schema_version",
            "operation",
            "protocol_version",
            "request",
            "runner",
            "surface",
        ),
        "projection.source",
    )
    case = projection_contract._require_object(value["case"], "projection.source.case")
    projection_contract._exact_keys(
        case,
        ("comparison_identity", "id", "source_identity"),
        "projection.source.case",
    )
    projection_contract._require_nonempty_string(
        case["id"], "projection.source.case.id"
    )
    _require_fingerprint(
        case["source_identity"], "projection.source.case.source_identity"
    )
    if case["comparison_identity"] is not None:
        _require_fingerprint(
            case["comparison_identity"],
            "projection.source.case.comparison_identity",
        )

    if rule_ids:
        projection_contract._exact_keys(
            semantic_observation,
            ("outcome",),
            "projection.semantic_observation",
        )
        outcome = projection_contract._validate_outcome(semantic_observation["outcome"])
        raw_observation = {
            "implementation": copy.deepcopy(value["implementation"]),
            "kind": reference.OBSERVATION_KIND,
            "observation_schema_version": value["observation_schema_version"],
            "operation": value["operation"],
            "outcome": outcome,
            "protocol_version": value["protocol_version"],
            "request": copy.deepcopy(value["request"]),
            "runner": copy.deepcopy(value["runner"]),
            "surface": value["surface"],
        }
    else:
        raw_observation = copy.deepcopy(dict(semantic_observation))

    validated_observation = projection_contract.validate_observation(raw_observation)
    for field in (
        "implementation",
        "observation_schema_version",
        "operation",
        "protocol_version",
        "request",
        "runner",
        "surface",
    ):
        if value[field] != validated_observation[field]:
            raise projection_contract.ComparisonContractError(
                f"projection source {field} does not match semantic observation"
            )
    if value["observation_identity"] != projection_contract.canonical_fingerprint(
        validated_observation
    ):
        raise projection_contract.ComparisonContractError(
            "projection source observation identity does not match"
        )

    projection_contract._validate_source_context(
        {
            "case_id": case["id"],
            "case_identity": case["source_identity"],
            "comparison_corpus_version": None,
            "corpus": value["corpus"],
        },
        validated_observation,
    )
    return reference.canonicalize(value)


def validate_projection_artifact(value: Any) -> dict[str, Any]:
    """Validate a self-contained projection before pairing or comparison."""

    projection = projection_contract._require_object(value, "projection")
    projection_contract._exact_keys(
        projection,
        (
            "kind",
            "normalization_rule_ids",
            "normalization_rules_version",
            "projection_fingerprint",
            "projection_schema_version",
            "semantic_observation",
            "source",
        ),
        "projection",
    )
    if projection["kind"] != projection_contract.PROJECTION_KIND:
        raise projection_contract.ComparisonContractError(
            "projection kind is incompatible"
        )
    if (
        projection["projection_schema_version"]
        != projection_contract.PROJECTION_SCHEMA_VERSION
    ):
        raise projection_contract.ComparisonContractError(
            "projection schema version is incompatible"
        )
    if (
        projection["normalization_rules_version"]
        != projection_contract.NORMALIZATION_RULES_VERSION
    ):
        raise projection_contract.ComparisonContractError(
            "normalization rules version is incompatible"
        )
    raw_rule_ids = projection["normalization_rule_ids"]
    if not isinstance(raw_rule_ids, list):
        raise projection_contract.ComparisonContractError(
            "projection normalization rules must be an array"
        )
    rule_ids = projection_contract._validate_rule_ids(raw_rule_ids)
    semantic = projection_contract._require_object(
        projection["semantic_observation"], "projection.semantic_observation"
    )
    source = _validate_projection_source(projection["source"], semantic, rule_ids)
    _require_fingerprint(
        projection["projection_fingerprint"], "projection.projection_fingerprint"
    )
    fingerprint_body = {
        key: copy.deepcopy(projection[key])
        for key in projection
        if key != "projection_fingerprint"
    }
    expected_fingerprint = projection_contract.canonical_fingerprint(fingerprint_body)
    if projection["projection_fingerprint"] != expected_fingerprint:
        raise projection_contract.ComparisonContractError(
            "projection fingerprint does not match its content"
        )
    return reference.canonicalize(
        {
            **fingerprint_body,
            "projection_fingerprint": expected_fingerprint,
            "source": source,
        }
    )


def _pairing_semantics(projection: Mapping[str, Any]) -> dict[str, Any]:
    source = projection["source"]
    request = source["request"]["value"]
    return {
        "case_id": source["case"]["id"],
        "input": request["input"],
        "operation": source["operation"],
        "options": request["options"],
    }


def _require_pair(left: Mapping[str, Any], right: Mapping[str, Any]) -> None:
    if left["projection_schema_version"] != right["projection_schema_version"]:
        raise PairingError("projection schema versions do not match")
    if left["normalization_rules_version"] != right["normalization_rules_version"]:
        raise PairingError("normalization rules versions do not match")
    if left["normalization_rule_ids"] != right["normalization_rule_ids"]:
        raise PairingError("normalization rule identities do not match")
    left_identity = left["source"]["case"]["comparison_identity"]
    right_identity = right["source"]["case"]["comparison_identity"]
    if left_identity is None or right_identity is None:
        raise PairingError("pair lacks explicit semantic correspondence identity")
    if left_identity != right_identity:
        raise PairingError("comparison case identities do not match")
    if _pairing_semantics(left) != _pairing_semantics(right):
        raise PairingError("pairing request semantics do not match")


def _surface_compatible(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_runner = left["source"]["runner"]["id"]
    right_runner = right["source"]["runner"]["id"]
    if {left_runner, right_runner} != {"python", "typescript"}:
        return False
    operation = left["source"]["operation"]
    correspondence = next(
        (
            entry
            for entry in projection_contract.CONTRACT["surface_correspondence"]
            if entry["operation"] == operation
        ),
        None,
    )
    if correspondence is None:
        return False
    return (
        left["source"]["surface"] == correspondence[left_runner]
        and right["source"]["surface"] == correspondence[right_runner]
    )


def _outcome(projection: Mapping[str, Any]) -> Mapping[str, Any]:
    return projection["semantic_observation"]["outcome"]


def _unsupported_reason(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> str | None:
    projections = (left, right)
    if not any(_outcome(item)["status"] == "unsupported" for item in projections):
        return None
    for item in projections:
        source = item["source"]
        operation = source["operation"]
        if (
            source["runner"]["id"] == "python"
            and operation in reference.OPERATION_SPECS
            and not reference.OPERATION_SPECS[operation]["exposed"]
        ):
            return "operation_not_exposed"
    return "unsupported_operation"


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise projection_contract.ComparisonContractError(
        "comparison value is not canonical JSON"
    )


def _pointer(path: tuple[str, ...]) -> str:
    if not path:
        return "/"
    escaped = (segment.replace("~", "~0").replace("/", "~1") for segment in path)
    return "/" + "/".join(escaped)


def _presence(present: bool, value: Any = None) -> dict[str, Any]:
    result = {"present": present}
    if present:
        result["value"] = copy.deepcopy(value)
    return result


def _difference(
    path: tuple[str, ...],
    kind: str,
    *,
    left_present: bool,
    right_present: bool,
    left: Any = None,
    right: Any = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "left": _presence(left_present, left),
        "path": _pointer(path),
        "right": _presence(right_present, right),
    }


def field_differences(
    left: Any, right: Any, path: tuple[str, ...] = ()
) -> list[dict[str, Any]]:
    """Return deterministic, non-collapsed JSON field differences."""

    left_type = _json_type(left)
    right_type = _json_type(right)
    if left_type != right_type:
        return [
            _difference(
                path,
                "type_mismatch",
                left_present=True,
                right_present=True,
                left=left,
                right=right,
            )
        ]
    if isinstance(left, dict) and isinstance(right, dict):
        differences: list[dict[str, Any]] = []
        for key in sorted(set(left) | set(right)):
            nested_path = (*path, key)
            if key not in left:
                differences.append(
                    _difference(
                        nested_path,
                        "left_missing",
                        left_present=False,
                        right_present=True,
                        right=right[key],
                    )
                )
            elif key not in right:
                differences.append(
                    _difference(
                        nested_path,
                        "right_missing",
                        left_present=True,
                        right_present=False,
                        left=left[key],
                    )
                )
            else:
                differences.extend(
                    field_differences(left[key], right[key], nested_path)
                )
        return differences
    if isinstance(left, list) and isinstance(right, list):
        differences = []
        for index in range(max(len(left), len(right))):
            nested_path = (*path, str(index))
            if index >= len(left):
                differences.append(
                    _difference(
                        nested_path,
                        "left_missing",
                        left_present=False,
                        right_present=True,
                        right=right[index],
                    )
                )
            elif index >= len(right):
                differences.append(
                    _difference(
                        nested_path,
                        "right_missing",
                        left_present=True,
                        right_present=False,
                        left=left[index],
                    )
                )
            else:
                differences.extend(
                    field_differences(left[index], right[index], nested_path)
                )
        return differences
    if reference.canonical_json(left) != reference.canonical_json(right):
        return [
            _difference(
                path,
                "value_mismatch",
                left_present=True,
                right_present=True,
                left=left,
                right=right,
            )
        ]
    return []


def _side(projection: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if projection is None:
        return None
    return {
        "normalization_rule_ids": copy.deepcopy(projection["normalization_rule_ids"]),
        "projection_fingerprint": projection["projection_fingerprint"],
        "source": copy.deepcopy(projection["source"]),
    }


def compare_projections(left: Any | None, right: Any | None) -> dict[str, Any]:
    """Pair validated projections and emit factual comparison evidence."""

    if left is None and right is None:
        raise PairingError("a comparison requires at least one projection")
    before_left = None if left is None else reference.canonical_json(left)
    before_right = None if right is None else reference.canonical_json(right)
    validated_left = None if left is None else validate_projection_artifact(left)
    validated_right = None if right is None else validate_projection_artifact(right)
    present = validated_left or validated_right
    assert present is not None

    reason: str | None = None
    differences: list[dict[str, Any]] = []
    if validated_left is None or validated_right is None:
        state = "not_comparable"
        reason = "missing_counterpart"
        relationship = "not_comparable"
    else:
        _require_pair(validated_left, validated_right)
        reason = _unsupported_reason(validated_left, validated_right)
        if reason is None and not _surface_compatible(validated_left, validated_right):
            reason = "incompatible_surface"
        if reason is not None:
            state = "not_comparable"
            relationship = "not_comparable"
        else:
            state = "comparable"
            differences = field_differences(
                validated_left["semantic_observation"],
                validated_right["semantic_observation"],
            )
            relationship = (
                "equivalent_observation" if not differences else "differing_observation"
            )

    left_source = None if validated_left is None else validated_left["source"]
    right_source = None if validated_right is None else validated_right["source"]
    case_identity = present["source"]["case"]["comparison_identity"]
    result = {
        "case_id": present["source"]["case"]["id"],
        "case_identity": case_identity,
        "comparability": {"reason": reason, "state": state},
        "comparator_implementation_version": COMPARATOR_IMPLEMENTATION_VERSION,
        "comparison_schema_version": COMPARISON_SCHEMA_VERSION,
        "differences": differences,
        "kind": COMPARISON_KIND,
        "left": _side(validated_left),
        "operation": present["source"]["operation"],
        "relationship": relationship,
        "right": _side(validated_right),
        "surfaces": {
            "left": None if left_source is None else left_source["surface"],
            "right": None if right_source is None else right_source["surface"],
        },
        "taxonomy_version": TAXONOMY_VERSION,
    }
    result["comparison_identity"] = projection_contract.canonical_fingerprint(result)
    if left is not None and reference.canonical_json(left) != before_left:
        raise projection_contract.ComparisonContractError(
            "comparison mutated the left projection"
        )
    if right is not None and reference.canonical_json(right) != before_right:
        raise projection_contract.ComparisonContractError(
            "comparison mutated the right projection"
        )
    return reference.canonicalize(result)
