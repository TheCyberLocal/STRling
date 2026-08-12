#!/usr/bin/env python3
"""Certify bounded Python ``re`` artifacts on exact CPython 3.11.15."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "conformance" / "python-re-runtime-certification.json"
HARNESS = ROOT / "tooling" / "python_re_harness.py"
PYTHON_ENV = "STRLING_CPYTHON_311_BINARY"
EXPECTED_VERSION = "3.11.15"
EXPECTED_IMPLEMENTATION = "cpython"
EXPECTED_PLATFORM = "linux"
EXPECTED_MACHINE = "x86_64"
EXPECTED_CACHE_TAG = "cpython-311"
EXPECTED_SOABI = "cpython-311-x86_64-linux-gnu"
EXPECTED_SYSCONFIG_PLATFORM = "linux-x86_64"
EXPECTED_ARCHIVE = "Python-3.11.15.tar.xz"
EXPECTED_ARCHIVE_SHA256 = (
    "272179ddd9a2e41a0fc8e42e33dfbdca0b3711aa5abf372d3f2d51543d09b625"
)
EXPECTED_EXECUTABLE_SHA256 = (
    "1fbfa9ca2d8b4a1180be898c8de67732deee8aff7bb838012acb63764be83232"
)
EXPECTED_PROFILES = [
    {
        "id": "profile:python-re/3.11",
        "version": "1.2.0",
        "pattern_kind": "str",
        "sha256": "55e7f0bc93e2192d5f09f6c4ef65b6bff0dc831571059d80edf9b8b661f80a6c",
    },
    {
        "id": "profile:python-re/3.11-bytes",
        "version": "1.0.0",
        "pattern_kind": "bytes",
        "sha256": "2ba10d0f9ba00c0f5685fc20a40ae436937952074558d8bba89ffe6bb244dfca",
    },
]
PROTOCOL_VERSION = "1.0.0"
OPERATION_ID = "certification.python-re-runtime"
CHECK_ID = f"{OPERATION_ID}.cpython-3.11.15"
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2, "incomplete": 3}


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def encode_subject(value: str, pattern_kind: str) -> str:
    return value.encode("ascii").hex() if pattern_kind == "bytes" else value


def encoded_value(value: str, pattern_kind: str) -> str:
    return value.encode("ascii").hex() if pattern_kind == "bytes" else value


def exact_observation(subject: str, value: str, pattern_kind: str) -> dict[str, Any]:
    encoded_subject = encode_subject(subject, pattern_kind)
    encoded_match = encoded_value(value, pattern_kind)
    end = len(value)
    return {
        "subject": encoded_subject,
        "matches": [
            {
                "span": [0, end],
                "value": encoded_match,
                "captures": [{"index": 0, "span": [0, end], "value": encoded_match}],
            }
        ],
    }


def generated_cases(configuration: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Create deterministic bounded str and bytes execution cases."""

    seed = configuration["seed"]
    count = configuration["count"]
    cases = []
    for index in range(count):
        value = (seed + index * 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
        width = 1 + value % 8
        letter = chr(ord("a") + (value >> 8) % 26)
        positive = letter * width
        case_id = f"generated-{index:04d}"
        kind = index % 4
        if kind == 0:
            pattern_kind = "str"
            source = rf"\A{positive}\Z"
            subjects = [positive, positive + "x"]
            expected = [
                exact_observation(positive, positive, pattern_kind),
                {"subject": subjects[1], "matches": []},
            ]
            flags: list[str] = []
        elif kind == 1:
            pattern_kind = "bytes"
            name = f"g{index}"
            source = rf"\A(?P<{name}>{letter}{{{width}}})(?P={name})\Z"
            doubled = positive * 2
            subjects = [doubled, doubled + "x"]
            encoded_doubled = doubled.encode("ascii").hex()
            encoded_positive = positive.encode("ascii").hex()
            expected = [
                {
                    "subject": encoded_doubled,
                    "matches": [
                        {
                            "span": [0, len(doubled)],
                            "value": encoded_doubled,
                            "captures": [
                                {
                                    "index": 0,
                                    "span": [0, len(doubled)],
                                    "value": encoded_doubled,
                                },
                                {
                                    "index": 1,
                                    "name": name,
                                    "span": [0, len(positive)],
                                    "value": encoded_positive,
                                },
                            ],
                        }
                    ],
                },
                {"subject": subjects[1].encode("ascii").hex(), "matches": []},
            ]
            flags = []
        elif kind == 2:
            pattern_kind = "str"
            source = rf"(?<=ab){letter}{{{width}}}(?!{letter})"
            matching = f"xxab{positive}!"
            missing_prefix = f"xxac{positive}!"
            subjects = [matching, missing_prefix]
            start = 4
            end = start + len(positive)
            expected = [
                {
                    "subject": matching,
                    "matches": [
                        {
                            "span": [start, end],
                            "value": positive,
                            "captures": [
                                {
                                    "index": 0,
                                    "span": [start, end],
                                    "value": positive,
                                }
                            ],
                        }
                    ],
                },
                {"subject": missing_prefix, "matches": []},
            ]
            flags = []
        else:
            pattern_kind = "bytes"
            source = rf"\A{letter}{{{width}}}\Z"
            matching = positive.upper()
            subjects = [matching, "0" * width]
            expected = [
                exact_observation(matching, matching, pattern_kind),
                {"subject": subjects[1].encode("ascii").hex(), "matches": []},
            ]
            flags = ["i"]
        encoded_subjects = [
            encode_subject(subject, pattern_kind) for subject in subjects
        ]
        cases.append(
            {
                "id": case_id,
                "source": source,
                "pattern_kind": pattern_kind,
                "flags": flags,
                "subjects": encoded_subjects,
                "expected": expected,
            }
        )

    maximum_source = configuration["maximum_source_bytes"]
    maximum_subject = configuration["maximum_subject_units"]
    if any(len(case["source"].encode("utf-8")) > maximum_source for case in cases):
        raise ValueError("generated source exceeds the governed byte maximum")
    if any(
        (len(subject) // 2 if case["pattern_kind"] == "bytes" else len(subject))
        > maximum_subject
        for case in cases
        for subject in case["subjects"]
    ):
        raise ValueError("generated subject exceeds the governed unit maximum")
    return cases


def validate_corpus_identity(corpus: Mapping[str, Any]) -> None:
    runtime = corpus.get("runtime")
    expected_runtime = {
        "python_version": EXPECTED_VERSION,
        "implementation": EXPECTED_IMPLEMENTATION,
        "platform": EXPECTED_PLATFORM,
        "machine": EXPECTED_MACHINE,
        "cache_tag": EXPECTED_CACHE_TAG,
        "soabi": EXPECTED_SOABI,
        "sysconfig_platform": EXPECTED_SYSCONFIG_PLATFORM,
        "archive": EXPECTED_ARCHIVE,
        "archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "executable_sha256": EXPECTED_EXECUTABLE_SHA256,
    }
    if not isinstance(runtime, Mapping) or any(
        runtime.get(key) != value for key, value in expected_runtime.items()
    ):
        raise ValueError(
            "runtime corpus identity differs from the governed CPython pin"
        )
    if corpus.get("profiles") != EXPECTED_PROFILES:
        raise ValueError(
            "runtime corpus profiles differ from the governed profile pins"
        )


def request_case(
    case: Mapping[str, Any], *, case_id: str | None = None
) -> dict[str, Any]:
    result = {
        "id": case_id or case["id"],
        "source": case["source"],
        "pattern_kind": case["pattern_kind"],
        "flags": case["flags"],
        "subjects": case.get("subjects", []),
    }
    if "maximum_matches" in case:
        result["maximum_matches"] = case["maximum_matches"]
    return result


def build_request(
    corpus: Mapping[str, Any], generated: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    cases = [request_case(case) for case in corpus["cases"]]
    cases.extend(request_case(case) for case in corpus["compile_error_cases"])
    rewrite_ids = []
    for rewrite in corpus["rewrite_cases"]:
        for variant in ("original", "rewritten"):
            case_id = f"rewrite:{rewrite['id']}:{variant}"
            rewrite_ids.append(case_id)
            cases.append(
                request_case(
                    {
                        **rewrite,
                        "id": case_id,
                        "source": rewrite[f"{variant}_source"],
                    }
                )
            )
    cases.extend(request_case(case) for case in generated)
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("runtime request case IDs must be unique")
    return {"protocol_version": PROTOCOL_VERSION, "cases": cases}, rewrite_ids


def run_harness(binary: Path, request: Mapping[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(
        request, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    environment = {"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC"}
    try:
        completed = subprocess.run(
            [str(binary), "-I", "-S", "-B", str(HARNESS)],
            input=encoded,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=ROOT,
            env=environment,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("CPython harness exceeded the 30-second timeout") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"CPython harness exited with code {completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("CPython harness returned malformed JSON") from exc
    if not isinstance(result, dict):
        raise TypeError("CPython harness result must be an object")
    return result


def runtime_identity(response: Mapping[str, Any]) -> dict[str, Any]:
    runtime = response.get("runtime")
    if not isinstance(runtime, Mapping):
        raise TypeError("CPython harness omitted runtime identity")
    return {
        "version": runtime.get("version"),
        "implementation": runtime.get("implementation"),
        "platform": runtime.get("platform"),
        "machine": runtime.get("machine"),
        "cache_tag": runtime.get("cache_tag"),
        "soabi": runtime.get("soabi"),
        "sysconfig_platform": runtime.get("sysconfig_platform"),
    }


def exact_runtime(runtime: Mapping[str, Any]) -> bool:
    return runtime == {
        "version": EXPECTED_VERSION,
        "implementation": EXPECTED_IMPLEMENTATION,
        "platform": EXPECTED_PLATFORM,
        "machine": EXPECTED_MACHINE,
        "cache_tag": EXPECTED_CACHE_TAG,
        "soabi": EXPECTED_SOABI,
        "sysconfig_platform": EXPECTED_SYSCONFIG_PLATFORM,
    }


def controller_identity() -> dict[str, Any]:
    return {
        "version": platform.python_version(),
        "implementation": platform.python_implementation().lower(),
        "platform": sys.platform,
        "machine": platform.machine(),
    }


def evaluate_response(
    response: Mapping[str, Any],
    request: Mapping[str, Any],
    corpus: Mapping[str, Any],
    generated: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if response.get("protocol_version") != PROTOCOL_VERSION:
        raise AssertionError("CPython harness protocol version differs")
    raw_results = response.get("cases")
    if not isinstance(raw_results, list) or not all(
        isinstance(item, Mapping) for item in raw_results
    ):
        raise AssertionError("CPython harness case results are malformed")
    requested_ids = [case["id"] for case in request["cases"]]
    actual_ids = [item.get("id") for item in raw_results]
    if actual_ids != requested_ids:
        raise AssertionError("CPython harness case order or identity differs")
    by_id = {item["id"]: item for item in raw_results}

    detailed = []
    for case in corpus["cases"]:
        actual = by_id[case["id"]]
        if (
            actual.get("compile", {}).get("status") != "ok"
            or actual.get("observations") != case["expected"]
        ):
            raise AssertionError(f"{case['id']}: runtime observations differ")
        detailed.append(actual)

    compile_errors = []
    for case in corpus["compile_error_cases"]:
        actual = by_id[case["id"]]
        if actual.get("compile") != case["expected_compile"]:
            raise AssertionError(f"{case['id']}: compile outcome differs")
        compile_errors.append(actual)

    rewrites = []
    for rewrite in corpus["rewrite_cases"]:
        original = by_id[f"rewrite:{rewrite['id']}:original"]
        rewritten = by_id[f"rewrite:{rewrite['id']}:rewritten"]
        if (
            original.get("compile", {}).get("status") != "ok"
            or rewritten.get("compile", {}).get("status") != "ok"
        ):
            raise AssertionError(f"{rewrite['id']}: rewrite comparison did not compile")
        if original.get("observations") != rewritten.get("observations"):
            raise AssertionError(f"{rewrite['id']}: rewrite observations differ")
        rewrites.append(
            {
                "id": rewrite["id"],
                "strategy_id": rewrite["strategy_id"],
                "observations": rewritten["observations"],
            }
        )

    generated_results = []
    for case in generated:
        actual = by_id[case["id"]]
        if (
            actual.get("compile", {}).get("status") != "ok"
            or actual.get("observations") != case["expected"]
        ):
            raise AssertionError(f"{case['id']}: generated observations differ")
        generated_results.append(actual)

    return {
        "detailed_cases": detailed,
        "compile_error_cases": compile_errors,
        "rewrite_cases": rewrites,
        "generated": {
            "seed": corpus["generated_cases"]["seed"],
            "count": len(generated_results),
            "result_sha256": canonical_digest(generated_results),
        },
    }


def result_digest(result: Mapping[str, Any]) -> str:
    projection = copy.deepcopy(result)
    projection.pop("deterministic_result_sha256", None)
    for check in projection.get("checks", []):
        evidence = check.get("evidence")
        if isinstance(evidence, dict):
            evidence.pop("timing_observations_microseconds", None)
    return canonical_digest(projection)


def structured_result(check: Mapping[str, Any]) -> dict[str, Any]:
    status = check["status"]
    result = {
        "certification_version": "1.0.0",
        "operation_id": OPERATION_ID,
        "status": status,
        "summary": {
            state: int(status == state)
            for state in ("passed", "failed", "waived", "unavailable", "incomplete")
        },
        "checks": [dict(check)],
    }
    return {**result, "deterministic_result_sha256": result_digest(result)}


def unavailable(reason: str) -> dict[str, Any]:
    return structured_result(
        {"check_id": CHECK_ID, "status": "unavailable", "unavailable_reason": reason}
    )


def run_certification(
    binary: Path | None,
    repeat_runs: int,
    runner: Callable[[Path, Mapping[str, Any]], dict[str, Any]] = run_harness,
    identity_reader: Callable[[Path], str] = file_digest,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    if repeat_runs < 2:
        raise ValueError("repeat_runs must be at least 2")
    corpus = load_json(CORPUS)
    validate_corpus_identity(corpus)
    generated = generated_cases(corpus["generated_cases"])
    request, _rewrite_ids = build_request(corpus, generated)

    if binary is None or not binary.is_file():
        return unavailable(
            f"exact CPython 3.11.15 binary is not available through {PYTHON_ENV}"
        )
    try:
        executable_sha256 = identity_reader(binary)
    except OSError:
        return unavailable("exact CPython executable identity is unreadable")
    if executable_sha256 != EXPECTED_EXECUTABLE_SHA256:
        return unavailable(
            "supplied CPython executable does not match the governed SHA-256"
        )

    semantic_digests = []
    durations = []
    runtime = None
    try:
        for _ in range(repeat_runs):
            started = clock()
            response = runner(binary, request)
            durations.append(round((clock() - started) * 1_000_000))
            observed_runtime = runtime_identity(response)
            if not exact_runtime(observed_runtime):
                return unavailable(
                    "supplied executable does not report the governed CPython 3.11.15 Linux x86-64 identity"
                )
            if runtime is not None and runtime != observed_runtime:
                raise AssertionError(
                    "repeated CPython runtime identity is nondeterministic"
                )
            runtime = observed_runtime
            semantic = evaluate_response(response, request, corpus, generated)
            semantic_digests.append(canonical_digest(semantic))
        if len(set(semantic_digests)) != 1:
            raise AssertionError(
                "repeated Python re semantic evidence is nondeterministic"
            )
        assert runtime is not None
        harness_sha256 = canonical_digest(
            {
                HARNESS.name: file_digest(HARNESS),
                Path(__file__).name: file_digest(Path(__file__).resolve()),
            }
        )
        controller = controller_identity()
        controller_sha256 = file_digest(Path(sys.executable))
        return structured_result(
            {
                "check_id": CHECK_ID,
                "status": "passed",
                "evidence": {
                    "runtime": runtime,
                    "archive": EXPECTED_ARCHIVE,
                    "archive_sha256": EXPECTED_ARCHIVE_SHA256,
                    "executable_sha256": executable_sha256,
                    "profiles": EXPECTED_PROFILES,
                    "corpus_sha256": canonical_digest(corpus),
                    "harness_sha256": harness_sha256,
                    "repeat_runs": repeat_runs,
                    "semantic_result_sha256": semantic_digests[0],
                    "detailed_cases": len(corpus["cases"]),
                    "compile_error_cases": len(corpus["compile_error_cases"]),
                    "rewrite_cases": len(corpus["rewrite_cases"]),
                    "generated_cases": len(generated),
                    "str_cases": sum(
                        case["pattern_kind"] == "str" for case in request["cases"]
                    ),
                    "bytes_cases": sum(
                        case["pattern_kind"] == "bytes" for case in request["cases"]
                    ),
                    "non_target_controller": {
                        **controller,
                        "executable_sha256": controller_sha256,
                        "accepted_as_target": controller_sha256
                        == EXPECTED_EXECUTABLE_SHA256,
                    },
                    "timing_observations_microseconds": durations,
                },
            }
        )
    except OSError:
        return unavailable("exact CPython executable could not be started")
    except (
        AssertionError,
        RuntimeError,
        subprocess.SubprocessError,
        ValueError,
    ) as exc:
        return structured_result(
            {
                "check_id": CHECK_ID,
                "status": "failed",
                "findings": [
                    {
                        "code": "PYTHON_RE_RUNTIME_CERTIFICATION_FAILED",
                        "message": str(exc),
                    }
                ],
            }
        )


def parse_binary() -> Path | None:
    return Path(value) if (value := os.environ.get(PYTHON_ENV)) else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repeat-runs", type=int, default=2)
    args = parser.parse_args()
    try:
        result = run_certification(parse_binary(), args.repeat_runs)
    except (OSError, RuntimeError, ValueError) as exc:
        result = structured_result(
            {
                "check_id": f"{OPERATION_ID}.configuration",
                "status": "incomplete",
                "findings": [
                    {
                        "code": "PYTHON_RE_RUNTIME_CERTIFICATION_INCOMPLETE",
                        "message": str(exc),
                    }
                ],
            }
        )
    serialized = json.dumps(
        result, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if args.json:
        print(serialized)
    else:
        print(
            f"Python re runtime certification: {result['status'].upper()} ({result['summary']})"
        )
    raise SystemExit(EXIT_CODES[result["status"]])


if __name__ == "__main__":
    main()
