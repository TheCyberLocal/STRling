"""Generate Java and Kotlin canonical standard-library helper facades."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "spec/stdlib/registry/1.0/registry.json"
OUTPUTS = {
    "java": ROOT
    / "bindings/java/src/main/java/com/strling/simply/Essential.java",
    "kotlin": ROOT / "bindings/kotlin/src/main/kotlin/strling/Essential.kt",
}


class JvmStdlibSurfaceError(RuntimeError):
    """The canonical registry cannot produce the reviewed JVM surfaces."""


def _registry() -> dict[str, Any]:
    value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("helpers"), list):
        raise JvmStdlibSurfaceError("canonical standard-library registry is invalid")
    return value


def _source_fingerprint(registry: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        {key: value for key, value in registry.items() if key != "fingerprint"},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _java(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    lines = [
        "package com.strling.simply;",
        "",
        "import java.util.Collections;",
        "import java.util.LinkedHashMap;",
        "import java.util.List;",
        "import java.util.Map;",
        "",
        "/**",
        " * Generated canonical standard-library identities for Simply 1.1.",
        " * These lexical helpers record registry identity; they do not validate semantics.",
        " */",
        "public final class Essential {",
        f'    public static final String SOURCE_SHA256 = "{fingerprint}";',
        f'    public static final String REGISTRY_VERSION = "{registry["registry_version"]}";',
        "    public static final List<String> HELPER_IDS = Collections.unmodifiableList(",
        "            java.util.Arrays.asList(",
    ]
    helpers = registry["helpers"]
    for index, helper in enumerate(helpers):
        suffix = "," if index + 1 < len(helpers) else ""
        lines.append(f'                    "{helper["id"]}"{suffix}')
    lines.extend(["            ));", "", "    private Essential() {}", ""])
    for helper in helpers:
        name = helper["names"]["simply"]
        helper_id = helper["id"]
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = parameters[0]["name"]
            lines.extend(
                [
                    f"    public static Pattern {name}() {{",
                    f"        return {name}(null);",
                    "    }",
                    "",
                    f"    public static Pattern {name}(Integer {parameter}) {{",
                    "        Map<String, Object> parameters = new LinkedHashMap<>();",
                    f'        parameters.put("{parameter}", {parameter});',
                    f'        return Pattern.stdlibHelper("{helper_id}", parameters);',
                    "    }",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"    public static Pattern {name}() {{",
                    f'        return Pattern.stdlibHelper("{helper_id}", Collections.emptyMap());',
                    "    }",
                    "",
                ]
            )
    lines.append("}")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _kotlin(registry: Mapping[str, Any], fingerprint: str) -> bytes:
    lines = [
        "package strling",
        "",
        "/**",
        " * Generated canonical standard-library identities for Simply 1.1.",
        " * These lexical helpers record registry identity; they do not validate semantics.",
        " */",
        "object Essential {",
        f'    const val SOURCE_SHA256: String = "{fingerprint}"',
        f'    const val REGISTRY_VERSION: String = "{registry["registry_version"]}"',
        "    val HELPER_IDS: List<String> = listOf(",
    ]
    helpers = registry["helpers"]
    lines.extend(f'        "{helper["id"]}",' for helper in helpers)
    lines.extend(["    )", ""])
    for helper in helpers:
        name = helper["names"]["simply"]
        helper_id = helper["id"]
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = parameters[0]["name"]
            lines.extend(
                [
                    f"    fun {name}({parameter}: Int? = null): Pattern =",
                    f'        Pattern.stdlibHelper("{helper_id}", mapOf("{parameter}" to {parameter}))',
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"    fun {name}(): Pattern =",
                    f'        Pattern.stdlibHelper("{helper_id}", emptyMap<String, Any?>())',
                    "",
                ]
            )
    lines.append("}")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def build_outputs() -> dict[Path, bytes]:
    registry = _registry()
    fingerprint = _source_fingerprint(registry)
    return {
        OUTPUTS["java"]: _java(registry, fingerprint),
        OUTPUTS["kotlin"]: _kotlin(registry, fingerprint),
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
    if arguments.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(report)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
