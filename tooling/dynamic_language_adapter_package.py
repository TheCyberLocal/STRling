#!/usr/bin/env python3
"""Project and verify dynamic-language adapter release dependency graphs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "tests/adapters/dynamic-languages-3.0/release-graphs.json"
BINDINGS = ("ruby", "php", "perl", "lua", "r")


class DynamicLanguagePackageError(RuntimeError):
    """A package manifest or governed release graph is incomplete."""


def _fingerprint(value: Mapping[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "fingerprint"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _ruby_graph() -> dict[str, Any]:
    lock = (ROOT / "bindings/ruby/Gemfile.lock").read_text(encoding="utf-8")
    packages = []
    seen: set[str] = set()
    for match in re.finditer(
        r"^    ([A-Za-z0-9_.-]+) \(([^)]+)\)$", lock, re.MULTILINE
    ):
        coordinate = f"{match.group(1)}:{match.group(2)}"
        if match.group(1) != "strling" and coordinate not in seen:
            seen.add(coordinate)
            packages.append(
                {
                    "coordinate": coordinate,
                    "scope": "test",
                    "license_status": "live-query-required",
                }
            )
    if not packages:
        raise DynamicLanguagePackageError("Ruby lock contains no resolved test graph")
    return {
        "manifest": "bindings/ruby/strling.gemspec",
        "lock": "bindings/ruby/Gemfile.lock",
        "runtime_dependencies": [],
        "resolved_packages": packages,
        "native_payload_packaged": False,
    }


def _php_graph() -> dict[str, Any]:
    lock = json.loads((ROOT / "bindings/php/composer.lock").read_text(encoding="utf-8"))
    packages = []
    for scope, field in (("runtime", "packages"), ("test", "packages-dev")):
        for item in lock[field]:
            packages.append(
                {
                    "coordinate": f"{item['name']}:{item['version']}",
                    "scope": scope,
                    "licenses": sorted(item.get("license", [])),
                }
            )
    return {
        "manifest": "bindings/php/composer.json",
        "lock": "bindings/php/composer.lock",
        "runtime_dependencies": ["ext-ffi:*", "ext-json:*"],
        "resolved_packages": packages,
        "native_payload_packaged": False,
    }


def _perl_graph() -> dict[str, Any]:
    manifest = (ROOT / "bindings/perl/Makefile.PL").read_text(encoding="utf-8")
    required = {
        name: version
        for name, version in re.findall(
            r"^\s*'(FFI::Platypus|JSON::PP)'\s*=>\s*'([^']+)'", manifest, re.MULTILINE
        )
    }
    if required != {"FFI::Platypus": "2.10", "JSON::PP": "4.00"}:
        raise DynamicLanguagePackageError(f"unexpected Perl runtime graph: {required}")
    return {
        "manifest": "bindings/perl/Makefile.PL",
        "lock": None,
        "runtime_dependencies": [
            f"{name}:>={version}" for name, version in sorted(required.items())
        ],
        "resolved_packages": [],
        "resolution_status": "live-resolution-required",
        "native_payload_packaged": False,
    }


def _lua_graph() -> dict[str, Any]:
    rockspec = (ROOT / "bindings/lua/strling-template.rockspec").read_text(
        encoding="utf-8"
    )
    dependencies = re.findall(r'^\s*"([^"]+)",?$', rockspec, re.MULTILINE)
    runtime = [item for item in dependencies if not item.startswith("lua ")]
    if runtime != ["lua-cjson >= 2.1.0, < 3.0.0"]:
        raise DynamicLanguagePackageError(f"unexpected Lua runtime graph: {runtime}")
    return {
        "manifest": "bindings/lua/strling-template.rockspec",
        "lock": None,
        "runtime_dependencies": runtime,
        "resolved_packages": [],
        "resolution_status": "live-resolution-required",
        "native_payload_packaged": False,
    }


def _r_graph() -> dict[str, Any]:
    description = (ROOT / "bindings/r/DESCRIPTION").read_text(encoding="utf-8")
    imports = re.search(r"(?m)^Imports:\s*(.+)$", description)
    suggests = re.search(r"(?m)^Suggests:\s*(.+)$", description)
    if imports is None or suggests is None:
        raise DynamicLanguagePackageError("R DESCRIPTION omits Imports or Suggests")
    return {
        "manifest": "bindings/r/DESCRIPTION",
        "lock": None,
        "runtime_dependencies": [imports.group(1).strip()],
        "test_dependencies": [suggests.group(1).strip()],
        "resolved_packages": [],
        "resolution_status": "live-resolution-required",
        "native_payload_packaged": False,
    }


def build_graph() -> dict[str, Any]:
    graph: dict[str, Any] = {
        "schema_version": "dynamic-language-release-graphs-v1",
        "bindings": {
            "ruby": _ruby_graph(),
            "php": _php_graph(),
            "perl": _perl_graph(),
            "lua": _lua_graph(),
            "r": _r_graph(),
        },
        "policy": {
            "caller_supplies_native_library": True,
            "native_payloads_packaged": [],
            "semantic_runtime_packages": [],
            "live_advisory_and_license_certification": "required-at-cp4",
        },
    }
    graph["fingerprint"] = _fingerprint(graph)
    return graph


def synchronize(*, write: bool) -> dict[str, Any]:
    expected = json.dumps(build_graph(), indent=4, sort_keys=True) + "\n"
    actual = GRAPH_PATH.read_text(encoding="utf-8") if GRAPH_PATH.is_file() else None
    matches = actual == expected
    if write and not matches:
        GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        GRAPH_PATH.write_text(expected, encoding="utf-8", newline="\n")
    return {
        "status": "passed" if write or matches else "failed",
        "output": GRAPH_PATH.relative_to(ROOT).as_posix(),
        "fingerprint": build_graph()["fingerprint"],
        "matches": matches,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-graph", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        result = synchronize(write=arguments.write_graph)
    except (DynamicLanguagePackageError, OSError, json.JSONDecodeError) as error:
        result = {"status": "failed", "error": str(error)}
    print(json.dumps(result, sort_keys=True) if arguments.json else result)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
