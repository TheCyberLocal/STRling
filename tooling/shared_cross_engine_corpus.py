#!/usr/bin/env python3
"""Validate and execute the specification-authored shared engine corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tooling.contract_validation import (
    ContractSuite,
    canonical_json,
    load_json,
)
from tooling.ecmascript_runtime_certification import (
    EXPECTED_ARCHITECTURE as EXPECTED_NODE_ARCHITECTURE,
    EXPECTED_EXECUTABLE_SHA256 as EXPECTED_NODE_EXECUTABLE_SHA256,
    EXPECTED_NODE,
    EXPECTED_PLATFORM as EXPECTED_NODE_PLATFORM,
    EXPECTED_V8,
    NODE_ENV,
    run_harness as run_node_harness,
)
from tooling.exact_runtime_toolchains import artifact_sha256
from tooling.pcre2_feature_probe import (
    Engine,
    MatchLimits,
    file_digest,
    profile_configuration,
)
from tooling.pcre2_runtime_certification import LIBRARY_ENV as PCRE2_ENVIRONMENTS
from tooling.python_re_runtime_certification import (
    EXPECTED_CACHE_TAG,
    EXPECTED_EXECUTABLE_SHA256 as EXPECTED_PYTHON_EXECUTABLE_SHA256,
    EXPECTED_IMPLEMENTATION,
    EXPECTED_MACHINE,
    EXPECTED_PLATFORM,
    EXPECTED_SOABI,
    EXPECTED_SYSCONFIG_PLATFORM,
    EXPECTED_VERSION,
    PYTHON_ENV,
    run_harness as run_python_harness,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "spec" / "conformance" / "shared-corpus-v1.json"
SCHEMA_PATH = ROOT / "spec" / "conformance" / "shared-corpus-v1.schema.json"
MANIFEST_PATH = ROOT / "spec" / "conformance" / "manifest.json"
PROFILE_ROOT = ROOT / "spec" / "targets" / "profiles"
EQUIVALENCE_REGISTRY = (
    ROOT / "spec" / "portability" / "equivalence" / "1.0" / "registry.json"
)
EVIDENCE_PATH = (
    ROOT
    / "tests"
    / "conformance"
    / "evidence"
    / "shared-cross-engine-observations.json"
)
PROJECTION_COMMAND = [
    "cargo",
    "run",
    "--manifest-path",
    "core/internal/Cargo.toml",
    "--example",
    "shared_conformance_projection",
    "--locked",
    "--quiet",
]
PROJECTION_TIMEOUT_SECONDS = 600
OPERATION_ID = "certification.shared-cross-engine-corpus"
CHECK_ID = f"{OPERATION_ID}.five-profile-denominator"
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2, "incomplete": 3}
EXPECTED_PROFILE_IDS = (
    "profile:ecmascript/2024",
    "profile:pcre2/10.42",
    "profile:pcre2/10.43",
    "profile:python-re/3.11",
    "profile:python-re/3.11-bytes",
)
EXPECTED_PCRE2_LIBRARIES = {
    "10.42": {"sha256": artifact_sha256("pcre2-10.42")},
    "10.43": {"sha256": artifact_sha256("pcre2-10.43")},
}
MINIMUM_CASE_COUNT = 20
REQUIRED_FEATURE_TAGS = (
    "alternation",
    "anchors.input",
    "anchors.line",
    "assertions.lookahead",
    "assertions.lookbehind.fixed",
    "assertions.lookbehind.variable",
    "backreference",
    "boundary.word",
    "capture.logical",
    "character_class.ascii",
    "character_class.negated",
    "character_class.unicode",
    "diagnostic.malformed",
    "literal",
    "repeat.greedy",
    "repeat.lazy",
    "repeat.possessive",
    "rewrite.atomic_literal_elision",
    "sequence",
    "unicode.case_insensitive",
    "wildcard.include_line_terminators",
)
FORBIDDEN_EXPECTATION_KEYS = {
    "artifact",
    "emitted_pattern",
    "majority",
    "observed_result",
    "pattern",
    "peer_result",
    "raw_observation",
    "runtime_result",
    "target_pattern",
}


class SharedCorpusError(ValueError):
    """The governed shared corpus is malformed or incomplete."""


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _profile_path(profile_id: str) -> Path:
    names = {
        "profile:ecmascript/2024": "ecmascript-2024.json",
        "profile:pcre2/10.42": "pcre2-10.42.json",
        "profile:pcre2/10.43": "pcre2-10.43.json",
        "profile:python-re/3.11": "python-re-3.11.json",
        "profile:python-re/3.11-bytes": "python-re-3.11-bytes.json",
    }
    return PROFILE_ROOT / names[profile_id]


def _walk_keys(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            found.append(str(key))
            found.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_keys(child))
    return found


def _require_sorted_unique(values: Sequence[str], label: str) -> None:
    if list(values) != sorted(set(values)):
        raise SharedCorpusError(f"{label} must be unique and sorted")


def _target_map(case: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        item["target_profile"]["profile_id"]: item
        for item in case["expectations"].get("targets", [])
    }


def _vector_identity(vector: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "case_id": vector["case_id"],
        "features": vector["features"],
        "requirements": vector["requirements"],
        "rewrite_strategies": vector["rewrite_strategies"],
        "applications": vector["applications"],
    }


def refresh_authority_identities() -> None:
    """Rotate derived case/profile identities without changing expectations."""
    corpus = load_json(CORPUS_PATH)
    manifest = load_json(MANIFEST_PATH)
    manifest_by_id = {entry["case_id"]: entry for entry in manifest["cases"]}
    profile_refs: dict[str, dict[str, str]] = {}
    for profile_id in EXPECTED_PROFILE_IDS:
        profile = load_json(_profile_path(profile_id))
        profile_refs[profile_id] = {
            "profile_id": profile_id,
            "profile_version": profile["profile_version"],
            "sha256": canonical_digest(profile),
        }

    profiles_by_id = {
        item["target_profile"]["profile_id"]: item for item in corpus["profiles"]
    }
    if set(profiles_by_id) != set(EXPECTED_PROFILE_IDS):
        raise SharedCorpusError("cannot refresh an incomplete profile denominator")
    for profile_id in EXPECTED_PROFILE_IDS:
        profiles_by_id[profile_id]["target_profile"] = profile_refs[profile_id]

    for vector in corpus["vectors"]:
        entry = manifest_by_id.get(vector["case_id"])
        if entry is None or vector["path"] != entry["path"]:
            raise SharedCorpusError(
                f"{vector['case_id']}: cannot refresh a non-authoritative vector"
            )
        vector["sha256"] = entry["sha256"]
        application_ids = [
            item["target_profile"]["profile_id"] for item in vector["applications"]
        ]
        if application_ids != list(EXPECTED_PROFILE_IDS):
            raise SharedCorpusError(
                f"{vector['case_id']}: cannot refresh an incomplete application denominator"
            )
        for application in vector["applications"]:
            profile_id = application["target_profile"]["profile_id"]
            application["target_profile"] = profile_refs[profile_id]

    case_set = [
        {
            "case_id": vector["case_id"],
            "path": vector["path"],
            "sha256": vector["sha256"],
        }
        for vector in corpus["vectors"]
    ]
    corpus["coverage"]["case_set_sha256"] = canonical_digest(case_set)
    corpus["coverage"]["vector_set_sha256"] = canonical_digest(
        [_vector_identity(vector) for vector in corpus["vectors"]]
    )
    CORPUS_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    validate_corpus()


def validate_corpus() -> dict[str, Any]:
    """Validate schema, authority, applicability, coverage, and shrinkage guards."""

    corpus = load_json(CORPUS_PATH)
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(corpus),
        key=lambda item: list(item.path),
    )
    if errors:
        error = errors[0]
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.path
        )
        raise SharedCorpusError(f"shared corpus schema {location}: {error.message}")

    manifest = load_json(MANIFEST_PATH)
    ContractSuite().validate("conformance-manifest.schema.json", manifest)
    if corpus["authority"] != {
        "manifest_id": manifest["manifest_id"],
        "status": manifest["authority_status"],
        "expectation_source": "specification",
    }:
        raise SharedCorpusError(
            "corpus authority must resolve exactly to the specification manifest"
        )

    profiles = corpus["profiles"]
    profile_ids = [item["target_profile"]["profile_id"] for item in profiles]
    if profile_ids != list(EXPECTED_PROFILE_IDS):
        raise SharedCorpusError("corpus profile denominator or canonical order changed")
    profile_refs: dict[str, Mapping[str, Any]] = {}
    for item in profiles:
        reference = item["target_profile"]
        profile_id = reference["profile_id"]
        profile = load_json(_profile_path(profile_id))
        expected = {
            "profile_id": profile["profile_id"],
            "profile_version": profile["profile_version"],
            "sha256": canonical_digest(profile),
        }
        if reference != expected:
            raise SharedCorpusError(f"{profile_id}: corpus profile reference is stale")
        profile_refs[profile_id] = reference

    vectors = corpus["vectors"]
    case_ids = [vector["case_id"] for vector in vectors]
    if case_ids != sorted(set(case_ids)):
        raise SharedCorpusError("corpus vectors must have unique sorted case IDs")
    if len(vectors) < MINIMUM_CASE_COUNT:
        raise SharedCorpusError(
            f"corpus cannot shrink below {MINIMUM_CASE_COUNT} cases"
        )
    manifest_by_id = {entry["case_id"]: entry for entry in manifest["cases"]}
    if set(case_ids) != set(manifest_by_id):
        raise SharedCorpusError(
            "corpus must reference every and only manifest-owned case"
        )

    feature_union: set[str] = set()
    requirement_union: set[str] = set()
    rewrite_union: set[str] = set()
    state_union: set[str] = set()
    counts = {"execute": 0, "unsupported": 0, "not_applicable": 0}
    case_set = []
    for vector in vectors:
        case_id = vector["case_id"]
        entry = manifest_by_id[case_id]
        if vector["path"] != entry["path"] or vector["sha256"] != entry["sha256"]:
            raise SharedCorpusError(
                f"{case_id}: vector identity differs from manifest authority"
            )
        case = load_json(ROOT / vector["path"])
        if canonical_digest(case) != vector["sha256"] or case["case_id"] != case_id:
            raise SharedCorpusError(
                f"{case_id}: case bytes or identity differ from vector"
            )
        if vector["input_kind"] != case["input"]["kind"]:
            raise SharedCorpusError(f"{case_id}: input kind differs from case")
        for field in (
            "features",
            "requirements",
            "rewrite_strategies",
            "evidence_refs",
        ):
            _require_sorted_unique(vector[field], f"{case_id}.{field}")
        if FORBIDDEN_EXPECTATION_KEYS.intersection(_walk_keys(vector)):
            raise SharedCorpusError(
                f"{case_id}: corpus vector contains target/runtime-derived expectation data"
            )
        feature_union.update(vector["features"])
        requirement_union.update(vector["requirements"])
        rewrite_union.update(vector["rewrite_strategies"])

        matches = case["expectations"].get("matches")
        semantic = case["input"].get("program")
        expected_modes = {
            "case_matching": semantic["case_matching"]
            if semantic
            else "not_applicable",
            "operation": matches["operation"] if matches else "diagnostic",
        }
        if vector["modes"] != expected_modes:
            raise SharedCorpusError(
                f"{case_id}: modes do not derive from the authored case"
            )

        applications = vector["applications"]
        application_ids = [
            item["target_profile"]["profile_id"] for item in applications
        ]
        if application_ids != list(EXPECTED_PROFILE_IDS):
            raise SharedCorpusError(
                f"{case_id}: applications must cover the exact five-profile denominator"
            )
        targets = _target_map(case)
        for application in applications:
            profile_id = application["target_profile"]["profile_id"]
            state = application["state"]
            state_union.add(state)
            counts[state] += 1
            if application["target_profile"] != profile_refs[profile_id]:
                raise SharedCorpusError(
                    f"{case_id}/{profile_id}: application profile reference is stale"
                )
            target = targets.get(profile_id)
            if state == "not_applicable":
                if target is not None:
                    raise SharedCorpusError(
                        f"{case_id}/{profile_id}: not-applicable profile cannot have a target expectation"
                    )
                continue
            if target is None:
                raise SharedCorpusError(
                    f"{case_id}/{profile_id}: executable/support case lacks a target expectation"
                )
            if target["target_profile"] != application["target_profile"]:
                raise SharedCorpusError(
                    f"{case_id}/{profile_id}: case and corpus profile references differ"
                )
            if target["status"] != application["portability_status"]:
                raise SharedCorpusError(
                    f"{case_id}/{profile_id}: portability expectation differs"
                )
            if state == "unsupported" and target["status"] != "unsupported":
                raise SharedCorpusError(
                    f"{case_id}/{profile_id}: unsupported state requires unsupported plan"
                )
            if state == "execute" and target["status"] not in {
                "native",
                "equivalent_rewrite",
            }:
                raise SharedCorpusError(
                    f"{case_id}/{profile_id}: execute state requires representable plan"
                )
            if state == "execute" and matches is None:
                raise SharedCorpusError(
                    f"{case_id}/{profile_id}: runtime execution requires authored match expectations"
                )
            if state == "execute" and profile_id.endswith("-bytes"):
                subjects = [
                    item["subject"]
                    for item in matches["positive"] + matches["negative"]
                ]
                if any(not subject.isascii() for subject in subjects):
                    raise SharedCorpusError(
                        f"{case_id}/{profile_id}: bytes execution requires ASCII subjects"
                    )
        case_set.append(
            {"case_id": case_id, "path": vector["path"], "sha256": vector["sha256"]}
        )

    coverage = corpus["coverage"]
    for key in (
        "required_feature_tags",
        "required_requirement_tags",
        "required_rewrite_strategies",
        "required_application_states",
    ):
        _require_sorted_unique(coverage[key], f"coverage.{key}")
    if set(REQUIRED_FEATURE_TAGS) - feature_union:
        missing = sorted(set(REQUIRED_FEATURE_TAGS) - feature_union)
        raise SharedCorpusError(
            f"required feature coverage is missing: {', '.join(missing)}"
        )
    if coverage["required_feature_tags"] != sorted(feature_union):
        raise SharedCorpusError(
            "coverage feature denominator must equal vector coverage"
        )
    if coverage["required_requirement_tags"] != sorted(requirement_union):
        raise SharedCorpusError(
            "coverage requirement denominator must equal vector coverage"
        )
    registry = load_json(EQUIVALENCE_REGISTRY)
    registry_strategies = sorted(
        item["strategy_id"]
        for item in registry["strategies"]
        if item["application_kind"] == "mandatory_portability"
    )
    if (
        coverage["required_rewrite_strategies"] != registry_strategies
        or sorted(rewrite_union) != registry_strategies
    ):
        raise SharedCorpusError(
            "every mandatory portability rewrite strategy must have shared-corpus evidence"
        )
    if coverage["required_application_states"] != sorted(state_union):
        raise SharedCorpusError(
            "coverage application states must equal observed states"
        )
    if coverage["expected_case_count"] != len(vectors):
        raise SharedCorpusError("anti-shrinkage case count differs from vectors")
    if coverage["expected_application_counts"] != counts:
        raise SharedCorpusError("anti-shrinkage application counts differ from vectors")
    if coverage["case_set_sha256"] != canonical_digest(case_set):
        raise SharedCorpusError("anti-shrinkage case-set fingerprint differs")
    if coverage["vector_set_sha256"] != canonical_digest(
        [_vector_identity(vector) for vector in vectors]
    ):
        raise SharedCorpusError("anti-shrinkage vector-set fingerprint differs")
    for strategy in registry_strategies:
        supporting = [
            vector for vector in vectors if strategy in vector["rewrite_strategies"]
        ]
        if len(supporting) != 1:
            raise SharedCorpusError(
                f"{strategy}: expected exactly one governing vector"
            )
        vector = supporting[0]
        case = load_json(ROOT / vector["path"])
        matches = case["expectations"]["matches"]
        if not matches["positive"] or not matches["negative"]:
            raise SharedCorpusError(
                f"{strategy}: rewrite evidence needs positive and negative subjects"
            )
        if not any(
            app.get("portability_status") == "equivalent_rewrite"
            for app in vector["applications"]
        ):
            raise SharedCorpusError(
                f"{strategy}: rewrite evidence needs an exact equivalent-rewrite execution"
            )

    return {
        "corpus": corpus,
        "manifest": manifest,
        "case_count": len(vectors),
        "application_counts": counts,
        "corpus_sha256": canonical_digest(corpus),
        "case_set_sha256": coverage["case_set_sha256"],
        "vector_set_sha256": coverage["vector_set_sha256"],
    }


def _projection_environment() -> dict[str, str]:
    environment = {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "PATH": os.environ.get("PATH", ""),
    }
    if os.name == "nt":
        for name in ("INCLUDE", "LIB", "LIBPATH", "SYSTEMROOT", "TEMP", "TMP"):
            if value := os.environ.get(name):
                environment[name] = value
    return environment


def run_projection() -> dict[str, Any]:
    completed = subprocess.run(
        PROJECTION_COMMAND,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=PROJECTION_TIMEOUT_SECONDS,
        check=False,
        env=_projection_environment(),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"shared projection failed with code {completed.returncode}: {completed.stderr[-1000:]}"
        )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("shared projection root must be an object")
    return value


def _subjects(case: Mapping[str, Any]) -> list[str]:
    matches = case["expectations"]["matches"]
    return [item["subject"] for item in matches["positive"] + matches["negative"]]


def _utf16_to_utf8(subject: str, offset: int) -> int:
    encoded = subject.encode("utf-16-le")
    prefix = encoded[: offset * 2].decode("utf-16-le")
    return len(prefix.encode("utf-8"))


def _scalar_to_utf8(subject: str, offset: int) -> int:
    return len(subject[:offset].encode("utf-8"))


def _normalize_match(
    match: Mapping[str, Any],
    subject: str,
    capture_slots: Mapping[int, str],
    coordinate: str,
    *,
    bytes_pattern: bool = False,
) -> dict[str, Any]:
    def convert(offset: int) -> int:
        if bytes_pattern or coordinate == "utf8-bytes":
            return offset
        if coordinate == "utf16-code-units":
            return _utf16_to_utf8(subject, offset)
        return _scalar_to_utf8(subject, offset)

    span = match.get("span")
    normalized_span = None if span is None else [convert(span[0]), convert(span[1])]
    captures: dict[str, Any] = {}
    for item in match.get("captures", []):
        capture_id = capture_slots.get(item["index"])
        if capture_id is None:
            continue
        raw_span = item.get("span")
        value = item.get("value")
        if bytes_pattern and value is not None:
            value = bytes.fromhex(value).decode("ascii")
        captures[capture_id] = {
            "matched": raw_span is not None,
            **(
                {
                    "text": value,
                    "subject_span": [convert(raw_span[0]), convert(raw_span[1])],
                }
                if raw_span is not None
                else {}
            ),
        }
    return {"span": normalized_span, "captures": captures}


def _expected_subjects(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    matches = case["expectations"]["matches"]
    values = []
    for item in matches["positive"]:
        values.append(
            {
                "match_id": item["match_id"],
                "subject": item["subject"],
                "expected": "match",
                "captures": item["captures"],
            }
        )
    for item in matches["negative"]:
        values.append(
            {
                "match_id": item["match_id"],
                "subject": item["subject"],
                "expected": "no_match",
                "captures": [],
            }
        )
    return values


def _compare_case(
    case: Mapping[str, Any], normalized: Sequence[Mapping[str, Any]]
) -> None:
    operation = case["expectations"]["matches"]["operation"]
    expected = _expected_subjects(case)
    if len(expected) != len(normalized):
        raise AssertionError(f"{case['case_id']}: subject observation count differs")
    for authored, observed in zip(expected, normalized):
        subject_bytes = authored["subject"].encode("utf-8")
        span = observed.get("span")
        matched = span is not None and (
            operation == "search" or span == [0, len(subject_bytes)]
        )
        if matched != (authored["expected"] == "match"):
            raise AssertionError(
                f"{case['case_id']}/{authored['match_id']}: match presence differs"
            )
        if not matched:
            continue
        actual_captures = observed["captures"]
        for expectation in authored["captures"]:
            actual = actual_captures.get(expectation["capture_id"])
            if actual is None or actual["matched"] != expectation["matched"]:
                raise AssertionError(
                    f"{case['case_id']}/{authored['match_id']}: capture participation differs"
                )
            if expectation["matched"] and (
                actual["text"] != expectation["text"]
                or actual["subject_span"]
                != [
                    expectation["subject_span"]["start"],
                    expectation["subject_span"]["end"],
                ]
            ):
                raise AssertionError(
                    f"{case['case_id']}/{authored['match_id']}: capture observation differs"
                )


def _runtime_paths() -> tuple[dict[str, Path], Path, Path]:
    pcre = {}
    for version, env_name in PCRE2_ENVIRONMENTS.items():
        raw = os.environ.get(env_name)
        if not raw:
            raise FileNotFoundError(f"{env_name} is not configured")
        pcre[version] = Path(raw).resolve()
    node_raw = os.environ.get(NODE_ENV)
    python_raw = os.environ.get(PYTHON_ENV)
    if not node_raw or not python_raw:
        raise FileNotFoundError(f"{NODE_ENV} and {PYTHON_ENV} must be configured")
    return pcre, Path(node_raw).resolve(), Path(python_raw).resolve()


def execute_once(projection: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_corpus()
    corpus = validation["corpus"]
    pcre_paths, node_binary, python_binary = _runtime_paths()
    if (
        hashlib.sha256(node_binary.read_bytes()).hexdigest()
        != EXPECTED_NODE_EXECUTABLE_SHA256
    ):
        raise ValueError("Node executable fingerprint differs from the governed pin")
    if (
        hashlib.sha256(python_binary.read_bytes()).hexdigest()
        != EXPECTED_PYTHON_EXECUTABLE_SHA256
    ):
        raise ValueError("CPython executable fingerprint differs from the governed pin")

    projected_by_case = {item["case_id"]: item for item in projection["vectors"]}
    observations = []
    node_cases = []
    node_meta = []
    python_cases = []
    python_meta = []
    pcre_jobs = []
    for vector in corpus["vectors"]:
        case = load_json(ROOT / vector["path"])
        projected = {
            item["profile_id"]: item
            for item in projected_by_case[vector["case_id"]]["applications"]
        }
        for application in vector["applications"]:
            profile_id = application["target_profile"]["profile_id"]
            product = projected[profile_id]
            base = {
                "case_id": vector["case_id"],
                "profile_id": profile_id,
                "state": application["state"],
                "portability_status": application.get("portability_status"),
            }
            if application["state"] != "execute":
                observations.append({**base, "raw": None, "normalized": None})
                continue
            artifact = product["artifact"]
            captures = {
                item["slot"]: item["capture_id"] for item in product["captures"]
            }
            subjects = _subjects(case)
            request_id = f"{vector['case_id']}@{profile_id}"
            if profile_id.startswith("profile:ecmascript/"):
                node_cases.append(
                    {
                        "id": request_id,
                        "source": artifact["pattern"]["text"],
                        "flags": artifact["pattern"].get("flags", []),
                        "capture_names": {
                            str(slot): capture_id
                            for slot, capture_id in captures.items()
                        },
                        "subjects": subjects,
                    }
                )
                node_meta.append((base, case, captures))
            elif profile_id.startswith("profile:python-re/"):
                pattern_kind = product["pattern_kind"]
                encoded_subjects = (
                    [subject.encode("ascii").hex() for subject in subjects]
                    if pattern_kind == "bytes"
                    else subjects
                )
                python_cases.append(
                    {
                        "id": request_id,
                        "source": artifact["pattern"]["text"],
                        "pattern_kind": pattern_kind,
                        "flags": artifact["pattern"].get("flags", []),
                        "subjects": encoded_subjects,
                    }
                )
                python_meta.append((base, case, captures, pattern_kind))
            else:
                version = profile_id.rsplit("/", 1)[1]
                pcre_jobs.append(
                    (base, case, captures, version, artifact["pattern"]["text"])
                )

    node_request = {"protocol_version": "1.0.0", "cases": node_cases}
    node_response = run_node_harness(node_binary, node_request)
    node_runtime = node_response.get("runtime")
    if node_runtime != {
        "node": EXPECTED_NODE,
        "v8": EXPECTED_V8,
        "platform": EXPECTED_NODE_PLATFORM,
        "architecture": EXPECTED_NODE_ARCHITECTURE,
    }:
        raise ValueError("Node runtime identity differs from the governed pin")
    for (base, case, captures), raw in zip(node_meta, node_response["cases"]):
        normalized = []
        for subject, item in zip(_subjects(case), raw["observations"]):
            match = (
                item["matches"][0]
                if item["matches"]
                else {"span": None, "captures": []}
            )
            normalized.append(
                _normalize_match(match, subject, captures, "utf16-code-units")
            )
        _compare_case(case, normalized)
        observations.append({**base, "raw": raw, "normalized": normalized})

    python_request = {"protocol_version": "1.0.0", "cases": python_cases}
    python_response = run_python_harness(python_binary, python_request)
    python_runtime = python_response.get("runtime")
    if python_runtime != {
        "version": EXPECTED_VERSION,
        "implementation": EXPECTED_IMPLEMENTATION,
        "platform": EXPECTED_PLATFORM,
        "machine": EXPECTED_MACHINE,
        "cache_tag": EXPECTED_CACHE_TAG,
        "soabi": EXPECTED_SOABI,
        "sysconfig_platform": EXPECTED_SYSCONFIG_PLATFORM,
    }:
        raise ValueError("CPython runtime identity differs from the governed pin")
    for (base, case, captures, pattern_kind), raw in zip(
        python_meta, python_response["cases"]
    ):
        normalized = []
        for subject, item in zip(_subjects(case), raw["observations"]):
            match = (
                item["matches"][0]
                if item["matches"]
                else {"span": None, "captures": []}
            )
            normalized.append(
                _normalize_match(
                    match,
                    subject,
                    captures,
                    "code-points",
                    bytes_pattern=pattern_kind == "bytes",
                )
            )
        _compare_case(case, normalized)
        observations.append({**base, "raw": raw, "normalized": normalized})

    limits = MatchLimits(match=100_000, depth=10_000, heap_kib=64 * 1024)
    pcre_runtime = {}
    for base, case, captures, version, pattern in pcre_jobs:
        library = pcre_paths[version]
        expected_library = EXPECTED_PCRE2_LIBRARIES[version]
        if file_digest(library) != expected_library["sha256"]:
            raise ValueError(
                f"PCRE2 {version} library fingerprint differs from the governed pin"
            )
        engine = Engine(library)
        if engine.version().split()[0] != version:
            raise ValueError(f"PCRE2 {version} runtime identity differs")
        profile = load_json(_profile_path(f"profile:pcre2/{version}"))
        raw = engine.run_detailed_case(
            pattern,
            [{"subject": subject} for subject in _subjects(case)],
            profile_configuration(profile),
            limits,
        )
        normalized = []
        for subject, item in zip(_subjects(case), raw["matches"]):
            normalized.append(_normalize_match(item, subject, captures, "utf8-bytes"))
        _compare_case(case, normalized)
        observations.append({**base, "raw": raw, "normalized": normalized})
        pcre_runtime[version] = {
            "engine_version": engine.version(),
            "library_sha256": file_digest(library),
        }

    observations.sort(key=lambda item: (item["case_id"], item["profile_id"]))
    evidence = {
        "evidence_version": "1.0.0",
        "corpus": {
            "id": corpus["corpus_id"],
            "sha256": validation["corpus_sha256"],
            "case_count": validation["case_count"],
            "application_counts": validation["application_counts"],
        },
        "projection_sha256": projection["result_sha256"],
        "runtimes": {
            "pcre2": pcre_runtime,
            "node": {
                **node_runtime,
                "executable_sha256": EXPECTED_NODE_EXECUTABLE_SHA256,
            },
            "python": {
                **python_runtime,
                "executable_sha256": EXPECTED_PYTHON_EXECUTABLE_SHA256,
            },
        },
        "observations": observations,
    }
    return {**evidence, "result_sha256": canonical_digest(evidence)}


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": dict(details)}],
    }


def certify(
    *, check: bool, write: bool, repeat_runs: int
) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    try:
        validation = validate_corpus()
        first_projection = run_projection()
        second_projection = run_projection()
        if first_projection != second_projection:
            raise AssertionError("canonical projection is nondeterministic")
        runs = [execute_once(first_projection) for _ in range(repeat_runs)]
        if any(run != runs[0] for run in runs[1:]):
            raise AssertionError(
                "shared exact-runtime observations are nondeterministic"
            )
        evidence = runs[0]
        serialized = json.dumps(evidence, ensure_ascii=False, indent=4) + "\n"
        if check:
            if (
                not EVIDENCE_PATH.is_file()
                or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized
            ):
                raise AssertionError("checked shared observation evidence is stale")
        if write:
            EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
            EVIDENCE_PATH.write_text(serialized, encoding="utf-8")
        details = {
            "case_count": validation["case_count"],
            "application_counts": validation["application_counts"],
            "corpus_sha256": validation["corpus_sha256"],
            "projection_sha256": first_projection["result_sha256"],
            "observation_sha256": evidence["result_sha256"],
            "repeat_runs": repeat_runs,
        }
        return _result("passed", started, details), 0
    except FileNotFoundError as error:
        return _result("unavailable", started, {"reason": str(error)}), EXIT_CODES[
            "unavailable"
        ]
    except Exception as error:
        return _result(
            "failed",
            started,
            {"error_type": type(error).__name__, "reason": str(error)},
        ), 1


def verify_evidence() -> dict[str, Any]:
    validation = validate_corpus()
    evidence = load_json(EVIDENCE_PATH)
    if evidence.get("corpus") != {
        "id": validation["corpus"]["corpus_id"],
        "sha256": validation["corpus_sha256"],
        "case_count": validation["case_count"],
        "application_counts": validation["application_counts"],
    }:
        raise SharedCorpusError("checked evidence corpus identity is stale")
    claimed = evidence.get("result_sha256")
    unsigned = dict(evidence)
    unsigned.pop("result_sha256", None)
    if claimed != canonical_digest(unsigned):
        raise SharedCorpusError("checked evidence result fingerprint differs")
    expected_pairs = [
        (vector["case_id"], profile_id)
        for vector in validation["corpus"]["vectors"]
        for profile_id in EXPECTED_PROFILE_IDS
    ]
    actual_pairs = [
        (item["case_id"], item["profile_id"])
        for item in evidence.get("observations", [])
    ]
    if actual_pairs != expected_pairs:
        raise SharedCorpusError(
            "checked evidence does not preserve the complete denominator"
        )
    return {"case_count": validation["case_count"], "result_sha256": claimed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verify-evidence", action="store_true")
    parser.add_argument("--refresh-authority-identities", action="store_true")
    parser.add_argument("--repeat-runs", type=int, default=2)
    args = parser.parse_args()
    if args.repeat_runs < 2:
        parser.error("--repeat-runs must be at least 2")
    if args.refresh_authority_identities:
        refresh_authority_identities()
        print("SHARED_CORPUS_IDENTITIES status=passed")
        return 0
    if args.validate_only:
        result = validate_corpus()
        payload = {
            key: result[key]
            for key in (
                "case_count",
                "application_counts",
                "corpus_sha256",
                "case_set_sha256",
                "vector_set_sha256",
            )
        }
        print(
            json.dumps(payload, sort_keys=True)
            if args.json
            else f"SHARED_CORPUS status=passed cases={payload['case_count']} sha256={payload['corpus_sha256']}"
        )
        return 0
    if args.verify_evidence:
        payload = verify_evidence()
        print(
            json.dumps(payload, sort_keys=True)
            if args.json
            else f"SHARED_CORPUS_EVIDENCE status=passed sha256={payload['result_sha256']}"
        )
        return 0
    result, code = certify(
        check=args.check, write=args.write, repeat_runs=args.repeat_runs
    )
    print(
        json.dumps(result, sort_keys=True)
        if args.json
        else f"SHARED_CORPUS_CERTIFICATION status={result['status']}"
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
