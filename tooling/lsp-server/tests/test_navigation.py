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

from canonical_intelligence_evidence import (
    load_catalog,
    load_manifest,
    materialize_completion_case,
)


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PY_SRC = os.path.join(ROOT, "bindings", "python", "src")
LSP_SRC = os.path.join(ROOT, "tooling", "lsp-server")

for path in (PY_SRC, LSP_SRC):
    if path not in sys.path:
        sys.path.insert(0, path)


from server.deferred_intelligence import format_pattern  # noqa: E402


# --------------------------------------------------------------------------- #
# Pure intelligence layer                                                     #
# --------------------------------------------------------------------------- #


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
        out = format_pattern(src)
        assert out["success"], out
        assert format_pattern(out["formatted"])["success"]

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

    with server_mod._STATE_LOCK:
        server_mod._LAST_DIAGNOSTICS.clear()
        server_mod._ISLANDS_BY_URI.clear()
        server_mod._CANONICAL_RESULTS_BY_URI.clear()
        server_mod._SNAPSHOTS_BY_URI.clear()
        server_mod._EDITOR_CACHE.clear()
        server_mod._EDITOR_CACHE_ORDER.clear()
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


def _compile_current(server_module, uri: str, source: str) -> None:
    _patch_workspace(server_module, source)
    snapshot = server_module._capture_snapshot(server_module.server, uri, 1)
    compiled = server_module._compile_snapshot(snapshot)
    with server_module._STATE_LOCK:
        server_module._CANONICAL_RESULTS_BY_URI[uri] = compiled
        server_module._ISLANDS_BY_URI[uri] = list(compiled.islands)


class TestDocumentSymbolHandler:
    def test_native_strl_outline(self, server_module, lsp_module) -> None:
        source = "(?<word>é+)x\\k<word>"
        uri = "file:///tmp/x.strl"
        _compile_current(server_module, uri, source)
        params = lsp_module.DocumentSymbolParams(
            text_document=lsp_module.TextDocument(uri=uri),
        )
        symbols = server_module.document_symbol(server_module.server, params)
        assert len(symbols) == 1
        assert symbols[0].detail == "sequence · node:regex-compat/00000001"
        assert symbols[0].range.end.character == len(source)
        assert symbols[0].children[0].detail.endswith(
            "capture:regex-compat/00001"
        )

    def test_host_outline_projects_to_host_coordinates(
        self, server_module, lsp_module
    ) -> None:
        py_src = 'pattern = s.parse("(foo|bar)")\n'
        uri = "file:///tmp/x.py"
        _compile_current(server_module, uri, py_src)
        params = lsp_module.DocumentSymbolParams(
            text_document=lsp_module.TextDocument(uri=uri),
        )
        symbols = server_module.document_symbol(server_module.server, params)
        assert len(symbols) == 1
        expected_col = py_src.index("(foo|bar)")
        assert symbols[0].range.start.line == 0
        assert symbols[0].range.start.character == expected_col


class TestDefinitionHandler:
    def test_jump_to_registry_from_host_call(self, server_module, lsp_module) -> None:
        py_src = "value = s.date_time()\n"
        uri = "file:///tmp/x.py"
        _compile_current(server_module, uri, py_src)
        col = py_src.index("date_time") + 1
        params = lsp_module.DefinitionParams(
            text_document=lsp_module.TextDocument(uri=uri),
            position=lsp_module.Position(line=0, character=col),
        )
        loc = server_module.definition(server_module.server, params)
        assert loc is not None
        assert loc.uri.endswith("/spec/stdlib/registry/1.0/registry.json")

    def test_jump_inside_island(self, server_module, lsp_module) -> None:
        py_src = 'pattern = s.parse(r"(?<word>a)\\k<word>")\n'
        uri = "file:///tmp/x.py"
        _compile_current(server_module, uri, py_src)
        col = py_src.rindex("word") + 1
        params = lsp_module.DefinitionParams(
            text_document=lsp_module.TextDocument(uri=uri),
            position=lsp_module.Position(line=0, character=col),
        )
        loc = server_module.definition(server_module.server, params)
        assert loc is not None
        assert loc.uri == uri
        assert loc.range.start.character == py_src.index("word")

    def test_trigger_alias_returns_none(self, server_module, lsp_module) -> None:
        source = "value = s.mail()\n"
        uri = "file:///tmp/x.py"
        _compile_current(server_module, uri, source)
        params = lsp_module.DefinitionParams(
            text_document=lsp_module.TextDocument(uri=uri),
            position=lsp_module.Position(line=0, character=source.index("mail") + 1),
        )
        assert server_module.definition(server_module.server, params) is None


class TestReferencesHandler:
    def test_reference_feature_and_capability_are_registered(
        self, server_module, lsp_module
    ) -> None:
        assert lsp_module.TEXT_DOCUMENT_REFERENCES in server_module.server._features
        capabilities = server_module.server._initialize_result()["capabilities"]
        assert capabilities["referencesProvider"] is True
        params = server_module.server._coerce_params(
            lsp_module.TEXT_DOCUMENT_REFERENCES,
            {
                "textDocument": {"uri": "file:///tmp/reference.strl"},
                "position": {"line": 2, "character": 3},
                "context": {"includeDeclaration": True},
            },
        )
        assert params.position == lsp_module.Position(line=2, character=3)
        assert params.context.include_declaration is True

    def test_capture_references_share_canonical_identity(
        self, server_module, lsp_module
    ) -> None:
        source = "(?<word>é+)x\\k<word>"
        uri = "file:///tmp/references.strl"
        _compile_current(server_module, uri, source)
        params = lsp_module.ReferenceParams(
            text_document=lsp_module.TextDocument(uri=uri),
            position=lsp_module.Position(line=0, character=4),
            context=lsp_module.ReferenceContext(include_declaration=True),
        )
        locations = server_module.references(server_module.server, params)
        assert len(locations) == 2
        assert [location.range.start.character for location in locations] == [3, 15]


class TestCompletionAndTokenHandlers:
    def test_partial_semantic_completion_uses_exact_text_edit(
        self, server_module, lsp_module
    ) -> None:
        case = next(
            item
            for item in load_manifest()["completion_cases"]
            if item["id"] == "semantic-root-prefix"
        )
        source, cursor, replacement_start = materialize_completion_case(case)
        uri = "file:///tmp/completion.semantic.strling"
        _compile_current(server_module, uri, source)
        params = lsp_module.CompletionParams(
            text_document=lsp_module.TextDocument(uri=uri),
            position=lsp_module.Position(line=2, character=len("pattern se")),
        )
        result = server_module.completion(server_module.server, params)
        assert [item.label for item in result.items] == ["sequence"]
        edit = result.items[0].text_edit
        assert edit is not None
        assert edit.range.start.character == len("pattern ")
        assert edit.range.end.character == len("pattern se")
        assert cursor - replacement_start == 2

    def test_host_completion_is_exactly_scoped_to_s_member_boundary(
        self, server_module, lsp_module
    ) -> None:
        source = "value = s.da\n"
        uri = "file:///tmp/completion.py"
        _compile_current(server_module, uri, source)
        params = lsp_module.CompletionParams(
            text_document=lsp_module.TextDocument(uri=uri),
            position=lsp_module.Position(line=0, character=source.index("da") + 2),
        )
        result = server_module.completion(server_module.server, params)
        assert [item.label for item in result.items] == ["date_time"]

    def test_host_semantic_tokens_project_inside_literal(
        self, server_module, lsp_module
    ) -> None:
        source = 'pattern = s.parse("é+")\n'
        uri = "file:///tmp/tokens.py"
        _compile_current(server_module, uri, source)
        params = lsp_module.SemanticTokensParams(
            text_document=lsp_module.TextDocument(uri=uri)
        )
        result = server_module.semantic_tokens_full(server_module.server, params)
        assert len(result.data) == 10
        first = result.data[:5]
        second = result.data[5:]
        start = source.index("é")
        assert first == [0, start, 1, server_module.TOKEN_TYPES.index("regexp"), 0]
        assert second == [0, 1, 1, server_module.TOKEN_TYPES.index("operator"), 0]


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
