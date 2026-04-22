"""Code-action coverage for the STRling language server.

The tests verify that nested unbounded quantifiers are surfaced as
``REDOS_RISK`` warnings *and* materialise as concrete quick-fix code
actions whose ``WorkspaceEdit`` targets the correct host coordinates
inside both native ``.strl`` files and embedded host-language literals.
"""

from __future__ import annotations

import os
import sys

import pytest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PY_SRC = os.path.join(ROOT, "bindings", "python", "src")
LSP_SRC = os.path.join(ROOT, "tooling", "lsp-server")

for path in (PY_SRC, LSP_SRC):
    if path not in sys.path:
        sys.path.insert(0, path)


from STRling.core.intelligence import (  # noqa: E402
    analyze_content,
    detect_safety_diagnostics,
)


# --------------------------------------------------------------------------- #
# Detector                                                                    #
# --------------------------------------------------------------------------- #


class TestRedosDetector:
    def test_canonical_nested_quantifier_flagged(self) -> None:
        diags = detect_safety_diagnostics("(a+)+")
        assert len(diags) == 1
        d = diags[0]
        assert d["code"] == "REDOS_RISK"
        assert d["severity"] == 2
        assert d["range"]["start"] == {"line": 0, "character": 0}
        assert d["range"]["end"] == {"line": 0, "character": 5}

    def test_replacements_payload_shape(self) -> None:
        d = detect_safety_diagnostics("(a+)+")[0]
        replacements = d["data"]["replacements"]
        assert len(replacements) == 2
        atomic, possessive = replacements
        assert atomic["newText"] == "(?>a+)+"
        assert possessive["newText"] == "(a++)+"
        assert "atomic" in atomic["title"].lower()
        assert "possessive" in possessive["title"].lower()

    def test_star_inner_and_outer(self) -> None:
        diags = detect_safety_diagnostics("(a*)*")
        assert len(diags) == 1
        replacements = diags[0]["data"]["replacements"]
        assert replacements[0]["newText"] == "(?>a*)*"
        assert replacements[1]["newText"] == "(a*+)*"

    def test_no_warning_for_safe_patterns(self) -> None:
        assert detect_safety_diagnostics("(abc)+") == []
        assert detect_safety_diagnostics("a+") == []
        assert detect_safety_diagnostics("") == []

    def test_multiline_range_projection(self) -> None:
        src = "Word()\n  (a+)+\n"
        diags = detect_safety_diagnostics(src)
        assert len(diags) == 1
        rng = diags[0]["range"]
        assert rng["start"] == {"line": 1, "character": 2}
        assert rng["end"] == {"line": 1, "character": 7}

    def test_analyze_content_threads_safety_warnings(self) -> None:
        out = analyze_content("(a+)+")
        assert out["success"] is True
        assert any(d["code"] == "REDOS_RISK" for d in out["diagnostics"])


# --------------------------------------------------------------------------- #
# Server-level code action handler                                            #
# --------------------------------------------------------------------------- #


@pytest.fixture
def server_module():
    import server  # type: ignore[import-not-found]

    server._LAST_DIAGNOSTICS.clear()
    server._ISLANDS_BY_URI.clear()
    return server


@pytest.fixture
def lsp_module():
    from lsprotocol import types as lsp  # type: ignore[import-not-found]

    return lsp


class TestCodeActionRegistration:
    def test_feature_registered(self, server_module, lsp_module) -> None:
        assert lsp_module.TEXT_DOCUMENT_CODE_ACTION in server_module.server._features
        opts = server_module.server._feature_options[
            lsp_module.TEXT_DOCUMENT_CODE_ACTION
        ]
        assert lsp_module.CodeActionKind.QuickFix in opts.code_action_kinds


class TestNativeStrlCodeActions:
    def test_redos_quickfix_in_native_pattern(self, server_module, lsp_module) -> None:
        diags = server_module.get_diagnostics_for_pattern("(a+)+")
        redos = [d for d in diags if d.code == "REDOS_RISK"]
        assert len(redos) == 1
        diag = redos[0]
        assert diag.range.start.character == 0
        assert diag.range.end.character == 5

        params = lsp_module.CodeActionParams(
            text_document=lsp_module.TextDocument(uri="file:///tmp/x.strl"),
            range=diag.range,
            context=lsp_module.CodeActionContext(diagnostics=diags),
        )
        actions = server_module.code_action(server_module.server, params)
        assert len(actions) == 2
        assert actions[0].is_preferred is True
        assert actions[0].kind == lsp_module.CodeActionKind.QuickFix
        edit = actions[0].edit.changes["file:///tmp/x.strl"][0]
        assert edit.new_text == "(?>a+)+"
        assert edit.range.start.character == 0
        assert edit.range.end.character == 5


class TestHostLiteralCodeActions:
    def test_python_literal_pixel_perfect(self, server_module, lsp_module) -> None:
        py_src = 'pattern = s.parse("(a+)+")\n'
        uri = "file:///tmp/x.py"
        host_diags = server_module._diagnostics_for_host(uri, py_src)
        redos = [d for d in host_diags if d.code == "REDOS_RISK"]
        assert len(redos) == 1
        expected_col = py_src.index("(a+)+")
        assert redos[0].range.start.line == 0
        assert redos[0].range.start.character == expected_col
        assert redos[0].range.end.character == expected_col + 5

        params = lsp_module.CodeActionParams(
            text_document=lsp_module.TextDocument(uri=uri),
            range=redos[0].range,
            context=lsp_module.CodeActionContext(diagnostics=host_diags),
        )
        actions = server_module.code_action(server_module.server, params)
        assert {a.title for a in actions} == {
            actions[0].title,
            actions[1].title,
        }
        atomic_edit = actions[0].edit.changes[uri][0]
        assert atomic_edit.new_text == "(?>a+)+"
        assert atomic_edit.range.start.character == expected_col
        assert atomic_edit.range.end.character == expected_col + 5

    def test_typescript_template_literal_multiline(
        self, server_module, lsp_module
    ) -> None:
        # Template literals can span multiple lines; the projector must
        # walk the per-line offsets table to land the edit on the right row.
        ts_src = "const p = strl.simply.parse(`\n  (a+)+\n`);\n"
        uri = "file:///tmp/x.ts"
        host_diags = server_module._diagnostics_for_host(uri, ts_src)
        redos = [d for d in host_diags if d.code == "REDOS_RISK"]
        assert len(redos) == 1
        # The literal opens on line 0, but `(a+)+` lives on line 1 of the
        # host file (continuation lines start at col 0 in virtual coords,
        # which projects back to host col == virtual col).
        assert redos[0].range.start.line == 1
        assert redos[0].range.start.character == 2
        assert redos[0].range.end.character == 7

    def test_outside_range_yields_no_actions(self, server_module, lsp_module) -> None:
        py_src = 'pattern = s.parse("(a+)+")\n'
        uri = "file:///tmp/x.py"
        host_diags = server_module._diagnostics_for_host(uri, py_src)
        outside = lsp_module.Range(
            start=lsp_module.Position(line=0, character=0),
            end=lsp_module.Position(line=0, character=2),
        )
        params = lsp_module.CodeActionParams(
            text_document=lsp_module.TextDocument(uri=uri),
            range=outside,
            context=lsp_module.CodeActionContext(diagnostics=host_diags),
        )
        actions = server_module.code_action(server_module.server, params)
        assert actions == []
