#!/usr/bin/env python3
"""Deterministic comparison evidence above immutable historical observations."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tooling.legacy_reference import python_reference as reference

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path(__file__).with_name("migration_comparison_contract.json")
FINGERPRINT_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ComparisonContractError(Exception):
    """Comparison input or derived evidence violates the locked contract."""


def _load_contract() -> dict[str, Any]:
    try:
        value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ComparisonContractError(
            "the migration comparison contract is unavailable or malformed"
        ) from error
    if not isinstance(value, dict):
        raise ComparisonContractError(
            "the migration comparison contract must be an object"
        )
    return reference.canonicalize(value)


CONTRACT = _load_contract()
COMPARISON_SCHEMA_VERSION = CONTRACT["comparison_schema_version"]
COMPARATOR_IMPLEMENTATION_VERSION = CONTRACT["comparator_implementation_version"]
NORMALIZATION_RULES_VERSION = CONTRACT["normalization_rules_version"]
PROJECTION_KIND = CONTRACT["projection_kind"]
PROJECTION_SCHEMA_VERSION = CONTRACT["projection_schema_version"]
TAXONOMY_VERSION = CONTRACT["taxonomy_version"]
NORMALIZATION_RULE_IDS = tuple(rule["id"] for rule in CONTRACT["normalization_rules"])


def canonical_fingerprint(value: Any) -> str:
    return reference.canonical_fingerprint(value)


def canonical_line(value: Any) -> str:
    return reference.canonical_line(value)


def _require_object(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ComparisonContractError(f"{location} must be an object")
    return value


def _exact_keys(
    value: Mapping[str, Any], expected: Sequence[str], location: str
) -> None:
    if sorted(value) != sorted(expected):
        wanted = ", ".join(sorted(expected))
        raise ComparisonContractError(f"{location} keys must be exactly: {wanted}")


def _require_nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ComparisonContractError(f"{location} must be a non-empty string")
    return value


def _require_fingerprint(value: Any, location: str) -> str:
    if not isinstance(value, str) or FINGERPRINT_PATTERN.fullmatch(value) is None:
        raise ComparisonContractError(
            f"{location} must be a canonical sha256 fingerprint"
        )
    return value


def _surface_registry() -> dict[tuple[str, str], str]:
    registry: dict[tuple[str, str], str] = {}
    for entry in CONTRACT["surface_correspondence"]:
        operation = entry["operation"]
        for runner_id in ("python", "typescript"):
            registry[(runner_id, operation)] = entry[runner_id]
    return registry


SURFACE_REGISTRY = _surface_registry()


def _validate_runner(value: Any) -> dict[str, Any]:
    runner = _require_object(value, "observation.runner")
    _exact_keys(runner, ("id", "kind", "language", "version"), "observation.runner")
    if runner["kind"] != "strling.legacy-reference-runner":
        raise ComparisonContractError(
            "observation.runner.kind is not a historical reference runner"
        )
    for field in ("id", "language", "version"):
        _require_nonempty_string(runner[field], f"observation.runner.{field}")
    if runner["id"] not in ("python", "typescript"):
        raise ComparisonContractError(
            f"observation runner '{runner['id']}' has no projection adapter"
        )
    return reference.canonicalize(runner)


def _validate_implementation(value: Any) -> dict[str, Any]:
    implementation = _require_object(value, "observation.implementation")
    for field in ("algorithm", "fingerprint", "kind", "runtime"):
        if field not in implementation:
            raise ComparisonContractError(
                f"observation.implementation.{field} is required"
            )
    if implementation["algorithm"] != "sha256":
        raise ComparisonContractError(
            "observation.implementation.algorithm must be 'sha256'"
        )
    _require_fingerprint(
        implementation["fingerprint"], "observation.implementation.fingerprint"
    )
    _require_nonempty_string(implementation["kind"], "observation.implementation.kind")
    runtime = _require_object(
        implementation["runtime"], "observation.implementation.runtime"
    )
    _exact_keys(runtime, ("name", "version"), "observation.implementation.runtime")
    for field in ("name", "version"):
        _require_nonempty_string(
            runtime[field], f"observation.implementation.runtime.{field}"
        )
    try:
        return reference.canonicalize(implementation)
    except TypeError as error:
        raise ComparisonContractError(str(error)) from error


def _validate_request(value: Any, operation: str, surface: str) -> dict[str, Any]:
    request = _require_object(value, "observation.request")
    _exact_keys(
        request,
        ("algorithm", "fingerprint", "value"),
        "observation.request",
    )
    if request["algorithm"] != "sha256":
        raise ComparisonContractError("observation.request.algorithm must be 'sha256'")
    _require_fingerprint(request["fingerprint"], "observation.request.fingerprint")
    request_value = _require_object(request["value"], "observation.request.value")
    _exact_keys(
        request_value,
        (
            "expected_legacy_surface",
            "input",
            "kind",
            "operation",
            "options",
            "protocol_version",
        ),
        "observation.request.value",
    )
    if request_value["kind"] != reference.REQUEST_KIND:
        raise ComparisonContractError("observation request kind is incompatible")
    if request_value["protocol_version"] != reference.PROTOCOL_VERSION:
        raise ComparisonContractError("observation request protocol is incompatible")
    if request_value["operation"] != operation:
        raise ComparisonContractError("observation request operation does not match")
    if request_value["expected_legacy_surface"] != surface:
        raise ComparisonContractError("observation request surface does not match")
    _require_object(request_value["input"], "observation.request.value.input")
    _require_object(request_value["options"], "observation.request.value.options")
    expected_fingerprint = canonical_fingerprint(request_value)
    if request["fingerprint"] != expected_fingerprint:
        raise ComparisonContractError("observation request fingerprint does not match")
    try:
        return reference.canonicalize(request)
    except TypeError as error:
        raise ComparisonContractError(str(error)) from error


def _validate_outcome(value: Any) -> dict[str, Any]:
    outcome = _require_object(value, "observation.outcome")
    status = outcome.get("status")
    if status == "success":
        _exact_keys(outcome, ("evidence", "status"), "observation.outcome")
        _require_object(outcome["evidence"], "observation.outcome.evidence")
    elif status == "legacy_failure":
        _exact_keys(outcome, ("failure", "status"), "observation.outcome")
        _require_object(outcome["failure"], "observation.outcome.failure")
    elif status == "unsupported":
        _exact_keys(outcome, ("reason", "status"), "observation.outcome")
        _require_nonempty_string(outcome["reason"], "observation.outcome.reason")
    else:
        raise ComparisonContractError(
            "observation.outcome.status must be success, legacy_failure, or unsupported"
        )
    try:
        return reference.canonicalize(outcome)
    except TypeError as error:
        raise ComparisonContractError(str(error)) from error


def validate_observation(value: Any) -> dict[str, Any]:
    """Validate one current historical observation without changing it."""

    observation = _require_object(value, "observation")
    _exact_keys(
        observation,
        (
            "implementation",
            "kind",
            "observation_schema_version",
            "operation",
            "outcome",
            "protocol_version",
            "request",
            "runner",
            "surface",
        ),
        "observation",
    )
    if observation["kind"] != reference.OBSERVATION_KIND:
        raise ComparisonContractError("observation kind is incompatible")
    if (
        observation["observation_schema_version"]
        != reference.OBSERVATION_SCHEMA_VERSION
    ):
        raise ComparisonContractError("observation schema version is incompatible")
    if observation["protocol_version"] != reference.PROTOCOL_VERSION:
        raise ComparisonContractError("observation protocol version is incompatible")

    runner = _validate_runner(observation["runner"])
    operation = _require_nonempty_string(
        observation["operation"], "observation.operation"
    )
    surface = _require_nonempty_string(observation["surface"], "observation.surface")
    expected_surface = SURFACE_REGISTRY.get((runner["id"], operation))
    if expected_surface is None:
        raise ComparisonContractError(
            f"operation '{operation}' has no registered surface for runner '{runner['id']}'"
        )
    if surface != expected_surface:
        raise ComparisonContractError(
            f"observation surface does not match registered '{operation}' surface"
        )

    return {
        "implementation": _validate_implementation(observation["implementation"]),
        "kind": reference.OBSERVATION_KIND,
        "observation_schema_version": reference.OBSERVATION_SCHEMA_VERSION,
        "operation": operation,
        "outcome": _validate_outcome(observation["outcome"]),
        "protocol_version": reference.PROTOCOL_VERSION,
        "request": _validate_request(observation["request"], operation, surface),
        "runner": runner,
        "surface": surface,
    }


def _validate_source_context(
    value: Any, observation: Mapping[str, Any]
) -> dict[str, Any]:
    context = _require_object(value, "source_context")
    _exact_keys(
        context,
        ("case_id", "case_identity", "comparison_corpus_version", "corpus"),
        "source_context",
    )
    case_id = _require_nonempty_string(context["case_id"], "source_context.case_id")
    case_identity = _require_fingerprint(
        context["case_identity"], "source_context.case_identity"
    )
    comparison_corpus_version = context["comparison_corpus_version"]
    if comparison_corpus_version is not None:
        _require_nonempty_string(
            comparison_corpus_version,
            "source_context.comparison_corpus_version",
        )
    corpus = _require_object(context["corpus"], "source_context.corpus")
    _exact_keys(
        corpus, ("algorithm", "fingerprint", "version"), "source_context.corpus"
    )
    if corpus["algorithm"] != "sha256":
        raise ComparisonContractError(
            "source_context.corpus.algorithm must be 'sha256'"
        )
    _require_fingerprint(corpus["fingerprint"], "source_context.corpus.fingerprint")
    corpus_version = _require_nonempty_string(
        corpus["version"], "source_context.corpus.version"
    )
    expected_case_identity = canonical_fingerprint(
        {
            "case_id": case_id,
            "corpus_version": corpus_version,
            "request": observation["request"]["value"],
        }
    )
    if case_identity != expected_case_identity:
        raise ComparisonContractError("source case identity does not match observation")
    return {
        "case_id": case_id,
        "case_identity": case_identity,
        "comparison_corpus_version": comparison_corpus_version,
        "corpus": reference.canonicalize(corpus),
    }


def _comparison_case_identity(
    observation: Mapping[str, Any], context: Mapping[str, Any]
) -> str | None:
    version = context["comparison_corpus_version"]
    if version is None:
        return None
    request = observation["request"]["value"]
    return canonical_fingerprint(
        {
            "cross_corpus_version": version,
            "semantics": {
                "case_id": context["case_id"],
                "input": request["input"],
                "operation": observation["operation"],
                "options": request["options"],
            },
        }
    )


def _validate_rule_ids(rule_ids: Sequence[str]) -> tuple[str, ...]:
    if isinstance(rule_ids, (str, bytes)):
        raise ComparisonContractError("normalization_rule_ids must be an array")
    values = tuple(rule_ids)
    if any(not isinstance(rule_id, str) for rule_id in values):
        raise ComparisonContractError("normalization rule identities must be strings")
    if len(values) != len(set(values)):
        raise ComparisonContractError("normalization rules must not repeat")
    unknown = [rule_id for rule_id in values if rule_id not in NORMALIZATION_RULE_IDS]
    if unknown:
        raise ComparisonContractError(f"unknown normalization rule '{unknown[0]}'")
    order = {rule_id: index for index, rule_id in enumerate(NORMALIZATION_RULE_IDS)}
    if list(values) != sorted(values, key=order.__getitem__):
        raise ComparisonContractError("normalization rules are out of contract order")
    return values


def _normalize_observation(
    observation: Mapping[str, Any], rule_ids: Sequence[str]
) -> dict[str, Any]:
    projected = copy.deepcopy(dict(observation))
    for rule_id in rule_ids:
        if rule_id == "select-semantic-outcome@1.0.0":
            projected = {"outcome": copy.deepcopy(observation["outcome"])}
        else:  # pragma: no cover - guarded by _validate_rule_ids
            raise ComparisonContractError(f"unknown normalization rule '{rule_id}'")
    return reference.canonicalize(projected)


def project_observation(
    raw_observation: Any,
    source_context: Any,
    *,
    normalization_rule_ids: Sequence[str] = NORMALIZATION_RULE_IDS,
) -> dict[str, Any]:
    """Derive one canonical projection while preserving the raw input."""

    try:
        before = reference.canonical_json(raw_observation)
    except TypeError as error:
        raise ComparisonContractError(str(error)) from error
    validated = validate_observation(copy.deepcopy(raw_observation))
    context = _validate_source_context(copy.deepcopy(source_context), validated)
    rule_ids = _validate_rule_ids(normalization_rule_ids)
    semantic_observation = _normalize_observation(validated, rule_ids)
    if rule_ids and semantic_observation.get("outcome") != validated["outcome"]:
        raise ComparisonContractError("normalization changed or hid the source outcome")

    projection = {
        "kind": PROJECTION_KIND,
        "normalization_rule_ids": list(rule_ids),
        "normalization_rules_version": NORMALIZATION_RULES_VERSION,
        "projection_schema_version": PROJECTION_SCHEMA_VERSION,
        "semantic_observation": semantic_observation,
        "source": {
            "case": {
                "comparison_identity": _comparison_case_identity(validated, context),
                "id": context["case_id"],
                "source_identity": context["case_identity"],
            },
            "corpus": context["corpus"],
            "implementation": copy.deepcopy(validated["implementation"]),
            "observation_identity": canonical_fingerprint(validated),
            "observation_schema_version": validated["observation_schema_version"],
            "operation": validated["operation"],
            "protocol_version": validated["protocol_version"],
            "request": copy.deepcopy(validated["request"]),
            "runner": copy.deepcopy(validated["runner"]),
            "surface": validated["surface"],
        },
    }
    projection["projection_fingerprint"] = canonical_fingerprint(projection)
    after = reference.canonical_json(raw_observation)
    if after != before:
        raise ComparisonContractError("projection mutated the raw observation")
    return reference.canonicalize(projection)


def validate_projection(
    projection: Any,
    source_observation: Any,
    source_context: Any,
) -> dict[str, Any]:
    """Rebuild a projection and reject source/projection identity mismatches."""

    value = _require_object(projection, "projection")
    rule_ids = value.get("normalization_rule_ids")
    if not isinstance(rule_ids, list):
        raise ComparisonContractError(
            "projection.normalization_rule_ids must be an array"
        )
    expected = project_observation(
        source_observation,
        source_context,
        normalization_rule_ids=rule_ids,
    )
    try:
        actual_line = canonical_line(value)
    except TypeError as error:
        raise ComparisonContractError(str(error)) from error
    if actual_line != canonical_line(expected):
        raise ComparisonContractError(
            "projection does not match its source observation"
        )
    return expected
