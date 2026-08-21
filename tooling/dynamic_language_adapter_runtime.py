#!/usr/bin/env python3
"""Execute repeated Ruby, PHP, Perl, Lua, and R strling.c-abi transport proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
OPERATION_ID = "certification.dynamic-language-adapter-runtime"
CHECK_ID = f"{OPERATION_ID}.cross-language-transport"
BINDINGS = ("ruby", "php", "perl", "lua", "r")
OPERATIONS = ("describe", "compile", "target_profile.inspect", "simply.compile")
EXIT_CODES = {"passed": 0, "failed": 1, "unavailable": 2}
EXPECTED_RESULT = {"unicode": "雪"}

PROBE_SOURCE = r"""
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <windows.h>
#endif

#if !defined(STRLING_PROBE_ABI)
#define STRLING_PROBE_ABI 1
#endif

#if !defined(STRLING_PROBE_RELEASE_STATUS)
#define STRLING_PROBE_RELEASE_STATUS 0
#endif

#if !defined(STRLING_PROBE_SPIN)
#define STRLING_PROBE_SPIN 0u
#endif

#if defined(_WIN32)
#define STRLING_EXPORT __declspec(dllexport)
#else
#define STRLING_EXPORT __attribute__((visibility("default")))
#endif

typedef struct { uint8_t *data; size_t len; } strling_owned_bytes;
#if defined(_WIN32)
__declspec(thread) static int outstanding = 0;
#else
static _Thread_local int outstanding = 0;
#endif

static int strling_valid_utf8(const uint8_t *data, size_t len) {
  size_t index = 0;
  while (index < len) {
    uint8_t lead = data[index++];
    uint32_t value;
    size_t continuation;
    uint32_t minimum;
    if (lead <= 0x7fu) continue;
    if ((lead & 0xe0u) == 0xc0u) {
      value = lead & 0x1fu; continuation = 1; minimum = 0x80u;
    } else if ((lead & 0xf0u) == 0xe0u) {
      value = lead & 0x0fu; continuation = 2; minimum = 0x800u;
    } else if ((lead & 0xf8u) == 0xf0u) {
      value = lead & 0x07u; continuation = 3; minimum = 0x10000u;
    } else {
      return 0;
    }
    if (continuation > len - index) return 0;
    while (continuation-- != 0) {
      uint8_t byte = data[index++];
      if ((byte & 0xc0u) != 0x80u) return 0;
      value = (value << 6) | (byte & 0x3fu);
    }
    if (value < minimum || value > 0x10ffffu ||
        (value >= 0xd800u && value <= 0xdfffu)) return 0;
  }
  return 1;
}

#if defined(STRLING_PROBE_DUPLICATE)
static const uint8_t response[] =
  "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
  "\"status\":\"completed\",\"result\":{},\"result\":{}}";
#elif defined(STRLING_PROBE_INVALID_UTF8)
static const uint8_t response[] =
  "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
  "\"status\":\"completed\",\"result\":\"\xff\"}";
#else
static const uint8_t response[] =
  "{\"interop_protocol_version\":\"1.0.0\",\"operation\":\"describe\","
  "\"status\":\"completed\",\"result\":{\"unicode\":\"\xe9\x9b\xaa\"}}";
#endif

STRLING_EXPORT uint32_t strling_interop_abi_version_v1(void) { return STRLING_PROBE_ABI; }

STRLING_EXPORT uint32_t strling_interop_execute_v1(
  const uint8_t *input, size_t input_len, strling_owned_bytes *output
) {
  if ((input == NULL && input_len != 0u) ||
      !strling_valid_utf8(input, input_len)) return 93;
  if (outstanding != 0) return 91;
  outstanding = 1;
  for (volatile uint32_t spin = 0; spin < STRLING_PROBE_SPIN; ++spin) { }
#if defined(STRLING_PROBE_OVERSIZE)
  output->data = (uint8_t *)(uintptr_t)response;
  output->len = 33554433u;
#else
  output->len = sizeof(response) - 1u;
  output->data = (uint8_t *)malloc(output->len);
  if (output->data == NULL) return 92;
  memcpy(output->data, response, output->len);
#endif
  return 0;
}

STRLING_EXPORT uint32_t strling_interop_owned_bytes_free_v1(strling_owned_bytes *output) {
#if !defined(STRLING_PROBE_OVERSIZE)
  free(output->data);
#endif
  output->data = NULL; output->len = 0;
  outstanding = 0;
  return STRLING_PROBE_RELEASE_STATUS;
}
"""


class DynamicLanguageRuntimeError(RuntimeError):
    """The shared dynamic-language runtime proof failed."""


@dataclass(frozen=True)
class RuntimeReport:
    executed_bindings: tuple[str, ...]
    repeat_runs: int
    probe_count: int
    operation_count: int
    semantic_copy_count: int
    result_fingerprint: str
    platform: str
    tool_versions: Mapping[str, str]


def _tool(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise FileNotFoundError(name)
    return resolved


def _run(
    arguments: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int = 900,
) -> str:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        env=dict(environment),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-8000:]
        raise DynamicLanguageRuntimeError(
            f"{' '.join(arguments)} failed with {completed.returncode}: {detail}"
        )
    return completed.stdout + completed.stderr


def _version(text: str, pattern: str, label: str) -> tuple[int, ...]:
    match = re.search(pattern, text)
    if match is None:
        raise DynamicLanguageRuntimeError(
            f"cannot parse governed {label} version from {text!r}"
        )
    return tuple(int(part) for part in match.group(1).split("."))


def _assert_versions(versions: Mapping[str, str]) -> None:
    ruby = _version(versions["ruby"], r"ruby (\d+(?:\.\d+){1,2})", "Ruby")
    php = _version(versions["php"], r"PHP (\d+(?:\.\d+){1,2})", "PHP")
    perl = _version(versions["perl"], r"v(\d+(?:\.\d+){1,2})", "Perl")
    lua = _version(versions["lua"], r"Lua (\d+(?:\.\d+){1,2})", "Lua")
    r_version = _version(versions["r"], r"version (\d+(?:\.\d+){1,2})", "R")
    constraints = {
        "Ruby": 3 <= ruby[0] < 4,
        "PHP": (8, 2) <= php[:2] < (9, 0),
        "Perl": (5, 10) <= perl[:2] < (6, 0),
        "Lua": (5, 1) <= lua[:2] < (5, 5),
        "R": (4, 3) <= r_version[:2] < (5, 0),
    }
    failed = [name for name, accepted in constraints.items() if not accepted]
    if failed:
        raise DynamicLanguageRuntimeError(
            f"tool versions outside governed ranges: {failed}"
        )


def _semantic_copy_count() -> int:
    baseline = json.loads(
        (ROOT / "tests/adapters/dynamic-languages-3.0/legacy-baseline.json").read_text(
            encoding="utf-8"
        )
    )
    paths = tuple(item["path"] for item in baseline["semantic_copy_files"])
    remaining = tuple(path for path in paths if (ROOT / path).exists())
    if remaining:
        raise DynamicLanguageRuntimeError(
            f"historical semantic copies remain: {remaining[:5]}"
        )
    return len(paths)


def _build_probe(
    compiler: str, root: Path, name: str, definitions: Sequence[str]
) -> Path:
    source = root / f"{name}.c"
    source.write_text(PROBE_SOURCE, encoding="utf-8", newline="\n")
    if sys.platform == "win32":
        output = root / f"{name}.dll"
        command = [
            compiler,
            "-shared",
            "-O2",
            *definitions,
            str(source),
            "-o",
            str(output),
        ]
    elif sys.platform == "darwin":
        output = root / f"lib{name}.dylib"
        command = [
            compiler,
            "-dynamiclib",
            "-O2",
            *definitions,
            str(source),
            "-o",
            str(output),
        ]
    else:
        output = root / f"lib{name}.so"
        command = [
            compiler,
            "-shared",
            "-fPIC",
            "-O2",
            *definitions,
            str(source),
            "-o",
            str(output),
        ]
    _run(command, cwd=root, environment=os.environ)
    if not output.is_file():
        raise DynamicLanguageRuntimeError(f"probe was not created: {output}")
    return output


def _commands(tools: Mapping[str, str]) -> dict[str, tuple[Path, list[str]]]:
    return {
        "ruby": (
            ROOT / "bindings/ruby",
            [tools["bundle"], "exec", "ruby", "-Ilib:test", "test/adapter_test.rb"],
        ),
        "php": (
            ROOT / "bindings/php",
            [str(ROOT / "bindings/php/vendor/bin/phpunit"), "tests/AdapterTest.php"],
        ),
        "perl": (ROOT / "bindings/perl", [tools["prove"], "-lv", "t/adapter.t"]),
        "lua": (
            ROOT / "bindings/lua",
            [tools["busted"], "-v", "-o", "plainTerminal", "spec/adapter_spec.lua"],
        ),
        "r": (ROOT / "bindings/r", [tools["sh"], "run_tests.sh"]),
    }


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _read_observation(root: Path, binding: str) -> dict[str, Any]:
    path = root / f"{binding}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DynamicLanguageRuntimeError(
            f"cannot read {binding} runtime observation: {error}"
        ) from error
    if not isinstance(value, dict) or set(value) != set(OPERATIONS):
        raise DynamicLanguageRuntimeError(
            f"{binding} runtime observation has an invalid operation set"
        )
    drifted = tuple(
        operation for operation in OPERATIONS if value[operation] != EXPECTED_RESULT
    )
    if drifted:
        raise DynamicLanguageRuntimeError(
            f"{binding} runtime observation drifted for {drifted!r}"
        )
    return value


def execute(repeat_runs: int) -> RuntimeReport:
    if repeat_runs < 2:
        raise DynamicLanguageRuntimeError("repeat_runs must be at least 2")
    tool_names = (
        "ruby",
        "php",
        "perl",
        "lua",
        "Rscript",
        "bundle",
        "prove",
        "busted",
        "sh",
        "cc",
    )
    tools = {name: _tool(name) for name in tool_names}
    versions = {
        "ruby": _run(
            [tools["ruby"], "--version"], cwd=ROOT, environment=os.environ
        ).strip(),
        "php": _run(
            [tools["php"], "--version"], cwd=ROOT, environment=os.environ
        ).strip(),
        "perl": _run(
            [tools["perl"], "-e", "print $^V"], cwd=ROOT, environment=os.environ
        ).strip(),
        "lua": _run([tools["lua"], "-v"], cwd=ROOT, environment=os.environ).strip(),
        "r": _run(
            [tools["Rscript"], "--version"], cwd=ROOT, environment=os.environ
        ).strip(),
    }
    _assert_versions(versions)
    semantic_count = _semantic_copy_count()
    commands = _commands(tools)
    target = ROOT / "target"
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="dynamic-adapter-", dir=target
    ) as directory:
        probe_root = Path(directory)
        probes = {
            "STRLING_DYNAMIC_PROBE": _build_probe(
                tools["cc"], probe_root, "release", ()
            ),
            "STRLING_DYNAMIC_ABI_PROBE": _build_probe(
                tools["cc"], probe_root, "abi", ("-DSTRLING_PROBE_ABI=2",)
            ),
            "STRLING_DYNAMIC_OVERSIZE_PROBE": _build_probe(
                tools["cc"], probe_root, "oversize", ("-DSTRLING_PROBE_OVERSIZE=1",)
            ),
            "STRLING_DYNAMIC_DUPLICATE_PROBE": _build_probe(
                tools["cc"], probe_root, "duplicate", ("-DSTRLING_PROBE_DUPLICATE=1",)
            ),
            "STRLING_DYNAMIC_INVALID_UTF8_PROBE": _build_probe(
                tools["cc"],
                probe_root,
                "invalid_utf8",
                ("-DSTRLING_PROBE_INVALID_UTF8=1",),
            ),
            "STRLING_DYNAMIC_RELEASE_FAILURE_PROBE": _build_probe(
                tools["cc"],
                probe_root,
                "release_failure",
                ("-DSTRLING_PROBE_RELEASE_STATUS=94",),
            ),
            "STRLING_DYNAMIC_CONCURRENCY_PROBE": _build_probe(
                tools["cc"],
                probe_root,
                "concurrency",
                ("-DSTRLING_PROBE_SPIN=5000000u",),
            ),
        }
        base_environment = os.environ.copy()
        base_environment.update(
            {name: str(path.resolve()) for name, path in probes.items()}
        )
        base_environment.update({"CI": "true", "NO_COLOR": "1"})
        observations = []
        for index in range(repeat_runs):
            run_root = probe_root / f"run-{index + 1}"
            run_root.mkdir()
            environment = dict(base_environment)
            environment["STRLING_DYNAMIC_EVIDENCE_DIR"] = str(run_root)
            for binding in BINDINGS:
                cwd, command = commands[binding]
                _run(command, cwd=cwd, environment=environment)
            per_binding = {
                binding: _read_observation(run_root, binding) for binding in BINDINGS
            }
            first = per_binding[BINDINGS[0]]
            differing = tuple(
                binding for binding in BINDINGS[1:] if per_binding[binding] != first
            )
            if differing:
                raise DynamicLanguageRuntimeError(
                    f"run {index + 1}: canonical results differ for {differing!r}"
                )
            observations.append(first)
    if any(item != observations[0] for item in observations[1:]):
        raise DynamicLanguageRuntimeError(
            "dynamic-language adapter results are nondeterministic"
        )
    return RuntimeReport(
        executed_bindings=BINDINGS,
        repeat_runs=repeat_runs,
        probe_count=7,
        operation_count=len(OPERATIONS),
        semantic_copy_count=semantic_count,
        result_fingerprint=_fingerprint(observations[0]),
        platform=platform.platform(),
        tool_versions=versions,
    )


def _result(status: str, started: float, details: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "certification-result-v1",
        "operation_id": OPERATION_ID,
        "status": status,
        "duration_ms": max(0, int((time.monotonic() - started) * 1000)),
        "checks": [{"id": CHECK_ID, "status": status, "details": dict(details)}],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat-runs", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    started = time.monotonic()
    try:
        report = execute(arguments.repeat_runs)
    except FileNotFoundError as error:
        payload = _result("unavailable", started, {"missing": str(error)})
    except (DynamicLanguageRuntimeError, OSError, subprocess.SubprocessError) as error:
        payload = _result("failed", started, {"error": str(error)})
    else:
        payload = _result("passed", started, asdict(report))
    print(json.dumps(payload, sort_keys=True) if arguments.json else payload)
    return EXIT_CODES[str(payload["status"])]


if __name__ == "__main__":
    raise SystemExit(main())
