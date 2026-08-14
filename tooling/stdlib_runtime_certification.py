#!/usr/bin/env python3
"""Certify canonical standard-library patterns on exact governed runtimes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tooling.contract_validation import canonical_json, load_json
from tooling.ecmascript_runtime_certification import (
    EXPECTED_ARCHITECTURE as EXPECTED_NODE_ARCHITECTURE,
    EXPECTED_EXECUTABLE_SHA256 as EXPECTED_NODE_EXECUTABLE_SHA256,
    EXPECTED_NODE,
    EXPECTED_PLATFORM as EXPECTED_NODE_PLATFORM,
    EXPECTED_V8,
    NODE_ENV,
    run_harness as run_node_harness,
)
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
from tooling.stdlib_registry import StandardLibraryRegistrySuite

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "spec" / "stdlib" / "registry" / "1.0" / "canonical-semantics.json"
)
PROFILE_ROOT = ROOT / "spec" / "targets" / "profiles"
EVIDENCE_PATH = (
    ROOT / "tests" / "conformance" / "evidence" / "stdlib-runtime-observations.json"
)
PROJECTION_COMMAND = [
    "cargo",
    "run",
    "--manifest-path",
    "core/Cargo.toml",
    "--example",
    "stdlib_runtime_projection",
    "--locked",
    "--quiet",
]
OPERATION_ID = "certification.stdlib-runtime"
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
    "10.42": {
        "sha256": "61acdf1505445bccf8257ca48b6a5b82af651e800f948d45f81ec684e1b129a7"
    },
    "10.43": {
        "sha256": "9998a4700a45c220c856ee2bf8389084234cdb91b4dfeb4dc0c001b65c537853"
    },
}
PCRE2_CERTIFICATION_LIMITS = MatchLimits(
    match=100_000,
    depth=100_000,
    heap_kib=64 * 1024,
)
EXPECTED_VARIANT_COUNT = 8
EXPECTED_RECORD_COUNTS = {
    "audited": 40,
    "compatibility": 60,
    "stress": 17,
    "total": 117,
}
EXPECTED_APPLICATION_COUNTS = {"execute": 580, "not_applicable": 5}


class StdlibRuntimeError(ValueError):
    """The canonical standard-library runtime contract is malformed."""


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


def validate_contract() -> dict[str, Any]:
    """Validate the exact authored case and profile denominator."""

    suite = StandardLibraryRegistrySuite()
    helper_count, variant_count, binding_count, audited_count = (
        suite.validate_canonical_file()
    )
    contract = load_json(CONTRACT_PATH)
    records = suite.materialize_runtime_cases()
    applications = suite.runtime_applications(records)
    profile_ids = tuple(
        item["target_profile"]["profile_id"]
        for item in contract["runtime_certification"]["profiles"]
    )
    if profile_ids != EXPECTED_PROFILE_IDS:
        raise StdlibRuntimeError("runtime profile denominator or order changed")
    if variant_count != EXPECTED_VARIANT_COUNT:
        raise StdlibRuntimeError("runtime variant denominator changed")
    record_counts = {
        "audited": sum(item["source"] == "audited" for item in records),
        "compatibility": sum(item["source"] == "compatibility" for item in records),
        "stress": sum(item["source"] == "stress" for item in records),
        "total": len(records),
    }
    if record_counts != EXPECTED_RECORD_COUNTS:
        raise StdlibRuntimeError("runtime record denominator changed")
    application_counts = {
        "execute": sum(item["state"] == "execute" for item in applications),
        "not_applicable": sum(
            item["state"] == "not_applicable" for item in applications
        ),
    }
    if application_counts != EXPECTED_APPLICATION_COUNTS:
        raise StdlibRuntimeError("runtime application denominator changed")
    return {
        "application_counts": application_counts,
        "applications": applications,
        "audited_count": audited_count,
        "binding_count": binding_count,
        "contract": contract,
        "contract_sha256": canonical_digest(contract),
        "helper_count": helper_count,
        "profile_ids": profile_ids,
        "record_counts": record_counts,
        "records": records,
        "variant_count": variant_count,
    }


def validate_projection(
    projection: Mapping[str, Any], validation: Mapping[str, Any]
) -> None:
    """Reject stale, incomplete, or unsupported compiler projections."""

    unsigned = dict(projection)
    claimed = unsigned.pop("result_sha256", None)
    if claimed != canonical_digest(unsigned):
        raise StdlibRuntimeError("projection result fingerprint differs")
    if projection.get("contract_sha256") != validation["contract_sha256"]:
        raise StdlibRuntimeError("projection canonical contract fingerprint is stale")
    if projection.get("registry_version") != validation["contract"]["registry_version"]:
        raise StdlibRuntimeError("projection registry version differs")

    expected_variants = [
        item["variant_id"] for item in validation["contract"]["entries"]
    ]
    variants = projection.get("variants")
    if (
        not isinstance(variants, list)
        or [item.get("variant_id") for item in variants] != expected_variants
    ):
        raise StdlibRuntimeError("projection variant denominator or order changed")
    helper_by_variant = {
        item["variant_id"]: item["helper_id"]
        for item in validation["contract"]["entries"]
    }
    for variant in variants:
        variant_id = variant["variant_id"]
        if variant.get("helper_id") != helper_by_variant[variant_id]:
            raise StdlibRuntimeError(f"{variant_id}: helper identity differs")
        projected_profiles = variant.get("applications")
        if not isinstance(projected_profiles, list) or [
            item.get("profile_id") for item in projected_profiles
        ] != list(EXPECTED_PROFILE_IDS):
            raise StdlibRuntimeError(
                f"{variant_id}: projection profile denominator or order changed"
            )
        for application in projected_profiles:
            profile_id = application["profile_id"]
            if application.get("planned_status") not in {
                "native",
                "equivalent_rewrite",
            }:
                raise StdlibRuntimeError(
                    f"{variant_id}/{profile_id}: projection is not executable"
                )
            artifact = application.get("artifact")
            if (
                not isinstance(artifact, Mapping)
                or not isinstance(artifact.get("pattern"), Mapping)
                or not isinstance(artifact["pattern"].get("text"), str)
                or not artifact["pattern"]["text"]
            ):
                raise StdlibRuntimeError(
                    f"{variant_id}/{profile_id}: projected artifact is malformed"
                )
            if (
                profile_id == "profile:python-re/3.11"
                and application.get("pattern_kind") != "str"
            ):
                raise StdlibRuntimeError(f"{variant_id}: Python str kind differs")
            if (
                profile_id == "profile:python-re/3.11-bytes"
                and application.get("pattern_kind") != "bytes"
            ):
                raise StdlibRuntimeError(f"{variant_id}: Python bytes kind differs")


def run_projection() -> dict[str, Any]:
    environment = {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "PATH": os.environ.get("PATH", ""),
    }
    if os.environ.get("CARGO_TARGET_DIR"):
        environment["CARGO_TARGET_DIR"] = os.environ["CARGO_TARGET_DIR"]
    completed = subprocess.run(
        PROJECTION_COMMAND,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=90,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"stdlib projection failed with code {completed.returncode}: "
            f"{completed.stderr[-1000:]}"
        )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("stdlib projection root must be an object")
    return value


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


def _whole_value_match(
    matches: Sequence[Mapping[str, Any]], subject: str, coordinate: str
) -> bool:
    lengths = {
        "code-points": len(subject),
        "utf16-code-units": len(subject.encode("utf-16-le")) // 2,
        "utf8-bytes": len(subject.encode("utf-8")),
    }
    expected_span = [0, lengths[coordinate]]
    return any(item.get("span") == expected_span for item in matches)


def _observation(
    item: Mapping[str, Any], profile_id: str, actual_match: bool | None
) -> dict[str, Any]:
    return {
        "actual_match": actual_match,
        "case_id": item["case_id"],
        "expected_match": item["expected_match"],
        "profile_id": profile_id,
        "source": item["source"],
        "state": item["state"],
        "subject_sha256": hashlib.sha256(item["input"].encode("utf-8")).hexdigest(),
        "subject_utf8_bytes": len(item["input"].encode("utf-8")),
        "variant_id": item["variant_id"],
    }


def _assert_match(item: Mapping[str, Any], actual: bool) -> None:
    if actual != item["expected_match"]:
        raise AssertionError(
            f"{item['case_id']}/{item['profile_id']}: expected "
            f"match={item['expected_match']}, observed {actual}"
        )


def _assert_pcre_match(item: Mapping[str, Any], raw: Mapping[str, Any]) -> bool:
    outcome = raw.get("outcome")
    if outcome not in {"match", "no_match"}:
        raise AssertionError(
            f"{item['case_id']}/{item['profile_id']}: PCRE2 returned "
            f"{outcome!r} (code {raw.get('return_code')!r})"
        )
    actual = _whole_value_match([raw], item["input"], "utf8-bytes")
    _assert_match(item, actual)
    return actual


def execute_once(
    projection: Mapping[str, Any], validation: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute all 580 applicable cases and return deterministic evidence."""

    validate_projection(projection, validation)
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

    records_by_id = {item["case_id"]: item for item in validation["records"]}
    applications = []
    for item in validation["applications"]:
        record = records_by_id[item["case_id"]]
        applications.append({**record, **item, "profile_id": item["profile_id"]})
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    observations = []
    for item in applications:
        if item["state"] == "not_applicable":
            observations.append(_observation(item, item["profile_id"], None))
        else:
            grouped[(item["variant_id"], item["profile_id"])].append(item)

    projected = {
        (variant["variant_id"], application["profile_id"]): application
        for variant in projection["variants"]
        for application in variant["applications"]
    }

    node_cases = []
    node_meta = []
    for variant_id in [item["variant_id"] for item in projection["variants"]]:
        profile_id = "profile:ecmascript/2024"
        items = grouped[(variant_id, profile_id)]
        product = projected[(variant_id, profile_id)]
        artifact = product["artifact"]
        node_cases.append(
            {
                "id": f"{variant_id}@{profile_id}",
                "source": artifact["pattern"]["text"],
                "flags": artifact["pattern"].get("flags", []),
                "subjects": [item["input"] for item in items],
            }
        )
        node_meta.append(items)
    node_response = run_node_harness(
        node_binary, {"protocol_version": "1.0.0", "cases": node_cases}
    )
    node_runtime = node_response.get("runtime")
    if node_runtime != {
        "node": EXPECTED_NODE,
        "v8": EXPECTED_V8,
        "platform": EXPECTED_NODE_PLATFORM,
        "architecture": EXPECTED_NODE_ARCHITECTURE,
    }:
        raise ValueError("Node runtime identity differs from the governed pin")
    for items, raw_case in zip(node_meta, node_response["cases"]):
        if raw_case["compile"] != "ok":
            raise AssertionError(f"{raw_case['id']}: Node compilation failed")
        for item, raw in zip(items, raw_case["observations"]):
            actual = _whole_value_match(
                raw["matches"], item["input"], "utf16-code-units"
            )
            _assert_match(item, actual)
            observations.append(_observation(item, item["profile_id"], actual))

    python_cases = []
    python_meta = []
    for profile_id in (
        "profile:python-re/3.11",
        "profile:python-re/3.11-bytes",
    ):
        for variant_id in [item["variant_id"] for item in projection["variants"]]:
            items = grouped[(variant_id, profile_id)]
            product = projected[(variant_id, profile_id)]
            pattern_kind = product["pattern_kind"]
            subjects = [item["input"] for item in items]
            if pattern_kind == "bytes":
                subjects = [subject.encode("ascii").hex() for subject in subjects]
            python_cases.append(
                {
                    "id": f"{variant_id}@{profile_id}",
                    "source": product["artifact"]["pattern"]["text"],
                    "pattern_kind": pattern_kind,
                    "flags": product["artifact"]["pattern"].get("flags", []),
                    "subjects": subjects,
                }
            )
            python_meta.append((items, pattern_kind))
    python_response = run_python_harness(
        python_binary, {"protocol_version": "1.0.0", "cases": python_cases}
    )
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
    for (items, pattern_kind), raw_case in zip(python_meta, python_response["cases"]):
        if raw_case["compile"]["status"] != "ok":
            raise AssertionError(f"{raw_case['id']}: Python re compilation failed")
        coordinate = "utf8-bytes" if pattern_kind == "bytes" else "code-points"
        for item, raw in zip(items, raw_case["observations"]):
            actual = _whole_value_match(raw["matches"], item["input"], coordinate)
            _assert_match(item, actual)
            observations.append(_observation(item, item["profile_id"], actual))

    pcre_runtime = {}
    for version in ("10.42", "10.43"):
        library = pcre_paths[version]
        if file_digest(library) != EXPECTED_PCRE2_LIBRARIES[version]["sha256"]:
            raise ValueError(
                f"PCRE2 {version} library fingerprint differs from the governed pin"
            )
        engine = Engine(library)
        if engine.version().split()[0] != version:
            raise ValueError(f"PCRE2 {version} runtime identity differs")
        profile_id = f"profile:pcre2/{version}"
        profile = load_json(_profile_path(profile_id))
        configuration = profile_configuration(profile)
        for variant_id in [item["variant_id"] for item in projection["variants"]]:
            items = grouped[(variant_id, profile_id)]
            product = projected[(variant_id, profile_id)]
            raw_case = engine.run_detailed_case(
                product["artifact"]["pattern"]["text"],
                [{"subject": item["input"]} for item in items],
                configuration,
                PCRE2_CERTIFICATION_LIMITS,
            )
            if raw_case["compile"] != "ok":
                raise AssertionError(
                    f"{variant_id}@{profile_id}: PCRE2 compilation failed"
                )
            for item, raw in zip(items, raw_case["matches"]):
                actual = _assert_pcre_match(item, raw)
                observations.append(_observation(item, profile_id, actual))
        pcre_runtime[version] = {
            "engine_version": engine.version(),
            "library_sha256": file_digest(library),
        }

    observations.sort(key=lambda item: (item["case_id"], item["profile_id"]))
    evidence = {
        "evidence_version": "1.0.0",
        "contract": {
            "application_counts": validation["application_counts"],
            "record_counts": validation["record_counts"],
            "registry_version": validation["contract"]["registry_version"],
            "sha256": validation["contract_sha256"],
            "variant_count": validation["variant_count"],
        },
        "observations": observations,
        "projection_sha256": projection["result_sha256"],
        "runtimes": {
            "node": {
                **node_runtime,
                "executable_sha256": EXPECTED_NODE_EXECUTABLE_SHA256,
            },
            "pcre2": pcre_runtime,
            "python": {
                **python_runtime,
                "executable_sha256": EXPECTED_PYTHON_EXECUTABLE_SHA256,
            },
        },
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
        validation = validate_contract()
        first_projection = run_projection()
        second_projection = run_projection()
        validate_projection(first_projection, validation)
        validate_projection(second_projection, validation)
        if first_projection != second_projection:
            raise AssertionError("canonical stdlib projection is nondeterministic")
        runs = [execute_once(first_projection, validation) for _ in range(repeat_runs)]
        if any(run != runs[0] for run in runs[1:]):
            raise AssertionError(
                "stdlib exact-runtime observations are nondeterministic"
            )
        evidence = runs[0]
        serialized = json.dumps(evidence, ensure_ascii=False, indent=4) + "\n"
        if check and (
            not EVIDENCE_PATH.is_file()
            or EVIDENCE_PATH.read_text(encoding="utf-8") != serialized
        ):
            raise AssertionError("checked stdlib runtime evidence is stale")
        if write:
            EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
            EVIDENCE_PATH.write_text(serialized, encoding="utf-8")
        details = {
            "application_counts": validation["application_counts"],
            "contract_sha256": validation["contract_sha256"],
            "observation_sha256": evidence["result_sha256"],
            "projection_sha256": first_projection["result_sha256"],
            "record_counts": validation["record_counts"],
            "repeat_runs": repeat_runs,
            "variant_count": validation["variant_count"],
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
    validation = validate_contract()
    evidence = load_json(EVIDENCE_PATH)
    if evidence.get("contract") != {
        "application_counts": validation["application_counts"],
        "record_counts": validation["record_counts"],
        "registry_version": validation["contract"]["registry_version"],
        "sha256": validation["contract_sha256"],
        "variant_count": validation["variant_count"],
    }:
        raise StdlibRuntimeError("checked evidence contract identity is stale")
    claimed = evidence.get("result_sha256")
    unsigned = dict(evidence)
    unsigned.pop("result_sha256", None)
    if claimed != canonical_digest(unsigned):
        raise StdlibRuntimeError("checked evidence result fingerprint differs")
    expected_pairs = sorted(
        (application["case_id"], application["profile_id"])
        for application in validation["applications"]
    )
    actual_pairs = [
        (item["case_id"], item["profile_id"])
        for item in evidence.get("observations", [])
    ]
    if actual_pairs != expected_pairs:
        raise StdlibRuntimeError("checked evidence does not preserve the denominator")
    return {
        "application_counts": validation["application_counts"],
        "record_counts": validation["record_counts"],
        "result_sha256": claimed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verify-evidence", action="store_true")
    parser.add_argument("--repeat-runs", type=int, default=2)
    args = parser.parse_args()
    if args.repeat_runs < 2:
        parser.error("--repeat-runs must be at least 2")
    if args.validate_only:
        validation = validate_contract()
        payload = {
            "application_counts": validation["application_counts"],
            "contract_sha256": validation["contract_sha256"],
            "record_counts": validation["record_counts"],
            "variant_count": validation["variant_count"],
        }
        print(
            json.dumps(payload, sort_keys=True)
            if args.json
            else "STDLIB_RUNTIME_CONTRACT status=passed "
            f"records={payload['record_counts']['total']} "
            f"applications={sum(payload['application_counts'].values())}"
        )
        return 0
    if args.verify_evidence:
        payload = verify_evidence()
        print(
            json.dumps(payload, sort_keys=True)
            if args.json
            else "STDLIB_RUNTIME_EVIDENCE status=passed "
            f"sha256={payload['result_sha256']}"
        )
        return 0
    result, code = certify(
        check=args.check, write=args.write, repeat_runs=args.repeat_runs
    )
    print(
        json.dumps(result, sort_keys=True)
        if args.json
        else f"STDLIB_RUNTIME_CERTIFICATION status={result['status']}"
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
