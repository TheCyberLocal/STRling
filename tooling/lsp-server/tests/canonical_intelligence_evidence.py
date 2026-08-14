"""Shared readers for the authored P16-T03 editor-intelligence evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator


LSP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = LSP_ROOT.parents[1]
MANIFEST_PATH = (
    Path(__file__).parent / "fixtures" / "canonical-intelligence" / "manifest.json"
)

CATALOG_PATHS = {
    "regex_dialect": REPOSITORY_ROOT
    / "spec"
    / "frontends"
    / "legacy-regex"
    / "1.0"
    / "dialect.json",
    "regex_grammar": REPOSITORY_ROOT
    / "spec"
    / "frontends"
    / "legacy-regex"
    / "1.0"
    / "grammar.ebnf",
    "semantic_language": REPOSITORY_ROOT
    / "spec"
    / "frontends"
    / "semantic"
    / "1.0"
    / "language.json",
    "simply_protocol": REPOSITORY_ROOT
    / "spec"
    / "frontends"
    / "simply"
    / "1.1"
    / "protocol.json",
    "stdlib_registry": REPOSITORY_ROOT
    / "spec"
    / "stdlib"
    / "registry"
    / "1.0"
    / "registry.json",
}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_catalog(name: str) -> dict[str, Any]:
    return json.loads(CATALOG_PATHS[name].read_text(encoding="utf-8"))


def file_fingerprint(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def manifest_fingerprint(manifest: dict[str, Any] | None = None) -> str:
    payload = dict(load_manifest() if manifest is None else manifest)
    payload.pop("fingerprint", None)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def materialize_completion_case(case: dict[str, Any]) -> tuple[str, int, int]:
    template = str(case["source_template"])
    marker = "<CURSOR>"
    assert template.count(marker) == 1
    before, after = template.split(marker)
    source = before + after
    cursor = len(before.encode("utf-8"))
    prefix = str(case.get("replacement_prefix", ""))
    assert before.endswith(prefix)
    replacement_start = cursor - len(prefix.encode("utf-8"))
    return source, cursor, replacement_start


def materialize_tokens(case: dict[str, Any]) -> list[dict[str, Any]]:
    source = str(case["source"])
    character_cursor = 0
    result: list[dict[str, Any]] = []
    for token in case["tokens"]:
        text = str(token["text"])
        start_character = source.find(text, character_cursor)
        assert start_character >= 0, (case["id"], text)
        end_character = start_character + len(text)
        start = len(source[:start_character].encode("utf-8"))
        end = len(source[:end_character].encode("utf-8"))
        result.append({"start": start, "end": end, "type": token["type"]})
        character_cursor = end_character
    return result


def iter_case_ids(manifest: dict[str, Any]) -> Iterator[str]:
    for section in (
        "completion_cases",
        "navigation_cases",
        "token_cases",
        "formatter_cases",
        "host_projection_cases",
        "lifecycle_cases",
    ):
        for case in manifest[section]:
            yield str(case["id"])
