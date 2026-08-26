#!/usr/bin/env python3
"""Certify the joined migration and explanation evidence without adding semantics."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from tooling.contract_validation import load_json
from tooling.explanation_contract import (
    ExplanationContractError,
    ExplanationContractSuite,
)
from tooling.frontend_convergence import FrontendConvergenceSuite
from tooling.no_match_explanation_contract import (
    NoMatchExplanationContractError,
    NoMatchExplanationContractSuite,
)
from tooling.semantic_conversion_contract import (
    SemanticConversionContractError,
    SemanticConversionContractSuite,
)
from tooling.shared_cross_engine_corpus import (
    EXPECTED_PROFILE_IDS,
    validate_corpus,
    verify_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
CERTIFICATION_ROOT = ROOT / "tests" / "certification" / "migration-explanation" / "1.0"
SCHEMA_PATH = CERTIFICATION_ROOT / "certification.schema.json"
MANIFEST_PATH = CERTIFICATION_ROOT / "manifest.json"
RUST_PROOF_PATH = ROOT / "core" / "tests" / "migration_explanation_certification.rs"
OPERATION_ID = "certification.migration-explanation"
CHECK_ID = f"{OPERATION_ID}.closed-denominator"
EXIT_CODES = {"passed": 0, "failed": 1}

DENOMINATOR_IDS = (
    "frontend_convergence",
    "semantic_explanation",
    "semantic_conversion",
    "bounded_no_match",
    "shared_target_corpus",
    "shared_target_evidence",
    "migration_differential",
)
MUTATION_CATEGORIES = (
    "capture_relationship",
    "branch_order",
    "repetition",
    "semantic_options",
    "source_authority",
    "explanation_evidence",
    "conversion_disposition",
    "authority_evidence",
)
RUST_MUTATION_IDS = (
    "mutation/capture-relationship",
    "mutation/branch-order",
    "mutation/repetition-bound",
    "mutation/case-option",
)
REQUIRED_ROUND_TRIP_COVERAGE = {
    "anchors",
    "assertion_polarity",
    "backreferences",
    "captures",
    "case_matching",
    "character_classes",
    "lookahead",
    "lookbehind",
    "repetition_bounds",
    "unicode",
    "wildcard",
}


class MigrationExplanationCertificationError(ValueError):
    """The non-normative joined certification evidence is malformed or stale."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def manifest_fingerprint(manifest: Mapping[str, Any]) -> str:
    unsigned = copy.deepcopy(dict(manifest))
    anti_shrinkage = unsigned.get("anti_shrinkage")
    if not isinstance(anti_shrinkage, dict):
        raise MigrationExplanationCertificationError(
            "manifest anti-shrinkage block must be an object"
        )
    anti_shrinkage.pop("manifest_sha256", None)
    return "sha256:" + hashlib.sha256(canonical_bytes(unsigned)).hexdigest()


def sign_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deep copy with its manifest fingerprint recomputed."""

    signed = copy.deepcopy(dict(manifest))
    anti_shrinkage = signed.get("anti_shrinkage")
    if not isinstance(anti_shrinkage, dict):
        raise MigrationExplanationCertificationError(
            "manifest anti-shrinkage block must be an object"
        )
    anti_shrinkage["manifest_sha256"] = manifest_fingerprint(signed)
    return signed


def _require_repository_file(root: Path, path_value: str) -> Path:
    relative = PurePosixPath(path_value)
    if relative.is_absolute() or ".." in relative.parts:
        raise MigrationExplanationCertificationError(
            f"evidence path escapes the repository: {path_value}"
        )
    path = root.joinpath(*relative.parts)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise MigrationExplanationCertificationError(
            f"evidence path escapes the repository: {path_value}"
        ) from error
    if not path.is_file():
        raise MigrationExplanationCertificationError(
            f"required evidence file is missing: {path_value}"
        )
    return path


def _validate_schema(manifest: Mapping[str, Any], root: Path) -> None:
    schema = load_json(root / SCHEMA_PATH.relative_to(ROOT))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            manifest
        ),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        raise MigrationExplanationCertificationError(
            f"manifest {location}: {error.message}"
        )


def _validate_paths(manifest: Mapping[str, Any], root: Path) -> int:
    paths = set(manifest["authority"]["semantic_authorities"])
    paths.update(entry["source"] for entry in manifest["denominators"])
    paths.update(
        entry["path"] for entry in manifest["corpora"]["conversion_dispositions"]
    )
    paths.update(
        entry["path"] for entry in manifest["corpora"]["semantic_explanations"]
    )
    paths.add(manifest["target_evidence"]["source"])
    paths.add(manifest["target_evidence"]["evidence"])
    for path in sorted(paths):
        _require_repository_file(root, path)
    return len(paths)


def _prefixed(value: str) -> str:
    return value if value.startswith("sha256:") else f"sha256:{value}"


def _actual_denominators(root: Path) -> dict[str, dict[str, Any]]:
    frontend = FrontendConvergenceSuite(root=root).certify()
    explanation = ExplanationContractSuite(
        root / "spec" / "explanations" / "semantic" / "1.0"
    ).certify()
    conversion = SemanticConversionContractSuite(
        root / "spec" / "conversions" / "semantic" / "1.0"
    ).certify()
    no_match = NoMatchExplanationContractSuite(
        root / "spec" / "explanations" / "no-match" / "1.0"
    ).certify()
    shared = validate_corpus()
    checked = verify_evidence()
    checked_document = load_json(
        root
        / "tests"
        / "conformance"
        / "evidence"
        / "shared-cross-engine-observations.json"
    )
    baseline = load_json(root / "tooling" / "migration_differential_baseline.json")
    historical_observations = sum(entry["case_count"] for entry in baseline["corpora"])
    return {
        "frontend_convergence": frontend,
        "semantic_explanation": explanation,
        "semantic_conversion": conversion,
        "bounded_no_match": no_match,
        "shared_target_corpus": {
            "case_count": shared["case_count"],
            **shared["application_counts"],
            "corpus_sha256": _prefixed(shared["corpus_sha256"]),
            "case_set_sha256": _prefixed(shared["case_set_sha256"]),
            "vector_set_sha256": _prefixed(shared["vector_set_sha256"]),
        },
        "shared_target_evidence": {
            "case_count": checked["case_count"],
            "observation_count": len(checked_document["observations"]),
            "result_sha256": _prefixed(checked["result_sha256"]),
        },
        "migration_differential": {
            "baseline_schema_version": baseline["baseline_schema_version"],
            "baseline_fingerprint": baseline["baseline_fingerprint"],
            "canonical_boundary_fingerprint": baseline[
                "canonical_boundary_fingerprint"
            ],
            "full_corpus_fingerprint": baseline["full_corpus_fingerprint"],
            "replacement_reviews": len(baseline["replacement_reviews"]),
            "historical_observations": historical_observations,
        },
    }


def refresh_denominator_identities(
    manifest: Mapping[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    """Renew only identities owned by the joined denominator validators."""

    refreshed = copy.deepcopy(dict(manifest))
    actual = _actual_denominators(root)
    for entry in refreshed["denominators"]:
        entry["expected"] = actual[entry["id"]]
    refreshed = sign_manifest(refreshed)
    _validate_schema(refreshed, root)
    _validate_anti_shrinkage(refreshed)
    _validate_denominators(refreshed, root)
    return refreshed


def _write_manifest(manifest: Mapping[str, Any], *, root: Path = ROOT) -> None:
    path = root / MANIFEST_PATH.relative_to(ROOT)
    governed_root = (
        root / "tests" / "certification" / "migration-explanation" / "1.0"
    ).resolve()
    if path.resolve().parent != governed_root:
        raise MigrationExplanationCertificationError(
            f"refusing non-governed output: {path}"
        )
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as output:
        json.dump(manifest, output, indent=4, ensure_ascii=False)
        output.write("\n")
        temporary = Path(output.name)
    os.replace(temporary, path)


def _validate_denominators(
    manifest: Mapping[str, Any], root: Path
) -> dict[str, dict[str, Any]]:
    entries = manifest["denominators"]
    ids = tuple(entry["id"] for entry in entries)
    if ids != DENOMINATOR_IDS:
        raise MigrationExplanationCertificationError(
            "denominator identity or order changed"
        )
    actual = _actual_denominators(root)
    for entry in entries:
        denominator_id = entry["id"]
        if entry["expected"] != actual[denominator_id]:
            raise MigrationExplanationCertificationError(
                f"{denominator_id}: expected denominator differs from owning validator"
            )
    return actual


def _validate_evidence_joins(manifest: Mapping[str, Any], root: Path) -> None:
    frontend = load_json(root / "tests" / "convergence" / "frontend-convergence.json")
    legacy_ids = [case["id"] for case in frontend["cases"] if "legacy" in case]
    surface_only_ids = [
        case["id"] for case in frontend["cases"] if "legacy" not in case
    ]
    round_trips = manifest["corpora"]["round_trip_cases"]
    if [case["source_case_id"] for case in round_trips] != legacy_ids:
        raise MigrationExplanationCertificationError(
            "round-trip cases do not equal the legacy convergence denominator"
        )
    if manifest["corpora"]["surface_only_case_ids"] != surface_only_ids:
        raise MigrationExplanationCertificationError(
            "surface-only cases do not equal the non-legacy convergence denominator"
        )
    coverage = {value for case in round_trips for value in case.get("coverage", [])}
    missing_coverage = REQUIRED_ROUND_TRIP_COVERAGE - coverage
    if missing_coverage:
        raise MigrationExplanationCertificationError(
            f"round-trip coverage shrank: {sorted(missing_coverage)}"
        )

    conversion_paths = [
        entry["path"] for entry in manifest["corpora"]["conversion_dispositions"]
    ]
    expected_conversion_paths = [
        "spec/conversions/semantic/1.0/examples/exact-semantic-dsl.json",
        "spec/conversions/semantic/1.0/examples/exact-simply.json",
        "spec/conversions/semantic/1.0/examples/partial-capture-name.json",
        "spec/conversions/semantic/1.0/examples/unsupported-forward-reference.json",
    ]
    if conversion_paths != expected_conversion_paths:
        raise MigrationExplanationCertificationError(
            "conversion disposition fixture denominator changed"
        )
    for entry in manifest["corpora"]["conversion_dispositions"]:
        if load_json(root / entry["path"])["status"] != entry["expected"]:
            raise MigrationExplanationCertificationError(
                f"{entry['id']}: conversion disposition differs"
            )

    explanation_entries = manifest["corpora"]["semantic_explanations"]
    expected_explanation_paths = [
        "spec/explanations/semantic/1.0/examples/source-less-literal.json",
        "spec/explanations/semantic/1.0/invalid/stale-concise-count.json",
        "spec/explanations/semantic/1.0/invalid/ui-specific-field.json",
        "spec/explanations/semantic/1.0/invalid/wrong-model-version.json",
    ]
    if [entry["path"] for entry in explanation_entries] != expected_explanation_paths:
        raise MigrationExplanationCertificationError(
            "semantic explanation fixture denominator changed"
        )

    no_match = load_json(
        root / "spec" / "explanations" / "no-match" / "1.0" / "verification-corpus.json"
    )
    no_match_manifest = manifest["corpora"]["no_match"]
    if no_match_manifest["required_case_ids"] != [
        case["case_id"] for case in no_match["cases"]
    ]:
        raise MigrationExplanationCertificationError(
            "no-match case denominator changed"
        )
    actual_dispositions = Counter(
        case["expected"]["disposition"] for case in no_match["cases"]
    )
    if dict(actual_dispositions) != no_match_manifest["expected_dispositions"]:
        raise MigrationExplanationCertificationError(
            "no-match disposition denominator changed"
        )

    target = load_json(root / "spec" / "conformance" / "shared-corpus-v1.json")
    target_manifest = manifest["target_evidence"]
    target_ids = [vector["case_id"] for vector in target["vectors"]]
    if target_manifest["required_case_ids"] != target_ids:
        raise MigrationExplanationCertificationError(
            "shared target case denominator changed"
        )
    if tuple(target_manifest["profiles"]) != EXPECTED_PROFILE_IDS:
        raise MigrationExplanationCertificationError(
            "shared target profile denominator changed"
        )
    target_id_set = set(target_ids)
    for case in round_trips:
        unknown = set(case["target_evidence_case_ids"]) - target_id_set
        if unknown:
            raise MigrationExplanationCertificationError(
                f"{case['id']}: unregistered target evidence {sorted(unknown)}"
            )


def _validate_pathological_cases(manifest: Mapping[str, Any], root: Path) -> None:
    cases = manifest["pathological_cases"]
    no_match_ids = set(manifest["corpora"]["no_match"]["required_case_ids"])
    limit_case_ids = {
        "subject-scalar-limit",
        "subject-utf8-limit",
        "step-limit",
        "depth-limit",
        "branch-limit",
        "finding-limit",
        "elapsed-limit",
    }
    actual_limits = {
        entry["source_case"]
        for entry in cases
        if entry["owner"] == "bounded_no_match" and entry["source_case"] in no_match_ids
    }
    if actual_limits != limit_case_ids:
        raise MigrationExplanationCertificationError(
            "pathological no-match guard denominator changed"
        )
    for entry in cases:
        source = entry["source_case"]
        if "#" not in source:
            continue
        path_value, anchor = source.split("#", 1)
        text = _require_repository_file(root, path_value).read_text(encoding="utf-8")
        if f"fn {anchor}(" not in text:
            raise MigrationExplanationCertificationError(
                f"{entry['id']}: pathological proof hook is missing"
            )


def _mutation_is_rejected(action: Any, error_type: type[Exception]) -> None:
    try:
        action()
    except error_type:
        return
    raise MigrationExplanationCertificationError(
        f"controlled mutation unexpectedly passed {error_type.__name__}"
    )


def _validate_owner_mutations(manifest: Mapping[str, Any], root: Path) -> int:
    explanation = load_json(
        root
        / "spec"
        / "explanations"
        / "semantic"
        / "1.0"
        / "examples"
        / "source-less-literal.json"
    )
    explanation["nodes"][0]["source"]["derived_from_node_ids"] = ["node:missing"]
    explanation_suite = ExplanationContractSuite(
        root / "spec" / "explanations" / "semantic" / "1.0"
    )
    _mutation_is_rejected(
        lambda: explanation_suite.validate(explanation), ExplanationContractError
    )

    no_match = load_json(
        root
        / "spec"
        / "explanations"
        / "no-match"
        / "1.0"
        / "examples"
        / "unknown-step-limit.json"
    )
    no_match["outcome"] = "no_match"
    no_match["explanation_disposition"] = "proven"
    no_match["findings"][0]["confidence"] = "proven"
    no_match_suite = NoMatchExplanationContractSuite(
        root / "spec" / "explanations" / "no-match" / "1.0"
    )
    _mutation_is_rejected(
        lambda: no_match_suite.validate(no_match), NoMatchExplanationContractError
    )

    conversion = load_json(
        root
        / "spec"
        / "conversions"
        / "semantic"
        / "1.0"
        / "examples"
        / "partial-capture-name.json"
    )
    conversion["status"] = "exact"
    conversion_suite = SemanticConversionContractSuite(
        root / "spec" / "conversions" / "semantic" / "1.0"
    )
    _mutation_is_rejected(
        lambda: conversion_suite.validate(conversion), SemanticConversionContractError
    )

    authority_mutation = copy.deepcopy(dict(manifest))
    authority_mutation["denominators"][0]["expected"]["cases"] -= 1
    authority_mutation = sign_manifest(authority_mutation)
    try:
        _validate_denominators(authority_mutation, root)
    except MigrationExplanationCertificationError:
        pass
    else:
        raise MigrationExplanationCertificationError(
            "controlled authority denominator shrinkage unexpectedly passed"
        )
    return 4


def _validate_mutation_inventory(manifest: Mapping[str, Any], root: Path) -> int:
    mutations = manifest["mutations"]
    categories = tuple(entry["category"] for entry in mutations)
    if categories != MUTATION_CATEGORIES:
        raise MigrationExplanationCertificationError(
            "mutation category identity or order changed"
        )
    rust_source = _require_repository_file(
        root, "core/tests/migration_explanation_certification.rs"
    ).read_text(encoding="utf-8")
    for mutation_id in RUST_MUTATION_IDS:
        if mutation_id not in rust_source:
            raise MigrationExplanationCertificationError(
                f"Rust proof hook is missing for {mutation_id}"
            )
    return _validate_owner_mutations(manifest, root) + len(RUST_MUTATION_IDS)


def _validate_anti_shrinkage(manifest: Mapping[str, Any]) -> None:
    anti = manifest["anti_shrinkage"]
    actual = {
        "round_trip_cases": len(manifest["corpora"]["round_trip_cases"]),
        "round_trip_destination_proofs": sum(
            len(case["destinations"])
            for case in manifest["corpora"]["round_trip_cases"]
        ),
        "surface_only_cases": len(manifest["corpora"]["surface_only_case_ids"]),
        "conversion_cases": len(manifest["corpora"]["conversion_dispositions"]),
        "semantic_explanation_cases": len(manifest["corpora"]["semantic_explanations"]),
        "no_match_cases": len(manifest["corpora"]["no_match"]["required_case_ids"]),
        "target_cases": len(manifest["target_evidence"]["required_case_ids"]),
        "target_observations": manifest["target_evidence"]["observation_count"],
        "pathological_cases": len(manifest["pathological_cases"]),
        "mutation_categories": len(
            {item["category"] for item in manifest["mutations"]}
        ),
    }
    for key, value in actual.items():
        if anti[key] != value:
            raise MigrationExplanationCertificationError(
                f"anti-shrinkage count differs for {key}"
            )
    claimed = anti["manifest_sha256"]
    actual_fingerprint = manifest_fingerprint(manifest)
    if claimed != actual_fingerprint:
        raise MigrationExplanationCertificationError(
            "manifest canonical fingerprint differs"
        )


def certify(
    *, root: Path = ROOT, manifest: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Validate the complete joined evidence denominator and return stable details."""

    value = (
        copy.deepcopy(dict(manifest))
        if manifest is not None
        else load_json(root / MANIFEST_PATH.relative_to(ROOT))
    )
    _validate_schema(value, root)
    if value["authority"] != {
        "classification": "campaign_certification_evidence",
        "normative": False,
        "owner": "P15-T04",
        "semantic_authorities": value["authority"]["semantic_authorities"],
    }:
        raise MigrationExplanationCertificationError(
            "certification evidence cannot claim normative semantic authority"
        )
    path_count = _validate_paths(value, root)
    _validate_anti_shrinkage(value)
    denominators = _validate_denominators(value, root)
    _validate_evidence_joins(value, root)
    _validate_pathological_cases(value, root)
    mutation_count = _validate_mutation_inventory(value, root)
    return {
        "certification_id": value["certification_id"],
        "certification_version": value["certification_version"],
        "manifest_sha256": value["anti_shrinkage"]["manifest_sha256"],
        "denominators": len(denominators),
        "evidence_paths": path_count,
        "round_trip_cases": len(value["corpora"]["round_trip_cases"]),
        "destination_proofs": value["anti_shrinkage"]["round_trip_destination_proofs"],
        "conversion_cases": len(value["corpora"]["conversion_dispositions"]),
        "semantic_explanation_cases": len(value["corpora"]["semantic_explanations"]),
        "no_match_cases": len(value["corpora"]["no_match"]["required_case_ids"]),
        "target_cases": len(value["target_evidence"]["required_case_ids"]),
        "target_observations": value["target_evidence"]["observation_count"],
        "pathological_cases": len(value["pathological_cases"]),
        "mutations_detected": mutation_count,
    }


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": dict(details)}],
    }


def run() -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    try:
        return _result("passed", started, certify()), EXIT_CODES["passed"]
    except Exception as error:
        return (
            _result(
                "failed",
                started,
                {"error_type": type(error).__name__, "reason": str(error)},
            ),
            EXIT_CODES["failed"],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate checked evidence"
    )
    parser.add_argument("--json", action="store_true", help="emit structured JSON")
    parser.add_argument(
        "--refresh-identities",
        action="store_true",
        help="renew validator-owned denominator identities and re-sign the manifest",
    )
    args = parser.parse_args()
    if args.refresh_identities:
        manifest = load_json(MANIFEST_PATH)
        _write_manifest(refresh_denominator_identities(manifest))
    result, code = run()
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        details = result["checks"][0]["details"]
        if result["status"] == "passed":
            print(
                "MIGRATION_EXPLANATION_CERTIFICATION status=passed "
                f"round_trip={details['round_trip_cases']} "
                f"destination_proofs={details['destination_proofs']} "
                f"no_match={details['no_match_cases']} "
                f"target_observations={details['target_observations']} "
                f"mutations={details['mutations_detected']} "
                f"fingerprint={details['manifest_sha256']}"
            )
        else:
            print(
                "MIGRATION_EXPLANATION_CERTIFICATION status=failed "
                f"error={details['reason']}"
            )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
