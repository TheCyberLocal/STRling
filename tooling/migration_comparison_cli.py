#!/usr/bin/env python3
"""Machine-readable entry points for migration comparison evidence."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tooling import migration_classification as classification
from tooling import migration_comparison as projection_contract
from tooling import migration_comparison_certification as certification
from tooling import migration_comparison_engine as comparison_engine
from tooling.legacy_reference import python_reference as reference

MODES = ("project", "compare", "classify", "certify")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Derive governed STRling migration comparison evidence."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)
    for mode in MODES[:-1]:
        command = subparsers.add_parser(mode)
        command.add_argument("--request", required=True, type=Path)
    certify = subparsers.add_parser("certify")
    certify.add_argument("--repeat-runs", default=3, type=int)
    return parser.parse_args(argv)


def _load_request(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise projection_contract.ComparisonContractError(
            "comparison CLI request is unavailable or malformed"
        ) from error
    return dict(projection_contract._require_object(value, "request"))


def _exact_request_keys(
    request: Mapping[str, Any], required: Sequence[str], optional: Sequence[str] = ()
) -> None:
    actual = set(request)
    required_set = set(required)
    allowed = required_set | set(optional)
    if not required_set.issubset(actual) or not actual.issubset(allowed):
        expected = ", ".join(sorted(required_set))
        if optional:
            expected += "; optional: " + ", ".join(sorted(optional))
        raise projection_contract.ComparisonContractError(
            f"request keys must be exactly: {expected}"
        )


def execute_request(mode: str, request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute one validated non-certification CLI request."""

    if mode == "project":
        _exact_request_keys(
            request,
            ("raw_observation", "source_context"),
            ("normalization_rule_ids",),
        )
        rule_ids = request.get(
            "normalization_rule_ids", projection_contract.NORMALIZATION_RULE_IDS
        )
        if not isinstance(rule_ids, list | tuple):
            raise projection_contract.ComparisonContractError(
                "normalization_rule_ids must be an array"
            )
        return projection_contract.project_observation(
            request["raw_observation"],
            request["source_context"],
            normalization_rule_ids=rule_ids,
        )
    if mode == "compare":
        _exact_request_keys(request, ("left", "right"))
        return comparison_engine.compare_projections(request["left"], request["right"])
    if mode == "classify":
        _exact_request_keys(
            request,
            ("comparison", "evidence_scope", "rationale", "roles"),
            (
                "corrected_rule",
                "exceptional_justification",
                "preservation_scope",
                "requested_disposition",
                "scope_boundary",
                "supersedes",
            ),
        )
        return classification.classify_comparison(
            request["comparison"],
            evidence_scope=request["evidence_scope"],
            roles=request["roles"],
            rationale=request["rationale"],
            requested_disposition=request.get("requested_disposition"),
            preservation_scope=request.get("preservation_scope"),
            corrected_rule=request.get("corrected_rule"),
            scope_boundary=request.get("scope_boundary"),
            exceptional_justification=request.get("exceptional_justification"),
            supersedes=request.get("supersedes", ()),
        )
    raise projection_contract.ComparisonContractError(f"unknown mode '{mode}'")


def _failure(error: Exception) -> str:
    return reference.canonical_line(
        {
            "error": {
                "code": "INVALID_MIGRATION_COMPARISON_REQUEST",
                "message": str(error),
            },
            "status": "failed",
        }
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.mode == "certify":
            result = certification.certify_fixture_corpus(repeat_runs=args.repeat_runs)
        else:
            result = execute_request(args.mode, _load_request(args.request))
    except (projection_contract.ComparisonContractError, TypeError) as error:
        sys.stderr.write(_failure(error))
        return 2
    sys.stdout.write(reference.canonical_line(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
