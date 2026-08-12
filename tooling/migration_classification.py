#!/usr/bin/env python3
"""Governed migration dispositions over immutable comparison evidence."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from tooling import migration_comparison as projection_contract
from tooling import migration_comparison_engine as comparison_engine
from tooling.legacy_reference import python_reference as reference

CLASSIFICATION_KIND = projection_contract.CONTRACT["taxonomy_kind"]
TAXONOMY_VERSION = projection_contract.TAXONOMY_VERSION
DISPOSITIONS = tuple(
    entry["id"] for entry in projection_contract.CONTRACT["dispositions"]
)
AUTHORITY_KINDS = {
    "canonical_contract",
    "normative_specification",
    "ratified_architecture",
    "replacement_evidence",
    "supported_scope_contract",
}
CORRECTION_AUTHORITIES = {
    "canonical_contract",
    "normative_specification",
    "ratified_architecture",
}
UNSUPPORTED_AUTHORITIES = {
    "canonical_contract",
    "normative_specification",
    "ratified_architecture",
    "supported_scope_contract",
}
EVIDENCE_SCOPES = {
    "certification_fixture",
    "historical_evidence_only",
    "migration_review",
}
ROLES = {"historical", "replacement"}


class ClassificationError(projection_contract.ComparisonContractError):
    """A requested disposition lacks valid evidence or governing authority."""


def _validate_presence(value: Any, location: str) -> dict[str, Any]:
    presence = projection_contract._require_object(value, location)
    present = presence.get("present")
    if not isinstance(present, bool):
        raise ClassificationError(f"{location}.present must be a boolean")
    expected = ("present", "value") if present else ("present",)
    projection_contract._exact_keys(presence, expected, location)
    try:
        return reference.canonicalize(presence)
    except TypeError as error:
        raise ClassificationError(str(error)) from error


def _validate_difference(value: Any, index: int) -> dict[str, Any]:
    location = f"comparison.differences/{index}"
    difference = projection_contract._require_object(value, location)
    projection_contract._exact_keys(
        difference,
        ("kind", "left", "path", "right"),
        location,
    )
    if difference["kind"] not in projection_contract.CONTRACT["difference_kinds"]:
        raise ClassificationError(f"{location}.kind is invalid")
    path = difference["path"]
    if not isinstance(path, str) or not path.startswith("/"):
        raise ClassificationError(f"{location}.path must be a JSON Pointer")
    left = _validate_presence(difference["left"], f"{location}.left")
    right = _validate_presence(difference["right"], f"{location}.right")
    if difference["kind"] == "left_missing" and (
        left["present"] or not right["present"]
    ):
        raise ClassificationError(f"{location} has inconsistent left presence")
    if difference["kind"] == "right_missing" and (
        not left["present"] or right["present"]
    ):
        raise ClassificationError(f"{location} has inconsistent right presence")
    if difference["kind"] in ("value_mismatch", "type_mismatch") and not (
        left["present"] and right["present"]
    ):
        raise ClassificationError(f"{location} requires both values")
    return {
        "kind": difference["kind"],
        "left": left,
        "path": path,
        "right": right,
    }


def _validate_side(value: Any, location: str) -> dict[str, Any] | None:
    if value is None:
        return None
    side = projection_contract._require_object(value, location)
    projection_contract._exact_keys(
        side,
        ("normalization_rule_ids", "projection_fingerprint", "source"),
        location,
    )
    rules = side["normalization_rule_ids"]
    if not isinstance(rules, list):
        raise ClassificationError(f"{location}.normalization_rule_ids must be an array")
    projection_contract._validate_rule_ids(rules)
    projection_contract._require_fingerprint(
        side["projection_fingerprint"], f"{location}.projection_fingerprint"
    )
    source = projection_contract._require_object(side["source"], f"{location}.source")
    for field in ("case", "operation", "runner", "surface"):
        if field not in source:
            raise ClassificationError(f"{location}.source.{field} is required")
    return reference.canonicalize(side)


def validate_comparison_result(value: Any) -> dict[str, Any]:
    """Validate comparison structure and its content-addressed identity."""

    comparison = projection_contract._require_object(value, "comparison")
    projection_contract._exact_keys(
        comparison,
        (
            "case_id",
            "case_identity",
            "comparability",
            "comparator_implementation_version",
            "comparison_identity",
            "comparison_schema_version",
            "differences",
            "kind",
            "left",
            "operation",
            "relationship",
            "right",
            "surfaces",
            "taxonomy_version",
        ),
        "comparison",
    )
    if comparison["kind"] != comparison_engine.COMPARISON_KIND:
        raise ClassificationError("comparison kind is incompatible")
    if (
        comparison["comparison_schema_version"]
        != comparison_engine.COMPARISON_SCHEMA_VERSION
    ):
        raise ClassificationError("comparison schema version is incompatible")
    if (
        comparison["comparator_implementation_version"]
        != comparison_engine.COMPARATOR_IMPLEMENTATION_VERSION
    ):
        raise ClassificationError("comparator implementation version is incompatible")
    if comparison["taxonomy_version"] != TAXONOMY_VERSION:
        raise ClassificationError("comparison taxonomy version is incompatible")
    projection_contract._require_nonempty_string(
        comparison["case_id"], "comparison.case_id"
    )
    if comparison["case_identity"] is not None:
        projection_contract._require_fingerprint(
            comparison["case_identity"], "comparison.case_identity"
        )
    projection_contract._require_nonempty_string(
        comparison["operation"], "comparison.operation"
    )
    left = _validate_side(comparison["left"], "comparison.left")
    right = _validate_side(comparison["right"], "comparison.right")
    if left is None and right is None:
        raise ClassificationError("comparison must retain at least one side")

    comparability = projection_contract._require_object(
        comparison["comparability"], "comparison.comparability"
    )
    projection_contract._exact_keys(
        comparability,
        ("reason", "state"),
        "comparison.comparability",
    )
    if (
        comparability["state"]
        not in projection_contract.CONTRACT["comparability"]["states"]
    ):
        raise ClassificationError("comparison comparability state is invalid")
    if comparability["state"] == "comparable":
        if comparability["reason"] is not None:
            raise ClassificationError("a comparable result cannot have a reason")
    elif (
        comparability["reason"]
        not in projection_contract.CONTRACT["comparability"]["not_comparable_reasons"]
    ):
        raise ClassificationError("not-comparable result reason is invalid")

    relationship = comparison["relationship"]
    if relationship not in projection_contract.CONTRACT["comparison_relationships"]:
        raise ClassificationError("comparison relationship is invalid")
    if (comparability["state"] == "not_comparable") != (
        relationship == "not_comparable"
    ):
        raise ClassificationError("relationship and comparability are inconsistent")
    raw_differences = comparison["differences"]
    if not isinstance(raw_differences, list):
        raise ClassificationError("comparison.differences must be an array")
    differences = [
        _validate_difference(difference, index)
        for index, difference in enumerate(raw_differences)
    ]
    paths = [difference["path"] for difference in differences]
    if len(paths) != len(set(paths)):
        raise ClassificationError("comparison difference paths must be unique")
    if relationship == "differing_observation" and not differences:
        raise ClassificationError("a differing comparison requires field differences")
    if relationship != "differing_observation" and differences:
        raise ClassificationError("only a differing comparison may carry differences")

    surfaces = projection_contract._require_object(
        comparison["surfaces"], "comparison.surfaces"
    )
    projection_contract._exact_keys(surfaces, ("left", "right"), "comparison.surfaces")
    for side_name, side in (("left", left), ("right", right)):
        surface = surfaces[side_name]
        if side is None:
            if surface is not None:
                raise ClassificationError(
                    f"missing {side_name} side must have null surface"
                )
        elif surface != side["source"]["surface"]:
            raise ClassificationError(
                f"comparison {side_name} surface does not match source"
            )

    projection_contract._require_fingerprint(
        comparison["comparison_identity"], "comparison.comparison_identity"
    )
    identity_body = {
        key: copy.deepcopy(comparison[key])
        for key in comparison
        if key != "comparison_identity"
    }
    expected_identity = projection_contract.canonical_fingerprint(identity_body)
    if comparison["comparison_identity"] != expected_identity:
        raise ClassificationError("comparison identity does not match its evidence")
    return reference.canonicalize(
        {
            **identity_body,
            "comparison_identity": expected_identity,
            "differences": differences,
            "left": left,
            "right": right,
        }
    )


def _validate_authority(value: Any, index: int) -> dict[str, Any]:
    location = f"rationale.authority/{index}"
    authority = projection_contract._require_object(value, location)
    projection_contract._exact_keys(
        authority,
        ("evidence_identity", "kind", "reference"),
        location,
    )
    if authority["kind"] not in AUTHORITY_KINDS:
        raise ClassificationError(f"{location}.kind is invalid")
    projection_contract._require_nonempty_string(
        authority["reference"], f"{location}.reference"
    )
    projection_contract._require_fingerprint(
        authority["evidence_identity"], f"{location}.evidence_identity"
    )
    return reference.canonicalize(authority)


def _string_array(value: Any, location: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ClassificationError(f"{location} must be an array of strings")
    if nonempty and not value:
        raise ClassificationError(f"{location} must not be empty")
    if len(value) != len(set(value)):
        raise ClassificationError(f"{location} must not contain duplicates")
    return list(value)


def _validate_rationale(value: Any, comparison: Mapping[str, Any]) -> dict[str, Any]:
    rationale = projection_contract._require_object(value, "rationale")
    projection_contract._exact_keys(
        rationale,
        projection_contract.CONTRACT["rationale_fields"],
        "rationale",
    )
    if rationale["comparison_identity"] != comparison["comparison_identity"]:
        raise ClassificationError("rationale comparison identity does not match")
    if rationale["affected_operation"] != comparison["operation"]:
        raise ClassificationError("rationale affected operation does not match")
    surfaces = _string_array(
        rationale["affected_surfaces"], "rationale.affected_surfaces", nonempty=True
    )
    expected_surfaces = sorted(
        surface for surface in comparison["surfaces"].values() if surface is not None
    )
    if surfaces != expected_surfaces:
        raise ClassificationError("rationale affected surfaces do not match")
    difference_paths = _string_array(
        rationale["difference_paths"], "rationale.difference_paths"
    )
    expected_paths = [difference["path"] for difference in comparison["differences"]]
    if difference_paths != expected_paths:
        raise ClassificationError("rationale difference paths do not match")
    raw_authority = rationale["authority"]
    if not isinstance(raw_authority, list):
        raise ClassificationError("rationale.authority must be an array")
    authority = [
        _validate_authority(entry, index) for index, entry in enumerate(raw_authority)
    ]
    evidence_identities = _string_array(
        rationale["evidence_identities"],
        "rationale.evidence_identities",
        nonempty=True,
    )
    for index, identity in enumerate(evidence_identities):
        projection_contract._require_fingerprint(
            identity, f"rationale.evidence_identities/{index}"
        )
    explanation = projection_contract._require_nonempty_string(
        rationale["explanation"], "rationale.explanation"
    )
    limitations = _string_array(rationale["limitations"], "rationale.limitations")
    unresolved = _string_array(
        rationale["unresolved_questions"], "rationale.unresolved_questions"
    )
    return {
        "affected_operation": comparison["operation"],
        "affected_surfaces": surfaces,
        "authority": authority,
        "comparison_identity": comparison["comparison_identity"],
        "difference_paths": difference_paths,
        "evidence_identities": evidence_identities,
        "explanation": explanation,
        "limitations": limitations,
        "unresolved_questions": unresolved,
    }


def _validate_roles(value: Any, comparison: Mapping[str, Any]) -> dict[str, str]:
    roles = projection_contract._require_object(value, "roles")
    projection_contract._exact_keys(roles, ("left", "right"), "roles")
    for side in ("left", "right"):
        if roles[side] not in ROLES:
            raise ClassificationError(f"roles.{side} is invalid")
        if comparison[side] is None and roles[side] == "historical":
            raise ClassificationError(f"missing {side} evidence cannot be historical")
    return {"left": roles["left"], "right": roles["right"]}


def _authority_kinds(rationale: Mapping[str, Any]) -> set[str]:
    return {entry["kind"] for entry in rationale["authority"]}


def _require_optional_text(value: Any, location: str) -> str | None:
    if value is None:
        return None
    return projection_contract._require_nonempty_string(value, location)


def _validate_disposition(
    disposition: str,
    comparison: Mapping[str, Any],
    roles: Mapping[str, str],
    rationale: Mapping[str, Any],
    *,
    evidence_scope: str,
    preservation_scope: str | None,
    corrected_rule: str | None,
    scope_boundary: str | None,
    exceptional_justification: str | None,
) -> None:
    relationship = comparison["relationship"]
    kinds = _authority_kinds(rationale)
    replacement_present = "replacement" in roles.values()
    historical_present = any(
        roles[side] == "historical" and comparison[side] is not None
        for side in ("left", "right")
    )

    if evidence_scope == "historical_evidence_only":
        raise ClassificationError(
            "historical-evidence-only comparisons cannot receive a disposition"
        )
    if not replacement_present and disposition != "unresolved_discrepancy":
        raise ClassificationError(
            "a substantive accepted disposition requires replacement evidence"
        )
    if evidence_scope == "migration_review" and replacement_present:
        replacement_sides = [
            side for side in ("left", "right") if roles[side] == "replacement"
        ]
        if any(
            comparison[side] is not None
            and comparison[side]["source"]["runner"]["kind"]
            == "strling.legacy-reference-runner"
            for side in replacement_sides
        ):
            raise ClassificationError(
                "no canonical replacement observation adapter is registered"
            )

    if disposition == "preserved_behavior":
        if relationship != "equivalent_observation":
            raise ClassificationError(
                "preserved behavior requires equivalent observations"
            )
        if preservation_scope is None:
            raise ClassificationError("preserved behavior requires preservation_scope")
        if "replacement_evidence" not in kinds:
            raise ClassificationError(
                "preserved behavior requires replacement evidence"
            )
    elif disposition == "intentional_specification_correction":
        if (
            relationship == "equivalent_observation"
            and exceptional_justification is None
        ):
            raise ClassificationError(
                "equivalent observations require exceptional correction justification"
            )
        if relationship not in ("differing_observation", "equivalent_observation"):
            raise ClassificationError("a correction requires a comparable observation")
        if corrected_rule is None:
            raise ClassificationError("a correction requires corrected_rule")
        if not kinds.intersection(CORRECTION_AUTHORITIES):
            raise ClassificationError("a correction requires governing authority")
    elif disposition == "unsupported_legacy_behavior":
        if not historical_present:
            raise ClassificationError(
                "unsupported legacy behavior requires historical evidence"
            )
        if scope_boundary is None:
            raise ClassificationError(
                "unsupported legacy behavior requires scope_boundary"
            )
        if not kinds.intersection(UNSUPPORTED_AUTHORITIES):
            raise ClassificationError(
                "unsupported legacy behavior requires scope authority"
            )
    elif disposition == "unresolved_discrepancy":
        if relationship == "equivalent_observation":
            raise ClassificationError(
                "equivalent observations are not an unresolved discrepancy"
            )
    else:
        raise ClassificationError(f"invalid disposition '{disposition}'")


def classify_comparison(
    raw_comparison: Any,
    *,
    evidence_scope: str,
    roles: Mapping[str, str],
    rationale: Any,
    requested_disposition: str | None = None,
    preservation_scope: str | None = None,
    corrected_rule: str | None = None,
    scope_boundary: str | None = None,
    exceptional_justification: str | None = None,
    supersedes: Sequence[str] = (),
) -> dict[str, Any]:
    """Interpret factual comparison evidence under explicit authority."""

    before = reference.canonical_json(raw_comparison)
    comparison = validate_comparison_result(copy.deepcopy(raw_comparison))
    if evidence_scope not in EVIDENCE_SCOPES:
        raise ClassificationError(f"invalid evidence_scope '{evidence_scope}'")
    validated_roles = _validate_roles(roles, comparison)
    validated_rationale = _validate_rationale(rationale, comparison)
    preservation_scope = _require_optional_text(
        preservation_scope, "preservation_scope"
    )
    corrected_rule = _require_optional_text(corrected_rule, "corrected_rule")
    scope_boundary = _require_optional_text(scope_boundary, "scope_boundary")
    exceptional_justification = _require_optional_text(
        exceptional_justification, "exceptional_justification"
    )
    if isinstance(supersedes, (str, bytes)):
        raise ClassificationError("supersedes must be an array")
    superseded = list(supersedes)
    if len(superseded) != len(set(superseded)):
        raise ClassificationError("supersedes must not repeat identities")
    for index, identity in enumerate(superseded):
        projection_contract._require_fingerprint(identity, f"supersedes/{index}")

    peer_only = all(role == "historical" for role in validated_roles.values())
    if evidence_scope == "historical_evidence_only":
        if requested_disposition is not None:
            raise ClassificationError(
                "historical peer evidence cannot request a migration disposition"
            )
        applicability = "not_applicable"
        disposition = None
    else:
        if requested_disposition is None:
            if comparison["relationship"] == "equivalent_observation" and peer_only:
                applicability = "not_applicable"
                disposition = None
            else:
                applicability = "classified"
                disposition = "unresolved_discrepancy"
        else:
            if requested_disposition not in DISPOSITIONS:
                raise ClassificationError(
                    f"invalid disposition '{requested_disposition}'"
                )
            applicability = "classified"
            disposition = requested_disposition
        if disposition is not None:
            _validate_disposition(
                disposition,
                comparison,
                validated_roles,
                validated_rationale,
                evidence_scope=evidence_scope,
                preservation_scope=preservation_scope,
                corrected_rule=corrected_rule,
                scope_boundary=scope_boundary,
                exceptional_justification=exceptional_justification,
            )

    classification = {
        "applicability": applicability,
        "comparison_identity": comparison["comparison_identity"],
        "corrected_rule": corrected_rule,
        "disposition": disposition,
        "evidence_scope": evidence_scope,
        "exceptional_justification": exceptional_justification,
        "kind": CLASSIFICATION_KIND,
        "preservation_scope": preservation_scope,
        "rationale": validated_rationale,
        "roles": validated_roles,
        "scope_boundary": scope_boundary,
        "supersedes": superseded,
        "taxonomy_version": TAXONOMY_VERSION,
    }
    classification["classification_identity"] = (
        projection_contract.canonical_fingerprint(classification)
    )
    if reference.canonical_json(raw_comparison) != before:
        raise ClassificationError("classification mutated comparison evidence")
    return reference.canonicalize(classification)
