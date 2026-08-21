#!/usr/bin/env python3
"""Generate Ruby, PHP, Perl, Lua, and R lexical-helper request surfaces."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "spec/stdlib/registry/1.0/registry.json"
OUTPUTS = {
    "ruby": ROOT / "bindings/ruby/lib/strling/stdlib_generated.rb",
    "php": ROOT / "bindings/php/src/Stdlib.php",
    "perl": ROOT / "bindings/perl/lib/STRling/StdlibGenerated.pm",
    "lua": ROOT / "bindings/lua/src/stdlib_generated.lua",
    "r": ROOT / "bindings/r/R/stdlib_generated.R",
}


class DynamicLanguageStdlibSurfaceError(RuntimeError):
    """The canonical registry cannot produce the reviewed dynamic surfaces."""


def _registry() -> dict[str, Any]:
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("helpers"), list):
        raise DynamicLanguageStdlibSurfaceError("canonical stdlib registry is invalid")
    return value


def _fingerprint(registry: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        {key: value for key, value in registry.items() if key != "fingerprint"},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _name(registry: Mapping[str, Any], helper: Mapping[str, Any], binding: str) -> str:
    simply = str(helper["names"]["simply"])
    names = registry["compatibility_projections"]["essential_5"]["naming_conventions"][
        "function_names"
    ][simply]
    if binding == "php":
        return str(names.get("default", simply))
    base = str(names.get("snake", names.get("default", simply)))
    return f"sl_{base}" if binding == "r" else base


def _ruby(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    lines = [
        "# frozen_string_literal: true",
        "",
        "# Generated from the canonical standard-library registry. Do not edit.",
        "# These lexical helpers record Simply recipes; they do not validate semantics.",
        "module Strling",
        f"  STDLIB_SURFACE_SOURCE_SHA256 = '{fingerprint}'",
        f"  STDLIB_REGISTRY_VERSION = '{registry['registry_version']}'",
        "  STDLIB_HELPER_IDS = %w["
        + " ".join(str(item["id"]) for item in helpers)
        + "].freeze",
        "",
        "  module_function",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "ruby")
        helper_id = str(helper["id"])
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = str(parameters[0]["name"])
            lines.extend(
                [
                    f"  def {name}(step_id, {parameter}: nil)",
                    f"    stdlib_helper(step_id, '{helper_id}', '{parameter}' => {parameter})",
                    "  end",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"  def {name}(step_id)",
                    f"    stdlib_helper(step_id, '{helper_id}')",
                    "  end",
                    "",
                ]
            )
    lines.append("end")
    return ("\n".join(lines).rstrip() + "\n").encode()


def _php(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    lines = [
        "<?php",
        "",
        "declare(strict_types=1);",
        "",
        "namespace STRling;",
        "",
        "// Generated from the canonical standard-library registry. Do not edit.",
        "// These lexical helpers record Simply recipes; they do not validate semantics.",
        "final class Stdlib",
        "{",
        f"    public const SURFACE_SOURCE_SHA256 = '{fingerprint}';",
        f"    public const REGISTRY_VERSION = '{registry['registry_version']}';",
        "    public const HELPER_IDS = ["
        + ", ".join(f"'{item['id']}'" for item in helpers)
        + "];",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "php")
        helper_id = str(helper["id"])
        parameters = helper["signature"]["parameters"]
        lines.append("    /** @return array<string, mixed> */")
        if parameters:
            parameter = str(parameters[0]["name"])
            lines.extend(
                [
                    f"    public static function {name}(string $stepId, ?int ${parameter} = null): array",
                    "    {",
                    f"        return Requests::stdlibHelper($stepId, '{helper_id}', ['{parameter}' => ${parameter}]);",
                    "    }",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"    public static function {name}(string $stepId): array",
                    "    {",
                    f"        return Requests::stdlibHelper($stepId, '{helper_id}');",
                    "    }",
                    "",
                ]
            )
    lines.append("}")
    return ("\n".join(lines).rstrip() + "\n").encode()


def _perl(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    ids = ", ".join(f"'{item['id']}'" for item in helpers)
    lines = [
        "package STRling::StdlibGenerated;",
        "",
        "use 5.010;",
        "use strict;",
        "use warnings;",
        "use STRling::Requests ();",
        "",
        "# Generated from the canonical standard-library registry. Do not edit.",
        "# These lexical helpers record Simply recipes; they do not validate semantics.",
        f"use constant SURFACE_SOURCE_SHA256 => '{fingerprint}';",
        f"use constant REGISTRY_VERSION => '{registry['registry_version']}';",
        "",
        "# STRling-public-arity: helper_ids=0",
        f"sub helper_ids {{ return [{ids}]; }}",
    ]
    for helper in helpers:
        name = _name(registry, helper, "perl")
        helper_id = str(helper["id"])
        parameters = helper["signature"]["parameters"]
        params = f"{{ {parameters[0]['name']} => $_[1] }}" if parameters else "{}"
        arity = "1..2" if parameters else "1"
        lines.append(f"# STRling-public-arity: {name}={arity}")
        lines.append(
            f"sub {name} {{ return STRling::Requests::stdlib_helper($_[0], '{helper_id}', {params}); }}"
        )
    lines.extend(("", "1;"))
    return ("\n".join(lines).rstrip() + "\n").encode()


def _lua(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    ids = ", ".join(f'"{item["id"]}"' for item in helpers)
    lines = [
        "-- Generated from the canonical standard-library registry. Do not edit.",
        "-- These lexical helpers record Simply recipes; they do not validate semantics.",
        "local surface = {",
        f'  SURFACE_SOURCE_SHA256 = "{fingerprint}",',
        f'  REGISTRY_VERSION = "{registry["registry_version"]}",',
        f"  HELPER_IDS = {{ {ids} }},",
        "}",
        'local json_null = require("cjson.safe").null',
        "",
        "local function helper(step_id, helper_id, parameters)",
        '  return { step_id = tostring(step_id), operation = "stdlib_helper", arguments = { helper_id = helper_id, parameters = parameters or {} } }',
        "end",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "lua")
        helper_id = str(helper["id"])
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = str(parameters[0]["name"])
            lines.append(
                f'function surface.{name}(step_id, {parameter}) return helper(step_id, "{helper_id}", {{ {parameter} = {parameter} == nil and json_null or {parameter} }}) end'
            )
        else:
            lines.append(
                f'function surface.{name}(step_id) return helper(step_id, "{helper_id}") end'
            )
    lines.extend(("", "return surface"))
    return ("\n".join(lines).rstrip() + "\n").encode()


def _r(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    ids = ", ".join(f'"{item["id"]}"' for item in helpers)
    lines = [
        "# Generated from the canonical standard-library registry. Do not edit.",
        "# These lexical helpers record Simply recipes; they do not validate semantics.",
        f'.strling_stdlib_source_sha256 <- "{fingerprint}"',
        f'.strling_stdlib_registry_version <- "{registry["registry_version"]}"',
        f".strling_stdlib_helper_ids <- c({ids})",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "r")
        helper_id = str(helper["id"])
        parameters = helper["signature"]["parameters"]
        lines.append("#' @export")
        if parameters:
            parameter = str(parameters[0]["name"])
            lines.append(
                f'{name} <- function(step_id, {parameter} = NULL) strling_stdlib_helper(step_id, "{helper_id}", list({parameter} = {parameter}))'
            )
        else:
            lines.append(
                f'{name} <- function(step_id) strling_stdlib_helper(step_id, "{helper_id}")'
            )
    return ("\n".join(lines).rstrip() + "\n").encode()


def build_outputs() -> dict[Path, bytes]:
    registry = _registry()
    fingerprint = _fingerprint(registry)
    return {
        OUTPUTS["ruby"]: _ruby(registry, fingerprint),
        OUTPUTS["php"]: _php(registry, fingerprint),
        OUTPUTS["perl"]: _perl(registry, fingerprint),
        OUTPUTS["lua"]: _lua(registry, fingerprint),
        OUTPUTS["r"]: _r(registry, fingerprint),
    }


def synchronize(*, write: bool) -> dict[str, Any]:
    mismatches = []
    for path, expected in build_outputs().items():
        actual = path.read_bytes() if path.exists() else None
        if actual != expected:
            mismatches.append(path.relative_to(ROOT).as_posix())
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
    return {
        "status": "passed" if write or not mismatches else "failed",
        "outputs": len(OUTPUTS),
        "mismatches": mismatches,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)
    report = synchronize(write=arguments.write)
    print(json.dumps(report, sort_keys=True) if arguments.json else report)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
