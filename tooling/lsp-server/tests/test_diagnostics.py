"""Parameterized diagnostics regression suite.

This suite pins the editor-facing contract for two failure modes that surfaced
in the live extension:

* Host-language extraction must find STRling patterns behind every supported
    anchor, including ``s.parse(...)`` and ``STRling.parse(...)``.
* Native diagnostics must preserve canonical half-open UTF-8 source spans;
  embedded diagnostics must project those spans through the island algebra
  without widening or clamping them.

The tests run in-process so ``python3 -m pytest tests/test_diagnostics.py``
from ``tooling/lsp-server`` is enough to validate extraction, projection, and
publication.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, List

import pytest


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_LSP_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_LSP_DIR, "..", ".."))
_PY_SRC = os.path.join(_REPO_ROOT, "bindings", "python", "src")

for _path in (_PY_SRC, _LSP_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)


@dataclass(frozen=True)
class Scenario:
    """A diagnostics fixture with its expected publication outcome."""

    name: str
    source: str
    uri: str
    expected_line: int
    expect_error: bool


def _strl_source(pattern: str) -> Scenario:
    return Scenario(
        name="raw_strl",
        source=pattern,
        uri="file:///fixtures/pattern.strl",
        expected_line=0,
        expect_error=False,
    )


def _host_source(pattern: str) -> Scenario:
    return Scenario(
        name="quoted_host",
        source=f'const pattern = s.parse("{pattern}");',
        uri="file:///fixtures/pattern.ts",
        expected_line=0,
        expect_error=False,
    )


def _multiline_host_source(pattern: str) -> Scenario:
    tail = "\n".join(f"const filler_{index} = 'ok';" for index in range(2, 102))
    return Scenario(
        name="multiline_host",
        source=(
            'const valid = simply.parse("Email()");\n'
            f'const broken = STRling.parse("{pattern}");\n'
            f"{tail}\n"
        ),
        uri="file:///fixtures/pattern_multi.ts",
        expected_line=1,
        expect_error=False,
    )


def _with_expectation(scenario: Scenario, expect_error: bool) -> Scenario:
    return Scenario(
        name=scenario.name,
        source=scenario.source,
        uri=scenario.uri,
        expected_line=scenario.expected_line,
        expect_error=expect_error,
    )


_VALID_PATTERNS = ["abc", "a+", "[a-z]"]
_ERROR_PATTERNS = ["[a-z", "a{5,2}", "(abc", "^*"]
_SCENARIO_BUILDERS: List[Callable[[str], Scenario]] = [
    _strl_source,
    _host_source,
    _multiline_host_source,
]

_PARAM_CASES = [
    pytest.param(
        _with_expectation(builder(pattern), False),
        id=f"ok::{builder(pattern).name}::{pattern}",
    )
    for pattern in _VALID_PATTERNS
    for builder in _SCENARIO_BUILDERS
] + [
    pytest.param(
        _with_expectation(builder(pattern), True),
        id=f"err::{builder(pattern).name}::{pattern}",
    )
    for pattern in _ERROR_PATTERNS
    for builder in _SCENARIO_BUILDERS
]


_MULTI_ANCHOR_SOURCE = (
    'const a = simply.parse("Email()");\n'
    'const b = s.parse("(abc");\n'
    'const c = STRling.parse("[a-z");\n'
)
_MULTI_ANCHOR_URI = "file:///fixtures/diagnostics_drift.ts"


def _expected_island_layout() -> List[tuple[int, int, str]]:
    """Return the ground-truth ``(line, host_start_char, content)`` per island."""
    lines = _MULTI_ANCHOR_SOURCE.split("\n")
    contents = ["Email()", "(abc", "[a-z"]
    layout = []
    for line_no, content in enumerate(contents):
        literal = f'"{content}"'
        col = lines[line_no].index(literal) + 1
        layout.append((line_no, col, content))
    return layout


# --------------------------------------------------------------------------- #
# Module-import fixtures                                                      #
# --------------------------------------------------------------------------- #


@pytest.fixture
def server_module():
    """Import the LSP server module and reset its per-URI caches.

    Importing ``server.server`` loads the canonical bridge and the explicitly
    deferred editor adapters; caches are cleared so each test sees a pristine
    state. We deliberately import the inner module
    rather than the package because the package ``__init__`` is a thin
    pedagogy shim with no re-exports.
    """
    from server import server as server_mod  # type: ignore[import-not-found]

    server_mod._ISLANDS_BY_URI.clear()
    server_mod._LAST_DIAGNOSTICS.clear()
    return server_mod


@pytest.fixture
def islands_module():
    """Import the explicitly deferred island-extractor adapter."""
    from server.island_extractor import (  # noqa: WPS433 — local import by design
        extract_islands_for_uri,
    )

    return extract_islands_for_uri


# --------------------------------------------------------------------------- #
# Step 2.2 — Extractor coordinate truth table                                 #
# --------------------------------------------------------------------------- #


class TestExtractorCoordinates:
    """Assert the extractor returns exact 0-indexed offsets for every island."""

    def test_three_islands_extracted(self, islands_module) -> None:
        islands = islands_module(_MULTI_ANCHOR_SOURCE, _MULTI_ANCHOR_URI)
        assert len(islands) == 3, (
            "Multi-island sweep stopped early — extractor must not break "
            f"after the first match. Got {len(islands)} of 3."
        )

    def test_virtual_content_per_island(self, islands_module) -> None:
        islands = islands_module(_MULTI_ANCHOR_SOURCE, _MULTI_ANCHOR_URI)
        assert [i.virtual_content for i in islands] == ["Email()", "(abc", "[a-z"]

    def test_host_start_is_zero_indexed_and_exact(self, islands_module) -> None:
        islands = islands_module(_MULTI_ANCHOR_SOURCE, _MULTI_ANCHOR_URI)
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
        islands = islands_module(_MULTI_ANCHOR_SOURCE, _MULTI_ANCHOR_URI)
        for island, (line, col, _content) in zip(islands, _expected_island_layout()):
            mapped = island.to_host(0, 0)
            assert (mapped.line, mapped.character) == (line, col), (
                f"to_host(0,0) misprojected for {island.virtual_content!r}: "
                f"got ({mapped.line},{mapped.character}), "
                f"expected ({line},{col})"
            )

    def test_last_virtual_char_maps_inside_literal(self, islands_module) -> None:
        islands = islands_module(_MULTI_ANCHOR_SOURCE, _MULTI_ANCHOR_URI)
        for island, (line, col, content) in zip(islands, _expected_island_layout()):
            last = len(content) - 1
            mapped = island.to_host(0, last)
            assert (mapped.line, mapped.character) == (line, col + last), (
                f"Tail of {content!r} drifted: "
                f"got ({mapped.line},{mapped.character}), "
                f"expected ({line},{col + last})"
            )

    def test_strl_pure_mode_extracts_each_line(self, islands_module) -> None:
        islands = islands_module("(abc\n[a-z\n", "file:///fixtures/pure.strl")
        assert [island.virtual_content for island in islands] == ["(abc", "[a-z"]
        assert islands[0].host_start.line == 0
        assert islands[1].host_start.line == 1


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

    @pytest.mark.parametrize("scenario", _PARAM_CASES)
    def test_contextual_permutations_preserve_single_line_ranges(
        self, server_module, scenario: Scenario
    ) -> None:
        diagnostics = server_module._diagnostics_for_host(scenario.uri, scenario.source)
        if scenario.expect_error:
            assert diagnostics, (
                f"Expected at least one diagnostic for {scenario.name} but got none."
            )
            assert any(
                diag.range.start.line == scenario.expected_line for diag in diagnostics
            ), (
                f"No diagnostic landed on expected line {scenario.expected_line} for "
                f"{scenario.name}."
            )
        else:
            assert diagnostics == [], (
                f"Valid pattern unexpectedly produced diagnostics in {scenario.name}."
            )

        for diag in diagnostics:
            assert diag.range.start.line == diag.range.end.line, (
                f"Diagnostic bled across lines in {scenario.name}: {diag.range}"
            )
            assert diag.range.start.line == scenario.expected_line, (
                f"Diagnostic started on wrong line in {scenario.name}: {diag.range}"
            )
            assert diag.range.start.character <= diag.range.end.character, (
                f"Diagnostic range inverted in {scenario.name}: {diag.range}"
            )

    def test_host_projection_returns_diagnostic_per_error_island(
        self, server_module
    ) -> None:
        diagnostics = server_module._diagnostics_for_host(
            _MULTI_ANCHOR_URI, _MULTI_ANCHOR_SOURCE
        )
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
        assert per_island_counts[0] == 0, (
            f"Valid island #0 produced spurious diagnostics: {per_island_counts[0]}"
        )
        assert per_island_counts[1] >= 1, (
            "Island #1 (s.parse unterminated group) produced no diagnostic."
        )
        assert per_island_counts[2] >= 1, (
            "Island #2 (STRling.parse unterminated class) produced no diagnostic."
        )

    def test_diagnostic_ranges_stay_inside_their_literal(self, server_module) -> None:
        diagnostics = server_module._diagnostics_for_host(
            _MULTI_ANCHOR_URI, _MULTI_ANCHOR_SOURCE
        )
        layout = {
            line: (col, content) for line, col, content in _expected_island_layout()
        }
        for diag in diagnostics:
            line = diag.range.start.line
            assert line in layout, f"Stray diagnostic on line {line}"
            col, content = layout[line]
            start_char = diag.range.start.character
            end_char = diag.range.end.character
            literal_end = col + len(content)
            assert col <= start_char <= literal_end, (
                f"Squiggle start drifted outside literal on line {line}: "
                f"start={start_char} not in [{col},{literal_end}]"
            )
            assert col <= end_char <= literal_end, (
                f"Squiggle end drifted past the literal on line {line}: "
                f"end={end_char} not in [{col},{literal_end}]"
            )
            assert start_char <= end_char, (
                f"Inverted range on line {line}: start={start_char} > end={end_char}"
            )
            assert diag.range.start.line == diag.range.end.line, (
                f"Single-line invariant regressed on line {line}: {diag.range}"
            )

    def test_native_multiline_eof_preserves_canonical_span(self, server_module) -> None:
        source = "[a-z\n" + "\n".join(f"line_{index}" for index in range(1, 101))
        diagnostics = server_module._diagnostics_for_host(
            "file:///fixtures/bleed.strl", source
        )
        assert len(diagnostics) == 1
        diagnostic = diagnostics[0]
        assert diagnostic.code == "STRL-FRONTEND-2018"
        assert (
            diagnostic.range.start.line,
            diagnostic.range.start.character,
            diagnostic.range.end.line,
            diagnostic.range.end.character,
        ) == (100, len("line_100"), 100, len("line_100"))

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
                self.workspace = _StubWorkspace(_MULTI_ANCHOR_SOURCE)

            def text_document_publish_diagnostics(self, params) -> None:
                captured.append(params)

            # ``validate_document`` only calls ``show_message_log`` from
            # the exception path; provide a no-op so accidental fallbacks
            # do not blow up the test.
            def show_message_log(self, _msg: str) -> None:  # pragma: no cover
                pass

        ls = _Stub()
        server_module.validate_document(ls, _MULTI_ANCHOR_URI)
        assert len(captured) == 1, (
            f"Expected exactly one publish call, got {len(captured)}"
        )
        published = captured[0].diagnostics
        # Match the per-island invariants from the projection test so a
        # regression in ``validate_document`` is caught here too.
        error_lines = {d.range.start.line for d in published}
        assert 1 in error_lines, "Island #1 error not published."
        assert 2 in error_lines, "Island #2 error not published."
        assert 0 not in error_lines, (
            "Valid simply.parse island produced unexpected published diagnostic."
        )
        assert all(d.range.start.line == d.range.end.line for d in published)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
