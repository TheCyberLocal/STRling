"""Authored completion-context denominator for P16-T03."""

from __future__ import annotations

from canonical_intelligence_evidence import (
    load_catalog,
    load_manifest,
    materialize_completion_case,
)


def test_completion_cases_cover_frontends_contexts_prefixes_and_no_results() -> None:
    cases = load_manifest()["completion_cases"]
    assert len(cases) == 21
    assert {case["frontend"] for case in cases} == {"semantic", "regex", "host"}
    assert {case["context"] for case in cases} == {
        "parser",
        "capture",
        "simply_member",
        "none",
    }
    assert sum(not case["expected_labels"] for case in cases) == 5
    assert sum("replacement_prefix" in case for case in cases) == 4

    for case in cases:
        source, cursor, replacement_start = materialize_completion_case(case)
        assert 0 <= replacement_start <= cursor <= len(source.encode("utf-8"))
        assert case["expected_labels"] == sorted(set(case["expected_labels"]))


def test_completion_values_are_governed_by_canonical_catalogs() -> None:
    manifest = load_manifest()
    cases = {case["id"]: case for case in manifest["completion_cases"]}
    semantic_keywords = set(load_catalog("semantic_language")["keyword_terminals"])
    root_labels = set(cases["semantic-root-constructs"]["expected_labels"])
    assert root_labels <= semantic_keywords

    regex = load_catalog("regex_dialect")
    assert (
        cases["regex-preamble-directive"]["expected_labels"]
        == regex["directives"]["supported"]
    )
    assert (
        cases["regex-flag-values"]["expected_labels"]
        == regex["directives"]["flag_letters"]
    )

    simply = load_catalog("simply_protocol")
    stdlib = load_catalog("stdlib_registry")
    operations = {operation["id"] for operation in simply["operations"]}
    python_binding = next(
        binding
        for binding in stdlib["host_bindings"]
        if binding["binding_id"] == "python"
    )
    helpers = {
        public_name
        for exposure in python_binding["exposures"]
        for public_name in exposure["public_names"]
    }
    assert set(cases["host-simply-boundary"]["expected_labels"]) == operations | helpers


def test_completion_denominator_preserves_scope_and_non_guessing_rules() -> None:
    cases = {case["id"]: case for case in load_manifest()["completion_cases"]}
    assert cases["semantic-reference-capture"]["expected_labels"] == ["word"]
    assert cases["semantic-reference-no-forward"]["expected_labels"] == []
    assert cases["regex-reference-no-forward"]["expected_labels"] == []
    assert cases["semantic-malformed-no-guess"]["expected_labels"] == []
    assert cases["regex-no-stdlib-syntax"]["expected_labels"] == []
    assert cases["host-unrecognized-member"]["expected_labels"] == []
