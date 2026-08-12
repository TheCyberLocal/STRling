#!/usr/bin/env python3
"""Bounded standard-library harness for governed Python ``re`` artifacts."""

from __future__ import annotations

import json
import platform
import re
import sys
import sysconfig
from collections.abc import Mapping
from typing import Any

PROTOCOL_VERSION = "1.0.0"
MAXIMUM_INPUT_BYTES = 4 * 1024 * 1024
MAXIMUM_CASES = 1024
MAXIMUM_SUBJECTS_PER_CASE = 32
MAXIMUM_SOURCE_BYTES = 64 * 1024
MAXIMUM_SUBJECT_UNITS = 1024 * 1024
MAXIMUM_MATCHES = 1024


def require_record(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    return value


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{label} must be an array of strings")
    return value


def bounded_case(raw_case: Any) -> dict[str, Any]:
    item = require_record(raw_case, "case")
    case_id = require_string(item.get("id"), "case.id")
    source = require_string(item.get("source"), f"{case_id}.source")
    pattern_kind = require_string(
        item.get("pattern_kind"), f"{case_id}.pattern_kind"
    )
    if pattern_kind not in {"str", "bytes"}:
        raise ValueError(f"{case_id}.pattern_kind is unsupported")
    flags = require_string_list(item.get("flags"), f"{case_id}.flags")
    if flags not in ([], ["i"]):
        raise ValueError(f"{case_id}.flags must be canonical [] or ['i']")
    if len(source.encode("utf-8")) > MAXIMUM_SOURCE_BYTES:
        raise ValueError(f"{case_id}.source exceeds the byte limit")
    if pattern_kind == "bytes" and not source.isascii():
        raise ValueError(f"{case_id}.bytes source must be ASCII")
    raw_subjects = item.get("subjects", [])
    subjects = require_string_list(raw_subjects, f"{case_id}.subjects")
    if len(subjects) > MAXIMUM_SUBJECTS_PER_CASE:
        raise ValueError(f"{case_id}.subjects exceeds the count limit")
    if any(len(subject) > MAXIMUM_SUBJECT_UNITS * 2 for subject in subjects):
        raise ValueError(f"{case_id}.subject exceeds the encoded limit")
    if pattern_kind == "bytes":
        try:
            decoded_subjects = [bytes.fromhex(subject) for subject in subjects]
        except ValueError as exc:
            raise ValueError(f"{case_id}.bytes subject is not canonical hex") from exc
        if any(subject.hex() != encoded.lower() for subject, encoded in zip(decoded_subjects, subjects)):
            raise ValueError(f"{case_id}.bytes subject is not canonical lowercase hex")
        if any(len(subject) > MAXIMUM_SUBJECT_UNITS for subject in decoded_subjects):
            raise ValueError(f"{case_id}.bytes subject exceeds the byte limit")
    else:
        decoded_subjects = subjects
        if any(len(subject) > MAXIMUM_SUBJECT_UNITS for subject in subjects):
            raise ValueError(f"{case_id}.str subject exceeds the scalar limit")
    maximum_matches = item.get("maximum_matches", MAXIMUM_MATCHES)
    if (
        not isinstance(maximum_matches, int)
        or isinstance(maximum_matches, bool)
        or maximum_matches < 1
        or maximum_matches > MAXIMUM_MATCHES
    ):
        raise ValueError(f"{case_id}.maximum_matches is outside the limit")
    return {
        "id": case_id,
        "source": source,
        "pattern_kind": pattern_kind,
        "flags": flags,
        "encoded_subjects": subjects,
        "subjects": decoded_subjects,
        "maximum_matches": maximum_matches,
    }


def encoded_value(value: str | bytes | None, pattern_kind: str) -> str | None:
    if value is None:
        return None
    if pattern_kind == "bytes":
        assert isinstance(value, bytes)
        return value.hex()
    assert isinstance(value, str)
    return value


def project_match(
    match: re.Match[str] | re.Match[bytes],
    names_by_slot: Mapping[int, str],
    pattern_kind: str,
) -> dict[str, Any]:
    captures = []
    for index in range(len(match.groups()) + 1):
        span = match.span(index)
        capture: dict[str, Any] = {
            "index": index,
            "span": None if span == (-1, -1) else [span[0], span[1]],
            "value": encoded_value(match.group(index), pattern_kind),
        }
        if index in names_by_slot:
            capture["name"] = names_by_slot[index]
        captures.append(capture)
    full_span = match.span(0)
    return {
        "span": [full_span[0], full_span[1]],
        "value": encoded_value(match.group(0), pattern_kind),
        "captures": captures,
    }


def run_case(raw_case: Any) -> dict[str, Any]:
    item = bounded_case(raw_case)
    source: str | bytes = item["source"]
    if item["pattern_kind"] == "bytes":
        source = source.encode("ascii")
    flags = re.IGNORECASE if item["flags"] == ["i"] else re.NOFLAG
    try:
        compiled = re.compile(source, flags)
    except (re.error, OverflowError) as exc:
        return {
            "id": item["id"],
            "compile": {
                "status": "error",
                "type": type(exc).__name__,
                "position": getattr(exc, "pos", None),
            },
            "observations": [],
        }
    names_by_slot = {slot: name for name, slot in compiled.groupindex.items()}
    observations = []
    for encoded_subject, subject in zip(item["encoded_subjects"], item["subjects"]):
        matches = []
        for match in compiled.finditer(subject):
            if len(matches) >= item["maximum_matches"]:
                raise ValueError(f"{item['id']}: match count exceeds the limit")
            matches.append(project_match(match, names_by_slot, item["pattern_kind"]))
        observations.append({"subject": encoded_subject, "matches": matches})
    return {
        "id": item["id"],
        "compile": {
            "status": "ok",
            "groups": compiled.groups,
            "groupindex": dict(sorted(compiled.groupindex.items())),
        },
        "observations": observations,
    }


def read_request() -> Mapping[str, Any]:
    encoded = sys.stdin.buffer.read(MAXIMUM_INPUT_BYTES + 1)
    if len(encoded) > MAXIMUM_INPUT_BYTES:
        raise ValueError("request exceeds the byte limit")
    request = require_record(json.loads(encoded.decode("utf-8")), "request")
    if request.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("unsupported protocol version")
    cases = request.get("cases")
    if not isinstance(cases, list) or len(cases) > MAXIMUM_CASES:
        raise ValueError("request.cases exceeds the count limit")
    return request


def runtime_identity() -> dict[str, Any]:
    return {
        "version": platform.python_version(),
        "implementation": platform.python_implementation().lower(),
        "platform": sys.platform,
        "machine": platform.machine(),
        "cache_tag": sys.implementation.cache_tag,
        "soabi": sysconfig.get_config_var("SOABI"),
        "sysconfig_platform": sysconfig.get_platform(),
    }


def main() -> None:
    try:
        request = read_request()
        result = {
            "protocol_version": PROTOCOL_VERSION,
            "runtime": runtime_identity(),
            "cases": [run_case(item) for item in request["cases"]],
        }
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    except (AssertionError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "fatal": {"code": "HARNESS_ERROR", "type": type(exc).__name__},
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
