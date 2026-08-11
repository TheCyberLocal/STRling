#!/usr/bin/env python3
"""Cross-runner certification without semantic comparison or disposition."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Mapping

try:
    from . import python_reference as reference
except ImportError:
    import python_reference as reference


ROOT = Path(__file__).resolve().parents[2]
TYPESCRIPT_CORPUS_PATH = Path(__file__).with_name("corpus.json")
PYTHON_CORPUS_PATH = Path(__file__).with_name("python_corpus.json")
CROSS_CERTIFICATION_KIND = "strling.legacy-reference-cross-runner-certification"
CROSS_CERTIFICATION_SCHEMA_VERSION = "1.1.0"
CROSS_CORPUS_VERSION = "1.0.0"
SELECTED_RUNNERS = ("python", "typescript")
RUNNER_IDENTITIES = {
    "python": reference.RUNNER,
    "typescript": {
        "id": "typescript",
        "kind": "strling.legacy-reference-runner",
        "language": "typescript",
        "version": "1.0.0",
    },
}
FINGERPRINT_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class CrossCertificationError(Exception):
    """A selected-runner certification cannot be aggregated safely."""


def load_corpus(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CrossCertificationError(
            f"corpus '{path.name}' is not valid JSON"
        ) from error
    if not isinstance(value, dict) or not isinstance(value.get("cases"), list):
        raise CrossCertificationError(
            f"corpus '{path.name}' must contain a cases array"
        )
    if not isinstance(value.get("corpus_version"), str):
        raise CrossCertificationError(
            f"corpus '{path.name}' must declare corpus_version"
        )
    case_ids: set[str] = set()
    for entry in value["cases"]:
        if not isinstance(entry, dict):
            raise CrossCertificationError(
                f"corpus '{path.name}' contains a non-object case"
            )
        case_id = entry.get("id")
        request = entry.get("request")
        if not isinstance(case_id, str) or not isinstance(request, dict):
            raise CrossCertificationError(
                f"corpus '{path.name}' contains an invalid case"
            )
        if case_id in case_ids:
            raise CrossCertificationError(
                f"corpus '{path.name}' repeats case id '{case_id}'"
            )
        case_ids.add(case_id)
        for key in ("operation", "input", "options"):
            if key not in request:
                raise CrossCertificationError(
                    f"case '{case_id}' is missing request.{key}"
                )
    return reference.canonicalize(value)


def _require_fingerprint(value: Any, location: str) -> str:
    if not isinstance(value, str) or FINGERPRINT_PATTERN.fullmatch(value) is None:
        raise CrossCertificationError(
            f"{location} must be a canonical sha256 fingerprint"
        )
    return value


def _case_semantics(entry: Mapping[str, Any]) -> dict[str, Any]:
    request = entry["request"]
    return {
        "case_id": entry["id"],
        "input": request["input"],
        "operation": request["operation"],
        "options": request["options"],
    }


def _runner_case_identity(
    runner_id: str,
    corpus_version: str,
    entry: Mapping[str, Any],
) -> str:
    return reference.canonical_fingerprint(
        {
            "corpus_version": corpus_version,
            "runner_id": runner_id,
            "semantics": _case_semantics(entry),
        }
    )


def _validate_certification(
    certification: Any,
    corpus: Mapping[str, Any],
    expected_runner_id: str,
) -> dict[str, Any]:
    if not isinstance(certification, dict):
        raise CrossCertificationError(
            f"{expected_runner_id} certification must be an object"
        )
    if certification.get("status") != "passed":
        raise CrossCertificationError(
            f"{expected_runner_id} certification must have passed"
        )
    if certification.get("protocol_version") != reference.PROTOCOL_VERSION:
        raise CrossCertificationError(
            f"{expected_runner_id} protocol version is incompatible"
        )
    if (
        certification.get("observation_schema_version")
        != reference.OBSERVATION_SCHEMA_VERSION
    ):
        raise CrossCertificationError(
            f"{expected_runner_id} observation schema is incompatible"
        )
    if (
        certification.get("certification_schema_version")
        != reference.CERTIFICATION_SCHEMA_VERSION
    ):
        raise CrossCertificationError(
            f"{expected_runner_id} certification schema is incompatible"
        )

    runner = certification.get("runner")
    if runner != RUNNER_IDENTITIES[expected_runner_id]:
        raise CrossCertificationError(
            f"{expected_runner_id} certification has the wrong runner identity"
        )

    implementation = certification.get("implementation")
    if not isinstance(implementation, dict):
        raise CrossCertificationError(
            f"{expected_runner_id} implementation identity is missing"
        )
    _require_fingerprint(
        implementation.get("fingerprint"),
        f"{expected_runner_id} implementation fingerprint",
    )

    corpus_identity = certification.get("corpus")
    if not isinstance(corpus_identity, dict):
        raise CrossCertificationError(
            f"{expected_runner_id} corpus identity is missing"
        )
    expected_corpus_fingerprint = reference.canonical_fingerprint(corpus)
    if corpus_identity.get("fingerprint") != expected_corpus_fingerprint:
        raise CrossCertificationError(
            f"{expected_runner_id} corpus fingerprint does not match its source"
        )
    if corpus_identity.get("version") != corpus["corpus_version"]:
        raise CrossCertificationError(
            f"{expected_runner_id} corpus version does not match its source"
        )

    summaries = certification.get("case_summaries")
    if not isinstance(summaries, list) or len(summaries) != len(corpus["cases"]):
        raise CrossCertificationError(
            f"{expected_runner_id} case summaries do not cover its corpus"
        )
    expected_cases = {
        entry["id"]: entry["request"]["operation"] for entry in corpus["cases"]
    }
    observed_cases: dict[str, str] = {}
    for summary in summaries:
        if not isinstance(summary, dict):
            raise CrossCertificationError(
                f"{expected_runner_id} contains an invalid case summary"
            )
        case_id = summary.get("case_id")
        operation = summary.get("operation")
        if not isinstance(case_id, str) or not isinstance(operation, str):
            raise CrossCertificationError(
                f"{expected_runner_id} contains an incomplete case summary"
            )
        if case_id in observed_cases:
            raise CrossCertificationError(
                f"{expected_runner_id} repeats case summary '{case_id}'"
            )
        observed_cases[case_id] = operation
    if observed_cases != expected_cases:
        raise CrossCertificationError(
            f"{expected_runner_id} case summaries do not match its corpus"
        )

    operation_counts = certification.get("operation_counts")
    outcome_counts = certification.get("outcome_counts")
    if (
        not isinstance(operation_counts, dict)
        or sum(operation_counts.values()) != len(corpus["cases"])
        or not isinstance(outcome_counts, dict)
        or sum(outcome_counts.values()) != len(corpus["cases"])
    ):
        raise CrossCertificationError(
            f"{expected_runner_id} certification counts are inconsistent"
        )

    repeatability = certification.get("repeatability")
    if (
        not isinstance(repeatability, dict)
        or repeatability.get("repeat_runs", 0) < 2
        or repeatability.get("mismatches") != 0
        or repeatability.get("canonical_observations_compared")
        != len(corpus["cases"]) * repeatability["repeat_runs"]
    ):
        raise CrossCertificationError(
            f"{expected_runner_id} repeatability evidence is invalid"
        )
    fixture_immutability = certification.get("fixture_immutability")
    if (
        not isinstance(fixture_immutability, dict)
        or fixture_immutability.get("corpus_unchanged") is not True
        or fixture_immutability.get("governed_implementation_inputs_unchanged")
        is not True
    ):
        raise CrossCertificationError(
            f"{expected_runner_id} fixture immutability did not pass"
        )
    if certification.get("unexplained_failures") != 0:
        raise CrossCertificationError(
            f"{expected_runner_id} has unexplained runner failures"
        )
    malformed_cases = certification.get("malformed_cases")
    if isinstance(malformed_cases, bool) or not isinstance(malformed_cases, int):
        raise CrossCertificationError(
            f"{expected_runner_id} malformed case count is invalid"
        )
    return certification


def derive_case_partitions(
    corpora: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    for runner_id in sorted(corpora):
        for entry in corpora[runner_id]["cases"]:
            by_id.setdefault(entry["id"], []).append((runner_id, entry))

    shared: list[dict[str, Any]] = []
    runner_specific: dict[str, list[dict[str, Any]]] = {
        runner_id: [] for runner_id in sorted(corpora)
    }
    for case_id in sorted(by_id):
        entries = by_id[case_id]
        semantic_encodings = {
            reference.canonical_json(_case_semantics(entry)) for _, entry in entries
        }
        if len(entries) > 1 and len(semantic_encodings) == 1:
            semantics = _case_semantics(entries[0][1])
            shared.append(
                {
                    "case_id": case_id,
                    "case_identity": reference.canonical_fingerprint(
                        {
                            "cross_corpus_version": CROSS_CORPUS_VERSION,
                            "semantics": semantics,
                        }
                    ),
                    "operation": semantics["operation"],
                    "runners": sorted(runner_id for runner_id, _ in entries),
                }
            )
            continue
        for runner_id, entry in entries:
            runner_specific[runner_id].append(
                {
                    "case_id": case_id,
                    "case_identity": _runner_case_identity(
                        runner_id,
                        corpora[runner_id]["corpus_version"],
                        entry,
                    ),
                    "operation": entry["request"]["operation"],
                }
            )

    return shared, [
        {
            "cases": runner_specific[runner_id],
            "runner_id": runner_id,
        }
        for runner_id in sorted(runner_specific)
    ]


def certify_cross_runner(
    certifications: Mapping[str, Any],
    corpora: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if tuple(sorted(certifications)) != SELECTED_RUNNERS:
        raise CrossCertificationError(
            "certifications must contain exactly the selected runners"
        )
    if tuple(sorted(corpora)) != SELECTED_RUNNERS:
        raise CrossCertificationError(
            "corpora must contain exactly the selected runners"
        )

    validated = {
        runner_id: _validate_certification(
            copy.deepcopy(certifications[runner_id]),
            corpora[runner_id],
            runner_id,
        )
        for runner_id in SELECTED_RUNNERS
    }
    shared_cases, runner_specific_cases = derive_case_partitions(corpora)
    runner_records = []
    for runner_id in SELECTED_RUNNERS:
        certification = validated[runner_id]
        runner_records.append(
            {
                "case_count": len(corpora[runner_id]["cases"]),
                "corpus": certification["corpus"],
                "fixture_immutability": certification["fixture_immutability"],
                "implementation": certification["implementation"],
                "malformed_cases": certification["malformed_cases"],
                "operation_counts": certification["operation_counts"],
                "outcome_counts": certification["outcome_counts"],
                "repeatability": certification["repeatability"],
                "runner": certification["runner"],
                "unexplained_failures": certification["unexplained_failures"],
            }
        )

    runner_specific_count = sum(
        len(partition["cases"]) for partition in runner_specific_cases
    )
    total_runner_cases = sum(record["case_count"] for record in runner_records)
    cross_corpus_manifest = {
        "runner_corpora": [
            {
                "corpus": record["corpus"],
                "runner_id": record["runner"]["id"],
            }
            for record in runner_records
        ],
        "runner_specific_cases": runner_specific_cases,
        "shared_cases": shared_cases,
        "version": CROSS_CORPUS_VERSION,
    }
    return {
        "certification_kind": CROSS_CERTIFICATION_KIND,
        "certification_schema_version": CROSS_CERTIFICATION_SCHEMA_VERSION,
        "corpus": {
            "algorithm": "sha256",
            "fingerprint": reference.canonical_fingerprint(cross_corpus_manifest),
            "version": CROSS_CORPUS_VERSION,
        },
        "observation_schema_version": reference.OBSERVATION_SCHEMA_VERSION,
        "protocol_version": reference.PROTOCOL_VERSION,
        "runner_specific_cases": runner_specific_cases,
        "runners": runner_records,
        "shared_cases": shared_cases,
        "status": "passed",
        "totals": {
            "canonical_observations_compared": sum(
                record["repeatability"]["canonical_observations_compared"]
                for record in runner_records
            ),
            "malformed_cases": sum(
                record["malformed_cases"] for record in runner_records
            ),
            "repeat_mismatches": sum(
                record["repeatability"]["mismatches"] for record in runner_records
            ),
            "repeat_runs": sum(
                record["repeatability"]["repeat_runs"] for record in runner_records
            ),
            "runner_cases": total_runner_cases,
            "runner_specific_cases": runner_specific_count,
            "runners": len(runner_records),
            "shared_cases": len(shared_cases),
            "shared_runner_cases": sum(len(entry["runners"]) for entry in shared_cases),
            "unexplained_failures": sum(
                record["unexplained_failures"] for record in runner_records
            ),
        },
    }


def certify_selected_runners(
    typescript_certification: Mapping[str, Any],
    python_certification: Mapping[str, Any],
    *,
    typescript_corpus_path: Path = TYPESCRIPT_CORPUS_PATH,
    python_corpus_path: Path = PYTHON_CORPUS_PATH,
) -> dict[str, Any]:
    corpora = {
        "python": load_corpus(python_corpus_path),
        "typescript": load_corpus(typescript_corpus_path),
    }
    return certify_cross_runner(
        {
            "python": python_certification,
            "typescript": typescript_certification,
        },
        corpora,
    )


def serialize_certification(certification: Mapping[str, Any]) -> str:
    return reference.canonical_line(certification)
