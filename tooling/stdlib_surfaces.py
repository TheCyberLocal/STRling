#!/usr/bin/env python3
"""Generate and verify canonical standard-library public surface projections."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "spec/stdlib/registry/1.0/registry.json"
SEMANTICS_PATH = ROOT / "spec/stdlib/registry/1.0/canonical-semantics.json"
EVIDENCE_PATH = ROOT / "tests/conformance/evidence/stdlib-runtime-observations.json"
PROTOCOL_PATH = ROOT / "spec/frontends/simply/1.1/protocol.json"
DERIVATION_ID = "projection.supported-surfaces"


class StandardLibrarySurfaceError(ValueError):
    """A governed surface input or generated output is inconsistent."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StandardLibrarySurfaceError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise StandardLibrarySurfaceError(f"{path}: root must be an object")
    return value


def compact_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def pretty_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _variant_rows(
    registry: Mapping[str, Any],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [
        (helper, variant)
        for helper in registry["helpers"]
        for variant in helper["semantic_definition"]["variants"]
    ]


def _source_fingerprint(
    registry: Mapping[str, Any],
    semantics: Mapping[str, Any],
    evidence: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> str:
    inputs = {
        "evidence_result_sha256": evidence["result_sha256"],
        "protocol_version": protocol["protocol_version"],
        "registry_fingerprint": registry["fingerprint"]["value"],
        "semantics_sha256": sha256(compact_json(semantics)),
    }
    return sha256(compact_json(inputs))


def validate_inputs(
    registry: Mapping[str, Any],
    semantics: Mapping[str, Any],
    evidence: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, int]:
    helpers = registry["helpers"]
    variants = _variant_rows(registry)
    bindings = registry["host_bindings"]
    profiles = registry["target_catalog"]["profiles"]
    adapters = registry["canonical_adapters"]
    counts = {
        "helpers": len(helpers),
        "variants": len(variants),
        "bindings": len(bindings),
        "profiles": len(profiles),
        "adapters": len(adapters),
        "semantic_validators": semantics["semantic_validator_count"],
    }
    if counts != {
        "helpers": 5,
        "variants": 8,
        "bindings": 17,
        "profiles": 5,
        "adapters": 2,
        "semantic_validators": 0,
    }:
        raise StandardLibrarySurfaceError(f"surface denominator drifted: {counts}")

    binding_ids = [binding["binding_id"] for binding in bindings]
    if len(binding_ids) != len(set(binding_ids)):
        raise StandardLibrarySurfaceError("host binding identities are not unique")
    adapter_ids = [adapter["binding_id"] for adapter in adapters]
    if adapter_ids != ["python", "typescript"]:
        raise StandardLibrarySurfaceError(
            "canonical adapter denominator must be ordered Python and TypeScript"
        )
    if any(adapter_id not in binding_ids for adapter_id in adapter_ids):
        raise StandardLibrarySurfaceError("canonical adapter is not a host binding")
    if any(adapter["protocol_version"] != "1.1.0" for adapter in adapters):
        raise StandardLibrarySurfaceError("canonical adapters must target Simply 1.1.0")

    operations = [operation["id"] for operation in protocol["operations"]]
    if protocol["protocol_version"] != "1.1.0" or len(operations) != 16:
        raise StandardLibrarySurfaceError("Simply 1.1.0 operation denominator drifted")
    if operations.count("stdlib_helper") != 1:
        raise StandardLibrarySurfaceError(
            "Simply 1.1.0 must contain exactly one stdlib_helper operation"
        )

    expected_variants = [
        (helper["id"], variant["variant_id"]) for helper, variant in variants
    ]
    semantic_variants = [
        (entry["helper_id"], entry["variant_id"]) for entry in semantics["entries"]
    ]
    if semantic_variants != expected_variants:
        raise StandardLibrarySurfaceError(
            "canonical Semantic DSL entries do not follow the registry denominator"
        )

    profile_ids = [profile["profile_id"] for profile in profiles]
    observations = evidence["observations"]
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for observation in observations:
        grouped[(observation["variant_id"], observation["profile_id"])].append(
            observation
        )
        if observation["state"] == "execute" and (
            observation["actual_match"] != observation["expected_match"]
        ):
            raise StandardLibrarySurfaceError(
                "runtime evidence contains a failed executed observation"
            )
        if observation["state"] == "not_applicable" and (
            observation["actual_match"] is not None
            or observation["expected_match"] is not None
        ):
            raise StandardLibrarySurfaceError(
                "not-applicable runtime evidence must have null outcomes"
            )
    expected_cells = {
        (variant["variant_id"], profile_id)
        for _, variant in variants
        for profile_id in profile_ids
    }
    if set(grouped) != expected_cells:
        raise StandardLibrarySurfaceError(
            "runtime evidence does not cover the exact variant/profile matrix"
        )
    state_counts = Counter(observation["state"] for observation in observations)
    if state_counts != {"execute": 580, "not_applicable": 5}:
        raise StandardLibrarySurfaceError(
            f"runtime application denominator drifted: {dict(state_counts)}"
        )
    return counts


def binding_support_projection(
    registry: Mapping[str, Any], protocol: Mapping[str, Any], source_fingerprint: str
) -> dict[str, Any]:
    adapters = {
        adapter["binding_id"]: adapter for adapter in registry["canonical_adapters"]
    }
    bindings = []
    for binding in registry["host_bindings"]:
        adapter = adapters.get(binding["binding_id"])
        bindings.append(
            {
                "binding_id": binding["binding_id"],
                "classification": (
                    "canonical_preview_adapter"
                    if adapter is not None
                    else "compatibility_only"
                ),
                "exposures": binding["exposures"],
                "implementation_references": binding["implementation_references"],
                "protocol_reference": (
                    adapter["protocol_reference"] if adapter is not None else None
                ),
                "surface_output": (
                    adapter["surface_output"] if adapter is not None else None
                ),
                "test_reference": binding["test_reference"],
                "transport_reference": (
                    adapter["transport_reference"] if adapter is not None else None
                ),
            }
        )
    return {
        "kind": "strling.stdlib-binding-support",
        "projection_version": "1.0.0",
        "registry_version": registry["registry_version"],
        "simply_protocol_version": protocol["protocol_version"],
        "source_fingerprint": source_fingerprint,
        "counts": {
            "bindings": len(bindings),
            "canonical_preview_adapters": len(adapters),
            "compatibility_only_bindings": len(bindings) - len(adapters),
            "helpers": len(registry["helpers"]),
        },
        "bindings": bindings,
    }


def portability_projection(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    source_fingerprint: str,
) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for observation in evidence["observations"]:
        grouped[(observation["variant_id"], observation["profile_id"])].append(
            observation
        )
    rows = []
    for helper, variant in _variant_rows(registry):
        for profile in registry["target_catalog"]["profiles"]:
            profile_id = profile["profile_id"]
            observations = grouped[(variant["variant_id"], profile_id)]
            state_counts = Counter(item["state"] for item in observations)
            rows.append(
                {
                    "helper_id": helper["id"],
                    "variant_id": variant["variant_id"],
                    "profile_id": profile_id,
                    "profile_reference": profile["reference"],
                    "status": "certified",
                    "observation_counts": {
                        "execute": state_counts["execute"],
                        "not_applicable": state_counts["not_applicable"],
                    },
                }
            )
    return {
        "kind": "strling.stdlib-portability-matrix",
        "projection_version": "1.0.0",
        "registry_version": registry["registry_version"],
        "source_fingerprint": source_fingerprint,
        "evidence": {
            "path": "tests/conformance/evidence/stdlib-runtime-observations.json",
            "projection_sha256": evidence["projection_sha256"],
            "result_sha256": evidence["result_sha256"],
        },
        "counts": {
            "rows": len(rows),
            "certified": len(rows),
            "unsupported": 0,
            "execute_applications": sum(
                row["observation_counts"]["execute"] for row in rows
            ),
            "not_applicable_applications": sum(
                row["observation_counts"]["not_applicable"] for row in rows
            ),
        },
        "rows": rows,
    }


def convergence_projection(
    registry: Mapping[str, Any], source_fingerprint: str
) -> dict[str, Any]:
    cases = []
    for helper, variant in _variant_rows(registry):
        cases.append(
            {
                "case_id": f"stdlib.frontend.{variant['variant_id']}",
                "canonical_semantics_reference": variant["canonical_semantics_ref"],
                "helper_id": helper["id"],
                "parameters": {
                    name: None if value == "default_or_other" else value
                    for name, value in variant["parameter_values"].items()
                },
                "semantic_dsl": (
                    f"spec/stdlib/generated/semantic-dsl/{variant['variant_id']}.strl"
                ),
                "simply": {
                    "operation": "stdlib_helper",
                    "protocol_version": "1.1.0",
                },
                "target_profiles": helper["targeting"]["profiles"],
                "variant_id": variant["variant_id"],
            }
        )
    return {
        "kind": "strling.stdlib-frontend-convergence",
        "projection_version": "1.0.0",
        "registry_version": registry["registry_version"],
        "source_fingerprint": source_fingerprint,
        "counts": {
            "cases": len(cases),
            "helpers": len(registry["helpers"]),
            "semantic_validators": 0,
        },
        "cases": cases,
    }


def _typescript_surface(registry: Mapping[str, Any], source_fingerprint: str) -> bytes:
    lines = [
        "/**",
        " * Generated by tooling/stdlib_surfaces.py from the canonical registry.",
        " * Do not edit; these wrappers only record Simply 1.1 helper identity and parameters.",
        " */",
        "",
        'import type { SimplyPreviewBuilder, SimplyPreviewValue } from "./preview.js";',
        "",
        f'export const STDLIB_SURFACE_SOURCE_SHA256 = "{source_fingerprint}" as const;',
        f'export const STDLIB_REGISTRY_VERSION = "{registry["registry_version"]}" as const;',
        "export const STDLIB_HELPER_IDS = [",
    ]
    lines.extend(f'    "{helper["id"]}",' for helper in registry["helpers"])
    lines.extend(
        [
            "] as const;",
            "",
            "export type StdlibHelperId = (typeof STDLIB_HELPER_IDS)[number];",
            "",
        ]
    )
    for helper in registry["helpers"]:
        name = helper["names"]["simply"]
        helper_id = helper["id"]
        parameters = helper["signature"]["parameters"]
        if parameters:
            parameter = parameters[0]
            lines.extend(
                [
                    f"export function {name}(",
                    "    builder: SimplyPreviewBuilder,",
                    "    stepId: string,",
                    f"    {parameter['name']}: number | null = null,",
                    "): SimplyPreviewValue {",
                    f'    return builder.stdlibHelper(stepId, "{helper_id}", {{',
                    f"        {parameter['name']},",
                    "    });",
                    "}",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"export function {name}(",
                    "    builder: SimplyPreviewBuilder,",
                    "    stepId: string,",
                    "): SimplyPreviewValue {",
                    f'    return builder.stdlibHelper(stepId, "{helper_id}", {{}});',
                    "}",
                    "",
                ]
            )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _python_surface(registry: Mapping[str, Any], source_fingerprint: str) -> bytes:
    lines = [
        '"""Generated canonical standard-library wrappers for the Simply 1.1 Preview adapter."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Final, Optional, Tuple",
        "",
        "from STRling.simply.preview import SimplyPreviewBuilder, SimplyPreviewValue",
        "",
        "STDLIB_SURFACE_SOURCE_SHA256: Final = (",
        f'    "{source_fingerprint}"',
        ")",
        f'STDLIB_REGISTRY_VERSION: Final = "{registry["registry_version"]}"',
        "STDLIB_HELPER_IDS: Final[Tuple[str, ...]] = (",
    ]
    lines.extend(f'    "{helper["id"]}",' for helper in registry["helpers"])
    lines.append(")")
    exported = [
        "STDLIB_SURFACE_SOURCE_SHA256",
        "STDLIB_REGISTRY_VERSION",
        "STDLIB_HELPER_IDS",
    ]
    for helper in registry["helpers"]:
        name = helper["names"]["canonical"]
        helper_id = helper["id"]
        parameters = helper["signature"]["parameters"]
        exported.append(name)
        if parameters:
            parameter = parameters[0]
            lines.extend(
                [
                    "",
                    "",
                    f"def {name}(",
                    "    builder: SimplyPreviewBuilder,",
                    "    step_id: str,",
                    f"    {parameter['name']}: Optional[int] = None,",
                    ") -> SimplyPreviewValue:",
                    "    return builder.stdlib_helper(",
                    "        step_id,",
                    f'        "{helper_id}",',
                    "        {",
                    f'            "{parameter["name"]}": {parameter["name"]},',
                    "        },",
                    "    )",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "",
                    f"def {name}(",
                    "    builder: SimplyPreviewBuilder,",
                    "    step_id: str,",
                    ") -> SimplyPreviewValue:",
                    f'    return builder.stdlib_helper(step_id, "{helper_id}", {{}})',
                ]
            )
    lines.extend(["", "", "__all__ = ["])
    lines.extend(f'    "{name}",' for name in exported)
    lines.extend(["]", ""])
    return "\n".join(lines).encode("utf-8")


def _markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _documentation(
    registry: Mapping[str, Any],
    support: Mapping[str, Any],
    portability: Mapping[str, Any],
    source_fingerprint: str,
) -> bytes:
    lines = [
        "# STRling standard library",
        "",
        "<!-- Generated by tooling/stdlib_surfaces.py; do not edit. -->",
        "",
        "This reference projects the canonical standard-library registry. The registry",
        "owns helper identity and guarantee metadata; generated examples and host wrappers",
        "do not create semantics.",
        "",
        f"- Registry version: `{registry['registry_version']}`",
        f"- Registry fingerprint: `{registry['fingerprint']['value']}`",
        f"- Surface source fingerprint: `{source_fingerprint}`",
        "- Simply protocol: `strling.simply-builder@1.1.0`",
        "",
        "## Host support",
        "",
        f"{support['counts']['canonical_preview_adapters']} of "
        f"{support['counts']['bindings']} host bindings expose the canonical Preview "
        "transport. The remaining "
        f"{support['counts']['compatibility_only_bindings']} retain historical "
        "Essential implementations as compatibility-only surfaces.",
        "",
        "| Binding | Classification | Canonical transport |",
        "| --- | --- | --- |",
    ]
    for binding in support["bindings"]:
        lines.append(
            f"| {_markdown_escape(binding['binding_id'])} | "
            f"{_markdown_escape(binding['classification'])} | "
            f"{_markdown_escape(binding['transport_reference'] or '—')} |"
        )
    lines.extend(["", "## Helpers", ""])
    for helper in registry["helpers"]:
        documentation = helper["documentation"]
        lines.extend(
            [
                f"### {documentation['snippet']} — {helper['id']}",
                "",
                documentation["description"],
                "",
                f"- Guarantee: `{helper['guarantee']['level']}`",
                f"- Support tier: `{helper['support_tier']}`",
                f"- Output: `{helper['signature']['output_type']}`",
            ]
        )
        parameters = helper["signature"]["parameters"]
        if parameters:
            lines.extend(["", "Parameters:", ""])
            for parameter in parameters:
                lines.append(
                    f"- `{parameter['name']}`: {parameter['description']} "
                    f"Default: `{json.dumps(parameter['default'])}`."
                )
        for title, field in (
            ("Accepts", "accepts"),
            ("Rejects", "rejects"),
            ("Does not guarantee", "non_guarantees"),
        ):
            lines.extend(["", f"{title}:", ""])
            lines.extend(f"- {item}" for item in helper["guarantee"][field])
        lines.extend(["", "Examples:", ""])
        seen_examples: set[tuple[str, bool, str]] = set()
        for example in helper["examples"] + helper["counterexamples"]:
            example_key = (
                example["input"],
                example["expected_match"],
                example["classification"],
            )
            if example_key in seen_examples:
                continue
            seen_examples.add(example_key)
            lines.append(
                f"- `{example['input']}` → "
                f"`{str(example['expected_match']).lower()}` "
                f"({example['classification']})"
            )
        references = helper["guarantee"]["standards"]["references"]
        if references:
            lines.extend(["", "Standards context:", ""])
            lines.extend(
                f"- [{reference['title']}]({reference['uri']}) — "
                f"{', '.join(reference['provisions'])}"
                for reference in references
            )
        lines.append("")
    lines.extend(
        [
            "## Certified portability",
            "",
            f"All {portability['counts']['rows']} helper-variant/profile cells are "
            "certified from the checked runtime evidence. This records target behavior;",
            "it does not strengthen any helper guarantee.",
            "",
            "| Variant | Target profile | Execute | N/A | Status |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in portability["rows"]:
        lines.append(
            f"| {row['variant_id']} | {row['profile_id']} | "
            f"{row['observation_counts']['execute']} | "
            f"{row['observation_counts']['not_applicable']} | {row['status']} |"
        )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def build_outputs() -> tuple[dict[str, bytes], dict[str, int]]:
    registry = load_json(REGISTRY_PATH)
    semantics = load_json(SEMANTICS_PATH)
    evidence = load_json(EVIDENCE_PATH)
    protocol = load_json(PROTOCOL_PATH)
    counts = validate_inputs(registry, semantics, evidence, protocol)
    source_fingerprint = _source_fingerprint(registry, semantics, evidence, protocol)
    support = binding_support_projection(registry, protocol, source_fingerprint)
    portability = portability_projection(registry, evidence, source_fingerprint)
    convergence = convergence_projection(registry, source_fingerprint)
    outputs: dict[str, bytes] = {
        "bindings/python/src/STRling/simply/stdlib_generated.py": _python_surface(
            registry, source_fingerprint
        ),
        "bindings/typescript/src/STRling/simply/stdlib.generated.ts": (
            _typescript_surface(registry, source_fingerprint)
        ),
        "docs/reference/standard-library.md": _documentation(
            registry, support, portability, source_fingerprint
        ),
        "spec/stdlib/generated/binding-support.json": pretty_json(support),
        "spec/stdlib/generated/portability-matrix.json": pretty_json(portability),
        "tests/convergence/stdlib-frontend-cases.json": pretty_json(convergence),
    }
    entries = {entry["variant_id"]: entry for entry in semantics["entries"]}
    for _, variant in _variant_rows(registry):
        variant_id = variant["variant_id"]
        lines = entries[variant_id]["semantic_dsl_lines"]
        outputs[f"spec/stdlib/generated/semantic-dsl/{variant_id}.strl"] = (
            "\n".join(lines).rstrip() + "\n"
        ).encode("utf-8")

    derivation = next(
        item
        for item in registry["derivations"]
        if item["derivation_id"] == DERIVATION_ID
    )
    if set(derivation["outputs"]) != set(outputs):
        raise StandardLibrarySurfaceError(
            "registry surface derivation outputs do not equal generator outputs"
        )
    counts = {
        **counts,
        "outputs": len(outputs),
        "portability_rows": portability["counts"]["rows"],
        "execute_applications": portability["counts"]["execute_applications"],
        "not_applicable_applications": portability["counts"][
            "not_applicable_applications"
        ],
    }
    return outputs, counts


def synchronize(*, write: bool) -> dict[str, Any]:
    outputs, counts = build_outputs()
    mismatches = []
    for relative, expected in outputs.items():
        path = ROOT / relative
        actual = path.read_bytes() if path.is_file() else None
        if actual != expected:
            mismatches.append(relative)
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
    semantic_root = ROOT / "spec/stdlib/generated/semantic-dsl"
    expected_semantic = {
        (ROOT / relative).resolve()
        for relative in outputs
        if relative.startswith("spec/stdlib/generated/semantic-dsl/")
    }
    stale = (
        sorted(
            path.relative_to(ROOT).as_posix()
            for path in semantic_root.glob("*.strl")
            if path.resolve() not in expected_semantic
        )
        if semantic_root.is_dir()
        else []
    )
    if stale and write:
        for relative in stale:
            (ROOT / relative).unlink()
    if (mismatches or stale) and not write:
        details = ", ".join([*mismatches, *stale])
        raise StandardLibrarySurfaceError(
            f"generated standard-library surfaces are stale: {details}"
        )
    output_fingerprint = sha256(
        compact_json(
            {relative: sha256(payload) for relative, payload in sorted(outputs.items())}
        )
    )
    return {
        **counts,
        "changed": len(mismatches),
        "removed": len(stale),
        "output_fingerprint": output_fingerprint,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    try:
        result = synchronize(write=arguments.write)
    except (OSError, StandardLibrarySurfaceError) as error:
        print(f"STDLIB_SURFACES status=failed error={error}")
        return 1
    print(
        "STDLIB_SURFACES status=passed "
        f"helpers={result['helpers']} variants={result['variants']} "
        f"bindings={result['bindings']} adapters={result['adapters']} "
        f"profiles={result['profiles']} rows={result['portability_rows']} "
        f"execute={result['execute_applications']} "
        f"not_applicable={result['not_applicable_applications']} "
        f"outputs={result['outputs']} changed={result['changed']} "
        f"removed={result['removed']} "
        f"fingerprint={result['output_fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
