"""
Module Pedagogy:
================
This module is the canonical home of STRling's "Island Grammar" extractor.
Host-language source files (TypeScript, Python, Rust, Java) embed STRling
patterns inside string-literal arguments to well-known boundary calls such
as ``s.parse("...")`` or ``strl.simply.parse(`...`)``. The extractor here
finds those literals, captures their *raw* characters (no escape unfolding,
so a 1:1 host↔virtual coordinate mapping holds), and emits ``Island``
objects that the language-intelligence layer feeds to the parser.

The boundary-call regexes and the language-suffix routing table are NOT
defined here — they live in ``spec/tooling/island_boundaries.json`` so the
Python language-intelligence layer and the Node test extractor read from a
single source of truth. This module owns the *algorithm* (literal scanning,
coordinate mirroring); the JSON owns the *registry* (which calls open an
island, which suffixes pick which language).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Public data structures                                                      #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class HostPosition:
    """A zero-based ``(line, character)`` coordinate inside the host file."""

    line: int
    character: int


@dataclass
class Island:
    """A single embedded STRling pattern extracted from a host document.

    Attributes
    ----------
    virtual_content : str
        Raw string-literal content (no unescaping) — fed to the parser.
    host_start : HostPosition
        Coordinate of the *first* character of ``virtual_content`` in the
        host file.
    line_offsets : List[HostPosition]
        ``line_offsets[v]`` gives the host ``(line, character)`` where the
        ``v``-th virtual line begins. Index 0 always equals ``host_start``.
    boundary_call : str
        The boundary expression that introduced the island (e.g. ``s.parse``).
        Useful for hover provenance and debug logging.
    """

    virtual_content: str
    host_start: HostPosition
    line_offsets: List[HostPosition] = field(default_factory=lambda: [])
    boundary_call: str = ""

    def to_host(self, vd_line: int, vd_character: int) -> HostPosition:
        """Project a virtual-document position back onto the host file."""
        if not self.line_offsets:
            return self.host_start
        if vd_line < 0:
            vd_line = 0
        if vd_line >= len(self.line_offsets):
            vd_line = len(self.line_offsets) - 1
        base = self.line_offsets[vd_line]
        # Subsequent virtual lines start at host column 0; the first virtual
        # line is offset by the column where the literal opened.
        host_char = base.character + vd_character if vd_line == 0 else vd_character
        return HostPosition(line=base.line, character=host_char)

    def contains_host(self, line: int, character: int) -> bool:
        """Return True if a host coordinate lies inside this island."""
        if not self.line_offsets:
            return False
        last_line_idx = len(self.line_offsets) - 1
        last_base = self.line_offsets[last_line_idx]
        lines = self.virtual_content.split("\n")
        last_len = len(lines[last_line_idx])
        last_end_char = (
            last_base.character + last_len if last_line_idx == 0 else last_len
        )

        first = self.line_offsets[0]
        if line < first.line or line > last_base.line:
            return False
        if line == first.line and character < first.character:
            return False
        if line == last_base.line and character > last_end_char:
            return False
        return True

    def from_host(self, line: int, character: int) -> Optional[Tuple[int, int]]:
        """Inverse of :meth:`to_host`. Returns ``None`` if outside the island."""
        if not self.contains_host(line, character):
            return None
        for vd_line, base in enumerate(self.line_offsets):
            if base.line == line:
                vd_char = character - base.character if vd_line == 0 else character
                return (vd_line, max(0, vd_char))
        return None


# --------------------------------------------------------------------------- #
# Boundary registry — loaded from spec/tooling/island_boundaries.json         #
# --------------------------------------------------------------------------- #


# Built-in fallback used when the spec JSON cannot be located (e.g. when the
# package is installed outside the repository tree). Keeping the fallback
# here means installed users still get correct island extraction even if the
# spec file is missing — they only lose the ability to amend boundaries
# without a code change.
_DEFAULT_BOUNDARIES: Dict[str, List[str]] = {
    "python": [
        r"\bs\.parse\s*\(\s*",
        r"\bstrl\.parse\s*\(\s*",
        r"\bSTRling\.parse\s*\(\s*",
        r"\bPattern\s*\(\s*",
    ],
    "typescript": [
        r"\bstrl\.simply\.parse\s*\(\s*",
        r"\bsimply\.parse\s*\(\s*",
        r"\bstrl\.parse\s*\(\s*",
        r"\bs\.parse\s*\(\s*",
        r"\bnew\s+Pattern\s*\(\s*",
    ],
    "rust": [
        r"\bstrling::parse!\s*\(\s*",
        r"\bstrl::parse\s*\(\s*",
        r"\bstrling::Pattern::new\s*\(\s*",
    ],
    "java": [
        r"\bSTRling\.parse\s*\(\s*",
        r"\bSTRlingPattern\s*\.\s*compile\s*\(\s*",
    ],
}

_DEFAULT_LANGUAGE_BY_SUFFIX: Dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
    ".rs": "rust",
    ".java": "java",
}


# Cache of the most recently loaded spec so we do not pay disk I/O per
# extraction call. The cache key is the resolved spec path (or ``None``
# when the fallback is in use).
_boundary_cache: Optional[Dict[str, List[str]]] = None
_suffix_cache: Optional[Dict[str, str]] = None
_spec_path_cache: Optional[Path] = None


def _candidate_spec_paths() -> List[Path]:
    """Return the ordered list of paths to probe for the boundary spec.

    Priority (highest first):

    1. ``$STRLING_ISLAND_BOUNDARIES_PATH`` — explicit override for tooling
       and tests that want to point at a non-default spec file.
    2. Repository-root ``spec/tooling/island_boundaries.json`` — discovered
       by walking up from this file. This is the path used during normal
       in-tree development, including the LSP server and the CLI tools.
    """
    paths: List[Path] = []
    env_override = os.environ.get("STRLING_ISLAND_BOUNDARIES_PATH")
    if env_override:
        paths.append(Path(env_override))

    # Walk up from this module until we hit a directory that contains the
    # canonical spec layout. Stop after a reasonable number of parents so we
    # do not scan the filesystem root in pathological install scenarios.
    here = Path(__file__).resolve()
    for parent in (here, *here.parents)[:10]:
        candidate = parent / "spec" / "tooling" / "island_boundaries.json"
        if candidate.is_file():
            paths.append(candidate)
            break
    return paths


def _load_spec() -> Tuple[Dict[str, List[str]], Dict[str, str], Optional[Path]]:
    """Load and cache the shared boundary registry.

    Returns a triple ``(boundaries, suffix_map, spec_path)``. ``spec_path``
    is ``None`` when the built-in fallback is in use.
    """
    global _boundary_cache, _suffix_cache, _spec_path_cache
    if _boundary_cache is not None and _suffix_cache is not None:
        return _boundary_cache, _suffix_cache, _spec_path_cache

    for candidate in _candidate_spec_paths():
        try:
            data: Any = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        languages: Dict[str, Any] = data.get("languages") or {}
        boundaries: Dict[str, List[str]] = {}
        suffixes: Dict[str, str] = {}
        for lang, entry in languages.items():
            patterns: List[Any] = list(entry.get("boundaries") or [])
            if patterns:
                boundaries[str(lang)] = [str(p) for p in patterns]
            entry_suffixes: List[Any] = list(entry.get("suffixes") or [])
            for suffix in entry_suffixes:
                suffixes[str(suffix).lower()] = str(lang)
        if boundaries and suffixes:
            _boundary_cache = boundaries
            _suffix_cache = suffixes
            _spec_path_cache = candidate
            return _boundary_cache, _suffix_cache, _spec_path_cache

    _boundary_cache = dict(_DEFAULT_BOUNDARIES)
    _suffix_cache = dict(_DEFAULT_LANGUAGE_BY_SUFFIX)
    _spec_path_cache = None
    return _boundary_cache, _suffix_cache, _spec_path_cache


def reload_boundary_spec() -> None:
    """Drop the cached spec so the next call re-reads disk.

    Provided for tests and long-running tools that may want to swap the
    spec file at runtime via ``STRLING_ISLAND_BOUNDARIES_PATH``.
    """
    global _boundary_cache, _suffix_cache, _spec_path_cache
    _boundary_cache = None
    _suffix_cache = None
    _spec_path_cache = None


def boundary_calls() -> Dict[str, List[str]]:
    """Return the boundary-call regex registry, indexed by language id."""
    boundaries, _suffixes, _path = _load_spec()
    return boundaries


def language_suffixes() -> Dict[str, str]:
    """Return the suffix → language id mapping."""
    _boundaries, suffixes, _path = _load_spec()
    return suffixes


def language_for_uri(uri: str) -> Optional[str]:
    """Return the boundary-language for a document URI, or ``None``."""
    suffixes = language_suffixes()
    lower = uri.lower()
    for suffix, lang in suffixes.items():
        if lower.endswith(suffix):
            return lang
    return None


# --------------------------------------------------------------------------- #
# String-literal scanners                                                     #
# --------------------------------------------------------------------------- #


# Python / Rust / Java / JS share enough literal syntax that we can enumerate
# the supported forms in a single table. Each entry is
# ``(opening_delimiter, closing_delimiter, allow_escape)``.
#
# String interpolation (template-literal expressions, f-string braces) is
# intentionally out of scope — interpolation breaks the 1:1 character-mapping
# guarantee that the projection algebra depends on.
_LITERAL_FORMS: List[Tuple[str, str, bool]] = [
    ('"""', '"""', True),
    ("'''", "'''", True),
    ("`", "`", True),  # JS/TS template literal (no ${} support)
    ('r"', '"', False),  # Python raw string
    ("r'", "'", False),
    ('"', '"', True),
    ("'", "'", True),
]


def _scan_literal(source: str, start: int) -> Optional[Tuple[str, int, int]]:
    """Scan a string literal beginning at ``source[start]``.

    Returns ``(content, content_start, content_end)`` where the indices are
    absolute offsets into ``source`` and ``content`` is the *raw* text
    between the delimiters. Returns ``None`` if no recognisable literal
    starts at the position.
    """
    for opener, closer, allow_escape in _LITERAL_FORMS:
        if not source.startswith(opener, start):
            continue
        content_start = start + len(opener)
        idx = content_start
        while idx < len(source):
            ch = source[idx]
            if allow_escape and ch == "\\" and idx + 1 < len(source):
                # Skip escape sequence — note we still advance over the
                # original characters (no unfolding) preserving 1:1 mapping.
                idx += 2
                continue
            if source.startswith(closer, idx):
                return source[content_start:idx], content_start, idx
            idx += 1
        # Unterminated literal — bail out.
        return None
    return None


# --------------------------------------------------------------------------- #
# Offset bookkeeping                                                          #
# --------------------------------------------------------------------------- #


def _offset_to_position(source: str, offset: int) -> HostPosition:
    """Convert an absolute byte offset to a zero-based ``(line, char)``."""
    if offset <= 0:
        return HostPosition(0, 0)
    prefix = source[:offset]
    line = prefix.count("\n")
    last_nl = prefix.rfind("\n")
    char = offset if last_nl == -1 else offset - last_nl - 1
    return HostPosition(line=line, character=char)


def _build_line_offsets(content: str, start: HostPosition) -> List[HostPosition]:
    """Compute per-virtual-line host positions for an extracted island."""
    offsets = [start]
    line_no = start.line
    for ch in content:
        if ch == "\n":
            line_no += 1
            offsets.append(HostPosition(line=line_no, character=0))
    return offsets


# --------------------------------------------------------------------------- #
# Public extraction entry points                                              #
# --------------------------------------------------------------------------- #


def extract_islands(source: str, language: str) -> List[Island]:
    """Sweep ``source`` for STRling boundary calls and return all islands."""
    boundaries = boundary_calls().get(language)
    if not boundaries:
        return []

    combined = re.compile("|".join(f"(?:{p})" for p in boundaries))
    islands: List[Island] = []
    for match in combined.finditer(source):
        literal_start = match.end()
        scanned = _scan_literal(source, literal_start)
        if scanned is None:
            continue
        content, content_start, _content_end = scanned
        host_start = _offset_to_position(source, content_start)
        line_offsets = _build_line_offsets(content, host_start)
        islands.append(
            Island(
                virtual_content=content,
                host_start=host_start,
                line_offsets=line_offsets,
                boundary_call=match.group(0).rstrip("( \t").rstrip(),
            )
        )
    return islands


def extract_islands_for_uri(source: str, uri: str) -> List[Island]:
    """Convenience wrapper that derives the language from the URI suffix."""
    lang = language_for_uri(uri)
    if lang is None:
        return []
    return extract_islands(source, lang)


__all__ = [
    "HostPosition",
    "Island",
    "boundary_calls",
    "extract_islands",
    "extract_islands_for_uri",
    "language_for_uri",
    "language_suffixes",
    "reload_boundary_spec",
]
