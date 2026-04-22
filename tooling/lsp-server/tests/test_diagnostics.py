"""Diagnostic coordinate & multi-error regression suite.

These tests pin two invariants that recently regressed in the live
language server:

* **Zero-drift host coordinates.** LSP positions are 0-indexed
  (``line: 0, character: 0``) at both axes. Any 1-indexed math anywhere
  in the projection pipeline shifts the editor squiggle relative to the
  string literal that produced it. The tests here derive the expected
  column from ``str.index`` so the assertion fails the moment a single
  off-by-one slips in.

* **Exhaustive multi-island reporting.** A host file may embed multiple
  STRling patterns. The extractor must continue past the first match,
  and every diagnostic raised by every island must reach the published
  payload — the bug we are guarding against was a premature ``break``
  that dropped errors in islands #2 and beyond.

The suite runs entirely in-process — no LSP transport, no VS Code
restart — so ``python3 -m pytest tests/test_diagnostics.py`` from
``tooling/lsp-server`` is sufficient to validate the contract.
"""

from __future__ import annotations

import os
import sys
from typing import List

import pytest


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_LSP_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_LSP_DIR, "..", ".."))
_PY_SRC = os.path.join(_REPO_ROOT, "bindings", "python", "src")

for _path in (_PY_SRC, _LSP_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)


# --------------------------------------------------------------------------- #
# Fixture corpus                                                              #
# --------------------------------------------------------------------------- #
#
# A three-island TypeScript snippet. Islands #0 and #2 contain known
# parse errors; island #1 is valid and must produce zero diagnostics.
# The exact host columns are derived at runtime via ``str.index`` so the
# expected coordinates remain a function of the source — never a
# hand-typed magic number.

_HOST_SOURCE = (
    'const a = simply.parse("Email(");\n'  # line 0 — error island
    'const b = simply.parse("Email()");\n'  # line 1 — valid island
    'const c = simply.parse("Email()%)");\n'  # line 2 — error island
)
_HOST_URI = "file:///fixtures/diagnostics_drift.ts"


def _expected_island_layout() -> List[tuple]:
    """Return the ground-truth ``(line, host_start_char, content)`` per island.

    Computed from ``_HOST_SOURCE`` so a refactor of the fixture cannot
    silently drift the test's expectations.
    """
    lines = _HOST_SOURCE.split("\n")
    contents = ["Email(", "Email()", "Email()%)"]
    layout = []
    for line_no, content in enumerate(contents):
        # The literal opens with a `"` immediately before the content.
        # Locate the literal in the host line and take the inner offset.
        literal = f'"{content}"'
        col = lines[line_no].index(literal) + 1  # +1 to skip the opening quote
        layout.append((line_no, col, content))
    return layout


# --------------------------------------------------------------------------- #
# Module-import fixtures                                                      #
# --------------------------------------------------------------------------- #


@pytest.fixture
def server_module():
    """Import the LSP server module and reset its per-URI caches.

    Importing ``server.server`` triggers ``sys.path`` mutations that load
    the in-tree STRling Python binding; the caches are cleared so each
    test sees a pristine state. We deliberately import the inner module
    rather than the package because the package ``__init__`` is a thin
    pedagogy shim with no re-exports.
    """
    from server import server as server_mod  # type: ignore[import-not-found]

    server_mod._ISLANDS_BY_URI.clear()
    server_mod._LAST_DIAGNOSTICS.clear()
    return server_mod


@pytest.fixture
def islands_module():
    """Import the canonical island extractor surface."""
    from STRling.core.intelligence import (  # noqa: WPS433 — local import by design
        extract_islands_for_uri,
    )

    return extract_islands_for_uri


# --------------------------------------------------------------------------- #
# Step 2.2 — Extractor coordinate truth table                                 #
# --------------------------------------------------------------------------- #


class TestExtractorCoordinates:
    """Assert the extractor returns exact 0-indexed offsets for every island."""

    def test_three_islands_extracted(self, islands_module) -> None:
        islands = islands_module(_HOST_SOURCE, _HOST_URI)
        assert len(islands) == 3, (
            "Multi-island sweep stopped early — extractor must not break "
            f"after the first match. Got {len(islands)} of 3."
        )

    def test_virtual_content_per_island(self, islands_module) -> None:
        islands = islands_module(_HOST_SOURCE, _HOST_URI)
        assert [i.virtual_content for i in islands] == [
            "Email(",
            "Email()",
            "Email()%)",
        ]

    def test_host_start_is_zero_indexed_and_exact(self, islands_module) -> None:
        islands = islands_module(_HOST_SOURCE, _HOST_URI)
        for island, (line, col, content) in zip(islands, _expected_island_layout()):
            assert island.host_start.line == line, (
                f"Line drift on island {content!r}: "
                f"got {island.host_start.line}, expected {line}"
            )
            assert island.host_start.character == col, (
                f"Character drift on island {content!r}: "
                f"got {island.host_start.character}, expected {col}"
            )


# --------------------------------------------------------------------------- #
# Step 2.3 — Coordinate translation through the projection algebra            #
# --------------------------------------------------------------------------- #


class TestCoordinateTranslation:
    """Verify ``Island.to_host`` is a pure 0-indexed offset translator."""

    def test_first_virtual_char_maps_to_literal_start(self, islands_module) -> None:
        islands = islands_module(_HOST_SOURCE, _HOST_URI)
        for island, (line, col, _content) in zip(islands, _expected_island_layout()):
            mapped = island.to_host(0, 0)
            assert (mapped.line, mapped.character) == (line, col), (
                f"to_host(0,0) misprojected for {island.virtual_content!r}: "
                f"got ({mapped.line},{mapped.character}), "
                f"expected ({line},{col})"
            )

    def test_last_virtual_char_maps_inside_literal(self, islands_module) -> None:
        islands = islands_module(_HOST_SOURCE, _HOST_URI)
        for island, (line, col, content) in zip(islands, _expected_island_layout()):
            last = len(content) - 1
            mapped = island.to_host(0, last)
            assert (mapped.line, mapped.character) == (line, col + last), (
                f"Tail of {content!r} drifted: "
                f"got ({mapped.line},{mapped.character}), "
                f"expected ({line},{col + last})"
            )


# --------------------------------------------------------------------------- #
# Step 2.4 — End-to-end diagnostic publication                                #
# --------------------------------------------------------------------------- #


class _StubWorkspace:
    """Minimal workspace stand-in for ``validate_document``.

    Only the ``get_text_document(uri)`` method is exercised by the
    server, so we expose just that surface and return an object with a
    ``source`` attribute.
    """

    def __init__(self, source: str) -> None:
        self._source = source

    def get_text_document(self, _uri: str):
        class _Doc:
            source = self._source

        return _Doc()


class TestDiagnosticPublication:
    """Drive the host-projection pipeline and verify every error surfaces."""

    def test_host_projection_returns_diagnostic_per_error_island(
        self, server_module
    ) -> None:
        diagnostics = server_module._diagnostics_for_host(_HOST_URI, _HOST_SOURCE)
        # Two error islands, each must contribute at least one diagnostic.
        # The valid middle island must contribute zero. We assert on a
        # per-island bucket rather than a flat total so REDOS-style
        # multi-warning emitters cannot mask a missing primary error.
        layout = _expected_island_layout()
        per_island_counts = [0, 0, 0]
        for diag in diagnostics:
            for idx, (line, _col, _content) in enumerate(layout):
                if diag.range.start.line == line:
                    per_island_counts[idx] += 1
                    break
            else:
                pytest.fail(
                    f"Diagnostic published outside any island line: {diag.range}"
                )
        assert per_island_counts[0] >= 1, (
            "Island #0 (unclosed paren) produced no diagnostic — "
            "exhaustive reporting regressed."
        )
        assert per_island_counts[1] == 0, (
            f"Valid island #1 produced spurious diagnostics: {per_island_counts[1]}"
        )
        assert per_island_counts[2] >= 1, (
            "Island #2 (trailing junk) produced no diagnostic — the "
            "extractor likely stopped after the first match."
        )

    def test_diagnostic_ranges_stay_inside_their_literal(self, server_module) -> None:
        diagnostics = server_module._diagnostics_for_host(_HOST_URI, _HOST_SOURCE)
        layout = {
            line: (col, content) for line, col, content in _expected_island_layout()
        }
        for diag in diagnostics:
            line = diag.range.start.line
            assert line in layout, f"Stray diagnostic on line {line}"
            col, content = layout[line]
            start_char = diag.range.start.character
            end_char = diag.range.end.character
            # ``literal_end`` is the host column of the closing quote — i.e.
            # one past the last content character. The parser may anchor
            # an unterminated-group diagnostic at the virtual EOF position
            # (one past content), which after projection lands the
            # exclusive ``end`` at ``literal_end + 1``. We accept that as
            # a legitimate EOF marker and only fail when the range drifts
            # further (the regression we are guarding against).
            literal_end = col + len(content)
            assert col <= start_char <= literal_end, (
                f"Squiggle start drifted outside literal on line {line}: "
                f"start={start_char} not in [{col},{literal_end}]"
            )
            assert col <= end_char <= literal_end + 1, (
                f"Squiggle end drifted past EOF marker on line {line}: "
                f"end={end_char} not in [{col},{literal_end + 1}]"
            )
            assert start_char <= end_char, (
                f"Inverted range on line {line}: start={start_char} > end={end_char}"
            )

    def test_validate_document_publishes_all_diagnostics(self, server_module) -> None:
        """Drive ``validate_document`` end-to-end with a stub workspace.

        This guards the publication pathway itself — not just the
        projection helper — so a future refactor that swaps the
        publishing transport cannot silently drop diagnostics.
        """
        captured: List = []

        class _Stub(server_module.STRlingLanguageServer):
            def __init__(self) -> None:  # noqa: D401 — fixture stub
                # Skip JSON-RPC base init; we only need the two attrs the
                # validator touches.
                self.workspace = _StubWorkspace(_HOST_SOURCE)

            def text_document_publish_diagnostics(self, params) -> None:
                captured.append(params)

            # ``validate_document`` only calls ``show_message_log`` from
            # the exception path; provide a no-op so accidental fallbacks
            # do not blow up the test.
            def show_message_log(self, _msg: str) -> None:  # pragma: no cover
                pass

        ls = _Stub()
        server_module.validate_document(ls, _HOST_URI)
        assert len(captured) == 1, (
            f"Expected exactly one publish call, got {len(captured)}"
        )
        published = captured[0].diagnostics
        # Match the per-island invariants from the projection test so a
        # regression in ``validate_document`` is caught here too.
        error_lines = {d.range.start.line for d in published}
        assert 0 in error_lines, "Island #0 error not published."
        assert 2 in error_lines, "Island #2 error not published."
        assert 1 not in error_lines, (
            "Valid middle island produced unexpected published diagnostic."
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
