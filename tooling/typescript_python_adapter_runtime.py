"""Execute deterministic TypeScript/WASM and Python/native adapter parity."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
BINDING_TYPESCRIPT = ROOT / "bindings" / "typescript"
BINDING_PYTHON = ROOT / "bindings" / "python"
NODE_PROBE = ROOT / "tests" / "adapters" / "2.0" / "runtime_probe.mjs"
PROFILE_PATH = ROOT / "spec" / "targets" / "profiles" / "pcre2-10.43.json"
OPERATION_ID = "certification.typescript-python-adapter-runtime"
CHECK_ID = f"{OPERATION_ID}.forty-four-case-parity"
EXPECTED_ACTION_COUNT = 44
EXPECTED_ACTION_FINGERPRINT = (
    "sha256:e45138d80f67e016214f2b90f01b161b1b39e2fefd70c1fbd5c10faba74219ed"
)
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2}

COMPILE_FIXTURES = (
    "source-success.json",
    "semantic-input.json",
    "regex-compat-success.json",
    "partial-failure.json",
    "target-artifact.json",
)
SIMPLY_FIXTURES = (
    ("1.0", "positive.json", "simply_success"),
    ("1.0", "negative.json", "simply_failure"),
    ("1.1", "positive.json", "simply_success"),
    ("1.1", "negative.json", "simply_failure"),
)


class AdapterRuntimeError(RuntimeError):
    """The live adapter parity proof failed."""


@dataclass(frozen=True)
class RuntimeReport:
    action_fingerprint: str
    action_count: int
    result_fingerprint: str
    repeat_runs: int
    node_version: str
    python_version: str


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdapterRuntimeError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise AdapterRuntimeError(f"{path} must contain one JSON object")
    return value


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fingerprint(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _unicode_request(root: Path, case_id: str, text: str) -> dict[str, Any]:
    request = _read_json(
        root
        / "spec"
        / "contracts"
        / "1.0"
        / "examples"
        / "compile-request"
        / "source-success.json"
    )
    document = request["input"]["document"]
    document["source_id"] = f"src:adapter-parity.{case_id}"
    document["content"]["text"] = text
    return request


def build_actions(root: Path = ROOT) -> list[dict[str, Any]]:
    profile = _read_json(root / "spec" / "targets" / "profiles" / "pcre2-10.43.json")
    compile_root = root / "spec" / "contracts" / "1.0" / "examples" / "compile-request"
    actions: list[dict[str, Any]] = [
        {"id": "parity-describe", "kind": "describe", "expect": "describe"}
    ]
    for name in COMPILE_FIXTURES:
        request = _read_json(compile_root / name)
        action: dict[str, Any] = {
            "id": f"compile-{Path(name).stem}",
            "kind": "compile",
            "request": request,
            "expect": "target_success" if name == "target-artifact.json" else "compile",
        }
        if name == "target-artifact.json":
            action["target_profile"] = profile
        actions.append(action)
    actions.append(
        {
            "id": "target-profile-inspect",
            "kind": "target_profile.inspect",
            "target_profile": profile,
            "expect": "target_profile",
        }
    )
    for version, filename, expectation in SIMPLY_FIXTURES:
        fixture = _read_json(
            root / "spec" / "frontends" / "simply" / version / "fixtures" / filename
        )
        cases = fixture.get("cases")
        if not isinstance(cases, list):
            raise AdapterRuntimeError(f"Simply {version}/{filename} has no case array")
        disposition = Path(filename).stem
        for case in cases:
            if not isinstance(case, dict) or not isinstance(case.get("request"), dict):
                raise AdapterRuntimeError(
                    f"Simply {version}/{filename} contains an invalid case"
                )
            request = copy.deepcopy(case["request"])
            action = {
                "id": f"simply-{version}-{disposition}-{case['case_id']}",
                "kind": "simply.compile",
                "request": request,
                "expect": expectation,
            }
            if request.get("compile", {}).get("target_profile") is not None:
                action["target_profile"] = profile
            actions.append(action)
    actions.extend(
        [
            {
                "id": "interop-unknown-operation",
                "kind": "raw",
                "request": {
                    "interop_protocol_version": "1.0.0",
                    "operation": "not-supported",
                    "payload": {},
                },
                "expect": "unknown_operation",
            },
            {
                "id": "interop-invalid-utf8",
                "kind": "invalid_utf8",
                "expect": "invalid_utf8",
            },
            {
                "id": "interop-request-limit",
                "kind": "oversize",
                "expect": "oversize",
            },
            {
                "id": "unicode-astral-scalar",
                "kind": "compile",
                "request": _unicode_request(root, "astral", "😀"),
                "expect": "compile",
            },
            {
                "id": "unicode-combining-sequence",
                "kind": "compile",
                "request": _unicode_request(root, "combining", "e\u0301"),
                "expect": "compile",
            },
        ]
    )
    ids = [str(action["id"]) for action in actions]
    if len(actions) != EXPECTED_ACTION_COUNT or len(ids) != len(set(ids)):
        raise AdapterRuntimeError("live adapter action denominator changed")
    fingerprint = _fingerprint(actions)
    if (
        EXPECTED_ACTION_FINGERPRINT != "TO_BE_REPLACED"
        and fingerprint != EXPECTED_ACTION_FINGERPRINT
    ):
        raise AdapterRuntimeError("live adapter action fingerprint changed")
    return actions


def _executable(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise FileNotFoundError(name)
    return resolved


def _run(
    arguments: Sequence[str],
    *,
    cwd: Path,
    input_text: str | None = None,
    timeout: int = 240,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise AdapterRuntimeError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail[-4000:]}"
        )
    return completed


def build_products() -> Path:
    _run([_executable("npm"), "run", "build"], cwd=BINDING_TYPESCRIPT)
    native = BINDING_PYTHON / "target" / "native"
    _run(
        [
            sys.executable,
            str(BINDING_PYTHON / "scripts" / "assemble_native.py"),
            "--output",
            str(native),
        ],
        cwd=ROOT,
    )
    names = {
        "win32": "strling_interop.dll",
        "darwin": "libstrling_interop.dylib",
    }
    library = native / names.get(sys.platform, "libstrling_interop.so")
    if not library.is_file():
        raise AdapterRuntimeError(f"native adapter library is missing: {library}")
    return library


def _python_results(
    actions: Sequence[Mapping[str, Any]], library: Path
) -> list[dict[str, Any]]:
    source = str(BINDING_PYTHON / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from STRling.interop import (  # pylint: disable=import-outside-toplevel
        MAX_INTEROP_REQUEST_BYTES,
        NativeClient,
    )

    client = NativeClient(library)
    results = []
    for action in actions:
        try:
            kind = action["kind"]
            if kind == "describe":
                value = client.describe()
            elif kind == "compile":
                value = client.compile(action["request"], action.get("target_profile"))
            elif kind == "target_profile.inspect":
                value = client.inspect_target_profile(action["target_profile"])
            elif kind == "simply.compile":
                value = client.simply_compile(
                    action["request"], action.get("target_profile")
                )
            elif kind == "raw":
                value = client.execute(action["request"])
            elif kind == "invalid_utf8":
                value = client.execute_bytes(b"\xff")
            elif kind == "oversize":
                value = client.execute_bytes(bytes(MAX_INTEROP_REQUEST_BYTES + 1))
            else:
                raise AdapterRuntimeError(f"unknown Python action kind: {kind}")
            results.append({"id": action["id"], "state": "value", "value": value})
        except Exception as error:
            results.append(
                {"id": action["id"], "state": "host_error", "message": str(error)}
            )
    return results


def _node_results(
    actions: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    completed = _run(
        [_executable("node"), str(NODE_PROBE)],
        cwd=ROOT,
        input_text=json.dumps(actions, ensure_ascii=False, allow_nan=False),
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AdapterRuntimeError(
            f"Node probe returned invalid JSON: {error}"
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise AdapterRuntimeError("Node probe returned an invalid payload")
    return str(payload.get("node_version", "")), payload["results"]


def assert_parity(
    actions: Sequence[Mapping[str, Any]],
    python_results: Sequence[Mapping[str, Any]],
    node_results: Sequence[Mapping[str, Any]],
) -> None:
    if python_results != node_results:
        for action, python_result, node_result in zip(
            actions, python_results, node_results
        ):
            if python_result != node_result:
                raise AdapterRuntimeError(
                    f"{action['id']}: Python/native and TypeScript/WASM differ: "
                    f"python={python_result!r} node={node_result!r}"
                )
        raise AdapterRuntimeError("adapter result counts differ")


def _validate_results(
    actions: Sequence[Mapping[str, Any]], results: Sequence[Mapping[str, Any]]
) -> None:
    if len(results) != len(actions):
        raise AdapterRuntimeError("live adapter result denominator changed")
    for action, result in zip(actions, results):
        if result.get("id") != action["id"]:
            raise AdapterRuntimeError("live adapter result order changed")
        expectation = action["expect"]
        if expectation == "oversize":
            if result != {
                "id": action["id"],
                "state": "host_error",
                "message": "interop request exceeds 10485760 bytes",
            }:
                raise AdapterRuntimeError("request-limit disposition differs")
            continue
        if result.get("state") != "value":
            raise AdapterRuntimeError(f"{action['id']}: unexpected host error")
        value = result.get("value")
        if expectation == "describe" and (
            not isinstance(value, dict)
            or value.get("protocol_version") != "1.0.0"
            or value.get("operations")
            != ["describe", "compile", "target_profile.inspect", "simply.compile"]
        ):
            raise AdapterRuntimeError(
                "describe result differs from the closed protocol"
            )
        if expectation == "target_success" and (
            not isinstance(value, dict) or value.get("outcome") != "succeeded"
        ):
            raise AdapterRuntimeError("exact target-artifact compile did not succeed")
        if expectation == "target_profile" and (
            not isinstance(value, dict)
            or value.get("profile_reference", {}).get("profile_id")
            != "profile:pcre2/10.43"
        ):
            raise AdapterRuntimeError("target profile inspection identity differs")
        if expectation == "simply_success" and (
            not isinstance(value, dict) or value.get("status") != "success"
        ):
            raise AdapterRuntimeError(f"{action['id']}: Simply success differs")
        if expectation == "simply_failure" and (
            not isinstance(value, dict) or value.get("status") != "failure"
        ):
            raise AdapterRuntimeError(f"{action['id']}: Simply failure differs")
        if expectation == "unknown_operation" and (
            not isinstance(value, dict)
            or value.get("error")
            != {"code": "STRL-INTEROP-0005", "path": "$.operation"}
        ):
            raise AdapterRuntimeError("unknown-operation identity differs")
        if expectation == "invalid_utf8" and (
            not isinstance(value, dict)
            or value.get("error") != {"code": "STRL-INTEROP-0001", "path": "$"}
        ):
            raise AdapterRuntimeError("invalid-UTF-8 identity differs")


def execute(repeat_runs: int) -> RuntimeReport:
    if repeat_runs < 2:
        raise AdapterRuntimeError("repeat_runs must be at least 2")
    actions = build_actions()
    library = build_products()
    observations = []
    node_version = ""
    for _ in range(repeat_runs):
        python_results = _python_results(actions, library)
        observed_node, node_results = _node_results(actions)
        assert_parity(actions, python_results, node_results)
        _validate_results(actions, python_results)
        observations.append(python_results)
        if node_version and observed_node != node_version:
            raise AdapterRuntimeError("Node runtime identity changed between runs")
        node_version = observed_node
    if any(run != observations[0] for run in observations[1:]):
        raise AdapterRuntimeError("live adapter results are nondeterministic")
    return RuntimeReport(
        action_fingerprint=_fingerprint(actions),
        action_count=len(actions),
        result_fingerprint=_fingerprint(observations[0]),
        repeat_runs=repeat_runs,
        node_version=node_version,
        python_version=platform.python_version(),
    )


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": dict(details)}],
    }


def certify(repeat_runs: int) -> tuple[dict[str, Any], int]:
    started = time.monotonic()
    try:
        report = execute(repeat_runs)
        return (
            _result(
                "passed",
                started,
                {
                    "action_count": report.action_count,
                    "action_fingerprint": report.action_fingerprint,
                    "node_version": report.node_version,
                    "python_version": report.python_version,
                    "repeat_runs": report.repeat_runs,
                    "result_fingerprint": report.result_fingerprint,
                },
            ),
            0,
        )
    except FileNotFoundError as error:
        return _result("unavailable", started, {"reason": str(error)}), EXIT_CODES[
            "unavailable"
        ]
    except Exception as error:
        return (
            _result(
                "failed",
                started,
                {
                    "error_type": type(error).__name__,
                    "host_platform": platform.platform(),
                    "reason": str(error),
                },
            ),
            EXIT_CODES["failed"],
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--repeat-runs", type=int, default=3)
    args = parser.parse_args(argv)
    payload, exit_code = certify(args.repeat_runs)
    if args.json_output:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"TYPESCRIPT_PYTHON_ADAPTER_RUNTIME status={payload['status']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
