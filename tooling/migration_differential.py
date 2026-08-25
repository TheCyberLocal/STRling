#!/usr/bin/env python3
"""Blocking, deterministic execution gate for the complete migration corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

try:
    import migration_classification as classification
    import migration_comparison as comparison_contract
    import migration_comparison_certification as comparison_certification
    from legacy_reference import cross_reference
    from legacy_reference import launch as legacy_launch
    from legacy_reference import python_reference as reference
except ModuleNotFoundError:  # pragma: no cover - import path differs under tests
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tooling import migration_classification as classification
    from tooling import migration_comparison as comparison_contract
    from tooling import migration_comparison_certification as comparison_certification
    from tooling.legacy_reference import cross_reference
    from tooling.legacy_reference import launch as legacy_launch
    from tooling.legacy_reference import python_reference as reference

CONTRACT_PATH = Path(__file__).with_name("migration_differential_contract.json")
BASELINE_PATH = Path(__file__).with_name("migration_differential_baseline.json")
FRONTEND_ORCHESTRATION_PATH = (
    ROOT / "spec/frontends/legacy-regex/1.0/orchestration/cases.json"
)
CANDIDATE_KIND = "strling.full-migration-differential-candidate"
NOT_COMPARABLE_REASONS = frozenset(
    comparison_contract.CONTRACT["comparability"]["not_comparable_reasons"]
)
FINGERPRINT_PREFIX = "sha256:"
CARGO = shutil.which("cargo")
if CARGO is None and sys.platform == "win32":
    candidate = Path.home() / ".cargo" / "bin" / "cargo.exe"
    CARGO = str(candidate) if candidate.is_file() else "cargo"
CARGO = CARGO or "cargo"
CANONICAL_FRONTEND_TEST = (
    CARGO,
    "test",
    "--manifest-path",
    "core/internal/Cargo.toml",
    "--test",
    "frontend_orchestration",
    "covers_every_governed_historical_source_through_compile_request",
    "--locked",
    "--quiet",
)


class DifferentialGateError(Exception):
    """The full migration differential cannot be certified safely."""


def _load_json(path: Path, location: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DifferentialGateError(
            f"{location} is unavailable or malformed"
        ) from error
    if not isinstance(value, dict):
        raise DifferentialGateError(f"{location} must be an object")
    return reference.canonicalize(value)


def _exact_keys(
    value: Mapping[str, Any], expected: Sequence[str], location: str
) -> None:
    actual = set(value)
    required = set(expected)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("unexpected " + ", ".join(extra))
        raise DifferentialGateError(
            f"{location} keys are invalid: {'; '.join(details)}"
        )


def _require_text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DifferentialGateError(f"{location} must be non-empty text")
    return value


def _require_fingerprint(value: Any, location: str) -> str:
    try:
        return comparison_contract._require_fingerprint(value, location)
    except comparison_contract.ComparisonContractError as error:
        raise DifferentialGateError(str(error)) from error


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = _load_json(path, "migration differential contract")
    validate_contract(contract)
    return contract


def load_baseline(path: Path = BASELINE_PATH) -> dict[str, Any]:
    return _load_json(path, "migration differential baseline")


def _validate_authority(value: Any, location: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise DifferentialGateError(f"{location} must contain governing authority")
    result = []
    for index, raw_entry in enumerate(value):
        if not isinstance(raw_entry, dict):
            raise DifferentialGateError(f"{location}/{index} must be an object")
        _exact_keys(raw_entry, ("kind", "reference"), f"{location}/{index}")
        result.append(
            {
                "kind": _require_text(raw_entry["kind"], f"{location}/{index}.kind"),
                "reference": _require_text(
                    raw_entry["reference"], f"{location}/{index}.reference"
                ),
            }
        )
    return result


def validate_contract(raw_contract: Mapping[str, Any]) -> dict[str, Any]:
    contract = copy.deepcopy(dict(raw_contract))
    _exact_keys(
        contract,
        (
            "artifact_kind",
            "artifact_schema_version",
            "authority_model",
            "baseline_schema_version",
            "canonical_boundary",
            "comparison_contract",
            "gate_schema_version",
            "runner_corpora",
        ),
        "contract",
    )
    for field in (
        "artifact_kind",
        "artifact_schema_version",
        "baseline_schema_version",
        "gate_schema_version",
    ):
        _require_text(contract[field], f"contract.{field}")

    authority = contract["authority_model"]
    if not isinstance(authority, dict):
        raise DifferentialGateError("contract.authority_model must be an object")
    _exact_keys(
        authority,
        (
            "historical_evidence_is_normative",
            "historical_peer_discrepancies_are_evidence_only",
            "not_comparable_requires_review",
            "unresolved_replacement_discrepancies_are_blocking",
        ),
        "contract.authority_model",
    )
    expected_authority = {
        "historical_evidence_is_normative": False,
        "historical_peer_discrepancies_are_evidence_only": True,
        "not_comparable_requires_review": True,
        "unresolved_replacement_discrepancies_are_blocking": True,
    }
    if authority != expected_authority:
        raise DifferentialGateError("contract authority invariants were weakened")

    versions = contract["comparison_contract"]
    if not isinstance(versions, dict):
        raise DifferentialGateError("contract.comparison_contract must be an object")
    expected_versions = {
        "comparison_schema_version": comparison_contract.COMPARISON_SCHEMA_VERSION,
        "normalization_rules_version": comparison_contract.NORMALIZATION_RULES_VERSION,
        "projection_schema_version": comparison_contract.PROJECTION_SCHEMA_VERSION,
        "taxonomy_version": comparison_contract.TAXONOMY_VERSION,
    }
    if versions != expected_versions:
        raise DifferentialGateError("comparison contract versions are incompatible")

    runner_corpora = contract["runner_corpora"]
    if not isinstance(runner_corpora, list):
        raise DifferentialGateError("contract.runner_corpora must be an array")
    runner_ids = []
    for index, entry in enumerate(runner_corpora):
        if not isinstance(entry, dict):
            raise DifferentialGateError(f"contract.runner_corpora/{index} is invalid")
        _exact_keys(
            entry,
            ("minimum_case_count", "path", "runner_id"),
            f"contract.runner_corpora/{index}",
        )
        runner_id = _require_text(
            entry["runner_id"], f"contract.runner_corpora/{index}.runner_id"
        )
        runner_ids.append(runner_id)
        _require_text(entry["path"], f"contract.runner_corpora/{index}.path")
        minimum = entry["minimum_case_count"]
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            raise DifferentialGateError(
                f"contract.runner_corpora/{index}.minimum_case_count is invalid"
            )
    if tuple(sorted(runner_ids)) != cross_reference.SELECTED_RUNNERS:
        raise DifferentialGateError("contract must cover exactly the selected runners")

    boundary = contract["canonical_boundary"]
    if not isinstance(boundary, dict):
        raise DifferentialGateError("contract.canonical_boundary must be an object")
    _exact_keys(
        boundary,
        ("authority", "implementation_paths", "routes"),
        "contract.canonical_boundary",
    )
    _validate_authority(boundary["authority"], "contract.canonical_boundary.authority")
    paths = boundary["implementation_paths"]
    if not isinstance(paths, list) or not paths:
        raise DifferentialGateError("canonical implementation paths are required")
    for index, path in enumerate(paths):
        _require_text(path, f"contract.canonical_boundary.implementation_paths/{index}")
    routes = boundary["routes"]
    if not isinstance(routes, list) or not routes:
        raise DifferentialGateError("canonical route reviews are required")
    operation_ids = set()
    review_ids = set()
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            raise DifferentialGateError(
                f"contract.canonical_boundary.routes/{index} is invalid"
            )
        location = f"contract.canonical_boundary.routes/{index}"
        _exact_keys(
            route,
            (
                "authority",
                "canonical_surface",
                "operation",
                "rationale",
                "reason",
                "review_id",
                "state",
            ),
            location,
        )
        operation = _require_text(route["operation"], f"{location}.operation")
        review_id = _require_text(route["review_id"], f"{location}.review_id")
        if operation in operation_ids or review_id in review_ids:
            raise DifferentialGateError("canonical route identities must be unique")
        operation_ids.add(operation)
        review_ids.add(review_id)
        _require_text(route["rationale"], f"{location}.rationale")
        _validate_authority(route["authority"], f"{location}.authority")
        state = route["state"]
        if state == "not_comparable":
            if route["reason"] not in NOT_COMPARABLE_REASONS:
                raise DifferentialGateError(f"{location}.reason is invalid")
            surface = route["canonical_surface"]
            if surface is not None and not isinstance(surface, str):
                raise DifferentialGateError(f"{location}.canonical_surface is invalid")
        elif state == "comparable":
            if route["reason"] is not None:
                raise DifferentialGateError(f"{location}.reason must be null")
            _require_text(route["canonical_surface"], f"{location}.canonical_surface")
        else:
            raise DifferentialGateError(f"{location}.state is invalid")
    return reference.canonicalize(contract)


def _contract_corpora(contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    corpora = {}
    for entry in contract["runner_corpora"]:
        path = ROOT / entry["path"]
        corpus = cross_reference.load_corpus(path)
        if len(corpus["cases"]) < entry["minimum_case_count"]:
            raise DifferentialGateError(
                f"{entry['runner_id']} corpus shrank below its contractual minimum"
            )
        corpora[entry["runner_id"]] = corpus
    return corpora


def _canonical_source_bytes(data: bytes) -> bytes:
    """Return repository-canonical bytes for governed text sources."""
    return data.replace(b"\r\n", b"\n")


def canonical_boundary_identity(contract: Mapping[str, Any]) -> dict[str, Any]:
    paths = set()
    for pattern in contract["canonical_boundary"]["implementation_paths"]:
        matches = [path for path in ROOT.glob(pattern) if path.is_file()]
        if not matches:
            raise DifferentialGateError(
                f"canonical implementation path pattern '{pattern}' matched no files"
            )
        paths.update(matches)
    inputs = []
    for path in sorted(paths):
        data = _canonical_source_bytes(path.read_bytes())
        inputs.append(
            {
                "bytes": len(data),
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {
        "algorithm": "sha256",
        "fingerprint": reference.canonical_fingerprint(
            {
                "authority": contract["canonical_boundary"]["authority"],
                "inputs": inputs,
            }
        ),
        "input_count": len(inputs),
        "inputs": inputs,
    }


def _validate_frontend_orchestration_coverage(
    orchestration: Mapping[str, Any] | None = None,
    corpora: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, int]:
    governed = (
        _load_json(FRONTEND_ORCHESTRATION_PATH, "frontend orchestration corpus")
        if orchestration is None
        else copy.deepcopy(dict(orchestration))
    )
    _exact_keys(
        governed,
        ("authorship", "authority", "case_set_version", "cases", "frontend"),
        "frontend orchestration corpus",
    )
    if governed["case_set_version"] != "1.0.0":
        raise DifferentialGateError(
            "frontend orchestration corpus version is unsupported"
        )
    if governed["frontend"] != "strling.regex-compat@1.0.0":
        raise DifferentialGateError("frontend orchestration identity is incompatible")
    if governed["authorship"] != "specification-authored":
        raise DifferentialGateError(
            "frontend orchestration must be specification-authored"
        )
    _require_text(governed["authority"], "frontend orchestration corpus.authority")

    raw_cases = governed["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise DifferentialGateError("frontend orchestration cases are required")
    coverage: dict[tuple[str, str], str] = {}
    sources: set[str] = set()
    for index, case in enumerate(raw_cases):
        location = f"frontend orchestration corpus.cases/{index}"
        if not isinstance(case, dict):
            raise DifferentialGateError(f"{location} must be an object")
        _exact_keys(
            case,
            ("expected", "historical_cases", "id", "source"),
            location,
        )
        _require_text(case["id"], f"{location}.id")
        source = _require_text(case["source"], f"{location}.source")
        if source in sources:
            raise DifferentialGateError("frontend orchestration sources must be unique")
        sources.add(source)
        expected = case["expected"]
        if not isinstance(expected, dict):
            raise DifferentialGateError(f"{location}.expected is invalid")
        outcome = expected.get("outcome")
        expected_keys = (
            ("outcome",) if outcome == "succeeded" else ("diagnostic_code", "outcome")
        )
        _exact_keys(expected, expected_keys, f"{location}.expected")
        if outcome == "failed":
            _require_text(
                expected["diagnostic_code"], f"{location}.expected.diagnostic_code"
            )
        elif outcome != "succeeded":
            raise DifferentialGateError(f"{location}.expected.outcome is invalid")
        references = case["historical_cases"]
        if not isinstance(references, list) or not references:
            raise DifferentialGateError(f"{location}.historical_cases is required")
        for reference_index, reference in enumerate(references):
            reference_location = f"{location}.historical_cases/{reference_index}"
            if not isinstance(reference, dict):
                raise DifferentialGateError(f"{reference_location} must be an object")
            _exact_keys(reference, ("case_id", "runner_id"), reference_location)
            key = (
                _require_text(
                    reference["runner_id"], f"{reference_location}.runner_id"
                ),
                _require_text(reference["case_id"], f"{reference_location}.case_id"),
            )
            if key in coverage:
                raise DifferentialGateError(
                    "historical source-bearing cases must map exactly once"
                )
            coverage[key] = source

    corpus_set = (
        _contract_corpora(load_contract()) if corpora is None else dict(corpora)
    )
    source_bearing_cases = 0
    for runner_id, corpus in sorted(corpus_set.items()):
        for case in corpus["cases"]:
            source = case["request"].get("input", {}).get("source")
            if source is None:
                continue
            source_bearing_cases += 1
            key = (runner_id, case["id"])
            if coverage.pop(key, None) != source:
                raise DifferentialGateError(
                    f"frontend orchestration coverage differs for {runner_id}/{case['id']}"
                )
    if coverage:
        raise DifferentialGateError(
            "frontend orchestration contains orphaned historical references"
        )
    return {
        "historical_source_cases": source_bearing_cases,
        "orchestration_cases": len(raw_cases),
    }


def _certify_canonical_frontend_route(runner: Any = None) -> None:
    _validate_frontend_orchestration_coverage()
    execute = subprocess.run if runner is None else runner
    try:
        completed = execute(
            list(CANONICAL_FRONTEND_TEST),
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise DifferentialGateError(
            "canonical CompileRequest frontend route could not be executed"
        ) from error
    if completed.returncode != 0:
        details = completed.stderr.decode("utf-8", errors="replace").strip()
        suffix = f": {details}" if details else ""
        raise DifferentialGateError(
            f"canonical CompileRequest frontend route failed{suffix}"
        )


def capture_full_corpus(repeat_runs: int) -> dict[str, list[dict[str, Any]]]:
    if (
        isinstance(repeat_runs, bool)
        or not isinstance(repeat_runs, int)
        or repeat_runs < 2
    ):
        raise DifferentialGateError("repeat_runs must be an integer of at least 2")
    _certify_canonical_frontend_route()
    batches: dict[str, list[dict[str, Any]]] = {"python": [], "typescript": []}
    temporary_parent = legacy_launch.TYPESCRIPT_ROOT / "target"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="strling-migration-differential-", dir=temporary_parent
    ) as raw:
        snapshot_root = Path(raw) / "snapshot"
        legacy_launch.adapter_evidence.materialize_historical_sources(snapshot_root)
        output = Path(raw) / "dist"
        if legacy_launch.build_legacy_typescript(snapshot_root, output) != 0:
            raise DifferentialGateError(
                "historical TypeScript runner could not be built"
            )
        environment = legacy_launch.frozen_environment(snapshot_root, output)
        for _ in range(repeat_runs):
            typescript = legacy_launch.capture_certification(
                [
                    "node",
                    str(legacy_launch.TOOL_ROOT / "corpus_cli.mjs"),
                    "--observations",
                ],
                env=environment,
            )
            python = legacy_launch.capture_certification(
                [
                    sys.executable,
                    str(legacy_launch.TOOL_ROOT / "python_reference.py"),
                    "--corpus",
                ],
                env=environment,
            )
            if typescript is None or python is None:
                raise DifferentialGateError(
                    "a historical runner did not produce a batch"
                )
            batches["typescript"].append(typescript)
            batches["python"].append(python)
    return batches


def _source_records(
    validated_batches: Mapping[str, Mapping[str, Any]],
    route_by_operation: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for runner_id in sorted(validated_batches):
        batch = validated_batches[runner_id]
        for entry in batch["observations"]:
            observation = entry["observation"]
            operation = observation["operation"]
            route = route_by_operation.get(operation)
            if route is None:
                raise DifferentialGateError(
                    f"operation '{operation}' has no canonical route review"
                )
            if route["state"] == "comparable":
                raise DifferentialGateError(
                    f"operation '{operation}' is marked comparable without canonical execution evidence"
                )
            records.append(
                {
                    "behavior_family": entry["behavior_family"],
                    "canonical_counterpart": {
                        "authority": route["authority"],
                        "canonical_surface": route["canonical_surface"],
                        "disposition": None,
                        "rationale": route["rationale"],
                        "reason": route["reason"],
                        "review_id": route["review_id"],
                        "state": route["state"],
                    },
                    "case_id": entry["case_id"],
                    "case_identity": entry["case_identity"],
                    "observation_identity": reference.canonical_fingerprint(
                        observation
                    ),
                    "operation": operation,
                    "outcome_fingerprint": reference.canonical_fingerprint(
                        observation["outcome"]
                    ),
                    "outcome_status": observation["outcome"]["status"],
                    "provenance": entry["provenance"],
                    "request_fingerprint": observation["request"]["fingerprint"],
                    "runner_id": runner_id,
                    "surface": observation["surface"],
                }
            )
    return reference.canonicalize(records)


def validate_replacement_reviews(
    raw_reviews: Any, *, allow_certification_fixture: bool = False
) -> list[dict[str, Any]]:
    if not isinstance(raw_reviews, list):
        raise DifferentialGateError("replacement_reviews must be an array")
    reviews = []
    review_ids = set()
    for index, raw_review in enumerate(raw_reviews):
        location = f"replacement_reviews/{index}"
        if not isinstance(raw_review, dict):
            raise DifferentialGateError(f"{location} must be an object")
        _exact_keys(
            raw_review,
            ("classification", "comparison", "review_id"),
            location,
        )
        review_id = _require_text(raw_review["review_id"], f"{location}.review_id")
        if review_id in review_ids:
            raise DifferentialGateError("replacement review IDs must be unique")
        review_ids.add(review_id)
        comparison = classification.validate_comparison_result(
            copy.deepcopy(raw_review["comparison"])
        )
        artifact = raw_review["classification"]
        if not isinstance(artifact, dict):
            raise DifferentialGateError(f"{location}.classification must be an object")
        evidence_scope = artifact.get("evidence_scope")
        if evidence_scope != "migration_review" and not (
            allow_certification_fixture and evidence_scope == "certification_fixture"
        ):
            raise DifferentialGateError(
                f"{location} must contain a governed migration review"
            )
        try:
            rebuilt = classification.classify_comparison(
                comparison,
                evidence_scope=artifact["evidence_scope"],
                roles=artifact["roles"],
                rationale=artifact["rationale"],
                requested_disposition=artifact["disposition"],
                preservation_scope=artifact["preservation_scope"],
                corrected_rule=artifact["corrected_rule"],
                scope_boundary=artifact["scope_boundary"],
                exceptional_justification=artifact["exceptional_justification"],
                supersedes=artifact["supersedes"],
            )
        except (KeyError, classification.ClassificationError) as error:
            raise DifferentialGateError(
                f"{location} contains an invalid approved disposition"
            ) from error
        if rebuilt != artifact:
            raise DifferentialGateError(
                f"{location} approved disposition is stale or altered"
            )
        if rebuilt["applicability"] != "classified":
            raise DifferentialGateError(
                f"{location} does not contain a replacement classification"
            )
        if rebuilt["disposition"] == "unresolved_discrepancy":
            raise DifferentialGateError(
                f"{location} contains a blocking unresolved discrepancy"
            )
        reviews.append(
            {
                "classification_identity": rebuilt["classification_identity"],
                "comparison_identity": comparison["comparison_identity"],
                "disposition": rebuilt["disposition"],
                "review_id": review_id,
            }
        )
    return reference.canonicalize(reviews)


def build_candidate(
    batches: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    contract: Mapping[str, Any],
    repeat_runs: int,
) -> dict[str, Any]:
    contract = validate_contract(contract)
    corpora = _contract_corpora(contract)
    if tuple(sorted(batches)) != cross_reference.SELECTED_RUNNERS:
        raise DifferentialGateError("batches must contain exactly the selected runners")
    route_by_operation = {
        route["operation"]: route for route in contract["canonical_boundary"]["routes"]
    }
    corpus_operations = {
        entry["request"]["operation"]
        for corpus in corpora.values()
        for entry in corpus["cases"]
    }
    if set(route_by_operation) != corpus_operations:
        raise DifferentialGateError(
            "canonical route reviews do not exactly cover corpus operations"
        )

    records_by_run = []
    first_batches = None
    for run_index in range(repeat_runs):
        selected = {}
        for runner_id in cross_reference.SELECTED_RUNNERS:
            runs = batches[runner_id]
            if isinstance(runs, (str, bytes)) or len(runs) != repeat_runs:
                raise DifferentialGateError(
                    f"{runner_id} must provide exactly {repeat_runs} batches"
                )
            selected[runner_id] = comparison_certification._validate_historical_batch(
                copy.deepcopy(runs[run_index]), runner_id, corpora[runner_id]
            )
        records_by_run.append(_source_records(selected, route_by_operation))
        if first_batches is None:
            first_batches = selected
    encoded_runs = [reference.canonical_line(records) for records in records_by_run]
    mismatches = sum(encoded != encoded_runs[0] for encoded in encoded_runs)
    if mismatches:
        raise DifferentialGateError(
            "repeated full-corpus observations were not deterministic"
        )
    assert first_batches is not None

    historical_peer = comparison_certification.certify_historical_batches(
        batches,
        repeat_runs=repeat_runs,
        typescript_corpus_path=ROOT / "tooling/legacy_reference/corpus.json",
        python_corpus_path=ROOT / "tooling/legacy_reference/python_corpus.json",
    )
    source_records = records_by_run[0]
    corpora_evidence = []
    for runner_id in sorted(corpora):
        corpus = corpora[runner_id]
        case_keys = [
            {
                "case_id": entry["id"],
                "operation": entry["request"]["operation"],
            }
            for entry in corpus["cases"]
        ]
        corpora_evidence.append(
            {
                "case_count": len(case_keys),
                "case_set_fingerprint": reference.canonical_fingerprint(case_keys),
                "corpus_fingerprint": reference.canonical_fingerprint(corpus),
                "corpus_version": corpus["corpus_version"],
                "runner_id": runner_id,
            }
        )

    peer_unresolved = historical_peer["metrics"]["disposition_counts"][
        "unresolved_discrepancy"
    ]
    return reference.canonicalize(
        {
            "baseline_schema_version": contract["baseline_schema_version"],
            "candidate_kind": CANDIDATE_KIND,
            "canonical_boundary": canonical_boundary_identity(contract),
            "contract_fingerprint": reference.canonical_fingerprint(contract),
            "corpora": corpora_evidence,
            "determinism": {
                "mismatches": mismatches,
                "repeat_runs": repeat_runs,
            },
            "full_corpus_fingerprint": reference.canonical_fingerprint(
                {
                    "corpora": corpora_evidence,
                    "source_observations": source_records,
                }
            ),
            "historical_peer_comparison": {
                "corpus": historical_peer["corpus"],
                "metrics": historical_peer["metrics"],
                "result_fingerprint": historical_peer["result_fingerprint"],
                "results": historical_peer["results"],
            },
            "metrics": {
                "blocking_unresolved_replacements": 0,
                "canonical_comparable_cases": 0,
                "canonical_not_comparable_cases": len(source_records),
                "historical_peer_unresolved_evidence": peer_unresolved,
                "source_observations": len(source_records),
            },
            "route_coverage_fingerprint": reference.canonical_fingerprint(
                [
                    {
                        "case_id": record["case_id"],
                        "review_id": record["canonical_counterpart"]["review_id"],
                        "runner_id": record["runner_id"],
                    }
                    for record in source_records
                ]
            ),
            "source_observations": source_records,
        }
    )


def baseline_projection(
    candidate: Mapping[str, Any], replacement_reviews: Any
) -> dict[str, Any]:
    reviews = validate_replacement_reviews(replacement_reviews)
    return reference.canonicalize(
        {
            "baseline_schema_version": candidate["baseline_schema_version"],
            "canonical_boundary_fingerprint": candidate["canonical_boundary"][
                "fingerprint"
            ],
            "contract_fingerprint": candidate["contract_fingerprint"],
            "corpora": candidate["corpora"],
            "full_corpus_fingerprint": candidate["full_corpus_fingerprint"],
            "historical_peer_corpus_fingerprint": candidate[
                "historical_peer_comparison"
            ]["corpus"]["fingerprint"],
            "historical_peer_result_fingerprint": candidate[
                "historical_peer_comparison"
            ]["result_fingerprint"],
            "replacement_reviews": reviews,
            "route_coverage_fingerprint": candidate["route_coverage_fingerprint"],
            "source_observations_fingerprint": reference.canonical_fingerprint(
                candidate["source_observations"]
            ),
        }
    )


def propose_baseline(candidate: Mapping[str, Any]) -> dict[str, Any]:
    baseline = baseline_projection(candidate, [])
    baseline["baseline_fingerprint"] = reference.canonical_fingerprint(baseline)
    return reference.canonicalize(baseline)


def validate_baseline(
    candidate: Mapping[str, Any], raw_baseline: Mapping[str, Any]
) -> dict[str, Any]:
    baseline = copy.deepcopy(dict(raw_baseline))
    _exact_keys(
        baseline,
        (
            "baseline_fingerprint",
            "baseline_schema_version",
            "canonical_boundary_fingerprint",
            "contract_fingerprint",
            "corpora",
            "full_corpus_fingerprint",
            "historical_peer_corpus_fingerprint",
            "historical_peer_result_fingerprint",
            "replacement_reviews",
            "route_coverage_fingerprint",
            "source_observations_fingerprint",
        ),
        "baseline",
    )
    baseline_fingerprint = _require_fingerprint(
        baseline.pop("baseline_fingerprint"), "baseline.baseline_fingerprint"
    )
    if reference.canonical_fingerprint(baseline) != baseline_fingerprint:
        raise DifferentialGateError("migration differential baseline was altered")
    actual = baseline_projection(candidate, raw_baseline["replacement_reviews"])
    if actual["contract_fingerprint"] != baseline["contract_fingerprint"]:
        raise DifferentialGateError(
            "migration review records are stale for the contract"
        )
    expected_total = sum(entry["case_count"] for entry in baseline["corpora"])
    actual_total = sum(entry["case_count"] for entry in actual["corpora"])
    if actual_total < expected_total:
        raise DifferentialGateError("migration corpus shrinkage is blocking")
    if actual["corpora"] != baseline["corpora"]:
        raise DifferentialGateError(
            "migration corpus identity or case coverage changed"
        )
    if (
        actual["canonical_boundary_fingerprint"]
        != baseline["canonical_boundary_fingerprint"]
    ):
        raise DifferentialGateError(
            "canonical boundary changed without renewed migration review"
        )
    if actual["route_coverage_fingerprint"] != baseline["route_coverage_fingerprint"]:
        raise DifferentialGateError("canonical route approvals are stale")
    if (
        actual["source_observations_fingerprint"]
        != baseline["source_observations_fingerprint"]
    ):
        raise DifferentialGateError("a governed source observation changed")
    if (
        actual["historical_peer_result_fingerprint"]
        != baseline["historical_peer_result_fingerprint"]
        or actual["historical_peer_corpus_fingerprint"]
        != baseline["historical_peer_corpus_fingerprint"]
    ):
        raise DifferentialGateError("historical peer comparison evidence changed")
    if actual["full_corpus_fingerprint"] != baseline["full_corpus_fingerprint"]:
        raise DifferentialGateError("full migration corpus fingerprint changed")
    if actual != baseline:
        raise DifferentialGateError("migration differential baseline is stale")
    return reference.canonicalize(
        {"baseline_fingerprint": baseline_fingerprint, **baseline}
    )


def certify(
    batches: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    contract: Mapping[str, Any],
    baseline: Mapping[str, Any],
    repeat_runs: int,
) -> dict[str, Any]:
    candidate = build_candidate(
        batches,
        contract=contract,
        repeat_runs=repeat_runs,
    )
    validated_baseline = validate_baseline(candidate, baseline)
    artifact = {
        "artifact_kind": contract["artifact_kind"],
        "artifact_schema_version": contract["artifact_schema_version"],
        "baseline_fingerprint": validated_baseline["baseline_fingerprint"],
        "canonical_boundary": candidate["canonical_boundary"],
        "contract_fingerprint": candidate["contract_fingerprint"],
        "corpora": candidate["corpora"],
        "determinism": candidate["determinism"],
        "full_corpus_fingerprint": candidate["full_corpus_fingerprint"],
        "historical_peer_comparison": candidate["historical_peer_comparison"],
        "metrics": candidate["metrics"],
        "replacement_reviews": validated_baseline["replacement_reviews"],
        "route_coverage_fingerprint": candidate["route_coverage_fingerprint"],
        "source_observations": candidate["source_observations"],
        "status": "passed",
    }
    artifact["result_fingerprint"] = reference.canonical_fingerprint(artifact)
    return reference.canonicalize(artifact)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the complete blocking STRling migration differential."
    )
    parser.add_argument("--repeat-runs", default=3, type=int)
    parser.add_argument("--print-baseline-candidate", action="store_true")
    return parser.parse_args(argv)


def _failure(error: Exception) -> str:
    return reference.canonical_line(
        {
            "error": {
                "code": "MIGRATION_DIFFERENTIAL_GATE_FAILED",
                "message": str(error),
            },
            "status": "failed",
        }
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        contract = load_contract()
        batches = capture_full_corpus(args.repeat_runs)
        if args.print_baseline_candidate:
            result = propose_baseline(
                build_candidate(
                    batches,
                    contract=contract,
                    repeat_runs=args.repeat_runs,
                )
            )
        else:
            result = certify(
                batches,
                contract=contract,
                baseline=load_baseline(),
                repeat_runs=args.repeat_runs,
            )
    except (
        DifferentialGateError,
        classification.ClassificationError,
        comparison_certification.CertificationError,
        comparison_contract.ComparisonContractError,
        cross_reference.CrossCertificationError,
    ) as error:
        sys.stderr.write(_failure(error))
        return 2
    sys.stdout.write(reference.canonical_line(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
