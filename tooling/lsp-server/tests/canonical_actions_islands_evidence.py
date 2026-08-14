"""Shared readers for the authored P16-T04 acceptance evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator


LSP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = LSP_ROOT.parents[1]
MANIFEST_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "canonical-actions-islands"
    / "manifest.json"
)

CATALOG_PATHS = {
    "semantic_language": REPOSITORY_ROOT
    / "spec"
    / "frontends"
    / "semantic"
    / "1.0"
    / "language.json",
    "rewrite_registry": REPOSITORY_ROOT
    / "spec"
    / "portability"
    / "equivalence"
    / "1.0"
    / "registry.json",
    "source_contract": REPOSITORY_ROOT
    / "spec"
    / "contracts"
    / "1.0"
    / "source.schema.json",
    "diagnostic_contract": REPOSITORY_ROOT
    / "spec"
    / "contracts"
    / "1.0"
    / "diagnostic.schema.json",
}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


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


def literal_forms(manifest: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for host in manifest["host_contracts"]:
        for form in host["literal_forms"]:
            yield {"language_id": host["language_id"], **form}


def evidence_case_ids(manifest: dict[str, Any]) -> Iterator[str]:
    for section in (
        "action_cases",
        "formatting_cases",
        "refusal_cases",
        "mapping_cases",
        "registry_mutations",
        "lifecycle_cases",
    ):
        for case in manifest[section]:
            yield str(case["id"])
    for form in literal_forms(manifest):
        yield str(form["id"])
