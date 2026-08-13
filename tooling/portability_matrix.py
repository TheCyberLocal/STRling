#!/usr/bin/env python3
"""Derive the initial portability matrix from governed corpus evidence."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tooling import shared_cross_engine_corpus as shared
from tooling.contract_validation import load_json


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "governance" / "schemas" / "portability-matrix-evidence.schema.json"
)
MATRIX_PATH = (
    ROOT / "tests" / "conformance" / "evidence" / "initial-portability-matrix.json"
)
SUMMARY_PATH = (
    ROOT / "tests" / "conformance" / "evidence" / "initial-portability-matrix.md"
)
OPERATION_ID = "certification.initial-portability-matrix"
CHECK_ID = f"{OPERATION_ID}.complete-classified-denominator"
DISPOSITIONS = (
    "native",
    "planner_certified_equivalent_rewrite",
    "target_unsupported_or_constraint",
    "not_applicable",
    "target_profile_or_documentation_discrepancy",
    "harness_defect",
    "canonical_expectation_defect",
    "implementation_or_runtime_discrepancy",
    "unresolved",
)
BLOCKING_DISPOSITIONS = {
    "target_profile_or_documentation_discrepancy",
    "harness_defect",
    "canonical_expectation_defect",
    "implementation_or_runtime_discrepancy",
    "unresolved",
}
PROFILE_PATHS = {
    "profile:ecmascript/2024": "ecmascript-2024.json",
    "profile:pcre2/10.42": "pcre2-10.42.json",
    "profile:pcre2/10.43": "pcre2-10.43.json",
    "profile:python-re/3.11": "python-re-3.11.json",
    "profile:python-re/3.11-bytes": "python-re-3.11-bytes.json",
}


class PortabilityMatrixError(ValueError):
    """The derived matrix input or output is incomplete or inconsistent."""


def _empty_counts() -> dict[str, int]:
    return {category: 0 for category in DISPOSITIONS}


def _profile_document(profile_id: str) -> dict[str, Any]:
    try:
        filename = PROFILE_PATHS[profile_id]
    except KeyError as error:
        raise PortabilityMatrixError(f"unknown profile {profile_id}") from error
    value = load_json(shared.PROFILE_ROOT / filename)
    if not isinstance(value, dict):
        raise PortabilityMatrixError(f"{profile_id}: profile root must be an object")
    return value


def _runtime_identity(profile_id: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
    runtimes = evidence.get("runtimes")
    if not isinstance(runtimes, Mapping):
        raise PortabilityMatrixError("checked observations lack runtime identities")
    if profile_id == "profile:ecmascript/2024":
        engine = "node-v8"
        identity = runtimes.get("node")
        version = "22.23.2"
    elif profile_id.startswith("profile:pcre2/"):
        engine = "pcre2"
        version = profile_id.rsplit("/", 1)[1]
        pcre2 = runtimes.get("pcre2")
        identity = pcre2.get(version) if isinstance(pcre2, Mapping) else None
    else:
        engine = "cpython-re"
        identity = runtimes.get("python")
        version = "3.11.15"
    if not isinstance(identity, Mapping):
        raise PortabilityMatrixError(f"{profile_id}: runtime identity is missing")
    copied = dict(identity)
    return {
        "engine": engine,
        "version": version,
        "identity": copied,
        "sha256": shared.canonical_digest(copied),
    }


def _validate_runtime_denominator(evidence: Mapping[str, Any]) -> None:
    pcre2 = evidence.get("runtimes", {}).get("pcre2", {})
    for version, expected in shared.EXPECTED_PCRE2_LIBRARIES.items():
        actual = pcre2.get(version, {}) if isinstance(pcre2, Mapping) else {}
        if actual.get("library_sha256") != expected["sha256"]:
            raise PortabilityMatrixError(
                f"PCRE2 {version}: checked runtime fingerprint differs"
            )
    node = evidence.get("runtimes", {}).get("node", {})
    if not isinstance(node, Mapping) or any(
        (
            node.get("node") != shared.EXPECTED_NODE,
            node.get("v8") != shared.EXPECTED_V8,
            node.get("platform") != shared.EXPECTED_NODE_PLATFORM,
            node.get("architecture") != shared.EXPECTED_NODE_ARCHITECTURE,
            node.get("executable_sha256") != shared.EXPECTED_NODE_EXECUTABLE_SHA256,
        )
    ):
        raise PortabilityMatrixError("checked Node/V8 runtime identity differs")
    python = evidence.get("runtimes", {}).get("python", {})
    if not isinstance(python, Mapping) or any(
        (
            python.get("version") != shared.EXPECTED_VERSION,
            python.get("implementation") != shared.EXPECTED_IMPLEMENTATION,
            python.get("cache_tag") != shared.EXPECTED_CACHE_TAG,
            python.get("platform") != shared.EXPECTED_PLATFORM,
            python.get("machine") != shared.EXPECTED_MACHINE,
            python.get("soabi") != shared.EXPECTED_SOABI,
            python.get("sysconfig_platform") != shared.EXPECTED_SYSCONFIG_PLATFORM,
            python.get("executable_sha256") != shared.EXPECTED_PYTHON_EXECUTABLE_SHA256,
        )
    ):
        raise PortabilityMatrixError("checked CPython runtime identity differs")


def _application_map(
    validation: Mapping[str, Any], evidence: Mapping[str, Any]
) -> dict[tuple[str, str], Mapping[str, Any]]:
    expected_corpus = {
        "id": validation["corpus"]["corpus_id"],
        "sha256": validation["corpus_sha256"],
        "case_count": validation["case_count"],
        "application_counts": validation["application_counts"],
    }
    if evidence.get("corpus") != expected_corpus:
        raise PortabilityMatrixError("checked observation corpus identity is stale")
    unsigned = dict(evidence)
    claimed = unsigned.pop("result_sha256", None)
    if claimed != shared.canonical_digest(unsigned):
        raise PortabilityMatrixError("checked observation fingerprint differs")
    projection = evidence.get("projection_sha256")
    if not isinstance(projection, str) or len(projection) != 64:
        raise PortabilityMatrixError("checked projection fingerprint is missing")
    _validate_runtime_denominator(evidence)

    expected_pairs = []
    applications: dict[tuple[str, str], Mapping[str, Any]] = {}
    for vector in validation["corpus"]["vectors"]:
        for application in vector["applications"]:
            profile_id = application["target_profile"]["profile_id"]
            pair = (vector["case_id"], profile_id)
            expected_pairs.append(pair)
            applications[pair] = application
    observations = evidence.get("observations")
    if not isinstance(observations, list):
        raise PortabilityMatrixError("checked observations must be an array")
    actual_pairs = [
        (item.get("case_id"), item.get("profile_id"))
        for item in observations
        if isinstance(item, Mapping)
    ]
    if actual_pairs != expected_pairs or len(actual_pairs) != len(observations):
        raise PortabilityMatrixError(
            "checked observations do not preserve the exact ordered denominator"
        )
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for item in observations:
        pair = (item["case_id"], item["profile_id"])
        application = applications[pair]
        if item.get("state") != application["state"] or item.get(
            "portability_status"
        ) != application.get("portability_status"):
            raise PortabilityMatrixError(
                f"{pair[0]}/{pair[1]}: observation disposition differs from corpus"
            )
        executing = application["state"] == "execute"
        if executing != (item.get("raw") is not None) or executing != (
            item.get("normalized") is not None
        ):
            raise PortabilityMatrixError(
                f"{pair[0]}/{pair[1]}: runtime evidence presence differs from state"
            )
        result[pair] = item
    return result


def _expectation_agrees(
    case: Mapping[str, Any], normalized: Sequence[Mapping[str, Any]]
) -> tuple[bool, str]:
    matches = case["expectations"].get("matches")
    if not isinstance(matches, Mapping):
        return False, "executed case lacks an authored match expectation"
    authored = list(matches["positive"]) + list(matches["negative"])
    if len(authored) != len(normalized):
        return False, "subject observation count differs"
    positive_count = len(matches["positive"])
    for index, (expected, observed) in enumerate(zip(authored, normalized)):
        if not isinstance(observed, Mapping):
            return False, f"subject {index} normalized observation is malformed"
        should_match = index < positive_count
        span = observed.get("span")
        subject_bytes = expected["subject"].encode("utf-8")
        matched = span is not None and (
            matches["operation"] == "search" or span == [0, len(subject_bytes)]
        )
        if matched != should_match:
            return False, f"{expected['match_id']} match presence differs"
        if not matched:
            continue
        captures = observed.get("captures")
        if not isinstance(captures, Mapping):
            return False, f"{expected['match_id']} capture map is malformed"
        for capture in expected.get("captures", []):
            actual = captures.get(capture["capture_id"])
            if (
                not isinstance(actual, Mapping)
                or actual.get("matched") != capture["matched"]
            ):
                return False, f"{expected['match_id']} capture participation differs"
            if capture["matched"] and (
                actual.get("text") != capture["text"]
                or actual.get("subject_span")
                != [
                    capture["subject_span"]["start"],
                    capture["subject_span"]["end"],
                ]
            ):
                return False, f"{expected['match_id']} capture observation differs"
    return True, "exact normalized execution agrees with authored expectation"


def _classify(
    application: Mapping[str, Any],
    case: Mapping[str, Any],
    observation: Mapping[str, Any],
) -> tuple[str, str]:
    state = application["state"]
    if state == "not_applicable":
        return "not_applicable", application["reason"]
    if state == "unsupported":
        return "target_unsupported_or_constraint", application["reason"]
    normalized = observation.get("normalized")
    if not isinstance(normalized, list):
        return "unresolved", "executed entry lacks normalized observations"
    agrees, rationale = _expectation_agrees(case, normalized)
    if not agrees:
        return "unresolved", rationale
    portability_status = application.get("portability_status")
    if portability_status == "native":
        return "native", rationale
    if portability_status == "equivalent_rewrite":
        return "planner_certified_equivalent_rewrite", (
            "authored planner-certified equivalent rewrite and exact execution "
            "agree with the canonical expectation"
        )
    return "unresolved", "executed entry has no final portability disposition"


def _claim(counts: Mapping[str, int]) -> str:
    if any(counts[item] for item in BLOCKING_DISPOSITIONS):
        return "blocked"
    if counts["target_unsupported_or_constraint"]:
        return "unsupported_for_profile"
    if counts["planner_certified_equivalent_rewrite"]:
        return "portable_with_certified_rewrite"
    if counts["native"]:
        return "portable_native_for_applicable_vectors"
    return "not_applicable"


def _aggregate_rows(
    dimension: str,
    keys: Sequence[str],
    entries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    source_field = "features" if dimension == "feature" else "requirements"
    rows = []
    for key in keys:
        for profile_id in shared.EXPECTED_PROFILE_IDS:
            selected = [
                entry
                for entry in entries
                if key in entry[source_field]
                and entry["target_profile"]["profile_id"] == profile_id
            ]
            if not selected:
                raise PortabilityMatrixError(
                    f"{dimension} {key}/{profile_id}: aggregate denominator is empty"
                )
            counts = _empty_counts()
            for entry in selected:
                counts[entry["disposition"]["category"]] += 1
            rows.append(
                {
                    "dimension": dimension,
                    "key": key,
                    "target_profile": selected[0]["target_profile"],
                    "entry_ids": [entry["entry_id"] for entry in selected],
                    "disposition_counts": counts,
                    "claim": _claim(counts),
                }
            )
    return rows


def build_matrix(
    *,
    validation: Mapping[str, Any] | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validation or shared.validate_corpus()
    evidence = evidence or load_json(shared.EVIDENCE_PATH)
    observations = _application_map(validation, evidence)
    corpus = validation["corpus"]
    schema = load_json(SCHEMA_PATH)
    profile_metadata = {
        item["target_profile"]["profile_id"]: item for item in corpus["profiles"]
    }
    profiles = []
    for profile_id in shared.EXPECTED_PROFILE_IDS:
        corpus_profile = profile_metadata[profile_id]
        profile = _profile_document(profile_id)
        options = profile.get("options", [])
        profiles.append(
            {
                "target_profile": corpus_profile["target_profile"],
                "execution_adapter": corpus_profile["execution_adapter"],
                "subject_representation": corpus_profile["subject_representation"],
                "options": options,
                "options_sha256": shared.canonical_digest(options),
                "runtime": _runtime_identity(profile_id, evidence),
            }
        )
    profiles_by_id = {item["target_profile"]["profile_id"]: item for item in profiles}

    entries = []
    semantic_inputs: dict[str, list[tuple[str, Any]]] = {}
    for vector in corpus["vectors"]:
        case = load_json(ROOT / vector["path"])
        semantic_inputs[vector["case_id"]] = []
        for application in vector["applications"]:
            profile_id = application["target_profile"]["profile_id"]
            pair = (vector["case_id"], profile_id)
            observation = observations[pair]
            category, rationale = _classify(application, case, observation)
            normalized = observation.get("normalized")
            if normalized is not None:
                semantic_inputs[vector["case_id"]].append((profile_id, normalized))
            profile = profiles_by_id[profile_id]
            entries.append(
                {
                    "entry_id": f"{vector['case_id']}@{profile_id}",
                    "case": {
                        "case_id": vector["case_id"],
                        "path": vector["path"],
                        "sha256": vector["sha256"],
                    },
                    "features": vector["features"],
                    "requirements": vector["requirements"],
                    "rewrite_strategies": vector["rewrite_strategies"],
                    "modes": vector["modes"],
                    "target_profile": application["target_profile"],
                    "profile_options_sha256": profile["options_sha256"],
                    "application": {
                        "predicate": application["predicate"],
                        "state": application["state"],
                        "portability_status": application.get("portability_status"),
                        "reason": application["reason"],
                    },
                    "observation": (
                        {
                            "raw_sha256": shared.canonical_digest(observation["raw"]),
                            "normalized_sha256": shared.canonical_digest(normalized),
                        }
                        if normalized is not None
                        else None
                    ),
                    "disposition": {
                        "category": category,
                        "divergence": category not in {"native", "not_applicable"},
                        "blocking": category in BLOCKING_DISPOSITIONS,
                        "rationale": rationale,
                    },
                }
            )

    semantic_comparisons = []
    for case_id, values in semantic_inputs.items():
        classes: dict[str, list[str]] = {}
        for profile_id, normalized in values:
            classes.setdefault(shared.canonical_digest(normalized), []).append(
                profile_id
            )
        semantic_comparisons.append(
            {
                "case_id": case_id,
                "status": (
                    "not_compared"
                    if not classes
                    else "consistent"
                    if len(classes) == 1
                    else "divergent"
                ),
                "classes": [
                    {"sha256": digest, "profile_ids": classes[digest]}
                    for digest in sorted(classes)
                ],
            }
        )

    divergent_case_ids = {
        item["case_id"]
        for item in semantic_comparisons
        if item["status"] == "divergent"
    }
    for entry in entries:
        if (
            entry["case"]["case_id"] in divergent_case_ids
            and entry["application"]["state"] == "execute"
        ):
            entry["disposition"] = {
                "category": "unresolved",
                "divergence": True,
                "blocking": True,
                "rationale": (
                    "applicable exact profiles form more than one normalized "
                    "semantic result class"
                ),
            }

    counts = _empty_counts()
    for entry in entries:
        counts[entry["disposition"]["category"]] += 1
    for profile in profiles:
        profile_counts = _empty_counts()
        profile_id = profile["target_profile"]["profile_id"]
        for entry in entries:
            if entry["target_profile"]["profile_id"] == profile_id:
                profile_counts[entry["disposition"]["category"]] += 1
        profile["disposition_counts"] = profile_counts
        profile["claim"] = _claim(profile_counts)

    features = corpus["coverage"]["required_feature_tags"]
    requirements = corpus["coverage"]["required_requirement_tags"]
    feature_matrix = _aggregate_rows("feature", features, entries)
    requirement_matrix = _aggregate_rows("requirement", requirements, entries)
    divergences = [
        {
            "divergence_id": f"divergence:{entry['entry_id']}",
            "entry_id": entry["entry_id"],
            "case_id": entry["case"]["case_id"],
            "profile_id": entry["target_profile"]["profile_id"],
            "category": entry["disposition"]["category"],
            "blocking": entry["disposition"]["blocking"],
            "rationale": entry["disposition"]["rationale"],
        }
        for entry in entries
        if entry["disposition"]["divergence"]
    ]
    unresolved_count = sum(counts[item] for item in BLOCKING_DISPOSITIONS)
    divergent_cases = sum(
        item["status"] == "divergent" for item in semantic_comparisons
    )
    unsigned = {
        "matrix_version": "1.0.0",
        "schema": {
            "id": schema["$id"],
            "sha256": shared.canonical_digest(schema),
        },
        "authority": {
            "manifest": {
                "id": validation["manifest"]["manifest_id"],
                "status": validation["manifest"]["authority_status"],
                "sha256": shared.canonical_digest(validation["manifest"]),
            },
            "corpus": {
                "id": corpus["corpus_id"],
                "version": corpus["corpus_version"],
                "sha256": validation["corpus_sha256"],
                "case_set_sha256": validation["case_set_sha256"],
                "vector_set_sha256": validation["vector_set_sha256"],
                "case_count": validation["case_count"],
                "application_counts": validation["application_counts"],
            },
            "observations": {
                "version": evidence["evidence_version"],
                "sha256": evidence["result_sha256"],
                "projection_sha256": evidence["projection_sha256"],
            },
        },
        "profiles": profiles,
        "counts": {
            "entries": len(entries),
            "dispositions": counts,
            "representation_or_support_divergences": sum(
                counts[item]
                for item in (
                    "planner_certified_equivalent_rewrite",
                    "target_unsupported_or_constraint",
                )
            ),
            "semantic_divergent_cases": divergent_cases,
            "unresolved": unresolved_count,
        },
        "entries": entries,
        "semantic_comparisons": semantic_comparisons,
        "feature_matrix": feature_matrix,
        "requirement_matrix": requirement_matrix,
        "divergences": divergences,
        "readiness": {
            "status": (
                "ready" if unresolved_count == 0 and divergent_cases == 0 else "blocked"
            ),
            "rule": "canonical-expectation-plus-every-applicable-exact-profile",
        },
    }
    return {**unsigned, "result_sha256": shared.canonical_digest(unsigned)}


def validate_matrix(matrix: Mapping[str, Any], *, require_ready: bool = True) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(matrix),
        key=lambda item: list(item.path),
    )
    if errors:
        error = errors[0]
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.path
        )
        raise PortabilityMatrixError(f"matrix schema {location}: {error.message}")
    unsigned = dict(matrix)
    claimed = unsigned.pop("result_sha256")
    if claimed != shared.canonical_digest(unsigned):
        raise PortabilityMatrixError("matrix result fingerprint differs")
    if matrix["counts"]["entries"] != 100 or len(matrix["entries"]) != 100:
        raise PortabilityMatrixError("matrix denominator must contain 100 entries")
    entry_ids = [item["entry_id"] for item in matrix["entries"]]
    if entry_ids != sorted(set(entry_ids)):
        raise PortabilityMatrixError("matrix entries must have unique canonical order")
    if require_ready and matrix["readiness"]["status"] != "ready":
        raise PortabilityMatrixError(
            "portability matrix has unresolved or divergent semantic evidence"
        )


def _table_cell(row: Mapping[str, Any]) -> str:
    counts = row["disposition_counts"]
    return (
        f"{row['claim']} "
        f"({counts['native']}/{counts['planner_certified_equivalent_rewrite']}/"
        f"{counts['target_unsupported_or_constraint']}/"
        f"{counts['not_applicable']}/{counts['unresolved']})"
    )


def render_markdown(matrix: Mapping[str, Any]) -> str:
    counts = matrix["counts"]
    lines = [
        "# Initial cross-engine portability matrix",
        "",
        "> Generated from the machine-authoritative matrix JSON. Do not edit by hand.",
        "",
        f"- Matrix SHA-256: `{matrix['result_sha256']}`",
        f"- Corpus SHA-256: `{matrix['authority']['corpus']['sha256']}`",
        f"- Observation SHA-256: `{matrix['authority']['observations']['sha256']}`",
        f"- Readiness: `{matrix['readiness']['status']}`",
        "",
        "## Disposition totals",
        "",
        "| Disposition | Count |",
        "| --- | ---: |",
    ]
    for category in DISPOSITIONS:
        lines.append(f"| `{category}` | {counts['dispositions'][category]} |")
    lines.extend(
        [
            "",
            "The compact aggregate cells below are ordered as "
            "`native/rewrite/unsupported/not-applicable/unresolved`.",
            "",
            "## Exact profiles",
            "",
            "| Profile | Revision | Runtime | Claim | Counts |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for profile in matrix["profiles"]:
        reference = profile["target_profile"]
        runtime = profile["runtime"]
        row_counts = profile["disposition_counts"]
        compact = (
            f"{row_counts['native']}/"
            f"{row_counts['planner_certified_equivalent_rewrite']}/"
            f"{row_counts['target_unsupported_or_constraint']}/"
            f"{row_counts['not_applicable']}/{row_counts['unresolved']}"
        )
        lines.append(
            f"| `{reference['profile_id']}` | `{reference['profile_version']}` | "
            f"`{runtime['engine']} {runtime['version']}` | `{profile['claim']}` | "
            f"`{compact}` |"
        )
    lines.extend(
        [
            "",
            "## Classified divergences",
            "",
            "| Case | Profile | Classification | Blocking |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in matrix["divergences"]:
        lines.append(
            f"| `{item['case_id']}` | `{item['profile_id']}` | "
            f"`{item['category']}` | {'yes' if item['blocking'] else 'no'} |"
        )

    profile_ids = list(shared.EXPECTED_PROFILE_IDS)
    for title, rows in (
        ("Feature matrix", matrix["feature_matrix"]),
        ("Requirement matrix", matrix["requirement_matrix"]),
    ):
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Key | " + " | ".join(profile_ids) + " |",
                "| --- | " + " | ".join("---" for _ in profile_ids) + " |",
            ]
        )
        by_key: dict[str, dict[str, Mapping[str, Any]]] = {}
        for row in rows:
            by_key.setdefault(row["key"], {})[row["target_profile"]["profile_id"]] = row
        for key in sorted(by_key):
            cells = [_table_cell(by_key[key][profile_id]) for profile_id in profile_ids]
            lines.append(f"| `{key}` | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def _serialize_outputs(matrix: Mapping[str, Any]) -> tuple[str, str]:
    return json.dumps(matrix, ensure_ascii=False, indent=4) + "\n", render_markdown(
        matrix
    )


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": dict(details)}],
    }


def certify(*, check: bool, write: bool) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    try:
        matrix = build_matrix()
        validate_matrix(matrix)
        matrix_text, summary_text = _serialize_outputs(matrix)
        if check and (
            not MATRIX_PATH.is_file()
            or MATRIX_PATH.read_text(encoding="utf-8") != matrix_text
            or not SUMMARY_PATH.is_file()
            or SUMMARY_PATH.read_text(encoding="utf-8") != summary_text
        ):
            raise PortabilityMatrixError("checked matrix outputs are stale")
        if write:
            MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
            MATRIX_PATH.write_text(matrix_text, encoding="utf-8")
            SUMMARY_PATH.write_text(summary_text, encoding="utf-8")
        details = {
            "entries": matrix["counts"]["entries"],
            "dispositions": matrix["counts"]["dispositions"],
            "representation_or_support_divergences": matrix["counts"][
                "representation_or_support_divergences"
            ],
            "semantic_divergent_cases": matrix["counts"]["semantic_divergent_cases"],
            "unresolved": matrix["counts"]["unresolved"],
            "matrix_sha256": matrix["result_sha256"],
        }
        return _result("passed", started, details), 0
    except Exception as error:
        return _result(
            "failed",
            started,
            {"error_type": type(error).__name__, "reason": str(error)},
        ), 1


def verify_evidence() -> dict[str, Any]:
    matrix = build_matrix()
    validate_matrix(matrix)
    matrix_text, summary_text = _serialize_outputs(matrix)
    if MATRIX_PATH.read_text(encoding="utf-8") != matrix_text:
        raise PortabilityMatrixError("checked matrix JSON differs")
    if SUMMARY_PATH.read_text(encoding="utf-8") != summary_text:
        raise PortabilityMatrixError("checked matrix Markdown differs")
    return {
        "entries": matrix["counts"]["entries"],
        "result_sha256": matrix["result_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify-evidence", action="store_true")
    args = parser.parse_args()
    if args.check and args.write:
        parser.error("--check and --write are mutually exclusive")
    if args.verify_evidence:
        payload = verify_evidence()
        print(
            json.dumps(payload, sort_keys=True)
            if args.json
            else f"PORTABILITY_MATRIX_EVIDENCE status=passed sha256={payload['result_sha256']}"
        )
        return 0
    result, code = certify(check=args.check, write=args.write)
    print(
        json.dumps(result, sort_keys=True)
        if args.json
        else f"PORTABILITY_MATRIX_CERTIFICATION status={result['status']}"
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
