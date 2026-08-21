"""Generate Go, Dart, and Swift canonical standard-library helper steps."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "spec/stdlib/registry/1.0/registry.json"
OUTPUTS = {
    "go": ROOT / "bindings/go/stdlib_generated.go",
    "dart": ROOT / "bindings/dart/lib/src/stdlib_generated.dart",
    "swift": ROOT / "bindings/swift/Sources/STRling/StdlibGenerated.swift",
}


class GoDartSwiftStdlibSurfaceError(RuntimeError):
    """The canonical registry cannot produce the reviewed adapter surfaces."""


def _registry() -> dict[str, Any]:
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("helpers"), list):
        raise GoDartSwiftStdlibSurfaceError(
            "canonical standard-library registry is invalid"
        )
    return value


def _source_fingerprint(registry: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        {key: value for key, value in registry.items() if key != "fingerprint"},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _name(registry: Mapping[str, Any], helper: Mapping[str, Any], binding: str) -> str:
    simply = str(helper["names"]["simply"])
    choices = registry["compatibility_projections"]["essential_5"][
        "naming_conventions"
    ]["function_names"][simply]
    if binding == "go":
        return str(choices.get("go", simply))
    return str(choices.get(binding, choices.get("default", simply)))


def _go(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    lines = [
        "// Code generated from the canonical standard-library registry. DO NOT EDIT.",
        "// These lexical helpers record Simply recipes; they do not validate semantics.",
        "package strling",
        "",
        f'const StdlibSurfaceSourceSHA256 = "{fingerprint}"',
        f'const StdlibRegistryVersion = "{registry["registry_version"]}"',
        "",
        "var StdlibHelperIDs = []string{" + ", ".join(f'"{item["id"]}"' for item in helpers) + "}",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "go")
        helper_id = helper["id"]
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = parameters[0]["name"]
            lines.extend(
                [
                    f"func {name}(stepID string, {parameter} *int) SimplyStep {{",
                    f'\treturn StdlibHelper(stepID, "{helper_id}", map[string]any{{"{parameter}": {parameter}}})',
                    "}",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"func {name}(stepID string) SimplyStep {{",
                    f'\treturn StdlibHelper(stepID, "{helper_id}", map[string]any{{}})',
                    "}",
                    "",
                ]
            )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _dart(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    lines = [
        "// Generated from the canonical standard-library registry. Do not edit.",
        "// These lexical helpers record Simply recipes; they do not validate semantics.",
        "import 'requests.dart';",
        "",
        f"const stdlibSurfaceSourceSha256 = '{fingerprint}';",
        f"const stdlibRegistryVersion = '{registry['registry_version']}';",
        "const stdlibHelperIds = <String>[",
        *(f"  '{item['id']}'," for item in helpers),
        "];",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "dart")
        helper_id = helper["id"]
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = parameters[0]["name"]
            lines.extend(
                [
                    f"SimplyStep {name}(String stepId, {{int? {parameter}}}) => stdlibHelper(",
                    "      stepId,",
                    f"      '{helper_id}',",
                    f"      <String, Object?>{{'{parameter}': {parameter}}},",
                    "    );",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"SimplyStep {name}(String stepId) =>",
                    f"    stdlibHelper(stepId, '{helper_id}', const <String, Object?>{{}});",
                    "",
                ]
            )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _swift(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    lines = [
        "// Generated from the canonical standard-library registry. Do not edit.",
        "// These lexical helpers record Simply recipes; they do not validate semantics.",
        "import Foundation",
        "",
        "public enum Essential {",
        f'    public static let sourceSHA256 = "{fingerprint}"',
        f'    public static let registryVersion = "{registry["registry_version"]}"',
        "    public static let helperIDs = [",
        *(f'        "{item["id"]}",' for item in helpers),
        "    ]",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "swift")
        helper_id = helper["id"]
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = parameters[0]["name"]
            lines.extend(
                [
                    f"    public static func {name}(_ stepID: String, {parameter}: Int? = nil) -> SimplyStep {{",
                    f'        stdlibHelper(stepID, "{helper_id}", ["{parameter}": {parameter}.map {{ $0 as Any }} ?? NSNull()])',
                    "    }",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"    public static func {name}(_ stepID: String) -> SimplyStep {{",
                    f'        stdlibHelper(stepID, "{helper_id}", [:])',
                    "    }",
                    "",
                ]
            )
    lines.append("}")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def build_outputs() -> dict[Path, bytes]:
    registry = _registry()
    fingerprint = _source_fingerprint(registry)
    return {
        OUTPUTS["go"]: _go(registry, fingerprint),
        OUTPUTS["dart"]: _dart(registry, fingerprint),
        OUTPUTS["swift"]: _swift(registry, fingerprint),
    }


def synchronize(*, write: bool) -> dict[str, Any]:
    mismatches = []
    outputs = build_outputs()
    for path, expected in outputs.items():
        actual = path.read_bytes() if path.exists() else None
        if actual != expected:
            mismatches.append(path.relative_to(ROOT).as_posix())
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
    return {
        "status": "passed" if write or not mismatches else "failed",
        "outputs": len(outputs),
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
