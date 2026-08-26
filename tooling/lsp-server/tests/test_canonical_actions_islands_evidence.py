"""Integrity checks for the authored P16-T04 acceptance denominator."""

from __future__ import annotations

from copy import deepcopy

from canonical_actions_islands_evidence import (
    CATALOG_PATHS,
    evidence_case_ids,
    file_fingerprint,
    literal_forms,
    load_manifest,
    manifest_fingerprint,
)


EXPECTED_HOSTS = {
    "strl",
    "python",
    "typescript",
    "rust",
    "java",
    "c",
    "cpp",
    "csharp",
    "fsharp",
    "go",
    "kotlin",
    "swift",
    "dart",
    "php",
    "ruby",
    "perl",
    "lua",
    "r",
}


def test_manifest_counts_identity_and_fingerprint_are_closed() -> None:
    manifest = load_manifest()
    counts = manifest["expected_counts"]
    assert counts == {
        "action_cases": 18,
        "formatting_cases": 6,
        "host_contracts": 18,
        "lifecycle_cases": 8,
        "literal_forms": 36,
        "mapping_cases": 8,
        "normalized_suffixes": 35,
        "refusal_cases": 18,
        "registry_boundaries": 47,
        "registry_mutations": 14,
        "total_evidence_cases": 108,
    }
    assert len(manifest["action_cases"]) == counts["action_cases"]
    assert len(manifest["formatting_cases"]) == counts["formatting_cases"]
    assert len(manifest["host_contracts"]) == counts["host_contracts"]
    assert len(manifest["refusal_cases"]) == counts["refusal_cases"]
    assert len(manifest["mapping_cases"]) == counts["mapping_cases"]
    assert len(manifest["registry_mutations"]) == counts["registry_mutations"]
    assert len(manifest["lifecycle_cases"]) == counts["lifecycle_cases"]
    forms = list(literal_forms(manifest))
    assert len(forms) == counts["literal_forms"]
    case_ids = list(evidence_case_ids(manifest))
    assert len(case_ids) == counts["total_evidence_cases"]
    assert len(case_ids) == len(set(case_ids))
    assert manifest_fingerprint(manifest) == manifest["fingerprint"]


def test_canonical_authority_catalogs_and_strategy_are_pinned() -> None:
    manifest = load_manifest()
    assert {
        name: file_fingerprint(path) for name, path in CATALOG_PATHS.items()
    } == manifest["catalog_fingerprints"]
    authority = manifest["action_authority"]
    assert authority["diagnostic_code"] == "STRL-QUALITY-0002"
    assert authority["strategy_id"] == "rewrite.repeat_exactly_once.elide.v1"
    assert authority["strategy_fingerprint"] == (
        "sha256:999caab104647f02de759c5dde48d5d6d020a464f9de793617088ebbb0f96d17"
    )
    assert authority["proof_conditions"] == [
        "original_node_is_repeat",
        "direct_body_relationship",
        "bounds_exactly_one",
        "mode_non_possessive",
    ]
    assert authority["forbidden_diagnostic_codes"] == ["STRL-SAFETY-0003"]
    assert manifest["starting_registry_fingerprint"] == (
        "sha256:7244c5d6933f18699be16d731fdb6d166d294b7be985d863280c54e1500d233d"
    )


def test_action_and_formatting_cases_are_exact_source_expectations() -> None:
    manifest = load_manifest()
    emitted = [
        case
        for case in manifest["action_cases"]
        if case["disposition"].startswith("emit_")
    ]
    assert len(emitted) == 4
    for case in manifest["action_cases"]:
        assert case["frontend"] in {"regex", "semantic"}
        assert isinstance(case["source"], str) and case["source"]
    for case in emitted:
        assert case["diagnostic_code"] == "STRL-QUALITY-0002"
        assert case["source"].count(case["wrapper_text"]) == 1
        assert case["replacement_text"] in case["wrapper_text"]
    assert {
        case["diagnostic_code"]
        for case in manifest["action_cases"]
        if case["id"].startswith("action.refuse.redos")
        or case["id"].startswith("action.refuse.safety_code")
    } == {"STRL-SAFETY-0003"}
    for case in manifest["formatting_cases"]:
        assert isinstance(case["source"], str) and case["source"]
        if case["disposition"] == "one_full_document_edit":
            assert case["frontend"] == "semantic"
            assert isinstance(case["expected"], str)
            assert case["expected"] != case["source"]
        elif case["expected"] is not None:
            assert case["expected"] == case["source"]


def test_every_host_suffix_boundary_and_literal_form_is_explicit() -> None:
    manifest = load_manifest()
    hosts = manifest["host_contracts"]
    assert {host["language_id"] for host in hosts} == EXPECTED_HOSTS
    assert [host["language_id"] for host in hosts] == sorted(
        EXPECTED_HOSTS, key=lambda value: (value != "strl", value)
    )
    suffixes = [suffix for host in hosts for suffix in host["suffixes"]]
    assert len(suffixes) == manifest["expected_counts"]["normalized_suffixes"]
    assert len(suffixes) == len(set(suffixes))
    boundaries = [spelling for host in hosts for spelling in host["boundary_spellings"]]
    assert len(boundaries) == manifest["expected_counts"]["registry_boundaries"]
    for host in hosts:
        assert host["frontend"] in {"native", "regex"}
        assert host["target_profile_policy"] == "never_infer"
        assert len(host["boundary_spellings"]) == len(set(host["boundary_spellings"]))
        if host["language_id"] == "strl":
            assert host["frontend"] == "native"
            assert host["literal_forms"] == []
        else:
            assert host["frontend"] == "regex"
            assert host["boundary_spellings"]
            assert host["literal_forms"]
    for form in literal_forms(manifest):
        assert form["source_template"].count("<PATTERN>") == 1
        assert form["content_policy"] == "identity_only"
        assert form["escape_policy"] in {"forbid", "raw_identity"}
        assert form["interpolation_policy"] == "forbid"


def test_refusal_mutation_lifecycle_and_resource_dimensions_are_closed() -> None:
    manifest = load_manifest()
    assert all(
        isinstance(case["source"], str) and case["source"]
        for case in manifest["refusal_cases"]
    )
    for case in manifest["mapping_cases"]:
        assert case["encodings"] == ["utf-8", "utf-16", "utf-32"]
        marker_count = case["source_template"].count("<PATTERN>")
        assert marker_count == (0 if case["id"] == "mapping.multiple.islands" else 1)
    assert {case["reason"] for case in manifest["refusal_cases"]} == {
        "ambiguous_boundary",
        "concatenated_expression",
        "cr_transformation",
        "initial_newline_elision",
        "interpolation",
        "processed_escape",
        "source_limit",
        "unterminated_comment",
        "unterminated_literal",
        "unsupported_literal_form",
    }
    assert {case["mutation"] for case in manifest["registry_mutations"]} == {
        "boundary_expression_too_long",
        "duplicate_boundary_id",
        "duplicate_host_id",
        "duplicate_suffix",
        "fingerprint_mismatch",
        "host_limit",
        "invalid_regex",
        "malformed_json",
        "missing_registry",
        "noncanonical_order",
        "per_host_boundary_limit",
        "unknown_literal_form",
        "unknown_scanner",
        "unsupported_version",
    }
    assert {case["event"] for case in manifest["lifecycle_cases"]} == {
        "cancelled_projection",
        "close_cleanup",
        "document_change",
        "malformed_evidence",
        "missing_service",
        "position_encoding_change",
        "resource_exhaustion",
        "stale_document_version",
    }
    assert manifest["resource_limits"] == {
        "boundary_expression_bytes": 1024,
        "comment_nesting": 64,
        "document_bytes": 1048576,
        "hosts": 18,
        "islands_per_document": 256,
        "literal_delimiter_bytes": 32,
        "literal_scan_bytes": 1048576,
        "mappings_per_document": 1048577,
        "per_host_boundaries": 16,
        "request_seconds": 5,
    }


def test_denominator_shrinkage_changes_counts_and_fingerprint() -> None:
    manifest = load_manifest()
    shrunk = deepcopy(manifest)
    shrunk["action_cases"].pop()
    assert len(shrunk["action_cases"]) != shrunk["expected_counts"]["action_cases"]
    assert manifest_fingerprint(shrunk) != manifest["fingerprint"]
