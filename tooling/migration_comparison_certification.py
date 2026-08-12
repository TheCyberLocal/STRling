#!/usr/bin/env python3
"""Determinism, non-loss, provenance, and taxonomy certification fixtures."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from tooling import migration_classification as classification
from tooling import migration_comparison as projection_contract
from tooling import migration_comparison_engine as comparison_engine
from tooling.legacy_reference import python_reference as reference

CERTIFICATION_SCHEMA_VERSION = "1.0.0"
CERTIFICATION_KIND = "strling.migration-comparison-certification"
CORPUS_KIND = "strling.migration-comparison-certification-corpus"
CORPUS_VERSION = "1.0.0"
DEFAULT_CORPUS_PATH = (
    Path(__file__).with_name("tests")
    / "fixtures"
    / "migration_comparison"
    / "certification.json"
)
EXPECTED_MALFORMED_CASES = (
    "malformed-observation",
    "malformed-comparison-request",
    "mismatched-pairing-identity",
    "projection-source-mismatch",
)
EXPECTED_MUTATION_CASES = (
    "observation-value-change",
    "runner-fingerprint-change",
    "normalization-rule-version-change",
    "deleted-authority-evidence",
    "invalid-disposition",
    "altered-difference-path",
    "unsupported-becoming-success",
    "raw-observation-mutation",
    "unresolved-promoted-to-accepted",
)


class CertificationError(projection_contract.ComparisonContractError):
    """The controlled comparison certification corpus did not pass."""


def load_corpus(path: Path = DEFAULT_CORPUS_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CertificationError(
            "comparison certification corpus is malformed"
        ) from error
    corpus = projection_contract._require_object(value, "certification_corpus")
    projection_contract._exact_keys(
        corpus,
        (
            "cases",
            "classification_cases",
            "description",
            "kind",
            "malformed_cases",
            "mutation_cases",
            "outcomes",
            "version",
        ),
        "certification_corpus",
    )
    if corpus["kind"] != CORPUS_KIND or corpus["version"] != CORPUS_VERSION:
        raise CertificationError(
            "comparison certification corpus version is incompatible"
        )
    projection_contract._require_nonempty_string(
        corpus["description"], "certification_corpus.description"
    )
    if corpus["malformed_cases"] != list(EXPECTED_MALFORMED_CASES):
        raise CertificationError("malformed certification cases do not match contract")
    if corpus["mutation_cases"] != list(EXPECTED_MUTATION_CASES):
        raise CertificationError("mutation certification cases do not match contract")
    if not isinstance(corpus["cases"], list) or not corpus["cases"]:
        raise CertificationError("certification corpus requires comparison cases")
    if not isinstance(corpus["classification_cases"], list):
        raise CertificationError(
            "certification corpus classifications must be an array"
        )
    projection_contract._require_object(
        corpus["outcomes"], "certification_corpus.outcomes"
    )
    return reference.canonicalize(corpus)


def _surface(runner_id: str, operation: str) -> str:
    surface = projection_contract.SURFACE_REGISTRY.get((runner_id, operation))
    if surface is None:
        raise CertificationError(
            f"fixture operation '{operation}' has no '{runner_id}' surface"
        )
    return surface


def _input(operation: str, case_id: str) -> dict[str, str]:
    key = "literal" if operation.startswith("api.simply.") else "source"
    return {key: f"fixture:{case_id}"}


def _observation(
    runner_id: str,
    operation: str,
    case_id: str,
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    surface = _surface(runner_id, operation)
    request_value = {
        "expected_legacy_surface": surface,
        "input": _input(operation, case_id),
        "kind": reference.REQUEST_KIND,
        "operation": operation,
        "options": {},
        "protocol_version": reference.PROTOCOL_VERSION,
    }
    runtime = "python" if runner_id == "python" else "node"
    language = "python" if runner_id == "python" else "typescript"
    return {
        "implementation": {
            "algorithm": "sha256",
            "fingerprint": projection_contract.canonical_fingerprint(
                {"certification_fixture_implementation": runner_id}
            ),
            "inputs": [],
            "kind": f"strling.certification-{runner_id}-implementation",
            "manifest_encoding": "canonical-json-v1",
            "runtime": {"name": runtime, "version": "fixture-1.0.0"},
        },
        "kind": reference.OBSERVATION_KIND,
        "observation_schema_version": reference.OBSERVATION_SCHEMA_VERSION,
        "operation": operation,
        "outcome": copy.deepcopy(dict(outcome)),
        "protocol_version": reference.PROTOCOL_VERSION,
        "request": {
            "algorithm": "sha256",
            "fingerprint": projection_contract.canonical_fingerprint(request_value),
            "value": request_value,
        },
        "runner": {
            "id": runner_id,
            "kind": "strling.legacy-reference-runner",
            "language": language,
            "version": "1.0.0",
        },
        "surface": surface,
    }


def _context(
    observation: Mapping[str, Any], case_id: str, corpus_fingerprint: str
) -> dict[str, Any]:
    corpus = {
        "algorithm": "sha256",
        "fingerprint": corpus_fingerprint,
        "version": CORPUS_VERSION,
    }
    return {
        "case_id": case_id,
        "case_identity": projection_contract.canonical_fingerprint(
            {
                "case_id": case_id,
                "corpus_version": CORPUS_VERSION,
                "request": observation["request"]["value"],
            }
        ),
        "comparison_corpus_version": CORPUS_VERSION,
        "corpus": corpus,
    }


def _project_case(
    case: Mapping[str, Any],
    outcomes: Mapping[str, Any],
    corpus_fingerprint: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    projections = []
    for side in ("left", "right"):
        runner_id = case[f"{side}_runner"]
        outcome_id = case[f"{side}_outcome"]
        if runner_id is None:
            if outcome_id is not None:
                raise CertificationError(f"{case['id']} missing side has an outcome")
            projections.append(None)
            continue
        if outcome_id not in outcomes:
            raise CertificationError(f"{case['id']} references unknown outcome")
        observation = _observation(
            runner_id,
            case["operation"],
            case["id"],
            outcomes[outcome_id],
        )
        projections.append(
            projection_contract.project_observation(
                observation,
                _context(observation, case["id"], corpus_fingerprint),
            )
        )
    comparison = comparison_engine.compare_projections(*projections)
    if comparison["relationship"] != case["expected_relationship"]:
        raise CertificationError(f"{case['id']} relationship did not match")
    if comparison["comparability"]["reason"] != case["expected_reason"]:
        raise CertificationError(f"{case['id']} comparability reason did not match")
    return [item for item in projections if item is not None], comparison


def _authority(kind: str, reference_value: str) -> dict[str, str]:
    return {
        "evidence_identity": projection_contract.canonical_fingerprint(
            {"certification_authority": reference_value}
        ),
        "kind": kind,
        "reference": reference_value,
    }


def _rationale(
    comparison: Mapping[str, Any], authority: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    return {
        "affected_operation": comparison["operation"],
        "affected_surfaces": sorted(
            surface
            for surface in comparison["surfaces"].values()
            if surface is not None
        ),
        "authority": authority or [],
        "comparison_identity": comparison["comparison_identity"],
        "difference_paths": [
            difference["path"] for difference in comparison["differences"]
        ],
        "evidence_identities": [
            comparison["comparison_identity"],
            projection_contract.canonical_fingerprint(
                {"certification_evidence": comparison["case_id"]}
            ),
        ],
        "explanation": "Controlled certification rationale; not a product decision.",
        "limitations": ["Certification-fixture evidence only."],
        "unresolved_questions": [],
    }


def _classify_fixture(
    fixture: Mapping[str, Any], comparison: Mapping[str, Any]
) -> dict[str, Any]:
    disposition = fixture["disposition"]
    kwargs: dict[str, Any] = {
        "evidence_scope": "certification_fixture",
        "rationale": _rationale(comparison),
        "requested_disposition": disposition,
        "roles": {"left": "historical", "right": "replacement"},
    }
    if disposition == "preserved_behavior":
        kwargs["preservation_scope"] = "controlled equivalent outcome fixture"
        kwargs["rationale"] = _rationale(
            comparison,
            [_authority("replacement_evidence", "fixture:replacement-evidence")],
        )
    elif disposition == "intentional_specification_correction":
        kwargs["corrected_rule"] = "controlled certification rule"
        kwargs["rationale"] = _rationale(
            comparison,
            [_authority("canonical_contract", "fixture:canonical-contract-rule")],
        )
    elif disposition == "unsupported_legacy_behavior":
        kwargs["scope_boundary"] = "controlled fixture replacement scope"
        kwargs["rationale"] = _rationale(
            comparison,
            [_authority("supported_scope_contract", "fixture:supported-scope")],
        )
    return classification.classify_comparison(comparison, **kwargs)


def _expect_error(callback: Callable[[], Any], label: str) -> None:
    try:
        callback()
    except projection_contract.ComparisonContractError:
        return
    raise CertificationError(f"controlled invalid case '{label}' was accepted")


def _run_malformed_cases(
    baseline_observation: Mapping[str, Any],
    baseline_projection: Mapping[str, Any],
    baseline_comparison: Mapping[str, Any],
    corpus_fingerprint: str,
) -> int:
    malformed_observation = copy.deepcopy(baseline_observation)
    del malformed_observation["outcome"]["status"]
    _expect_error(
        lambda: projection_contract.project_observation(
            malformed_observation,
            _context(
                malformed_observation, "malformed-observation", corpus_fingerprint
            ),
        ),
        "malformed-observation",
    )
    _expect_error(
        lambda: comparison_engine.compare_projections(None, None),
        "malformed-comparison-request",
    )
    different_observation = _observation(
        "typescript",
        "parser.parse",
        "different-case",
        baseline_observation["outcome"],
    )
    different_projection = projection_contract.project_observation(
        different_observation,
        _context(different_observation, "different-case", corpus_fingerprint),
    )
    _expect_error(
        lambda: comparison_engine.compare_projections(
            baseline_projection, different_projection
        ),
        "mismatched-pairing-identity",
    )
    altered_projection = copy.deepcopy(baseline_projection)
    altered_projection["source"]["observation_identity"] = "sha256:" + "a" * 64
    _expect_error(
        lambda: comparison_engine.compare_projections(
            altered_projection, baseline_projection
        ),
        "projection-source-mismatch",
    )
    if baseline_comparison["comparison_identity"] == "":  # pragma: no cover
        raise CertificationError("baseline comparison identity is empty")
    return len(EXPECTED_MALFORMED_CASES)


def _run_mutations(
    baseline_observation: Mapping[str, Any],
    baseline_projection: Mapping[str, Any],
    differing_comparison: Mapping[str, Any],
    unsupported_comparison: Mapping[str, Any],
    corpus_fingerprint: str,
) -> int:
    detected = 0

    value_changed = copy.deepcopy(baseline_observation)
    value_changed["outcome"]["evidence"]["value"] = "mutated"
    changed_projection = projection_contract.project_observation(
        value_changed,
        _context(value_changed, "equivalent-after-normalization", corpus_fingerprint),
    )
    if (
        changed_projection["projection_fingerprint"]
        != baseline_projection["projection_fingerprint"]
    ):
        detected += 1

    fingerprint_changed = copy.deepcopy(baseline_observation)
    fingerprint_changed["implementation"]["fingerprint"] = "sha256:" + "b" * 64
    runner_projection = projection_contract.project_observation(
        fingerprint_changed,
        _context(
            fingerprint_changed,
            "equivalent-after-normalization",
            corpus_fingerprint,
        ),
    )
    if (
        runner_projection["projection_fingerprint"]
        != baseline_projection["projection_fingerprint"]
    ):
        detected += 1

    normalization_changed = copy.deepcopy(baseline_projection)
    normalization_changed["normalization_rules_version"] = "9.9.9"
    _expect_error(
        lambda: comparison_engine.validate_projection_artifact(normalization_changed),
        "normalization-rule-version-change",
    )
    detected += 1

    _expect_error(
        lambda: classification.classify_comparison(
            differing_comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=_rationale(differing_comparison),
            requested_disposition="intentional_specification_correction",
            corrected_rule="controlled certification rule",
        ),
        "deleted-authority-evidence",
    )
    detected += 1

    _expect_error(
        lambda: classification.classify_comparison(
            differing_comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=_rationale(differing_comparison),
            requested_disposition="accepted_difference",
        ),
        "invalid-disposition",
    )
    detected += 1

    altered_path = copy.deepcopy(differing_comparison)
    altered_path["differences"][0]["path"] = "/altered/path"
    _expect_error(
        lambda: classification.classify_comparison(
            altered_path,
            evidence_scope="historical_evidence_only",
            roles={"left": "historical", "right": "historical"},
            rationale=_rationale(altered_path),
        ),
        "altered-difference-path",
    )
    detected += 1

    success_replacement = _observation(
        "typescript",
        "parser.parse",
        "unsupported-operation",
        baseline_observation["outcome"],
    )
    success_projection = projection_contract.project_observation(
        success_replacement,
        _context(success_replacement, "unsupported-operation", corpus_fingerprint),
    )
    if (
        success_projection["source"]["observation_identity"]
        != unsupported_comparison["right"]["source"]["observation_identity"]
    ):
        detected += 1

    raw_mutation = copy.deepcopy(baseline_observation)
    raw_mutation["outcome"]["evidence"]["items"].reverse()
    _expect_error(
        lambda: projection_contract.validate_projection(
            baseline_projection,
            raw_mutation,
            _context(
                raw_mutation, "equivalent-after-normalization", corpus_fingerprint
            ),
        ),
        "raw-observation-mutation",
    )
    detected += 1

    _expect_error(
        lambda: classification.classify_comparison(
            differing_comparison,
            evidence_scope="certification_fixture",
            roles={"left": "historical", "right": "replacement"},
            rationale=_rationale(
                differing_comparison,
                [_authority("replacement_evidence", "fixture:promotion")],
            ),
            requested_disposition="preserved_behavior",
            preservation_scope="invalid promotion fixture",
        ),
        "unresolved-promoted-to-accepted",
    )
    detected += 1

    if detected != len(EXPECTED_MUTATION_CASES):
        raise CertificationError("not every controlled mutation was detected")
    return detected


def _run_once(corpus: Mapping[str, Any]) -> dict[str, Any]:
    corpus_fingerprint = projection_contract.canonical_fingerprint(corpus)
    comparisons: dict[str, dict[str, Any]] = {}
    projections: list[dict[str, Any]] = []
    for case in corpus["cases"]:
        case_projections, result = _project_case(
            case, corpus["outcomes"], corpus_fingerprint
        )
        projections.extend(case_projections)
        comparisons[case["id"]] = result

    raw_observation = _observation(
        "python",
        "parser.parse",
        "raw-equivalence",
        corpus["outcomes"]["success-base"],
    )
    if reference.canonical_line(raw_observation) != reference.canonical_line(
        copy.deepcopy(raw_observation)
    ):
        raise CertificationError("equivalent raw observations changed")
    raw_projection = projection_contract.project_observation(
        raw_observation,
        _context(raw_observation, "raw-equivalence", corpus_fingerprint),
        normalization_rule_ids=(),
    )
    projections.append(raw_projection)

    classifications = []
    for fixture in corpus["classification_cases"]:
        comparison = comparisons.get(fixture["comparison_case"])
        if comparison is None:
            raise CertificationError("classification references an unknown comparison")
        result = _classify_fixture(fixture, comparison)
        if result["disposition"] != fixture["disposition"]:
            raise CertificationError("classification disposition did not match")
        classifications.append(result)

    peer = classification.classify_comparison(
        comparisons["meaningful-difference"],
        evidence_scope="historical_evidence_only",
        roles={"left": "historical", "right": "historical"},
        rationale=_rationale(comparisons["meaningful-difference"]),
    )
    if peer["applicability"] != "not_applicable" or peer["disposition"] is not None:
        raise CertificationError("historical peer comparison received a disposition")

    baseline_observation = _observation(
        "python",
        "parser.parse",
        "equivalent-after-normalization",
        corpus["outcomes"]["success-base"],
    )
    baseline_projection = next(
        projection
        for projection in projections
        if projection["source"]["case"]["id"] == "equivalent-after-normalization"
        and projection["source"]["runner"]["id"] == "python"
    )
    malformed_count = _run_malformed_cases(
        baseline_observation,
        baseline_projection,
        comparisons["equivalent-after-normalization"],
        corpus_fingerprint,
    )
    mutation_count = _run_mutations(
        baseline_observation,
        baseline_projection,
        comparisons["meaningful-difference"],
        comparisons["unsupported-operation"],
        corpus_fingerprint,
    )

    relationships = [result["relationship"] for result in comparisons.values()]
    comparability = [
        result["comparability"]["state"] for result in comparisons.values()
    ]
    disposition_counts = {disposition: 0 for disposition in classification.DISPOSITIONS}
    for result in classifications:
        disposition_counts[result["disposition"]] += 1
    metrics = {
        "classifications": len(classifications),
        "comparable_results": comparability.count("comparable"),
        "comparisons": len(comparisons),
        "differing_results": relationships.count("differing_observation"),
        "disposition_counts": disposition_counts,
        "equivalent_results": relationships.count("equivalent_observation"),
        "malformed_cases": malformed_count,
        "mutation_cases": mutation_count,
        "normalization_applications": sum(
            len(projection["normalization_rule_ids"]) for projection in projections
        ),
        "not_applicable_classifications": 1,
        "not_comparable_results": comparability.count("not_comparable"),
        "projections": len(projections),
        "source_observations": len(projections),
        "unexplained_failures": 0,
    }
    return {
        "case_results": [
            {
                "case_id": case_id,
                "comparability": result["comparability"],
                "comparison_identity": result["comparison_identity"],
                "difference_paths": [
                    difference["path"] for difference in result["differences"]
                ],
                "relationship": result["relationship"],
            }
            for case_id, result in sorted(comparisons.items())
        ],
        "classification_results": [
            {
                "classification_identity": result["classification_identity"],
                "disposition": result["disposition"],
            }
            for result in classifications
        ],
        "metrics": metrics,
        "peer_classification_identity": peer["classification_identity"],
        "projection_fingerprints": sorted(
            projection["projection_fingerprint"] for projection in projections
        ),
    }


def certify_fixture_corpus(
    corpus_path: Path = DEFAULT_CORPUS_PATH, repeat_runs: int = 3
) -> dict[str, Any]:
    if (
        isinstance(repeat_runs, bool)
        or not isinstance(repeat_runs, int)
        or repeat_runs < 2
    ):
        raise CertificationError("repeat_runs must be an integer of at least 2")
    corpus_bytes = corpus_path.read_bytes()
    corpus = load_corpus(corpus_path)
    runs = [_run_once(corpus) for _ in range(repeat_runs)]
    lines = [reference.canonical_line(run) for run in runs]
    mismatches = sum(line != lines[0] for line in lines)
    if mismatches:
        raise CertificationError("repeated certification runs were not deterministic")
    if corpus_path.read_bytes() != corpus_bytes:
        raise CertificationError("certification mutated its corpus")
    first = runs[0]
    return reference.canonicalize(
        {
            "certification_kind": CERTIFICATION_KIND,
            "certification_schema_version": CERTIFICATION_SCHEMA_VERSION,
            "comparison_schema_version": projection_contract.COMPARISON_SCHEMA_VERSION,
            "comparator_implementation_version": projection_contract.COMPARATOR_IMPLEMENTATION_VERSION,
            "corpus": {
                "algorithm": "sha256",
                "fingerprint": projection_contract.canonical_fingerprint(corpus),
                "version": corpus["version"],
            },
            "determinism": {
                "mismatches": mismatches,
                "repeat_runs": repeat_runs,
            },
            "metrics": first["metrics"],
            "normalization_rules_version": projection_contract.NORMALIZATION_RULES_VERSION,
            "projection_schema_version": projection_contract.PROJECTION_SCHEMA_VERSION,
            "result_fingerprint": projection_contract.canonical_fingerprint(first),
            "status": "passed",
            "taxonomy_version": projection_contract.TAXONOMY_VERSION,
        }
    )
