#!/usr/bin/env python3
"""Generate non-normative text views from authoritative explanation JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tooling.explanation_contract import CONTRACT_ROOT, ExplanationContractSuite


ROOT = Path(__file__).resolve().parents[1]
SOURCE = CONTRACT_ROOT / "examples" / "source-less-literal.json"
OUTPUT_ROOT = ROOT / "spec" / "explanations" / "semantic" / "generated"
OUTPUTS = {
    OUTPUT_ROOT / "source-less-literal.concise.txt": "concise",
    OUTPUT_ROOT / "source-less-literal.detailed.txt": "detailed",
}


class ExplanationFixtureError(ValueError):
    """A generated explanation projection is absent or stale."""


def _load_source() -> dict[str, Any]:
    with SOURCE.open(encoding="utf-8") as stream:
        document = json.load(stream)
    ExplanationContractSuite().validate(document)
    return document


def _maximum(value: dict[str, Any]) -> str:
    return str(value["value"]) if value["kind"] == "bounded" else "unbounded"


def render_concise(document: dict[str, Any]) -> str:
    concise = document["concise"]
    facts = concise["root_facts"]
    target = concise.get("target")
    target_text = "none"
    if target is not None:
        reference = target["target_profile"]
        target_text = (
            f"{reference['profile_id']}@{reference['profile_version']} "
            f"status={target['status']} decisions={target['decision_count']} "
            f"unresolved={target['unresolved_count']} "
            f"diagnostics={target['diagnostic_count']}"
        )
    return "\n".join(
        (
            "# Non-normative concise semantic explanation",
            f"model={document['model_version']}",
            f"semantic_program={document['semantic_program']}",
            f"root={concise['root_node_id']} source={concise['source_mode']}",
            (
                f"entities nodes={concise['node_count']} "
                f"captures={concise['capture_count']} "
                f"backreferences={concise['backreference_count']}"
            ),
            (
                f"root_facts nullability={facts['nullability']} "
                f"length={facts['minimum_consumption']}.."
                f"{_maximum(facts['maximum_consumption'])} "
                f"consumption={facts['consumption']}"
            ),
            (
                f"evidence safety={concise['safety_finding_count']} "
                f"uncertainty={concise['uncertainty_count']} "
                f"diagnostics={concise['diagnostic_count']}"
            ),
            f"target={target_text}",
            "",
        )
    )


def _semantic_summary(semantic: dict[str, Any]) -> str:
    kind = semantic["kind"]
    if kind == "literal":
        return f"literal text={json.dumps(semantic['text'], ensure_ascii=False)}"
    if kind in {"sequence", "alternation"}:
        field = "items" if kind == "sequence" else "branches"
        return f"{kind} {field}={','.join(semantic[field])}"
    if kind in {"repeat", "capture", "lookaround", "atomic"}:
        return f"{kind} body={semantic['body_node_id']}"
    return kind


def render_detailed(document: dict[str, Any]) -> str:
    lines = [
        "# Non-normative detailed semantic explanation",
        f"model={document['model_version']}",
        f"semantic_program={document['semantic_program']}",
        "",
    ]
    for node in document["nodes"]:
        facts = node["facts"]
        structural = node["structural"]
        leading = ",".join(
            term["kind"] + (f":{term['value']}" if term["kind"] == "scalar" else "")
            for term in structural["leading_consumption"]
        )
        length = structural["length"]
        length_text = length["kind"]
        if length["kind"] == "fixed":
            length_text += f":{length['value']}"
        lines.append(
            " ".join(
                (
                    f"node={node['node_id']}",
                    f"semantic={_semantic_summary(node['semantic'])}",
                    f"nullability={facts['nullability']}",
                    (
                        f"length={facts['minimum_consumption']}.."
                        f"{_maximum(facts['maximum_consumption'])}"
                    ),
                    f"consumption={facts['consumption']}",
                    f"leading={leading}",
                    f"structural_length={length_text}",
                    f"source_spans={len(node['source']['source_spans'])}",
                    (f"derived_nodes={len(node['source']['derived_from_node_ids'])}"),
                )
            )
        )
    lines.extend(
        (
            "",
            f"captures={len(document['captures'])}",
            f"safety_findings={len(document['safety_findings'])}",
            f"uncertainties={len(document['uncertainties'])}",
            f"diagnostics={len(document['diagnostics'])}",
            f"target={'present' if document.get('target') is not None else 'none'}",
            "",
        )
    )
    return "\n".join(lines)


def render_outputs() -> dict[Path, str]:
    document = _load_source()
    rendered = {
        path: render_concise(document)
        if form == "concise"
        else render_detailed(document)
        for path, form in OUTPUTS.items()
    }
    return rendered


def write_outputs() -> dict[str, Any]:
    rendered = render_outputs()
    for path, content in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return _summary(rendered)


def check_outputs() -> dict[str, Any]:
    rendered = render_outputs()
    for path, expected in rendered.items():
        if not path.is_file():
            raise ExplanationFixtureError(
                f"generated explanation fixture is missing: {path.relative_to(ROOT)}"
            )
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            raise ExplanationFixtureError(
                f"generated explanation fixture is stale: {path.relative_to(ROOT)}"
            )
    return _summary(rendered)


def _summary(rendered: dict[Path, str]) -> dict[str, Any]:
    digest = hashlib.sha256()
    for path, content in sorted(rendered.items()):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return {"outputs": len(rendered), "fingerprint": digest.hexdigest()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    result = write_outputs() if args.write else check_outputs()
    print(
        "EXPLANATION_RENDERING_FIXTURES status=passed "
        f"outputs={result['outputs']} fingerprint={result['fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
