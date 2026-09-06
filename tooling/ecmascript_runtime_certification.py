#!/usr/bin/env python3
"""Certify bounded ECMAScript artifacts on one exact Node/V8 runtime."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "conformance" / "ecmascript-runtime-certification.json"
HARNESS = ROOT / "tooling" / "node_regexp_harness.mjs"
NODE_ENV = "STRLING_NODE_22_BINARY"
EXPECTED_NODE = "v22.23.2"
EXPECTED_V8 = "12.4.254.21-node.56"
EXPECTED_PLATFORM = "linux"
EXPECTED_ARCHITECTURE = "x64"
EXPECTED_ARCHIVE = "node-v22.23.2-linux-x64.tar.xz"
EXPECTED_ARCHIVE_SHA256 = (
    "d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307"
)
EXPECTED_EXECUTABLE_SHA256 = (
    "3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327"
)
EXPECTED_PROFILE_SHA256 = (
    "5b012d7b0536610d4496718e6954c8f9ec80c16dde26a18f70663d0275ec333e"
)
PROTOCOL_VERSION = "1.0.0"
OPERATION_ID = "certification.ecmascript-runtime"
CHECK_ID = f"{OPERATION_ID}.node-v22.23.2"
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
        raise ValueError(f"{path} must contain a JSON object")
    return value


def utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def exact_observation(subject: str, value: str) -> dict[str, Any]:
    end = utf16_units(value)
    return {
        "subject": subject,
        "matches": [
            {
                "span": [0, end],
                "value": value,
                "captures": [{"index": 0, "span": [0, end], "value": value}],
            }
        ],
    }


def generated_cases(configuration: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Create deterministic bounded syntax and observation cases."""

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
            source = rf"^(?:{positive})(?![\s\S])"
            subjects = [positive, positive + "x"]
            expected = [
                exact_observation(positive, positive),
                {"subject": subjects[1], "matches": []},
            ]
            capture_names: dict[str, str] = {}
            flags = ["u"]
        elif kind == 1:
            name = f"g{index}"
            source = rf"^(?<{name}>{letter}{{{width}}})\k<{name}>(?![\s\S])"
            doubled = positive * 2
            subjects = [doubled, doubled + "x"]
            end = utf16_units(doubled)
            middle = utf16_units(positive)
            expected = [
                {
                    "subject": doubled,
                    "matches": [
                        {
                            "span": [0, end],
                            "value": doubled,
                            "captures": [
                                {"index": 0, "span": [0, end], "value": doubled},
                                {
                                    "index": 1,
                                    "name": name,
                                    "span": [0, middle],
                                    "value": positive,
                                },
                            ],
                        }
                    ],
                },
                {"subject": subjects[1], "matches": []},
            ]
            capture_names = {"1": name}
            flags = ["u"]
        elif kind == 2:
            source = rf"(?<=ab){letter}{{{width}}}(?!{letter})"
            matching = f"xxab{positive}!"
            missing_prefix = f"xxac{positive}!"
            subjects = [matching, missing_prefix]
            start = 4
            end = start + utf16_units(positive)
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
            capture_names = {}
            flags = ["u"]
        else:
            source = rf"^(?:{letter}|{letter.upper()}){{{width}}}(?![\s\S])"
            subjects = [positive, "0" * width]
            expected = [
                exact_observation(positive, positive),
                {"subject": subjects[1], "matches": []},
            ]
            capture_names = {}
            flags = ["u"]
        cases.append(
            {
                "id": case_id,
                "source": source,
                "flags": flags,
                "capture_names": capture_names,
                "subjects": subjects,
                "expected": expected,
            }
        )

    maximum_source = configuration["maximum_source_bytes"]
    maximum_subject = configuration["maximum_subject_utf16_units"]
    if any(len(case["source"].encode("utf-8")) > maximum_source for case in cases):
        raise ValueError("generated source exceeds governed byte maximum")
    if any(
        utf16_units(subject) > maximum_subject
        for case in cases
        for subject in case["subjects"]
    ):
        raise ValueError("generated subject exceeds governed UTF-16 maximum")
    return cases


def validate_corpus_identity(corpus: Mapping[str, Any]) -> None:
    runtime = corpus.get("runtime")
    profile = corpus.get("profile")
    expected_runtime = {
        "node_version": EXPECTED_NODE,
        "v8_version": EXPECTED_V8,
        "platform": EXPECTED_PLATFORM,
        "architecture": EXPECTED_ARCHITECTURE,
        "archive": EXPECTED_ARCHIVE,
        "archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "executable_sha256": EXPECTED_EXECUTABLE_SHA256,
    }
    if not isinstance(runtime, Mapping) or any(
        runtime.get(key) != value for key, value in expected_runtime.items()
    ):
        raise ValueError("runtime corpus identity differs from the governed Node pin")
    if (
        not isinstance(profile, Mapping)
        or profile.get("sha256") != EXPECTED_PROFILE_SHA256
    ):
        raise ValueError("runtime corpus profile differs from the governed profile pin")


def request_case(
    case: Mapping[str, Any], *, case_id: str | None = None
) -> dict[str, Any]:
    result = {
        "id": case_id or case["id"],
        "source": case["source"],
        "flags": case["flags"],
        "subjects": case.get("subjects", []),
    }
    for key in ("capture_names", "mode", "maximum_matches"):
        if key in case:
            result[key] = case[key]
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
                        "id": case_id,
                        "source": rewrite[f"{variant}_source"],
                        "flags": rewrite["flags"],
                        "subjects": rewrite["subjects"],
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
            [str(binary), "--no-warnings", str(HARNESS)],
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
        raise RuntimeError("Node harness exceeded the 30-second timeout") from exc
    if completed.returncode != 0:
        raise RuntimeError(f"Node harness exited with code {completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Node harness returned malformed JSON") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Node harness result must be an object")
    return result


def runtime_identity(response: Mapping[str, Any]) -> dict[str, Any]:
    runtime = response.get("runtime")
    if not isinstance(runtime, Mapping):
        raise ValueError("Node harness omitted runtime identity")
    return {
        "node": runtime.get("node"),
        "v8": runtime.get("v8"),
        "platform": runtime.get("platform"),
        "architecture": runtime.get("architecture"),
    }


def exact_runtime(runtime: Mapping[str, Any]) -> bool:
    return runtime == {
        "node": EXPECTED_NODE,
        "v8": EXPECTED_V8,
        "platform": EXPECTED_PLATFORM,
        "architecture": EXPECTED_ARCHITECTURE,
    }


def evaluate_response(
    response: Mapping[str, Any],
    request: Mapping[str, Any],
    corpus: Mapping[str, Any],
    generated: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if response.get("protocol_version") != PROTOCOL_VERSION:
        raise AssertionError("Node harness protocol version differs")
    raw_results = response.get("cases")
    if not isinstance(raw_results, list) or not all(
        isinstance(item, Mapping) for item in raw_results
    ):
        raise AssertionError("Node harness case results are malformed")
    requested_ids = [case["id"] for case in request["cases"]]
    actual_ids = [item.get("id") for item in raw_results]
    if actual_ids != requested_ids:
        raise AssertionError("Node harness case order or identity differs")
    by_id = {item["id"]: item for item in raw_results}

    detailed = []
    for case in corpus["cases"]:
        actual = by_id[case["id"]]
        if (
            actual.get("compile") != "ok"
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
        if original.get("compile") != "ok" or rewritten.get("compile") != "ok":
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
            actual.get("compile") != "ok"
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
        {
            "check_id": CHECK_ID,
            "status": "unavailable",
            "unavailable_reason": reason,
        }
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
            f"exact Node v22.23.2 binary is not available through {NODE_ENV}"
        )
    try:
        executable_sha256 = identity_reader(binary)
    except OSError:
        return unavailable("exact Node executable identity is unreadable")
    if executable_sha256 != EXPECTED_EXECUTABLE_SHA256:
        return unavailable(
            "supplied Node executable does not match the governed SHA-256"
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
                    "supplied executable does not report the governed Node/V8 Linux x64 identity"
                )
            if runtime is not None and runtime != observed_runtime:
                raise AssertionError(
                    "repeated Node runtime identity is nondeterministic"
                )
            runtime = observed_runtime
            semantic = evaluate_response(response, request, corpus, generated)
            semantic_digests.append(canonical_digest(semantic))
        if len(set(semantic_digests)) != 1:
            raise AssertionError(
                "repeated ECMAScript semantic evidence is nondeterministic"
            )
        assert runtime is not None
        harness_sha256 = canonical_digest(
            {
                HARNESS.name: file_digest(HARNESS),
                Path(__file__).name: file_digest(Path(__file__).resolve()),
            }
        )
        return structured_result(
            {
                "check_id": CHECK_ID,
                "status": "passed",
                "evidence": {
                    "runtime": runtime,
                    "archive": EXPECTED_ARCHIVE,
                    "archive_sha256": EXPECTED_ARCHIVE_SHA256,
                    "executable_sha256": executable_sha256,
                    "profile_sha256": EXPECTED_PROFILE_SHA256,
                    "corpus_sha256": canonical_digest(corpus),
                    "harness_sha256": harness_sha256,
                    "repeat_runs": repeat_runs,
                    "semantic_result_sha256": semantic_digests[0],
                    "detailed_cases": len(corpus["cases"]),
                    "compile_error_cases": len(corpus["compile_error_cases"]),
                    "rewrite_cases": len(corpus["rewrite_cases"]),
                    "generated_cases": len(generated),
                    "timing_observations_microseconds": durations,
                },
            }
        )
    except OSError:
        return unavailable("exact Node executable could not be started")
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
                        "code": "ECMASCRIPT_RUNTIME_CERTIFICATION_FAILED",
                        "message": str(exc),
                    }
                ],
            }
        )


def parse_binary() -> Path | None:
    return Path(value) if (value := os.environ.get(NODE_ENV)) else None


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
                        "code": "ECMASCRIPT_RUNTIME_CERTIFICATION_INCOMPLETE",
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
            f"ECMAScript runtime certification: {result['status'].upper()} "
            f"({result['summary']})"
        )
    raise SystemExit(EXIT_CODES[result["status"]])


if __name__ == "__main__":
    main()
