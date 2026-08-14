"""Coverage for document symbols, definition, and formatting handlers.

These tests pin the structural-navigation surface of the STRling LSP:
the outline tree exposed via ``textDocument/documentSymbol``, the
registry-backed ``textDocument/definition`` jump, and the safe
host-aware ``textDocument/formatting`` rewrite.
"""

from __future__ import annotations

import os
import sys

import pytest

from canonical_intelligence_evidence import load_catalog, load_manifest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PY_SRC = os.path.join(ROOT, "bindings", "python", "src")
LSP_SRC = os.path.join(ROOT, "tooling", "lsp-server")

for path in (PY_SRC, LSP_SRC):
    if path not in sys.path:
        sys.path.insert(0, path)


from STRling.core.intelligence import (  # noqa: E402
    extract_document_symbols,
    find_registry_definition,
    format_pattern,
)


# --------------------------------------------------------------------------- #
# Pure intelligence layer                                                     #
# --------------------------------------------------------------------------- #


class TestDocumentSymbolScanner:
    def test_top_level_group(self) -> None:
        syms = extract_document_symbols("(abc)+")
        assert len(syms) == 1
        outer = syms[0]
        assert outer["kind"] == 13  # SymbolKind.Variable for capturing group
        assert outer["range"]["start"] == {"line": 0, "character": 0}
        assert outer["range"]["end"]["character"] == 5

    def test_nested_groups_form_tree(self) -> None:
        syms = extract_document_symbols("(a(b(c)))")
        assert len(syms) == 1
        depth = 0
        node = syms[0]
        while node.get("children"):
            child_groups = [
                c for c in node["children"] if c["detail"].endswith("group")
            ]
            if not child_groups:
                break
            node = child_groups[0]
            depth += 1
        assert depth == 2

    def test_named_atomic_lookaround(self) -> None:
        syms = extract_document_symbols("(?>x)(?=y)(?<n>z)(?<!q)")
        kinds = [(s["name"], s["detail"]) for s in syms]
        assert ("atomic", "atomic group") in kinds
        assert ("lookahead", "positive lookahead") in kinds
        assert ("n", "named group") in kinds
        assert ("lookbehind", "negative lookbehind") in kinds

    def test_alternation_branches_become_children(self) -> None:
        syms = extract_document_symbols("(foo|bar|baz)")
        assert len(syms) == 1
        branch_names = [c["name"] for c in syms[0]["children"]]
        assert "foo" in branch_names
        assert "bar" in branch_names
        assert "baz" in branch_names

    def test_character_class_does_not_open_group(self) -> None:
        # Brackets with a literal '(' inside must not confuse the scanner.
        syms = extract_document_symbols("[(]+")
        assert syms == []


class TestRegistryDefinition:
    def test_canonical_name_resolves_to_registry_file(self) -> None:
        loc = find_registry_definition("ip")
        assert loc is not None
        assert loc["uri"].endswith("/spec/stdlib/registry.json")
        assert loc["range"]["start"]["character"] >= 0

    def test_trigger_keyword_resolves_to_canonical_entry(self) -> None:
        canonical = find_registry_definition("email")
        keyword = find_registry_definition("mail")
        assert canonical is not None and keyword is not None
        assert canonical == keyword

    def test_unknown_word_returns_none(self) -> None:
        assert find_registry_definition("not_a_real_pattern_name") is None
        assert find_registry_definition("") is None


class TestFormatter:
    @pytest.mark.parametrize(
        "src",
        [
            "(a|bc)+(?=d)hello",
            "(?<year>\\d{4})-(?<month>\\d{2})",
            "(foo|bar|baz){2,5}?",
            "[a-z]+@[a-z]+\\.[a-z]{2,}",
            "(a(b(c(d))))",
        ],
    )
    def test_round_trip_through_parser(self, src: str) -> None:
        from STRling.core.parser import parse

        out = format_pattern(src)
        assert out["success"], out
        parse(out["formatted"])  # must not raise

    def test_blank_input_returns_unchanged(self) -> None:
        assert format_pattern("")["formatted"] == ""

    def test_invalid_input_surfaces_diagnostic(self) -> None:
        out = format_pattern("(unclosed")
        assert out["success"] is False
        assert len(out["diagnostics"]) == 1


# --------------------------------------------------------------------------- #
# LSP handlers                                                                #
# --------------------------------------------------------------------------- #


@pytest.fixture
def server_module():
    # ``server`` is a package whose hand-authored implementation lives in
    # ``server/server.py``; the package ``__init__`` is intentionally empty,
    # so we import the inner submodule directly to access the in-process
    # caches and handler functions.
    from server import server as server_mod  # type: ignore[import-not-found]

    server_mod._LAST_DIAGNOSTICS.clear()
    server_mod._ISLANDS_BY_URI.clear()
    return server_mod


@pytest.fixture
def lsp_module():
    from lsprotocol import types as lsp  # type: ignore[import-not-found]

    return lsp


class _FakeDoc:
    def __init__(self, source: str) -> None:
        self.source = source


class _FakeWorkspace:
    def __init__(self, source: str) -> None:
        self._source = source

    def get_text_document(self, _uri: str) -> _FakeDoc:
        return _FakeDoc(self._source)


def _patch_workspace(server_module, source: str) -> None:
    server_module.server.workspace = _FakeWorkspace(source)  # type: ignore[attr-defined]


class TestDocumentSymbolHandler:
    def test_native_strl_outline(self, server_module, lsp_module) -> None:
        _patch_workspace(server_module, "(foo|bar)+")
        params = lsp_module.DocumentSymbolParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/x.strl"),
        )
        symbols = server_module.document_symbol(server_module.server, params)
        assert len(symbols) == 1
        # The group span covers ``(foo|bar)`` (9 characters); the
        # trailing ``+`` quantifier sits outside the group symbol.
        assert symbols[0].range.end.character == 9
        # Outer group has two alt branches as children.
        assert {c.name for c in symbols[0].children} >= {"foo", "bar"}

    def test_host_outline_projects_to_host_coordinates(
        self, server_module, lsp_module
    ) -> None:
        py_src = 'pattern = s.parse("(foo|bar)")\n'
        _patch_workspace(server_module, py_src)
        params = lsp_module.DocumentSymbolParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/x.py"),
        )
        symbols = server_module.document_symbol(server_module.server, params)
        assert len(symbols) == 1
        # The literal opens at the index of "(foo|bar)" inside py_src.
        expected_col = py_src.index("(foo|bar)")
        assert symbols[0].range.start.line == 0
        assert symbols[0].range.start.character == expected_col


class TestDefinitionHandler:
    def test_jump_to_registry_from_host_call(self, server_module, lsp_module) -> None:
        # ``email`` is *outside* any island here \u2014 it is the host method
        # name. The handler must still fall back to host-buffer word
        # extraction so calls like ``s.email()`` resolve.
        py_src = "value = s.email()\n"
        _patch_workspace(server_module, py_src)
        col = py_src.index("email") + 1  # cursor mid-word
        params = lsp_module.DefinitionParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/x.py"),
            position=lsp_module.Position(line=0, character=col),
        )
        loc = server_module.definition(server_module.server, params)
        assert loc is not None
        assert loc.uri.endswith("/spec/stdlib/registry.json")

    def test_jump_inside_island(self, server_module, lsp_module) -> None:
        py_src = 'pattern = s.parse("ip")\n'
        _patch_workspace(server_module, py_src)
        col = py_src.index("ip") + 1
        params = lsp_module.DefinitionParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/x.py"),
            position=lsp_module.Position(line=0, character=col),
        )
        loc = server_module.definition(server_module.server, params)
        assert loc is not None
        # The ip entry's name field sits on a known line in the registry.
        assert loc.range.start.line >= 0

    def test_unknown_word_returns_none(self, server_module, lsp_module) -> None:
        _patch_workspace(server_module, "value = nothing_useful\n")
        params = lsp_module.DefinitionParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/x.py"),
            position=lsp_module.Position(line=0, character=10),
        )
        assert server_module.definition(server_module.server, params) is None


class TestFormattingHandler:
    def test_native_strl_formats_whole_document(
        self, server_module, lsp_module
    ) -> None:
        src = "(a|b)+xyz"
        _patch_workspace(server_module, src)
        params = lsp_module.DocumentFormattingParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/x.strl"),
            options=lsp_module.FormattingOptions(tab_size=2, insert_spaces=True),
        )
        edits = server_module.formatting(server_module.server, params)
        assert len(edits) == 1
        assert edits[0].range.start.line == 0
        assert edits[0].range.start.character == 0
        # Native edit covers the whole single-line source.
        assert edits[0].range.end.character == len(src)
        assert "\n" in edits[0].new_text

    def test_host_formatting_preserves_quotes(self, server_module, lsp_module) -> None:
        py_src = 'pattern = s.parse("(a|b)+xyz")\n'
        _patch_workspace(server_module, py_src)
        params = lsp_module.DocumentFormattingParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/x.py"),
            options=lsp_module.FormattingOptions(tab_size=2, insert_spaces=True),
        )
        edits = server_module.formatting(server_module.server, params)
        assert len(edits) == 1
        # The edit range covers ONLY the interior of the literal: it must
        # not include the surrounding quotes or the host code around it.
        literal_start = py_src.index('"') + 1
        literal_end = py_src.rindex('"')
        assert edits[0].range.start.character == literal_start
        assert edits[0].range.end.character == literal_end
        assert '"' not in edits[0].new_text
        # Applying the edit by string slicing must yield syntactically
        # valid Python (parens balanced, quotes intact).
        rewritten = py_src[:literal_start] + edits[0].new_text + py_src[literal_end:]
        assert rewritten.count('"') == py_src.count('"')
        # Parenthesis balance check on the host source.
        assert rewritten.count("(") - rewritten.count(")") == 0

    def test_no_change_returns_empty_edits(self, server_module, lsp_module) -> None:
        src = "abc"  # already \"formatted\" \u2014 no nested groups
        _patch_workspace(server_module, src)
        params = lsp_module.DocumentFormattingParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/y.strl"),
            options=lsp_module.FormattingOptions(),
        )
        edits = server_module.formatting(server_module.server, params)
        # Identity formatter result -> zero edits.
        assert edits == [] or edits[0].new_text.strip() == "abc"


class TestCanonicalNavigationEvidence:
    def test_navigation_denominator_covers_identity_and_no_result_cases(self) -> None:
        cases = load_manifest()["navigation_cases"]
        assert len(cases) == 13
        assert {case["frontend"] for case in cases} == {
            "semantic",
            "regex",
            "host",
        }
        assert {case["kind"] for case in cases} == {
            "symbols",
            "definition",
            "references",
            "catalog_definition",
            "no_result",
        }
        ids = {case["id"] for case in cases}
        assert {
            "semantic-reference-definition",
            "semantic-references-without-declaration",
            "regex-named-reference-definition",
            "regex-numeric-reference-definition",
            "trigger-keyword-does-not-navigate",
        } <= ids

    def test_symbol_and_capture_spans_are_utf8_exact_and_bounded(self) -> None:
        for case in load_manifest()["navigation_cases"]:
            source_bytes = case["source"].encode("utf-8")
            for node in case.get("expected_nodes", []):
                start, end = node["span"]
                assert 0 <= start <= end <= len(source_bytes)
            for key in ("expected_declaration",):
                if key in case:
                    start, end = case[key]
                    assert 0 <= start < end <= len(source_bytes)
            for start, end in case.get("expected_locations", []):
                assert 0 <= start < end <= len(source_bytes)

    def test_catalog_navigation_targets_authored_authority_not_projection(self) -> None:
        cases = {case["id"]: case for case in load_manifest()["navigation_cases"]}
        stdlib = cases["stdlib-python-definition"]
        simply = cases["simply-sequence-definition"]
        assert stdlib["authority_path"] == "spec/stdlib/registry/1.0/registry.json"
        assert stdlib["json_pointer"] == "/helpers/0"
        assert (
            load_catalog("stdlib_registry")["helpers"][0]["id"]
            == stdlib["canonical_id"]
        )
        assert simply["authority_path"] == "spec/frontends/simply/1.1/protocol.json"
        assert simply["json_pointer"] == "/operations/13"
        assert (
            load_catalog("simply_protocol")["operations"][13]["id"]
            == simply["canonical_id"]
        )

    def test_formatter_evidence_requires_alpha_equivalence_and_recomputation(
        self,
    ) -> None:
        cases = load_manifest()["formatter_cases"]
        assert len(cases) == 3
        assert all(case["expected_alpha_equivalent"] for case in cases)
        assert all(case["expected_identity_recomputed"] for case in cases)
