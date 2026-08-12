#!/usr/bin/env python3
"""Determinism, non-loss, provenance, and taxonomy certification fixtures."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from tooling import migration_classification as classification
from tooling import migration_comparison as projection_contract
from tooling import migration_comparison_engine as comparison_engine
from tooling.legacy_reference import cross_reference
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
HISTORICAL_CERTIFICATION_KIND = (
    "strling.migration-comparison-historical-evidence-certification"
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


def _validate_historical_batch(
    value: Any,
    runner_id: str,
    corpus: Mapping[str, Any],
) -> dict[str, Any]:
    batch = projection_contract._require_object(
        value, f"historical_batches.{runner_id}"
    )
    projection_contract._exact_keys(
        batch,
        (
            "batch_kind",
            "batch_schema_version",
            "corpus",
            "implementation",
            "observation_schema_version",
            "observations",
            "protocol_version",
            "runner",
        ),
        f"historical_batches.{runner_id}",
    )
    if (
        batch["batch_kind"] != reference.BATCH_KIND
        or batch["batch_schema_version"] != reference.BATCH_SCHEMA_VERSION
        or batch["observation_schema_version"] != reference.OBSERVATION_SCHEMA_VERSION
        or batch["protocol_version"] != reference.PROTOCOL_VERSION
    ):
        raise CertificationError(f"{runner_id} historical batch schema is incompatible")
    if batch["runner"] != cross_reference.RUNNER_IDENTITIES[runner_id]:
        raise CertificationError(f"{runner_id} historical batch runner is incompatible")
    expected_corpus = {
        "algorithm": "sha256",
        "fingerprint": reference.canonical_fingerprint(corpus),
        "version": corpus["corpus_version"],
    }
    if batch["corpus"] != expected_corpus:
        raise CertificationError(
            f"{runner_id} historical batch corpus identity does not match"
        )
    implementation = projection_contract._require_object(
        batch["implementation"], f"historical_batches.{runner_id}.implementation"
    )
    projection_contract._require_fingerprint(
        implementation.get("fingerprint"),
        f"historical_batches.{runner_id}.implementation.fingerprint",
    )
    observations = batch["observations"]
    if not isinstance(observations, list) or len(observations) != len(corpus["cases"]):
        raise CertificationError(
            f"{runner_id} historical batch does not cover its corpus"
        )
    expected_cases = {entry["id"]: entry for entry in corpus["cases"]}
    observed_cases: set[str] = set()
    for index, raw_entry in enumerate(observations):
        entry = projection_contract._require_object(
            raw_entry, f"historical_batches.{runner_id}.observations/{index}"
        )
        projection_contract._exact_keys(
            entry,
            (
                "behavior_family",
                "case_id",
                "case_identity",
                "observation",
                "provenance",
            ),
            f"historical_batches.{runner_id}.observations/{index}",
        )
        case_id = projection_contract._require_nonempty_string(
            entry["case_id"],
            f"historical_batches.{runner_id}.observations/{index}.case_id",
        )
        if case_id in observed_cases or case_id not in expected_cases:
            raise CertificationError(
                f"{runner_id} historical batch has an invalid case identity"
            )
        observed_cases.add(case_id)
        observation = projection_contract._require_object(
            entry["observation"],
            f"historical_batches.{runner_id}.observations/{index}.observation",
        )
        if (
            observation.get("implementation") != implementation
            or observation.get("runner") != batch["runner"]
            or observation.get("operation")
            != expected_cases[case_id]["request"]["operation"]
        ):
            raise CertificationError(
                f"{runner_id} historical observation provenance does not match"
            )
        expected_case_identity = reference.canonical_fingerprint(
            {
                "case_id": case_id,
                "corpus_version": corpus["corpus_version"],
                "request": observation.get("request", {}).get("value"),
            }
        )
        if entry["case_identity"] != expected_case_identity:
            raise CertificationError(
                f"{runner_id} historical source case identity does not match"
            )
    if observed_cases != set(expected_cases):
        raise CertificationError(
            f"{runner_id} historical batch case coverage does not match"
        )
    return reference.canonicalize(batch)


def _historical_rationale(comparison: Mapping[str, Any]) -> dict[str, Any]:
    sources = [
        comparison[side]["source"]
        for side in ("left", "right")
        if comparison[side] is not None
    ]
    differing = comparison["relationship"] == "differing_observation"
    not_comparable = comparison["relationship"] == "not_comparable"
    limitations = ["Historical agreement cannot establish normative correctness."]
    unresolved_questions: list[str] = []
    if differing:
        unresolved_questions.append(
            "Which behavior, if either, conforms to governing authority?"
        )
    elif not_comparable:
        unresolved_questions.append(
            "Can a governed replacement counterpart establish semantic correspondence?"
        )
    return {
        "affected_operation": comparison["operation"],
        "affected_surfaces": sorted(
            surface
            for surface in comparison["surfaces"].values()
            if surface is not None
        ),
        "authority": [],
        "comparison_identity": comparison["comparison_identity"],
        "difference_paths": [
            difference["path"] for difference in comparison["differences"]
        ],
        "evidence_identities": sorted(
            source["observation_identity"] for source in sources
        ),
        "explanation": (
            "Historical runner evidence is recorded without treating consensus "
            "or divergence as normative correctness."
        ),
        "limitations": limitations,
        "unresolved_questions": unresolved_questions,
    }


def _run_historical_once(
    raw_batches: Mapping[str, Any],
    corpora: Mapping[str, Mapping[str, Any]],
    shared_cases: Sequence[Mapping[str, Any]],
    runner_specific_cases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    batches = {
        runner_id: _validate_historical_batch(
            copy.deepcopy(raw_batches[runner_id]),
            runner_id,
            corpora[runner_id],
        )
        for runner_id in cross_reference.SELECTED_RUNNERS
    }
    indexed = {
        runner_id: {
            entry["case_id"]: entry for entry in batches[runner_id]["observations"]
        }
        for runner_id in cross_reference.SELECTED_RUNNERS
    }
    case_results = []
    classifications = []
    projections = []
    comparisons = []
    for shared in shared_cases:
        case_id = shared["case_id"]
        pair = []
        for runner_id in cross_reference.SELECTED_RUNNERS:
            entry = indexed[runner_id][case_id]
            projection = projection_contract.project_observation(
                entry["observation"],
                {
                    "case_id": case_id,
                    "case_identity": entry["case_identity"],
                    "comparison_corpus_version": cross_reference.CROSS_CORPUS_VERSION,
                    "corpus": batches[runner_id]["corpus"],
                },
            )
            projections.append(projection)
            pair.append(projection)
        comparison = comparison_engine.compare_projections(pair[0], pair[1])
        comparisons.append(comparison)
        classification_result = classification.classify_comparison(
            comparison,
            evidence_scope="migration_review",
            roles={"left": "historical", "right": "historical"},
            rationale=_historical_rationale(comparison),
        )
        classifications.append(classification_result)
        case_results.append(
            {
                "case_id": case_id,
                "classification_identity": classification_result[
                    "classification_identity"
                ],
                "comparability": comparison["comparability"],
                "comparison_identity": comparison["comparison_identity"],
                "difference_paths": [
                    difference["path"] for difference in comparison["differences"]
                ],
                "disposition": classification_result["disposition"],
                "projection_fingerprints": [
                    projection["projection_fingerprint"] for projection in pair
                ],
                "relationship": comparison["relationship"],
            }
        )

    relationships = [item["relationship"] for item in comparisons]
    comparability = [item["comparability"]["state"] for item in comparisons]
    disposition_counts = {item: 0 for item in classification.DISPOSITIONS}
    for result in classifications:
        if result["disposition"] is not None:
            disposition_counts[result["disposition"]] += 1
    source_observations = sum(len(batch["observations"]) for batch in batches.values())
    runner_specific_count = sum(
        len(partition["cases"]) for partition in runner_specific_cases
    )
    metrics = {
        "classifications": sum(
            result["disposition"] is not None for result in classifications
        ),
        "comparable_results": comparability.count("comparable"),
        "comparisons": len(comparisons),
        "differing_results": relationships.count("differing_observation"),
        "disposition_counts": disposition_counts,
        "equivalent_results": relationships.count("equivalent_observation"),
        "normalization_applications": sum(
            len(projection["normalization_rule_ids"]) for projection in projections
        ),
        "not_applicable_classifications": sum(
            result["applicability"] == "not_applicable" for result in classifications
        ),
        "not_comparable_results": comparability.count("not_comparable"),
        "projections": len(projections),
        "runner_specific_observations_not_paired": runner_specific_count,
        "selected_source_observations": len(projections),
        "source_observations": source_observations,
        "unexplained_failures": 0,
    }
    return {
        "case_results": case_results,
        "metrics": metrics,
        "runners": [
            {
                "corpus": batches[runner_id]["corpus"],
                "implementation": batches[runner_id]["implementation"],
                "runner": batches[runner_id]["runner"],
            }
            for runner_id in cross_reference.SELECTED_RUNNERS
        ],
    }


def certify_historical_batches(
    batches: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    repeat_runs: int = 3,
    typescript_corpus_path: Path = cross_reference.TYPESCRIPT_CORPUS_PATH,
    python_corpus_path: Path = cross_reference.PYTHON_CORPUS_PATH,
) -> dict[str, Any]:
    """Certify governed shared historical cases without running the full gate."""

    if (
        isinstance(repeat_runs, bool)
        or not isinstance(repeat_runs, int)
        or repeat_runs < 2
    ):
        raise CertificationError("repeat_runs must be an integer of at least 2")
    if tuple(sorted(batches)) != cross_reference.SELECTED_RUNNERS:
        raise CertificationError(
            "historical batches must contain exactly the selected runners"
        )
    for runner_id in cross_reference.SELECTED_RUNNERS:
        runs = batches[runner_id]
        if isinstance(runs, (str, bytes)) or len(runs) != repeat_runs:
            raise CertificationError(
                f"{runner_id} must provide exactly {repeat_runs} historical batches"
            )

    corpus_paths = {
        "python": python_corpus_path,
        "typescript": typescript_corpus_path,
    }
    corpus_bytes = {
        runner_id: path.read_bytes() for runner_id, path in corpus_paths.items()
    }
    corpora = {
        runner_id: cross_reference.load_corpus(path)
        for runner_id, path in corpus_paths.items()
    }
    shared_cases, runner_specific_cases = cross_reference.derive_case_partitions(
        corpora
    )
    raw_before = reference.canonical_json(batches)
    runs = [
        _run_historical_once(
            {
                runner_id: batches[runner_id][index]
                for runner_id in cross_reference.SELECTED_RUNNERS
            },
            corpora,
            shared_cases,
            runner_specific_cases,
        )
        for index in range(repeat_runs)
    ]
    encoded_runs = [reference.canonical_line(run) for run in runs]
    mismatches = sum(encoded != encoded_runs[0] for encoded in encoded_runs)
    if mismatches:
        raise CertificationError(
            "repeated historical comparisons were not deterministic"
        )
    if reference.canonical_json(batches) != raw_before:
        raise CertificationError("historical comparison mutated raw observations")
    if any(
        path.read_bytes() != corpus_bytes[runner_id]
        for runner_id, path in corpus_paths.items()
    ):
        raise CertificationError("historical comparison mutated a source corpus")

    first = runs[0]
    cross_corpus_manifest = {
        "runner_corpora": [
            {
                "corpus": record["corpus"],
                "runner_id": record["runner"]["id"],
            }
            for record in first["runners"]
        ],
        "runner_specific_cases": runner_specific_cases,
        "shared_cases": shared_cases,
        "version": cross_reference.CROSS_CORPUS_VERSION,
    }
    return reference.canonicalize(
        {
            "certification_kind": HISTORICAL_CERTIFICATION_KIND,
            "certification_schema_version": CERTIFICATION_SCHEMA_VERSION,
            "comparison_schema_version": projection_contract.COMPARISON_SCHEMA_VERSION,
            "comparator_implementation_version": projection_contract.COMPARATOR_IMPLEMENTATION_VERSION,
            "corpus": {
                "algorithm": "sha256",
                "fingerprint": reference.canonical_fingerprint(cross_corpus_manifest),
                "version": cross_reference.CROSS_CORPUS_VERSION,
            },
            "determinism": {
                "mismatches": mismatches,
                "repeat_runs": repeat_runs,
            },
            "metrics": first["metrics"],
            "normalization_rules_version": projection_contract.NORMALIZATION_RULES_VERSION,
            "projection_schema_version": projection_contract.PROJECTION_SCHEMA_VERSION,
            "result_fingerprint": projection_contract.canonical_fingerprint(first),
            "results": first["case_results"],
            "runners": first["runners"],
            "status": "passed",
            "taxonomy_version": projection_contract.TAXONOMY_VERSION,
        }
    )
