"""Closed P16-T03 editor-intelligence denominator and authority checks."""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from pathlib import Path
import sys

import pytest

LSP_ROOT = str(Path(__file__).resolve().parents[1])
if LSP_ROOT not in sys.path:
    sys.path.insert(0, LSP_ROOT)

evidence = import_module("canonical_intelligence_evidence")
CATALOG_PATHS = evidence.CATALOG_PATHS
file_fingerprint = evidence.file_fingerprint
iter_case_ids = evidence.iter_case_ids
load_catalog = evidence.load_catalog
load_manifest = evidence.load_manifest
manifest_fingerprint = evidence.manifest_fingerprint

canonical = import_module("server.canonical_intelligence")
CanonicalIntelligence = canonical.CanonicalIntelligence
EditorServiceError = canonical.EditorServiceError
catalog_definition = canonical.catalog_definition


def test_manifest_has_closed_version_fingerprint_legend_and_limits() -> None:
    manifest = load_manifest()
    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["editor_evidence_contract_version"] == "1.0.0"
    assert manifest["fingerprint"] == manifest_fingerprint(manifest)
    assert manifest["semantic_token_legend"] == [
        "string",
        "number",
        "operator",
        "regexp",
        "keyword",
        "function",
        "variable",
        "comment",
    ]
    assert manifest["semantic_token_modifiers"] == []
    assert manifest["completion_tiers"] == [
        "parser_expected_terminal",
        "canonical_capture_identity",
        "simply_operation_or_stdlib_helper",
        "governed_option_or_profile",
    ]
    assert manifest["resource_limits"] == {
        "max_source_bytes": 1_048_576,
        "max_completion_items": 256,
        "max_tokens": 16_384,
        "max_symbols": 4_096,
        "max_capture_locations": 16_384,
        "max_islands": 256,
        "projection_timeout_seconds": 5.0,
    }


def test_manifest_has_complete_unique_case_denominator() -> None:
    manifest = load_manifest()
    expected_counts = {
        "completion_cases": 21,
        "navigation_cases": 13,
        "token_cases": 8,
        "formatter_cases": 3,
        "host_projection_cases": 3,
        "lifecycle_cases": 17,
    }
    assert {name: len(manifest[name]) for name in expected_counts} == expected_counts
    case_ids = list(iter_case_ids(manifest))
    assert len(case_ids) == 65
    assert len(case_ids) == len(set(case_ids))


def test_manifest_fingerprint_detects_evidence_shrinkage() -> None:
    manifest = load_manifest()
    reduced = deepcopy(manifest)
    reduced["completion_cases"].pop()
    assert manifest_fingerprint(reduced) != manifest["fingerprint"]


def test_canonical_catalog_fingerprints_and_versions_are_exact() -> None:
    manifest = load_manifest()
    catalogs = manifest["canonical_catalogs"]
    for name, expected in catalogs.items():
        assert expected["path"].replace("/", "\\") in str(CATALOG_PATHS[name])
        assert file_fingerprint(CATALOG_PATHS[name]) == expected["sha256"]

    semantic = load_catalog("semantic_language")
    assert (
        semantic["contract_version"]
        == catalogs["semantic_language"]["contract_version"]
    )
    assert (
        len(semantic["keyword_terminals"])
        == catalogs["semantic_language"]["keyword_count"]
    )

    regex = load_catalog("regex_dialect")
    assert regex["contract_version"] == catalogs["regex_dialect"]["contract_version"]
    assert (
        regex["directives"]["supported"]
        == catalogs["regex_dialect"]["supported_directives"]
    )
    assert (
        regex["directives"]["flag_letters"] == catalogs["regex_dialect"]["flag_letters"]
    )

    simply = load_catalog("simply_protocol")
    assert simply["protocol_version"] == catalogs["simply_protocol"]["protocol_version"]
    assert [operation["id"] for operation in simply["operations"]] == catalogs[
        "simply_protocol"
    ]["operation_ids"]

    stdlib = load_catalog("stdlib_registry")
    assert stdlib["registry_version"] == catalogs["stdlib_registry"]["registry_version"]
    assert (
        stdlib["fingerprint"]["value"]
        == catalogs["stdlib_registry"]["declared_fingerprint"]
    )
    assert [helper["id"] for helper in stdlib["helpers"]] == catalogs[
        "stdlib_registry"
    ]["helper_ids"]
    levels: dict[str, int] = {}
    for helper in stdlib["helpers"]:
        level = helper["guarantee"]["level"]
        levels[level] = levels.get(level, 0) + 1
    assert levels == catalogs["stdlib_registry"]["guarantee_levels"]


def test_lifecycle_denominator_covers_mutation_identity_failure_and_recovery() -> None:
    cases = load_manifest()["lifecycle_cases"]
    assert {case["class"] for case in cases} == {
        "publication",
        "mutation",
        "close",
        "cancellation",
        "stale",
        "identity",
        "cache",
        "failure",
        "recovery",
    }
    ids = {case["id"] for case in cases}
    assert {
        "editor-stale-result-discarded",
        "editor-cursor-offset-separates-completion",
        "editor-projection-version-invalidates",
        "editor-recovery-after-failure",
    } <= ids


def test_editor_transport_rejects_stale_identity_and_invalid_utf8_cursor() -> None:
    editor = CanonicalIntelligence()
    result = editor.project("é", frontend="regex")
    stale = deepcopy(result)
    stale["source_id"] = "src:cli.stale"
    with pytest.raises(EditorServiceError, match="stale"):
        editor._validate(stale, "é", "regex", None)
    with pytest.raises(EditorServiceError, match="UTF-8 boundary"):
        editor.project("é", frontend="regex", cursor_byte=1)


def test_catalog_navigation_resolves_only_exact_authored_identities() -> None:
    stdlib = catalog_definition("date_time", binding_id="python")
    simply = catalog_definition("sequence", binding_id="python")
    assert stdlib is not None and stdlib.path == CATALOG_PATHS["stdlib_registry"]
    assert simply is not None and simply.path == CATALOG_PATHS["simply_protocol"]
    assert catalog_definition("mail", binding_id="python") is None
