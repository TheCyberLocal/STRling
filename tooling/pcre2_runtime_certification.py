#!/usr/bin/env python3
"""Certify canonical artifacts against exact bounded PCRE2 8-bit runtimes."""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from tooling.pcre2_feature_probe import (
    Engine,
    MatchLimits,
    canonical_digest,
    file_digest,
    load_json,
    profile_configuration,
    run_probe,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURE_CORPUS = ROOT / "tests" / "conformance" / "pcre2-versioned-features.json"
RUNTIME_CORPUS = ROOT / "tests" / "conformance" / "pcre2-runtime-certification.json"
PROFILES = {
    "10.42": ROOT / "spec" / "targets" / "profiles" / "pcre2-10.42.json",
    "10.43": ROOT / "spec" / "targets" / "profiles" / "pcre2-10.43.json",
}
LIBRARY_ENV = {
    "10.42": "STRLING_PCRE2_1042_LIBRARY",
    "10.43": "STRLING_PCRE2_1043_LIBRARY",
}
BUILD_ENV = {
    "10.42": "STRLING_PCRE2_1042_BUILD_ID",
    "10.43": "STRLING_PCRE2_1043_BUILD_ID",
}
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2, "incomplete": 3}
STATUS_PRECEDENCE = ("failed", "incomplete", "unavailable", "passed")


def limits(raw: Mapping[str, Any]) -> MatchLimits:
    return MatchLimits(
        match=raw["match"],
        depth=raw["depth"],
        heap_kib=raw["heap_kib"],
    )


def repeated_subject(raw: Mapping[str, Any]) -> str:
    return raw["text"] * raw["count"] + raw["suffix"]


def generated_cases(configuration: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Create deterministic, bounded, expectation-bearing runtime fuzz cases."""

    seed = configuration["seed"]
    count = configuration["count"]
    cases = []
    for index in range(count):
        value = (seed + index * 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
        width = 1 + value % 12
        letter = chr(ord("a") + (value >> 8) % 26)
        case_kind = index % 4
        if case_kind == 0:
            literal = letter * width
            pattern = rf"\A(?:{literal})\z"
            positive = literal
        elif case_kind == 1:
            name = f"g{index}"
            pattern = rf"\A(?<{name}>[a-z]{{{width}}})\g{{1}}\z"
            positive = letter * (width * 2)
        elif case_kind == 2:
            pattern = rf"\A(?>{letter}{{{width}}})!\z"
            positive = letter * width + "!"
        else:
            pattern = rf"\A(?:{letter}|{letter}{letter}){{{width}}}+\z"
            positive = letter * width
        cases.append(
            {
                "id": f"generated-{index:04d}",
                "pattern": pattern,
                "observations": [
                    {"subject": positive, "outcome": "match"},
                    {"subject": positive + "x", "outcome": "no_match"},
                ],
            }
        )
    maximum_pattern = configuration["maximum_pattern_bytes"]
    maximum_subject = configuration["maximum_subject_bytes"]
    if any(len(case["pattern"].encode("utf-8")) > maximum_pattern for case in cases):
        raise ValueError("generated pattern exceeds governed byte maximum")
    if any(
        len(observation["subject"].encode("utf-8")) > maximum_subject
        for case in cases
        for observation in case["observations"]
    ):
        raise ValueError("generated subject exceeds governed byte maximum")
    return cases


def observation_projection(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "subject": result["subject"],
        "outcome": result["outcome"],
        "span": result["span"],
        "captures": result["captures"],
    }


def assert_detailed_case(
    case_id: str,
    actual: Mapping[str, Any],
    expected: Sequence[Mapping[str, Any]],
) -> None:
    if actual["compile"] != "ok":
        raise AssertionError(f"{case_id}: expected successful compilation")
    if actual["matches"] != list(expected):
        raise AssertionError(
            f"{case_id}: detailed observations differ: {actual['matches']!r}"
        )


def run_version_once(
    version: str,
    library: Path,
    feature_corpus: Mapping[str, Any],
    runtime_corpus: Mapping[str, Any],
    engine_factory: Callable[[Path], Engine],
) -> dict[str, Any]:
    profile_path = PROFILES[version]
    profile = load_json(profile_path)
    configuration = profile_configuration(profile)
    engine = engine_factory(library)
    engine_version = engine.version()
    if engine_version.split()[0] != version:
        raise ValueError(
            f"loaded PCRE2 version {engine_version!r} does not match {version}"
        )

    feature_result = run_probe(
        FEATURE_CORPUS,
        profile_path,
        library,
        engine_factory=engine_factory,
    )
    feature_by_id = {case["id"]: case for case in feature_corpus["cases"]}
    normal_limits = limits(runtime_corpus["normal_limits"])
    detailed_results = []
    for case in runtime_corpus["detailed_cases"]:
        pattern = case.get("pattern")
        if pattern is None:
            feature = feature_by_id[case["feature_case_id"]]
            pattern = feature["profiles"][version].get("pattern", feature["pattern"])
        observations = [{"subject": item["subject"]} for item in case["observations"]]
        actual = engine.run_detailed_case(
            pattern,
            observations,
            configuration,
            normal_limits,
        )
        assert_detailed_case(case["id"], actual, case["observations"])
        detailed_results.append({"id": case["id"], **actual})

    resource_results = []
    for case in runtime_corpus["resource_cases"]:
        subject = repeated_subject(case["subject_repeat"])
        actual = engine.run_detailed_case(
            case["pattern"],
            [{"subject": subject}],
            configuration,
            limits(case["limits"]),
        )
        if actual["compile"] != "ok" or len(actual["matches"]) != 1:
            raise AssertionError(f"{case['id']}: resource case did not execute once")
        outcome = actual["matches"][0]["outcome"]
        if outcome != case["expected_outcome"]:
            raise AssertionError(
                f"{case['id']}: expected {case['expected_outcome']}, observed {outcome}"
            )
        resource_results.append(
            {
                "id": case["id"],
                "outcome": outcome,
                "return_code": actual["matches"][0]["return_code"],
            }
        )

    rewrite_results = []
    for case in runtime_corpus["rewrite_cases"]:
        observations = [{"subject": subject} for subject in case["subjects"]]
        original = engine.run_detailed_case(
            case["original_pattern"], observations, configuration, normal_limits
        )
        rewritten = engine.run_detailed_case(
            case["rewritten_pattern"], observations, configuration, normal_limits
        )
        if original["compile"] != "ok" or rewritten["compile"] != "ok":
            raise AssertionError(f"{case['id']}: rewrite comparison did not compile")
        original_projection = [
            observation_projection(item) for item in original["matches"]
        ]
        rewritten_projection = [
            observation_projection(item) for item in rewritten["matches"]
        ]
        if original_projection != rewritten_projection:
            raise AssertionError(f"{case['id']}: rewrite observations differ")
        rewrite_results.append(
            {
                "id": case["id"],
                "strategy_id": case["strategy_id"],
                "observations": original_projection,
            }
        )

    generated_results = []
    generated = generated_cases(runtime_corpus["generated_cases"])
    for case in generated:
        actual = engine.run_detailed_case(
            case["pattern"],
            [{"subject": item["subject"]} for item in case["observations"]],
            configuration,
            normal_limits,
        )
        outcomes = [item["outcome"] for item in actual["matches"]]
        expected = [item["outcome"] for item in case["observations"]]
        if actual["compile"] != "ok" or outcomes != expected:
            raise AssertionError(
                f"{case['id']}: expected outcomes {expected}, observed {outcomes}"
            )
        generated_results.append(
            {
                "id": case["id"],
                "pattern": case["pattern"],
                "outcomes": outcomes,
            }
        )

    semantic_evidence = {
        "feature_cases": feature_result["cases"],
        "detailed_cases": detailed_results,
        "resource_cases": resource_results,
        "rewrite_cases": rewrite_results,
        "generated": {
            "seed": runtime_corpus["generated_cases"]["seed"],
            "count": len(generated_results),
            "result_sha256": canonical_digest(generated_results),
        },
    }
    evidence = {
        "engine_version": engine_version,
        "profile_sha256": canonical_digest(profile),
        "library_sha256": file_digest(library),
        "configuration": {
            "compile_options": configuration.compile_options,
            "matcher_api": configuration.matcher_api,
            "maximum_variable_lookbehind": (configuration.maximum_variable_lookbehind),
            "newline": configuration.newline,
        },
        "feature_result_sha256": feature_result["result_sha256"],
        **semantic_evidence,
    }
    return {
        **evidence,
        "semantic_result_sha256": canonical_digest(semantic_evidence),
    }


def aggregate_status(checks: Sequence[Mapping[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    return next(status for status in STATUS_PRECEDENCE if status in statuses)


def result_digest(result: Mapping[str, Any]) -> str:
    projection = copy.deepcopy(result)
    projection.pop("deterministic_result_sha256", None)
    for check in projection.get("checks", []):
        evidence = check.get("evidence")
        if isinstance(evidence, dict):
            evidence.pop("timing_observations_microseconds", None)
    return canonical_digest(projection)


def run_certification(
    libraries: Mapping[str, Path | None],
    repeat_runs: int,
    engine_factory: Callable[[Path], Engine] = Engine,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    if repeat_runs < 2:
        raise ValueError("repeat_runs must be at least 2")
    feature_corpus = load_json(FEATURE_CORPUS)
    runtime_corpus = load_json(RUNTIME_CORPUS)
    if feature_corpus["profiles"] != runtime_corpus["profiles"]:
        raise ValueError("feature and runtime corpora disagree on profile versions")

    harness_files = [Path(__file__).resolve(), ROOT / "tooling/pcre2_feature_probe.py"]
    harness_sha256 = canonical_digest(
        {path.name: file_digest(path) for path in harness_files}
    )
    checks = []
    for version in runtime_corpus["profiles"]:
        library = libraries.get(version)
        check_id = f"certification.pcre2-runtime.{version}"
        if library is None or not library.is_file():
            checks.append(
                {
                    "check_id": check_id,
                    "status": "unavailable",
                    "unavailable_reason": (
                        f"exact PCRE2 {version} library is not available through "
                        f"{LIBRARY_ENV[version]}"
                    ),
                }
            )
            continue
        try:
            semantic_digests = []
            durations = []
            latest = None
            for _ in range(repeat_runs):
                started = clock()
                latest = run_version_once(
                    version,
                    library,
                    feature_corpus,
                    runtime_corpus,
                    engine_factory,
                )
                durations.append(round((clock() - started) * 1_000_000))
                semantic_digests.append(latest["semantic_result_sha256"])
            if len(set(semantic_digests)) != 1:
                raise AssertionError(
                    f"PCRE2 {version} repeated semantic evidence is nondeterministic"
                )
            assert latest is not None
            checks.append(
                {
                    "check_id": check_id,
                    "status": "passed",
                    "evidence": {
                        "engine_version": latest["engine_version"],
                        "build_id": os.environ.get(BUILD_ENV[version], "unreported"),
                        "library_sha256": latest["library_sha256"],
                        "profile_sha256": latest["profile_sha256"],
                        "feature_corpus_sha256": canonical_digest(feature_corpus),
                        "runtime_corpus_sha256": canonical_digest(runtime_corpus),
                        "harness_sha256": harness_sha256,
                        "platform": {
                            "system": platform.system(),
                            "machine": platform.machine(),
                            "python_implementation": platform.python_implementation(),
                            "python_version": platform.python_version(),
                        },
                        "repeat_runs": repeat_runs,
                        "semantic_result_sha256": semantic_digests[0],
                        "feature_cases": len(feature_corpus["cases"]),
                        "detailed_cases": len(runtime_corpus["detailed_cases"]),
                        "resource_cases": len(runtime_corpus["resource_cases"]),
                        "rewrite_cases": len(runtime_corpus["rewrite_cases"]),
                        "generated_cases": runtime_corpus["generated_cases"]["count"],
                        "timing_observations_microseconds": durations,
                    },
                }
            )
        except (AssertionError, OSError, RuntimeError, ValueError) as exc:
            checks.append(
                {
                    "check_id": check_id,
                    "status": "failed",
                    "findings": [
                        {
                            "code": "PCRE2_RUNTIME_CERTIFICATION_FAILED",
                            "message": str(exc),
                        }
                    ],
                }
            )

    status = aggregate_status(checks)
    summary = {
        state: sum(check["status"] == state for check in checks)
        for state in ("passed", "failed", "waived", "unavailable", "incomplete")
    }
    result = {
        "certification_version": "1.0.0",
        "operation_id": "certification.pcre2-runtime",
        "status": status,
        "summary": summary,
        "checks": checks,
    }
    return {**result, "deterministic_result_sha256": result_digest(result)}


def parse_libraries() -> dict[str, Path | None]:
    return {
        version: Path(value) if (value := os.environ.get(variable)) else None
        for version, variable in LIBRARY_ENV.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repeat-runs", type=int, default=2)
    args = parser.parse_args()
    try:
        result = run_certification(parse_libraries(), args.repeat_runs)
    except (OSError, RuntimeError, ValueError) as exc:
        result = {
            "certification_version": "1.0.0",
            "operation_id": "certification.pcre2-runtime",
            "status": "incomplete",
            "summary": {
                "passed": 0,
                "failed": 0,
                "waived": 0,
                "unavailable": 0,
                "incomplete": 1,
            },
            "checks": [
                {
                    "check_id": "certification.pcre2-runtime.configuration",
                    "status": "incomplete",
                    "findings": [
                        {
                            "code": "PCRE2_RUNTIME_CERTIFICATION_INCOMPLETE",
                            "message": str(exc),
                        }
                    ],
                }
            ],
        }
        result["deterministic_result_sha256"] = result_digest(result)
    serialized = json.dumps(
        result, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if args.json:
        print(serialized)
    else:
        print(
            f"PCRE2 runtime certification: {result['status'].upper()} "
            f"({result['summary']})"
        )
    raise SystemExit(EXIT_CODES[result["status"]])


if __name__ == "__main__":
    main()
