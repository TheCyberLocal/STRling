"""Generate C# and F# canonical standard-library helper facades."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "spec/stdlib/registry/1.0/registry.json"
OUTPUTS = {
    "csharp": ROOT
    / "bindings/csharp/src/STRling/Canonical/Simply/Essential.Generated.cs",
    "fsharp": ROOT / "bindings/fsharp/src/STRling.FSharp/Essential.Generated.fs",
}


class DotNetStdlibSurfaceError(RuntimeError):
    """The canonical registry cannot produce the reviewed .NET surfaces."""


def _registry() -> dict[str, Any]:
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("helpers"), list):
        raise DotNetStdlibSurfaceError("canonical standard-library registry is invalid")
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
    conventions = registry["compatibility_projections"]["essential_5"][
        "naming_conventions"
    ]
    return str(conventions["function_names"][simply].get(binding, simply))


def _csharp(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    lines = [
        "#nullable enable",
        "",
        "namespace Strling.Simply;",
        "",
        "/// <summary>",
        "/// Generated canonical standard-library identities for Simply 1.1.",
        "/// These lexical helpers record registry identity; they do not validate semantics.",
        "/// </summary>",
        "public static class Essential",
        "{",
        f'    public const string SourceSha256 = "{fingerprint}";',
        f'    public const string RegistryVersion = "{registry["registry_version"]}";',
        "    public static IReadOnlyList<string> HelperIds { get; } =",
        "        [" + ", ".join(f'"{item["id"]}"' for item in helpers) + "];",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "csharp")
        helper_id = helper["id"]
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = parameters[0]["name"]
            lines.extend(
                [
                    f"    public static Pattern {name}(int? {parameter} = null) => Pattern.StdlibHelper(",
                    f'        "{helper_id}", new Dictionary<string, object?> {{ ["{parameter}"] = {parameter} }});',
                ]
            )
        else:
            lines.append(
                f'    public static Pattern {name}() => Pattern.StdlibHelper("{helper_id}", new Dictionary<string, object?>());'
            )
    lines.append("}")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _fsharp(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    helpers = registry["helpers"]
    lines = [
        "namespace STRling.FSharp",
        "",
        "open System",
        "",
        "/// Generated F# names for canonical lexical-shape helpers.",
        "[<RequireQualifiedAccess>]",
        "module Essential =",
        f'    let SourceSha256 = "{fingerprint}"',
        f'    let RegistryVersion = "{registry["registry_version"]}"',
        "    let HelperIds = [ "
        + "; ".join(f'"{item["id"]}"' for item in helpers)
        + " ]",
        "",
    ]
    for helper in helpers:
        name = _name(registry, helper, "fsharp")
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = parameters[0]["name"]
            lines.extend(
                [
                    f"    let {name} ({parameter}: int option) =",
                    f"        match {parameter} with",
                    f"        | Some value -> Strling.Simply.Essential.{name}(Nullable value)",
                    f"        | None -> Strling.Simply.Essential.{name}()",
                ]
            )
        else:
            lines.append(f"    let {name} () = Strling.Simply.Essential.{name}()")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def build_outputs() -> dict[Path, bytes]:
    registry = _registry()
    fingerprint = _source_fingerprint(registry)
    return {
        OUTPUTS["csharp"]: _csharp(registry, fingerprint),
        OUTPUTS["fsharp"]: _fsharp(registry, fingerprint),
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
